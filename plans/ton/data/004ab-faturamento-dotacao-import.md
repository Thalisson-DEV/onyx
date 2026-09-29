# DATA-004A/B: Faturamento and Dotação source import

## Issues to Address

Capture invoice and budget workbooks as source-level records. Preserve original bytes, typed fields, physical rows, and safe diagnostics. Stop before accounting normalization.

## Important Notes

The real billing XLS has 20 sheets. Eighteen have invoice tables. Two contain a summary and retention reference, and are outside the record contract. Invoice tables have three header shapes: an older A:K table, a B:W table, and a table with a separate competence column. The header can follow ten metadata rows and can repeat between monthly sections. Totals repeat invoice amounts. Some dates are BIFF date cells; older rows use day-first text. The current table has an explicit Comp date cell and a free-text service period. The separate competence table has month/year text. Other historical tables do not prove competence.

The three budget workbooks have the following structure. Labels A, B, and C refer to the three supplied files in the order listed in the goal.

| Workbook | Sheets | Hidden | Merged ranges | Named ranges | Structural profile |
| --- | ---: | ---: | ---: | ---: | --- |
| A | 44 | 0 | 2,488 | 2,684 | budget_annual_schedule v1 |
| B | 19 | 13 | 56 | 7,308 | budget_annual_schedule v1 |
| C | 110 | 99 | 2,725 | 22,825 | budget_term_schedule v1 |

Each workbook has one visible, 69-row DOTAÇÃO schedule. A is an item code, B a description, C a total amount, and D a share. The cost composition starts at row 10. The financial proposal starts at row 35 and repeats or derives cost values. Other sheets provide prices, labor, fleet, formulas, summaries, and references. They are classified but do not become records. The schedule itself has no merged ranges. Its values refer to support sheets.

The annual profile has an explicit annual contract label and a monthly cell with source formula C3 = C2 / 12. The term profile has an explicit 30-month contract label and source formula C2 = C3 * 30. These structural differences select profiles. Neither profile uses a city or filename. Both express their cost composition in the source's monthly contract basis. No calendar month allocation is present.

## Implementation strategy

Source -> ImportRun -> SourceSnapshot -> ImportProfileExecution -> OperationalSourceRecord reuses DATA-001 and DATA-002. Create one billing_invoices logical Source and one budget logical Source in each tenant. An acquisition change can keep the same Source. The immutable profile contracts are billing_export v1 (XLS), budget_annual_schedule v1 (XLSX), and budget_term_schedule v1 (XLSX). The profile selection API reads verified snapshot bytes and checks workbook structure. It does not inspect the filename.

The XLS reader is xlrd 2.0.2, pinned directly because the source is BIFF/XLS. It reads static cell data without Excel, Office automation, LibreOffice, or macro execution. Header labels select columns. It skips metadata, repeated headers, totals, and reference sheets. It accepts numeric cell values and strict Brazilian decimal text. A dash in an optional monetary column is null. It never changes null to zero. Dates use BIFF date formatting or explicit day-first text. Competence uses a date cell or an explicit month/year label. A competence range with no single month is rejected.

Billing records store the invoice number, payer text, emission date, optional competence, service amount, optional invoice tax and retention amounts, optional net values, collection/status text, and raw physical cells. Fields appear only when the sheet header supports them. The invoice number is not a proved global identifier. A SHA-256 fingerprint covers the profile version, payer, invoice number, emission date, competence, service amount, and typed optional fields. All matching rows remain. Their ordinal records duplicate order. The parser rejects an invalid invoice number, date, competence, or money field. It reports a retention-total mismatch only when all three retained components and the total exist. It makes no tax-law claim.

The budget parser selects the one coded schedule and classifies other sheets as SUPPORT, REFERENCE, or SUMMARY. It takes only terminal codes in the cost composition. It excludes five parent codes and the coded financial-proposal rows. Code alone is not unique in the source, so row location is part of record identity. It stores the source contract label, code, description, cached amount, share, contract term, monthly basis, raw A:D cells, and whether the amount came from a formula cache. A missing or malformed essential cache rejects the row. It does not evaluate formulas or follow external links. A merged essential cell is rejected. Merges on support sheets cannot silently create detail.

