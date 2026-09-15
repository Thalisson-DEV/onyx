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
- Execution baseline SHA: `6e4b2a066459e3bd7217341b6f2fa5af4eb4bc4f`.
- The discovery SHA is an ancestor of the execution baseline. Later changes
  affect Zoom and generated deployment files, not the inventoried TON contracts.
- Vale Norte report: available at
  `plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt`; it is
  incorporated as candidate evidence, not as a production rule catalog.
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
| 003 | Rule/analysis/Finding/Occurrence/Report contract and migrations | 001, 002, decision approval | TODO |
| 004 | File lifecycle, ingestion, knowledge and quality hooks | 001, 002, 003 | TODO |
| 005 | Specialist agents and native supervisor extension | 002, 003, 004 | TODO |
| 006 | Reports, alerts, administration and scheduled processing | 001, 002, 003, 004, 005 | TODO |
| 007 | Deployment credential hardening and generated artifact sync | 001, 002 | PARTIAL: credentials and artifact sync DONE; provider-secret encryption blocked on Plan 003 |
| 008 | Web-only product surface and shared-contract gate | 001, 002, 006, 007 | TODO |
| 009 | Telegram channel adapter | 002, 005, 006 | BLOCKED: channel contract unavailable |

## Dependency graph

```text
001 baseline/contracts
  -> 002 security/privacy
      -> 003 domain schema/rules
          -> 004 files/knowledge/ingestion
              -> 005 agents/orchestration
                  -> 006 reports/alerts/admin/schedules
001 + 002 -> 007 deployment hardening
001 + 002 + 006 + 007 -> 008 web-only product surface
002 + 005 + 006 -> 009 Telegram channel adapter
```

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

- [ ] All nine executable plans exist and are linked from `plans/ton/README.md`.
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
