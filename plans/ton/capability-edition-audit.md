# TON capability, edition boundary and entitlement audit

Read-only audit. No product code was changed. Discovery and planning only.

- Audited at commit `d49ea04e09`.
- Scope: `backend/onyx`, `backend/ee`, `web/src`, `deployment`, `plans/ton`.
- Authorization premise: the project owner may use, modify, adapt and ship all
  code in this repository, including `ee` paths. License text is not a blocker.
- The only question this audit answers is technical: can the capability run
  self-hosted with zero recurring Onyx payment?

## Executive answer

Yes. TON can operate indefinitely with zero paid Onyx entitlement, after a small
set of controlled local changes.

Three facts carry that conclusion:

1. **Every gate is local.** Tier resolution for a self-hosted deployment reads a
   license row from the local PostgreSQL and verifies an RSA signature against a
   public key file shipped in the repository
   (`backend/ee/onyx/utils/license.py:110-234`,
   `backend/ee/onyx/utils/tier.py:73-102`). No entitlement server is contacted.
2. **The gated surface is small and declarative.** Exactly 18 path prefixes are
   gated, all listed in one dictionary
   (`backend/ee/onyx/configs/license_enforcement_config.py:76-95`). Everything
   else is ungated at every tier.
3. **The gated capabilities are already implemented locally.** User groups, RBAC
   grants, query history, usage reports, analytics and enterprise/branding
   settings all persist in local tables and run against local PostgreSQL, Redis,
   OpenSearch and the local file store. They are commercially gated, not
   technically absent.

The material exception is **document ACLs by user group**. Group-aware ACL
computation lives only in `backend/ee/onyx/access/access.py`. TON keeps it by
running the EE code tree, which is the default (see the `LICENSE_ENFORCEMENT_ENABLED`
finding below). No payment is involved.

## Correction to a common assumption in the existing TON plans

**This fork no longer uses `UserRole` for authorization.** `UserRole` is an
explicit tombstone kept only as the column type for `User.role`, which is never
read or written (`backend/onyx/auth/schemas.py:11-24`,
`backend/onyx/db/models.py:338-341`). `current_admin_user` and
`current_curator_or_admin_user` do not exist anywhere in the backend.

Authorization is a **permission-token model**:

- `Permission` — 30 tokens, `backend/onyx/db/enums.py:640-716`.
- `PermissionAuthority` — `GLOBAL | SCOPED | NONE`, `enums.py:717-729`.
- `User.effective_permissions` — JSONB column, the actual grant store,
  `backend/onyx/db/models.py:429-435`.
- `PermissionGrant` — `(group_id, permission)`, the group→permission bridge,
  `models.py:5027-5090`.
- `require_permission(...)` — the only role-enforcing FastAPI dependency,
  `backend/onyx/auth/permissions.py:322-365`.

This matters directly for Plan 005, which says "do not assume its current role
names are the TON policy" (`plans/ton/backend/005-agents-orchestration.md:39-45`).
That instruction is correct, and the reason is stronger than the plan states:
there are no roles to assume. There are permission tokens plus group scoping,
which is a better fit for the TON access model than roles would have been.

## The entitlement mechanism, traced end to end

### Which code tree runs

```python
# backend/onyx/utils/variable_functionality.py:42-45
_LICENSE_ENFORCEMENT_ENABLED = (
    os.environ.get("LICENSE_ENFORCEMENT_ENABLED", "true").lower() == "true"
)
```

`set_is_ee_based_on_env_variable()` (`:47-72`) sets `global_version.set_ee()` when
either `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` **or**
`LICENSE_ENFORCEMENT_ENABLED` is true. The second defaults to `"true"`.

**Consequence: every default deployment already runs the `ee.*` code tree.** It
simply resolves to `Tier.COMMUNITY` and returns 402 on the 18 gated prefixes.
This is the single most useful fact in the audit: TON does not need to "enable EE".
EE code is already loaded and already serving group-aware ACLs.

CE→EE dispatch is a runtime module-path rewrite with an MIT fallback
(`fetch_versioned_implementation`, `:76-132`; `fetch_ee_implementation_or_noop`,
`:171-200`).

### Which tier is resolved

```python
# backend/ee/onyx/utils/tier.py:130-133
def get_tier(tenant_id: str | None = None) -> Tier:
    if not MULTI_TENANT:
        return _self_hosted_tier()
```

`_self_hosted_tier()` (`:73-102`) reads cached license metadata from Redis, falls
back to the local `license` table, and maps it with
`tier_from_license_metadata` (`:52-70`). Missing table or DB error →
`Tier.COMMUNITY`. **No network call.**

Two documented escape hatches exist in upstream code:

- `LICENSE_ENFORCEMENT_ENABLED=false` → `_self_hosted_tier()` returns
  `Tier.ENTERPRISE` when EE code is loaded (`tier.py:74-81`), and
  `apply_license_status_to_settings` sets `ee_features_enabled = True`
  (`backend/ee/onyx/server/settings/api.py:82-89`). But it also unloads EE via
  `set_is_ee_based_on_env_variable` unless the legacy flag is set, and it disables
  the EE beat entries. Not a clean TON answer on its own.
- A legacy license lacking `customer_tier` resolves to `Tier.ENTERPRISE` for
  back-compat (`tier.py:66-69`).

### Where the 402 comes from

Three sites, all EE middleware, all self-contained:

```python
# backend/ee/onyx/server/middleware/tier_gate.py:100-112
payload = OnyxErrorCode.FEATURE_NOT_AVAILABLE.detail(
    f"This feature requires the {required.value.title()} plan.")
payload["required_tier"] = required.value
return JSONResponse(status_code=OnyxErrorCode.FEATURE_NOT_AVAILABLE.status_code,
                    content=payload)
```

`FEATURE_NOT_AVAILABLE.status_code` is 402. This is the exact source of the
"endpoint de grupos exigiu o plano Business e retornou 402" already recorded in
`plans/ton/frontend/implementation-roadmap.md`. The declaration is one line:

```python
# backend/ee/onyx/configs/license_enforcement_config.py:83
"/manage/admin/user-group": Tier.BUSINESS,  # groups + RBAC
```

The other two 402 sites are license-state, not feature-tier
(`backend/ee/onyx/server/middleware/license_enforcement.py:189` seat limit,
`:221` expired license). Both require a license row to exist. **With no license
at all, neither fires** — `is_gated = False` on the no-license branch (`:201-213`).

### The one real hazard

```python
# backend/ee/onyx/server/settings/api.py:126-131
else:
    # No license found in cache or DB.
    if ENTERPRISE_EDITION_ENABLED:
        settings.application_status = _BLOCKING_STATUS   # GATED_ACCESS
    settings.ee_features_enabled = False
```

Setting `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES=true` **without** a license puts
the whole application into `GATED_ACCESS`, which the license middleware then 402s
outside its allowlist and `ProductGatingWrapper` locks in the UI. **TON must
leave that flag unset.** Record this as a deployment invariant.

### Seat limits without a license

```python
# backend/ee/onyx/db/license.py:495-499
metadata = get_license_metadata(db_session, tenant_id)
# No license = no enforcement (self-hosted without license)
if metadata is None:
    return SeatAvailabilityResult(available=True)
```

Unlimited users with no license. No user-count cost.

## The complete gated surface

`PATH_PREFIX_MIN_TIER`, `backend/ee/onyx/configs/license_enforcement_config.py:76-95`.
Longest-prefix-wins via `_SORTED_GATES` (`tier_gate.py:41-45`).

| Prefix | Tier | Capability | Local implementation exists? | TON relevance |
|---|---|---|---|---|
| `/manage/admin/user-group` | BUSINESS | User groups + permission grants + group scoping | Yes, fully | **P0 — required** |
| `/admin/enterprise-settings` | BUSINESS | Branding, app name, logo, appearance | Yes, fully | **P1 — required** |
| `/admin/query-history` | BUSINESS | Query history read + CSV export | Yes, fully | P2 — pattern source |
| `/admin/chat-sessions` | BUSINESS | Per-user session list | Yes, fully | P2 |
| `/admin/chat-session-history` | BUSINESS | Paginated session history | Yes, fully | P2 |
| `/admin/usage-report` | BUSINESS | Usage report generate/list/download | Yes, fully | P2 — pattern source |
| `/analytics/admin` | BUSINESS | Query/user/bot/persona analytics | Yes, fully | P3 |
| `/admin/api-key` | BUSINESS | Service-account API keys | Yes, fully | P2 |
| `/gateway` | BUSINESS | OpenAI-compatible API **Onyx exposes** | Yes, fully | P2 (Craft dependency) |
| `/analytics` | ENTERPRISE | Non-admin assistant stats | Yes, fully | P3 |
| `/admin/enterprise-settings/custom-analytics-script` | ENTERPRISE | Third-party JS injection | Yes | **NOT_NEEDED** |
| `/admin/enterprise-settings/scim` | ENTERPRISE | SCIM token management | Yes | NOT_NEEDED |
| `/scim` | ENTERPRISE | SCIM 2.0 protocol | Yes | NOT_NEEDED |
| `/manage/admin/standard-answer` | ENTERPRISE | Canned answers | Yes | DEFER |
| `/admin/token-rate-limits` | ENTERPRISE | Token/cost budgets | Yes | P3 |
| `/admin/hooks` | ENTERPRISE | Outbound webhooks | Yes | DEFER |
| `/admin/log-export` | ENTERPRISE | Deployment log bundles | Yes | P3 |
| `/evals` | ENTERPRISE | Eval pipeline | Yes | NOT_NEEDED |

Two additional gates are **not** path-based and are easy to miss:

- `require_business_tier_for_sync_access` — blocks `AccessType.SYNC` connectors at
  create time (`backend/ee/onyx/utils/tier.py:168-189`), called from
  `backend/onyx/db/connector_credential_pair.py:763-777`.
- `require_business_tier_for_multi_sso` — blocks a *second* simultaneously enabled
  SSO provider (`tier.py:192-202`). One provider works at every tier.
- Chat retention limit is an ENTERPRISE **field-level** check inside the CE
  settings handler (`backend/onyx/server/settings/api.py:117-125`). CE therefore
  retains chat history indefinitely, because the TTL deletion task is EE-only
  (`backend/ee/onyx/background/celery/tasks/ttl_management/tasks.py:147-190`).

### Never gated (community tier, no license, works today)

Chat, search, streaming, personas/agents including private/public/user-sharing,
document sets, projects, user files, incognito files, connectors, indexing,
LLM providers, tools/MCP/OpenAPI actions, Slack and Discord bots, web search,
image generation, voice, code interpreter, users administration, SSO providers
(one enabled), security hardening, tracing, index settings, document explorer,
Craft, scheduled tasks, all Celery workers and beat entries, FileStore, audit
logging.

## External Onyx dependencies

Every runtime reference to an Onyx-operated host, classified.

| Dependency | Location | Class | Blocks TON? |
|---|---|---|---|
| `https://telemetry.onyx.app/anonymous_telemetry` | `backend/onyx/utils/telemetry.py:35` | TELEMETRY ONLY | No. Daemon thread, 5 s timeout, double exception swallow (`:157-170`). `DISABLE_TELEMETRY` early-returns (`:120-122`). |
| `https://cloud.onyx.app/api` (`CLOUD_DATA_PLANE_URL`) | `backend/ee/onyx/configs/app_configs.py:170-173`; used `ee/onyx/utils/license.py:438` | COMMERCIAL GATE ONLY | No. Only reachable for `LicenseSource.AUTO_FETCH` licenses. TON has no license, so never called. |
| `CONTROL_PLANE_API_BASE_URL` | `backend/onyx/configs/app_configs.py:1912-1915`, default `http://localhost:8082` | UNUSED IN TON | No. Only `ee/onyx/server/tenants/*`, registered `if MULTI_TENANT` (`ee/onyx/main.py:167-170`). |
| `https://us.i.posthog.com` | `onyx/configs/app_configs.py:162` | TELEMETRY ONLY | No. Inert without `POSTHOG_API_KEY`. **Caveat below.** |
| `HUBSPOT_TRACKING_URL` | `ee/onyx/configs/app_configs.py:158` | TELEMETRY ONLY | No. Unset by default. |
| `onyx-stripe-public.s3.amazonaws.com/publishable-key.txt` | `onyx/configs/app_configs.py:2207-2210` | COMMERCIAL GATE ONLY | No. Billing UI only. |
| `AUTO_LLM_CONFIG_URL` → `raw.githubusercontent.com/onyx-dot-app/onyx/.../recommended-models.json` | `onyx/configs/app_configs.py:1853-1856` | OPTIONAL | No. Same JSON ships in-repo. Only providers with `is_auto_mode=True` use it. Beat entry added only `if AUTO_LLM_CONFIG_URL`. |
| `https://docs.onyx.app/*`, `onyx.app` referer header, crawler UA, pricing link in cancellation email | `web/src/lib/constants.ts:13`; `onyx/llm/factory.py:61`; `onyx/tools/.../onyx_web_crawler.py:35`; `onyx/auth/email_utils.py:345` | OPTIONAL | No. Strings and links, not calls to Onyx services. Already covered by `SHOW_UPSTREAM_LINKS = false`. |
| HuggingFace Hub (embedding/rerank weights) | model server, `backend/model_server/encoders.py` | **REQUIRED on first boot** | Yes, once — unless weights are pre-baked into the image or a model directory is mounted. **Not an Onyx dependency and not a payment.** |

