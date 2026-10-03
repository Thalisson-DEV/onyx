## ADDED Requirements

### Requirement: Weighted index with fixed weights
The ISC SHALL be the weighted mean of the dimension scores (0–100) with weights Financeiro 20, Faturamento 15, Operacional 15, Frota 12, Consumo 10, Pessoas 10, Compliance 10 and Risco contratual 8, each dimension computed by an approved formula over its §14.3 basis.

#### Scenario: All dimensions available
- **WHEN** all eight dimensions have data for a contract
- **THEN** the ISC uses the fixed weights without redistribution

### Requirement: Not-evaluated dimensions
A dimension without data SHALL be reported as "não avaliada", its weight SHALL be redistributed proportionally among evaluated dimensions, and the ISC SHALL carry a caveat listing the missing dimensions.

#### Scenario: Only financial data
- **WHEN** only the Financeiro dimension has data
- **THEN** the ISC is shown with the caveat that seven dimensions were not evaluated

### Requirement: Loss concentration reading
Every ISC publication SHALL state where the potential margin loss is concentrated, naming the dimension with the largest weighted loss and its related occurrences.

#### Scenario: Loss in fleet
- **WHEN** the Frota dimension has the largest weighted loss
- **THEN** the reading names Frota and links its occurrences