The record table keeps source, snapshot, execution, sheet, row, typed core columns, optional typed fields, and raw cell text. Composite foreign keys enforce lineage. A database trigger permits insertion only while the execution is RUNNING and forbids later record changes. The service checks the stored SHA-256 before parsing. It inserts 500 rows per batch. The final status and all records commit together. A failed transaction leaves a FAILED execution and no records. Source ACL and tenant sessions govern create, execute, and read. Profile actions use existing audit events. Logs contain IDs and counts only. APIs list profiles, select a profile, execute it, inspect diagnostics, and page through records. They expose no storage path.

Limits: 10 MiB original bytes, 120 sheets, 2,000 rows per invoice or budget detail sheet, 30,000 total XLS rows, 300 columns, 8,192 characters per cell, and a 45-second parser time check. OOXML ZIP metadata is validated before load. The budget reader opens formula and cached views once each. It does not reopen a workbook per row.

## Real smoke

All four files passed through DATA-001 capture and DATA-004A/B execution in a disposable migrated PostgreSQL database. The test FileStore held raw bytes in memory. It did not put customer data in the repository.

Full rows inspected counts header scans in the XLS and detail-schedule scans in each XLSX. The budget reader classifies support sheets from their names and structural probes. It does not scan those sheets for records.

| File | Profile | Status | Sheets | Full rows inspected | Records | Rejected | Warnings | Duplicate candidates |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Billing XLS | billing_export v1 | PARTIAL | 20 | 1,871 | 1,258 | 15 | 1 | 0 |
| Budget A | budget_annual_schedule v1 | SUCCEEDED | 44 | 69 | 15 | 0 | 0 | 0 |
| Budget B | budget_annual_schedule v1 | SUCCEEDED | 19 | 69 | 15 | 0 | 0 | 0 |
| Budget C | budget_term_schedule v1 | SUCCEEDED | 110 | 69 | 15 | 0 | 0 | 0 |

The billing parser accepts 18 invoice sheets and skips two non-invoice sheets. It excludes 186 aggregate or narrative rows. Rejections are 11 invalid invoice identifiers, three invalid or absent dates, and one competence range that does not identify one month. The accepted emission dates cover July 2013 through August 2026. Explicit competence exists on 327 accepted records. One accepted competence year is more than five years from emission and has a warning. The parser preserves the source value and does not infer a correction.

Each budget execution accepts one detail sheet. Each excludes five coded parent rows and 28 coded proposal rows. The remaining sheets are support, reference, or summary. Detail amount caches were present. Formula freshness cannot be proved from a static workbook. Workbook A has 37 support, three summary, and three reference sheets. B has 14 support, one summary, and three reference sheets. C has 98 support, five summary, and six reference sheets.

## Tests

Synthetic XLS and XLSX tests cover structural matching, metadata and repeated headers, date and competence parsing, Brazilian money, null and zero, malformed rows, duplicate-looking records, formulas and missing caches, merged cells, detail and aggregate separation, annual and term profiles, unknown structures, and resource limits. Disposable PostgreSQL tests cover capture, profile creation, replay, physical lineage, PARTIAL and FAILED states, access checks, audit, batch inserts, rollback, and migration downgrade/re-upgrade. No client row or value is a fixture.

## DATA-004C/D handoff

Billing records provide trusted source invoice number, payer text, emission date, gross service amount, and fields present in each header. Explicit competence is trusted as a parsed source value, except the flagged year gap needs human review. The source provides no official invoice ID. The next phase needs entity identity, account and unit mappings, and reconstruction of the later FATURAMENTO VBA entries. This task creates no revenue entry, PIS/COFINS entry, or DRE fact.

Budget records provide a coded monthly cost-composition amount with exact row lineage and a contract label. A and B use the annual contract layout; C uses the 30-month layout. The source has no dated monthly allocation. The next phase needs an approved account crosswalk, contract/unit crosswalk, budget effective period, and confirmation that cached formulas match the source's intended version. It must not divide an annual total by 12 or compare these records with NG Actual until those mappings exist.
