## ADDED Requirements

### Requirement: Explicit normalization input policy
Each normalization run SHALL record a versioned input policy (`ACTUAL_ONLY` or `ACTUAL_AND_APPROVED_BUDGET`), and importing billing or budget files SHALL NOT change actual facts nor add budget facts to the DRE input unless the policy includes approved budgets.

#### Scenario: Budget imported under actual-only policy
- **WHEN** a dotação workbook is imported while the policy is `ACTUAL_ONLY`
- **THEN** the next normalization keeps the same DRE input and READY periods stay READY

### Requirement: Reconciliation decisions follow the record content
A reconciliation decision SHALL apply to a later normalization whose NG or billing record has the same source, content fingerprint and duplicate ordinal as the decided record, even when the record was re-imported with a new id.

#### Scenario: Same NG file imported again
- **WHEN** the NG export is re-imported and normalized again
- **THEN** the earlier "eventos distintos" decision still applies and the run counts it as carried over
