# ng-financial-review Specification

## Purpose
Linha de base da revisão financeira determinística do NG (DATA-003): regras versionadas geram
achados com evidência, recomendação e decisão humana, e produzem um dataset revisado em que só
registros seguros seguem adiante. Código: `backend/onyx/ton/financial_review/*`,
`backend/onyx/db/ton/financial_review.py`, `backend/onyx/server/ton/financial_review.py`.

## Requirements

### Requirement: Active deterministic review rules
The system SHALL evaluate exactly the active rule versions registered in `onyx/ton/financial_review/rules.py`: `NGF-SRC-ROW-REJECTED.v1`, `NGF-UNIT-MISSING.v1`, `NGF-DUP-EXACT.v1` and `NGF-DUP-DOC.v2` (blocking), `NGF-ACCT-LABEL-DRIFT.v1` and `NGF-UNIT-LABEL-DRIFT.v1` (non-blocking). Catalogued rules without an executor (for example `NGF-DUP-NEAR`, `NGF-HIST-*`, `NGF-XS-*`) SHALL NOT run.

#### Scenario: Same invoice in two document formats
- **WHEN** two rows share account, date, unit and gross amount and their document numbers differ only by year prefix and zero padding (for example 392 and 2600000000392)
- **THEN** `NGF-DUP-DOC` records one blocking finding with both rows as evidence

#### Scenario: Catalogued rule without executor
- **WHEN** a review runs
- **THEN** rules without an executor produce no findings and are not reported as operational

### Requirement: Findings feed the occurrence ledger
The system SHALL record each review finding through `record_detection__no_commit` into `Finding` and `Occurrence` with deterministic identity keys, evidence (sheet, row, values) and a recommendation, and SHALL never use an LLM to detect findings.

#### Scenario: Repeated detection
- **WHEN** the same identity key is detected again in the same lineage
- **THEN** the existing occurrence receives a repeat event instead of a duplicate occurrence

### Requirement: Reviewed dataset dispositions
The system SHALL classify each parsed record as ACCEPTED, JUSTIFIED_EXCEPTION, REVIEW_REQUIRED, CORRECTION_REQUIRED, SUPERSEDED_BY_CORRECTION or EXCLUDED_SOURCE_ERROR, and only ACCEPTED and JUSTIFIED_EXCEPTION records SHALL be downstream-safe.

#### Scenario: Unit missing accepted as risk
- **WHEN** a human accepts the risk of a record without unit with a justification
- **THEN** the record becomes JUSTIFIED_EXCEPTION, flows downstream under "(sem unidade)" and the decision is audited