**No `REPLACEMENT REQUIRED` dependency exists for any TON capability.**

One caveat worth flagging: Craft availability consults a PostHog feature-flag
provider (`backend/onyx/server/features/build/utils.py:117-186`). Without PostHog
the provider is a no-op, and I did not verify which way the no-op branch resolves.
If TON wants Craft, confirm that branch; if TON does not want Craft, it is
irrelevant. Plan 008 already forbids making TON depend on PostHog.

## RBAC audit — the exact boundary

The audit asked for fifteen separate answers. Here they are.

| # | Concern | Where | Edition | Persistence | FE gate | BE gate | Local only? | External Onyx? | TON can use directly? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Authentication | `backend/onyx/auth/*` | CE | `user`, `oauth_account`, SSO provider rows, `pat`, API keys | login pages | fastapi-users + PAT + API key ladder (`users.py:2214-2277`) | Yes | No | **Yes** |
| 2 | User model | `models.py:332-452` | CE | `user` table | — | — | Yes | No | **Yes** |
| 3 | Admin role | `Permission.FULL_ADMIN_PANEL_ACCESS`, `enums.py:711` | CE | `user.effective_permissions` JSONB | `hasPermission` | short-circuit to all permissions (`permissions.py:246-248`) | Yes | No | **Yes** |
| 4 | Roles | none — replaced by permission tokens; `UserRole` is a tombstone (`auth/schemas.py:11-24`) | CE | — | — | — | Yes | No | **Yes, and better suited** |
| 5 | Permission scopes | `Permission` (30 tokens) + `IMPLIED_PERMISSIONS` graph, `permissions.py:28-86` | CE | JSONB column | `useUser().permissions` | `require_permission` | Yes | No | **Yes** |
| 6 | User groups | model `models.py:5188-5256`; API `ee/onyx/server/user_group/api.py`; DB `ee/onyx/db/user_group.py` | model CE, API **EE** | `user_group` | `useCanManageGroups()` = tier ≥ BUSINESS (`web/src/lib/permissions/hooks.ts:39-46`) | **BUSINESS tier gate** | Yes | No | **Yes, after gate change** |
| 7 | Group membership | `User__UserGroup` incl. `is_manager`, `models.py:5008-5024` | CE model | `user__user_group` | admin groups page | EE routes | Yes | No | **Yes** |
| 8 | Resource ACLs | CE `onyx/access/access.py:115-142` (email + public); EE `ee/onyx/access/access.py:182-208` (adds groups) | CE base + **EE groups** | OpenSearch `access_control_list` | — | `build_access_filters_for_user`, fail-closed default `frozenset({PUBLIC_DOC_PAT})` (`document_index/interfaces_new.py:187`) | Yes | No | **Yes — EE tree already loaded** |
| 9 | Persona/Agent permissions | `Persona.is_public`, `public_permission`, `Persona__User`, `Persona__UserGroup`, `owner_group_id`; filter `_add_user_filters` `db/persona.py:89-169` | user-sharing CE, **group-sharing EE** | `persona*` tables | `svc.ts:173-199` strips group shares when EE off | CE raises `NotImplementedError` (`db/persona.py:369-375`) | Yes | No | **Yes** |
| 10 | Project permissions | `UserProject`, `models.py:5530-5551` | CE | `user_project` | — | every route `BASIC_ACCESS`, ownership by `user_id` | Yes | No | Owner-only today — **needs TON extension** |
| 11 | File/document permissions | `UserFile` + `collect_user_file_access` (`access.py:203-217`); EE adds group names (`ee/access/access.py:152-181`) | CE base + EE groups | `user_file`, OpenSearch ACL | — | `user_can_access_chat_file` (`access.py:220-270`) | Yes | No | **Yes**, derived via personas |
| 12 | Connector/source permissions | `AccessType` (`enums.py:280`), `Credential__UserGroup`, `UserGroup__ConnectorCredentialPair` | CE models; SYNC gated BUSINESS; external sync **EE** | `connector_credential_pair`, `credential` | admin pages | `require_business_tier_for_sync_access` | Yes | No | PUBLIC/PRIVATE **yes**; SYNC needs gate change |
| 13 | Admin route protection | `web/src/lib/admin-routes.ts` + `ClientLayout.tsx` | CE | — | permission hides, tier disables (`admin-sidebar-utils.ts:211-226`) | per-route `require_permission` | Yes | No | **Yes** |
| 14 | API route protection | `require_permission` + PAT fail-closed routing (`users.py:2199-2212`) | CE | — | — | two-gate: token scope ∧ user authority | Yes | No | **Yes** |
| 15 | Tenant isolation | `MULTI_TENANT`, `POSTGRES_DEFAULT_SCHEMA` (`shared_configs/configs.py:194-202`), schema-per-tenant, `TenantAwareTask` | config shared; **provisioning EE + cloud** | schema per tenant | — | middleware + contextvars | Single-tenant: yes | Provisioning: **yes, control plane** | **Yes** for single-tenant; skip provisioning |

### The two-gate design worth preserving

`require_permission(perm, allow_scope=True)` is **GATE 1** — it lets a scoped group
manager *reach* a handler, never authorizes them. The handler must then apply
**GATE 2**: `assert_within_scope` for writes, `within_managed_scope_clause` for
reads. The docstring is explicit that omitting GATE 2 gives a manager every
resource (`permissions.py:341-347`). Delete and `set_group_permissions` routes
deliberately omit `allow_scope`.

TON must respect this contract in any new domain route it adds. It is the single
highest-risk pattern in the codebase to get wrong.

### Verdict on the TON access model

The required TON roles map onto existing primitives with **no new authorization
machinery**:

| TON role | Mechanism | Notes |
|---|---|---|
| ADMIN | group with `FULL_ADMIN_PANEL_ACCESS` grant | exists |
| CONTROLADORIA | group with a curated `PermissionGrant` set | exists; grants are per-group rows |
| GESTOR / OPERACIONAL | group + `is_manager` on selected groups → SCOPED authority | exists; this is the scoped-manager bundle |
| LEITURA | group with `BASIC_ACCESS` only | exists; `BASIC_ACCESS` implies read/write chat and read search |

Future restrictions, assessed individually:

| Restriction | Supportable today? | Mechanism / gap |
|---|---|---|
| user → permitted specialist agents | **Yes** | `Persona__UserGroup` share rows + `_add_user_filters`; `is_listed` controls listing |
| user → permitted business units | **Yes, by convention** | model a unit as a `UserGroup`; no first-class "unit" entity |
| user → permitted contracts | **No** | needs a TON domain entity; no generic per-row ACL framework exists |
| user → permitted sources | **Yes** | `DocumentSet__UserGroup` + `Credential__UserGroup` + `UserGroup__ConnectorCredentialPair` |
| user → permitted files/documents | **Yes** | document ACLs via groups (EE path) + user-file access via persona attachment |
| user → permitted Findings/Occurrences | **No** | TON must own it. Reuse the `Persona__UserGroup` + `within_managed_scope_clause` pattern rather than inventing one |
| user → permitted Reports | **No** | same as Findings. `UsageReport` is admin-scoped metadata, not a per-user ACL model |

**Conclusion:** the permission system can carry the four TON roles and five of the
seven future restrictions with configuration only. Contracts, Findings/Occurrences
and Reports need TON-owned ACL rows, and the codebase already contains the exact
pattern to copy.

## Agents / Personas audit

| Capability | Location | Edition | Gate | Runs locally | TON decision |
|---|---|---|---|---|---|
| Create | `POST /persona`, `features/persona/api.py:344-369` | CE | `ADD_AGENTS` (`allow_scope`) | Yes | KEEP_AS_IS |
| Edit | `PATCH /persona/{id}`, `:373-398` | CE | `BASIC_ACCESS` + editable | Yes | KEEP_AS_IS |
| Delete | `DELETE /persona/{id}`, `:579-624` | CE | `ADD_AGENTS` + ownership | Yes | KEEP_AS_IS |
| Ownership | `Persona.user_id` XOR `owner_group_id`, `models.py:4182-4192`, `CheckConstraint ck_persona_single_owner` | user CE, **group owner EE** | — | Yes | REUSE_EE_LOCAL_IMPLEMENTATION |
| Transfer ownership | `POST /persona/{id}/transfer-ownership`, `:536-560` | CE + EE variant | versioned dispatch | Yes | KEEP_AS_IS |
| User sharing | `Persona__User.permission`, `models.py:700-712` | CE | `BASIC_ACCESS` + editable | Yes | KEEP_AS_IS |
| **Group sharing** | `Persona__UserGroup.permission`, `models.py:5099-5113`; logic `ee/onyx/db/persona.py:133-199` | **EE** | CE raises `NotImplementedError`; FE strips payload | Yes | **REUSE_EE_LOCAL_IMPLEMENTATION** |
| Visibility (`is_listed`) | `PATCH /admin/persona/{id}/listed`, `:166-178` | CE | `MANAGE_AGENTS` | Yes | KEEP_AS_IS |
| Public/private | `Persona.is_public` + `public_permission` (VIEWER/EDITOR) | CE columns | `BASIC_ACCESS` + owner check | Yes | KEEP_AS_IS |
| Source assignment | `Persona__DocumentSet`, `Persona__HierarchyNode`, `Persona__Document` | CE | via upsert | Yes | KEEP_AS_IS |
| Document-set assignment | `Persona__DocumentSet`, `models.py:672-679` | CE | via upsert | Yes | KEEP_AS_IS |
| Tool assignment | `Persona__Tool`, `models.py:839-856`; bounded by `get_tool_ids_on_editable_personas` | CE | via upsert | Yes | KEEP_AS_IS |
| Default agent | `DEFAULT_PERSONA_ID = 0`, `constants.py:70`; unified by migration `505c488f6662` | CE | — | Yes | ADAPT_EXISTING (TON Central) |
| Deployment seeding | `_seed_personas()`, `ee/onyx/server/seeding.py:168-193` | **EE** | none | Yes | REUSE_EE_LOCAL_IMPLEMENTATION |
| Per-group agent attach | `PATCH /manage/admin/user-group/{id}/agents`, `ee/user_group/api.py:456-521` | **EE** | **BUSINESS** | Yes | ENABLE_LATER |
| Agent analytics | `/analytics/admin/persona/*`, `ee/analytics/api.py:157-221` | **EE** | BUSINESS + `READ_AGENT_ANALYTICS` + owner GATE 2 | Yes | DEFER |

**Direct answer for the six TON specialists** (Central, CFO, Frota, Contratos,
Auditor, RH): all six can be created, scoped to document sets and tools, made
private, and shared with specific users **today at community tier**. Only
*group* sharing needs the Business gate changed. `PATH_PREFIX_MIN_TIER` contains
no persona, agent, or document-set entry — verified.

## Files and knowledge audit

