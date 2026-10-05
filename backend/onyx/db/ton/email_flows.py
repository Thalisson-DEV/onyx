"""Email flows persistence and the read models flows consume.

Reads only TON data: the NG is never written. Flows run with the visibility
of their owner (who registered or activated them), so a flow never e-mails
what that person could not see in TON.
"""

import datetime
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import acl
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import OccurrenceTransition, TonAuditResourceKind
from onyx.db.ton.financial_review import FINDING_SCHEMA
from onyx.db.ton.models import (
    EmailFlow,
    EmailFlowDelivery,
    EmailFlowEvent,
    EmailFlowRun,
    EmailFlowVersion,
    Finding,
    FindingEvidence,
    Occurrence,
    OccurrenceEvent,
    ParsedSourceRecord,
    ReviewRun,
)
from onyx.db.ton.occurrences import OPEN_STATUSES
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.email_flows.catalog import (
    DEFAULT_NG_CORRECTION,
    EVENT_KIND_DRE,
    ITEM_STATE_LABELS,
    NG_CORRECTIONS,
    ItemState,
)
from onyx.ton.email_flows.logic import FlowItem, format_money, state_of
from onyx.ton.email_flows.models import (
    FlowDefinition,
    FlowOrigin,
    FlowStatus,
)
from onyx.ton.financial_review.catalog import DEFAULT_CATALOG
from onyx.ton.financial_review.models import ReviewRunStatus
from onyx.utils.audit import AuditAction, AuditOutcome

# ---------------------------------------------------------------------------
# Access
# ---------------------------------------------------------------------------


def can_read(user: User) -> bool:
    return acl.holds_ton_report_read_capability(user) or acl.is_ton_administrator(user)


def can_manage(user: User) -> bool:
    return acl.holds_ton_report_manage_capability(user) or acl.is_ton_administrator(
        user
    )


def require_read(user: User) -> None:
    if not can_read(user):
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS)


def require_manage(user: User) -> None:
    if not can_manage(user):
        raise OnyxError(
            OnyxErrorCode.INSUFFICIENT_PERMISSIONS,
            f"Cadastrar fluxos exige a permissão {Permission.MANAGE_TON_REPORTS.value}",
        )


# ---------------------------------------------------------------------------
# Read model: NG inconsistencies
# ---------------------------------------------------------------------------

_RULE_NAMES = {definition.key: definition.name for definition in DEFAULT_CATALOG}


@dataclass(frozen=True)
class InconsistencySnapshot:
    items: list[FlowItem]
    last_review_at: datetime.datetime | None


def _payload(name: str) -> sa.ColumnElement[str]:
    return Finding.deterministic_payload.op("->>")(name)


