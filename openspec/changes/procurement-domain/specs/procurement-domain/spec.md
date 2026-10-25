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
The system SHALL consolidate equipment and vehicle rentals by asset, competence and unit from the rental contracts of the fleet domain, flagging shared assets without apportionment and possible duplicates.

#### Scenario: Same vehicle rented twice
- **WHEN** the same plate appears in two rental entries for the same competence in different units
- **THEN** a duplicate candidate is recorded for human confirmation

### Requirement: Supplier registry shared by payables, fleet and procurement
The system SHALL keep one supplier and payee registry keyed by tax ID, with legal and everyday names, type (company, individual, employee, public body), payment data in the payee's own name and a default natureza, shared by unit payables, rental contracts and purchases; a new supplier SHALL wait for approval.

#### Scenario: Same supplier under two names
- **WHEN** "ITA CHAVES SERVICOS E COMERCIO LTDA" with a tax ID and "ITA FERRAMENTAS" without one are entered
- **THEN** the second is held for approval with the first suggested as a possible match, never merged automatically

#### Scenario: Bank account used by two payees
- **WHEN** the same bank account is registered for two different payees
- **THEN** a finding is recorded for human review
