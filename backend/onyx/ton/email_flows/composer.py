"""E-mail composition for flows v2.

The body comes from the browser editor as HTML. Here it is sanitized by an
allowlist, variables become escaped text, data blocks are filled from the
read models (numbers never come from the editor or an LLM), images become
inline attachments (cid:) and the default style template wraps it all.
"""

import datetime
import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from html import escape
from typing import Any

from lxml import html as lxml_html
from lxml.etree import ParserError

from onyx.ton.email_flows.logic import BRASILIA, FlowItem, format_money

# ---------------------------------------------------------------------------
# Sanitizing
# ---------------------------------------------------------------------------

_ALLOWED_TAGS: dict[str, set[str]] = {
    "p": {"style"},
    "h1": {"style"},
    "h2": {"style"},
    "h3": {"style"},
    "strong": set(),
    "b": set(),
    "em": set(),
    "i": set(),
    "u": set(),
    "s": set(),
    "br": set(),
    "hr": set(),
    "blockquote": {"style"},
    "ul": set(),
    "ol": set(),
    "li": {"style"},
    "a": {"href"},
    "span": {"style", "data-variable"},
    "mark": {"style", "data-color"},
    "img": {"data-asset-id", "alt", "width"},
    "div": {"data-block"},
}
_STYLE_RULES = {
    "color": re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\([\d\s.,%]+\))$"),
    "background-color": re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\([\d\s.,%]+\))$"),
    "text-align": re.compile(r"^(left|right|center|justify)$"),
    "font-size": re.compile(r"^\d{1,2}(px|pt|em|rem)$"),
}
_HREF = re.compile(r"^(https?://|mailto:)", re.IGNORECASE)
_ASSET_ID = re.compile(r"^[0-9a-f-]{32,36}$")
_VARIABLE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
BLOCKS: dict[str, str] = {
    "inconsistency_table": "Tabela de inconsistências por unidade",
    "account_table": "Lista de contas sem classificação",
    "summary": "Resumo em números",
    "ton_button": "Botão “Abrir no TON”",
}


def _clean_style(value: str) -> str:
    kept = []
    for declaration in value.split(";"):
        if ":" not in declaration:
            continue
        name, _, raw = declaration.partition(":")
        name, raw = name.strip().lower(), raw.strip()
        rule = _STYLE_RULES.get(name)
        if rule and rule.match(raw):
            kept.append(f"{name}: {raw}")
    return "; ".join(kept)


