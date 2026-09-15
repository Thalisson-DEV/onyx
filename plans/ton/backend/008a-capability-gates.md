# Plan 008a: Separate TON capability and authorization from commercial tier

> **Executor instructions**: This is the first backend capability slice split out
> of Plan 008. Run it after Plans 001 and 002. It removes the product-tier
> requirement from TON-required local capabilities and changes nothing else.
> Removing a commercial gate must never remove an authorization gate.
>
> **Drift check (run first)**: from the repository root, run `git status --short`
> and `git diff --stat -- backend/ee/onyx/configs backend/onyx/configs`. Stop if
> the gate map or the authorization dependencies differ from
> `plans/ton/capability-edition-audit.md`.

## Status

- **State**: DONE for the P0 Groups/RBAC slice. Branding writes, connector
  auto-sync, query history, usage, analytics and service-account keys stay
  gated by decision, not by omission.
- **Priority**: P0
- **Effort**: S
- **Risk**: HIGH (a mistake here fails open at the index layer)
- **Depends on**: `001-baseline-contracts.md`, `002-security-privacy.md`
- **Blocks**: `005-agents-orchestration.md` (specialist group sharing),
  `006-reports-schedules-admin.md` (group-scoped report ACLs)
- **Category**: security / capability
- **Planned and executed at**: commit `51688f8ead`, 2026-09-15

## Issues to Address

TON is a single-company self-hosted deployment with no paid Onyx entitlement. A
purchased subscription tier must not decide whether a locally implemented
capability exists. Runtime access must depend on:

    feature available + user authorized + tenant valid + resource allowed

and not on a commercial product tier.

The P0 blocker is User Groups plus permission grants. The capability is complete
locally — models, migrations, API, DB layer, sync tasks and admin screens all
exist and run against the deployment's own PostgreSQL — but
`/manage/admin/user-group` was declared `Tier.BUSINESS`, so a no-license
deployment received HTTP 402 on every route. Without groups, TON cannot express
its access model, cannot assign group document ACLs, and cannot share specialist
agents per business unit.

## Important Notes

Facts established before any code changed, all from the capability audit and
re-verified in this slice:

- **Every gate is local.** Tier resolution reads a license row from the local
  PostgreSQL and verifies an RSA signature against a public key shipped in the
  repository. No entitlement service is contacted
  (`backend/ee/onyx/utils/tier.py:73-102`).
- **The gate is declarative and in one place.** 18 path prefixes in
  `PATH_PREFIX_MIN_TIER`, resolved longest-prefix-first by the `tier_gate`
  middleware, which returns 402 `FEATURE_NOT_AVAILABLE`.
- **The EE implementation tree already loads by default.**
  `LICENSE_ENFORCEMENT_ENABLED` defaults to `"true"`, and that alone calls
  `global_version.set_ee()` (`backend/onyx/utils/variable_functionality.py:42-72`).
  Group-aware document ACLs therefore already run. TON does not need to "enable
  EE", and must not disable it.
- **With no license row nothing else gates.** The license middleware takes its
  no-license branch and seat availability is unlimited.
- **Authorization is not role-based.** `UserRole` is a tombstone. The model is
  permission tokens, `PermissionGrant`, `User.effective_permissions`, group
  scoping and `require_permission`.
- **The tier gate ran before authentication.** Confirmed live against the
  running deployment: an unauthenticated `GET /api/manage/admin/user-group`
  returned 402, not 401. The commercial gate was evaluated ahead of the
  authorization gate, which is why removing it changes the error semantics in
  the right direction.

## Implementation strategy

Adapt the existing declarative gating architecture. Do not build a second
authorization system.

1. Keep the upstream gate declaration verbatim as
   `UPSTREAM_PATH_PREFIX_MIN_TIER`.
2. Declare TON's local capabilities in one TON-owned module, each entry naming
   the authorization gate that stays authoritative.
