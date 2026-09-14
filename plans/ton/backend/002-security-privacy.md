# Plan 002: Close TON tenant, upload, error and privacy boundaries

> **Executor instructions**: Read `gap-analysis.md` findings SECURITY-01 through
> SECURITY-07 and PRIVACY-01/02. Implement this slice only after Plan 001 is
> DONE. Use `OnyxError`, short database sessions, typed models and existing
> permission patterns. Never log or print secret values.
>
> **Drift check (run first)**:
> `git status --short; git diff --stat -- backend/onyx web/src; git diff --cached --stat -- backend/onyx web/src`

## Status

- **State**: DONE
- **Priority**: P0
- **Effort**: M
- **Risk**: HIGH
- **Depends on**: `001-baseline-contracts.md`
- **Category**: security
- **Planned at**: commit `a0370f232b`, 2026-09-13

## Issues to Address

Sensitive TON analysis needs strict tenant context, bounded uploads, sanitized
client errors, redacted traces and local-by-default telemetry. Current code has
several fail-open or content-bearing paths.

## Important Notes

- `backend/onyx/background/celery/apps/app_base.py:110-128` falls back to the
  default schema when `tenant_id` is missing.
- `backend/onyx/server/query_and_chat/chat_backend.py:937-940` sends raw exception
  text in SSE.
- `backend/onyx/server/documents/connector.py:325-350` reads ZIP members fully.
- `backend/onyx/server/features/projects/projects_file_utils.py:38-68` skips a
  size check when stream size is unknown.
- `backend/onyx/tools/tool_runner.py:138-218` and
  `backend/onyx/tracing/framework/create.py:185-244` permit content-bearing spans.
- `backend/onyx/utils/telemetry.py:97-157`,
  `backend/ee/onyx/utils/telemetry.py:29-63`,
  `web/src/app/layout.tsx:137-176` and `web/src/app/providers.tsx:11-22`
  create backend/browser analytics paths.
- `web/src/proxy.ts:138-145`, `web/src/sections/sidebar/AccountPopover.tsx:56-67`
  and `web/src/lib/chat/hooks.ts:146-147` carry URL or message boundaries.

## Implementation strategy

First create the named unit, integration and web specs. Then make each boundary
fail closed while preserving standard Onyx error and permission contracts.
Expose only metadata in TON telemetry by default. Keep generic Onyx behavior
unchanged when TON mode is disabled unless the security fix is global and
backwards-compatible.

## Scope

In scope:

- `backend/onyx/background/celery/apps/app_base.py`;
- `backend/onyx/server/query_and_chat/chat_backend.py`;
- `backend/onyx/server/documents/connector.py`;
- `backend/onyx/server/features/projects/projects_file_utils.py`;
- `backend/onyx/tools/tool_runner.py`;
- `backend/onyx/tracing/framework/create.py`;
- `backend/onyx/utils/telemetry.py`;
- `backend/ee/onyx/utils/telemetry.py`;
- `web/src/app/layout.tsx`, `web/src/app/providers.tsx`,
  `web/src/lib/chat/hooks.ts`, `web/src/proxy.ts`;
- `backend/tests/unit/ton/test_security_boundaries.py` (create);
- `backend/tests/integration/ton/test_security_boundaries.py` (create);
- `web/src/ton/ton-privacy.test.tsx` (create).

Out of scope:

- Domain migrations, Findings, reports and agent routing.
- Deployment template or generated artifacts; those belong to Plan 007.
- Client surface removal.
- Credential rotation execution. Rotation is required operationally, but values
  must remain outside the repository and this plan.

## Commands you will need

Create the named specs first, then run:

```text
uv run pytest backend/tests/unit/ton/test_security_boundaries.py -xv
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_security_boundaries.py -xv
cd web; bun run test -- src/ton/ton-privacy.test.tsx --runInBand
cd web; bun run types:check
```

Expected results: all named tests pass, web types pass, and tests prove tenant
absence/mismatch denial, bounded ZIP expansion, unknown-size limits, sanitized
SSE, redacted spans, disabled external telemetry, URL allowlisting and message
origin/source validation.

## Tests

Cover both TON mode and the default mode where applicable. Mock outbound
requests and assert that payloads contain metadata only. Test missing tenant,
malformed archive, oversized archive, unknown stream size, provider exception,
LLM input, tool argument, query redirect, iframe origin and extension message.

## Done criteria

- [x] TON tasks reject missing or mismatched tenant context.
- [x] ZIP entry, expanded-byte and member limits are enforced.
- [x] Unknown-size uploads are counted during streaming.
- [x] SSE exposes stable error information only.
- [x] Tool/model traces are metadata-only by default.
- [x] Backend telemetry and browser PostHog/GTM/custom analytics are off by default in TON.
- [x] Query redirects and window messages use allowlists and source/origin checks.
- [x] Named tests and typecheck pass.

## Execution evidence

- Tenant-aware tasks require a non-empty tenant in TON. Published headers bind
  the tenant to worker execution. Cleanup does not use the default tenant.
- ZIP handling validates entry count, paths, depth, member size, total expanded
  size and compression ratio. Member reads also enforce byte limits.
- Unknown-size uploads use bounded spooled storage and remain readable.
- SSE uses a stable public error code and includes the request ID. Internal
  logs keep the exception detail.
- TON traces default to metadata-only. Model content, tool arguments, error
  detail, request parameters and private model configuration are removed.
- TON external telemetry defaults to off. The optional backend metadata mode
  uses field allowlists. Browser analytics do not initialize in TON.
- Login return paths remove query and fragment data. Extension messages require
  the parent source, an extension origin, the app origin and allowed fields.
- The named backend unit suite passed 26 tests. The named integration suite
  passed 2 tests. The named web suite passed 4 tests. Web type checks passed.

## Boundaries and remaining risks

- SECURITY-06 stays deferred. Agent memory policy and routing are outside this
  plan and belong to Plan 005.
- SECURITY-07 stays deferred. Deployment credentials belong to Plan 007.
- No domain model or migration changed. The local service database reports an
  unknown Alembic revision, `6e8f0a2b1c35`. Integration tests used a disposable
  PostgreSQL database migrated to the repository head.
- `uv` was not available in this environment. Checks used the repository
  `.venv` executables. Pytest could not write its cache due to local permissions.
- Pre-commit could not initialize `ripsecrets` because the Windows MSVC linker
  was not installed. Focused Ruff, ty, oxfmt, test and type checks passed.

## STOP conditions

- Stop if fixing a boundary requires changing a shared response shape without a client review.
- Stop if a test needs a real secret or unrestricted outbound payload.
- Stop if tenant fallback remains for a sensitive TON task.
- Stop if any trace, analytics or error path still exports raw content without an approved exception.
- Stop if ZIP limits cannot be enforced before bytes are accumulated.
