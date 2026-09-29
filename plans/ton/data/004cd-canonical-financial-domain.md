# DATA-004C/D: Canonical financial domain

## Issues to Address

DATA-003 reviews NG launches. DATA-004A/B parses billing and budget records. These sources use different identities and periods. A DRE consumer needs stable facts, exact mappings, and a clear readiness result.

## Important Notes

The canonical layer does not read source workbooks. It reads stored parsed records and the reviewed NG dataset. The legacy XLSM was inspected without macro execution. Its mappings were imported only into a disposable local smoke database. No client mapping value is in a migration, test, or committed document.

DATA-003 permits `ACCEPTED` and `JUSTIFIED_EXCEPTION` downstream. Other dispositions do not create actual facts. Rejected source rows are never facts. The normalization run pins the dataset revision and its `as_of` time.

## Canonical model

Each fact type has its own table.

| Fact | Source | Period | Value | Role |
| --- | --- | --- | --- | --- |
| Actual | Reviewed NG parsed record | Emission calendar month; source sheet month stays separate | Movement and final amounts stay separate | Authoritative actual source |
| Billing | Accepted billing record | Emission date and explicit competence | Service, retained, and net amounts present in the source | Invoice evidence |
| Derived | Billing fact and a versioned rule | Explicit competence only | Gross service or supported negative retention | Supplementary, never added to NG actuals by default |
| Budget | Accepted budget record | Monthly contract basis; calendar month only with an explicit map | Source detail amount | Independent budget version |

`ton_business_unit` supplies stable unit identity within each tenant schema. `ton_financial_account` supplies stable account identity. A mapping links a source code or label to one of these identities. It does not replace the source code, source label, or source Natureza Gerencial. Account classification is separate from both the source label and the account identity. An account with no DRE classification blocks readiness. An administrator can set the actual amount basis to `MOVEMENT` or `FINAL` when creating an account. A null basis keeps its actual amount unresolved. A changed basis needs a new account identity and mapping revision.

The billing fact stores the invoice number, payer text, emission date, competence, service amount, and available retained and net amounts. Missing optional fields stay null. The budget fact keeps its source record, amount, and period basis. It is never a field on an actual transaction.

## Period model

NG emission date defines `calendar_period` for an actual fact. The original sheet month remains available as `source_sheet_month`. No NG service competence is inferred. Billing emission and competence remain separate. A billing record without explicit competence cannot create a derived fact. Every source budget record has `MONTHLY_CONTRACT` basis. It has no calendar period until a `BUDGET_PERIOD` mapping names one exact execution and month. No annual total is divided by 12.

## Mapping model and versioning

Mapping keys are exact. The kinds are NG account and unit, billing gross account and entity, billing retention account, budget account and unit, and budget period. Mapping rows have a source, optional source snapshot, effective dates, and a revision number. Each change adds a row and a new revision. The latest applicable row at or before the pinned revision wins. Facts store the mapping row IDs and canonical target IDs. Old fact revisions stay unchanged. No fuzzy text, supplier, history, or LLM mapping runs.

The local smoke imported exact legacy account codes from the XLSM `NATUREZA` table. It also inspected the `AUXILIAR` unit table. NG unit labels and its structured code prefixes did not match a unique legacy unit key. The importer left them unmapped. The importer used no legacy workbook at normalization time. The XLSM is not a production configuration source.

## Billing VBA reconstruction

Static inspection found the `FINANCEIRONG` procedure in the legacy XLSM. It reads the `IMPOSTOS` table on the billing sheet. Columns 1 through 4 hold a number, unit, competence, and gross value. It writes a positive gross row at competence. It scans later named columns. Numeric values below one are treated as rates against gross. It writes nonzero tax or fee rows with negative values. It writes the net gross row as gross less identified taxes. It looks up a document and history from an NG row by a literal account code and unit. The lookup is a first match, so it does not prove invoice identity. The procedure uses hard-coded account literals; TON stores the resulting account choices as versioned mappings.

TON rule `BILLING_GROSS` version 1 copies the parsed service value only with explicit competence, account mapping, and unit mapping. Rules `BILLING_RETAINED_ISS` and `BILLING_RETAINED_INSS` version 1 write negative source retained amounts under explicit account mappings. A zero amount creates no row. A negative retained amount is unresolved. The parsed `IR Retido` label does not prove the VBA `IRPJ Retido` meaning. IR derivation is unresolved. The raw billing file does not prove the PIS, COFINS, fee, or contingency values used by the VBA table. TON does not derive those rows or run a tax engine. The PIS/COFINS PDF is not a source.

Each derived fact has `BILLING_DERIVED` origin, a rule key and version, a billing fact ID, and source record lineage. The run pins `billing-vba-proven-1`. A rule change needs a new version and a new run.

## Source authority and reconciliation

Policy `ng-actual-billing-diagnostic-1` treats reviewed NG facts as the only additive actual source. Billing and derived rows are separate evidence. A consumer must not add derived gross to NG revenue. An unmatched billing row blocks revenue readiness. This policy is provisional until Finance confirms authority for each revenue area.

