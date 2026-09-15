"""``ton-canon-1`` — the canonical serialisation TON hashes (Plan 003d).

Readiness §12 required the canonicalisation to be decided *before* any hash is
computed, and named the contract: RFC 8785 JSON Canonicalization Scheme as the
base — UTF-8, no insignificant whitespace, lexicographic key ordering — with four
TON domain rules layered on top.

1. **Money, quantities and percentages serialise as decimal strings, never JSON
   numbers.** This is the load-bearing rule. Prompt Mestre §6 exists because
   arithmetic in this data is already wrong by cents, and an IEEE-754 round-trip
   would make a published amount irreproducible across platforms. A ``float``
   is therefore *rejected*, never coerced: ``0.1 + 0.2`` must not be allowed to
   become a supposedly exact decimal.
2. **Timestamps are RFC 3339 UTC with an explicit ``Z``**, at a fixed
   microsecond precision, so two spellings of one instant cannot differ.
3. **Absent keys are omitted, never emitted as ``null``.** One representation
   only, or two semantically identical payloads hash differently.
4. **Enums serialise as their ``.value`` string**, matching the repository's
   ``native_enum=False`` convention.

Two further rules this module adds, because the four above do not by themselves
make the bytes unique:

5. **Strings are Unicode NFC.** RFC 8785 fixes escaping but not composition, so
   without this the same visible text can produce two digests.
   :mod:`onyx.db.ton.identity` already set the NFC precedent for identity keys.
6. **A bare ``Decimal`` is normalised, a declared scale is honoured.**
   ``Decimal("10.5")`` and ``Decimal("10.50")`` are the same number and must
   hash alike, so a bare ``Decimal`` drops trailing fractional zeros. When the
   *published* scale is itself part of the contract — an amount at the scale its
   ``RuleVersion`` declared — wrap it in :class:`ScaledDecimal` and the
   representation is fixed at that scale instead.

The version string is carried in the payload and persisted alongside every hash
(``TonReportRevision.canonicalization_version``,
``TonReportRevision.hash_algorithm``), so changing either later cannot
invalidate a hash already recorded.

Nothing here touches a database, a session or the network. It is pure, which is
what lets a test assert the serialisation rather than only the digest.
"""

from __future__ import annotations

import datetime
import hashlib
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, Inexact, InvalidOperation, localcontext
from enum import Enum
from typing import Any
from uuid import UUID

# Bumped only if the serialisation below changes. Persisted as data on every
# revision, so an old hash stays verifiable under the scheme that produced it.
CANONICALIZATION_VERSION = "ton-canon-1"

# Readiness §12 specifies SHA-256. Stored as data for the same reason as the
# version above.
HASH_ALGORITHM = "sha256"

# Fixed, not "as supplied": emitting a variable number of fractional digits would
# let 12:00:00 and 12:00:00.000000 be two payloads for one instant.
TIMESTAMP_FRACTIONAL_DIGITS = 6

# The widest scale the TON numeric columns can hold — ``TON_AMOUNT`` is
# ``NUMERIC(30, 10)``. A declared scale beyond it could not survive a round trip
# through the database, so it is refused here rather than silently truncated.
MAX_DECIMAL_SCALE = 10

# RFC 8785 §3.2.2.2: only these two characters and the C0 controls are escaped,
# and the five named short forms are mandatory where they exist.
_STRING_ESCAPES: dict[str, str] = {
    "\u0008": "\\b",
    "\u0009": "\\t",
    "\u000a": "\\n",
    "\u000c": "\\f",
    "\u000d": "\\r",
    '"': '\\"',
    "\\": "\\\\",
}


@dataclass(frozen=True)
class ScaledDecimal:
    """A business decimal together with the scale it is published at.

    Use this wherever the scale is part of the contract rather than an accident
    of construction — a monetary amount at the scale its ``RuleVersion``
    declared, a percentage, a quantity with exact decimal semantics. The
    canonical form then has exactly ``scale`` fractional digits, so an amount
    published as ``10.50`` never canonicalises as ``10.5``.

    Refusing to round is deliberate. A value carrying more precision than the
    declared scale is a caller defect, not something to quietly discard: dropping
    a digit off a published figure is exactly the class of error Prompt Mestre §6
    is about. Trailing zeros are padded, because that is lossless.
    """

    value: Decimal
    scale: int

    def __post_init__(self) -> None:
        # `bool`/`int` would work arithmetically but hide the caller's intent, and
        # `float` is the error this whole module exists to prevent.
        if isinstance(self.value, float):
            raise ValueError(
                "A business decimal must not be a float. Pass a Decimal: an "
                "IEEE-754 round-trip makes a published amount irreproducible."
            )
        if not isinstance(self.value, Decimal):
            raise ValueError(
                f"ScaledDecimal.value must be a Decimal, got "
                f"{type(self.value).__name__}."
            )
        _require_scale(self.scale)

    def canonical_text(self) -> str:
        """The decimal string this value contributes to the canonical payload."""
        return canonical_decimal_text(self.value, scale=self.scale)


