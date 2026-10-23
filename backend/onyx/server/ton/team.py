"""TON users and their access, managed by a TON administrator."""

from uuid import UUID

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import team as repository
from onyx.db.ton.team import (
    TeamAccessLink,
    TeamMemberCreate,
    TeamMemberUpdate,
    TeamMemberView,
)

router = APIRouter(prefix="/ton/team", tags=["TON team"])


@router.get("")
def list_members(
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> list[TeamMemberView]:
    return repository.list_members(session, user)


@router.post("")
def create_member(
    request: TeamMemberCreate,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> TeamAccessLink:
    return repository.create_member(session, user, request)


@router.put("/{user_id}")
def update_member(
    user_id: UUID,
    request: TeamMemberUpdate,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> TeamMemberView:
    return repository.update_member(session, user, user_id, request)


@router.put("/{user_id}/active")
def set_member_active(
    user_id: UUID,
    active: bool = Body(..., embed=True),
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> TeamMemberView:
    return repository.set_member_active(session, user, user_id, active)


@router.post("/{user_id}/access-link")
def access_link(
    user_id: UUID,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> TeamAccessLink:
    return repository.access_link(session, user, user_id)
