# TON domain contract: rules, interpretation, Findings and reports

This document defines the domain behavior that implementation plans must honor.
It contains no production thresholds. Report-derived candidates require source
validation and Vale Norte approval before deployment.

## Issues to Address

Onyx has no first-class Rule, RuleVersion, Finding, Occurrence, AnalysisRun or
domain Report entities. TON must add them without making an LLM the detector,
calculator, source writer or hidden state machine.

## Important Notes

- `backend/onyx/db/models.py:2115-2125` is a credential capability report, not
  a business report.
- `backend/onyx/db/models.py:5443-5468` is an admin usage report that stores
  metadata and a FileRecord link, not an immutable TON snapshot.
- `backend/onyx/db/models.py:6837-6915` stores Craft scheduled run history and
  references BuildSession. It is not an AnalysisRun.
- `plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt:8-18` is now
  available. It reports a Jan-Apr 2026 cross-check of a cash-flow database,
  Ferrari DRE and active contracts, with 5,191 entries across seven units.
- The report is domain evidence, not an implementation instruction. The
  underlying workbook, DRE, contracts, bank extracts and NG/Keevo access are
  not present here. Report values are therefore candidate evidence only.

## Report provenance and validation boundary

The report is the source of the candidate catalog below. Its declared period
is January-April 2026 and its meeting date is 15 June 2026
(`plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt:6-18`). It names
the cash-flow workbook, Ferrari DRE and active contracts as source classes
(`:65-66`). Those source artifacts are not in this repository. A report claim
must not be treated as a validated source snapshot until the source artifact,
record identity, unit, currency, period and extraction timestamp are captured.

The report contains facts, interpretations and recommendations. TON stores
these separately:

- **Report fact**: a stated count, amount, date, comparison or missing field.
- **Architectural interpretation**: a candidate rule shape, evidence contract
  or lifecycle state proposed by TON.
- **Unvalidated hypothesis**: a cause, accounting treatment, threshold or
  expected result that needs owner evidence and approval.

The severity shown in the report is recorded as **indicated**. Where the report
does not assign a severity, this document marks a proposed severity as
**inferred** and gives the reason. Inferred severity is not a production
priority until an owner approves it.

In the entries below, `Relatorio...` is shorthand for
`plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt`. The line ranges
refer to that file. No report document number, person name, credential or
business identifier is reproduced unless it is needed as a field type.

## Report-derived candidate catalog

The following entries cover every inconsistency and process control item in the
report. They are not executable rules. Each entry must pass source validation,
domain approval and the mandatory AI interpretation flow before it can create a
final Finding.

| ID | Report section | Classification | Current status |
|---|---|---|---|
| FIN-TAX-01 | 1.1 | mixed | Four source values conflict; arithmetic and accounting treatment need validation. |
| FIN-TAX-02 | 1.2 | mixed | Count and zero-value comparison are report facts; ERP integration meaning is open. |
| FIN-INTERCO-01 | 1.3 | mixed | Three source totals conflict; monthly aggregation and balance-sheet treatment need validation. |
| FIN-VENDOR-01 | 1.4 | mixed | Visible rows are R$ 275.00 below the stated total; supplier and contract justification are missing. |
| FIN-PAYROLL-01 | 1.5 | mixed | Unit sums conflict with aggregates; the ratio and 35–45% range are blocked/unapproved. |
| FIN-REV-MOSS-01 | 1.6 | mixed | Baseline and percentage variants conflict; the cause is a hypothesis. |
| FIN-FIN-01 | 1.7 | mixed | Month-over-month spikes are deterministic; cause and contract link are missing. |
| FIN-REV-ITAB-01 | 1.8 | mixed | Revenue increase is deterministic; retroactivity or amendment is unvalidated. |
| OPS-POST-01 | 2.1 | mixed | Submission and NF-link checks are deterministic once event data exists; root cause is interpretive. |
| OPS-AP-01 | 2.2 | mixed | Required-field and lead-time checks are deterministic; policy ownership is open. |
| FLEET-RENT-01 | 2.3 | mixed | Competence, allocation and duplicate-document checks are deterministic after source capture. |
| OPS-EXPENSE-01 | 2.4 | mixed | Deadline and open-balance checks are deterministic; policy conflict must be resolved. |
| FIN-DUP-01 | 2.5 | mixed | Duplicate candidates are deterministic; legitimacy and estorno require evidence. |
| FIN-BANK-01 | 3.1 | mixed | Reconciliation mismatches are deterministic after both ledgers arrive; listed causes are hypotheses. |
| FIN-BANK-AUTO-01 | 3.2 | insufficient-data | Feasibility cannot be assessed without a validated NG/Keevo and bank contract. |
| SEC-BANK-ACCESS-01 | 3.3 | insufficient-data | Unauthorized access is asserted but user, role and activity evidence is absent. |
| FIN-BUDGET-01 | 4.1 | mixed | Budget completeness and variance are deterministic; report counts conflict and need reconciliation. |
| FUEL-CREDIT-01 | 4.2 | insufficient-data | Spend is reported, but agreement, vehicle and station data are absent. |

### FIN-TAX-01 — parcelamentos in the periodic result

- **Report facts**: Section 1.1 states seven April 2026 `PARCELAMENTOS`
  records. The seven visible amounts sum to R$ 90,877,705.63; the table
  reports R$ 90,877,705.65; the narrative reports R$ 90,882,225.05; and the
  action states that R$ 4,519.42 was paid in April. The narrative/table
  difference is R$ 4,519.40. The report says the agreement values are
  consolidated balances, not April cash outflow (`Relatorio...:69-102`).
  These four values are conflicting source-material values and form a gate.
