## Context

`record_detection__no_commit` já deduplica ocorrências por `identity_key` (digest dos componentes
de identidade da versão da regra) e registra eventos de repetição. As decisões de revisão
(`ton_review_decision`) ficam presas ao `ReviewRun`; o dataset revisado de uma nova revisão começa
com todos os registros afetados em REVIEW_REQUIRED. A normalização usa "todas as fontes
disponíveis", por isso uma importação de dotação muda o Realizado/Orçado da base.

## Goals / Non-Goals

**Goals:** reaproveitar decisões de forma determinística e auditável; não alterar a DRE ao importar
fontes não aprovadas; dar ao usuário uma prévia antes de confirmar.

**Non-Goals:** reaproveitar decisões de mapeamento (já são globais e versionadas); inferir que um
achado foi corrigido sem evidência (isso é `action-verification`).

## Decisions

- **Chave de reaproveitamento = identity_key + evidence_fingerprint.** A identidade já existe; o
  fingerprint é o hash dos campos de evidência (conta, data, unidade, documento, valores, planilha
  não entra porque a linha muda de posição). Alternativa rejeitada: reaproveitar só por identidade,
  porque um valor alterado no NG precisa de nova decisão.
- **Decisão reaplicada é uma nova decisão de sistema** (`decided_by = system`, `basis =
  CARRIED_OVER`, referência à decisão original), nunca uma cópia silenciosa. A trilha mostra a origem.
- **Política de entradas da normalização** como configuração versionada (`ACTUAL_ONLY` hoje;
  `ACTUAL_AND_APPROVED_BUDGET` depois), registrada no `FinancialNormalizationRun`.

## Risks / Trade-offs

- [Fingerprint muito estrito reabre decisões por mudanças irrelevantes] → começar estrito e medir na
  reimportação real; afrouxar só com decisão registrada.
- [Decisão de sistema confundida com decisão humana] → rótulo distinto na UI e no log de decisões.

## Migration Plan

Sem migração destrutiva: nova coluna/tabela para fingerprint e base da decisão; revisões antigas
continuam válidas. Rollback: desligar a política de reaproveitamento (volta ao comportamento atual).

## Open Questions

- A Luyla aceita reaproveitamento automático ou quer confirmar em lote na prévia?
