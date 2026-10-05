"""Email flows: trigger -> condition -> yes/no e-mail action. Read with the
TON report read permission; registering, editing and approving suggestions
need the report management permission."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.ton.email_flows import service
from onyx.ton.email_flows.models import (
    CatalogView,
    FlowBranch,
    FlowCreate,
    FlowDefinition,
    FlowDetail,
    FlowStatus,
    FlowTable,
    FlowUpdate,
    PreviewView,
    RunView,
    SuggestionRunResult,
)

_read = require_permission(Permission.READ_TON_REPORTS)
_manage = require_permission(Permission.MANAGE_TON_REPORTS)

router = APIRouter(prefix="/ton/email-flows", tags=["TON Email Flows"])


class PreviewRequest(BaseModel):
    flow_id: UUID | None = None
    definition: FlowDefinition | None = None
    branch: FlowBranch | None = None


class TestRequest(BaseModel):
    branch: FlowBranch | None = None


@router.get("")
def list_flows(
    user: User = Depends(_read),
    session: Session = Depends(get_session),
) -> FlowTable:
    return service.flow_table(session, user)


@router.get("/catalog")
def get_catalog(user: User = Depends(_read)) -> CatalogView:
    return service.catalog_view()


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
        branch=request.branch,
    )


@router.post("/suggestions")
def request_suggestions(
    user: User = Depends(_manage),
    session: Session = Depends(get_session),
) -> SuggestionRunResult:
    return service.request_suggestions(session, user)


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
    """Also how a TON suggestion is registered ("Cadastrar")."""
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
    return service.send_test(session, user, flow_id, request.branch)
