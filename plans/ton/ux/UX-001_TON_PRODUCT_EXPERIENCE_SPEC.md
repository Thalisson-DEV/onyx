# UX-001 — TON Product Experience & Visual Polish

## Mission
Transform the current TON from a functional engineering/demo surface into a polished client-facing controladoria product, while preserving all existing financial semantics, agent behavior, routines, reports, imports and permissions.

Baseline expected: `49134b4e33` on clean local `main`. Do not push.

## 1. Principles
- Reuse the existing Onyx design system and components before creating new primitives.
- Preserve existing backend contracts unless a real UI gap requires a minimal API change.
- Prefer calm, compact, enterprise UI: subtle borders, strong hierarchy, dense but readable information.
- Avoid decorative AI aesthetics, giant whitespace, markdown walls, raw JSON, UUIDs, debug payloads and equal-weight pill buttons everywhere.
- Support both existing light/dark themes via current tokens.
- Client-facing language must be pt-BR and business-oriented.
- Technical/internal metadata should live behind `Detalhes técnicos`, collapsed by default.

## 2. Product shell and navigation
Create a coherent TON product area in the existing Onyx shell.

Primary TON navigation:
- Central
- Fontes de dados
- DRE
- Pendências
- Especialistas
- Rotinas
- Relatórios
- Cobertura do TON (secondary/admin)

Keep generic Onyx administration accessible separately, but do not make client flows feel like they live inside a generic admin/debug console.

## 3. Controladoria overview `/ton/controladoria`
Redesign completely.

### Header
- `Controladoria`
- concise subtitle
- scope selector
- period selector when applicable
- primary CTA `Abrir TON`
- secondary CTA `Executar fechamento`

### Executive strip
Show concise real-state summaries:
- Fechamento
- DRE
- Pendências
- Fontes
- Última análise

### Attention queue
Section `O que precisa de atenção`:
- title
- status/severity
- short explanation
- affected records
- source/evidence
- action
- CTA

### TON activity
Timeline/list:
- last analysis
- last R3
- latest report
- latest import

### Specialists / routines
Compact summaries only. Detailed information belongs in dedicated pages.

The overview must not look like rendered Markdown.

## 4. Chat — highest UX priority
The current raw JSON/tool payload rendering must be removed from normal user view.

### Tool execution rendering
Render domain cards/components:
- Fontes consultadas
- Prontidão da DRE
- Evidência
- Achado
- Relatório gerado
- Rotina executada

Raw JSON is allowed only under `Ver dados técnicos`, collapsed and admin/dev only.

### Tool progress
Humanized progress:
- Consultando fontes
- Validando fechamento
- Verificando DRE
- Consultando evidências
- Preparando relatório

Do not expose internal tool names by default.

### Final answer
Structured semantic sections when useful:
- Situação
- Evidência
- Impacto
- Recomendação
- Próxima ação
- Limitação

Do not display huge plain Markdown walls.

### Empty state
Use 4 concise suggestions:
- Analisar fechamento atual
- Ver bloqueios da DRE
- Mostrar principais pendências
- Gerar relatório do fechamento

Ensure no clipping.

### Artifact cards
Generated report message should show:
- title
- period
- status
- generated time
- Abrir
- Baixar

Do not show long revision IDs in the main conversation body.

## 5. Evidence UX
Create a reusable evidence card/drawer.

Default:
- finding/title
- evidence/source
- period/scope
- affected records
- status
- confidence level if supported
- recommendation

Expandable:
- deterministic observation
- source lineage
- rule
- supporting records
- human decision still required

Internal IDs, UUIDs, hashes and normalized versions go under `Detalhes técnicos`.

## 6. Reports
Redesign report routes as professional controladoria deliverables.

### Header
- title
- period
- scope
- status
- generated at
- actions: Voltar / Baixar

### Executive summary
Use a dedicated layout, not plain Markdown labels.

### Findings
Render each relevant issue as an exception card:
- severity
- title
- what happened
- evidence
- impact
- action
- owner/deadline when available

### Readiness
Dedicated readiness block with counts and CTA.

### Traceability
Revision IDs/reference IDs collapsed under `Rastreabilidade`.

No report page should look like a Markdown preview.

## 7. DRE
Preserve DATA-005/006 semantics.

### Filters
Primary:
- período
- escopo/unidade

Advanced:
- revisão dos dados
- versão da estrutura DRE

### Summary
Polished compact financial metrics:
- Realizado
- Orçado
- Variação
- Variação %
- secondary YTD

### Table
Improve:
- hierarchy indentation
- subtotal/result emphasis
- right-aligned numeric columns
- row hover/selection
- sticky/clear header if existing component supports
- horizontal-scroll affordance
- responsive behavior

### Drill-down
Replace empty right column with proper drawer/resizable detail panel:
`Lançamentos que compõem este valor`

Tabs:
- Realizado
- Orçado

### Chart
Reuse existing Onyx chart/theme.
Improve legend, tooltip, spacing, null handling.
Do not add a new major chart dependency unless necessary.

### Synthetic mode
Keep clear but restrained dev banner. Never let synthetic results look real.

## 8. Financial Readiness -> business workflow
Client-facing concept should be closer to `Pendências do fechamento`.

Group technical blockers into:
- Classificação financeira
- Unidade
- Dotação
- Conciliação
- Base de cálculo

### Work queue
Columns/items:
- origem
- problema
- registros afetados
- sugestão when available
- status
- ação

### Decision flow
Use modal/drawer with:
- context
- recommendation
- affected scope
- consequence
- reason
- confirm/reject

Use verbs:
- Classificar
- Vincular unidade
- Definir base
- Definir período
- Resolver conciliação

