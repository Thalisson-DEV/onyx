## ADDED Requirements

### Requirement: Controller-assigned unit for NG entries without a unit
When an NG entry has no administrative unit and the Controladoria assigned a unit to its record identity, the normalization SHALL use the assigned unit for the actual fact. An assignment SHALL never replace a unit that came from the NG.

#### Scenario: Sticker purchase belongs to the head office
- **WHEN** the Controladoria assigns "Vale Norte matriz" to the January sticker purchase that has no unit in the NG
- **THEN** after the base is recalculated the entry is in the head office DRE and no longer in "Sem unidade no NG"

#### Scenario: NG starts to carry the unit
- **WHEN** a new NG export brings the same entry with its unit filled in
- **THEN** the entry uses the NG unit and the assignment no longer applies

### Requirement: Assignments survive re-imports and keep their history
The system SHALL key an assignment by the content identity of the record (the review record key, without sheet or row) and SHALL keep every assignment as an append-only version with author, time and reason; the latest version per record identity is the one in force, and a version without a unit undoes the assignment.

#### Scenario: Same export imported again
- **WHEN** the same Jan–Set export is imported again
- **THEN** the 29 assigned entries keep their units without a new decision