| Capability | Location | Edition | Gate | TON decision |
|---|---|---|---|---|
| Project files | `UserProject` + `Project__UserFile`, `models.py:5530-5551` | CE | `BASIC_ACCESS`, owner-scoped | ADAPT_EXISTING |
| Temporary / incognito files | `UserFile.incognito` + `incognito_session_id`, `models.py:5583-5592`; sweep `db/incognito.py` | CE | `BASIC_ACCESS` | **KEEP_AS_IS** |
| Persistent knowledge | `UserFile.incognito = false` + project/persona attachment | CE | `BASIC_ACCESS` | **KEEP_AS_IS** |
| Retention / cleanup | `INCOGNITO_FILE_ORPHAN_AGE = 48h` (`db/incognito.py:22`), Celery `check-for-incognito-file-cleanup` every 10 min | CE | — | KEEP_AS_IS |
| Recent files | `UserFile.last_accessed_at`, `/user/files/recent` | CE | `BASIC_ACCESS` | KEEP_AS_IS |
| Document sets | `DocumentSet`, `models.py:3955-4012` | CE | `MANAGE_DOCUMENT_SETS` | KEEP_AS_IS |
| Document-set → group | `DocumentSet__UserGroup`, `models.py:5166-5174` | **EE** | via BUSINESS group routes | REUSE_EE_LOCAL_IMPLEMENTATION |
| Tags | `Tag` + `Document__Tag`, `db/tag.py:35-76` | CE | — | KEEP_AS_IS (documents only) |
| User-file tags | **absent** — flat columns only | — | — | REIMPLEMENT_MINIMAL_TON_VERSION if needed |
| Project ownership | `UserProject.user_id`, no sharing table | CE | owner-only | **ADAPT_EXISTING** for shared units |
| Document ACLs | CE email+public; EE adds groups | CE + **EE** | — | REUSE_EE_LOCAL_IMPLEMENTATION |
| Connector ACLs | `AccessType`, `Credential__UserGroup` | CE models | SYNC = BUSINESS | REMOVE_PRODUCT_GATE_LATER (SYNC only) |

**Answer to the TON distinction question.** Yes, TEMPORARY ANALYSIS versus
PERSISTENT ORGANIZATIONAL KNOWLEDGE is directly expressible with existing local
primitives, and it is the strongest reuse opportunity in the whole audit:

- Temporary = `UserFile.incognito = true`. Privacy is decided at upload time, the
  session adopts the file on the first message, and an unadopted orphan is swept
  after 48 hours. The comments in `models.py:5583-5592` state this design
  explicitly.
- Persistent = `UserFile.incognito = false`, attached to a `UserProject` and/or a
  persona, indexed, ACL-computed, and reachable through search.

TON does not need a new lifecycle. It needs the **contract declared** so the
frontend can show scope and retention without inferring it from a temp id — which
is exactly what `TON-FE-006` already blocks on.

The one genuine gap: `UserProject` has no sharing or group table. A "business
unit knowledge space" therefore needs either a TON-owned project-sharing table or
modelling units as personas with group shares. Prefer the second; it reuses ACLs
that already propagate to the index.

## Administration audit

Every admin route, with its permission, tier and visibility predicate, is in
`web/src/lib/admin-routes.ts:99-522`. Tier-insufficient entries render **disabled
with an upsell tooltip and still resolve** so deep links reach the gate UI
(`admin-sidebar-utils.ts:215-226`). Permission failure and `visibleWhen` failure
**hide** the entry.

| Admin capability | Route | Permission | Tier | TON decision |
|---|---|---|---|---|
| Users | `/admin/users` | `FULL_ADMIN_PANEL_ACCESS` | — | KEEP_AS_IS |
| **Groups** | `/admin/groups` | `MANAGE_USER_GROUPS` | **BUSINESS** | **REMOVE_PRODUCT_GATE_LATER** |
| Permissions registry | `GET /admin/permissions/registry` | admin | — | KEEP_AS_IS |
| Agents | `/admin/agents` | `MANAGE_AGENTS` | — | KEEP_AS_IS |
| LLM providers | `/admin/language-models` | `MANAGE_LLMS` | — | KEEP_AS_IS |
| Connectors | `/admin/add-connector`, `/admin/indexing/status` | `MANAGE_CONNECTORS` | — | KEEP_AS_IS |
| Indexing / index settings | `/admin/index-settings` | `FULL_ADMIN` | — | KEEP_AS_IS |
| Document sets | `/admin/documents/sets` | `MANAGE_DOCUMENT_SETS` | — | KEEP_AS_IS |
| System settings | `/api/settings` PATCH | `FULL_ADMIN` | field-level: retention ENTERPRISE, `search_ui_enabled` BUSINESS | ADAPT_EXISTING |
| **Branding / theme** | `/admin/theme` → `/admin/enterprise-settings` | `FULL_ADMIN` | **BUSINESS** | **REMOVE_PRODUCT_GATE_LATER** |
| Query history | `/admin/performance/query-history` | `READ_QUERY_HISTORY` | **BUSINESS** | ENABLE_LATER |
| Usage | `/admin/performance/usage` | `FULL_ADMIN` | **BUSINESS** | ENABLE_LATER |
| Analytics | `/admin/performance/analytics` | `FULL_ADMIN` | **BUSINESS** | DEFER |
| Service accounts | `/admin/service-accounts` | `MANAGE_SERVICE_ACCOUNT_API_KEYS` | **BUSINESS** | ENABLE_LATER |
| Diagnostics / tracing | `/admin/tracing` | `FULL_ADMIN` | — | KEEP_AS_IS |
| Security hardening | `/admin/security` | `FULL_ADMIN` | — | KEEP_AS_IS |
| SSO providers | `/admin/sso-providers` | `FULL_ADMIN` | — (multi-provider BUSINESS) | KEEP_AS_IS |
| SCIM | `/admin/scim` | `FULL_ADMIN` | ENTERPRISE | NOT_NEEDED |
| Billing | `/admin/billing` | `FULL_ADMIN` | — | already hidden by `SHOW_COMMERCE_SURFACES = false` |
| Export logs | `/admin/export-logs` | `FULL_ADMIN` | ENTERPRISE | DEFER |
| Hooks | `/admin/hooks` | `FULL_ADMIN` | ENTERPRISE | DEFER |

**Features hidden only by plan/tier, not by absent code:** groups, branding/theme,
query history, usage, analytics, service accounts, SCIM, hooks, log export,
standard answers, token rate limits, custom analytics script, LLM gateway,
connector auto-sync, multi-SSO, chat retention limit.

One inconsistency to note: `STANDARD_ANSWERS` declares `requiredTier: null` in the
frontend (`admin-routes.ts:494-503`) while the backend gates it at ENTERPRISE. It
is hidden from the sidebar, so a deep-link visitor reaches the page and fails only
on the API call. Cosmetic for TON, but it shows the two tables can drift.

## Query and audit history audit

| Component | Location | Edition | Tier | Notes |
|---|---|---|---|---|
| Chat session/message persistence | `ChatSession` `models.py:3168`, `ChatMessage` `:3271` | **CE** | none | Always recorded. First message in a chain is an empty root node — anything walking history must tolerate it. |
| Query history read API | `ee/onyx/server/query_history/api.py` | **EE** | BUSINESS | Reads CE tables. |
| Query history CSV export | `ee/.../query_history/tasks.py:31-121` | **EE** | BUSINESS | `csv_generation` queue, `sanitize_csv_row` against formula injection. |
| Anonymisation | `QueryHistoryType` `constants.py:355-358`, applied at read | CE enum, EE application | — | Rows keep real emails; masking is presentation. |
| Admin history / usage reports | `UsageReport` `models.py:5443-5466` | **model CE**, generation **EE** | BUSINESS | Metadata row + zip in file store, joined by `report_name` → `file_record.file_id`. |
| Analytics | `ee/onyx/server/analytics/api.py` | **EE** | BUSINESS / ENTERPRISE | CE tables. |
| Audit / activity events | `backend/onyx/utils/audit.py` | **CE** | none | **OCSF-mapped structured events to stdout. No `AuditLog` table exists.** |
| Credential access audit | `onyx/utils/credential_audit.py` | CE | none | Dedup window, never raises. |
| Log export | `ee/onyx/server/log_export/api.py` | **EE** | ENTERPRISE | Single-tenant only; distributed lock; fan-out per worker queue. |

**The finding TON must plan around:** audit logging is stdout-only. There is no
queryable audit table and therefore no reusable audit-trail persistence. Plan 006
lists `backend/onyx/utils/audit.py` as an in-scope reuse point
(`006-reports-schedules-admin.md:22-23`). That reuse gives TON **event emission
and OCSF field shape**, not storage or query. If TON needs a queryable audit trail
for Findings, Occurrences and Reports — and a controladoria product will — TON must
own that table. Amend Plan 006 to say so explicitly.

## Reporting audit

The reusable pieces, in order of value to TON:

1. **Async generate → poll → download.** Query history is the reference
   implementation (`ee/query_history/api.py:322-455`). The API mints the task id,
   registers a `Task` row in Postgres, and sends the Celery task with that same
   id. The worker deletes the task row on success, so the status endpoint falls
   back to a file-store existence check. Download maps task state to HTTP: 202 for
   pending/started, 500 for failure, 404 for unknown. **Copy this one.**
2. **Fire-and-forget.** Usage report `POST` returns 204 with no handle
   (`usage_export_api.py:37-68`); the client re-polls the list. Simpler, no
   progress signal. Do not copy for TON reports — controladoria needs failure
   visibility.
3. **Single-flight with fan-out.** Log export takes a distributed lock, returns
   `RATE_LIMITED` on contention, fans out per worker queue with `expires=deadline`,
   and releases in a `finally` that also catches `BaseException`
   (`log_export/api.py:154-231`). Copy this if a TON analysis run must never
   overlap.
4. **Multi-artifact zip report.** `create_new_usage_report`
   (`usage_export_generation.py:264-386`): spooled temp files so small reports never
   touch disk, `sanitize_csv_cell_or_none` on every user-supplied cell, best-effort
   PDF that never costs the CSVs, a duplicate-id re-check immediately before the
   final write, and intermediate cleanup in a `finally`.
5. **FileStore.** Four backends selected by `FILE_STORE_BACKEND`
   (`file_store.py:697-738`): S3-compatible (default, MinIO), **Postgres large
   objects** (`postgres_file_store.py:93` — fully self-contained, no object store),
   GCS, Azure Blob. Downloads are always chunked `StreamingResponse`. **No external
   Onyx service anywhere in this path.**

TON Reports therefore need no new export infrastructure. They need a TON report
entity with its own ACL, plus the pattern above.

## Model providers audit

| Capability | Location | Edition | Gate | Verdict |
|---|---|---|---|---|
| OpenAI | `LlmProviderNames`, `llm/constants.py:11-56` | CE | `MANAGE_LLMS` | Available |
| OpenAI-compatible | `OPENAI_COMPATIBLE = "openai_compatible"`, `constants.py:29`; dynamic model list `llm_provider_options.py:65` | CE | `MANAGE_LLMS` | **Available, first-class** |
| Ollama / LM Studio / LiteLLM proxy / Bifrost / Portkey / OpenRouter | same enum | CE | `MANAGE_LLMS` | Available |
| Anthropic / Azure / Bedrock / Vertex | same enum | CE | `MANAGE_LLMS` | Available |
| Custom (any LiteLLM provider) | `fetch_custom_provider_names`, `manage/llm/api.py:401-418` | CE | `FULL_ADMIN` | Available |
| Multiple providers | `LLMProvider` rows, `PUT /admin/llm/provider` | CE | `MANAGE_LLMS` | Available |
| Model selection / defaults | `POST /admin/llm/default*` | CE | `MANAGE_LLMS` | Available |
| Credentials | `api_key` via `EncryptedString`, `models.py:3617-3619` | CE | — | Encrypted at rest |
| Per-persona restriction | `LLMProvider__Persona`, `models.py:5139-5152` | CE | — | Available |
| Per-group restriction | `LLMProvider__UserGroup`, `models.py:5155-5163` + `is_public` | EE-flavoured | groups = BUSINESS | Needs gate change |
| LLM gateway | `ee/onyx/server/gateway/api.py:133` | **EE** | **BUSINESS** | **Not required for chat** |

**No Onyx-hosted LLM access exists or is required.** The gateway is an
OpenAI-compatible API that *your* deployment serves to third parties, backed by
*your* `LLMProvider` rows (`resolve_gateway_model`, `gateway/api.py:154-190`).
Normal chat resolves LLMs directly through `onyx/llm/factory.py`. The only internal
consumer of the gateway is Craft, which loops back to your own server
(`build/session/llm_config.py:158-160`).

Two cautions, neither a payment issue:

- `custom_config` is **plain JSONB, not encrypted** (`models.py:3623-3625`), yet it
  holds Bedrock keys, Vertex service-account JSON and LM Studio bearer tokens. It
  is masked on API output (`_mask_provider_credentials`, `api.py:239-254`) but stored
  in cleartext. Feed this to Plan 007 (deployment credential hardening) — it is a
  real P0 security item independent of TON.
- The SSRF guard forcing API-key re-entry when `api_base` changes is
  `MULTI_TENANT`-only (`api.py:~296-300`). Self-hosted admins can repoint
  `api_base` freely. Acceptable for an internal product with a trusted admin, but
  worth recording.

## Connectors audit

