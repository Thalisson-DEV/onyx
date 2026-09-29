# DATA-003: NG financial review

## Issues to Address

Controladoria reviews each NG export by hand before the managerial close. Errors in financial launches affect the DRE and PIS/COFINS. DATA-003 adds a deterministic review of an ORIGINAL export. It finds supported inconsistencies, explains them, links them to the exact source row, and recommends an action only when the evidence supports one. People decide. Finance corrects NG. A later import verifies the correction. A reviewed dataset gives the future DRE a safe input boundary.

TON is not an Excel fixer. It never writes to NG and never changes a captured or parsed record.

## Important Notes

- Input is the DATA-002 output only: `ParsedSourceRecord` rows and the stored `ParseDiagnostic` list. DATA-003 has no parser and opens no workbook.
- The export has no source row identifier. Every cross-import correspondence is a content key, so it is conservative.
- The manually reviewed "ok" workbook is calibration evidence. The engine never receives it.
- DATA-002 stores at most 2,000 diagnostics per execution. The review compares the stored rejections with the full count and reports the difference as a blind spot.
- The real client workbooks were not available in this session (Drive access returned 401, and no local copy exists). The real-file results below come from the verified DATA-002 handoff. They were not revalidated by a DATA-003 run.

## Implementation strategy

### Reuse of the TON spine

| Need | Reused | Extension |
| --- | --- | --- |
| Rule catalog and versions | `Rule`, `RuleVersion`, `definition_hash` | none |
| Execution envelope | `AnalysisRun`, `AnalysisRunRuleVersion`, `AnalysisRun__SourceSnapshot` | `ton_review_run` (1:1) |
| Detection | `Finding` with `deterministic_payload` | none |
| Evidence | `FindingEvidence` | nullable `parsed_record_id`, `import_execution_id` |
| Case and lifecycle | `Occurrence`, `OccurrenceEvent`, `record_detection__no_commit` | none |
| Verification | `record_verification__no_commit` | none |
| AI boundary | `FindingInterpretation` | none; findings stay `NOT_REQUIRED` |
| Recommendation | none fits | `ton_review_recommendation` |
| Review decision detail | events have no kind, category or recommendation link | `ton_review_decision` |
| Audit | `TonAuditEvent`, `AuditAction` | new `ton_review.*` actions |

`ton_review_run` exists because `AnalysisRun` has no link to a parse execution. It holds the source, snapshot and execution (composite foreign keys), the rule set with definition hashes, the rule-set digest, the engine version, the rule evaluations, the diagnostic summary and the statistics.

### ReviewRun state machine

`RUNNING` → `SUCCEEDED` or `FAILED`. There is no PENDING, because execution is synchronous. There is no PARTIAL: evaluation is atomic, so a review either persists every result or none. A parse execution that is `PARTIAL` is a valid input; its rejected rows become findings.

1. Transaction 1 registers the catalog and commits the `RUNNING` run and a `RUNNING` analysis run.
2. The engine evaluates in memory. Transaction 2 writes findings, evidence, recommendations, rule outcomes, verifications and the `SUCCEEDED` state.
3. On any error, transaction 2 rolls back. Transaction 3 marks the run `FAILED` with a safe error code.

A database trigger makes terminal runs and run identity immutable and blocks deletes. `(status = 'RUNNING') = (finished_at IS NULL)` and `(status = 'FAILED') = (error_code IS NOT NULL)` are CHECK constraints. A `RUNNING` run older than 15 minutes is marked `FAILED` with `ABANDONED` before a new attempt starts.

### Rule contract and versioning

Each rule is a `RuleDefinition`: key, version, name, description, POP category, related categories, rule type, rule kind, engine status, severity, blocking flag, issue origin, required sources, required fields, recommendation capability, correctable fields, diagnostic codes, verification criterion and known limitations. One executor function exists per `key.vN`. There is no central if/elif.

The catalog in code is canonical. At the first review it becomes `Rule` and `RuleVersion` rows. A stored version whose `definition_hash` differs from the code definition stops the review with CONFLICT, so a change without a version bump cannot reinterpret history. A new version gives a new rule-set digest and a new review run. Old findings keep their version.

