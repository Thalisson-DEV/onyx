"""Artifacts the TON built in the person's conversations, for the library."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.models import ChatSession, ToolCall, User


class ChatArtifactView(BaseModel):
    artifact_id: str
    artifact_kind: str
    title: str
    subtitle: str | None
    created_at: str
    versions: int
    slides: int
    blocks: int
    chat_session_id: UUID
    chat_name: str | None
    chat_updated: datetime


def _artifact(response: str) -> dict[str, Any] | None:
    try:
        data = json.loads(response)
    except (TypeError, ValueError):
        return None
    # Stored as the call summary: {"tool_name", "tool_result": {...}}.
    if isinstance(data, dict) and isinstance(data.get("tool_result"), dict):
        data = data["tool_result"]
    if not isinstance(data, dict) or data.get("kind") != "ton_artifact":
        return None
    if not isinstance(data.get("artifact_id"), str) or not data.get("title"):
        return None
    return data


def list_chat_artifacts(
    session: Session, user: User, limit: int
) -> list[ChatArtifactView]:
    """The latest version of each artifact in the person's own conversations."""
    rows = session.execute(
        select(
            ToolCall.tool_call_response,
            ChatSession.id,
            ChatSession.description,
            ChatSession.time_updated,
        )
        .join(ChatSession, ChatSession.id == ToolCall.chat_session_id)
        .where(
            ChatSession.user_id == user.id,
            ChatSession.deleted.is_(False),
            ToolCall.tool_call_response.contains('"ton_artifact"'),
        )
        .order_by(ToolCall.id.desc())
    )
    found: dict[str, ChatArtifactView] = {}
    for response, chat_id, chat_name, chat_updated in rows:
        data = _artifact(response)
        if data is None:
            continue
        key = data["artifact_id"]
        if key in found:
            found[key].versions += 1
            continue
        if len(found) >= limit:
            continue
        found[key] = ChatArtifactView(
            artifact_id=key,
            artifact_kind=str(data.get("artifact_kind", "painel")),
            title=str(data["title"]),
            subtitle=data.get("subtitle"),
            created_at=str(data.get("created_at", "")),
            versions=1,
            slides=len(data.get("slides") or []),
            blocks=len(data.get("blocks") or []),
            chat_session_id=chat_id,
            chat_name=chat_name,
            chat_updated=chat_updated,
        )
    return list(found.values())
