"""Check that money amounts in an assistant answer come from persisted data.

An amount is grounded when it equals, at the precision the answer shows, a
value the TON tools returned or a line of the persisted DRE statement. Only
amounts written as money ("R$ 1.234,56", "R$ 10,4 milhões", "4,2 mi") count;
counts and percentages are not checked.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

SCALES = {
    "mil": Decimal(1_000),
    "mi": Decimal(1_000_000),
    "milhao": Decimal(1_000_000),
    "milhão": Decimal(1_000_000),
    "milhoes": Decimal(1_000_000),
    "milhões": Decimal(1_000_000),
    "bi": Decimal(1_000_000_000),
    "bilhao": Decimal(1_000_000_000),
    "bilhão": Decimal(1_000_000_000),
    "bilhoes": Decimal(1_000_000_000),
    "bilhões": Decimal(1_000_000_000),
}
_NUMBER = r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
_SCALE = r"(?:\s*(" + "|".join(sorted(SCALES, key=len, reverse=True)) + r")\b)?"
MONEY = re.compile(r"(-\s*)?R\$\s*(-\s*)?" + _NUMBER + _SCALE, re.IGNORECASE)
SCALED = re.compile(
    r"(?<![\w$,.])(-\s*)?"
    + _NUMBER
    + r"\s*("
    + "|".join(sorted(SCALES, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


class CitedAmount:
    def __init__(self, text: str, value: Decimal, step: Decimal) -> None:
        self.text = text
        self.value = value
        # Half of the last shown digit: "10,4 milhões" covers 10.35–10.45 mi.
        self.tolerance = step / 2

    def matches(self, expected: Decimal) -> bool:
        return abs(abs(expected) - abs(self.value)) <= self.tolerance


def _parse(number: str, scale: str | None) -> tuple[Decimal, Decimal]:
    integer, _, fraction = number.replace(".", "").partition(",")
    try:
        value = Decimal(f"{integer}.{fraction}" if fraction else integer)
    except InvalidOperation:
        return Decimal(0), Decimal(0)
    multiplier = SCALES[scale.lower()] if scale else Decimal(1)
    step = Decimal(1).scaleb(-len(fraction)) * multiplier
    return value * multiplier, step


def cited_amounts(answer: str) -> list[CitedAmount]:
    found: list[CitedAmount] = []
    spans: list[tuple[int, int]] = []
    for match in MONEY.finditer(answer):
        value, step = _parse(match.group(3), match.group(4))
        found.append(CitedAmount(match.group(0).strip(), value, step))
        spans.append(match.span())
    for match in SCALED.finditer(answer):
        if any(start <= match.start() < end for start, end in spans):
            continue
        value, step = _parse(match.group(2), match.group(3))
        found.append(CitedAmount(match.group(0).strip(), value, step))
    return [item for item in found if item.value]


def numbers_in(data: Any) -> set[Decimal]:
    """Every number in a tool payload, including numeric strings like '10409196.48'."""
    values: set[Decimal] = set()
    if isinstance(data, dict):
        for item in data.values():
            values |= numbers_in(item)
    elif isinstance(data, list):
        for item in data:
            values |= numbers_in(item)
    elif isinstance(data, bool):
        pass
    elif isinstance(data, (int, float)):
        values.add(Decimal(str(data)))
    elif isinstance(data, str) and re.fullmatch(r"-?\d+(\.\d+)?", data):
        values.add(Decimal(data))
    return values


def ungrounded(answer: str, expected: set[Decimal]) -> list[str]:
    """Amounts cited in the answer that match no expected value."""
    return [
        amount.text
        for amount in cited_amounts(answer)
        if not any(amount.matches(value) for value in expected)
    ]
