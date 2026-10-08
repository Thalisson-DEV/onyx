"""Condition groups, as built in the condition editor: rules joined by
"e"/"ou", with nested groups. Each side of a rule is a template."""

from collections.abc import Mapping
from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from onyx.ton.automations.expressions import (
    _as_datetime,
    render,
    to_number,
    to_text,
    truthy,
)

Operator = Literal[
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "empty",
    "not_empty",
    "in",
    "not_in",
    "is_true",
    "is_false",
]

OPERATOR_LABELS: dict[str, str] = {
    "eq": "é igual a",
    "ne": "é diferente de",
    "gt": "é maior que",
    "gte": "é maior ou igual a",
    "lt": "é menor que",
    "lte": "é menor ou igual a",
    "contains": "contém",
    "not_contains": "não contém",
    "starts_with": "começa com",
    "ends_with": "termina com",
    "empty": "está vazio",
    "not_empty": "não está vazio",
    "in": "é um de",
    "not_in": "não é nenhum de",
    "is_true": "é verdadeiro",
    "is_false": "é falso",
}
UNARY_OPERATORS = {"empty", "not_empty", "is_true", "is_false"}
MAX_RULES = 20


class ConditionRule(BaseModel):
    left: Any = ""
    operator: Operator = "eq"
    right: Any = ""


class ConditionGroup(BaseModel):
    op: Literal["and", "or"] = "and"
    rules: list[Union["ConditionGroup", ConditionRule]] = Field(default_factory=list)

    def count(self) -> int:
        return sum(rule.count() if isinstance(rule, ConditionGroup) else 1 for rule in self.rules)


ConditionGroup.model_rebuild()


def parse_group(raw: Any) -> ConditionGroup:
    if isinstance(raw, ConditionGroup):
        return raw
    if not raw:
        return ConditionGroup()
    if isinstance(raw, Mapping) and "rules" not in raw and "left" in raw:
        return ConditionGroup(rules=[ConditionRule.model_validate(raw)])
    return ConditionGroup.model_validate(raw)


def _empty(value: Any) -> bool:
    return value is None or (isinstance(value, (str, list, dict, tuple)) and len(value) == 0) or (
        isinstance(value, str) and not value.strip()
    )


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [] if value is None else [value]


def compare(operator: str, left: Any, right: Any) -> bool:
    if operator == "empty":
        return _empty(left)
    if operator == "not_empty":
        return not _empty(left)
    if operator == "is_true":
        return truthy(left)
    if operator == "is_false":
        return not truthy(left)
    if operator in ("in", "not_in"):
        options = {to_text(option).strip().casefold() for option in _list(right)}
        inside = to_text(left).strip().casefold() in options
        return inside if operator == "in" else not inside
    if operator in ("contains", "not_contains"):
        if isinstance(left, (list, tuple)):
            target = to_text(right).strip().casefold()
            found = any(to_text(entry).strip().casefold() == target for entry in left)
        else:
            found = to_text(right).casefold() in to_text(left).casefold()
        return found if operator == "contains" else not found
    if operator == "starts_with":
        return to_text(left).casefold().startswith(to_text(right).casefold())
    if operator == "ends_with":
        return to_text(left).casefold().endswith(to_text(right).casefold())
    a, b = to_number(left), to_number(right)
    if operator in ("eq", "ne"):
        if a is not None and b is not None:
            equal = float(a) == float(b)
        else:
            equal = to_text(left).strip().casefold() == to_text(right).strip().casefold()
        return equal if operator == "eq" else not equal
    if a is None or b is None:
        left_date, right_date = _as_datetime(left), _as_datetime(right)
        if left_date is None or right_date is None:
            return False
        x, y = left_date.timestamp(), right_date.timestamp()
    else:
        x, y = float(a), float(b)
    return {"gt": x > y, "gte": x >= y, "lt": x < y, "lte": x <= y}[operator]


def evaluate_group(group: ConditionGroup, scope: Mapping[str, Any]) -> bool:
    """An empty group is true (no condition = always)."""
    if not group.rules:
        return True
    results = (
        evaluate_group(rule, scope)
        if isinstance(rule, ConditionGroup)
        else compare(rule.operator, render(rule.left, scope), render(rule.right, scope))
        for rule in group.rules
    )
    return all(results) if group.op == "and" else any(results)


def iter_rules(group: ConditionGroup) -> list[ConditionRule]:
    rules: list[ConditionRule] = []
    for rule in group.rules:
        if isinstance(rule, ConditionGroup):
            rules.extend(iter_rules(rule))
        else:
            rules.append(rule)
    return rules
