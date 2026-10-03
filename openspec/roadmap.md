# TON — Roadmap completo de desenvolvimento

Atualizado em 2026-10-03 (após a reunião com a Luyla; ata em `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`). Fonte de intenção: `plans/ton/masterprompt.md` (Prompt Mestre v2.0).
Contexto: `plans/ton/context/`. Linha de base verificada no código: `openspec/specs/`.
Trabalho pendente: `openspec/changes/` (41 changes, cada uma com proposta, specs e tarefas).

---

## 1. O que o TON é (e o que ainda não é)

O TON é a **Controladoria Digital 24/7 de cada contrato** da Vale Norte. Ele cruza CONTRATO ×
OPERAÇÃO × FINANCEIRO × DOCUMENTAÇÃO × REGULAÇÃO, percorre a cadeia contratado → planejado →
executado → medido → faturado → recebido → custo → margem, encontra desvios com evidência, quantifica
em R$, prioriza pela régua do PAD-CTRL-001, registra num ledger com dono e prazo, verifica no ciclo
seguinte e mede o resultado financeiro (ROI). O indicador-mãe é **margem contratual prevista × real**.

O que existe hoje é a **fundação financeira** desse sistema. Ela está bem construída, mas é uma
fração do Prompt Mestre:

| Camada do Prompt Mestre | Estado em 2026-10-02 |
|---|---|
| Fontes rastreáveis, imutáveis (DATA-001/002/004ab) | ✅ NG, faturamento, dotação (só aba DOTAÇÃO), por arquivo |
| Revisão determinística NG (DATA-003) | ✅ 6 regras NGF ativas |
| Domínio canônico, prontidão, decisões versionadas, loop de decisão | ✅ |
| DRE gerencial (DATA-005/006) | ✅ READY real jan–jun/2026, consolidado + unidades, só Realizado, export CSV |
| Assistente com 19 ferramentas, Python, timeline | ⚠️ funciona, lento (1,5–3 min) |
| Rotina R3 (fechamento preliminar mensal) | ✅ agendada e manual |
| Shell de produto TON (FE-001..003) | ✅ |
| §3 Contrato de dados e níveis de confiança A–D | ❌ |
| §4 Cadastro mestre do contrato ("o cérebro") | ❌ (só identidade mínima) |
| §5 Protocolo de 7 passos com bloqueio | ⚠️ passos do R3 registrados, sem gate comum |
| §6 Sanidade S1–S10 | ⚠️ só S10 |
| §7 Testes T1–T12 | ⚠️ T4 parcial; demais ❌ |
| §8 Testes T13–T30 | ❌ |
| §9 Quantificação em R$ | ❌ ("não quantificado") |
| §10 Régua PAD-CTRL-001, NC, escalonamento | ⚠️ campos existem, sem cálculo |
| §11 Pontos cegos | ❌ |
| §12 Rotinas R1–R9 | ⚠️ só R3 |
| §13 Ledger de ocorrências / oportunidades / ROI | ⚠️ modelo pronto, sem operação |
| §14 Ficha de exceção, modo executivo, ISC, Dinheiro Escondido | ❌ |
| §15 Subagentes | ⚠️ 3 de 9 atuando (CFO, AUDITOR, CEO), só financeiro |
| §16 Regulação | ❌ |
| §17 Previsão e simulação de licitação | ❌ |
| Integração direta NG/Keevo | ❌ (VPN em liberação pela TI) |
| Integração Zeev (processos, liberações financeiras, SLA) | ⚠️ adaptador somente leitura + catálogo de 35 fluxos prontos (BE-004A/B); sem sincronização |
| Produção para a equipe da Luyla | ❌ (ambiente de validação local) |

---

## 1.1 Decisões da reunião de 2026-10-03

- **Prioridade agora é a DRE.** Contratos e dotações vêm depois.
- **Parcelamentos:** só a parcela paga, no mês do pagamento; a Luyla limpa o NG com o contador.
- **Relatório semanal de inconsistências por e-mail ao Financeiro**, com verificação de correção a
  cada extração (change nova `weekly-inconsistency-report`).
- **Correções sugeridas pelo TON sempre com aprovação humana.**
- **Classificação editável no TON** com conta nova acusada e regras de pré-classificação (change nova
  `account-classification-admin`).
- **Natureza × CNPJ do fornecedor** para não perder crédito de PIS/COFINS (change nova
  `supplier-nature-consistency`, depende do NG por VPN).
