"""R3 and automations use the existing tenant-aware Celery Beat and primary worker."""

from uuid import UUID

from celery import shared_task

from onyx.configs.constants import OnyxCeleryTask
from onyx.db.engine.sql_engine import get_session_with_tenant
from onyx.db.ton.routine_schedule import dispatch_due_r3
from onyx.ton.automations import service as automations


@shared_task(name=OnyxCeleryTask.TON_R3_DISPATCH_DUE, ignore_result=True)
def dispatch_ton_r3(*, tenant_id: str) -> bool:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    with get_session_with_tenant(tenant_id=tenant_id) as session:
        return dispatch_due_r3(session)


@shared_task(name=OnyxCeleryTask.TON_AUTOMATIONS_TICK, ignore_result=True)
def ton_automations_tick(*, tenant_id: str) -> int:
    """Consume the event outbox, fire due schedules, end runs past their
    limit and queue every runnable run (due waits, orphaned leases)."""
    if not tenant_id:
        raise ValueError("tenant_id is required")
    with get_session_with_tenant(tenant_id=tenant_id) as session:
        return automations.tick(session, tenant_id=tenant_id)


@shared_task(name=OnyxCeleryTask.TON_EMAIL_FLOWS_TICK, ignore_result=True)
def ton_email_flows_tick(*, tenant_id: str) -> int:
    """Kept for messages queued before the switch: e-mail flows now run as
    automations."""
    return ton_automations_tick(tenant_id=tenant_id)


@shared_task(name=OnyxCeleryTask.TON_AUTOMATION_EXECUTE_RUN, ignore_result=True, acks_late=True)
def ton_automation_execute_run(*, run_id: str, tenant_id: str) -> str | None:
    """Execute (or continue) one run. Safe to receive twice: the run lease
    lets one worker in; the step checkpoints make it resumable."""
    if not tenant_id:
        raise ValueError("tenant_id is required")
    with get_session_with_tenant(tenant_id=tenant_id) as session:
        status = automations.execute_run(session, UUID(run_id), tenant_id=tenant_id)
    return status.value if status else None
