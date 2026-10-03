## Context

R3 usa Celery Beat tenant-aware, calendário de feriados confirmado (Petrolina) e chave de publicação
idempotente. `registry.ROUTINES` lista R1–R9 só como texto com dependência. As rotinas de domínio
chegarão em changes diferentes; sem framework, cada uma reinventaria agenda, silêncio e entrega.

## Goals / Non-Goals

**Goals:** uma definição declarativa; gatilhos por cron, D+n útil e evento; silêncio auditável;
entrega in-app + e-mail; idempotência.

**Non-Goals:** editor visual de workflow; rotinas que decidem ou escrevem em sistemas externos.

## Decisions

- **`RoutineDefinition` versionada** (código, versão, gatilho, escopo, limiar, destinatários,
  silêncio) + `RoutineRun` (execução → `AnalysisRun` do protocolo → publicação ou silêncio com motivo).
- **Gatilho D+n útil** calculado a partir do fim da competência com o calendário confirmado; sem
  calendário a rotina não ativa (mesmo comportamento atual do R3).
- **Gatilho por evento** (nova importação concluída) com debounce, para R1 quando o NG for diário.
- **Idempotência** por (rotina, versão, competência/janela) — reaproveita o padrão do R3.
- **Entrega** via fila: notificação in-app (já existe) + e-mail SMTP; destinatário é papel nominal
  resolvido para usuários no momento da entrega.

## Risks / Trade-offs

- [Ruído] → limiar + teto 7/12 + silêncio por padrão; métricas de execuções silenciosas × publicadas.
- [Migração do R3] → teste de equivalência do relatório antes/depois.

## Open Questions

- Destinatários nominais de cada rotina; SMTP do ambiente de produção.
