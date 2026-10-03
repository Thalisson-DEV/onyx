## ADDED Requirements

### Requirement: Versioned contract master with the five §4 blocks
The system SHALL store a versioned, append-only contract master per contract with the Prompt Mestre §4 blocks Identificação, Econômico, Operacional, Econômico-operacional and Governança, each filled field referencing its source document and evidence level.

#### Scenario: Field with document
- **WHEN** a user records the global value of Mossoró-RN contract 02/2023 citing the contract PDF
- **THEN** a new master version stores the value with evidence level A and the document snapshot

### Requirement: Contract events derive current values
Amendments, apostilamentos, reajustes, repactuações and extensions SHALL be recorded as append-only contract events with values, dates and document, and the current monthly value and term SHALL be derived from the original values plus applied events.

#### Scenario: Reajuste applied
- **WHEN** a reajuste event of 5% effective 2026-08-01 is recorded
- **THEN** the current monthly value from August 2026 reflects it and the original value remains visible

### Requirement: Declared analysis block for incomplete master
Any contract-level analysis SHALL check the completeness of the master fields it requires and, when incomplete, return "bloqueada — cadastro mestre incompleto" listing the missing fields, without estimating them.

#### Scenario: Margin without planned margin
- **WHEN** planned margin is requested for a contract without dotação data
- **THEN** the analysis is blocked and lists "margem contratual prevista" as missing

### Requirement: Contract, unit and payer links
The system SHALL keep versioned approved links between each contract, the NG business unit(s) and the billing payer text(s), and SHALL NOT infer links by similarity.

#### Scenario: Payer without link
- **WHEN** billing has a payer text not linked to any contract
- **THEN** it is listed as "tomador sem contrato vinculado" for a human decision

### Requirement: LLM suggestions require human confirmation
Values proposed by the assistant from contract documents SHALL be marked "proposto — confirmar" and SHALL enter the master only after human confirmation.

#### Scenario: Proposed value
- **WHEN** the assistant extracts the BDI from a contract PDF
- **THEN** the value appears as a proposal and the master is unchanged until a user confirms it
