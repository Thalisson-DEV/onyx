"""Edits the chat proposes on a derived DRE (Caixa, Econômica) and the
percentage lines of the Controladoria's model (taxa adm 2%, contingência 1%)."""

from decimal import Decimal
from uuid import uuid4

import pytest

from onyx.db.ton.dre_line_sources import billing_fields_text, billing_share
from onyx.ton.agent.structure_ops import LineOperation, apply_operations
from onyx.ton.dre.derived import CAIXA, build, sync
from onyx.ton.dre.engine import calculation_order, evaluate_lines
from onyx.ton.dre.models import (
    BillingField,
    DreLineDefinition,
    DreLineSource,
    DreLineType,
    DreOperation,
)


def _group(code: str, label: str, position: int) -> DreLineDefinition:
    return DreLineDefinition(
        code=code,
        label=label,
        position=position,
        line_type=DreLineType.SUBTOTAL,
        operation=DreOperation.SUM_CHILDREN,
    )


def _nature(code: str, label: str, position: int, parent: str) -> DreLineDefinition:
    return DreLineDefinition(
        code=code,
        label=label,
        position=position,
        parent_code=parent,
        line_type=DreLineType.SOURCE_SUM,
    )


BASE = [
    _group("g1", "1 RECEITA", 1),
    _nature("n1.01", "Faturamento", 2, "g1"),
    _group("g2", "2 MÃO DE OBRA", 3),
    _nature("n2.01", "Folha", 4, "g2"),
    _group("g3", "3 OPERACIONAIS", 5),
    _nature("n3.13", "Taxa adm central", 6, "g3"),
    DreLineDefinition(
        code="r1",
        label="RESULTADO",
        position=7,
        line_type=DreLineType.RESULT,
        operation=DreOperation.SUM_LINES,
        operands=["g1", "g2", "g3"],
    ),
]


def _caixa_with_gross_billing() -> list[DreLineDefinition]:
    """DRE Caixa after the chat added gross billing, its taxes group and the
    taxa de administração as 2% of the invoices."""
    caixa = build(CAIXA, BASE)
    edit = apply_operations(
        caixa,
        [],
        [
            LineOperation(
                op="add_group",
                label="IMPOSTOS S/ FATURAMENTO",
                after_code="s1",
            ),
            LineOperation(
                op="add_line",
                label="PIS (1% da NF)",
                parent_code="x1",
                source=DreLineSource.BILLING,
                billing_fields=[BillingField.SERVICE_AMOUNT],
                billing_percent=Decimal(1),
                negate=True,
            ),
            LineOperation(
                op="add_line",
                label="Taxa adm (2% da NF)",
                parent_code="s3",
                source=DreLineSource.BILLING,
                billing_fields=[BillingField.SERVICE_AMOUNT],
                billing_percent=Decimal(2),
                negate=True,
            ),
            LineOperation(op="set_formula", code="t1", operation=DreOperation.SUM_LINES, operands=["s1", "x1", "m1"]),
            LineOperation(op="set_line_source", code="m2", source=DreLineSource.ADJUSTMENT, negate=True),
        ],
        {},
        derived=True,
    )
    return edit.lines


def test_derived_edits_use_own_codes_and_percentages() -> None:
    lines = _caixa_with_gross_billing()
    calculation_order(lines)
    by_code = {line.code: line for line in lines}
    assert by_code["x1"].label == "IMPOSTOS S/ FATURAMENTO"
    assert by_code["x2"].billing_percent == Decimal(1)
    assert by_code["x3"].parent_code == "s3"
    assert by_code["m2"].source == DreLineSource.ADJUSTMENT
    values = evaluate_lines(
        lines,
        {"n1.01": Decimal(1000), "x2": Decimal(-10), "x3": Decimal(-20), "n2.01": Decimal(-300)},
    )
    assert values["t1"] == Decimal(990)
    assert values["s3"] == Decimal(-20)


