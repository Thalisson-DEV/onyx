# UX-002 — TON Native Product Integration, Navigation & Truthfulness

## Mission
Correct the structural product problems that remain after UX-001. This is not another cosmetic polish pass. TON must behave as one coherent Onyx-native product.

Primary outcomes:
1. one obvious entry point into TON;
2. no admin-panel detour required;
3. chat remains native Onyx but stays inside the TON journey;
4. specialists reuse the actual TON/Onyx runtime, not a parallel frontend concept;
5. routines use the real Prompt Mestre R1–R9 semantics and real runtime state;
6. client-facing status/names/schedules come from backend truth;
7. financial screens are fully humanized;
8. critical interactions give explicit feedback;
9. QA validates real journeys, not only isolated components.

## 0. Baseline
Expected clean local `main`. Latest UX-001 report indicates `8b8e3ee723`.

Start with:
```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -15 --oneline --decorate
```

If dirty, STOP and report.

Do not push, rebase, reset, stash, duplicate shells, duplicate agent systems, or duplicate business-state stores.

## 1. Structural problem to fix
The current product still behaves like:
```text
Generic Onyx app
→ Admin
→ one TON route
→ TON sidebar
→ Central
→ generic Onyx app again
```

Target:
```text
Onyx authenticated app
→ TON
→ TON product shell
   ├── Central
   ├── Chat TON
   ├── Fontes
   ├── DRE
   ├── Pendências
   ├── Especialistas
   ├── Rotinas
   ├── Relatórios
   └── Cobertura
```

A normal authorized user must never need the admin panel to enter or return to TON.

## 2. P0 — Canonical TON entry and navigation

### Canonical routes
Ensure:
```text
/ton
/ton/controladoria
/ton/chat
/ton/data-sources
/ton/dre
/ton/pendencias
/ton/especialistas
/ton/rotinas
/ton/relatorios
/ton/cobertura
```

`/ton` redirects to `/ton/controladoria`.

### Main Onyx entry
Add a visible TON entry in the normal authenticated Onyx navigation/home for authorized users. Not admin-only.

Reuse native Onyx extension points. Do not fork the full global sidebar.

### Central semantics
Inside TON:
- `Central` → `/ton/controladoria`
- separate `Chat TON` item for conversation

Central must never eject the user to generic `/app`.

### Native chat reuse
Preferred: `/ton/chat` reuses native Onyx chat components/runtime inside the TON shell.

Do not:
- implement another chat engine;
- iframe `/app`;
- lose conversations, streaming, tools, artifacts, model picker or persona behavior.

If direct embedding is unsafe, reuse/extract the smallest existing Onyx chat route component and preserve native behavior.

### Navigation acceptance
Starting from login/home, without manually typing URLs:
1. enter TON;
2. Controladoria;
3. Chat TON;
4. back to Controladoria;
5. DRE;
6. Pendências;
7. Especialistas;
8. Rotinas;
9. Relatórios;
10. back to Chat TON.

No admin detour anywhere.

## 3. P0 — Specialist model correction

### Audit first
Inspect:
- Onyx Agent/Persona entities and existing UI;
- TON specialist registry/orchestrator;
- current `/ton/especialistas` data source;
- hard-coded frontend arrays.

Remove/refactor presentation-only specialist definitions that duplicate runtime truth.

### Canonical Prompt Mestre identities
Use exactly:
1. TON CFO
2. TON COO
3. TON FROTA
4. TON CONTRATOS
5. TON COMPLIANCE
6. TON PROCUREMENT
7. TON RH
8. TON AUDITOR
9. TON CEO

Do not replace them with a different taxonomy such as “Controladoria & Conciliação”, “Planejamento & Orçamento”, etc.

Descriptions can be humanized; identity must remain canonical.

### Runtime-backed status
Status comes from backend/runtime capability state.

No frontend literals for operational state except test fixtures.

Expected current truth unless backend genuinely changed:
- TON AUDITOR: operational
- TON CEO: operational
- TON CFO: partial while readiness unresolved
- COO/FROTA/CONTRATOS/COMPLIANCE/PROCUREMENT/RH: awaiting required sources

Never mark CONTRACTS operational without contract capability/source.
Never mark COMPLIANCE operational merely because TON has an audit trail.

### Reuse Onyx agents/personas
TON remains coordinator.

If direct specialist chat exists, reuse/provision an actual Onyx persona backed by the specialist runtime and allowed tools.

Do not create frontend-only fake agents.

If specialists are orchestration roles only, say so in code/UI and route interaction through TON.

### Detail view
Show:
- canonical name
- purpose
- status
- required sources
- available capabilities
- blocked capabilities
- last execution
- `Abrir no TON` / `Conversar` only when supported

