## Why

O princípio operacional do Prompt Mestre (§2) é atravessar a cadeia **CONTRATADO → PLANEJADO →
EXECUTADO → MEDIDO → FATURADO → RECEBIDO → CUSTO → MARGEM** e aplicar a **regra do elo**: o desvio
pertence ao elo em que a quantidade mudou (faturar 100% de coleta com produção de 97% é desvio de
medição/produção, não de faturamento). O passo 3 do protocolo monta essa régua por contrato e serviço,
marcando **[lacuna]** onde falta dado. Os testes T13 (execução × medição > 3% na curva A), T14
(medição × faturamento sem glosa formalizada), T15 (faturamento sem lastro), T16 (produção sem
faturamento) e T20 (prazo médio de recebimento > 45 dias) e a rotina **R4 — Reconciliação contratual**
(mensal D+3, Controladoria + Faturamento) dependem disso. Hoje só existe conciliação NG × faturamento
por nota.

## What Changes

- Novas fontes: **boletim de medição** (competência, contrato, serviço, quantidade e valor medidos,
  glosa) e **recebimento** (NF, data e valor recebido — extrato/conciliação ou contas a receber).
- Régua da cadeia por contrato × serviço × competência com quantidade e valor em cada elo e
  **[lacuna]** explícita; marcação do elo onde a quantidade muda.
- Testes T14, T15, T16 e T20 (T13 quando houver produção — change `production-domain`).
- Rotina R4 mensal D+3 com publicação sempre (mesmo sem achado), para Controladoria e Faturamento.

## Capabilities

### New Capabilities
- `contract-chain`: régua contratado→recebido, regra do elo, T13–T16, T20 e R4.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novos perfis de fonte, novo read model de cadeia, testes, rotina R4, ficha do contrato.

## Dependências

- Boletins de medição e dados de recebimento (Faturamento/Financeiro). `contract-master-registry`
  (serviços contratados, critérios de medição/faturamento, prazo de pagamento), `routine-framework`.

## Estado de dado

Real, quando as fontes forem fornecidas.
