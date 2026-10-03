## ADDED Requirements

### Requirement: Purchases and supplier identity
The system SHALL ingest purchases with item, quantity, unit price, supplier tax ID, unit, date and purchase type, and SHALL record an identity finding for every expense whose supplier cannot be identified.

#### Scenario: Consulting without supplier
- **WHEN** a consulting expense has no identifiable supplier
- **THEN** a finding states that the expense cannot be audited without supplier identity

### Requirement: T30 purchase price
T30 SHALL flag purchases whose unit price exceeds the median of the same item over the last 12 months by more than 15%, and recurring emergency purchases of the same item as a process failure; with less than 12 months of history it SHALL state the window used.

#### Scenario: Price above median
- **WHEN** an item is bought 20% above its 12-month median
- **THEN** a T30 occurrence is recorded with the median and the purchases used

### Requirement: T8 supplier versus unit
T8 SHALL flag expenses whose supplier tax ID or address is incompatible with the unit that recorded them, according to an approved compatibility rule.

#### Scenario: Supplier from another state
- **WHEN** a local-service supplier registered in another state is booked by Toledo-PR and the rule marks it incompatible
- **THEN** a T8 occurrence (NC-04) is recorded

### Requirement: Rentals consolidated
The system SHALL consolidate equipment and vehicle rentals by asset, competence and unit, flagging shared assets without apportionment and possible duplicates.

#### Scenario: Same vehicle rented twice
- **WHEN** the same plate appears in two rental entries for the same competence in different units
- **THEN** a duplicate candidate is recorded for human confirmation
