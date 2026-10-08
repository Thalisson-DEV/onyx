"""Send an e-mail: the rich editor body (style template, images, data
blocks, dynamic content) composed by the e-mail flows composer and sent by
the configured transport (Resend or SMTP)."""

import re
from html import escape
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from onyx.configs.app_configs import WEB_DOMAIN
from onyx.ton.automations.definition import AutomationKind, RetryPolicy
from onyx.ton.automations.expressions import (
    ExpressionError,
    evaluate,
    render,
    to_number,
    to_text,
)
from onyx.ton.automations.nodes.common import as_flow_item
from onyx.ton.automations.registry import (
    ActionContext,
    ActionError,
    NodeSpec,
    OutputSpec,
    ParamSpec,
    register,
)
from onyx.ton.email_flows.composer import RenderContext, compose, sanitize, system_variables
from onyx.ton.email_flows.logic import FlowItem

_TEMPLATE = re.compile(r"{{(.*?)}}", re.DOTALL)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_RECIPIENTS = 200


def addresses(value: Any) -> list[str]:
    """Flatten resolved recipients: lists, comma/semicolon text, dicts with
    an e-mail field."""
    found: list[str] = []

    def add(raw: Any) -> None:
        if raw is None:
            return
        if isinstance(raw, list):
            for entry in raw:
                add(entry)
            return
        if isinstance(raw, dict):
            add(raw.get("email") or raw.get("e-mail") or raw.get("emails"))
            return
        for part in re.split(r"[,;\s]+", to_text(raw)):
            address = part.strip().strip("<>").lower()
            if not address:
                continue
            if not _EMAIL.match(address):
                raise ActionError(f"E-mail inválido: {part}")
            if address not in found:
                found.append(address)

    add(value)
    return found


def inline_templates(body: str, scope: Mapping[str, Any]) -> str:
    """{{ expr }} typed as text in the body: escaped values."""

    def value(match: "re.Match[str]") -> str:
        try:
            return escape(to_text(evaluate(match.group(1), scope)))
        except ExpressionError:
            return ""

    return _TEMPLATE.sub(value, body)


def _ton_url(link: str) -> str:
    base = WEB_DOMAIN.rstrip("/")
    if not link:
        return f"{base}/ton/pendencias"
    return link if link.startswith("https://") else f"{base}{link if link.startswith('/') else '/' + link}"


def _flow_items(value: Any) -> list[FlowItem]:
    if value is None or value == "":
        return []
    if isinstance(value, dict):
        value = value.get("items", [value])
    if not isinstance(value, list):
        raise ActionError("A lista dos blocos de dados não é uma lista")
    return [as_flow_item(item) for item in value]


def _fields(items: Sequence[FlowItem]) -> dict[str, Any]:
    total = sum((Decimal(str(to_number(item.fields.get("valor")) or 0)) for item in items), Decimal(0))
    return {"itens": len(items), "valor_total": float(total)}


