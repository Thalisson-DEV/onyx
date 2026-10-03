## ADDED Requirements

### Requirement: XLSX export with calculation trail
The system SHALL export a persisted READY DRE calculation as an `.xlsx` workbook that covers January to the calculation's month of the same base (normalization) and structure version. The workbook SHALL have a DRE sheet, a Base sheet and a Premissas sheet. The DRE sheet SHALL show one block for the consolidated scope (only for users who can read the consolidated DRE) and one block for each visible unit/filial with entries, with one column per month and one Acumulado column. Each source line cell SHALL be a SUMIFS formula over the Base table, and each calculated line SHALL use the structure formula translated to cell references. The Base sheet SHALL list every NG entry that composes a source line with competence, unit, DRE line, amount, date, unit name, natureza, NG account code and label, document, history, amount basis, review disposition, source file and sheet · row.

#### Scenario: Export January to June
- **WHEN** an administrator downloads the Excel from the June 2026 consolidated result
- **THEN** the workbook opens with DRE, Base and Premissas sheets, the DRE sheet has the consolidated block and one block per unit with columns jan–jun and Acumulado, and each source line cell contains a SUMIFS formula over the Base table

#### Scenario: Unit-scoped user
- **WHEN** a user without consolidated access downloads the Excel from a unit result
- **THEN** the workbook has no consolidated block, and the Base sheet and the blocks contain only units visible to the user

#### Scenario: Entry without unit
- **WHEN** the base has an entry without unit/filial
- **THEN** the entry is in the Base sheet and in the consolidated block, in no unit block, and the Premissas sheet states the count

### Requirement: Exported totals equal the persisted calculation
Every DRE line value in the workbook, both cached and recalculated, SHALL equal the persisted result line to the cent for every month and unit with a READY result. The system SHALL refuse the export when a value differs.

#### Scenario: Recalculated in Excel
- **WHEN** the exported workbook is recalculated
- **THEN** every formula gives its cached value, and every line equals the persisted calculation

#### Scenario: Divergent value
- **WHEN** a value built from the Base differs from a persisted READY result line
- **THEN** the export fails with a conflict and no workbook is served

### Requirement: Not-ready periods are blocked or marked
The system SHALL refuse the export of a NOT_READY calculation. In a block whose unit has no READY result for a month, the system SHALL mark the month "Não pronta", show its values in a muted style, and list the unit and months in the Premissas sheet.

#### Scenario: Not-ready calculation
- **WHEN** a user requests the Excel of a NOT_READY calculation
- **THEN** the export fails with a conflict

#### Scenario: Unit month without a ready DRE
- **WHEN** a unit has no READY result for February
- **THEN** the unit block marks February "Não pronta" and the Premissas sheet lists the unit with "fev"

### Requirement: Premissas lists what the DRE does not apply yet
The Premissas sheet SHALL state the points the DRE does not apply yet: parcelamentos by paid installment, PIS/COFINS, revenue basis, budget (zero when no approved dotação is loaded), units without a ready DRE and entries without unit.

#### Scenario: No budget loaded
- **WHEN** no persisted result in the workbook has a budget value
- **THEN** the Premissas sheet states that the budget is zero and that the workbook shows only Realizado
