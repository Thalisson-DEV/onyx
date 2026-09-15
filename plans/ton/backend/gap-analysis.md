# TON discovery: gap analysis and prioritized findings

This artifact converts the current architecture into actionable gaps. It was
written from direct reads at the evidence paths. It is not a production rule
catalog.

## Issues to Address

TON requires deterministic detection, mandatory AI interpretation before final
Finding/Report publication, specialist agents, read-only source integration,
temporary/persistent document controls, immutable reports and private
self-hosted telemetry defaults. Onyx supplies useful primitives but not the TON
domain lifecycle.

## Important Notes

`plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt` is now available
and is incorporated as domain evidence. It covers Jan-Apr 2026 and states a
cross-check of 5,191 cash-flow entries, seven units, the Ferrari DRE and active
contracts (`:8-18`, `:65-66`). The underlying workbook, DRE, contracts, bank
extracts and NG/Keevo contract are still absent. No report-derived candidate
may reach production until source records, units, limits, periods,
missing-data behavior and business ownership are approved.

## Vale Norte evidence impact

The report adds concrete candidate checks, but it does not add a validated
source schema. Full evidence, fields, owners, open questions and traceability
are in `domain-rules.md`.

| Report items | Classification | Gap added | Planned handling |
|---|---|---|---|
| 1.1, 1.2, 1.3 | mixed | Tax, retention and intercompany values need source-row reconciliation; 1.1 has four conflicting values and 1.3 has three conflicting totals. | Plan 001 evidence; Plan 003 typed rules and approval gates. |
| 1.4, 1.5 | mixed | 1.4 visible rows are R$ 275.00 below the stated total; 1.5 unit sums conflict with aggregates. Supplier identity, contracts and payroll components are also missing. | Plan 001 provenance; Plan 003 completeness and ratio gates. |
| 1.6, 1.7, 1.8 | mixed | 1.6 has conflicting baseline/percentage variants; revenue and expense spikes remain hypotheses for cause and competence. | Plan 003 deterministic candidates; Plan 006 report review. |
| 2.1, 2.2 | mixed | Posting and accounts-payable controls lack event logs, accepted fields and approved SLA/sanction policy. | Plan 004 evidence-preserving intake; Plan 006 administration. |
| 2.3, 2.4, 2.5 | mixed | Rental allocation, duplicate payment and expense settlement need identity, timing and exception contracts. | Plans 003/004/006; do not infer blocking or estorno. |
| 3.1 | mixed | Bank-to-ERP mismatches have no detailed extract, amount or matching tolerance. | Plan 004 reconciliation evidence; Plan 006 workflow. |
| 3.2 | insufficient-data | API/CNAB feasibility depends on missing NG/Keevo and bank contracts. | Keep adapter read-only and BLOCKED; assess only after access. |
| 3.3 | insufficient-data | Bank access risk is asserted without user, role or activity evidence. | Plan 002 security gate; Plan 006 controlled administration. |
| 4.1 | mixed | Budget coverage is stated as both five and six of seven units. | Reconcile source snapshots before Plan 003 rule approval. |
| 4.2 | insufficient-data | Fuel spend exists, but station agreements, vehicle logs and limits are absent. | Plan 004 source and quality contract; Plan 006 review. |

The report also contains policy proposals. It conflicts on travel settlement
timing (48 hours versus five business days) and gives dates and responsibilities
that require owner approval. These are workflow inputs, not automatic rules.

## Material-source reconciliation gates

The following values are copied as source conflicts, not business corrections.
They must stay visible until the underlying artifacts are reconciled:
(`plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt:24-58,69-99,134-173,179-212,218-251,257-280`).

1. **Section 1.1**: seven-row sum R$ 90,877,705.63; table total
   R$ 90,877,705.65; paid amount R$ 4,519.42; narrative/table difference
   R$ 4,519.40.
2. **Section 1.3**: totals by origin R$ 4,210,512.00; monthly table total
   R$ 4,210,513.00; narrative total R$ 4,210,513.16.
3. **Section 1.4**: visible rows sum R$ 473,552.00 versus stated total
   R$ 473,827.00, a R$ 275.00 difference. Completeness blocks activation.
4. **Section 1.5**: visible unit sums are payroll R$ 4,984,535.00 and charges
   R$ 2,827,183.00; declared totals are payroll R$ 4,733,535.00 and charges
   R$ 2,936,450.00. The aggregate ratio is blocked.
