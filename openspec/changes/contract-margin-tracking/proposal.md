## Why

"Margem prevista × margem real é o indicador-mãe da diretoria" (Prompt Mestre §4.1). Em Mossoró:
prevista 16,89%; realizada jan/26 17,67%, fev 25,18%, mar 21,89%, abr −313,9% (distorção de
competência — receita de abril lançada em outra unidade). É a primeira pergunta da diretoria (§19:
"Quanto estamos ganhando em cada contrato?") e a dimensão Financeiro do ISC (§14.3). Hoje a DRE é por
unidade, sem margem prevista e sem leitura de distorção.

## What Changes

- Margem real mensal por contrato a partir da DRE da unidade vinculada (rateio só com regra aprovada
  quando a unidade tem mais de um contrato).
- Margem prevista do cadastro mestre (dotação confirmada).
- Série prevista × real com desvio em p.p. e em R$/mês; meses com base reprovada (S10) ou com
  violação de S1 aparecem como "não legível" com o motivo, nunca como número.
- Ranking de contratos só com unidades operacionais e meses legíveis.

## Capabilities

### New Capabilities
- `contract-margin`: margem contratual prevista × real por contrato e mês.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novo read model sobre DRE + cadastro mestre, tela do contrato, Visão Geral (resumo), ferramentas do
  CFO.

## Dependências

- `contract-master-registry`, `dotacao-composition-import`, `unit-classification-and-consolidation`,
  `sanity-battery` (S1/S10).

## Estado de dado

Real (Mossoró, Juazeiro-BA, Itabirito com dotação; demais "sem margem prevista").
