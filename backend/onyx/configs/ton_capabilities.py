"""TON deployment capability policy.

Upstream Onyx gates a fixed set of API path prefixes behind a purchased product
tier: `PATH_PREFIX_MIN_TIER` -> the `tier_gate` middleware -> HTTP 402
`FEATURE_NOT_AVAILABLE`. TON is a single-company self-hosted deployment with no
paid Onyx entitlement, so a subscription tier cannot be the authority for
whether a capability exists here.

This module is the one declarative answer to "does this capability exist in this
deployment?". It changes nothing else. The four questions stay separate:

    capability (this module)   does the feature exist in this deployment
    Permission + group scope   may this user use it (GATE 1 / GATE 2)
    tenant context             is the tenant valid
    resource ACL               which rows may this user read

Every prefix declared here satisfies all of the following, verified by the TON
capability/edition audit (`plans/ton/capability-edition-audit.md`):

- the implementation is entirely local: models, migrations, API, DB layer and
  workers run against this deployment's own PostgreSQL, Redis, OpenSearch and
  file store;
- no Onyx-operated service is contacted at any point;
- the existing authorization gate is untouched, and is named in
  `TON_LOCAL_CAPABILITIES` so a reviewer can check it;
- TON requires the capability.

Removing a commercial gate never removes an authorization gate. A prefix that is
not declared here stays gated exactly as upstream ships it. The retained and
deferred inventory lives in `plans/ton/backend/008a-capability-gates.md`.
"""

from collections.abc import Mapping
from typing import TypeVar

_TierT = TypeVar("_TierT")


# Path prefix -> the authorization gate that remains authoritative for it.
# The value is documentation for reviewers, and the TON gate test asserts every
# entry names a real gate that is still enforced in the handler chain.
TON_LOCAL_CAPABILITIES: Mapping[str, str] = {
    # P0. User groups, permission grants and group scoping. Carries the TON
    # access model (admin / controladoria / gestor / leitura) and the
    # group-aware document ACLs computed by the EE access implementation.
    "/manage/admin/user-group": (
        "GATE 1 require_permission(READ_USER_GROUPS | MANAGE_USER_GROUPS | "
        "FULL_ADMIN_PANEL_ACCESS); GATE 2 assert_manages_group / "
        "assert_within_scope / restrict_to_group_ids for scoped managers"
    ),
}

TON_LOCAL_CAPABILITY_PREFIXES: frozenset[str] = frozenset(TON_LOCAL_CAPABILITIES)


def apply_ton_capability_policy(
    upstream_gates: Mapping[str, _TierT],
) -> dict[str, _TierT]:
    """Drop the product-tier requirement from TON's local capabilities.

    Returns a copy of `upstream_gates` without the declared prefixes. Pure and
    total: unknown or already-absent declarations are ignored so a benign
    upstream edit can never stop the application from booting. Drift is reported
    by `ton_capability_policy_drift` and asserted by the TON gate test, which is
    where a renamed or shadowed prefix must fail.
    """
    return {
        prefix: tier
        for prefix, tier in upstream_gates.items()
        if prefix not in TON_LOCAL_CAPABILITY_PREFIXES
    }


def ton_capability_policy_drift(upstream_gates: Mapping[str, _TierT]) -> list[str]:
    """Describe every way this policy no longer matches the upstream gate map.

    Two failure modes matter, both silent at runtime:

    1. A declared prefix is absent upstream. The declaration is stale, or the
       gate was renamed and now applies to TON again.
    2. A retained prefix extends a declared prefix. `tier_gate` resolves the
       longest match, so the nested entry would re-gate part of a capability TON
       declared available.
    """
    stale = [
        f"declared TON capability prefix {prefix!r} is not in the upstream tier "
        "gate map; the declaration is stale or the upstream prefix was renamed"
        for prefix in sorted(TON_LOCAL_CAPABILITY_PREFIXES)
        if prefix not in upstream_gates
    ]
    shadowed = [
        f"retained gate {retained!r} extends TON capability prefix {declared!r}; "
        "longest-prefix matching would still gate it"
        for retained in sorted(apply_ton_capability_policy(upstream_gates))
        for declared in sorted(TON_LOCAL_CAPABILITY_PREFIXES)
        if retained.startswith(declared)
    ]
    return stale + shadowed
