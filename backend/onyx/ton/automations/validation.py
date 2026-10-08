"""The flow checker: errors (block activation) and warnings per node.

The designer runs the same rules in the browser for instant feedback; the
server result is the one that counts."""

import re
from dataclasses import dataclass
from typing import Any, Literal

from onyx.ton.automations import schedule as recurrence
from onyx.ton.automations.conditions import (
    UNARY_OPERATORS,
    ConditionGroup,
    iter_rules,
    parse_group,
)
from onyx.ton.automations.definition import (
    KIND_LABELS,
    AutomationDefinition,
    AutomationKind,
    Node,
    iter_nodes,
)
from onyx.ton.automations.expressions import ExpressionError, template_references
from onyx.ton.automations.registry import NodeSpec, ParamSpec, get_registry

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Parameters evaluated per item (``item`` is the list element there).
ITEM_PARAMS = {
    ("data.filter", "condition"),
    ("data.select", "mapping"),
    ("data.table", "columns"),
}
_STEP_FIELDS = ("outputs", "status", "error")


@dataclass(frozen=True)
class Issue:
    severity: Literal["error", "warning"]
    message: str
    node_id: str | None = None
    param: str | None = None

    def dump(self) -> dict[str, Any]:
        return {"severity": self.severity, "message": self.message, "node_id": self.node_id, "param": self.param}


@dataclass
class _Visibility:
    steps: set[str]
    loops: tuple[str, ...]


def _empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _output_keys(spec: NodeSpec) -> set[str] | None:
    if spec.dynamic_outputs is not None:
        return None
    keys = {output.key for output in spec.outputs}
    if spec.ai:
        keys.add("gerado_por_ia")
    return keys