Engine status maps to governance status at registration: ACTIVE → `PENDING_APPROVAL`, EXPERIMENTAL → `TEST_ONLY`, BLOCKED → `DRAFT`, DISABLED → `SUSPENDED`. The review does not need approval, because no rule has a threshold. Report publication still needs `ACTIVE` through the existing approval path.

### Reproducibility and idempotency

A run records the snapshot, the execution (which pins the profile version), the rule keys, versions and hashes, and the engine version. Rules read no clock and no random value. A second request for the same execution and rule-set digest returns the existing `SUCCEEDED` run (`reused = true`) and writes nothing. `Finding` keeps `UNIQUE(analysis_run_id, rule_version_id, identity_key)`.

### Issue identity across imports

Identity components: `rule_code`, `source_system` (source id), `period` (sheet month) and `source_record_key`. The rule version is not a component. The record key is a SHA-256 over month, account code and label, effective date, unit, document, history and the twelve amounts, **without the fields the rule asks to correct**, plus an ordinal for equal content. A re-parse of the same snapshot gives the same keys, so the same occurrences receive `REPEAT_DETECTED`. Group, account and unit rules use `dup:month:fingerprint`, `acct:code` and `unit:code`. Rejected rows use their location only.

A repeated detection of a case that a person justified (`RISK_ACCEPTED`) or dismissed (`DISMISSED`) under the same rule version keeps that decision. The finding is recorded; the case does not reopen. A resolved case that is detected again reopens.

### Diagnostic is not finding

| Code | Treatment | Rule |
| --- | --- | --- |
| `INVALID_AMOUNT`, `MISSING_AMOUNTS`, `INVALID_DATE`, `INHERITED_DATE_INVALID`, `MISSING_DATE`, `UNKNOWN_ROW`, `FORMULA_UNSUPPORTED` (ERROR) | FINDING_ELIGIBLE | NGF-SRC-ROW-REJECTED |
| `UNIT_BLANK` | FINDING_ELIGIBLE, evaluated on the record | NGF-UNIT-MISSING |
| `PARENT_ROW_WITHOUT_CHILD_MATCH`, `CHILD_ROW_WITHOUT_PARENT_MATCH` | EXPERIMENTAL | NGF-HIER-RECONCILIATION |
| `MONTH_SHEET_EMPTY`, `ACCOUNT_SECTION_REPEATED` | REVIEW_RELEVANT | none |
| `SHEET_OUT_OF_SCOPE`, `CELL_OUTSIDE_CONTRACT`, `FORMULA_UNSUPPORTED` (WARNING) | TECHNICAL_ONLY | none |

Rejected rows have no parsed record. The finding uses the diagnostic and its locator as evidence and invents no value.

Unit is required because the managerial close attributes every launch to a unit or contract, the export carries the unit in column C, and the Controladoria checklist requires the destination unit. The finding says the attribution is missing. It never suggests a unit, because no structured evidence determines one.

### Active rules

| Rule | Scope | Blocking | Recommendation |
| --- | --- | --- | --- |
| NGF-SRC-ROW-REJECTED v1 | diagnostic or execution | yes | SOURCE_CORRECTION_REQUIRED |
| NGF-UNIT-MISSING v1 | record | yes | SOURCE_CORRECTION_REQUIRED |
| NGF-DUP-EXACT v1 | record group | yes | REQUEST_JUSTIFICATION (AMBIGUOUS) |
| NGF-ACCT-LABEL-DRIFT v1 | account | no | REVIEW_CLASSIFICATION, or DETERMINISTIC_CORRECTION with an authoritative mapping |
| NGF-UNIT-LABEL-DRIFT v1 | unit code | no | REQUEST_INFORMATION |

Duplicates: equal DATA-002 fingerprints inside one monthly sheet. The fingerprint covers account, label, effective date, unit, document, history, all amounts and extra cells. Equal amounts alone never match. All records stay. Cross-month repetition is not evaluated.

Competence, near duplicates, zero final amounts and blank documents are EXPERIMENTAL counts only. The sheet month has no year and no confirmed meaning, so no competence rule is active. The full catalog, including blocked rules, is in `financial-rule-catalog.md`.

### Issue origin

Each rule declares `SOURCE_BUSINESS_ERROR`, `EXPORT_STRUCTURE` or `UNRESOLVED`. A missing unit is `SOURCE_BUSINESS_ERROR`: the export repeats the unit on every date group, so a blank unit reflects the NG launch. Rejected rows and duplicates are `UNRESOLVED`. Hierarchy differences are `EXPORT_STRUCTURE`. A blank physical date that continues a date group is export structure and is never a finding.

