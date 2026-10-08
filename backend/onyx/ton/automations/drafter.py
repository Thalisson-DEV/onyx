"""Draft an automation from a request written in Portuguese (chat or the
designer's "Pedir ao TON").

The LLM sees the node catalog and returns a v3 definition. It passes the
same structure validation as the designer and is saved as a DRAFT (or a new
version of the draft being adjusted). Nothing runs until a person activates
it."""

import json
import re
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import automations as repository
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.automations.api import DraftResult
from onyx.ton.automations.definition import (
    KIND_LABELS,
    AutomationDefinition,
    AutomationKind,
    AutomationOrigin,
    AutomationStatus,
    Node,
    iter_nodes,
    unique_id,
)
from onyx.ton.automations.expressions import FUNCTION_HELP
from onyx.ton.automations.registry import NodeSpec, OutputSpec, get_registry
from onyx.ton.automations.templates import TEMPLATES
from onyx.ton.automations.validation import activation_problems, suggest_kind, validate
from onyx.utils.audit import AuditAction
from onyx.utils.logger import setup_logger

logger = setup_logger()

LLM_TIMEOUT_SECONDS = 150
_CONTAINER_KEYS = ("then", "else", "steps", "default")

SYSTEM_PROMPT = """Você monta automações (workflows) para a Controladoria de uma empresa, a partir \
de um pedido em português, no estilo do Power Automate. Responda SOMENTE com JSON:
{"name": "nome curto", "kind": "EMAIL|ALERT|ROUTINE|APPROVAL|DATA_AI|GENERAL", \
"summary": "uma frase do que a automação faz", \
"missing": ["o que a pessoa ainda precisa informar, ex.: e-mail do Financeiro"], \
"definition": {"schema": 3, "trigger": {"type": "...", "params": {...}}, \
"variables": [{"name": "limite", "type": "number", "value": 100000}], "steps": [nó, ...]}}

Nó: {"id": "id_curto_sem_espaco", "type": "...", "label": "Rótulo em português", "params": {...}}
Blocos (contêineres):
- control.condition: "params": {"condition": {"op": "and|or", "rules": [{"left": "{{ ... }}", "operator": "gt", "right": "0"}]}}, "then": [nós], "else": [nós]
- control.switch: "params": {"on": "{{ ... }}"}, "cases": [{"id": "c1", "value": "...", "steps": [nós]}], "default": [nós]
- control.foreach: "params": {"items": "{{ lista }}"}, "steps": [nós]  (dentro use {{ item.campo }})
- control.until: "params": {"condition": {...}, "max_iterations": 10}, "steps": [nós]
- control.scope: "steps": [nós]; control.parallel: "branches": [{"id": "b1", "label": "...", "steps": [nós]}]
Tratamento de erro: "run_after": ["failed"] num nó faz ele rodar só se o anterior falhar; \
"retry": {"policy": "exponential", "count": 3, "interval_seconds": 30}.

Expressões (conteúdo dinâmico) entre {{ }}: trigger.outputs.<campo>, steps.<id>.outputs.<campo>, \
vars.<nome>, item.<campo> (dentro de 'Para cada' ou nas regras de 'Filtrar lista'), funções: %s.
Um valor que é só {{ expr }} mantém o tipo (lista, número).

Regras:
- Use só os tipos de nó do catálogo enviado e os parâmetros listados.
- Um nó só pode usar saídas de nós que rodam ANTES dele.
- E-mail: corpo em HTML simples (p, h2, h3, strong, em, ul, li, a). Dados no corpo: \
<span data-expr="steps.x.outputs.campo"></span> e blocos <div data-block="inconsistency_table|account_table|items_table|summary|ton_button" data-source="steps.x.outputs.items"></div>. \
Nunca escreva números ou listas à mão: use expressões e blocos.
- IA interpreta, não decide: se uma condição usar resposta de IA antes de enviar algo para fora, \
inclua 'approval.request' antes.
- Não invente e-mails: use só endereços escritos no pedido; senão deixe a lista vazia e cite em "missing".
- Ids em minúsculas, únicos, com _ (ex.: buscar, tem_itens, enviar_financeiro).
"""


def _output_keys(outputs: tuple[OutputSpec, ...]) -> list[str]:
    keys: list[str] = []
    for output in outputs:
        if output.item_fields:
            keys.append(f"{output.key}[]: {', '.join(f.key for f in output.item_fields)}")
        else:
            keys.append(output.key)
    return keys


def _spec_for_prompt(spec: NodeSpec) -> dict[str, Any]:
    params = []
    for param in spec.params:
        entry: dict[str, Any] = {"key": param.key, "kind": param.kind}
        if param.required:
            entry["required"] = True
        if param.options:
            # Value -> meaning (e.g. weekdays: "0" -> "Segunda"), so the model does not guess.
            entry["options"] = {key: label for key, label in param.options}
        if param.item_fields:
            entry["fields"] = [field.key for field in param.item_fields]
        if param.default not in (None, "", [], {}):
            entry["default"] = param.default
        params.append(entry)
    return {
        "type": spec.type,
        "label": spec.label,
        "description": spec.description,
        **({"container": spec.container} if spec.container else {}),
        **({"params": params} if params else {}),
        **({"outputs": _output_keys(spec.outputs)} if spec.outputs else {}),
    }


