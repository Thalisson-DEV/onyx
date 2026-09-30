# DATA-006C/D: DRE product

## Scope and architecture

The `/admin/dre` workspace reads the current financial readiness overview before it shows a DRE result. It uses the selected normalization, latest DRE structure version, unit, and period. Administrators can select consolidated scope. Other users select an authorized unit. The workspace uses SWR for cached reads. It loads one stored statement and one monthly series. It loads source facts only when a user opens a source line.

The DRE calculation engine remains in DATA-005. This slice adds no financial rules. New read APIs list result revisions, return a stored statement with its structure, return a monthly series of stored results, and page through contributors. The CSV route reads stored result lines. An audit migration widens `ton_audit_event.resource_kind` from 15 to 64 characters because DRE resource names exceed the old limit.

## NOT_READY and READY

For NOT_READY, the page shows the period, scope, status, blocker count, blocker types, and affected record counts. It links to Financial Readiness with normalization, unit, period, and first blocker in the URL. The readiness workspace reads these filters. The page hides old result values and the official export while the current scope is blocked. An explicit recalculation can also return blockers. It never approves configuration.

For READY, the page shows the latest stored calculation for the selected normalization and structure version. A result needs an explicit calculation request; readiness alone does not create one. The page shows loading, empty, failed calculation, access denied, and network error states. It marks previous revisions as historical.

## Statement and period analysis

The statement uses the pinned DRE structure version and stored result lines. The structure defines row labels, hierarchy, order, and line types. Users can expand and collapse parents. Subtotals and results use border and type weight. The table scrolls on narrow screens.

The summary uses the final result line, or the final subtotal or source sum when no result line exists. It displays stored Realizado, Orçado, variance, variance percent, and YTD values. The client formats amounts and percentages for the active locale. A null percent remains unavailable, never zero. Negative amounts use normal financial sign formatting.

The monthly chart shows Realizado and Orçado for months that have stored READY results for the same normalization, structure version, year, unit, and line code. Missing months have no invented values. The chart reads no source facts and calculates no financial totals.

## Drill down and provenance

Users open a `SOURCE_SUM` line to inspect its stored totals and paged Actual or Budget contributors. The API limits each page to 100 facts; the UI requests 25. The facts include account, unit, date or competence, amount, amount basis, source type, review status, source file, sheet, and row where available. Billing-derived origin remains explicit. Source lineage follows the canonical fact to its source snapshot. Tenant and source ACL checks run on the backend. The UI does not expose raw internal JSON.

## Revisions, recalculation, export, and audit

The revision control lists stored READY results for the period and unit. Opening a historical revision does not recalculate it. Version details show calculation time, structure version, normalization revision, dataset revision, and budget executions. Long technical identifiers stay in the detail section.

Recalculation is an explicit action for users with import permission. It calls the DATA-005 calculation API and refreshes cached results. The backend keeps its calculation audit. Result reads require source read permission. Calculation requires import permission. Configuration requires administrator permission in the existing workspace.

CSV export requires source read permission and a stored READY run. The export contains period, scope, status, revision ID and time, structure and input revisions, budget execution IDs, and all stored monthly and YTD result fields. It uses stored values and does not put spreadsheet formulas in cells. Text cells that start with spreadsheet formula prefixes receive a safe leading apostrophe. The backend writes one export audit event with IDs only. A NOT_READY run cannot export an official result.

## Validation and limits

Synthetic tests cover READY hierarchy, Actual and Budget drill down, pagination, revisions, chart input, blocked export, and stored CSV values. The backend regression set also covers readiness, financial domain, ACL, and audit. The prior real client smoke had six NOT_READY periods and no READY periods. A new live client smoke requires the real source workbooks; they were unavailable in this checkout. No client approvals or business values were added to tests or production data.

A second synthetic fixture imports January and February NG records and billing invoices. It maps one monthly budget schedule to both months. The DRE test verifies two READY results, February YTD totals, two series points, and February source lineage.

CSV is the supported report format in this slice. The chart and summary show one selected statement line. No forecast, AV/AH, AI analysis, or automatic report delivery is included.

The audit migration passed on a fresh PostgreSQL database and the local default database. A new synthetic blocked calculation stored two audit rows. The temporary migration database was removed after the check.

## Local synthetic evaluation

The local default PostgreSQL database initially had no TON sources, imports, reviews, normalizations, structures, or calculations. The text “Não há normalização ou estrutura de DRE disponível” was accurate. The first local demo used a separate database named `onyx_dre_demo`. That changed the active user directory and prevented login with accounts from the default database. The API now points to `postgres` again. The synthetic TON data was seeded there after confirming it had no TON sources. Its four original users remain intact. The separate demo database remains stored but inactive.

The synthetic seed is `backend/tests/dev_harness/ton/seed_dre_demo.py`. It reuses test workbooks and the real import, review, normalization, and DRE engines. It creates one January 2026 READY scope, two READY result revisions, a blocked DRE structure, an Actual fact, and two Budget facts. It creates unit and consolidated results. The dashboard chart has one stored month. The synthetic input files exist only while seeding; the drill down retains file, sheet, and row metadata. The demo is for local evaluation only.

Use an administrator account from the default database at `/admin/dre`. Select “Demonstração sintética: DRE pronta” to inspect the statement, drill down, version details, and CSV. Select “Demonstração sintética: pendências” to inspect the NOT_READY state and its link to Financial Readiness. The API smoke returned READY and NOT_READY, four statement lines, one Actual fact, two Budget facts, two READY revisions, one series point, CSV HTTP 200 for READY, and HTTP 409 for blocked export. No browser or visual check was used after the user's request to skip it.

The separate demo database is disposable. The default database now contains synthetic TON rows as well as the original users. The seed script refuses to add another demo when TON sources already exist. It accepts `postgres` only when `TON_DRE_DEMO_LOCAL_MAIN=1` and the host is local. Start the API without `docker-compose.dre-demo.yml` to keep the original login directory.

## Bringing real data into the application

The DRE page consumes configured data. It does not import workbooks or create a financial structure. The current frontend has no first-use import wizard for TON. Initial setup uses the authenticated API through `http://localhost:3000/api`:

1. Create logical sources with `POST /api/ton/sources`. Use separate sources for NG financial, billing, and budget.
2. Upload each source file with `POST /api/ton/sources/{source_id}/imports`, then create and execute its NG or operational import profile.
3. Review the NG execution with the financial review API. Create canonical accounts and mappings, then call `POST /api/ton/financial-domain/normalizations` with the reviewed NG run, billing execution, and budget executions.
4. Create a DRE structure with `POST /api/ton/dre/structures`. Assign canonical accounts to source lines with approved, reasoned versions.
5. Open `/admin/financial-readiness`. Inspect blockers, approve only verified account, unit, amount basis, DRE line, budget period, and reconciliation decisions. Recompute normalization after changes.
6. Open `/admin/dre`. Choose normalization, structure, unit, and period. For READY, request an explicit DRE calculation. Then inspect the stored result, contributors, revisions, and CSV.

Importing a source does not make a period READY. The application does not infer financial approvals. Real source file locations are needed to run this flow for Vale Norte again.
