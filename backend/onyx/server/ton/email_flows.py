"""Email flows: trigger → steps (conditions, e-mails, per unit, waits,
approvals). Read with the TON report read permission; registering, editing,
drafting and approving need the report management permission (approvers
named in a flow may decide their own approvals)."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.email_flows import service
from onyx.ton.email_flows.api import (
    ApprovalView,
    AssetView,
    CatalogView,
    DecisionRequest,
    DraftResult,
    FlowCreate,
    FlowDetail,
    FlowTable,
    FlowUpdate,
    LayoutView,
    PreviewRequest,
    PreviewView,
    RunView,
    TestRequest,
)
from onyx.ton.email_flows.models import FlowStatus

_read = require_permission(Permission.READ_TON_REPORTS)
_manage = require_permission(Permission.MANAGE_TON_REPORTS)

router = APIRouter(prefix="/ton/email-flows", tags=["TON Email Flows"])

MAX_UPLOAD_BYTES = 1_048_576


class DraftRequest(BaseModel):
    request: str = Field(min_length=5, max_length=4000)
    flow_id: UUID | None = None


@router.get("")
def list_flows(
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> FlowTable:
    return service.flow_table(session, user)


@router.get("/catalog")
def get_catalog(
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> CatalogView:
    return service.catalog_view(session)


@router.post("")
def create_flow(
    request: FlowCreate,
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> FlowDetail:
    return service.create(session, user, request)


@router.post("/preview")
def preview_flow(
    request: PreviewRequest,
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> PreviewView:
    return service.preview(
        session,
        user,
        flow_id=request.flow_id,
        definition=request.definition,
        step_id=request.step_id,
        flow_name=request.flow_name,
    )


@router.post("/drafts")
def draft_flow(
    request: DraftRequest,
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> DraftResult:
    return service.draft_flow(session, user, request.request, request.flow_id)


@router.get("/layout")
def get_layout(
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> LayoutView:
    return service.layout_view(session)


@router.put("/layout")
def put_layout(
    request: LayoutView,
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> LayoutView:
    return service.save_layout(session, user, request)


@router.post("/assets")
async def upload_asset(
    file: UploadFile = File(...),
    name: str = Form(""),
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> AssetView:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "A imagem deve ter até 1 MB")
    return service.upload_asset(
        session, user, name or file.filename or "imagem", file.content_type or "", data
    )


@router.get("/assets/{asset_id}")
def get_asset(
    asset_id: UUID,
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> Response:
    data, content_type = service.asset_bytes(session, user, asset_id)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.post("/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: UUID,
    request: DecisionRequest,
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> ApprovalView:
    return service.decide(session, user, approval_id, request.approve, request.note)


@router.get("/deliveries/{delivery_id}/html")
def delivery_html(
    delivery_id: UUID,
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    return HTMLResponse(service.delivery_html(session, user, delivery_id))


@router.get("/{flow_id}")
def get_flow(
    flow_id: UUID,
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> FlowDetail:
    return service.flow_detail(session, user, flow_id)


@router.put("/{flow_id}")
def update_flow(
    flow_id: UUID,
    request: FlowUpdate,
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> FlowDetail:
    return service.update(session, user, flow_id, request)


@router.post("/{flow_id}/activate")
def activate_flow(
    flow_id: UUID,
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> FlowDetail:
    """Also how a TON draft is registered ("Ativar")."""
    return service.change_status(session, user, flow_id, FlowStatus.ACTIVE)


@router.post("/{flow_id}/pause")
def pause_flow(
    flow_id: UUID,
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> FlowDetail:
    return service.change_status(session, user, flow_id, FlowStatus.PAUSED)


@router.post("/{flow_id}/discard")
def discard_flow(
    flow_id: UUID,
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> FlowDetail:
    return service.change_status(session, user, flow_id, FlowStatus.DISCARDED)


@router.post("/{flow_id}/test")
def send_test(
    flow_id: UUID,
    request: TestRequest,
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> RunView:
    return service.send_test(session, user, flow_id, request.step_id)
