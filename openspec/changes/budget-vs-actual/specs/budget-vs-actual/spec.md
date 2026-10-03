## ADDED Requirements

### Requirement: Budget enters only after explicit sign, calendar and mapping decisions
A dotação version SHALL contribute budget facts to a unit DRE only after versioned human decisions on sign convention, period calendar and line-to-DRE mapping exist for it; the system SHALL NOT divide annual values by 12, infer months from file names, or map lines by similarity.

#### Scenario: Calendar not decided
- **WHEN** Mossoró-RN dotação has mapping and sign but no calendar decision
- **THEN** Mossoró-RN shows a readiness item "calendário da dotação não definido" and Orçado stays out of the DRE

### Requirement: Budget versus actual statement
For units with an approved dotação, the DRE SHALL show Orçado, Realizado, absolute variance and percent variance per line and period, with percent variance null when Orçado is zero.

#### Scenario: Approved dotação
- **WHEN** Juazeiro-BA dotação is approved and the DRE is recalculated
- **THEN** each Juazeiro-BA line shows Orçado, Realizado and variances for the period

### Requirement: Units without dotação are explicit
Units without an approved dotação SHALL be labelled "sem orçado" in DRE views and exports instead of showing zero budget.

#### Scenario: Toledo-PR without dotação
- **WHEN** a user opens Toledo-PR
- **THEN** the Orçado column says "sem orçado" and no variance is computed

### Requirement: Outdated dotação signal
The system SHALL flag a dotação as outdated when its data-base precedes an approved staleness limit or a recorded reajuste/CCT date for the unit.

#### Scenario: Old data-base
- **WHEN** Itabirito-MG dotação has data-base 17/10/2025 and the approved limit is exceeded
- **THEN** the unit shows "dotação desatualizada" with its data-base
