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

## Execução: OpenSpec (desde 2026-10-02)

O trabalho pendente do TON está especificado em **`openspec/`** na raiz do repositório:

- `openspec/config.yaml` — contexto do projeto e regras para todo artefato;
- `openspec/roadmap.md` — **roadmap completo**: estado × Prompt Mestre, fases 0–5 + produção,
  dependências, insumos externos, rastreabilidade S/T/R → change;
- `openspec/specs/` — linha de base **verificada no código** do que existe hoje;
- `openspec/changes/` — uma change por item pendente (proposta, specs, design quando necessário,
  tarefas).

Planos antigos em `plans/ton/` (FE-001..003, UX, overnight, backend/data) são histórico. O que
estiver pendente neles e ainda for válido foi incorporado às changes.

## Fontes originais relevantes

### Prompt Mestre
`TON VALE — PROMPT MESTRE v2.0`
No repositório: `plans/ton/masterprompt.md` (arquivo enviado pela Luyla; leitura integral obrigatória —
o digesto 02 resume, mas não substitui).

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

> Atualizado em 2026-10-02. Tabela detalhada por camada do Prompt Mestre: `openspec/roadmap.md` §1.
>
> **Leitura correta do projeto:** o TON pedido no Prompt Mestre é uma controladoria **por contrato**
> (cadastro mestre, cadeia contratado→recebido, T1–T30, ledger com dono/prazo/verificação, ROI,
> rotinas R1–R9, nove subagentes). O que está construído é a **fundação financeira** (fontes →
> revisão → prontidão → DRE) mais o shell do produto. Desde 2026-10-02 a base local tem **dados
> reais** jan–jun/2026 e DRE READY real (consolidado + unidades, só Realizado). Do Prompt Mestre,
> apenas S10 está operacional, T4 parcial e R3 ativa.

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

- integração direta NG/Keevo (TI liberando VPN + usuário read-only);
- DRE em Excel com memória de cálculo (pedido da Luyla em 2026-10-02; hoje só CSV);
- regras da DRE validadas pela Controladoria (parcelamentos, 392, receita, orçado, PIS/COFINS);
- reaproveitamento de decisões ao reimportar o NG;
- contrato de dados, protocolo de 7 passos com bloqueio, S1–S9, T1–T30, quantificação, régua
  PAD-CTRL-001, pontos cegos;
- operação do ledger (dono, prazo, verificação no ciclo seguinte, R9) e ROI;
- cadastro mestre de contratos, margem prevista × real, cadeia de medição/faturamento/recebimento;
- domínios frota, produção, RH, compras, compliance, banco; 6 dos 9 especialistas;
- rotinas R1, R2, R4–R9; ISC; Dinheiro Escondido; previsão;
- histórico 2025;
- produto em produção para a equipe da Luyla.

O próximo grande desafio do produto é transformar a fundação em uma **controladoria operacional realmente usada no dia a dia**, e não apenas uma demonstração bonita.

