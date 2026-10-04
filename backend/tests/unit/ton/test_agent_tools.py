"""Tool input and tenant boundaries independent of the LLM provider."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from onyx.chat.emitter import Emitter
from onyx.db.models import User
from onyx.server.query_and_chat.placement import Placement
from onyx.ton.agent.models import FinancialContext
from onyx.tools.models import ToolCallException
from onyx.tools.tool_implementations.ton.ton_tool import TonFinancialContextTool


def test_tool_binds_tenant_and_reloads_user_before_query() -> None:
    user = User(id=uuid4(), is_active=True)
    emitter = Mock(spec=Emitter)
    with patch(
        "onyx.tools.tool_implementations.ton.ton_tool.get_current_tenant_id",
        return_value="tenant_original",
    ):
        tool = TonFinancialContextTool(42, emitter, user)
    session = Mock()
    session.get.return_value = user
    with (
        patch(
            "onyx.tools.tool_implementations.ton.ton_tool.get_session_with_tenant"
        ) as sessions,
        patch(
            "onyx.tools.tool_implementations.ton.ton_tool.query_domain",
            return_value=FinancialContext(bases=[], structure_version_ids=[]),
        ) as query,
    ):
        sessions.return_value.__enter__.return_value = session
        result = tool.run(Placement(turn_index=0), None, limit=2)
    sessions.assert_called_once_with(tenant_id="tenant_original")
    session.get.assert_called_once_with(User, user.id)
    assert query.call_args.args[1] is user
    assert query.call_args.args[2] == "ton_get_financial_context"
    assert (
        result.llm_facing_response
        == '{"bases": [], "structure_version_ids": [], "units": []}'
    )
    assert emitter.emit.call_count == 1


@pytest.mark.parametrize(
    "arguments", [{"tenant_id": "another_tenant"}, {"sql": "SELECT 1"}, {"limit": 1000}]
)
def test_tool_rejects_scope_override_and_unbounded_query(
    arguments: dict[str, object],
) -> None:
    user = User(id=uuid4(), is_active=True)
    tool = TonFinancialContextTool(42, Mock(spec=Emitter), user)
    with patch(
        "onyx.tools.tool_implementations.ton.ton_tool.get_session_with_tenant"
    ) as sessions:
        with pytest.raises(ToolCallException):
            tool.run(Placement(turn_index=0), None, **arguments)
        sessions.assert_not_called()


def test_demo_mode_requires_explicit_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from onyx.ton.agent.policy import uses_synthetic_demo_data

    monkeypatch.delenv("TON_DEMO_SYNTHETIC_DATA", raising=False)
    assert not uses_synthetic_demo_data()
    monkeypatch.setenv("TON_DEMO_SYNTHETIC_DATA", "true")
    assert uses_synthetic_demo_data()
