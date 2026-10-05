"""Deterministic e-mail templates. Every word and number comes from the
catalog and the read models; nothing here is written by an LLM.

The HTML uses inline styles and a single column so it stays readable in mail
clients on a phone.
"""

import datetime
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html import escape
from typing import Any

from onyx.ton.email_flows.catalog import TRIGGERS, TemplateKey
from onyx.ton.email_flows.logic import (
    BRASILIA,
    FlowEvent,
    FlowItem,
    format_money,
    render_subject,
)

_FONT = "font-family:Arial,Helvetica,sans-serif;color:#1f2937"
_CELL = "padding:6px 8px;border-bottom:1px solid #e5e7eb;font-size:13px;vertical-align:top"
_HEAD = "padding:6px 8px;border-bottom:2px solid #d1d5db;font-size:12px;text-align:left;color:#6b7280"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]], numeric: set[int]) -> str:
    head = "".join(
        f'<th style="{_HEAD}{";text-align:right" if i in numeric else ""}">{escape(h)}</th>'
        for i, h in enumerate(headers)
    )
    body = "".join(
        "<tr>"
        + "".join(
            f'<td style="{_CELL}{";text-align:right;white-space:nowrap" if i in numeric else ""}">{escape(v)}</td>'
            for i, v in enumerate(row)
        )
        + "</tr>"
        for row in rows
    )
    return (
        '<table role="presentation" cellspacing="0" cellpadding="0" '
        f'style="border-collapse:collapse;width:100%;margin:4px 0 18px">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def _page(title: str, intro: str, body: str, footer: str) -> str:
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        f'<body style="margin:0;padding:16px;background:#ffffff;{_FONT}">'
        '<div style="max-width:720px;margin:0 auto">'
        f'<h1 style="font-size:18px;margin:0 0 8px">{escape(title)}</h1>'
        f'<p style="font-size:14px;line-height:1.5;margin:0 0 16px">{escape(intro)}</p>'
        f"{body}"
        f'<p style="font-size:12px;color:#6b7280;line-height:1.5;margin-top:24px">{escape(footer)}</p>'
        "</div></body></html>"
    )


def _footer(event: FlowEvent) -> str:
    note = f"{event.note} " if event.note else ""
    return (
        f"{note}Enviado automaticamente pelo TON. O TON não altera o NG: "
        "as correções são feitas no NG e conferidas na próxima extração."
    )


def _inconsistency_report(
    items: Sequence[FlowItem], fields: Mapping[str, Any], event: FlowEvent
) -> tuple[str, str, str]:
    title = "Inconsistências do NG"
    if not items:
        intro = "Nenhuma inconsistência aberta."
        return title, intro, _page(title, intro, "", _footer(event))
    count = len(items)
    intro = (
        f"{count} {'inconsistência precisa' if count == 1 else 'inconsistências precisam'} "
        f"de correção no NG, somando {format_money(fields.get('valor_total'))}. "
        "Agrupadas por unidade."
    )
    by_unit: dict[str, list[FlowItem]] = defaultdict(list)
    for item in items:
        by_unit[str(item.fields.get("unidade") or "Sem unidade")].append(item)
    sections = []
    text_lines = []
    for unit in sorted(by_unit):
        unit_items = sorted(
            by_unit[unit],
            key=lambda item: (-(item.fields.get("semanas_em_aberto") or 0), item.key),
        )
        rows = [
            [
                item.columns.get("regra_nome", ""),
                item.columns.get("evidencia", ""),
                item.columns.get("conta", ""),
                format_money(item.fields.get("valor")),
                item.columns.get("correcao", ""),
                item.columns.get("situacao", ""),
                str(item.fields.get("semanas_em_aberto") or 0),
            ]
            for item in unit_items
        ]
        sections.append(
            f'<h2 style="font-size:15px;margin:16px 0 4px">{escape(unit)} · {len(rows)}</h2>'
            + _table(
                ["Inconsistência", "Onde", "Conta", "Valor", "O que fazer no NG", "Situação", "Semanas"],
                rows,
                {3, 6},
            )
        )
        text_lines.append(f"\n{unit} ({len(rows)})")
        text_lines.extend(
            f"- {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} semana(s)"
            for r in rows
        )
    html = _page(title, intro, "".join(sections), _footer(event))
    return title, intro + "\n" + "\n".join(text_lines), html


def _account_list(
    items: Sequence[FlowItem], fields: Mapping[str, Any], event: FlowEvent
) -> tuple[str, str, str]:
    title = "Contas do NG sem classificação"
    count = len(items)
    intro = (
        "Todas as contas estão classificadas."
        if not items
        else f"{count} {'conta ainda não tem' if count == 1 else 'contas ainda não têm'} "
        "natureza confirmada. Elas ficam fora da DRE até a confirmação em "
        "Classificação de contas."
    )
    rows = [
        [
            str(item.fields.get("conta") or ""),
            item.columns.get("descricao", ""),
            str(item.fields.get("lancamentos") or 0),
            format_money(item.fields.get("valor")),
        ]
        for item in sorted(items, key=lambda item: item.key)
    ]
    body = _table(["Conta", "Descrição", "Lançamentos", "Valor"], rows, {2, 3}) if rows else ""
    text = intro + "\n" + "\n".join(f"- {r[0]} {r[1]} | {r[2]} | {r[3]}" for r in rows)
    return title, text, _page(title, intro, body, _footer(event))


def _simple_notice(
    items: Sequence[FlowItem], fields: Mapping[str, Any], event: FlowEvent
) -> tuple[str, str, str]:
    spec = TRIGGERS[event.kind]
    title = spec.label
    parts = [f"Aconteceu: {spec.label.lower()}."]
    if event.kind is not event.kind.DRE_RECALCULATED:
        parts.append(f"Itens considerados: {len(items)}.")
        if fields.get("valor_total"):
            parts.append(f"Valor total: {format_money(fields.get('valor_total'))}.")
    if fields.get("competencia") and not event.note:
        parts.append(f"Mês de competência: {fields['competencia']}.")
    intro = " ".join(parts)
    return title, intro, _page(title, intro, "", _footer(event))


_RENDERERS = {
    TemplateKey.INCONSISTENCY_REPORT: _inconsistency_report,
    TemplateKey.ACCOUNT_LIST: _account_list,
    TemplateKey.SIMPLE_NOTICE: _simple_notice,
}


def render(
    template: TemplateKey,
    subject: str,
    items: Sequence[FlowItem],
    fields: Mapping[str, Any],
    event: FlowEvent,
    now: datetime.datetime | None = None,
) -> RenderedEmail:
    when = (now or event.occurred_at).astimezone(BRASILIA)
    _, text, html = _RENDERERS[template](items, fields, event)
    return RenderedEmail(
        render_subject(subject, fields, when), html, f"{text}\n\n{_footer(event)}"
    )
