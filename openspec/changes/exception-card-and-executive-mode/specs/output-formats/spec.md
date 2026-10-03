## ADDED Requirements

### Requirement: Exception card with ten fields
Every published finding SHALL be rendered as an exception card with criticality and one-line title, contract or unit, competence, test code and NC, followed by the ten fields: what happened, evidence (source and level), deviation, probable cause (labelled hypothesis), financial impact (monthly, yearly, confidence, method), risk, recommended action (infinitive verb), responsible, deadline and how to verify.

#### Scenario: Card with missing cause
- **WHEN** a finding has no determined cause
- **THEN** the card shows "Causa provável: não determinada — falta <insumo>" instead of omitting the field

### Requirement: Executive mode
Executive deliveries (executive brief, TON CEO answers) SHALL present each topic in the order RESULTADO, PROBLEMA, IMPACTO, CAUSA, AÇÃO with at most five lines per topic and no raw data dumps.

#### Scenario: Executive brief for June
- **WHEN** the executive brief for June 2026 is generated
- **THEN** each topic has at most five lines in the mandated order

### Requirement: Seven board questions coverage
Every executive delivery SHALL state which of the seven board questions (§19) it answers and, for each unanswered question, which source or capability is missing; a delivery that answers none SHALL NOT be published.

#### Scenario: No contract data
- **WHEN** an executive brief is generated without contract master or production sources
- **THEN** it marks "Estamos executando o que contratamos?" as unanswered due to missing measurement and production sources

### Requirement: No problem without the four essentials
A finding SHALL NOT be published as a problem unless it has estimated impact (or explicit "não quantificado — falta <insumo>"), probable cause (or explicit gap), evidence and recommended action.

#### Scenario: Finding without evidence
- **WHEN** a candidate finding has no evidence records
- **THEN** it is kept in the ledger and not published
