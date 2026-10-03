## Why

O backlog contratual ("BACK LOG CTs VALE NORTE", JUL/2026) é a base de projeção institucional da
empresa e, segundo o Prompt Mestre §6.2, está **errado hoje** de formas verificáveis: Juazeiro do Norte
com margem de 187% (S1), Juazeiro-BA 153% (S1), Canoas-RS 1.020% e em julgamento (S1 e S7, projeção de
R$ 1,295 bi no total), Toledo e Itabirito com saldo a realizar = valor total ignorando meses executados
(S2 — Toledo com R$ 9,75 mi de excesso), subtotal de saldo R$ 362,7 mi > valor total R$ 235,1 mi
(S2/S4). Essas são as calibrações-gabarito do agente: o TON precisa encontrá-las sozinho. O backlog
não está no TON e o arquivo não está no repositório.

## What Changes

- Fonte "Backlog contratual" com perfil determinístico (item, contratante, valor total, valor mensal,
  prazo a realizar, saldo, margem média, resultado projetado, status de assinatura).
- Regras **S1** (margem ∈ [−100%, +60%]), **S2** (saldo = mensal × prazo, ±2%), **S3** (resultado
  projetado = margem mensal × prazo), **S4** (subtotais ±0,5%) e **S7** (contrato não assinado fora de
  backlog/receita/projeção) sobre cada versão do backlog.
- Visão "backlog declarado × backlog saneado" lado a lado (sem nunca sobrescrever o declarado): itens
  com S1 violado ficam com valor bloqueado; não assinados saem; saldo recalculado quando S2 falha.
- Conferência cruzada backlog × cadastro mestre (valores e vigência).

## Capabilities

### New Capabilities
- `contract-backlog`: importação do backlog, sanidade S1/S2/S3/S4/S7 e visão saneada.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novo perfil em `operational_import`, regras na bateria de sanidade, UI em Contratos, relatórios.

## Dependências

- **Arquivo do backlog** (pedir à Luyla). `sanity-battery` (framework). `contract-master-registry` para
  status de assinatura e cruzamento.

## Estado de dado

Real, quando fornecido. Aceite = reproduzir as calibrações do §6.2.
