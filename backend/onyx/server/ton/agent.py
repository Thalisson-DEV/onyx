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
from onyx.db.ton import agent_actions
from onyx.db.ton.agent_ledger import r1_automation
from onyx.db.ton.agent import (
    configured_agent_id,
    provision_agent,
    specialist_agent_id,
)
from onyx.db.ton.agent_occurrences import query_occurrences
from onyx.db.ton.chat_artifacts import ChatArtifactView, list_chat_artifacts
from onyx.db.ton.occurrence_ledger import (
    LedgerDetail,
    LedgerFilter,
    LedgerPage,
    ledger_detail,
    ledger_page,
)
from onyx.db.ton.capabilities import capability_registry
from onyx.db.ton.closing import (
    execute_closing,
    inspect_closing,
    latest_r3_publication,
    list_publications,
    list_report_groups,
    read_publication,
    report_group_history,
    specialist_views,
)
from onyx.db.ton.enums import AnalysisTrigger
from onyx.db.ton.routine_schedule import configure_schedule, schedule_view
from onyx.ton.agent.action_models import AgentActionView
from onyx.ton.agent.capabilities import CapabilityView
from onyx.ton.agent.closing_models import (
    ClosingOutput,
    ClosingRequest,
    PublishedClosing,
    ReportGroup,
    SpecialistView,
)
from onyx.ton.agent.models import OccurrencePage, ToolQuery
from onyx.ton.agent.registry import ROUTINES
from onyx.ton.agent.rendering import render_markdown
from onyx.ton.agent.scheduling import R3ScheduleRequest, R3ScheduleView

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
    last_run: str | None = None
    last_result: str | None = None
    last_report_url: str | None = None
    manual_available: bool


@router.get("/configuration")
def agent_configuration(
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> AgentConfiguration:
    return AgentConfiguration(persona_id=configured_agent_id(session, user))


@router.get("/specialists/{key}/configuration")
def specialist_configuration(
    key: str,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> AgentConfiguration:
    """The persona of one specialist conversation (CFO, AUDITOR, …)."""
    return AgentConfiguration(persona_id=specialist_agent_id(session, user, key))


@router.get("/routines")
def routine_definitions(
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[RoutineView]:
    schedule = schedule_view(session, user)
    sweep = r1_automation(session)
    views = [
        RoutineView(
            key=key,
            name=name,
            status=("Agendada" if schedule.enabled else "Execução manual disponível")
            if key == "R3"
            else "Bloqueada",
            reason=schedule.reason
            if key == "R3"
            else "Capacidade pendente: " + reason + ".",
            schedule=schedule.schedule
            if key == "R3"
            else "Agendamento não configurado",
            next_run=schedule.next_run_at.isoformat()
            if key == "R3" and schedule.next_run_at
            else None,
            last_run=schedule.last_run_at.isoformat()
            if key == "R3" and schedule.last_run_at
            else None,
            last_result=schedule.last_result if key == "R3" else None,
            last_report_url=schedule.last_report_url if key == "R3" else None,
            manual_available=key == "R3",
        )
        for key, name, reason in ROUTINES
    ]
    # R1 is configured from the chat (ton_propose_daily_sweep).
    for index, view in enumerate(views):
        if view.key != "R1":
            continue
        enabled = sweep is not None and sweep.status == "ACTIVE"
        views[index] = view.model_copy(
            update={
                "status": "Ligada" if enabled else "Disponível pelo chat",
                "reason": (
                    "Automação “Varredura financeira diária (R1)”: testes financeiros todo dia, casos no ledger."
                    if enabled
                    else "Peça ao TON para ligar a varredura diária, ou use o modelo em Automações."
                ),
                "schedule": "Diária (veja em Automações)" if enabled else "Desligada",
            }
        )
    return views


@router.get("/routines/R3/schedule")
def r3_schedule(
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> R3ScheduleView:
    return schedule_view(session, user)


@router.put("/routines/R3/schedule")
def update_r3_schedule(
    request: R3ScheduleRequest,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> R3ScheduleView:
    return configure_schedule(session, user, request)


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
    unit_id: UUID | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[SpecialistView]:
    return specialist_views(
        session, user, ClosingRequest(request_id=uuid4(), unit_id=unit_id)
    )


@router.get("/capabilities")
def capabilities(
    unit_id: UUID | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[CapabilityView]:
    return capability_registry(
        session, user, ClosingRequest(request_id=uuid4(), unit_id=unit_id)
    )


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


@router.get("/routines/R3/latest")
def latest_r3_result(
    period: date,
    unit_id: UUID | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_REPORTS)),
    session: Session = Depends(get_session),
) -> PublishedClosing | None:
    return latest_r3_publication(session, user, period, unit_id)


@router.get("/reports/groups")
def report_groups(
    limit: int = Query(default=25, ge=1, le=100),
    user: User = Depends(require_permission(Permission.READ_TON_REPORTS)),
    session: Session = Depends(get_session),
) -> list[ReportGroup]:
    return list_report_groups(session, user, limit)


@router.get("/artifacts")
def chat_artifacts(
    limit: int = Query(default=100, ge=1, le=300),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[ChatArtifactView]:
    """Dashboards, decks and reports the TON built in the person's conversations."""
    return list_chat_artifacts(session, user, limit)


@router.get("/reports/{revision_id}/history")
def report_history(
    revision_id: UUID,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_REPORTS)),
    session: Session = Depends(get_session),
) -> list[PublishedClosing]:
    return report_group_history(session, user, revision_id, limit, offset)


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


@router.get("/ledger")
def ledger(
    status: LedgerFilter = "open",
    text: str | None = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_OCCURRENCES)),
    session: Session = Depends(get_session),
) -> LedgerPage:
    """The occurrence ledger: open cases first, overdue and critical on top."""
    return ledger_page(session, user, status, text, limit, offset)


@router.get("/ledger/{occurrence_id}")
def ledger_case(
    occurrence_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_OCCURRENCES)),
    session: Session = Depends(get_session),
) -> LedgerDetail:
    return ledger_detail(session, user, occurrence_id)


@router.get("/actions/overdue")
def list_overdue_actions(
    limit: int = Query(10, ge=1, le=25),
    user: User = Depends(require_permission(Permission.READ_TON_OCCURRENCES)),
    session: Session = Depends(get_session),
) -> OccurrencePage:
    """Open assigned actions past their recorded deadline; owner and date come from the assignment."""
    return query_occurrences(
        session, user, "ton_list_overdue_actions", ToolQuery(limit=limit)
    )


@router.get("/actions")
def list_agent_actions(
    chat_session_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[AgentActionView]:
    return agent_actions.list_for_session(session, user, chat_session_id)


@router.get("/actions/{action_id}")
def get_agent_action(
    action_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> AgentActionView:
    return agent_actions.get(session, user, action_id)


@router.post("/actions/{action_id}/apply")
def apply_agent_action(
    action_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> AgentActionView:
    return agent_actions.apply(session, user, action_id)


@router.post("/actions/{action_id}/cancel")
def cancel_agent_action(
    action_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> AgentActionView:
    return agent_actions.cancel(session, user, action_id)


@router.post("/actions/{action_id}/undo")
def undo_agent_action(
    action_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> AgentActionView:
    return agent_actions.undo(session, user, action_id)
