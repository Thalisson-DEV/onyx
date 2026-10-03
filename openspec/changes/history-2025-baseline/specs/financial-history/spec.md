## ADDED Requirements

### Requirement: Multi-year history through the same pipeline
The system SHALL ingest prior-year NG exports through the same source, review, normalization and DRE pipeline, with mappings carrying a validity period so that account or natureza changes between years are explicit versioned decisions.

#### Scenario: Account renamed in 2026
- **WHEN** an NG code used in 2025 maps to a different natureza in 2026
- **THEN** each year uses the mapping valid for its competence and the change is visible in the decision log

### Requirement: Year-over-year comparison
The DRE SHALL offer same-month and year-to-date comparison against the prior year for units with coverage in both years, and SHALL state "sem histórico comparável" otherwise.

#### Scenario: Unit opened in 2026
- **WHEN** a unit has no 2025 actuals
- **THEN** the comparison column says "sem histórico comparável" and no variance is shown

### Requirement: Historical coverage indicator
The system SHALL expose, per unit, the number of closed competences available, and rules or forecasts that require a minimum history SHALL read this indicator before running.

#### Scenario: Forecast with five closed months
- **WHEN** a unit has five closed competences
- **THEN** forecast is reported as unavailable because the minimum of six is not met
