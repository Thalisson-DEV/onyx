"""Outbound HTTP (webhooks of Teams, Slack, Zeev, any HTTPS API).

Only https; hosts that resolve to private, loopback or link-local addresses
are refused, so a flow cannot reach the TON's internal network."""

import ipaddress
import json
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from onyx.ton.automations.definition import RetryPolicy
from onyx.ton.automations.expressions import to_text
from onyx.ton.automations.registry import (
    ActionContext,
    ActionError,
    FieldSpec,
    NodeSpec,
    OutputSpec,
    ParamSpec,
    register,
)

MAX_BODY = 1_000_000
DEFAULT_TIMEOUT = 30
_RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}


def check_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ActionError("Use um endereço https:// completo")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ActionError(f"Não encontrei o endereço {parsed.hostname}", retryable=True) from None
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast:
            raise ActionError("Endereços internos não são permitidos")
    return url.strip()


def _headers(value: Any) -> dict[str, str]:
    headers: dict[str, str] = {}
    for entry in value or []:
        if isinstance(entry, dict) and str(entry.get("key") or "").strip():
            headers[str(entry["key"]).strip()] = to_text(entry.get("value"))
    return headers


def _request(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    method = str(params.get("method") or "POST").upper()
    url = check_url(to_text(params.get("url")))
    headers = _headers(params.get("headers"))
    body = params.get("body")
    content: bytes | None = None
    if method not in ("GET", "DELETE") and body not in (None, ""):
        if isinstance(body, (dict, list)):
            content = json.dumps(body, ensure_ascii=False).encode()
            headers.setdefault("Content-Type", "application/json")
        else:
            content = to_text(body).encode()
            stripped = to_text(body).strip()
            if stripped.startswith(("{", "[")):
                headers.setdefault("Content-Type", "application/json")
    timeout = min(120, ctx.timeout_seconds or DEFAULT_TIMEOUT)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.request(method, url, headers=headers, content=content)
    except httpx.TimeoutException:
        raise ActionError("O serviço não respondeu a tempo", retryable=True) from None
    except httpx.HTTPError as error:
        raise ActionError(f"Falha de conexão: {type(error).__name__}", retryable=True) from None
    raw = response.content[:MAX_BODY].decode(response.encoding or "utf-8", errors="replace")
    try:
        parsed: Any = json.loads(raw) if raw.strip() else None
    except json.JSONDecodeError:
        parsed = raw
    if response.status_code >= 400 and params.get("fail_on_error", True) is not False:
        raise ActionError(
            f"O serviço respondeu {response.status_code}: {raw[:200]}",
            retryable=response.status_code in _RETRY_STATUSES,
        )
    return {
        "status": response.status_code,
        "ok": response.status_code < 400,
        "body": parsed,
        "headers": {key: value for key, value in list(response.headers.items())[:40]},
    }


register(
    NodeSpec(
        type="http.request",
        group="integration",
        label="Chamar serviço (HTTP)",
        description="Chama um endereço https (webhook do Teams, Slack, Zeev ou outra API) e usa a resposta nos próximos passos.",
        icon="globe",
        params=(
            ParamSpec("method", "Método", "select", default="POST", dynamic=False, options=(("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("PATCH", "PATCH"), ("DELETE", "DELETE"))),
            ParamSpec("url", "Endereço", "text", required=True, placeholder="https://..."),
            ParamSpec("headers", "Cabeçalhos", "keyvalue", default=[], item_fields=(FieldSpec("key", "Nome"), FieldSpec("value", "Valor"))),
            ParamSpec("body", "Corpo", "textarea", placeholder='{"texto": "..."}', show_if=("method", ("POST", "PUT", "PATCH"))),
            ParamSpec("fail_on_error", "Falhar quando o serviço responder erro (4xx/5xx)", "boolean", default=True, dynamic=False, advanced=True),
        ),
        outputs=(
            OutputSpec("status", "Código da resposta", "number"),
            OutputSpec("ok", "Deu certo", "boolean"),
            OutputSpec("body", "Resposta", "any"),
            OutputSpec("headers", "Cabeçalhos da resposta", "object"),
        ),
        executor=_request,
        side_effect=True,
        default_retry=RetryPolicy(policy="exponential", count=3, interval_seconds=10),
        keywords=("webhook", "api", "teams", "slack", "zeev", "integração", "rest"),
    )
)
