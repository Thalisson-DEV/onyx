## ADDED Requirements

### Requirement: Chat writes only through confirmed proposals
Every write requested through the TON chat SHALL be an action proposal validated by the backend, shown with its before × after effect, and applied only by the click of a person with permission, through the same service the screen uses, with audit origin "chat"; versioned services SHALL offer undo.

#### Scenario: Proposal not applied
- **WHEN** the agent proposes a DRE structure change and the person does not click Apply
- **THEN** nothing changes and the proposal stays open until it is cancelled or replaced

### Requirement: Remove a line from the DRE structure
The DRE structure SHALL allow removing a line, from the screen and from a chat proposal, recording the reason in a new structure version that can be restored; a removed line SHALL stop appearing and summing in that version only.

#### Scenario: Line already inside a group
- **WHEN** the Controladoria removes the line "imposto sem faturamento" because its value is already inside a group
- **THEN** a new structure version without the line is created, the DRE recalculates, and the history shows who removed it and why

#### Scenario: Line still referenced by a formula
- **WHEN** the line to be removed is used by a subtotal formula
- **THEN** the proposal shows the affected subtotal and asks for confirmation before applying

### Requirement: Billing percentage defaults follow the Controladoria rules
The default billing-percentage lines proposed by the agent SHALL follow the Controladoria rules in force and SHALL NOT include the 1% contingency rate excluded in the Controladoria minutes of 2026-10-20; PIS and COFINS fixed rates SHALL be replaced by the effective rates when the PIS/COFINS apuração is loaded.

#### Scenario: Default proposal after the exclusion
- **WHEN** a person asks the agent to add the taxes on billing without naming the rates
- **THEN** the proposal includes the administration fee and PIS/COFINS but no contingency line
