# UX-002 — Tasks & Validation

Mark:
- [x] done
- [~] partial
- [!] blocked
- [ ] not started

## 0. Baseline
- [x] main
- [x] clean tree (except the two user-authorized UX-002 input files)
- [x] baseline HEAD: `8b8e3ee7231be50aeec463c26ddf215606e67b0a`
- [x] inspect `/ton` shell
- [x] inspect normal Onyx navigation
- [x] inspect native Onyx chat route/components
- [x] inspect Onyx Agent/Persona model/UI
- [x] inspect TON specialist registry
- [x] inspect TON routine registry/scheduler
- [x] inspect hard-coded frontend specialist/routine data

Audit: `AppSidebar` exposes native extension points. `AppPage` owns chat, tools,
streaming and artifacts. `useAppPosition` controls conversation URLs. TON uses
an existing public built-in Onyx Persona, provisioned by `db/ton/agent.py`.
Specialists are orchestration roles in `registry.py` and `closing.py`.
The frontend specialist and routine arrays invent taxonomy, status and schedules.
`routine_schedule.py` stores R3 configuration in the existing tenant KV store.
The scheduler uses the first business day at 08:00 Brasília, with a confirmed calendar.
`CoveragePage` also invents counts when API values are zero or missing.

Decision: reuse the TON coordinator Persona and native chat. Do not provision
independent specialist Personas. Specialist conversations go through TON.

## 1. Navigation
- [~] `/ton` → `/ton/controladoria` (implemented; validation pending)
- [~] TON entry in normal authenticated app (implemented; validation pending)
- [~] entry is not admin-only (READ_TON_SOURCES gate)
- [~] Central → `/ton/controladoria` (implemented; validation pending)
- [~] Chat TON separate (implemented; validation pending)
- [ ] Controladoria → Chat → Controladoria
- [ ] no admin detour
- [ ] active states correct
- [ ] legacy routes handled

## 2. Chat reuse
- [ ] audit native chat reuse
- [ ] `/ton/chat` if safely reusable
- [ ] no second chat runtime
- [ ] conversations preserved
- [ ] tools preserved
- [ ] model picker preserved
- [ ] artifacts preserved
- [ ] clear return to TON

## 3. Specialists
- [ ] TON CFO
- [ ] TON COO
- [ ] TON FROTA
- [ ] TON CONTRATOS
- [ ] TON COMPLIANCE
- [ ] TON PROCUREMENT
- [ ] TON RH
- [ ] TON AUDITOR
- [ ] TON CEO
- [ ] remove alternate taxonomy
- [ ] statuses from backend/runtime
- [ ] CFO truth checked
- [ ] CONTRACTS truth checked
- [ ] COMPLIANCE truth checked
- [ ] missing-source roles not operational
- [ ] audit Onyx Persona reuse
- [ ] no frontend-only fake agent model
- [ ] detail from runtime data

## 4. Routines
- [ ] R1 daily exceptions
- [ ] R2 weekly fuel audit
- [ ] R3 monthly preliminary close
- [ ] R4 monthly contract reconciliation
- [ ] R5 Dinheiro Escondido
- [ ] R6 executive package
- [ ] R7 contract expiry/repricing sentinel
- [ ] R8 receivables sentinel
- [ ] R9 overdue-action verification
- [ ] names from backend registry
- [ ] no “DRE Oficial” when blocked
- [ ] schedule from backend
- [ ] exact timezone/cadence
- [ ] no duplicate frontend schedule constants

## 5. R3 Execute Now
- [ ] immediate loading feedback
- [ ] start toast/banner
- [ ] running state
- [ ] prevent duplicate run
- [ ] completion feedback
- [ ] blocked completion feedback
- [ ] failure feedback
- [ ] result CTA
- [ ] report CTA
- [ ] survives refresh/navigation
- [ ] 21 steps collapsed

## 6. Product truth contract
- [ ] specialist status from API
- [ ] routine status from API
- [ ] schedule from API
- [ ] coverage from API
- [ ] DRE blockers from API
- [ ] source state from API
- [ ] no hard-coded runtime state

## 7. Chat execution UX
- [ ] grouped execution summary
- [ ] final answer prioritized
- [ ] evidence cards
- [ ] artifact cards
- [ ] repeated same-tool tabs removed
- [ ] technical JSON grouped/collapsed
- [ ] technical payload admin/dev only
- [ ] humanized partial/error state

