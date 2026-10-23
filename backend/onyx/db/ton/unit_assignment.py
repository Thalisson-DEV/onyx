"""Units the Controladoria assigns to NG entries that have none.

An assignment is keyed by the record's content identity (the review record
key, without sheet or row), so it survives a re-import and stops applying as
soon as the NG export carries the unit itself.
"""

import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton.acl import business_unit_visible_clause
from onyx.db.ton.enums import OccurrenceStatus
from onyx.db.ton.financial_review import (
    load_finding_states,
    load_review_inputs,
    record_review_decision__no_commit,
)
from onyx.db.ton.models import (
    BusinessUnit,
    FinancialNormalizationRun,
    Finding,
    FindingEvidence,
    ImportProfileExecution,
    Occurrence,
    ParsedSourceRecord,
    RecordUnitAssignment,
    ReviewRun,
    Rule,
)
from onyx.db.ton.sources import get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.financial_domain.readiness_models import EvidenceRecordView
from onyx.ton.financial_review.catalog import DEFAULT_CATALOG
from onyx.ton.financial_review.models import (
    JustificationCategory,
    ReviewDecisionKind,
    ReviewDecisionRequest,
    UnitMissingItemView,
)
from onyx.ton.financial_review.rules import record_keys

UNIT_MISSING_RULE = "NGF-UNIT-MISSING"
OPEN_STATUSES = frozenset(
    {OccurrenceStatus.NEW, OccurrenceStatus.REOPENED, OccurrenceStatus.CONFIRMED}
)


def latest_assignments(
    rows: list[tuple[str, UUID | None]],
) -> dict[str, UUID]:
    """Rows newest first: the first per key is in force; None undoes it."""
    seen: dict[str, UUID | None] = {}
    for key, unit_id in rows:
        seen.setdefault(key, unit_id)
    return {key: unit_id for key, unit_id in seen.items() if unit_id is not None}


def current_assignments(session: Session, source_id: UUID) -> dict[str, UUID]:
    rows = session.execute(
        sa.select(RecordUnitAssignment.record_key, RecordUnitAssignment.unit_id)
        .where(RecordUnitAssignment.source_id == source_id)
        .order_by(
            RecordUnitAssignment.created_at.desc(), RecordUnitAssignment.id.desc()
        )
    ).all()
    return latest_assignments([(key, unit_id) for key, unit_id in rows])


def record_keys_of(
    session: Session, execution: ImportProfileExecution
) -> dict[UUID, str]:
    """Content identity of every record of one NG import."""
    records, _ = load_review_inputs(session, execution)
    return {
        record_id: key.review_key
        for record_id, key in record_keys(records, frozenset()).items()
    }


