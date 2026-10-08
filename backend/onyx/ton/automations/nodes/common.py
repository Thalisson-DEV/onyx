"""Shared pieces of TON nodes: the item shape of inconsistencies and
accounts, and the outputs every list-producing node exposes."""

import datetime
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from onyx.ton.automations.expressions import BRASILIA, format_money
from onyx.ton.automations.registry import OutputSpec
from onyx.ton.email_flows.logic import FlowItem

INCONSISTENCY_ITEM_FIELDS: tuple[OutputSpec, ...] = (
    OutputSpec("codigo", "Código", "string"),
    OutputSpec("regra", "Regra (código)", "string"),
    OutputSpec("regra_nome", "Regra", "string"),
    OutputSpec("unidade", "Unidade", "string"),
    OutputSpec("valor", "Valor", "number"),
    OutputSpec("valor_formatado", "Valor (R$)", "string"),
    OutputSpec("semanas_em_aberto", "Semanas em aberto", "number"),
    OutputSpec("competencia", "Mês de competência", "number"),
    OutputSpec("situacao", "Situação (código)", "string"),
    OutputSpec("situacao_label", "Situação", "string"),
    OutputSpec("mudou", "Mudança nesta importação", "string"),
    OutputSpec("evidencia", "Onde está (planilha, linha, documento)", "string"),
    OutputSpec("conta", "Conta", "string"),
    OutputSpec("correcao", "O que fazer no NG", "string"),
)
ACCOUNT_ITEM_FIELDS: tuple[OutputSpec, ...] = (
    OutputSpec("conta", "Código da conta", "string"),
    OutputSpec("descricao", "Descrição", "string"),
    OutputSpec("valor", "Valor lançado", "number"),
    OutputSpec("valor_formatado", "Valor (R$)", "string"),
    OutputSpec("lancamentos", "Lançamentos", "number"),
)
BY_UNIT_FIELDS: tuple[OutputSpec, ...] = (
    OutputSpec("unidade", "Unidade", "string"),
    OutputSpec("count", "Quantidade", "number"),
    OutputSpec("total", "Valor total", "number"),
    OutputSpec("items", "Itens da unidade", "array", item_fields=INCONSISTENCY_ITEM_FIELDS),
)


def list_outputs(item_fields: tuple[OutputSpec, ...], noun: str) -> tuple[OutputSpec, ...]:
    return (
        OutputSpec("items", f"Lista de {noun}", "array", item_fields=item_fields),
        OutputSpec("count", "Quantidade", "number"),
        OutputSpec("total", "Valor total", "number"),
        OutputSpec("total_formatado", "Valor total (R$)", "string"),
    )


def inconsistency_item(item: FlowItem) -> dict[str, Any]:
    fields, columns = dict(item.fields), dict(item.columns)
    return {
        "chave": item.key,
        "codigo": columns.get("codigo", ""),
        "regra": fields.get("regra", ""),
        "regra_nome": columns.get("regra_nome", ""),
        "unidade": fields.get("unidade") or "Sem unidade",
        "valor": float(fields.get("valor") or 0),
        "valor_formatado": columns.get("valor") or format_money(fields.get("valor")),
        "semanas_em_aberto": int(fields.get("semanas_em_aberto") or 0),
        "competencia": fields.get("competencia"),
        "situacao": fields.get("situacao"),
        "situacao_label": columns.get("situacao", ""),
        "mudou": fields.get("mudou"),
        "evidencia": columns.get("evidencia", ""),
        "conta": columns.get("conta", ""),
        "correcao": columns.get("correcao", ""),
    }


def as_flow_item(item: Any) -> FlowItem:
    """The e-mail blocks read FlowItem; accept any dict produced here."""
    if isinstance(item, FlowItem):
        return item
    data = dict(item) if isinstance(item, dict) else {"valor": 0}
    columns = {key: str(value) if value is not None else "" for key, value in data.items()}
    columns["situacao"] = str(data.get("situacao_label") or data.get("situacao") or "")
    columns["valor"] = str(data.get("valor_formatado") or format_money(data.get("valor")))
    return FlowItem(str(data.get("chave") or data.get("conta") or id(item)), data, columns)


def summarize(items: Sequence[dict[str, Any]]) -> dict[str, Any]:
    total = sum((Decimal(str(item.get("valor") or 0)) for item in items), Decimal(0))
    return {
        "items": list(items),
        "count": len(items),
        "total": float(total),
        "total_formatado": format_money(total),
    }


def by_unit(items: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[str(item.get("unidade") or "Sem unidade")].append(item)
    return [
        {
            "unidade": unit,
            "count": len(groups[unit]),
            "total": float(sum((Decimal(str(i.get("valor") or 0)) for i in groups[unit]), Decimal(0))),
            "items": groups[unit],
        }
        for unit in sorted(groups)
    ]


def review_note(last_review_at: datetime.datetime | None) -> str:
    if last_review_at is None:
        return "Nenhuma extração do NG conferida ainda."
    local = last_review_at.astimezone(BRASILIA)
    return f"Última extração do NG conferida em {local:%d/%m/%Y às %H:%M}."


def optional_uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except ValueError:
        return None