- Frota lançada direto no TON; PIS/COFINS pela planilha Excel dela; 2025 pela VPN.

## 2. Princípios de ordenação

1. **Base confiável antes de inteligência.** Nada novo sobre runtime não reprodutível (Fase 0).
2. **Primeiro o que a Controladoria já usa todo mês:** DRE oficial em Excel, com regras validadas por
   ela (Fase 1). É o que gera confiança e adoção.
3. **Depois o motor do Prompt Mestre** sobre os dados que já existem (Fase 2): os testes T1–T12, a
   sanidade e o ledger funcionam com NG + faturamento, sem esperar novas fontes.
4. **Contrato como cérebro** (Fase 3) desbloqueia margem prevista × real e quase todo o §8.
5. **Domínios operacionais na ordem de prioridade da Luyla** (Fase 4).
6. **Autonomia e valor** quando há regras, ledger e verificação para automatizar (Fase 5).
7. **Produção** como trilha paralela assim que a Fase 1 estiver aceita.
8. Toda fase entrega algo **demonstrável com dado real**, e cada change atualiza a cobertura do
   Prompt Mestre no produto (`capabilities.py`/`registry.py`).

---

## 3. Fases

Tamanho relativo: P (até ~2 dias de trabalho de agente), M (~1 semana), G (> 1 semana). Sem datas:
dependem de insumos externos.

### Fase 0 — Estabilizar a base real (agora)

| Change | O quê | Tam. | Depende de |
|---|---|---|---|
| `stabilize-real-data-runtime` | Rebuild das imagens (fim do `docker cp`), assistente rápido e correto, cards honestos, identidade de dotação, papel cliente validado, renomes pedidos (Unidades/filiais, Compras/Suprimentos) | M | — |
| `visual-polish` | Base visual sóbria (sem cara de IA), gaveta da DRE em tabela, status corretos, textos sem termos técnicos; tela a tela | M | — |
| `carry-over-decisions-on-reimport` | Reimportar o NG sem perder decisões; dotação não altera a DRE; prévia de reimportação | M | — |
| `controller-validated-treatments` | Parcelamentos pela parcela paga (decidido), 392 (decidido), receita/folha/mútuos (segunda) viram tratamentos versionados | M | Reunião 2026-10-05 para o restante |

**Marco:** a DRE real jan–jun/2026 sobrevive a uma reimportação, com as regras da Controladoria
aplicadas e rastreáveis; o assistente responde em < 45 s com números iguais às telas.

### Fase 1 — Fechamento oficial confiável

Ordem dentro da fase, conforme a reunião: (1) `ng-direct-integration`, (2) `weekly-inconsistency-report`,
(3) `dre-excel-export`, (4) `account-classification-admin`, (5) `history-2025-baseline` (pela VPN),
(6) `pis-cofins-source` (planilha da Luyla), (7) `unit-classification-and-consolidation`.
`budget-vs-actual` desce para depois da compatibilização dotação → natureza pela Controladoria.

| Change | O quê | Tam. | Depende de |
|---|---|---|---|
| `dre-excel-export` | DRE em Excel com fórmulas e aba Base (pedido da Luyla) | M | Fase 0 |
| `unit-classification-and-consolidation` | Operacional × não operacional; resultado operacional; ressalva no consolidado | P | C3 da Luyla |
| `pis-cofins-source` | Apuração da Contabilidade na linha de impostos | M | Arquivo estruturado, R3 da Luyla |
| `budget-vs-actual` | Orçado × realizado das dotações aprovadas | M | O1–O3 da Luyla, carry-over |
| `history-2025-baseline` | Histórico 2025 e comparação anual | M | NG 2025 autorizado |
| `ng-direct-integration` | Conector somente leitura via VPN, modo sombra → primário | G | TI (Celso): VPN, SGBD, usuário read-only |
| `weekly-inconsistency-report` | E-mail semanal ao Financeiro com as inconsistências abertas; verificação de correção a cada extração (pedido da Luyla) | M | SMTP, e-mails do Financeiro |
| `account-classification-admin` | Tabela de classificação editável no TON, conta nova acusada, regras de pré-classificação, 29 códigos a confirmar | M | Regras da Controladoria |
| `zeev-integration` | BE-004C: sincronizar os fluxos Zeev escolhidos (liberações financeiras, aprovações, contratos, certidões, desligamentos) como snapshots; fatos de aprovação e SLA | G | 8 perguntas do catálogo Zeev à Luyla |