| Capability | Location | Edition | Gate | Verdict |
|---|---|---|---|---|
| Framework / registry | `connectors/registry.py:13+`, `factory.py:44-98` | CE | — | KEEP_AS_IS. Three-step registration: `DocumentSource` value, connector class, `CONNECTOR_CLASS_MAP` entry. |
| File connector / upload | `DocumentSource.FILE → LocalFileConnector` | CE | `MANAGE_CONNECTORS` | KEEP_AS_IS |
| OAuth connectors | `ee/onyx/server/oauth/api.py` + CE credential flow | mixed | `MANAGE_CONNECTORS` | KEEP_AS_IS |
| Admin configuration | `/admin/add-connector` | CE | `MANAGE_CONNECTORS` | KEEP_AS_IS |
| Indexing | `check-for-indexing` → docfetching → docprocessing | CE | — | KEEP_AS_IS |
| Credentials | `Credential.credential_json` via `EncryptedJson`, `models.py:2074-2076` | CE | — | Encrypted at rest |
| `AccessType.PUBLIC` / `PRIVATE` | `enums.py:280` | CE | none | **Works at community tier** |
| `AccessType.SYNC` | gated at create, `connector_credential_pair.py:763-777` | CE call, **EE gate** | **BUSINESS** | REMOVE_PRODUCT_GATE_LATER if a source needs mirrored ACLs |
| External permission / group sync | `ee/onyx/external_permissions/*` | **EE** | beat entries added only when EE loaded | REUSE_EE_LOCAL_IMPLEMENTATION |

**No connector capability requires external Onyx infrastructure.** For the planned
NG/Keevo and Telegram work, the framework is a sufficient foundation: add a
`DocumentSource`, a connector class, a registry entry. Note that on pure CE the
SYNC guard becomes a no-op and a SYNC cc-pair row can be created that never
syncs — a silent-failure mode to avoid.

## Background infrastructure audit

All local. All CE except the seven EE beat entries listed below.

| Component | Evidence | Verdict |
|---|---|---|
| Celery apps | `background/celery/apps/{primary,light,heavy,docfetching,docprocessing,monitoring,user_file_processing,scheduled_tasks,beat}.py` | Available |
| Queues | `OnyxCeleryQueues`, `constants.py:450-506` (~25 named queues) | Available |
| Beat schedule | `tasks/beat_schedule.py`; `BEAT_EXPIRES_DEFAULT = 15 min` (`:33`) | Available |
| Scheduled jobs (user-defined) | `dispatch-due-scheduled-tasks` every 30 s + `cleanup-stuck-scheduled-runs` hourly, both **CE**; API `features/build/scheduled_tasks/api.py` | **Available** — gated by a Craft feature flag, not a tier |
| Retries | Business retry is per-task; Celery time limits are inert because workers use thread pools | Available, with caveat |
| Locks | `OnyxRedisLocks` `constants.py:508+`; non-blocking `lock.acquire(blocking=False)` idiom | Available |
| Redis | `onyx/redis/*` incl. per-tenant key prefixing and IAM auth | Available |
| Task monitoring | `monitor-background-processes` 5 min; self-hosted adds queue/memory/heartbeat monitors | Available |

**EE-only beat entries** (all local, none paid): `autogenerate-usage-report`,
`check-ttl-management`, `export-query-history-cleanup-task`,
`revalidate-sso-domains`, `hook-execution-log-cleanup`,
`check-license-expiry-notifications`, `export-logs-cleanup-task`, plus
`check-for-doc-permissions-sync` and `check-for-external-group-sync` injected into
the CE schedule when EE is loaded (`beat_schedule.py:247-274`).

**For TON routines R1–R9:** the infrastructure is sufficient and already running.
Plan 006 correctly notes that Celery acknowledgement is not analysis success. Two
additions from this audit: always pass `expires=` on `send_task` (query history and
usage report do not, log export does), and implement timeouts inside the task
because Celery's are silently disabled under thread pools.

## Multi-tenancy audit

| Aspect | Location | Edition | TON needs it? |
|---|---|---|---|
| `MULTI_TENANT` flag, schema-per-tenant | `shared_configs/configs.py:194-202` | shared | Keep `false` |
| Tenant contextvars | `shared_configs/contextvars.py` | shared | **Yes — keep** |
| `TenantAwareTask` | `apps/app_base.py:112-138` | shared | **Yes — keep**; falls back to default schema when `tenant_id` absent |
| `DynamicTenantScheduler` | `apps/beat.py:26-29` | shared | Keep |
| Tenant middleware | `ee/middleware/tenant_tracking.py` | EE | Only under `MULTI_TENANT` |
| `UserTenantMapping` catalog tables | `models.py` `PublicBase` | shared | Not needed |
| **Tenant provisioning** | `ee/onyx/server/tenants/provisioning.py` → `CONTROL_PLANE_API_BASE_URL` | **EE + cloud** | **No — registered only `if MULTI_TENANT`** |
| Cloud billing / usage limits | `ee/onyx/server/tenants/billing.py`, `tenant_usage_limits.py` | EE + cloud | No |

**Verdict:** TON is single-tenant. Keep the tenant plumbing — it costs nothing and
the Celery, cache-key and index layers all depend on it. Do not adopt SaaS tenant
provisioning. Never set `MULTI_TENANT=true`; that is the only switch that turns on
control-plane calls.

## Branding and customization audit

| Capability | Location | Edition | Gate | Verdict |
|---|---|---|---|---|
| Product name (`application_name`) | `EnterpriseSettings`, `ee/enterprise_settings/store.py:56-81` | **EE** | write **BUSINESS**, read open | **Artificially gated** |
| Logo / logotype upload | `upload_logo`, `store.py:_LOGO_FILENAME` → file store | **EE** | write **BUSINESS**, read open | **Artificially gated** |
| Appearance / theme fields | `EnterpriseSettings` + `APPEARANCE_FIELD_MAX_LENGTHS` | **EE** | write **BUSINESS** (`/admin/theme`) | **Artificially gated** |
| Public read of branding | `GET /enterprise-settings` — in `LICENSE_ENFORCEMENT_ALLOWED_PREFIXES` and not tier-gated | EE router | **none** | Works today |
| Footer / upstream attribution | `SHOW_UPSTREAM_ATTRIBUTION = false`, `web/src/lib/ton/product-surface.ts` | TON | none | Already handled |
| Docs / community links | `SHOW_UPSTREAM_LINKS = false` | TON | none | Already handled |
| Design tokens | `web/lib/shared/tokens/*` — Vale Norte palette already mapped by `TON-FE-002` | TON | none | Done |
| Custom analytics script | `/admin/enterprise-settings/custom-analytics-script` | EE | **ENTERPRISE** + `CUSTOM_ANALYTICS_SECRET_KEY` | **NOT_NEEDED** |

Storage is the local KV store (`get_kv_store()`, Postgres-backed) plus the local
file store. Nothing external.

**Direct answer:** yes, required branding is artificially gated. Reading branding
is open at every tier; **writing** it needs Business because
`/admin/enterprise-settings` is in `PATH_PREFIX_MIN_TIER`. TON already controls its
theme through tokens, so the practical gap is narrow: setting the application name
and uploading the final logo through the admin UI. Two options, both local:

1. Remove `/admin/enterprise-settings` from the tier map (keeps the admin UI
   working) — preferred.
2. Seed the KV row at deploy time and never open the admin page.

The logo asset itself does not yet exist, so this is not urgent. `ADR-009` in the
frontend roadmap already covers that.

## SaaS / entitlement model map

| State | Set by | Affects FE | Affects routes | Affects real function |
|---|---|---|---|---|
| `Tier.COMMUNITY` | no license, or `GATED_ACCESS` license (`tier.py:52-70`) | disables gated sidebar items | 402 on 18 prefixes | Yes — group/branding/history APIs |
| `Tier.BUSINESS` | license `customer_tier = BUSINESS` | enables Business items | passes Business prefixes | Yes |
| `Tier.ENTERPRISE` | license `customer_tier = ENTERPRISE`, or legacy license without the field, or `LICENSE_ENFORCEMENT_ENABLED=false` | enables everything | passes all | Yes |
| `ApplicationStatus.ACTIVE` | valid license | normal | normal | No |
| `PAYMENT_REMINDER` / `GRACE_PERIOD` | license dates | banner only | none | **No** |
| `SEAT_LIMIT_EXCEEDED` | `used_seats > seats` | lock screen | 402 outside allowlist | Yes — but needs a license to exist |
| `GATED_ACCESS` | expired license, **or legacy EE flag with no license** | `ProductGatingWrapper` lock | 402 outside allowlist | Yes |
| Trial | `LicensePayload.trial_end` | copy only | none | **No** — trial never changes the resolved tier (`tier.py:6-10`) |
| Subscription / Stripe | `ee/onyx/server/tenants/*`, `web/src/lib/billing/*` | billing pages | none | **No** on self-hosted; `useCloudSubscription` returns `true` immediately when not cloud (`:15-17`) |
| Cloud | `MULTI_TENANT` / `NEXT_PUBLIC_CLOUD_ENABLED` | cloud branches | tenant routes | Only if enabled |

### The distinction the audit asked for

**PRODUCT COMMERCIAL GATE** — exists purely to sell upgrades. Removing it changes
no technical requirement:

Free/Business/Enterprise tier names, trial state, subscription state, Stripe
checkout, customer portal, payment reminders, upgrade navigation, plan comparison,
`upgradePlan` sidebar entry, seat counts, license expiry notifications, and the
18 `PATH_PREFIX_MIN_TIER` entries.

**REAL TECHNICAL REQUIREMENT** — must keep working regardless of commercial model:

Permission tokens and grants, `require_permission` GATE 1 / GATE 2, group
membership and scoped managers, document ACLs and index-level access filters,
tenant context propagation, credential encryption, PAT scope fail-closed routing,
audit event emission, and connector external-permission sync where a source's own
ACLs must be honoured.

**Every single gate in this repository is a commercial gate implemented locally.**
Not one of them is a technical requirement, and not one requires a remote check.

## EE directory audit — TON-relevant features

Format as requested: FEATURE / EE PATH / SHARED DEPENDENCIES / DATABASE MODELS /
MIGRATIONS / API / FRONTEND / FEATURE GATE / EXTERNAL SERVICE / RUNS LOCALLY /
TON VALUE / RECOMMENDED ACTION.

### 1. User groups, permission grants, group scoping

- EE path: `backend/ee/onyx/server/user_group/api.py`, `backend/ee/onyx/db/user_group.py`
- Shared deps: `onyx/auth/permissions.py`, `onyx/auth/scoped_permissions.py`, `onyx/db/models.py`
- Models: `UserGroup`, `User__UserGroup`, `PermissionGrant`, `UserGroup__ConnectorCredentialPair`, `DocumentSet__UserGroup`, `Persona__UserGroup`, `Skill__UserGroup`, `Credential__UserGroup`, `LLMProvider__UserGroup` — **all in CE `models.py`**
- Migrations: in the standard CE alembic tree
- API: mounted at `ee/onyx/main.py:133`
- Frontend: `/admin/groups`, `useCanManageGroups()`
- Gate: **LICENSE_TIER_ONLY** — `PATH_PREFIX_MIN_TIER["/manage/admin/user-group"] = BUSINESS`
- External service: none
- Runs locally: **yes**
- TON value: **critical** — carries CONTROLADORIA/GESTOR/LEITURA, source scoping, agent scoping, document ACLs
- Action: **REUSE_EE_LOCAL_IMPLEMENTATION + REMOVE_PRODUCT_GATE_LATER**
- Would it work if the gate disappeared? **Yes.** The router, DB layer, privilege-escalation guard (`ee/db/user_group.py:645-650`), sync Celery tasks and frontend all exist and target local PostgreSQL.

### 2. Group-aware document and user-file ACLs

- EE path: `backend/ee/onyx/access/access.py`
- Shared deps: `onyx/access/access.py`, `onyx/access/models.py`, `onyx/document_index/opensearch/search.py`
- Models: reuses group tables; ACL strings live in the OpenSearch document
- Migrations: none
- API: none (computed during indexing and query)
- Frontend: none
- Gate: **ARCHITECTURAL** — selected by `fetch_versioned_implementation`, which resolves to EE by default
- External service: none
- Runs locally: **yes**
- TON value: **critical** — without it, only per-email and public ACLs exist
- Action: **REUSE_EE_LOCAL_IMPLEMENTATION**
- Would it work if the gate disappeared? Already works; the "gate" is which module path loads, and EE loads by default.

### 3. Persona group sharing and group ownership

