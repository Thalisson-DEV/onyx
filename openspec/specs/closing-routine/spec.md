# closing-routine Specification

## Purpose
Linha de base da rotina R3 (Fechamento preliminar mensal) e dos relatórios versionados. R3 é a
única rotina do Prompt Mestre §12 implementada. Código: `backend/onyx/ton/agent/scheduling.py`,
`backend/onyx/db/ton/{routine_schedule,closing,reports}.py`,
`backend/onyx/background/celery/tasks/ton/tasks.py`, `web/src/views/ton/{AutomationsPage,ReportsPage,ReportViewer}`.

## Requirements

### Requirement: Scheduled monthly R3 with confirmed calendar
The system SHALL schedule R3 on the first business day of the month at 08:00 America/Sao_Paulo using an explicitly confirmed holiday calendar (Petrolina), through the tenant-aware Celery Beat, with retry-safe idempotent publication keys, and SHALL allow a manual run.

#### Scenario: Calendar not confirmed
- **WHEN** no confirmed calendar is configured
- **THEN** R3 is not activated and the UI explains that the calendar must be confirmed

### Requirement: R3 inspects closing through CFO, AUDITOR and CEO
The system SHALL run the closing analysis (sources, review findings, readiness, DRE state) recording analysis steps, and publish an immutable report revision linked to the analysis run, findings, rule versions and source snapshots. R3 SHALL NOT approve financial decisions.

#### Scenario: Pending decisions at run time
- **WHEN** R3 runs while readiness blockers exist
- **THEN** the report lists them as blockers and no margin or estimated value is published

### Requirement: Versioned printable reports
The system SHALL keep report revisions append-only, viewable in the TON report viewer, printable and downloadable, with version history and a warning when the latest report predates the current normalization run.

#### Scenario: Report older than base
- **WHEN** decisions were applied after the last R3 report
- **THEN** Fechamento flags the report as outdated and offers to generate a new one explicitly
