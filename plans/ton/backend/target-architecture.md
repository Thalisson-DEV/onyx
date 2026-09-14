# TON target architecture and boundary decisions

This document describes the target shape for TON V1. It is a design handoff,
not source code. It assumes only a web product experience.

## Issues to Address

Preserve Onyx's proven chat, knowledge, file, provider and worker boundaries,
while isolating TON domain behavior from Craft, SaaS billing, external
channels and source-system writes.

## Important Notes

- `plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt` is now an
  available domain evidence artifact. It supplies candidate financial,
  operational, reconciliation, budget, fuel and access-control scenarios for
  Jan-Apr 2026, but it does not validate source schemas or production rules.
- `backend/onyx/main.py:552-631` is the CE router registry. New TON routes
  should be added as a focused feature module and use existing global prefix
  and auth checks.
- `backend/ee/onyx/main.py:132-178` owns EE groups, tenant, license, billing
  and SCIM surfaces. TON should reuse permission primitives, not inherit SaaS
  gating accidentally.
- `backend/onyx/server/query_and_chat/models.py:103-168` warns that the core
  send-message model is a backwards-compatible contract. Keep TON metadata
  additive or use a separate TON route.
- `backend/onyx/connectors/interfaces.py:45-110` and
  `backend/onyx/connectors/models.py:196-247` are the source adapter boundary.
- `backend/onyx/background/celery/tasks/scheduled_tasks/tasks.py:88-243`
  provides useful queue, commit/enqueue, expiry and sweeper patterns but is
  Craft-specific and has no business retry.

## Report-driven source boundary

The target source layer must preserve enough provenance to reproduce the
report-derived candidates. Before a candidate can become a rule, it must carry
the source snapshot, opaque record identifiers, unit, period, currency,
extraction time and evidence location. The report names these source classes:
cash-flow database, Ferrari DRE, active contracts, bank extracts, payroll,
invoice/measurement records, fleet/rental records and access logs
(`plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt:65-66,534-556`).

The source layer must also represent missing or conflicting evidence. Examples
include two parcelamento totals, two mutual totals, five versus six units with
current budgets, and two proposed travel-accountability deadlines. These cases
must remain non-final until an owner resolves them. A business field mentioned
by the report is a candidate contract, not a confirmed NG/Keevo column.

## Target components

```text
Web application
  -> TON API routes
     -> auth, tenant, global/scoped permission checks
     -> TON command/query services
        -> Rule detector (deterministic)
        -> Interpretation service (mandatory for final state)
        -> Finding/Occurrence lifecycle
        -> Report snapshot service

Source adapters
  -> Onyx Connector/Document/UserFile boundary
  -> normalized source snapshot/evidence
  -> existing parser/chunker/embedder/indexing/retrieval

Agent layer
  TON Central/CEO supervisor
    -> CFO
    -> Frota
    -> Contratos
    -> Auditoria
    -> RH

Worker layer
  beat -> AnalysisSchedule dispatcher -> analysis queue
       -> detector -> interpretation -> finalization -> report projection

Future adapters
  NG/Keevo read-only adapter (blocked)
  Telegram adapter (first external channel, outside core)
  WhatsApp adapter (later, outside core)
```

## Authorized agent access

Direct access is explicit, not inferred from a general chat persona:

| Agent | Default data scope | Allowed output | Required authorization |
|---|---|---|---|
| TON Central/CEO | Cross-domain summaries and approved evidence | Supervisor result and report | Executive role plus tenant scope |
| CFO | Financial sources and approved financial evidence | Financial Findings and interpretation | Finance role plus unit scope |
| Frota | Fleet, trip and maintenance sources | Fleet Findings and interpretation | Fleet role plus unit scope |
| Contratos | Contract documents and clauses | Contract Findings and interpretation | Legal/contract role plus document ACL |
| Auditoria | Approved controls and audit evidence | Audit Findings and interpretation | Audit role plus tenant scope |
| RH | Approved HR/policy data, masked by default | HR Findings and interpretation | HR role plus restricted unit scope |

Every result stores the agent identity, source scope, permission decision,
result type (`result`, `timeout`, `error`, `insufficient_data`) and safe error
class. A partial supervisor result preserves successful child results and makes
the finalization policy explicit.

## File lifecycle

Use a separate lifecycle from Onyx's current file processing status. The exact
column names are implementation choices, but states and transitions are not:

```text
uploaded -> processing -> ready_temporary -> deleted
uploaded -> processing -> ready_persistent -> promoted -> ready_persistent
processing -> failed
any non-deleted state -> deleting -> deleted
any state with missing metadata/blob -> orphaned -> reconciled or quarantined
```

Rules:

- `ready_temporary` is private to its request/session/run.
- Temporary records carry `no_index`, `no_retrieval` and `no_report` policy
  flags where the product requires strict isolation.
- Promotion from temporary to persistent is an explicit authorized action. It
  creates a new audit event and must not be inferred from project linkage.
- Cleanup is idempotent. Repeating it after the blob or row is already gone is
  a successful no-op.
- A failed promotion leaves an auditable state and does not expose the file as
  persistent. Safe operational reversal returns to temporary or quarantine;
  it must not silently restore a deleted record.
- A periodic reconciler finds rows without blobs and blobs without rows. It
  records `orphaned`, retries safe cleanup and quarantines ambiguous cases.