### Findings, evidence and lineage

`Finding.deterministic_payload` holds the rule key and version, category, origin, scope, blocking flag, run, source, snapshot and execution ids, sheet month, keys, facts (codes, rows, counts), impact and the explanation. It holds no history, supplier, document or unit text.

Lineage: `Finding` → `FindingEvidence.parsed_record_id` → `ParsedSourceRecord.execution_id` → `ImportProfileExecution` → `SourceSnapshot` → locator `{sheet, row}`. Diagnostic evidence has `import_execution_id`, `source_snapshot_id` and `{sheet, row, column, diagnostic_code}`. A group finding links every member record. Evidence has confidence A (primary export) and redaction NONE, because it carries no value.

Explanations are pt-BR templates over the facts. Example: "Este lançamento não possui unidade administrativa, necessária para atribuição ao contrato/unidade no fechamento gerencial." No LLM is called. `interpretation_status` stays `NOT_REQUIRED`, and the existing interpretation table can attach to any finding later.

### Recommendations

`build_recommendation` runs after detection and is a separate module. Evidence levels: DETERMINISTIC, HIGH_EVIDENCE, AMBIGUOUS, INSUFFICIENT_EVIDENCE. No percentage exists. `suggested_value` is set only for DETERMINISTIC_CORRECTION with a single authoritative value; two CHECK constraints enforce it. No authoritative mapping is configured today, so no real finding carries a suggested value.

### Severity and financial impact

Severity uses the single TON scale: HIGH for rejected rows and duplicates, MEDIUM for a missing unit, MONITORING for label drift. No rule is CRITICAL. Impact is stored in the payload, never over the source value: `EXACT` unattributed final amount for a missing unit, `CONDITIONAL` exposure for duplicates (final amount times the extra occurrences), `UNKNOWN` elsewhere. `Finding.computed_impact_amount` stays NULL.

### Human decisions

`POST /occurrences/{id}/decisions` appends a `ton_review_decision` row and, where the lifecycle changes, the matching occurrence event in the same transaction.

| Decision | Occurrence transition | Requires |
| --- | --- | --- |
| ACKNOWLEDGE | none | reason |
| ACCEPT_RECOMMENDATION, REJECT_RECOMMENDATION | none | recommendation of this case |
| REQUEST_SOURCE_CORRECTION | ASSERT_NONCOMPLIANCE → CONFIRMED | authorization reference |
| JUSTIFY_EXCEPTION | ACCEPT_RISK → RISK_ACCEPTED | category and authorization reference |
| MARK_FALSE_POSITIVE | DISMISS → DISMISSED | authorization reference |
| CONFIRM_SOURCE_CORRECTION | RESOLVED (or RESOLVE_CRITICAL) | identified user |

Decisions need `MANAGE_TON_OCCURRENCES` and an EDITOR share. Closed cases accept no decision. Decisions and recommendations are immutable (ORM listener and trigger). Findings and evidence are never changed.

### Correction verification

After a review, TON checks open cases of the same source whose latest finding came from an earlier snapshot and that this import did not detect again. PASSED needs a unique correspondence: one record with the key in the earlier import and one in the later import, or a dissolved group, or a single label. Otherwise the result is INCONCLUSIVE with a reason: `NO_CORRESPONDING_RECORD`, `AMBIGUOUS_CORRESPONDENCE` or `LOCATION_ONLY_IDENTITY`. Rejected rows are always INCONCLUSIVE. Verification never closes a case; a person confirms with CONFIRM_SOURCE_CORRECTION.

### Reviewed dataset

The dataset is a derived projection, not a table. For one successful run and an `as_of` instant, each parsed record gets a disposition from the blocking findings of that run and the occurrence history up to `as_of`.

| Finding state | Disposition | Downstream-safe |
| --- | --- | --- |
| no blocking finding | ACCEPTED | yes |
| RISK_ACCEPTED | JUSTIFIED_EXCEPTION | yes |
| DISMISSED | ACCEPTED | yes |
| NEW, REOPENED, SUPERSEDED | REVIEW_REQUIRED | no |
| CONFIRMED | CORRECTION_REQUIRED | no |
| RESOLVED or verification PASSED | SUPERSEDED_BY_CORRECTION | no; use the later import |