def catalog_for_prompt() -> dict[str, Any]:
    registry = get_registry()
    return {
        "triggers": [_spec_for_prompt(s) for s in registry.values() if s.is_trigger],
        "nodes": [_spec_for_prompt(s) for s in registry.values() if not s.is_trigger and not s.type.startswith("test.")],
        "kinds": {kind.value: KIND_LABELS[kind] for kind in AutomationKind},
        "example": {"name": TEMPLATES[0].name, "kind": TEMPLATES[0].kind.value, "definition": TEMPLATES[0].definition},
    }


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,;]", value) if item.strip()]
    return [value]


def _normalize_nodes(raw: Any, taken: set[str]) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    nodes: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict) or not entry.get("type"):
            continue
        node = dict(entry)
        base = str(node.get("id") or node.get("label") or node["type"].split(".")[-1])
        node_id = unique_id(base, taken)
        taken.add(node_id)
        node["id"] = node_id
        params = dict(node.get("params") or {})
        for key in ("to", "cc", "bcc", "approvers"):
            if key in params and not (isinstance(params[key], str) and "{{" in params[key]):
                params[key] = _as_list(params[key])
        if "condition" in params and isinstance(params["condition"], dict) and "rules" not in params["condition"]:
            params["condition"] = {"op": "and", "rules": [params["condition"]]}
        node["params"] = params
        if "run_after" in node:
            node["run_after"] = _as_list(node["run_after"]) or ["succeeded"]
        for key in _CONTAINER_KEYS:
            if key in node:
                node[key] = _normalize_nodes(node[key], taken)
        if "cases" in node and isinstance(node["cases"], list):
            node["cases"] = [
                {**case, "id": unique_id(str(case.get("id") or "caso"), taken), "value": str(case.get("value", "")), "steps": _normalize_nodes(case.get("steps"), taken)}
                for case in node["cases"]
                if isinstance(case, dict)
            ]
            for case in node["cases"]:
                taken.add(case["id"])
        if "branches" in node and isinstance(node["branches"], list):
            node["branches"] = [
                {**branch, "id": unique_id(str(branch.get("id") or "ramo"), taken), "steps": _normalize_nodes(branch.get("steps"), taken)}
                for branch in node["branches"]
                if isinstance(branch, dict)
            ]
            for branch in node["branches"]:
                taken.add(branch["id"])
        nodes.append(node)
    return nodes


def normalize(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("definição ausente")
    definition = dict(raw)
    definition["schema"] = 3
    trigger = definition.get("trigger")
    if isinstance(trigger, str):
        trigger = {"type": trigger, "params": {}}
    if not isinstance(trigger, dict):
        trigger = {"type": "trigger.manual", "params": {}}
    definition["trigger"] = {"type": trigger.get("type") or "trigger.manual", "params": trigger.get("params") or {}}
    definition["steps"] = _normalize_nodes(definition.get("steps"), set())
    definition["variables"] = [v for v in definition.get("variables") or [] if isinstance(v, dict) and v.get("name")]
    return definition


def _llm_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("a resposta não trouxe JSON")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        raise ValueError("JSON inválido") from None
    if not isinstance(parsed, dict):
        raise ValueError("JSON inválido")
    return parsed


def _blocking_errors(definition: AutomationDefinition) -> list[str]:
    """Errors worth one more LLM attempt (missing recipients are expected)."""
    return [
        f"{issue.node_id or ''}: {issue.message}"
        for issue in validate(definition)
        if issue.severity == "error" and not issue.message.startswith("Preencha 'Para'") and not issue.message.startswith("Preencha 'Quem aprova'")
    ]


def generate(request: str, *, current: dict[str, Any] | None = None, current_name: str | None = None) -> tuple[dict[str, Any], AutomationDefinition, str | None]:
    from onyx.llm.factory import get_default_llm
    from onyx.llm.models import AssistantMessage, SystemMessage, UserMessage
    from onyx.llm.utils import llm_response_to_string
    from onyx.tracing.flows import LLMFlow
    from onyx.tracing.llm_utils import llm_generation_span

    try:
        model = get_default_llm(timeout=LLM_TIMEOUT_SECONDS, temperature=0)
    except Exception as error:  # noqa: BLE001 - no provider configured
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, f"Nenhum modelo de IA configurado ({type(error).__name__})") from None
    context: dict[str, Any] = {"catalogo": catalog_for_prompt(), "pedido": request}
    if current is not None:
        context["automacao_atual"] = {"name": current_name, "definition": current}
        context["instrucao"] = "Ajuste a automação atual conforme o pedido e devolva a automação completa."
    system = SYSTEM_PROMPT % ", ".join(FUNCTION_HELP)
    messages: list[Any] = [SystemMessage(content=system), UserMessage(content=json.dumps(context, ensure_ascii=False))]
    last_error = ""
    best: tuple[dict[str, Any], AutomationDefinition] | None = None
    for _attempt in range(3):
        with llm_generation_span(llm=model, flow=LLMFlow.TON_AUTOMATION_DRAFT, input_messages=messages):
            response = model.invoke(messages, timeout_override=LLM_TIMEOUT_SECONDS)
        text = llm_response_to_string(response)
        try:
            raw = _llm_json(text)
            definition = AutomationDefinition.model_validate(normalize(raw.get("definition")))
        except (ValueError, ValidationError) as error:
            if isinstance(error, ValidationError):
                first = error.errors()[0]
                last_error = f"{'.'.join(str(p) for p in first.get('loc', ()))}: {first.get('msg', 'inválido')}"
            else:
                last_error = str(error)
            feedback = f"A resposta não passou na validação ({last_error}). Corrija e responda só o JSON."
        else:
            errors = _blocking_errors(definition)
            best = (raw, definition)
            if not errors:
                return raw, definition, model.config.model_name
            last_error = "; ".join(errors[:8])
            feedback = f"O verificador encontrou problemas: {last_error}. Corrija e responda só o JSON completo."
        logger.info("TON automation draft retry: %s", last_error)
        messages = [*messages, AssistantMessage(content=text), UserMessage(content=feedback)]
    if best is not None:
        return best[0], best[1], model.config.model_name
    raise OnyxError(OnyxErrorCode.INVALID_INPUT, f"Não consegui montar a automação: {last_error}")