def _require_scale(scale: int) -> None:
    if isinstance(scale, bool) or not isinstance(scale, int):
        raise ValueError(
            f"A declared scale must be an int, got {type(scale).__name__}."
        )
    if scale < 0 or scale > MAX_DECIMAL_SCALE:
        raise ValueError(
            f"A declared scale must be between 0 and {MAX_DECIMAL_SCALE}, got {scale}."
        )


def canonical_decimal_text(value: Decimal, *, scale: int) -> str:
    """*value* as a fixed-point decimal string with exactly *scale* digits.

    Raises when the value cannot be represented at that scale without losing a
    digit. ``Decimal("10.5")`` at scale 2 is ``"10.50"``; ``Decimal("10.555")``
    at scale 2 is an error, not ``"10.56"``.
    """
    if isinstance(value, float):
        raise ValueError(
            "A business decimal must not be a float. Pass a Decimal instead."
        )
    if not isinstance(value, Decimal):
        raise ValueError(f"Expected a Decimal, got {type(value).__name__}.")
    _require_scale(scale)
    if not value.is_finite():
        raise ValueError(f"{value} has no canonical decimal form.")

    try:
        with localcontext() as context:
            # Trapping Inexact turns "this rounds" into an exception. Comparing
            # after the fact would work too, but the trap states the intent and
            # cannot be forgotten by a later edit.
            context.prec = 60
            context.traps[Inexact] = True
            quantized = value.quantize(Decimal(1).scaleb(-scale))
    except (Inexact, InvalidOperation) as error:
        raise ValueError(
            f"{value} does not fit scale {scale} without rounding. Declare the "
            "scale the value is actually published at rather than losing a digit."
        ) from error

    return _fixed_point_text(quantized)


def canonical_document(payload: Mapping[str, Any]) -> dict[str, Any]:
    """*payload* reduced to JSON-native types, with every domain rule applied.

    The result contains only ``dict``, ``list``, ``str``, ``int`` and ``bool``:
    decimals have become decimal strings, timestamps RFC 3339 UTC strings, enums
    their ``.value``, absent keys have been dropped and floats rejected. It is
    therefore safe to store in JSONB *and* to re-canonicalise after reading back.

    That round-trip property is why this function exists rather than only
    :func:`canonical_text`. ``TonReportRevision.canonical_payload`` stores this
    form, so recomputing the hash on read digests exactly the bytes that were
    hashed at publication — even though PostgreSQL reorders JSONB keys, because
    :func:`canonical_text` sorts them again.
    """
    if not isinstance(payload, Mapping):
        raise ValueError("A canonical payload must be a mapping at the top level.")
    return _document_object(payload)


def canonical_text(payload: Mapping[str, Any]) -> str:
    """The exact string :func:`compute_content_hash` digests.

    Exposed so a test can assert the serialisation itself. A digest comparison
    alone cannot show *why* two payloads disagreed.

    Always routed through :func:`canonical_document`, so the stored form and the
    hashed form cannot drift apart: there is one set of rules, applied once.
    """
    return _serialise_value(canonical_document(payload))


def canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """:func:`canonical_text` as UTF-8, which is what is actually hashed."""
    return canonical_text(payload).encode("utf-8")


def compute_content_hash(payload: Mapping[str, Any]) -> str:
    """The SHA-256 hex digest of the canonical bytes of *payload*.

    Bare hex, with no scheme prefix: unlike an identity key, a content hash is
    always stored next to its ``canonicalization_version`` and
    ``hash_algorithm``, so the scheme is already recorded as data.
    """
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def canonical_timestamp_text(value: datetime.datetime) -> str:
    """*value* as RFC 3339 UTC with an explicit ``Z``.

    A naive datetime is refused rather than assumed to be UTC. Assuming would
    make the canonical form depend on where the process happened to run, which is
    precisely the non-reproducibility this module exists to prevent.
    """
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(
            "A canonical timestamp must be timezone-aware. A naive value cannot "
            "be normalised to UTC without guessing."
        )
    in_utc = value.astimezone(datetime.UTC)
    fraction = f"{in_utc.microsecond:06d}"[:TIMESTAMP_FRACTIONAL_DIGITS]
    return f"{in_utc:%Y-%m-%dT%H:%M:%S}.{fraction}Z"


def _fixed_point_text(value: Decimal) -> str:
    text = format(value, "f")
    # "-0.00" and "0.00" are one number, so they get one representation.
    if text.startswith("-") and value == 0:
        text = text[1:]
    return text


