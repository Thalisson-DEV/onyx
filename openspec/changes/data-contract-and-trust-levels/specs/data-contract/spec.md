## ADDED Requirements

### Requirement: Canonical base registry
The system SHALL keep a versioned registry of the Prompt Mestre §3.1 canonical bases (lançamentos, cadastro mestre do contrato, dotação, backlog contratual, frota, abastecimento, produção, pessoal, medição e faturamento) with key and minimum fields for each.

#### Scenario: Registry lookup
- **WHEN** a profile declares it feeds the "lançamentos" base
- **THEN** the registry returns key Natureza + Mês + Unidade and minimum fields Natureza Gerencial, Natureza (Grupo), Mês, Unidade, Valor, Histórico

### Requirement: Source conformance check
Each profile execution SHALL be checked against the canonical base it feeds and the snapshot SHALL record CONFORMING or NON_STANDARD with the missing fields; numbers derived from a NON_STANDARD source SHALL carry the label "[fonte não padronizada]" wherever published.

#### Scenario: Missing minimum field
- **WHEN** a production spreadsheet lacks the unit-of-measure column
- **THEN** the snapshot is NON_STANDARD listing "unidade de medida" and every number from it is labelled "[fonte não padronizada]"

### Requirement: Evidence level on every published number
Every fact, finding, impact, report line and assistant statement with a number SHALL carry an evidence level A (documental), B (sistema), C (registro operacional) or D (declaratória) derived from its source type, and the lowest level among its inputs SHALL prevail.

#### Scenario: Mixed sources
- **WHEN** an impact uses an NG amount (B) and a unit manager spreadsheet quantity (C)
- **THEN** the impact is published with level C and the origin caveat

### Requirement: Declaratory information stays hypothesis
Any conclusion depending on a level D input SHALL open with "Hipótese — necessita validação" and SHALL NOT be upgraded to a higher level by repetition or by being recorded by a user.

#### Scenario: Manager statement
- **WHEN** a note records a manager verbal explanation for a revenue drop
- **THEN** reports present it as hypothesis to validate, never as the cause
