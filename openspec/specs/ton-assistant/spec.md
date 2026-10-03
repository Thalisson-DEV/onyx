# ton-assistant Specification

## Purpose
Linha de base do assistente TON: uma Persona coordenadora sobre o runtime de chat do Onyx, com
ferramentas TON somente leitura/publicação, especialistas como papéis internos (não nove
Personas) e Code Interpreter limitado (D-030..D-032). Código: `backend/onyx/prompts/ton/agent.py`,
`backend/onyx/ton/agent/*`, `backend/onyx/db/ton/agent.py`, `web/src/views/ton/ChatPage`.

## Requirements

### Requirement: Grounded answers through TON tools
The system SHALL answer business questions only from TON tools: `ton_list_sources`, `ton_get_source_status`, `ton_get_financial_context`, `ton_get_financial_review_summary`, `ton_list_findings`, `ton_get_finding`, `ton_get_dre_readiness`, `ton_get_dre_result`, `ton_get_readiness_evidence`, `ton_analyze_closing`, `ton_get_billing_summary`, `ton_get_budget_summary`, `ton_get_reconciliation_summary`, `ton_list_occurrences`, `ton_get_occurrence`, `ton_list_overdue_actions`, `ton_get_recent_changes`, `ton_generate_closing_report`, `ton_generate_executive_brief`; never from model memory.

#### Scenario: Persisted DRE exists
- **WHEN** the user asks for the June DRE of a scope that has a persisted calculation
- **THEN** the assistant returns the persisted values equal to the DRE screen

#### Scenario: No persisted calculation
- **WHEN** no calculation exists for the requested scope
- **THEN** the assistant says so and reports readiness only

### Requirement: Specialists as internal roles
The system SHALL treat CFO, AUDITOR and CEO as active internal roles with allowed tool lists, and COO, FROTA, CONTRATOS, COMPLIANCE, PROCUREMENT and RH as "aguardando fonte" with no tools.

#### Scenario: Specialist without source
- **WHEN** the specialists page is opened
- **THEN** each waiting specialist states what source it needs and performs no analysis

### Requirement: Safe output and explicit publication
The system SHALL hide internal identifiers and enums, translate states to business language, separate fact, evidence, interpretation, hypothesis and recommendation, publish reports only when explicitly asked, and treat Python results as exploratory calculations, never official values or decisions.

#### Scenario: Python used on tool numbers
- **WHEN** the assistant uses Python to sum values returned by tools
- **THEN** it names the source of the numbers and does not present the result as DRE or approved value

### Requirement: Known performance limitation
The system SHALL be treated as slow for analytical answers: it currently takes about 1.5 to 3 minutes (20+ steps), a known defect addressed by change `stabilize-real-data-runtime`; live demonstrations MUST use pre-generated conversations until then.

#### Scenario: Analytical question
- **WHEN** the user asks which blockers prevent publishing the DRE
- **THEN** the answer is grounded but may take more than one minute