- EE path: `backend/ee/onyx/db/persona.py`
- Shared deps: `onyx/db/persona.py` (CE raises `NotImplementedError` at `:369-375`)
- Models: `Persona.owner_group_id`, `Persona__UserGroup.permission` — CE `models.py`
- Migrations: CE tree
- API: CE `PATCH /persona/{id}/share` dispatches via versioned implementation
- Frontend: `ShareAgentModal.tsx`; `svc.ts:173-199` strips group shares when EE is off
- Gate: **LOCAL_DEPENDENCY** on user groups, plus that BUSINESS tier gate
- External service: none
- Runs locally: **yes**
- TON value: **high** — six specialist agents scoped per business unit
- Action: **REUSE_EE_LOCAL_IMPLEMENTATION**
- Would it work if the gate disappeared? Yes, but only if groups are reachable. This is a category-D dependency.

### 4. Enterprise settings (branding, name, logo, appearance)

- EE path: `backend/ee/onyx/server/enterprise_settings/{api,store,models}.py`
- Shared deps: `onyx/key_value_store`, `onyx/file_store`
- Models: KV row `KV_ENTERPRISE_SETTINGS_KEY` + file-store blobs; no table
- Migrations: none
- API: `/admin/enterprise-settings` (write), `/enterprise-settings` (read, open)
- Frontend: `/admin/theme`, `useSettings().enterprise`
- Gate: **LICENSE_TIER_ONLY** on writes; reads ungated and in the license allowlist
- External service: none
- Runs locally: **yes**
- TON value: **high** — product identity
- Action: **REUSE_EE_LOCAL_IMPLEMENTATION + REMOVE_PRODUCT_GATE_LATER** (or seed the KV row)

### 5. Query history read and CSV export

- EE path: `backend/ee/onyx/server/query_history/api.py`, `ee/.../tasks/query_history/tasks.py`
- Shared deps: `ChatSession`, `ChatMessage`, `Task`, FileStore, `csv_generation` queue
- Models: **all CE**
- Migrations: CE
- API: seven routes, all `READ_QUERY_HISTORY`
- Frontend: `/admin/performance/query-history`, `QueryHistoryTable.tsx`
- Gate: **LICENSE_TIER_ONLY** — three BUSINESS prefixes
- External service: none
- Runs locally: **yes**
- TON value: **medium** — the async export pattern is the real prize
- Action: **ENABLE_LATER** (audit view) + **ADAPT_EXISTING** (copy the pattern for TON Reports)

### 6. Usage reports

- EE path: `ee/onyx/server/reporting/{usage_export_api,usage_export_generation,usage_report_pdf}.py`
- Shared deps: `UsageReport` (CE `models.py:5443`), `FileRecord`, FileStore, `onyx/db/system_usage.py`, `onyx/db/user_usage.py`, `onyx/db/users.py`
- Models: **`UsageReport` is CE**
- Migrations: CE
- API: three routes, `FULL_ADMIN_PANEL_ACCESS`
- Frontend: `/admin/performance/usage`, `UsageReports.tsx`
- Gate: **LICENSE_TIER_ONLY** — BUSINESS
- External service: none
- Runs locally: **yes**
- TON value: **medium** — multi-artifact zip generation pattern
- Action: **ADAPT_EXISTING**. Do not repurpose `UsageReport` itself; Plan 003 already forbids that coupling.

### 7. Analytics

- EE path: `ee/onyx/server/analytics/api.py`, `ee/onyx/db/analytics.py`
- Shared deps: CE chat tables
- Gate: **LICENSE_TIER_ONLY** — BUSINESS for `/analytics/admin`, ENTERPRISE for `/analytics`
- Runs locally: **yes** / no external service
- TON value: low
- Action: **DEFER**

### 8. External permission and group sync

- EE path: `backend/ee/onyx/external_permissions/*` (Confluence, Drive, Slack, Jira, SharePoint, Teams, GitHub, Salesforce, Box, Canvas, Gmail)
- Shared deps: connector framework, `AccessType.SYNC`, heavy queues
- Gate: **LICENSE_TIER_ONLY** at create time (`require_business_tier_for_sync_access`)
- Runs locally: **yes** / no external Onyx service (it talks to the *source* system)
- TON value: low today; relevant only if a Vale Norte source has its own ACLs to mirror
- Action: **DEFER**, then REMOVE_PRODUCT_GATE_LATER if needed

### 9. Deployment seeding

- EE path: `backend/ee/onyx/server/seeding.py`
- Shared deps: `upsert_persona`, LLM provider upsert
- Gate: **CONFIGURATION** — no tier check; driven by an env-supplied `SeedConfiguration`
- Runs locally: **yes**
- TON value: **high** — declaratively seed the six specialists and TON Central
- Action: **REUSE_EE_LOCAL_IMPLEMENTATION**

### 10. License, billing, tenant provisioning, SCIM, evals, hooks, standard answers, log export, LLM gateway, token rate limits

- EE paths: `ee/onyx/server/{license,billing,tenants,scim,evals,log_export,gateway,token_rate_limits}`, `ee/onyx/server/manage/standard_answer.py`, `ee/onyx/server/features/hooks/`
- Gate: license/tier and, for tenants, `MULTI_TENANT`
- External service: **only** `tenants/*` (control plane) and license auto-fetch (`CLOUD_DATA_PLANE_URL`)
- Runs locally: everything except `tenants/*`
- TON value: **none** for license/billing/tenants/SCIM/evals; low for the rest
- Action: **NOT_NEEDED** for license, billing, tenants, SCIM, evals. **DEFER** for hooks, standard answers, log export, token rate limits, LLM gateway.

## TON domain requirements — dependency map

No gated capability blocks any TON domain entity. The dependencies are on
patterns and on group scoping, not on entitlements.

| TON entity | Blocked by a gate? | Depends on | Pattern to reuse |
|---|---|---|---|
| Rule | No | Plan 003 schema | none needed |
| RuleVersion | No | Plan 003 | append-only transitions |
| AnalysisRun | No | Celery + Redis locks (CE) | `check_for_indexing` lock idiom; `scheduled_tasks` dispatcher |
| Finding | No | Plan 003; ACL is TON-owned | `Persona__UserGroup` + `within_managed_scope_clause` |
| Occurrence | No | Plan 003 | same |
| Reports | No | FileStore + `Task` table (CE) | query-history generate/poll/download |
| Specialist agents | **Group sharing = BUSINESS** | user groups (D) | `Persona__UserGroup`; EE seeding |
| TON supervisor | No | `deep_research/dr_loop.py`, `tool_constructor.py` (CE) | native loop; no LangGraph |
| Scheduler | No | beat + `scheduled_tasks` worker (CE) | `dispatch-due-scheduled-tasks` + `FOR UPDATE SKIP LOCKED` |
| Files / knowledge | No | `UserFile.incognito` (CE) | incognito sweep + 48 h orphan age |
| Telegram | No | Plan 009 contract | connector/bot registration; credentials server-side |
| Audit trail | No | **no storage exists** | emission shape from `utils/audit.py`; TON owns the table |

## Decision matrix

Columns: CAPABILITY / TON REQUIREMENT / IMPLEMENTATION LOCATION / EDITION / GATE
TYPE / EXTERNAL ONYX DEP / RUNS LOCALLY / PAID ONYX REQUIRED / TON DECISION /
IMPLEMENTATION NEEDED / BACKEND IMPACT / FRONTEND IMPACT / PRIORITY / EVIDENCE.

Category letters: A already functional · B local but gated · C EE and
self-contained · D depends on another local EE capability · E external Onyx
dependency · F partial, needs adaptation · G absent · H irrelevant.