def _weeks_open(first: datetime.datetime, now: datetime.datetime) -> int:
    return max(0, (now - first).days // 7)


def inconsistencies(
    session: Session,
    user: User,
    *,
    now: datetime.datetime,
    review_run_id: UUID | None = None,
) -> InconsistencySnapshot:
    """Every NG inconsistency still open in TON, with evidence and where it
    stands after the latest import. With ``review_run_id``, each item also
    carries ``mudou`` = the change that import caused (new, corrected,
    reappeared), if any."""
    latest_finding = (
        sa.select(
            Finding.id.label("finding_id"),
            Finding.occurrence_id,
            Finding.deterministic_payload,
        )
        .where(_payload("schema") == FINDING_SCHEMA)
        .order_by(Finding.occurrence_id, Finding.detected_at.desc(), Finding.id.desc())
        .distinct(Finding.occurrence_id)
        .subquery()
    )
    passed_before = (
        sa.select(sa.literal(1))
        .where(
            OccurrenceEvent.occurrence_id == Occurrence.id,
            OccurrenceEvent.transition == OccurrenceTransition.VERIFICATION_PASSED,
            OccurrenceEvent.occurred_at < Occurrence.last_detected_at,
        )
        .exists()
    )
    rows = session.execute(
        sa.select(
            Occurrence,
            latest_finding.c.finding_id,
            latest_finding.c.deterministic_payload,
            passed_before.label("passed_before"),
        )
        .join(latest_finding, latest_finding.c.occurrence_id == Occurrence.id)
        .where(
            Occurrence.status.in_(list(OPEN_STATUSES)),
            acl.occurrence_visible_clause(user),
        )
    ).all()
    last_review = session.execute(
        sa.select(ReviewRun.started_at, ReviewRun.finished_at)
        .where(ReviewRun.status == ReviewRunStatus.SUCCEEDED)
        .order_by(ReviewRun.started_at.desc())
        .limit(1)
    ).first()
    latest_review_at = last_review.started_at if last_review else None

    finding_ids = [row.finding_id for row in rows]
    records: dict[UUID, list[Any]] = defaultdict(list)
    if finding_ids:
        evidence = session.execute(
            sa.select(
                FindingEvidence.finding_id,
                FindingEvidence.locator,
                ParsedSourceRecord.administrative_unit,
                ParsedSourceRecord.account_code,
                ParsedSourceRecord.account_label,
                ParsedSourceRecord.document_number,
                ParsedSourceRecord.final_amount,
            )
            .outerjoin(
                ParsedSourceRecord,
                ParsedSourceRecord.id == FindingEvidence.parsed_record_id,
            )
            .where(FindingEvidence.finding_id.in_(finding_ids))
            .order_by(FindingEvidence.finding_id, FindingEvidence.created_at)
        ).all()
        for item in evidence:
            records[item.finding_id].append(item)

    changed: dict[UUID, ItemState] = {}
    if review_run_id is not None:
        corrected = session.scalars(
            sa.select(OccurrenceEvent.occurrence_id).where(
                OccurrenceEvent.transition == OccurrenceTransition.VERIFICATION_PASSED,
                OccurrenceEvent.context.op("->>")("review_run_id") == str(review_run_id),
            )
        ).all()
        changed.update({occurrence_id: ItemState.CORRECTED for occurrence_id in corrected})

    items: list[FlowItem] = []
    for row in rows:
        occurrence: Occurrence = row.Occurrence
        payload: dict[str, Any] = row.deterministic_payload or {}
        state = state_of(
            True,
            occurrence.first_detected_at,
            occurrence.last_detected_at,
            occurrence.verification_result.value
            if occurrence.verification_result
            else None,
            occurrence.verification_checked_at,
            bool(row.passed_before),
            latest_review_at,
        )
        assert state is not None
        if (
            review_run_id is not None
            and payload.get("review_run_id") == str(review_run_id)
            and state in (ItemState.NEW, ItemState.REAPPEARED)
        ):
            changed[occurrence.id] = state
        evidence_rows = records.get(row.finding_id, [])
        first = evidence_rows[0] if evidence_rows else None
        facts = payload.get("facts") or {}
        sheet = (first.locator or {}).get("sheet") if first else facts.get("sheet_name")
        line = (first.locator or {}).get("row") if first else facts.get("row_number")
        documents = sorted(
            {str(item.document_number) for item in evidence_rows if item.document_number}
        )
        if not documents and facts.get("document_number"):
            documents = [str(facts["document_number"])]
        if facts.get("kept_document_number"):
            documents.append(f"mantido {facts['kept_document_number']}")
        impact = (payload.get("impact") or {}).get("amount")
        amount = (
            Decimal(impact)
            if impact is not None
            else (first.final_amount if first and first.final_amount is not None else None)
        )
        rule_key = str(payload.get("rule_key") or "")
        where = " · ".join(
            part
            for part in (
                f"{sheet}, linha {line}" if sheet and line else (sheet or ""),
                f"doc. {', '.join(documents)}" if documents else "",
            )
            if part
        )
        account = (
            f"{first.account_code} {first.account_label or ''}".strip()
            if first and first.account_code
            else ""
        )
        items.append(
            FlowItem(
                key=str(occurrence.id),
                fields={
                    "regra": rule_key,
                    "unidade": (first.administrative_unit if first else None)
                    or "Sem unidade",
                    "valor": float(amount) if amount is not None else 0.0,
                    "semanas_em_aberto": _weeks_open(occurrence.first_detected_at, now),
                    "competencia": payload.get("sheet_month"),
                    "situacao": state.value,
                    "mudou": changed.get(occurrence.id).value
                    if occurrence.id in changed
                    else None,
                },
                columns={
                    "codigo": occurrence.short_code or "",
                    "regra_nome": _RULE_NAMES.get(rule_key, occurrence.title or rule_key),
                    "evidencia": where,
                    "conta": account,
                    "valor": format_money(amount),
                    "correcao": NG_CORRECTIONS.get(rule_key, DEFAULT_NG_CORRECTION),
                    "situacao": ITEM_STATE_LABELS[state],
                },
            )
        )
    items.sort(key=lambda item: item.key)
    return InconsistencySnapshot(items, last_review.finished_at if last_review else None)


# ---------------------------------------------------------------------------
# Event outbox
# ---------------------------------------------------------------------------


def emit_flow_event__no_commit(
    session: Session, *, kind: str, event_key: str, payload: dict[str, Any]
) -> None:
    """Record a domain event in the caller's transaction. Re-emitting the
    same (kind, key) is a no-op, so a retried source never doubles flows."""
    session.execute(
        insert(EmailFlowEvent)
        .values(kind=kind, event_key=event_key, payload=payload)
        .on_conflict_do_nothing(constraint="uq_ton_email_flow_event_key")
    )


DRE_EVENT_KIND = EVENT_KIND_DRE
# A year recalculation runs the DRE once per month and unit; wait this long
# after the last one before the grouped event is handed to flows.
DRE_QUIET_PERIOD = datetime.timedelta(minutes=3)


def record_dre_recalculated__no_commit(
    session: Session,
    *,
    normalization_run_id: UUID,
    period: datetime.date,
    unit_id: UUID | None,
    now: datetime.datetime,
) -> None:
    """One pending event per normalization base: every READY calculation of
    that base folds its month and unit into it, so recalculating the whole
    year e-mails once, not once per month and unit."""
    pending = session.scalar(
        sa.select(EmailFlowEvent)
        .where(
            EmailFlowEvent.kind == DRE_EVENT_KIND,
            EmailFlowEvent.processed_at.is_(None),
            EmailFlowEvent.payload.op("->>")("normalization_run_id")
            == str(normalization_run_id),
        )
        .with_for_update()
    )
    month = period.isoformat()
    unit = str(unit_id) if unit_id else "consolidado"
    if pending is not None:
        payload = dict(pending.payload)
        payload["competencias"] = sorted({*payload.get("competencias", []), month})
        payload["unidades"] = sorted({*payload.get("unidades", []), unit})
        payload["last_at"] = now.isoformat()
        pending.payload = payload
        return
    session.add(
        EmailFlowEvent(
            kind=DRE_EVENT_KIND,
            event_key=f"{normalization_run_id}:{now.isoformat()}",
            payload={
                "normalization_run_id": str(normalization_run_id),
                "competencias": [month],
                "unidades": [unit],
                "last_at": now.isoformat(),
            },
        )
    )


def claim_pending_events(
    session: Session, now: datetime.datetime, limit: int = 20
) -> list[EmailFlowEvent]:
    rows = session.scalars(
        sa.select(EmailFlowEvent)
        .where(EmailFlowEvent.processed_at.is_(None))
        .order_by(EmailFlowEvent.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    return [
        row
        for row in rows
        if row.kind != DRE_EVENT_KIND
        or now - datetime.datetime.fromisoformat(str(row.payload.get("last_at")))
        >= DRE_QUIET_PERIOD
    ]


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------


def get_flow(session: Session, flow_id: UUID) -> EmailFlow:
    flow = session.get(EmailFlow, flow_id)
    if flow is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Fluxo não encontrado")
    return flow


def current_version(session: Session, flow: EmailFlow) -> EmailFlowVersion:
    version = session.scalar(
        sa.select(EmailFlowVersion).where(
            EmailFlowVersion.flow_id == flow.id,
            EmailFlowVersion.version == flow.current_version,
        )
    )
    assert version is not None
    return version


def list_flows(session: Session) -> list[tuple[EmailFlow, EmailFlowVersion]]:
    rows = session.execute(
        sa.select(EmailFlow, EmailFlowVersion)
        .join(
            EmailFlowVersion,
            sa.and_(
                EmailFlowVersion.flow_id == EmailFlow.id,
                EmailFlowVersion.version == EmailFlow.current_version,
            ),
        )
        .where(EmailFlow.status != FlowStatus.DISCARDED.value)
        .order_by(EmailFlow.created_at)
    ).all()
    return [(row[0], row[1]) for row in rows]


def active_flows(
    session: Session, trigger_kind: str
) -> list[tuple[EmailFlow, EmailFlowVersion]]:
    return [
        (flow, version)
        for flow, version in list_flows(session)
        if flow.status == FlowStatus.ACTIVE.value and version.trigger_kind == trigger_kind
    ]


def _audit(
    session: Session,
    user: User | None,
    action: AuditAction,
    flow: EmailFlow,
    extra: dict[str, Any],
) -> None:
    emit_ton_audit_event(
        session,
        action=action,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id if user else None,
        resource_kind=TonAuditResourceKind.EMAIL_FLOW,
        resource_id=flow.id,
        extra={"flow_name": flow.name, **extra},
    )


def create_flow__no_commit(
    session: Session,
    user: User | None,
    *,
    name: str,
    definition: FlowDefinition,
    origin: FlowOrigin,
    status: FlowStatus,
    now: datetime.datetime,
    suggestion_reason: str | None = None,
    suggestion_model: str | None = None,
    seed_key: str | None = None,
) -> EmailFlow:
    active = status is FlowStatus.ACTIVE
    flow = EmailFlow(
        name=name,
        origin=origin.value,
        status=status.value,
        current_version=1,
        seed_key=seed_key,
        suggestion_reason=suggestion_reason,
        suggestion_model=suggestion_model,
        owner_id=user.id if user and active else None,
        active_since=now if active else None,
        created_by=user.id if user else None,
        approved_by=user.id if user and active else None,
        approved_at=now if active else None,
        updated_at=now,
    )
    session.add(flow)
    session.flush()
    session.add(
        EmailFlowVersion(
            flow_id=flow.id,
            version=1,
            name=name,
            trigger_kind=definition.trigger.kind.value,
            definition=definition.model_dump(mode="json"),
            created_by=user.id if user else None,
        )
    )
    _audit(
        session,
        user,
        AuditAction.TON_EMAIL_FLOW_CHANGE,
        flow,
        {"change": "created", "origin": origin.value, "status": status.value},
    )
    return flow


def add_version__no_commit(
    session: Session,
    user: User,
    flow: EmailFlow,
    *,
    name: str,
    definition: FlowDefinition,
    now: datetime.datetime,
) -> EmailFlowVersion:
    if flow.status == FlowStatus.DISCARDED.value:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Fluxo descartado não pode ser editado")
    flow.current_version += 1
    flow.name = name
    flow.updated_at = now
    version = EmailFlowVersion(
        flow_id=flow.id,
        version=flow.current_version,
        name=name,
        trigger_kind=definition.trigger.kind.value,
        definition=definition.model_dump(mode="json"),
        created_by=user.id,
    )
    session.add(version)
    _audit(
        session,
        user,
        AuditAction.TON_EMAIL_FLOW_CHANGE,
        flow,
        {"change": "new_version", "version": flow.current_version},
    )
    return version


def set_status__no_commit(
    session: Session,
    user: User,
    flow: EmailFlow,
    status: FlowStatus,
    now: datetime.datetime,
) -> None:
    previous = FlowStatus(flow.status)
    allowed = {
        FlowStatus.SUGGESTED: {FlowStatus.ACTIVE, FlowStatus.DISCARDED},
        FlowStatus.ACTIVE: {FlowStatus.PAUSED},
        FlowStatus.PAUSED: {FlowStatus.ACTIVE, FlowStatus.DISCARDED},
        FlowStatus.DISCARDED: set(),
    }
    if status not in allowed[previous]:
        raise OnyxError(
            OnyxErrorCode.CONFLICT,
            f"Não é possível passar de {previous.value} para {status.value}",
        )
    flow.status = status.value
    flow.updated_at = now
    if status is FlowStatus.ACTIVE:
        # The person who turns it on answers for it and lends their visibility.
        flow.owner_id = user.id
        flow.active_since = now
        if previous is FlowStatus.SUGGESTED:
            flow.approved_by = user.id
            flow.approved_at = now
    if status is FlowStatus.DISCARDED:
        flow.discarded_by = user.id
        flow.discarded_at = now
    _audit(
        session,
        user,
        AuditAction.TON_EMAIL_FLOW_CHANGE,
        flow,
        {"change": "status", "from": previous.value, "to": status.value},
    )


def seeded_flow(session: Session, seed_key: str) -> EmailFlow | None:
    return session.scalar(sa.select(EmailFlow).where(EmailFlow.seed_key == seed_key))


# ---------------------------------------------------------------------------
# Runs and deliveries
# ---------------------------------------------------------------------------


def start_run__no_commit(
    session: Session,
    *,
    flow: EmailFlow,
    version: EmailFlowVersion,
    event_key: str,
    is_test: bool,
    triggered_by: UUID | None,
    now: datetime.datetime,
) -> EmailFlowRun | None:
    """Claim the (flow, event) pair. ``None`` when it already ran."""
    values = dict(
        flow_id=flow.id,
        version_id=version.id,
        event_key=event_key,
        is_test=is_test,
        status="RUNNING",
        item_count=0,
        context={},
        triggered_by=triggered_by,
        started_at=now,
    )
    if is_test:
        run = EmailFlowRun(**values)
        session.add(run)
        session.flush()
        return run
    run_id = session.scalar(
        insert(EmailFlowRun)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=["flow_id", "event_key"],
            index_where=sa.text("NOT is_test"),
        )
        .returning(EmailFlowRun.id)
    )
    return session.get(EmailFlowRun, run_id) if run_id else None


def add_delivery__no_commit(session: Session, delivery: EmailFlowDelivery) -> None:
    session.add(delivery)


def runs_for_flows(
    session: Session, flow_ids: Sequence[UUID], per_flow: int
) -> dict[UUID, list[tuple[EmailFlowRun, int, list[EmailFlowDelivery]]]]:
    if not flow_ids:
        return {}
    ranked = (
        sa.select(
            EmailFlowRun.id,
            sa.func.row_number()
            .over(
                partition_by=EmailFlowRun.flow_id,
                order_by=EmailFlowRun.started_at.desc(),
            )
            .label("position"),
        )
        .where(EmailFlowRun.flow_id.in_(flow_ids))
        .subquery()
    )
    rows = session.execute(
        sa.select(EmailFlowRun, EmailFlowVersion.version)
        .join(ranked, ranked.c.id == EmailFlowRun.id)
        .join(EmailFlowVersion, EmailFlowVersion.id == EmailFlowRun.version_id)
        .where(ranked.c.position <= per_flow)
        .order_by(EmailFlowRun.started_at.desc())
    ).all()
    run_ids = [row[0].id for row in rows]
    deliveries: dict[UUID, list[EmailFlowDelivery]] = defaultdict(list)
    if run_ids:
        for delivery in session.scalars(
            sa.select(EmailFlowDelivery)
            .where(EmailFlowDelivery.run_id.in_(run_ids))
            .order_by(EmailFlowDelivery.batch_no)
        ):
            deliveries[delivery.run_id].append(delivery)
    result: dict[UUID, list[tuple[EmailFlowRun, int, list[EmailFlowDelivery]]]] = (
        defaultdict(list)
    )
    for run, version in rows:
        result[run.flow_id].append((run, version, deliveries.get(run.id, [])))
    return result


def get_delivery(session: Session, delivery_id: UUID) -> EmailFlowDelivery:
    delivery = session.get(EmailFlowDelivery, delivery_id)
    if delivery is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Envio não encontrado")
    return delivery


def user_emails(session: Session, user_ids: Sequence[UUID | None]) -> dict[UUID, str]:
    ids = [item for item in user_ids if item is not None]
    if not ids:
        return {}
    return dict(session.execute(sa.select(User.id, User.email).where(User.id.in_(ids))).all())


def get_user(session: Session, user_id: UUID | None) -> User | None:
    return session.get(User, user_id) if user_id else None


def latest_succeeded_review(session: Session) -> ReviewRun | None:
    return session.scalar(
        sa.select(ReviewRun)
        .where(ReviewRun.status == ReviewRunStatus.SUCCEEDED)
        .order_by(ReviewRun.started_at.desc())
        .limit(1)
    )
