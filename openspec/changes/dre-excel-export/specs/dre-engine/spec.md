## ADDED Requirements

### Requirement: XLSX export with calculation trail
The system SHALL export a persisted DRE calculation as an `.xlsx` workbook whose DRE sheet computes each line with formulas over a Base sheet containing every contributing fact with natureza, NG account, unit, competence, document, history, amount, source file, sheet, row and review disposition.

#### Scenario: Export June consolidated
- **WHEN** a user downloads the Excel for June 2026 consolidated
- **THEN** the workbook opens with DRE, Base, Tratamentos e decisões and Pendências sheets, and each DRE line cell contains a formula referencing the Base sheet

### Requirement: Exported totals equal the persisted calculation
Every DRE line value in the workbook, both cached and recalculated, SHALL equal the persisted result line to the cent.

#### Scenario: Recalculated in Excel
- **WHEN** the exported workbook is recalculated
- **THEN** every line equals the persisted calculation and the integration test fails on any difference

### Requirement: Not-ready export is blocked or marked draft
The system SHALL block the export for a NOT_READY period, except for users with Controladoria permission who MAY export a draft marked "Rascunho — base não pronta" on every sheet with the blockers listed.

#### Scenario: Draft export
- **WHEN** a Controladoria user exports a NOT_READY period
- **THEN** every sheet shows the draft mark and the Pendências sheet lists the blockers