- **Fields cited**: reporting month, nature, agreement/document identifier,
  registered amount, effective payment amount, DRE account, balance-sheet
  account, agreement and installment schedule. These are business fields from
  the report, not confirmed NG/Keevo columns.
- **Sources and period**: cash-flow database, Ferrari DRE and tax agreements;
  April 2026, within the Jan-Apr report period (`:65-70`).
- **Candidate check**: reconcile the source rows and table sum; compare the
  effective payment to the periodic result; flag any consolidated balance
  posted as April expense. This is **mixed**: arithmetic is deterministic,
  while liability-versus-expense treatment is interpretation-only.
- **Expected result**: after approval, the DRE contains the effective period
  payment and the consolidated balance is represented in the approved
  liability treatment. The seven-row sum, table total, narrative total and
  paid amount must reconcile before a Finding.
- **Severity**: ALTA, indicated by the report (`:27-29`).
- **Action and owner**: reconcile with legal/tax and correct the DRE;
  Ferrari and Controladoria are named in the consolidated action
  (`:102`, `:681-685`).
- **Open questions and missing data**: source row IDs and signs; bank proof;
  agreement and installment schedule; accounting policy; reason for the
  R$ 4,519.40 difference between the two reported totals; whether the paid
  amount is already included in either total. No implementation may invent a
  tax or NG/Keevo field.

### FIN-TAX-02 — retained taxes with zero final value

- **Report facts**: 139 records are stated for `IMPOSTOS S/FATURAMENTO` and
  `TAXAS E CONTINGÊNCIAS`; movement is negative and final value is zero. The
  report gives 99 records and R$ 8,304,644.97 for the first nature, 40 and
  R$ 1,264,813.99 for the second, total R$ 9,569,458.96
  (`Relatorio...:105-128`). It names IRPJ, INSS, ISS, PIS and COFINS as
  retention examples (`:106`).
- **Fields cited**: nature, record count, movement, final value, retained tax
  type, gross revenue and ERP integration field. The field names in the report
  are not a validated source schema.
- **Sources and period**: cash-flow/DRE report scope Jan-Apr 2026; exact row
  dates and source snapshot are missing.
- **Candidate check**: flag a negative movement with zero final value and
  reconcile it to the revenue-retention presentation. This is **mixed**:
  arithmetic and completeness are deterministic; the correct DRE presentation
  needs interpretation and ERP evidence.
- **Expected result**: every retained value is either explicitly reconciled as
  a gross-revenue deduction or is an identified open item with an owner.
- **Severity**: ALTA, indicated in the executive summary (`:30-32`).
- **Action and owner**: Financeiro confirms ERP integration and regularizes
  open items (`:131`); role names only are retained.
- **Open questions and missing data**: detailed records, tax-period mapping,
  revenue invoice IDs, ERP import/export evidence, sign convention and whether
  zero means already netted or missing.

### FIN-INTERCO-01 — intercompany and Chácara classification

- **Report facts**: Section 1.3 states that intercompany transfers and Chácara
  São Judas expenses are in `DESPESAS DIVERSAS`. The totals by origin sum to
  R$ 4,210,512.00; the monthly table totals R$ 4,210,513.00; and the narrative
  states R$ 4,210,513.16 (`Relatorio...:134-173`). These three totals are
  conflicting source-material values and form a gate.
- **Fields cited**: origin, month, amount, nature, counterparty, legal entity,
  unit, project and balance-sheet destination. These are candidate business
  fields, not NG/Keevo columns.
- **Sources and period**: cash-flow/DRE and active contracts, Jan-Apr 2026.
- **Candidate check**: aggregate by source origin and month; identify
  intercompany transfers and compare both sides of each transfer. Separately
  test Chácara items against approved investment criteria. This is **mixed**.
- **Expected result**: approved mutuals are excluded from operating expense;
  approved investment is represented as the correct asset category. The
  by-origin, monthly and narrative totals must reconcile before a Finding.
- **Severity**: ALTA, indicated in the executive summary (`:33-35`).
- **Action and owner**: Controladoria and Contabilidade reclassify only after
  supporting evidence (`:176`, `:732-735`).
- **Open questions and missing data**: source row IDs, legal-entity mapping,
  two-sided transfer evidence, Chácara project documents, capitalization
  policy and reason for the R$ 0.16 discrepancy.

### FIN-VENDOR-01 — legal, engineering and consulting increase

- **Report facts**: Jan-Feb expense is stated as R$ 72,500 in 2025 versus
  R$ 473,827 in 2026, described as a 554% increase. The five visible amount
  rows sum to R$ 473,552.00, leaving R$ 275.00 against the stated total. The
  report highlights R$ 323,682 in Itabirito consulting and says supplier names
  in the DRE are masked (`Relatorio...:179-212`). This completeness conflict
  blocks the candidate until reconciled.
- **Fields cited**: unit, expense type, supplier identity, amount, month,
  invoice/receipt and contract reference. The supplier names are missing from
  the report, so no personal or vendor identity is copied here.
- **Sources and period**: Ferrari DRE, Jan-Feb 2025 and Jan-Feb 2026; report
  cross-check context is Jan-Apr 2026.
- **Candidate check**: compare period totals and require an identified supplier
  and contract for each expense. This is **mixed**. The percentage needs a
  defined meaning (increase versus index), and supplier legitimacy needs
  interpretation.
- **Expected result**: all entries have auditable supplier, invoice and
  contract evidence; the visible-row sum and stated total reconcile; and the
  Itabirito amount has a documented business reason.
