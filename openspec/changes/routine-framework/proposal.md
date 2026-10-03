## Why

"'Rode toda madrugada' só vira operação quando existe o que disparar, quando calar e a quem notificar"
(Prompt Mestre, camada 6; §12). O §12 define nove rotinas com gatilho, escopo, limiar de publicação e
destinatário, e a regra "fora do limiar, você não fala". Hoje só o R3 existe, com agenda própria
(`ton:routines:R3:schedule:v1`), e o único canal é o sino dentro do TON. As changes de domínio (R2, R4,
R7, R8, R9, R5) precisam de uma base comum — e R1 (varredura diária 06h) e R6 (pacote executivo D+9)
são rotinas transversais sem dono.

## What Changes

- **Definição de rotina** declarativa e versionada: código R1–R9, gatilho (cron, dia útil relativo ao
  fechamento D+n do calendário PAD-CTRL-001, evento de nova importação), escopo (testes/baterias),
  limiar de publicação, destinatários (papéis nominais), regra de silêncio.
- Execução sempre pelo protocolo de 7 passos; registro de execuções silenciosas (rodou, não publicou,
  por quê).
- Migração do R3 para o framework (sem mudar o comportamento) e implementação de **R1** (T13–T26 do
  dia anterior, publica com ≥ 1 ocorrência 🟠+, resumo ≤ 7 linhas) e **R6** (pacote executivo D+9,
  insumo P1/P2 do PAD-CTRL-001).
- **Entrega**: in-app (sino) + e-mail para destinatários; canal Telegram/WhatsApp só com contrato
  (plano backend 009).
- Administração de rotinas no admin do TON (ativar, destinatários, histórico); nenhuma rotina aprova
  decisão financeira (§12.1).

## Capabilities

### New Capabilities
- `routine-framework`: definição, agendamento, limiares, silêncio, destinatários e entrega das rotinas R1–R9.

### Modified Capabilities
- `closing-routine`: R3 passa a ser uma definição do framework.

## Impact

- `backend/onyx/db/ton/routine_schedule.py`, `backend/onyx/background/celery/tasks/ton/tasks.py`,
  `backend/onyx/ton/agent/{scheduling,registry}.py`, Automações UI, Administração do TON, e-mail.

## Dependências

- Calendário D0–D+12 (PAD-CTRL-001), destinatários nominais (Luyla), servidor SMTP de produção.
  R1 só faz sentido com dado diário (`ng-direct-integration`).

## Estado de dado

Real.
