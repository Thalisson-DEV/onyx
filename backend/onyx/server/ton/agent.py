from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton.agent import configured_agent_id, provision_agent
from onyx.db.ton.closing import (
    execute_closing,
    inspect_closing,
    list_publications,
    read_publication,
)
from onyx.db.ton.enums import AnalysisTrigger
from onyx.ton.agent.closing_models import (
    ClosingOutput,
    ClosingRequest,
    PublishedClosing,
    SpecialistDefinition,
)
from onyx.ton.agent.registry import ROUTINES, SPECIALISTS
from onyx.ton.agent.rendering import render_markdown

router = APIRouter(prefix="/ton/agent", tags=["TON Agent"])


class AgentConfiguration(BaseModel):
    persona_id: int | None


class RoutineView(BaseModel):
    key: str
    name: str
    status: str
    reason: str
    schedule: str = "Agendamento não configurado"
    next_run: str | None = None
    manual_available: bool


@router.get("/configuration")
def agent_configuration(
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> AgentConfiguration:
    return AgentConfiguration(persona_id=configured_agent_id(session, user))


@router.get("/routines")
def routine_definitions(
    _user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
) -> list[RoutineView]:
    return [
        RoutineView(
            key=key,
            name=name,
            status="Execução manual disponível" if key == "R3" else "Bloqueada",
            reason=reason if key == "R3" else "Capacidade pendente: " + reason + ".",
            manual_available=key == "R3",
        )
        for key, name, reason in ROUTINES
    ]


class AgentView(BaseModel):
    persona_id: int
    name: str


@router.post("/provision")
def configure_agent(
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> AgentView:
    persona = provision_agent(session, user)
    return AgentView(persona_id=persona.id, name=persona.name)


@router.get("/closing")
def closing_snapshot(
    unit_id: UUID | None = None,
    period: date | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ClosingOutput:
    return inspect_closing(
        session,
        user,
        ClosingRequest(request_id=uuid4(), unit_id=unit_id, period=period),
    )


@router.get("/specialists")
def specialists(
    _user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
) -> list[SpecialistDefinition]:
    return list(SPECIALISTS)


@router.post("/routines/R3/run")
def run_closing(
    request: ClosingRequest,
    user: User = Depends(require_permission(Permission.MANAGE_TON_REPORTS)),
    session: Session = Depends(get_session),
) -> PublishedClosing:
    return execute_closing(
        session, user, request, trigger=AnalysisTrigger.MANUAL_REPLAY, routine_code="R3"
    )


@router.get("/reports")
def report_list(
    limit: int = Query(default=10, ge=1, le=25),
    user: User = Depends(require_permission(Permission.READ_TON_REPORTS)),
    session: Session = Depends(get_session),
) -> list[PublishedClosing]:
    return list_publications(session, user, limit)


@router.get("/reports/{revision_id}")
def report_detail(
    revision_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_REPORTS)),
    session: Session = Depends(get_session),
) -> PublishedClosing:
    return read_publication(session, user, revision_id)


@router.get("/reports/{revision_id}/download")
def report_download(
    revision_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_REPORTS)),
    session: Session = Depends(get_session),
) -> Response:
    publication = read_publication(session, user, revision_id)
    return Response(
        content=render_markdown(publication),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="ton-fechamento-{publication.output.period:%Y-%m}-{revision_id}.md"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
