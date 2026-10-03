## ADDED Requirements

### Requirement: Read-only registered queries
The NG connector SHALL execute only versioned queries registered in the repository, through a read-only database user, and SHALL NOT execute SQL supplied by users or by the assistant.

#### Scenario: Write attempt
- **WHEN** any code path attempts a statement other than a registered SELECT
- **THEN** the connector refuses it and records an audit event

### Requirement: Query results become immutable snapshots in the existing pipeline
Each ingestion SHALL store the query result as a canonical, hashed, immutable `SourceSnapshot` and process it through a versioned profile that yields the same parsed record shape as the export profile, followed by the existing review, normalization and DRE steps.

#### Scenario: Scheduled ingestion
- **WHEN** the scheduled ingestion runs for the current competence
- **THEN** a new snapshot is created, reviewed and normalized exactly like a manual import

### Requirement: Equivalence before becoming primary
The connector SHALL NOT become the primary NG source until an equivalence report for at least one closed period (counts, sums by natureza and unit, document keys) against the reviewed export has been accepted by the Controladoria.

#### Scenario: Divergent sums
- **WHEN** the database snapshot differs from the reviewed export for June 2026
- **THEN** the report lists the divergences and the source stays in shadow mode

### Requirement: Freshness, failure visibility and manual fallback
The Sources page SHALL show last successful ingestion, next scheduled run and connection failures, and manual import SHALL remain available.

#### Scenario: VPN down
- **WHEN** the connection fails
- **THEN** the source shows "falha de conexão" with time, retries are bounded, and manual import still works

### Requirement: Secrets protection
Connection credentials SHALL be stored encrypted, never logged, never returned by APIs, and never available to the assistant.

#### Scenario: Configuration read
- **WHEN** an administrator opens the connector configuration
- **THEN** the password is masked and cannot be read back
