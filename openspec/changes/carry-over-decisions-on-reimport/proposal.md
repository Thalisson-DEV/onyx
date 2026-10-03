## Why

Hoje uma nova importação do NG cria uma revisão do zero: as decisões já tomadas (a duplicidade da
NF 392, os 19 lançamentos sem unidade aceitos como risco) voltam como pendência, e qualquer
importação (NG, faturamento ou dotação) recalcula a base incluindo as três dotações, tirando a DRE
de "Pronta" (guia de apresentação de 2026-10-02, §0.1). O processo da Luyla é mensal e tem
correções retroativas (contexto 03 §1): reimportar é rotina, não exceção. Sem reaproveitar decisões,
o TON gera retrabalho a cada mês e fica impossível verificar se uma correção foi feita na origem
(Prompt Mestre §13, regra do ROI; §10, escalonamento por ciclos).

## What Changes

- Decisões de revisão (por achado) passam a ser reaplicadas numa nova revisão quando o mesmo achado
  reaparece com a mesma identidade e a mesma evidência; se a evidência mudou, volta para decisão.
- Achado decidido que **não** reaparece na nova importação fica registrado como "não detectado nesta
  importação" (insumo da verificação de ações).
- A seleção de entradas da normalização fica explícita: as dotações só entram quando o orçado estiver
  aprovado (change `budget-vs-actual`); importar faturamento ou dotação não muda o Realizado.
- Prévia de reimportação: antes de confirmar, o usuário vê quantas decisões serão reaproveitadas,
  quantas voltam para decisão e quantos achados novos surgem.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `ng-financial-review`: reaproveitamento de decisões entre revisões.
- `financial-readiness`: seleção explícita de entradas da normalização.

## Impact

- `backend/onyx/db/ton/financial_review.py`, `backend/onyx/db/ton/identity.py`,
  `backend/onyx/db/ton/financial_domain.py`, `backend/onyx/ton/client_import/service.py`.
- Fontes (UI de importação) e Pendências.

## Dependências

- Nenhuma externa. Validar com a Luyla se "mesma evidência" (mesma conta, data, unidade, documento e
  valores) é o critério correto para reaproveitar uma decisão.

## Estado de dado

Real: testar reimportando o NG jan–jun/2026 sobre a base atual (com backup).