- **Severity**: not assigned in the item; **inferred MED** for auditability,
  because the report calls out masked suppliers and a concentrated amount.
- **Action and owner**: Financeiro requests unmasked audit metadata and the
  contract justification (`:215`). Store access-controlled identities; do not
  expose them in reports by default.
- **Open questions and missing data**: supplier master and role-based access,
  invoices, contracts, exact period totals, missing R$ 275.00, unit start dates
  and percentage denominator.

### FIN-PAYROLL-01 — social charges ratio

- **Report facts**: Jan-Feb 2026 payroll is stated as R$ 4,733,535 and social
  charges as R$ 2,936,450, stated as 62.0%. The visible unit rows sum to
  payroll R$ 4,984,535.00 and charges R$ 2,827,183.00. Unit ratios are 50.0%,
  61.6%, 68.5% and 57.9% (`Relatorio...:218-251`). The row and aggregate
  totals conflict, so the aggregate ratio is blocked.
- **Fields cited**: unit, payroll, social charges, charge component, employee
  withholding, employer charge, severance item and period.
- **Sources and period**: Ferrari DRE and payroll/DP detail, Jan-Feb 2026.
- **Candidate check**: calculate charges/payroll per unit and identify
  components that overlap. This is **mixed**. The report's 35–45% expected
  range is a provisional domain hypothesis, not a TON threshold. Do not use
  the aggregate ratio until the row and aggregate totals reconcile.
- **Expected result**: approved payroll components reconcile once. Any
  exception is explained by an approved policy or corrected source data.
- **Severity**: not assigned in the item; **inferred ALTA** because the report
  estimates about R$ 1.5MM of apparent quarterly inflation (`:254`).
- **Action and owner**: DP and Financeiro audit composition and separate
  severance, FGTS fine and employee withholding where approved (`:254`).
- **Open questions and missing data**: payroll ledger, component definitions,
  labor regime, severance evidence, withholding treatment, rounding, the
  reason for both total conflicts and the approved comparison range.

### FIN-REV-MOSS-01 — Mossoró revenue drop

- **Report facts**: revenue is R$ 3,171,543 in Jan, R$ 3,517,865 in Feb,
  R$ 3,733,314 in Mar and R$ 447,016 in Apr 2026. The calculated Jan-Mar
  average is R$ 3,474,240.67, versus the report's R$ 3,474,174. The report
  describes a 87% drop in prose and -88.0% in the table; the calculated drop
  is approximately 87.13%. Operating costs stayed near R$ 2.2MM
  (`Relatorio...:257-280`). The average and percentage variants are a
  source-material conflict and form a baseline gate.
- **Fields cited**: unit, contract, month, invoiced revenue, expected monthly
  revenue, invoice status, suspension/glosa status and operating cost.
- **Sources and period**: DRE, contract and invoice evidence, Jan-Apr 2026.
- **Candidate check**: compare April revenue to the approved trailing-period
  baseline and flag the variance. This is **mixed**: the variance is
  deterministic; pending invoice, suspension or glosa is a hypothesis.
- **Expected result**: the April value is reconciled to an issued invoice,
  approved glosa/suspension, or a corrected period allocation. An owner must
  approve the baseline and rounding method before the candidate is evaluated.
- **Severity**: **inferred ALTA**, based on immediate action and stated
  approximately R$ 3MM result distortion (`:283`; consolidated action `:701-705`).
- **Action and owner**: Financeiro investigates invoice and contract status
  with the unit owner (`:283`). Personal names are omitted.
- **Open questions and missing data**: invoice IDs, measurement records,
  contract schedule, glosa/suspension notices, costs by month and an approved
  choice between the calculated average, report average, 87%, -88.0% and
  approximately 87.13% with its rounding policy.

### FIN-FIN-01 — atypical financial expenses

- **Report facts**: financial expenses are R$ 45,646 in Jan, R$ 446,272 in
  Feb, R$ 46,593 in Mar and R$ 46,017 in Apr. Financing is zero in Jan-Feb,
  R$ 1,296,657 in Mar and R$ 5,000 in Apr; total reported accumulation is
  R$ 1,886,185. The report describes February as an 878% increase from
  January (`Relatorio...:286-313`).
- **Fields cited**: nature, month, amount, bank transaction, financing/credit
  contract, fee type, IOF or fine classification and posting date.
- **Sources and period**: DRE and bank extract, Jan-Apr 2026.
- **Candidate check**: compare monthly amount to an approved baseline, flag
  the February increase and require a contract link for financing. This is
  **mixed**; the report's cause suggestions are hypotheses.
- **Expected result**: every material amount has bank evidence, approved
  nature and a linked financing contract. The posting month is correct.
- **Severity**: **inferred ALTA**, due to the immediate investigation and
  material March amount (`:316`, `:706-710`).
- **Action and owner**: Tesouraria and Financeiro reconcile the February and
  March amounts to bank and credit-contract evidence (`:316`).
- **Open questions and missing data**: detailed bank rows, contract IDs,
  payment schedules, fee/tax classification, date policy and materiality
  threshold.

### FIN-REV-ITAB-01 — Itabirito revenue increase

- **Report facts**: Itabirito revenue is R$ 3,975,430 in Apr 2026 versus a
  stated prior three-month average of R$ 1,214,150, described as almost three
  times the average (`Relatorio...:319-320`).
- **Fields cited**: unit, month, invoice, measurement, contract amendment,
  retroactive competence, accumulated installment and revenue amount.
- **Sources and period**: DRE, invoices and contract/addendum records, Jan-Apr
  2026.