def steps_text(definition: AutomationDefinition) -> list[str]:
    registry = get_registry()
    lines: list[str] = []
    trigger = registry.get(definition.trigger.type)
    lines.append(f"Quando: {trigger.label if trigger else definition.trigger.type}")

    def walk(nodes: list[Node], depth: int) -> None:
        for node in nodes:
            spec = registry.get(node.type)
            lines.append(f"{'  ' * depth}• {node.label or (spec.label if spec else node.type)}")
            for slot, children in node.children():
                if not children:
                    continue
                name = {"then": "Sim", "else": "Não", "steps": "", "default": "Padrão"}.get(slot, slot.split(":", 1)[-1])
                if name:
                    lines.append(f"{'  ' * (depth + 1)}{name}:")
                walk(children, depth + 2 if name else depth + 1)

    walk(definition.steps, 0)
    return lines[:40]


def draft_automation(
    session: Session,
    user: User,
    request: str,
    automation_id: UUID | None = None,
    current: AutomationDefinition | None = None,
) -> DraftResult:
    from onyx.ton.automations import service

    repository.require_manage(user)
    existing = repository.get_automation(session, automation_id) if automation_id else None
    if existing is not None and existing.status == AutomationStatus.ARCHIVED.value:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Essa automação está arquivada")
    base = current.dump() if current is not None else (
        repository.current_version(session, existing).definition if existing else None
    )
    raw, definition, model_name = generate(request, current=base, current_name=existing.name if existing else None)
    definition = service._clean(definition)
    if base and isinstance(base.get("layout"), dict):
        # Keep where the user placed the nodes that survived the adjustment.
        known = {node.id for node in iter_nodes(definition.steps)} | {"trigger"}
        definition.layout = {key: value for key, value in base["layout"].items() if key in known}
    try:
        kind = AutomationKind(str(raw.get("kind") or ""))
    except ValueError:
        kind = suggest_kind(definition)
    name = str(raw.get("name") or "Automação do TON").strip()[:120]
    if len(name) < 3:
        name = "Automação do TON"
    summary = str(raw.get("summary") or "").strip()[:500]
    missing = [str(item)[:200] for item in _as_list(raw.get("missing"))][:10]
    problems = activation_problems(definition, kind)
    now = service._now()
    if existing is None:
        automation = repository.create__no_commit(
            session,
            user,
            name=name,
            description=summary or None,
            kind=kind,
            definition=definition,
            origin=AutomationOrigin.TON_SUGGESTED,
            status=AutomationStatus.DRAFT,
            now=now,
            suggestion_reason=f"Pedido: {request[:900]}",
            suggestion_model=model_name,
        )
        created = True
    else:
        automation = existing
        if automation.status == AutomationStatus.ACTIVE.value and problems:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "O ajuste deixaria a automação ativa incompleta: " + "; ".join(problems[:5]))
        repository.add_version__no_commit(
            session, user, automation, name=name, description=summary or automation.description,
            kind=kind, definition=definition, now=now, note=f"Ajustada pelo TON: {request[:200]}",
        )
        created = False
    repository.audit(session, user, AuditAction.TON_AUTOMATION_SUGGEST, automation, {"created": created, "model": model_name})
    session.commit()
    return DraftResult(
        automation_id=automation.id,
        name=automation.name,
        kind=kind,
        status=AutomationStatus(automation.status),
        created=created,
        summary=summary,
        when=service._when(definition)[1],
        steps_text=steps_text(definition),
        problems=problems,
        missing=missing,
        editor_url=f"/ton/automacoes/{automation.id}/editar",
        definition=definition,
    )
