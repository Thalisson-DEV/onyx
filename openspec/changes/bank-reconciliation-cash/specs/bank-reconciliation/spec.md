## ADDED Requirements

### Requirement: Bank statement ingestion
The system SHALL ingest bank statements per account (OFX, CNAB or CSV) as immutable snapshots with account, date, amount, description and document when present.

#### Scenario: Duplicate statement upload
- **WHEN** the same statement file is uploaded twice
- **THEN** the second upload is rejected by content hash

### Requirement: Deterministic bank versus NG reconciliation
The system SHALL match bank movements and NG entries by amount, document and date within an approved tolerance, classifying unmatched items as NG without bank debit, bank debit without NG, intercompany on one side only, or date difference, and SHALL leave ambiguous matches to a human decision.

#### Scenario: Two candidates for one debit
- **WHEN** a bank debit matches two NG entries with the same amount within tolerance
- **THEN** the item is ambiguous and requires a human choice; no automatic match is made

### Requirement: Duplicate payment workflow
Duplicate payment candidates detected in statements SHALL follow candidate, manager confirmation, refund or reversal record, with evidence at each step, and the system SHALL NOT mark a payment as duplicate without confirmation.

#### Scenario: Manager rejects candidate
- **WHEN** the manager states the two payments are distinct
- **THEN** the candidate is closed as not duplicate with the justification

### Requirement: Petty cash and advances control
The system SHALL track advances and their settlements per person and flag advances without settlement beyond the approved period, recommending (not enforcing) blocking new advances.

#### Scenario: Open settlement
- **WHEN** an advance remains unsettled beyond the approved period
- **THEN** an occurrence is recorded with the recommendation to block new advances
