# financial-readiness Specification

## Purpose
Linha de base do domínio financeiro canônico, das decisões humanas versionadas e do loop de
decisão (DATA-004cd, DATA-006ab, TON-FE-003). Código: `backend/onyx/db/ton/{financial_domain,
financial_readiness,decision_loop,canonical}.py`, `backend/onyx/server/ton/financial_domain.py`,
frontend `web/src/views/ton/{PendingPage,ClosingPage}`.

## Requirements

### Requirement: Canonical facts from reviewed inputs only
The system SHALL build actual facts only from downstream-safe reviewed NG records, billing facts from billing records and budget facts from budget records, inside a `FinancialNormalizationRun` that records the mapping, amount-basis and reconciliation decision versions it used and an input digest.

#### Scenario: Same inputs
- **WHEN** a normalization is requested with an unchanged input digest
- **THEN** the existing run is returned (idempotent)

### Requirement: Versioned human decisions
The system SHALL persist unit and account mappings, amount basis, DRE classification, candidate rejections and reconciliation decisions as append-only revisions with author, timestamp and mandatory reason, protected by the `ton_financial_immutable` trigger.

#### Scenario: Decision changed
- **WHEN** a user records a new decision for an already decided item
- **THEN** a new version is appended and earlier versions stay readable in the decision log

### Requirement: Deterministic candidates only
The system SHALL offer mapping candidates only from deterministic evidence (exact code, previously approved mapping, or the controller workbook legacy import) and SHALL NOT use fuzzy matching, semantic similarity or LLM classification.

#### Scenario: No exact evidence
- **WHEN** a unit label has no exact code match
- **THEN** no candidate is suggested and the item stays unresolved

### Requirement: Readiness gates and decision loop
The system SHALL compute per-period readiness (READY or NOT_READY with blockers by category), expose record-level evidence for each blocker, recompute after a confirmed decision when the user may recompute, show before and after deltas between runs, list decisions recorded but not yet applied, and expose a unified decision log.

#### Scenario: Decision confirmed with recompute permission
- **WHEN** a user confirms a decision in Pendências
- **THEN** readiness is recomputed and the dialog shows blockers before and after by category

#### Scenario: Decision recorded without recompute
- **WHEN** a decision is saved but no recompute happened
- **THEN** Fechamento, Pendências and the work queue show it as "registrada, aguardando recálculo"
