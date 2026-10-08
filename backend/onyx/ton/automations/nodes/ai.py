"""AI steps: interpret what earlier steps produced and hand text or
structured fields to the next steps.

AI interprets, extracts, classifies and summarizes; it never produces an
official number. Every output carries ``gerado_por_ia`` and the checker warns
when a condition routes on AI output without a human approval before an
external effect."""

import json
from dataclasses import replace
import re
from typing import Any

from onyx.ton.automations.expressions import to_number, to_text
from onyx.ton.automations.registry import (
    ActionContext,
    ActionError,
    FieldSpec,
    NodeSpec,
    OutputSpec,
    ParamSpec,
    register,
)
from onyx.ton.automations.definition import AutomationKind, RetryPolicy

DEFAULT_TIMEOUT = 120
MAX_INPUT_CHARS = 60_000
_AI_RETRY = RetryPolicy(policy="exponential", count=2, interval_seconds=5)
_FIELD_TYPES = (("text", "Texto"), ("number", "Número"), ("boolean", "Sim/Não"), ("list", "Lista"), ("date", "Data"))

SYSTEM = (
    "Você é um passo de uma automação da Controladoria de uma empresa brasileira. "
    "Responda em português do Brasil, de forma objetiva. Use somente as informações recebidas; "
    "se algo não estiver nos dados, diga que não está. Nunca invente números."
)


def _llm_call(ctx: ActionContext, system: str, user: str, temperature: float) -> str:
    from onyx.llm.factory import get_default_llm
    from onyx.llm.models import SystemMessage, UserMessage
    from onyx.llm.utils import llm_response_to_string
    from onyx.tracing.flows import LLMFlow
    from onyx.tracing.llm_utils import llm_generation_span

    timeout = ctx.timeout_seconds or DEFAULT_TIMEOUT
    try:
        model = get_default_llm(timeout=timeout, temperature=temperature)
    except Exception as error:  # noqa: BLE001 - no provider configured
        raise ActionError(f"Nenhum modelo de IA configurado no TON ({type(error).__name__})") from None
    messages: list[Any] = [SystemMessage(content=system), UserMessage(content=user)]
    try:
        with llm_generation_span(llm=model, flow=LLMFlow.TON_AUTOMATION_AI_STEP, input_messages=messages):
            response = model.invoke(messages, timeout_override=timeout)
    except Exception as error:  # noqa: BLE001 - provider errors are transient
        raise ActionError(f"O modelo de IA não respondeu: {type(error).__name__}", retryable=True) from None
    return llm_response_to_string(response)


def _as_input(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str, indent=1)
    if len(text) > MAX_INPUT_CHARS:
        return text[:MAX_INPUT_CHARS] + "\n[… cortado]"
    return text


def _json_from(text: str) -> Any:
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    if not match:
        raise ActionError("A IA não devolveu JSON", retryable=True)
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        raise ActionError("A IA devolveu JSON inválido", retryable=True) from None


def _coerce_fields(fields: list[dict[str, Any]], raw: Any) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    result: dict[str, Any] = {}
    for field in fields:
        name = str(field.get("name") or "").strip()
        if not name:
            continue
        value = data.get(name)
        kind = field.get("type") or "text"
        if kind == "number":
            value = to_number(value)
        elif kind == "boolean":
            value = value if isinstance(value, bool) else to_text(value).strip().casefold() in ("true", "sim", "1")
        elif kind == "list":
            value = value if isinstance(value, list) else ([] if value in (None, "") else [value])
        else:
            value = None if value is None else to_text(value)
        result[name] = value
    return result


def _schema_text(fields: list[dict[str, Any]]) -> str:
    lines = []
    for field in fields:
        name = str(field.get("name") or "").strip()
        if name:
            lines.append(f'- "{name}" ({field.get("type") or "text"}): {field.get("description") or ""}')
    return "\n".join(lines)


def _clean_fields(params: dict[str, Any]) -> list[dict[str, Any]]:
    return [field for field in params.get("fields") or [] if str(field.get("name") or "").strip()]


