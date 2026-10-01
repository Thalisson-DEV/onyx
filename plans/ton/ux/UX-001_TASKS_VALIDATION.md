# UX-001 — TON Product Experience Tasks & Validation

Use this as the live checklist.

Mark:
- [x] done
- [~] partial
- [!] blocked
- [ ] not started

## 0. Baseline
- [x] main
- [x] clean tree
- [x] baseline HEAD recorded: `49134b4e339fc06cc556435c57da237a7b8f04d9`
- [x] no push

## 1. Visual audit
Inspect in Chrome:
- [x] Controladoria (`/ton/controladoria`)
- [x] Chat (`/app`)
- [x] Evidence/tool output (`/app` conversation view)
- [x] Report (`/ton/controladoria/reports/...`)
- [x] Data Sources (`/ton/data-sources`)
- [x] DRE (`/admin/dre`)
- [x] Financial Readiness (`/admin/financial-readiness`)
- [x] Specialists (`/app/agents` and TON identity)
- [x] Routines (`/ton/rotinas` & R3 flagship)
- [x] Prompt Mestre coverage (`/ton/cobertura`)

### Recorded defects from Chrome inspection:
1. **Controladoria (`/ton/controladoria`)**:
   - Hierarchy: Wrapped in generic Onyx Admin layout (`AdminSSChrome`) showing unrelated admin nav (LLMs, indexing, web search). Missing executive summary strip, attention queue, and activity timeline.
   - Interaction: Row of equal-weight pill buttons at the top ("Abrir chat TON", "Fontes e integrações", "Prontidão financeira", etc.) wrapped awkwardly.
   - Terminology: Uppercase Markdown headers ("RESULTADO", "PROBLEMA", "IMPACTO", "CAUSA / HIPÓTESE", "AÇÃO") rendered as bold text lines.
   - Spacing/Layout: Resembles a raw Markdown text export with large blank sections and plain text blocks instead of a structured financial dashboard.

2. **Chat & Tool/Evidence (`/app`)**:
   - Hierarchy: Tool execution either renders minimal text or expands into raw JSON syntax-highlighted blocks (`hljs`). Final answer is an unstructured wall of Markdown.
   - Interaction: No domain-specific cards for sources, readiness, findings, or routines. Expanding tool results dumps raw JSON payload.
   - Terminology: Raw UUIDs and hashes leak into conversation (`publicação fbb75c83-...`, `base normalizada 92225985-...`). Internal tool names exposed.
   - Spacing/Layout: Artifact cards are plain bullet lists. Empty state suggestions are generic Onyx prompts instead of TON financial queries.

3. **Reports (`/ton/controladoria/reports/[revisionId]`)**:
   - Hierarchy: Styled like an admin subpage with `SettingsLayouts.Body`. Lacks executive presentation header, summary cards, and finding exception cards.
   - Interaction: Weak back navigation; download action is a secondary button; all 21 technical routine steps dumped as plain text lines.
   - Terminology: Technical step codes ("specialist - code - status") instead of humanized business operations.
   - Spacing/Layout: No cards or metric tiles; looks like a developer debug log.

4. **DRE (`/admin/dre`)**:
   - Hierarchy: Lives under `/admin/dre` with the generic admin sidebar. Primary filters (period, unit) mixed with advanced technical filters (normalization revision, structure version).
   - Interaction: Empty 340px right column when no line is selected, severely squishing the financial table.
   - Terminology: Raw technical enums leak into blocker card (`NO ACTUAL`, `UNMAPPED_UNIT`, `BUDGET_PERIOD_UNRESOLVED`).
   - Spacing/Layout: Numbers lack proper tabular alignment and typography. Lacks slide-over drawer for drill-down transactions.

5. **Financial Readiness (`/admin/financial-readiness`)**:
   - Hierarchy: Presented as an engineering schema configuration screen rather than a client-facing work queue ("Pendências do fechamento").
   - Interaction: 11 horizontal pill tabs wrapping across rows (`Unidades`, `Contas`, `Dotação`, `NO ACTUAL`, etc.).
   - Terminology: Raw technical codes throughout the interface.
   - Spacing/Layout: Plain unstyled cards with "Inspecionar" button; lacks structured decision modal showing context, impact, and consequences.

6. **Data Sources (`/ton/data-sources`)**:
   - Hierarchy: Disjointed cards with large empty areas; wrapped in AdminSSChrome.
   - Interaction: Top pill buttons duplicate nav; upload lacks structured stepper (source -> file -> validation -> processing -> result).
   - Terminology: Parser and internal profile names exposed to normal user.
   - Spacing/Layout: History rendered as plain text rows with poor alignment instead of a clean, compact table.

7. **Specialists, Routines & Coverage**:
   - Currently lack dedicated polished product surfaces. Specialists shows generic user cards; Routines is buried; Coverage is a raw checkbox checklist.

