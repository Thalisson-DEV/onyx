## ADDED Requirements

### Requirement: Declarative versioned routine definitions
Each routine R1–R9 SHALL be a versioned definition with trigger (cron, business day relative to competence close D+n, or source event), scope, publication threshold, nominal recipient roles and silence rule, and SHALL execute through the seven-step protocol.

#### Scenario: Routine without confirmed calendar
- **WHEN** a D+n routine is enabled without a confirmed business calendar
- **THEN** the routine is not activated and Automações explains the missing calendar

### Requirement: Silence below threshold
A routine run whose results are below its publication threshold SHALL publish nothing and SHALL record the run as silent with the reason.

#### Scenario: R1 with only medium findings
- **WHEN** R1 runs and finds only MEDIUM occurrences
- **THEN** nothing is published and the run is recorded as silent "nenhuma ocorrência alta ou crítica"

### Requirement: R1 daily exception scan
R1 SHALL run daily at 06:00 over the previous day data for the implemented T13–T26 tests and publish to Controladoria a summary of at most 7 lines when at least one HIGH or CRITICAL occurrence exists.

#### Scenario: Two critical items
- **WHEN** R1 detects two CRITICAL occurrences
- **THEN** Controladoria receives a summary with at most 7 lines including both

### Requirement: R6 executive package
R6 SHALL run monthly on D+9 and always publish the executive package in executive mode as input for the PAD-CTRL-001 board presentation.

#### Scenario: Monthly package
- **WHEN** D+9 of the September competence arrives
- **THEN** the executive package is published to Controladoria

### Requirement: Delivery to recipients
Published routine outputs SHALL be delivered in-app and by e-mail to users resolved from the recipient roles at delivery time, and delivery failures SHALL be visible in Automações.

#### Scenario: SMTP failure
- **WHEN** e-mail delivery fails
- **THEN** the in-app notification is kept and Automações shows the failed delivery

### Requirement: Idempotent runs
Each routine run SHALL be idempotent per routine version and competence or window, so retries never publish twice.

#### Scenario: Worker retry
- **WHEN** a worker retries a completed R6 run
- **THEN** no second publication is created
