"""TON-suggested flows: the assistant proposes definitions built only from
catalog items. Each proposal passes the same validator as the screen and is
stored as "Sugerido pelo TON"; it runs only after a person registers it. The
assistant never writes e-mail content, only picks catalog entries."""

import json
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from onyx.llm.factory import get_default_llm
from onyx.llm.interfaces import LLM
from onyx.llm.models import SystemMessage, UserMessage
from onyx.llm.utils import llm_response_to_string
from onyx.ton.email_flows.catalog import (
    CHANGE_STATES,
    OPERATORS_BY_TYPE,
    SUBJECT_MARKERS,
    TRIGGERS,
)
from onyx.ton.email_flows.logic import FlowItem
from onyx.ton.email_flows.models import FlowDefinition
from onyx.tracing.flows import LLMFlow
from onyx.tracing.llm_utils import llm_generation_span
from onyx.utils.logger import setup_logger

logger = setup_logger()

LLM_TIMEOUT_SECONDS = 120
MAX_SUGGESTIONS = 3

SYSTEM_PROMPT = """Você ajuda a Controladoria de uma empresa a montar fluxos de e-mail \
automáticos sobre os dados financeiros do NG. Um fluxo é: gatilho → condições → ação \
no "sim" / ação no "não". Proponha no máximo 3 fluxos úteis que ainda não existam, \
usando SOMENTE os gatilhos, campos, operadores, modelos e marcadores do catálogo. \
Não invente destinatários: use apenas os endereços conhecidos informados, ou deixe \
"to" vazio para a pessoa preencher. O texto do e-mail é gerado pelo sistema; você só \
escolhe o modelo e escreve um assunto curto. Responda apenas com JSON no formato \
{"suggestions": [{"name": "...", "reason": "uma frase dizendo por que ajuda", \
"definition": {...}}]}. Exemplo de definition válida (os parâmetros do gatilho ficam \
direto no objeto trigger): {"trigger": {"kind": "SCHEDULE", "frequency": "WEEKLY", \
"weekday": 0, "time": "08:00", "changes": []}, "conditions": [{"field": "itens", \
"operator": "GT", "value": 0}], "on_yes": {"kind": "EMAIL", "to": [], "cc": [], "bcc": [], \
"subject": "Inconsistências ({total})", "template": "INCONSISTENCY_REPORT"}, "on_no": \
{"kind": "NONE"}}. Para NG_OCCURRENCE_CHANGED use "changes": ["NEW", "REAPPEARED"] \
(ou "CORRECTED")."""


@dataclass
class ParsedSuggestion:
    name: str
    reason: str
    definition: FlowDefinition


@dataclass
class SuggestionOutcome:
    suggestions: list[ParsedSuggestion] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    model_name: str | None = None


def catalog_for_prompt() -> dict[str, Any]:
    return {
        "triggers": [
            {
                "kind": spec.kind.value,
                "label": spec.label,
                "description": spec.description,
                "params": (
                    {"frequency": ["WEEKLY", "DAILY"], "weekday": "0=segunda … 6=domingo", "time": "HH:MM (Brasília)"}
                    if spec.kind.value == "SCHEDULE"
                    else {"changes": [state.value for state in CHANGE_STATES]}
                    if spec.kind.value == "NG_OCCURRENCE_CHANGED"
                    else {}
                ),
                "fields": [
                    {
                        "key": item.key,
                        "label": item.label,
                        "operators": [op.value for op in OPERATORS_BY_TYPE[item.type]],
                        **({"choices": [key for key, _ in item.choices]} if item.choices else {}),
                    }
                    for item in spec.fields
                ],
                "templates": [template.value for template in spec.templates],
            }
            for spec in TRIGGERS.values()
        ],
        "action": {
            "kind": ["EMAIL", "NONE"],
            "fields": ["to", "cc", "bcc", "subject", "template"],
            "subject_markers": list(SUBJECT_MARKERS),
        },
    }


def build_prompt(
    items: Sequence[FlowItem],
    existing: Sequence[str],
    known_addresses: Sequence[str],
) -> str:
    by_rule = Counter(str(item.fields.get("regra")) for item in items)
    by_unit = Counter(str(item.fields.get("unidade")) for item in items)
    context = {
        "inconsistencias_abertas": len(items),
        "por_regra": dict(by_rule.most_common(10)),
        "por_unidade": dict(by_unit.most_common(10)),
        "fluxos_existentes": list(existing),
        "enderecos_conhecidos": list(known_addresses),
        "catalogo": catalog_for_prompt(),
    }
    return json.dumps(context, ensure_ascii=False)


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,;]", value) if item.strip()]
    return [value]


def _normalize(raw: Any) -> Any:
    """Forgive the near-misses models make in otherwise valid proposals:
    trigger parameters nested under "params", a single condition or address
    given outside a list. Anything else is left for the validator to reject."""
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
    conditions = definition.get("conditions")
    if isinstance(conditions, dict):
        definition["conditions"] = [conditions]
    elif conditions is None:
        definition["conditions"] = []
    for key in ("on_yes", "on_no"):
        action = definition.get(key)
        if isinstance(action, dict):
            action = dict(action)
            for field in ("to", "cc", "bcc"):
                if field in action:
                    action[field] = _as_list(action[field])
            definition[key] = action
        elif action is None and key == "on_no":
            definition[key] = {"kind": "NONE"}
    return definition


def parse_suggestions(text: str, existing: Sequence[str]) -> SuggestionOutcome:
    outcome = SuggestionOutcome()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        outcome.rejected.append("resposta sem JSON")
        return outcome
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        outcome.rejected.append("JSON inválido")
        return outcome
    taken = {name.casefold() for name in existing}
    for entry in (raw.get("suggestions") or [])[:MAX_SUGGESTIONS]:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()[:120]
        reason = str(entry.get("reason") or "").strip()[:1000]
        if len(name) < 3 or name.casefold() in taken:
            outcome.rejected.append(name or "sem nome")
            continue
        try:
            definition = FlowDefinition.model_validate(
                _normalize(entry.get("definition") or {})
            )
        except ValidationError as error:
            outcome.rejected.append(f"{name}: {error.errors()[0].get('msg', 'inválido')}")
            continue
        taken.add(name.casefold())
        outcome.suggestions.append(ParsedSuggestion(name, reason or "Sugestão do TON", definition))
    return outcome


def suggest(
    items: Sequence[FlowItem],
    existing: Sequence[str],
    known_addresses: Sequence[str],
    llm: LLM | None = None,
) -> SuggestionOutcome:
    model = llm or get_default_llm(timeout=LLM_TIMEOUT_SECONDS, temperature=0)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        UserMessage(content=build_prompt(items, existing, known_addresses)),
    ]
    try:
        with llm_generation_span(
            llm=model, flow=LLMFlow.TON_EMAIL_FLOW_SUGGESTION, input_messages=messages
        ):
            response = model.invoke(messages, timeout_override=LLM_TIMEOUT_SECONDS)
        text = llm_response_to_string(response)
    except Exception:
        logger.exception("TON email flow suggestion failed")
        return SuggestionOutcome(rejected=["o assistente não respondeu"], model_name=model.config.model_name)
    outcome = parse_suggestions(text, existing)
    outcome.model_name = model.config.model_name
    return outcome
