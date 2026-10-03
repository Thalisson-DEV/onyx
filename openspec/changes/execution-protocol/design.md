## Context

`AnalysisRun` já vincula versões de regra e snapshots; `AnalysisStep` registra etapas; `execute_closing`
(R3) faz inspeção de fontes, revisão, prontidão e DRE em sequência própria. Cada nova bateria
(sanidade, T1–T30) precisa rodar dentro de uma ordem comum para que o gate do §5 seja verdadeiro em
todo lugar, inclusive no assistente.

## Goals / Non-Goals

**Goals:** um orquestrador; passos como interfaces plugáveis; gate determinístico; estado auditável;
teto de publicação.

**Non-Goals:** paralelizar passos; deixar o LLM decidir a ordem ou pular passos.

## Decisions

- **Protocolo como pipeline de `StepExecutor`s** registrados por passo (1..7); cada executor recebe o
  contexto (escopo, competência, snapshots) e devolve status PASSED / FAILED_CRITICAL / FAILED /
  SKIPPED_BLOCKED com achados. Baterias de regras se registram no passo 2 (sanidade) ou 4 (detecção).
- **Gate:** FAILED_CRITICAL em 1 ou 2 marca 3–7 como SKIPPED_BLOCKED com motivo; o passo 7 ainda
  publica o relatório de bloqueio (base reprovada), nunca margem.
- **Pontos cegos** como regras determinísticas do passo 1/3 (ex.: "faturamento sem medição" = existe
  faturamento no período e não existe fonte de medição), com resultado "indisponível — pendente de
  informação de campo".
- **Teto 7/12:** ordenação por (criticidade, impacto R$, urgência por prazo); o restante é registrado
  no ledger com flag `published = false`.
- **Assistente:** perguntas analíticas chamam o orquestrador (modo leitura) em vez de encadear tools
  livremente; isso também reduz latência.

## Risks / Trade-offs

- [Refatorar R3 quebra a rotina agendada] → R3 migra por último, com teste de equivalência do relatório.
- [Pontos cegos geram ruído] → passam pelo mesmo teto e pela régua de criticidade (🟢 monitoramento).

## Open Questions

- Lista oficial de insumos e calendário D0–D+12 do PAD-CTRL-001.
