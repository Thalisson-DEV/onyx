# occurrence-ledger Specification

## Purpose
Linha de base do ledger de ocorrências (Prompt Mestre §13.1; plano backend 003c). O modelo está
completo, mas hoje só a revisão NG o alimenta e quase nenhuma ocorrência tem responsável, prazo,
impacto ou verificação. Código: `backend/onyx/db/ton/{occurrences,occurrence_records,
agent_occurrences,findings,identity,rule_versions,acl}.py`; tabelas `ton_occurrence*`,
`ton_finding*`, `ton_rule`, `ton_rule_version`.

## Requirements

### Requirement: Event-sourced occurrences with deterministic identity
The system SHALL keep each occurrence as an event-sourced record (`ton_occurrence_event`) whose projection must match its history, identified by a deterministic identity key derived from the rule version identity components, with supersede generations when the rule version changes.

#### Scenario: Rule version changed
- **WHEN** a detection repeats under a different rule version
- **THEN** the previous occurrence is superseded and a successor shares its logical identity key

### Requirement: Ledger fields available in the model
The system SHALL store per occurrence: short code, rule and rule version, owning domain (handoff rule §15) plus impacted domains, ledger kind (EXCEPTION or OPPORTUNITY), criticality, optional NC code, optional business unit and contract, impacts (category, confidence, method, unit cost source, predicted and realized amount, verification time), assignments (responsible, deadline, status) and notes.

#### Scenario: Impact with low confidence
- **WHEN** an impact with confidence Baixa is evaluated for ROI
- **THEN** `is_roi_eligible` returns false

### Requirement: Lifecycle operations exist at the database layer
The system SHALL provide database operations for detection, transition, resolution, verification, escalation by cycle rule, assignment and notes, and an API for listing overdue actions (`GET /api/ton/agent/actions/overdue`). There is no product UI or routine yet to assign owners, set deadlines, escalate or verify (see changes `occurrence-ledger-workflow` and `action-verification`).

#### Scenario: Overdue list without assignments
- **WHEN** no occurrence has an assignment with a past deadline
- **THEN** the overdue list is empty and nothing is reported as late
