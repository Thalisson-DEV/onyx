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

## Implementation notes (2026-10-03)

What the code already did, verified on the real database before changing anything:

- Occurrence identity was already content-based for record rules (`ngf-rk-1`: month, account,
  date, unit, document, history, amounts; correctable fields excluded) and did not include the
  row number. The second real review on 2026-10-02 kept all 23 decisions
  (`occurrences_repeated_human_decision_kept: 23`). The presentation guide's claim that "decisions
  are not reused" was wrong for review decisions.
- The real gaps were: (1) every import refreshed readiness with **all** budget workbooks;
  (2) reconciliation decisions pointed at `parsed_source_record.id`, which is new on every import;
  (3) a kept decision did not check whether the evidence changed (label drift, duplicate group size);
  (4) no "not detected" record for decided cases, no preview, no trail of kept decisions.

Decisions taken while implementing:

- **A decision is never copied to a different occurrence.** `ACCEPT_RISK` and `DISMISS` are
  human-only transitions enforced by a database CHECK (readiness §9, meeting decision D4). Carry-over
  therefore only happens on the same occurrence (same identity). A changed evidence on the same
  identity appends a system `REOPENED` event with `context.carry_over = EVIDENCE_CHANGED`.
- **Evidence fingerprint** (`ngf-ev-1`) is stored in the finding payload: full content of the member
  records (no position), duplicate group size, candidate labels. Label findings use the labels only,
  because their representative rows grow every month. Diagnostic and execution findings have no
  fingerprint: the parser keeps no cell values of rejected rows, so they stay location-only. A
  cleaned export that shifts rows makes a rejected row a new case (the preview says so).
- Findings recorded before fingerprints existed keep their decision (legacy = match).
- The carried decision is a `ton_review_decision` row with `basis = CARRIED_OVER`,
  `actor_user_id = NULL` and `carried_from_decision_id`; the API returns the original author and date.
  The decision log groups carried decisions per import ("N decisões mantidas").
- "Not detected" reuses the verification event (`VERIFICATION_PASSED/FAILED`, never a status change)
  with `context.not_detected_in_snapshot_id`, for decided cases as well as open ones.
- **Input policy**: `ACTUAL_ONLY` is the policy of the automatic refresh after any import. Explicit
  budget inputs are `ACTUAL_AND_APPROVED_BUDGET`; runs made before the policy are backfilled as
  `LEGACY_ALL_AVAILABLE`.
- **Reconciliation decisions** are matched by record content (source, fingerprint, duplicate
  ordinal) instead of record id; the run statistics count `reconciliation_decisions_carried_over`.
- The Open Question (automatic vs. batch confirmation) is answered for now by the preview: the user
  sees the counts and confirms the import; nothing is carried without that confirmation.
