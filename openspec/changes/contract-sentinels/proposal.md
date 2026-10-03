## Why

Dinheiro que escapa em silêncio nos contratos públicos: reajuste vencido e não faturado, saldo que
acaba antes do aditivo, contrato que vence sem prorrogação preparada, município que paga tarde.
O Prompt Mestre §8 define T17 (data-base de reajuste vencida há > 30 dias sem alteração do valor
mensal faturado), T18 (saldo insuficiente para 4 meses no ritmo atual → necessidade de aditivo), T19
(alertas a 180, 120, 90 e 60 dias do fim) e o §12 as rotinas **R7 — Sentinela de vigência e reajuste**
(semanal, segunda 07h, Controladoria + Jurídico) e **R8 — Sentinela de recebimento** (semanal, PMR
> 45 dias, Financeiro).

## What Changes

- Testes T17, T18 e T19 sobre o cadastro mestre + faturamento.
- R7 semanal (segunda 07h) publicando só quando um marco é atingido; R8 semanal publicando quando T20
  passa de 45 dias.
- Conclusões que dependem de interpretação contratual/jurídica saem como "Ponto para validação
  jurídica" (§12.1, §16) — o TON não afirma descumprimento.

## Capabilities

### New Capabilities
- `contract-sentinels`: T17–T19 e rotinas R7/R8.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Testes sobre cadastro mestre, rotinas no framework, notificações para Jurídico e Financeiro.

## Dependências

- `contract-master-registry` (índice e data-base de reajuste, vigência, saldo), `contract-chain-reconciliation`
  (T20), `routine-framework`.

## Estado de dado

Real, após o cadastro mestre.
