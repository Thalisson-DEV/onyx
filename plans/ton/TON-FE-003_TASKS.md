# TON-FE-003 — Task Tracker

Status: `[x]` feito · `[~]` parcial · `[!]` bloqueado · `[ ]` não iniciado · `[d]` adiado

## 0. Baseline
HEAD: `a7dc9b9bc2`
Branch: `main` (local, sem push)
Working tree: limpo, exceto os planos TON-FE-003 e `plans/ton/context/` (entrada desta tarefa)
Current milestone: `Encerrado — M0 a M6 entregues`

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
- [x] status
- [x] blockers (fila ordenada por quem pode agir)
- [x] recently resolved (o que mudou desde a base anterior)
- [x] activity (decisões recentes com autor e versão)
- [x] next actions
- [x] DRE state
- [x] latest report (com aviso de relatório anterior à base atual)
- [x] next automation (R3)
- [x] change summary

## 4. Finance Work Queue
- [x] blockers
- [x] decisions (registradas e não aplicadas)
- [~] findings (aparecem no Fechamento; achados de revisão vazios na base local)
- [x] overdue actions (`GET /api/ton/agent/actions/overdue`; 0 na base local)
- [x] source problems (importação com falha/avisos)
- [x] priority (ordem determinística: fonte quebrada → aplicar → decidir → dados → acompanhar)
- [x] owner when supported (só da atribuição da ocorrência)
- [x] deadline when supported (idem)
- [x] impact ("Bloqueia a DRE" / "Acompanhar")
- [x] action

## 5. Assistant ↔ actions
- [x] deep-link from answers
- [x] open filtered pending queue (cartão DRE: uma ação por bloqueio)
- [x] open DRE context
- [x] open report (cartões de publicação; resumo executivo rotulado corretamente)
- [x] resolve supported action (leva à fila; nada é decidido no chat)
- [x] show changes after decision (`ton_get_recent_changes`)
- [x] linha de raciocínio visível: raciocínio, consultas, especialistas, Python (D-031)
- [x] Code Interpreter disponível ao TON com limites (D-032)
- [x] item → assistente ("Perguntar ao TON sobre este item")

## 6. Closed-loop automation
- [x] post-decision recompute
- [x] detect blocker removal
- [x] detect new blocker
- [x] notify meaningful state changes (sino: decisões, prontidão recalculada, DRE sem bloqueios)
- [x] report regeneration where justified (sinalizada quando o relatório é anterior à base; gerar continua explícito)
- [x] bounded/idempotent execution (digest de entrada)

## 7. Proactive intelligence
- [x] identify supported proactive signals (GAP_REPORT §9)
- [!] anomaly candidates (sem histórico; não ativado)
- [!] repeated corrections (0 ocorrências na base local)
- [~] source freshness (data da última importação e falhas; sem SLA oficial não há "desatualizada")
- [x] closing changes (antes/agora no Fechamento, sino e chat)
- [x] decision follow-up (decisões aguardando recálculo na fila, banner e sino)
- [x] no invented thresholds

## 8. Daily Finance utility
- [x] identify repetitive external work (abrir planilha para conferir nota/valor; anotar números antes/depois; perguntar "o que mudou")
- [x] prioritize high-value flows
- [x] implement selected flow(s) (evidência no diálogo, antes/agora, fila diária)
- [~] measure reduced manual steps (qualitativo: decidir uma conciliação não exige abrir a planilha nem recalcular à parte)

## 9. UX evidence pass
- [x] hierarchy (Fechamento: estado → próximas ações → o que mudou → decisões)
- [x] actionability
- [x] feedback (resultado da decisão com antes/agora)
- [x] continuity (item → próxima pendência; chat → fila na categoria)
- [x] density ("Sem decisão" repetido trocado por triagem)
- [x] consistency (uma fila, um log, um componente de antes/agora)
- [x] trust (evidência de origem; "muda / não muda números da DRE")
- [x] identity
- [x] AI quality ("Leitura do TON" repetitiva removida; nenhuma decisão sugerida por IA)
- [x] systemic component fixes (EvidenceRecords, ReadinessDelta, DecisionLogList, WorkQueue, MemoizedParagraph)

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
- [x] audit (Trilha de decisões financeiras na Administração do TON)

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
- [x] ask TON what changed
- [~] generate report (fluxo existente; agora só sob pedido explícito)
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

### 2026-10-02 12:30
Milestone: M2 a M6 — Fechamento como centro de controle, fila de trabalho, assistente ↔
ações, linha de raciocínio + Python, trilha de auditoria.
Commits: 35294a9f9a, c250f45ded, 591c70a7d5, 0b77ca20c6, 3e1f32b2da (+ este registro).
What changed: Fechamento com próximas ações, o que mudou, decisões e relatório
desatualizado; `buildWorkQueue` compartilhado; `GET /api/ton/agent/actions/overdue`; eventos
de decisão e prontidão no sino; `ton_get_recent_changes`; cartões do chat com ação por
bloqueio; timeline com especialistas e Python; Python anexado ao TON; publicação só sob
pedido; hidratação corrigida para imagens em parágrafos; trilha de decisões no admin.
What is demonstrable: Visão Geral → "O que precisa de você hoje" → Decidir → diálogo com
evidência → antes/agora → Fechamento mostra a mudança → chat "o que mudou?" responde com a
comparação persistida e aponta Pendências/Fontes → timeline mostra CFO/AUDITOR/CEO e Python.
Validation: pytest (contêiner) decision_loop 5/5, agent 2/2, readiness/domain/dre/closing
14/14; jest 256/256 (app/message, lib/ton, views/ton, components/chat); tsc limpo; Chrome
:3005, incluindo três perguntas reais ao modelo; 390/768 px sem rolagem horizontal (iframes).
New gaps discovered: o modelo publicava relatórios sem pedido; consultou setembro antes de
julho (agora cada etapa nomeia o período); a decisão semeada de período orçamentário não
corresponde à execução de dotação usada (dado sintético; o próprio TON sinalizou).
Known issues: imagem `onyx-backend` não reconstruída (alterações aplicadas por docker cp em
api_server/background); build de produção web não refeito.
Next: ver "Restante" no GAP_REPORT.
