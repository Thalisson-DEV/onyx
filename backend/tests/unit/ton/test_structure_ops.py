from decimal import Decimal
from uuid import uuid4

import pytest

from onyx.ton.agent.structure_ops import LineOperation, apply_operations
from onyx.ton.dre.engine import evaluate_lines
from onyx.ton.dre.models import (
    BillingField,
    DreAccountAssignment,
    DreLineDefinition,
    DreLineSource,
    DreLineType,
    DreOperation,
)

REVENUE_ACCOUNT = uuid4()
PAYROLL_ACCOUNT = uuid4()
ACCOUNTS = {"1.01": REVENUE_ACCOUNT, "2.01": PAYROLL_ACCOUNT}

LINES = [
    DreLineDefinition(
        code="g1",
        label="1 RECEITA LÍQUIDA",
        position=0,
        line_type=DreLineType.SUBTOTAL,
        operation=DreOperation.SUM_CHILDREN,
    ),
    DreLineDefinition(
        code="n1.01",
        label="Faturamento (NG)",
        position=1,
        parent_code="g1",
        line_type=DreLineType.SOURCE_SUM,
    ),
    DreLineDefinition(
        code="n1.02",
        label="Impostos s/faturamento",
        position=2,
        parent_code="g1",
        line_type=DreLineType.SOURCE_SUM,
    ),
    DreLineDefinition(
        code="g2",
        label="2 CUSTOS",
        position=3,
        line_type=DreLineType.SUBTOTAL,
        operation=DreOperation.SUM_CHILDREN,
    ),
    DreLineDefinition(
        code="n2.01",
        label="Folha",
        position=4,
        parent_code="g2",
        line_type=DreLineType.SOURCE_SUM,
    ),
    DreLineDefinition(
        code="r1",
        label="RESULTADO",
        position=5,
        line_type=DreLineType.RESULT,
        operation=DreOperation.SUM_LINES,
        operands=["g1", "g2"],
    ),
]
ASSIGNMENTS = [
    DreAccountAssignment(account_id=REVENUE_ACCOUNT, line_code="n1.01", status="APPROVED"),
    DreAccountAssignment(account_id=PAYROLL_ACCOUNT, line_code="n2.01", status="APPROVED"),
]


def _codes(lines: list[DreLineDefinition]) -> list[str]:
    return [line.code for line in sorted(lines, key=lambda line: line.position)]


def test_gross_billing_with_retentions_replaces_the_ng_revenue() -> None:
    edit = apply_operations(
        LINES,
        ASSIGNMENTS,
        [
            LineOperation(
                op="add_line",
                label="Faturamento bruto",
                parent_code="g1",
                after_code="g1",
                source=DreLineSource.BILLING,
                billing_fields=[BillingField.SERVICE_AMOUNT],
            ),
            LineOperation(
                op="add_line",
                label="Retenções",
                parent_code="g1",
                after_code="a1",
                source=DreLineSource.BILLING,
                billing_fields=[BillingField.TOTAL_RETAINED],
                negate=True,
            ),
            LineOperation(op="exclude_line", code="n1.01"),
        ],
        ACCOUNTS,
    )
    assert _codes(edit.lines) == ["g1", "a1", "a2", "n1.01", "n1.02", "g2", "n2.01", "r1"]
    values = evaluate_lines(
        edit.lines,
        {
            "a1": Decimal(100),
            "a2": Decimal(-12),
            "n1.01": Decimal(88),
            "n2.01": Decimal(-50),
        },
    )
    # The NG net revenue stays visible but out of the result: no double count.
    assert values["g1"] == Decimal(88)
    assert values["r1"] == Decimal(38)
    assert edit.assignments == sorted(ASSIGNMENTS, key=lambda item: str(item.account_id))


def test_move_nature_and_remove_the_empty_line() -> None:
    edit = apply_operations(
        LINES,
        ASSIGNMENTS,
        [
            LineOperation(op="move_nature", nature_code="1.01", target_code="n1.02"),
            LineOperation(op="remove_line", code="n1.01"),
            LineOperation(op="rename_line", code="n1.02", label="Receita NG"),
        ],
        ACCOUNTS,
    )
    assert "n1.01" not in _codes(edit.lines)
    revenue = next(item for item in edit.assignments if item.account_id == REVENUE_ACCOUNT)
    assert revenue.line_code == "n1.02"
    assert next(line for line in edit.lines if line.code == "n1.02").label == "Receita NG"


def test_move_group_keeps_its_children_together() -> None:
    edit = apply_operations(
        LINES,
        ASSIGNMENTS,
        [LineOperation(op="move_line", code="g2", after_code="r1")],
        ACCOUNTS,
    )
    assert _codes(edit.lines) == ["g1", "n1.01", "n1.02", "r1", "g2", "n2.01"]


@pytest.mark.parametrize(
    "operation, message",
    [
        (LineOperation(op="remove_line", code="n1.01"), "naturezas"),
        (LineOperation(op="remove_line", code="g1"), "ainda tem linhas"),
        (
            LineOperation(
                op="set_line_source",
                code="n1.01",
                source=DreLineSource.ADJUSTMENT,
            ),
            "mova-as antes",
        ),
        (LineOperation(op="exclude_line", code="g1"), "dentro de um grupo"),
        (LineOperation(op="add_line", label="X", parent_code="n1.01"), "não é um grupo"),
        (LineOperation(op="move_nature", nature_code="9.99", target_code="n1.02"), "não existe"),
    ],
)
def test_edits_that_do_not_fit_are_refused(operation: LineOperation, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        apply_operations(LINES, ASSIGNMENTS, [operation], ACCOUNTS)


def test_billing_line_needs_fields() -> None:
    with pytest.raises(ValueError):
        apply_operations(
            LINES,
            ASSIGNMENTS,
            [
                LineOperation(
                    op="add_line",
                    label="Bruto",
                    parent_code="g1",
                    source=DreLineSource.BILLING,
                )
            ],
            ACCOUNTS,
        )