## 4. P0 — Routine semantic correction

### Canonical Prompt Mestre R1–R9
- R1 — Varredura diária de exceções
- R2 — Auditoria semanal de combustível
- R3 — Fechamento preliminar mensal
- R4 — Reconciliação contratual mensal
- R5 — Dinheiro Escondido
- R6 — Pacote executivo
- R7 — Sentinela de vigência/reajuste contratual
- R8 — Sentinela de recebíveis
- R9 — Verificação de ações vencidas

Do not replace these with another taxonomy.

If backend registry differs, confirm against Prompt Mestre docs in repo and correct the registry rather than hard-coding the UI.

### R3 wording
R3 is preliminary close.

Do not label `DRE Oficial` unless an official READY DRE exists.

Allowed result labels:
- DRE pronta
- DRE pendente
- execução concluída com bloqueios

### Schedule source of truth
Render schedule from backend/runtime config only.

No frontend duplicate constants.

Previous configured R3 schedule was first business day, 08:00 Brasília, Petrolina calendar for 2026. If backend still says that, UI must display exactly that.

Never show `Dia 01 às 06:00` unless persisted backend state says so.

### Execute-now feedback
Lifecycle must be explicit.

Immediately:
- disable button
- spinner
- `Iniciando fechamento...`

Started:
- toast/banner `Fechamento iniciado`
- start time

Running:
- visible state/progress summary
- safe message that run is persisted if true

Completed:
- `Fechamento concluído`
- outcome
- `Ver resultado`
- `Abrir relatório` if available

Completed with blockers:
- neutral warning state

Failed:
- safe failure reason
- retry if permitted

Do not rely on a one-second button spinner.

### Persistence
After refresh/navigation:
- latest run state remains;
- result remains accessible;
- accidental duplicate run is prevented.

Keep 21 internal steps under `Ver execução`.

## 5. P0 — Product truth contract

Create tests/contracts ensuring UI cannot invent backend state.

At minimum:
- specialists from runtime/API payload
- routines from runtime/API payload
- schedule from runtime/API payload
- coverage from capability registry
- DRE blockers from readiness APIs
- sources from import/source APIs

No “operational” status merely because a card exists.

## 6. P0 — Chat execution UX correction

UX-001 improved chat, but runtime flow remains noisy.

### Group tool execution
Instead of repeated:
```text
Processado
Evidência...
Processado
Evidência...
```

render:
```text
Análise concluída
✓ Contexto financeiro
✓ Fontes financeiras
✓ Prontidão da DRE
✓ Evidências
✓ Relatório
[Ver etapas]
```

### Default collapsed execution
Prioritize:
1. final TON answer;
2. key evidence cards;
3. artifact/report cards.

Detailed runtime/tool steps collapsed by default.

### Technical JSON
Available under one grouped `Ver dados técnicos (JSON)` disclosure, admin/dev only.

Avoid one disclosure per tiny tool call.

### Repeated tabs
Do not create multiple horizontally repeated tabs with the same label.

Group repeated tool calls into one result family with count + expandable items.

## 7. P0 — DRE correction

Remove client-facing raw labels:
- `NO ACTUAL`
- `UNMAPPED`
- `Gross revenue`
- `Cost`
- `Result`
- internal rule codes

Centralize mappings.

Examples:
- NO_ACTUAL → `Sem realizado no período`
- UNMAPPED → `Não vinculado`

### NOT_READY
Focus on action:
```text
DRE ainda não pode ser fechada
13 registros exigem atenção
```

Grouped blockers:
- Dotação
- Conciliação
- Unidade
- Realizado

Each:
- count
- short explanation
- `Resolver`

Avoid giant empty space.

### READY
Preserve engine semantics, hierarchy, actual, budget, variance, YTD, revisions and drill-down.

Technical revision filters remain under advanced options.

## 8. P0 — Financial Readiness correction

Do not display:
- `Synthetic unit`
- `UNMAPPED`
- `Exact source field from reviewed NG records`
- `NO ACTUAL`

Use:
- `Unidade de demonstração`
- `Não vinculada`
- `Origem: lançamentos financeiros revisados`
- `Sem realizado no período`

Keep global synthetic banner.

Primary business groups:
- Unidades
- Classificação financeira
- Dotação
- Base do realizado
- Conciliação
- Correspondências ambíguas

`Inspecionar` opens a clear drawer/modal with:
- origin value
- affected records
- suggestion
- consequence
- justification
- confirm/reject

## 9. P1 — Data Sources completion

Keep pipeline unchanged.

Improve:
- compact source summaries
- status badge
- acquisition method
- last update
- records
- warnings
- `Atualizar`

Default show latest import summary.

`Ver histórico` expands a real table instead of always showing long history under every source.