3. Compute the map the middleware enforces as `upstream minus TON capabilities`.
4. Touch nothing else: no middleware change, no license change, no EE dispatch
   change, no authorization change, no migration.

The result is that the four questions stay separate and answerable:

| Question | Answered by |
|---|---|
| Does the feature exist in this deployment? | `onyx/configs/ton_capabilities.py` |
| May this user use it? | `Permission` + group scope (GATE 1 / GATE 2) |
| Is the tenant valid? | tenant contextvars, `MULTI_TENANT=false` |
| Which rows may the user read? | resource ACL / document ACL |

## Files changed

| File | Change |
|---|---|
| `backend/onyx/configs/ton_capabilities.py` | new. TON capability declaration, the `apply_ton_capability_policy` filter, and `ton_capability_policy_drift` for upstream-drift detection. |
| `backend/ee/onyx/configs/license_enforcement_config.py` | upstream map renamed to `UPSTREAM_PATH_PREFIX_MIN_TIER`; `PATH_PREFIX_MIN_TIER` now derives from it through the TON policy. No entry was edited. |
| `backend/tests/unit/ton/test_capability_gates.py` | new. 147 tests: baseline reproduction, post-change behavior, retained gates, the route authorization contract, negative security tests, no-license state, EE dispatch invariant. |
| `backend/tests/external_dependency_unit/ton/{__init__.py,test_group_capability.py}` | new. 6 tests against a disposable PostgreSQL: group + permission-grant lifecycle, scoped-manager boundary in the DB layer, group document ACL, EE dispatch. |
| `plans/ton/backend/008a-capability-gates.md` | new. This document. |
| `plans/ton/backend/roadmap.md` | 008 split into 008a/008b; Plan 005 and 006 now depend on 008a. |
| `plans/ton/backend/README.md` | same split; Plan 002 status drift corrected to DONE. |
| `plans/ton/backend/008-web-only-product.md` | scope note pointing the gate work at 008a. |

No model, no migration, no route, no permission, no middleware and no frontend
file was modified.

## Commercial gate inventory

`PATH / FEATURE · CURRENT REQUIRED TIER · REAL AUTHORIZATION REQUIREMENT · LOCAL
IMPLEMENTATION? · EXTERNAL DEPENDENCY? · TON REQUIRED? · ACTION`

### Changed

| Path / feature | Tier was | Real authorization requirement | Local? | External? | TON needs? | Action |
|---|---|---|---|---|---|---|
| `/manage/admin/user-group` (groups, membership, managers, permission grants, group→agent, group→document-set) | BUSINESS | `READ_USER_GROUPS` / `MANAGE_USER_GROUPS` / `FULL_ADMIN_PANEL_ACCESS` at GATE 1, plus `assert_manages_group` / `assert_within_scope` / `restrict_to_group_ids` at GATE 2 | Yes, fully | No | **Yes, P0** | **PRODUCT TIER REQUIREMENT REMOVED** |

### Inspected and deliberately retained