def sanitize(body: str) -> str:
    """Keep only what the editor produces; everything else is dropped (its
    text kept). Safe to store and to render in the preview iframe."""
    if not body.strip():
        return ""
    try:
        root = lxml_html.fragment_fromstring(body, create_parent="div")
    except (ParserError, ValueError):
        return ""
    for element in list(root.iter()):
        if element is root or not isinstance(element.tag, str):
            if element is not root and element.getparent() is not None:
                element.drop_tree()
            continue
        tag = element.tag.lower()
        if tag in {"script", "style", "iframe", "object", "embed", "form", "input"}:
            element.drop_tree()
            continue
        allowed = _ALLOWED_TAGS.get(tag)
        if allowed is None:
            element.drop_tag()
            continue
        for attribute in list(element.attrib):
            if attribute not in allowed:
                del element.attrib[attribute]
        if "style" in element.attrib:
            style = _clean_style(element.attrib["style"])
            if style:
                element.attrib["style"] = style
            else:
                del element.attrib["style"]
        if tag == "a":
            href = element.attrib.get("href", "")
            if not _HREF.match(href):
                element.attrib.pop("href", None)
        if tag == "img" and not _ASSET_ID.match(element.attrib.get("data-asset-id", "")):
            element.drop_tree()
            continue
        if tag == "span" and "data-variable" in element.attrib:
            if not _VARIABLE.match(element.attrib["data-variable"]):
                del element.attrib["data-variable"]
        if tag == "div" and element.attrib.get("data-block") not in BLOCKS:
            element.drop_tag()
    inner = (root.text or "") and escape(root.text or "")
    return inner + "".join(
        lxml_html.tostring(child, encoding="unicode") for child in root
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_INLINE: dict[str, str] = {
    "p": "margin:0 0 12px;font-size:14px;line-height:1.55",
    "h1": "margin:0 0 12px;font-size:22px;line-height:1.3",
    "h2": "margin:16px 0 8px;font-size:18px;line-height:1.3",
    "h3": "margin:14px 0 6px;font-size:16px;line-height:1.3",
    "ul": "margin:0 0 12px;padding-left:22px;font-size:14px;line-height:1.55",
    "ol": "margin:0 0 12px;padding-left:22px;font-size:14px;line-height:1.55",
    "blockquote": "margin:0 0 12px;padding:8px 14px;border-left:3px solid #d1d5db;color:#4b5563",
    "hr": "border:none;border-top:1px solid #e5e7eb;margin:16px 0",
}
_CELL = "padding:7px 9px;border-bottom:1px solid #e5e7eb;font-size:13px;vertical-align:top"
_HEAD = "padding:7px 9px;border-bottom:2px solid #d1d5db;font-size:12px;text-align:left;color:#6b7280"


@dataclass(frozen=True)
class EmailLayout:
    brand_color: str = "#1f6f43"
    logo_asset_id: str | None = None
    footer: str = (
        "Enviado automaticamente pelo TON. O TON não altera o NG: as correções são "
        "feitas no NG e conferidas na próxima extração."
    )


@dataclass
class RenderContext:
    variables: Mapping[str, str]
    items: Sequence[FlowItem]
    fields: Mapping[str, Any]
    ton_url: str
    note: str | None = None
    # "cid" for sending, "url" for the preview in the browser.
    image_mode: str = "cid"
    asset_url: Callable[[str], str] = lambda asset_id: f"/api/ton/email-flows/assets/{asset_id}"
    used_assets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ComposedEmail:
    subject: str
    html: str
    text: str
    asset_ids: list[str]


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
        'style="border-collapse:collapse;width:100%;margin:4px 0 16px">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def _inconsistency_block(ctx: RenderContext, color: str) -> str:
    if not ctx.items:
        return f'<p style="{_INLINE["p"]}">Nenhuma inconsistência aberta.</p>'
    by_unit: dict[str, list[FlowItem]] = defaultdict(list)
    for item in ctx.items:
        by_unit[str(item.fields.get("unidade") or "Sem unidade")].append(item)
    parts = []
    for unit in sorted(by_unit):
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
            for item in sorted(
                by_unit[unit],
                key=lambda item: (-(item.fields.get("semanas_em_aberto") or 0), item.key),
            )
        ]
        parts.append(
            f'<h3 style="{_INLINE["h3"]};color:{color}">{escape(unit)} · {len(rows)}</h3>'
            + _table(
                ["Inconsistência", "Onde", "Conta", "Valor", "O que fazer no NG", "Situação", "Semanas"],
                rows,
                {3, 6},
            )
        )
    return "".join(parts)


def _account_block(ctx: RenderContext) -> str:
    if not ctx.items:
        return f'<p style="{_INLINE["p"]}">Todas as contas estão classificadas.</p>'
    rows = [
        [
            str(item.fields.get("conta") or ""),
            item.columns.get("descricao", ""),
            str(item.fields.get("lancamentos") or 0),
            format_money(item.fields.get("valor")),
        ]
        for item in sorted(ctx.items, key=lambda item: item.key)
    ]
    return _table(["Conta", "Descrição", "Lançamentos", "Valor"], rows, {2, 3})


def _summary_block(ctx: RenderContext, color: str) -> str:
    total = ctx.fields.get("itens", len(ctx.items))
    amount = format_money(ctx.fields.get("valor_total"))
    cell = (
        "padding:12px 16px;border:1px solid #e5e7eb;border-radius:8px;"
        "font-size:13px;color:#6b7280"
    )
    number = f"display:block;font-size:22px;font-weight:700;color:{color}"
    return (
        '<table role="presentation" cellspacing="8" cellpadding="0" style="margin:4px 0 16px"><tr>'
        f'<td style="{cell}"><span style="{number}">{escape(str(total))}</span>itens</td>'
        f'<td style="{cell}"><span style="{number}">{escape(amount)}</span>valor total</td>'
        "</tr></table>"
    )


def _button_block(ctx: RenderContext, color: str) -> str:
    return (
        f'<p style="margin:8px 0 16px"><a href="{escape(ctx.ton_url, quote=True)}" '
        f'style="display:inline-block;background:{color};color:#ffffff;text-decoration:none;'
        'padding:10px 18px;border-radius:6px;font-size:14px;font-weight:600">Abrir no TON</a></p>'
    )


def _image_src(ctx: RenderContext, asset_id: str) -> str:
    if asset_id not in ctx.used_assets:
        ctx.used_assets.append(asset_id)
    return f"cid:asset-{asset_id}" if ctx.image_mode == "cid" else ctx.asset_url(asset_id)