## 8. DRE
- [ ] no `NO ACTUAL`
- [ ] no `UNMAPPED`
- [ ] no English fixture labels
- [ ] blocker groups humanized
- [ ] clear NOT_READY action state
- [ ] Resolve CTA
- [ ] advanced filters remain advanced
- [ ] READY behavior unchanged

## 9. Pendências
- [ ] no `Synthetic unit`
- [ ] no `UNMAPPED`
- [ ] no raw English evidence
- [ ] business categories
- [ ] affected records
- [ ] candidate/suggestion
- [ ] inspect drawer
- [ ] consequence visible
- [ ] safe confirm/reject
- [ ] no approvals during QA

## 10. Data Sources
- [ ] compact source summary
- [ ] latest status
- [ ] acquisition method
- [ ] latest import
- [ ] warnings
- [ ] upload dialog
- [ ] history collapsed/table
- [ ] cancel safely
- [ ] navigation back to Controladoria

## 11. Reports
- [ ] latest grouped by period/scope/type
- [ ] history/older revisions expandable
- [ ] demo/synthetic clearly marked
- [ ] no revision IDs on default cards
- [ ] open/download works

## 12. Coverage
- [ ] no `IN PROGRESS`
- [ ] all statuses pt-BR
- [ ] counts from backend
- [ ] secondary/internal positioning

## 13. Controladoria
- [ ] top 3 attention items
- [ ] reduce duplicated content
- [ ] quick actions valid
- [ ] R3 CTA uses real feedback
- [ ] statuses from backend truth

## 14. Journey A — Enter TON
- [ ] login/home
- [ ] click TON
- [ ] Controladoria
- [ ] Chat TON
- [ ] return Controladoria
- [ ] DRE
- [ ] Pendências
- [ ] Especialistas
- [ ] Rotinas
- [ ] Relatórios
- [ ] no Admin

## 15. Journey B — R3
- [ ] Execute now
- [ ] immediate feedback
- [ ] running
- [ ] completion
- [ ] result
- [ ] report
- [ ] refresh
- [ ] persisted state

## 16. Journey C — Specialists
- [ ] canonical names
- [ ] runtime statuses
- [ ] CFO matches API
- [ ] missing-source roles not operational
- [ ] detail matches API

## 17. Journey D — Chat
- [ ] closing analysis
- [ ] grouped progress
- [ ] no raw JSON
- [ ] technical details expandable
- [ ] evidence
- [ ] report artifact

## 18. Journey E — DRE/Pendências
- [ ] no raw internal labels
- [ ] resolve navigation context
- [ ] inspect item
- [ ] no approval

## 19. Journey F — Sources
- [ ] current status
- [ ] upload open
- [ ] cancel
- [ ] history
- [ ] return Controladoria

## 20. Backend/UI cross-check

### Specialists
API:
UI:
PASS:

### Routines
API:
UI:
PASS:

### R3 schedule
API:
UI:
PASS:

### DRE blockers
API:
UI:
PASS:

### Sources
API:
UI:
PASS:

### Coverage
API:
UI:
PASS:

## 21. Tests
- [ ] routing tests
- [ ] specialist truth tests
- [ ] routine truth tests
- [ ] execute-now lifecycle
- [ ] chat grouping
- [ ] DRE labels
- [ ] readiness labels
- [ ] report grouping
- [ ] focused typecheck
- [ ] lint
- [ ] format
- [ ] diff check

## 22. Final fail-fast visual checks
Must be zero in normal client view:
- [ ] raw JSON by default
- [ ] `UNMAPPED`
- [ ] `NO ACTUAL`
- [ ] `IN PROGRESS`
- [ ] incorrect specialist taxonomy
- [ ] incorrect routine taxonomy
- [ ] incorrect schedule
- [ ] admin-only TON entry
- [ ] Central leaving TON unintentionally

## 23. Handoff
- [ ] baseline
- [ ] commits
- [ ] final HEAD
- [ ] clean tree
- [ ] no push
- [ ] canonical routes
- [ ] Onyx agent/persona reuse decision
- [ ] actual specialist states
- [ ] actual routine schedule
- [ ] Journeys A–F results
- [ ] remaining blockers
- [ ] exact demo path
