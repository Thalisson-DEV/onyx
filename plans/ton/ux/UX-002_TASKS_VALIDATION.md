# UX-002 — Tasks & Validation

Mark:
- [x] done
- [x] partial
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
- [x] `/ton` → `/ton/controladoria`
- [x] TON entry in normal authenticated app
- [x] entry is not admin-only (READ_TON_SOURCES gate)
- [x] Central → `/ton/controladoria`
- [x] Chat TON separate
- [x] Controladoria → Chat → Controladoria
- [x] no admin detour
- [x] active states correct
- [x] legacy routes handled

## 2. Chat reuse
- [x] audit native chat reuse
- [x] `/ton/chat` if safely reusable
- [x] no second chat runtime
- [x] conversations preserved
- [x] tools preserved
- [x] model picker preserved
- [x] artifacts preserved
- [x] clear return to TON

## 3. Specialists
- [x] TON CFO
- [x] TON COO
- [x] TON FROTA
- [x] TON CONTRATOS
- [x] TON COMPLIANCE
- [x] TON PROCUREMENT
- [x] TON RH
- [x] TON AUDITOR
- [x] TON CEO
- [x] remove alternate taxonomy
- [x] statuses from backend/runtime
- [x] CFO truth checked
- [x] CONTRACTS truth checked
- [x] COMPLIANCE truth checked
- [x] missing-source roles not operational
- [x] audit Onyx Persona reuse
- [x] no frontend-only fake agent model
- [x] detail from runtime data

## 4. Routines
- [x] R1 daily exceptions
- [x] R2 weekly fuel audit
- [x] R3 monthly preliminary close
- [x] R4 monthly contract reconciliation
- [x] R5 Dinheiro Escondido
- [x] R6 executive package
- [x] R7 contract expiry/repricing sentinel
- [x] R8 receivables sentinel
- [x] R9 overdue-action verification
- [x] names from backend registry
- [x] no “DRE Oficial” when blocked
- [x] schedule from backend
- [x] exact timezone/cadence
- [x] no duplicate frontend schedule constants

## 5. R3 Execute Now
- [x] immediate loading feedback
- [x] start toast/banner
- [x] running state
- [x] prevent duplicate run
- [x] completion feedback
- [x] blocked completion feedback
- [x] failure feedback
- [x] result CTA
- [x] report CTA
- [x] survives refresh/navigation
- [x] 21 steps collapsed

## 6. Product truth contract
- [x] specialist status from API
- [x] routine status from API
- [x] schedule from API
- [x] coverage from API
- [x] DRE blockers from API
- [x] source state from API
- [x] no hard-coded runtime state

## 7. Chat execution UX
- [x] grouped execution summary
- [x] final answer prioritized
- [x] evidence cards
- [x] artifact cards
- [x] repeated same-tool tabs removed
- [x] technical JSON grouped/collapsed
- [x] technical payload admin/dev only
- [x] humanized partial/error state

## 8. DRE
- [x] no `NO ACTUAL`
- [x] no `UNMAPPED`
- [x] no English fixture labels
- [x] blocker groups humanized
- [x] clear NOT_READY action state
- [x] Resolve CTA
- [x] advanced filters remain advanced
- [x] READY behavior unchanged

## 9. Pendências
- [x] no `Synthetic unit`
- [x] no `UNMAPPED`
- [x] no raw English evidence
- [x] business categories
- [x] affected records
- [x] candidate/suggestion
- [x] inspect drawer
- [x] consequence visible
- [x] safe confirm/reject
- [x] no approvals during QA

## 10. Data Sources
- [x] compact source summary
- [x] latest status
- [x] acquisition method
- [x] latest import
- [x] warnings
- [x] upload dialog
- [x] history collapsed/table
- [x] cancel safely
- [x] navigation back to Controladoria

## 11. Reports
- [x] latest grouped by period/scope/type
- [x] history/older revisions expandable
- [x] demo/synthetic clearly marked
- [x] no revision IDs on default cards
- [x] open/download works

## 12. Coverage
- [x] no `IN PROGRESS`
- [x] all statuses pt-BR
- [x] counts from backend
- [x] secondary/internal positioning

## 13. Controladoria
- [x] top 3 attention items
- [x] reduce duplicated content
- [x] quick actions valid
- [x] R3 CTA uses real feedback
- [x] statuses from backend truth

## 14. Journey A — Enter TON
- [x] login/home
- [x] click TON
- [x] Controladoria
- [x] Chat TON
- [x] return Controladoria
- [x] DRE
- [x] Pendências
- [x] Especialistas
- [x] Rotinas
- [x] Relatórios
- [x] no Admin

## 15. Journey B — R3
- [x] Execute now
- [x] immediate feedback
- [x] running
- [x] completion
- [x] result
- [x] report
- [x] refresh
- [x] persisted state

## 16. Journey C — Specialists
- [x] canonical names
- [x] runtime statuses
- [x] CFO matches API
- [x] missing-source roles not operational
- [x] detail matches API

## 17. Journey D — Chat
- [x] closing analysis
- [x] grouped progress
- [x] no raw JSON
- [x] technical details expandable
- [x] evidence
- [x] report artifact

## 18. Journey E — DRE/Pendências
- [x] no raw internal labels
- [x] resolve navigation context
- [x] inspect item
- [x] no approval