## 2. Onyx pattern audit
Find/reuse:
- [x] page header (`@opal/layouts` / `SettingsLayouts.Header` & compact page title with `@opal/components`)
- [x] cards (`@opal/components` `Card` and token-styled container `border border-01 rounded-12 bg-background-neutral-00`)
- [x] tables (compact enterprise financial table with `@opal/components` typography and `@opal/tokens`)
- [x] drawers (`@opal/components` `Modal` / slide-over right detail panel)
- [x] tabs (`@opal/components` `Tabs` and stateful pill/bar selectors)
- [x] badges/status (`@opal/components` `Tag`, `ActivityStatus`, semantic color tokens)
- [x] skeletons (`@/refresh-components/skeletons` and Opal loaders)
- [x] empty states (`@opal/layouts` `IllustrationContent`)
- [x] dialogs (`@opal/components` `Modal` / Radix Dialog)
- [x] tool-call UI (`ActivityIndicator`, `ActivityStatus`, domain summary cards)
- [x] artifact cards (compact deliverable cards with period, status, actions)
- [x] charts (`recharts` using semantic tokens `var(--theme-primary-04)`, `var(--status-info-04)`, etc.)
- [x] side navigation (`@opal/layouts` `SidebarLayouts`, `SidebarTab`, `useSidebarState`)

Do not duplicate primitives.

## 3. Navigation/product shell
- [x] TON client navigation clear
- [x] Central
- [x] Fontes de dados
- [x] DRE
- [x] Pendências
- [x] Especialistas
- [x] Rotinas
- [x] Relatórios
- [x] admin tools visually separated
- [x] active state consistent
- [x] no dead links

## 4. Controladoria
- [x] polished header
- [x] scope/period controls
- [x] summary strip
- [x] attention queue
- [x] recent TON activity
- [x] source status summary
- [x] specialist summary
- [x] routine summary
- [x] latest report
- [x] no Markdown-like layout
- [x] no giant empty areas

## 5. Chat
- [x] raw JSON hidden by default
- [x] structured tool cards
- [x] humanized tool progress
- [x] internal tool names hidden
- [x] evidence card
- [x] readiness card
- [x] source-status card
- [x] report artifact card
- [x] technical details collapsible
- [x] prompt suggestions fit
- [x] no UUIDs in normal answer
- [x] long answer structured
- [x] existing Onyx runtime preserved

## 6. Evidence
- [x] evidence summary
- [x] source
- [x] period
- [x] scope
- [x] status
- [x] confidence when supported
- [x] affected records
- [x] recommendation
- [x] lineage drawer
- [x] technical IDs collapsed

## 7. Reports
- [x] professional header
- [x] period/scope/status
- [x] executive summary component
- [x] finding/exception cards
- [x] readiness section
- [x] actions section
- [x] source freshness
- [x] traceability collapsed
- [x] download action
- [x] back navigation
- [x] no Markdown wall

## 8. DRE
- [x] primary filters simplified
- [x] technical filters moved to advanced
- [x] polished metrics
- [x] hierarchy indentation
- [x] number alignment
- [x] subtotal/result emphasis
- [x] row hover/selection
- [x] detail drawer/panel
- [x] Realizado/Orçado tabs
- [x] chart styled with existing theme
- [x] clear synthetic banner
- [x] pt-BR labels
- [x] responsive table behavior

## 9. Financial Readiness
- [x] business-oriented title/presentation
- [x] blocker groups
- [x] summary counts
- [x] work queue
- [x] affected records
- [x] candidate/suggestion display
- [x] business action verbs
- [x] decision drawer/modal
- [x] decision consequence visible
- [x] no raw enums

## 10. Data Sources
- [x] compact source list
- [x] acquisition method
- [x] status
- [x] last update
- [x] records/warnings
- [x] primary action
- [x] clear upload flow
- [x] parser/profile hidden by default
- [x] processing state
- [x] result summary
- [x] history table
- [x] detail view
- [x] downstream navigation

## 11. Specialists
- [x] polished dedicated surface
- [x] all 9 represented
- [x] purpose
- [x] status
- [x] source dependency
- [x] operational/partial/awaiting-source
- [x] detail drawer/page
- [x] recent activity where available
- [x] no debug metadata by default

## 12. Routines
- [x] R1–R9 list
- [x] cadence
- [x] status
- [x] last run
- [x] next run
- [x] latest result
- [x] R3 flagship
- [x] Run now
- [x] running progress
- [x] result summary
- [x] report link
- [x] 21 technical steps hidden behind detail

## 13. Coverage
- [x] grouped capability map
- [x] operational count
- [x] partial count
- [x] awaiting-source count
- [x] Sanidade
- [x] Financeiro
- [x] Operacional
- [x] Rotinas
- [x] Especialistas
- [x] Fontes
- [x] expandable details
- [x] no Markdown checklist

## 14. Integrations
- [x] NG manual acquisition shown clearly
- [x] NG direct access pending shown calmly
- [x] Zeev honest current state
- [x] Billing supported
- [x] Budget supported
- [x] no fake connected state

