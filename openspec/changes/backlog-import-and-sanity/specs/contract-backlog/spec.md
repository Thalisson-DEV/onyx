## ADDED Requirements

### Requirement: Backlog import as versioned source
The system SHALL import each backlog version as an immutable snapshot and parse, per item, contracting party, total value, monthly value, remaining term, remaining balance, average monthly margin, projected result and signature status, with lineage.

#### Scenario: Backlog JUL/2026 imported
- **WHEN** the July 2026 backlog is uploaded
- **THEN** each item is parsed with its row of origin and the declared subtotals are kept

### Requirement: Backlog sanity rules
The system SHALL apply to every backlog version S1 (margin within −100% and +60%), S2 (remaining balance equals monthly value times remaining term within 2%), S3 (projected result equals monthly margin times remaining term), S4 (declared subtotals within 0.5%) and S7 (unsigned contracts excluded from backlog, revenue and projection), recording each violation as an occurrence.

#### Scenario: Margin above 60%
- **WHEN** an item declares monthly margin R$ 6.166.244,74 over monthly revenue R$ 3.297.457,08
- **THEN** S1 flags a 187% margin as input error and blocks the use of that margin

#### Scenario: Balance ignoring executed months
- **WHEN** an item declares remaining balance equal to the total contract value while part of the term was executed
- **THEN** S2 flags the difference between the declared balance and monthly value times remaining term

#### Scenario: Contract under judgement
- **WHEN** an item has status "em julgamento"
- **THEN** S7 excludes it from backlog totals and projections

### Requirement: Declared versus sanitized backlog
The system SHALL show the declared backlog and a sanitized backlog side by side, where values failing S1 are blocked, unsigned items are excluded and balances failing S2 are recomputed, and SHALL never overwrite the declared values.

#### Scenario: Sanitized totals
- **WHEN** a user opens the backlog view
- **THEN** both totals are shown with the list of adjustments and the rule behind each one
