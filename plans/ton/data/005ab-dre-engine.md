# DATA-005A/B: Versioned DRE engine

## Issues to Address

DATA-004C/D supplies canonical facts and readiness. A DRE needs approved account classification, a stable line structure, deterministic calculations, and immutable results. Current real data has no ready period. This slice keeps its blockers visible.

## Important Notes

The engine reads `DreInputDataset` through the DATA-004 scoped fact and readiness services. It never reads parsed source rows for calculation. Each input period contains canonical actual and budget facts. DATA-004 readiness also checks review, billing, reconciliation, authority, amount basis, and budget allocation.

The primary PBIX report layout references `dEstruturaDRE.contaGerencial`, `dPlanoConta` levels, `dCalendario` fields, `auxMeta`, and `Medidas` for Realizado, Meta, their YTD values, and Meta versus Realizado percentages. Its `DataModel` did not expose reliable DAX formulas through ZIP/layout inspection. The report layout does not prove AV or AH denominators or comparison periods. The XLSM contains `NATUREZA`, `AUXILIAR`, and `IMPOSTOS` tables. `NATUREZA` has structured account code and managerial nature columns. It does not prove an approved account-to-DRE-line assignment. No VBA ran. No mapping row was imported into production configuration.

## Implementation strategy

`DreStructure` has a stable key and label. `DreStructureVersion` stores the complete ordered line definition. A new version replaces the complete definition and assignment set. Old versions remain immutable. A line has a code, label, position, optional parent, type, operation, and operand codes. `SOURCE_SUM` lines receive account facts. `SUM_CHILDREN`, `SUM_LINES`, `SUBTRACT`, and `RATIO` are typed operations. Structure validation rejects duplicate codes or positions, missing parents or operands, cycles, and invalid operation arity. Formula strings, SQL expressions, and `eval()` are absent.

`DreAccountMapping` attaches one canonical account to a source line in one structure version. `PENDING_APPROVAL` blocks official calculation. Only `APPROVED` assignments contribute values. A new assignment or approval creates a new structure version. No free-text or fuzzy classification occurs. Legacy mappings need a person to verify DRE line semantics before approval. No transitional importer is enabled because the XLSM table alone does not establish that approval.

The DRE readiness endpoint checks all months from January through the requested month. It includes DATA-004 blockers and explicit DRE mapping blockers. Run-wide DATA-004 blockers count once; scoped fact blockers sum across the checked periods. An unresolved unit in a unit-scoped request remains a blocker, because an unmapped fact cannot be assigned safely to that unit. The DATA-004 legacy `dre_classification` flag is superseded by the approved DRE account mapping; its other blockers remain in force. A blocked calculation creates a `NOT_READY` run with blockers and no result lines. There is no preview mode.

Realizado sums only DATA-004 `AUTHORITATIVE_ACTUAL` facts. DATA-004 chooses `MOVEMENT` or `FINAL` only from the canonical account's approved basis. Missing basis or amount blocks calculation. Billing and derived billing facts remain diagnostic under authority policy `ng-actual-billing-diagnostic-1`; the DRE never adds them to Realizado. Orçado sums canonical budget facts for explicit calendar periods. It does not divide an annual amount by 12. The normalization revision pins budget executions and financial mapping revisions.

The pure engine uses `Decimal` with 100-digit calculation precision. Final persisted values use 25 decimal places and half-even rounding in `NUMERIC(50,25)` columns. Absolute variance is Realizado minus Orçado. Percentage variance divides this difference by Orçado and multiplies by 100. A zero Orçado gives `null`, meaning not applicable. A configured `RATIO` also multiplies by 100; a zero denominator blocks the official calculation. The output API does not impose a display rounding scale. YTD sums January through the requested month in the same year, unit scope, normalization run, and DRE version. It does not cross years. AV and AH are deferred pending verified reference semantics. Forecast is deferred.