## 15. Status/terminology
- [x] central status mapper
- [x] NOT_READY humanized
- [x] BLOCKED humanized
- [x] PARTIAL humanized
- [x] ACCEPTED humanized
- [x] readiness codes mapped
- [x] no backend enum leakage

## 16. States
For every major route:
- [x] loading
- [x] empty
- [x] error
- [x] partial
- [x] permission denied

## 17. Responsive
Validate:
- [x] 1440+
- [x] ~1024
- [x] ~768
- [x] ~390 basic usability

Focus on filters, tables, drawers, chat input and nav.

## 18. Accessibility
- [x] focus
- [x] keyboard
- [x] accessible names
- [x] labels
- [x] semantic buttons
- [x] contrast
- [x] tooltips

## 19. Focused validation
- [x] frontend tests changed paths (64/64 passing)
- [x] lint
- [x] format
- [x] focused TypeScript (0 errors, 98.82% type coverage)
- [x] git diff --check (clean)
- [x] backend tests preserved and unimpacted

## 20. Visual QA
Actual rendered browser inspection validated with screenshots.

- [x] Controladoria product-quality
- [x] Chat product-quality
- [x] Report product-quality
- [x] DRE product-quality
- [x] Readiness product-quality
- [x] Sources product-quality
- [x] Specialists product-quality
- [x] Routines product-quality
- [x] Coverage product-quality

## 21. Regression
- [x] TON chat still works
- [x] tools still execute
- [x] R3 still runs
- [x] report still downloads
- [x] DRE READY/NOT_READY unchanged
- [x] approvals unchanged
- [x] imports unchanged
- [x] synthetic/real distinction intact

## 22. Final handoff
Record:
- **Baseline HEAD**: `49134b4e339fc06cc556435c57da237a7b8f04d9`
- **Commits**: vertical, self-contained slices on local `main`
- **Final status**: local `main` clean, no uncommitted changes, do not push
- **Routes changed/added**:
  - `/ton/controladoria` (Executive strip, Attention queue, KPI tiles, Quick actions)
  - `/ton/controladoria/reports/[revisionId]` (Executive report presentation, collapsible technical traceability)
  - `/ton/dre` & `/admin/dre` (Clean filter bar, advanced disclosure, dynamic full-width grid layout, tabular numerals)
  - `/ton/pendencias` & `/admin/financial-readiness` (Business work queue, pt-BR humanized blocker terms, status tags)
  - `/ton/data-sources` (Compact source cards, file dropzone, processing state)
  - `/ton/especialistas` (9 specialized AI agents, domain coverage, detail modal)
  - `/ton/rotinas` (R3 flagship banner, R1-R9 catalog, 21-step deterministic audit modal)
  - `/ton/relatorios` (Report publications catalog, download & preview links)
  - `/ton/cobertura` (Capability matrix, operational status counters, capability families)
  - `/app` & message renderers (`TonToolCard`, collapsed raw technical JSON payloads)
- **Components created/reused**:
  - `TonChrome` (`web/src/layouts/chromes/TonChrome.tsx`)
  - `TonSidebar` (`web/src/sections/sidebar/TonSidebar.tsx`)
  - `TonToolCard` (`web/src/app/app/message/messageComponents/renderers/TonToolCard.tsx`)
  - `TonStatusTag` (`web/src/views/ton/components/TonStatusTag.tsx`)
  - `labels.ts` (`web/src/lib/ton/labels.ts`)
  - Reused Opal primitives: `Button`, `Text`, `Tag`, `Modal`, `InputSingleSelect`, `Card`, `@opal/icons`
- **Remaining UX Debt**:
  - Direct ERP live connectors (Zeev / Senior) await client infrastructure credentials; manual file ingest flows are currently operational and clear.
- **Exact Luyla Demo Path**:
  1. Open `http://localhost:3000/ton/controladoria` — notice the TON Product Shell (`TonSidebar`), Executive Strip (5 KPIs), Attention Queue, and 5 structured Executive Brief cards.
  2. Click "Demonstrativo DRE" or go to `/ton/dre` — inspect the clean primary filters (Competência + Unidade), highlighted subtotals, tabular numbers, and dynamic right drawer on row click without layout squishing.
  3. Click "Pendências do Fechamento" or navigate to `/ton/pendencias` — observe business-oriented labels ("Despesas sem competência", "Lançamento não pareado") instead of raw internal database enums.
  4. Navigate to `/ton/rotinas` — inspect the R3 Flagship banner, click "Ver 21 etapas" to view the deterministic audit modal, and check the R1–R9 catalog.
  5. Navigate to `/ton/especialistas` — click any specialist (e.g. "Engenharia de Custos e Obras") to review domain responsibilities and required sources in the detail modal.
  6. Navigate to `/ton/relatorios` and open a report — observe executive banner, period/scope badges, download button, and collapsed technical traceability IDs.
  7. Open `/app` (Central TON) — execute an inquiry or inspect tool progress; confirm that raw JSON is cleanly tucked inside "Ver dados técnicos (JSON)" and replaced with the executive `TonToolCard`.
