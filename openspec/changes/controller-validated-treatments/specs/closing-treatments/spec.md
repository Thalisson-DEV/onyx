## ADDED Requirements

### Requirement: Versioned closing treatments
The system SHALL store each closing treatment as an append-only versioned rule with scope (account or natureza, unit, period range), a deterministic effect (exclude from period result, reclassify to a DRE line, or replace by an authorized source value), author, timestamp, mandatory justification and a reference to the Controladoria decision evidence.

#### Scenario: Treatment recorded
- **WHEN** an authorized Controladoria user records "PARCELAMENTOS de saldo de acordo saem do resultado do período"
- **THEN** a new treatment version is stored with scope, effect, author, date and justification, and earlier versions remain readable

#### Scenario: Unauthorized user
- **WHEN** a user without financial decision permission tries to record a treatment
- **THEN** the request is rejected and audited

### Requirement: Treatments applied deterministically with provenance
The normalization SHALL apply the treatments in force, record the treatment versions it used, and the DRE SHALL show for each affected line the value before and after treatment and the treatment that changed it.

#### Scenario: DRE line with treatment
- **WHEN** a user opens the Parcelamentos line after the treatment is applied and recalculated
- **THEN** the line shows the treated value, the original NG value and the treatment version with author and date

### Requirement: Treatments needing missing data stay blocked
A treatment whose effect depends on a source that is not available SHALL remain blocked, SHALL NOT change any value, and SHALL appear as a pending input with the source it needs.

#### Scenario: Only paid installment enters
- **WHEN** the Controladoria decides that only the monthly paid installment of tax agreements enters the result but no installment schedule source exists
- **THEN** the treatment is recorded as blocked by "cronograma de parcelas" and the DRE is unchanged