**Marco:** a Luyla fecha um mês usando o Excel do TON lado a lado com o BI, com diferenças explicadas;
o NG chega sem upload manual (quando o acesso existir); os fluxos Zeev vigentes sincronizam sozinhos.

### Fase 2 — Motor de controle do Prompt Mestre

Pode começar em paralelo à Fase 1 depois da Fase 0.

| Change | O quê | Tam. | Depende de |
|---|---|---|---|
| `data-contract-and-trust-levels` | Bases canônicas (§3.1), conformidade, níveis A–D em todo número | M | — |
| `execution-protocol` | 7 passos com bloqueio, insumos ausentes, pontos cegos (§11), teto 7/12 | G | data-contract |
| `sanity-battery` | S4, S5, S6, S8 agora; framework para S1–S3, S7, S9 | M | protocol |
| `financial-test-battery` | T1–T11 sobre NG/faturamento (T12 no RH) | G | protocol, criticality |
| `criticality-and-nc-catalog` | Régua PAD-CTRL-001, prazos, escalonamento, catálogo NC | M | **PAD-CTRL-001** |
| `impact-quantification` | Impacto em R$, categorias, confiança, rótulo de estimativa | M | data-contract |
| `supplier-nature-consistency` | Natureza × CNPJ/atividade do fornecedor (crédito de PIS/COFINS), unidade pela cidade do fornecedor, com aprovação | M | CNPJ via NG direto |
| `occurrence-ledger-workflow` | Tela do ledger; dono, prazo, status, ciclos, export | M | criticality |
| `action-verification` | Critério de verificação, checagem no ciclo seguinte, R9 | M | ledger, carry-over |
| `exception-card-and-executive-mode` | Ficha de 10 campos, modo executivo, 7 perguntas | M | quantification, ledger |

**Marco:** o fechamento de uma competência real roda os 7 passos, publica no máximo 12 fichas de
exceção quantificadas, cada uma com dono e prazo, e no mês seguinte o TON diz sozinho o que foi
corrigido (ex.: a 392 sumiu do NG).

### Fase 3 — Contrato como cérebro

| Change | O quê | Tam. | Depende de |
|---|---|---|---|
| `contract-master-registry` | Cadastro mestre §4, eventos contratuais, completude, vínculos (começando pela planilha de controle de contratos) | G | Planilha de contratos (Luyla mostra em 05/10) |
| `dotacao-composition-import` | Composição, ABC, BDI, MO, frota, reserva, DP-01; margem prevista | G | contract-master |
| `backlog-import-and-sanity` | Backlog JUL/2026 + S1/S2/S3/S4/S7; declarado × saneado | M | **Arquivo do backlog**, sanity |
| `contract-margin-tracking` | Margem prevista × real por contrato (indicador-mãe) | M | master, dotação, unidades |
| `contract-chain-reconciliation` | Cadeia contratado→recebido, regra do elo, T13–T16, T20, R4 | G | Medição e recebimento |
| `contract-sentinels` | T17–T19, R7, R8 | P | master, chain |

**Marco:** Mossoró-RN 02/2023 com cadastro completo, margem prevista 16,89% × real mês a mês, cadeia
montada com lacunas explícitas, e as calibrações do §6.2 do backlog encontradas pelo TON.

### Fase 4 — Domínios operacionais (ordem a definir pela Luyla)

| Change | O quê | Tam. | Fonte necessária |
|---|---|---|---|
| `fleet-fuel-domain` | Cadastro de frota no TON (substitui a planilha), T21–T24, R2, TON FROTA | G | Planilha de frota (Igor), abastecimento, manutenção |
| `production-domain` | S9, T25, T26, habilita T13; TON COO | M | Produção/apontamento |
| `hr-payroll-domain` | T12, T27–T29, LGPD; TON RH | G | Folha, DP-01/02, ponto |
| `procurement-domain` | T30, T8, locações; TON PROCUREMENT | M | Compras com fornecedor |
| `compliance-regulatory-domain` | Matriz de obrigações; TON COMPLIANCE | M | Documentos de evidência |
| `bank-reconciliation-cash` | Banco × NG, duplicidade de pagamento, fundo fixo, DFC | G | Extratos bancários |