- File bytes, extracted text, embeddings and report artifacts each need a
  retention decision. Deleting one layer must not leave a searchable orphan.

## Integration boundaries

### NG/Keevo

NG/Keevo is future and BLOCKED. The repository has no validated source schema,
access credentials, record identifiers, quotas or deletion contract. Implement
only a read-only interface with operations such as source health, bounded page
read and snapshot metadata. Do not name fields, map business records or write
back until Vale Norte supplies the contract and access test.

### Telegram

Telegram is the first planned external TON channel. It is not a core
dependency. It may translate an authorized message into a TON command. It may
return a report link or summary. It must use the same application and domain
capabilities as the web. It must not own domain state, bypass server
permissions or add channel-specific logic to the detector.

### WhatsApp

WhatsApp follows later through the same adapter boundary. It must not own
domain state or bypass web permissions. It requires an
approved transport, identity, replay, rate-limit and delivery contract before
implementation.

## Web-only configuration

The implementation must define a TON configuration independent of PostHog:

| Setting | TON V1 default | Meaning |
|---|---|---|
| `TON_WEB_ONLY` | `true` | Web UX is the only shipped experience. |
| `TON_EXTERNAL_TELEMETRY_MODE` | `off` | No external content telemetry. |
| `TON_TRACE_CONTENT_MODE` | `metadata` | Spans contain IDs/status/timing only. |
| `TON_PRODUCT_SURFACES` | `ton` | Hide Onyx SaaS/Craft surfaces. |
| `TON_REPORTS_ENABLED` | `true` | Enable web report review. |
| `TON_EXTERNAL_CHANNELS` | empty | Core starts without a channel dependency. Telegram is the first later adapter. |
| `TON_SOURCE_WRITES` | `false` | Advisory-only analysis. |

These names are proposed configuration contracts. The executor must search for
existing names, add tests for defaults and avoid making TON depend on the
PostHog package. `web/src/app/providers.tsx:11-22` may remain in the Onyx web
bundle only when TON explicitly disables initialization; the TON core must be
usable with PostHog absent.

## Surface policy

- **Preserve**: web auth, chat, search, files, agents, sources, settings,
  permissions and operational health.
- **Replace**: default persona names, app branding, navigation, settings copy,
  reports and admin pages.
- **Hide**: Craft/build, billing, trial, plans, Stripe, upsell, Cloud tenant
  acquisition, Onyx support/marketing/legal links, mobile/desktop/widget and
  extension UX when not needed by a shared contract.
- **Remove only after proof**: mobile auth, shared `MessageOrigin` values,
  extension context fields, generated desktop package and worker listeners.

## Dangerous dependencies

Do not remove OpenSearch, FileStore, PostgreSQL migrations, Redis, Celery
queues, tenant context, permissions or shared chat routes. Vespa remains a
compatibility dependency until tenant migration evidence proves otherwise.
Do not edit generated compose output directly; the deployment plan owns its
template and generated artifacts.

## Implementation strategy

Build the domain behind existing boundaries. Keep channels and product gates at
the edge. Make source adapters, detector, interpreter, lifecycle, reporting and
workers independently testable. Use the target components above as dependency
direction, not as permission to introduce a new orchestration framework.

## Scope

In scope: target boundaries, agents, file lifecycle, integrations, web-only
configuration and preserve/hide/replace/remove policy.

Out of scope: source schema invention, Telegram/WhatsApp implementation, source writes,
mobile/desktop/widget/extension UX, generated deployment edits and code changes.

## Tests

Create named specs before running them:

```text
rg -n "TON_WEB_ONLY|TON_EXTERNAL_TELEMETRY_MODE|TON_TRACE_CONTENT_MODE|TON_SOURCE_WRITES" backend web
rg -n "ready_temporary|ready_persistent|promoted|orphaned|no_index|no_retrieval|no_report" backend/tests web/tests
uv run pytest backend/tests/unit/ton/test_boundaries.py -xv
cd web; bun run test -- src/ton/ton-web-only.test.tsx --runInBand
```

Expected result after implementation: settings have safe defaults, lifecycle
transitions and web surface policy are covered, the report-derived evidence
catalog remains non-final until validation, and the TON core imports without
PostHog or a channel adapter.

## Done criteria

- [ ] Agent access is explicit for Central/CEO, CFO, Frota, Contratos, Auditoria and RH.
- [ ] Partial specialist states persist result, timeout, error or insufficient data.
- [ ] Temporary/persistent lifecycle and explicit promotion exist.
- [ ] Cleanup is idempotent and orphan reconciliation is auditable.
- [ ] Temporary files enforce no-index/no-retrieval/no-report where configured.
- [ ] NG/Keevo is a blocked read-only interface with no field mapping.
- [ ] Telegram and WhatsApp stay outside core. Telegram is the first external adapter.
- [ ] TON web-only settings work with PostHog disabled.
- [ ] Remove/hide decisions use the surface matrix and consumer evidence.

## STOP conditions

- Stop if an agent is granted cross-domain data without an approved role/scope.
- Stop if temporary data can enter persistent search, Finding evidence or reports.
- Stop if NG/Keevo access or schema is assumed rather than supplied.
- Stop if TON configuration requires PostHog or a channel adapter.
- Stop if a removal changes a shared contract without deprecation evidence.
- Stop if generated deployment files are edited outside the deployment plan.