Revenue reconciliation uses an exact calendar period, unit ID, account ID, and document or invoice number. One NG row and one billing row with equal movement and service values give `MATCHED`. Both sides with differing amounts or multiple rows give `AMBIGUOUS`. A single side gives `NG_ONLY` or `BILLING_ONLY`. Missing mapping or competence gives `UNMAPPED`. No history text guess is used. A 1:N or N:1 group remains ambiguous. A reconciliation item stores fact links and a hash of its structured key. The API returns summary counts and paged items. Each item is a projection of one normalization run. No mismatch creates a DATA-003 Finding.

## Actual and budget alignment

Alignment needs the same calendar period, canonical unit, and canonical account. The budget source execution remains part of each fact's lineage. A budget with no calendar mapping cannot align. Readiness reports unmapped account, unmapped unit, unresolved budget period, and missing budget separately. A missing budget count covers only actuals with mapped account and unit.

## DRE input and readiness

The API exposes a scoped, paged fact list and a readiness summary for one period and optional unit. Each fact view carries its source, snapshot, execution, account classification, unit code and kind, and authority role. The run supplies review, mapping, derivation, and policy versions. Only `AUTHORITATIVE_ACTUAL` rows are actual inputs. An actual view returns an amount only when its mapped account has an explicit amount basis. `SUPPLEMENTAL_NOT_ADDITIVE` derived rows support review. Budget rows form a separate input. The API does not calculate a DRE measure.

Readiness blocks unresolved reviewed rows, excluded source rows, unmapped or unclassified accounts, unmapped units, unresolved billing competence, unsupported derivation, ambiguous or unmatched billing evidence, unresolved budget periods, missing aligned budgets, and unconfirmed NG amount semantics. The NG movement and final amount columns remain separate. Finance must confirm which amount enters each DRE line. A scope with no actual also blocks.

## Lineage, revision, and access

An actual fact links to a parsed NG record. That record links to the parse execution, source snapshot, and source. The normalization run links to the ReviewRun and pins the reviewed dataset revision. Billing and budget facts link to their own operational source records and executions. The run pins all budget execution IDs, the mapping revision, the derivation version, and the authority policy version. The input digest makes a successful rerun idempotent. A failed attempt can retry under the same digest with a new attempt number. Batches and the final status commit together. Failed batches roll back all facts.

All tables use the tenant database schema. Existing source group ACLs guard every input and output. Existing permissions govern account configuration, mapping edits, normalization, and reads. Audit rows record account and mapping changes and normalization start, success, or failure. They contain IDs, not business payload. The database rejects updates to canonical facts and mapping history. A normalization run can change only once from running to a terminal state.

## Real local smoke

The smoke used a disposable PostgreSQL database and the original five source files. It used exact legacy mapping rows only in that database. All counts came from current services, not constants. No client amount was written to this document.

| Measure | Count |
| --- | ---: |
| Parsed NG detail | 6,306 |
| Downstream-safe reviewed NG | 6,287 |
| Review-required NG | 19 |
| Excluded source rows | 4 |
| Canonical actuals | 6,287 |
| Billing records and billing facts | 1,258 |
| Derived billing facts | 0 |
| Budget facts across three executions | 45 |
| Legacy account identities inspected | 127 |
| Legacy unit identities inspected | 20 |

Exact legacy account mappings covered 5,717 of 6,287 actuals. They left 570 actual accounts unmapped. No NG unit matched an exact or unique structured legacy unit key, so all 6,287 actual units remain unmapped. The gross billing account mapped for all 1,258 billing facts. Exact billing entity matches covered 21; none had explicit competence. The other 1,237 billing entities remain unmapped. Of all billing facts, 931 have no explicit competence. No source budget account or unit mapped. All 45 budget periods remain unresolved. These blockers prevented real derived rows and actual-to-budget alignment. No actual has a mapped account, unit, and budget period together. The evaluable missing-budget count is therefore zero; it does not show budget coverage.

The reconciliation projection has 1,909 `UNMAPPED` items, zero matched, zero NG-only, zero billing-only, and zero ambiguous items. The real result does not establish absence of economic overlap. Six actual calendar periods exist. All six are blocked; none is DRE-ready. A representative normalization took 1.54 seconds after parsing and review.

The legacy consolidated table had 9,510 rows with a usable exact comparison key. Exact account, emission date, document, and movement comparisons matched 4,082 canonical actuals. They left 2,205 canonical-only and 5,428 legacy-only keys. The legacy table mixes other transformations and history. These differences are diagnostic, not proof of a source error. No monetary aggregate was published.

## Tests

Synthetic persistence tests cover safe and blocked NG records, excluded source rows, exact mappings, mapping revisions, billing fields, gross and retained derivation, budget period blockers, structured reconciliation, a ready scope with an approved amount basis, lineage, idempotency, rollback, and source ACLs. Migration validation used an empty PostgreSQL database and a downgrade/re-upgrade. Existing DATA-001 through DATA-004 regression suites remain separate.

## DATA-005A/B handoff

DATA-005 must use the scoped fact service and readiness result. It must refuse or clearly mark blocked scopes. It must confirm NG movement versus final amount, approve account DRE classes, map stable units, approve dated budget allocation, settle billing competence gaps, and resolve source authority for revenue overlap. It can then calculate DRE measures in a new versioned layer. DATA-004C/D does not calculate them.
