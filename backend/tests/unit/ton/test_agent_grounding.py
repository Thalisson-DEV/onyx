from decimal import Decimal
from uuid import uuid4

from onyx.db.ton.agent_overview import resolve_unit
from onyx.ton.agent.grounding import cited_amounts, numbers_in, ungrounded
from onyx.ton.agent.models import UnitContext

UNITS = [
    UnitContext(unit_id=uuid4(), code=code, name=name)
    for code, name in (
        ("000009", "MOSSORÓ-RN"),
        ("000027", "MOSSORO ATERRO"),
        ("000002", "JUAZEIRO-BA"),
        ("000026", "JUAZEIRO DO NORTE"),
        ("000005", "SENTO SÉ-BA"),
    )
]


def _names(wanted: str) -> list[str]:
    return [unit.name for unit in resolve_unit(UNITS, wanted)]


def test_unit_resolves_by_name_code_and_without_accents() -> None:
    assert _names("Mossoró-RN") == ["MOSSORÓ-RN"]
    assert _names("mossoro rn") == ["MOSSORÓ-RN"]
    assert _names("000027") == ["MOSSORO ATERRO"]
    assert _names("sento se") == ["SENTO SÉ-BA"]


def test_unit_ambiguous_or_unknown_is_not_guessed() -> None:
    assert _names("Juazeiro") == ["JUAZEIRO-BA", "JUAZEIRO DO NORTE"]
    assert _names("Mossoró") == ["MOSSORÓ-RN", "MOSSORO ATERRO"]
    assert _names("Natal") == []


def test_cited_amounts_read_brazilian_money_formats() -> None:
    amounts = cited_amounts(
        "Receita de R$ 10.409.196,48, custos de R$ -4,57 milhões e resultado de 318 mil; 33 linhas."
    )
    assert [item.value for item in amounts] == [
        Decimal("10409196.48"),
        Decimal("4570000"),
        Decimal("318000"),
    ]


def test_rounded_amount_matches_at_shown_precision() -> None:
    expected = {Decimal("10409196.48"), Decimal("-317988.55")}
    assert (
        ungrounded("Receita de R$ 10,4 milhões; resultado de R$ -318 mil.", expected)
        == []
    )
    assert ungrounded("Receita de R$ 10,5 milhões.", expected) == ["R$ 10,5 milhões"]


def test_numbers_in_tool_payload_include_numeric_strings() -> None:
    payload = {"linhas_dre": [{"realizado": "-317988.55"}], "quantidade": 3, "ok": True}
    assert numbers_in(payload) == {Decimal("-317988.55"), Decimal(3)}
