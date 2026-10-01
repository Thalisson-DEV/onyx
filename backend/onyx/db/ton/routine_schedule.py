"""Tenant-local R3 configuration and retry-safe scheduled publication."""

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import KVStore, User
from onyx.db.ton import acl
from onyx.db.ton.closing import execute_closing, read_publication
from onyx.db.ton.enums import AnalysisTrigger
from onyx.db.ton.models import BusinessUnit
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.closing_models import ClosingRequest
from onyx.ton.agent.scheduling import (
    R3ScheduleRequest,
    R3ScheduleState,
    R3ScheduleView,
    closing_period,
    next_business_run,
)
from onyx.utils.audit import AuditAction, AuditActor, AuditOutcome, emit_audit_event

SCHEDULE_KEY = "ton:routines:R3:schedule:v1"
LOCK_KEY = 789446103135


def _locked_row(session: Session) -> KVStore | None:
    session.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
    session.execute(sa.text("SET LOCAL statement_timeout = '45s'"))
    session.execute(sa.text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOCK_KEY})
    return session.scalar(
        sa.select(KVStore)
        .where(KVStore.key == SCHEDULE_KEY)
        .execution_options(populate_existing=True)
    )


def _save(session: Session, state: R3ScheduleState) -> None:
    row = session.get(KVStore, SCHEDULE_KEY)
    if row is None:
        row = KVStore(key=SCHEDULE_KEY)
        session.add(row)
    row.value = state.model_dump(mode="json")
    session.commit()


def schedule_view(session: Session, user: User) -> R3ScheduleView:
    acl.assert_global(user, permission=Permission.READ_TON_SOURCES)
    row = session.get(KVStore, SCHEDULE_KEY)
    if row is None:
        return R3ScheduleView()
    state = R3ScheduleState.model_validate(row.value)
    report_url = None
    if state.last_revision_id:
        try:
            report_url = read_publication(
                session, user, state.last_revision_id
            ).report_url
        except OnyxError:
            pass
    return R3ScheduleView(
        enabled=state.enabled,
        schedule=f"Primeiro dia útil do mês, às 08:00 de Brasília. Calendário: {state.calendar_name or 'não confirmado'}.",
        next_run_at=state.next_run_at if state.enabled else None,
        last_run_at=state.last_run_at if report_url else None,
        last_report_url=report_url,
        last_result=state.last_result if report_url else None,
        reason=state.failure_reason
        or (
            "Publicação interna. Considera o mês anterior. Exclui fins de semana e os feriados confirmados."
            if state.enabled
            else "Agendamento desativado."
        ),
    )


def configure_schedule(
    session: Session,
    user: User,
    request: R3ScheduleRequest,
    *,
    now: datetime | None = None,
) -> R3ScheduleView:
    acl.assert_global(user, permission=Permission.FULL_ADMIN_PANEL_ACCESS)
    acl.assert_global(user, permission=Permission.READ_TON_SOURCES)
    acl.assert_global(user, permission=Permission.READ_TON_OCCURRENCES)
    acl.assert_global(user, permission=Permission.READ_TON_REPORTS)
    acl.assert_global(user, permission=Permission.MANAGE_TON_REPORTS)
    if not user.is_active:
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS)
    # Scope validation uses the same closing ACL before storing a schedule.
    if request.unit_id is not None:
        if (
            session.scalar(
                sa.select(BusinessUnit.id).where(
                    BusinessUnit.id == request.unit_id,
                    acl.business_unit_visible_clause(user),
                )
            )
            is None
        ):
            raise OnyxError(OnyxErrorCode.NOT_FOUND, "Unidade indisponível.")
    try:
        next_run = (
            next_business_run(now or datetime.now(timezone.utc), request)
            if request.enabled
            else None
        )
    except ValueError as exc:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, str(exc)) from exc
    old_row = _locked_row(session)
    old = R3ScheduleState.model_validate(old_row.value) if old_row else None
    state = R3ScheduleState(
        **request.model_dump(),
        revision=uuid4(),
        actor_id=user.id,
        next_run_at=next_run,
        last_run_at=old.last_run_at if old else None,
        last_revision_id=old.last_revision_id if old else None,
        last_result=old.last_result if old else None,
    )
    _save(session, state)
    emit_audit_event(
        AuditAction.TON_ROUTINE_SCHEDULE_UPDATE,
        AuditOutcome.SUCCESS,
        actor=AuditActor(user_id=str(user.id)),
        resource_type="ton_routine_schedule",
        resource_id=str(state.revision),
        extra={
            "routine_code": "R3",
            "enabled": state.enabled,
            "next_run_at": state.next_run_at.isoformat() if state.next_run_at else None,
            "calendar_valid_through": str(state.calendar_valid_through),
        },
    )
    return schedule_view(session, user)


def dispatch_due_r3(session: Session, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    row = _locked_row(session)
    if row is None:
        session.rollback()
        return False
    state = R3ScheduleState.model_validate(row.value)
    due = state.next_run_at
    if not state.enabled or due is None or due > current:
        session.rollback()
        return False
    actor = session.get(User, state.actor_id, populate_existing=True)
    try:
        if actor is None or not actor.is_active or not acl.is_ton_administrator(actor):
            raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS)
        # The identity stays stable if publication committed before the cursor update.
        publication = execute_closing(
            session,
            actor,
            ClosingRequest(
                request_id=uuid5(
                    NAMESPACE_URL, f"ton:R3:{state.revision}:{due.isoformat()}"
                ),
                period=closing_period(due),
                unit_id=state.unit_id,
            ),
            trigger=AnalysisTrigger.SCHEDULED,
            routine_code="R3",
        )
    except OnyxError:
        session.rollback()
        row = _locked_row(session)
        if row and R3ScheduleState.model_validate(row.value).revision == state.revision:
            state.enabled = False
            state.failure_reason = (
                "Execução suspensa. Verifique as permissões e o escopo do responsável."
            )
            _save(session, state)
        return False
    # execute_closing commits. Reacquire the lock and preserve concurrent edits.
    row = _locked_row(session)
    if row is None:
        session.rollback()
        return True
    latest = R3ScheduleState.model_validate(row.value)
    if latest.revision != state.revision or latest.next_run_at != due:
        session.rollback()
        return True
    state.last_run_at = current
    state.last_revision_id = publication.revision_id
    state.last_result = publication.status
    try:
        # Skip missed cycles. Never create an unbounded catch-up queue.
        state.next_run_at = next_business_run(max(current, due), state)
    except ValueError:
        state.enabled = False
        state.next_run_at = None
        state.failure_reason = (
            "Calendário vencido. Confirme os feriados da próxima execução."
        )
    _save(session, state)
    return True
