"""TON Plan 008a — commercial gate vs authorization gate.

Two things are proved here, and they must both hold:

1. The TON-required Groups/RBAC capability no longer depends on a purchased
   product tier. At `Tier.COMMUNITY` (the intended TON state: no license row, no
   subscription) `/manage/admin/user-group` and every subpath reach their
   handler. The same request against the unmodified upstream gate map still
   returns 402, which is the baseline failure this slice removes.

2. Removing that commercial gate removed no authorization gate. Every route on
   the group router keeps its `require_permission` dependency (GATE 1) with the
   same permission and the same `allow_scope` value, and every `allow_scope`
   route still applies a GATE 2 scope check. A `BASIC_ACCESS`-only user is still
   refused, and a scoped manager is still scoped.

Also pinned: the gates TON deliberately retains, the no-license tier resolution,
and the EE dispatch invariant that keeps group-aware document ACLs alive.

No external service and no database are required. Nothing here writes anywhere.
"""

import inspect
import json
from collections.abc import Awaitable, Callable, Iterator
from types import FunctionType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import params
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from ee.onyx.access import access as ee_access
from ee.onyx.configs.license_enforcement_config import (
    PATH_PREFIX_MIN_TIER,
    UPSTREAM_PATH_PREFIX_MIN_TIER,
)
from ee.onyx.db import user_group as ee_user_group_db
from ee.onyx.server.middleware import tier_gate
from ee.onyx.server.middleware.tier_gate import add_tier_gate_middleware
from ee.onyx.server.user_group import api as user_group_api
from ee.onyx.utils import tier as ee_tier
from onyx.access import access as ce_access
from onyx.access.utils import prefix_user_email, prefix_user_group
from onyx.auth import scoped_permissions
from onyx.auth.permissions import has_global_permission, has_permission
from onyx.auth.users import current_user
from onyx.configs.app_configs import ENTERPRISE_EDITION_ENABLED
from onyx.configs.constants import ANONYMOUS_USER_UUID, PUBLIC_DOC_PAT
from onyx.configs.ton_capabilities import (
    TON_LOCAL_CAPABILITIES,
    TON_LOCAL_CAPABILITY_PREFIXES,
    apply_ton_capability_policy,
    ton_capability_policy_drift,
)
from onyx.db.enums import AccessType, Permission, PermissionAuthority
from onyx.db.models import User
from onyx.error_handling.exceptions import OnyxError
from onyx.server.settings.models import Tier
from onyx.utils import variable_functionality
from onyx.utils.variable_functionality import (
    fetch_versioned_implementation,
    global_version,
)
from shared_configs.configs import MULTI_TENANT

GROUP_CAPABILITY_PREFIX = "/manage/admin/user-group"

# Every path the TON Groups/RBAC capability is served on, as mounted by
# `ee/onyx/main.py`. All of these were 402 at community tier before this slice.
GROUP_CAPABILITY_PATHS: list[str] = [
    "/manage/admin/user-group",
    "/manage/admin/user-group?include_default=true",
    "/manage/admin/user-group/7",
    "/manage/admin/user-group/rename",
    "/manage/admin/user-group/7/permissions",
    "/manage/admin/user-group/7/incognito",
    "/manage/admin/user-group/7/add-users",
    "/manage/admin/user-group/7/agents",
    "/manage/admin/user-group/7/document-sets",
    "/manage/admin/user-group/7/manager",
]

# Served by the same router but outside the gated prefix, so they already worked
# at community tier. Listed to make the boundary explicit.
GROUP_ROUTER_ALWAYS_OPEN_PATHS: list[str] = [
    "/manage/admin/permissions/registry",
    "/manage/user-groups/minimal",
]

