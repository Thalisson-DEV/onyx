## ADDED Requirements

### Requirement: Executable verification criterion at detection
Every occurrence SHALL be created with an objective, executable verification criterion declared by its rule version (for example identity not detected in the next snapshot, group value back within the approved band, missing source delivered by a date).

#### Scenario: Duplicate detected
- **WHEN** NGF-DUP-DOC records the 392 occurrence
- **THEN** its verification criterion is "identidade não detectada na próxima importação do NG para fevereiro/2026"

### Requirement: Automatic evaluation on the next cycle
On each new snapshot or competence closing that covers the occurrence scope, the system SHALL evaluate the criterion and record VERIFIED, NOT_VERIFIED or INCONCLUSIVE with the evidence snapshot.

#### Scenario: Corrected at the source
- **WHEN** the next NG import for February no longer contains the duplicated row
- **THEN** the occurrence verification is VERIFIED with the new snapshot as evidence, and closure is proposed to a human

#### Scenario: Scope not covered
- **WHEN** the new import does not include February
- **THEN** no verification result is recorded for the 392 occurrence

### Requirement: R9 overdue action verification routine
R9 SHALL run monthly on D+2 (second business day until the PAD-CTRL-001 calendar is loaded), list occurrences with overdue deadlines or NOT_VERIFIED results, and notify each responsible person and the Gerência Geral; with nothing overdue it SHALL publish nothing.

#### Scenario: Two overdue items
- **WHEN** R9 runs and two occurrences are past their deadline
- **THEN** each responsible receives their item and the Gerência Geral receives the two-line summary

### Requirement: Realized impact only after verification
An impact SHALL move from predicted to realized only when the occurrence verification is VERIFIED against the following cycle base.

#### Scenario: Declared but not verified
- **WHEN** a manager declares a saving but the verification is NOT_VERIFIED
- **THEN** the saving remains predicted in the ROI register