Upload flow:
1. choose file
2. validate
3. process
4. result

## 10. P1 — Reports cleanup

Do not show many visually identical demo reports as equal cards.

Default:
- latest report per period/scope/type
- revision/history count

Use `Ver versões anteriores`.

Synthetic/demo badge remains clear.

Hide revision IDs from default cards.

## 11. P1 — Coverage cleanup

Humanize:
- `IN PROGRESS` → `Parcial`
- waiting → `Aguardando fonte`
- ready → `Operacional`

No English statuses in pt-BR UI.

Coverage is secondary/internal, not a primary client demo centerpiece.

## 12. Controladoria refinement

Keep:
- KPI strip
- quick access
- latest reports
- routines

Improve:
- reduce duplicated summary/readiness content
- prioritize top 3 actions
- ensure every CTA works
- R3 CTA uses real lifecycle feedback
- all statuses derive from backend truth

## 13. No hard-coded product truth

Search frontend for:
- specialist names/statuses
- routine names/schedules/statuses
- coverage counts
- source states
- DRE/readiness runtime state

Display labels may be constants.
Runtime state may not.

If backend lacks a required read endpoint:
- add minimal read-only endpoint
- reuse domain service
- test it
- do not create a parallel store

## 14. Routing migration

Prefer canonical product routes:
- `/ton/dre`
- `/ton/pendencias`

Legacy admin routes may redirect or remain only for truly admin-only configuration.

Do not silently break deep links.

## 15. Visual language

Continue native Onyx style.

Avoid:
- gradients
- glass
- giant heroes
- custom shadow system
- excessive colors
- “AI” decoration

Focus:
- hierarchy
- density
- feedback
- truthful state
- clear actions

## 16. Required browser journeys

### Journey A — Enter TON
Login/home → TON → Controladoria → Chat → Controladoria → DRE → Pendências → Especialistas → Rotinas → Relatórios.

No admin panel.

### Journey B — R3
Open Rotinas → Executar agora → immediate feedback → running → complete → persisted result → report → refresh → state remains.

### Journey C — Specialist truth
Open Especialistas → canonical names → CFO state matches API → missing-source roles not operational → detail matches payload.

### Journey D — Chat
Ask closing analysis → grouped progress → no raw JSON → expand technical data → ask evidence → evidence card → generate report → artifact card opens.

### Journey E — DRE/Pendências
Open DRE → no raw labels → Resolver → Pendências opens correct context → inspect item → no approval during QA.

### Journey F — Sources
Open Sources → current status → upload dialog → cancel safely → history → return to Controladoria.

## 17. Backend/UI cross-check

Record payload vs rendered UI for:
- specialists
- routines
- R3 schedule
- DRE blockers
- sources
- coverage

Screenshots alone are not sufficient.

## 18. Tests

Required:
- normal app → TON entry
- `/ton` redirect
- Central stays inside TON
- chat return path
- active nav
- canonical specialist names
- specialist status from backend
- canonical R1–R9 labels
- R3 schedule from backend
- execute-now lifecycle
- refresh persistence
- grouped chat tools
- technical JSON collapsed
- DRE raw labels absent
- readiness raw labels absent
- report grouping/history

## 19. Validation budget

During development:
- focused tests
- lint/format/types
- backend tests only for changed endpoint/service

Before completion:
- relevant frontend suite
- relevant backend suite
- `git diff --check`
- one full Chrome walkthrough Journeys A–F

Do not mark complete if TON requires Admin even once.

Do not mark complete if normal client UI contains:
- raw JSON
- UNMAPPED
- NO ACTUAL
- IN PROGRESS
- incorrect specialist taxonomy
- incorrect routine taxonomy
- incorrect schedule

## 20. Commit strategy

Recommended:
1. `fix(ton): unify product entry and navigation`
2. `fix(ton): align specialists and routines with runtime`
3. `refactor(ton): simplify chat execution and financial states`
4. `refactor(ton): finish source report and coverage ux`
5. `chore(ton): validate end-to-end product journeys`

Do not push.

## 21. Final handoff

Report:
- canonical product entry
- canonical routes
- chat reuse approach
- Onyx Agent/Persona reuse decision
- canonical specialists + actual statuses
- canonical routines + actual R3 schedule
- execute-now UX
- chat grouping
- DRE/readiness/source changes
- API-vs-UI truth checks
- Journeys A–F pass/fail
- baseline / commits / final HEAD / clean tree / no push

## Success condition

TON is reachable and usable as one coherent product without entering Admin.

UI reflects actual runtime truth.

Specialists and routines align with Prompt Mestre and existing Onyx/TON architecture.

No frontend-only fake agent/routine system.

Critical interactions provide explicit feedback.

The product is demoable through normal navigation without manually typing routes.
