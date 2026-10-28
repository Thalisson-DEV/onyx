## ADDED Requirements

### Requirement: Payable title entered by the unit
The system SHALL let a unit user enter one payable title per document installment with: unit (from the user), supplier from the registry, document type and number, issue date, competência, due date, installment "x of y" with the purchase total, title amount, natureza, destination (registered vehicle, site, stock or administration), description and the Zeev request number when there is one.

#### Scenario: Supplier not registered
- **WHEN** a unit user enters a title for a tax ID that is not in the supplier registry
- **THEN** the title is saved as waiting for supplier approval and is not released for payment

#### Scenario: Missing mandatory field
- **WHEN** a title lacks competência or document number
- **THEN** the title is refused with the missing field named

### Requirement: Mandatory attachments
Every non-estimate title SHALL carry its supporting documents (invoice and boleto, or receipt); the system SHALL compare amount and tax ID read from the attachment with the title when the attachment is machine-readable, and SHALL mark the title for human conference otherwise.

#### Scenario: Attachment amount differs
- **WHEN** the boleto reads R$ 791,40 and the title says R$ 1.582,80
- **THEN** a conference finding names both amounts and the title cannot be released until resolved

#### Scenario: No attachment
- **WHEN** a title is sent without any attachment
- **THEN** it stays in "aguardando anexo" and is listed to the unit

### Requirement: Estimates kept apart from real titles
The system SHALL record estimates (for example the fuel of a fortnight) as a separate title type that never counts as a real payable, SHALL replace an estimate with the real title when the invoice arrives, and SHALL flag an estimate whose period ended without a real title.

#### Scenario: Estimate without invoice
- **WHEN** the fuel estimate for 01–15/10 has no real title after its period ends plus the approved tolerance
- **THEN** an alert is raised to the unit and the Controladoria

### Requirement: Finance workflow with history
Titles SHALL move through received → conferred → released → booked in NG → paid, each transition recording who, when and why; payment status SHALL come from the NG settlement or a reconciled bank statement and SHALL NOT be typed by the unit.

#### Scenario: Paid status without NG data
- **WHEN** no NG settlement or reconciled statement exists for a released title
- **THEN** the title stays "liberado" and is not shown as paid

### Requirement: Deterministic payable checks
The system SHALL flag: the same document and installment sent twice; a payee different from the registered supplier; one bank account used by different payees; a new supplier whose name resembles a registered one with a different tax ID; a title sent within the approved notice window before its due date; titles in NG without a unit title and unit titles without an NG entry.

#### Scenario: Duplicate installment across weeks
- **WHEN** NF 38371 installment 3/3 was already sent and is sent again
- **THEN** a duplicate finding links both titles and the second cannot be released without a human decision

#### Scenario: NG data absent
- **WHEN** no NG snapshot covers the period
- **THEN** the TON × NG comparison is not evaluated and states the missing source

### Requirement: Reconciliation with Zeev payment requests
The system SHALL read the Zeev payment request flows in scope and reconcile them with unit titles by Zeev request number, or by supplier, document and amount when the number is absent, recording requests without a title, titles without a request, and differences in amount, supplier, due date or approval.

#### Scenario: Request approved in Zeev without a unit title
- **WHEN** a Zeev payment request is approved and no unit title matches it
- **THEN** a reconciliation item lists the request for the unit and the finance team

#### Scenario: Zeev sync stale
- **WHEN** the last Zeev synchronization is older than the approved freshness
- **THEN** the reconciliation is shown as outdated and no "sem pedido" finding is raised

### Requirement: DRE use by competência and by payment
The economic DRE SHALL take unit titles by competência and the cash DRE SHALL take only paid titles by payment date, without double counting entries that already come from NG for the same document.

#### Scenario: Title also in NG
- **WHEN** a unit title and an NG entry share supplier, document and installment
- **THEN** the DRE counts the amount once and shows both origins in the line composition

### Requirement: Reading notes that are not XML
The system SHALL read a DANFE PDF from its access key without a model, and SHALL send an NFS-e PDF, a scanned PDF or a photo to a model only for transcription, validating every value it returns and marking the reading as AI so a person confirms it.

#### Scenario: DANFE in PDF
- **WHEN** a unit attaches a DANFE whose text has a valid 44-digit access key
- **THEN** issuer, model and number come from the key and the reading counts as read from the file, like the XML

#### Scenario: Photo of a note
- **WHEN** a unit attaches a photo of an NFS-e
- **THEN** the form fills supplier, number, issue date, amount and due date marked "Lido pela IA · confira"
- **AND** a mismatch between that reading and the title is an attention point, not a block

#### Scenario: No model or unreadable answer
- **WHEN** no model reads images, the call fails or the answer has no valid field
- **THEN** the attachment is kept with no reading and the title is marked for a manual look
