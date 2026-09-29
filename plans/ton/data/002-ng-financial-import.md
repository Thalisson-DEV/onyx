# DATA-002: NG financial export import

## Issues to Address

NG monthly financial worksheets repeat each launch under every ancestor account block. A flat row import counts a launch once per hierarchy level. DATA-002 adds a versioned structural parser for captured DATA-001 snapshots. It produces source-level records with exact row lineage and location-only diagnostics. It applies no business correction.

## Important Notes

The export has no header row and no official row identifier. The parser must infer structure from account codes and grouped cells. Parent blocks are not exact copies of their child blocks, so the import keeps only terminal-account rows and reports hierarchy differences.

The consolidated macro workbook gives labels for the monetary columns. It is a reference for column meaning only. The parser never opens it.

## Implementation strategy

Keep DATA-001 capture separate from parsing. Pin one immutable profile version to one parser. Read the verified snapshot offline, classify each row deterministically, and store accepted records in one transaction. Compare two exports by content, not by row position.

## Tests

Unit tests use synthetic workbooks for recognition, classification, parsing, diagnostics, limits, and diff. External dependency tests use migrated disposable PostgreSQL databases for profiles, executions, atomicity, triggers, ACL, tenancy, logging, and migration. A real-file smoke uses both client workbooks and reports only counts.

## Observed workbook contract

Each workbook has 20 sheets. Six sheets are financial: `Jan` to `Jun` in the original and `Jan ok` to `Jun ok` in the reviewed copy. Six `FG` sheets and six `-f` sheets are payroll. Two sheets are empty separators.

A financial sheet has data in A:Q from row 1. January also has 18 numeric cells in R:V with no known meaning. There are no formulas, headers, subtotals, or totals in the financial sheets.

| Column | Field | Meaning in the export |
| --- | --- | --- |
| A | `account_path` | `code - label` starts an account block. Blank continues the block. |
| B | `emission_date` | Date cell. Set on the first row of a date group. |
| C | `administrative_unit` | Set on the first row of a unit group inside a date group. |
| D | `document_number` | Optional. Often blank on parent-level copies. |
| E | `history` | Source text. |
| F:Q | twelve amounts | Movement, movement retention, movement net, installment retention, installment net, interest, penalty, discount, expense, loss, other deductions, final. |

Each account code occurs once per sheet. Codes form a tree, such as `1`, `1.1`, and `1.1.0001`. Terminal accounts are at depth three in most branches, but some are at depth two or one. Dates increase inside each block. Every date cell is at midnight.

Grouping evidence: a new date repeats C 1,359 times even when the unit does not change. A new date with blank C occurs 40 times, plus 7 account-start rows. Thus C is nested inside B. A new date with blank C means a blank unit, not the previous unit. The previous implementation carried C across dates. That rule was wrong and is replaced.

## Profile and recognition

`ng_financial_export` v1 is an immutable `ImportProfile` row for the logical `financial_launches` source. It stores XLSX and the A:Q column map. The service maps `(key, version)` to one parser class. It refuses a profile with no parser, a different stored column map, or a non-XLSX snapshot. A new layout needs a new version and parser. Old snapshots stay reparsable with v1.

A sheet is in scope when its name is a Portuguese month abbreviation, with an optional `ok` suffix. `ok` grants no authority. Other sheets, including payroll, are skipped without reading their rows. A month sheet must also match the structure. Its first non-blank row starts an account block or is a header. It has at least one dotted code. It has at least one account row with a date, a history, and a numeric amount. An empty month sheet is skipped with a warning. A mismatched month sheet, two sheets for one month, or no accepted sheet fails the execution. The filename is never used.

## Hierarchy and detail rule

The parser first collects all codes in a sheet. A code that is the nearest existing ancestor of another code is a parent. Rows in a parent block are `HIERARCHY` and are never records. Rows in a terminal block are `DETAIL`. Each physical row belongs to exactly one block, and terminal blocks are disjoint. Therefore no launch is counted at more than one level.