Do not expose raw readiness enums.

## 9. Data Sources
Keep DELIVERY-001 logic unchanged.

### Source list
Compact rows/cards:
- name
- acquisition method
- status
- last update
- records
- warnings
- primary action

### Upload
Clear focused flow:
1. source
2. file
3. validation
4. processing
5. result

Parser/profile names hidden unless advanced details.

### Result
Show:
- imported
- rejected
- warnings
- downstream effect
- CTA to Pendências/DRE

### History
Use a compact table rather than large cards.

## 10. Specialists
Dedicated polished surface.

Each specialist:
- icon
- name
- one-line purpose
- status: Operacional / Parcial / Aguardando fonte
- dependency
- latest action/run if available

Detail drawer:
- role
- available capabilities
- unavailable capabilities
- required sources
- recent analyses

No debug metadata by default.

## 11. Routines
Dedicated routine experience.

For R1–R9 show:
- name
- cadence
- status
- last run
- next run
- latest outcome

### R3 flagship
Show:
- schedule
- next run
- last result
- `Executar agora`
- progress while running
- concise result
- report link

The 21 internal steps belong behind `Ver execução`, not on the main page.

## 12. Prompt Mestre coverage
Render as a capability map, not a Markdown checklist.

Groups:
- Sanidade
- Financeiro
- Operacional
- Rotinas
- Especialistas
- Fontes

For each group:
- operational count
- partial count
- awaiting-source count

Expandable detail:
- requirement
- status
- source
- blocker
- next dependency

## 13. Integrations
Polished integration status.

### NG/Keevo
- `Importação manual ativa`
- `Integração direta aguardando acesso`
- needs VPN + authorized API/read-only DB + docs

Use neutral waiting state, not scary failure styling.

### Zeev
Show only validated state.

### Faturamento / Dotação
Show supported state.

## 14. Centralized business labels
Create/reuse a centralized mapping layer.

Examples:
- `NOT_READY` -> `Pendente`
- `READY` -> `Pronta`
- `BLOCKED` -> `Aguardando dados`
- `PARTIAL` -> `Parcial`
- `ACCEPTED` -> `Revisado`
- `DRE_ACCOUNT_UNMAPPED` -> `Conta sem classificação na DRE`
- `UNIT_UNMAPPED` -> `Unidade não vinculada`

Do not scatter enum translation through components.

## 15. States
Every major route must have polished:
- loading
- empty
- partial
- error
- permission denied

Do not show raw fetch/API exceptions.

## 16. Layout / typography
Reuse Onyx tokens.

Rules:
- one clear H1 per page
- compact subtitles
- consistent section spacing
- reduce giant blank areas
- avoid full-width paragraphs
- align financial numbers
- cards only where they add structure
- prefer existing table/card/drawer/dialog primitives

## 17. Responsive
Desktop is primary, but validate:
- 1440+
- ~1024
- ~768
- ~390 basic usability

Focus on:
- filters
- tables
- drawers
- chat input
- nav

Do not destroy financial-table density to force mobile cards.

## 18. Accessibility
Preserve:
- semantic controls
- keyboard/focus
- labels
- accessible names
- contrast
- tooltip accessibility

## 19. Do not change
Do NOT change:
- financial formulas
- review logic
- DRE readiness semantics
- financial mappings
- import semantics
- rule thresholds
- specialist business logic
- routine schedules
- customer data

This is primarily product/frontend work.

## 20. Implementation process
### Phase 1 — Visual audit
Use Chrome DevTools on:
- `/ton/controladoria`
- TON chat
- report
- `/ton/data-sources`
- DRE
- readiness
- specialists
- routines
- coverage

Record defects. Timebox 20–30 min.

### Phase 2 — Onyx pattern audit
Inspect polished existing Onyx screens/components. Timebox ~20 min.

### Phase 3 — Shell + overview
### Phase 4 — Chat + evidence + reports
### Phase 5 — DRE + readiness + sources
### Phase 6 — specialists + routines + coverage
### Phase 7 — responsive + visual QA

## 21. Validation
During development:
- focused frontend tests
- lint changed files
- format
- focused TypeScript
- Chrome visual inspection

Backend tests only when backend contracts change.

Final:
- relevant frontend suite
- lint
- format
- typecheck according to project convention
- `git diff --check`
- visual smoke of all demo routes

A screen does NOT pass merely because it compiles or has no overflow.

Evaluate:
- hierarchy
- scannability
- density
- consistency
- spacing
- alignment
- interaction clarity
- business language

If it still looks like Markdown, it is not done.

## 22. Demo acceptance
Tomorrow:
1. Controladoria feels like a product dashboard.
2. Chat tool activity is human-readable.
3. Evidence is a structured UI component.
4. Reports look professional.
5. R3 looks like an operational routine.
6. Specialists look intentional.
7. DRE looks like financial software.
8. Readiness looks like a work queue.
9. Sources look like integration/import management.
10. Raw JSON/UUIDs do not dominate any normal view.

## 23. Commit strategy
Prefer coherent commits:
- `refactor(ton): reorganizar experiencia principal`
- `feat(ton): melhorar chat evidencias e relatorios`
- `feat(ton): polir fluxos financeiros`
- `chore(ton): finalizar qa visual`

Do not push.

## 24. Final report
Report:
- baseline
- commits
- final HEAD
- clean tree
- routes changed
- components created
- Onyx primitives reused
- visual QA per route
- remaining design debt
- exact Luyla demo path

## Success condition
TON no longer looks like a Markdown/debug/admin prototype. It feels like one coherent enterprise controladoria product built on Onyx, with all existing functionality preserved.