The worst state wins. Non-blocking findings never block. A rejected row is EXCLUDED_SOURCE_ERROR and makes its month incomplete until a person justifies, dismisses or confirms it. `downstream_ready` is true only when every record is safe and no row is excluded. `dataset_revision` is a canonical hash of the run, the policy version and the last event number of each case at `as_of`. The same run and the same decision history give the same revision, and an older `as_of` reproduces an older revision.

### API

Prefix `/api/ton/financial-review`. Lists paginate with `limit` 1..100 and `offset`.

| Method and path | Permission and ACL |
| --- | --- |
| `GET /rules` | READ_TON_ANALYSIS |
| `POST /sources/{s}/executions/{e}/reviews` | IMPORT_TON_SOURCES, source write ACL |
| `GET /sources/{s}/reviews`, `GET .../reviews/{r}`, `.../rule-evaluations` | READ_TON_SOURCES, source ACL |
| `GET .../reviews/{r}/dataset`, `.../dataset/records` | READ_TON_SOURCES, source ACL |
| `GET /findings`, `/findings/{f}`, `/findings/{f}/evidence` | READ_TON_OCCURRENCES, occurrence ACL |
| `GET` and `POST /occurrences/{o}/decisions` | READ or MANAGE_TON_OCCURRENCES, occurrence ACL |

Filters: source, review run, execution, rule, POP category, severity, status, month, blocking for findings; disposition, month, account, unit and missing unit for records. List views carry no amounts, history, document or unit text, and no storage reference. Amounts appear only in the finding detail impact.

New occurrences inherit the source groups with EDITOR share. Tenant isolation is the tenant schema of the session; a review in one schema is invisible from another. Unknown or forbidden sources return NOT_FOUND. Occurrences and findings keep the existing 403 for absent or forbidden.

### Audit and logs

Audit actions: `ton_review.start`, `succeed`, `fail`, `verify_correction`, `acknowledge`, `request_correction`, `justify`, `false_positive`, `confirm_correction`, `recommendation_accept`, `recommendation_reject`. Finding creation is domain history (`DETECT`, `REPEAT_DETECTED`), so the run audit carries counts rather than one row per finding. Logs carry ids, counts, durations and exception class names only.

### Performance

The engine loads the execution in one query and builds grouped indexes once. Evidence and recommendations are batch inserts. Rule outcomes are one upsert. Each finding costs about eight statements through the existing occurrence path. A synthetic smoke through the real pipeline with 6,302 records, six sheets, 19 missing units, 4 rejected rows, 6 duplicate pairs and 18 cells outside A:Q took 1.37 s and 236 statements for 29 findings. A repeated request returned the stored run in 0.05 s. A test asserts that 300 extra clean records do not change the statement count by more than 10.

## Calibration methodology

`calibration.calibrate(original, reviewed, ton_flags)` uses the DATA-002 diff. `ton_flags` must come from a review of ORIGINAL. It reports per-month unchanged, changed, added, removed and ambiguous counts; changed records by field-group signature (DATE, UNIT, DOCUMENT, HISTORY, CLASSIFICATION, MONETARY, INTEREST, PENALTY, DISCOUNT, RETENTION, NET, FINAL_AMOUNT, OTHER); deltas with and without a TON finding; TON-only candidates; and the carry-forward structure. It reports no accuracy, precision or recall. A TON finding the reviewer did not act on is a TON-only candidate, not an error.

## April

Verified structure (DATA-002): 1,009 unchanged, 1 added, 1 changed. The added record has its own date and sits directly above the changed record in the same account. The changed record has a blank physical date in both files, so only its effective date moved.

- Added record: UNRESOLVED. It is a launch missing from the export or a manual enrichment. The export contains no trace of it.
- Changed record: EXPORT_STRUCTURE consequence. The date moved through carry-forward, not through an edit. The insertion may also have misdated this record in the reviewed file without intent; the reviewed file is not proof.
- Detectable from ORIGINAL alone: no. A blank-date continuation is normal structure, and an absent launch needs an external reference: the NG ledger, a bank statement or a document source.
- A synthetic equivalent reproduces the structure, gives no TON finding, and calibration classifies the change as `CARRY_FORWARD_AFTER_ADDED_RECORD` linked to the added record.

