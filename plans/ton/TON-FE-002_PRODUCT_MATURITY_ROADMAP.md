# TON-FE-002 — Product Maturity & Interface Refinement Roadmap

## Context

The TON frontend rebuild reached a stable P0 on local `main`.

Current baseline reported by the previous implementation:
- HEAD: `ea11f7be6d`
- clean working tree
- no push
- P0 demo journey working
- Vale Norte branding applied
- TON-specific shell established
- custom client presentation over the existing runtime
- DRE / Pendências / Automações / Relatórios / Fontes operational
- native Onyx runtime capabilities preserved

This roadmap is the next stage.

It is NOT another rebuild of the same scope and it is NOT a cosmetic pass consisting of isolated CSS tweaks.

The objective is to turn the current good foundation into a coherent, mature product that feels intentionally designed end-to-end.

The implementing agent must inspect the actual repository and runtime before deciding exact implementation details. The roadmap describes the target product, not every implementation detail.

---

# 1. Product principle

## TON must feel like one product

Every primary surface should answer these questions quickly:

1. Onde estou?
2. O que está acontecendo?
3. O que precisa da minha atenção?
4. O que posso fazer agora?
5. O que o TON está fazendo por mim?

The client should never need to understand the underlying framework.

The product hierarchy is:

```text
Vale Norte
    ↓
TON
    ↓
Controladoria / Operação / Inteligência
    ↓
Workflows
    ↓
Dados + Especialistas + Automações
```

Onyx remains infrastructure.

---

# 2. Current baseline observations

The current screenshots show major progress, but also reveal the next layer of problems:

### Identity
The TON now has a clear Vale Norte identity. Preserve it.

### Shell
The new dark-green shell is much closer to the reference, but some surfaces still feel like adapted application pages rather than one unified product.

### Home
The new Home/Visão Geral works, but it still has room for:
- stronger visual hierarchy;
- better attention prioritization;
- better use of activity;
- more meaningful empty/healthy states;
- clearer relationship between TON, closing and automations.

### Assistant
The chat presentation is substantially improved, but the surrounding experience still needs stronger:
- conversational context;
- specialist/context awareness;
- analysis summaries;
- artifacts;
- follow-up actions;
- history semantics.

### Closing / DRE
The content is correct enough for the current scope, but the DRE still reads like an application page rather than a mature financial workspace.

### Pending decisions
The flow is understandable, but it can become much more task-oriented and less form-like.

### Sources
The model is correct, but the screen should feel like a data health/integration center instead of an import manager.

### Automations
Routines are now productized, but should feel more like automation management and less like a list of scheduled backend jobs.

### Reports
The result is cleaner, but report browsing/viewing should feel like a real deliverable workspace.

### Specialists
They are now understandable, but their relationship to the TON coordinator still needs stronger product expression.

### Admin
The generic Onyx administration experience remains a major source of “I am back inside Onyx” feeling.

### Login / account
The login still looks closer to a generic SaaS authentication page than a carefully branded Vale Norte internal product experience. Review whether:
- self-registration should exist at all;
- demo/test values should ever be visible;
- account recovery/onboarding needs its own TON treatment.

---

# 3. Priority model

## P0 — Product maturity
These should be handled before low-value cosmetic work:

1. global design system coherence;
2. navigation / information architecture refinement;
3. client/admin boundary;
4. login and account experience;
5. assistant workspace maturity;
6. Controladoria/Home maturity;
7. DRE/closing workspace refinement;
8. Sources / integration health;
9. Automations UX;
10. report viewer/catalog;
11. specialist/context experience;
12. global feedback/state system.

## P1 — Quality and depth
13. activity center;
14. notifications;
15. command/search experience;
16. responsive refinement;
17. accessibility;
18. performance;
19. empty/error/loading states;
20. browser metadata / favicon / installability;
21. print/export presentation.

## P2 — Longer-term
22. advanced personalization;
23. richer analytics interactions;
24. collaborative workflows;
25. more channels;
26. additional specialist surfaces.

---

# 4. Phase 0 — Audit before implementation

Inspect the current repository and compare the existing frontend against the target.

Audit:

- route tree;
- layout tree;
- global CSS/tokens;
- component primitives;
- typography;
- color tokens;
- sidebar/header;
- navigation;
- modal/drawer primitives;
- toast/notification system;
- loading/skeleton system;
- table/chart components;
- command/search components;
- chat components;
- report components;
- source components;
- admin routes;
- auth routes;
- i18n removal status;
- branding assets;
- all client-visible Onyx remnants;
- responsive breakpoints;
- dark/light behavior;
- accessibility patterns.

