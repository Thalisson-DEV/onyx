from decimal import Decimal

from onyx.ton.dre.derived import CAIXA, ECONOMICA, build, sync
from onyx.ton.dre.engine import calculation_order, evaluate_lines
from onyx.ton.dre.models import DreLineDefinition, DreLineType, DreOperation


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
    _nature("n3.01", "Combustível", 6, "g3"),
    _nature("n3.13", "Taxa adm central", 7, "g3"),
    _nature("n3.16", "Despesas financeiras", 8, "g3"),
    DreLineDefinition(
        code="r1",
        label="RESULTADO",
        position=9,
        line_type=DreLineType.RESULT,
        operation=DreOperation.SUM_LINES,
        operands=["g1", "g2", "g3"],
    ),
    _group("g4", "4 FINANCIAMENTO", 10),
    _nature("n4.01", "Financiamento", 11, "g4"),
    _group("g9", "NÃO GERENCIAIS", 12),
    _nature("n9.02", "Fundo fixo", 13, "g9"),
]
VALUES = {
    "n1.01": Decimal(1000),
    "n2.01": Decimal(-300),
    "n3.01": Decimal(-100),
    "n3.13": Decimal(-10),
    "n3.16": Decimal(-5),
    "n4.01": Decimal(-50000),
    "n9.02": Decimal(-20),
}


def _parents(lines: list[DreLineDefinition]) -> dict[str, str | None]:
    return {line.code: line.parent_code for line in lines}


def test_caixa_follows_the_controladoria_model() -> None:
    lines = build(CAIXA, BASE)
    calculation_order(lines)
    parents = _parents(lines)
    assert parents["n1.01"] == "s1"
    assert parents["n2.01"] == parents["n3.01"] == parents["n9.02"] == "s2"
    assert parents["n3.13"] == parents["n3.16"] == "s3"
    assert parents["n4.01"] == "s9"
    values = evaluate_lines(lines, VALUES)
    assert values["t1"] == Decimal(1000)
    assert values["t2"] == Decimal(1000 - 300 - 100 - 20)
    # Financing stays out of the result.
    assert values["r1"] == Decimal(1000 - 300 - 100 - 20 - 15)
    assert values["s9"] == Decimal(-50000)


def test_economica_puts_every_cost_in_one_block() -> None:
    lines = build(ECONOMICA, BASE)
    values = evaluate_lines(lines, VALUES)
    assert values["t1"] == Decimal(1000)
    assert values["s2"] == Decimal(-300 - 100 - 10 - 5 - 20)
    assert values["r1"] == Decimal(1000 - 435)


def test_sync_adds_new_natureza_with_its_siblings_and_keeps_moves() -> None:
    derived = build(CAIXA, BASE)
    # The Controladoria moved Combustível to Taxas in the derived structure.
    derived = [
        line.model_copy(update={"parent_code": "s3"}) if line.code == "n3.01" else line
        for line in derived
    ]
    base = [
        *BASE,
        _nature("n3.20", "Consultoria", 14, "g3"),
    ]
    base = [
        line.model_copy(update={"label": "Folha de pagamento"})
        if line.code == "n2.01"
        else line
        for line in base
        if line.code != "n9.02"
    ]
    synced = sync(CAIXA, derived, base)
    assert synced is not None
    calculation_order(synced)
    parents = _parents(synced)
    assert parents["n3.01"] == "s3"
    assert "n9.02" not in parents
    assert parents["n3.20"] in ("s2", "s3")
    assert next(line for line in synced if line.code == "n2.01").label == (
        "Folha de pagamento"
    )
    assert sync(CAIXA, synced, base) is None
