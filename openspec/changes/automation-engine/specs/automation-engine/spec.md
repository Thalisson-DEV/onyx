## ADDED Requirements

### Requirement: Automation definition built from a node catalog
An automation SHALL consist of one trigger, declared variables, a tree of nodes and settings, where every node type SHALL come from the code catalog and every edit SHALL append an immutable version.

#### Scenario: Unknown node type
- **WHEN** a definition contains a node type that is not in the catalog
- **THEN** the save is rejected with the node id and nothing is stored

#### Scenario: Reference to a later step
- **WHEN** a parameter references `steps.x` where `x` does not run before the node
- **THEN** the checker reports an error on that node and activation is blocked

### Requirement: Automation types gate activation
Each automation SHALL have a type (EMAIL, ALERT, ROUTINE, APPROVAL, DATA_AI, GENERAL) and activation SHALL be blocked when the definition lacks the node the type needs.

#### Scenario: E-mail automation without e-mail step
- **WHEN** a user activates an automation of type EMAIL that has no `email.send` node
- **THEN** activation fails with "A automação de e-mail não envia nenhum e-mail"

### Requirement: Durable step-by-step execution
The engine SHALL persist every node execution with inputs, outputs, status, attempts and duration, SHALL resume a run from the persisted steps after a worker failure, and SHALL never repeat an external side effect that may have happened.

#### Scenario: Worker stops in the middle of a run
- **WHEN** the worker stops after step 3 of 6 and the lease expires
- **THEN** the next tick queues the run again and steps 1–3 are reused, not executed again

#### Scenario: Worker stops while sending an e-mail
- **WHEN** a run is found with an `email.send` step still RUNNING
- **THEN** the step is marked failed as interrupted and the e-mail is not sent again

### Requirement: Retries and failure handling
Each node SHALL support a retry policy (none, fixed, exponential) and a run-after setting (succeeded, failed, skipped, timed out) relative to the previous node, and scopes SHALL report failure of their content so a following node can handle it.

#### Scenario: Transient HTTP error
- **WHEN** an HTTP node fails with status 503 and has 3 exponential retries
- **THEN** the run waits and retries, and the step history shows each attempt

#### Scenario: Try/catch
- **WHEN** a node inside scope "Tentar" fails and scope "Tratar" runs after "failed"
- **THEN** "Tratar" runs and the run ends as succeeded

### Requirement: Data and AI in the middle of a flow
Users SHALL be able to inject structured (JSON, CSV, spreadsheet) and unstructured (text) data at any step, and AI nodes SHALL take previous outputs as input and expose text or structured fields to later nodes; AI output SHALL be labeled as AI-generated.

#### Scenario: Extract fields from pasted text
- **WHEN** an `ai.extract` node receives the text of a "Inserir dados" node with fields `fornecedor` and `valor`
- **THEN** later nodes can use `{{ steps.extrair.outputs.fields.valor }}`

#### Scenario: LLM not available
- **WHEN** no LLM provider is configured
- **THEN** the AI node fails with a clear message and the failure handling of the flow applies

### Requirement: Human control
Automations drafted by the assistant SHALL be saved as drafts and SHALL NOT run until a person with management permission activates them; runs SHALL read data with the owner's visibility.

#### Scenario: Draft from the chat
- **WHEN** the user asks in the chat "toda segunda me mande as inconsistências abertas"
- **THEN** a DRAFT automation is created, the chat shows its steps and what is missing, and nothing runs

#### Scenario: Owner lost access
- **WHEN** the owner of an active automation is deactivated
- **THEN** the next trigger records a failed run with the reason and sends nothing

### Requirement: Email flows become automations
Existing e-mail flows SHALL be converted into automations of type EMAIL with the same trigger, conditions, recipients and e-mail body, and the v2 engine SHALL stop running.

#### Scenario: Weekly inconsistency flow
- **WHEN** the system starts with the seeded weekly flow
- **THEN** an EMAIL automation exists with a weekly Monday 08:00 trigger, an inconsistency query, a condition and the same e-mail