`DreCalculationRun` pins the requested scope, normalization ID and digest, reviewed dataset revision and time, ReviewRun, source snapshots, billing and budget executions, financial mapping revision, DRE structure version, authority and derivation policy versions, and engine version. A digest over scope and engine version makes repeated calculation idempotent. A new normalization or DRE version creates a new result. `DreResultLine` rows persist the line code, label, monthly values, variance, percentage, and YTD values. Database triggers reject update and delete on the structure, versions, mappings, runs, and result lines. Tenant schema isolation follows existing sessions. Source ACLs guard input and result reads. A consolidated calculation requires a TON administrator. Unit calculations also require unit visibility. Structure changes require the existing admin permission; calculation requires the existing source import capability.

The API provides structure creation/listing, version creation/readback, readiness, calculation, run readback, and paged result lines. It adds no dashboard. Audit events contain IDs for structure version creation and calculation start, blocked, success, or failed request. They contain no financial payload.

YTD percentage lines divide cumulative numerator totals by cumulative denominator totals. The engine does not add monthly percentages.

## Real readiness and legacy validation

A disposable PostgreSQL database replayed migrations, the original NG snapshot, ReviewRun, billing, and three budgets. Exact XLSM account and entity identities were applied only in that database. One workbook account row with an explicit revenue label and the billing gross source account received the DATA-004 revenue diagnostic classification. No DRE line assignment or amount basis was approved. The final normalization reproduced the prior smoke counts:

| Measure | Count |
| --- | ---: |
| NG parsed | 6,306 |
| Downstream-safe actuals | 6,287 |
| Review required / excluded source rows | 19 / 4 |
| Actual accounts mapped / units mapped | 5,717 / 0 |
| Billing facts / mapped accounts / mapped entities | 1,258 / 1,258 / 21 |
| Billing-derived facts | 0 |
| Budget facts / unresolved calendar periods | 45 / 45 |
| Reconciliation items, all unresolved | 1,909 |

The real DRE readiness smoke used a structure version with no approved account assignments. Each available month from January to June returned `NOT_READY`; `READY` was 0 of 6. The June YTD scope reported 6,287 unmapped actual units, 570 unmapped canonical actual accounts, 5,717 accounts without an approved DRE line, 6,287 unresolved amount bases, 45 unresolved budget periods, 19 review-required records, 4 excluded source rows, 931 unresolved billing competences, 1,258 unsupported derivations, and 1,909 unresolved reconciliation items. Each run-wide blocker counts once across YTD. A June calculation persisted `NOT_READY` and zero result lines. Readiness took 0.4 to 2.4 seconds per month scope; larger scopes include more fact pages.

No real period became ready. The real Power BI/Excel amount comparison is `BLOCKED_BY_CURRENT_MAPPING_READINESS`. No account or unit mapping was inferred to force a result. The legacy report supplies semantic field evidence, but no verified DAX formula for AV, AH, or a real line-by-line comparison.

## Tests

Synthetic tests cover hierarchy, formula dependencies, cycles, monthly and YTD values, variance, zero denominators, Decimal precision, DRE mapping approval, a blocked scope, a ready scope, result provenance, idempotency, immutable result lines, audit payload safety, and source ACLs. DATA-004 tests cover review policy, amount basis, budget allocation, billing derivation, reconciliation, and normalized fact lineage. A disposable PostgreSQL migration test runs upgrade, downgrade, and re-upgrade. Broader TON regression and quality checks run separately. No client artifact or value enters tests or this document.

The complete synthetic ready calculation took 83 ms on the local disposable PostgreSQL test. This time measures DRE execution after source capture, review, normalization, and structure setup.

## Remaining business configuration

Finance must approve exact unit mappings, account amount bases, account-to-DRE assignments, budget calendar allocation, and revenue authority and reconciliation. These steps can create a first real ready DRE without changing the engine. Dashboard and report integration can then consume the versioned result API.
