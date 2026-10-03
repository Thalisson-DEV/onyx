## ADDED Requirements

### Requirement: Obligations matrix per contract
The system SHALL keep, per contract, a versioned matrix of obligations with origin (contract clause, norm or CCT), required evidence, periodicity, due date, responsible and evidence status (valid, expired, missing).

#### Scenario: Missing evidence
- **WHEN** an obligation requires a valid environmental licence and no evidence document exists
- **THEN** the obligation status is "ausente" and a finding names the responsible

### Requirement: Due-date alerts
The system SHALL alert the responsible before an evidence expires, at approved lead times, and record an occurrence when it expires.

#### Scenario: Insurance expires
- **WHEN** the contract insurance policy passes its end date without a renewal document
- **THEN** an occurrence is recorded for the contract

### Requirement: Fact, interpretation and hypothesis separation
Compliance outputs SHALL classify each statement as fact (document), interpretation or hypothesis, and any conclusion depending on legal interpretation SHALL end as "Ponto para validação jurídica" without asserting non-compliance.

#### Scenario: Possible breach
- **WHEN** evidence suggests a contractual obligation was not met
- **THEN** the output states the documented fact and marks the breach question as "Ponto para validação jurídica"

### Requirement: Compliance input for ISC
The system SHALL compute, per contract, valid mandatory documents divided by required documents as the ISC Compliance dimension, reporting "não avaliada" when the matrix is empty.

#### Scenario: Empty matrix
- **WHEN** a contract has no obligations registered
- **THEN** the Compliance dimension is "não avaliada"