# Commercial gates TON keeps. Each entry is a deliberate decision recorded in
# `plans/ton/backend/008a-capability-gates.md`, not an oversight.
RETAINED_GATE_PATHS: dict[str, Tier] = {
    "/admin/enterprise-settings/appearance": Tier.BUSINESS,  # branding writes: DEFERRED P1
    "/admin/query-history/start-export": Tier.BUSINESS,
    "/admin/chat-sessions/abc": Tier.BUSINESS,
    "/admin/chat-session-history/abc": Tier.BUSINESS,
    "/admin/usage-report/generate": Tier.BUSINESS,
    "/analytics/admin/query": Tier.BUSINESS,
    "/admin/api-key": Tier.BUSINESS,
    "/gateway/v1/models": Tier.BUSINESS,
    "/admin/enterprise-settings/custom-analytics-script": Tier.ENTERPRISE,
    "/admin/enterprise-settings/scim/token": Tier.ENTERPRISE,
    "/manage/admin/standard-answer": Tier.ENTERPRISE,
    "/admin/token-rate-limits": Tier.ENTERPRISE,
    "/admin/hooks/1": Tier.ENTERPRISE,
    "/admin/log-export/start": Tier.ENTERPRISE,
    "/analytics/assistant/1/stats": Tier.ENTERPRISE,
    "/evals/run": Tier.ENTERPRISE,
    "/scim/v2/Users": Tier.ENTERPRISE,
}


# ---------------------------------------------------------------------------
# 1. Capability policy declaration
# ---------------------------------------------------------------------------


def test_group_capability_is_the_declared_ton_policy() -> None:
    assert TON_LOCAL_CAPABILITY_PREFIXES == {GROUP_CAPABILITY_PREFIX}


def test_every_declared_capability_names_its_surviving_authorization_gate() -> None:
    """The declaration is only safe if a real gate still applies. Each entry must
    name the permission dependency and the scope check that stay authoritative."""
    for prefix, gate in TON_LOCAL_CAPABILITIES.items():
        assert "require_permission" in gate, prefix
        assert "GATE 2" in gate, prefix


def test_policy_matches_the_upstream_gate_map() -> None:
    """Fails if upstream renames, removes or nests a gated prefix under a TON
    capability. Either would silently change what TON un-gates."""
    assert ton_capability_policy_drift(UPSTREAM_PATH_PREFIX_MIN_TIER) == []


def test_upstream_map_still_carries_the_business_gate() -> None:
    """The baseline this slice changes. Keeping the upstream declaration intact
    is what makes the before/after comparison below meaningful."""
    assert UPSTREAM_PATH_PREFIX_MIN_TIER[GROUP_CAPABILITY_PREFIX] is Tier.BUSINESS


def test_enforced_map_is_upstream_minus_exactly_the_ton_capabilities() -> None:
    assert set(UPSTREAM_PATH_PREFIX_MIN_TIER) - set(PATH_PREFIX_MIN_TIER) == (
        TON_LOCAL_CAPABILITY_PREFIXES
    )
    for prefix, tier in PATH_PREFIX_MIN_TIER.items():
        assert UPSTREAM_PATH_PREFIX_MIN_TIER[prefix] is tier


def test_policy_is_a_pure_filter() -> None:
    """It may only drop declared keys — never add one, retier one, or mutate the
    input."""
    upstream = dict(UPSTREAM_PATH_PREFIX_MIN_TIER)
    result = apply_ton_capability_policy(upstream)
    assert upstream == UPSTREAM_PATH_PREFIX_MIN_TIER
    assert set(result).issubset(set(upstream))
    assert all(result[key] is upstream[key] for key in result)


# ---------------------------------------------------------------------------
# 2. Middleware behavior — before and after
# ---------------------------------------------------------------------------

MiddlewareHarness = tuple[
    Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]],
    Callable[[Request], Awaitable[Response]],
]


def _build_harness() -> MiddlewareHarness:
    app = MagicMock()
    captured: Any = None

    def capture_middleware(_kind: str) -> Callable[[Any], Any]:
        def decorator(func: Any) -> Any:
            nonlocal captured
            captured = func
            return func

        return decorator

    app.middleware = capture_middleware
    add_tier_gate_middleware(app, MagicMock())

    async def call_next(_req: Request) -> Response:
        response = MagicMock()
        response.status_code = 200
        return response

    return captured, call_next


@pytest.fixture
def middleware_harness() -> MiddlewareHarness:
    return _build_harness()