- **Candidate check**: compare April revenue to the approved trailing average
  and flag the change. This is **mixed**; the listed causes are hypotheses.
- **Expected result**: a retroactive measurement, accumulated installment,
  addendum or corrected posting is supported and recorded with its competence.
- **Severity**: not assigned in the item; **inferred MED** for trend integrity.
- **Action and owner**: Financeiro confirms the business justification and
  records it in the system (`:323`).
- **Open questions and missing data**: three monthly source values, invoice and
  measurement IDs, addendum, competence policy and baseline calculation.

### OPS-POST-01 — weekly unit posting protocol

- **Report facts**: units send postings late, misclassify records, omit NFs
  from receipts and post forecasts/contracts without generated NFs
  (`Relatorio...:333-352`). The proposed controls are weekly Monday posting,
  NF validation at save, monthly closure by day 25, training and a weekly
  pending dashboard (`:355-382`). The report estimates more than two hours of
  rework per classification occurrence (`:344-349`).
- **Fields cited**: unit, posting timestamp, entry/exit, nature, receipt,
  linked NF, contract/forecast marker and closure date.
- **Sources and period**: NG/Keevo process events and the Jan-Apr operating
  period; event logs and current SLA are missing.
- **Candidate check**: flag missing NF links, late postings and unclosed
  records against an approved calendar. This is **mixed**; stated causes and
  sanctions require interpretation and approval.
- **Expected result**: approved weekly and month-end controls produce complete
  records with NF evidence. No system action may block an advance until its
  authorization is approved.
- **Severity**: ALTA, indicated in the executive summary (`:36-38`).
- **Action and owner**: Controladoria and unit managers own the proposed
  protocol; the report requests a decision on mandatory use and sanction
  (`:385`).
- **Open questions and missing data**: actual posting timestamps, unit-level
  backlog, NF availability delay, holiday calendar, exception process and
  sanction authority.

### OPS-AP-01 — accounts-payable intake completeness

- **Report facts**: Financeiro receives late and incomplete packages. Missing
  information includes supplier, competence and vehicle allocation
  (`Relatorio...:388-407`). The checklist proposes a legible document, supplier
  identity, service competence, destination unit/cost center, vehicle plate and
  destination, and duplicate confirmation. It proposes five business days
  before due date and seven days for new supplier registration (`:410-427`).
- **Fields cited**: document, supplier name and business identifier, service
  month/year, unit/cost center, vehicle identifier/destination and duplicate
  attestation. These are business requirements, not confirmed database
  columns. Business identifiers must be protected.
- **Sources and period**: accounts-payable submissions and NG/Keevo workflow;
  no submission log or field schema is supplied.
- **Candidate check**: validate required-field presence and lead time before
  processing. This is **mixed** because payment risk and responsibility need
  owner policy.
- **Expected result**: incomplete requests are returned with a stable reason;
  complete requests retain competence and allocation evidence.
- **Severity**: ALTA, indicated in the executive summary (`:39-41`).
- **Action and owner**: Financeiro and unit managers approve the checklist;
  the report assigns deadline responsibility to the submitting manager
  (`:430`).
- **Open questions and missing data**: exact accepted file types, validation
  authority, privacy handling for business IDs, holiday calculation, vendor
  onboarding SLA and duplicate matching policy.

### FLEET-RENT-01 — rental competence, allocation and duplicate documents

- **Report facts**: rentals total R$ 5,444,710 for Jan-Apr 2026. Reported unit
  amounts are R$ 2,203,232 for Mossoró, R$ 1,427,208 for Juazeiro do Norte,
  R$ 836,341 for Central Administration and R$ 631,355 for Itabirito. It
  cites missing competence, a December 2025 rental paid in January, unknown
  Central Administration usage and duplicate documents in Itabirito
  (`Relatorio...:433-457`).
- **Fields cited**: rental type, vehicle/equipment ID or plate, supplier,
  amount, competence, payment date, unit, destination, shared-use allocation,
  document and contract.
- **Sources and period**: cash-flow/DRE and rental contracts, Jan-Apr 2026.
- **Candidate check**: require competence, identify the consuming unit, apply
  approved shared-use allocation and flag duplicate document assignments. This
  is **mixed** until the duplicate and allocation policies are approved.
- **Expected result**: every rental is assigned to the correct competence,
  vehicle/equipment and unit, with duplicate evidence resolved before report
  finalization. The report requests a fleet report before day 5 each month
  (`:460-483`).
- **Severity**: MÉDIA, indicated in the executive summary (`:42-44`).
- **Action and owner**: Financeiro/Controladoria standardize history;
  Gestores and Controladoria supply the monthly fleet report and planning
  (`:466-480`).
- **Open questions and missing data**: remaining units, revenue denominator
  for the listed percentages, full rental ledger, vehicle IDs, contract
  periods, allocation basis and duplicate-document evidence.

### OPS-EXPENSE-01 — fixed-fund and travel-accountability deadlines

- **Report facts**: fixed-fund and travel expenses are not posted regularly;
  receipts are not linked and advances are not separated from settlement
  (`Relatorio...:486-501`). The table proposes weekly Friday fixed-fund
  settlement, travel documents within 48 hours after return and blocking a new
  advance when an open settlement exceeds seven days. The decision request
  instead proposes five business days after return for travel (`:504`).
- **Fields cited**: advance ID, employee identifier, return date, receipt,
  destination, justification, settlement status, open balance and approval.
  Employee identifiers must be masked or tokenized.
- **Sources and period**: NG/Keevo expense and advance records; no counts or
  detailed rows are supplied.
