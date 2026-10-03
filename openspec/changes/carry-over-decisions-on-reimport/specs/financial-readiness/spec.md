## ADDED Requirements

### Requirement: Explicit normalization input policy
Each normalization run SHALL record a versioned input policy (`ACTUAL_ONLY` or `ACTUAL_AND_APPROVED_BUDGET`), and importing billing or budget files SHALL NOT change actual facts nor add budget facts to the DRE input unless the policy includes approved budgets.

#### Scenario: Budget imported under actual-only policy
- **WHEN** a dotação workbook is imported while the policy is `ACTUAL_ONLY`
- **THEN** the next normalization keeps the same DRE input and READY periods stay READY
