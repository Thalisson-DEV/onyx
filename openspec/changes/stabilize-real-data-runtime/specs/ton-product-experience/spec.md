## ADDED Requirements

### Requirement: Specialist statements derived from persisted state
Specialist cards and summaries SHALL describe what the specialist actually did in the referenced analysis run and SHALL NOT contradict persisted state (for example, claim that no DRE exists when a persisted calculation exists for the scope).

#### Scenario: DRE calculated
- **WHEN** a persisted DRE calculation exists for the period and the specialist did not calculate it in this run
- **THEN** the card says the DRE was read from the persisted calculation, not that none exists

### Requirement: Client role end-to-end validation
The product SHALL be validated with a user in the Controladoria role without administrator rights across Visão Geral, Fontes, Fechamento, DRE, Pendências, Relatórios and Assistente, and every permission error SHALL show a business message.

#### Scenario: Controladoria user decides a pending item
- **WHEN** a non-admin Controladoria user records a decision
- **THEN** the decision is saved under that user, and technical administration stays unreachable