- **Candidate check**: flag missing receipt links, open advances and overdue
  settlements against an approved policy. This is **mixed**.
- **Expected result**: one approved deadline is applied; fixed-fund and travel
  balances are visible without exposing employee PII. Blocking is an
  authorized policy decision, not an inferred detector action.
- **Severity**: MÉDIA, indicated in the executive summary (`:45-47`).
- **Action and owner**: Financeiro and unit managers define the policy; the
  report asks for approval of deadlines and blocking (`:504`, `:758-761`).
- **Open questions and missing data**: resolve 48 hours versus five business
  days, define return date and holidays, quantify open balances, approve
  blocking authority and define exception/audit behavior.

### FIN-DUP-01 — duplicate payment and estorno evidence

- **Report facts**: identical document numbers are assigned to different
  suppliers, especially in Mossoró rentals. The report gives examples with
  three and six supplier assignments but no quantified amount
  (`Relatorio...:507-508`). It proposes bank matching, written unit
  confirmation within 48 hours, supplier refund, same-month estorno and a
  monthly evidence report (`:511-525`).
- **Fields cited**: document identifier, supplier, amount, beneficiary,
  payment date, bank transaction, unit, confirmation, refund and estorno
  evidence. Report examples are not reproduced.
- **Sources and period**: bank extract and NG/Keevo, Jan-Apr 2026; detailed
  extracts and quantification are missing.
- **Candidate check**: flag repeated document identity across distinct
  suppliers or near-time, same-value payments. This is **mixed** because
  document reuse may be legitimate and requires owner/bank evidence.
- **Expected result**: each candidate is classified as legitimate or duplicate;
  confirmed duplicates have refund and estorno evidence linked to the same
  period or an approved correction.
- **Severity**: ALTA, indicated in the executive summary (`:51-56`).
- **Action and owner**: Tesouraria, Financeiro, unit managers and
  Controladoria perform the cross-check and evidence the estorno (`:515-525`).
- **Open questions and missing data**: detailed bank extracts, transaction and
  beneficiary identifiers, exact amounts, document uniqueness policy, refund
  status and the 30 June quantification result (`:528`).

### FIN-BANK-01 — bank-to-ERP reconciliation

- **Report facts**: the report states that bank balances and NG/Keevo balances
  diverge in some accounts. It lists possible causes: ERP-only entries,
  bank-only debits, one-sided intercompany transfers and posting versus
  settlement dates (`Relatorio...:534-553`).
- **Fields cited**: account, bank transaction identifier, beneficiary business
  identifier, debit/credit, amount, posting date, settlement date, NG/Keevo
  entry and intercompany counterpart. These fields are requested by the report,
  not confirmed NG/Keevo columns.
- **Sources and period**: detailed bank extracts and NG/Keevo ledger, Jan-Apr
  2026. No extracts, counts or variance amounts are supplied.
- **Candidate check**: perform account-by-account, month-by-month matching and
  classify unmatched items. This is **mixed**; proposed causes are hypotheses.
- **Expected result**: every variance has a type, period, owner and evidence;
  two-sided transfers reconcile or remain explicit open items.
- **Severity**: ALTA, indicated in the executive summary (`:54-56`).
- **Action and owner**: Tesouraria and Controladoria obtain detailed extracts
  and perform the reconciliation (`:542-556`).
- **Open questions and missing data**: account inventory, bank permissions,
  extracts with transaction identifiers, matching tolerance, timing policy,
  intercompany ledger and quantified variances.

### FIN-BANK-AUTO-01 — reconciliation and remittance automation feasibility

- **Report facts**: the report proposes bank/API or Power Automate reconciliation
  and CNAB remittance, with target months September and August 2026. It asks
  for a technical assessment (`Relatorio...:559-577`).
- **Fields cited**: API capability, authentication, pagination/rate limits,
  transaction identifiers, CNAB format, approval workflow, bank and ERP
  integration status. These are contract requirements, not known fields.
- **Sources and period**: bank provider, NG/Keevo and internal payment workflow;
  no technical contract is present.
- **Candidate check**: no production rule is authorized. The current item is
  **insufficient-data** and may become a capability gate after contracts arrive.
- **Expected result**: a read-only feasibility record documents supported
  endpoints, limits, auth, error handling and approval controls. Any later
  payment automation must preserve dual approval and source-write boundaries.
- **Severity**: not assigned; **inferred MED** for operational efficiency,
  not a release blocker.
- **Action and owner**: Financeiro and technical operations perform the
  requested assessment (`:577`, `:743-747`).
- **Open questions and missing data**: validated NG/Keevo schema and access,
  bank API/CNAB documentation, test tenant, quotas, deletion semantics,
  approval model and whether any write is permitted. NG/Keevo remains BLOCKED.

### SEC-BANK-ACCESS-01 — bank portal access review

- **Report facts**: the report says that unknown bank-portal users should be
  reviewed and that a support user should be added with dual approval
  (`Relatorio...:580-595`). It gives no user list, count or activity evidence.
- **Fields cited**: portal, user token, role, last activity, authorization,
  approval, status and dual-approval setting. No user names are reproduced.
- **Sources and period**: bank access-control portals; no export or audit log is
  present.
- **Candidate check**: flag accounts without an approved owner or current
  authorization. This is **insufficient-data** until access evidence arrives;
  the access decision itself is interpretation and owner approval.
- **Expected result**: unauthorized access is removed through the bank's
  approved process, and any support access has least privilege and dual
  approval. TON must not automate external access changes in V1.
- **Severity**: not assigned in the item; **inferred ALTA** because it is a
  direct access-control risk.