| Capability | TON req | Location | Edition | Gate type | Ext. Onyx | Local | Paid | Decision | Impl needed | BE impact | FE impact | Pri | Cat | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Authentication | Required | `onyx/auth/*` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | `auth/users.py:2214-2277` |
| Permission tokens + grants | Required | `onyx/auth/permissions.py`, `db/enums.py:640` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P0 | A | `permissions.py:322-365` |
| Admin capability | Required | `FULL_ADMIN_PANEL_ACCESS` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P0 | A | `enums.py:711` |
| **User groups + RBAC UI** | Required | `ee/user_group/api.py`, `models.py:5188` | model CE / API EE | LICENSE_TIER_ONLY | No | Yes | No | **REUSE_EE + REMOVE_PRODUCT_GATE_LATER** | Yes, 1 line | remove map entry | un-disable `/admin/groups` | **P0** | B+C | `license_enforcement_config.py:83` |
| Group membership + scoped managers | Required | `models.py:5008`, `scoped_permissions.py` | CE | LOCAL_DEPENDENCY | No | Yes | No | REUSE_EE_LOCAL_IMPLEMENTATION | No | none | none | P0 | D | `permissions.py:114-127` |
| Document ACLs by group | Required | `ee/access/access.py:182-208` | EE | ARCHITECTURAL | No | Yes | No | REUSE_EE_LOCAL_IMPLEMENTATION | No | none | none | **P0** | C | `variable_functionality.py:76-132` |
| Document ACLs by email/public | Required | `onyx/access/access.py:115-136` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P0 | A | same |
| Index-level access filter | Required | `context/search/preprocessing/access_filters.py` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P0 | A | `interfaces_new.py:187` fail-closed |
| Agents CRUD + user sharing | Required | `features/persona/api.py` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | `api.py:344-624` |
| **Agent group sharing** | Required | `ee/db/persona.py:133-199` | EE | LOCAL_DEPENDENCY | No | Yes | No | REUSE_EE_LOCAL_IMPLEMENTATION | No | none | drop client-side strip | P1 | D | `db/persona.py:369-375` |
| Agent seeding | Useful | `ee/server/seeding.py:168-193` | EE | CONFIGURATION | No | Yes | No | REUSE_EE_LOCAL_IMPLEMENTATION | Config only | none | none | P2 | C | same |
| Default agent (TON Central) | Required | `constants.py:70`, migration `505c488f6662` | CE | none | No | Yes | No | ADAPT_EXISTING | Config | none | label | P1 | A | `db/persona.py:2095` |
| Document sets | Required | `features/document_set/api.py` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | routes `:47-342` |
| Document set → group | Required | `models.py:5166` + EE writer | model CE / EE writer | LOCAL_DEPENDENCY | No | Yes | No | REUSE_EE_LOCAL_IMPLEMENTATION | No | none | none | P1 | D | `ee/db/document_set.py` |
| Projects | Required | `features/projects/api.py` | CE | none | No | Yes | No | ADAPT_EXISTING | Yes if shared | project sharing model | scope UI | P1 | F | `models.py:5530-5551` |
| Temporary/incognito files | Required | `models.py:5583`, `db/incognito.py` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | declare scope | P1 | A | `incognito.py:22` |
| Persistent knowledge | Required | `UserFile` + project/persona | CE | none | No | Yes | No | KEEP_AS_IS | No | none | declare scope | P1 | A | `models.py:5558-5645` |
| User-file ACL | Required | `access.py:203-217` + EE groups | CE + EE | ARCHITECTURAL | No | Yes | No | REUSE_EE_LOCAL_IMPLEMENTATION | No | none | none | P1 | C | `ee/access/access.py:152-181` |
| Tags on user files | Useful | absent | — | MISSING_DEPENDENCY | No | — | No | REIMPLEMENT_MINIMAL_TON_VERSION | Yes | small table | filter UI | P3 | G | flat columns only |
| Connector framework | Required | `connectors/registry.py`, `factory.py` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | `factory.py:44-98` |
| File connector / upload | Required | `connectors/file/connector.py` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | `registry.py:17-20` |
| Connector `PRIVATE`/`PUBLIC` | Required | `enums.py:280` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | — |
| Connector `SYNC` | Optional | gate `ee/utils/tier.py:168` | CE call / EE gate | LICENSE_TIER_ONLY | No | Yes | No | DEFER → REMOVE_PRODUCT_GATE_LATER | Only if needed | 1 guard | none | P3 | B | `connector_credential_pair.py:763` |
| External group sync | Optional | `ee/external_permissions/*` | EE | LICENSE_TIER_ONLY | No | Yes | No | DEFER | No | none | none | P3 | C | `beat_schedule.py:247-274` |
| Indexing pipeline | Required | `docprocessing/tasks.py:853` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | — |
| LLM providers (OpenAI, custom, compatible) | Required | `manage/llm/api.py` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | `llm/constants.py:11-56` |
| LLM per-persona restriction | Useful | `models.py:5139` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P2 | A | — |
| LLM per-group restriction | Useful | `models.py:5155` | EE-flavoured | LOCAL_DEPENDENCY | No | Yes | No | ENABLE_LATER | No | none | none | P2 | D | — |
| LLM gateway | Not needed | `ee/gateway/api.py:133` | EE | LICENSE_TIER_ONLY | No | Yes | No | DEFER | No | none | none | P3 | B | `gateway/configs.py:5-6` |
| Auto-mode model list | Optional | `AUTO_LLM_CONFIG_URL` → GitHub | CE | CONFIGURATION | No (GitHub) | Yes | No | KEEP_AS_IS or unset | No | none | none | P3 | A | `app_configs.py:1853` |
| Embedding weights | Required | model server → HuggingFace | CE | MISSING_DEPENDENCY at first boot | No | Yes after cache | No | KEEP_AS_IS (pre-bake) | Deployment | none | none | P1 | A | `model_server/main.py:35-38` |
| Celery / workers / queues | Required | `background/celery/*` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | `constants.py:450-506` |
| Beat + scheduled jobs | Required | `beat_schedule.py`, `scheduled_tasks/api.py` | CE | FEATURE_FLAG (Craft) | No | Yes | No | ADAPT_EXISTING | TON schedules | R1–R9 | admin UI | P1 | F | `beat_schedule.py:200-232` |
| Redis locks | Required | `OnyxRedisLocks` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | `constants.py:508+` |
| FileStore (4 backends) | Required | `file_store/file_store.py:697-738` | CE | CONFIGURATION | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | Postgres LO option |
| Async report generate/poll/download | Required | `ee/query_history/api.py:322-455` | EE pattern, CE deps | LICENSE_TIER_ONLY on that route | No | Yes | No | ADAPT_EXISTING | Yes | TON reports | reports UI | P1 | F | same |
| Usage report zip pipeline | Useful | `usage_export_generation.py:264-386` | EE | LICENSE_TIER_ONLY | No | Yes | No | ADAPT_EXISTING | Yes | TON reports | none | P2 | F | same |
| Query/chat history storage | Required | `models.py:3168,3271` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | — |
| Query history admin view | Useful | `ee/query_history/api.py` | EE | LICENSE_TIER_ONLY | No | Yes | No | ENABLE_LATER | Gate change | map entry | un-disable | P2 | B | `config:77-79` |
| Chat retention limit | Useful | `settings/api.py:117-125` + EE TTL task | CE gate / EE worker | LICENSE_TIER_ONLY | No | Yes | No | ENABLE_LATER | Gate change | field check | none | P2 | B+D | same |
| Audit event emission | Required | `onyx/utils/audit.py` | CE | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | OCSF, stdout |
| **Queryable audit trail** | Required | **absent** | — | MISSING_DEPENDENCY | No | — | No | **REIMPLEMENT_MINIMAL_TON_VERSION** | Yes | new table | history UI | **P1** | G | no `AuditLog` model |
| Analytics | Optional | `ee/analytics/api.py` | EE | LICENSE_TIER_ONLY | No | Yes | No | DEFER | No | none | none | P3 | B | `config:80,92` |
| Service-account API keys | Useful | `/admin/api-key` | EE | LICENSE_TIER_ONLY | No | Yes | No | ENABLE_LATER | Gate change | map entry | un-disable | P2 | B | `config:81` |
| **Branding: name, logo, appearance** | Required | `ee/enterprise_settings/*` | EE | LICENSE_TIER_ONLY (writes) | No | Yes | No | **REUSE_EE + REMOVE_PRODUCT_GATE_LATER** | Yes, small | map entry | `/admin/theme` | **P1** | B+C | `config:82` |
| Branding read | Required | `GET /enterprise-settings` | EE router | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | allowlist `config:44` |
| TON theme tokens | Required | `web/lib/shared/tokens/*` | TON | none | No | Yes | No | KEEP_AS_IS | Done | none | done | P1 | A | TON-FE-002 |
| Commerce surface hiding | Required | `web/src/lib/ton/product-surface.ts` | TON | UI_ONLY | No | Yes | No | KEEP_AS_IS | In progress | none | TON-FE-003 | P1 | A | flags all `false` |
| Billing / Stripe / subscription | Not needed | `ee/tenants/*`, `web/lib/billing/*` | EE | COMMERCIAL GATE ONLY | Yes (unused) | n/a | No | NOT_NEEDED | No | none | hidden | H | H | `useCloudSubscription:15-17` |
| License upload / claim | Not needed | `ee/server/license/api.py` | EE | none | Optional | Yes | No | NOT_NEEDED | No | none | none | H | H | offline RSA verify |
| Tenant provisioning | Not needed | `ee/tenants/provisioning.py` | EE | EXTERNAL_SERVICE | **Yes** | No | No | NOT_NEEDED | No | none | none | H | E | `if MULTI_TENANT` only |
| SCIM | Not needed | `ee/scim/*` | EE | LICENSE_TIER_ONLY | No | Yes | No | NOT_NEEDED | No | none | none | H | H | `config:86,93` |
| Evals | Not needed | `ee/evals/*` | EE | LICENSE_TIER_ONLY | No | Yes | No | NOT_NEEDED | No | none | none | H | H | `config:92` |
| Custom analytics script | Not needed | `/admin/.../custom-analytics-script` | EE | LICENSE_TIER_ONLY | Third-party JS | Yes | No | NOT_NEEDED | No | none | none | H | H | `config:85` |
| Hooks / standard answers / log export / rate limits | Optional | `ee/features/hooks`, `manage/standard_answer.py`, `ee/log_export`, `ee/token_rate_limits` | EE | LICENSE_TIER_ONLY | No | Yes | No | DEFER | No | none | none | P3 | B | `config:87-91` |
| Telemetry (PostHog, telemetry.onyx.app) | Not needed | `utils/telemetry.py` | CE | CONFIGURATION | Yes | Yes | No | KEEP_AS_IS, off | `DISABLE_TELEMETRY` | none | Plan 008 | P1 | A | `:120-122` |
| Tenant context / `TenantAwareTask` | Required | `shared_configs/contextvars.py`, `app_base.py:112` | shared | none | No | Yes | No | KEEP_AS_IS | No | none | none | P1 | A | — |
| Rule / RuleVersion / AnalysisRun / Finding / Occurrence / TON Report | Required | **absent** | — | MISSING_DEPENDENCY | No | — | No | Plans 003 + 006 | Yes | new schema | new screens | P1 | G | Plan 003 |
| TON per-resource ACL (contracts, findings, reports) | Required | **absent** | — | MISSING_DEPENDENCY | No | — | No | REIMPLEMENT_MINIMAL_TON_VERSION | Yes | new junction tables | filters | **P0** | G | pattern exists |
| Telegram adapter | Required later | **absent** | — | MISSING_DEPENDENCY | No | — | No | Plan 009 | Yes | new adapter | admin status | P2 | G | Plan 009 BLOCKED |

## Gap priority summary

**P0 — blocks secure operation or core architecture**

1. User groups are tier-gated, so group-based authorization cannot be configured.
   Without it, TON's four roles collapse to admin-or-everyone and document ACLs
   fall back to per-email only.
2. TON has no per-resource ACL model for contracts, Findings, Occurrences and
   Reports. A controladoria product cannot ship without it. The pattern exists
   (`Persona__UserGroup` + `within_managed_scope_clause`); the tables do not.
3. Deployment invariant not yet recorded: `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES`
   must stay unset, or the whole app enters `GATED_ACCESS`.
4. `LLMProvider.custom_config` stores provider secrets unencrypted. Independent of
   TON, but it is a credential-at-rest defect and Plan 007 owns it.

**P1 — required for TON MVP**

5. Branding writes (application name, logo) are tier-gated.
6. No queryable audit trail exists; only stdout events.
7. `UserProject` has no sharing model, so a shared business-unit knowledge space
   needs either a TON table or persona-based modelling.
8. TON domain schema absent (Plans 003, 006).
9. Async report generate/poll/download must be built for TON reports; the pattern
   is available but the route that demonstrates it is Business-gated.
10. Embedding weights must be pre-baked or mounted for an offline first boot.

**P2 — useful shortly after MVP**

11. Query history admin view, usage reports, service-account API keys, chat
    retention limit, per-group LLM restriction, Telegram adapter.

**P3 — optional / upstream convenience**

12. Analytics, hooks, standard answers, log export, token rate limits, connector
    auto-sync, external group sync, user-file tags, LLM gateway.

**Not needed:** billing, Stripe, subscriptions, trials, plan comparison, license
upload/claim, tenant provisioning, SCIM, evals, custom analytics script, PostHog,
GTM, HubSpot, cloud signup and referral flows.

## Recommended Plan 008 change

**Plan 008 is the correct execution point for the entitlement→capability
transformation, but its current scope is too narrow and its dependency order is
wrong for the gates TON actually needs.**

Current Plan 008 scope is frontend-only: `layout.tsx`, `providers.tsx`,
`ProductGatingWrapper.tsx`, `constants.ts`, billing pages, `AccessRestrictedPage`,
`AccountPopover`, `proxy.ts`, `chat/hooks.ts`. Its own out-of-scope list excludes
backend domain work. But the gates that matter are **backend middleware**:
`PATH_PREFIX_MIN_TIER`, `tier_gate`, `license_enforcement`, and
`apply_license_status_to_settings`. Hiding frontend commerce surfaces — which
`web/src/lib/ton/product-surface.ts` already does correctly, and which its own
docstring says "never change authorization" — cannot un-gate `/admin/groups`.

Recommended amendments to `plans/ton/backend/008-web-only-product.md`:

1. **Rename the plan's purpose** from "web-only product surface" to "web-only
   product surface and entitlement→capability transformation". Keep the surface
   work; add the backend gate layer.
2. **Add to scope:**
   - `backend/ee/onyx/configs/license_enforcement_config.py` — remove the TON-required
     entries from `PATH_PREFIX_MIN_TIER` (`/manage/admin/user-group`,
     `/admin/enterprise-settings`; optionally the history/usage/api-key prefixes).
   - `backend/ee/onyx/server/settings/api.py` — decide what `tier` and
     `ee_features_enabled` report to the frontend under a TON capability model.
   - `backend/ee/onyx/utils/tier.py` — the `require_business_tier_for_*` in-handler
     guards, which the path map does not cover.
   - `backend/onyx/server/settings/api.py:117-125` — the field-level retention and
     `search_ui_enabled` tier checks.
   - `web/src/lib/admin-routes.ts` and `web/src/lib/tiers.ts` — the frontend mirror.
3. **Add an explicit target model.** TON should answer four questions and nothing
   else:
   - is the feature available in this deployment? → configuration / feature flag
   - is the user authorized? → `Permission` + group scope (GATE 1 / GATE 2)
   - is the tenant valid? → tenant context
   - is the resource allowed? → resource ACL
   `Free`, `Business`, `Enterprise`, `Trial`, `Subscription` and `Upgrade` have no
   place in the final TON product model. Concretely: keep the `Tier` type as a
   compatibility shim if that reduces churn, but make TON resolve to a single
   constant capability level rather than a purchased one. Do not delete the tier
   plumbing in one step — `useTierAtLeast`, `admin-routes.ts` and `tier_gate` all
   read it, and `check_ee_features_enabled` fails closed on Redis errors.
4. **Fix the dependency order.** Plan 008 currently depends on 001, 002, 006, 007.
   Plan 005 (agents) needs agent **group sharing**, and Plan 006 (reports/admin)
   needs group-scoped report ACLs. Both therefore need the group gate removed
   before they can be verified end to end. Two options:
   - split a small **Plan 008a — capability gate transformation** that depends only
     on 001 and 002 and runs before 005; leave the surface/telemetry work as 008b; or
   - move the group and branding gate items into Plan 002 (security boundaries),
     which is where authorization already lives.
   Prefer the split. It keeps Plan 002's scope honest and makes the gate change
   independently testable.
5. **Add STOP conditions:**
   - Stop if removing a tier entry also removes a permission or scope check.
   - Stop if `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` is set anywhere in
     deployment config; that flag plus no license equals `GATED_ACCESS`.
   - Stop if a change makes `MULTI_TENANT` true, which is the only switch that
     enables control-plane calls.
   - Stop if `fetch_versioned_implementation` stops resolving to `ee.*`, because
     that silently downgrades document ACLs to per-email only. This is the most
     dangerous possible regression in the whole transformation: it fails **open**,
     quietly, at the index layer.
6. **Add a test requirement:** an integration test asserting that a non-admin user
   in group A cannot retrieve a document whose ACL names only group B, executed
   with the tier gate removed. That single test protects the ACL invariant that
   the gate change puts at risk.

