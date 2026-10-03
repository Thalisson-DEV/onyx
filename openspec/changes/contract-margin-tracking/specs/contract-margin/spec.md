## ADDED Requirements

### Requirement: Planned versus actual margin per contract and month
The system SHALL show, per contract and competence, the planned margin from the confirmed contract master, the actual margin from the linked unit DRE, and the deviation in percentage points and in R$ per month.

#### Scenario: Mossoró January
- **WHEN** a user opens Mossoró-RN contract 02/2023 for January 2026
- **THEN** the view shows planned 16,89%, the actual margin of the month and the deviation

### Requirement: Unreadable months are not published as numbers
A month whose base failed critical validation (S10) or whose margin violates S1 SHALL be shown as "não legível" with the reason and SHALL be excluded from averages and rankings.

#### Scenario: April distortion
- **WHEN** April 2026 actual margin for Mossoró-RN is −313,9% due to revenue booked in another unit
- **THEN** April is shown as "não legível — receita da competência fora da unidade" and excluded from the average

### Requirement: Shared units require an approved apportionment
When a business unit serves more than one contract, actual margin per contract SHALL be computed only with an approved apportionment rule; otherwise the contracts show "margem real indisponível — unidade compartilhada".

#### Scenario: Two contracts in one unit
- **WHEN** a unit is linked to two contracts and no apportionment rule exists
- **THEN** both contracts show the unavailable message and no actual margin

### Requirement: Contract ranking
The contract ranking SHALL include only operational units and readable months, ordered by deviation from planned margin.

#### Scenario: Ranking with unreadable months
- **WHEN** the ranking is produced for the semester
- **THEN** unreadable months are excluded and the number of months used is shown per contract
