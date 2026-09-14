# TON discovery: current architecture and web contract map

This is a read-only discovery artifact. It was checked against commit
`a0370f232b` on 2026-09-13. Plan 001 revalidated it against
`6e4b2a066459e3bd7217341b6f2fa5af4eb4bc4f` on 2026-09-14. It is not an
implementation plan and contains no secret values.

## Issues to Address

Map the Onyx backend before changing it for TON. Preserve the web contracts
that remain in scope. Do not infer that a client or route is removable because
TON V1 has only a web experience.

The Vale Norte source report
`plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt` is now in this
checkout. Its report-derived candidates are incorporated in `domain-rules.md`.
They do not authorize production rules: the underlying workbook, DRE,
contracts, bank extracts and NG/Keevo contract remain unvalidated.

## Important Notes

### Runtime entrypoints and API groups

### Vale Norte evidence boundary

- `plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt:8-18` declares a
  Jan-Apr 2026 review of 5,191 cash-flow entries across seven units, cross-read
  with the Ferrari DRE and active contracts.
- Sections 1.1-4.2 provide candidate financial, operational, bank, budget,
  fleet and access-control checks. `plans/ton/domain-rules.md` records each
  item as deterministic candidate, interpretation-only, mixed or
  insufficient-data.
- The report is evidence data. It does not confirm NG/Keevo columns, source
  identifiers, thresholds, credentials, access roles or write permissions.

- `backend/onyx/main.py:516-631` builds the CE FastAPI app and includes chat,
  query, documents, users, admin, connectors, credentials, projects,
  document sets, hierarchy, search, personas, agents, tools, settings, LLM,
  embedding, MCP, skills, PAT and captcha routers.
- `backend/ee/onyx/main.py:81-178` wraps CE with tier, tenant and license
  middleware. It adds groups, analytics, query/search, hooks, LLM gateway,
  enterprise settings, usage/log export, license, billing, tenants and SCIM.
- `backend/model_server/main.py:148-166` starts the model server.
- `backend/onyx/server/auth_check.py:17-35` defines health, `/me`, auth type
  and opt-in API documentation as public route specifications.
- `backend/onyx/server/query_and_chat/chat_backend.py:771-803` exposes
  `/chat/send-chat-message`; `:1280-1357` exposes resumable SSE.
- `backend/onyx/server/features/projects/api.py:174-230` uploads user files;
  `:280-362` links and unlinks project files.
- `backend/onyx/server/features/persona/api.py:166-225` shows persona
  visibility and admin permission patterns.
- `backend/ee/onyx/server/user_group/api.py:83-125` shows scoped group reads.

### Authentication and authorization

- `backend/onyx/auth/permissions.py:320-365` is the native
  `require_permission` dependency. Scoped managers need a second handler-level
  check. New TON routes must use this pattern.
- `backend/onyx/server/auth/mobile.py:8-60` reuses the same session strategy
  with bearer transport for mobile. This is out of the TON V1 experience but
  not safe to delete before consumer deprecation.
- `backend/onyx/utils/audit.py:1-12,53-108,261-310` emits tenant-tagged,
  secret-free, log-only audit events. It lacks domain events for rule changes,
  analysis, delegation, Findings, Occurrences and reports.

### Data and execution layers

- `backend/onyx/db/models.py:3168-3268` stores chat sessions and incognito
  mode; `:3271-3411` stores messages; `:3414-3487` stores nested tool calls,
  parallel turns and child calls.
- `backend/onyx/db/models.py:3955-4013` stores document sets;
  `:4015-4065` stores tools; `:4178-4290` stores personas and sharing.
- `backend/onyx/db/models.py:4841-4885` stores FileStore metadata and
  PostgreSQL Large Object content.
- `backend/onyx/db/models.py:5558-5645` stores user files, status, project and
  persona links, incognito ownership and cleanup indexes.
- `backend/onyx/db/models.py:5813-5888` stores MCP server configuration and
  public/ACL metadata.
- `backend/onyx/db/models.py:6740-6915` stores Craft scheduled tasks and runs;
  the run references `BuildSession` and is not a TON analysis record.
- `backend/onyx/chat/process_message.py` and
  `backend/onyx/chat/llm_loop.py` execute the chat/tool loop.
- `backend/onyx/tools/tool_constructor.py:143-175,211-249,523-534` constructs
  persona tools and injects MemoryTool when the user setting enables it.