| Path / feature | Tier | Why retained |
|---|---|---|
| `/admin/enterprise-settings` (branding writes) | BUSINESS | **DEFERRED P1.** TON-FE-001/002 already supply product identity through design tokens, and the final logo asset does not exist yet. Reads are already open at every tier. No TON capability depends on it today. |
| `/admin/query-history`, `/admin/chat-sessions`, `/admin/chat-session-history` | BUSINESS | Not required by this slice. Un-gating exposes full chat content and real user emails even in `ANONYMIZED` mode (masking is read-time only) — a privacy decision, not a formality. |
| `/admin/usage-report` | BUSINESS | Not required. Pattern source for TON reports; the pattern is reusable without un-gating the route. |
| `/analytics/admin`, `/analytics` | BUSINESS / ENTERPRISE | Not required. |
| `/admin/api-key` (service accounts) | BUSINESS | Not required by the TON MVP. |
| `/gateway` | BUSINESS | An OpenAI-compatible API this deployment would serve to third parties. Not needed for chat. |
| `/manage/admin/standard-answer`, `/admin/hooks`, `/admin/token-rate-limits`, `/admin/log-export` | ENTERPRISE | Deferred. |
| `/admin/enterprise-settings/custom-analytics-script` | ENTERPRISE | **Never un-gate.** Injects arbitrary JS into every page. |
| `/admin/enterprise-settings/scim`, `/scim` | ENTERPRISE | SCIM is not required for the TON MVP. |
| `/evals` | ENTERPRISE | Not needed. |
| `require_business_tier_for_sync_access` (`AccessType.SYNC`) | BUSINESS | **DEFERRED, investigated.** Not required for Groups or ACL correctness: group document ACLs come from `UserGroup__ConnectorCredentialPair` and `DocumentSet__UserGroup` on `PUBLIC`/`PRIVATE` connectors, which were never gated. SYNC only mirrors a *source system's* own ACLs. Un-gating it without verifying the external-sync beat entries would create cc-pairs whose permission sync may never run — a silent over-exposure. Revisit only when a Vale Norte source carries its own ACLs. |
| `require_business_tier_for_multi_sso` | BUSINESS | One enabled SSO provider works at every tier. TON needs one. |
| `search_ui_enabled` field check (`onyx/server/settings/api.py`) | BUSINESS | Field-level, outside this slice. |
| `maximum_chat_retention_days` field check | ENTERPRISE | Field-level, outside this slice. |

## Authorization gates preserved

Nothing in the authorization chain was touched. The slice pins it instead.

- **GATE 1** — `require_permission(...)`. Every route on the group router keeps
  its dependency, its permission and its `allow_scope` value.
- **GATE 2** — the authorization of record for a scoped manager:
  `assert_manages_group`, `assert_within_scope`, and `restrict_to_group_ids` /
  `manages_group` on the read paths.
- `allow_scope=False` on create, delete and `set_group_permissions` is itself a
  security decision and is asserted, not just left alone.
- The privilege-amplification guard, `assert_group_config_is_editable`,
  `assert_group_membership_survives_deletion`, default-group protection, audit
  emission, tenant context and every DB constraint are unchanged.

Route contract pinned by `test_capability_gates.py`:

| Method + path | Permission | `allow_scope` | GATE 2 |
|---|---|---|---|
| GET `/manage/admin/user-group` | `READ_USER_GROUPS` | yes | `get_scoped_groups` + `restrict_to_group_ids` + `manages_group` |
| GET `/manage/admin/user-group/{id}` | `READ_USER_GROUPS` | yes | `manages_group` |
| GET `/manage/user-groups/minimal` | `BASIC_ACCESS` | no | own membership via `fetch_user_groups_for_user` |
| GET `/manage/admin/permissions/registry` | `FULL_ADMIN_PANEL_ACCESS` | no | global |
| GET `/manage/admin/user-group/{id}/permissions` | `MANAGE_USER_GROUPS` | no | global |
| PUT `/manage/admin/user-group/{id}/permissions` | `FULL_ADMIN_PANEL_ACCESS` | no | global |
| POST `/manage/admin/user-group` | `MANAGE_USER_GROUPS` | no | global by design |
| PATCH `/manage/admin/user-group/rename` | `MANAGE_USER_GROUPS` | yes | `assert_manages_group` |
| PATCH `/manage/admin/user-group/{id}/incognito` | `FULL_ADMIN_PANEL_ACCESS` | no | global |
| PATCH `/manage/admin/user-group/{id}` | `MANAGE_USER_GROUPS` | yes | `assert_manages_group` in `update_user_group` + `assert_within_scope` on cc-pairs |
| POST `/manage/admin/user-group/{id}/add-users` | `MANAGE_USER_GROUPS` | yes | `assert_manages_group` in `add_users_to_user_group` |
| DELETE `/manage/admin/user-group/{id}` | `MANAGE_USER_GROUPS` | no | global by design |
| PATCH `/manage/admin/user-group/{id}/agents` | `MANAGE_USER_GROUPS` | yes | `assert_manages_group` |
| PATCH `/manage/admin/user-group/{id}/document-sets` | `MANAGE_USER_GROUPS` | yes | `assert_manages_group` + `assert_within_scope` |
| PUT `/manage/admin/user-group/{id}/manager` | `MANAGE_USER_GROUPS` | yes | `assert_manages_group` |

