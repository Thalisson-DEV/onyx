# dre-engine Specification

## Purpose
Linha de base do motor de DRE versionado (DATA-005ab, DATA-006cd, D-020). Estado real em
2026-10-02: estrutura `vale-norte-gerencial` (26 contas canônicas derivadas do
"Banco de Dados (Vale Norte).xlsm"), DRE READY jan–jun/2026 para consolidado e unidades com
lançamento, somente Realizado (Orçado = 0). Código: `backend/onyx/ton/dre/*`,
`backend/onyx/db/ton/dre.py`, `backend/onyx/server/ton/dre.py`, `web/src/views/ton/DrePage`.

## Requirements

### Requirement: Versioned structure and declarative formulas
The system SHALL calculate the DRE from a versioned structure with line hierarchy, approved account assignments and declarative formulas using Decimal arithmetic, producing immutable calculation runs and result lines with provenance.

#### Scenario: Zero denominator
- **WHEN** a formula denominator is zero
- **THEN** the calculation is blocked for that line instead of producing a value

### Requirement: No official result without readiness
The system SHALL refuse to produce an official result for a NOT_READY period and SHALL never present a NOT_READY period as READY in the UI.

#### Scenario: Unit without actuals
- **WHEN** a unit has no actual records in a month
- **THEN** the period and scope are NOT_READY with reason "sem realizado" and no result is shown

### Requirement: Monthly, year-to-date, drill-down and CSV export
The system SHALL serve monthly and YTD statements per scope (consolidated or unit), line contributors back to source file, sheet and row, a time series endpoint and a CSV export.

#### Scenario: Drill-down
- **WHEN** a user opens a DRE line
- **THEN** the contributing facts are listed with source file, sheet and row

### Requirement: Calculation is explicit
The system SHALL calculate a DRE only on explicit request (`POST /api/ton/dre/calculations`, the "Recalcular DRE" button or the work-queue item), never automatically after a decision.

#### Scenario: Base became ready
- **WHEN** the last blocker of a period is resolved
- **THEN** the work queue offers "Calcular" and no calculation runs until a user triggers it
