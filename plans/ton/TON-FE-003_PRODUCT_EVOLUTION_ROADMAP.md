# TON-FE-003 — Product Evolution: Finance Operations, Pending Resolution & Continuous Gap Discovery

## Purpose

The TON now has a credible client identity and a usable P0 frontend. The next step is not another visual-only sprint.

The product must start delivering **real day-to-day value to Finance/Controladoria**, especially around:

- identifying what needs attention;
- resolving pending decisions;
- understanding consequences;
- re-running analysis safely;
- generating trustworthy outputs;
- reducing repetitive control work;
- making the TON proactively useful without inventing facts.

This roadmap also gives the implementing agent an explicit mission to **find gaps that we have not identified ourselves**.

The agent is expected to challenge the current product, not merely implement a fixed backlog.

---

# 1. Product north star

TON should become the operational layer between data and financial decisions.

```text
Dados
  ↓
Validação
  ↓
Detecção
  ↓
Evidência
  ↓
Decisão
  ↓
Reprocessamento
  ↓
Resultado
  ↓
Acompanhamento
```

The key missing transition after the current P0 is:

> **“TON found something” → “Finance resolved it” → “TON recalculated what changed”.**

That loop is the main macro focus.

---

# 2. Non-negotiable principles

## 2.1 Product before feature count

Do not add screens merely because the Prompt Mestre lists capabilities.

A feature is valuable only when it reduces effort, increases visibility, improves control, or creates a trustworthy decision workflow.

## 2.2 Evidence before AI

TON may:
- summarize;
- explain;
- prioritize;
- suggest;
- formulate next actions.

TON may not invent:
- source values;
- approvals;
- financial mappings;
- integrations;
- business facts;
- consequences not supported by deterministic data.

## 2.3 Human decisions remain explicit

Approvals, mappings, authority decisions and other financial governance actions remain human-controlled.

AI can assist the decision; it does not silently make it.

## 2.4 No AI-slop UX

Do not use:
- giant decorative AI cards;
- fake “insights”;
- excessive gradients;
- meaningless animations;
- generic chatbot filler;
- repeated summaries;
- empty dashboards;
- invented KPIs;
- technical information presented as value.

Every visible element needs a job.

## 2.5 One coherent workflow

The same pending item should be resolvable from:
- Home;
- Closing;
- DRE;
- Assistant;
- Reports;

without losing context.

---

# 3. Agent autonomy: GAP DISCOVERY is part of the task

The agent must perform a structured gap audit before major implementation.

It should inspect:

- current UX;
- backend capabilities;
- existing APIs;
- current database/domain models;
- current demo journey;
- Prompt Mestre;
- existing financial workflow documentation available in the repository;
- previously identified client problems;
- current UI screenshots/reference;
- current navigation and admin boundaries.

The agent should identify:

### Product gaps
Capabilities that materially limit daily use.

### Workflow gaps
Places where the user still has to leave TON, copy values, reconcile manually, or repeat work.

### Data gaps
Important decisions blocked because a source, field, mapping or authority is missing.

### UX gaps
Confusing flows, duplicated information, excessive clicks, hidden state, weak CTAs, poor feedback.

### Trust gaps
Places where the system does not adequately explain:
- what it knows;
- why it reached a conclusion;
- what is still uncertain;
- what changed after a decision.

### Automation gaps
Places where TON detects something but does not:
- follow up;
- notify;
- re-check;
- retry;
- close the loop.

### Presentation gaps
Surfaces that technically work but still look generic, internal, AI-generated or unfinished.

For each discovered gap, record:

```text
Gap
Observed evidence
User impact
Why it matters
Possible solution
Dependencies
Confidence
Priority
```

Do not implement speculative ideas just because they sound sophisticated.

---

# 4. Phase 0 — Baseline & gap report

Deliverable:

`plans/ton/TON-FE-003_GAP_REPORT.md`

The report must contain:

1. current product strengths;
2. current weaknesses;
3. critical workflow gaps;
4. highest-value missing capabilities;
5. UX issues;
6. trust/explainability issues;
7. automation gaps;
8. data/integration blockers;
9. recommended P0/P1/P2 changes.

The agent may revise this roadmap after the audit when justified by repository evidence.

---

# 5. Phase 1 — Pending Resolution Engine

This is the main development target.

Turn the current readiness workflow into a complete decision-resolution loop.

## Required flow

```text
Finding / Blocker
      ↓
Inspect evidence
      ↓
Understand decision
      ↓
Candidate (if deterministic evidence exists)
      ↓
Human chooses
      ↓
Justification
      ↓
Confirm
      ↓
Persist new version
      ↓
Recompute readiness
      ↓
Show what changed
```

## UX must show

- what was detected;
- source;
- affected records;
- period/unit;
- candidate;
- confidence/evidence basis when available;
- what approving changes;
- what remains blocked;
- who decided;
- when;
- version.

## After a decision

Do not simply display “saved”.

Show:

```text
Decisão registrada

2 registros afetados
Readiness recalculada

Antes:
13 bloqueios

Agora:
11 bloqueios

DRE:
Ainda não pronta
```

Only when deterministic facts support these numbers.

## Batch resolution

Investigate whether multiple equivalent pending items can be safely resolved together.

Example:
- several rows share the same exact account mapping;
- multiple records share the same verified unit mapping.

Batch actions must:
- show scope;
- preview consequence;
- require explicit confirmation;
- create auditable versioned decisions.

Never bulk-approve ambiguous items.

---

# 6. Phase 2 — Closing Control Center

Evolve “Fechamento” from a reporting page into an operational workspace.

It should answer:

```text
Como está o fechamento?
O que falta?
O que mudou desde a última análise?
O que precisa de uma pessoa?
O que o TON já fez?
O que será feito automaticamente?
```

Recommended structure:

- status;
- blockers;
- recently resolved;
- activity;
- next actions;
- latest DRE state;
- latest report;
- next automated execution.

Include change summaries when backed by data:

```text
2 pendências resolvidas desde a última análise
1 nova divergência detectada
```

Do not invent trends.

---

# 7. Phase 3 — Finance work queue

Create a cross-module work queue that unifies:

- financial blockers;
- decisions;
- findings;
- overdue actions;
- source problems.

The goal is not another inbox.

It is the place where Finance can answer:

> “O que eu preciso resolver hoje?”

Each item should have:
- priority;
- owner when known;
- deadline when known;
- source;
- evidence;
- impact;
- action;
- current state.

Do not invent owners/deadlines if the source does not contain them.

---

# 8. Phase 4 — Assistant ↔ product actions

TON should stop being only an analysis endpoint.

A conversation should be able to take the user directly to the correct action.

Examples:

User:
“Por que a DRE está bloqueada?”

TON:
structured explanation

CTA:
`Resolver 3 conciliações`

User:
“Quais pendências posso resolver agora?”

TON:
list supported actions

CTA:
`Abrir fila de decisões`

User:
“O que mudou depois das decisões?”

TON:
change summary based on the persisted versions.

The assistant should deep-link into product context instead of only generating prose.

---

# 9. Phase 5 — Closed-loop automation

Find opportunities for TON to follow up after human decisions.

Examples:
- recompute readiness;
- detect whether a blocker disappeared;
- detect new blockers created by the new state;
- notify that DRE became ready;
- regenerate a report when a meaningful state change occurs;
- remind about unresolved items when a real deadline exists.

Do not create noisy autonomous behavior.

Every automated action must be:
- explainable;
- idempotent;
- auditable;
- bounded.

---

# 10. Phase 6 — Agentic proactive intelligence

Only after the decision loop is reliable.

Investigate capabilities where TON can proactively say:

```text
Encontrei algo novo.

Desde a última análise:
- ...
- ...

Isso exige sua decisão.
```

Potential domains:
- financial anomalies;
- source freshness;
- closing blockers;
- reconciliation changes;
- repeated corrections;
- recurring exceptions.

The agent must first determine which of these are actually supported by current data.

No fake anomaly detection.

No arbitrary thresholds copied from demos.

---

# 11. Phase 7 — Daily Finance utility

Identify repetitive activities still outside TON and determine which can be safely absorbed.

Potential categories:

- daily opening/check;
- pending decision follow-up;
- closing preparation;
- review of source freshness;
- recurring exception review;
- report generation;
- “what changed since yesterday?”;
- “what requires me today?”;
- “what is waiting on another person?”

Do not implement all categories automatically.

Rank them by observed evidence and current system capability.

---

# 12. Phase 8 — UX quality pass driven by evidence

After the macro workflow works, audit every primary surface again.

Evaluate:

### Information hierarchy
Can the user understand the state in seconds?

### Actionability
Is the next action obvious?

### Feedback
Does every mutation explain what happened?

### Continuity
Does navigation preserve context?

### Density
Is there too much empty space or too much information?

### Consistency
Are the same concepts represented identically everywhere?

### Trust
Can the user see evidence without seeing implementation internals?

### Product identity
Does it still feel like TON/Vale Norte?

### AI quality
Does it feel like useful intelligence or decorative chatbot UI?

Fix systemic problems in shared components rather than patching every screen separately.

---

# 13. Phase 9 — UX research / improvement sources

When useful, the agent may inspect external references for:
- modern B2B finance software;
- controllership/FP&A workflows;
- ERP decision queues;
- audit/evidence interfaces;
- agentic enterprise UX;
- data-health/integration UX.

External references must inspire patterns, not copy branding or unsupported functionality.

Record meaningful references in the gap report or decision log.

---

# 14. Phase 10 — Admin/configuration maturity

Only after the client workflow is strong.

Separate:

```text
TON
→ Administração do TON
```

from:

```text
Sistema
→ Administração técnica / Onyx
```

TON administration may include:
- access;
- source configuration;
- automation configuration;
- specialist availability;
- financial decision controls;
- publication;
- audit.

Generic Onyx administration remains technical.

Do not rebuild the entire Onyx admin unless necessary.

---

# 15. Data and backend boundaries

The frontend must not become the financial rules engine.

For each important workflow:

```text
UI
→ API/read model
→ domain service
→ persisted state
```

Prefer backend aggregation when it avoids excessive client requests.

Add APIs only where the current domain model cannot provide a clean product workflow.

Keep:
- versioning;
- lineage;
- audit;
- human decision boundaries;
- deterministic calculations.

---

# 16. Definition of Done

A macro feature is complete when:

- it solves a real workflow;
- it uses real backend truth;
- it has a clear user action;
- mutations are auditable;
- state survives refresh;
- user can understand the consequence;
- assistant/product navigation is connected;
- errors/loading/empty states are handled;
- the feature is visually consistent with TON;
- the feature does not feel like generic Onyx or AI decoration.

---

# 17. Delivery protocol

Use vertical slices.

After each stable slice:
1. update `TON-FE-003_TASKS.md`;
2. update decisions/gap report;
3. run focused validation;
4. inspect in Chrome;
5. commit locally;
6. continue to the next highest-value task.

The agent may alter the roadmap order when evidence supports it.

Do not stop after every phase.

Stop only for:
- destructive migration;
- external credentials/access;
- unrelated user work;
- materially consequential ambiguity;
- anything that would require fabricated data/capability.

Do not push.

---

# 18. Final deliverable

The project should progress from:

```text
TON analyzes
```

to:

```text
TON analyzes
→ explains
→ identifies
→ guides decision
→ records decision
→ recalculates
→ shows consequence
→ follows up
→ reports change
```

That closed loop is the core of the next product stage.
