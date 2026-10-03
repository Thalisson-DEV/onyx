## ADDED Requirements

### Requirement: Production source
The system SHALL ingest production records with service, unit, day, quantity, unit of measure, team and vehicle through the source pipeline and the data contract.

#### Scenario: Missing unit of measure
- **WHEN** production rows lack the unit of measure
- **THEN** the source is NON_STANDARD and no unit cost or productivity is computed from it

### Requirement: S9 comparability guard
Any unit cost or productivity comparison SHALL include only services measured in the same unit of measure, and SHALL refuse comparisons across units of measure.

#### Scenario: Tons versus kilometres
- **WHEN** a benchmark mixes collection in tons and sweeping in km
- **THEN** S9 refuses the comparison and reports the incompatible units

### Requirement: T25 productivity
T25 SHALL compare production per team or vehicle with the productivity of the confirmed dotação and with comparable units, flagging deviations above 12% against the dotação.

#### Scenario: Productivity below dotação
- **WHEN** a collection team produces 15% less than the dotação reference
- **THEN** a T25 occurrence is recorded with both values

### Requirement: T26 unit cost comparison
T26 SHALL compute cost per unit produced per service and unit and flag differences above 15% between units of the same size and frequency as approved by the Controladoria.

#### Scenario: Unapproved comparability
- **WHEN** no size and frequency grouping is approved
- **THEN** T26 is not evaluated and states the missing configuration

### Requirement: Active COO specialist
The COO specialist SHALL become active with production tools (productivity ranking, cost per unit produced) once the production source exists.

#### Scenario: COO activated
- **WHEN** a conforming production source exists for a unit
- **THEN** the specialists page shows COO as active for that unit
