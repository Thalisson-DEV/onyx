# DATA-006A/B financial readiness workspace

## Issues to Address

DATA-005 reports why a DRE scope cannot run. Finance needs a controlled path from each blocker to an approved decision.

The workspace shows source evidence, candidate configuration, affected records, and period readiness. Approval never runs an official DRE calculation.

## Important Notes

- A candidate is evidence. It does not change a canonical fact.
- An approved mapping has an append-only mapping revision. A later mapping supersedes its target for new runs.
- A normalization pins mapping, amount basis, and reconciliation decision revision numbers.
- A DRE structure version pins its approved account assignments. An assignment change creates a new version.
- Source snapshots, parsed records, facts, prior normalization runs, and DRE results remain historical.
- A source reader needs a visible business unit for unit scoped readiness. Consolidated DRE readiness requires an administrator.
- A legacy reference file is optional evidence. Runtime normalization does not open XLSM or PBIX files.

## Implementation strategy

### Blocker taxonomy and overview

The overview evaluates each actual period through the DATA-005 readiness service. It keeps the existing blocker codes.

The workspace has dedicated lists for `UNMAPPED_UNIT`, `UNMAPPED_ACCOUNT`, `ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED`, `DRE_ACCOUNT_UNMAPPED`, `DRE_MAPPING_PENDING_APPROVAL`, `BUDGET_UNMAPPED_ACCOUNT`, `BUDGET_UNMAPPED_UNIT`, `BUDGET_PERIOD_UNRESOLVED`, and both reconciliation blockers.

Other DATA-005 blockers remain visible by period. These include review decisions, excluded rows, missing budget, unsupported derivation, retention, missing actuals, and formula errors. They require the source, review, or DRE structure workflow.

Dedicated lists aggregate in PostgreSQL and return at most 100 groups per page. A row shows source key, affected count, periods, status, and safe evidence. Reconciliation rows show source presence, mapping state, document match availability, and period. The UI does not return financial amounts.

### Candidate and approved states

Exact canonical code matches produce candidates when one visible target exists. An earlier approved mapping appears as `APPROVED`. An administrator can import exact legacy reference rows with a SHA-256 digest. Import validates that each source key exists. Imported evidence stays separate from canonical accounts and mappings.

The import endpoint accepts at most 500 rows per request. It requires exact source and suggested codes. It stores only the suggested code, optional label, reference label, and digest. The reviewer can reject a target candidate or legacy reference with a reason. Rejection is append-only. An approved mapping cannot be rejected through the candidate endpoint.

### Unit and account workflow

The reviewer searches existing canonical targets, reviews an exact candidate or legacy evidence, enters a reason, and confirms approval. An administrator can create a canonical account before mapping. Account creation alone does not map a source code.

The mapping API requires a reason. It writes a new mapping revision and audit event. The reviewer recomputes normalization to use the new revision. The previous run retains its mapped or unmapped state.

### Amount basis

`MOVEMENT` and `FINAL` are the only approved choices. The blocker list counts available components without returning values. An unmapped account shows a dependency on account mapping.

The reviewer approves a basis with a reason. The account basis revision is append-only. New normalization runs use the latest pinned revision. No amount field is inferred from a nonzero value. The inspected legacy reference supplied no proven basis candidate.

### DRE assignment

The list groups mapped actual and budget accounts by canonical account. An exact classification code can suggest a source-sum line. A pending assignment remains a candidate.

An administrator selects a line and enters a reason. The DATA-005 assignment service copies the structure into a new version. It never changes a prior version. The real smoke had no canonical account catalog, so it had no DRE-line candidates.

### Budget period

The source has monthly contract budget rows. The reviewer can approve one month or a start and end month. A range must fit the exact source contract term. Only `MONTHLY_CONTRACT` accepts a range.

Each selected month retains the source amount and the mapping ID. The service never divides an annual value by twelve. A single approved month does not prove a full contract allocation. Finance must choose the correct relation.

### Reconciliation

The reviewer can choose `NG_AUTHORITATIVE`, `SUPPLEMENTAL`, `EXPECTED_DIFFERENCE`, or `NOT_SAME_EVENT`. `NG_AUTHORITATIVE` requires a paired NG and billing item. Billing cannot become an independent actual under the DATA-004 authority policy.

A decision pins exact source record IDs and a reason. Reconciliation applies the decision only to a new normalization. A document match is evidence, not an authority decision.

### Recompute and revisions

The recompute endpoint reconstructs the input request from a selected run. It checks source access and writes an audit event. Normalization creates a new run when a pinned decision changes. Readiness then evaluates the new run and the selected DRE version.

Approval does not execute `/ton/dre/calculations`. A user must call that DATA-005 endpoint explicitly to create an official result.

### RBAC, audit, and frontend

`READ_TON_SOURCES` permits source scoped reads. Visible business unit rules protect unit scoped views. `MANAGE_TON_SOURCES` permits source mapping and reconciliation decisions. `FULL_ADMIN_PANEL_ACCESS` permits account, amount basis, and DRE structure changes. `IMPORT_TON_SOURCES` permits recomputation.

The audit records candidate rejection, legacy evidence import, mapping revisions, amount basis revisions, DRE assignment versions, reconciliation decisions, and recompute requests. It records actor, time, revision, and safe reason where relevant. It excludes source amounts and financial histories.

`/admin/financial-readiness` shows period status, blocker chips, category lists, search, pagination, candidate evidence, target selection, and a two-step approval. It reports loading, error, and empty states. A non-admin reader selects a visible unit.

## Real smoke

A disposable PostgreSQL database reproduced the current real source inputs. No Finance approval was applied.

| Measure | Result |
| --- | ---: |
| NG parsed / downstream safe | 6,306 / 6,287 |
| Billing / budget facts | 1,258 / 45 |
| Evaluated / ready periods | 6 / 0 |
| Distinct unmapped unit keys | 22 |
| Distinct unmapped account keys | 145 |
| Exact legacy account evidence | 122 keys, affecting 5,717 actual records |
| Exact legacy unit evidence | 0 keys |
| Approved mappings in this disposable run | 0 |
| Amount basis / DRE-line candidates | 0 / 0 |
| Budget period / reconciliation authority candidates | 0 / 0 |
| Unresolved budget period facts | 45 |
| Unresolved reconciliation items | 7,545 |

The reconciliation count uses a fresh catalog with no approved mappings. It differs from an earlier smoke with approved account mappings. Legacy evidence import changed no mapped fact. Readiness stayed 0/6.

Finance must create or review canonical accounts, approve mappings, choose amount bases and DRE lines, map budget periods, and decide reconciliation. The imported evidence covers source codes only. It does not approve a target.

## Tests

Synthetic backend tests cover candidate rejection, account approval, reasoned revisions, readiness lists, budget ranges, amount basis pins, reconciliation decisions, audit, and old-run immutability. DATA-005, DATA-004, and DATA-003 regression suites check existing contracts.

The focused frontend test covers loading, error, empty, reason, confirmation, and approval request fields. Migration checks run against disposable PostgreSQL. The real smoke prints counts only.

## DATA-006C/D handoff

The next phase can build the final DRE dashboard and reports from explicit DATA-005 calculation runs. It must keep the `READY` gate and pinned lineage. It must not treat this workspace's candidates or a ready check as an official DRE result.