def _send(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    from onyx.ton.email_flows import service as flow_service
    from onyx.ton.email_flows.logic import batch_recipients
    from onyx.ton.email_flows.models import EmailAction
    from onyx.ton.email_flows.transport import (
        OutgoingEmail,
        TransportError,
        get_transport,
        provider_name,
    )

    session, _owner = ctx.require_db()
    to, cc, bcc = addresses(params.get("to")), addresses(params.get("cc")), addresses(params.get("bcc"))
    if ctx.is_test:
        if not ctx.test_recipient:
            raise ActionError("Teste sem e-mail de quem testa")
        to, cc, bcc = [ctx.test_recipient], [], []
    if not to:
        raise ActionError("Informe ao menos um destinatário em Para")
    if len(to) + len(cc) + len(bcc) > MAX_RECIPIENTS:
        raise ActionError(f"No máximo {MAX_RECIPIENTS} destinatários")
    subject = to_text(params.get("subject")).strip()
    if not subject:
        raise ActionError("Informe o assunto")
    body = inline_templates(to_text(params.get("body")), ctx.scope)
    if not body.strip():
        raise ActionError("O texto do e-mail está vazio")

    default_items = _flow_items(params.get("items"))
    link = _ton_url(to_text(params.get("link")).strip())
    variables = system_variables(
        when=ctx.now,
        fields=_fields(default_items),
        flow_name=ctx.automation_name,
        ton_url=link,
    )
    for name, value in (ctx.scope.get("vars") or {}).items():
        variables.setdefault(name, to_text(value))

    def resolve(expression: str) -> str:
        try:
            return to_text(evaluate(expression, ctx.scope))
        except ExpressionError:
            return ""

    def items_for(source: str | None) -> tuple[Sequence[FlowItem], Mapping[str, Any]]:
        if not source:
            return default_items, _fields(default_items)
        try:
            listed = _flow_items(evaluate(source, ctx.scope))
        except ExpressionError as error:
            raise ActionError(f"Bloco de dados: {error}") from None
        return listed, _fields(listed)

    render_ctx = RenderContext(
        variables=variables,
        items=default_items,
        fields=_fields(default_items),
        ton_url=link,
        note=to_text(params.get("note")) or None,
        resolve=resolve,
        items_for=items_for,
    )
    layout = flow_service._layout(session) if params.get("use_layout", True) is not False else None
    email = compose(subject=subject, body=body, ctx=render_ctx, layout=layout)
    final_subject = f"[Teste] {email.subject}" if ctx.is_test else email.subject
    transport = get_transport()
    outputs: dict[str, Any] = {
        "to": to,
        "cc": cc,
        "bcc": bcc,
        "subject": final_subject,
        "html": email.html,
        "provider": transport.name if transport else provider_name(),
    }
    if transport is None:
        return {
            **outputs,
            "delivery": "NOT_CONFIGURED",
            "message": "E-mail não configurado no ambiente: o conteúdo ficou guardado no TON.",
            "message_ids": [],
        }
    images = flow_service._images(session, email.asset_ids)
    action = EmailAction.model_construct(kind="EMAIL", to=to, cc=cc, bcc=bcc, subject=final_subject, template=None)
    message_ids: list[str] = []
    for batch in batch_recipients(action, transport.max_recipients):
        message = OutgoingEmail(batch.to, batch.cc, batch.bcc, final_subject, email.html, email.text, images)
        try:
            result = transport.send(message)
        except TransportError as error:
            raise ActionError(f"O provedor recusou o envio: {error}"[:500], retryable=True) from None
        if result.provider_message_id:
            message_ids.append(result.provider_message_id)
    return {**outputs, "delivery": "SENT", "message": "Enviado", "message_ids": message_ids}


def preview_html(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    """The composed e-mail without sending (designer preview)."""
    default_items = _flow_items(params.get("items"))
    link = _ton_url(to_text(params.get("link")).strip())
    variables = system_variables(when=ctx.now, fields=_fields(default_items), flow_name=ctx.automation_name, ton_url=link)

    def resolve(expression: str) -> str:
        try:
            return to_text(evaluate(expression, ctx.scope))
        except ExpressionError:
            return ""

    def items_for(source: str | None) -> tuple[Sequence[FlowItem], Mapping[str, Any]]:
        if not source:
            return default_items, _fields(default_items)
        try:
            listed = _flow_items(evaluate(source, ctx.scope))
        except (ExpressionError, ActionError):
            listed = []
        return listed, _fields(listed)

    render_ctx = RenderContext(
        variables=variables,
        items=default_items,
        fields=_fields(default_items),
        ton_url=link,
        image_mode="url",
        resolve=resolve,
        items_for=items_for,
    )
    layout = None
    if params.get("use_layout", True) is not False and ctx.session is not None:
        from onyx.ton.email_flows import service as flow_service

        layout = flow_service._layout(ctx.session)
    email = compose(subject=to_text(params.get("subject")), body=inline_templates(to_text(params.get("body")), ctx.scope), ctx=render_ctx, layout=layout)
    return {"subject": email.subject, "html": email.html}


register(
    NodeSpec(
        type="email.send",
        group="email",
        label="Enviar e-mail",
        description="Envia um e-mail com o modelo de estilo do TON, texto livre, conteúdo dinâmico e blocos de dados.",
        icon="mail",
        params=(
            ParamSpec("to", "Para", "emails", required=True, default=[]),
            ParamSpec("cc", "Cc", "emails", default=[]),
            ParamSpec("bcc", "Cco", "emails", default=[], advanced=True),
            ParamSpec("subject", "Assunto", "text", required=True, placeholder="Ex.: Inconsistências do NG da semana"),
            ParamSpec("body", "Mensagem", "html", required=True, resolve=False),
            ParamSpec("items", "Lista dos blocos de dados", "expression", placeholder="Use ⚡ para escolher a lista", help="Os blocos (tabela, resumo) usam esta lista quando não indicam outra."),
            ParamSpec("link", "Link do botão “Abrir no TON”", "text", default="/ton/pendencias", advanced=True),
            ParamSpec("use_layout", "Usar o modelo de estilo (logo, cores, rodapé)", "boolean", default=True, dynamic=False),
        ),
        outputs=(
            OutputSpec("subject", "Assunto enviado", "string"),
            OutputSpec("to", "Destinatários", "array"),
            OutputSpec("delivery", "Entrega (SENT / NOT_CONFIGURED)", "string"),
            OutputSpec("message_ids", "Ids no provedor", "array"),
        ),
        executor=_send,
        side_effect=True,
        default_retry=RetryPolicy(policy="exponential", count=3, interval_seconds=30),
        satisfies=(AutomationKind.EMAIL, AutomationKind.ALERT),
        keywords=("email", "e-mail", "mensagem", "outlook", "enviar", "notificar"),
    )
)


def clean_body(body: Any) -> str:
    return sanitize(to_text(body))


__all__ = ["addresses", "clean_body", "preview_html", "render"]
