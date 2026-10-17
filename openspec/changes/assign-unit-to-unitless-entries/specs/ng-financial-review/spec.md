## ADDED Requirements

### Requirement: Assign a unit from the unit-missing case
For a case of the rule NGF-UNIT-MISSING, the system SHALL let a person with occurrence management permission assign an active, visible unit to the case's records, alone or for several selected cases at once. Assigning SHALL record a justified-exception decision on each occurrence that names the unit, so the case leaves the queue and the decision log shows who assigned it.

#### Scenario: Batch of unitless entries
- **WHEN** the controller selects 12 unitless cases and assigns "Mossoró" with a reason
- **THEN** each occurrence gets a decision "Unidade atribuída pela Controladoria: MOSSORÓ-RN", the readiness is recomputed and the 12 cases leave the queue
