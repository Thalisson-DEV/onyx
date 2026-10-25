"""The correction plan (Ocorrências): cases to fix at the source."""

import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import correction_plan as service
from onyx.ton.correction.models import (
    ActionRequest,
    BoardRequest,
    BoardSummary,
    CaseDetail,
    CaseRow,
    DecisionRequest,
    OwnerRequest,
    ReminderDraft,
    ReminderRequest,
)

router = APIRouter(prefix="/ton/correction", tags=["TON correction plan"])
_member = require_permission(Permission.READ_TON_SOURCES)


@router.get("/cases")
def list_cases(
    user: User = Depends(_member), session: Session = Depends(get_session)
) -> list[CaseRow]:
    return service.list_cases(session, user)


@router.get("/cases/{case_id}")
def get_case(
    case_id: UUID,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> CaseDetail:
    return service.get_case(session, user, case_id)


@router.post("/cases/owner")
def set_owner(
    request: OwnerRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> list[CaseRow]:
    return service.set_owner(session, user, request)


@router.put("/cases/{case_id}/action")
def set_action(
    case_id: UUID,
    request: ActionRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> CaseDetail:
    return service.set_action(session, user, case_id, request)


@router.post("/cases/{case_id}/decision")
def decide(
    case_id: UUID,
    request: DecisionRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> CaseDetail:
    return service.decide(session, user, case_id, request)


@router.post("/cases/board")
def set_board(
    request: BoardRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> None:
    service.set_board(session, user, request)


@router.post("/cases/reminder")
def reminder(
    request: ReminderRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> list[ReminderDraft]:
    return service.reminder(session, user, request)


@router.get("/board")
def board(
    user: User = Depends(_member), session: Session = Depends(get_session)
) -> BoardSummary:
    return service.board(session, user)


@router.get("/board.xlsx")
def board_xlsx(
    user: User = Depends(_member), session: Session = Depends(get_session)
) -> Response:
    return Response(
        content=service.board_xlsx(session, user),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=plano-de-correcao-{datetime.date.today():%Y-%m-%d}.xlsx"
        },
    )
