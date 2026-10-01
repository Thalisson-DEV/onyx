"""R3 uses the existing tenant-aware Celery Beat and primary worker."""

from celery import shared_task

from onyx.configs.constants import OnyxCeleryTask
from onyx.db.engine.sql_engine import get_session_with_tenant
from onyx.db.ton.routine_schedule import dispatch_due_r3


@shared_task(name=OnyxCeleryTask.TON_R3_DISPATCH_DUE, ignore_result=True)
def dispatch_ton_r3(*, tenant_id: str) -> bool:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    with get_session_with_tenant(tenant_id=tenant_id) as session:
        return dispatch_due_r3(session)