class _Checker:
    def __init__(self, definition: AutomationDefinition) -> None:
        self.definition = definition
        self.registry = get_registry()
        self.issues: list[Issue] = []
        self.variables = {variable.name for variable in definition.variables}
        self.specs_by_id: dict[str, NodeSpec] = {}
        self.ai_nodes: set[str] = set()
        for node in iter_nodes(definition.steps):
            spec = self.registry.get(node.type)
            if spec is not None:
                self.specs_by_id[node.id] = spec
                if spec.ai:
                    self.ai_nodes.add(node.id)

    def add(self, severity: Literal["error", "warning"], message: str, node_id: str | None = None, param: str | None = None) -> None:
        self.issues.append(Issue(severity, message, node_id, param))

    # -- references ----------------------------------------------------------

    def check_value(self, node_id: str | None, param: str, value: Any, visible: _Visibility, *, item_allowed: bool) -> set[str]:
        """Check a template; return the step ids it reads."""
        try:
            references = template_references(value)
        except ExpressionError as error:
            self.add("error", f"Expressão inválida: {error}", node_id, param)
            return set()
        read: set[str] = set()
        for ref in references:
            if ref.root == "steps":
                if ref.name is None:
                    self.add("error", "Indique o passo: steps.<id>.outputs…", node_id, param)
                    continue
                read.add(ref.name)
                if ref.name == node_id:
                    self.add("error", "Um passo não pode usar a própria saída", node_id, param)
                elif ref.name not in self.specs_by_id:
                    self.add("error", f"O passo '{ref.name}' não existe", node_id, param)
                elif ref.name not in visible.steps:
                    self.add("error", f"O passo '{ref.name}' não roda antes deste (ou está dentro de um 'Para cada' ou de outro ramo)", node_id, param)
                elif ref.rest and ref.rest[0] not in _STEP_FIELDS:
                    self.add("warning", f"Use steps.{ref.name}.outputs.{ref.rest[0]}", node_id, param)
                elif len(ref.rest) >= 2 and ref.rest[0] == "outputs":
                    keys = _output_keys(self.specs_by_id[ref.name])
                    if keys is not None and ref.rest[1] not in keys:
                        self.add("warning", f"O passo '{ref.name}' não tem a saída '{ref.rest[1]}'", node_id, param)
            elif ref.root == "vars":
                if ref.name is not None and ref.name not in self.variables:
                    self.add("error", f"A variável '{ref.name}' não foi declarada", node_id, param)
            elif ref.root == "item":
                if not item_allowed and not visible.loops:
                    self.add("error", "{{ item }} só existe dentro de 'Para cada' (ou nas regras de 'Filtrar lista')", node_id, param)
            elif ref.root == "loop":
                if ref.name is not None and ref.name not in visible.loops:
                    self.add("error", f"'{ref.name}' não é um 'Para cada' que contém este passo", node_id, param)
            elif ref.root == "trigger":
                if ref.name not in (None, "outputs", "type"):
                    self.add("warning", "Use trigger.outputs.<campo>", node_id, param)
                elif ref.name == "outputs" and ref.rest:
                    spec = self.registry.get(self.definition.trigger.type)
                    if spec is not None:
                        keys = _output_keys(spec)
                        if keys is not None and ref.rest[0] not in keys:
                            self.add("warning", f"O gatilho não tem a saída '{ref.rest[0]}'", node_id, param)
        return read

    def check_condition(self, node_id: str, param: str, raw: Any, visible: _Visibility, *, item_allowed: bool) -> set[str]:
        try:
            group: ConditionGroup = parse_group(raw)
        except ValueError as error:
            self.add("error", f"Regras inválidas: {error}", node_id, param)
            return set()
        rules = iter_rules(group)
        read: set[str] = set()
        if not rules:
            self.add("warning", "Sem regras: será sempre verdadeiro", node_id, param)
        for rule in rules:
            if _empty(rule.left):
                self.add("error", "Regra sem valor à esquerda", node_id, param)
            if rule.operator not in UNARY_OPERATORS and rule.right is None:
                self.add("error", "Regra sem valor de comparação", node_id, param)
            read |= self.check_value(node_id, param, rule.left, visible, item_allowed=item_allowed)
            read |= self.check_value(node_id, param, rule.right, visible, item_allowed=item_allowed)
        return read

    # -- params --------------------------------------------------------------

    def check_params(self, node: Node | None, node_id: str | None, node_type: str, spec: NodeSpec, params: dict[str, Any], visible: _Visibility) -> set[str]:
        read: set[str] = set()
        for param in spec.params:
            if param.show_if is not None:
                other, values = param.show_if
                current = params.get(other, (spec.param(other) or ParamSpec(other, other)).default)
                if str(current) not in values:
                    continue
            value = params.get(param.key, param.default)
            if param.required and _empty(value) and param.kind != "condition":
                self.add("error", f"Preencha '{param.label}'", node_id, param.key)
                continue
            item_allowed = (node_type, param.key) in ITEM_PARAMS
            if param.kind == "condition":
                read |= self.check_condition(node_id or "trigger", param.key, value, visible, item_allowed=item_allowed)
                continue
            if param.kind == "emails":
                for entry in value if isinstance(value, list) else [value]:
                    text = str(entry or "").strip()
                    if text and "{{" not in text and not _EMAIL.match(text.lower()):
                        self.add("error", f"E-mail inválido: {text}", node_id, param.key)
            if param.kind in ("select",) and not param.dynamic and param.options and value not in (None, ""):
                if str(value) not in {key for key, _ in param.options}:
                    self.add("error", f"Opção inválida em '{param.label}'", node_id, param.key)
            if param.kind == "multiselect" and param.options and isinstance(value, list):
                allowed = {key for key, _ in param.options}
                if any(str(v) not in allowed for v in value):
                    self.add("error", f"Opção inválida em '{param.label}'", node_id, param.key)
            if param.dynamic or param.kind in ("mapping", "columns", "keyvalue", "expression"):
                read |= self.check_value(node_id, param.key, value, visible, item_allowed=item_allowed)
            if param.kind == "html" and isinstance(value, str):
                for expression in re.findall(r'data-(?:expr|source)="([^"]*)"', value):
                    read |= self.check_value(node_id, param.key, "{{" + expression.replace("&quot;", '"').replace("&#39;", "'") + "}}", visible, item_allowed=False)
                read |= self.check_value(node_id, param.key, re.sub(r"<[^>]+>", " ", value), visible, item_allowed=False)
        if node is not None and node.type.startswith("variable."):
            name = params.get("name")
            if name and name not in self.variables:
                self.add("error", f"A variável '{name}' não foi declarada", node_id, "name")
        return read

    # -- tree ----------------------------------------------------------------

    def walk(self, nodes: list[Node], visible: _Visibility) -> set[str]:
        """Check a list; return the ids later nodes may read."""
        produced: set[str] = set()
        for position, node in enumerate(nodes):
            current = _Visibility(visible.steps | produced, visible.loops)
            spec = self.registry.get(node.type)
            if spec is None:
                self.add("error", f"Tipo de passo desconhecido: {node.type}", node.id)
                produced.add(node.id)
                continue
            if spec.is_trigger:
                self.add("error", "Um gatilho só pode ficar no topo", node.id)
                continue
            if position == 0 and "succeeded" not in node.run_after and not visible.loops and not produced:
                self.add("warning", "Primeiro passo de um bloco: com 'Executar após' sem 'sucesso' ele nunca roda", node.id)
            self.check_slots(node, spec)
            read = self.check_params(node, node.id, node.type, spec, node.params, current)
            self.ai_route_warning(node, spec, read)
            produced.add(node.id)
            if spec.container is None:
                continue
            for slot, children in node.children():
                if not children and slot not in ("else", "default"):
                    self.add("warning", "Bloco vazio", node.id)
                if spec.container in ("loop", "until"):
                    inner = _Visibility(current.steps, (*current.loops, node.id) if spec.container == "loop" else current.loops)
                    self.walk(children, inner)
                else:
                    produced |= self.walk(children, current)
        return produced

    def check_slots(self, node: Node, spec: NodeSpec) -> None:
        allowed = {
            None: set(),
            "condition": {"then", "else"},
            "switch": {"case", "default"},
            "loop": {"steps"},
            "until": {"steps"},
            "scope": {"steps"},
            "parallel": {"branch"},
        }[spec.container]
        for slot, _children in node.children():
            if slot.split(":")[0] not in allowed:
                self.add("error", f"'{spec.label}' não tem o bloco '{slot}'", node.id)
        if spec.container == "switch":
            values = [case.value.strip().casefold() for case in node.cases or []]
            if not values:
                self.add("warning", "Sem casos: tudo vai para o Padrão", node.id)
            if len(values) != len(set(values)):
                self.add("error", "Há casos com o mesmo valor", node.id)
        if spec.container == "parallel" and len(node.branches or []) < 2:
            self.add("warning", "Ramos paralelos precisam de ao menos dois ramos", node.id)

    def ai_route_warning(self, node: Node, spec: NodeSpec, read: set[str]) -> None:
        if spec.container not in ("condition", "switch") and node.type != "data.filter":
            return
        if not (read & self.ai_nodes):
            return
        nodes = list(iter_nodes(self.definition.steps))
        has_effect = any((s := self.registry.get(n.type)) is not None and s.side_effect for n in nodes)
        has_approval = any(n.type == "approval.request" for n in nodes)
        if has_effect and not has_approval:
            self.add(
                "warning",
                "Esta decisão usa uma resposta da IA. A IA interpreta, não decide: inclua 'Pedir aprovação' antes de enviar algo para fora.",
                node.id,
            )

    def run(self) -> list[Issue]:
        trigger = self.registry.get(self.definition.trigger.type)
        if trigger is None or not trigger.is_trigger:
            self.add("error", f"Gatilho desconhecido: {self.definition.trigger.type}", "trigger")
        else:
            self.check_params(None, "trigger", trigger.type, trigger, self.definition.trigger.params, _Visibility(set(), ()))
            if trigger.type == "trigger.schedule":
                try:
                    recurrence.check(self.definition.trigger.params)
                except ValueError as error:
                    self.add("error", str(error), "trigger")
        for variable in self.definition.variables:
            self.check_value(None, f"var:{variable.name}", variable.value, _Visibility(set(), ()), item_allowed=False)
        if not self.definition.steps:
            self.add("error", "Adicione ao menos um passo depois do gatilho")
        self.walk(self.definition.steps, _Visibility(set(), ()))
        for address in self.definition.settings.notify_on_failure:
            if not _EMAIL.match(address.strip().lower()):
                self.add("error", f"E-mail inválido em 'Avisar quando falhar': {address}")
        return self.issues