**Marco:** os 9 especialistas atuando com fontes reais; T1–T30 com cobertura OPERACIONAL ou
BLOQUEADA com motivo.

### Fase 5 — Inteligência, autonomia e valor

| Change | O quê | Tam. | Depende de |
|---|---|---|---|
| `routine-framework` | R1–R9 declarativas, silêncio, destinatários, e-mail; R1 e R6 | G | protocol; R1 exige NG diário |
| `hidden-money-and-roi` | Ledger de oportunidades, painel Dinheiro Escondido, R5, ROI | M | quantification, verification |
| `contract-health-index` | ISC 0–100 com pesos do §14.3 | M | domínios |
| `specialist-subagents` | Contrato de especialista, delegação, handoff, CEO em 5 linhas | M | domínios |
| `forecast-and-bid-simulation` | 3 cenários (≥ 6 competências) e simulação de licitação | G | histórico, custos unitários |

**Marco:** o TON roda sozinho pela agenda do PAD-CTRL-001, fala só acima do limiar, e o painel
Dinheiro Escondido mostra identificado × realizado verificado.

### Trilha transversal — Produção

| Change | O quê | Tam. | Depende de |
|---|---|---|---|
| `production-deployment` | Host, VPN a partir do host, backups testados, papéis, retenção, pipeline | G | Hospedagem e usuários (Vale Norte) |

Começar assim que a Fase 1 for aceita. Sem produção não existe uso diário.

---

## 4. Grafo de dependências (resumo)

```text
stabilize ─┬─> carry-over ─┬─> budget-vs-actual
           │               └─> action-verification
           ├─> treatments ──> dre-excel-export
           └─> data-contract ─> execution-protocol ─┬─> sanity-battery ──> backlog-import
                                                    ├─> financial-tests (+ criticality)
                                                    └─> routine-framework
criticality ─> ledger-workflow ─> action-verification ─> hidden-money
impact-quantification ─┬─> criticality
                       └─> exception-card
contract-master ─┬─> dotacao-composition ─> contract-margin ─> contract-health-index
                 ├─> contract-chain ─> contract-sentinels
                 └─> compliance-domain
unit-classification ─> contract-margin, financial-tests (T4)
history-2025 ─> forecast ; ng-direct ─> R1 (routine-framework), production-deployment
zeev-integration ─> financial-tests (pagamento × aprovação), execution-protocol (ponto cego),
                    contract-master (contrato assinado), hr (T12), fleet (T23), compliance (certidões)
production/fleet/hr/procurement ─> specialist-subagents, contract-health-index, forecast
```

---

## 5. Insumos a pedir (consolidado)

| Insumo | De quem | Desbloqueia |
|---|---|---|
| Respostas C1–C3, D1–D3, P1–P3, R1–R3, O1–O3, F1–F3 (guia de apresentação §6) | Luyla | treatments, units, budget, pis-cofins |
| **PAD-CTRL-001** (régua, NC-01..14, testes, calendário D0–D+12, insumos obrigatórios) | Luyla | criticality, protocol, rotinas |
| Apuração PIS/COFINS em XLSX/CSV | Contabilidade | pis-cofins-source |
| NG 2025 "ok" | Luyla | history-2025 |
| VPN, endereço, SGBD, usuário read-only, dicionário de dados | TI (Celso) | ng-direct |
| Respostas às 8 perguntas do catálogo Zeev (fluxos vigentes, variantes de liberação, cópias/testes, arquivos) + credencial de serviço somente leitura | Luyla / admin do Zeev | zeev-integration |
| BACK LOG CTs VALE NORTE (JUL/2026) | Luyla | backlog |
| Contratos, editais, aditivos, apostilamentos; gestor nominal por contrato | Luyla/Jurídico | contract-master |
| Confirmação das abas oficiais das dotações | João Hebert | dotacao-composition |
| Boletins de medição; recebimentos | Faturamento/Financeiro | contract-chain |
| Frota, abastecimento, manutenção, postos | Unidades/Frota | fleet |
| Produção/apontamento | Operação | production |
| Folha analítica, DP-01/02, ponto; papéis de acesso a dado pessoal | DP/Luyla | hr |
| Compras com fornecedor; locações | Compras/Financeiro | procurement |
| Extratos bancários detalhados | Financeiro | bank-reconciliation |
| Responsáveis nominais por tipo de pendência; destinatários das rotinas | Luyla | ledger, routines |
| Hospedagem, usuários e papéis, política de retenção | Vale Norte | production-deployment |