@pytest.fixture
def upstream_middleware_harness() -> Iterator[MiddlewareHarness]:
    """The same middleware, resolving against the unmodified upstream gate map.
    Reproduces the pre-008a behavior through the real code path."""
    upstream_sorted = sorted(
        UPSTREAM_PATH_PREFIX_MIN_TIER.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    with patch.object(tier_gate, "_SORTED_GATES", upstream_sorted):
        yield _build_harness()


def _make_request(path: str) -> MagicMock:
    request = MagicMock()
    request.url.path = path.split("?", 1)[0]
    return request


@pytest.mark.asyncio
@pytest.mark.parametrize("path", GROUP_CAPABILITY_PATHS)
@patch("ee.onyx.server.middleware.tier_gate.get_tier")
async def test_baseline_community_tier_was_charged_for_groups(
    mock_get_tier: MagicMock,
    path: str,
    upstream_middleware_harness: MiddlewareHarness,
) -> None:
    """Evidence of the failure 008a removes: an authorized admin on a
    no-license deployment got 402 with a plan name in the payload."""
    mock_get_tier.return_value = Tier.COMMUNITY
    middleware, call_next = upstream_middleware_harness
    response = await middleware(_make_request(path), call_next)

    assert response.status_code == 402
    payload = json.loads(bytes(response.body))
    assert payload["required_tier"] == Tier.BUSINESS.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path", GROUP_CAPABILITY_PATHS + GROUP_ROUTER_ALWAYS_OPEN_PATHS
)
@patch("ee.onyx.server.middleware.tier_gate.get_tier")
async def test_community_tier_reaches_the_group_handler(
    mock_get_tier: MagicMock, path: str, middleware_harness: MiddlewareHarness
) -> None:
    """After 008a the request is handed to the handler, where
    `require_permission` decides. No tier is resolved at all, so the decision
    touches no Redis key, no license row and no network."""
    middleware, call_next = middleware_harness
    response = await middleware(_make_request(path), call_next)

    assert response.status_code == 200
    mock_get_tier.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("api_prefix", ["/api", "/v2"])
@patch("ee.onyx.server.middleware.tier_gate.get_tier")
async def test_group_capability_is_ungated_under_any_api_prefix(
    mock_get_tier: MagicMock, api_prefix: str, middleware_harness: MiddlewareHarness
) -> None:
    mock_get_tier.return_value = Tier.COMMUNITY
    middleware, call_next = middleware_harness
    with patch(
        "onyx.server.middleware.api_prefix.APP_API_PREFIX", api_prefix.strip("/")
    ):
        response = await middleware(
            _make_request(f"{api_prefix}{GROUP_CAPABILITY_PREFIX}/7/add-users"),
            call_next,
        )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 3. Retained commercial gates — scope must not widen
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("path,expected", sorted(RETAINED_GATE_PATHS.items()))
@patch("ee.onyx.server.middleware.tier_gate.get_tier")
async def test_retained_gates_still_charge_community_tier(
    mock_get_tier: MagicMock,
    path: str,
    expected: Tier,
    middleware_harness: MiddlewareHarness,
) -> None:
    mock_get_tier.return_value = Tier.COMMUNITY
    middleware, call_next = middleware_harness
    response = await middleware(_make_request(path), call_next)

    assert response.status_code == 402
    assert json.loads(bytes(response.body))["required_tier"] == expected.value


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", sorted(PATH_PREFIX_MIN_TIER))
@patch("ee.onyx.server.middleware.tier_gate.get_tier")
async def test_no_retained_prefix_became_free(
    mock_get_tier: MagicMock, prefix: str, middleware_harness: MiddlewareHarness
) -> None:
    """Exhaustive companion to the curated list above: nothing left in the map
    may pass at community tier."""
    mock_get_tier.return_value = Tier.COMMUNITY
    middleware, call_next = middleware_harness
    response = await middleware(_make_request(f"{prefix}/anything"), call_next)
    assert response.status_code == 402


def test_branding_writes_remain_deferred() -> None:
    """Branding is P1 and deliberately out of this slice. TON-FE-001/002 already
    supply the product identity through design tokens."""
    assert PATH_PREFIX_MIN_TIER["/admin/enterprise-settings"] is Tier.BUSINESS