NOT REVALIDATED IN THIS SESSION — DRIVE/FILES UNAVAILABLE.

## June

Verified structure: 1,079 unchanged, 19 changed, 0 added, 0 removed. Both workbooks have 19 blank-unit warnings, so the two unit changes most likely reassign a unit rather than fill a blank one.

| Group | Records | Detectability |
| --- | --- | --- |
| INTEREST + FINAL_AMOUNT | 11 | REQUIRES_CROSS_SOURCE (payment date, bank statement or contract terms) |
| HISTORY | 5 | REQUIRES_HUMAN_CONTEXT (free-text standardisation) |
| UNIT + RETENTION + NET + FINAL_AMOUNT | 1 | REQUIRES_CROSS_SOURCE (unit or contract master, tax documents) |
| INTEREST + PENALTY + FINAL_AMOUNT | 1 | REQUIRES_CROSS_SOURCE |
| UNIT + HISTORY + INTEREST + FINAL_AMOUNT | 1 | REQUIRES_CROSS_SOURCE and REQUIRES_HUMAN_CONTEXT |

None of the 19 is DETECTABLE_NOW with the active rules. Final amount moves together with interest, retention or penalty, which suggests a derived final amount. The formula is not confirmed, so the composition rule stays BLOCKED. Even with a formula, a consistent but wrong interest value stays undetectable. Expected calibration: the 19 blank units and 4 rejected rows appear in both files, so they are TON-only candidates. NOT REVALIDATED IN THIS SESSION — DRIVE/FILES UNAVAILABLE.

## Hierarchy investigation

- Parent blocks repeat child launches. DATA-002 compares each parent block with its direct children on F:Q as type-tagged cell values, before any row rejection.
- Mismatches are not expected by the parser contract, but they exist: 25 parent rows without a child match and 7 child rows without a parent match, and root totals differ from leaf totals in five of six months.
- Rejected rows do not explain them. Reconciliation uses the raw cells, so a rejected child still matches an identical parent copy. All 4 rejections are in January, while totals differ in five months.
- At most 7 differences are value-changed copies (one parent and one child row each). At least 18 parent rows have no counterpart at any child: aggregate-only rows, or launches absent from the leaves.
- The old VBA and Power BI steps were not inspected in this session. DATA-002 used the macro workbook only for column labels. Whether they discard parent blocks is unknown.
- Decision: NGF-HIER-RECONCILIATION stays EXPERIMENTAL and diagnostic-only. It counts differences per sheet, pairing balance and overlap with rejected rows. It creates no finding and blocks nothing.
- Evidence still needed: NG documentation of parent-block content; confirmation whether NG accepts launches on non-terminal accounts; the differing column letters of unmatched rows (a future diagnostic can store letters, not values); and the VBA or Power BI treatment of parent rows.

## Boundaries

No DRE, DFC, PIS/COFINS, payroll parsing, dotação, Zeev rules, outlier baselines, LLM detection, Keevo API or source writes. The reviewed workbook is never an engine input. Real client files stay outside Git, fixtures, docs and logs.

## Tests

Unit (`tests/unit/ton/test_financial_review_engine.py`): each active rule positive, negative and edge cases; diagnostic promotion and the hierarchy exclusion; experimental counts; gating of disabled and blocked rules; rule versions; determinism; catalog integrity; production modules never import the calibration, the diff, openpyxl or an LLM; no client name in the package; dataset policy; April and June synthetic calibration.

External dependency (`tests/external_dependency_unit/ton/test_financial_review.py`): lineage to the physical row; idempotent rerun; re-parse keeps cases; immutability of snapshots, records, runs, recommendations and decisions; new rule version; unbumped change refused; atomic failure and retry; bounded statements; log redaction; every decision kind and its audit; justified exception survives a rerun; later corrected import verifies; unresolved and ambiguous imports do not verify; dataset dispositions, revision and `as_of` replay; source and occurrence ACL; another tenant schema; API surface; downgrade, refusal and re-upgrade.

## Handoff

The next data or DRE slice consumes `dataset_summary` and `dataset_records` for a `SUCCEEDED` review run, records the `dataset_revision`, and reads values only for downstream-safe records. Remaining risks and sources are listed in `financial-rule-catalog.md`.
