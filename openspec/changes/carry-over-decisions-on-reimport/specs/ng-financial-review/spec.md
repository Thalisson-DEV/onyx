## ADDED Requirements

### Requirement: Carry over review decisions across imports
When a new NG review detects a finding with the same identity key and the same evidence fingerprint as a finding decided in a previous review of the same source, the system SHALL apply the previous decision to the new review as a system decision that references the original human decision.

#### Scenario: Same duplicate found again
- **WHEN** the NG export is re-imported and the 392 duplicate appears with identical account, date, unit, documents and amounts
- **THEN** the previous treatment is applied, marked "reaproveitada da decisão de <autor, data>", and the item is not pending

#### Scenario: Evidence changed
- **WHEN** the same identity reappears with a different amount
- **THEN** the finding returns to pending and the previous decision is shown as context only

### Requirement: Decided finding not detected again is recorded
When a finding decided in the previous review is not detected in the new review, the system SHALL record a "não detectado nesta importação" event on its occurrence, linked to the new snapshot.

#### Scenario: Duplicate corrected at the source
- **WHEN** the new NG export no longer contains the duplicated 392 row
- **THEN** the occurrence receives a not-detected event that the verification routine can use

### Requirement: Re-import preview
Before confirming an NG import of periods that already have a review, the system SHALL show how many decisions will be carried over, how many findings return to decision and how many new findings appear.

#### Scenario: Preview before confirm
- **WHEN** a user uploads a new NG file for jan–jun/2026
- **THEN** the preview lists carried-over, reopened and new counts before anything is persisted as current
