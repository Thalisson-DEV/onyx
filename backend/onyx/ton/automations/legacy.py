"""Convert e-mail flows (definition v1/v2) into automations v3.

v2 conditions on item fields split the items (matching ones go "Sim", the
rest "Não"); here that becomes "Filtrar lista" plus conditions on the
filtered lists. "Para cada unidade" becomes "Agrupar lista" by unit plus
"Para cada" over the groups, with the unit e-mail chosen by an expression.
A refused approval ends the run, as before."""

import re
from typing import Any

from onyx.ton.automations.definition import AutomationDefinition, unique_id
from onyx.ton.email_flows.catalog import TRIGGERS, TriggerKind
from onyx.ton.email_flows.steps import (
    UNIT_RECIPIENT_TOKEN,
    ApprovalStep,
    ConditionStep,
    FlowDefinitionV2,
    ForEachUnitStep,
    SendEmailStep,
    WaitStep,
)

_OPERATORS = {"EQ": "eq", "IN": "in", "GT": "gt", "GTE": "gte"}


def _quote(text: str) -> str:
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


class _Converter:
    def __init__(self, definition: FlowDefinitionV2) -> None:
        self.definition = definition
        self.taken: set[str] = set()

    def new_id(self, base: str) -> str:
        node_id = unique_id(base, self.taken)
        self.taken.add(node_id)
        return node_id

    def summary_left(self, field: str, items: str | None) -> str:
        if field == "itens":
            return f"{{{{ length({items}) }}}}" if items else "0"
        if field == "valor_total":
            return f"{{{{ sum({items}, 'valor') }}}}" if items else "0"
        return "{{ trigger.outputs.ultimo_mes }}"

    def rule(self, clause: Any, left: str) -> dict[str, Any]:
        value = clause.value
        right = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
        if isinstance(value, float) and value == int(value):
            right = str(int(value))
        return {"left": left, "operator": _OPERATORS.get(clause.operator.value, "eq"), "right": right}

    def steps(self, steps: list[Any], items: str | None, unit: dict[str, str] | None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for step in steps:
            result.extend(self.step(step, items, unit))
        return result

    def step(self, step: Any, items: str | None, unit: dict[str, str] | None) -> list[dict[str, Any]]:
        if isinstance(step, SendEmailStep):
            return [self.email(step, items, unit)]
        if isinstance(step, WaitStep):
            params: dict[str, Any] = (
                {"mode": "duration", "days": step.days, "hours": step.hours}
                if step.mode == "duration"
                else {"mode": "weekday", "weekday": str(step.weekday or 0), "time": step.time or "08:00"}
            )
            return [{"id": self.new_id("esperar"), "type": "control.wait", "label": step.label or "Esperar", "params": params}]
        if isinstance(step, ApprovalStep):
            approval_id = self.new_id("aprovacao")
            return [
                {
                    "id": approval_id,
                    "type": "approval.request",
                    "label": step.label or "Pedir aprovação",
                    "params": {
                        "approvers": step.approvers,
                        "title": "Aprovar o envio?",
                        "details": step.message,
                        "kind": "approve_reject",
                    },
                },
                {
                    "id": self.new_id("recusado"),
                    "type": "control.condition",
                    "label": "Foi recusado?",
                    "params": {"condition": {"op": "and", "rules": [{"left": f"{{{{ steps.{approval_id}.outputs.approved }}}}", "operator": "is_false", "right": ""}]}},
                    "then": [
                        {
                            "id": self.new_id("encerrar"),
                            "type": "control.terminate",
                            "label": "Encerrar",
                            "params": {"status": "cancelled", "message": "Aprovação recusada"},
                        }
                    ],
                    "else": [],
                },
            ]
        if isinstance(step, ForEachUnitStep):
            return self.for_each_unit(step, items)
        if isinstance(step, ConditionStep):
            return self.condition(step, items, unit)
        return []

    def email(self, step: SendEmailStep, items: str | None, unit: dict[str, str] | None) -> dict[str, Any]:
        def recipients(addresses: list[str]) -> list[str]:
            return [unit["email"] if address == UNIT_RECIPIENT_TOKEN and unit else address for address in addresses if address != UNIT_RECIPIENT_TOKEN or unit]

        body = step.body
        subject = step.subject
        if unit is not None:
            body = re.sub(r'data-variable="unidade"', 'data-expr="item.key"', body)
            subject = subject.replace("{unidade}", "{{ item.key }}")
        return {
            "id": self.new_id("email"),
            "type": "email.send",
            "label": step.label or "Enviar e-mail",
            "params": {
                "to": recipients(step.to),
                "cc": recipients(step.cc),
                "bcc": recipients(step.bcc),
                "subject": subject,
                "body": body,
                "items": f"{{{{ {items} }}}}" if items else "",
                "link": "/ton/classificacao" if self.definition.trigger.kind is TriggerKind.ACCOUNT_UNCLASSIFIED else "/ton/dre" if self.definition.trigger.kind is TriggerKind.DRE_RECALCULATED else "/ton/pendencias",
                "use_layout": step.use_layout,
            },
        }

    def for_each_unit(self, step: ForEachUnitStep, items: str | None) -> list[dict[str, Any]]:
        group_id = self.new_id("agrupar_unidades")
        loop_id = self.new_id("cada_unidade")
        email_id = self.new_id("email_da_unidade")
        expression = _quote(", ".join(step.default_emails))
        for entry in reversed(step.recipients):
            expression = f"if(lower(item.key) == {_quote(entry.unit.strip().lower())}, {_quote(', '.join(entry.emails))}, {expression})"
        inner = self.steps(step.steps, "item.items", {"email": f"{{{{ steps.{email_id}.outputs.value }}}}"})
        return [
            {
                "id": group_id,
                "type": "data.group",
                "label": "Agrupar por unidade",
                "params": {"items": f"{{{{ {items} }}}}" if items else "", "by": "unidade", "sum_field": "valor"},
            },
            {
                "id": loop_id,
                "type": "control.foreach",
                "label": step.label or "Para cada unidade",
                "params": {"items": f"{{{{ steps.{group_id}.outputs.groups }}}}"},
                "steps": [
                    {"id": email_id, "type": "data.compose", "label": "E-mail da unidade", "params": {"value": f"{{{{ {expression} }}}}"}},
                    *inner,
                ],
            },
        ]

    def condition(self, step: ConditionStep, items: str | None, unit: dict[str, str] | None) -> list[dict[str, Any]]:
        spec = TRIGGERS[self.definition.trigger.kind]
        item_clauses = []
        summary_clauses = []
        for clause in step.conditions:
            field = spec.field(clause.field)
            if field is not None and field.per_item:
                item_clauses.append(clause)
            else:
                summary_clauses.append(clause)
        label = step.label or "Condição"
        if not item_clauses:
            rules = [self.rule(clause, self.summary_left(clause.field, items)) for clause in summary_clauses]
            return [
                {
                    "id": self.new_id("condicao"),
                    "type": "control.condition",
                    "label": label,
                    "params": {"condition": {"op": "and", "rules": rules}},
                    "then": self.steps(step.then, items, unit),
                    "else": self.steps(step.otherwise, items, unit),
                }
            ]
        filter_id = self.new_id("filtrar")
        matched = f"steps.{filter_id}.outputs.items"
        rest = f"steps.{filter_id}.outputs.rest"
        nodes: list[dict[str, Any]] = [
            {
                "id": filter_id,
                "type": "data.filter",
                "label": "Separar os itens da condição",
                "params": {
                    "items": f"{{{{ {items} }}}}" if items else "",
                    "condition": {"op": "and", "rules": [self.rule(clause, f"{{{{ item.{clause.field} }}}}") for clause in item_clauses]},
                    "keep_rest": True,
                },
            },
            {
                "id": self.new_id("condicao"),
                "type": "control.condition",
                "label": label,
                "params": {
                    "condition": {
                        "op": "and",
                        "rules": [
                            {"left": f"{{{{ length({matched}) }}}}", "operator": "gt", "right": "0"},
                            *[self.rule(clause, self.summary_left(clause.field, matched)) for clause in summary_clauses],
                        ],
                    }
                },
                "then": self.steps(step.then, matched, unit),
                "else": [],
            },
        ]
        if step.otherwise:
            nodes.append(
                {
                    "id": self.new_id("senao"),
                    "type": "control.condition",
                    "label": "Itens que não atendem",
                    "params": {"condition": {"op": "and", "rules": [{"left": f"{{{{ length({rest}) }}}}", "operator": "gt", "right": "0"}]}},
                    "then": self.steps(step.otherwise, rest, unit),
                    "else": [],
                }
            )
        return nodes

    def run(self) -> AutomationDefinition:
        trigger = self.definition.trigger
        kind = trigger.kind
        prefix: list[dict[str, Any]] = []
        items: str | None
        if kind is TriggerKind.SCHEDULE:
            params: dict[str, Any] = {"frequency": "week" if trigger.frequency == "WEEKLY" else "day", "time": trigger.time or "08:00"}
            if trigger.frequency == "WEEKLY":
                params["weekdays"] = [trigger.weekday or 0]
            else:
                params["interval"] = 1
            new_trigger = {"type": "trigger.schedule", "params": params}
            fetch_id = self.new_id("inconsistencias")
            prefix.append({"id": fetch_id, "type": "ton.inconsistencies", "label": "Buscar inconsistências abertas", "params": {}})
            items = f"steps.{fetch_id}.outputs.items"
        elif kind is TriggerKind.NG_IMPORT_COMPLETED:
            new_trigger = {"type": "trigger.ng_import", "params": {}}
            items = "trigger.outputs.items"
        elif kind is TriggerKind.NG_OCCURRENCE_CHANGED:
            new_trigger = {"type": "trigger.ng_occurrence_changed", "params": {"changes": [change.value for change in trigger.changes]}}
            items = "trigger.outputs.items"
        elif kind is TriggerKind.ACCOUNT_UNCLASSIFIED:
            new_trigger = {"type": "trigger.account_unclassified", "params": {"skip_when_empty": False}}
            items = "trigger.outputs.items"
        else:
            new_trigger = {"type": "trigger.dre_recalculated", "params": {}}
            items = None
        steps = prefix + self.steps(self.definition.steps, items, None)
        return AutomationDefinition.model_validate(
            {
                "schema": 3,
                "trigger": new_trigger,
                "variables": [{"name": v.name, "type": "string", "value": v.value} for v in self.definition.variables],
                "steps": steps,
            }
        )


def convert(definition: dict[str, Any] | FlowDefinitionV2) -> AutomationDefinition:
    parsed = definition if isinstance(definition, FlowDefinitionV2) else FlowDefinitionV2.model_validate(definition)
    return _Converter(parsed).run()