Produce a gap report in the task tracker.

The agent may change the ordering of phases after the audit.

---

# 5. Phase 1 — Global TON design system

The product now needs a consistent visual grammar.

Create/reuse a lightweight TON UI system.

## Tokens

Centralize:
- brand green;
- dark green shell;
- deeper shell surfaces;
- gold intelligence accent;
- warm attention;
- danger;
- success;
- info;
- neutral surfaces;
- border strengths;
- text hierarchy;
- spacing scale;
- radius scale;
- shadow policy;
- typography scale.

Do not create a large design-system package unless the repository architecture makes it worthwhile.

## Components

Create/reuse consistent primitives for:
- PageHeader;
- SectionHeader;
- StatusBadge;
- KPI;
- ActionButton;
- SecondaryButton;
- Card;
- MetricCard;
- Alert/AttentionCard;
- EmptyState;
- LoadingState;
- ErrorState;
- Drawer;
- Modal;
- Table;
- Timeline/Activity;
- RichEvidenceCard;
- ArtifactCard;
- SourceCard;
- RoutineCard;
- SpecialistCard.

All product surfaces should use the same primitives.

## Visual rule

A new page should look like TON without requiring custom CSS decisions from scratch.

---

# 6. Phase 2 — Navigation & information architecture

Refine the product hierarchy.

Recommended primary navigation:

```text
Visão Geral
Assistente
Fechamento
  DRE
  Pendências
Automações
Relatórios
Fontes
```

Specialists may remain secondary/contextual rather than a primary top-level destination if audit shows this creates a clearer product.

History belongs to the Assistant workspace, not as a generic application menu.

Technical diagnostics belong to admin.

## Navigation requirements

- persistent active context;
- breadcrumbs only when they add meaning;
- no duplicated navigation;
- no dead-end pages;
- predictable back behavior;
- deep links work;
- URLs map naturally to product concepts;
- no accidental return to generic Onyx.

---

# 7. Phase 3 — Header & global status

The top bar is a product command surface.

It should communicate:

- Vale Norte;
- TON;
- environment;
- sync/data freshness;
- notifications;
- help;
- user.

## Environment indicator

Synthetic/dev/demo data must remain honest.

Use a compact global indicator.

Do not repeat large “synthetic data” warnings in every card.

## Data freshness

Display freshness only when backed by actual source state.

Potential states:
- Atualizado;
- Atualizando;
- Atenção;
- Aguardando integração.

No fabricated “Sincronização OK”.

---

# 8. Phase 4 — Login / authentication

Reassess the current login experience.

Target:
- Vale Norte/TON visual identity;
- no generic Onyx feel;
- no developer/debug wording;
- no prefilled developer/test credentials in normal experience;
- Portuguese;
- appropriate password recovery;
- clear session error;
- loading state;
- optional invitation-only behavior if repository/auth model supports it.

Do not change authentication semantics unnecessarily.

Important:
Do not expose a “Criar uma conta” path merely because generic Onyx provides it if the TON deployment is controlled/invitation-based.

Decide from the actual auth model.

---

# 9. Phase 5 — Visão Geral maturity

Make Home the executive command center.

Recommended hierarchy:

### Header
Greeting + current closing context.

### Executive status
- Fechamento;
- DRE;
- Pendências;
- Fontes;
- próxima automação.

### Attention queue
Top issues first.

Each item:
- business meaning;
- impact/count;
- origin;
- CTA.

### TON activity
Show what TON actually did recently.

### Automation
R3 spotlight.

### Sources
compact health.

### Latest report
one or two current deliverables.

### Specialist context
only those actually involved.

Avoid:
- repetitive cards;
- duplicated data;
- large empty areas;
- backend terminology.

---

# 10. Phase 6 — Assistant / Agent Workspace maturity

This is one of the most important product areas.

The assistant should feel like an operational AI workspace, not a chat page.

## Conversation surface

Support:
- natural conversation;
- files;
- rich responses;
- structured evidence;
- artifacts;
- follow-up actions;
- specialist focus;
- analysis context.

## Context bar

When appropriate:

```text
TON
Contexto: Fechamento · Julho/2026
```

or:

```text
TON CFO
Foco: Fechamento financeiro
```

The user must understand what the TON is analyzing.

## Analysis lifecycle

Use a visual state model:

```text
Preparando
→ Consultando
→ Analisando
→ Consolidando
→ Concluído
```

Do not expose internal tool spam.

## Structured response model