def validate(definition: AutomationDefinition) -> list[Issue]:
    return _Checker(definition).run()


KIND_REQUIREMENTS: dict[AutomationKind, str] = {
    AutomationKind.EMAIL: "A automação de e-mail não envia nenhum e-mail",
    AutomationKind.ALERT: "O alerta não avisa ninguém: adicione 'Avisar no TON' ou 'Enviar e-mail'",
    AutomationKind.APPROVAL: "A automação de aprovação não tem 'Pedir aprovação'",
    AutomationKind.DATA_AI: "A automação de dados e IA não tem passo de IA",
}


def kind_problems(definition: AutomationDefinition, kind: AutomationKind) -> list[str]:
    registry = get_registry()
    if kind is AutomationKind.ROUTINE:
        if definition.trigger.type == "trigger.manual":
            return ["Uma rotina roda sozinha: use recorrência ou um gatilho de evento"]
        return []
    if kind not in KIND_REQUIREMENTS:
        return []
    satisfied = any(
        kind in (registry[node.type].satisfies if node.type in registry else ())
        for node in iter_nodes(definition.steps)
    )
    if kind is AutomationKind.DATA_AI and not satisfied:
        satisfied = any(node.type.startswith(("data.", "ai.")) for node in iter_nodes(definition.steps))
    return [] if satisfied else [KIND_REQUIREMENTS[kind]]


def activation_problems(definition: AutomationDefinition, kind: AutomationKind) -> list[str]:
    errors = [
        (f"{issue.node_id}: " if issue.node_id and issue.node_id != "trigger" else "") + issue.message
        for issue in validate(definition)
        if issue.severity == "error"
    ]
    return errors + kind_problems(definition, kind)


def suggest_kind(definition: AutomationDefinition) -> AutomationKind:
    types = {node.type for node in iter_nodes(definition.steps)}
    if "approval.request" in types:
        return AutomationKind.APPROVAL
    if "email.send" in types:
        return AutomationKind.EMAIL
    if "ton.notify" in types:
        return AutomationKind.ALERT
    if any(t.startswith("ai.") for t in types):
        return AutomationKind.DATA_AI
    if definition.trigger.type != "trigger.manual":
        return AutomationKind.ROUTINE
    return AutomationKind.GENERAL


__all__ = ["Issue", "KIND_LABELS", "activation_problems", "kind_problems", "suggest_kind", "validate"]
