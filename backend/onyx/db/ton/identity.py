"""Logical-identity contract for TON rule versions (Plan 003b).

Pure domain code: no session, no I/O, no LLM. It exists in 003b so that 003c can
build ``Finding.identity_key`` on a contract that is already validated and
tested, rather than inventing dimensions at detection time.

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

from collections.abc import Iterable

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
