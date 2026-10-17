import pytest

from onyx.db.ton.account_classification import _with_new_group
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.dre.engine import calculation_order
from onyx.ton.dre.models import DreLineDefinition, DreLineType, DreOperation


def _lines() -> list[DreLineDefinition]:
    return [
        DreLineDefinition(
            code="g1",
            label="1 RECEITA",
            position=1,
            line_type=DreLineType.SUBTOTAL,
            operation=DreOperation.SUM_CHILDREN,
        ),
        DreLineDefinition(
            code="n1.01",
            label="Faturamento",
            position=2,
            parent_code="g1",
            line_type=DreLineType.SOURCE_SUM,
        ),
        DreLineDefinition(
            code="r1",
            label="RESULTADO",
            position=3,
            line_type=DreLineType.RESULT,
            operation=DreOperation.SUM_LINES,
            operands=["g1"],
        ),
        DreLineDefinition(
            code="g9",
            label="FORA DO RESULTADO",
            position=4,
            line_type=DreLineType.SUBTOTAL,
            operation=DreOperation.SUM_CHILDREN,
        ),
        DreLineDefinition(
            code="n9.01",
            label="Movimentos",
            position=5,
            parent_code="g9",
            line_type=DreLineType.SOURCE_SUM,
        ),
    ]


def _with_child(lines: list[DreLineDefinition], group: str) -> list[DreLineDefinition]:
    position = max(line.position for line in lines) + 1
    return [
        *lines,
        DreLineDefinition(
            code="n.new",
            label="Nova",
            position=position,
            parent_code=group,
            line_type=DreLineType.SOURCE_SUM,
        ),
    ]


def test_group_in_the_result_sits_above_the_total_and_joins_it() -> None:
    lines, group = _with_new_group(_lines(), "Investimento", True)
    by_code = {line.code: line for line in lines}
    assert group.code == "g10" and group.label == "INVESTIMENTO"
    assert by_code["g10"].position == 3
    assert by_code["r1"].position == 4
    assert by_code["r1"].operands == ["g1", "g10"]
    # Valid once the group has its first natureza.
    calculation_order(_with_child(lines, "g10"))


def test_group_out_of_the_result_goes_last_and_joins_no_total() -> None:
    lines, group = _with_new_group(_lines(), "mútuo", False)
    by_code = {line.code: line for line in lines}
    assert by_code[group.code].position == 6
    assert by_code["r1"].operands == ["g1"]


def test_an_existing_name_is_refused() -> None:
    with pytest.raises(OnyxError):
        _with_new_group(_lines(), "1 receita", True)
