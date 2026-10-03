## ADDED Requirements

### Requirement: Supplier registry from NG
The system SHALL keep a supplier registry with tax ID, name and city/state taken from NG entries and, when an approved official source is configured, the economic activity code.

#### Scenario: NG without supplier tax ID
- **WHEN** the NG source does not provide supplier tax IDs
- **THEN** the registry stays empty and the checks report "não avaliado — falta CNPJ do fornecedor"

### Requirement: Natureza versus supplier activity
The system SHALL compare each entry natureza with the natureza expected for the supplier activity according to a versioned table approved by the Controladoria, and record a divergence as a suggestion with evidence and possible PIS/COFINS credit impact.

#### Scenario: Fuel booked as extra expense
- **WHEN** an entry from a supplier whose activity maps to COMBUSTÍVEL is booked as DESPESAS EXTRAS
- **THEN** a suggestion "natureza provável COMBUSTÍVEL — crédito de PIS/COFINS possivelmente perdido" is created for approval

### Requirement: Unit suggestion by supplier city
For entries without unit, the system SHALL suggest the operational unit of the supplier city when exactly one unit matches, always as a suggestion requiring approval.

#### Scenario: Supplier in Toledo
- **WHEN** an entry without unit comes from a supplier located in Toledo-PR
- **THEN** the suggestion "unidade provável Toledo-PR (cidade do fornecedor)" awaits approval

### Requirement: Human approval and no silent learning
Every suggestion SHALL be approved or rejected by a person with justification; approved suggestions SHALL reclassify the entry in TON and appear in the weekly report for correction in the NG, and the system SHALL NOT change its rules from approvals without an explicit Controladoria rule decision.

#### Scenario: Suggestion rejected
- **WHEN** the Controladoria rejects a suggestion stating the purchase was not fuel
- **THEN** the entry stays as booked and the rejection is recorded with the reason