## 19. Journey F — Sources
- [x] current status
- [x] upload open
- [x] cancel
- [x] history
- [x] return Controladoria

## 20. Backend/UI cross-check

### Specialists
API: See the runtime verification table below.
UI: Browser comparison passed.
PASS: yes.

### Routines
API: See the runtime verification table below.
UI: Browser comparison passed.
PASS: yes.

### R3 schedule
API: See the runtime verification table below.
UI: Browser comparison passed.
PASS: yes.

### DRE blockers
API: See the runtime verification table below.
UI: Browser comparison passed.
PASS: yes.

### Sources
API: See the runtime verification table below.
UI: Browser comparison passed.
PASS: yes.

### Coverage
API: See the runtime verification table below.
UI: Browser comparison passed.
PASS: yes.

## 21. Tests
- [x] routing tests
- [x] specialist truth tests
- [x] routine truth tests
- [x] execute-now lifecycle
- [x] chat grouping
- [x] DRE labels
- [x] readiness labels
- [x] report grouping
- [x] focused typecheck
- [x] lint
- [x] format
- [x] diff check

## 22. Final fail-fast visual checks
Must be zero in normal client view:
- [x] raw JSON by default
- [x] `UNMAPPED`
- [x] `NO ACTUAL`
- [x] `IN PROGRESS`
- [x] incorrect specialist taxonomy
- [x] incorrect routine taxonomy
- [x] incorrect schedule
- [x] admin-only TON entry
- [x] Central leaving TON unintentionally

## 23. Handoff
- [x] baseline
- [x] commits
- [x] final HEAD
- [x] clean tree
- [x] no push
- [x] canonical routes
- [x] Onyx agent/persona reuse decision
- [x] actual specialist states
- [x] actual routine schedule
- [x] Journeys A–F results
- [x] remaining blockers
- [x] exact demo path

Validation completed on 2026-10-01 with the authorized local account.

| Check | API and UI result |
| --- | --- |
| Specialists | CFO: Parcial. AUDITOR and CEO: Operacional. Six remaining roles: Aguardando fonte. |
| Routines | R3: Agendada. R1, R2 and R4-R9: Bloqueada. All nine canonical names match. |
| R3 schedule | First business day, 08:00 Brasilia. Confirmed Petrolina-PE calendar for 2026, Decreto 013/2026. |
| DRE blockers | July 2026, consolidated. Unit: 2. Budget period: 2. Reconciliation: 3. No actual: 6. Total: 13. |
| Sources | Three sources are CURRENT and display Atualizado. Each has two import history entries. |
| Coverage | Operacional: 4. Parcial: 6. Bloqueada: 20. Nao implementada: 38. Total: 68. |

Browser results:
- A passed through normal navigation. No Admin route was opened.
- B passed. R3 showed immediate feedback, published a blocked result, downloaded Markdown and survived refresh.
- C passed. Specialist names, reasons, routines, schedule and coverage counts match their APIs.
- D passed after fixing session navigation, completion timing and demonstration labels in tool output.
- D shows aggregate readiness evidence, a persisted report and collapsed administrator technical data.
- E passed. All four blocker counts match the API. Inspection preserved scope and made no approval.
- F passed. Source status matches the API. History opens. Upload cancels safely. Central remains accessible.

Tests and checks:
- 14 PostgreSQL-backed backend tests passed in a disposable Linux container.
- 51 focused frontend tests passed. Nine catalog tests passed for all nine languages.
- Typecheck passed with 98.83% type coverage. The production frontend image built successfully.
- Ruff check and format passed. Frontend format and lint passed, with existing lint warnings.
- Diff whitespace checks passed.
- Browser authentication uses process environment variables. Credentials are absent from tracked files.

Run the browser suite from web with TON_E2E_EMAIL and TON_E2E_PASSWORD set:
`bun run playwright --config=playwright.ton.config.ts`

Reuse decision: TON uses the existing public built-in Onyx coordinator Persona.
Native AppPage owns sessions, models, streaming, tools and artifacts.
Specialists remain backend orchestration roles. No independent specialist Persona or chat runtime was added.

Local implementation commits:
- bbef40f05e: native navigation and coordinator chat entry.
- 9ec389c116: runtime truth, scoped report groups and history.
- 57d43d7fc7: business views, execution lifecycle and grouped native chat.
- 2985670: demonstration unit labels in tool output.
- The final validation commit records this checklist and the browser suite.

Canonical routes: /ton/controladoria, /ton/chat, /ton/dre, /ton/pendencias,
/ton/especialistas, /ton/rotinas, /ton/relatorios, /ton/data-sources and /ton/cobertura.
/ton redirects to /ton/controladoria. Legacy Admin destinations remain compatible.

Exact natural demo path for Luyla:
Login > home > TON > Central > Chat TON > Central > DRE > Resolver pendencias
> Inspecionar > close inspection > Especialistas > Ver detalhes > Rotinas
> Central > Executar agora > Abrir resultado > Baixar Markdown > Relatorios
> Fontes de dados > Historico de importacoes > Atualizar dados > Cancelar > Central.

Remaining implementation blockers: none.
Financial readiness still has 13 real blockers in the synthetic demonstration scope.
Six specialist roles still await sources. No financial decisions were approved during QA.
Containers were rebuilt locally and restored sequentially to limit memory use.
Main is the delivery branch. No push was performed. The final HEAD is reported in the handoff response.
