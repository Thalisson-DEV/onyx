# Plan 003 readiness gate — TON domain schema

Read-only readiness assessment for `003-domain-rules-findings.md`. This document
closes architectural ambiguity before the first TON-owned migration exists. It
creates no model, no migration and no API. It changed no application code and no
database.

- **Baseline commit**: `73b8ec4d34c34eb90abc784bcff542117164f515` (`main`, equal to
  `origin/main`).
- **Assessed at**: 2026-09-15.
- **Inputs**: `plans/ton/masterprompt.md` (TON VALE Prompt Mestre v2.0, read in
  full), `roadmap.md`, `003-domain-rules-findings.md`, `gap-analysis.md`,
  `decision-log.md`, `domain-rules.md`, `plans/ton/capability-edition-audit.md`,
  `007-deployment-hardening.md`, `008a-capability-gates.md`, `coordination.md`,
  `plans/ton/frontend/backend-dependencies.md`, `findings-ux-plan.md`,
  `reports-ux-plan.md`, root and `backend/` AGENTS instructions,
  `CONTRIBUTING.md` engineering best practices.

---

## 1. Verdict

# READY

Plan 003 is safe and sufficiently specified to implement, as the four slices in
section 21, with one carve-out: **slice 003a waits on open decision 7a**
(encryption-key custody). Slices 003b, 003c and 003d may proceed now.

The gate's success condition required two things to be understood. Both are.

| Question | Answer |
|---|---|
| Is the migration history understood? | **Yes.** Revision `6e8f0a2b1c35` is fully identified (§17, verdict A). The repository history is linear with a single head `ad99acb9be41`. An empty disposable database reaches head cleanly. |
| Is the domain contract understood? | **Yes.** Sections 3–15 close every architectural question the plan left open. |
| Can the first TON migration be created and applied now? | **Yes.** Verified directly: the live database now reports `ad99acb9be41`. |
| What exactly should it contain, in what order, with which guarantees? | Sections 19, 10, 11 and 20. |

### Why this verdict changed during the gate

This assessment opened as BLOCKED on four items. Three cleared during the gate.

**B1 — cleared, verified directly.** The primary blocker was that the local
database was stamped at orphan revision `6e8f0a2b1c35`, so no migration could be
applied to it. Plan 001 recorded that state. It is no longer true. A read-only
query confirms:

| Check | Result |
|---|---|
| `public.alembic_version` | **`ad99acb9be41`** — the repository head |
| row count in `alembic_version` | 1 |
| public tables | **151** — identical to a freshly migrated disposable database |
| `persona.ton_role` (the orphan migration's column) | **absent** |
| schemas present | `public` only |
| TON domain tables | **0** — the first TON migration genuinely does not exist yet |
| existing data | 2 users, 2 chat sessions, 2 user groups, 2 permission grants |

The database is repository-consistent and accepts a new migration. Section 17.4's
remedies are retained for the record but are no longer required.

**B2 — cleared by this document.** Plan 003 stops if "domain keys, limits, units,
retention or immutable snapshot approval is missing". Sections 3–15 supply the
domain keys (§7), the units and rounding contract (§3, §12), the immutable
snapshot decision including its canonicalisation rules (§12), and the two scope
areas the plan omitted entirely: resource ACLs (§10) and the audit-history model
(§11). Plan 003 now points here and lists both in its scope and done criteria.

**B3 — corrected.** Two of the five commands Plan 003 told its executor to run
cannot pass. Both are now removed from the plan and replaced with the gate CI
actually enforces. Measured evidence in §17.3.

**B4 — open, and correctly scoped.** Open decision 7a — who holds
`ENCRYPTION_KEY_SECRET`, where it is stored, the rotation window — remains a human
decision. It blocks **only** slice 003a. It does not block the TON domain schema.
Section 18 explains why the two must not be coupled, and 003a and 003b have no
schema dependency in either direction, so the chain order can accommodate either
resolving first.

### What READY does and does not authorise

**Authorised now:** create the TON domain schema as 003b, 003c and 003d. Add the
permission tokens and ACL junctions. Add the audit-history tables. Write the tests
in section 20.

**Not authorised:** activating any business rule. Every threshold in §6–§10 of the
Prompt Mestre, all six Vale Norte source-material gates, the travel-settlement
policy, the budget-coverage count and the payroll ratio range remain unapproved.

This separation is what makes READY defensible. Section 3 keeps every threshold,
baseline and policy value as **data** in a `RuleVersion` row, never as a column, a
constraint or a seeded row. A `CHECK` constraint makes `ACTIVE` require a recorded
approval, so an unapproved number cannot reach production even by accident. The
schema can therefore be created before the business values are settled — which is
precisely the controlled rule evolution this gate asked for.

**Nothing is seeded.** No migration inserts a `Rule` or `RuleVersion` row.

---

## 2. Prompt Mestre coverage matrix

Classification legend:

- **DOMAIN CONTRACT NOW** — becomes schema in Plan 003.
- **RULE CANDIDATE** — becomes a `RuleVersion` row, not schema.
- **NEEDS SOURCE VALIDATION** — the source artifact is absent.
- **NEEDS BUSINESS OWNER APPROVAL** — the value or policy needs Vale Norte sign-off.
- **LATER PHASE** — deferred to a named later plan.
- **BLOCKED** — cannot proceed on current evidence.

A concept can carry two classifications. That is the point of the rule-structure
versus rule-parameter split: the structure lands now, the value waits.

### §3 Data contract

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| §3.1 canonical base registry (8 bases) | DOMAIN CONTRACT NOW (structure) + NEEDS SOURCE VALIDATION (fields) | `SourceSnapshot.source_type` enum carries the base identity. No field mapping. |
| §3.1 minimum-schema admission | DOMAIN CONTRACT NOW | `FindingEvidence.is_non_standard_source` renders the `[fonte não padronizada]` label. |
| §3.2 nature groups (23 groups) | RULE CANDIDATE + NEEDS SOURCE VALIDATION | A `RuleVersion.applicability` value. Not an enum in code — the chart of accounts changes. |
| §3.3 unit list (7 operational, 6 implantation, 9 non-operational) | DOMAIN CONTRACT NOW (identity) + NEEDS BUSINESS OWNER APPROVAL (membership) | `BusinessUnit` rows. Not seeded by migration. |
| §3.3 consolidation rule (non-operational excluded from ranking) | DOMAIN CONTRACT NOW | Requires `BusinessUnit.kind`. Without it the rule is inexpressible. |
| §3.4 confidence hierarchy A/B/C/D | **DOMAIN CONTRACT NOW** | `FindingEvidence.confidence_level`, NOT NULL. A published number without its level is a defect. |
| §3.4 "never convert D to A by repetition" | DOMAIN CONTRACT NOW | Confidence is per-evidence and immutable; no aggregate promotes it. |

### §4 Contract master data

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| Contract identification block | DOMAIN CONTRACT NOW (identity subset only) | `Contract`: code, unit, authority, object summary, dates, status. |
| Contract status incl. "under judgement" | **DOMAIN CONTRACT NOW** | Required by S7. This is the Canoas-RS defect. |
| Economic block (global value, monthly value, readjustment, amendments, balance) | LATER PHASE | Plan 004/006. |
| Operational block (services, crews, fleet sizing, headcount sizing) | LATER PHASE | Plan 004/006. |
| Dotação block (unit cost, BDI, ABC curve, charges, reserve, floor, CCT) | LATER PHASE + NEEDS SOURCE VALIDATION | The dotação workbook is absent. |
| Governance block (measurement, glosa, penalties, SLAs, guarantees, fiscal) | LATER PHASE | Plan 006. |
| §4.1 Mossoró calibration figures | RULE CANDIDATE + NEEDS BUSINESS OWNER APPROVAL | Reference values only. Never constants. |
| "Analysis blocked until the master record exists" | DOMAIN CONTRACT NOW | `AnalysisStep` BLOCKED with a named cause. |

### §5 Seven-step execution protocol

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| Fixed 7-step order | **DOMAIN CONTRACT NOW** | `AnalysisStep.step_code` closed enum. Seven members, not a workflow engine. |
| Passo 1 — record what did not arrive | DOMAIN CONTRACT NOW | `SourceSnapshot.missing_inputs`, `is_complete`. |
| Passo 2 — failed base interrupts result analysis | **DOMAIN CONTRACT NOW** | Domain-scoped blocking. Section 5. |
| Passo 3 — chain reconciliation with `[lacuna]` marks | DOMAIN CONTRACT NOW | `Finding.finding_kind = BLIND_SPOT`. |
| Passo 4 — detection with test code and NC | DOMAIN CONTRACT NOW | `RuleVersion.nc_code`, `Rule.code`. |
| Passo 5 — quantification | DOMAIN CONTRACT NOW | `OccurrenceImpact`. |
| Passo 6 — criticality ordering | DOMAIN CONTRACT NOW (field) + RULE CANDIDATE (bands) | `Occurrence.criticality`. |
| Passo 6 — publication ceiling 7/day, 12/month | LATER PHASE | A **publication** limit, not a detection limit. Plan 006. Do not add a cap column to `Finding`. |
| Passo 7 — publish, record, define verification | DOMAIN CONTRACT NOW | `Occurrence.verification_criterion` and `verification_result`. |

### §6 S1–S10 sanity arithmetic

Every S-rule is structurally identical to a T-rule. All ten are RULE CANDIDATE.
The numeric bounds are separable parameters.

| Rule | Structure | Parameter | Classification |
|---|---|---|---|
| S1 margin range | range check | `[-100%, +60%]` | RULE CANDIDATE + NEEDS BUSINESS OWNER APPROVAL |
| S2 balance = monthly × remaining term | identity check with tolerance | `±2%` | RULE CANDIDATE + NEEDS BUSINESS OWNER APPROVAL |
| S3 projected result = monthly margin × term | identity check | exact | RULE CANDIDATE |
| S4 line sum = declared subtotal | identity check with tolerance | `±0.5%` | RULE CANDIDATE + NEEDS BUSINESS OWNER APPROVAL |
| S5 Σ units = consolidated | identity check | to the cent | RULE CANDIDATE |
| S6 sign by nature | sign check | per nature group | RULE CANDIDATE + NEEDS SOURCE VALIDATION |
| S7 unsigned contract excluded | precondition check | `Contract.status` | **DOMAIN CONTRACT NOW** (needs the column) + RULE CANDIDATE |
| S8 AV% over own gross revenue | denominator check | — | RULE CANDIDATE |
| S9 unit-cost comparability | comparability guard | same unit of measure | RULE CANDIDATE |
| S10 no margin on a failed base | **publication block** | — | **DOMAIN CONTRACT NOW** — this is domain-scoped blocking, not a threshold |
| §6.2 calibration findings (187%, 153%, 1020%, R$ 9.75MM, R$ 6.84MM, R$ 90.89MM) | — | — | NEEDS SOURCE VALIDATION + NEEDS BUSINESS OWNER APPROVAL. Test fixtures at most. Never constants. |
| §6.2 consequence (consolidated -R$ 94.5MM is not an operating result) | DOMAIN CONTRACT NOW | A caveat must travel with the number. `TonReportRevision.canonical_payload` carries caveats inline. |

### §7 T1–T12 financial and accounting rules

All twelve are RULE CANDIDATE for structure. Every trigger value is a separable
parameter needing approval. The T-code and NC-code vocabularies are
DOMAIN CONTRACT NOW because §7 forbids renaming them.

| Test | Structure (reusable executor) | Parameter | NC |
|---|---|---|---|
| T1 zeroed group | presence check over a group set | which groups are contractual | NC-05 |
| T2 moving-average deviation | deviation versus trailing mean | window `3`, threshold `15%` | NC-07 |
| T3 duplicate | exact-tuple match | match dimensions | NC-01/06 |
| T4 revenue NF versus NG | cross-source reconciliation | `1%` | NC-14 |
| T5 replicated revenue | exact repeat detection | exact | NC-14 |
| T6 inverted sign | sign check | per nature | NC-03 |
| T7 unappropriated posting | required-field completeness | target zero | NC-03/08 |
| T8 supplier versus unit | cross-entity consistency | — | NC-04 |
| T9 retroactive competence | date-lag check | `30 days`, `5%` accumulation | NC-02 |
| T10 non-recurring event | share-of-total threshold | `5%` | NC-03/12 |
| T11 related parties | counterparty-class match | CPC 05 disclosure | NC-09/13 |
| T12 severance without FGTS fine | paired-record check | `40%` | NC-08 |

Six reusable executor shapes cover all twelve: presence, deviation-versus-baseline,
exact-match duplicate, cross-source reconciliation, sign/domain check, and
share-of-total. This is why `RuleVersion.executor_key` plus `parameters` is
sufficient and why no rule needs bespoke anonymous code.

### §8 T13–T30 operational and contractual rules

All eighteen are RULE CANDIDATE. The same six executor shapes cover them, plus
two more: threshold-versus-replacement-value ratio (T23) and escalating-milestone
alert (T19).

| Group | Tests | Parameter examples | Extra classification |
|---|---|---|---|
| Contract × execution × billing | T13–T20 | `3%`, glosa formalised, `4 months`, `180/120/90/60 days`, `45 days` | NEEDS SOURCE VALIDATION (measurement and billing records absent) |
| Fleet, fuel, productivity | T21–T26 | `15%`/2 weeks, `<4h`, tank capacity, `60%`/`80%`, `12%`, `15%` | NEEDS SOURCE VALIDATION (fleet, fuelling, production data absent) |
| People and procurement | T27–T30 | `5%`, `10.04%`, `8%`/2 months, `15%` | NEEDS SOURCE VALIDATION + NEEDS BUSINESS OWNER APPROVAL (payroll and purchasing data absent) |

**New conflict found.** The §8 heading says "T13–T26". The body defines T13
through T30. The T-code vocabulary is therefore ambiguous. Because §7 forbids
renaming codes, an owner must reconcile the range before any T-code becomes a
`Rule.code`. Recorded in section 13.

### §9 Impact quantification

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| `Impact = operational difference × reference unit cost` | DOMAIN CONTRACT NOW | `OccurrenceImpact.method`. |
| Reference-cost preference order (dotação → own 3-month actual → comparable median) | **DOMAIN CONTRACT NOW** | `OccurrenceImpact.unit_cost_source` enum. "Diga sempre qual usou" is a NOT NULL column. |
| Seven impact categories | **DOMAIN CONTRACT NOW** | `OccurrenceImpact.category` enum. Also carries the Opportunity distinction — section 10. |
| Confidence Alta/Média/Baixa | DOMAIN CONTRACT NOW | `OccurrenceImpact.confidence`. |
| "Low confidence never enters a target or realised ROI" | DOMAIN CONTRACT NOW | Enforced when computing realised ROI. Section 10. |
| Estimate labelling with premise and sensitivity | DOMAIN CONTRACT NOW | `premise`, `sensitivity_pct`. |

### §10 Criticality

| Concept | Classification | Notes |
|---|---|---|
| Four levels 🔴🟠🟡🟢 | DOMAIN CONTRACT NOW | Closed enum. §10 forbids a parallel scale. |
| Bands ≥1%, 0.3–1%, 0.1–0.3% | RULE CANDIDATE + NEEDS BUSINESS OWNER APPROVAL | `RuleVersion.severity_mapping`. **Verified contiguous, no gap.** |
| Base of calculation (unit gross revenue, or consolidated) | RULE CANDIDATE | A parameter, because the base differs by finding scope. |
| Deadlines (immediate–5 business days, 15, 30, next cycle) | RULE CANDIDATE + NEEDS BUSINESS OWNER APPROVAL | `OccurrenceAssignment.deadline`. |
| Automatic escalation (🟠 open two cycles → 🔴 on the third) | DOMAIN CONTRACT NOW | Needs `Occurrence.open_cycle_count`. |
| "Applies the scale without consulting anyone" | DOMAIN CONTRACT NOW | A system transition, `actor_kind = SYSTEM`. |

### §11 Blind spots

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| Twelve active blind-spot questions | RULE CANDIDATE | Each is a rule with `finding_kind = BLIND_SPOT`. |
| "Data gap is a first-class finding" | **DOMAIN CONTRACT NOW** | `Finding.finding_kind` enum member. A finding with no numeric impact must be valid. |
| Published as "indisponível — pendente de informação de campo" with a named owner | DOMAIN CONTRACT NOW | `OccurrenceAssignment` on a blind-spot occurrence. |

### §12 R1–R9 autonomy routines and hard limits

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| R1–R9 triggers, cadence, scope, recipients | LATER PHASE (Plan 006) | `AnalysisRun.routine_code` is the only hook Plan 003 adds. |
| Publication thresholds ("fora do limiar, você não fala") | LATER PHASE (Plan 006) | Publication policy, not detection. |
| §12.1 what runs alone | DOMAIN CONTRACT NOW | System transitions are permitted for read, test, calculate, classify, draft, alert, ledger write. |
| §12.1 eight actions requiring human decision | **DOMAIN CONTRACT NOW** | Section 6. Enforced by CHECK constraints, not convention. |
| "Delivers everything preparable and names the missing decision" | DOMAIN CONTRACT NOW | Partial results survive; `AnalysisStep` names the blocker. |

### §13 Persistent ledgers

| Ledger | Classification | Decision |
|---|---|---|
| §13.1 occurrence ledger (19 fields) | **DOMAIN CONTRACT NOW** | Normalised across six tables. Section 4. |
| §13.2 opportunity ledger | DOMAIN CONTRACT NOW as a discriminator, not a table | `Occurrence.ledger_kind`. Section 10. |
| §13.3 ROI registry | LATER PHASE | Derived, not stored. Section 10. |
| ROI rule (only verified savings count as realised) | DOMAIN CONTRACT NOW | `OccurrenceImpact.realized_amount` plus `verified_at`. |

### §14 Output formats

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| §14.1 exception card (10 fields) | DOMAIN CONTRACT NOW | A projection over Occurrence + Impact + Evidence + Interpretation. Not a table. |
| §14.2 executive mode ordering | LATER PHASE (Plan 006) | Presentation. |
| §14.3 ISC score, 8 dimensions with fixed weights | RULE CANDIDATE + LATER PHASE | Weights **verified to sum to 100**. A report type, computed in Plan 006. |
| §14.3 "only publish a dimension whose data exists; redistribute weight; state the caveat" | DOMAIN CONTRACT NOW | The report snapshot must be able to record a not-assessed dimension and the redistribution. |
| §14.4 Dinheiro Escondido panel | LATER PHASE (Plan 006) | A report type over `ledger_kind = OPPORTUNITY`. |
| Report immutability of any published output | **DOMAIN CONTRACT NOW** | Section 9. |

### §15 Specialist agents

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| Nine specialists | DOMAIN CONTRACT NOW (identity only) | `AnalysisRun.specialist` closed enum. Agent implementation is Plan 005. |
| "All write to the same ledger and use the same scale" | DOMAIN CONTRACT NOW | One `Occurrence` table, one criticality enum. |
| Handoff rule — recorded once, by the link where the quantity changed | **DOMAIN CONTRACT NOW** | `UNIQUE(identity_key)` on Occurrence makes double-recording impossible. `OccurrenceImpactedDomain` lists the others. |
| §2 elo rule (deviation belongs to the link where quantity changed) | DOMAIN CONTRACT NOW | `Occurrence.owning_domain` plus impacted-domain rows. |

### §16 Regulatory handling

| Concept | Classification | Plan 003 treatment |
|---|---|---|
| Lei 14.133/2021, TCU guidance, ANA NR 7/2024 and NR 14/2025, CCT, municipal law | RULE CANDIDATE + LATER PHASE | `RuleVersion.source_reference`. Compliance rules are Plan 005/006. |
| NR 14/2025 segregation by municipality and activity | DOMAIN CONTRACT NOW | Already satisfied by `BusinessUnit` plus domain scoping. |
| Separate documented fact from interpretation from hypothesis | **DOMAIN CONTRACT NOW** | Deterministic values live on `Finding`; narrative lives on `FindingInterpretation`. Distinct tables, no overlap. |
| "Ponto para validação jurídica" and stop | **DOMAIN CONTRACT NOW** | `Occurrence.legal_review_required`. TON records the flag, never the conclusion. |

### §17 Forecast mode

| Concept | Classification |
|---|---|
| Three-scenario forecast, minimum 6 closed periods | LATER PHASE (Plan 006) |
| Re-presenting prior forecast error against actuals | LATER PHASE — needs the immutable report snapshot from Plan 003 |
| Named seasonality premises | LATER PHASE + NEEDS SOURCE VALIDATION |
| §17.1 bid simulation | LATER PHASE + NEEDS SOURCE VALIDATION |

### §18–§19 (present in the source, outside the requested range)

| Concept | Classification |
|---|---|
| §18 golden rule — never a problem without impact, cause, evidence and action | DOMAIN CONTRACT NOW. Four NOT NULL-equivalent requirements before an Occurrence may be published. |
| §19 seven board questions | LATER PHASE (Plan 006 report acceptance criteria). |

### Coverage result

- Concepts classified: 78.
- DOMAIN CONTRACT NOW: 34.
- RULE CANDIDATE: 46 rule shapes (S1–S10, T1–T30, plus blind spots and regulatory).
- Distinct deterministic executor shapes needed to cover all 40 numbered tests: **8**.
- NEEDS BUSINESS OWNER APPROVAL: 24 parameter sets.
- NEEDS SOURCE VALIDATION: 21 concepts, all traceable to a base absent from this checkout.
- LATER PHASE: 19.
- BLOCKED: 1 (NG/Keevo field mapping, per D-009).

**No Prompt Mestre number becomes a production constant.** Every threshold in
§6–§10 lands in `RuleVersion.parameters` with provenance, approval and effective
dates. This is the core reason the schema can be created before the business
values are approved.

---

## 3. Rule and RuleVersion decision

**Decision: split on mutability. `Rule` holds only what must never change.
`RuleVersion` holds everything that can.**

### Rule — the stable spine

| Field | Reason |
|---|---|
| `id` | surrogate key |
| `code` UNIQUE | the stable identifier. `T2`, `S1`, `FIN-TAX-01`. §7 forbids renaming. |
| `domain` | FINANCIAL, OPERATIONAL, CONTRACT, FLEET, HR, PROCUREMENT, COMPLIANCE, AUDIT, QUALITY |
| `kind` | SANITY (§6) / DETECTION (§7–§8) / BLIND_SPOT (§11) |
| `created_at`, `created_by` | provenance of the rule itself |

`Rule` carries **no** threshold, no status and no effective date. A rule that is
retired is a rule whose versions are all retired.

### RuleVersion — append-only, one row per approved revision

| Field | Reason |
|---|---|
| `rule_id`, `version` (UNIQUE together) | ordered history |
| `title`, `description` | as worded at this version |
| `executor_key` | names the deterministic implementation, for example `deviation_vs_trailing_mean.v1`. A stable string, never a Python import path. |
| `parameters` JSONB | thresholds, windows, tolerances |
| `unit`, `currency`, `scale`, `rounding_mode` | §9 and canonicalisation need these explicit |
| `applicability` JSONB | units, nature groups, contract classes |
| `effective_from`, `effective_to` | controlled evolution |
| `status` | DRAFT, PENDING_APPROVAL, ACTIVE, SUSPENDED, RETIRED, TEST_ONLY |
| `source_reference` | `PAD-CTRL-001 T2`, `Prompt Mestre §7`, `Relatorio 1.6` |
| `provenance` | PAD_CTRL_001, PROMPT_MESTRE_V2, VALE_NORTE_REPORT_2026, OWNER_APPROVED, DERIVED |
| `approved_by`, `approved_at`, `approval_reference` | the approval record |
| `missing_data_behavior` | BLOCK, FINDING_BLIND_SPOT, SKIP_WITH_NOTE |
| `evidence_requirements` JSONB, `min_confidence_level` | §3.4 A/B/C/D gate |
| `severity_mapping` JSONB, `nc_code` | §10 bands and NC-01…NC-14 |
| `identity_components` JSONB | the dedup dimensions. Section 7 of this document. |
| `post_resolution_policy` | REOPEN_SAME_OCCURRENCE, SUPERSEDE_WITH_NEW_OCCURRENCE |
| `definition_hash` | tamper evidence over the canonical version definition |

### Placement rules

- **`status` belongs to RuleVersion, never Rule.** Otherwise activating a new
  threshold silently reinterprets old findings.
- **`ACTIVE` requires approval.** Enforceable:
  `CHECK (status <> 'ACTIVE' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))`.
  This makes "no disputed number reaches production" a database property, not a
  review habit.
- **A `TEST_ONLY` version may never produce a publishable Occurrence.**
- **Historical reference is by `rule_version_id`, never `rule_id`.** Every
  `Finding` pins the version that produced it. Changing a threshold cannot rewrite
  history. This is the requirement the gate asked for.

### Why no anonymous hardcoded logic

`executor_key` + `parameters` separates the two things cleanly. The code contains
eight parameterised executor shapes (section 2). The database contains the values.
A reviewer can answer "which rule fired, at which threshold, approved by whom, in
force when" from rows alone. A rule cannot exist without a named, versioned,
provenance-carrying row.

### Rule structure versus rule parameter value, worked

T2 moving-average deviation:

- `Rule.code = 'T2'`, `kind = DETECTION`, `domain = FINANCIAL` — **valid now**.
- `executor_key = 'deviation_vs_trailing_mean.v1'` — **valid now**.
- `parameters = {"window_months": 3, "threshold_pct": "15"}` — **needs approval**,
  and is a row, not code.

The rule definition is READY. The threshold is not. Both statements are true at
once, and the schema expresses that.

---

## 4. AnalysisRun decision

**Decision: `AnalysisRun` is the audit envelope. `AnalysisStep` is the unit of
execution and of blocking. `AnalysisRunRuleVersion` pins what actually ran.**

### AnalysisRun — minimum contract for auditability

| Field | Required? | Reason |
|---|---|---|
| `id` | yes | |
| `trigger` | yes | INTERACTIVE, SCHEDULED, BACKFILL, MANUAL_REPLAY. Supports both modes the gate asked for. |
| `triggered_by_user_id` | nullable | NULL for scheduled. Actor attribution. |
| `routine_code` | nullable | R1–R9 (§12). The only §12 hook Plan 003 adds. |
| `specialist` | yes | §15 nine specialists |
| `domain` | yes | scoping for blocking |
| `business_unit_id` | nullable | NULL for corporate scope |
| `period_start`, `period_end` | yes | competência |
| `status` | yes | QUEUED, RUNNING, COMPLETED, COMPLETED_WITH_BLOCKED_DOMAINS, FAILED, TIMED_OUT, CANCELLED |
| `started_at`, `finished_at` | yes | |
| `idempotency_key` UNIQUE | **yes** | retry convergence. Without it a Celery retry duplicates a run. |
| `attempt_no` | yes | retry visibility |
| `error_class` | nullable | safe enum. **No stack trace** — SECURITY-01/02 already closed that. |
| `executor_version` | yes | reproducibility |
| `interpretation_status` | yes | roll-up over child findings |

**Deliberately excluded:**

- **A resulting-Finding-ID array.** Findings point at the run. A denormalised
  array is a mutable duplicate of an immutable relation.
- **A report FK.** A report references runs, not the reverse. One run can feed
  several report revisions.
- **`schedule_id`.** Plan 006 owns `AnalysisSchedule`. Plan 003 must not create a
  nullable FK to a table that does not exist. `routine_code` is enough for now.

`input_provenance` is not a JSONB blob on the run. It is
`AnalysisRun__SourceSnapshot` rows. This keeps §5 Passo 1 queryable: "which runs
used the April extract" must be answerable in SQL.

### AnalysisRunRuleVersion

`(analysis_run_id, rule_version_id)` plus per-rule `outcome`
(EXECUTED, SKIPPED_NOT_APPLICABLE, SKIPPED_MISSING_DATA, ERRORED) and
`finding_count`. This is what makes a report reproducible: it records the rules
that ran **and the ones that did not, with the reason**.

---

## 5. Domain-scoped blocking decision

This is the section that prevents Plan 003 from reproducing the original TON
defect.

### The defect and the correct reading

§5 says "se um passo falha, os seguintes ficam bloqueados". Read literally in
software, one failed base validation would silence Frota, Contratos and RH. That
is the defect.

**The software interpretation: failure blocks only the affected
(step, domain, business unit) and its declared dependents. It never blocks an
unrelated specialist.**

### Where blocking lives

**Decision: on `AnalysisStep`, with a self-referencing cause. Not on
`AnalysisRun`. Not a generic workflow engine.**

| Field | Reason |
|---|---|
| `analysis_run_id` | owner |
| `step_code` | closed enum, seven members: INGESTION, BASE_VALIDATION, CHAIN_RECONCILIATION, DETECTION, QUANTIFICATION, PRIORITIZATION, PUBLICATION |
| `domain` | nullable. NULL means run-wide. |
| `business_unit_id` | nullable |
| `status` | PENDING, RUNNING, PASSED, FAILED, BLOCKED, SKIPPED |
| `blocked_by_step_id` | self-FK, nullable |
| `blocked_reason` | closed enum: PREREQUISITE_FAILED, MISSING_SOURCE, MISSING_CONTRACT_MASTER, BASE_REPROVED, AWAITING_HUMAN_DECISION |
| `started_at`, `finished_at` | |

### Invariants

1. **The blocking unit is the triple `(step_code, domain, business_unit_id)`.** Not
   the run.
2. **A step becomes BLOCKED only when a declared prerequisite in the same
   `(domain, business_unit_id)` scope reached FAILED.** Prerequisites are the fixed
   §5 order plus per-rule declarations in `RuleVersion.applicability`. They are
   data, not a graph engine.
3. `CHECK (status <> 'BLOCKED' OR (blocked_by_step_id IS NOT NULL AND blocked_reason IS NOT NULL))`
   — a BLOCKED step always names its cause. No silent blocking.
4. **A run with both FAILED and PASSED steps lands in
   `COMPLETED_WITH_BLOCKED_DOMAINS`, never `FAILED`.** This is the whole point.
   Successful specialist results survive.
5. **S10 is expressed as a blocked PUBLICATION step**, scoped to the domain and
   unit whose base was reproved. Not as a global flag.

### Worked example, matching the gate's requirement

Mossoró financial base validation fails.

| Step scope | Status |
|---|---|
| `BASE_VALIDATION` / FINANCIAL / Mossoró | FAILED |
| `DETECTION` / FINANCIAL / Mossoró | BLOCKED, `blocked_reason = BASE_REPROVED` |
| `PUBLICATION` / FINANCIAL / Mossoró | BLOCKED |
| `DETECTION` / FLEET / Mossoró | **PASSED** |
| `DETECTION` / CONTRACT / Mossoró | **PASSED** |
| `DETECTION` / HR / Mossoró | **PASSED** |
| `DETECTION` / FINANCIAL / Itabirito | **PASSED** |
| Run status | `COMPLETED_WITH_BLOCKED_DOMAINS` |

Note the last row: blocking is scoped by unit as well as domain. A Mossoró base
failure does not block Itabirito financial analysis.

### Why not a workflow engine

The Prompt Mestre fixes seven steps (§5) and nine specialists (§15). Both are
closed vocabularies. A seven-member enum with one self-FK and one CHECK constraint
covers every case and is directly testable. A generic engine would add scheduling,
retry and dependency-resolution semantics that Plan 006 already owns for Celery.
**Explicitly rejected.**

### Required anti-defect test

A named test must assert that a FAILED step in `(domain=X, unit=U)` produces
BLOCKED **only** on steps whose scope is `(X, U)` and which declare X as a
prerequisite. Every other step in the run must remain PASSED. This test is the
regression guard for the original defect and is listed in section 20.

---

## 6. Finding versus Occurrence decision

**Decision: keep both. The split the gate proposed is correct, with one
correction.**

| Entity | Meaning | Mutability | Cardinality |
|---|---|---|---|
| `Finding` | one deterministic detection event, with its evidence | **immutable, append-only** | one per `(analysis_run, rule_version, identity_key)` |
| `Occurrence` | the persistent business case with a lifecycle — the §13.1 ledger row | lifecycle by appended events; status is a projection | one per `identity_key` |

### Evaluation against the required criteria

| Criterion | Why the split holds |
|---|---|
| repeated detection | new `Finding`, same `Occurrence`. If `Finding` carried the lifecycle, a rerun would either mutate history or duplicate the case. |
| deduplication | `UNIQUE(identity_key)` on Occurrence; `UNIQUE(analysis_run_id, rule_version_id, identity_key)` on Finding |
| recurrence | `OccurrenceEvent` rows; `open_cycle_count` drives §10 escalation |
| open unresolved issue | `Occurrence.status` |
| resolution | `OccurrenceEvent(RESOLVED)` plus actor, time, reason, evidence |
| reopening | `OccurrenceEvent(REOPENED)`. Never an UPDATE that loses the prior state. |
| many findings, one occurrence | `Finding.occurrence_id` FK. Directly supported. |
| scheduled reruns | the Finding unique constraint makes a rerun idempotent |
| audit history | `OccurrenceEvent` is the immutable domain history (section 8) |

### The correction

Plan 003 and the frontend documents use both words for the same thing.
`findings-ux-plan.md` names the route `/app/occurrences` and its field list is the
§13.1 occurrence field list.

**Resolution: `Occurrence` is the user-facing entity. `Finding` is internal
detection evidence.** The UI, the API and the report vocabulary say Occurrence.
This matches the frontend plan and §13.1, and removes the ambiguity.

### Rejected alternatives

- **Finding only, with mutable status.** Fails audit history and fails the
  many-findings-one-case requirement.
- **Occurrence only, recomputed each run.** Loses which run and which rule version
  detected what. Makes reports irreproducible.
- **One table with a discriminator.** The two have different mutability rules.
  Immutable and lifecycle rows must not share a table.

### §13.1 ledger field placement

The nineteen ledger fields are not nineteen columns.

**On `Occurrence`:** `id`, `short_code`, `identity_key`, `rule_id`,
`current_rule_version_id`, `owning_domain`, `ledger_kind`, `criticality`,
`nc_code`, `business_unit_id`, `contract_id`, `title`, `status`,
`first_detected_at`, `last_detected_at`, `detection_count`, `open_cycle_count`,
`resolved_at`, `verification_criterion`, `verification_result`,
`verification_checked_at`, `legal_review_required`, `requires_human_closure`,
`superseded_by_occurrence_id`.

**Normalised out, with the reason:**

| Ledger concept | Table | Reason |
|---|---|---|
| description, probable cause, recommended action, TON interpretation | `FindingInterpretation` | AI-produced, versioned, needs model provenance |
| evidence + confidence | `FindingEvidence` | many per finding; confidence is per source, not per case |
| financial impact | `OccurrenceImpact` | §9 requires category, confidence, method, unit-cost source, sensitivity, and it is re-estimated |
| responsible party, deadline | `OccurrenceAssignment` | §10 escalation and §12 R9 need deadline history, not the latest value |
| status, cycles open, resolution | `OccurrenceEvent` | append-only history is the requirement |
| impacted other domains | `OccurrenceImpactedDomain` | §15 handoff rule: recorded once, others listed as impacted |

`Occurrence.status` and `open_cycle_count` are maintained projections. A named test
must assert each equals the value derived from `OccurrenceEvent`. That keeps the
convenience columns honest.

---

## 7. Deduplication and recurrence contract

### The four outcomes

| Outcome | Precondition | Effect |
|---|---|---|
| **NEW** | no Occurrence with this `identity_key` | create Occurrence (`status = NEW`) + Finding |
| **REPEATED, SAME OPEN ISSUE** | Occurrence exists, status is open | new Finding; bump `last_detected_at`, `detection_count`; append `OccurrenceEvent(REPEAT_DETECTED)`. **Never a second Occurrence.** |
| **RESOLVED** | Occurrence resolved, no detection this cycle | no Finding. Optionally an `OccurrenceEvent(VERIFICATION_PASSED)` when the rule declares a verification criterion. |
| **RECURRED AFTER RESOLUTION** | Occurrence resolved, new detection arrives | apply `RuleVersion.post_resolution_policy` |

### Recurrence policy

`post_resolution_policy` is **per RuleVersion and mandatory**. There is no global
default, because "the executor must not choose silently" (`domain-rules.md`).

- `REOPEN_SAME_OCCURRENCE` — append `OccurrenceEvent(REOPENED)`, increment
  `open_cycle_count`. Same case, same history.
- `SUPERSEDE_WITH_NEW_OCCURRENCE` — create a new Occurrence, set
  `superseded_by_occurrence_id` on the old one. Used when the case is genuinely
  new.

**Forced supersede.** If the `rule_version` that detects the recurrence differs
from the one that produced the resolution, the outcome is always
`SUPERSEDE_WITH_NEW_OCCURRENCE`, whatever the policy says. Two detections under
different thresholds are not the same measurement. This mirrors the S9
comparability principle.

### Identity strategy

`identity_key` is an opaque, deterministic digest of a canonical tuple. Its
components are declared in `RuleVersion.identity_components`, drawn from a
**closed vocabulary**:

`rule_code`, `business_unit_id`, `contract_id`, `period` (AAAA-MM),
`source_system`, `source_record_key`, `nature_group`, `vehicle_key`,
`supplier_key`, `employee_key_masked`.

Canonicalisation before hashing: Unicode NFC, trimmed, case-folded for
case-insensitive components, components emitted in the declared order with an
unambiguous separator, absent components omitted rather than emitted empty.

### Two decisions worth stating

**1. `identity_key` includes `rule_code`, never `rule_version`.** If the version
were part of identity, every threshold change would break recurrence tracking and
reset every open case. Version comparability is handled by the forced-supersede
rule above instead.

**2. LLM text is never an identity input.** The identity function lives in the
deterministic module, takes no interpreter output, and receives no title or
description. A named test must assert `identity_key` is unchanged when title,
description and interpretation all change. Text similarity is not a dedup
mechanism here, as the gate required.

### Concurrency

Database-level, because application-level dedup is insufficient
(`domain-rules.md`):

- `UNIQUE(identity_key)` on Occurrence.
- `UNIQUE(analysis_run_id, rule_version_id, identity_key)` on Finding.
- Writes use `INSERT … ON CONFLICT DO NOTHING` then re-read, so concurrent
  detector workers and Celery retries converge on one logical result.
- `AnalysisRun.idempotency_key` UNIQUE stops a duplicate run at the envelope.

---

## 8. AI interpretation lifecycle

Flow, unchanged from `domain-rules.md` and D-003/D-004:

```text
deterministic rule -> Finding + evidence -> AI interpretation
  -> impact/context -> recommended action -> Occurrence/report
```

### State

`Finding.interpretation_status`: `NOT_REQUIRED`, `PENDING`, `RUNNING`,
`COMPLETED`, `FAILED`.

`PENDING` is persisted and committed **before** any provider request starts. This
is the durability requirement: a crash between request and response must leave a
visible non-final record, never a silent gap.

### FindingInterpretation — append-only, one row per attempt

| Field | Reason |
|---|---|
| `finding_id`, `attempt_no` | ordered attempts |
| `status` | per-attempt outcome |
| `llm_provider`, `model_name` | provenance |
| `prompt_key`, `prompt_version` | reproducibility without storing the prompt body |
| `summary`, `probable_cause`, `recommended_action`, `impact_narrative` | the business-facing output |
| `proposed_criticality`, `proposed_nc_code` | **proposals only** |
| `evidence_reference_ids` | which evidence rows were shown |
| `input_scope` | STRUCTURED_ONLY, MASKED_EXCERPT, FULL_EVIDENCE |
| `started_at`, `finished_at` | |
| `failure_class` | PROVIDER_UNAVAILABLE, TIMEOUT, MALFORMED_OUTPUT, POLICY_REFUSAL, INSUFFICIENT_EVIDENCE |
| `retry_eligible` | explicit, not inferred |

### What is not stored

**No chain-of-thought. No raw prompt body. No raw response transcript.** Only the
business-facing interpretation and the provenance needed to reproduce the call
shape. `input_scope` is the privacy control and it composes with
`TON_TRACE_CONTENT_MODE` from Plan 002 (D-015): a metadata-only deployment must
not be able to persist `FULL_EVIDENCE`.

### Invariants

1. A `Finding` may not reach a final state unless `interpretation_status IN
   ('COMPLETED', 'NOT_REQUIRED')`. Expressible as a CHECK constraint.
2. A report revision may not include a Finding whose interpretation is `PENDING`,
   `RUNNING` or `FAILED`. Enforced when the snapshot is built, and tested.
3. `FAILED` is durable and operator-visible. It is never treated as an empty
   success — a rejected approach in the decision log.
4. The interpreter **cannot** change: deterministic expected and actual values,
   source identifiers, `rule_version_id`, `identity_key`, or the computed impact
   amount. It writes to its own table only; it holds no write path to `Finding`
   or `Occurrence` numeric columns.
5. Promotion of `proposed_criticality` to `Occurrence.criticality` is a separate,
   audited action. The proposal alone changes nothing.

---

## 9. Human decision boundaries

TON V1 is advisory. §12.1 lists eight actions that require a human. The schema
must make the boundary structural, not conventional.

### Actions TON must never be able to take

| §12.1 action | Schema treatment |
|---|---|
| contest a glosa | **no such transition exists**, and no glosa write path |
| modify ERP data | **no column, no write path** |
| alter billing | **no column, no write path** |
| alter measurement | **no column, no write path** |
| communicate with the contracting authority | out of scope; Plan 009 owns channels and TON core stays channel-neutral |
| reach a legal conclusion | only `Occurrence.legal_review_required`. TON records the flag; §16 stops there. |
| impute conduct to a named person | evidence stores role or cargo by default; person identity only behind ACL and `redaction_level` |
| close a 🔴 critical occurrence | `requires_human_closure`, enforced below |

**Recorded invariant: Plan 003 adds no column and no function that writes to any
source system.** The advisory boundary is enforced by absence, which cannot be
bypassed by a future caller.

### Transitions requiring human authorisation

`OccurrenceEvent` carries `actor_kind` (USER or SYSTEM), `actor_user_id` and
`authorization_reference`.

`CHECK (transition NOT IN ('RESOLVE_CRITICAL','ACCEPT_RISK','DISMISS','ASSERT_NONCOMPLIANCE','PROMOTE_INTERPRETATION','OVERRIDE_DETERMINISTIC_VALUE')
        OR (actor_kind = 'USER' AND actor_user_id IS NOT NULL AND authorization_reference IS NOT NULL))`

`Occurrence.requires_human_closure` is TRUE whenever `criticality = 'CRITICAL'`.

### Transitions TON may perform alone

Per §12.1: read, test, calculate, classify, draft, alert, and write to the ledger.
So `DETECT`, `REPEAT_DETECTED`, `ESCALATE_BY_CYCLE_RULE` (§10 escalation, which
§10 says applies "sem consultar ninguém"), `VERIFICATION_PASSED`,
`VERIFICATION_FAILED` and `SUPERSEDE` may carry `actor_kind = SYSTEM`.

Workflow is not implemented in Plan 003. The **boundary** is, because retrofitting
it after rows exist is a one-way door.

---

## 10. Resource ACL model

**Decision: reuse the Plan 008a primitives without change. Add tokens and
junctions only. Invert one default.**

Plan 008a did not create the authorization framework — it removed a commercial
gate in front of one that already existed. Everything needed is in the Community
Edition tree.

### What exists and is reused verbatim

| Primitive | Location |
|---|---|
| `Permission` enum, `Enum(native_enum=False)` | `backend/onyx/db/enums.py:640-716` |
| `PermissionAuthority` GLOBAL / SCOPED / NONE | `enums.py:717-729` |
| `PermissionGrant` (group-only) | `backend/onyx/db/models.py:5027-5071` |
| GATE 1 `require_permission(...)` | `backend/onyx/auth/permissions.py:320-378` |
| GATE 2 write `assert_within_scope` | `backend/onyx/auth/scoped_permissions.py:98` |
| GATE 2 read `within_managed_scope_clause` | `backend/onyx/db/scoped_permissions.py:43-84` |
| Admin bypass `has_global_permission` | `permissions.py:313` |
| Delete gate `assert_global` | `scoped_permissions.py:181` |
| Junction shape with a share level | `Persona__UserGroup`, `models.py:5099-5113` |

Because `Permission` is `native_enum=False`, **adding TON tokens needs no
migration**. It is a pure code change.

### Tokens to add

`READ_TON_OCCURRENCES`, `MANAGE_TON_OCCURRENCES`, `READ_TON_REPORTS`,
`MANAGE_TON_REPORTS`, `READ_TON_ANALYSIS`, `MANAGE_TON_RULES`,
`MANAGE_TON_BUSINESS_UNITS`.

Each needs a `PERMISSION_REGISTRY` entry (`permissions.py:158`) to be grantable in
the admin UI.

**`MANAGE_TON_RULES` must not be added to `SCOPED_MANAGER_PERMISSIONS`.**
Approving a rule version is a global act with company-wide effect. A business-unit
manager must not activate a threshold.

### Junctions to add

Shaped on `Persona__UserGroup`: composite primary key plus a share-level enum.

| Junction | Share level |
|---|---|
| `BusinessUnit__UserGroup` | VIEWER / EDITOR |
| `Contract__UserGroup` | VIEWER / EDITOR |
| `Occurrence__UserGroup` | VIEWER / EDITOR |
| `TonReport__UserGroup` | VIEWER / EDITOR |

**`Finding` and `FindingEvidence` get no junction.** Their ACL derives from the
owning `Occurrence` and its `business_unit_id`. Two independent ACLs over one case
is a divergence bug waiting to happen — one would eventually grant what the other
denies.

### Ownership

`Occurrence` and `TonReport` are system-generated. They have no `user_id` owner.
Ownership is expressed by `business_unit_id` plus junction rows, which matches
`Persona.owner_group_id` semantics already in the tree.

### Fail-closed — the required correction

The existing pattern is fail-closed on the scoped-manager path but **fail-open at
the resource default**. `Persona.is_public` defaults to `True`
(`models.py:4284`), and `is_public == True` short-circuits the entire group ACL.
`LLMProvider__Persona` states the convention in its own docstring: with no
junction rows, the resource is accessible to all.

Copying that would leak Vale Norte financial data.

**Corrections, all mandatory:**

1. **No TON entity gets an `is_public` column.** Not defaulted false — **absent**.
   A column that does not exist cannot be short-circuited by future code.
2. `within_managed_scope_clause` needs a `non_public_clause`. TON passes
   `sa.true()`: a TON resource is always non-public.
3. **Visibility requires at least one junction row.** Zero rows means DENIED. The
   junction is restrictive for TON, not additive-grant as elsewhere.
4. Admin bypass uses `has_global_permission`, never `has_permission`. A scoped
   manager must not bypass.
5. Delete uses `assert_global`. **Never `allow_scope=True` on a delete route.**
6. Writes call `assert_within_scope` with current groups re-read in-transaction
   under `with_for_update()`, never taken from the request.
7. Every `allow_scope=True` read route applies `within_managed_scope_clause`, or a
   manager sees every row.

### Differentiated sensitivity

Financial, payroll and contract data need different scopes. **Do not add a second
mechanism.** Use separate `UserGroup` rows per sensitivity domain and require that
an Occurrence in a given domain carries only groups authorised for it. Enforced in
the write path plus a named cross-domain denial test. Adding a parallel
classification system would create the second authorization framework the gate
forbids.

### A CE/EE trap Plan 003 must avoid

`onyx/db/persona.py:323-374` — the CE `update_persona_access` raises
`NotImplementedError("Onyx MIT does not support group-based sharing")`. Group
sharing is written only by the EE override.

**TON must not copy that split for its own junctions.** TON's ACL is TON's own
capability, and Plan 008a established that capability must not depend on edition
or tier. If TON's group-share write path lived in an EE-only module, a
CE-resolved process would silently write no junction rows — and with correction 3
above, every TON resource would become invisible. TON ACL writes belong in the
Community tree (`backend/onyx/db/ton/`) unconditionally.

Note the current runtime state: `LICENSE_ENFORCEMENT_ENABLED` defaults to `"true"`,
so `global_version.set_ee()` runs and the EE tree loads even with no license
(`variable_functionality.py:47-71`, matching D-022). That makes the trap easy to
miss in testing and severe in a CE-resolved worker.

### Terminology

`UserRole` is an explicit tombstone with zero usages
(`backend/onyx/auth/schemas.py:11-22`). `CURATOR` and `GLOBAL_CURATOR` do nothing.
`User__UserGroup.is_curator` is dead; `is_manager` is live. **Plan 003 must not use
role language.** Classification is `AccountType`; authorization is `Permission`.

---

## 11. Audit and history model

**Decision: both, with a strict division of labour. Not duplication.**

### Verified current state

No persistent queryable audit store exists. `emit_audit_event`
(`backend/onyx/utils/audit.py`) writes one JSON line to a stdout handler on the
`onyx.audit` logger tree. It holds no `db_session`. Its whole body is wrapped in
`try/except: return`, so it never raises and never guarantees delivery. Redis
`SETNX` dedup can suppress events, and degrades to always-emit when Redis is down.
`docs/AUDIT_LOGGING.md` names an in-product `audit_event` table as future work.
There is no `AuditLog` model, no `*audit*` table name, and no SQLAlchemy
versioning. The capability audit records this as TON-CAP-007,
`REIMPLEMENT_MINIMAL_TON_VERSION`, P1.

### The division

| Layer | Content | Guarantee |
|---|---|---|
| **Domain history tables** — authoritative | `OccurrenceEvent`, `OccurrenceAssignment`, `OccurrenceNote`, `RuleVersion`, `FindingInterpretation`, `TonReportRevision` | **transactional**. The write is part of the business transaction and **must raise** on failure. |
| **One `TonAuditEvent` table** | actor-attributed actions that are not already domain state | best-effort, **never raises into the caller** |
| **Existing stdout stream** | unchanged | SIEM export, per `docs/AUDIT_LOGGING.md` |

The distinction matters and is easy to get wrong: a lost domain transition is data
loss, so it must fail loudly. A lost audit line must not break a user's action.
Two different guarantees mean two different mechanisms.

### Anti-duplication rule

If a fact is already an immutable domain row, `TonAuditEvent` stores a
**reference** — `resource_type`, `resource_id`, `domain_event_id` — not a copy of
the payload. This satisfies the gate's requirement to avoid duplicating immutable
domain history.

### Required coverage, mapped

| Required event | Where |
|---|---|
| occurrence status change | `OccurrenceEvent` (domain) |
| assignment | `OccurrenceAssignment` (domain) |
| deadline change | `OccurrenceAssignment` (domain, append-only, so history survives) |
| comment / note | `OccurrenceNote` (domain, ACL-filtered, may contain PII) |
| resolution | `OccurrenceEvent` (domain) |
| reopening | `OccurrenceEvent` (domain) |
| report generation | `TonReportRevision` (domain) + `TonAuditEvent` (actor) |
| rule activation / version change | `RuleVersion` row + `TonAuditEvent` (actor) |
| manual correction / override | `TonAuditEvent` with before/after + `OccurrenceEvent` |
| human approval | `TonAuditEvent` with `authorization_reference` |

### Schema reuse

`TonAuditEvent` reuses the existing shapes so the table and the stdout stream stay
one schema: `AuditAction`, `AuditOutcome`, `AuditActor`, `OCSFEventClass`, plus
`audit_schema_version`, `tenant_id`, `resource_type`, `resource_id`, `endpoint`,
`request_id`, `source_ip`, `extra`.

Adding TON members to `AuditAction` requires a matching `_OCSF_CLASS_BY_ACTION`
entry. An import-time `RuntimeError` guard already enforces this, so an unmapped
action cannot ship.

Audit rows may contain PII, so the read route carries the section 10 resource ACL.

---

## 12. Report snapshot and hash decision

**Decision: append-only revisions, one pinned canonical payload per revision, one
persisted hash, canonicalisation rules fixed and versioned before any hash is
computed.**

This confirms D-011 and D-012 with the missing detail: D-011 was recorded as
"Recommended; approval required before migration" and never specified how the
payload is serialised.

### Structure

`TonReport` is the logical report. `TonReportRevision` is immutable.

| Field | Reason |
|---|---|
| `report_id`, `revision_no` (UNIQUE together) | ordered revisions |
| `report_type` | §14 types: EXCEPTION_CARD, EXECUTIVE, ISC, HIDDEN_MONEY_PANEL, MONTHLY_CLOSE, RECONCILIATION, FORECAST |
| `period_start`, `period_end`, `business_unit_id` | scope |
| `canonical_payload` JSONB | the frozen content |
| `canonicalization_version` NOT NULL | for example `ton-canon-1` |
| `hash_algorithm` NOT NULL | for example `sha256` |
| `content_hash` NOT NULL | over the canonical serialisation |
| `generator_version` NOT NULL | code identity |
| `generated_at`, `generated_by` | provenance |
| `superseded_by_revision_id`, `correction_reason` | a correction is a new revision |
| `file_record_id` | optional FileStore artifact |

The included set is pinned by join tables, not by an array:
`TonReportRevision__AnalysisRun`, `__Occurrence`, `__Finding`, `__RuleVersion`,
`__SourceSnapshot`.

Storing the algorithm and the canonicalisation version as data means a future
change to either cannot invalidate an existing hash.

### Canonicalisation strategy, decided before hashing

The gate required this decision. RFC 8785 JSON Canonicalization Scheme as the
base — UTF-8, no insignificant whitespace, lexicographic key ordering — with four
domain rules layered on top:

1. **Monetary and quantity values serialise as decimal strings, never JSON
   numbers**, at the scale declared by the `RuleVersion`. Percentages likewise.
   This is the most important rule in this domain: §6 exists because arithmetic in
   this data is already wrong by cents, and IEEE-754 float round-tripping would
   make a hash non-reproducible across platforms.
2. **Timestamps as RFC 3339 UTC with an explicit `Z`**, truncated to a declared
   precision.
3. **Absent keys are omitted, never emitted as `null`.** One representation only,
   or two semantically identical payloads hash differently.
4. **Enums serialise as their `.value` string**, matching the repository's
   `native_enum=False` convention.

### Reproducibility

A report generated today stays reproducible after rules change, findings change,
occurrences resolve, source records change and interpretations change, because:

- the revision pins `rule_version_id` values, and `RuleVersion` is append-only;
- it pins `SourceSnapshot` rows, which are receipts of a specific extraction;
- it pins occurrence and finding identifiers, and `Finding` is immutable;
- a later interpretation creates a new `FindingInterpretation` row, never an update;
- a later resolution appends an `OccurrenceEvent`, never a rewrite;
- `canonical_payload` holds the values as published, so a later source correction
  cannot alter what was published.

§14.3 needs one extra capability: the payload must be able to record a
not-assessed ISC dimension and the redistributed weights, because §14.3 requires
publishing the caveat alongside the score.

### Immutability enforcement

Three layers, in order of strength:

1. No UPDATE path exists in `backend/onyx/db/ton/reports.py`. A correction calls
   the revision creator.
2. A named test asserts an attempted mutation raises.
3. A `content_hash` recomputation check on read detects tampering that bypassed
   the application.

A `BEFORE UPDATE` trigger that raises is available as defence in depth. It is
recommended but flagged as optional, since it is closer to a one-way door than the
other three.

---

## 13. Opportunity and ROI decision

**Decision: the occurrence ledger now. Opportunity as a discriminator, not a
table. The ROI registry is derived, not stored.**

### Reasoning

§13.2's opportunity ledger fields — id, description, contract, cause, monthly and
annual impact, confidence, §9 category, responsible, action, deadline, status —
are a near-subset of §13.1's occurrence fields. The only additions are predicted
and realised saving.

So:

- `Occurrence.ledger_kind` enum: `EXCEPTION` or `OPPORTUNITY`.
- `OccurrenceImpact.category` already carries §9's seven categories, including
  `economia potencial` and `oportunidade de margem`.
- `OccurrenceImpact.predicted_amount`, `realized_amount`, `verified_at` cover the
  two extra fields.

**Why this is correct and not merely cheap.** §13.3's ROI rule — only savings
verified against the following month's base count as realised — is a verification
rule over the same impact rows. A separate Opportunity table would force
duplicating the impact model, the verification logic and the ACL. That is three
copies of logic that must never disagree.

`ledger_kind` is also a two-way door: promoting it to a separate table later is
straightforward. Building two tables now and merging them later is not.

### ROI registry

§13.3 is a pure aggregation over `OccurrenceImpact` filtered by verification state.
It needs **no table in Plan 003**. Deferred to Plan 006 reporting. If a frozen ROI
statement is later wanted, it is a `TonReportRevision` with `report_type = ROI`,
which gets immutability and hashing for free.

§9's rule that low-confidence impact never enters a target or realised ROI is
enforced when computing the aggregate: `confidence <> 'BAIXA'`.

---

## 14. Evidence and source model

**Decision: two tables. `SourceSnapshot` is a receipt. `FindingEvidence` is a
pointer with a generic locator. Neither is an ETL definition.**

### SourceSnapshot — the provenance anchor

| Field | Reason |
|---|---|
| `source_type` | NG_KEEVO, UPLOADED_SPREADSHEET, CONTRACT_DOCUMENT, DOCUMENT_CHUNK, MANUAL_ENTRY, CALCULATED_AGGREGATE, BANK_STATEMENT, PAYROLL_EXPORT |
| `source_system_label` | free text, for example `DRE Gerencial 2026` |
| `extracted_at` | §3.1 requires the extraction date |
| `period_start`, `period_end` | competência covered |
| `units_covered` JSONB | §5 Passo 1 |
| `row_count`, `checksum` | completeness and tamper evidence |
| `is_complete`, `missing_inputs` JSONB | §5 Passo 1: record what did not arrive |
| `is_schema_conformant` | drives the §3 `[fonte não padronizada]` label |
| `ingested_by`, `notes` | |

`SourceSnapshot` is required in Plan 003, not deferred, for two reasons: without it
a report is not reproducible (section 12), and S10 — no margin published on a
reproved base — is not expressible.

### FindingEvidence

| Field | Reason |
|---|---|
| `finding_id`, `source_snapshot_id` | linkage |
| `source_type` | same enum |
| **`confidence_level`** NOT NULL | §3.4 A/B/C/D. A published number without its level is a defect, so this is not nullable. |
| `record_key` | opaque source row key. **Not** an NG/Keevo column name. |
| `locator` JSONB | the single generic field: `{page, sheet, row, column, cell, chunk_id, char_span, line}` |
| `file_record_id`, `document_id`, `chat_message_id` | nullable links to existing Onyx storage |
| `extracted_value`, `value_scale`, `value_unit`, `value_currency` | decimal-as-string, per section 12 |
| `is_non_standard_source` | renders the §3 label |
| `redaction_level` | masked HR and PII handling |

`locator` is deliberately generic. It is the mechanism that lets one evidence table
serve spreadsheets, PDFs, chunks, manual entries and aggregates without
hard-coding any source schema.

### Explicitly not an ETL platform

No transform definitions, no scheduling, no field mapping, no connector
configuration. `SourceSnapshot` is a receipt of something that already happened.
NG/Keevo stays BLOCKED per D-009: the enum member exists so evidence can be
labelled later; no field mapping does.

### Blind spots

`Finding.finding_kind`: `DETECTION`, `SANITY_VIOLATION`, `BLIND_SPOT`. A
`BLIND_SPOT` finding is valid with no numeric impact and no source record — that is
what makes §11's "lacuna de dado é achado de primeira classe" real rather than
aspirational.

---

## 15. Contract and BusinessUnit identity scope

**Decision: identity and reference now. The full §4 contract master later.**

### BusinessUnit — identity only

| Field | Justification for inclusion now |
|---|---|
| `code` UNIQUE, `name` | reference |
| **`kind`** | OPERATIONAL, IMPLANTATION, PROSPECT, NON_OPERATIONAL. Required: §3.3's consolidation rule — a non-operational cost centre never enters a profitability ranking or an inter-municipal benchmark — is inexpressible without it. |
| `is_active` | lifecycle |
| `external_ref` | nullable, opaque |

Excluded: financials, dotação, headcount, fleet.

### Contract — identity only

| Field | Justification for inclusion now |
|---|---|
| `code` UNIQUE | nº contrato |
| `business_unit_id` | scope |
| `contracting_authority`, `object_summary` | reference |
| `start_date`, `end_date` | T19 vigência milestones need them |
| **`status`** | DRAFT, BIDDING, UNDER_JUDGEMENT, SIGNED, ACTIVE, SUSPENDED, ENDED. Required: S7 — an unsigned contract must not enter backlog, revenue or projection. This is precisely the Canoas-RS defect in §6.2, where a contract under judgement contributed a R$ 1.295 billion projection. |

Excluded, all LATER PHASE: global value, monthly value, readjustment index and
base date, amendments, apostilamentos, balance, percentage executed, contracted
services and quantities, crew and fleet sizing, dotação cost composition, BDI, ABC
curve, social charges, technical reserve, category floor, CCT, measurement and
billing criteria, penalties, glosa hypotheses, SLAs, guarantees, insurance,
obligations, fiscal and manager names.

### The inclusion test used

A §4 field is included in Plan 003 only if an already-specified S-rule or T-rule
cannot be expressed without it. Two fields pass: `BusinessUnit.kind` (§3.3) and
`Contract.status` (S7). Everything else waits.

`Occurrence` and `Finding` reference `business_unit_id` and `contract_id` as
**nullable** FKs, because corporate-level findings have no unit and some findings
precede contract identification.

---

## 16. Unresolved business-rule conflicts

No disputed value becomes a production rule. Each conflict gets schema support now
as a `RuleVersion` row with `status = PENDING_APPROVAL` and
`provenance = VALE_NORTE_REPORT_2026`. None becomes `ACTIVE`, and the CHECK
constraint in section 3 makes that structural.

### The six material-source reconciliation gates

| # | Section | Conflict | Schema now | Approval later |
|---|---|---|---|---|
| 1 | 1.1 | seven-row sum R$ 90,877,705.63; table total R$ 90,877,705.65; paid R$ 4,519.42; difference R$ 4,519.40 | yes — rule shape is reconciliation | **required**: liability versus expense treatment, and which total is authoritative |
| 2 | 1.3 | by origin R$ 4,210,512.00; monthly R$ 4,210,513.00; narrative R$ 4,210,513.16 | yes | **required**: aggregation level and the R$ 0.16 |
| 3 | 1.4 | visible rows R$ 473,552.00 versus stated R$ 473,827.00; gap R$ 275.00 | yes | **required**: completeness first. Rule activation blocked. |
| 4 | 1.5 | unit sums payroll R$ 4,984,535.00 / charges R$ 2,827,183.00 versus declared R$ 4,733,535.00 / R$ 2,936,450.00 | yes | **required**: the aggregate ratio is blocked; the 35–45% range is unapproved |
| 5 | 1.6 | calculated average R$ 3,474,240.67 versus R$ 3,474,174; drop ~87.13% versus prose 87% versus table −88.0% | yes | **required**: baseline and rounding policy |
| 6 | summary versus §1 | summary declares nine types; §1 contains eight items (1.1–1.8) | n/a | **required**: catalogue coverage |

### Other documented conflicts

| Conflict | Schema now | Approval later |
|---|---|---|
| Travel settlement: 48 hours versus five business days | yes — a `parameters` value | **required**, plus blocking authority |
| Budget coverage: five versus six of seven units | yes | **required** |
| Payroll charge range 35–45% | yes | **required** — provisional hypothesis, not a threshold |

### Two conflicts found by this gate, not previously recorded

| Conflict | Impact | Action |
|---|---|---|
| **§8 heading says "T13–T26"; the body defines T13–T30** | The T-code vocabulary is ambiguous, and §7 forbids renaming codes. `Rule.code` values cannot be fixed until this is settled. | Owner must reconcile the range before any T-code becomes a `Rule.code`. |
| **§5 Passo 6 publication ceilings (7 per day, 12 per month)** | These are publication limits. If read as detection limits they would silently drop findings. | Record explicitly: they belong to Plan 006 publication policy. **Do not add a cap column to `Finding` or `Occurrence`.** |

### Two consistency checks that passed

Worth recording, because they were checked rather than assumed:

- **§14.3 ISC weights sum to 100**: 20 + 15 + 15 + 12 + 10 + 10 + 10 + 8 = 100.
- **§10 criticality bands are contiguous with no gap**: ≥1%, 0.3–1%, 0.1–0.3%,
  below that monitoring.

### The §6.2 calibration figures

The margins of 187%, 153% and 1,020%, the R$ 9.75MM Toledo excess, the R$ 6.84MM
swapped revenue and the R$ 90.89MM parcelamento are **test fixtures at most**. They
are the defects TON must find, not values TON should encode. None becomes a
constant, a default or a seeded row.

---

## 17. Alembic investigation result

# Verdict A — REVISION IDENTIFIED

Revision `6e8f0a2b1c35` exists in this repository's object database. It was never
committed to any branch or tag, and it is not in the working tree.

### Exact provenance

| Attribute | Value |
|---|---|
| Blob | `9cd983b327f7dd2d3c8dca707407651431fd3ede` |
| Path | `backend/alembic/versions/6e8f0a2b1c35_merge_ton_and_federated_heads.py` |
| Size | 462 bytes |
| `revision` | `"6e8f0a2b1c35"` |
| `down_revision` | `("9drpiiw74ljy", "5d7e9a1c2b34")` — a **merge** revision |
| Body | empty `upgrade()` and `downgrade()`; joins two histories, alters no schema |
| Create Date | 2026-09-14 |

Reachable only from two Codex turn-diff refs, both pointing at tree `0fa14352e2`:

- `refs/codex/turn-diffs/captures/1789397232769/d0756505-…/base`
- `refs/codex/turn-diffs/checkpoints/af74fa8569…/bc42da6cee…/1789399443456/4f64244f-…`

That snapshot tree holds **447** files under `backend/alembic/versions` against
**444** in the working tree. The three extras form a local branch that no longer
exists:

| File | Revision | down_revision | Effect |
|---|---|---|---|
| `3c4a1f6e9b27_add_specialist_contributions_to_chat_message.py` | `3c4a1f6e9b27` | `("c7bf5721733e", "ad99acb9be41")` | a merge |
| `5d7e9a1c2b34_add_ton_role_to_persona.py` | `5d7e9a1c2b34` | `3c4a1f6e9b27` | adds `persona.ton_role VARCHAR(32) NULL` |
| `6e8f0a2b1c35_merge_ton_and_federated_heads.py` | `6e8f0a2b1c35` | tuple above | a merge |

Parent `9drpiiw74ljy` **is** in the tree, mid-chain. Parent `5d7e9a1c2b34` is
**not**; it survives only as blob `118bdb36571d3ff650c066616b170691605d895d` in the
same snapshot.

### Why history searches missed it

`git log --all -S/-G 6e8f0a2b1c35` returns four commits — `73b8ec4d34`,
`51688f8ead`, `ea903d2965`, `48ff0aba07` — and every hit is a
`plans/ton/backend/*.md` document, never a `.py`. The blob hangs off refs that
point directly at **trees**, not commits, so no commit diff ever contains it.
`git log --all --diff-filter=A` confirms the file was never added in any reachable
commit.

### Most likely sequence

An earlier agent session authored the three migrations, ran `alembic upgrade`
against the local development database — which stamped `alembic_version` to
`6e8f0a2b1c35` — then deleted the files without downgrading. The database is
therefore stamped at a revision the repository can no longer resolve. The snapshot
tree is a recoverable source for all three files.

This is inference from file contents and reachability. It was not confirmed against
the database, because this gate read no `alembic_version` row and ran no SQL against
the live database.

### Repository history state

| Directory | Files | Head | Root | Shape |
|---|---|---|---|---|
| `backend/alembic/versions` | 444 | **`ad99acb9be41`** | `47433d30de82` | **linear**, zero merge revisions, zero dangling `down_revision` |
| `backend/alembic_tenants/versions` | 10 | `a754e4f72e60` | `14a83a331951` | linear |

The repository itself is clean. Revision ids are 12 lowercase hex characters
(453 of 454; the exception is the hand-written `9drpiiw74ljy`). `6e8f0a2b1c35`
matches that convention syntactically, but its stepped `6e-8f-0a-2b-1c-35` pattern
marks it as hand-authored, like its siblings.

Remotes: `origin` = `Thalisson-DEV/onyx`, `upstream` = `onyx-dot-app/onyx`. `main`
is 11 commits ahead of `upstream/main` and 0 behind.

### 17.1 Empty disposable database to head — PASS

Run against a **new throwaway container** (`postgres:15.2-alpine`, host port
55432), never the live database.

| Check | Result |
|---|---|
| `alembic current` on the empty database | no revision — clean start |
| `alembic upgrade head` | **exit code 0** |
| `public.alembic_version` afterwards | `ad99acb9be41` |
| Tables created in `public` | 151 |
| External file-store migration step | completed, nothing to migrate |

The container was removed afterwards. Confirmed: `docker ps` still shows only the
five original `onyx-*` containers.

### 17.2 Column-level confirmation of SECURITY-08

On the freshly migrated disposable database, `information_schema.columns` for
`llm_provider`:

| Column | SQL type |
|---|---|
| `api_key` | `bytea` |
| `custom_config` | **`jsonb`** |

This confirms the defect at schema level, from repository migrations alone, without
reading the live database and without reading any credential value.

### 17.3 Two collateral findings — Plan 003's verification commands are wrong

**`alembic check` fails on the untouched baseline.** Measured against the disposable
database built purely from repository migrations at `HEAD`, with zero TON changes:

| Reported operation | Count |
|---|---|
| `modify_default` | 230 |
| `modify_nullable` | 88 |
| `remove_index` | 50 |
| `add_fk` | 40 |
| `remove_fk` | 34 |
| `modify_type` | 28 |
| `add_index` | 18 |
| `remove_column` | 10 |
| `remove_constraint` | 10 |
| `add_table` | 6 (includes `celery_taskmeta`, `celery_tasksetmeta`, `milestone`) |
| `remove_table` | 2 (includes `alembic_version` itself) |

Cause: `target_metadata` includes Celery's `ResultModelBase`, whose tables are
created at runtime rather than by migration, and `compare_server_default=True`
reports a difference for every Python-side default. **`alembic check` is not a
usable gate here.** Plan 003's done criterion "`alembic check` reports no model
drift" cannot pass and must be removed.

**`alembic -n schema_private upgrade head` collides in a single-tenant
deployment.** Observed: `Can't locate revision identified by 'ad99acb9be41'`.
Cause: `backend/alembic_tenants/env.py` does not set `version_table_schema`, so it
reads the same default-schema `alembic_version` table the main chain already owns.
The two chains cannot share one schema. TON is single-tenant
(`MULTI_TENANT=false`), so this command must not be in Plan 003's command list.
Record it as an environment fact rather than skipping the migration review, as the
plan already requires.

**The correct gate already exists.** `.github/workflows/pr-database-tests.yml` runs
`pytest tests/integration/tests/migrations/`, which applies pytest-alembic's
`test_single_head_revision`, `test_up_down_consistency` and `test_upgrade` to both
chains. Two consequences bind Plan 003:

1. **`test_single_head_revision` is enforced.** Every TON migration must chain
   linearly. A branched history or a merge revision fails CI. This is exactly what
   went wrong before.
2. **`test_up_down_consistency` is enforced.** Every TON migration needs a
   `downgrade()` that executes. It may be lossy; it may not be missing.

### 17.4 Live database state — the orphan stamp is gone

Plan 001 recorded the live integration database reporting `6e8f0a2b1c35`. **That is
no longer its state.** Verified by read-only query at the time of this gate:

| Check | Result | Meaning |
|---|---|---|
| `SELECT version_num FROM public.alembic_version` | **`ad99acb9be41`** | the repository head |
| row count | 1 | no split or duplicated stamp |
| public tables | **151** | byte-for-byte the same count as the freshly migrated disposable database in §17.1 |
| `persona.ton_role` present? | **no** | the orphan migration's only schema effect is absent |
| schemas | `public` only | no tenant schemas, consistent with `MULTI_TENANT=false` |
| TON domain tables | 0 | the first TON migration does not exist yet |
| data present | 2 users, 2 chat sessions, 2 user groups, 2 permission grants | light real usage, consistent with the Plan 008a slice |

The database is repository-consistent and will accept a new migration. The
container also shows `RestartCount=0` with a start time hours after this gate's only
Docker activity, so the change was not caused by anything here.

**No remedy is required.** The two options below are retained only as a record of
what would have been needed, and in case a second checkout or environment still
carries the orphan stamp.

**Option 1 — recreate the development database.**
Plan 001 proved a fresh database reaches head, and §17.1 reproduced it. Simplest;
costs local development data.

**Option 2 — surgical downgrade, if data must be kept.**
Restore the three orphan files from blob `9cd983b327f7dd2d3c8dca707407651431fd3ede`
and its two siblings **into the working tree only, never committed**, downgrade to
`ad99acb9be41`, then delete the files.
Caution: while those files exist the tree has two heads and a merge revision, so
`test_single_head_revision` would fail. Use a throwaway worktree and never commit.

### What this gate did not do

No stamp. No upgrade, downgrade or repair of any database. No manual
`alembic_version` edit. No replacement migration invented. No history deleted. The
live database was **read** — `SELECT` only, on `alembic_version`,
`information_schema` and row counts — to verify the primary blocker. No row was
written, altered or deleted, and no credential value was selected.

---

## 18. SECURITY-08 migration decision

**Decision: a separate security migration, immediately before the TON domain
chain. Do not couple it to TON schema.**

The six questions, answered.

### 1. Can the conversion safely live in the first TON migration chain?

Technically yes — the chain is linear and a revision can do both. **It should not.**

| Dimension | SECURITY-08 | TON domain schema |
|---|---|---|
| Target | an **existing** table holding **live credentials** | **new, empty** tables |
| Data transition | required, per-row, irreversible | none |
| Rollback | deliberately lossy by design | clean drop |
| Approval gate | open decision 7a (key custody) | none once section 2 holds |
| Failure mode | credentials unreadable or silently plaintext | tables absent |

Coupling them means a TON schema rollback also rolls back credential encryption, or
that an unresolved key-custody decision blocks the entire TON domain. Both are
avoidable by separating them. The gate's own instruction applies: prefer a separate
security migration if coupling increases rollback risk. It does.

### 2. Should it be a separate security migration immediately before Plan 003?

**Yes.** Call it **Plan 003a**. One revision, `down_revision` = the head at
implementation time. It creates no TON table.

### 3. How should existing plaintext rows be handled?

**In-place per-row re-encryption**, following `0a98909f2757_enable_encrypted_fields.py`:
add a temporary `LargeBinary` column, declare a lightweight `sa.sql.table()` literal
rather than importing the ORM, re-encrypt each row, drop the old column, rename.

**Reject the delete-the-data variant.** `b4950827c0dd_encrypt_external_app_credentials.py`
avoided a data transition by deleting rows. Here that would destroy live Bedrock and
Vertex credentials in existing deployments. Plan 007 reached the same conclusion.

Scope: `LLMProvider.custom_config` and `VoiceProvider.custom_config`, the two named
in SECURITY-08. `InternetSearchProvider.config`, `InternetContentProvider`, the
tracing provider and hook configs carry the same shape and are recorded as an
explicit follow-up rather than left to drift.

### 4. How should migration rollback behave?

`downgrade()` must exist and execute — `test_up_down_consistency` is enforced in
CI. It must be **deliberately lossy**: drop the encrypted column, re-add an empty
`JSONB` column, restore nullability, **do not decrypt**. `0a98909f2757` states the
reason in its own comment: a downgrade must not become a decryption oracle.
Operators re-enter credentials through the admin UI.

### 5. What happens if `ENCRYPTION_KEY_SECRET` is absent?

**The migration raises and aborts.** It must not write plaintext bytes into a column
the schema now claims is encrypted. That state is worse than the status quo, because
the EE read path falls back to a raw UTF-8 decode
(`backend/ee/onyx/utils/encryption.py:49-85`), so a plaintext row reads back
perfectly and there is **no read-time signal** that it was never encrypted.

**One addition to the Plan 007 sketch, which it does not currently state.** The
migration must also assert `global_version.is_ee_version()`. The Community
implementation of `_encrypt_string` returns `input_str.encode()` unconditionally
(`backend/onyx/utils/encryption.py:17-30`) — it logs a warning when a key is set and
stores cleartext anyway. `0a98909f2757` hit exactly this and its own comment admits
it. Without the EE assertion, `alembic upgrade` under a CE-resolved process converts
the column and writes plaintext, undetectably.

So the migration needs **two** guards:

```text
if not global_version.is_ee_version():   raise
if not ENCRYPTION_KEY_SECRET:            raise
```

Both must be tested.

Related note for CE deployments: the conversion still has value there — it stops the
value appearing in a plain `SELECT` or a JSONB index — but it provides no
cryptography. That should be stated plainly rather than implied.

### 6. How is key rotation preserved?

**Automatically, with no rotation-script change.**
`backend/onyx/db/rotate_encryption_key.py::_discover_encrypted_columns()` walks
`Base.registry.mappers` and collects every column whose type is `EncryptedJson` or
`EncryptedString`. Converting `custom_config` to `EncryptedJson` enrols it in
rotation for free. The routine reads raw bytes via `raw_col.cast(LargeBinary)`,
skips rows already readable under the current key so it is idempotent and resumable,
and `json.loads` values for JSON columns so the type decorator does not double-encode.

Add one test asserting `llm_provider.custom_config` appears in the discovered set.
That converts a free behaviour into a guaranteed one.

Two properties of the current scheme to record, unchanged by this work: AES-CBC here
is unauthenticated, with no MAC or AEAD, and the stored blob carries no key
identifier or version byte. Neither blocks SECURITY-08. Both are worth a follow-up.

### Masking is not a substitute

`_mask_provider_credentials` (`backend/onyx/server/manage/llm/api.py:250-264`) is
transport-only and opt-in per call site, with four call sites. Its sensitivity test
is a substring allow-list (`is_sensitive_custom_config_key`,
`backend/onyx/llm/utils.py:364-370`), so a secret under an unrecognised key is
returned unmasked. Plan 007's step 5 — replace the heuristic with a whole-dict mask —
should ship with 003a, not after it.

### 003a acceptance

- raw column bytes are not the plaintext value;
- round-trip through the runtime returns the original dict;
- API output stays masked;
- update preserves protection;
- a missing key aborts the migration;
- a CE-resolved process aborts the migration;
- a wrong key fails safely;
- logs and serialisation do not expose the value;
- a background worker can still read it;
- the rotation routine discovers the column.

---

## 19. Exact migration sequence

Derived from the evidence in sections 17 and 18. Each numbered migration is exactly
**one** Alembic revision, chained linearly, each with a working `downgrade()`.

### Step 0 — confirm the database is repository-consistent

Verified at gate time: `public.alembic_version` reports `ad99acb9be41`, one row,
151 public tables, no orphan `persona.ton_role`, zero TON tables (§17.4). **No
remedy is needed.** Re-run this one read-only check before starting, in case the
environment changed:

```text
docker exec onyx-relational_db-1 psql -U postgres -tAc "SELECT version_num FROM public.alembic_version;"
```

Stop if it returns anything that is not a revision present in
`backend/alembic/versions`.

### Step 1 — establish the current safe head

Read `backend/alembic/versions` and take the revision that no other file names as
`down_revision`. Today that is `ad99acb9be41`. **Do not hardcode it** — upstream
merges move it, and `main` is already 11 commits ahead of `upstream/main`.

### Step 2 — Plan 003a, security prerequisite

`down_revision` = head from step 1. Converts `LLMProvider.custom_config` and
`VoiceProvider.custom_config` to `EncryptedJson`. Two guards from section 18. Lossy
downgrade. **No TON table.** Ships with the whole-dict masking fix.

### Step 3 — verify before continuing

```text
cd backend; uv run pytest tests/integration/tests/migrations/
```

This is the repository's real gate: single head, up/down consistency, upgrade to
head, on both chains. Then the 003a acceptance list and the rotation-discovery test.

### Step 4 — Plan 003b, TON identity and rule spine

`down_revision` = 003a. Creates `BusinessUnit`, `Contract`, `Rule`, `RuleVersion`,
`SourceSnapshot`, `AnalysisRun`, `AnalysisRunRuleVersion`,
`AnalysisRun__SourceSnapshot`, `AnalysisStep`.

### Step 5 — Plan 003c, findings, occurrences and ACL

`down_revision` = 003b. Creates `Finding`, `FindingEvidence`,
`FindingInterpretation`, `Occurrence`, `OccurrenceEvent`, `OccurrenceImpact`,
`OccurrenceAssignment`, `OccurrenceNote`, `OccurrenceImpactedDomain`, and the four
`*__UserGroup` junctions.

### Step 6 — Plan 003d, reports and audit

`down_revision` = 003c. Creates `TonReport`, `TonReportRevision`, the five
`TonReportRevision__*` join tables, and `TonAuditEvent`.

### Step 7 — seed no business rule

**No migration inserts a `Rule` or `RuleVersion` row.** Rule creation is an
explicit, audited admin action. The `ACTIVE`-requires-approval CHECK from section 3
makes an accidental activation impossible.

One distinction worth stating, because a precedent exists that looks contrary:
`977e834c1427_seed_default_groups.py` seeds default groups and permission grants.
That is an **authorization bootstrap** — the deployment cannot function without it.
A business rule is not in that category.

### Step 8 — environment facts to record, not commands to run

- **Do not** run `alembic -n schema_private upgrade head` in this deployment. It
  collides with the main chain's `alembic_version` (section 17.3).
- **Do not** use `alembic check` as a gate. It reports 470-plus spurious operations
  on the untouched baseline (section 17.3).

### Per-migration constraints

Every one of 003a–003d must satisfy:

| Constraint | Source |
|---|---|
| exactly one head after the revision | CI `test_single_head_revision` |
| `downgrade()` exists and executes | CI `test_up_down_consistency` |
| empty database reaches head | CI `test_upgrade` |
| written by hand into the file Alembic generates | `backend/AGENTS.md` |
| Alembic run from `backend/` through `uv run` | `backend/AGENTS.md` |
| no existing table deleted or silently altered | Plan 003 STOP condition |

---

## 20. Mandatory implementation tests

Placement follows `backend/AGENTS.md`: prefer integration; use external dependency
unit tests where real Postgres is needed but the function is called directly; keep
unit tests for pure functions only. Repository test types, not invented ones.

### Schema — `backend/tests/integration/tests/migrations/`

The three pytest-alembic tests already present cover single head, up/down
consistency and empty-database-to-head for both chains. They run in CI. Adding TON
migrations requires **no new file here** — but each slice must be verified against
them before the next slice starts.

Add TON-specific schema assertions in
`backend/tests/external_dependency_unit/ton/test_domain_schema.py`:

- every unique constraint exists: `Occurrence.identity_key`,
  `Finding(analysis_run_id, rule_version_id, identity_key)`,
  `AnalysisRun.idempotency_key`, `RuleVersion(rule_id, version)`,
  `TonReportRevision(report_id, revision_no)`;
- every foreign key and its `ondelete` behaviour;
- `CHECK (status <> 'ACTIVE' OR approved_by IS NOT NULL)` on `RuleVersion`;
- `CHECK` on `AnalysisStep` BLOCKED requiring a named cause;
- `CHECK` on `OccurrenceEvent` requiring a user actor for human-only transitions;
- **no TON table has an `is_public` column** — an inverse assertion, which is what
  makes the fail-closed decision durable.

### Rules — `backend/tests/unit/ton/test_rule_versioning.py`

- a new `RuleVersion` does not alter a `Finding` that pinned the previous version;
- `effective_from` / `effective_to` selection picks exactly one version for a date;
- `status` transitions are legal, and `ACTIVE` without approval is rejected;
- a `TEST_ONLY` version cannot produce a publishable Occurrence;
- the eight executor shapes run positive, negative, boundary, missing and malformed
  inputs;
- the six source-material conflicts (section 16) remain non-final.

### Analysis — `backend/tests/integration/ton/test_analysis_run.py`

- **domain-scoped blocking, the anti-defect test**: a FAILED step in
  `(domain=X, unit=U)` blocks only steps scoped to `(X, U)` that declare X as a
  prerequisite; every other domain and every other unit stays PASSED; the run ends
  `COMPLETED_WITH_BLOCKED_DOMAINS`, never `FAILED`;
- S10: a reproved base blocks the PUBLICATION step for that domain and unit only;
- partial runs persist `result`, `timeout`, `error` and `insufficient_data` per
  specialist, and a failed specialist does not erase a successful sibling;
- retry idempotency: re-sending the same `idempotency_key` converges on one run;
- `AnalysisRunRuleVersion` records skipped rules with a reason.

### Findings and occurrences — `backend/tests/integration/ton/test_occurrence_lifecycle.py`

- create: one Finding, one Occurrence;
- dedupe: two concurrent workers on the same `identity_key` converge on one
  Occurrence — run as a genuine concurrent test, not sequential;
- repeat: second detection creates a Finding, bumps counters, creates no second
  Occurrence;
- resolve: status projection and `OccurrenceEvent` agree;
- recurrence: both `post_resolution_policy` branches, plus forced supersede when the
  rule version changed;
- **identity stability**: `identity_key` is unchanged when title, description and
  interpretation change — the guard against LLM-derived identity;
- evidence linkage: `confidence_level` is NOT NULL and A/B/C/D is preserved;
- blind spot: a `BLIND_SPOT` finding is valid with no impact and no source record;
- projection honesty: `status` and `open_cycle_count` equal the values derived from
  `OccurrenceEvent`.

### Interpretation — `backend/tests/integration/ton/test_interpretation_lifecycle.py`

- `PENDING` is committed before the provider call;
- provider unavailable, timeout, malformed output and policy refusal each leave a
  durable `FAILED` and a non-final Finding;
- a Finding cannot reach final state without `COMPLETED` or `NOT_REQUIRED`;
- a report revision refuses a Finding whose interpretation is not complete;
- the interpreter cannot change deterministic values, source ids, `rule_version_id`,
  `identity_key` or the impact amount;
- no chain-of-thought and no raw transcript is persisted — an inverse assertion.

### ACL — `backend/tests/integration/ton/test_ton_acl.py`

- admin (global token) reads everything;
- allowed group reads;
- disallowed group is denied, **by id and by list** — both paths, because a list
  filter that works while a detail fetch leaks is the classic failure;
- scoped manager acts only within managed groups;
- **no ACL row means denied** — the fail-closed test;
- cross-unit denial: a Mossoró group cannot read an Itabirito occurrence;
- cross-domain denial: an HR-scoped group cannot read a financial occurrence;
- delete requires global authority; a scoped manager is refused;
- a scoped manager cannot widen scope by reassigning groups in the request;
- **CE-resolution test**: TON ACL writes still work when the versioned dispatch
  resolves Community implementations — the trap in section 10.

### Report — `backend/tests/integration/ton/test_report_immutability.py`

- an attempted mutation of a final revision raises;
- a correction creates a new revision and links the prior one;
- **canonical hash determinism**: the same logical content hashes identically across
  two processes and two orderings of input;
- decimal-string serialisation: a monetary value never round-trips through a float,
  asserted by hashing the same value supplied as `Decimal` and as string;
- absent versus null: a payload omitting a key and one setting it to null are
  rejected as ambiguous, or normalise to one form;
- reproducibility: after a rule change, an occurrence resolution and a new
  interpretation, the pinned revision still reproduces its hash;
- a not-assessed ISC dimension and its redistributed weights survive the snapshot;
- unauthorised report access is denied.

### Audit — `backend/tests/integration/ton/test_ton_audit.py`

- each of the ten required events from section 11 persists;
- a domain transition write failure **raises** and rolls back the business change;
- a `TonAuditEvent` write failure **does not** fail the business operation;
- the audit read route is ACL-filtered and paginated;
- a new `AuditAction` without an OCSF mapping fails at import.

### SECURITY-08 — `backend/tests/external_dependency_unit/ton/test_provider_secret_encryption.py`

Real Postgres is required to read raw bytes, and the precedent
`test_rotate_encryption_key.py` already lives in this directory with a
`_raw_credential_bytes` helper that bypasses the type decorator — reuse it.

- **no plaintext persisted**: raw column bytes are not the value;
- round-trip returns the original dict;
- a missing `ENCRYPTION_KEY_SECRET` aborts the migration;
- a CE-resolved implementation aborts the migration;
- a wrong key fails safely rather than returning garbage;
- API output remains masked, including a key whose name matches no known fragment;
- a background worker can read the value;
- `rotate_encryption_key` discovers `llm_provider.custom_config`.

### Tests deliberately not written now

This gate wrote no product test. `domain-rules.md` requires named specs to exist
before implementation, and Plan 003 lists three specific paths. Creating them is the
first task of the implementation slice, not of this readiness gate.

---

## 21. Recommended Plan 003 slicing

**Recommendation: split into four slices.**

Plan 003 today is one P1 / effort-L / risk-HIGH slice that mixes a blocked security
migration, an unapproved report-immutability decision, an absent ACL model and an
absent audit model. That is too broad to verify.

The split is justified against the gate's bar — split only to reduce migration or
security risk, or to produce independently testable boundaries — not for tidiness.

| Slice | Contents | Why it is a real boundary |
|---|---|---|
| **003a** | security prerequisite: provider `custom_config` encryption + whole-dict masking | **Risk reduction.** Different blast radius (an existing table with live credentials), different rollback (deliberately lossy), different approval gate (open decision 7a). Coupling it to TON schema means a TON rollback un-encrypts credentials. |
| **003b** | `BusinessUnit`, `Contract`, `Rule`, `RuleVersion`, `SourceSnapshot`, `AnalysisRun`, `AnalysisStep` | **Independently testable.** Rule versioning, effective-date selection, approval constraints and domain-scoped blocking need no Finding table. The anti-defect blocking test runs here. |
| **003c** | `Finding`, evidence, interpretation, `Occurrence` and its history tables, the four ACL junctions | **Independently testable.** Lifecycle, dedup, concurrency and ACL. Depends on 003b. |
| **003d** | `TonReport`, `TonReportRevision`, join tables, `TonAuditEvent` | **Independently testable.** Snapshot immutability, hash determinism and audit persistence. Depends on 003c. |

Each slice is one Alembic revision, chained linearly, individually reversible, with
its own test file from section 20.

Ownership boundaries already recorded in `README.md` are preserved: Plan 003 owns
report snapshot storage; Plan 006 owns schedules, run dispatch, alert projection and
API use of the report service. Nothing here moves that line.

### Corrections Plan 003 must absorb

1. Remove the `alembic check` done criterion — it cannot pass (section 17.3).
2. Remove `alembic -n schema_private upgrade head` from the command list, and record
   the single-tenant environment fact instead (section 17.3).
3. Add resource ACLs to scope — the plan currently has none (section 10).
4. Add the audit-history model to scope (section 11).
5. Replace "logical identity stays opaque until approved domain keys exist" with the
   concrete contract in section 7. Identity is now specified: opaque digest, closed
   component vocabulary, declared per RuleVersion.
6. Record the canonicalisation rules before any hashing code is written (section 12).
7. State that the detector holds no source-write path, and that this is enforced by
   the absence of any such column (section 9).

---

## 22. Frontend contract impact

No frontend file is modified. These are provisional backend requirements for
TON-FE-008 (Occurrences) and TON-FE-009 (Reports), per the coordination matrix.

**No endpoint path is invented.** `findings-ux-plan.md` and `reports-ux-plan.md`
both flag `/api/ton/occurrences` and `/api/ton/reports` as planning markers, not
approved APIs, and `backend-dependencies.md` states the route name is still pending.
That decision stays open. Integration tests must call the frontend at
`http://localhost:3000/api/*`, per the repository instructions.

### FE-008 Occurrences — capabilities the backend must eventually provide

| Need | Backing |
|---|---|
| list with server-side pagination and stable ordering | `Occurrence`; stable sort requires a tiebreaker, so order by `(last_detected_at, id)` |
| filters: status, criticality, assignee, domain, business unit, contract, period, `ledger_kind`, free text | indexed `Occurrence` columns |
| filter state reflected in the URL | a query-parameter contract, not a POST body |
| detail | `Occurrence` plus its impact, assignment, interpretation and evidence |
| **allowed transitions for the current user** | computed server-side from section 9's constraints plus the caller's tokens. The UI must not infer them, or it will offer an action the backend refuses. |
| history | `OccurrenceEvent`, paginated, ACL-filtered |
| evidence | `FindingEvidence` with `confidence_level` and `locator`; content stays out of the list response |
| authorization surfaced per row | so the UI can hide edit affordances — while the backend still refuses direct access |
| criticality as text plus a token, never colour alone | accessibility requirement already in the FE plan |
| financial impact with currency, scale and confidence | `OccurrenceImpact`; decimal-as-string on the wire, matching section 12 |
| unknown or unauthorised field renders as absent | never inferred, never filled from another source |

### FE-009 Reports — capabilities the backend must eventually provide

| Need | Backing |
|---|---|
| list with type, period, status, creator, validity | `TonReport` + latest `TonReportRevision` |
| asynchronous creation returning an identifier and a state | Plan 006 owns dispatch; Plan 003 owns the snapshot |
| report state vocabulary | `queued`, `generating`, `ready`, `failed`, `expired`, `forbidden` — matching the FE plan |
| bounded polling with a timeout | the state must be terminal-detectable |
| detail: metrics, included occurrences, rule versions, sources | the `TonReportRevision__*` join tables |
| download metadata: time-bounded authorisation, no permanent URL | `file_record_id` plus a short-lived grant |
| revision history and correction reason | `TonReportRevision.superseded_by_revision_id` |
| re-check authorization at download time | permissions can change after generation |
| metrics filtered by the same ACL as occurrences | section 10 |

### Contracts this work must not change

`persona` and its snapshots, projects, files, incognito, chat, search, citations,
connectors, OAuth, indexing, usage export, query history, authentication, RBAC and
capabilities. Plan 003 adds tables and tokens; it changes no existing contract.

---

## 23. Remaining blockers

### Cleared during this gate

| # | Blocker | How it cleared |
|---|---|---|
| **B1** | The local database was stamped at orphan revision `6e8f0a2b1c35` | **CLEARED, verified.** It now reports `ad99acb9be41` with 151 tables, no orphan column and zero TON tables (§17.4). |
| **B2** | Plan 003 lacked ACL scope, audit scope and the canonicalisation decision | **CLEARED.** Sections 10, 11 and 12 supply them. Plan 003 now points here and lists both in scope and done criteria. |
| **B3** | Two of Plan 003's verification commands cannot pass | **CLEARED.** Both removed from the plan and replaced with `pytest tests/integration/tests/migrations/` (§17.3). |

### Cleared after this gate

| # | Blocker | How it cleared |
|---|---|---|
| **B4** | Open decision 7a — who holds `ENCRYPTION_KEY_SECRET`, where it is stored, the rotation window | **CLEARED.** Resolved as D-040 and executed as Plan 003a, revision `714172b66b07`. See `003a-provider-secret-encryption.md`. 003b takes `714172b66b07` as its `down_revision`. |

### Blocking rule activation, not schema creation

These do **not** block the migration, because section 3 keeps every one of them as
data. They block a `RuleVersion` reaching `ACTIVE`.

1. The six material-source reconciliation gates (section 16).
2. Travel settlement: 48 hours or five business days, plus blocking authority.
3. Budget coverage: five or six of seven units.
4. The payroll charge range (35–45% is an unapproved hypothesis).
5. The §1.6 baseline and rounding policy.
6. **New**: the §8 T-code range, T13–T26 versus T13–T30.
7. Every threshold in §6 S1–S10 and §7–§8 T1–T30 (24 parameter sets).
8. Accepted units, currencies, timezones, rounding and precision.
9. Which roles see HR, financial, contract and fleet evidence — the group design of
   section 10, not a new mechanism.
10. Retention for temporary inputs, source snapshots, evidence and report artifacts.
11. Whether interpretation may receive raw evidence, masked excerpts or structured
    values only.

### Unchanged pre-existing blockers

| Item | Status |
|---|---|
| NG/Keevo schema, authentication, limits, identifiers, deletion contract | BLOCKED (D-009). The enum member exists; no field mapping does. |
| Telegram channel contract (Plan 009) | BLOCKED. Not a Plan 003 dependency. |
| The underlying workbook, DRE, contracts, bank extracts, payroll detail | absent from this checkout |
| SECURITY-06 specialist memory bypass | assigned to Plan 005 |
| `alembic check` baseline drift | pre-existing upstream condition; not TON-caused; not TON's to fix |
| AES-CBC is unauthenticated; no key id or version byte in the blob | pre-existing; follow-up, not a Plan 003 blocker |

### Documentation drift corrected by this gate

| Drift | Correction |
|---|---|
| `roadmap.md` and `decision-log.md` cite execution baseline `6e4b2a066459e3bd7217341b6f2fa5af4eb4bc4f` | current baseline is `73b8ec4d34` |
| Several documents cite the Vale Norte report at `plans/ton/Relatorio_…` | it is at `plans/ton/backend/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt` |
| `008a` and `docs/group-manager-scoped-permissions/` cite `enums.py:490-549` and `models.py:4371-4391` | actual locations are `enums.py:640` and `models.py:5027` |

---

## Confirmations

- **No application code was changed.** No model, no migration, no ORM edit, no API,
  no tier gate, no frontend, no agent, no scheduler, no Telegram, no NG/Keevo, no
  deterministic rule. `git status` shows only files under `plans/`.
- **No migration was created.** `backend/alembic/versions` still holds 444 files;
  `backend/alembic_tenants/versions` still holds 10.
- **The live database was not mutated.** No stamp, no upgrade, no downgrade, no
  `alembic_version` edit, no INSERT, UPDATE or DELETE, no DDL. It was **read**:
  `SELECT` on `alembic_version`, `information_schema` and row counts, to verify
  blocker B1.
- **The `onyx-*` containers were not restarted by this gate.** `RestartCount=0` and
  a start time hours after the only Docker activity here.
- **Migration verification used a new disposable container**, `postgres:15.2-alpine`
  on host port 55432, removed afterwards. `docker ps -a` confirms none remains.
- **No secret value was read or printed.** SECURITY-08 was confirmed by column type
  from `information_schema` alone, on both the disposable and the live database.
