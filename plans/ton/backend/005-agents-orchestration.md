# Plan 005: Authorized agents and orchestration

Status: proposed. Priority: P1. Size: large. Risk: high.

Dependencies: Plans 001, 002, 003, and 004. This plan does not depend on an
external NG or Keevo contract.

## Issues to Address

TON needs a web-facing analysis flow with six named specialist capabilities:

- TON Central/CEO
- CFO
- Frota
- Contratos
- Auditoria
- RH

The current repository has useful agent-like building blocks, but no TON
specialist policy or durable supervisor contract. `backend/onyx/tools/tool_constructor.py:143-175`
and `:211-249` construct tools from persona and user context. The deep-research
loop is a domain-specific execution loop at
`backend/onyx/deep_research/dr_loop.py:1-4` and `:254-257`. The research agent
tool calls that loop at `backend/onyx/tools/fake_tools/research_agent.py:399-408`.
These paths are evidence of native orchestration primitives. They do not prove
that a persistent supervisor, Finding, or TON role exists.

Implement a TON policy and orchestration boundary that can call only approved
specialists. The boundary must enforce tenant, user, role, source, and tool
permissions before execution. A specialist cannot grant access to another
specialist or widen the source scope.

Each specialist result is durable. It records one of `result`, `timeout`,
`error`, or `insufficient_data`. Partial completion is valid and visible. One
failed specialist must not erase successful specialist results. The final
report must state which specialists did not complete.

## Important Notes

The existing permission helper checks role and capability at
`backend/onyx/auth/permissions.py:320-365`. Reuse its authorization pattern,
but do not assume its current role names are the TON policy. Map each TON
specialist to an explicitly approved permission during implementation.

`backend/onyx/server/query_and_chat/chat_backend.py:771-803` and `:918-940`
show the current query and chat execution boundaries. Chat remains a web API
contract. Mobile and desktop are outside V1 experience scope, but shared API
schemas and authentication contracts remain preserved until their consumers are
verified.

The native research loop is not evidence for a requirement to add LangGraph.
Do not add LangGraph in this slice. First prove a missing state, retry,
checkpoint, or human approval requirement that the current primitives cannot
represent. Record that proof in the decision log before considering a new
orchestration dependency.

The detector and rule executor from Plan 003 never depend on an LLM. This plan
may ask a specialist to interpret approved evidence, but it must pass the
interpretation state machine and durable failure contract from
`plans/ton/domain-rules.md`.

The following files are implementation boundaries, not permission to edit them
in this planning task.

In scope:

- `backend/onyx/ton/agents.py` (new TON specialist policy module)
- `backend/onyx/ton/orchestration.py` (new TON execution boundary)
- `backend/onyx/tools/tool_constructor.py` (shared contract adapter only)
- `backend/onyx/deep_research/dr_loop.py` (shared loop adapter only)
- `backend/onyx/tools/fake_tools/research_agent.py` (shared caller adapter only)
- `backend/onyx/db/models.py` and `backend/onyx/db/ton.py` for approved durable
  specialist and run relations from Plan 003
- `backend/onyx/auth/permissions.py` for explicit TON authorization checks
- `backend/tests/unit/ton/test_agent_policy.py` (new named spec)
- `backend/tests/integration/ton/test_agent_orchestration.py` (new named spec)

Out of scope:

- Mobile, desktop, widget, and browser extension user experiences
- NG or Keevo field mapping and schema design
- Telegram transport
- Connector writes or arbitrary external actions
- LangGraph or another orchestration framework
- Generated deployment artifacts

## Implementation strategy

1. Define a typed specialist registry with stable opaque identifiers. Store the
   display label separately from the authorization identifier. Do not use a
   free-form model-generated role name for access control.
2. Define an execution request containing tenant, actor, chat or analysis run,
   source scope, requested specialist set, and trace metadata. Validate the
   request before creating work.
3. Resolve permissions for all six specialists before starting work. Return a
   durable denial for an unauthorized specialist. Do not silently downgrade a
   request to a different role.
4. Use the existing tool constructor and research loop through a small adapter.
   The adapter passes the approved source scope and excludes tools that can
   write data or contact an unapproved system.
5. Persist specialist start, completion state, result reference, error class,
   timeout, and insufficient-data reason. Never put full secret values or
   unredacted connector credentials in a result or trace.
6. Enforce an internal timeout. A supervisor records a timeout and allows other
   specialists to finish. A late worker can only commit an idempotent terminal
   result for its own execution key.
7. Produce a combined orchestration result only after all requested specialists
   are terminal or the run reaches an explicit partial-report policy. The
   combined result must list missing, failed, or insufficient sources.
8. Add audit events for authorization decisions, specialist start, terminal
   state, and final report creation. Apply the metadata-only telemetry policy
   from Plan 002.
9. Add a narrow web API adapter in Plan 006. Keep the backend orchestration
   contract independent from frontend rendering.

### Required specialist access policy

| Specialist | Initial allowed purpose | Required boundary |
| --- | --- | --- |
| TON Central/CEO | Cross-domain executive summary | Read approved tenant sources; no source mutation |
| CFO | Financial evidence and control analysis | Finance-scoped sources and tools only |
| Frota | Fleet and vehicle evidence | Fleet-scoped sources and tools only |
| Contratos | Contract evidence and obligations | Contract-scoped sources and tools only |
| Auditoria | Evidence trace and control exceptions | Read audit metadata and approved sources; no event deletion |
| RH | Human-resources evidence | HR-scoped sources; no cross-domain data by default |

The policy must support a partial specialist set. It must not use a hidden
superuser bypass for TON Central/CEO.

### Required state and failure behavior

Use the durable states from Plan 003 for findings and the following execution
states for specialist work: `queued`, `running`, `result`, `timeout`, `error`,
`insufficient_data`, and `cancelled`. Terminal states are immutable except for
an approved append-only correction record. Retries use an idempotency key and
never create two active executions for the same requested work.

## Tests

Create the named specs before running them. The specs must cover:

- every six specialist authorization paths and a denied cross-domain path;
- tenant isolation and source-scope enforcement;
- tool allow-list and no arbitrary connector write;
- successful, partial, timeout, error, and insufficient-data outcomes;
- supervisor completion when one specialist fails;
- duplicate delivery and late completion idempotency;
- interpretation-pending and interpretation-failed behavior before a final
  Finding or Report;
- audit event presence and metadata-only trace content;
- web API contract preservation for existing chat and session consumers.

Run from the repository root:

```text
uv run pytest -xv backend/tests/unit/ton/test_agent_policy.py
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_agent_orchestration.py
```

Run the migration checks from the backend directory after schema changes:

```text
cd backend
uv run alembic check
uv run alembic upgrade head
uv run alembic -n schema_private upgrade head
```

Expected result: the two named specs pass, migration heads are current, and
unauthorized or incomplete specialist work cannot produce a final report.

Done criteria:

- The six specialist identifiers and permission rules are typed and documented.
- Direct and partial specialist execution is durable and idempotent.
- Existing chat, session, tool, and authentication contracts remain compatible.
- Interpretation failure blocks final Finding/Report publication.
- The named unit and integration specs pass.
- No new orchestration dependency is added without a recorded decision.

STOP conditions:

- A required source-scope or role contract is not present in the current API.
- A specialist would need an NG/Keevo field or an unapproved external write.
- A result cannot be persisted without exposing secret or personal data.
- Existing mobile or desktop consumers reveal a breaking shared-contract change.
- The current native loop cannot express a required guarantee and no decision
  has approved a replacement.

Maintenance: update the specialist registry, permission table, and named specs
in the same change when a specialist is added, removed, or renamed.