def _prompt(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    instructions = to_text(params.get("instructions")).strip()
    if not instructions:
        raise ActionError("Escreva as instruções do prompt")
    data = params.get("input")
    fields = _clean_fields(params)
    temperature = float(to_number(params.get("temperature")) or 0)
    user = instructions
    if data not in (None, ""):
        user += f"\n\nDADOS:\n{_as_input(data)}"
    if params.get("output") == "fields" and fields:
        user += (
            "\n\nResponda SOMENTE com um objeto JSON com estes campos:\n"
            + _schema_text(fields)
            + "\nUse null quando a informação não existir."
        )
        text = _llm_call(ctx, SYSTEM, user, temperature)
        values = _coerce_fields(fields, _json_from(text))
        return {"text": text, "fields": values}
    text = _llm_call(ctx, SYSTEM, user, temperature).strip()
    return {"text": text, "fields": {}}


_FIELDS_PARAM = ParamSpec(
    "fields",
    "Campos de saída",
    "fields",
    default=[],
    dynamic=False,
    item_fields=(
        FieldSpec("name", "Nome", placeholder="fornecedor"),
        FieldSpec("type", "Tipo", "select", _FIELD_TYPES),
        FieldSpec("description", "O que é", placeholder="Razão social do fornecedor"),
    ),
)

register(
    NodeSpec(
        type="ai.prompt",
        group="ai",
        label="Executar prompt de IA",
        description="A IA lê os dados que você indicar e responde em texto ou em campos que os próximos passos usam.",
        icon="sparkles",
        params=(
            ParamSpec("instructions", "Instruções", "textarea", required=True, placeholder="Resuma as inconsistências abaixo para a diretoria, em 5 linhas."),
            ParamSpec("input", "Dados para a IA", "textarea", placeholder="Use ⚡ para escolher os dados de um passo anterior"),
            ParamSpec("output", "Resposta em", "select", default="text", dynamic=False, options=(("text", "Texto"), ("fields", "Campos estruturados"))),
            replace(_FIELDS_PARAM, show_if=("output", ("fields",))),
            ParamSpec("temperature", "Criatividade (0 a 1)", "number", default=0, dynamic=False, min=0, max=1, advanced=True),
        ),
        outputs=(
            OutputSpec("text", "Resposta", "string"),
            OutputSpec("fields", "Campos", "object"),
            OutputSpec("gerado_por_ia", "Gerado por IA", "boolean"),
        ),
        executor=_prompt,
        default_retry=_AI_RETRY,
        satisfies=(AutomationKind.DATA_AI,),
        dynamic_outputs="fields",
        ai=True,
        keywords=("gpt", "llm", "prompt", "ia", "inteligência", "copilot"),
    )
)


def _extract(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    fields = _clean_fields(params)
    if not fields:
        raise ActionError("Informe os campos a extrair")
    data = params.get("input")
    if data in (None, ""):
        raise ActionError("Informe o texto de onde extrair")
    user = (
        "Extraia os campos abaixo do conteúdo. Responda SOMENTE com um objeto JSON.\n"
        + _schema_text(fields)
        + "\nUse null quando o campo não estiver no conteúdo; não deduza valores."
        + f"\n\nCONTEÚDO:\n{_as_input(data)}"
    )
    text = _llm_call(ctx, SYSTEM, user, 0)
    values = _coerce_fields(fields, _json_from(text))
    missing = [name for name, value in values.items() if value in (None, "", [])]
    return {"fields": values, "missing": missing, "complete": not missing}


register(
    NodeSpec(
        type="ai.extract",
        group="ai",
        label="Extrair informações",
        description="Tira campos estruturados de um texto livre (e-mail, PDF, observação).",
        icon="scan",
        params=(
            ParamSpec("input", "Texto", "textarea", required=True, placeholder="Use ⚡ para escolher o texto de um passo anterior"),
            replace(_FIELDS_PARAM, required=True, label="Campos a extrair"),
        ),
        outputs=(
            OutputSpec("fields", "Campos", "object"),
            OutputSpec("missing", "Campos não encontrados", "array"),
            OutputSpec("complete", "Encontrou todos", "boolean"),
            OutputSpec("gerado_por_ia", "Gerado por IA", "boolean"),
        ),
        executor=_extract,
        default_retry=_AI_RETRY,
        satisfies=(AutomationKind.DATA_AI,),
        dynamic_outputs="fields",
        ai=True,
        keywords=("extrair", "ocr", "ler", "documento", "estruturar"),
    )
)


def _classify(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    categories = [to_text(c).strip() for c in (params.get("categories") or []) if to_text(c).strip()]
    if isinstance(params.get("categories"), str):
        categories = [c.strip() for c in str(params["categories"]).split(",") if c.strip()]
    if len(categories) < 2:
        raise ActionError("Informe ao menos duas categorias")
    data = params.get("input")
    if data in (None, ""):
        raise ActionError("Informe o que classificar")
    guidance = to_text(params.get("guidance")).strip()
    user = (
        "Classifique o conteúdo em UMA das categorias. Responda SOMENTE com JSON "
        '{"category": "...", "confidence": 0.0 a 1.0, "reason": "uma frase"}.\n'
        f"Categorias: {json.dumps(categories, ensure_ascii=False)}\n"
        + (f"Critério: {guidance}\n" if guidance else "")
        + f"\nCONTEÚDO:\n{_as_input(data)}"
    )
    raw = _json_from(_llm_call(ctx, SYSTEM, user, 0))
    category = to_text(raw.get("category") if isinstance(raw, dict) else "").strip()
    match = next((c for c in categories if c.casefold() == category.casefold()), None)
    if match is None:
        raise ActionError(f"A IA respondeu uma categoria fora da lista: {category}", retryable=True)
    confidence = to_number(raw.get("confidence")) if isinstance(raw, dict) else None
    return {
        "category": match,
        "confidence": float(confidence) if confidence is not None else None,
        "reason": to_text(raw.get("reason") if isinstance(raw, dict) else ""),
    }


register(
    NodeSpec(
        type="ai.classify",
        group="ai",
        label="Classificar com IA",
        description="Escolhe uma categoria para o conteúdo, com confiança e motivo. Combine com 'Escolher caso'.",
        icon="tag",
        params=(
            ParamSpec("input", "Conteúdo", "textarea", required=True),
            ParamSpec("categories", "Categorias", "list", required=True, default=[], placeholder="Urgente"),
            ParamSpec("guidance", "Critério", "textarea", placeholder="Urgente quando o valor passa de R$ 100 mil ou o prazo vence em 3 dias"),
        ),
        outputs=(
            OutputSpec("category", "Categoria", "string"),
            OutputSpec("confidence", "Confiança (0 a 1)", "number"),
            OutputSpec("reason", "Motivo", "string"),
            OutputSpec("gerado_por_ia", "Gerado por IA", "boolean"),
        ),
        executor=_classify,
        default_retry=_AI_RETRY,
        satisfies=(AutomationKind.DATA_AI,),
        ai=True,
        keywords=("categoria", "triagem", "classificar", "prioridade"),
    )
)


def _summarize(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    data = params.get("input")
    if data in (None, ""):
        raise ActionError("Informe o que resumir")
    style = {
        "executive": "um resumo executivo para a diretoria, com o que importa e o que fazer",
        "bullets": "tópicos curtos",
        "email": "um parágrafo cordial para um e-mail",
    }.get(str(params.get("style") or "executive"), "um resumo executivo")
    limit = int(to_number(params.get("max_lines")) or 7)
    user = f"Escreva {style}, em no máximo {limit} linhas.\n\nDADOS:\n{_as_input(data)}"
    return {"text": _llm_call(ctx, SYSTEM, user, 0.2).strip()}


register(
    NodeSpec(
        type="ai.summarize",
        group="ai",
        label="Resumir com IA",
        description="Resume dados ou textos em linguagem de negócio.",
        icon="text",
        params=(
            ParamSpec("input", "O que resumir", "textarea", required=True),
            ParamSpec("style", "Formato", "select", default="executive", dynamic=False, options=(("executive", "Resumo executivo"), ("bullets", "Tópicos"), ("email", "Parágrafo de e-mail"))),
            ParamSpec("max_lines", "Máximo de linhas", "number", default=7, dynamic=False, min=1, max=40),
        ),
        outputs=(OutputSpec("text", "Resumo", "string"), OutputSpec("gerado_por_ia", "Gerado por IA", "boolean")),
        executor=_summarize,
        default_retry=_AI_RETRY,
        satisfies=(AutomationKind.DATA_AI,),
        ai=True,
        keywords=("resumo", "síntese", "executivo"),
    )
)