def test_history_usage_analytics_and_service_accounts_remain_gated() -> None:
    for prefix in (
        "/admin/query-history",
        "/admin/chat-sessions",
        "/admin/chat-session-history",
        "/admin/usage-report",
        "/analytics/admin",
        "/analytics",
        "/admin/api-key",
        "/admin/hooks",
        "/admin/log-export",
        "/admin/token-rate-limits",
        "/manage/admin/standard-answer",
        "/evals",
        "/scim",
    ):
        assert prefix in PATH_PREFIX_MIN_TIER


# ---------------------------------------------------------------------------
# 4. Non-path commercial gates — untouched
# ---------------------------------------------------------------------------


@patch("ee.onyx.utils.tier.get_tier", return_value=Tier.COMMUNITY)
def test_connector_sync_access_gate_is_untouched(mock_get_tier: MagicMock) -> None:
    """`AccessType.SYNC` mirrors a source system's own ACLs. TON does not need it
    yet, so the gate stays; removing it would create cc-pairs whose permission
    sync may never run."""
    with pytest.raises(OnyxError):
        ee_tier.require_business_tier_for_sync_access(AccessType.SYNC)

    # PUBLIC and PRIVATE were never gated and stay usable.
    ee_tier.require_business_tier_for_sync_access(AccessType.PUBLIC)
    ee_tier.require_business_tier_for_sync_access(AccessType.PRIVATE)
    assert mock_get_tier.called


@patch("ee.onyx.utils.tier.get_tier", return_value=Tier.COMMUNITY)
def test_multi_sso_gate_is_untouched(_mock_get_tier: MagicMock) -> None:
    with pytest.raises(OnyxError):
        ee_tier.require_business_tier_for_multi_sso()


# ---------------------------------------------------------------------------
# 5. Authorization contract on the group router (the absolute security rule)
# ---------------------------------------------------------------------------

# method + path -> (required permission, allow_scope, GATE 2 symbols that must
# appear in the handler or in the DB function it delegates to).
#
# `allow_scope=False` is itself a security decision: create, delete and
# permission changes deliberately refuse a scoped manager.
GROUP_ROUTE_CONTRACT: dict[str, tuple[Permission, bool, tuple[str, ...]]] = {
    "GET /manage/admin/user-group": (
        Permission.READ_USER_GROUPS,
        True,
        ("get_scoped_groups", "restrict_to_group_ids", "manages_group"),
    ),
    "GET /manage/admin/user-group/{user_group_id}": (
        Permission.READ_USER_GROUPS,
        True,
        ("manages_group",),
    ),
    "GET /manage/user-groups/minimal": (
        Permission.BASIC_ACCESS,
        False,
        ("fetch_user_groups_for_user",),
    ),
    "GET /manage/admin/permissions/registry": (
        Permission.FULL_ADMIN_PANEL_ACCESS,
        False,
        (),
    ),
    "GET /manage/admin/user-group/{user_group_id}/permissions": (
        Permission.MANAGE_USER_GROUPS,
        False,
        (),
    ),
    "PUT /manage/admin/user-group/{user_group_id}/permissions": (
        Permission.FULL_ADMIN_PANEL_ACCESS,
        False,
        (),
    ),
    "POST /manage/admin/user-group": (Permission.MANAGE_USER_GROUPS, False, ()),
    "PATCH /manage/admin/user-group/rename": (
        Permission.MANAGE_USER_GROUPS,
        True,
        ("assert_manages_group",),
    ),
    "PATCH /manage/admin/user-group/{user_group_id}/incognito": (
        Permission.FULL_ADMIN_PANEL_ACCESS,
        False,
        (),
    ),
    "PATCH /manage/admin/user-group/{user_group_id}": (
        Permission.MANAGE_USER_GROUPS,
        True,
        ("assert_manages_group",),
    ),
    "POST /manage/admin/user-group/{user_group_id}/add-users": (
        Permission.MANAGE_USER_GROUPS,
        True,
        ("assert_manages_group",),
    ),
    "DELETE /manage/admin/user-group/{user_group_id}": (
        Permission.MANAGE_USER_GROUPS,
        False,
        (),
    ),
    "PATCH /manage/admin/user-group/{user_group_id}/agents": (
        Permission.MANAGE_USER_GROUPS,
        True,
        ("assert_manages_group",),
    ),
    "PATCH /manage/admin/user-group/{user_group_id}/document-sets": (
        Permission.MANAGE_USER_GROUPS,
        True,
        ("assert_manages_group", "assert_within_scope"),
    ),
    "PUT /manage/admin/user-group/{user_group_id}/manager": (
        Permission.MANAGE_USER_GROUPS,
        True,
        ("assert_manages_group",),
    ),
}

