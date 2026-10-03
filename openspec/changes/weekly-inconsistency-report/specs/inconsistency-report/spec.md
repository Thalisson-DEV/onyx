## ADDED Requirements

### Requirement: Periodic inconsistency report
The system SHALL produce, at the configured frequency (weekly by default), a report of open NG inconsistencies listing for each one the rule, evidence (sheet and row or database record, account, unit, document, amount), the correction expected in the NG and the number of weeks it has been open.

#### Scenario: Weekly report with open items
- **WHEN** the weekly run happens and the 392 duplicate is still open
- **THEN** the report lists it with both documents, unit Toledo-PR, the amounts, "corrigir no NG" and its weeks open

#### Scenario: Nothing open
- **WHEN** no inconsistency is open
- **THEN** the report states "nenhuma inconsistência aberta" and the last extraction checked

### Requirement: E-mail delivery to configured recipients
The report SHALL be sent by e-mail to the configured Financeiro recipients with copy to Controladoria, and SHALL also be available inside TON; delivery failures SHALL be visible to administrators.

#### Scenario: SMTP unavailable
- **WHEN** e-mail delivery fails
- **THEN** the report remains available in TON and the administration shows the failed delivery

### Requirement: Administrable rules, frequency and recipients
A TON administrator SHALL be able to choose which rules enter the report, the frequency and the recipients, with every change audited.

#### Scenario: Frequency changed
- **WHEN** the administrator changes the frequency from weekly to every two days
- **THEN** the next runs follow the new frequency and the change appears in the audit trail

### Requirement: Correction check on each new extraction
On each new NG extraction the system SHALL mark each reported inconsistency as corrected, still open or reappeared, per competence month, and SHALL never claim a correction for a month the extraction did not cover.

#### Scenario: Corrected in the NG
- **WHEN** a new extraction of February no longer contains the duplicated 392 row
- **THEN** the item is marked "corrigida no NG" with the extraction date and leaves the next report

#### Scenario: Retroactive correction undone
- **WHEN** an item marked corrected appears again in a later full extraction
- **THEN** it is marked "reapareceu" and returns to the report

### Requirement: TON never corrects the NG
The report and the correction check SHALL only read NG data and SHALL NOT write to the NG or alter source files.

#### Scenario: Correction pending
- **WHEN** an inconsistency stays open for weeks
- **THEN** TON keeps reporting it and does not change any NG record
