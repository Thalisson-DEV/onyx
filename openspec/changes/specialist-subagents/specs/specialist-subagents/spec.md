## ADDED Requirements

### Requirement: Specialist contract and source-derived activation
Each specialist SHALL declare domain, allowed tools, owned rules, characteristic deliverable and required sources, and SHALL be active only when conforming sources of its domain exist and at least one of its rules is operational.

#### Scenario: FROTA activation
- **WHEN** conforming fleet and fuelling sources exist and T22 is operational
- **THEN** FROTA becomes active and its deliverable is available

### Requirement: Coordinator delegation within the protocol
The TON coordinator SHALL delegate analytical questions only to the specialists of the relevant domains, each running inside the seven-step protocol with restricted tools and structured output, and the CEO role SHALL consolidate their outputs.

#### Scenario: Question about fuel and margin
- **WHEN** the user asks why Mossoró margin fell with fuel costs
- **THEN** CFO and FROTA are delegated, and the answer consolidates both outputs

### Requirement: Single registration handoff
A finding that crosses domains SHALL be registered once by the domain of the link where the quantity changed, with other specialists listed as impacted domains, never duplicated in the ledger.

#### Scenario: Billing above production
- **WHEN** CONTRATOS and COO both observe billing above production
- **THEN** one occurrence exists owned by the execution/measurement link domain with the other as impacted

### Requirement: CEO five-line answer
The CEO role SHALL answer "como estão nossos contratos?" in at most five lines in executive mode, stating which contracts lack data.

#### Scenario: Executive question
- **WHEN** the board asks how the contracts are doing
- **THEN** the answer has at most five lines and names contracts without enough data