# GATE 2 for these routes lives in the DB layer, which the handler delegates to.
GATE_2_DELEGATES: dict[str, Callable[..., Any]] = {
    "PATCH /manage/admin/user-group/{user_group_id}": (
        ee_user_group_db.update_user_group
    ),
    "POST /manage/admin/user-group/{user_group_id}/add-users": (
        ee_user_group_db.add_users_to_user_group
    ),
}


def _permission_dependencies(endpoint: Callable[..., Any]) -> list[FunctionType]:
    found: list[FunctionType] = []
    for param in inspect.signature(endpoint).parameters.values():
        default = param.default
        if not isinstance(default, params.Depends):
            continue
        dependency = default.dependency
        # Function attributes live in __dict__, so this needs no getattr and
        # tolerates dependencies that are not require_permission at all.
        if isinstance(dependency, FunctionType) and dependency.__dict__.get(
            "_is_require_permission", False
        ):
            found.append(dependency)
    return found


def _closure_value(func: FunctionType, name: str) -> Any:
    """`require_permission` closes over `allow_scope`, which it does not publish
    the way it publishes `_required_permission`. Read it from the closure rather
    than change production code to suit a test."""
    cells = func.__closure__ or ()
    values = dict(
        zip(
            func.__code__.co_freevars,
            (cell.cell_contents for cell in cells),
            strict=True,
        )
    )
    return values[name]


def _base_user_dependency(func: FunctionType) -> Callable[..., Any]:
    """`allow_anonymous` is consumed in the factory, not the returned closure.
    It survives as the base user dependency the gate depends on."""
    default = inspect.signature(func).parameters["user"].default
    assert isinstance(default, params.Depends)
    assert default.dependency is not None
    return default.dependency


def _router_contract_keys() -> dict[str, APIRoute]:
    routes: dict[str, APIRoute] = {}
    for route in user_group_api.router.routes:
        assert isinstance(route, APIRoute)
        for method in sorted(route.methods):
            routes[f"{method} {route.path}"] = route
    return routes


def test_group_router_surface_is_fully_pinned() -> None:
    """A new route must be added to the contract table deliberately, with its
    permission and its scope decision stated."""
    assert set(_router_contract_keys()) == set(GROUP_ROUTE_CONTRACT)


@pytest.mark.parametrize("key", sorted(GROUP_ROUTE_CONTRACT))
def test_every_group_route_keeps_gate_1(key: str) -> None:
    expected_permission, expected_allow_scope, _ = GROUP_ROUTE_CONTRACT[key]
    route = _router_contract_keys()[key]

    dependencies = _permission_dependencies(route.endpoint)
    assert len(dependencies) == 1, f"{key} must have exactly one permission gate"
    dependency = dependencies[0]

    assert dependency.__dict__["_required_permission"] is expected_permission
    assert _closure_value(dependency, "allow_scope") is expected_allow_scope
    # Anonymous access is never appropriate on a group administration router.
    assert _base_user_dependency(dependency) is current_user


