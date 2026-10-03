## ADDED Requirements

### Requirement: Opportunity ledger
The system SHALL list opportunities with description, contract, cause, monthly and yearly impact, confidence, category, responsible, action, deadline, status, predicted saving, realized saving and verification date.

#### Scenario: Opportunity without verification
- **WHEN** an opportunity has a predicted saving and no verification
- **THEN** its realized saving is empty and its status is not "realizada"

### Requirement: Hidden Money panel
The Hidden Money panel SHALL list opportunities ordered by monthly impact descending with contract, monthly and yearly impact, confidence, responsible, deadline and status, ending with the total identified and the portion verified as realized.

#### Scenario: Panel totals
- **WHEN** the panel is opened
- **THEN** it shows total identified and total realized separately, excluding confidence Baixa from both totals

### Requirement: R5 monthly publication
R5 SHALL run monthly on D+4 and always publish the panel to the Gerência Geral.

#### Scenario: No opportunities
- **WHEN** no opportunity exists
- **THEN** R5 publishes the panel stating zero identified and the reasons (missing quantified rules or sources)

### Requirement: Intelligence ROI register
The ROI register SHALL show, for the fiscal year, identified saving, recovered revenue, avoided cost, system cost and net ROI, counting as realized only impacts verified against the following cycle base.

#### Scenario: Declared saving
- **WHEN** a manager declares a saving that is not verified
- **THEN** it appears as predicted and does not enter realized ROI