## Groups API behavior, before and after

Both measured with `Tier.COMMUNITY`, the tier a no-license TON deployment
resolves.

**Before** — reproduced at the baseline commit through the real middleware, and
observed live against the running deployment:

```text
GET  /api/manage/admin/user-group            -> 402 FEATURE_NOT_AVAILABLE
     detail: "This feature requires the Business plan."
     required_tier: "business"
```

Every subpath behaved the same, and the gate fired before authentication.

**After** — the request reaches the handler and `require_permission` decides:

| Caller | Result |
|---|---|
| admin (`FULL_ADMIN_PANEL_ACCESS`) | reaches every route |
| global `MANAGE_USER_GROUPS` holder | reaches every route |
| scoped group manager | reaches the `allow_scope` routes only, then bounded by GATE 2 |
| `BASIC_ACCESS`-only user | 403 `INSUFFICIENT_PERMISSIONS` on every admin route |
| unauthenticated | 401 at the auth dependency |

No tier is resolved for these paths at all, so the decision reads no Redis key,
no license row and no network.

## Error semantics

A TON user who lacks authorization now receives `403 INSUFFICIENT_PERMISSIONS`
with no commercial vocabulary. The test asserts the detail contains none of
"plan", "business", "enterprise", "upgrade" or "license".

## Scoped manager invariant

Scoped authority did not become global authority.

- A group manager resolves `MANAGE_USER_GROUPS` as `SCOPED`, never `GLOBAL`.
- GATE 1 admits them only where `allow_scope=True`; create, delete and
  permission changes still refuse them.
- GATE 2 bounds them to groups they manage: in scope passes, out of scope
  raises, an empty managed set fails closed, and a plain member of a group is
  refused.
- A global holder is not narrowed by the managed set.

## Group document ACL verification

The chain `user -> group membership -> group ACL -> document access filter` is
unchanged and asserted:

- the EE `_get_acl_for_user` returns `group:<name>` alongside
  `user_email:<addr>` and `PUBLIC_DOC_PAT`;
- the CE implementation returns only the email and public entries, which is
  exactly what a fallback would cost;
- an anonymous user still resolves to `{PUBLIC_DOC_PAT}` only.

No user gains access to a document because a commercial gate was removed: the
gate never contributed to `access_control_list` computation.

## EE dispatch invariant

The most dangerous possible regression in this transformation is a silent
fallback from EE to CE access control. It fails **open**, quietly, at the index
layer. Asserted:

- `LICENSE_ENFORCEMENT_ENABLED` is at its `true` default;
- `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` is unset/false, so the deployment
  never enters `GATED_ACCESS`;
- `MULTI_TENANT` is false, so no control-plane call is possible;
- `fetch_versioned_implementation("onyx.access.access", X)` resolves to
  `ee.onyx.access.access` for `_get_acl_for_user`,
  `_get_access_for_documents`, `get_access_for_user_files_impl` and
  `build_access_for_user_files_impl`.

## Persona / agent group sharing

Verified compatible, nothing changed:

- no `PATH_PREFIX_MIN_TIER` entry mentions personas, agents or document sets, so
  persona group sharing has **no independent product-tier gate**. It is
  EE-dispatched (`ee/onyx/db/persona.py`), and EE loads by default;
