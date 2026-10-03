## ADDED Requirements

### Requirement: Sanity rules run in step 2 as versioned deterministic rules
Each sanity rule S1–S10 SHALL be a versioned `Rule` with a deterministic executor run in the Validação da base step; a rule without its required data SHALL report "não avaliada — falta <fonte>" instead of passing.

#### Scenario: S2 without backlog
- **WHEN** step 2 runs and no backlog source exists
- **THEN** S2 is reported as not evaluated because the backlog source is missing

### Requirement: S5 units equal consolidated
S5 SHALL verify that the sum of all unit amounts (including "sem unidade") equals the consolidated amount to the cent for every DRE line and period, and any divergence SHALL be critical.

#### Scenario: Missing unit in consolidation
- **WHEN** the consolidated revenue differs from the sum of unit revenues by R$ 0,01 or more
- **THEN** a critical S5 finding names the line, period and difference, and margin publication is blocked

### Requirement: S6 sign by natureza
S6 SHALL flag every fact whose sign contradicts the approved sign of its natureza (revenue negative or expense positive) as NC-03, using only approved natureza sign decisions.

#### Scenario: Positive expense
- **WHEN** a COMBUSTÍVEIS fact is positive and the approved sign is negative
- **THEN** an S6 finding with NC-03 is recorded with the fact evidence

### Requirement: S8 vertical analysis base
S8 SHALL compute AV% of each line only over the gross revenue of the same unit and period, and SHALL refuse to publish AV% when that revenue is zero or the unit is non-operational.

#### Scenario: Unit without revenue
- **WHEN** Administração Central has no gross revenue
- **THEN** AV% is not published for it and the reason is shown

### Requirement: S4 declared subtotals
S4 SHALL verify, for any imported source that declares subtotals, that the sum of its lines equals the declared subtotal within 0.5%, and flag divergence as a source integrity finding.

#### Scenario: Backlog subtotal
- **WHEN** the declared backlog balance subtotal differs from the sum of item balances by more than 0.5%
- **THEN** an S4 finding names the subtotal and the computed sum

### Requirement: Calibration cases as regression tests
The project SHALL keep synthetic fixtures that reproduce each Prompt Mestre §6.2 calibration pattern available to the implemented rules (revenue swapped between units, single-month non-recurring tax agreement, fuel collapse versus prior average) and the battery SHALL detect each one.

#### Scenario: Calibration suite
- **WHEN** the sanity and financial test suites run
- **THEN** each calibration pattern produces the expected finding code