Prefer rendering backend structures as components:

- executive answer;
- evidence;
- metric;
- finding;
- pending decision;
- report;
- source;
- routine result.

Markdown remains available for narrative, not as the entire product rendering strategy.

## Follow-up actions

After a result:

```text
Ver pendências
Abrir DRE
Gerar relatório
Perguntar ao CFO
```

Actions should be contextual.

## Conversation history

History should show meaningful titles and secondary metadata such as:
- last activity;
- domain;
- period.

Do not show meaningless “New Chat” entries when better titles can be generated.

---

# 11. Phase 7 — Closing / DRE maturity

The closing workflow should become a first-class product workspace.

Recommended:

```text
Fechamento
   Visão geral
   DRE
   Pendências
```

## Closing overview

Show:
- period;
- scope;
- closing state;
- DRE state;
- blockers;
- specialists involved;
- latest execution;
- next automated execution.

## DRE not ready

Present:

```text
DRE ainda não pode ser publicada

13 itens exigem atenção

Unidades       2
Dotação        2
Conciliação    3
Realizado      6
```

Each card:
- why;
- count;
- CTA.

## DRE ready

Present as financial software:
- hierarchy;
- monthly;
- YTD;
- variance;
- %;
- drill-down;
- source composition;
- export.

## Drill-down

Clicking a financial line should show:
- source facts;
- period;
- source;
- review state;
- provenance;
- amount.

Technical IDs remain secondary.

---

# 12. Phase 8 — Pending decisions maturity

Transform pending decisions into a proper work queue.

Views:
- Todas;
- críticas;
- por categoria;
- por período;
- resolvidas/recentemente resolvidas.

Card should answer:

```text
O que aconteceu?
O que precisa ser decidido?
Quantos registros serão afetados?
Qual a sugestão?
O que muda se eu aprovar?
```

Decision flow:
- review;
- select;
- justify;
- confirm;
- audit.

No silent mutation.

---

# 13. Phase 9 — Sources / Integration Center

Rename concept mentally from “uploads” to “data health”.

Each source should expose:

```text
NG / Keevo
Status
Última atualização
Modo atual
Cobertura
Problemas
Integração direta
```

## Source lifecycle

```text
Conectado
Atualizando
Atualizado
Atenção
Aguardando configuração
Indisponível
```

Only use real backend state.

## NG

Current truth:
manual file acquisition.

Future:
direct VPN/API/read-only DB.

The UI should clearly show this transition without pretending it already exists.

## Import flow

Make it a guided operation:
1. choose source;
2. choose file;
3. validate;
4. process;
5. review;
6. publish to canonical dataset.

Keep technical diagnostics behind detail.

---

# 14. Phase 10 — Automations maturity

Automations should feel like the autonomous heart of TON.

Primary card:
- automation name;
- what it does;
- schedule;
- next execution;
- last execution;
- outcome;
- active/blocked state.

## R3

Make the flagship.

Show:
- first business day;
- 08:00 Brasília;
- next execution;
- latest result;
- blockers;
- Execute agora.

Execution states should be visible and persistent.

## History

Show runs in a timeline/table:

```text
03/10 — concluído com pendências
01/10 — concluído com pendências
...
```

Technical 21-step trace is secondary.

---

# 15. Phase 11 — Reports maturity

Reports become deliverables.

## Catalog

Organize by:
- period;
- type;
- latest;
- revisions.

Avoid repeated cards for every execution.

## Viewer

Strong hierarchy:

```text
VALE NORTE
TON

Relatório de fechamento
Julho/2026 · Consolidado

Resumo executivo

Principais achados

Pendências

Ações

Fontes

Rastreabilidade
```

Include:
- print-friendly styling;
- download;
- version context;
- synthetic/demo status when applicable.

---

# 16. Phase 12 — Specialists maturity

Do not make the specialist page the product center.

Use specialists where they create context.

Examples:

```text
Análise realizada por
TON CFO
TON AUDITOR
TON CEO
```

Click:
`Ver análise do especialista`

opens focused context inside TON.

## Specialist detail

Should answer:
- role;
- current availability;
- capabilities;
- required sources;
- last involvement;
- why blocked.

Avoid:
- technical agent admin concepts;
- generic Onyx Persona terms.

---

# 17. Phase 13 — Activity & notifications

Build a consistent global event model.

Examples:
- import finished;
- routine started;
- routine finished;
- DRE became ready;
- decision changed;
- report generated;
- source failed.

Header notification center can summarize events.

Avoid notification spam.

---

