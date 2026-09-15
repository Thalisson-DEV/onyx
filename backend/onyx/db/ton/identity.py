"""Logical-identity contract for TON rule versions (Plans 003b and 003c).

Pure domain code: no session, no I/O, no LLM. 003b fixed the component
vocabulary and its canonical order; 003c adds the digest built on top of it
(:func:`compute_identity_key`). The 003b contract is consumed unchanged — no
member was added, removed or reordered.

Two decisions from readiness §7 are enforced here:

* the component vocabulary is **closed** — an arbitrary dimension is rejected,
  which is what stops an LLM-proposed identity dimension from entering the
  domain;
* ``rule_code`` is part of identity, ``rule_version`` never is. If the version
  were part of identity, every threshold change would reset recurrence tracking
  on every open case.

Interpretation output — title, description, summary, probable cause — is absent
from the vocabulary on purpose. Text similarity is not a deduplication mechanism
in this domain.
"""

import hashlib
import unicodedata
from collections.abc import Iterable, Mapping

from onyx.db.ton.enums import IdentityComponent

# The declared order matters: 003c emits components in this order before hashing,
# so two rule versions listing the same dimensions differently still produce the
# same identity. Keeping the canonical order here rather than in the caller is
# what makes that property structural.
IDENTITY_COMPONENT_ORDER: tuple[IdentityComponent, ...] = (
    IdentityComponent.RULE_CODE,
    IdentityComponent.BUSINESS_UNIT_ID,
    IdentityComponent.CONTRACT_ID,
    IdentityComponent.PERIOD,
    IdentityComponent.SOURCE_SYSTEM,
    IdentityComponent.SOURCE_RECORD_KEY,
    IdentityComponent.NATURE_GROUP,
    IdentityComponent.VEHICLE_KEY,
    IdentityComponent.SUPPLIER_KEY,
    IdentityComponent.EMPLOYEE_KEY_MASKED,
)

ALLOWED_IDENTITY_COMPONENTS: frozenset[str] = frozenset(
    component.value for component in IdentityComponent
)


def validate_identity_components(
    components: Iterable[str] | None,
) -> list[str]:
    """Return *components* normalised to canonical order, or raise.

    Rejects an unknown dimension, a duplicate and an empty list. An empty list is
    an error rather than a permissive default: a rule version whose findings have
    no identity would deduplicate every detection into one case.
    """
    if components is None:
        raise ValueError(
            "identity_components is required: a rule version must declare which "
            "dimensions make one of its findings distinct."
        )

    declared = list(components)
    if not declared:
        raise ValueError(
            "identity_components must not be empty: every rule version needs at "
            "least one dimension, otherwise all its findings share one identity."
        )

    seen: set[str] = set()
    for component in declared:
        if not isinstance(component, str):
            raise ValueError(
                "identity_components entries must be strings from the closed "
                f"vocabulary, got {type(component).__name__}."
            )
        if component not in ALLOWED_IDENTITY_COMPONENTS:
            allowed = ", ".join(sorted(ALLOWED_IDENTITY_COMPONENTS))
            raise ValueError(
                f"'{component}' is not an approved identity component. "
                f"Allowed: {allowed}."
            )
        if component in seen:
            raise ValueError(
                f"'{component}' is declared more than once in identity_components."
            )
        seen.add(component)

    return [
        component.value
        for component in IDENTITY_COMPONENT_ORDER
        if component.value in seen
    ]


# ---------------------------------------------------------------------------
# Plan 003c — the deterministic digest.
# ---------------------------------------------------------------------------

# Bumped only if the canonicalisation below changes. Carrying it inside the key
# means a future change breaks recurrence *visibly* — every case starts a new
# lineage — rather than silently re-matching cases under new rules.
IDENTITY_SCHEME = "ton-id-1"

# ASCII unit separator. Chosen because it cannot occur in a business value: a
# printable separator such as "|" or ":" could appear inside a source record key
# and let two different tuples serialise identically.
_FIELD_SEPARATOR = "\x1f"

# Components whose case carries no meaning, so two spellings must not create two
# cases. Everything else is compared as written: `source_record_key`,
# `vehicle_key`, `supplier_key` and `employee_key_masked` are opaque external
# keys where a case difference may well distinguish two records, and `period` is
# numeric. Erring towards case-sensitive is the safe direction — it can only ever
# split one case into two, never merge two distinct cases into one.
CASE_INSENSITIVE_COMPONENTS: frozenset[IdentityComponent] = frozenset(
    {
        IdentityComponent.RULE_CODE,
        IdentityComponent.BUSINESS_UNIT_ID,
        IdentityComponent.CONTRACT_ID,
        IdentityComponent.NATURE_GROUP,
        IdentityComponent.SOURCE_SYSTEM,
    }
)

