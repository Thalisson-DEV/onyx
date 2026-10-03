"""Pure DRE formula evaluation. All amounts remain Decimal."""

from collections import defaultdict
from decimal import Decimal, localcontext

from onyx.ton.dre.models import DreLineDefinition, DreOperation, DreResultLineView

ENGINE_VERSION = "data005ab-1"
ZERO = Decimal(0)


def calculation_order(lines: list[DreLineDefinition]) -> list[DreLineDefinition]:
    by_code = {line.code: line for line in lines}
    if len(by_code) != len(lines) or len({line.position for line in lines}) != len(
        lines
    ):
        raise ValueError("DRE line codes and positions must be unique")
    children: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        if line.parent_code is not None:
            if line.parent_code not in by_code or line.parent_code == line.code:
                raise ValueError("Invalid DRE parent")
            children[line.parent_code].append(line.code)
    for line in lines:
        ancestors: set[str] = set()
        parent = line.parent_code
        while parent is not None:
            if parent in ancestors or parent == line.code:
                raise ValueError("DRE hierarchy has a cycle")
            ancestors.add(parent)
            parent = by_code[parent].parent_code
    for line in lines:
        if line.operation == DreOperation.SUM_CHILDREN and not children[line.code]:
            raise ValueError("SUM_CHILDREN requires direct children")
        dependencies = (
            children[line.code]
            if line.operation == DreOperation.SUM_CHILDREN
            else line.operands
        )
        if any(code not in by_code for code in dependencies):
            raise ValueError("DRE formula references a missing line")
    ordered: list[DreLineDefinition] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(code: str) -> None:
        if code in visiting:
            raise ValueError("DRE formula or hierarchy has a cycle")
        if code in visited:
            return
        visiting.add(code)
        line = by_code[code]
        dependencies = (
            children[code]
            if line.operation == DreOperation.SUM_CHILDREN
            else line.operands
        )
        for dependency in dependencies:
            visit(dependency)
        visiting.remove(code)
        visited.add(code)
        ordered.append(line)

    for line in sorted(lines, key=lambda item: (item.position, item.code)):
        visit(line.code)
    return ordered


def _evaluate(
    ordered: list[DreLineDefinition], source: dict[str, Decimal]
) -> dict[str, Decimal]:
    result = _evaluate_lenient(ordered, source)
    if any(value is None for value in result.values()):
        raise ValueError("DRE ratio denominator is zero")
    return {code: value for code, value in result.items() if value is not None}


def _evaluate_lenient(
    ordered: list[DreLineDefinition], source: dict[str, Decimal]
) -> dict[str, Decimal | None]:
    """Evaluate every line; a ratio over zero, and lines using it, give None."""
    children: dict[str, list[str]] = defaultdict(list)
    for line in ordered:
        if line.parent_code is not None:
            children[line.parent_code].append(line.code)
    result: dict[str, Decimal | None] = {}
    for line in ordered:
        if line.operation is None:
            result[line.code] = source.get(line.code, ZERO)
            continue
        operands = (
            children[line.code]
            if line.operation == DreOperation.SUM_CHILDREN
            else line.operands
        )
        values = [result[code] for code in operands]
        if any(value is None for value in values):
            result[line.code] = None
            continue
        present = [value for value in values if value is not None]
        if line.operation in (DreOperation.SUM_CHILDREN, DreOperation.SUM_LINES):
            result[line.code] = sum(present, ZERO)
        elif line.operation == DreOperation.SUBTRACT:
            result[line.code] = present[0] - present[1]
        elif not present[1]:
            result[line.code] = None
        else:
            result[line.code] = present[0] / present[1] * 100
    return result


def evaluate_lines(
    lines: list[DreLineDefinition], source: dict[str, Decimal]
) -> dict[str, Decimal | None]:
    """Line values for one set of source sums, without the readiness checks."""
    with localcontext() as context:
        context.prec = 100
        return _evaluate_lenient(calculation_order(lines), source)


def _percentage(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    return numerator / denominator * 100 if denominator else None


def calculate(
    lines: list[DreLineDefinition],
    actual_by_period: dict[int, dict[str, Decimal]],
    budget_by_period: dict[int, dict[str, Decimal]],
    month: int,
) -> list[DreResultLineView]:
    with localcontext() as context:
        context.prec = 100
        return _calculate(lines, actual_by_period, budget_by_period, month)


def _calculate(
    lines: list[DreLineDefinition],
    actual_by_period: dict[int, dict[str, Decimal]],
    budget_by_period: dict[int, dict[str, Decimal]],
    month: int,
) -> list[DreResultLineView]:
    ordered = calculation_order(lines)
    actual_month = _evaluate(ordered, actual_by_period.get(month, {}))
    budget_month = _evaluate(ordered, budget_by_period.get(month, {}))
    actual_source_ytd: dict[str, Decimal] = defaultdict(Decimal)
    budget_source_ytd: dict[str, Decimal] = defaultdict(Decimal)
    for current_month in range(1, month + 1):
        for code, amount in actual_by_period.get(current_month, {}).items():
            actual_source_ytd[code] += amount
        for code, amount in budget_by_period.get(current_month, {}).items():
            budget_source_ytd[code] += amount
    actual_ytd = _evaluate(ordered, actual_source_ytd)
    budget_ytd = _evaluate(ordered, budget_source_ytd)
    result: list[DreResultLineView] = []
    for line in sorted(lines, key=lambda item: item.position):
        actual = actual_month[line.code]
        budget = budget_month[line.code]
        ytd_actual = actual_ytd[line.code]
        ytd_budget = budget_ytd[line.code]
        result.append(
            DreResultLineView(
                code=line.code,
                label=line.label,
                position=line.position,
                realizado=actual,
                orcado=budget,
                variance=actual - budget,
                variance_percent=_percentage(actual - budget, budget),
                realizado_ytd=ytd_actual,
                orcado_ytd=ytd_budget,
                variance_ytd=ytd_actual - ytd_budget,
                variance_percent_ytd=_percentage(ytd_actual - ytd_budget, ytd_budget),
            )
        )
    return result
