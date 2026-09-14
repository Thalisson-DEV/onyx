# Plan 001: Establish the TON evidence and contract baseline

> **Executor instructions**: Read `architecture-map.md`, `gap-analysis.md` and
> `decision-log.md` first. This slice creates the evidence baseline and named
> test specifications. It must not delete a route or alter runtime behavior.
>
> **Drift check (run first)**: run the commands in “Commands you will need”.
> Compare staged and unstaged changes with the cited baseline before proceeding.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: tests
- **Planned at**: commit `a0370f232b`, 2026-09-13
- **Execution state**: DONE
- **Execution baseline**: commit `6e4b2a066459e3bd7217341b6f2fa5af4eb4bc4f`, 2026-09-14

## Issues to Address

The executor needs a reproducible inventory of web routes, shared mobile/
desktop/widget/extension contracts, missing TON domain records and the newly
available Vale Norte report. Without this baseline, a web-only cleanup can
remove an API still used by the web or another deployed client, or promote
report candidates without source provenance.

## Important Notes

- `backend/onyx/server/query_and_chat/models.py:103-168` warns that
  `SendMessageRequest` is a backwards-compatible core contract.
- `web/src/app/app/services/lib.tsx:147-187` duplicates `MessageOrigin` and
  `additionalContext`; it must stay synchronized with the backend.
- Mobile uses shared chat APIs in `mobile/src/api/chat/sessions.ts:15-90` and
  `mobile/src/api/chat/stream.ts:129-155`.
- `plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt` is the declared
  Jan-Apr 2026 domain evidence. Record its provenance and candidate sections;
  do not treat it as a validated source schema or production rule catalog.
- The underlying workbook, DRE, contracts, bank extracts and NG/Keevo contract
  are not in this checkout. Keep those source and integration gates explicit.

## Implementation strategy

Create a named contract test specification before running it. Capture route and
consumer inventories as test assertions or a plan note. Add no feature flag or
removal in this slice. Treat environment files and credentials as opaque.

## Scope

In scope:

- `backend/tests/unit/ton/test_contract_matrix.py` (create);
- `backend/tests/integration/ton/test_contract_inventory.py` (create);
- `web/src/lib/ton/ton-web-only.contract.test.tsx` (create). The canonical
  `web/src/ton` path was outside the repository Jest discovery pattern;
- `plans/ton/architecture-map.md`, `gap-analysis.md`, `decision-log.md` if
  direct evidence has changed.

Out of scope:

- Runtime source changes under `backend/onyx`, `backend/ee`, `web/src`, mobile,
  desktop, widget, extensions or deployment.
- Deleting or deprecating any route.
- Reading or printing `.env`, credentials, tokens or secret values.
- Generated deployment artifacts.

## Commands you will need

```text
git rev-parse --short HEAD
git status --short
git diff --stat -- backend web mobile desktop deployment package.json pyproject.toml
git diff --cached --stat -- backend web mobile desktop deployment package.json pyproject.toml
rg -n "MessageOrigin|additional_context|/chat/|/user/projects|/auth/mobile" web mobile desktop backend
rg -n "class (Finding|Occurrence|Rule|RuleVersion|AnalysisRun)|__tablename__.*(finding|occurrence|rule|analysis|report)" backend/onyx/db/models.py backend/alembic/versions backend/alembic_tenants/versions
rg --files --hidden --no-ignore -g 'Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt' -g '*Relatorio*Inconsistencias*Jan*Abr*2026*'
```

Expected results: the discovery SHA is `a0370f232b`. The execution SHA is
recorded above. Shared contracts are found. No TON domain classes are found.
The report search returns the file under `plans/ton/`. Do not output secrets.

After creating the specs, run:

```text
uv run pytest backend/tests/unit/ton/test_contract_matrix.py -xv
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_contract_inventory.py -xv
cd web; bun run test -- src/lib/ton/ton-web-only.contract.test.tsx --runInBand
```

Expected result: the three named specifications pass and assert the intended
contract inventory. If the test runner cannot discover a new test directory,
stop and use the repository's existing test discovery pattern.

## Tests

The three named specs must cover web auth, chat, stream resume, projects/files,
  persona/agents, search/document sets, mobile bearer routes, desktop wrapper,
  widget enum, extension context, report provenance, and the absent Finding/Rule
  search.

## Done criteria

- [x] The SHA, staged diff and unstaged diff are recorded.
- [x] Every shared API consumer is classified preserve, deprecate or remove-later.
- [x] The Vale Norte report is recorded with provenance, candidate-only status
      and missing underlying source artifacts.
- [x] Absence of TON domain models is reproducible by command.
- [x] All three named test specifications exist and pass.
- [x] No runtime or generated deployment file changed.

## Execution evidence

The discovery SHA is an ancestor of the execution baseline. Changes between
them affect Zoom and generated deployment files. They do not affect the TON
contract inventory.

The initial tracked worktree was clean. Eighteen untracked frontend planning
documents already existed under `docs/ton/frontend/`. Ignored stale Jest and
Python cache files mention earlier TON experiments. No related application
source exists, so these caches do not change runtime behavior.

No staged or unstaged tracked changes existed in `backend`, `web`, `mobile`,
`desktop`, or `deployment`. This execution added only planning documents and
the three named test specifications.

| Consumer or artifact | Classification | Evidence |
|---|---|---|
| Web auth, chat, resume, projects, files, personas, search, and document sets | preserve | Existing backend and web contracts remain present. |
| Mobile bearer auth and chat | deprecate only after a separate consumer gate | Shared auth and chat contracts remain active. |
| Desktop wrapper | deprecate UX only | It wraps the web and has no unique backend API. |
| Widget origin and chat | remove-later after deprecation evidence | It uses the shared chat contract. |
| Extension context | remove-later after deprecation evidence | It shares message context with web chat. |
| Vale Norte report | preserve as candidate evidence | The report exists under `plans/ton/`; source artifacts remain unavailable. |

The source search found no `Finding`, `Occurrence`, `Rule`, `RuleVersion`, or
`AnalysisRun` class. Existing generic usage and capability reports are not TON
domain models. All domain questions in `decision-log.md` remain unresolved.

Final test results:

- Unit contract matrix: 3 passed.
- Frontend contract specification: 3 passed.
- Integration inventory: 2 passed.

The integration runner initially could not connect from the Windows host.
Docker reports the live Onyx database as healthy, but it has no published host
port.

A temporary fork-capable TCP bridge reached the database. Alembic then reported
revision `6e8f0a2b1c35`, which does not exist in this checkout. This proves that
the live integration database belongs to a different migration baseline. The
temporary bridge was removed. The database was not reset or restamped.

The final run used fresh disposable PostgreSQL and Redis containers. It used
the supported PostgreSQL file store and vector-free test mode. A random
process-local auth secret was neither printed nor stored. The repository
migrations completed, both tests passed, and both containers were removed.

The test body was not bypassed with a fixture override. The source baseline is
therefore reproducible without changing the mismatched live database. Later
live tests must not use that database until its owning checkout is identified.

The host has no `uv` command and `.vscode/.env` is absent. The successful
secret-free tests used `.venv/Scripts/python.exe`. No secret was needed or
printed.

## STOP conditions

- Stop if the baseline SHA or cited contracts differ and cannot be reconciled.
- Stop if a test requires a secret value to be printed.
- Stop if an out-of-scope source file is needed to make the inventory pass.
- Stop if a client consumer is found that changes the web-only removal decision.