# The supersede generation. Not a member of the closed component vocabulary
# because it is not a business dimension: it exists so that a case superseded
# under `SUPERSEDE_WITH_NEW_OCCURRENCE` can carry a distinct `identity_key` while
# `UNIQUE(identity_key)` stays the deduplication boundary (readiness §7). It is
# omitted entirely for generation 1, so an ordinary case digests to exactly the
# canonical tuple.
_GENERATION_FIELD = "supersede_generation"


def canonicalize_identity_value(
    component: IdentityComponent, value: object | None
) -> str | None:
    """Normalise one identity component value, or return ``None`` if absent.

    Unicode NFC, trimmed, and case-folded when the component is declared
    case-insensitive. A value that is empty after trimming is *absent*: readiness
    §7 requires omitting it rather than emitting an empty-string substitute, so
    that "no contract" and "contract ''" cannot be two different cases.
    """
    if value is None:
        return None

    text = value if isinstance(value, str) else str(value)
    text = unicodedata.normalize("NFC", text).strip()
    if not text:
        return None
    if component in CASE_INSENSITIVE_COMPONENTS:
        text = text.casefold()
    return text


def canonical_identity_payload(
    *,
    rule_code: str,
    components: Iterable[str],
    values: Mapping[str, object | None],
    supersede_generation: int = 1,
) -> str:
    """Build the exact string that :func:`compute_identity_key` digests.

    Exposed so a test can assert the serialisation rather than only the digest —
    a hash comparison alone cannot show *why* two tuples collided.

    ``rule_code`` is always emitted first, whether or not the rule version
    declared it. Readiness §7 fixes that identity includes the rule code and
    never the rule version: were the version part of identity, every threshold
    change would reset recurrence tracking on every open case.

    Nothing derived from a language model can reach this function. It takes no
    title, no description and no interpretation, and the component vocabulary is
    closed, so an LLM-proposed dimension is rejected rather than hashed.
    """
    if supersede_generation < 1:
        raise ValueError("supersede_generation starts at 1.")

    normalised_components = validate_identity_components(components)
    declared = {IdentityComponent(name) for name in normalised_components}

    unknown_values = set(values) - ALLOWED_IDENTITY_COMPONENTS
    if unknown_values:
        raise ValueError(
            "Identity values must come from the closed vocabulary. "
            f"Unknown: {', '.join(sorted(unknown_values))}."
        )
    undeclared = {
        name
        for name, value in values.items()
        if value is not None and IdentityComponent(name) not in declared
    }
    if undeclared:
        raise ValueError(
            "A value was supplied for a dimension this rule version does not "
            f"declare: {', '.join(sorted(undeclared))}. Identity must follow "
            "RuleVersion.identity_components, not the caller."
        )

    canonical_rule_code = canonicalize_identity_value(
        IdentityComponent.RULE_CODE, rule_code
    )
    if canonical_rule_code is None:
        raise ValueError("rule_code is required: it is what makes recurrence logical.")

    # `name=value` pairs rather than bare values, so omitting a component cannot
    # produce the same string as shifting the next one into its place.
    fields = [f"{IdentityComponent.RULE_CODE.value}={canonical_rule_code}"]
    for component in IDENTITY_COMPONENT_ORDER:
        if component is IdentityComponent.RULE_CODE or component not in declared:
            continue
        canonical = canonicalize_identity_value(component, values.get(component.value))
        if canonical is None:
            continue
        fields.append(f"{component.value}={canonical}")

    if supersede_generation > 1:
        fields.append(f"{_GENERATION_FIELD}={supersede_generation}")

    return _FIELD_SEPARATOR.join(fields)


def compute_identity_key(
    *,
    rule_code: str,
    components: Iterable[str],
    values: Mapping[str, object | None],
    supersede_generation: int = 1,
) -> str:
    """The opaque deterministic identity of one logical case.

    A scheme-prefixed SHA-256 over :func:`canonical_identity_payload`. Opaque on
    purpose: nothing may parse a business value back out of it, and a caller that
    needs a dimension must read the column.

    Pass ``supersede_generation = 1`` (the default) for the logical lineage key.
    A higher generation yields the distinct key a superseding occurrence needs.
    """
    payload = canonical_identity_payload(
        rule_code=rule_code,
        components=components,
        values=values,
        supersede_generation=supersede_generation,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{IDENTITY_SCHEME}:{digest}"
