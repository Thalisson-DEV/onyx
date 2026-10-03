## Why

O loop do TON hoje para em "recalcula": falta **acompanhar e verificar** (guia de apresentação §9 —
"Acompanha ❌, Verifica ❌"). O Prompt Mestre exige que toda ocorrência nasça com um critério objetivo
de verificação no ciclo seguinte (§5 passo 7, §14.1 item 10), que a rotina **R9 — Verificação de
ações** rode mensalmente em D+2 sobre o ledger com prazo vencido e notifique o responsável nominal e a
Gerência Geral (§12), e que economia só conte como realizada depois de verificada contra a base do mês
seguinte (§13.3). Exemplo concreto: na próxima importação, confirmar sozinho que a duplicidade da 392
sumiu do NG.

## What Changes

- Critério de verificação declarado na detecção (por regra), em forma executável: "identidade não
  detectada no próximo snapshot", "valor do grupo dentro de ±x% no próximo ciclo", "fonte entregue até
  D+n", etc.
- Avaliação automática do critério a cada novo snapshot/fechamento; resultado registrado
  (VERIFIED, NOT_VERIFIED, INCONCLUSIVE) com evidência.
- **R9** mensal (D+2 do calendário PAD-CTRL-001; até lá, 2º dia útil): lista de ações vencidas e não
  verificadas para o responsável e a Gerência Geral.
- Impacto passa de previsto a realizado somente quando a verificação é VERIFIED.

## Capabilities

### New Capabilities
- `action-verification`: critério de verificação, avaliação no ciclo seguinte e rotina R9.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/occurrences.py` (`record_verification__no_commit`), regras (critério por
  versão), rotina agendada, notificações, ledger UI.

## Dependências

- `occurrence-ledger-workflow`, `carry-over-decisions-on-reimport` (evento "não detectado"),
  `routine-framework` para agendar R9 (pode começar como tarefa Celery dedicada).

## Estado de dado

Real: verificar a 392 e os 19 sem unidade na próxima importação do NG.