def assign_unit__no_commit(
    session: Session,
    user: User,
    occurrence_id: UUID,
    unit_id: UUID | None,
    reason: str,
) -> int:
    """Assign a unit to the records of a unit-missing case and decide it."""
    occurrence = session.get(Occurrence, occurrence_id)
    if occurrence is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Occurrence not found")
    rule = session.get(Rule, occurrence.rule_id)
    if rule is None or not rule.code.startswith(UNIT_MISSING_RULE):
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Only entries without a unit take a unit"
        )
    unit = (
        session.scalar(
            sa.select(BusinessUnit).where(
                BusinessUnit.id == unit_id,
                BusinessUnit.is_active.is_(True),
                business_unit_visible_clause(user),
            )
        )
        if unit_id is not None
        else None
    )
    if unit_id is not None and unit is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Business unit not found")
    latest_finding = session.scalar(
        sa.select(Finding.id)
        .where(Finding.occurrence_id == occurrence_id)
        .order_by(Finding.detected_at.desc())
        .limit(1)
    )
    record_ids = list(
        session.scalars(
            sa.select(FindingEvidence.parsed_record_id).where(
                FindingEvidence.finding_id == latest_finding,
                FindingEvidence.parsed_record_id.is_not(None),
            )
        )
    )
    records = list(
        session.scalars(
            sa.select(ParsedSourceRecord).where(ParsedSourceRecord.id.in_(record_ids))
        )
    )
    if not records:
        raise OnyxError(OnyxErrorCode.CONFLICT, "The case has no NG entries")
    if any(record.administrative_unit for record in records):
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "The NG already gives a unit to this entry"
        )
    keys: dict[UUID, str] = {}
    for execution_id in {record.execution_id for record in records}:
        execution = session.get(ImportProfileExecution, execution_id)
        assert execution is not None
        keys.update(record_keys_of(session, execution))
    note = reason.strip()
    for record in records:
        session.add(
            RecordUnitAssignment(
                source_id=record.source_id,
                record_key=keys[record.id],
                unit_id=unit.id if unit else None,
                occurrence_id=occurrence_id,
                reason=note
                or (
                    "Unidade atribuída pela Controladoria"
                    if unit
                    else "Atribuição desfeita pela Controladoria"
                ),
                created_by=user.id,
            )
        )
    session.flush()
    # A case already accepted keeps its decision; only the unit changes. Undoing
    # leaves the case as it is.
    if unit is None or occurrence.status not in OPEN_STATUSES:
        return len(records)
    decision_reason = f"Unidade atribuída pela Controladoria: {unit.name}" + (
        f" — {note}" if note else ""
    )
    record_review_decision__no_commit(
        session,
        user,
        occurrence_id,
        ReviewDecisionRequest(
            kind=ReviewDecisionKind.JUSTIFY_EXCEPTION,
            reason=decision_reason[:2000],
            justification_category=JustificationCategory.BUSINESS_EXCEPTION,
            authorization_reference="Controladoria",
        ),
        DEFAULT_CATALOG,
    )
    # The decision above is the audited event; each assignment row keeps its
    # author and time.
    return len(records)


def list_unit_missing(session: Session, user: User) -> list[UnitMissingItemView]:
    """Every NG entry of the current base without a unit, decided or not."""
    from onyx.db.ton.financial_readiness import ng_evidence

    run = session.scalar(
        sa.select(FinancialNormalizationRun)
        .where(FinancialNormalizationRun.status == "SUCCEEDED")
        .order_by(FinancialNormalizationRun.started_at.desc())
        .limit(1)
    )
    if run is None:
        return []
    review = session.get(ReviewRun, run.review_run_id)
    execution = (
        session.get(ImportProfileExecution, review.execution_id) if review else None
    )
    if review is None or execution is None:
        return []
    # The entries come straight from the NG file, which covers every unit:
    # only who reads that source sees them.
    get_source(session, user, review.source_id)
    states, _ = load_finding_states(
        session, review, datetime.datetime.now(datetime.timezone.utc)
    )
    cases = [state for state in states if state.rule_key == UNIT_MISSING_RULE]
    if not cases:
        return []
    record_ids = {record_id for state in cases for record_id in state.record_ids}
    records = {
        record.id: record
        for record in session.scalars(
            sa.select(ParsedSourceRecord).where(ParsedSourceRecord.id.in_(record_ids))
        )
    }
    keys = record_keys_of(session, execution)
    assigned = current_assignments(session, review.source_id)
    statuses = {
        occurrence.id: occurrence.status
        for occurrence in session.scalars(
            sa.select(Occurrence).where(
                Occurrence.id.in_({state.occurrence_id for state in cases})
            )
        )
    }
    items: list[UnitMissingItemView] = []
    for state in sorted(
        cases, key=lambda item: (item.sheet_month or 0, str(item.occurrence_id))
    ):
        evidence: list[EvidenceRecordView] = [
            ng_evidence(records[record_id], None)
            for record_id in state.record_ids
            if record_id in records
        ]
        units = {
            assigned.get(keys.get(record_id, ""))
            for record_id in state.record_ids
            if record_id in records
        }
        status = statuses.get(state.occurrence_id)
        items.append(
            UnitMissingItemView(
                occurrence_id=state.occurrence_id,
                open=status in OPEN_STATUSES,
                records=evidence,
                assigned_unit_id=next(iter(units)) if len(units) == 1 else None,
            )
        )
    return items
