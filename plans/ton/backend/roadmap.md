# TON implementation roadmap

This roadmap orders the executable slices. It is not a promise of dates. Each
slice has a separate plan with exact scope and STOP conditions.

## Issues to Address

The transformation spans security, data contracts, deterministic rules,
ingestion, agents, reports, workers, administration and web-only product
cleanup. Domain schema and production rules must wait for the decisions in
`decision-log.md`, report-source validation and owner approval.

## Important Notes

- Discovery SHA: `a0370f232b`.
- Execution baseline SHA: `73b8ec4d34c34eb90abc784bcff542117164f515`.
- The discovery SHA is an ancestor of the execution baseline. Later changes
  affect Zoom and generated deployment files, not the inventoried TON contracts.
- Vale Norte report: available at
  `plans/ton/backend/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt`; it is
  incorporated as candidate evidence, not as a production rule catalog.
- TON VALE Prompt Mestre v2.0: `plans/ton/masterprompt.md`. It is the domain
  source. Its thresholds are rule parameters requiring approval, not constants.
- Plan 003 readiness: `003-readiness.md`. Verdict BLOCKED on four named items.
  It resolves Alembic revision `6e8f0a2b1c35` and settles the domain contract.
- Underlying workbook, DRE, contracts, bank extracts, payroll detail and
  NG/Keevo contract remain unavailable in this checkout.
- NG/Keevo: future, read-only and BLOCKED.
- Telegram is the first planned external TON channel. It stays outside TON core.
- WhatsApp is a later channel adapter.
- Existing deployment files are generated. Only Plan 007 may alter their
  template/generated copies and must run the generator plus Go drift tests.
- P0 marks a release/security blocker; dependency order still controls
  execution. Plan 001 is the required read-only baseline.
- All executor plans preserve the four required AGENTS headings and use
  `uv run` from the repository root for tests, or from `backend/` for Alembic.

## Execution order

| Plan | Result | Depends on | Status |
|---|---|---|---|
| 001 | Evidence baseline, web contract inventory and named test specs | none | DONE |
| 002 | Tenant, upload, error, trace and telemetry boundaries | 001 | DONE |
| 003a | Provider secret encryption (SECURITY-08) | 001, 002, 007, `003-readiness.md`, decision 7a | DONE |
| 003b | TON identity, rules and analysis core | 003a, `003-readiness.md`, 008a | DONE |
| 003 | Rule/analysis/Finding/Occurrence/Report contract and migrations | 001, 002, 003a, `003-readiness.md` | READY for 003c/003d. 003a and 003b DONE. |
| 004 | File lifecycle, ingestion, knowledge and quality hooks | 001, 002, 003 | TODO |
| 005 | Specialist agents and native supervisor extension | 002, 003, 004, 008a | TODO |
| 006 | Reports, alerts, administration and scheduled processing | 001, 002, 003, 004, 005, 008a | TODO |
| 007 | Deployment credential hardening and generated artifact sync | 001, 002 | DONE: credentials and artifact sync DONE; provider-secret encryption delivered by 003a |
| 008a | Capability/authorization separated from commercial tier (Groups + permission grants) | 001, 002 | DONE for the P0 Groups slice; branding and other gates deliberately deferred |
| 008b | Web-only product surface and shared-contract gate | 001, 002, 006, 007, 008a | TODO |
| 009 | Telegram channel adapter | 002, 005, 006 | BLOCKED: channel contract unavailable |

Plan 008 is split. `008a-capability-gates.md` owns the backend
entitlement→capability transformation and is done for the P0 Groups/RBAC slice.
`008-web-only-product.md` remains the surface slice (008b) and is still TODO;
it must not be marked complete because of 008a.

Plan 003 passed its readiness gate. `003-readiness.md` holds the result and is
canonical where it is more specific than the plan. It splits Plan 003 into four
slices: 003a (provider-secret encryption), 003b (rules and analysis), 003c
(findings, occurrences and ACL) and 003d (report snapshot and audit).