5. **Section 1.6**: calculated Jan-Mar average R$ 3,474,240.67 versus
   R$ 3,474,174; calculated fall approximately 87.13%, versus report prose
   87% and table −88.0%. Baseline and rounding require owner decision.
6. **Summary versus section 1**: nine types are declared in the summary, but
   section 1 contains eight numbered items, 1.1–1.8. Coverage is not complete
   until this count is reconciled.

## Gap matrix

| Area | CURRENT | REQUIREMENT | GAP | CHANGE | COMPONENTS | RISK | TEST |
|---|---|---|---|---|---|---|---|
| Chat | `ChatSession`, messages and resumable SSE exist (`backend/onyx/db/models.py:3168-3268`; `backend/onyx/server/query_and_chat/chat_backend.py:771-803,1280-1357`). | Web chat links to analyses, evidence and reports. | No TON run/evidence references in the core response. | Add optional TON references without breaking `SendMessageRequest`. | Chat route/models, session DB layer, web service contract. | HIGH | Chat, resume, permission and incognito integration tests. |
| Agents | Persona and Tool models exist (`backend/onyx/db/models.py:4015-4065,4178-4290`). | Central TON supervisor and direct specialist access. | No domain capability, memory policy or per-agent ACL. | Add agent metadata, source/tool/memory allowlists and authorization. | Persona API, tool constructor, permissions. | HIGH | Allowed/denied source and tool tests. |
| Orchestration | Deep Research is search-only (`backend/onyx/deep_research/dr_loop.py:254-257`). | Specialist routing with durable execution state. | Existing runner has search restrictions and one-tool-type turn (`backend/onyx/tools/fake_tools/research_agent.py:399-408`). | Extend native nested ToolCall/parallel runner with TON run records. | Deep Research, ToolCall, Celery. | HIGH | Parallel, timeout, retry and partial-failure tests. |
| Background | Celery apps/workers exist; `TenantAwareTask` sets context (`backend/onyx/background/celery/apps/app_base.py:110-128`). | Safe asynchronous analysis and cleanup. | Missing tenant falls back to default schema. | Require tenant ID and verify resource ownership. | Celery base, DB tenant context. | HIGH | Missing/mismatch tenant tests. |
| Scheduled processing | Due-run locking and queues exist (`backend/onyx/background/celery/tasks/scheduled_tasks/tasks.py:88-186`). | `AnalysisSchedule` triggers repeatable rule runs. | Current task is Craft-oriented; `acks_late=False` and executor catches exceptions (`:209-243`); V1 has no Celery retry. | Add TON schedule/run records, internal timeout, business retry, `expires`, crash/sweeper and misfire policy. | Scheduled tasks, beat, dedicated queue. | HIGH | overlap, misfire, retry, crash and stale-run tests. |
| Alerts | No TON alert or notification model found. | Web-visible advisory alert state with audit. | No alert recipient, delivery, acknowledgement or suppression contract. | Add an in-app alert projection from Finding lifecycle; keep external delivery out of V1. | Finding service, web route, audit. | MED/HIGH | create, dedup, acknowledge and permission tests. |
| Knowledge | Connector/document/indexing pipeline exists (`backend/onyx/connectors/interfaces.py:45-110`; `backend/onyx/indexing/indexing_pipeline.py:1463-1568`). | Vale Norte knowledge with source ACL and quality signals. | No TON source registry or quality result contract. | Add source metadata and quality extension points. | Connector boundary, DocumentSet, indexing adapters. | HIGH | ACL, stale, malformed and reindex tests. |
| Persistent documents | UserFile and projects persist files (`backend/onyx/db/models.py:5558-5645`). | Explicit persistent organizational knowledge. | User ownership does not define TON source, retention or promotion. | Add lifecycle/scope metadata and explicit promotion. | UserFile, FileStore, UserProject, DocumentSet. | HIGH | promotion, retention and cross-user tests. |
| Temporary documents | Incognito file cleanup uses status/session fields (`backend/onyx/db/models.py:5582-5639`). | Temporary input has no persistent retrieval/report effect. | No TON-wide no-index/no-retrieval/no-report contract. | Enforce scope at indexing, retrieval, findings and report boundaries. | UserFile, incognito context, indexing adapters. | HIGH | leakage and orphan cleanup tests. |
| Ingestion | Parser/chunker/embedder/vector writer exist (`backend/onyx/file_processing/extract_file_text.py:829-890`; `backend/onyx/indexing/chunking/document_chunker.py:25-128`). | Preserve evidence and spreadsheet structure. | `.xls` and quality semantics are not validated. | Decide parser with fixtures; carry sheet/row/column evidence. | Extractor, chunker, embedder, FileStore. | HIGH | PDF, XLSX, XLS, CSV, DOCX, image, text, JSON and ZIP tests. |
| Rule engine | No Rule or RuleVersion model found; report-derived candidates now exist in `domain-rules.md`. | Detector never depends on LLM. | Source artifacts, domain keys, thresholds and missing-data contracts are not validated. | Add typed deterministic operators only after source and owner approval; retain mixed and insufficient-data states. | New TON domain, DB/migrations, services. | HIGH | boundary, arithmetic-conflict and deterministic tests. |
| Finding/Occurrence | No domain Finding/Occurrence model found; only `UsageReport` and capability report (`backend/onyx/db/models.py:2115,5443-5468`). | Stable identity, evidence, lifecycle and dedup. | No logical-key or concurrent merge semantics. | Add generic lifecycle with opaque identity until domain approval. | PostgreSQL, service, API, audit. | HIGH | duplicate, retry, concurrent and reopen tests. |
| AI interpretation | Current chat/Deep Research uses LLM loops. | Interpretation is mandatory before final Finding/Report. | No interpretation state or explicit failure state. | State candidate/detected -> interpretation_pending -> interpreted/final; persist failure and block finalization. | AnalysisRun, Finding, interpreter service. | HIGH | LLM unavailable, malformed output and retry tests. |
| Reporting | `UsageReport` links metadata to FileRecord only (`backend/onyx/db/models.py:5443-5468`). | Canonical immutable TON report. | No domain snapshot, hash or append-only history. | Use append-only rows plus canonical snapshot hash and FileStore artifact when needed. | Report model/service, FileStore, audit. | HIGH | mutation rejection, hash and reproducibility tests. |
| NG/Keevo | No validated adapter, schema or access was found. | Future read-only source adapter. | Contract, authentication, identifiers and limits are unknown. | BLOCK implementation. Define only a typed interface with no field mapping. | Connector interface, contract fixtures later. | HIGH | Contract tests only after Vale Norte supplies access. |
| Telegram/WhatsApp | No validated channel contract was found. | Telegram is the first external adapter; WhatsApp follows later. | No adapter contract, identity or ownership. | Keep core channel-neutral; block Plan 009 until its contract exists. | Port/adapter boundary later. | MED | Prove no core dependency; add adapter tests after contract approval. |
| Administration | EE groups and admin routes exist (`backend/ee/onyx/server/user_group/api.py:83-125`; `backend/onyx/main.py:583-598`). | Web admin for rules, agents, sources, runs, findings and reports. | No TON admin resources or audit events. | Add private routes with global/scoped permission checks. | Admin routers, permissions, audit. | HIGH | admin authorization and audit integration tests. |
| Security | RBAC/scopes and log-only audit exist. | Tenant isolation and domain audit. | Tenant fallback, public defaults, memory bypass and raw errors/traces. | Apply security findings before domain rollout. | Auth, Celery, tool runner, SSE, audit. | HIGH | negative security suite. |
| Telemetry/privacy | Backend sends arbitrary data (`backend/onyx/utils/telemetry.py:97-157`); web loads PostHog/GTM (`web/src/app/layout.tsx:4-25,137-176`; `web/src/app/providers.tsx:11-22`). | Default off or metadata-only. | Full traces, session recording, IP, custom JS and outbound analytics need policy. | Add TON privacy profile and network tests. | Backend telemetry/tracing, web providers/layout. | HIGH | outbound request and redaction tests. |
| Product cleanup | Billing/gating exists (`web/src/lib/billing/svc.ts:1-70`; `web/src/providers/ProductGatingWrapper.tsx:7-25`). | TON web-only experience without SaaS upsell. | Cloud, trial, plans, Stripe, support and Onyx links remain. | Classify each surface as hide/replace/preserve/remove. | Web routes, settings, EE billing. | MED/HIGH | route and visual smoke tests. |
| Deployment | Compose and Supervisor run full Onyx stack (`deployment/docker_compose/docker-compose.yml:46-127`; `backend/supervisord.conf:30-142`). | TON internal deployment with secure injection. | Committed/default credential fallbacks are P0. | External secret injection, rotate existing credentials, disable unneeded SaaS. | Compose template, supervisor, env orchestration. | CRITICAL | config scan, clean deploy, health and worker smoke. |