- **Action and owner**: Financeiro and the authorized approver review and
  update portal access (`:588-595`).
- **Open questions and missing data**: complete user export, authorization
  records, last-use data, role matrix, removal evidence and support-account
  approval. Never record credentials or tokens.

### FIN-BUDGET-01 — budget completeness and variance

- **Report facts**: the executive summary says six of seven units lack current
  2026 budget data (`Relatorio...:57-59`), while section 4.1 says five of seven
  units lack a filled 2026 budget column (`:601-603`). The table marks several
  units as outdated, partial, pending or in course; Toledo has R$ 9,740,259
  annual budget and a projected R$ 1.39MM deficit (`:606-637`).
- **Fields cited**: unit, budget version, contract/addendum, annual amount,
  period coverage, DRE actual, variance, status and delivery date.
- **Sources and period**: Ferrari DRE and 2026 budget/contract documents;
  current source files are not present.
- **Candidate check**: flag a unit with no approved 2026 budget coverage and
  calculate actual-versus-budget variance. This is **mixed** because the count
  conflict and approval status need interpretation.
- **Expected result**: each unit has one approved budget version with explicit
  coverage; DRE reports actual, budget and variance using the same period.
  Report counts must reconcile before a Finding.
- **Severity**: MÉDIA, indicated in the executive summary (`:57-59`).
- **Action and owner**: Controladoria requests updated budgets for the named
  units by the report's June deadline (`:640`, `:727-731`). Unit names are
  retained as organizational data; personal names are omitted.
- **Open questions and missing data**: reconcile five versus six units, budget
  documents and addenda, actual DRE values, version approval, coverage for
  implementation units and contract expiry handling. The section requests
  delivery by 30 June, while consolidated action 10 lists 30 July; this date
  conflict needs owner resolution (`:640`, `:727-731`).

### FUEL-CREDIT-01 — fuel credit and station control

- **Report facts**: fuel spend is reported as R$ 2,797,074 for Jan-Apr 2026 and
  as the third largest operating expense. The report estimates that a 5%
  station-choice variance is about R$ 140,000 per year, but says there is no
  consolidated record of negotiated stations, discounts, credit terms or
  limits (`Relatorio...:643-647`).
- **Fields cited**: station, business identifier, unit, vehicle/plate, driver,
  date, liters, amount, discount, credit term, monthly limit and contract.
  Business identifiers and driver data require access control.
- **Sources and period**: fuel ledger, station agreements and vehicle logs,
  Jan-Apr 2026; agreement and vehicle data are missing.
- **Candidate check**: after source capture, compare fueling events to approved
  stations and agreement limits, and reconcile liters, price and discount. The
  current status is **insufficient-data**. The annual R$ 140,000 estimate is a
  report hypothesis until its annualization basis is supplied.
- **Expected result**: every fueling event maps to an approved vehicle, unit,
  station and agreement, with monthly credit-versus-use evidence.
- **Severity**: not assigned in the item; **inferred MED** from stated spend
  and control gap.
- **Action and owner**: Financeiro and unit managers build the station and
  vehicle register and monthly review (`:650-665`).
- **Open questions and missing data**: all active agreements, station and
  vehicle master data, driver privacy policy, annualization denominator,
  approved station policy and exception handling.

## Report traceability

This table is the required link from report evidence to candidate behavior. A
planned phase is not approval to implement the rule. Phase 001 captures source
provenance; Phase 003 owns domain contracts; Phase 004 owns ingestion and
evidence preservation; Phase 006 owns reports, schedules and admin workflows.

| Report section/example | Candidate rule | Required evidence | Unresolved contract | Planned phase |
|---|---|---|---|---|
| 1.1 parcelamento balance versus April payment | FIN-TAX-01 | Cash-flow rows, DRE, bank proof, tax agreement and installment schedule | Reconcile two totals; approve liability treatment and payment-period policy | 001 -> 003 |
| 1.2 negative movement with zero final value | FIN-TAX-02 | 139 source rows, revenue records and ERP integration evidence | Tax retention presentation, signs and missing-value semantics | 001 -> 003/004 |
| 1.3 mutuals/Chácara aggregation | FIN-INTERCO-01 | Source rows, both transfer sides, project and asset evidence | Identity, capitalization and total discrepancy policy | 001 -> 003 |
| 1.4 Jan-Feb expense comparison and masked suppliers | FIN-VENDOR-01 | DRE detail, supplier master, invoices and contracts | Supplier access, percentage meaning and contract linkage | 001 -> 003/004 |
| 1.5 social-charge ratio | FIN-PAYROLL-01 | Payroll detail and charge components by unit | Approved range, regime, overlap and rounding | 001 -> 003 |
| 1.6 Mossoró April revenue drop | FIN-REV-MOSS-01 | Invoices, measurements, contract, glosa/suspension and costs | Baseline, competence and missing-invoice policy | 001 -> 003/006 |
| 1.7 financial-expense spikes | FIN-FIN-01 | Bank rows, DRE detail, fees and credit contracts | Materiality, period and nature mapping | 001 -> 003 |
| 1.8 Itabirito April increase | FIN-REV-ITAB-01 | Invoices, measurements, addenda and competence | Retroactive revenue and baseline policy | 001 -> 003/006 |
| 2.1 weekly posting protocol | OPS-POST-01 | Posting/NF-link events, unit calendar and closure log | SLA, holidays, exceptions and sanctions | 001 -> 004/006 |
| 2.2 accounts-payable checklist | OPS-AP-01 | Submission payloads, documents, vendor registry and due dates | Required fields, privacy, lead times and return policy | 001 -> 004 |
| 2.3 rental competence/allocation and duplicate docs | FLEET-RENT-01 | Rental ledger, fleet inventory, contracts and allocation proof | Shared-use rateio, duplicate identity and day-5 control | 001 -> 004/006 |
| 2.4 fixed-fund/travel controls | OPS-EXPENSE-01 | Advances, returns, receipts, balances and approvals | Resolve 48h versus five business days; blocking authority | 001 -> 003/006 |
| 2.5 duplicate-payment process | FIN-DUP-01 | Detailed bank extract, ERP rows, supplier confirmation and refund proof | Duplicate identity, refund and same-month correction policy | 001 -> 003/006 |
| 3.1 bank versus NG/Keevo balances | FIN-BANK-01 | Account inventory, bank extract, ERP ledger and transfer pairs | Matching tolerance, timing and source identifiers | 001 -> 004/006 |
| 3.2 API/CNAB proposal | FIN-BANK-AUTO-01 | Bank/API/CNAB docs, auth, quotas and test access | NG/Keevo contract and whether writes are allowed | 001 -> 004/006 (blocked) |
| 3.3 bank users and support access | SEC-BANK-ACCESS-01 | Portal export, role matrix, activity and approvals | Least privilege, dual approval and removal evidence | 001 -> 002/006 |
| 4.1 2026 budget coverage and Toledo variance | FIN-BUDGET-01 | Approved budgets, addenda, DRE actuals and unit coverage | Five-versus-six count, version and variance policy | 001 -> 003/006 |
| 4.2 negotiated stations and fuel spend | FUEL-CREDIT-01 | Station agreements, fueling events, vehicle and unit master data | Station policy, annualization and driver privacy | 001 -> 004/006 |