**003c and 003d are READY.** Alembic revision `6e8f0a2b1c35` is identified as an
orphan merge migration that was never committed, and the repository history is
linear with a single head.

**003a is DONE.** Decision 7a is resolved and recorded in
`003a-provider-secret-encryption.md`, which closes readiness blocker B4 and
SECURITY-08. Both provider `custom_config` columns are now `EncryptedJson`, and
revision `714172b66b07` chains from `ad99acb9be41`.

**003b is DONE.** Recorded in `003b-ton-identity-rules-analysis.md`. Revision
`faee7eaa921e` creates the nine identity, rule and analysis tables and is the new
single head. **003c takes `faee7eaa921e` as its `down_revision`.** Plan 003 as a
whole is not complete: Finding, Occurrence and the resource ACL junctions belong
to 003c, and the report snapshot and TON audit trail to 003d.

The original TON global-blocking defect is closed structurally by 003b:
`AnalysisStep` scopes blocking to `(step_code, domain, business_unit_id)`, a
BLOCKED row must name its cause, and a partially blocked run reports
`COMPLETED_WITH_BLOCKED_DOMAINS` rather than `FAILED`.

The running development database was **not** migrated by 003a or 003b. It stays
at `ad99acb9be41`. The operational upgrade path is recorded in
`003b-ton-identity-rules-analysis.md`.

Business-rule approval does **not** block any migration. Every threshold stays a
`RuleVersion` row, and a CHECK constraint makes an `ACTIVE` version require a
recorded approval. Rule activation stays blocked; schema creation does not.

## Dependency graph

```text
001 baseline/contracts
  -> 002 security/privacy
      -> 003 domain schema/rules
          -> 004 files/knowledge/ingestion
              -> 005 agents/orchestration
                  -> 006 reports/alerts/admin/schedules
001 + 002 -> 007 deployment hardening
001 + 002 -> 008a capability/authorization gates
008a -> 005 agents (specialist group sharing)
008a -> 006 reports/admin (group-scoped report ACLs)
001 + 002 + 006 + 007 + 008a -> 008b web-only product surface
002 + 005 + 006 -> 009 Telegram channel adapter
```

Plan 005 depends on 008a because specialist agents are shared per business unit
through `Persona__UserGroup`, which is administered on the group routes. Plan 006
depends on 008a because group-scoped report and finding ACLs reuse the same group
primitives.

## Implementation strategy

Use one executor per slice. Each executor reads this roadmap and the canonical
artifact named by its plan. Executors must create a named test specification
before running a new test path. Update this status table only after the plan's
done criteria pass.

## Scope

In scope: execution order, dependencies, status and phase exit gates.

Out of scope: dates, source changes, external coordination and credentials.

## Tests

Reproduce roadmap inputs with:

```text
git rev-parse --short HEAD
git status --short
rg -n "Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte" .
rg -n "TON_WEB_ONLY|TON_EXTERNAL_TELEMETRY_MODE|AnalysisSchedule|interpretation_pending" plans/ton
```

Expected result: the execution SHA matches the baseline above. Worktree changes
remain visible. The report search returns the file under `plans/ton/`. All nine
plans are linked. Unresolved report conflicts remain visible in
`domain-rules.md`.

## Done criteria

- [ ] All executable plans exist and are linked from `plans/ton/backend/README.md`.
- [ ] Dependencies prevent schema work before decision approval.
- [ ] Every phase has a named test spec and verification gate.
- [ ] Web-only cleanup is last and contract-gated.
- [ ] NG/Keevo and missing underlying source contracts remain visible blockers.
- [ ] Report-derived candidates remain blocked until source and owner approval.

## STOP conditions

- Stop if a later plan is started before its dependencies are done.
- Stop if a plan hides an unresolved domain or integration question.
- Stop if any plan contains a placeholder command or unbounded scope.
- Stop if generated deployment artifacts are touched outside Plan 007.
