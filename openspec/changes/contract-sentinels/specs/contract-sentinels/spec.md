## ADDED Requirements

### Requirement: T17 reajuste not incorporated
T17 SHALL flag a contract whose reajuste data-base passed more than 30 days ago without a change in the monthly billed value, labelling the entitlement interpretation as "Ponto para validação jurídica".

#### Scenario: Overdue reajuste
- **WHEN** a contract data-base was 2026-08-01 and billing in September is unchanged
- **THEN** a T17 occurrence is recorded with the data-base, index and billed values

### Requirement: T18 contract balance runway
T18 SHALL compute months of remaining balance at the current execution pace and flag contracts with less than 4 months as needing an amendment.

#### Scenario: Short runway
- **WHEN** remaining balance covers 3 months at the average pace of the last 3 months
- **THEN** a T18 occurrence states the runway and the amendment need

### Requirement: T19 term milestones
T19 SHALL raise escalating alerts when a contract is 180, 120, 90 and 60 days from its end date, once per milestone.

#### Scenario: 90 days
- **WHEN** a contract reaches 90 days before its end date
- **THEN** a single T19 alert for the 90-day milestone is recorded

### Requirement: R7 and R8 weekly sentinels
R7 SHALL run weekly on Monday at 07:00 for T17–T19 and publish to Controladoria and Jurídico only when a milestone is reached; R8 SHALL run weekly for T20 and publish to Financeiro only when the average receivable term exceeds 45 days.

#### Scenario: Quiet week
- **WHEN** R7 runs and no milestone is reached
- **THEN** nothing is published and the run is recorded as silent
