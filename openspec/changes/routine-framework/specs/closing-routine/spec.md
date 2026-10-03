## ADDED Requirements

### Requirement: R3 runs as a framework routine
R3 SHALL be defined as a routine of the routine framework (trigger D+1 business day, scope T1–T12 plus sanity, always publish, recipient Controladoria) and its report SHALL remain equivalent to the pre-migration report for the same inputs.

#### Scenario: Equivalence after migration
- **WHEN** R3 runs for June 2026 before and after the migration with the same base
- **THEN** both reports contain the same blockers, findings and DRE state