def render_body(body: str, ctx: RenderContext, layout: EmailLayout) -> str:
    clean = sanitize(body)
    if not clean:
        return ""
    root = lxml_html.fragment_fromstring(clean, create_parent="div")
    color = layout.brand_color
    for element in list(root.iter()):
        if element is root or not isinstance(element.tag, str):
            continue
        tag = element.tag
        if tag == "span" and "data-variable" in element.attrib:
            name = element.attrib["data-variable"]
            value = ctx.variables.get(name)
            replacement = lxml_html.fragment_fromstring(
                f"<span>{escape(value if value is not None else '{' + name + '}')}</span>"
            )
            replacement.tail = element.tail
            element.getparent().replace(element, replacement)
            continue
        if tag == "div" and "data-block" in element.attrib:
            block = element.attrib["data-block"]
            markup = {
                "inconsistency_table": lambda: _inconsistency_block(ctx, color),
                "account_table": lambda: _account_block(ctx),
                "summary": lambda: _summary_block(ctx, color),
                "ton_button": lambda: _button_block(ctx, color),
            }[block]()
            replacement = lxml_html.fragment_fromstring(markup, create_parent="div")
            replacement.tail = element.tail
            element.getparent().replace(element, replacement)
            continue
        if tag == "img":
            asset_id = element.attrib.pop("data-asset-id")
            element.attrib["src"] = _image_src(ctx, asset_id)
            width = element.attrib.get("width", "")
            element.attrib["style"] = (
                f"max-width:100%;height:auto;{'width:' + width + 'px;' if width.isdigit() else ''}"
                "border:0;display:block;margin:4px 0 12px"
            )
            continue
        if tag == "a":
            element.attrib["style"] = f"color:{color}"
        base = _INLINE.get(tag)
        if base:
            own = element.attrib.get("style")
            element.attrib["style"] = f"{base};{own}" if own else base
    return "".join(lxml_html.tostring(child, encoding="unicode") for child in root)


def wrap_layout(content: str, ctx: RenderContext, layout: EmailLayout | None) -> str:
    footer_note = f"{escape(ctx.note)} " if ctx.note else ""
    if layout is None:
        inner = (
            f'<div style="max-width:720px;margin:0 auto">{content}'
            f'<p style="font-size:12px;color:#6b7280;margin-top:24px">{footer_note}</p></div>'
        )
    else:
        logo = (
            f'<img src="{_image_src(ctx, layout.logo_asset_id)}" alt="Logo" '
            'style="height:40px;width:auto;border:0;display:block">'
            if layout.logo_asset_id
            else ""
        )
        inner = (
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
            'style="max-width:720px;margin:0 auto;border:1px solid #e5e7eb;border-radius:10px;'
            'overflow:hidden;background:#ffffff">'
            f'<tr><td style="padding:18px 24px;border-bottom:4px solid {layout.brand_color}">{logo}</td></tr>'
            f'<tr><td style="padding:24px">{content}</td></tr>'
            '<tr><td style="padding:16px 24px;background:#f9fafb;font-size:12px;line-height:1.5;color:#6b7280">'
            f"{footer_note}{escape(layout.footer)}</td></tr></table>"
        )
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:16px;background:#f3f4f6;'
        'font-family:Arial,Helvetica,sans-serif;color:#1f2937">'
        f"{inner}</body></html>"
    )


_MARKER = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def render_subject(subject: str, variables: Mapping[str, str]) -> str:
    return _MARKER.sub(lambda m: variables.get(m.group(1), m.group(0)), subject)


def html_to_text(document: str) -> str:
    try:
        root = lxml_html.fromstring(document)
    except (ParserError, ValueError):
        return ""
    for br in root.iter("br"):
        br.tail = "\n" + (br.tail or "")
    for element in root.iter("p", "h1", "h2", "h3", "li", "tr", "div"):
        element.tail = "\n" + (element.tail or "")
    for cell in root.iter("td", "th"):
        cell.tail = " | " + (cell.tail or "")
    text = root.text_content()
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def compose(
    *,
    subject: str,
    body: str,
    ctx: RenderContext,
    layout: EmailLayout | None,
) -> ComposedEmail:
    content = render_body(body, ctx, layout or EmailLayout())
    document = wrap_layout(content, ctx, layout)
    return ComposedEmail(
        subject=render_subject(subject, ctx.variables)[:300],
        html=document,
        text=html_to_text(document),
        asset_ids=list(ctx.used_assets),
    )


def system_variables(
    *,
    when: datetime.datetime,
    fields: Mapping[str, Any],
    flow_name: str,
    ton_url: str,
) -> dict[str, str]:
    local = when.astimezone(BRASILIA)
    return {
        "semana": str(local.isocalendar()[1]),
        "data": local.strftime("%d/%m/%Y"),
        "total": str(fields.get("itens", 0)),
        "valor_total": format_money(fields.get("valor_total")),
        "nome_fluxo": flow_name,
        "link_ton": ton_url,
    }
