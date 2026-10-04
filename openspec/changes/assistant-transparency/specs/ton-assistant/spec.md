## ADDED Requirements

### Requirement: Visible work in business language
The assistant SHALL show, live, each step it takes to answer: the query in business terms, the period and unit by name, and a one-line result summary. Tool codes, identifiers and model-private reasoning text MUST NOT be displayed. Reasoning phases SHALL be named by position only.

#### Scenario: Query running
- **WHEN** TON is reading the persisted DRE of June 2026, consolidated
- **THEN** the panel shows "Lendo o resultado oficial da DRE…", the elapsed time, and the step appears with "Junho de 2026 · Consolidado"

#### Scenario: Answer finished
- **WHEN** the answer text has rendered
- **THEN** the panel folds into one line with duration, number of queries and specialists, and the steps stay one click away

#### Scenario: Query without data
- **WHEN** a query returns nothing or fails
- **THEN** the step says so in business language and the answer continues

### Requirement: Readable query data
Opening a step SHALL show what was read as a table or labelled fields with formatted values; keys without a business label, identifiers and hashes MUST be hidden. Raw payloads SHALL be available only as a copy action for administrators.

#### Scenario: DRE lines read
- **WHEN** the user opens "Resultado da DRE"
- **THEN** a table shows Linha and Realizado in R$ without ids or engine versions

### Requirement: Optional answer details
Below the answer, cards that ask for an action (published report, evidence rows, DRE blockers) SHALL stay visible; sources, specialists and the other result cards SHALL be folded behind a details bar and open one at a time on request.

#### Scenario: Ready DRE
- **WHEN** the analysis finds no blocker
- **THEN** the DRE card sits behind "Resultados" and the answer ends with the details bar and follow-ups

### Requirement: Sources of an answer
The details SHALL list each kind of data consulted, linked to the product page that shows it, and the imported files behind them with import date and acquisition mode.

#### Scenario: No source consulted
- **WHEN** the answer used no TON query
- **THEN** no sources section is shown

### Requirement: Specialists made visible
Each specialist SHALL have its own avatar in the Onyx agent style. The specialists detail SHALL show who worked, the seven protocol steps with their state, the recorded reason of each step not executed, and the recommended actions; specialists waiting for a source SHALL appear muted with their reason.

#### Scenario: Step not executed
- **WHEN** CFO did not run Quantificação
- **THEN** the strip marks the step as not executed and the reason recorded by the backend is shown

### Requirement: Cards state their scope
Result cards SHALL show the period and scope they refer to, and only one readiness card per period and scope SHALL be shown, the latest call winning.

#### Scenario: Two periods queried
- **WHEN** the assistant analysed February and June
- **THEN** each DRE card names its period and they do not read as contradictory
