"""Draft a flow from a request written in the chat.

The assistant turns "quando tal coisa acontecer, mande um e-mail para tal
pessoa, no modelo padrão" into a v2 definition (steps and e-mail text). The
result passes the same validator as the editor and is saved as a draft; it
never sends anything until a person activates it. Numbers and items come
only from variables and data blocks filled by the server.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from onyx.llm.factory import get_default_llm
from onyx.llm.interfaces import LLM
from onyx.llm.models import AssistantMessage, SystemMessage, UserMessage
from onyx.llm.utils import llm_response_to_string
from onyx.ton.email_flows.catalog import CHANGE_STATES, OPERATORS_BY_TYPE, TRIGGERS
from onyx.ton.email_flows.composer import BLOCKS
from onyx.ton.email_flows.steps import (
    SYSTEM_VARIABLES,
    UNIT_VARIABLES,
    FlowDefinitionV2,
)
from onyx.tracing.flows import LLMFlow
from onyx.tracing.llm_utils import llm_generation_span
from onyx.utils.logger import setup_logger

logger = setup_logger()

LLM_TIMEOUT_SECONDS = 120

SYSTEM_PROMPT = """Você monta fluxos de e-mail automáticos para a Controladoria de uma \
empresa, a partir de um pedido em português. Responda SOMENTE com JSON:
{"name": "nome curto do fluxo", "summary": "uma frase do que o fluxo faz", \
"missing": ["o que a pessoa ainda precisa informar, ex.: e-mail do Financeiro"], \
"definition": {...}}

Formato de "definition":
{"trigger": {"kind": "...", ...parâmetros...}, "variables": [{"name": "prazo", "value": "sexta-feira"}],
 "steps": [passo, ...]}
Passos:
- {"type": "send_email", "to": [], "cc": [], "bcc": [], "subject": "...", "body": "<p>...</p>", "use_layout": true}
- {"type": "condition", "conditions": [{"field": "...", "operator": "...", "value": ...}], "then": [passos], "else": [passos]}
  Condições sobre campos de item separam os itens: os que atendem vão para "then", os outros para "else".
- {"type": "for_each_unit", "recipients": [{"unit": "Nome da unidade", "emails": ["..."]}], "default_emails": [], "steps": [passos]}
  Dentro dele use "{email_unidade}" em "to" para mandar a cada unidade os seus itens.
- {"type": "wait", "mode": "duration", "days": 2, "hours": 0} ou {"type": "wait", "mode": "until", "weekday": 4, "time": "17:00"}
  (weekday 0 = segunda; ao retomar, só seguem os itens ainda abertos)
- {"type": "approval", "approvers": ["..."], "message": "..."}

