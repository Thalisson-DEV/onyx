"""The occurrence ledger as a screen: one row per case, details on demand."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy.orm import Session, aliased

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import acl
from onyx.db.ton.agent_occurrences import TERMINAL
from onyx.db.ton.enums import AssignmentStatus
from onyx.db.ton.models import (
    BusinessUnit,
    Finding,
    Occurrence,
    OccurrenceAssignment,
    OccurrenceEvent,
    OccurrenceNote,
    RuleVersion,
)
from onyx.ton.agent.labels import business_label

LedgerFilter = Literal["open", "overdue", "all"]


class LedgerRow(BaseModel):
    id: UUID
    reference: str
    title: str
    rule: str | None
    unit: str | None
    criticality: str
    criticality_code: str
    status: str
    open: bool
    owner: str | None
    deadline: date | None
    overdue: bool
    detections: int
    impact: Decimal | None
    last_detected_at: datetime


class LedgerPage(BaseModel):
    rows: list[LedgerRow]
    total: int
    open_total: int
    overdue_total: int


class LedgerHistoryItem(BaseModel):
    at: datetime
    text: str


class LedgerDetail(BaseModel):
    row: LedgerRow
    verification: str | None
    evidence: dict[str, Any] | None
    history: list[LedgerHistoryItem]


def _latest_assignment() -> Any:
    previous = aliased(OccurrenceAssignment)
    return (
        sa.select(sa.func.max(previous.sequence_no))
        .where(previous.occurrence_id == Occurrence.id)
        .correlate(Occurrence)
        .scalar_subquery()
    )


def _impact_subquery() -> Any:
    return (
        sa.select(Finding.computed_impact_amount)
        .where(Finding.occurrence_id == Occurrence.id)
        .order_by(Finding.detected_at.desc())
        .limit(1)
        .correlate(Occurrence)
        .scalar_subquery()
    )


def _row(
    occurrence: Occurrence,
    assignment: OccurrenceAssignment | None,
    rule_code: str | None,
    unit_name: str | None,
    impact: Decimal | None,
    today: date,
) -> LedgerRow:
    is_open = occurrence.status not in TERMINAL
    overdue = bool(
        is_open
        and assignment is not None
        and assignment.status == AssignmentStatus.OPEN
        and assignment.deadline is not None
        and assignment.deadline < today
    )
    return LedgerRow(
        id=occurrence.id,
        reference=occurrence.short_code,
        title=occurrence.title[:500],
        rule=rule_code,
        unit=unit_name,
        criticality=business_label(occurrence.criticality.value),
        criticality_code=occurrence.criticality.value,
        status=business_label(occurrence.status.value),
        open=is_open,
        owner=assignment.responsible_label[:200]
        if assignment and assignment.status == AssignmentStatus.OPEN
        else None,
        deadline=assignment.deadline
        if assignment and assignment.status == AssignmentStatus.OPEN
        else None,
        overdue=overdue,
        detections=occurrence.detection_count,
        impact=impact,
        last_detected_at=occurrence.last_detected_at,
    )


def _statement(user: User) -> Any:
    return (
        sa.select(Occurrence, OccurrenceAssignment, RuleVersion.title, BusinessUnit.name, _impact_subquery())
        .select_from(Occurrence)
        .outerjoin(
            OccurrenceAssignment,
            sa.and_(
                OccurrenceAssignment.occurrence_id == Occurrence.id,
                OccurrenceAssignment.sequence_no == _latest_assignment(),
            ),
        )
        .outerjoin(RuleVersion, RuleVersion.id == Occurrence.current_rule_version_id)
        .outerjoin(BusinessUnit, BusinessUnit.id == Occurrence.business_unit_id)
        .where(acl.occurrence_visible_clause(user))
    )


CRITICALITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "MONITORING": 3}


def ledger_page(
    session: Session,
    user: User,
    status: LedgerFilter,
    text: str | None,
    limit: int,
    offset: int,
) -> LedgerPage:
    acl.assert_global(user, permission=Permission.READ_TON_OCCURRENCES)
    today = datetime.now(UTC).date()
    rows = [
        _row(occurrence, assignment, code, unit, impact, today)
        for occurrence, assignment, code, unit, impact in session.execute(_statement(user)).all()
    ]
    open_rows = [row for row in rows if row.open]
    overdue_rows = [row for row in rows if row.overdue]
    chosen = open_rows if status == "open" else overdue_rows if status == "overdue" else rows
    if text:
        folded = text.lower()
        chosen = [
            row
            for row in chosen
            if folded in f"{row.reference} {row.title} {row.unit or ''} {row.owner or ''} {row.rule or ''}".lower()
        ]
    chosen.sort(
        key=lambda row: (
            not row.open,
            not row.overdue,
            CRITICALITY_ORDER.get(row.criticality_code, 9),
            -row.last_detected_at.timestamp(),
        )
    )
    return LedgerPage(
        rows=chosen[offset : offset + limit],
        total=len(chosen),
        open_total=len(open_rows),
        overdue_total=len(overdue_rows),
    )


TRANSITION_TEXT = {
    "DETECT": "Detectada",
    "REPEAT_DETECTED": "Detectada de novo",
    "REOPENED": "Reaberta",
    "SUPERSEDE": "Substituída por nova geração",
}


def ledger_detail(session: Session, user: User, occurrence_id: UUID) -> LedgerDetail:
    acl.assert_global(user, permission=Permission.READ_TON_OCCURRENCES)
    occurrence = acl.get_occurrence_for_user(session, user, occurrence_id)
    today = datetime.now(UTC).date()
    found = session.execute(
        _statement(user).where(Occurrence.id == occurrence.id)
    ).first()
    assert found is not None
    row = _row(*found, today)
    finding = session.scalar(
        sa.select(Finding)
        .where(Finding.occurrence_id == occurrence.id)
        .order_by(Finding.detected_at.desc())
        .limit(1)
    )
    history: list[LedgerHistoryItem] = []
    for event in session.scalars(
        sa.select(OccurrenceEvent).where(OccurrenceEvent.occurrence_id == occurrence.id)
    ):
        label = TRANSITION_TEXT.get(event.transition.value) or business_label(event.transition.value)
        reason = f": {event.reason}" if event.reason else ""
        history.append(LedgerHistoryItem(at=event.occurred_at, text=f"{label}{reason}"))
    for assignment in session.scalars(
        sa.select(OccurrenceAssignment).where(OccurrenceAssignment.occurrence_id == occurrence.id)
    ):
        deadline = f" até {assignment.deadline:%d/%m/%Y}" if assignment.deadline else ""
        history.append(
            LedgerHistoryItem(
                at=assignment.assigned_at,
                text=f"Responsável: {assignment.responsible_label}{deadline}",
            )
        )
    for note in session.scalars(
        sa.select(OccurrenceNote).where(OccurrenceNote.occurrence_id == occurrence.id)
    ):
        history.append(LedgerHistoryItem(at=note.created_at, text=f"Nota: {note.body}"))
    history.sort(key=lambda item: item.at)
    payload = dict(finding.deterministic_payload) if finding else None
    return LedgerDetail(
        row=row,
        verification=occurrence.verification_criterion,
        evidence=payload,
        history=history,
    )
