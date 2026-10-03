## ADDED Requirements

### Requirement: Versioned unit classification
The system SHALL store each business unit classification (OPERATIONAL, IMPLEMENTATION, NON_OPERATIONAL, UNASSIGNED) as an append-only human decision with author, date and justification, and SHALL initially propose the Prompt Mestre §3.3 lists only as candidates pending confirmation.

#### Scenario: Unit without classification
- **WHEN** a unit has no confirmed classification
- **THEN** it is shown as "classificação pendente" and excluded from rankings until decided

### Requirement: Operational result view
The DRE SHALL offer an "Resultado operacional" scope that sums only OPERATIONAL units, shown next to the consolidated result, with non-operational units listed separately and the difference explained on the same view.

#### Scenario: June 2026 consolidated
- **WHEN** a user opens June 2026
- **THEN** the consolidated and operational results appear side by side and Administração Central is shown as a separate segregated amount

### Requirement: Rankings exclude non-operational units
Any ranking, benchmark or comparison between units SHALL include only OPERATIONAL units of comparable classification.

#### Scenario: Margin ranking
- **WHEN** a margin ranking is produced
- **THEN** Administração Central, Diretoria, Chácara, Shopping and mútuos are absent from it

### Requirement: Mandatory caveat on distorted consolidated result
When the consolidated result includes a non-recurring event above the T10 threshold or a non-operational distortion, every display of the consolidated result SHALL carry the caveat on the same line.

#### Scenario: Parcelamentos in the period
- **WHEN** the consolidated YTD result includes the tax-agreement balance in Parcelamentos
- **THEN** the consolidated figure is shown with "não é resultado operacional — inclui evento não recorrente" on the same line
