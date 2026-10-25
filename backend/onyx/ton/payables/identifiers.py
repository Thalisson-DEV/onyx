"""Normalization and validation of the identifiers a unit types.

Each function returns the canonical form or ``None`` when the input is not a
valid identifier, so the caller decides how to tell the person.
"""

import datetime
import re
import unicodedata

_PLATE = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
_NON_ALNUM = re.compile(r"[^A-Z0-9]")


def digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def _cpf_ok(number: str) -> bool:
    if len(number) != 11 or len(set(number)) == 1:
        return False
    for size in (9, 10):
        total = sum(int(number[i]) * (size + 1 - i) for i in range(size))
        check = (total * 10) % 11 % 10
        if check != int(number[size]):
            return False
    return True


def _cnpj_ok(number: str) -> bool:
    if len(number) != 14 or len(set(number)) == 1:
        return False
    weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for size in (12, 13):
        factors = weights if size == 12 else [6, *weights]
        total = sum(int(number[i]) * factors[i] for i in range(size))
        rest = total % 11
        check = 0 if rest < 2 else 11 - rest
        if check != int(number[size]):
            return False
    return True


def tax_id(value: str) -> str | None:
    """CPF (11 digits) or CNPJ (14 digits) with valid check digits."""
    number = digits(value)
    if len(number) == 11 and _cpf_ok(number):
        return number
    if len(number) == 14 and _cnpj_ok(number):
        return number
    return None


def format_tax_id(number: str) -> str:
    if len(number) == 11:
        return f"{number[:3]}.{number[3:6]}.{number[6:9]}-{number[9:]}"
    if len(number) == 14:
        return f"{number[:2]}.{number[2:5]}.{number[5:8]}/{number[8:12]}-{number[12:]}"
    return number


def plate(value: str) -> str | None:
    """A Brazilian plate (old or Mercosul) without hyphen or space."""
    candidate = _NON_ALNUM.sub("", value.upper())
    return candidate if _PLATE.match(candidate) else None


def document_key(value: str | None) -> str | None:
    """The document number as the duplicate check compares it.

    "NF 009151", "9151" and "9.151" are the same document; several numbers in
    one field ("113/114") keep their order.
    """
    if not value:
        return None
    text = value.strip().upper()
    # "9.151" is one number written with a thousands dot.
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")
    # Words such as "NF", "NFSE" or "REF" are not part of the number.
    parts = [
        part
        for part in re.findall(r"[0-9A-Z]+", text)
        if any(c.isdigit() for c in part)
    ]
    joined = "/".join(part.lstrip("0") or "0" for part in parts)
    return joined[:60] or None


def name_key(value: str) -> str:
    """Upper case, no accents, no company suffixes or punctuation."""
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Z0-9 ]", " ", text.upper())
    stop = {"LTDA", "ME", "EPP", "EIRELI", "SA", "S", "A", "CIA", "E", "DE", "DA", "DO"}
    return " ".join(word for word in text.split() if word not in stop)


def business_days_between(start: datetime.date, end: datetime.date) -> int:
    """Working days (Monday to Friday) after ``start`` up to ``end``.

    Negative when ``end`` is before ``start``. Holidays are not known here.
    """
    if end < start:
        return -business_days_between(end, start)
    count = 0
    day = start
    while day < end:
        day += datetime.timedelta(days=1)
        if day.weekday() < 5:
            count += 1
    return count
