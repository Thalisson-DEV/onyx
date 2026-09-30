"""Synthetic DRE formula and period semantics."""

from decimal import Decimal

import pytest

from onyx.ton.dre.engine import calculate, calculation_order
from onyx.ton.dre.models import DreLineDefinition, DreLineType, DreOperation


def line(
    code: str,
    position: int,
    line_type: DreLineType = DreLineType.SOURCE_SUM,
    *,
    parent_code: str | None = None,
    operation: DreOperation | None = None,
    operands: list[str] | None = None,
) -> DreLineDefinition:
    return DreLineDefinition(
        code=code,
        label=code,
        position=position,
        line_type=line_type,
        parent_code=parent_code,
        operation=operation,
        operands=operands or [],
    )


def test_month_ytd_subtotals_variance_and_decimal_precision() -> None:
    lines = [
        line("revenue", 1, DreLineType.SUBTOTAL, operation=DreOperation.SUM_CHILDREN),
        line("service", 2, parent_code="revenue"),
        line("other", 3, parent_code="revenue"),
        line("cost", 4),
        line(
            "result",
            5,
            DreLineType.RESULT,
            operation=DreOperation.SUBTRACT,
            operands=["revenue", "cost"],
        ),
    ]
    values = calculate(
        lines,
        {
            1: {
                "service": Decimal("0.1000000000000000000000001"),
                "cost": Decimal("0.01"),
            },
            2: {
                "service": Decimal("10.20"),
                "other": Decimal("0.30"),
                "cost": Decimal("2.00"),
            },
        },
        {
            1: {"service": Decimal("1.00"), "cost": Decimal("0.50")},
            2: {
                "service": Decimal("10.00"),
                "other": Decimal("0.50"),
                "cost": Decimal("2.50"),
            },
        },
        2,
    )
    by_code = {item.code: item for item in values}
    assert by_code["revenue"].realizado == Decimal("10.50")
    assert by_code["revenue"].orcado == Decimal("10.50")
    assert by_code["result"].realizado == Decimal("8.50")
    assert by_code["result"].orcado == Decimal("8.00")
    assert by_code["result"].variance == Decimal("0.50")
    assert by_code["result"].variance_percent == Decimal("6.25")
    assert by_code["service"].realizado_ytd == Decimal("10.3000000000000000000000001")
    assert by_code["result"].variance_ytd == Decimal("0.0900000000000000000000001")


def test_zero_budget_percentage_is_not_applicable() -> None:
    result = calculate(
        [line("revenue", 1)],
        {1: {"revenue": Decimal("3")}},
        {},
        1,
    )[0]
    assert result.variance == Decimal("3")
    assert result.variance_percent is None
    assert result.variance_percent_ytd is None


def test_only_months_in_requested_year_are_passed_to_engine() -> None:
    result = calculate(
        [line("revenue", 1)],
        {1: {"revenue": Decimal("2")}, 12: {"revenue": Decimal("99")}},
        {1: {"revenue": Decimal("1")}},
        1,
    )[0]
    assert result.realizado_ytd == 2
    assert result.orcado_ytd == 1


@pytest.mark.parametrize(
    "lines",
    [
        [
            line(
                "a",
                1,
                DreLineType.RESULT,
                operation=DreOperation.SUM_LINES,
                operands=["missing"],
            )
        ],
        [
            line(
                "a",
                1,
                DreLineType.RESULT,
                operation=DreOperation.SUM_LINES,
                operands=["b"],
            ),
            line(
                "b",
                2,
                DreLineType.RESULT,
                operation=DreOperation.SUM_LINES,
                operands=["a"],
            ),
        ],
        [line("a", 1, parent_code="b"), line("b", 2, parent_code="a")],
    ],
)
def test_invalid_dependencies_are_rejected(lines: list[DreLineDefinition]) -> None:
    with pytest.raises(ValueError):
        calculation_order(lines)


def test_ratio_zero_denominator_blocks_calculation() -> None:
    lines = [
        line("revenue", 1),
        line("cost", 2),
        line(
            "ratio",
            3,
            DreLineType.PERCENTAGE,
            operation=DreOperation.RATIO,
            operands=["revenue", "cost"],
        ),
    ]
    with pytest.raises(ValueError, match="denominator"):
        calculate(lines, {1: {"revenue": Decimal("5")}}, {}, 1)


def test_ratio_uses_percentage_scale() -> None:
    lines = [
        line("revenue", 1),
        line("cost", 2),
        line(
            "ratio",
            3,
            DreLineType.PERCENTAGE,
            operation=DreOperation.RATIO,
            operands=["revenue", "cost"],
        ),
    ]
    result = calculate(
        lines,
        {1: {"revenue": Decimal("1"), "cost": Decimal("4")}},
        {1: {"revenue": Decimal("1"), "cost": Decimal("2")}},
        1,
    )
    assert result[2].realizado == Decimal("25")
    assert result[2].orcado == Decimal("50")


def test_ytd_ratio_uses_cumulative_operands() -> None:
    lines = [
        line("revenue", 1),
        line("cost", 2),
        line(
            "ratio",
            3,
            DreLineType.PERCENTAGE,
            operation=DreOperation.RATIO,
            operands=["revenue", "cost"],
        ),
    ]
    result = calculate(
        lines,
        {
            1: {"revenue": Decimal("1"), "cost": Decimal("4")},
            2: {"revenue": Decimal("9"), "cost": Decimal("6")},
        },
        {
            1: {"revenue": Decimal("1"), "cost": Decimal("2")},
            2: {"revenue": Decimal("3"), "cost": Decimal("2")},
        },
        2,
    )[2]
    assert result.realizado == Decimal("150")
    assert result.realizado_ytd == Decimal("100")
    assert result.orcado_ytd == Decimal("100")


def test_large_decimal_input_keeps_full_intermediate_precision() -> None:
    amount = Decimal("123456789012345.1234567890123456789012345")
    result = calculate([line("source", 1)], {1: {"source": amount}}, {}, 1)[0]
    assert result.realizado == amount
