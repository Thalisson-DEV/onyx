## ADDED Requirements

### Requirement: Tests run per competence with PAD-CTRL codes
The system SHALL run the implemented T1–T12 tests over canonical facts of each competence in the Detecção step, recording each trigger as an occurrence carrying the test code, its NC code(s) from the Prompt Mestre §7, the evidence records and the owning domain, without renaming codes.

#### Scenario: Re-run of the same competence
- **WHEN** the battery runs twice for June 2026 with the same inputs
- **THEN** each trigger maps to the same occurrence identity and no duplicate occurrence is created

### Requirement: Approved versioned parameters
Thresholds and lists (T2 window 3 months and 15%, T4 1%, T9 30 days and 5%, T10 5%, contractual groups for T1, related parties for T11) SHALL be read from an approved rule version; changing a parameter SHALL create a new rule version.

#### Scenario: Threshold change
- **WHEN** the Controladoria approves T2 at 20% instead of 15%
- **THEN** a new T2 version is active and occurrences detected under the old version are superseded on recurrence

### Requirement: T10 non-recurring event
T10 SHALL flag every single fact whose absolute amount exceeds 5% of the total expense of the same competence and scope, requiring a technical note.

#### Scenario: Tax agreement balance in April
- **WHEN** April 2026 contains a Parcelamentos fact larger than 5% of April total expense
- **THEN** a T10 occurrence (NC-03/12) is recorded asking for a technical note

### Requirement: T2 moving-average deviation
T2 SHALL compare each group amount of a unit with the mean of the same group in the three previous competences of that unit and flag deviations above the approved threshold; with fewer than three previous competences it SHALL report "não avaliado — histórico insuficiente".

#### Scenario: Fuel collapse with incomplete window
- **WHEN** the base starts in January 2026 and T2 evaluates Mossoró-RN fuel for March
- **THEN** March is reported as not evaluated (only two prior months) and April is evaluated against the January–March mean

### Requirement: T4 revenue NF versus NG per unit
T4 SHALL compare, per operational unit and competence, revenue in NG with issued invoices mapped to that unit and flag differences above 1%; invoices without an approved unit mapping SHALL be reported as a blind spot, not as a difference.

#### Scenario: Invoices without unit mapping
- **WHEN** billing has invoices whose payer has no approved unit mapping
- **THEN** T4 reports them as "nota sem unidade correspondente" and evaluates only mapped units

### Requirement: Tests without required fields are not evaluated
A test whose required fields are absent from the sources (for example supplier tax ID for T8) SHALL be reported as not evaluated with the missing field, and its coverage status SHALL stay BLOCKED.

#### Scenario: NG without supplier tax ID
- **WHEN** the NG export has no supplier CNPJ
- **THEN** T8 is reported as not evaluated because "CNPJ do fornecedor" is missing
