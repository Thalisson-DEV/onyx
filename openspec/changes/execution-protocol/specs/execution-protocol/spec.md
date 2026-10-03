## ADDED Requirements

### Requirement: Fixed seven-step order
Every routine run, on-demand analysis and analytical assistant answer SHALL execute the steps Ingestão, Validação da base, Reconciliação da cadeia, Detecção, Quantificação, Priorização and Publicação e registro in this order, persisting each step status in the analysis run.

#### Scenario: Monthly closing run
- **WHEN** R3 runs for June 2026
- **THEN** the analysis run records seven steps in order, each with status and outputs

### Requirement: Critical failure blocks downstream steps
A critical failure in Ingestão or Validação da base SHALL mark all later result steps as blocked with the reason, and the publication SHALL report the inconsistency and what it prevents from concluding, without any margin indicator.

#### Scenario: Revenue swapped between units
- **WHEN** step 2 detects a critical sanity failure for April 2026
- **THEN** steps 3 to 6 are blocked, and the report states which check failed and that April margins cannot be read

### Requirement: Missing inputs are findings with an owner
Step 1 SHALL record every required input that did not arrive for the competence as a finding "indisponível — pendente de informação de campo" with the responsible role, instead of silence.

#### Scenario: PIS/COFINS not delivered
- **WHEN** the competence closes without the PIS/COFINS apportionment
- **THEN** a missing-input finding names the source and its responsible role

### Requirement: Blind spot scan
Each scan SHALL evaluate the Prompt Mestre §11 blind-spot questions that the available data can answer (for example billing without measurement source, fuel without production, cost without cost center, contract without reajuste on data-base) and record each positive answer as a finding even without a monetary value.

#### Scenario: Billing without measurement
- **WHEN** billing exists for a contract and no measurement source exists for it
- **THEN** a blind-spot finding "faturamento sem medição correspondente" is recorded

### Requirement: Publication cap
Publication SHALL include at most 7 exceptions per daily scan and 12 per monthly closing, ordered by criticality, financial impact and urgency; the remainder SHALL be recorded in the ledger as not published.

#### Scenario: Twenty exceptions in a closing
- **WHEN** a monthly closing detects 20 exceptions
- **THEN** the report shows the top 12 and states that 8 more are in the ledger
