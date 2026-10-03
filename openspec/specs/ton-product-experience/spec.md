# ton-product-experience Specification

## Purpose
Linha de base da experiência cliente TON (FE-001..FE-003): shell Vale Norte/TON próprio sobre o
Onyx, pt-BR, superfícies Visão Geral, Assistente, Fechamento (Visão geral, DRE, Pendências),
Automações, Relatórios, Fontes, Especialistas, Conversas e Administração do TON separada da
administração técnica do Onyx. Código: `web/src/app/ton/*`, `web/src/views/ton/*`, `web/src/lib/ton/*`.

## Requirements

### Requirement: Product truth comes from the backend
The system SHALL render statuses, blockers, specialist availability, routine schedules, mappings and DRE values from backend read models and SHALL NOT implement financial rules in React.

#### Scenario: Before and after display
- **WHEN** the UI shows a readiness delta
- **THEN** it is the difference between two backend responses, not a client-side calculation

### Requirement: Unified work queue from persisted state
The system SHALL show "O que precisa de você hoje" in Visão Geral and Fechamento ordered deterministically (broken source, apply decisions, decide, data, follow-up), with owner and deadline only when an occurrence assignment exists.

#### Scenario: No assignments
- **WHEN** no occurrence has a responsible person
- **THEN** queue items show no owner or deadline instead of invented ones

### Requirement: Honest data provenance labels
The system SHALL show the synthetic-data banner only when `TON_DEMO_SYNTHETIC_DATA=true`, label missing integrations as missing, and never show synthetic READY states as real.

#### Scenario: Real data environment
- **WHEN** `TON_DEMO_SYNTHETIC_DATA` is false
- **THEN** no synthetic banner appears and reports say the data comes from authorized sources

### Requirement: Client users stay inside TON
The system SHALL keep Controladoria users inside the TON shell; technical Onyx administration (agents, providers, MCP, connectors) is reachable only by administrators. Validation with a non-admin client role is still pending.

#### Scenario: Admin returns to TON
- **WHEN** an administrator leaves technical administration
- **THEN** they return to the TON shell
