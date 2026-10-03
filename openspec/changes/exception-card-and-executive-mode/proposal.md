## Why

O Prompt Mestre §14 fixa os formatos de saída e o §19 diz que uma entrega que não responde a nenhuma
das sete perguntas da diretoria não deveria ter sido emitida. Hoje o relatório do R3 e o assistente
usam SITUAÇÃO/EVIDÊNCIA/IMPACTO/RECOMENDAÇÃO/PRÓXIMA AÇÃO/LIMITAÇÃO — próximo, mas não é a **ficha de
exceção** de 10 campos (§14.1), nem o **modo executivo** RESULTADO → PROBLEMA → IMPACTO → CAUSA → AÇÃO
em no máximo 5 linhas por tema (§14.2). A regra de ouro (§18) exige que nenhum problema seja mostrado
sem impacto estimado, causa provável, evidência e ação recomendada.

## What Changes

- **Ficha de exceção** como componente canônico (backend serializa, frontend e relatórios renderizam):
  criticidade + título, contrato/unidade · competência · teste · NC, e os 10 campos (o que aconteceu,
  evidência com nível, desvio, causa provável rotulada, impacto, risco, ação no infinitivo,
  responsável, prazo, como verificar).
- **Modo executivo** para a diretoria (relatório executivo e resposta do TON CEO), máximo 5 linhas por
  tema, sem despejo de dados.
- Checagem das **7 perguntas** em cada entrega executiva: quais foram respondidas e quais não podem
  ser respondidas por falta de fonte (dita explicitamente).
- Campo ausente na ficha aparece como lacuna nomeada ("causa provável: não determinada — falta
  <insumo>"), nunca omitido.

## Capabilities

### New Capabilities
- `output-formats`: ficha de exceção, modo executivo e checagem das sete perguntas.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/ton/agent/rendering.py`, `backend/onyx/db/ton/reports.py`, prompt do TON, componentes
  de relatório e chat no frontend.

## Dependências

- `impact-quantification`, `criticality-and-nc-catalog`, `occurrence-ledger-workflow` (responsável,
  prazo), `action-verification` (como verificar).

## Estado de dado

Real.