## Findings

Plan 002 closed SECURITY-01 through SECURITY-05 and PRIVACY-01/02. SECURITY-06
remains assigned to Plan 005. Plan 002 did not change domain schema, agent
routing or deployment artifacts.

Plan 007 closed SECURITY-07 and opened SECURITY-08, which it analysed and
deferred rather than fixed. SECURITY-08 needs a migration and is blocked on Plan
003 readiness.

### [SECURITY-01] Redact content-bearing traces

- **Evidence**: `backend/onyx/tools/tool_runner.py:138-218` attaches tool
  arguments, errors and stack traces; `backend/onyx/tracing/framework/create.py:185-244`
  accepts full model input/output/reasoning/tools.
- **Impact**: financial, HR and contract content can leave the deployment.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Fix sketch**: TON default metadata-only spans, allowlisted fields,
  redaction and network assertions.

### [SECURITY-02] Sanitize SSE errors

- **Evidence**: `backend/onyx/server/query_and_chat/chat_backend.py:937-940`
  yields `str(e)` to the client.
- **Impact**: internal provider or infrastructure details can be disclosed.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Fix sketch**: stable public code and request ID; detail only in sanitized logs.

### [SECURITY-03] Bound ZIP expansion

- **Evidence**: `backend/onyx/server/documents/connector.py:325-350` reads each
  ZIP member completely without a visible aggregate expansion/member cap.