The parser reconciles each parent block with its direct children on the F:Q cell values. D and E cannot be used, because parent copies often blank D and change E. A parent row with no child match gives `PARENT_ROW_WITHOUT_CHILD_MATCH`. A child row with no parent match gives `CHILD_ROW_WITHOUT_PARENT_MATCH`. These rows are reported by location and are not imported or fixed. Root blocks have no parent and are not reconciled.

Other row classes are `HEADER`, `REPEATED_HEADER`, `SECTION`, `SUBTOTAL`, `TOTAL`, `BLANK`, and `UNKNOWN`. Header recognition uses the reference labels. Each sheet summary stores class counts and compact row spans.

## Field parsing

B continues within a block until the next B. A new B clears C. C continues within its date group. Account changes clear both. `source_values` keeps the physical cells, so a blank B or C stays blank there.

Amounts use `Decimal`. Numeric cells are exact through `str()`. Text must be pt-BR: dot groups thousands, and comma is the decimal separator. `R$` is allowed. Dot decimals, mixed separators, spaces inside numbers, and parentheses are rejected. Values must fit `NUMERIC(30, 10)`, so storage never rounds. Blank stays null. Zero stays zero.

Dates accept date cells at midnight, `dd/mm/yyyy`, and `yyyy-mm-dd`. Excel serial numbers, times, and datetimes with a time part are rejected. An invalid date rejects its row. Continuation rows after it are rejected with `INHERITED_DATE_INVALID`, so they never inherit an earlier date.

## Diagnostics and run status

| Code | Level | Effect |
| --- | --- | --- |
| `UNKNOWN_ROW`, `INVALID_DATE`, `INHERITED_DATE_INVALID`, `MISSING_DATE`, `INVALID_AMOUNT`, `MISSING_AMOUNTS`, `FORMULA_UNSUPPORTED` on a detail row | ERROR | The row is rejected. |
| `UNIT_BLANK` | WARNING | The row is kept with a null unit. |
| `PARENT_ROW_WITHOUT_CHILD_MATCH`, `CHILD_ROW_WITHOUT_PARENT_MATCH` | WARNING | Hierarchy difference. Nothing changes. |
| `ACCOUNT_SECTION_REPEATED`, `MONTH_SHEET_EMPTY`, `FORMULA_UNSUPPORTED` on a hierarchy row | WARNING | Report only. |
| `SHEET_OUT_OF_SCOPE`, `CELL_OUTSIDE_CONTRACT` | INFO | Report only. |

Diagnostics hold the sheet, row, column, level, and code. They never hold a cell value. An execution stores at most 2,000 diagnostics. Its statistics keep full counts for each code.

`ImportRun` keeps the DATA-001 states: `PENDING`, `RUNNING`, `SUCCEEDED`, and `FAILED`. It reports raw capture only and is not changed. `ImportProfileExecution` has its own states. `RUNNING` is committed before parsing. `SUCCEEDED` has no errors. `PARTIAL` means at least one row was rejected and the accepted rows were stored. `FAILED` stores no records and has an error code. Check constraints link `finished_at` and `error_code` to the state. A failed parse leaves the snapshot and its run unchanged.

## Lineage, identity, and duplicates

Every record stores source, snapshot, execution, sheet name, physical row number, and sheet month. `SourceLocator.source_record_key` stays empty, because the export has no source key.

`fingerprint` is a SHA-256 of the profile key and version, account code and label, effective date and unit, document, history, twelve amounts, and cells outside the contract. It excludes row number, sheet name, and snapshot. It is an import-local content hash, not a Keevo identifier. Two real launches with the same content have the same fingerprint. `duplicate_ordinal` numbers them in row order inside a sheet. Duplicate-looking rows are all kept.

## Persistence and atomicity

Tables: `ton_import_profile`, `ton_import_profile_execution`, and `ton_parsed_source_record`. Composite foreign keys tie records to the same snapshot and source as their execution. One execution cannot store two records for one sheet row.

Records are inserted as Core `executemany` batches of 500 in the same transaction as the terminal state. The real workbook needs 13 insert statements and 28 SQL statements in total. Any failure rolls back all records. The service then marks the execution `FAILED` in a new transaction.

