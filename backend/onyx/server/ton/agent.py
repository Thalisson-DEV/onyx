from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton.agent import provision_agent

router = APIRouter(prefix="/ton/agent", tags=["TON Agent"])


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
