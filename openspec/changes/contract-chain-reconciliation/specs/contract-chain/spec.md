## ADDED Requirements

### Requirement: Chain ruler per contract, service and competence
The system SHALL build, per contract, service and competence, the ruler CONTRATADO, PLANEJADO, EXECUTADO, MEDIDO, FATURADO, RECEBIDO with quantity and value at each link, marking a link without data as "[lacuna]" and recording the gap as a blind-spot finding.

#### Scenario: No measurement source
- **WHEN** a contract has billing but no measurement bulletin for the competence
- **THEN** the MEDIDO link shows "[lacuna]" and a blind-spot finding is recorded

### Requirement: Link rule
A deviation SHALL be attributed to the first link where the quantity changes, and the occurrence SHALL be owned by that link domain with the other links listed as impacted.

#### Scenario: Billed 100 with production 97
- **WHEN** collection billed is 100% of contracted quantity and executed production is 97%
- **THEN** the occurrence is attributed to the execution/measurement link, not to billing

### Requirement: Measurement and billing tests
The system SHALL run T14 (measured value versus billed value with any difference not explained by a formal glosa), T15 (billing above recorded production) and T16 (production above plan without corresponding billing), and T13 (executed versus measured quantity above 3% on ABC curve A services) when production exists.

#### Scenario: Billing without glosa
- **WHEN** billed value is lower than measured value and no glosa is recorded
- **THEN** a T14 occurrence is recorded with both values

### Requirement: Receivable term test
T20 SHALL compute the average receivable term per municipality from invoice and receipt dates and flag terms above 45 days as critical working-capital risk.

#### Scenario: Slow payer
- **WHEN** a municipality average receivable term is 52 days
- **THEN** a T20 occurrence is recorded with the invoices used

### Requirement: R4 monthly contract reconciliation
R4 SHALL run monthly on D+3, execute the chain and T13–T16 per contract and always publish to Controladoria and Faturamento, stating "sem divergências" when nothing triggers.

#### Scenario: Clean month
- **WHEN** R4 finds no deviation
- **THEN** it publishes the reconciliation stating no divergences and the gaps that remain
