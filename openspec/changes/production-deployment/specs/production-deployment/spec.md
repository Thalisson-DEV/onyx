## ADDED Requirements

### Requirement: Reproducible production build
Production images SHALL be built from the repository by a documented pipeline with migrations applied in a controlled step, and production SHALL NOT receive code by container copy or pull upstream onyx-backend/onyx-web-server images.

#### Scenario: New release
- **WHEN** a release is deployed
- **THEN** the running images match a repository commit and migrations ran once before traffic

### Requirement: Backups with restore test
The production database and file store SHALL be backed up automatically with a documented retention, and a restore SHALL be tested at least once per month.

#### Scenario: Monthly restore test
- **WHEN** the monthly restore test runs
- **THEN** a restored copy passes a smoke check of DRE and sources and the result is recorded

### Requirement: Role-based access for the client team
Production SHALL provide roles admin, controladoria, gestor and leitura with unit and contract scoping, and client users SHALL have only the rights of their role.

#### Scenario: Unit manager
- **WHEN** a gestor of Toledo-PR signs in
- **THEN** they see only Toledo-PR data and cannot record financial decisions

### Requirement: Network route to NG from the TON host
The production host SHALL reach the NG database through the client VPN, and connector traffic SHALL originate from the host, not from personal machines.

#### Scenario: Scheduled ingestion in production
- **WHEN** the NG ingestion runs in production
- **THEN** it connects from the production host through the VPN

### Requirement: Approved retention policy
Sources, evidence, reports and personal data SHALL follow an approved retention policy applied by scheduled jobs and recorded in audit.

#### Scenario: Personal data past retention
- **WHEN** payroll personal data exceeds its retention period
- **THEN** it is purged or anonymized by the scheduled job and the action is audited