def _normalised_decimal_text(value: Decimal) -> str:
    """A bare ``Decimal`` in its scale-free canonical form."""
    if not value.is_finite():
        raise ValueError(f"{value} has no canonical decimal form.")
    # `normalize` strips trailing fractional zeros so numerically equal values
    # agree, but turns an integral value into exponent form ("1E+2"); `f`
    # formatting puts it back.
    return _fixed_point_text(value.normalize())


def _canonical_string(text: str) -> str:
    characters = ['"']
    for character in unicodedata.normalize("NFC", text):
        escape = _STRING_ESCAPES.get(character)
        if escape is not None:
            characters.append(escape)
        elif character < "\u0020":
            characters.append(f"\\u{ord(character):04x}")
        else:
            characters.append(character)
    characters.append('"')
    return "".join(characters)


def _sorted_keys(keys: list[str]) -> list[str]:
    """RFC 8785 key order: by UTF-16 code unit.

    Encoding to UTF-16BE and comparing bytes *is* that ordering. Python's default
    string comparison is by code point and differs for characters above the BMP.
    """
    return sorted(keys, key=lambda key: key.encode("utf-16-be"))


def _document_object(mapping: Mapping[str, Any]) -> dict[str, Any]:
    present: dict[str, Any] = {}
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise ValueError(
                f"A canonical object key must be a string, got {type(key).__name__}."
            )
        # Domain rule 3. Absence is expressed by the key not being there, so a
        # payload omitting a key and one setting it to null normalise to one form.
        if value is None:
            continue
        normalised = unicodedata.normalize("NFC", key)
        if normalised in present:
            raise ValueError(
                f"Two keys normalise to {normalised!r}. A canonical payload must "
                "have one representation per key."
            )
        present[normalised] = _document_value(value)

    return {key: present[key] for key in _sorted_keys(list(present))}


def _document_array(values: Sequence[Any]) -> list[Any]:
    items: list[Any] = []
    for value in values:
        if value is None:
            # Dropping it would shift every later element, so a null inside a list
            # is ambiguous rather than absent.
            raise ValueError(
                "A canonical array must not contain null. Omit the element, or "
                "use an object with the key absent."
            )
        items.append(_document_value(value))
    return items


def _document_value(value: Any) -> Any:
    # `float` first: it is the rejection this module exists for, and `isinstance`
    # against the numeric checks below would otherwise let one through.
    if isinstance(value, float):
        raise ValueError(
            "A float has no canonical form in ton-canon-1. Monetary values, "
            "quantities, percentages and rates must be Decimal or ScaledDecimal: "
            "an IEEE-754 round-trip would make the hash platform-dependent."
        )
    if isinstance(value, complex):
        raise ValueError("A complex number has no canonical form.")
    # `bool` before `int`, because bool is a subclass of int.
    if isinstance(value, bool):
        return value
    if isinstance(value, ScaledDecimal):
        return value.canonical_text()
    if isinstance(value, Decimal):
        return _normalised_decimal_text(value)
    if isinstance(value, int):
        # Exact by construction, so a count or an ordinal stays a JSON number. A
        # business decimal must never arrive here as an int with an implied scale
        # — that is what ScaledDecimal is for.
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Enum):
        # Domain rule 4. A non-string member would serialise as whatever its value
        # happened to be, so it is refused instead.
        if not isinstance(value.value, str):
            raise ValueError(
                f"{type(value).__name__}.{value.name} has a non-string value and "
                "cannot serialise as a stable enum string."
            )
        return value.value
    # `datetime` before `date`: datetime is a subclass of date.
    if isinstance(value, datetime.datetime):
        return canonical_timestamp_text(value)
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Mapping):
        return _document_object(value)
    if isinstance(value, (bytes, bytearray)):
        raise ValueError(
            "Raw bytes have no canonical form. Publish a decoded value or a "
            "reference, not the material itself."
        )
    if isinstance(value, Sequence):
        return _document_array(value)
    raise ValueError(
        f"{type(value).__name__} has no canonical form in ton-canon-1. The "
        "accepted types are str, bool, int, Decimal, ScaledDecimal, date, "
        "datetime, UUID, str-valued Enum, mapping and sequence."
    )


def _serialise_value(value: Any) -> str:
    """Render a :func:`canonical_document` tree as RFC 8785 JSON text.

    Only the five JSON-native types reach here. Keys are re-sorted rather than
    trusted: a document read back from JSONB carries PostgreSQL's own key order,
    not the one it was written with.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _canonical_string(value)
    if isinstance(value, Mapping):
        body = ",".join(
            f"{_canonical_string(key)}:{_serialise_value(value[key])}"
            for key in _sorted_keys([str(key) for key in value])
        )
        return "{" + body + "}"
    if isinstance(value, Sequence):
        return "[" + ",".join(_serialise_value(item) for item in value) + "]"
    raise ValueError(
        f"{type(value).__name__} is not a canonical document type. Build the "
        "document with canonical_document() first."
    )