- `Persona__UserGroup` is administrable through
  `PATCH /manage/admin/user-group/{id}/agents`, which sits under the un-gated
  prefix, so group sharing becomes reachable as a direct consequence of this
  slice with no extra change;
- `Persona.owner_group_id`, `DocumentSet__UserGroup`, `Credential__UserGroup`,
  `LLMProvider__UserGroup` and `UserGroup__ConnectorCredentialPair` all become
  assignable through the same routes.

Plan 005 can therefore rely on group-scoped specialists.

## No-license behavior

The intended TON deployment state — no license row, no subscription,
`MULTI_TENANT=false`, `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` unset, EE
dispatch active — is asserted directly:

- `tier_from_license_metadata(None)` is `Tier.COMMUNITY`;
- at `Tier.COMMUNITY` an authorized administrator reaches every group route;
- the retained gates still return 402 at `Tier.COMMUNITY`, so nothing widened.

## External Onyx dependencies

None are contacted by this capability. Group requests no longer resolve a tier,
so they touch no license cache and no license row; the group ACL and group DB
modules reference no Onyx-operated host, Stripe or PostHog. Asserted by test.

## Frontend follow-up required

**Not executed here. This is a backend slice.** The backend endpoint is usable —
`/admin/groups` resolves on direct navigation and the Groups page itself does not
consult the tier for group CRUD — so no frontend change was needed to unblock
the capability.

The frontend still mirrors the old commercial gate. Narrow follow-up, to be run
with TON-FE-004 or as TON-CAP-002:

| File | Current | Follow-up |
|---|---|---|
| `web/src/lib/admin-routes.ts` | `ADMIN_ROUTES.GROUPS.requiredTier = Tier.BUSINESS` | set to `null` so the sidebar entry stops rendering disabled with an unavailability tooltip |
| `web/src/lib/permissions/hooks.ts` | `useCanManageGroups()` returns `useTierAtLeast(Tier.BUSINESS)` | derive from `MANAGE_USER_GROUPS` authority (global or scoped) via `adminCapabilities`; the docstring's "below Business the endpoint 402s" is now false |
| `web/src/ton/ton-product-surface.test.tsx` | asserts `GROUPS.requiredTier === Tier.BUSINESS` | repoint the "tier mechanism intact" assertion at a route that is still Business-gated, e.g. `SERVICE_ACCOUNTS` |
| `web/src/components/GroupsMultiSelect.tsx`, `IsPublicGroupSelector.tsx`, `sections/modals/languageModels/shared.tsx`, `credentials/components/CreateCredential.tsx`, `sections/agents/AgentCard.tsx`, `views/admin/AgentsPage/AgentRowActions.tsx`, `views/AgentEditorPage.tsx` | gate group pickers and agent group-sharing on `useTierAtLeast(Tier.BUSINESS)` | replace the availability check with the permission check; keep every permission check |
| `web/tests/e2e/global-setup.ts` | fails when the user-group endpoint 402s | works unmodified once the backend change is deployed; the documented temporary skip can be dropped |

Hiding or showing a surface never grants access. The backend refuses
unauthorized direct navigation either way.

## Branding gate decision

**DEFERRED P1.** `/admin/enterprise-settings` keeps its Business requirement.
TON does not currently need the API to persist app name, theme or logo: FE-001
and FE-002 already deliver product identity through design tokens, and the final
logo asset does not exist (ADR-009). When it is needed, the change is the same
one-line addition to `TON_LOCAL_CAPABILITIES`, and it must keep
`FULL_ADMIN_PANEL_ACCESS` on writes, keep the `.png/.jpg/.jpeg` upload
restriction and the appearance-field length clamps, and must **not** un-gate
`custom-analytics-script`, which longest-prefix matching already keeps at
ENTERPRISE.

## Tests

Named spec: `backend/tests/unit/ton/test_capability_gates.py`. Unit-only by
design — no external service, no database write, nothing that could touch the
live deployment.