def test_sync_keeps_the_lines_the_controladoria_added_to_a_derived_dre() -> None:
    lines = _caixa_with_gross_billing()
    base = [*BASE, _nature("n3.20", "Consultoria", 8, "g3")]
    synced = sync(CAIXA, lines, base)
    assert synced is not None
    codes = {line.code for line in synced}
    assert {"x1", "x2", "x3", "n3.20"} <= codes
    assert sync(CAIXA, synced, base) is None


@pytest.mark.parametrize(
    "operation,message",
    [
        (LineOperation(op="move_nature", nature_code="1.01", target_code="n2.01"), "seguem a DRE Gerencial"),
        (LineOperation(op="rename_line", code="n1.01", label="Receita"), "segue a DRE Gerencial"),
        (LineOperation(op="remove_line", code="n2.01"), "segue a DRE Gerencial"),
        (LineOperation(op="add_line", label="Nova natureza", parent_code="s2"), "lê faturamento"),
    ],
)
def test_derived_dre_leaves_natureza_changes_to_the_managerial(
    operation: LineOperation, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        apply_operations(build(CAIXA, BASE), [], [operation], {"1.01": uuid4()}, derived=True)


def test_derived_dre_still_moves_and_excludes_naturezas() -> None:
    edit = apply_operations(
        build(CAIXA, BASE),
        [],
        [
            LineOperation(op="move_line", code="n3.13", parent_code="s2", after_code="n2.01"),
            LineOperation(op="exclude_line", code="n2.01"),
        ],
        {},
        derived=True,
    )
    by_code = {line.code: line for line in edit.lines}
    assert by_code["n3.13"].parent_code == "s2"
    assert by_code["n2.01"].excluded


def test_billing_percentage_takes_its_share_of_the_invoice() -> None:
    line = DreLineDefinition(
        code="x3",
        label="Contingências",
        position=1,
        parent_code="s3",
        line_type=DreLineType.SOURCE_SUM,
        source=DreLineSource.BILLING,
        billing_fields=[BillingField.SERVICE_AMOUNT],
        billing_percent=Decimal("1"),
        negate=True,
    )
    assert billing_share(Decimal("12345.60"), line) == Decimal("-123.456")
    assert billing_fields_text(line) == "1% de valor do serviço (bruto)"
    # Stored as JSON and read back unchanged.
    again = DreLineDefinition.model_validate(line.model_dump(mode="json"))
    assert again.billing_percent == Decimal(1)


def test_percentage_only_on_billing_lines() -> None:
    with pytest.raises(ValueError):
        DreLineDefinition(
            code="x1",
            label="Errada",
            position=1,
            line_type=DreLineType.SOURCE_SUM,
            source=DreLineSource.ADJUSTMENT,
            billing_percent=Decimal(2),
        )


def test_a_group_left_out_of_every_total_is_flagged() -> None:
    from onyx.db.ton.agent_actions import _loose_warnings
    from onyx.ton.dre.models import DreResultLineView

    caixa = build(CAIXA, BASE)
    edit = apply_operations(
        caixa,
        [],
        [
            LineOperation(op="add_group", label="IMPOSTOS S/ FATURAMENTO", after_code="s1"),
            LineOperation(
                op="add_line",
                label="PIS",
                parent_code="x1",
                source=DreLineSource.BILLING,
                billing_fields=[BillingField.SERVICE_AMOUNT],
                billing_percent=Decimal(1),
                negate=True,
            ),
        ],
        {},
        derived=True,
    )
    values = [
        DreResultLineView.model_construct(code="x1", realizado=Decimal("-122982.54")),
        DreResultLineView.model_construct(code="s9", realizado=Decimal("512507.22")),
    ]
    warnings = _loose_warnings(caixa, edit.lines, values)
    assert len(warnings) == 1
    assert "IMPOSTOS S/ FATURAMENTO" in warnings[0] and "x1" in warnings[0]