## Other roadmap impacts

### Backend

| Plan | Impact | Recommended amendment |
|---|---|---|
| 003 — domain rules/Findings | Confirms no reusable Finding/Report entity exists. Confirms `UsageReport` is unrelated metadata. | Add: TON Finding/Occurrence/Report must carry their own ACL junction rows; reuse `within_managed_scope_clause` and the GATE 1 / GATE 2 contract rather than inventing an authorization path. Add: audit-trail storage is TON-owned because no `AuditLog` table exists. |
| 004 — files/knowledge | Confirms `UserFile.incognito` + 48 h orphan sweep already model TEMPORARY vs PERSISTENT. | Add: the distinction needs a **declared contract**, not new lifecycle code. Add: user-file group ACLs come from the EE `build_access_for_user_files_impl`; note the dependency so nobody replaces it. Note `UserProject` has no sharing table. |
| 005 — agents/orchestration | Its warning about role names is correct and understated: `UserRole` is a tombstone. Agent **group** sharing is Business-gated. | Replace role language with `Permission` / `PermissionAuthority` / group-scope language. Add a dependency on the group gate change (008a or 002). Add: `Persona.owner_group_id` XOR `user_id` gives business-unit ownership for free. |
| 006 — reports/schedules/admin | Reusable async pattern found; audit storage absent; scheduled-task infrastructure is CE and already running. | Add the query-history generate/poll/download pattern as the named reference. Add: `send_task` must always carry `expires=`. Add: implement in-task timeouts because Celery limits are inert under thread pools. Change the `utils/audit.py` reuse note to "event emission only — storage is TON-owned". |
| 007 — deployment hardening | New P0 finding. | Add `LLMProvider.custom_config` cleartext secrets to scope. Add the deployment invariant that `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` stays unset and `LICENSE_ENFORCEMENT_ENABLED` stays at its default. Add pre-baked embedding weights for offline boot. |
| 008 — web-only product | See the dedicated section above. | Split into 008a (gates) + 008b (surface), or move gates into 002. |
| 009 — Telegram | No gate blocks it. | Add: bot/channel admin surfaces are ungated (`MANAGE_BOTS`, no tier), so the Telegram admin screen faces no entitlement obstacle. Keep the plan blocked on its contract only. |
| README / roadmap status drift | `README.md` shows Plan 002 as `TODO`; `roadmap.md` shows it `DONE`. | Reconcile. The working tree contains uncommitted TON-FE-003 work, so status tracking is already drifting. |

### Frontend

| Item | Impact | Recommended amendment |
|---|---|---|
| TON-FE-003 (hidden surfaces) | Already in progress in the working tree; `product-surface.ts` exists with all four flags `false`. Its docstring correctly states these flags never change authorization. | Add an explicit note that hiding commerce surfaces does **not** un-gate anything, and that `/admin/groups` and `/admin/theme` will still render disabled until the backend map changes. Cross-reference 008a. |
| TON-FE-004 (navigation) | No gate involved. | No change. |
| TON-FE-005 (Central + specialists) | Confirmed: personas, `_add_user_filters`, share modal all local. Group-share UI is stripped client-side when EE is off (`svc.ts:173-199`). | Add: the client-side strip is presentation; the real gate is the Business tier on group routes. Remove the strip only after 008a. Add: `id = 0` is the unified default agent, created by migration `505c488f6662` — the roadmap's "id 0 pode não ser Central customizada" risk is resolvable by reading that migration. |
| TON-FE-006 (file scope) | Confirmed the retention contract is derivable from `UserFile.incognito`, `incognito_session_id` and the 48 h orphan age. | Un-block partially: the backend contract already exists in the model comments and `db/incognito.py`. What is missing is an API field exposing scope, not a design decision. |
| TON-FE-007 (sources) | Confirmed connectors, document sets and credential/group tables are all local. | Add: `DocumentSet__UserGroup`, `Credential__UserGroup` and `UserGroup__ConnectorCredentialPair` give per-source ACL for free once groups are un-gated. |
| TON-FE-008 (occurrences) | Confirmed no occurrence entity exists. Correctly blocked. | Add: the ACL shape should mirror `Persona__UserGroup`; specify it in the contract so the UI can filter by group. |
| TON-FE-009 (reports) | Confirmed usage reports and query history are admin/EE and may contain PII; query-history rows keep real emails even in anonymised mode. | Add: anonymisation is applied at read time only (`api.py:245`), so TON must not treat `ANONYMIZED` mode as data minimisation. Add the generate/poll/download states from the query-history pattern. |
| TON-FE-010 (Telegram) | Bot admin routes are ungated. | Note that no tier gate applies; the block is the Plan 009 contract only. |
| Playwright global setup | Root cause found: the setup calls the user-groups endpoint, which 402s at community tier. | Add to the plan: after 008a the setup works unmodified. Until then, document the temporary skip rather than re-discovering it each run. |

## Implementation candidate tasks

Not implemented. Each is a future controlled change.

### TON-CAP-001 — Remove the upstream tier gate from user groups and RBAC

- **OBJECTIVE:** make group-based authorization configurable in a self-hosted TON
  deployment with no license.
- **CURRENT IMPLEMENTATION:** models in CE `models.py` (`UserGroup:5188`,
  `User__UserGroup:5008`, `PermissionGrant:5027`); API `ee/onyx/server/user_group/api.py`
  mounted at `ee/onyx/main.py:133`; DB layer `ee/onyx/db/user_group.py`; frontend
  `/admin/groups` + `useCanManageGroups()`.
- **GATE:** LICENSE_TIER_ONLY. `license_enforcement_config.py:83` →
  `tier_gate.py:100-112` → HTTP 402.
- **WHY:** without it, CONTROLADORIA, GESTOR/OPERACIONAL and LEITURA cannot be
  expressed, group document ACLs cannot be assigned, agent group sharing is
  unreachable, and the Playwright global setup fails.
- **EXISTING CODE TO REUSE:** everything. No new model, migration, route or screen.
- **MINIMUM CHANGE:** remove the `/manage/admin/user-group` entry from
  `PATH_PREFIX_MIN_TIER`; change `useCanManageGroups()` to stop requiring Business;
  set `requiredTier: null` on `ADMIN_ROUTES.GROUPS`.
