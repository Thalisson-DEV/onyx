## ADDED Requirements

### Requirement: Single PAD-CTRL-001 criticality scale
The system SHALL classify each occurrence as CRITICAL (impact ≥ 1% of the unit gross revenue of the month, or of the consolidated gross revenue for corporate findings), HIGH (0.3% to 1%, or the same error recurring for 2 months), MEDIUM (0.1% to 0.3%, or an isolated classification failure without consolidated effect) or MONITORING (no material impact, unfavourable trend), and SHALL NOT use any other scale.

#### Scenario: Impact of 1.2% of unit revenue
- **WHEN** an occurrence at Toledo-PR has a quantified impact equal to 1.2% of Toledo-PR gross revenue of the month
- **THEN** it is classified CRITICAL

#### Scenario: Unit without revenue in the month
- **WHEN** the unit has zero gross revenue in the month
- **THEN** the percentage criterion is not applied and the occurrence requires a human criticality decision

### Requirement: Qualitative critical criteria are human decisions
Classifying an occurrence as CRITICAL for invalidating a unit reading or for material tax or labour risk SHALL be a recorded human decision with justification.

#### Scenario: Revenue swapped between units
- **WHEN** a Controladoria user marks a revenue swap as invalidating the April reading of three units
- **THEN** the occurrences become CRITICAL with the author and justification recorded

### Requirement: Default deadlines from criticality
The system SHALL set the default deadline from the scale (CRITICAL up to 5 business days, HIGH 15 days, MEDIUM 30 days, MONITORING next cycle) using the confirmed business calendar.

#### Scenario: High occurrence assigned
- **WHEN** a HIGH occurrence is assigned on 2026-10-05
- **THEN** the default deadline is 15 days later

### Requirement: Automatic cycle escalation
At each competence closing, an occurrence classified HIGH and open for two consecutive cycles SHALL be reclassified CRITICAL in the third, recording the responsible person of the pending item.

#### Scenario: Third cycle open
- **WHEN** a HIGH occurrence is still open at the third closing
- **THEN** it becomes CRITICAL and the escalation event names the responsible person

### Requirement: NC catalogue from PAD-CTRL-001
NC codes SHALL come from a catalogue loaded from the PAD-CTRL-001 document; until it is loaded, codes cited in the Prompt Mestre SHALL be shown with "descrição pendente do PAD-CTRL-001".

#### Scenario: Catalogue not loaded
- **WHEN** an occurrence carries NC-07 and the catalogue is not loaded
- **THEN** the UI shows NC-07 with the pending-description label
