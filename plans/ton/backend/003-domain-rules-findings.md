# Plan 003: Add the TON rule, interpretation and Finding domain

> **Executor instructions**: Read `003-readiness.md` first, then `domain-rules.md`
> and `decision-log.md` fully. `003-readiness.md` is the readiness gate result and
> is canonical where it is more specific than this plan. It settles the
> append-only report shape and its canonicalisation rules, the logical identity
> contract, domain-scoped blocking, the Finding/Occurrence split, the resource ACL
> model, the audit-history model and the migration order. It also adds two scope
> areas this plan omitted: **resource ACLs** and the **audit-history model**.
> This plan adds no NG/Keevo field mapping and no source-system writes.
>
> **Slicing**: execute as 003a/003b/003c/003d per `003-readiness.md` §21. Do not
> execute this plan as one migration.
>
> **Drift check (run first)**:
> `git status --short; git diff --stat -- backend/onyx/db backend/alembic backend/alembic_tenants; git diff --cached --stat -- backend/onyx/db backend/alembic backend/alembic_tenants`

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: HIGH
- **Depends on**: `001-baseline-contracts.md`, `002-security-privacy.md`, approved decisions in `decision-log.md`
- **Category**: direction
- **Planned at**: commit `a0370f232b`, 2026-09-13

## Issues to Address

Onyx has no first-class Rule, RuleVersion, AnalysisRun, Finding, Occurrence or
immutable domain Report. TON needs deterministic detection, mandatory AI
interpretation and an idempotent lifecycle that survives retries and concurrent
workers.

## Important Notes

- Current report-like models are unrelated: `backend/onyx/db/models.py:2115-2125`
  is a credential capability report; `:5443-5468` is UsageReport metadata plus
  a FileRecord link.
- Current nested execution records are technical: `backend/onyx/db/models.py:3414-3487`
  is ToolCall, not a business Finding.
- Use states `candidate/detected`, `interpretation_pending`,
  `interpreted/final` and `interpretation_failed`.
- The detector never depends on the LLM. AI interpretation is mandatory before
  final Finding or Report output.
- Logical identity stays opaque until approved domain keys exist. Do not invent
  NG/Keevo fields.
- `domain-rules.md` now contains all report-derived candidates from
  `plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt`. Preserve their
  classifications and report/source provenance. The report does not validate
  production thresholds or source columns.
- The report has unresolved arithmetic and policy conflicts, including
  parcelamento and mutual totals, budget coverage, and travel deadlines. Add
  explicit non-final states for these conflicts.

## Implementation strategy

Create named test specs before migrations. Implement typed deterministic rules
and evidence first. Persist `interpretation_pending` before an LLM call. Persist
safe interpretation failure and block finalization. Use append-only transitions,
database uniqueness and idempotency keys. Create a new revision for corrections;
never silently mutate a final report.

## Scope

In scope:

- `backend/onyx/db/models.py` for TON SQLAlchemy entities;
- `backend/onyx/db/ton.py` (create) for TON database operations;
- `backend/onyx/ton/__init__.py` (create);
- `backend/onyx/ton/rules.py` (create) for deterministic detection;
- `backend/onyx/ton/interpretation.py` (create) for mandatory interpretation;
- `backend/onyx/ton/findings.py` (create) for lifecycle and deduplication;
- `backend/onyx/ton/reports.py` (create) for append-only snapshots and hashes;
- `backend/alembic/versions/` new TON migration files only;
- `backend/alembic_tenants/versions/` new tenant migration files only;
- `backend/tests/unit/ton/test_domain_contract.py` (create);
- `backend/tests/integration/ton/test_finding_lifecycle.py` (create);
- `backend/tests/integration/ton/test_report_immutability.py` (create).

Out of scope:

- Existing Onyx table deletion or alteration without approved compatibility work.
- NG/Keevo fields, external source writes, Telegram and web UI.
- Agent routing and Celery schedule wiring; Plan 005/006 own those.

## Commands you will need

Create the named specs before running them. For migrations, run from `backend/`:

```text
uv run pytest backend/tests/unit/ton/test_domain_contract.py -xv
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_finding_lifecycle.py -xv
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_report_immutability.py -xv
cd backend; uv run alembic upgrade head
cd backend; uv run pytest tests/integration/tests/migrations/
```

Expected results: named tests pass; the migration reaches head; and the
migration suite passes, which asserts a single head revision, up/down
consistency and a clean empty-database upgrade on both chains.

Two commands were removed because they cannot pass. Measured evidence in
`003-readiness.md` §17.3.

- `alembic check` is **not** a usable gate. It reports over 470 operations
  against an untouched baseline, because `target_metadata` includes Celery's
  runtime-created tables and `compare_server_default=True` flags every
  Python-side default. Do not reinstate it.
- `alembic -n schema_private upgrade head` **collides** in this single-tenant
  deployment. `alembic_tenants/env.py` sets no `version_table_schema`, so it
  reads the main chain's `alembic_version` and fails with
  `Can't locate revision identified by 'ad99acb9be41'`. TON runs
  `MULTI_TENANT=false` with only the `public` schema. Record the environment
  fact; do not skip the migration review.

## Tests

Test deterministic positive/negative/boundary/missing/malformed inputs,
report-derived arithmetic conflicts and each candidate classification; state
transitions; malformed interpreter output; provider timeout; explicit failure;
concurrent same-key insertion; retry idempotency; post-resolution repeat;
rule-version separation; append-only correction; canonical snapshot hash; and
unauthorized report access.

## Done criteria

- [ ] Schema exists only after decisions are approved.
- [ ] Detector has no LLM dependency.
- [ ] Final Finding/Report requires successful interpretation.
- [ ] Interpretation failure is durable and non-final.
- [ ] Logical identity is opaque and approved before production keys are used.
- [ ] Repetition updates last-seen/occurrence according to an explicit policy.
- [ ] Resolution and post-resolution repeat behavior are explicit.
- [ ] Concurrent retries converge on one logical result.
- [ ] Reports use append-only rows, canonical snapshot and hash.
- [ ] Resource ACLs exist for BusinessUnit, Contract, Occurrence and Report, and
      fail closed when no ACL row exists (`003-readiness.md` §10).
- [ ] The audit-history model persists every lifecycle event
      (`003-readiness.md` §11).
- [ ] Named tests pass and `pytest tests/integration/tests/migrations/` passes.

## STOP conditions

- Stop if domain keys, limits, units, retention or immutable snapshot approval is missing.
- Stop if a rule calculates through an LLM or invents source fields.
- Stop if finalization can bypass interpretation or hide its failure.
- Stop if a retry can duplicate a logical Finding.
- Stop if schema work requires deleting or silently changing an existing Onyx table.