## 6. Decisões em aberto que atravessam fases

- Faixa T13–T26 (título do §8) × T13–T30 (corpo) — decision-log nº 11.
- Runtime dos especialistas: papéis internos × sub-agente do Onyx (contexto 05 §3).
- Fonte oficial de folha na DRE: NG × relatório de folha.
- Receita da DRE: NG líquida de retenções × faturamento bruto.
- Prioridade da Fase 4 (opções G, F, H da apresentação).

## 7. Rastreabilidade Prompt Mestre → change

| Código | Change |
|---|---|
| S1, S2, S3, S7 | `backlog-import-and-sanity` (framework em `sanity-battery`) |
| S4, S5, S6, S8, S10 | `sanity-battery` |
| S9 | `production-domain` |
| T1–T11 | `financial-test-battery` (T4 também `unit-classification…`) |
| T12, T27, T28, T29 | `hr-payroll-domain` |
| T13, T14, T15, T16, T20 | `contract-chain-reconciliation` (T13 com `production-domain`) |
| T17, T18, T19 | `contract-sentinels` |
| T21, T22, T23, T24 | `fleet-fuel-domain` |
| T25, T26 | `production-domain` |
| T30 (e T8) | `procurement-domain` |
| R1, R6 (e migração R3) | `routine-framework` |
| R2 | `fleet-fuel-domain` |
| R4 | `contract-chain-reconciliation` |
| R5 | `hidden-money-and-roi` |
| R7, R8 | `contract-sentinels` |
| R9 | `action-verification` |
| §3 contrato de dados / §3.4 níveis | `data-contract-and-trust-levels` |
| §3.3 unidades | `unit-classification-and-consolidation` |
| §4 cadastro mestre | `contract-master-registry`, `dotacao-composition-import` |
| §5 protocolo / §11 pontos cegos | `execution-protocol` |
| §9 quantificação | `impact-quantification` |
| §10 criticidade / NC | `criticality-and-nc-catalog` |
| §13.1 ledger | `occurrence-ledger-workflow`, `action-verification` |
| §13.2, §13.3, §14.4 | `hidden-money-and-roi` |
| §14.1, §14.2, §19 | `exception-card-and-executive-mode` |
| §14.3 ISC | `contract-health-index` |
| §15 subagentes | `specialist-subagents` (+ cada domínio ativa o seu) |
| §16 regulação | `compliance-regulatory-domain` |
| §17 previsão / licitação | `forecast-and-bid-simulation` |
| Pedido do cliente: DRE em Excel | `dre-excel-export` |
| Pedido do cliente: relatório semanal de inconsistências | `weekly-inconsistency-report` |
| Pedido do cliente: classificação editável | `account-classification-admin` |
| Pedido do cliente: natureza × CNPJ / crédito PIS-COFINS; T8 | `supplier-nature-consistency` |
| Zeev (processos, aprovações, SLA; `NGF-XS-APPROVAL-MISSING`; ponto cego "processo sem rastreabilidade") | `zeev-integration` |
| Processo da Luyla: PIS/COFINS, orçado, banco | `pis-cofins-source`, `budget-vs-actual`, `bank-reconciliation-cash` |

---

## 8. Como um agente trabalha com este roadmap

1. Ler `openspec/config.yaml`, este roadmap, `plans/ton/context/00..10` e o Prompt Mestre.
2. Escolher a próxima change desbloqueada (Fase e dependências acima). `openspec list` mostra o
   progresso; `openspec show <change>` mostra a proposta.
3. Ler `proposal.md`, `design.md` (quando houver) e `specs/**/spec.md`; conferir com o código atual.
   Se o código divergir da spec, o código é a verdade — atualizar a spec antes de implementar.
4. Implementar seguindo `tasks.md`, marcando `- [x]` a cada tarefa concluída e validada.
5. Ao concluir: testes, validação no Chrome quando houver UI, `openspec validate <change> --strict`,
   `openspec archive <change>` (atualiza `openspec/specs/`), atualizar a tabela de estado (§1) e as
   fases deste roadmap, e o contexto em `plans/ton/context/` se o estado do produto mudou.
6. Insumo externo faltando: marcar a tarefa como bloqueada no `tasks.md`, registrar no §5 e seguir
   com outra change independente. Nunca inventar dado para destravar.