Regras:
- Use só gatilhos, campos e operadores do catálogo enviado.
- Corpo do e-mail em HTML simples: p, h2, h3, strong, em, u, ul, ol, li, a. Escreva um texto \
cordial e objetivo em português. Variáveis: <span data-variable="nome"></span> (as do sistema \
ou as definidas em "variables"). Blocos de dados: <div data-block="..."></div>. Nunca escreva \
números, valores ou listas de itens à mão: use variáveis e blocos.
- "use_layout": true aplica o modelo padrão de estilo (logo, cores, rodapé). Use sempre, salvo \
pedido contrário.
- Não invente e-mails: use apenas endereços escritos no pedido; senão deixe a lista vazia e \
cite em "missing".
- Assunto pode usar variáveis entre chaves, ex.: "Inconsistências – semana {semana} ({total})".
"""


@dataclass
class DraftOutcome:
    name: str
    summary: str
    missing: list[str]
    definition: FlowDefinitionV2
    model_name: str | None


class DraftError(Exception):
    pass


def catalog_for_prompt() -> dict[str, Any]:
    return {
        "triggers": [
            {
                "kind": spec.kind.value,
                "label": spec.label,
                "description": spec.description,
                "params": (
                    {"frequency": ["WEEKLY", "DAILY"], "weekday": "0=segunda … 6=domingo", "time": "HH:MM"}
                    if spec.kind.value == "SCHEDULE"
                    else {"changes": [state.value for state in CHANGE_STATES]}
                    if spec.kind.value == "NG_OCCURRENCE_CHANGED"
                    else {}
                ),
                "fields": [
                    {
                        "key": item.key,
                        "label": item.label,
                        "per_item": item.per_item,
                        "operators": [op.value for op in OPERATORS_BY_TYPE[item.type]],
                        **({"choices": [key for key, _ in item.choices]} if item.choices else {}),
                    }
                    for item in spec.fields
                ],
            }
            for spec in TRIGGERS.values()
        ],
        "system_variables": SYSTEM_VARIABLES,
        "unit_variables_inside_for_each_unit": UNIT_VARIABLES,
        "blocks": BLOCKS,
    }


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,;]", value) if item.strip()]
    return [value]


def _normalize_steps(steps: Any) -> list[Any]:
    if isinstance(steps, dict):
        steps = [steps]
    if not isinstance(steps, list):
        return []
    result = []
    for raw in steps:
        if not isinstance(raw, dict):
            continue
        step = dict(raw)
        for key in ("to", "cc", "bcc", "approvers", "default_emails"):
            if key in step:
                step[key] = _as_list(step[key])
        if "conditions" in step and isinstance(step["conditions"], dict):
            step["conditions"] = [step["conditions"]]
        for key in ("then", "else", "steps"):
            if key in step:
                step[key] = _normalize_steps(step[key])
        result.append(step)
    return result


def normalize(raw: Any) -> Any:
    """Forgive near-misses: trigger params nested under "params", single
    values where lists are expected."""
    if not isinstance(raw, dict):
        return raw
    definition = dict(raw)
    trigger = definition.get("trigger")
    if isinstance(trigger, dict):
        trigger = dict(trigger)
        params = trigger.pop("params", None) or trigger.pop("parameters", None)
        if isinstance(params, dict):
            trigger = {**params, **trigger}
        if "changes" in trigger:
            trigger["changes"] = _as_list(trigger["changes"])
        definition["trigger"] = trigger
    definition["steps"] = _normalize_steps(definition.get("steps"))
    definition.setdefault("variables", [])
    return definition


def parse(text: str) -> tuple[str, str, list[str], FlowDefinitionV2]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise DraftError("a resposta não trouxe JSON")
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        raise DraftError("JSON inválido") from None
    try:
        definition = FlowDefinitionV2.model_validate(normalize(raw.get("definition") or {}))
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first.get("loc", ()))
        raise DraftError(f"{location}: {first.get('msg', 'inválido')}") from None
    name = str(raw.get("name") or "Fluxo do TON").strip()[:120]
    if len(name) < 3:
        name = "Fluxo do TON"
    summary = str(raw.get("summary") or "").strip()[:500]
    missing = [str(item)[:200] for item in _as_list(raw.get("missing"))][:10]
    return name, summary, missing, definition


def draft(
    request: str,
    *,
    current: dict[str, Any] | None = None,
    current_name: str | None = None,
    llm: LLM | None = None,
) -> DraftOutcome:
    model = llm or get_default_llm(timeout=LLM_TIMEOUT_SECONDS, temperature=0)
    context: dict[str, Any] = {"catalogo": catalog_for_prompt(), "pedido": request}
    if current is not None:
        context["fluxo_atual"] = {"name": current_name, "definition": current}
        context["instrucao"] = "Ajuste o fluxo atual conforme o pedido e devolva o fluxo completo."
    messages: list[Any] = [
        SystemMessage(content=SYSTEM_PROMPT),
        UserMessage(content=json.dumps(context, ensure_ascii=False)),
    ]
    last_error = ""
    for _attempt in range(2):
        with llm_generation_span(llm=model, flow=LLMFlow.TON_EMAIL_FLOW_SUGGESTION, input_messages=messages):
            response = model.invoke(messages, timeout_override=LLM_TIMEOUT_SECONDS)
        text = llm_response_to_string(response)
        try:
            name, summary, missing, definition = parse(text)
            return DraftOutcome(name, summary, missing, definition, model.config.model_name)
        except DraftError as error:
            last_error = str(error)
            logger.info("TON flow draft rejected, retrying: %s", last_error)
            messages = [
                *messages,
                AssistantMessage(content=text),
                UserMessage(content=f"O JSON não passou na validação ({last_error}). Corrija e responda só o JSON."),
            ]
    raise DraftError(last_error)