## Source-material conflict gates

These are reconciliation gates from the report itself. They are not business
corrections and must not be silently normalized by a detector:

1. **1.1**: seven-row sum R$ 90,877,705.63; table total R$ 90,877,705.65;
   paid amount R$ 4,519.42; narrative/table difference R$ 4,519.40.
2. **1.3**: totals by origin R$ 4,210,512.00; monthly table total
   R$ 4,210,513.00; narrative total R$ 4,210,513.16.
3. **1.4**: visible amount rows sum R$ 473,552.00; stated total R$ 473,827.00;
   difference R$ 275.00. Rule activation is blocked until completeness is
   reconciled.
4. **1.5**: visible unit sums are payroll R$ 4,984,535.00 and charges
   R$ 2,827,183.00; declared totals are payroll R$ 4,733,535.00 and charges
   R$ 2,936,450.00. The aggregate ratio is blocked.
5. **1.6**: calculated Jan-Mar average R$ 3,474,240.67 versus reported
   R$ 3,474,174; calculated fall is approximately 87.13%, versus report prose
   87% and table −88.0%. Baseline and rounding require owner decision.
6. **Executive summary versus section 1**: the summary declares nine types,
   while section 1 contains eight numbered items (1.1–1.8). Reconcile the
   catalog count before claiming complete coverage
   (`Relatorio...:24-58,65-69`).

The report's consolidated action list is a planning input, not a Finding. Its
dates and named responsibilities remain owner decisions and must be recorded
as schedule metadata only after approval (`Relatorio...:671-761`).

## Interpretation state machine

The detector never calls an LLM to decide whether data violates a rule. It
produces a deterministic candidate and evidence. The final Finding and Report
path must require interpretation.

```text
candidate/detected
        |
        v
interpretation_pending -- failure --> interpretation_failed
        |
        v
interpreted/final
```

Required semantics:

- `candidate` means the detector produced a typed candidate with source IDs,
  deterministic expected/actual values and evidence.
- `detected` means the candidate passed deterministic validity checks and is
  eligible for interpretation. Implementations may store `candidate` and
  `detected` as separate states or a status plus validity flag, but the
  distinction must be observable.
- `interpretation_pending` is durable before any LLM request starts.
- `interpreted` means the mandatory AI interpretation passed schema, evidence
  and policy validation. `final` is allowed only after this success.
- `interpretation_failed` is explicit and durable. It stores a safe error class,
  retry eligibility and timestamps. It is never silently treated as final.
- A missing provider, timeout, malformed output, policy refusal or insufficient
  evidence must leave the record non-final and visible to operators.
- The interpreter can classify severity, summarize impact and explain evidence.
  It cannot change deterministic numbers, source IDs, rule version, identity
  key or write to NG/Keevo or another source.

## Generic Finding and Occurrence contract

Do not invent NG/Keevo fields. Use opaque identity components until Vale Norte
approves domain keys.

### Logical identity

The logical key is an opaque, canonical representation of approved values. It
must not be derived from title, description or LLM text. Candidate components
may include rule version, domain, organizational unit, period and source record
IDs, but the exact fields remain a decision gate.

### Repetition and resolution

- First valid detection creates one Finding and one Occurrence.
- A repeat with the same approved logical key updates `last_seen` and creates a
  new occurrence record or increments a documented occurrence count. It must
  not create a second logical Finding.
- Resolution closes the Finding and records actor, time, reason and evidence.
- A repeat after resolution follows an explicit rule policy: either create a
  new occurrence and reopen the same logical Finding, or create a new Finding
  when the rule version or approved identity changes. The executor must not
  choose silently.
- Suppression, acknowledgement, reopening and superseding are append-only
  transitions with audit events.
- Concurrent detector workers and Celery retries must converge on one logical
  result. Database uniqueness and idempotency are required; application-only
  deduplication is insufficient.

### Partial specialist results

