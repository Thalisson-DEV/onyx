"""The artifact tool keeps a clean, bounded spec the chat can draw."""

import json
from unittest.mock import Mock
from uuid import uuid4

import pytest

from onyx.db.models import User
from onyx.tools.tool_implementations.ton.ton_tool import TonCreateArtifactTool


def _compute(**kwargs: object) -> dict:
    tool = TonCreateArtifactTool.__new__(TonCreateArtifactTool)
    return tool.compute(Mock(), User(id=uuid4(), is_active=True), kwargs)


def test_dashboard_keeps_blocks_and_gets_an_id() -> None:
    result = _compute(
        artifact_kind="painel",
        title="Receita por unidade",
        blocks=[
            {"type": "kpis", "items": [{"label": "Receita", "value": 10.5, "display": "R$ 10,5 mi", "tone": "odd"}]},
            {"type": "barras", "items": [{"label": "Toledo-PR", "value": 3412880.1}], "format": "xx"},
            {"type": "tabela", "columns": ["Unidade", "Receita"], "rows": [["Toledo-PR", "3.412.880,10", "extra"]]},
        ],
        sources=["NG · carga 16/10", ""],
    )
    assert result["kind"] == "ton_artifact"
    assert len(result["artifact_id"]) == 12
    kpis, bars, table = result["blocks"]
    assert kpis["items"][0]["tone"] == "neutral"
    assert bars["format"] == "brl"
    # Cells beyond the declared columns are dropped.
    assert table["rows"] == [["Toledo-PR", "3.412.880,10"]]
    assert result["sources"] == ["NG · carga 16/10"]


def test_new_version_reuses_the_artifact_id() -> None:
    result = _compute(
        artifact_kind="apresentacao",
        title="Fechamento",
        artifact_id="abc123def456",
        slides=[{"title": "Resultado", "metric": {"value": "R$ 1,12 mi", "label": "resultado"}}, {"body": "sem título"}],
    )
    assert result["artifact_id"] == "abc123def456"
    assert [slide["title"] for slide in result["slides"]] == ["Resultado"]


def test_redo_without_id_continues_the_same_artifact() -> None:
    tool = TonCreateArtifactTool.__new__(TonCreateArtifactTool)
    tool._chat_session_id = uuid4()
    session = Mock()
    session.scalars.return_value = [
        "not json",
        json.dumps({"kind": "ton_artifact", "artifact_id": "other1234567", "artifact_kind": "painel", "title": "Outro"}),
        json.dumps(
            {
                "tool_name": "ton_create_artifact",
                "tool_result": {
                    "kind": "ton_artifact",
                    "artifact_id": "abc123def456",
                    "artifact_kind": "painel",
                    "title": "Receita · SET",
                },
            }
        ),
    ]
    result = tool.compute(
        session,
        User(id=uuid4(), is_active=True),
        {"artifact_kind": "painel", "title": "Receita · set", "blocks": [{"type": "texto", "body": "a"}]},
    )
    assert result["artifact_id"] == "abc123def456"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"artifact_kind": "planilha", "title": "X", "blocks": [{"type": "texto", "body": "a"}]},
        {"artifact_kind": "painel", "title": "", "blocks": [{"type": "texto", "body": "a"}]},
        {"artifact_kind": "painel", "title": "X"},
        {"artifact_kind": "apresentacao", "title": "X"},
        {"artifact_kind": "painel", "title": "X", "blocks": [{"type": "pizza"}]},
        {"artifact_kind": "painel", "title": "X", "artifact_id": "../etc", "blocks": [{"type": "texto", "body": "a"}]},
    ],
)
def test_rejects_incomplete_or_unknown_specs(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        _compute(**kwargs)