- **DEPENDENCIES:** none technical. Should land before Plan 005 verification.
- **SECURITY:** the tier gate is not an authorization control — `require_permission`
  and GATE 2 are, and they are untouched. Do not weaken: the escalation guard at
  `ee/db/user_group.py:645-650` (adding a member grants them the group's permissions),
  `assert_not_shared_with_default_group`, and the deliberate absence of `allow_scope`
  on create, delete and `set_group_permissions`. Verify `is_default` groups stay
  undeletable.
- **ACCEPTANCE:** admin creates a group, grants permissions, adds members, and a
  member gains exactly the granted tokens; a scoped manager can act only inside a
  managed group; a document ACL'd to group B is not retrievable by a group-A member;
  no 402 on any `/manage/admin/user-group` route; Playwright global setup passes
  unmodified.

### TON-CAP-002 — Expose local RBAC capability to the TON admin surface

- **OBJECTIVE:** present groups and permissions as a first-class TON administration
  feature instead of a disabled upsell row.
- **CURRENT IMPLEMENTATION:** `admin-routes.ts` `GROUPS` entry with
  `requiredTier: Tier.BUSINESS`; `admin-sidebar-utils.ts:215-226` renders
  tier-insufficient rows disabled with an upsell tooltip;
  `GET /admin/permissions/registry` already serves display names and grouping.
- **GATE:** UI_ONLY on top of TON-CAP-001's backend gate.
- **WHY:** a disabled row with an upgrade tooltip is wrong for an internal product
  that is not for sale.
- **EXISTING CODE TO REUSE:** `PERMISSION_REGISTRY` (`permissions.py:150+`) and the
  existing groups admin screens.
- **MINIMUM CHANGE:** drop `requiredTier` on `GROUPS`; ensure `buildItems` never
  emits an upsell tooltip for TON; keep permission-based hiding intact.
- **DEPENDENCIES:** TON-CAP-001.
- **SECURITY:** hiding is not enforcement. Confirm `ClientLayout` still applies the
  per-page permission gate and that direct navigation is refused by the backend.
- **ACCEPTANCE:** an admin sees an enabled Groups entry with no upgrade copy; a
  `BASIC_ACCESS` user sees neither the entry nor the page; both light and dark
  themes and both mobile breakpoints pass.

### TON-CAP-003 — Un-gate branding writes (application name, logo, appearance)

- **OBJECTIVE:** let a TON operator set product identity without a license.
- **CURRENT IMPLEMENTATION:** `ee/onyx/server/enterprise_settings/{api,store}.py`;
  KV row `KV_ENTERPRISE_SETTINGS_KEY`; logo blobs in the local file store; frontend
  `/admin/theme`.
- **GATE:** LICENSE_TIER_ONLY on `/admin/enterprise-settings` (BUSINESS). Reads are
  ungated and in the license allowlist.
- **WHY:** product name and logo are baseline identity, not a premium feature.
- **EXISTING CODE TO REUSE:** the whole store, upload path and admin page.
- **MINIMUM CHANGE:** remove `/admin/enterprise-settings` from `PATH_PREFIX_MIN_TIER`
  while **keeping** the ENTERPRISE entries for `custom-analytics-script` and `scim`
  (longest-prefix-wins already handles that); set `requiredTier: null` on
  `ADMIN_ROUTES.THEME`. Alternative with no code change: seed the KV row at deploy.
- **DEPENDENCIES:** none. The final logo asset is still missing (ADR-009).
- **SECURITY:** keep `FULL_ADMIN_PANEL_ACCESS` on writes. Do **not** un-gate
  `custom-analytics-script` — it injects arbitrary JS into every page and needs
  `CUSTOM_ANALYTICS_SECRET_KEY`. Keep logo upload restricted to `.png/.jpg/.jpeg`
  (`store.py:is_valid_file_type`) and preserve the appearance-field length clamps.
- **ACCEPTANCE:** admin sets the application name and uploads a logo; both appear on
  the auth screen and in the app shell; a non-admin cannot write;
  `custom-analytics-script` still refuses at community tier.

### TON-CAP-004 — Record the zero-entitlement deployment invariants

- **OBJECTIVE:** prevent a configuration change from locking the deployment or
  silently downgrading ACLs.
- **CURRENT IMPLEMENTATION:** `variable_functionality.py:42-72`;
  `ee/onyx/server/settings/api.py:126-131`; `ee/onyx/utils/tier.py:73-102`.
- **GATE:** CONFIGURATION.
- **WHY:** three settings are dangerous. `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES=true`
  with no license forces `GATED_ACCESS`. `LICENSE_ENFORCEMENT_ENABLED=false` unloads
  EE unless the legacy flag is set, which removes group ACLs and the EE beat entries.
  `MULTI_TENANT=true` turns on control-plane calls.
- **EXISTING CODE TO REUSE:** none; this is documentation plus an optional startup
  assertion.
- **MINIMUM CHANGE:** document the invariants in Plan 007 and the deployment guide.
  Optionally add a boot check that logs an error when the legacy flag is set without
  a license.
- **DEPENDENCIES:** none.
- **SECURITY:** the failure mode of losing the EE ACL implementation is **fail-open**
  at the index layer — documents lose group restriction and become reachable by
  per-email/public matching only. That deserves an explicit test, not just a note.
- **ACCEPTANCE:** invariants documented; a smoke test asserts
  `global_version.is_ee_version()` is true and that `get_acl_for_user` for a group
  member returns group-prefixed entries.

### TON-CAP-005 — Declare the file scope and retention contract

- **OBJECTIVE:** expose TEMPORARY vs PERSISTENT scope through the API so the UI
  stops inferring it.
- **CURRENT IMPLEMENTATION:** `UserFile.incognito`, `incognito_session_id`
  (`models.py:5583-5592`); sweep helpers in `db/incognito.py`; Celery
  `check-for-incognito-file-cleanup` every 10 min; `INCOGNITO_CONTEXT_TTL_SECONDS = 3600`.
- **GATE:** MISSING_DEPENDENCY — a response field, not a feature.
- **WHY:** `TON-FE-006` is blocked on a contract that the model already implies.
- **EXISTING CODE TO REUSE:** all of the above; no lifecycle change.
- **MINIMUM CHANGE:** add scope and retention fields to the user-file and project
  file response models; document the 48 h orphan rule.
- **DEPENDENCIES:** Plan 004.
- **SECURITY:** do not let an API response leak another user's incognito file
  existence. Keep privacy decided at upload time, as the model comment requires.
- **ACCEPTANCE:** the composer, project panel and file card show scope without
  reading a temp id; an unadopted incognito upload is swept after 48 h; no
  cross-user visibility.

### TON-CAP-006 — TON resource ACL foundation

- **OBJECTIVE:** give contracts, Findings, Occurrences and Reports group-scoped
  access using the existing authorization contract.
- **CURRENT IMPLEMENTATION:** absent. The reference pattern is
  `Persona__UserGroup` + `within_managed_scope_clause` + `assert_within_scope`.
- **GATE:** MISSING_DEPENDENCY.
- **WHY:** a controladoria product must restrict Findings and Reports per business
  unit. No generic per-row ACL framework exists.
- **EXISTING CODE TO REUSE:** `onyx/auth/scoped_permissions.py`, the GATE 1 / GATE 2
  contract, and the `Persona__UserGroup` junction shape including a permission level.
- **MINIMUM CHANGE:** one junction table per TON resource with a share level, plus a
  read filter and a write assertion per route. Do not invent a new authorization
  primitive.
- **DEPENDENCIES:** TON-CAP-001, Plan 003.
- **SECURITY:** every `allow_scope=True` route needs GATE 2 or a scoped manager sees
  every row. Never set `allow_scope` on delete routes. Default to non-public.
- **ACCEPTANCE:** a group-A user cannot read a group-B Finding or Report by id or by
  list; a scoped manager acts only within managed groups; deletion requires owner or
  global authority; tests cover list, detail, write and delete.

### TON-CAP-007 — TON audit trail storage

- **OBJECTIVE:** provide a queryable audit trail for TON domain events.
- **CURRENT IMPLEMENTATION:** `onyx/utils/audit.py` emits OCSF-mapped events to a
  dedicated stdout logger. **No `AuditLog` table exists.**
- **GATE:** MISSING_DEPENDENCY.
- **WHY:** Finding, Occurrence and Report history need durable, queryable, ACL-aware
  records. Query history is chat-scoped, Business-gated, and the wrong entity.
- **EXISTING CODE TO REUSE:** the audit event shape and `emit_audit_event` call sites;
  the pagination and table patterns from `QueryHistoryTable.tsx`.
- **MINIMUM CHANGE:** a TON audit table plus a read route carrying the TON-CAP-006
  ACL. Keep stdout emission as-is for SIEM.
- **DEPENDENCIES:** TON-CAP-006, Plan 003, Plan 006.
- **SECURITY:** audit rows may contain PII; apply the resource ACL. Never let audit
  writes raise into the caller — preserve the existing invariant.
- **ACCEPTANCE:** a state transition writes exactly one durable row; the history view
  is ACL-filtered and paginated; audit failure never fails the business operation.

### TON-CAP-008 — TON asynchronous report pipeline

- **OBJECTIVE:** generate, poll and download TON reports without copying the
  Business-gated route.
- **CURRENT IMPLEMENTATION:** the reference is
  `ee/onyx/server/query_history/api.py:322-455` plus
  `ee/.../query_history/tasks.py:31-121`; the multi-artifact variant is
  `usage_export_generation.py:264-386`.
- **GATE:** MISSING_DEPENDENCY for TON; the reference route is BUSINESS-gated.
- **WHY:** TON reports must be async, resumable and auditable, with visible failure.
- **EXISTING CODE TO REUSE:** the `Task` table + `register_task`, deterministic file
  ids, FileStore `has_file`/`read_file`, `StreamingResponse`, spooled temp files,
  `sanitize_csv_cell_or_none`.
- **MINIMUM CHANGE:** a TON report route set that mints its own task id, registers a
  `Task` row, sends with `expires=`, and maps state to 202/404/500 the same way.
- **DEPENDENCIES:** TON-CAP-006, Plan 003 (snapshot service), Plan 006.
- **SECURITY:** downloads must be ACL-checked and time-bounded; never expose a
  permanent URL; sanitise every user-supplied CSV cell; do not publish an
  `interpretation_pending` result as final.
- **ACCEPTANCE:** states empty/queued/generating/ready/failed/expired all reachable
  and tested; a non-authorized user cannot download; a failed run is visible, not
  silent; concurrent duplicate requests do not corrupt output.

### TON-CAP-009 — Optional: un-gate query history, usage and service accounts

- **OBJECTIVE:** restore three local admin capabilities if TON wants them.
- **CURRENT IMPLEMENTATION:** EE routers over CE tables; all local.
- **GATE:** LICENSE_TIER_ONLY — `/admin/query-history`, `/admin/chat-sessions`,
  `/admin/chat-session-history`, `/admin/usage-report`, `/admin/api-key`.
- **WHY:** useful operational visibility; also the pattern source for TON reports.
- **MINIMUM CHANGE:** remove the chosen entries from `PATH_PREFIX_MIN_TIER` and clear
  the matching `requiredTier` values.
- **DEPENDENCIES:** none.
- **SECURITY:** query history exposes full chat content and real user emails even in
  `ANONYMIZED` mode (masking is read-time only). Decide the `query_history_type`
  policy and who holds `READ_QUERY_HISTORY` before un-gating. This is a genuine
  privacy decision, not a formality.
- **ACCEPTANCE:** only `READ_QUERY_HISTORY` holders reach it; the configured
  anonymisation mode is honoured; CSV export completes and the file is ACL-checked.

### TON-CAP-010 — Optional: connector auto-sync gate

- **OBJECTIVE:** allow `AccessType.SYNC` connectors if a Vale Norte source has its
  own ACLs to mirror.
- **CURRENT IMPLEMENTATION:** `require_business_tier_for_sync_access`
  (`ee/onyx/utils/tier.py:168-189`) called from
  `connector_credential_pair.py:763-777`; per-source implementations in
  `ee/onyx/external_permissions/*`; EE beat entries every 20–30 s.
- **GATE:** LICENSE_TIER_ONLY.
- **WHY:** only if a source requires mirrored permissions. NG/Keevo and Telegram do
  not obviously need it.
- **MINIMUM CHANGE:** relax the tier check in that one guard.
- **DEPENDENCIES:** TON-CAP-001 (external groups map onto user groups).
- **SECURITY:** a SYNC cc-pair whose sync never runs is a silent over-exposure risk
  — the row exists and documents may index without correct external ACLs. Verify the
  beat entries are registered before enabling, and confirm
  `check_if_valid_sync_source` accepts the source.
- **ACCEPTANCE:** a SYNC cc-pair syncs external groups and per-document permissions;
  a user without upstream access cannot retrieve the document; disabling sync does
  not leave stale permissive ACLs.

## Success condition answers

**1. What disappears when paid Onyx entitlement is zero?**

Exactly the 18 path prefixes in `PATH_PREFIX_MIN_TIER` plus three non-path guards.
Of TON-relevant items: user-group and RBAC management, enterprise/branding writes,
query history, chat-session history, usage reports, admin analytics, service-account
API keys, the LLM gateway, SCIM, standard answers, token rate limits, outbound
hooks, log export, evals, connector auto-sync, a second enabled SSO provider, and
the chat-retention limit. Nothing else. Chat, search, agents, document sets,
projects, files, connectors, indexing, LLM providers, users administration, SSO,
Celery, Redis, FileStore and audit emission all keep working.

**2. Which of those already exist locally and only need the product gate adapted?**

All of them. Every gated capability has complete local implementation — model,
migration, API, worker and frontend — against local PostgreSQL, Redis, OpenSearch
and the local file store. Not one gated capability is missing code.

**3. Which capabilities genuinely depend on Onyx-hosted services?**

Three, none of which TON needs:

- **Tenant provisioning** (`ee/onyx/server/tenants/provisioning.py` →
  `CONTROL_PLANE_API_BASE_URL`). Registered only when `MULTI_TENANT` is true.
- **Cloud billing information** (`ee/onyx/server/tenants/billing.py` → control plane).
  Same condition.
- **License auto-fetch / re-claim** (`ee/onyx/utils/license.py:438` →
  `CLOUD_DATA_PLANE_URL`). Only for Stripe-issued `AUTO_FETCH` licenses. TON has no
  license, so it is never called.

Everything else that touches the network is telemetry (`telemetry.onyx.app`,
PostHog, HubSpot), a convenience model list on GitHub, documentation links, or a
Stripe publishable key for the billing UI. All optional, all non-blocking. **No
capability is marked REPLACEMENT REQUIRED.**

**4. What is the minimum amount of code TON itself must own?**

Six things:

1. The TON domain schema — Rule, RuleVersion, AnalysisRun, Finding, Occurrence,
   Report (Plan 003).
2. Per-resource ACL junction tables for those entities plus contracts (TON-CAP-006),
   built on the existing `Permission` + group-scope contract.
3. A queryable audit trail table (TON-CAP-007). Event emission already exists.
4. The TON report pipeline routes and tasks (TON-CAP-008), reusing FileStore, the
   `Task` table and the existing async pattern.
5. TON schedules and analysis runs (Plan 006), on top of the existing Celery, beat,
   Redis-lock and `scheduled_tasks` infrastructure.
6. The Telegram adapter (Plan 009), once its contract exists.

Plus roughly a dozen lines of gate removal across three files (TON-CAP-001, 003,
optionally 009 and 010).

Everything else — authentication, authorization, groups, ACLs, agents, document
sets, projects, files, connectors, indexing, LLM providers, workers, storage,
branding — is reused as-is or with configuration.

**5. Can the final TON deployment operate indefinitely without paying Onyx?**

**Yes.** Concretely:

- Tier resolution is a local DB read plus a local RSA verification; the public key
  ships in the repository. No entitlement server is contacted at any point.
- With no license row, the license middleware never gates and seat availability is
  unlimited (`ee/onyx/db/license.py:495-499`).
- Removing an entry from `PATH_PREFIX_MIN_TIER` is a local edit to a plain Python
  dictionary. No signature, no remote validation, nothing to expire.
- Every gated capability's implementation already runs against local infrastructure.
- The one item that must not be broken — the EE group-ACL implementation — loads by
  **default**, because `LICENSE_ENFORCEMENT_ENABLED` defaults to `"true"` and that
  alone sets `global_version.set_ee()`.

Conditions: leave `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` unset, leave
`MULTI_TENANT` false, keep the EE code tree loaded, set `DISABLE_TELEMETRY`, and
pre-bake or mount embedding weights for an offline first boot.

## Verification and integrity statement

- Method: static reading of source. Nothing was executed against a running service.
- `git status --short` was captured before and after. The only change this audit
  made is the creation of this file, `plans/ton/capability-edition-audit.md`.
- **Pre-existing uncommitted changes were present before the audit started** and
  were not made by it: 25 modified files under `web/src` and `web/tests` (error
  pages, i18n catalogs, `admin-routes.ts`, `admin-sidebar-utils.ts`,
  `AdminChrome.tsx`, sidebar components, `constants.ts`, `AppProvider.tsx`,
  `SettingsPage.tsx`, appearance-theme e2e specs) plus untracked `web/scripts/`,
  `web/src/lib/ton/product-surface.ts` and `web/src/ton/ton-product-surface.test.tsx`.
  This is TON-FE-003 work in progress.
- No tier check was removed. No EE route was enabled. No import was altered. No EE
  code was moved. No migration was created. No database model was changed. No
  environment variable or feature flag was changed. No billing code was touched. No
  navigation was modified. No RBAC was implemented. No hidden feature was exposed.
  No dependency was installed.

### Claims I could not fully verify

Stated plainly so they are not mistaken for confirmed facts:

- The exact HuggingFace repository ids and revisions the model server pulls at first
  boot. I read `model_server/main.py` (HF telemetry disabled, cache path,
  lifespan does no network fetch) but not all of `encoders.py`.
- Which way `is_craft_available_for_deployment` resolves when the feature-flag
  provider is the no-op. Relevant only if TON wants Craft.
- The full body of `ee/onyx/db/license.py` beyond `check_seat_availability`,
  `get_license_metadata` and `refresh_license_cache` call sites.
- `OnyxErrorCode.FEATURE_NOT_AVAILABLE.status_code == 402` is confirmed by the unit
  test `backend/tests/unit/ee/onyx/server/middleware/test_tier_gate.py:106-109` and
  by the observed 402 recorded in the frontend roadmap, not by reading
  `error_codes.py` directly.
- Whether a `visibleWhen` predicate elsewhere gates the `/admin/standard-answer`
  page, whose frontend `requiredTier` is `null` while the backend requires
  ENTERPRISE.
