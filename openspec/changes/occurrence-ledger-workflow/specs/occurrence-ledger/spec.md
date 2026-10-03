## ADDED Requirements

### Requirement: Ledger view with Prompt Mestre fields
The product SHALL provide an occurrence ledger view showing, per occurrence, the Prompt Mestre §13.1 fields, with filters by status, criticality, unit, contract, domain, test code and responsible, and an Excel export of the filtered list.

#### Scenario: Filter critical open items
- **WHEN** a user filters CRITICAL and open
- **THEN** only critical open occurrences are listed with responsible, deadline and cycles open

### Requirement: Assignment and deadline
An authorized user SHALL be able to assign a nominal responsible (TON user or named role) and a deadline, defaulting to the criticality deadline; every assignment change SHALL be an audited event.

#### Scenario: Assign responsible
- **WHEN** a Controladoria user assigns the 392 occurrence to the Toledo-PR financial lead with the default deadline
- **THEN** the work queue and overdue list show that responsible and deadline

### Requirement: Status transitions respect autonomy limits
Status transitions SHALL follow the occurrence state machine, and closing a CRITICAL occurrence SHALL require a human decision with justification; the system SHALL never close a CRITICAL occurrence automatically.

#### Scenario: Automatic closure attempt
- **WHEN** a routine finds that a CRITICAL occurrence is no longer detected
- **THEN** it records the evidence and proposes closure, and the occurrence stays open until a human closes it

### Requirement: Cycles open counter
At each competence closing the system SHALL increment the cycles-open counter of every unresolved occurrence and show it in the ledger.

#### Scenario: Second closing
- **WHEN** an occurrence detected in July remains open at the August closing
- **THEN** its cycles-open counter is 2
