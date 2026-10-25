## ADDED Requirements

### Requirement: Write only through an approved proposal
The system SHALL write to NG only by applying an action proposal approved by a person with permission, using an operation from a closed, versioned list, and SHALL refuse any other write path, including writes requested directly by the assistant.

#### Scenario: Operation not in the list
- **WHEN** a proposal asks for an NG operation that is not in the approved list
- **THEN** the proposal is refused and nothing is sent to NG

#### Scenario: Write disabled
- **WHEN** the NG write switch is off
- **THEN** proposals that need NG writing can be created but cannot be applied, and reading from NG keeps working

### Requirement: Write audit and read-back verification
Every NG write SHALL record approver, time, value before, value sent and NG response, and SHALL be followed by a read-back of the same record; a read-back that differs from the value sent SHALL open a critical occurrence.

#### Scenario: Read-back differs
- **WHEN** the natureza written was 3.1.0006 and the read-back shows the old natureza
- **THEN** a critical occurrence links the proposal, the write record and the read-back

#### Scenario: NG unreachable after write
- **WHEN** the read-back cannot reach NG
- **THEN** the write stays "não verificada" and is retried, visible in the ledger

### Requirement: No write before written authorization
The system SHALL keep the NG write connector disabled until a written authorization from Vale Norte and a write-enabled NG user are recorded in the configuration.

#### Scenario: Authorization missing
- **WHEN** no authorization record exists
- **THEN** the write connector cannot be enabled in any environment
