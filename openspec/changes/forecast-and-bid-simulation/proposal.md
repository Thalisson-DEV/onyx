## Why

O Prompt Mestre §17 pede o **modo previsão** (receita, margem, caixa, manutenção, consumo, produção,
demanda, necessidade de frota e pessoal, risco de déficit) só com no mínimo 6 competências fechadas,
sempre em três cenários com premissas explícitas e reapresentando o desvio do forecast anterior × o
realizado; sazonalidade conhecida entra como premissa nomeada. O §17.1 pede a **simulação de
licitação**: receita proposta − MO − frota − combustível − manutenção − terceiros − administrativo −
impostos = resultado e margem, com custo unitário do realizado das unidades comparáveis (não a dotação
teórica), entregando o preço mínimo para a margem-alvo e o ponto em que o contrato destrói valor.

## What Changes

- Forecast por unidade/contrato em três cenários (otimista, base, pessimista) com premissas
  explícitas e versionadas; bloqueado com menos de 6 competências fechadas.
- Registro do forecast e comparação forecast anterior × realizado a cada fechamento.
- Sazonalidade como premissa nomeada (base: histórico de coleta 2021/2022 das dotações), nunca ajuste
  silencioso.
- Simulador de licitação com custos unitários do realizado de unidades comparáveis, preço mínimo para
  margem-alvo e ponto de destruição de valor.

## Capabilities

### New Capabilities
- `forecast`: previsão em três cenários e simulação de licitação.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novo serviço de projeção (determinístico, premissas explícitas), telas de previsão e simulação,
  ferramentas do CFO.

## Dependências

- `history-2025-baseline` (cobertura), `contract-margin-tracking`, `production-domain` e
  `fleet-fuel-domain` para custos unitários comparáveis; premissas aprovadas pela Controladoria.

## Estado de dado

Real; indisponível até haver 6 competências fechadas legíveis por escopo.