@pytest.mark.parametrize("key", sorted(GROUP_ROUTE_CONTRACT))
def test_every_scoped_group_route_keeps_gate_2(key: str) -> None:
    _, allow_scope, gate_2_symbols = GROUP_ROUTE_CONTRACT[key]
    if allow_scope:
        assert gate_2_symbols, (
            f"{key} admits a scoped manager (GATE 1) and therefore must name a "
            "GATE 2 scope check"
        )

    if not gate_2_symbols:
        return

    route = _router_contract_keys()[key]
    sources = [inspect.getsource(route.endpoint)]
    delegate = GATE_2_DELEGATES.get(key)
    if delegate is not None:
        sources.append(inspect.getsource(delegate))
        sources.append(inspect.getsource(ee_user_group_db))
    combined = "\n".join(sources)

    for symbol in gate_2_symbols:
        assert symbol in combined, f"{key} lost its GATE 2 symbol {symbol}"


def test_scoped_manager_is_refused_on_create_delete_and_permission_routes() -> None:
    """These three keep `allow_scope=False` on purpose: a scoped manager must not
    create a group, delete one, or hand out permission grants."""
    for key in (
        "POST /manage/admin/user-group",
        "DELETE /manage/admin/user-group/{user_group_id}",
        "PUT /manage/admin/user-group/{user_group_id}/permissions",
    ):
        _, allow_scope, _ = GROUP_ROUTE_CONTRACT[key]
        assert allow_scope is False


# ---------------------------------------------------------------------------
# 6. Negative security tests
# ---------------------------------------------------------------------------


def _user(
    *,
    permissions: list[Permission],
    is_group_manager: bool = False,
    email: str = "person@valenorte.example",
) -> User:
    return User(
        email=email,
        prior_emails=[],
        effective_permissions=[p.value for p in permissions],
        is_group_manager=is_group_manager,
    )


ADMIN = _user(
    permissions=[Permission.FULL_ADMIN_PANEL_ACCESS], email="admin@vn.example"
)
GROUPS_ADMIN = _user(permissions=[Permission.MANAGE_USER_GROUPS], email="ga@vn.example")
SCOPED_MANAGER = _user(
    permissions=[Permission.BASIC_ACCESS],
    is_group_manager=True,
    email="gestor@vn.example",
)
BASIC_ONLY = _user(permissions=[Permission.BASIC_ACCESS], email="leitura@vn.example")


async def _call_gate_1(route_key: str, user: User) -> User:
    route = _router_contract_keys()[route_key]
    dependency = _permission_dependencies(route.endpoint)[0]
    request = MagicMock()
    request.state = MagicMock()
    request.state.token_scopes = None
    return await dependency(request, user)


@pytest.mark.asyncio
@pytest.mark.parametrize("key", sorted(GROUP_ROUTE_CONTRACT))
async def test_admin_can_reach_every_group_route(key: str) -> None:
    assert await _call_gate_1(key, ADMIN) is ADMIN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key",
    sorted(k for k in GROUP_ROUTE_CONTRACT if "permissions/registry" not in k),
)
async def test_basic_access_only_user_cannot_manage_groups(key: str) -> None:
    """The point of the whole slice: dropping the tier gate did not turn Groups
    into a public capability. The only route a BASIC_ACCESS user reaches is the
    read-only `/manage/user-groups/minimal` list of their own groups."""
    if GROUP_ROUTE_CONTRACT[key][0] is Permission.BASIC_ACCESS:
        assert await _call_gate_1(key, BASIC_ONLY) is BASIC_ONLY
        return

    with pytest.raises(OnyxError) as excinfo:
        await _call_gate_1(key, BASIC_ONLY)
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_denial_is_authorization_not_payment() -> None:
    """Error semantics: an unauthorized TON user must never be told to buy a
    plan for a capability this deployment already owns."""
    with pytest.raises(OnyxError) as excinfo:
        await _call_gate_1("POST /manage/admin/user-group", BASIC_ONLY)

    error = excinfo.value
    assert error.status_code == 403
    assert error.error_code.code == "INSUFFICIENT_PERMISSIONS"
    detail = str(error.detail).lower()
    for commercial_word in ("plan", "business", "enterprise", "upgrade", "license"):
        assert commercial_word not in detail


