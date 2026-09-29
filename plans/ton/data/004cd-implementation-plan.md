# DATA-004C/D implementation plan

## Issues to Address

Build versioned canonical actual, billing, billing-derived, and budget facts. Exclude unsafe reviewed NG rows. Expose reconciliation and DRE input readiness without calculating DRE metrics.

## Important Notes

DATA-003 derives dispositions from a review run and decision history. Pin its dataset revision and `as_of` time. Billing parser fields vary by sheet. The legacy VBA reads a separate `IMPOSTOS` table, uses its competence and gross amount, and writes one gross row plus negative tax or fee rows. Only source-supported components may be derived. Budget amounts use a monthly contract basis without calendar allocation. Existing BusinessUnit has stable identity and tenant schema scope. All sources retain group ACLs.

## Implementation strategy

Add account identities, append-only mapping revisions, and separate canonical fact tables. Pin source executions, mapping revision, derivation version, and authority policy in a normalization revision. Load all mappings and reviewed dispositions once. Persist facts in batches and publish a successful revision in one transaction. Use NG actuals as the provisional authoritative DRE actuals. Reconcile structured revenue candidates; block ambiguous or unresolved overlap. Keep budget facts separate and block calendar comparison until a period mapping is approved. Provide small permissioned APIs for mappings, normalization, inspection, reconciliation, and DRE readiness.

## Tests

Use synthetic database tests for safe dispositions, mapping versions, lineage, derivation, budget period limits, reconciliation, readiness, idempotency, rollback, tenant ACL, and batching. Run DATA-001 through DATA-004 regressions. Validate migration on a disposable database, then run lint, format, type, and diff checks. Use real local records for smoke counts only. Keep client values out of code and reports.
