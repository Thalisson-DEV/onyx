# TON-FE-003 — Task Tracker

Status: `[x]` feito · `[~]` parcial · `[!]` bloqueado · `[ ]` não iniciado · `[d]` adiado

## 0. Baseline
HEAD: `a7dc9b9bc2`
Branch: `main` (local, sem push)
Working tree: limpo, exceto os planos TON-FE-003 e `plans/ton/context/` (entrada desta tarefa)
Current milestone: `M2 — Fechamento como centro de controle`

Ambiente de validação: `next dev :3005` contra a API local (sessão do usuário autorizado no
Chrome). Backend alterado é copiado para `onyx-api_server-1` (`docker cp` + restart); a imagem
`onyx-backend:latest` **não** foi reconstruída. Testes de banco rodam num contêiner descartável
na rede `onyx_default` (a porta 5432 do host é de um Postgres local do Windows).

## 1. Gap discovery
- [x] audit current product
- [x] audit backend/API capabilities
- [x] compare to Prompt Mestre
- [x] inspect current finance workflow docs
- [x] identify product gaps
- [x] identify workflow gaps
- [x] identify data gaps
- [x] identify UX gaps
- [x] identify trust gaps
- [x] identify automation gaps
- [x] identify presentation gaps
- [x] create prioritized GAP_REPORT

## 2. Pending resolution
- [x] evidence → decision flow (registros de origem no diálogo)
- [x] candidate presentation ("Pronta para avançar" só com evidência determinística)
- [x] consequence preview (o que muda, escopo, se muda números da DRE)
- [x] explicit confirmation
- [x] versioned persistence (já existia; agora exibida)
- [x] audit trail (log de decisões: quem, quando, por quê, versão)
- [x] recompute readiness (após confirmar, com permissão)
- [x] before/after result
- [d] batch resolution where safe (D-026)
- [x] duplicate/ambiguous protection (sem escolha padrão; conciliação nunca em lote)
- [x] refresh persistence (banner de pendentes + "O que mudou" + log)
- [x] realizado ausente como guia de importação (D-028)
- [x] explicação leiga e triagem (D-027)

## 3. Closing Control Center
- [ ] status
- [ ] blockers
- [ ] recently resolved
- [ ] activity
- [ ] next actions
- [ ] DRE state
- [ ] latest report
- [ ] next automation
- [ ] change summary

## 4. Finance Work Queue
- [ ] blockers
- [ ] decisions
- [ ] findings
- [ ] overdue actions
- [ ] source problems
- [ ] priority
- [ ] owner when supported
- [ ] deadline when supported
- [ ] impact
- [ ] action

## 5. Assistant ↔ actions
- [ ] deep-link from answers
- [ ] open filtered pending queue
- [ ] open DRE context
- [ ] open report
- [ ] resolve supported action
- [ ] show changes after decision
- [x] item → assistente ("Perguntar ao TON sobre este item")

## 6. Closed-loop automation
- [x] post-decision recompute
- [x] detect blocker removal
- [x] detect new blocker
- [ ] notify meaningful state changes
- [ ] report regeneration where justified
- [x] bounded/idempotent execution (digest de entrada)

## 7. Proactive intelligence
- [ ] identify supported proactive signals
- [ ] anomaly candidates
- [ ] repeated corrections
- [ ] source freshness
- [ ] closing changes
- [ ] decision follow-up
- [ ] no invented thresholds

## 8. Daily Finance utility
- [ ] identify repetitive external work
- [ ] prioritize high-value flows
- [ ] implement selected flow(s)
- [ ] measure reduced manual steps

## 9. UX evidence pass
- [ ] hierarchy
- [ ] actionability
- [ ] feedback
- [ ] continuity
- [ ] density
- [ ] consistency
- [ ] trust
- [ ] identity
- [ ] AI quality
- [ ] systemic component fixes

## 10. External UX references
- [x] finance/B2B references if useful (registradas no GAP_REPORT §11)
- [ ] audit/evidence patterns
- [ ] agentic UX patterns
- [ ] integration/data-health patterns
- [ ] useful sources recorded

## 11. Admin
- [ ] TON administration boundary
- [ ] technical Onyx admin boundary
- [ ] access
- [ ] sources
- [ ] automations
- [ ] specialists
- [ ] financial controls
- [ ] audit

## 12. Truth / backend
- [x] important UI states mapped to APIs
- [x] no business rules in frontend (antes/agora = diff de duas respostas do backend)
- [x] read models added only where justified (D-024)
- [x] version/audit preserved

## 13. Demo / daily workflow
- [x] discover issue
- [x] inspect evidence
- [x] resolve
- [x] recompute
- [x] see consequence
- [ ] ask TON what changed
- [ ] generate report
- [x] return to queue

## 14. Quality
- [x] focused tests (backend 4 testes novos; jest TON 32/32)
- [x] TypeScript
- [x] lint (sem erros; avisos anti-slop iguais ao padrão do repositório)
- [x] format
- [!] build (imagem web não reconstruída — memória WSL)
- [x] git diff --check
- [x] Chrome QA

## 15. Progress log

### 2026-10-02 10:30
Milestone: M0 auditoria + M1 loop de resolução de pendências.
Commit: ver `git log` (feat(ton): close the pending decision loop…)
What changed: GAP_REPORT; read models `records[]`, `readiness/changes`, `decisions`
(backend/onyx/db/ton/decision_loop.py); `NO_ACTUAL` lista meses faltantes; PendingPage
refatorada (model.ts, DecisionDialog.tsx, MissingActualsGuide.tsx) com evidência, prévia,
confirmação, recálculo e antes/agora; componentes compartilhados EvidenceRecords,
ReadinessDelta, DecisionLogList; Fontes abre o upload do NG por link com orientação de
período; explicação leiga e triagem.
What is demonstrable: Pendências → Conciliação → abrir item → ver nota/valor → escolher
opção (com significado) → justificar → confirmar → "Decisão registrada · Versão 2 · e-mail ·
hoje" + Antes 12 / Agora 11 → "Próxima pendência". Refresh mantém "O que mudou" e o log.
Realizado ausente mostra jul/2026 presente e jan–jun/2026 faltantes com link para importar.
Validation: pytest (contêiner) test_decision_loop 4/4 + readiness/domain/dre/closing 14/14;
tsc limpo; jest TON 32/32; Chrome :3005.
New gaps discovered: importação do NG substitui a anterior (armadilha para importação
parcial); conciliação não muda valores da DRE (só libera o item) — antes não dito.
Known issues: imagem do backend não reconstruída (alterações aplicadas por docker cp).
Next: Fechamento como centro de controle; fila de trabalho; CTAs do assistente; notificações.