TON Central/CEO, CFO, Frota, Contratos, Auditoria and RH have direct authorized
  access according to role and scope. Each specialist result is persisted with
  `result`, `timeout`, `error` or `insufficient_data`. A failed specialist does
  not erase successful results. The supervisor result records all child states
  and is non-final when policy requires every specialist or when interpretation
  for any required result fails.

## Rule catalog matrix

These are slots for approved rules, not executable rules.

| Domain | Data needed | Deterministic check | Evidence | AI interpretation | Open decision |
|---|---|---|---|---|---|
| Financial | approved transactions/ledger | balance, variance, duplicate or threshold comparison | source IDs, period, currency and calculation version | explain impact | currency, tolerance, rounding and period |
| Fleet | vehicles, trips, maintenance | compliance, gap, stale or out-of-range check | vehicle/trip/maintenance IDs | summarize operational risk | date window and missing-data policy |
| Contracts | clauses, dates and obligations | deadline, missing clause or mismatch | document ID, page/section/span | explain clause evidence | precedence, timezone and grace period |
| Audit | controls and source results | expected versus actual control state | control ID and record IDs | classify and narrate | duplicate/resolved definition |
| HR | approved employee/policy data | policy or completeness check | masked employee ID and policy span | explain approved evidence | privacy role, aggregation and masking |
| Quality | profile, schema and freshness data | missingness, uniqueness, range or stale age | field/profile/run IDs | prioritize remediation | thresholds and exception policy |

## Immutability decision

Recommended decision: use append-only database rows for rule execution,
Finding/Occurrence transitions and report revisions; store one canonical,
versioned snapshot per final report; compute and persist a cryptographic hash;
store a FileStore artifact when the report is large or must be downloaded.

The canonical snapshot must contain rule versions, source snapshot IDs,
deterministic values, evidence references, interpretation output, model/config
metadata allowed by privacy policy, timestamps, confidence and authorization
context. No update may silently alter a final snapshot. A correction creates a
new revision linked to the prior report and records the reason.

This decision must be approved before the schema migration. It is not an open
detail for an implementation agent to choose after creating tables.

## Data and limits questions

1. What are the canonical Vale Norte IDs for tenant, company, unit, employee,
   vehicle, contract, ledger entry and reporting period?
2. What are the accepted units, currencies, timezones, rounding and precision?
3. What values count as missing, malformed, late, contradictory or unknown?
4. What is the approved logical identity for each rule domain?
5. Does a post-resolution repeat reopen an existing Finding or create a new one?
6. Which roles can see HR, financial, contract and fleet evidence?
7. Can interpretation receive raw evidence, masked excerpts or only structured
   values?
8. Which rule versions are approved, retired, backfilled or test-only?
9. What is the retention for temporary inputs, source snapshots, evidence and
   report artifacts?
10. What are NG/Keevo authentication, pagination, rate, freshness and deletion
    contracts?
11. How are the report's conflicting totals for parcelamentos and mutuals
    reconciled before source snapshots are accepted?
12. Does the budget gap cover five or six of seven units, and what defines
    approved 2026 coverage?
13. Is travel settlement due within 48 hours or five business days after
    return? Which policy controls exceptions and advance blocking?
14. Which report values can be corroborated by source exports, bank evidence,
    contracts, invoices, payroll detail and access logs?
15. Which reported ranges, baselines and materiality values become approved
    rule parameters, and which remain interpretation context only?

## Implementation strategy

Implement this contract after the baseline and security slices. Create typed
models and service interfaces first. Add no domain schema until the immutability
decision and identity questions are approved. Keep detector, interpreter,
deduplication and report finalization as separate service boundaries.

## Scope

In scope: domain contracts, state machine, identity policy, rules, partial
results, report immutability and data questions.

Out of scope: NG/Keevo field mappings, production thresholds, source writes,
external messaging and UI implementation.

## Tests

Before implementation, create named specs in the TON test namespace. Then run
only the named tests until they pass:

```text
rg -n "candidate|detected|interpretation_pending|interpreted|final|interpretation_failed" backend/tests web/tests
rg -n "Finding|Occurrence|RuleVersion|AnalysisRun|Report" backend/tests web/tests
uv run pytest backend/tests/unit/ton/test_domain_contract.py -xv
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_finding_lifecycle.py -xv
```

Expected result after the implementation slice: the named files exist, state
transitions and invalid transitions are tested, and concurrent duplicate/retry
tests converge. Before the slice, the first `rg` commands may return no matches;
that absence is the reason to create the specs first.

## Done criteria

- [ ] The interpretation state machine is explicit and durable.
- [ ] Final Finding/Report is impossible without successful interpretation.
- [ ] Detector code has no LLM dependency.
- [ ] LLM cannot change deterministic values or write to sources.
- [ ] Logical identity remains opaque until domain keys are approved.
- [ ] Repetition, resolution and post-resolution behavior are explicit.
- [ ] Concurrent and retry paths are idempotent.
- [ ] Specialist result, timeout, error and insufficient-data outcomes persist.
- [ ] Append-only plus canonical snapshot plus hash decision is approved before migration.
- [ ] Named unit and integration tests pass.

## STOP conditions

- Stop if the Vale Norte report-derived candidates lack source validation,
  domain keys or owner approval for production rules.
- Stop if an agent proposes a threshold, field or NG/Keevo mapping without approval.
- Stop if interpretation failure can be hidden or finalization can bypass it.
- Stop if a schema design permits silent mutation of a final report.
- Stop if a specialist needs unauthorized data, tools or memory.
- Stop if a retry can create duplicate logical Findings.
