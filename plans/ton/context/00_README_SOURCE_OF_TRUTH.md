# TON — CONTEXT PACKAGE / README

## Objetivo

Este pacote foi criado para dar a um novo agente de desenvolvimento o máximo de contexto confiável possível sobre o projeto TON, desde a origem até o estado atual.

Ele complementa as specs/roadmaps de execução. Não substitui a leitura do código atual.

## Regra principal

**O repositório e os contratos executáveis atuais são a verdade de implementação.**

Este pacote é contexto histórico, de negócio, arquitetura e produto.

Quando existir conflito:

1. código/API atual;
2. decisões explicitamente aprovadas e ainda vigentes;
3. Prompt Mestre v2.0;
4. documentação de processo da Luyla;
5. planos históricos;
6. relatórios de agentes antigos.

Não assuma que um plano antigo continua válido apenas porque está em `plans/`.

## Leitura recomendada

Leia nesta ordem:

1. `00_README_SOURCE_OF_TRUTH.md`
2. `01_PROJECT_ORIGIN_AND_OBJECTIVE.md`
3. `02_PROMPT_MASTER_DIGEST.md`
4. `03_CLIENT_PROCESS_AND_FINANCIAL_PROBLEMS.md`
5. `04_DATA_EVOLUTION_001_006.md`
6. `05_CURRENT_ARCHITECTURE.md`
7. `06_FRONTEND_PRODUCT_EVOLUTION.md`
8. `07_DECISIONS_BOUNDARIES_AND_NONNEGOTIABLES.md`
9. `08_REAL_VS_SYNTHETIC_AND_EXTERNAL_DEPENDENCIES.md`
10. `09_CURRENT_GAPS_AND_PRODUCT_OPPORTUNITIES.md`
11. `10_AGENT_ONBOARDING_AND_EXECUTION_RULES.md`

Depois compare tudo com o estado atual do repositório.

## Fontes originais relevantes

### Prompt Mestre
`TON VALE — PROMPT MESTRE v2.0`
Arquivo original conhecido no acervo: `Markdown(1).md colado.md`

### Problemas financeiros/operacionais da Luyla
`Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt`

### Especificação / operação financeira
`POP-CTR-01 — Controladoria v2.0`

### Apresentação conceitual
`apresentacao_TON_proposta_seria.html`

### Planos de implementação
- `TON_OVERNIGHT_CODEX_SPEC.md`
- `TON_DEMO_FIRST_OVERNIGHT_SPEC.md`
- `TON_DEMO_FIRST_OVERNIGHT_SPEC_V2.md`
- `TON_DEMO_FIRST_TASKS.md`
- `TON_DEMO_FIRST_TASKS_VALIDATION_V2.md`
- `UX-001_TON_PRODUCT_EXPERIENCE_SPEC.md`
- `UX-002_TASKS_VALIDATION.md`
- `TON-FE-002_PRODUCT_MATURITY_ROADMAP.md`
- `TON-FE-003_PRODUCT_EVOLUTION_ROADMAP.md`

### Histórico técnico DATA
Os planos executáveis DATA-001 a DATA-006 estão em `plans/ton/data/` quando presentes.

## Estado atual resumido

O TON já tem:

- backend financeiro versionado;
- fontes/importações manuais;
- revisão determinística;
- readiness;
- DRE versionada;
- workspace de pendências;
- relatórios;
- rotinas;
- especialistas;
- ferramentas do agente;
- chat;
- Code Interpreter/infraestrutura Onyx;
- shell frontend próprio Vale Norte/TON;
- experiência P0 demonstrável.

Ainda NÃO tem:

- integração direta NG/Keevo via VPN/API/read-only DB;
- cobertura real validada de todos os domínios operacionais;
- fechamento financeiro real com 2025/2026 vivo;
- todos os especialistas alimentados por fontes reais;
- loop completo de resolução de pendência → recalcular → verificar correção com dados reais;
- produto final em produção.

O próximo grande desafio do produto é transformar a fundação em uma **controladoria operacional realmente usada no dia a dia**, e não apenas uma demonstração bonita.

