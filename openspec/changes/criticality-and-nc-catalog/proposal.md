## Why

O Prompt Mestre §10 manda usar a **régua única do PAD-CTRL-001**, sem régua paralela: 🔴 Crítico
(impacto ≥ 1% da receita bruta do mês da unidade — ou consolidada, para achado corporativo —, ou
distorção que invalida a leitura de uma unidade, ou risco fiscal/trabalhista material; prazo imediato
a 5 dias úteis), 🟠 Alto (0,3%–1% ou reincidência por 2 meses; 15 dias), 🟡 Médio (0,1%–0,3% ou falha
isolada; 30 dias), 🟢 Monitoramento (tendência desfavorável; próximo ciclo). Escalonamento automático:
🟠 aberto por dois ciclos vira 🔴 no terceiro, com registro nominal do responsável. Também exige os
códigos NC-01 a NC-14 idênticos ao padrão. O modelo de ocorrência já tem `criticality` e `nc_code`, e
existe `escalate_by_cycle_rule__no_commit`, mas nada calcula criticidade pela régua nem roda o
escalonamento, e o catálogo NC não foi carregado (o documento PAD-CTRL-001 não está no repositório).
Há também a decisão aberta nº 11 do decision-log: o título do §8 diz T13–T26, o corpo define T13–T30.

## What Changes

- Cálculo determinístico de criticidade a partir do impacto quantificado e da receita bruta do mês da
  unidade (ou consolidada), com critérios qualitativos (distorção que invalida leitura, risco material)
  como decisão humana registrada.
- Prazo padrão derivado da criticidade (dias úteis com o calendário confirmado).
- Rotina de escalonamento por ciclo no fechamento de cada competência.
- Catálogo NC-01..NC-14 carregado a partir do PAD-CTRL-001 (texto oficial); até lá, só os códigos
  citados no Prompt Mestre, marcados "descrição pendente do PAD-CTRL-001".
- Registro da decisão sobre a faixa T13–T26 × T13–T30.

## Capabilities

### New Capabilities
- `criticality-rule`: régua PAD-CTRL-001, prazos, escalonamento e catálogo NC.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/occurrences.py` (escalonamento), novo serviço de criticidade, catálogo NC,
  ledger UI e relatórios.

## Dependências

- **Documento PAD-CTRL-001** (régua, NC-01..NC-14, calendário D0–D+12, nomenclatura de arquivos) — a
  solicitar à Luyla. `impact-quantification` para o impacto em R$.

## Estado de dado

Real.