| Group | What it proves |
|---|---|
| capability policy | the declaration is exactly the group prefix; every entry names its surviving gate; the enforced map is upstream minus exactly the declared prefixes; the filter is pure |
| upstream drift | fails if upstream renames, removes or nests a gated prefix under a TON capability |
| baseline | the real middleware against the unmodified upstream map returns 402 with `required_tier: business` for every group path |
| after | at `Tier.COMMUNITY` every group path reaches the handler, under any API prefix, with no tier resolution at all |
| retained gates | every remaining prefix still returns 402 at community tier, curated and exhaustively |
| non-path gates | `AccessType.SYNC` and multi-SSO still raise; `PUBLIC`/`PRIVATE` still pass |
| route contract | the router surface is fully enumerated; every route keeps its permission, its `allow_scope` value and a non-anonymous base user; every `allow_scope` route names a GATE 2 check that is present in the handler or its DB delegate |
| negative security | a `BASIC_ACCESS`-only user is refused on every admin group route with 403 and no commercial wording; a scoped manager is refused on create/delete/permissions; GATE 2 keeps them inside their managed groups |
| no-license state | community tier resolution, license-enforcement default, legacy flag unset, single-tenant |
| EE dispatch | EE tree loaded; all four access functions resolve to `ee.onyx.access.access`; EE ACL includes group entries; CE ACL does not; anonymous stays public-only; no Onyx-hosted host in the group path |
| persona sharing | no persona/agent/document-set prefix is tier-gated; per-group agent attachment sits under the un-gated prefix |

Second named spec:
`backend/tests/external_dependency_unit/ton/test_group_capability.py`. Runs the
production EE DB functions against a **disposable** PostgreSQL, never a live
deployment database, and proves the capability works with no license row:

| Test | What it proves |
|---|---|
| `test_deployment_has_no_license_row` | states the premise: `select count(*) from license` is 0 |
| `test_admin_configures_group_and_member_gains_exactly_granted_permissions` | group create, `PermissionGrant` set/revoke, membership; the member gains exactly the granted tokens and never `FULL_ADMIN_PANEL_ACCESS` |
| `test_scoped_manager_adds_users_only_inside_a_managed_group` | a manager of one group adds members there and is refused on another; no out-of-scope membership row is written |
| `test_plain_member_cannot_edit_group_membership` | group membership alone is not authority; only a manager edge is |
| `test_group_membership_reaches_the_document_access_filter` | a member's ACL contains `group:<name>`, a non-member's does not, and email/public entries are unchanged |
| `test_acl_computation_runs_the_ee_implementation` | the versioned dispatch resolves to `ee.onyx.access.access` against real rows |

Existing suites that cover the same boundary and were re-run:
`tests/unit/ee/onyx/server/middleware/test_tier_gate.py`,
`tests/unit/ee/onyx/server/settings/test_license_enforcement_settings.py`,
`tests/external_dependency_unit/tier/test_tier_order.py` (parametrized off the
map, so it follows the change),
`tests/external_dependency_unit/auth/` (including `test_scoped_permissions.py`
and `test_sso_admin_api.py::test_second_enabled_provider_requires_business_tier`,
which confirms the multi-SSO commercial gate still fires),
`tests/external_dependency_unit/db/test_agent_sharing_permissions.py`,
`test_recompute_permissions.py`, `test_groupless_creator_fallback.py`.

### Checks executed