- `backend/onyx/deep_research/dr_loop.py:1-4,254-257` documents a native
  search-only supervisor. `backend/onyx/tools/fake_tools/research_agent.py:399-408`
  limits calls to one tool type per turn.

### Files, knowledge and indexing

- `backend/onyx/file_processing/file_types.py:20-100` accepts PDF, DOCX,
  PPTX, EML, EPUB, text, JSON, XML, YAML, CSV, XLSX/XLSM and selected images.
  `.xls` is not present in the extension set and is unvalidated.
- `backend/onyx/file_processing/extract_file_text.py:829-890` returns text,
  images and metadata, with an optional external Unstructured path.
- `backend/onyx/server/documents/connector.py:325-350` expands ZIP members
  with `read()`; archive limits need characterization before TON uploads.
- `backend/onyx/connectors/interfaces.py:45-110` defines connector and raw
  file callback boundaries; `backend/onyx/connectors/models.py:196-247`
  defines normalized documents, metadata, owners, access, hierarchy and file IDs.
- `backend/onyx/connectors/file/connector.py:282-373` converts stored local
  files into normalized documents.
- `backend/onyx/indexing/indexing_pipeline.py:1463-1568` performs chunking,
  optional contextual enrichment, embeddings and vector writes.
- `backend/onyx/indexing/chunking/document_chunker.py:25-128` dispatches text,
  image and tabular sections. `backend/onyx/indexing/embedder.py:32-85` and
  `backend/onyx/indexing/vector_db_insertion.py:31-119` are provider/index
  boundaries.
- `backend/onyx/indexing/adapters/document_indexing_adapter.py:44-96` keeps
  database sessions short around long embedding/indexing work.

### Workers and deployment

- `backend/onyx/background/celery/apps/app_base.py:110-128` falls back to the
  default schema if a task has no tenant ID. TON must fail closed.
- `backend/onyx/background/celery/tasks/scheduled_tasks/tasks.py:88-243`
  claims runs, enqueues after commit, uses expiry, has `acks_late=False`,
  catches executor errors and relies on the sweeper rather than Celery retry.
- `backend/onyx/background/celery/apps/beat.py:80-150` creates tenant-specific
  schedule entries and injects `tenant_id`.
- `backend/supervisord.conf:30-142` defines API-adjacent workers, file
  processing, scheduled tasks, beat, monitoring and integration listeners.
- `deployment/docker_compose/docker-compose.yml:46-127` starts API, database,
  OpenSearch, cache, model server and FileStore services. It contains default
  credential fallbacks at credential-setting lines. Treat those as P0
  hardening risks; never reproduce their values.
- `deployment/README.md:6-26` requires changing the compose template and
  running `ods generate-compose --write`; `cli/README.md:218-220` documents
  `go test ./...`.

### Web, SaaS and privacy surfaces

- `web/src/app/layout.tsx:4-25,137-176` loads GTM, PostHog trackers, custom
  analytics and product gating.
- `web/src/app/providers.tsx:1-40` initializes PostHog and leaves input
  masking disabled unless individual fields opt out.
- `web/src/providers/ProductGatingWrapper.tsx:7-25` gates by application status.
- `web/src/lib/constants.ts:18-67` contains auth, EE, analytics, GTM and cloud
  flags.
- `web/src/lib/billing/svc.ts:1-70` chooses Cloud tenant billing or
  self-hosted admin billing and includes license actions.
- `web/src/app/admin/billing/page.tsx:1-32` is billing/license UI;
  `web/src/components/errorPages/AccessRestrictedPage.tsx:20-68` handles seat,
  subscription and license restrictions.
- `web/src/lib/settings/hooks.ts:21-49` merges CE/EE settings and product
  defaults. `web/src/sections/sidebar/AccountPopover.tsx:1-130` owns account
  and settings navigation.
- `backend/onyx/utils/telemetry.py:97-157` sends arbitrary telemetry data when
  enabled. `backend/ee/onyx/utils/telemetry.py:29-63` sends PostHog events and
  client-IP enrichment. `backend/onyx/tracing/framework/create.py:185-244`
  permits complete generation inputs, outputs, reasoning and tool schemas.
- `web/src/lib/chat/hooks.ts:146-147` listens for window messages; any TON
  iframe or extension path must validate origin and source before acting.

### Web-only shared-contract matrix

