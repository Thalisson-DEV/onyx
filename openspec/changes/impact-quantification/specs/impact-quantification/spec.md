## ADDED Requirements

### Requirement: Impact method and reference unit cost order
For occurrences measured in operational quantities, impact SHALL equal the operational difference times a reference unit cost chosen in this order: the contract dotação composition, then the unit realized mean of the last 3 months, then the median of comparable units; the impact record SHALL state which source was used.

#### Scenario: No dotação composition
- **WHEN** a fuel overconsumption occurrence at Toledo-PR has no dotação composition available
- **THEN** the impact uses Toledo-PR realized mean unit cost of the last 3 months and records that source

### Requirement: Direct monetary impacts
For occurrences whose difference is already monetary (duplicate payment, invoice not issued, revenue not recognized), impact SHALL equal that amount with method DIRECT and no unit cost.

#### Scenario: Duplicate payment
- **WHEN** a manager confirms that a T3 candidate is the same invoice paid twice for R$ 10.000,00
- **THEN** the impact is R$ 10.000,00, category "receita recuperável", method DIRECT

### Requirement: Categories and confidence
Each impact SHALL have one of the categories economia potencial, perda evitada, receita recuperável, receita não faturada, custo excedente, risco financeiro or oportunidade de margem, and a confidence Alta (complete A/B data), Média (B/C data with one premise) or Baixa (two or more premises).

#### Scenario: Two premises
- **WHEN** an impact depends on an estimated quantity and a comparable-unit median
- **THEN** its confidence is Baixa

### Requirement: Estimates labelled and excluded when low confidence
Any estimated impact SHALL be published as "Estimativa — premissa: <x>; sensibilidade: ±<y>%", and impacts with confidence Baixa SHALL NOT count toward goals or realized ROI.

#### Scenario: ROI totals
- **WHEN** the ROI register sums identified savings
- **THEN** impacts with confidence Baixa are listed separately and excluded from the totals

### Requirement: Unquantifiable stays explicit
When neither a monetary difference nor a reference cost exists, the occurrence SHALL be published as "não quantificado — falta <insumo>" and SHALL NOT receive an invented value.

#### Scenario: Missing unit cost
- **WHEN** a productivity deviation has no dotação, no unit history and no comparable unit
- **THEN** the impact is "não quantificado — falta custo unitário de referência"