| Check | Result |
|---|---|
| `pytest tests/unit/ton/test_capability_gates.py` | 147 passed |
| `pytest tests/unit/ton` | 275 passed, 1 pre-existing failure (`test_contract_matrix.py` looks for `plans/ton/decision-log.md`; the file is at `plans/ton/backend/decision-log.md` — Plan 001/002 documentation drift, already recorded by Plan 007) |
| `pytest tests/unit/ton tests/unit/ee` | 1254 passed; 35 pre-existing failures, all `ModuleNotFoundError: No module named 'litellm'` in the gateway suite, plus the one documentation-drift failure |
| `pytest tests/unit` (whole suite) | 8605 passed, 33 skipped, 185 failed. Every failure cause is an environment gap on this Windows checkout: missing `litellm` (140), Windows file semantics (`[Errno 22]`, `os.O_DIRECTORY`, `cp1252` decode), and Redis absent on `localhost:6379`. None involve tiers, gates, groups, permissions or ACLs. Full-suite baseline re-run was not performed. |
| `pytest tests/external_dependency_unit/{ton,auth,tier}` + persona sharing, recompute, groupless fallback — disposable PostgreSQL 15.2 + Redis 7 | **203 passed, 8 skipped, 0 failed** |
| Baseline probe at `51688f8ead` in a detached `git worktree` | every group path returned 402 `FEATURE_NOT_AVAILABLE`, `required_tier: business` |
| Live running deployment, unauthenticated `GET /api/manage/admin/user-group` through the frontend | 402 — the commercial gate fired ahead of authentication |
| `ruff check` / `ruff format --check` on all changed and new files | clean |
| `ty check` on all changed and new files | clean |

Environment notes: `uv run` cannot build this project on this Windows host (the
`chonkie` C extension needs MSVC), so Python ran from the repository `.venv`, as
Plan 007 also did. `pytest` ran with `-p no:cacheprovider` because the cache
directory is not writable.

## Done criteria

- [x] `/manage/admin/user-group` no longer requires a product tier.
- [x] Every authorization gate on the group router is unchanged and pinned.
- [x] An unauthorized user receives 403, never 402, and no commercial wording.
- [x] Scoped managers remain scoped; scoped never becomes global.
- [x] Group-aware document ACLs still come from the EE implementation.
- [x] The no-license, single-tenant, EE-dispatched deployment state is asserted.
- [x] No external Onyx service is required by the capability.
- [x] No migration, no schema change, no live DB write.
- [x] No TON domain schema, no agent orchestration, no FE-004+ work.
- [x] Retained and deferred gates are recorded with reasons.

## STOP conditions

- Stop if group functionality is found to depend on a remote Onyx service.
- Stop if un-gating requires disabling EE dispatch, a global license bypass, a
  fabricated license, or `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES=true`.
- Stop if a permission or scope check has to move or weaken.
- Stop if a migration becomes necessary. The live database still references
  unknown Alembic revision `6e8f0a2b1c35`; 008a is migration-free.
- Stop if any test shows access becoming broader than before.

None of these triggered.

## Remaining capability gaps

**P0, carried forward**

1. TON has no per-resource ACL model for contracts, Findings, Occurrences and
   Reports (TON-CAP-006, needs Plan 003). The pattern to copy is
   `Persona__UserGroup` plus the GATE 1 / GATE 2 contract.
2. `LLMProvider.custom_config` still stores provider secrets as plaintext JSONB
   (SECURITY-08 / TON-SEC-007-A). Unchanged by this slice and still blocked on
   the Alembic prerequisite.

**P1**

3. Branding writes remain gated (decision above).
4. No queryable audit trail exists; `onyx/utils/audit.py` emits to stdout only.
5. `UserProject` has no sharing model.
6. The frontend still mirrors the commercial gate for group affordances (table
   above).

**P2 / P3**

7. Query history, usage reports, service-account keys, chat retention limit,
   per-group LLM restriction, connector auto-sync, analytics, hooks, standard
   answers, log export, token rate limits — all retained deliberately.

## Maintenance notes

When upstream changes `UPSTREAM_PATH_PREFIX_MIN_TIER`, `test_capability_gates.py`
is the gate: `ton_capability_policy_drift` fails on a renamed, removed or nested
prefix, and the exhaustive retained-gate test fails if anything else becomes
free. Add a capability to `TON_LOCAL_CAPABILITIES` only with its surviving
authorization gate named, and add the corresponding route contract entries in
the same change.