| Surface | API/contract | Queue/task | DB/cache/storage/search | Deployment/env decision |
|---|---|---|---|---|
| Web chat | `/chat/*`, `SendMessageRequest`, `MessageOrigin` | primary/chat and stream buffer | ChatSession/Message/ToolCall, Redis, PostgreSQL | Preserve. |
| Web auth | `/auth/*`, `/me`, auth cookie | none | User, PAT, Redis session | Preserve. |
| Web agents | `/persona`, `/agents`, `/tools`, `/mcp` | LLM/tool executor | Persona, Tool, MCPServer, DocumentSet | Preserve and harden ACL. |
| Web projects/files | `/user/projects*`, `/user/projects/file/upload` | user-file processing/indexing | UserProject/UserFile/FileStore/OpenSearch | Preserve; add TON lifecycle. |
| Web knowledge | `/search*`, `/document-set*`, hierarchy | docfetching/docprocessing | Document/Hierarchy/DocumentSet/OpenSearch | Preserve. |
| Mobile | `/auth/mobile/*`, shared `/chat/*` | same shared queues | same shared DB/cache | D for UX, G for contracts until deprecation. |
| Desktop | Tauri wrapper around web | same shared queues | same web resources | D; no unique backend API found. |
| Widget | `MessageOrigin.WIDGET`, usage branch | shared chat | shared chat | D for UX, G for enum/branch until deprecation. |
| Extension | `origin=chrome_extension`, `additional_context` | shared chat | shared chat | D for UX, G for shared payload. |
| SaaS billing | `/api/tenants/*`, `/api/admin/billing/*`, `/api/license/*` | billing/license tasks | EE tenant/license tables | E; hide or replace in TON. |
| Analytics | PostHog/GTM/custom analytics | background telemetry | provider-side | E; TON default off. |

## Classification A-G

- **A — directly reusable**: FastAPI, web auth, permissions, chat/session/
  streaming, Persona/Tool, connector/indexing pipeline, FileStore, PostgreSQL,
  Redis, OpenSearch and Celery primitives.
- **B — reusable with configuration/branding changes**: default personas,
  app settings, labels, favicon, navigation, feature flags and deployment
  defaults.
- **C — reusable with domain extension**: Persona as specialist agent,
  DocumentSet as knowledge boundary, nested ToolCall as execution trace,
  scheduled worker primitives, audit emitter and file lifecycle.
- **D — unnecessary for TON V1 experience**: mobile, desktop, widget,
  extension, Slack/Discord, voice, image generation, code interpreter and
  Craft UI unless a later approved adapter needs them.
- **E — coupled to Onyx SaaS/product concepts**: billing, trial, seats,
  licensing, Stripe, PostHog, GTM, custom analytics, upsell and cloud tenant
  acquisition.
- **F — enterprise-only**: EE tier gates, SCIM, enterprise settings, tenant
  control-plane and some group/analytics APIs. Preserve shared RBAC primitives.
- **G — dangerous to remove**: web contracts, shared chat/file/search routes,
  auth and permissions, tenant-aware task context, active OpenSearch path,
  storage, migrations and worker queues. Trace consumers before removal.

## Unvalidated areas

This map did not read every connector implementation, every migration, every EE
module, every frontend consumer, or run live services. It did not validate
NG/Keevo access, schema, quotas or source record identifiers. It also did not
prove that Vespa has no remaining consumer. Treat these as discovery gates.

## Implementation strategy

Keep this artifact as the baseline. Before each implementation slice, rerun
the absence and consumer searches in the roadmap. Update only with direct
path:line evidence and a short decision reference.

## Tests

This artifact has no source tests. Verify it with:

```text
git rev-parse --short HEAD
git status --short
rg -n "MessageOrigin|additional_context|/chat/|/user/projects|/auth/mobile" web mobile desktop backend
rg -n "class (Finding|Occurrence|Rule|RuleVersion|AnalysisRun)|__tablename__.*(finding|occurrence|rule|analysis|report)" backend/onyx/db/models.py backend/alembic/versions backend/alembic_tenants/versions
rg --files -g 'Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt' -g '*Relatorio*Inconsistencias*Jan*Abr*2026*'
```

Expected results: the SHA is the execution baseline recorded above. Shared
web/mobile contracts are found. No TON domain classes are found. The Vale Norte
report search returns the file under `plans/ton/`. Report candidates remain
blocked until source validation and owner approval. Do not print secrets.