@pytest.mark.asyncio
async def test_scoped_authority_did_not_become_global_authority() -> None:
    """A group manager holds MANAGE_USER_GROUPS as SCOPED, never GLOBAL. GATE 1
    admits them only where `allow_scope=True`."""
    assert _holds_scoped_but_not_global(SCOPED_MANAGER)

    # allow_scope route: reachable.
    assert (
        await _call_gate_1(
            "PATCH /manage/admin/user-group/{user_group_id}", SCOPED_MANAGER
        )
        is SCOPED_MANAGER
    )

    # global-only routes: refused at GATE 1.
    for key in (
        "POST /manage/admin/user-group",
        "DELETE /manage/admin/user-group/{user_group_id}",
        "PUT /manage/admin/user-group/{user_group_id}/permissions",
    ):
        with pytest.raises(OnyxError):
            await _call_gate_1(key, SCOPED_MANAGER)


def _holds_scoped_but_not_global(user: User) -> bool:
    return has_permission(
        user, Permission.MANAGE_USER_GROUPS
    ) is PermissionAuthority.SCOPED and not has_global_permission(
        user, Permission.MANAGE_USER_GROUPS
    )


def test_scoped_manager_gate_2_stays_bounded_by_managed_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GATE 2 is the authorization of record for a scoped manager. In scope
    passes; out of scope raises; a global holder is unrestricted."""
    managed_group_id = 11
    other_group_id = 22

    def fake_managed_group_ids(user: User, _db: Any) -> set[int]:
        # Mirrors the real query: only a manager edge yields a managed group.
        return {managed_group_id} if user.is_group_manager else set()

    monkeypatch.setattr(
        scoped_permissions, "fetch_managed_group_ids", fake_managed_group_ids
    )
    db_session = MagicMock()

    assert scoped_permissions.manages_group(
        SCOPED_MANAGER, db_session, group_id=managed_group_id
    )
    assert not scoped_permissions.manages_group(
        SCOPED_MANAGER, db_session, group_id=other_group_id
    )

    scoped_permissions.assert_manages_group(
        SCOPED_MANAGER, db_session, group_id=managed_group_id
    )
    with pytest.raises(OnyxError):
        scoped_permissions.assert_manages_group(
            SCOPED_MANAGER, db_session, group_id=other_group_id
        )

    # A global holder is not narrowed by the managed set.
    assert scoped_permissions.manages_group(
        GROUPS_ADMIN, db_session, group_id=other_group_id
    )
    # A member who manages nothing is refused even in a group they belong to.
    assert not scoped_permissions.manages_group(
        BASIC_ONLY, db_session, group_id=managed_group_id
    )


# ---------------------------------------------------------------------------
# 7. Intended TON deployment state: no license, no subscription
# ---------------------------------------------------------------------------


def test_no_license_resolves_to_community_tier() -> None:
    """TON runs with no license row. Tier resolution is a local read that lands
    on COMMUNITY; it never contacts an entitlement service."""
    assert ee_tier.tier_from_license_metadata(None) is Tier.COMMUNITY


def test_license_enforcement_stays_at_its_secure_default() -> None:
    """Plan 007 invariant. The default keeps the EE implementation tree loaded,
    which is what computes group-aware document ACLs. 008a must not need to
    change it."""
    assert variable_functionality._LICENSE_ENFORCEMENT_ENABLED is True


def test_legacy_paid_flag_stays_unset() -> None:
    """`ENABLE_PAID_ENTERPRISE_EDITION_FEATURES=true` with no license drives the
    whole application into GATED_ACCESS."""
    assert ENTERPRISE_EDITION_ENABLED is False


def test_deployment_stays_single_tenant() -> None:
    assert MULTI_TENANT is False


# ---------------------------------------------------------------------------
# 8. EE dispatch invariant — group-aware document ACLs must keep running
# ---------------------------------------------------------------------------


@pytest.fixture
def ee_dispatch_active() -> Iterator[None]:
    """Force the runtime state a TON deployment boots into, and leave the
    process exactly as it was found. `fetch_versioned_implementation` is
    lru_cached, so the cache has to be cleared on both sides."""
    was_ee = global_version.is_ee_version()
    fetch_versioned_implementation.cache_clear()
    global_version.set_ee()
    try:
        yield
    finally:
        if not was_ee:
            global_version.unset_ee()
        fetch_versioned_implementation.cache_clear()


def test_default_env_loads_the_ee_implementation_tree(
    ee_dispatch_active: None,
) -> None:
    del ee_dispatch_active
    assert global_version.is_ee_version() is True


@pytest.mark.parametrize(
    "attribute",
    [
        "_get_acl_for_user",
        "_get_access_for_documents",
        "get_access_for_user_files_impl",
        "build_access_for_user_files_impl",
    ],
)
def test_access_control_still_dispatches_to_ee(
    attribute: str, ee_dispatch_active: None
) -> None:
    """The most dangerous possible regression in this transformation is a silent
    fallback to the CE access implementation: it drops group ACLs and fails
    open at the index layer."""
    del ee_dispatch_active
    resolved = fetch_versioned_implementation("onyx.access.access", attribute)
    assert resolved.__module__ == "ee.onyx.access.access"
    assert resolved is not ce_access.__dict__.get(attribute)


def test_ee_user_acl_includes_group_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """`user -> group membership -> group ACL` still resolves, and the CE
    email/public entries survive alongside it."""
    member = _user(permissions=[Permission.BASIC_ACCESS], email="member@vn.example")
    monkeypatch.setattr(
        ee_access,
        "fetch_user_groups_for_user",
        lambda _db, _uid: [SimpleNamespace(name="Frota")],
    )
    monkeypatch.setattr(
        ee_access, "fetch_external_groups_for_user", lambda _db, _uid: []
    )

    acl = ee_access._get_acl_for_user(member, MagicMock())

    assert prefix_user_group("Frota") in acl
    assert prefix_user_email("member@vn.example") in acl
    assert PUBLIC_DOC_PAT in acl


def test_ce_user_acl_has_no_group_entries() -> None:
    """States the cost of losing EE dispatch, so the invariant above is not
    mistaken for a formality."""
    member = _user(permissions=[Permission.BASIC_ACCESS], email="member@vn.example")

    acl = ce_access._get_acl_for_user(member, MagicMock())

    assert acl == {prefix_user_email("member@vn.example"), PUBLIC_DOC_PAT}
    assert not any(entry.startswith("group:") for entry in acl)


def test_anonymous_user_still_sees_only_public_documents() -> None:
    """Public/email document access is unchanged by this slice."""
    anonymous = _user(permissions=[], email="anonymous@onyx.app")
    anonymous.id = ANONYMOUS_USER_UUID  # ty: ignore[invalid-assignment]

    assert ce_access._get_acl_for_user(anonymous, MagicMock()) == {PUBLIC_DOC_PAT}


def test_group_ee_dispatch_needs_no_onyx_hosted_service() -> None:
    """The EE group ACL and group DB modules resolve against local
    infrastructure only — no Onyx-operated host appears in either import
    closure."""
    for module in (ee_access, ee_user_group_db):
        source = inspect.getsource(module)
        for host in ("cloud.onyx.app", "telemetry.onyx.app", "stripe", "posthog"):
            assert host not in source.lower()


# ---------------------------------------------------------------------------
# 9. Persona / agent group sharing stays compatible
# ---------------------------------------------------------------------------


def test_persona_group_sharing_has_no_product_tier_gate() -> None:
    """Group sharing is EE-dispatched, not tier-gated. Once groups are reachable
    it works, so Plan 005 can rely on it."""
    for prefix in PATH_PREFIX_MIN_TIER:
        assert "persona" not in prefix
        assert "agent" not in prefix
        assert "document-set" not in prefix


def test_per_group_agent_attachment_is_part_of_the_group_capability() -> None:
    """`PATCH /manage/admin/user-group/{id}/agents` writes `Persona__UserGroup`.
    It sits under the un-gated prefix, so persona group sharing is administrable
    without a paid tier."""
    assert "/manage/admin/user-group/7/agents".startswith(GROUP_CAPABILITY_PREFIX)
    key = "PATCH /manage/admin/user-group/{user_group_id}/agents"
    assert key in GROUP_ROUTE_CONTRACT
    assert GROUP_ROUTE_CONTRACT[key][0] is Permission.MANAGE_USER_GROUPS
