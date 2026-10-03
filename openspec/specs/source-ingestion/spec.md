# source-ingestion Specification

## Purpose
Linha de base (2026-10-02) da ingestão rastreável do TON: fontes como entidades de primeira
classe, execuções de importação, snapshots brutos imutáveis e perfis determinísticos de leitura
para NG/Keevo (lançamentos financeiros), faturamento (resumo de NFs) e dotação. Código:
`backend/onyx/ton/{sources,ng_financial,operational_import,client_import}`,
`backend/onyx/db/ton/{sources,import_profiles,operational_import,client_import}.py`,
`backend/onyx/server/ton/{sources,client_import}.py`. Histórico: plans/ton/data/001, 002, 004ab.

## Requirements

### Requirement: Immutable source snapshots
The system SHALL persist every imported file as an immutable `SourceSnapshot` tied to a `Source` and an `ImportRun`, with content hash, import time, tenant isolation, group ACL and audit events.

#### Scenario: File imported
- **WHEN** an authorized user uploads a file to a source
- **THEN** a new snapshot is stored with its hash and the original bytes are never modified afterwards

#### Scenario: User without import permission
- **WHEN** a user lacking `IMPORT_TON_SOURCES` attempts an import
- **THEN** the request is rejected and no snapshot is created

### Requirement: Deterministic NG financial export parser
The system SHALL parse NG/Keevo financial exports with a versioned deterministic profile that handles Brazilian currency, date and unit carry-forward, parent/detail hierarchy, fingerprints, lineage (sheet and row) and diagnostics, persisting `ParsedSourceRecord` and `ParseDiagnostic` rows.

#### Scenario: Invalid value cell
- **WHEN** a detail row has a non-numeric value cell
- **THEN** the row is rejected with a diagnostic and no amount is guessed

#### Scenario: New date resets unit context
- **WHEN** the parser reaches a new date block
- **THEN** the carried unit context is reset and an invalid date never leaks a previous context

### Requirement: Billing and budget structural readers
The system SHALL read the billing XLS export (payer, invoice number, emission date, service amount) and budget workbooks (only the `DOTAÇÃO` sheet, columns code, description, amount, share) as `OperationalSourceRecord` rows with diagnostics and lineage. The other dotação sheets (composições, curva ABC, BDI, dimensionamento de mão de obra e frota, DP-01/DP-02, encargos, reserva técnica) are not read yet.

#### Scenario: Budget workbook imported
- **WHEN** a dotação workbook is imported
- **THEN** only budget lines from the DOTAÇÃO sheet are extracted and no monthly calendar is inferred from the file name or by dividing annual values by 12

### Requirement: Manual acquisition is the only NG acquisition mode
The system SHALL expose NG/Keevo as manual file acquisition and SHALL label direct integration as awaiting authorized access until a real connector exists.

#### Scenario: Sources page
- **WHEN** a user opens Fontes
- **THEN** NG shows manual import and "aguardando acesso" for direct integration, never "conectado"

### Requirement: Re-import starts a fresh NG review
The system SHALL treat a new NG import as a new snapshot reviewed from scratch; decisions recorded on a previous review are not carried over (known limitation addressed by change `carry-over-decisions-on-reimport`). Budget sources are grouped by file name, so the same workbook uploaded under a different name creates a separate budget.

#### Scenario: NG re-imported
- **WHEN** the same NG period is imported again
- **THEN** a new review run is created and previously decided findings reappear as pending
