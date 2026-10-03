## ADDED Requirements

### Requirement: Fleet, fuel and maintenance sources
The system SHALL ingest fleet, fuelling and maintenance sources through the source pipeline with the minimum fields of the data contract, keyed by plate (fleet), plate + date + time (fuelling) and plate + date (maintenance).

#### Scenario: Fuelling without odometer
- **WHEN** a fuelling spreadsheet lacks the odometer column
- **THEN** the snapshot is NON_STANDARD and T21/T22 checks that need odometer are not evaluated

### Requirement: T21 anomalous consumption
T21 SHALL compare each vehicle km/l with the mean of vehicles of the same type in the same unit, only when at least 3 comparable vehicles exist, and flag deviations above 15% for 2 consecutive weeks.

#### Scenario: Fewer than three comparables
- **WHEN** a unit has two compactors of the same type
- **THEN** T21 is not evaluated for that type with the reason

### Requirement: T22 inconsistent fuelling
T22 SHALL flag fuelling of the same plate less than 4 hours apart, litres above tank capacity, regressive odometer, and fuelling on a day without recorded production for the vehicle.

#### Scenario: Litres above capacity
- **WHEN** a fuelling records 300 litres for a vehicle with a 275-litre tank
- **THEN** a T22 occurrence is recorded with the fuelling record

### Requirement: T23 and T24 fleet economics
T23 SHALL flag vehicles whose accumulated maintenance exceeds 60% of estimated replacement value (study) and 80% (mandatory decision); T24 SHALL compare vehicles planned in the confirmed dotação with vehicles in operation per type and unit.

#### Scenario: Fewer vehicles than planned
- **WHEN** the dotação plans 12 compactors and 10 operate
- **THEN** a T24 occurrence states the shortfall and the glosa risk

### Requirement: R2 weekly fuel audit and active FROTA specialist
R2 SHALL run on Fridays at 07:00 for T21 and T22 per unit and publish to Controladoria and the unit manager only on T22 exceptions or recurring T21; the FROTA specialist SHALL become active with fleet tools once the sources exist.

#### Scenario: No exceptions
- **WHEN** R2 finds no T22 exception and no recurring T21
- **THEN** nothing is published
