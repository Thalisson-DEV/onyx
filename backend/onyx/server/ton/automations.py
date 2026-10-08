"""Automations: trigger → steps, built in the canvas and run by the durable
engine. Reading needs the TON report read permission; building, running
and drafting need the report management permission (approvers named in a
step may answer their own approvals)."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.automations import drafter, service
from onyx.ton.automations.api import (
    ApprovalView,
    AutomationCreate,
    AutomationDetail,
    AutomationTable,
    AutomationUpdate,
    CatalogView,
    DecisionRequest,
    DraftRequest,
    DraftResult,
    FileView,
    NoticeView,
    PreviewRequest,
    PreviewResult,
    RunDetail,
    RunRequest,
    RunSummary,
    StatusRequest,
    ValidateRequest,
    ValidateResult,
)

_read = require_permission(Permission.READ_TON_REPORTS)
_manage = require_permission(Permission.MANAGE_TON_REPORTS)

router = APIRouter(prefix="/ton/automations", tags=["TON Automations"])


@router.get("")
def list_automations(user: User = Depends(_read), session: Session = Depends(get_session)) -> AutomationTable:
    return service.table(session, user)


@router.get("/catalog")
def get_catalog(user: User = Depends(_read), session: Session = Depends(get_session)) -> CatalogView:
    return service.catalog_view(session, user)


@router.post("")
def create_automation(
    request: AutomationCreate, user: User = Depends(_manage), session: Session = Depends(get_session)
) -> AutomationDetail:
    return service.create(session, user, request)


@router.post("/validate")
def validate_definition(
    request: ValidateRequest, user: User = Depends(_read), session: Session = Depends(get_session)
) -> ValidateResult:
    return service.check(session, user, request.definition, request.kind)


@router.post("/preview")
def preview_step(
    request: PreviewRequest, user: User = Depends(_read), session: Session = Depends(get_session)
) -> PreviewResult:
    return service.preview(session, user, request)


@router.post("/drafts")
def draft_automation(
    request: DraftRequest, user: User = Depends(_manage), session: Session = Depends(get_session)
) -> DraftResult:
    return drafter.draft_automation(session, user, request.request, request.automation_id, request.definition)


@router.post("/files")
async def upload_file(
    file: UploadFile = File(...), user: User = Depends(_manage), session: Session = Depends(get_session)
) -> FileView:
    data = await file.read(service.MAX_FILE_BYTES + 1)
    if len(data) > service.MAX_FILE_BYTES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Arquivo maior que 5 MB")
    return service.upload_file(session, user, file.filename or "arquivo", file.content_type or "", data)


@router.get("/notices")
def list_notices(user: User = Depends(_read), session: Session = Depends(get_session)) -> list[NoticeView]:
    return service.notices(session, user)


@router.get("/approvals")
def list_approvals(user: User = Depends(_read), session: Session = Depends(get_session)) -> list[ApprovalView]:
    return service.approvals_for(session, user)


@router.post("/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: UUID, request: DecisionRequest, user: User = Depends(_read), session: Session = Depends(get_session)
) -> ApprovalView:
    return service.decide(session, user, approval_id, request.outcome, request.comment)


@router.get("/runs/{run_id}")
def get_run(run_id: UUID, user: User = Depends(_read), session: Session = Depends(get_session)) -> RunDetail:
    return service.run_detail(session, user, run_id)


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: UUID, user: User = Depends(_manage), session: Session = Depends(get_session)) -> RunSummary:
    return service.cancel(session, user, run_id)


@router.post("/runs/{run_id}/resubmit")
def resubmit_run(run_id: UUID, user: User = Depends(_manage), session: Session = Depends(get_session)) -> RunSummary:
    return service.resubmit(session, user, run_id)


@router.get("/runs/{run_id}/steps/{node_id}/email")
def step_email(
    run_id: UUID, node_id: str, iteration: str = "", user: User = Depends(_read), session: Session = Depends(get_session)
) -> HTMLResponse:
    return HTMLResponse(service.step_html(session, user, run_id, node_id, iteration))


@router.get("/{automation_id}")
def get_automation(automation_id: UUID, user: User = Depends(_read), session: Session = Depends(get_session)) -> AutomationDetail:
    return service.detail(session, user, automation_id)


@router.put("/{automation_id}")
def update_automation(
    automation_id: UUID, request: AutomationUpdate, user: User = Depends(_manage), session: Session = Depends(get_session)
) -> AutomationDetail:
    return service.update(session, user, automation_id, request)


@router.post("/{automation_id}/status")
def change_status(
    automation_id: UUID, request: StatusRequest, user: User = Depends(_manage), session: Session = Depends(get_session)
) -> AutomationDetail:
    return service.change_status(session, user, automation_id, request.status)


@router.post("/{automation_id}/run")
def run_now(
    automation_id: UUID, request: RunRequest, user: User = Depends(_manage), session: Session = Depends(get_session)
) -> RunSummary:
    return service.start_manual(session, user, automation_id, request.inputs, test=False)


@router.post("/{automation_id}/test")
def test_run(
    automation_id: UUID, request: RunRequest, user: User = Depends(_manage), session: Session = Depends(get_session)
) -> RunSummary:
    return service.start_manual(session, user, automation_id, request.inputs, test=True)


@router.post("/{automation_id}/duplicate")
def duplicate(automation_id: UUID, user: User = Depends(_manage), session: Session = Depends(get_session)) -> AutomationDetail:
    return service.duplicate(session, user, automation_id)


@router.post("/{automation_id}/versions/{version}/restore")
def restore_version(
    automation_id: UUID, version: int, user: User = Depends(_manage), session: Session = Depends(get_session)
) -> AutomationDetail:
    return service.restore_version(session, user, automation_id, version)
