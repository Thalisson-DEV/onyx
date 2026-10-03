## Why

O Prompt Mestre §14.3 define o **Índice de Saúde do Contrato (ISC)**, nota 0–100 por contrato com pesos
fechados — Financeiro 20, Faturamento 15, Operacional 15, Frota 12, Consumo 10, Pessoas 10, Compliance
10, Risco contratual 8 — com a regra de só publicar dimensão cujo dado exista (as demais "não
avaliadas", peso redistribuído e ressalva explícita), sempre com a leitura "onde está concentrada a
perda potencial de margem". É a resposta compacta para "como estão nossos contratos?" (TON CEO).

## What Changes

- Cálculo do ISC por contrato e competência a partir das dimensões disponíveis, cada uma 0–100 com a
  base de cálculo do §14.3.
- Redistribuição de peso para dimensões não avaliadas, com ressalva listando-as.
- Leitura textual determinística da concentração de perda potencial (dimensão com maior perda
  ponderada e ocorrências associadas).
- Exibição na lista de contratos, ficha do contrato e pacote executivo.

## Capabilities

### New Capabilities
- `contract-health-index`: ISC por contrato com pesos do §14.3 e dimensões não avaliadas explícitas.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Read model sobre margem, cadeia, frota, RH, compliance e sentinelas; telas de contrato; R6.

## Dependências

- `contract-margin-tracking` (Financeiro); `contract-chain-reconciliation` (Faturamento);
  `production-domain` (Operacional); `fleet-fuel-domain` (Frota, Consumo); `hr-payroll-domain`
  (Pessoas); `compliance-regulatory-domain` (Compliance); `contract-sentinels` (Risco). A fórmula de
  0–100 de cada dimensão precisa de aprovação da Controladoria.

## Estado de dado

Real; nasce parcial (só Financeiro) e cresce com os domínios.