- **Impact**: archive bombs can exhaust memory or storage.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Fix sketch**: enforce expanded-byte, entry, depth, name and ratio limits.

### [SECURITY-04] Enforce unknown-size upload limits

- **Evidence**: `backend/onyx/server/features/projects/projects_file_utils.py:38-68`
  skips the size check when stream size is unknown.
- **Impact**: an unknown-size stream may bypass the upload limit.
- **Effort**: M.
- **Risk**: MED/HIGH.
- **Confidence**: MEDIUM.
- **Fix sketch**: count bytes while streaming and reject after the cap.

### [SECURITY-05] Fail closed without tenant ID

- **Evidence**: `backend/onyx/background/celery/apps/app_base.py:110-128`
  substitutes the default schema when `tenant_id` is absent.
- **Impact**: a sensitive analysis may use the wrong tenant.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Fix sketch**: require tenant ID, validate object ownership and test absent/mismatch.

### [SECURITY-06] Audit specialist memory bypass

- **Evidence**: `backend/onyx/tools/tool_constructor.py:523-534` injects
  MemoryTool from a user flag outside ordinary persona tool selection.
- **Impact**: a specialist may read memory outside its domain.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: MEDIUM.
- **Fix sketch**: explicit agent memory policy, default deny for sensitive domains.

### [SECURITY-07] Remove deployment credential fallbacks

- **Status**: CLOSED by Plan 007 at commit `80e76cfb12`.
- **Evidence**: credential environment fallbacks were present in
  `deployment/docker_compose/docker-compose.yml:81-93,530-531` and the source
  template at `deployment/docker_compose/docker-compose.template.yml:100-115,640-643`.
  The env templates also committed database and object-storage passwords.
- **Impact**: default credentials can expose search or object storage when
  deployments copy development settings.
- **Effort**: M.
- **Risk**: CRITICAL.
- **Confidence**: HIGH.
- **Resolution**: every owned compose variant now declares its credentials with
  `${NAME:?...}`, so a missing value is a configuration failure that names the
  variable and starts nothing. The env templates ship the keys with no value, and
  both guided installers generate them. Operational rotation is documented in
  `007-deployment-hardening.md`; no value was read or printed.
- **Follow-up**: application-level defaults still exist at
  `backend/onyx/configs/app_configs.py:470,637`. No compose path reaches them, but
  a process started outside compose can. Tracked as a remaining risk in Plan 007.

### [SECURITY-08] Encrypt LLM provider `custom_config` at rest

- **Status**: OPEN. Raised by the capability audit, analysed by Plan 007,
  deferred with a named prerequisite. Not fixed.
- **Evidence**: `backend/onyx/db/models.py:3624-3626` stores `custom_config` as
  plain `postgresql.JSONB()` while the sibling `api_key` at `:3617-3619` uses
  `EncryptedString()`. The dict holds AWS Bedrock keys, Vertex service-account
  JSON and LM Studio bearer tokens. `VoiceProvider.custom_config` at `:3809-3812`
  has the same defect.
- **Impact**: provider credentials are readable by anything with database access.
  API masking (`_mask_provider_credentials`) is presentation, not encryption.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Blocker**: the fix needs a `jsonb` → `bytea` migration plus an
  application-level data rewrite, and the live database still references unknown
  Alembic revision `6e8f0a2b1c35`. Plan 007 must not author migration-bearing
  changes.
