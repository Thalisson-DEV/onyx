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

### Requirement: Vehicle registry is the unit reference
The system SHALL keep one registry of vehicles and equipment with internal prefix or normalized plate, type, origin (own, rented from a company, rented from an employee, lent), current unit, service, status, fuel type, tank capacity and meter type, and the current unit SHALL change only through a recorded transfer event.

#### Scenario: Same plate in two units
- **WHEN** the initial load finds the same plate assigned to two units
- **THEN** the vehicle is loaded once and a conflict is listed for a person to choose the unit

### Requirement: Rental contracts drive rental payments
The system SHALL generate the monthly rental amount only for vehicles with an active rental contract and a monthly confirmation by the unit manager, SHALL apply the contract discount for recorded stopped days when the contract provides it, and SHALL apportion the cost by unit and by days in each unit.

#### Scenario: Rental without contract
- **WHEN** a rental payment is requested for a vehicle with no contract attached
- **THEN** the payment is held as "sem contrato" and the Controladoria is alerted

#### Scenario: Monthly confirmation missing
- **WHEN** the unit manager has not confirmed the vehicles in use for the month
- **THEN** the rentals of that unit are not released and the manager is reminded

#### Scenario: Transfer in the middle of the month
- **WHEN** a vehicle moves from Mossoró to Juazeiro do Norte on day 11 of a 30-day month
- **THEN** 10/30 of the cost goes to Mossoró and 20/30 to Juazeiro do Norte

### Requirement: Fleet events notify everyone at once
A fleet event (entry, transfer, breakdown or stop, return to operation, return or termination, replacement by the lessor, accident or fine, sale) SHALL be recorded once by the responsible person and SHALL notify fleet, operations management, finance and Controladoria at the same time, recording the days between the fact and its record.

#### Scenario: Termination recorded late
- **WHEN** a rental termination dated 01/10 is recorded on 20/10
- **THEN** the event shows 19 days of delay and any rental paid for the period after 01/10 is flagged

### Requirement: Fuelling record minimum fields and competência
A fuelling record SHALL carry vehicle, driver tax ID, date and time, litres, fuel, unit price, meter reading and station tax ID, SHALL be assigned to the competência of the fuelling date, and fuelling outside a vehicle (tank, can) SHALL carry a reason.

#### Scenario: Card statement without driver
- **WHEN** a card statement line has no driver and a zero odometer
- **THEN** the line is imported flagged NON_STANDARD and counted in the "sem motorista/hodômetro" check

#### Scenario: Invoice due two months after consumption
- **WHEN** a card invoice due in August contains June fuellings
- **THEN** the DRE assigns those fuellings to June

### Requirement: Impossible fuelling sequences and round values
The system SHALL flag a card or vehicle whose fuelled volume within an approved short window exceeds its tank capacity, and repeated round-value transactions on the same day, as findings for human explanation, never as conclusions.

#### Scenario: Twenty-five fuellings in two hours
- **WHEN** one compactor card records about 2,580 litres in two hours
- **THEN** a finding lists the transactions and asks for the explanation

#### Scenario: Tank capacity unknown
- **WHEN** the vehicle has no tank capacity in the registry
- **THEN** the check is not evaluated and the missing field is listed to the fleet owner
