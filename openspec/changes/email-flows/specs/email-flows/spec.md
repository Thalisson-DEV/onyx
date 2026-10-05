## ADDED Requirements

### Requirement: Flow definition with one yes/no branch
A flow SHALL consist of one trigger, an optional condition and an action for the "yes" branch, with an optional action for the "no" branch; triggers, condition fields, operators, actions and e-mail templates SHALL come from closed catalogs, and every edit SHALL create a new immutable version.

#### Scenario: Business user registers a flow
- **WHEN** a Controladoria user with report management permission creates "Quando a importação do NG terminar, se houver duplicidade na unidade Toledo-PR, enviar e-mail ao Financeiro"
- **THEN** the flow is saved as version 1, active, and the change appears in the audit trail

#### Scenario: Invalid field for the trigger
- **WHEN** a condition references a field the selected trigger does not expose
- **THEN** the flow is rejected with a message naming the field and nothing is saved

#### Scenario: Condition false without "no" action
- **WHEN** the condition evaluates false and the flow has no "no" action
- **THEN** the run is recorded as silent with the reason and nothing is sent

### Requirement: TON-suggested flows need human approval
The assistant SHALL be able to propose a flow definition built only from catalog items, which SHALL be stored as "Sugerido pelo TON" with its reason and SHALL NOT run until a user with permission registers it; e-mail content SHALL never be written by the LLM.

#### Scenario: Suggestion registered
- **WHEN** the user clicks "Cadastrar" on a suggestion
- **THEN** the flow becomes active with the user recorded as approver

#### Scenario: Suggestion discarded
- **WHEN** the user clicks "Descartar"
- **THEN** the flow never runs and the discard is audited with user and time

### Requirement: Default weekly inconsistency flow
The system SHALL provide "Inconsistências da semana" as the first flow, seeded as a suggestion, which at the configured schedule (weekly by default) reports open NG inconsistencies with rule, evidence (sheet and row or database record, account, unit, document, amount), the correction expected in the NG and weeks open, grouped by unit and readable on a phone.

#### Scenario: Weekly report with open items
- **WHEN** the weekly run happens and the 392 duplicate is still open
- **THEN** the e-mail lists it with both documents, unit Toledo-PR, the amounts, "corrigir no NG" and its weeks open

#### Scenario: Nothing open
- **WHEN** no inconsistency is open
- **THEN** the run follows the "no" branch and the TON shows "nenhuma inconsistência aberta" with the last extraction checked

### Requirement: Correction check on each new extraction
On each new NG extraction the system SHALL mark each inconsistency as corrected, still open or reappeared, per competence month, and SHALL never claim a correction for a month the extraction did not cover.

#### Scenario: Corrected in the NG
- **WHEN** a new extraction of February no longer contains the duplicated 392 row
- **THEN** the item is marked "corrigida no NG" with the extraction date and leaves the next report

#### Scenario: Retroactive correction undone
- **WHEN** an item marked corrected appears again in a later full extraction
- **THEN** it is marked "reapareceu" and returns to the report

#### Scenario: Ambiguous correspondence
- **WHEN** the verification is inconclusive
- **THEN** the item stays open with the note "conferir à mão"

### Requirement: Idempotent runs and delivery history
Each run SHALL be idempotent per flow version and event key (schedule window or source event), and every delivery SHALL be recorded with recipients, rendered content, status and error.

#### Scenario: Worker retry
- **WHEN** a worker retries the weekly run of week 2026-W41
- **THEN** no second e-mail is sent

#### Scenario: Provider not configured
- **WHEN** a flow runs and no e-mail provider is configured in the environment
- **THEN** the delivery is recorded as "e-mail não configurado" and its content stays visible in TON

#### Scenario: Provider failure
- **WHEN** e-mail delivery fails
- **THEN** the delivery is marked failed with the error and the flow history shows it

### Requirement: Configurable provider and grouped recipients
E-mail SHALL be sent through the provider chosen by environment (Resend or SMTP); each run SHALL send one message with all To, Cc and Bcc recipients together, split into recorded batches only when the provider's per-message recipient limit is exceeded.

#### Scenario: Several recipients
- **WHEN** the weekly flow has three Financeiro addresses in To and Luyla in Cc
- **THEN** exactly one message is sent and the history shows one line with the four recipients

#### Scenario: Above the provider limit
- **WHEN** a flow has 60 recipients and the provider accepts 50 per message
- **THEN** two messages are sent and the history records "lote 1 de 2" and "lote 2 de 2"

### Requirement: Test mode
A user SHALL be able to preview the e-mail a flow would send with current data, and to send it only to themselves, without consuming the schedule window.

#### Scenario: Send only to me
- **WHEN** the user clicks "Enviar só para mim" on the weekly flow
- **THEN** only the user receives the e-mail, the delivery is marked as test and the next scheduled run still happens

### Requirement: TON never corrects the NG
Flows, reports and the correction check SHALL only read NG data and SHALL NOT write to the NG or alter source files.

#### Scenario: Correction pending
- **WHEN** an inconsistency stays open for weeks
- **THEN** TON keeps reporting it and does not change any NG record