- **Fix sketch**: reuse `EncryptedJson`; see TON-SEC-007-A in
  `007-deployment-hardening.md` for the full design, reader list and test list.
  Depends on Plan 003 readiness.

### [PRIVACY-01] Make telemetry and browser analytics opt-in

- **Evidence**: backend telemetry sends arbitrary `data` at
  `backend/onyx/utils/telemetry.py:97-157`; PostHog session recording leaves
  `maskAllInputs` false at `web/src/app/providers.tsx:11-22`; layout loads GTM,
  trackers and custom script at `web/src/app/layout.tsx:137-176`.
- **Impact**: query content, identifiers, IP and browser events may leave TON.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Fix sketch**: default off, metadata-only, field masking, outbound allowlist,
  explicit consent/config and network tests.

### [PRIVACY-02] Protect full URL and message boundaries

- **Evidence**: `web/src/proxy.ts:138-145` carries full query/hash in login
  redirects; `web/src/sections/sidebar/AccountPopover.tsx:56-67` encodes current
  query state; `web/src/lib/chat/hooks.ts:146-147` accepts window messages.
- **Impact**: tokens or sensitive query data can enter URLs; an unvalidated
  message source/origin can alter chat state.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: MEDIUM.
- **Fix sketch**: allowlist query keys, never carry secrets in `next`, validate
  `event.origin` and `event.source`, and add iframe/extension tests.

### [DIRECTION-01] Introduce explicit interpretation states

- **Evidence**: current Finding/Rule models are absent; chat and Deep Research
  are LLM-oriented. No `interpretation_pending` state exists in the inspected
  domain models.
- **Impact**: a detected candidate can be shown as final without mandatory AI
  interpretation or an auditable failure.
- **Effort**: M.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Fix sketch**: use `candidate`/`detected`, `interpretation_pending`,
  `interpreted`/`final` and `interpretation_failed`; block final report output
  until interpretation succeeds or an explicit failed state is shown.

### [DIRECTION-02] Make reports append-only and hashable

- **Evidence**: `UsageReport` is metadata plus a FileRecord link at
  `backend/onyx/db/models.py:5443-5468`; scheduled run history is Craft/Build
  coupled at `:6837-6915`.
- **Impact**: reports cannot prove which inputs, rules and evidence produced them.
- **Effort**: L.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Fix sketch**: append-only rows, canonical snapshot, hash, optional FileStore
  artifact and mutation rejection. A schema decision must precede migrations.

### [TECH-DEBT-01] Separate TON schedules from Craft execution

- **Evidence**: `backend/onyx/background/celery/tasks/scheduled_tasks/tasks.py:117-160`
  gates runs on Craft; `:209-243` uses `acks_late=False`, catches exceptions and
  does not request Celery retry.
- **Impact**: TON business retry and timeout semantics would be hidden by Craft
  behavior.
- **Effort**: M/L.
- **Risk**: HIGH.
- **Confidence**: HIGH.
- **Fix sketch**: reuse locking, commit/enqueue, expiry and sweeper; add
  `AnalysisSchedule`/`AnalysisRun`, internal timeout, business retry policy and
  explicit overlap/misfire outcomes.

## Implementation strategy

Execute the numbered plans in `plans/ton/`. Keep this matrix as the acceptance
source. Add a row for every new boundary rather than hiding a gap in prose.

## Tests

This discovery artifact has no source tests. Reproduce absence claims with:

```text
rg -n "class (Finding|Occurrence|Rule|RuleVersion|AnalysisRun)|__tablename__.*(finding|occurrence|rule|analysis|report)" backend/onyx/db/models.py backend/alembic/versions backend/alembic_tenants/versions
rg -n "acks_late=False|autoretry_for|self\.retry|run_scheduled_task" backend/onyx/background/celery/tasks/scheduled_tasks/tasks.py
rg -n "PostHog|session_recording|maskAllInputs|CustomAnalyticsScript|GTM|postMessage|searchParams" web/src/app web/src/lib web/src/providers web/src/sections
rg -n "OPENSEARCH_ADMIN_PASSWORD|S3_AWS_ACCESS_KEY_ID|S3_AWS_SECRET_ACCESS_KEY|MINIO_ROOT_PASSWORD" deployment/docker_compose/docker-compose.template.yml deployment/docker_compose/docker-compose.yml
```

Expected results: no TON domain models; `acks_late=False` and no retry policy;
analytics/message boundaries; credential fallback names; and the report file
under `plans/`. Report-derived candidates remain gated by source validation and
approval. Do not output secret values.
