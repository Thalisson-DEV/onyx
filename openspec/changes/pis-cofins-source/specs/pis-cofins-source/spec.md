## ADDED Requirements

### Requirement: Deterministic PIS/COFINS apportionment import
The system SHALL import the Contabilidade PIS/COFINS apportionment as an immutable snapshot and parse, per competence month, the revenue base and the PIS and COFINS amounts payable, validating that parsed monthly values sum to the document totals.

#### Scenario: Totals do not match
- **WHEN** the parsed monthly PIS values do not sum to the document total
- **THEN** the import is marked failed with a diagnostic and no tax fact is created

### Requirement: Tax facts enter the DRE through an approved assignment
Tax facts SHALL reach the DRE line "Impostos s/ faturamento" only through an approved, versioned account assignment; without it the period shows a readiness item "imposto sem linha aprovada".

#### Scenario: Assignment approved
- **WHEN** the assignment is approved and the DRE is recalculated
- **THEN** June 2026 shows PIS and COFINS payable in Impostos s/ faturamento with the apportionment as source

### Requirement: Revenue base reconciliation
The system SHALL compare, per competence, the apportionment revenue base with the DRE revenue and expose the difference as a reconciliation item labelled as hypothesis until explained.

#### Scenario: Semester difference
- **WHEN** jan–jun/2026 revenue base is R$ 65,91 mi and DRE revenue is R$ 59,03 mi
- **THEN** a reconciliation item shows the difference per month and states it is unexplained until classified

### Requirement: No unit apportionment without source or rule
The system SHALL keep consolidated-only tax facts out of unit DREs unless the source is per unit or the Controladoria approved an apportionment rule.

#### Scenario: Consolidated-only apportionment
- **WHEN** the apportionment has no unit breakdown and no rule exists
- **THEN** unit DREs show taxes as "não rateado" and the consolidated includes them
