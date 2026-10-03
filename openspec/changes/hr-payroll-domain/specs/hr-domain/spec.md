## ADDED Requirements

### Requirement: Payroll, headcount and timekeeping sources with personal-data protection
The system SHALL ingest payroll, DP-01/DP-02 headcount and timekeeping sources with personal identifiers masked by default, visible only to roles granted HR data access, and SHALL NOT expose personal data to the assistant for users without that access.

#### Scenario: Controladoria without HR access
- **WHEN** a user without HR data access opens a T29 occurrence
- **THEN** amounts by unit and role are visible and employee names and IDs are masked

### Requirement: Single payroll source in the DRE
The DRE SHALL use payroll cost from exactly one approved source (NG or payroll report) per period, defined by a versioned decision, so that payroll is never counted twice.

#### Scenario: Both sources present
- **WHEN** the NG and the payroll report both contain June payroll
- **THEN** only the approved source feeds the DRE and the other is used for reconciliation

### Requirement: Headcount and reserve tests
T27 SHALL flag differences above 5% between headcount and dotação sizing for ABC curve A roles; T28 SHALL flag when absent plus relief workers exceed the contracted technical reserve.

#### Scenario: Reserve exceeded
- **WHEN** Mossoró-RN has 23 relief workers plus 26 absent over 207 active and the contracted reserve is 10,04%
- **THEN** T28 computes the ratio against the reserve and records an occurrence if it is exceeded

### Requirement: Overtime and severance tests
T29 SHALL flag units whose overtime exceeds 8% of payroll for 2 consecutive months; T12 SHALL flag severance payments without the corresponding 40% FGTS fine.

#### Scenario: Overtime two months
- **WHEN** a unit overtime is 9% of payroll in May and June
- **THEN** a T29 occurrence is recorded