# 18. Phase 14 — Search / command experience

TON eventually needs a strong command/search layer.

Possible commands:

```text
Abrir DRE de julho
Ver pendências
Analisar fechamento
Mostrar último relatório
Abrir fontes
```

Reuse existing Onyx command/search infrastructure where sensible.

The client should not have to remember exact routes.

---

# 19. Phase 15 — Administration experience

This is a distinct product area.

Do not try to turn every generic Onyx admin screen into “TON”.

Instead create a clean separation:

```text
TON
 └── Administração do TON

Sistema
 └── Administração técnica
```

## Administração do TON

Only product-relevant configuration:
- user access;
- roles;
- source configuration;
- automation settings;
- specialist availability;
- financial readiness controls;
- report/publication settings;
- audit.

## Administração técnica

Only for technical administrators:
- native Onyx agents/personas;
- model/provider configuration;
- MCP/OpenAPI;
- generic connectors;
- infrastructure diagnostics.

Do not expose technical admin to normal users.

## UX requirement

Technical admin should still feel intentional.

At minimum:
- branded shell;
- clear section hierarchy;
- breadcrumbs;
- searchable settings;
- grouped configuration;
- unsaved-change handling;
- confirmation for destructive operations.

Do not fully rebuild every upstream admin page if reuse is safe.

---

# 20. Phase 16 — Global states

Every important product component should have:

- loading;
- empty;
- success;
- partial;
- warning;
- error;
- unauthorized;
- offline/connection degraded.

No silent transitions.

Buttons that trigger background operations must explain:
- started;
- running;
- completed;
- failed.

---

# 21. Phase 17 — Responsive / accessibility

Test:
- 1440+;
- 1280;
- 1024;
- 768;
- 390.

Check:
- sidebar collapse;
- right-rail transformation;
- tables;
- drawers;
- chat composer;
- sticky actions;
- no horizontal scroll;
- keyboard focus;
- semantic buttons/links;
- readable contrast;
- modal focus trap.

---

# 22. Phase 18 — Production polish

Audit:
- page titles;
- favicon;
- manifests;
- OpenGraph where relevant;
- loading/splash;
- version placement;
- error pages;
- not-found;
- auth failure;
- maintenance state.

No client-facing:
- `0.0.0-dev`;
- internal build debug strings;
- UUIDs;
- raw JSON;
- provider names;
- Onyx branding.

---

# 23. Phase 19 — Data truth and backend contract

For every important UI state, record source:

```text
UI element → endpoint/service → field → transformation
```

Especially:
- DRE state;
- blockers;
- source state;
- specialist state;
- routine schedule;
- routine result;
- notifications;
- report status.

Never rebuild domain logic in React simply to make the screen work.

If aggregation belongs in backend:
add the smallest clean read model/API.

---

# 24. Phase 20 — Visual QA methodology

The new agent must judge the product as a product.

For every P0/P1 page:

1. open in real Chrome;
2. inspect at target viewport;
3. compare with `ton_reference_visual`;
4. verify content hierarchy;
5. verify primary CTA;
6. verify actual backend state;
7. test keyboard;
8. test loading/error/empty.

Passing TypeScript/build is not visual acceptance.

---

# 25. Definition of Done

A surface is not done if it merely:
- compiles;
- passes a unit test;
- renders the backend response.

A surface is done when:
- it belongs unmistakably to TON;
- hierarchy is immediately clear;
- the client understands it without technical explanation;
- primary action is obvious;
- state is truthful;
- loading/errors are explicit;
- it uses the global TON design language;
- it does not feel like generic Onyx;
- it does not read like Markdown;
- it does not expose backend internals.

---

# 26. Delivery strategy

Do not produce one enormous frontend diff.

Use vertical slices.

Recommended commit groups:

1. `refactor(ton): consolidate product design system`
2. `refactor(ton): mature navigation and shell`
3. `feat(ton): refine assistant workspace`
4. `feat(ton): refine closing and financial workspaces`
5. `feat(ton): refine sources and automations`
6. `feat(ton): refine reports and specialist context`
7. `refactor(ton): separate product and technical administration`
8. `chore(ton): harden visual and responsive quality`

The agent may consolidate or reorder when justified.

Do not push.

---

# 27. Final priority rule

When choosing between:
- deeper internal architecture;
- additional business features;
- more polished existing product experience;

prioritize the polished experience first, unless the deeper architecture is required to prevent a false or fragile UI.

The goal of this roadmap is not to increase the number of screens.

It is to make the existing capabilities feel like one mature product.
