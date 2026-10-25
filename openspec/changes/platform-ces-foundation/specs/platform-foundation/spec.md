## ADDED Requirements

### Requirement: Recorded stack decision before migration
The project SHALL record the platform stack decision, its criteria and the alternatives considered before any module is migrated or rebuilt on another stack.

#### Scenario: Migration without decision
- **WHEN** a change proposes moving TON code to another stack and no decision record exists
- **THEN** the change is blocked until the decision is recorded

### Requirement: Change history on every business record
Every business record of the platform modules SHALL keep an append-only timeline of creation, approvals, edits and deliveries with author, time and before × after values.

#### Scenario: Record edited
- **WHEN** a unit manager changes the quantity of a material request after approval
- **THEN** the timeline shows the original value, the new value, who changed it and when

### Requirement: Requests with approval
The platform SHALL support requests (fuel, payment, material) that go to an approver by rule, can be approved, reduced or refused with a reason, and keep the decision in the timeline.

#### Scenario: Approver reduces the amount
- **WHEN** an approver reduces a fuel request from 100 to 60 litres
- **THEN** the request is approved for 60 litres with the reason and the requester is notified

### Requirement: Controller announcements
The Controladoria SHALL be able to publish announcements with image, PDF or video attachments to chosen users, shown on their next access, with read confirmation.

#### Scenario: User has not read
- **WHEN** an announcement is published to unit managers
- **THEN** the Controladoria sees who has and has not read it

### Requirement: Unused fork parts removed safely
Removal of Onyx parts the TON does not use SHALL happen in stages, each keeping the TON test suites green and the homolog working.

#### Scenario: Removed part still referenced
- **WHEN** a removal stage breaks a TON import or test
- **THEN** the stage is not merged
