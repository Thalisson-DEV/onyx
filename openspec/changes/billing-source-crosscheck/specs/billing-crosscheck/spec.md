## ADDED Requirements

### Requirement: Municipal NFS-e source
The system SHALL ingest the municipal NFS-e export with a versioned deterministic profile that reads number, issue date, competência, taker, service amount, deductions, base, ISS, withholdings and status (normal, cancelled, replaced).

#### Scenario: Cancelled invoice
- **WHEN** an invoice has status cancelled in the municipal export
- **THEN** its amount is recorded as zero for revenue and the status is kept

### Requirement: Invoice crosscheck across sources
The system SHALL compare each invoice between the finance spreadsheet, the municipal export and NG, and SHALL record a divergence for an invoice missing in a source, or differing in amount, issue date, competência, withholdings or status beyond the approved tolerance.

#### Scenario: Cancelled invoice counted in the spreadsheet
- **WHEN** NF 535 is cancelled at the municipality and the spreadsheet shows R$ 818,11
- **THEN** a divergence names both values and the source of each

#### Scenario: Municipal export missing for the month
- **WHEN** no municipal export covers the competência
- **THEN** the crosscheck is not evaluated for that month and the missing source is stated

### Requirement: Official billing source is a versioned decision
The DRE SHALL take revenue from the billing source chosen by a versioned Controladoria decision and SHALL NOT switch sources automatically.

#### Scenario: Municipal export available but not chosen
- **WHEN** the municipal export is loaded and the decision still names the finance spreadsheet
- **THEN** the DRE keeps the spreadsheet and shows the crosscheck divergences beside it
