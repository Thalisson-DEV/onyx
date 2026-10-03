## ADDED Requirements

### Requirement: Explicit versioned synchronization scope
The system SHALL synchronize only Zeev flow IDs listed in an approved, versioned scope configuration, recording for each flow whether it is current, historical or excluded, and SHALL never synchronize a flow by name match.

#### Scenario: Copy flow not in scope
- **WHEN** flow 150 "Copy of VALE NORTE - Pedido de Liberações Financeiras" is not in the approved scope
- **THEN** no instance of flow 150 is read or stored

### Requirement: Synchronization through immutable snapshots
Each synchronization SHALL store the instances, form values and task records of a flow and time window as a canonical, hashed, immutable `SourceSnapshot` processed by the source pipeline, using only the read-only `ZeevClient`.

#### Scenario: Scheduled sync
- **WHEN** the scheduled sync runs for flow 108
- **THEN** a new snapshot with the window instances is created and processed, and zero mutation calls are sent

### Requirement: Validated incremental capture
Incremental synchronization SHALL combine a date-window read with periodic re-reads of active instances, and SHALL be accepted only after a full backfill of a closed period matches the union of incremental windows for the same period.

#### Scenario: Form edited without task completion
- **WHEN** a form value of an active instance changes without any task finishing
- **THEN** the next active-instance re-read captures the change in a new snapshot

### Requirement: Human-approved field mapping per flow version
Process facts SHALL be produced from form fields only through a human-approved mapping per flow ID and flow version, and a new flow version SHALL put its mapping back to review.

#### Scenario: New flow version deployed
- **WHEN** flow 108 changes version
- **THEN** facts for the new version are not produced until its mapping is reviewed and approved

### Requirement: Process facts used by TON rules
The system SHALL expose payment approval facts (supplier, tax ID, amount, due date, invoice, unit, approvers and approval timestamps) and task cycle-time facts, so that rules can cross NG payments with approved releases and report process SLA, labelling the source as evidence level B.

#### Scenario: Payment without approval
- **WHEN** an NG payment has no matching approved release in the in-scope Zeev flows
- **THEN** the cross-check rule records "pagamento sem aprovação registrada" as a finding for human review, never as misconduct

### Requirement: Personal data and attachments protection
Requester and executor identities SHALL be pseudonymized in snapshots and shown only to authorized roles, and attachments SHALL remain references until an authorized read path exists.

#### Scenario: Attachment field
- **WHEN** a release request has a file field
- **THEN** the system stores the reference and does not download the file
