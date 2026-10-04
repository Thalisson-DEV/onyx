## ADDED Requirements

### Requirement: Editable classification table
TON administrators SHALL see and edit, in a spreadsheet-like grid, every NG account code with description, natureza, DRE group, origin (controller workbook, rule, manual decision), author and date; each edit SHALL require a justification and be stored as a new mapping version.

#### Scenario: Reclassify an account
- **WHEN** the Controladoria changes 9.8.0001 from DESPESAS DIVERSAS to another natureza with a justification
- **THEN** a new mapping version is stored, the previous one stays in history, and affected periods show "recalcular"

### Requirement: Spreadsheet import and export
The system SHALL export the classification table to Excel and import an edited table as a batch of proposed changes that a user reviews and confirms before they take effect.

#### Scenario: Imported table with changes
- **WHEN** an Excel with five changed rows is imported
- **THEN** the five changes appear as proposals and nothing changes until a user confirms them

### Requirement: New accounts are flagged
When an import contains an NG account code without classification, the system SHALL create a "classificação pendente" item and include it in the weekly inconsistency report.

#### Scenario: New code in July
- **WHEN** the July NG import contains a code never seen before
- **THEN** a pending classification item lists the code, description, unit and amounts

### Requirement: Controller-defined pre-classification rules
The system SHALL apply deterministic, versioned pre-classification rules written by the Controladoria (code prefix or description term to natureza) only as suggestions, and SHALL NOT let similarity or language models decide a classification.

#### Scenario: Rule suggestion
- **WHEN** a new code 3.1.0021 matches the rule "prefixo 3.1 → FOLHA"
- **THEN** the item shows the suggestion FOLHA with the rule name and waits for confirmation

### Requirement: Assistant pre-classification is advice only
The system SHALL let a TON administrator ask the assistant to pre-classify every unconfirmed code, giving it the confirmed codes, the prefix pattern and entry histories, and SHALL store each answer as a suggestion with natureza, confidence and rationale that changes nothing until a person confirms or changes the classification.

#### Scenario: Suggestion disagrees with the analogy
- **WHEN** the assistant suggests MOVIMENTOS NÃO GERENCIAIS for a code classified by analogy as DESPESAS DIVERSAS
- **THEN** the row shows "Sugestão diferente" with the rationale, and the natureza stays DESPESAS DIVERSAS until the Controladoria saves a change with justification

### Requirement: Unconfirmed analogical classifications are visible
The 29 codes classified by analogy SHALL be marked "aguardando confirmação da Controladoria" until confirmed or changed.

#### Scenario: Filter unconfirmed
- **WHEN** the administrator filters by "aguardando confirmação"
- **THEN** the 29 codes are listed with the reason used for each