Database triggers make profiles immutable. They make terminal executions immutable, block execution deletes, and block changes to execution identity. They also make records immutable and allow inserts only while the execution is `RUNNING`. ORM listeners give the same errors earlier. Downgrade refuses while any profile exists.

## Security and limits

The parser reads the bytes from FileStore and checks their SHA-256 against the snapshot. It checks ZIP metadata again and refuses containers with `vbaProject`. It loads with `read_only=True`, `data_only=False`, `keep_links=False`, and `keep_vba=False`. It never evaluates formulas, follows links, or calls HTTP. It ignores declared sheet dimensions and counts the stored rows.

Limits: 10 MiB, 24 sheets, 10,000 rows per sheet, 50,000 rows in total, 32 columns, 8,192 characters per cell, and 30 seconds. Each limit fails the execution without records.

The API uses the source ACL: `MANAGE_TON_SOURCES` to create the profile, `IMPORT_TON_SOURCES` to execute, and `READ_TON_SOURCES` to read executions and records. It returns no storage path. Logs contain IDs and counts only. The parse runs synchronously in the request.

## Structural diff

`compare_source_imports` compares two results month by month. It never decides which side is correct.

1. Records with equal fingerprints are unchanged. Equal duplicates pair in row order.
2. Other records pair when at least three of account, date, unit, document, and history are equal. The best score wins, then row order. A tie is counted as ambiguous.
3. Other records are added or removed.

A change to amounts, history, unit, or account is therefore a changed record, not a removal and an addition. The diff reports field names and row locations only. Limit: it is a heuristic without a source ID. A launch with three or more identity fields changed looks like one removal and one addition.

## Real-file acceptance

Both workbooks were captured as DATA-001 snapshots in an isolated PostgreSQL database with the PostgreSQL FileStore. Both executions were `PARTIAL`. A second execution of the original snapshot gave identical fingerprints.

| Measure | Original | Reviewed |
| --- | --- | --- |
| Sheets inspected / accepted | 20 / 6 | 20 / 6 |
| Physical rows in accepted sheets | 18,932 | 18,935 |
| Hierarchy rows excluded | 12,622 | 12,624 |
| Detail records stored | 6,306 | 6,307 |
| Records on hierarchy rows | 0 | 0 |
| Rejected rows (`INVALID_AMOUNT`, January, text in a money cell) | 4 | 4 |
| `UNIT_BLANK` warnings | 19 | 19 |
| `PARENT_ROW_WITHOUT_CHILD_MATCH` | 25 | 25 |
| `CHILD_ROW_WITHOUT_PARENT_MATCH` | 7 | 7 |
| `CELL_OUTSIDE_CONTRACT` (January R:V) | 18 | 18 |

Records by month in the original: 875, 1,012, 1,170, 1,010, 1,141, 1,098. The reviewed counts are the same except April, which has 1,011.

April: 1,009 unchanged, 1 added, and 1 changed record. The added row has its own date and is directly above the changed record in the same account. The changed record has a blank B in both files. In the reviewed file it now continues the date group of the inserted row, so only its effective date differs. DATA-003 must decide if that is intended.

June: 1,079 unchanged and 19 changed records, with no additions or removals. Changed fields: interest and final amount in 11 records; history only in 5; unit with retention, net, and final amounts in 1; interest, penalty, and final amount in 1; unit, history, interest, and final amount in 1. The previous candidate-key diff reported 17 changed, 2 added, and 2 removed. Its key included the unit, so the two unit changes looked like new launches.

The 25 parent rows without a child match show that leaf totals and root totals differ in five of six months. This is export evidence for DATA-003, not a parser error.

## Handoff to DATA-003

DATA-003 decides which reviewed changes are valid. It can use the April and June diffs, the hierarchy reconciliation warnings, the rejected money cells, and blank units. DATA-002 performs no correction, DRE, DFC, recommendation, LLM call, Keevo API call, or write to a source system.
