# Plan 003c — TON findings, occurrences, evidence and resource ACL

> **Executor instructions**: This is the second TON-owned domain schema, split out
> of Plan 003 by `003-readiness.md` §21. It chains from 003b and creates no
> report or audit table.
>
> **Drift check (run first)**: `git status --short`. Then read the current
> main-chain head from `backend/alembic/versions` — take the revision no other
> file names as `down_revision`. Do not hardcode a head.

## Status

- **State**: DONE
- **Priority**: P1
- **Effort**: L
- **Risk**: MEDIUM (twelve new tables; no existing table is altered)
- **Depends on**: `003-readiness.md`, `003b-ton-identity-rules-analysis.md`,
  `008a-capability-gates.md`
- **Blocks**: `003d` uses this revision as its `down_revision`
- **Category**: direction
- **Baseline commit**: `1a9b40476abbac0594c40eb264ed3e97e3a14bb3` (`main`)
- **Executed at**: 2026-09-15

## Issues to Address

After 003b, TON could define a rule and record that an analysis ran. It could not
record what the analysis *found*.

Without this slice there is no immutable detection, so a rerun either rewrites
history or duplicates it. There is no persistent business case, so "is this the
same problem as last month?" has no answer. There is no interpretation lifecycle,
so a provider failure is indistinguishable from an empty result. And there is no
resource ACL, so Vale Norte financial data would be visible to everyone who can
reach the deployment.

## Alembic chain

| | |
|---|---|
| Previous head | `faee7eaa921e` (003b) |
| New revision | `6b0ca4eb29fb` |
| `down_revision` | `faee7eaa921e` |
| Heads after the change | one (`6b0ca4eb29fb`) |

Pre-flight confirmed a single main-chain head across 446 revision files, that
`faee7eaa921e` was that head and therefore the correct parent, that
`714172b66b07` (003a) was present, and that no occurrence or finding migration
already existed.

## The readiness correction this slice records

`003-readiness.md` §21 says 003c creates "the four `*__UserGroup` junctions", and
§10 lists `TonReport__UserGroup` among them.

**That wording conflicts with the slice boundary.** `TonReport` does not exist
until 003d. A junction to an absent table cannot be created, and a permission that
authorizes nothing while telling an administrator otherwise is worse than a
missing one.

The authoritative slicing is therefore:

| Slice | Junctions |
|---|---|
| **003c** | `BusinessUnit__UserGroup`, `Contract__UserGroup`, `Occurrence__UserGroup` |
| **003d** | `TonReport__UserGroup` |

`Finding` and `FindingEvidence` get **no** junction in any slice. Their visibility
derives from the owning occurrence and its organizational context. Two independent
ACLs over one analytical case would eventually grant what the other denies
(readiness §10).

Three tests pin the correction: the junction set at head is exactly three, no
`ton_finding__user_group` exists, and no TON permission token contains `report`.

## Schema introduced

Twelve tables and one sequence, all prefixed `ton_`. Class names follow the
readiness names.

| Table | Purpose |
|---|---|
| `ton_occurrence` | the persistent §13.1 business ledger |
| `ton_finding` | immutable deterministic detections |
| `ton_finding_evidence` | source pointers with a generic locator |
| `ton_finding_interpretation` | append-only AI-interpretation attempts |
| `ton_occurrence_event` | authoritative append-only lifecycle history |
| `ton_occurrence_impact` | normalised §9 quantification |
| `ton_occurrence_assignment` | responsibility and deadline history |
| `ton_occurrence_note` | human commentary |
| `ton_occurrence_impacted_domain` | the §15 handoff list |
| `ton_business_unit__user_group` | fail-closed unit ACL |
| `ton_contract__user_group` | fail-closed contract ACL |
| `ton_occurrence__user_group` | fail-closed occurrence ACL |

Plus `ton_occurrence_short_code_seq`, which allocates the human-facing occurrence
code. A sequence rather than a Python counter: two concurrent detector workers must
not compute the same code, and a gap in a display code is not a defect whereas a
duplicate would be.

Primary keys are UUIDs with a Python-side `uuid4` default. Timestamps are
`DateTime(timezone=True)` with `server_default=func.now()`. JSON is `JSONB`. Enums
are `Enum(..., native_enum=False)`.

Files created:

- `backend/onyx/db/ton/findings.py`
- `backend/onyx/db/ton/occurrences.py`
- `backend/onyx/db/ton/occurrence_records.py`
- `backend/onyx/db/ton/interpretations.py`
- `backend/onyx/db/ton/acl.py`
- `backend/alembic/versions/6b0ca4eb29fb_ton_findings_occurrences_and_resource_acl.py`

Files modified: `backend/onyx/db/ton/models.py` (twelve models),
`backend/onyx/db/ton/enums.py` (sixteen vocabularies),
`backend/onyx/db/ton/identity.py` (the digest, on top of the unchanged 003b
contract), `backend/onyx/db/enums.py` (two permission tokens),
`backend/onyx/auth/permissions.py` (two registry entries and one implication).

`backend/alembic/env.py` needed no change: it already imports
`onyx.db.ton.models`, so the new tables are in `target_metadata`.

Everything sits in the Community tree. No TON behaviour resolves through EE
dispatch, and no function here reads a licence, a tier or `global_version`.

## Finding versus Occurrence

Preserved exactly as readiness §6 decided.

| | `Finding` | `Occurrence` |
|---|---|---|
| Meaning | one deterministic detection | one persistent business case |
| Mutability | immutable, append-only | lifecycle by appended events |
| Cardinality | one per `(run, rule_version, identity_key)` | one per `identity_key` |
| Audience | internal analytical evidence | the user-facing entity |

They are not merged. A single mutable entity would fail audit history and the
many-findings-one-case requirement.

## Finding implementation

Every finding pins `analysis_run_id`, `rule_version_id`, `occurrence_id`,
`identity_key`, `finding_kind` and `interpretation_status`, plus the deterministic
measurement and scope.

**`rule_version_id`, never `rule_id`.** There is no `rule_id` column on
`ton_finding` at all, and a schema test asserts its absence. A column that could
disagree with the version is a column a threshold change could use to reinterpret
a published detection. `create_finding__no_commit` takes the `RuleVersion` object
rather than an id, so a caller cannot pass a rule by mistake.

`business_unit_id` and `contract_id` are nullable: a corporate finding has no unit,
and a finding may precede contract identification (readiness §15).

### Uniqueness

`uq_ton_finding_run_rule_version_identity` over
`(analysis_run_id, rule_version_id, identity_key)`. Retrying a detection inside one
logical analysis cannot produce a second finding — asserted both through the domain
path and by inserting the duplicate row directly.

### Kind

`DETECTION`, `SANITY_VIOLATION`, `BLIND_SPOT`.

A `BLIND_SPOT` finding is valid with no numeric value and no evidence row. Nothing
in the model or the create function requires an amount, which is what makes Prompt
Mestre §11's "lacuna de dado é achado de primeira classe" real rather than
aspirational. A named test creates one with no impact and no source row, and a
companion test assigns it to a named field owner who holds no Onyx account.

### Immutability

There is no `update_` and no `delete_` function in `findings.py`, and a test
asserts it by name prefix. Immutability is enforced by the absence of a write path
rather than by a convention a later caller could overlook.

`interpretation_status` is the single mutable column, owned by
`interpretations.py`. `ton_finding` carries **no** lifecycle status: no `status`,
no `resolved_at`, no `criticality`. Lifecycle belongs to the occurrence, narrative
to the interpretation.

`IMMUTABLE_FINDING_COLUMNS` names the twenty deterministic columns in one place,
and a test parses `interpretations.py` with `ast` to assert no function there
assigns any of them.

## FindingEvidence implementation

The readiness §14 contract, in full: `finding_id`, `source_snapshot_id`,
`source_type`, `confidence_level`, `record_key`, `locator`, `file_record_id`,
`document_id`, `chat_message_id`, `extracted_value`, `value_scale`, `value_unit`,
`value_currency`, `is_non_standard_source`, `redaction_level`.

Foreign-key types match the existing tables exactly: `file_record.file_id` and
`document.id` are `String`, `chat_message.id` is `Integer`. All three use
`SET NULL` — losing a stored artifact must not delete the record that it was cited.

### The generic locator

`locator` is JSONB and source-agnostic. It may carry `page`, `sheet`, `row`,
`column`, `cell`, `chunk_id`, `char_span` or `line`. A test round-trips a
spreadsheet locator, a PDF locator and a chunk locator through the same column.

There is no `ng_account_id` and no `keevo_document_number`. `FindingEvidence` is a
pointer to source material, not an ETL schema, and NG/Keevo field mapping stays
BLOCKED under D-009.

### Confidence

`confidence_level` reuses the 003b `EvidenceConfidenceLevel` (`A`/`B`/`C`/`D`) and
is **NOT NULL**. Prompt Mestre §3.4 makes a published number without its level a
defect.

`highest_evidence_confidence` reads the best level present; it never combines
levels. A test adds five `D` rows and asserts the aggregate is still `D`. There is
deliberately no arithmetic that could turn quantity into quality.

### Decimal strings

`extracted_value` is a `String`, not a numeric column. It records what the source
stated at the source's own scale, and passing a `float` raises. A schema test
asserts the column type is `character varying`.

### Redaction

`redaction_level` is NOT NULL with **no server default** — the writer states how
much identity a row carries rather than letting it be assumed. Members: `NONE`,
`ROLE_ONLY` (the §9 default posture), `MASKED_IDENTIFIER`, `IDENTIFIED`.

## FindingInterpretation implementation

Append-only, one row per attempt, with the readiness §8 field list: `finding_id`,
`attempt_no`, `status`, `llm_provider`, `model_name`, `prompt_key`,
`prompt_version`, `summary`, `probable_cause`, `recommended_action`,
`impact_narrative`, `proposed_criticality`, `proposed_nc_code`,
`evidence_reference_ids`, `input_scope`, `started_at`, `finished_at`,
`failure_class`, `retry_eligible`.

`uq_ton_finding_interpretation_attempt` over `(finding_id, attempt_no)` gives the
ordered attempts. A retry appends; it never rewrites.

### Lifecycle primitives

`interpretations.py` holds the transactional lifecycle a later Plan 005 agent
caller will drive. **No provider is contacted anywhere in this slice**: there is no
LiteLLM import, no HTTP call and no prompt text.

- `begin_interpretation(...)` — creates the PENDING attempt, sets
  `Finding.interpretation_status = PENDING`, and **commits**;
- `mark_interpretation_running(...)` — optional, for a long-running attempt;
- `complete_interpretation(...)` — records the business-facing output;
- `fail_interpretation(...)` — records a durable failure class.

The commit inside `begin_interpretation` *is* the durability guarantee, which is
why that function carries no `__no_commit` suffix while the rest of the TON package
does: the difference is visible at the call site.

### PENDING before the provider

The critical invariant, and the way it is verified: a second, independent
connection reads `Finding.interpretation_status` while the first is still
mid-flight. Only committed data is visible there, so the assertion cannot pass
unless PENDING was durable before any provider request could begin. A companion
test discards the writer session entirely — simulating a call that never returns —
and reads back a visible, non-final PENDING record.

### Failure is durable

All five failure classes are tested through an injected fake provider boundary that
raises: `PROVIDER_UNAVAILABLE`, `TIMEOUT`, `MALFORMED_OUTPUT`, `POLICY_REFUSAL`,
`INSUFFICIENT_EVIDENCE`. Each leaves a `FAILED` attempt and a non-final finding
that survives the session, with `summary` still null.

Three constraints stop a failure becoming an empty success:

- `ck_ton_finding_interpretation_completed_has_summary`;
- `ck_ton_finding_interpretation_completed_has_provenance`;
- `ck_ton_finding_interpretation_failed_has_class`.

`retry_eligible` is explicit rather than inferred from the failure class: whether a
policy refusal is worth retrying is a judgement the caller makes.

### No hidden model output

No chain-of-thought, no hidden reasoning, no raw prompt body, no response
transcript. Reproducibility comes from `prompt_key` plus `prompt_version`, not from
the body. Two inverse assertions — one over the built schema, one over the model
metadata — reject any column whose name contains `chain_of_thought`, `reasoning`,
`raw_response`, `raw_prompt`, `prompt_body`, `prompt_text`, `transcript`,
`completion`, `messages` or `thinking`. No message, traceback or provider payload
is stored on failure either; the failure class is the whole record.

### Proposals only

`proposed_criticality` and `proposed_nc_code` are named as proposals, and a test
asserts that `criticality` and `nc_code` do **not** exist on this table — a field
with the bare name would invite a caller to treat model output as decided.

Completing an interpretation with a proposal changes nothing on the occurrence.
Promotion is `promote_interpretation__no_commit`, a `PROMOTE_INTERPRETATION`
transition the event table forces to carry an identified user and an authorization
reference. That function accepts no deterministic value, no source id, no
`identity_key`, no `rule_version_id` and no impact amount — there is no parameter
for any of them.

### Input scope

`STRUCTURED_ONLY`, `MASKED_EXCERPT`, `FULL_EVIDENCE`.

`begin_interpretation` refuses `FULL_EVIDENCE` when `TON_TRACE_CONTENT_MODE` is
`metadata`, which is the Plan 002 / D-015 privacy contract: a deployment that
promised not to send content cannot persist an attempt that did. Tested in both
directions, including that the two narrower scopes stay available.

## Occurrence implementation

The readiness §6 field contract, in full: `id`, `short_code`, `identity_key`,
`rule_id`, `current_rule_version_id`, `owning_domain`, `ledger_kind`,
`criticality`, `nc_code`, `business_unit_id`, `contract_id`, `title`, `status`,
`first_detected_at`, `last_detected_at`, `detection_count`, `open_cycle_count`,
`resolved_at`, `verification_criterion`, `verification_result`,
`verification_checked_at`, `legal_review_required`, `requires_human_closure`,
`superseded_by_occurrence_id`.

Plus two columns the supersede contract requires — see below.

### Uniqueness, and how supersede coexists with it

`UNIQUE(identity_key)` is the deduplication boundary. Application-level pre-checks
are insufficient, so the database is the authority.

Readiness §7 also requires `SUPERSEDE_WITH_NEW_OCCURRENCE`, which creates a *new*
occurrence for the same logical case. The two only hold together if the superseding
case's canonical tuple differs. So:

| Column | Meaning |
|---|---|
| `identity_key` UNIQUE | the effective dedup key: the digest including the supersede generation |
| `logical_identity_key` | the generation-free digest — the lineage key, shared by every generation |
| `supersede_generation` | 1 for a case never superseded |

`uq_ton_occurrence_lineage_generation` over
`(logical_identity_key, supersede_generation)` makes a concurrent double-supersede
impossible, and `ck_ton_occurrence_first_generation_identity` forces
`identity_key = logical_identity_key` at generation 1. **Every case that was never
superseded therefore carries exactly the pure canonical digest** — the ordinary
path is precisely the readiness contract, and the generation column only appears in
the digest of a case that was actually superseded.

This is an implementation decision, not a reopened architecture decision: it is the
only way to satisfy both readiness requirements at once.

`Finding.identity_key` stores the occurrence's *effective* key, so a retry inside
one run collides with the pre-existing finding for that generation.

### Ledger kind

`EXCEPTION` and `OPPORTUNITY`, on the occurrence. No separate Opportunity table
exists, and a test asserts no table name contains `opportunity`. ROI stays derived
and belongs to later reporting.

### Criticality

`CRITICAL`, `HIGH`, `MEDIUM`, `MONITORING` — the four Prompt Mestre §10 levels
(🔴 Crítico, 🟠 Alto, 🟡 Médio, 🟢 Monitoramento). §10 forbids a parallel scale, and
an inverse test asserts the TON enum module declares nothing named `severity`,
`priority` or `urgency`.

**No percentage threshold is encoded.** The ≥1%, 0.3–1% and 0.1–0.3% bands stay
`ton_rule_version.severity_mapping` data requiring owner approval.
`escalate_by_cycle_rule__no_commit` applies a criticality the caller determined and
records why; it does not decide *when* to escalate.

### Critical closure

`ck_ton_occurrence_critical_requires_human_closure` makes `requires_human_closure`
true whenever `criticality = 'CRITICAL'`. `apply_transition__no_commit` then refuses
a plain `RESOLVED` on such a case, so the only route to a closed status is
`RESOLVE_CRITICAL` — which the event table forces to carry an identified user and an
authorization reference. Escalating to `CRITICAL` also sets the flag, so TON removes
its own ability to close the case it just escalated.

## Deduplication and recurrence

`record_detection__no_commit` produces exactly one of four deterministic outcomes.

| Outcome | Condition | Effect |
|---|---|---|
| `NEW` | no case carries this lineage | create occurrence + finding, append `DETECT` |
| `REPEATED` | the case is open | new finding on the **same** occurrence, bump `detection_count` and `last_detected_at`, append `REPEAT_DETECTED` |
| `REOPENED` | closed, policy `REOPEN_SAME_OCCURRENCE` | append `REOPENED`, increment `open_cycle_count`, clear `resolved_at` |
| `SUPERSEDED` | closed, policy `SUPERSEDE_WITH_NEW_OCCURRENCE` **or** a changed rule version | close the old case with `SUPERSEDE`, link it, open generation *n+1* |

The absence of a detection produces nothing at all. No finding is created to
represent a case not recurring; a verification event is how absence is recorded, and
a named test asserts the finding count does not move.

### Post-resolution policy

`RuleVersion.post_resolution_policy` is NOT NULL with no default and no server
default — asserted by test. The executor never chooses silently.

**Forced supersede.** `resolve_post_resolution_policy` returns
`SUPERSEDE_WITH_NEW_OCCURRENCE` whenever the version detecting the recurrence
differs from the version attributed to the resolved case, whatever the policy says.
Two detections measured against different thresholds are not the same measurement —
the same comparability principle as rule S9. Tested with a rule version that
declares `REOPEN_SAME_OCCURRENCE` and is overridden anyway, plus a control that the
unchanged version does honour its policy.

### Concurrency

`_insert_occurrence_if_absent` uses `INSERT … ON CONFLICT DO NOTHING` on
`identity_key`, then re-reads. Concurrency-safe without a lock: the loser blocks on
the winner's row lock, `DO NOTHING` writes nothing, and the following `SELECT` — a
fresh READ COMMITTED snapshot — reads the committed winner.

**Tested with genuine concurrency.** Two threads, two connections, two
transactions, released together by a `threading.Barrier`. A sequential test would
prove nothing here, because one worker would simply finish first and the race would
never happen. Result: one occurrence row, two findings (one per run),
`detection_count = 2`, a `DETECT` followed by a `REPEAT_DETECTED`, both workers
holding the same occurrence id, and exactly one of them reporting `NEW`. The stored
projection matches the event history.

## OccurrenceEvent implementation

The authoritative append-only lifecycle history. `sequence_no` gives one canonical
replay order per case, independent of clock skew between workers, and
`uq_ton_occurrence_event_sequence` enforces it.

Each event carries `transition`, `resulting_status`, `actor_kind`, `actor_user_id`,
`authorization_reference`, `reason`, `context`, `finding_id`, `rule_version_id` and
`occurred_at`.

### The transition vocabulary

Fourteen members in three authorization classes. A test asserts the three classes
**partition** the vocabulary, so no transition can be authorized by omission.

| Class | Members | Requirement |
|---|---|---|
| System-allowed | `DETECT`, `REPEAT_DETECTED`, `REOPENED`, `ESCALATE_BY_CYCLE_RULE`, `VERIFICATION_PASSED`, `VERIFICATION_FAILED`, `SUPERSEDE` | none — §12.1 lets TON read, test, calculate, classify, draft, alert and write to the ledger |
| Requires an identified user | `RESOLVED` | `actor_kind = USER` + `actor_user_id` |
| Human-only | `RESOLVE_CRITICAL`, `ACCEPT_RISK`, `DISMISS`, `ASSERT_NONCOMPLIANCE`, `PROMOTE_INTERPRETATION`, `OVERRIDE_DETERMINISTIC_VALUE` | `actor_kind = USER` + `actor_user_id` + `authorization_reference` |

`RESOLVED` needs a person because closing a case is absent from §12.1's autonomous
list. It does not need a separate authorization record; a critical case does, and
must go through `RESOLVE_CRITICAL`.

### Human-only transitions are structural

Three CHECK constraints, so the boundary survives a writer that never calls the
domain module:

- `ck_ton_occurrence_event_human_only_transitions` — readiness §9, verbatim;
- `ck_ton_occurrence_event_resolution_requires_user`;
- `ck_ton_occurrence_event_user_actor_identified` — a `USER` actor is always
  identified, so `SYSTEM` cannot masquerade as a person.

Tested at both layers: the domain function raises for each of the six with a
`SYSTEM` actor and for each without an authorization reference, **and** a
hand-written `DISMISS` event with `actor_kind = SYSTEM` is rejected by the database.

### One deliberate exception to the SET NULL convention

`ton_occurrence_event.actor_user_id` uses **`ON DELETE RESTRICT`**. Every other user
reference in 003c uses `SET NULL`, matching 003b.

The reason: the readiness §9 CHECK requires the column to be non-null for an
authorized decision, and Onyx hard-deletes `User` rows through
`delete_user_from_db`. `SET NULL` would silently void that guarantee the first time
an account was deleted. An account that authorized a human-only TON decision
therefore stays referenceable.

**Operational consequence**: hard-deleting such an account fails with a foreign-key
violation. Deactivate the account instead. This is recorded rather than worked
around, because an authorization nobody can attribute is not an authorization.

### Projection honesty

`Occurrence.status`, `detection_count`, `open_cycle_count` and `resolved_at` are
cached projections. `apply_transition__no_commit` is the only writer, and it appends
the event and updates the projection in one call, so the two cannot drift.

`project_from_events` recomputes the projection from history alone and reads no
occurrence column, so it cannot be fooled by a drifted projection.
`projection_matches_history` compares them, and it is asserted after create,
repeat, resolve, reopen, supersede, escalate and the concurrency race.

The definitions:

- `detection_count` counts every event that carries a finding — `DETECT`,
  `REPEAT_DETECTED`, `REOPENED`;
- `open_cycle_count` counts `DETECT` and `REOPENED`, so two repeats inside one open
  cycle are not two cycles. This is what makes §10's "🟠 open two cycles → 🔴 on the
  third" expressible;
- `resolved_at` is set by a resolving transition and cleared by `REOPENED`;
- `status` is `TRANSITION_RESULTING_STATUS.get(transition, unchanged)`.

An escalation and a verification record real history without moving the status. A
test asserts every `OccurrenceStatus` member is produced by some transition — a
status nothing produces would be a projection the history cannot explain.

### Status vocabulary

`NEW`, `REOPENED`, `CONFIRMED`, `RESOLVED`, `RISK_ACCEPTED`, `DISMISSED`,
`SUPERSEDED`. `OPEN_STATUSES` and `CLOSED_STATUSES` partition it, asserted by test.

## OccurrenceImpact implementation

The readiness §9 contract: `occurrence_id`, `category`, `confidence`, `method`,
`unit_cost_source`, `predicted_amount`, `realized_amount`, `quantity`,
`quantity_unit`, `unit_cost`, `currency`, `scale`, `verified_at`, `verified_by`,
`premise`, `sensitivity_pct`, `period_start`, `period_end`.

Several rows per occurrence are expected — a monthly and an annual view, a predicted
and a later verified figure — which is why the period is scoped on the row rather
than duplicated as columns.

Vocabularies, all from §9:

- `ImpactCategory` — the seven Dinheiro Escondido columns;
- `ImpactConfidence` — `ALTA`, `MEDIA`, `BAIXA`. Portuguese, because readiness §13
  states the ROI rule as `confidence <> 'BAIXA'`; keeping the literal identical
  means the aggregation rule and the stored value cannot drift;
- `UnitCostSource` — the three preference-order members plus `NOT_APPLICABLE`;
- `ImpactMethod` — executor-defined, in the same position as
  `AnalysisRunErrorClass`: readiness fixes the §9 formula and leaves the rest open.

`unit_cost_source` is NOT NULL because §9 says "diga sempre qual usou", and
`ck_ton_occurrence_impact_unit_cost_source_required` refuses `NOT_APPLICABLE` for
the §9 formula itself — so the escape hatch cannot be used to avoid naming a real
reference cost. Enforced at both layers.

### Numeric safety

One module constant, `TON_AMOUNT = Numeric(30, 10, asdecimal=True)`, plus
`TON_PERCENT = Numeric(9, 4, asdecimal=True)` for percentages. `asdecimal=True` is
stated rather than relied on.

This is deliberately **not** the existing `Numeric(18, 6, asdecimal=False)`
token-cost pattern, which returns a `float`. Every write function raises `TypeError`
on a `float` argument rather than coercing it.

Verified against the built schema, not the annotations: nine named amount columns
are `numeric`, and an inverse assertion rejects `double precision` or `real` on any
of the twenty-one TON tables. A round-trip test stores `1234567.8901234567` and
reads back the identical `Decimal`; another stores `0.3` and asserts it does not
equal `Decimal(str(0.1 + 0.2))`. A third asserts
`quantity * unit_cost == predicted_amount` after a database round trip.

At the serialisation boundary the decimal-string contract 003d needs stays
available: `Finding` and `OccurrenceImpact` carry explicit `value_scale`/`scale`,
`value_unit`/`quantity_unit` and currency metadata, and
`FindingEvidence.extracted_value` is already a decimal string.

### Verification and ROI

`ck_ton_occurrence_impact_realized_requires_verification` makes §13.3 structural:
only a verified saving is realised. `verify_impact__no_commit` sets the realised
amount and its stamp together and leaves the prediction untouched, so a later report
can show forecast error rather than quietly replacing the estimate.

**No ROI table exists**, asserted over the metadata. `ROI_ELIGIBLE_CONFIDENCE` and
`is_roi_eligible` state the §9 rule — verified, realised, not `BAIXA` — as the single
definition the Plan 006 aggregation will read. A low-confidence impact stays fully
representable in the ledger; it is excluded from ROI, not suppressed. A test records
four rows and asserts exactly two are eligible.

## Assignment, note and impacted-domain implementation

**`OccurrenceAssignment`** preserves history. `assign_responsible__no_commit`
appends a new row and stamps the previous open one `SUPERSEDED` with a timestamp;
the current assignment is the highest `sequence_no`. A test asserts the *first*
deadline and responsible label survive a reassignment, which is what §10 escalation
and §12 R9 need. `responsible_label` is required and free text, and
`responsible_user_id` is optional: a §11 blind spot is published with a named field
owner who may hold no Onyx account. No HR integration and no directory lookup
exists.

**`OccurrenceNote`** is append-only — no edit, no delete — with its own
`redaction_level` because a note may carry PII. It inherits the occurrence ACL, has
no permissive visibility column, and `onyx/db/ton/acl.py` is the only read path.

**`OccurrenceImpactedDomain`** supports the §15 handoff rule. One domain owns the
case; the others are listed. `set_impacted_domains__no_commit` refuses the owning
domain — it is already `Occurrence.owning_domain`, and listing it here would make
"who owns this" answerable two ways. A test records two impacted domains and asserts
there is still exactly one occurrence, not three.

## Identity key

The 003b contract is consumed **unchanged**: `validate_identity_components` and
`IDENTITY_COMPONENT_ORDER` are untouched, and no member was added, removed or
reordered. 003c adds the digest on top.

`compute_identity_key` returns `ton-id-1:<sha256 hex>` over
`canonical_identity_payload`. The scheme prefix means a future canonicalisation
change breaks recurrence *visibly* — every case starts a new lineage — rather than
silently rematching cases under new rules.

Canonicalisation, per readiness §7:

- Unicode NFC (tested with decomposed versus precomposed `ó`);
- trimmed;
- case-folded for the declared case-insensitive components;
- emitted in the declared canonical order (tested: shuffling the declaration
  produces the same key);
- `name=value` pairs joined by `\x1f`, the ASCII unit separator — a printable
  separator could appear inside a source record key and let two different tuples
  serialise identically. A test asserts that swapping two values between components
  changes the digest;
- an absent or blank-after-trim component is **omitted**, never emitted as an empty
  string, so "no contract" and "contract ''" cannot be two different cases.

`rule_code` is always emitted first, whether or not the rule version declared it,
and `rule_version` never appears — asserted over the payload. Including the version
would reset recurrence tracking on every open case at each threshold change.

**Case-insensitivity is declared explicitly**, because readiness requires
"components declared case-insensitive" and leaves the declaration to the executor:

| Case-folded | Preserved |
|---|---|
| `rule_code`, `business_unit_id`, `contract_id`, `nature_group`, `source_system` | `source_record_key`, `vehicle_key`, `supplier_key`, `employee_key_masked`, `period` |

The folded set is the controlled internal codes. Erring towards case-sensitive is
the safe direction: it can only ever split one case into two, never merge two
distinct source records into one.

**No LLM text can reach the digest.** The function takes no title, no description
and no interpretation, and a test asserts no such parameter exists. An undeclared
dimension value is refused, and a dimension outside the closed vocabulary is
refused — the guard that stops an LLM-proposed identity dimension entering the
domain. `identity_key` is unchanged after the title, the criticality and the NC code
all change.

## Permission tokens

Two, added to the existing `Permission` enum. Because it is `native_enum=False`,
this needs no migration.

| Token | Value |
|---|---|
| `READ_TON_OCCURRENCES` | `read:ton_occurrences` |
| `MANAGE_TON_OCCURRENCES` | `manage:ton_occurrences` |

Both have `PERMISSION_REGISTRY` entries in group 4, so the existing Groups and RBAC
administration can grant them. `MANAGE_TON_OCCURRENCES` implies
`READ_TON_OCCURRENCES`, matching the existing `MANAGE_AGENTS → READ_AGENTS`
convention.

**Only the 003c tokens are added.** `READ_TON_REPORTS` and `MANAGE_TON_REPORTS`
wait for 003d, and a test asserts no TON token contains `report`. No role was added
and `UserRole` is untouched. No frontend change was needed: the admin section types
`permissions` as `string[]` and falls back to a generic icon.

### The scoped-authority decision

Readiness §10 fixes this only for `MANAGE_TON_RULES` and leaves the occurrence
tokens open, so the decision is recorded here and tested.

**No TON token joins `SCOPED_MANAGER_PERMISSIONS`.** Group-manager scope is a
different axis from a TON share level. Overlapping them would let managing a group
confer authority over financial cases that were merely shared with that group, which
is not what a manager was granted. Resource-level authority comes from the
`*__UserGroup` junctions instead. A test asserts it for every TON token against both
the bundle and its expansion, and separately asserts the
`MANAGE → READ` implication does not leak into the expanded bundle.

The resulting model supports all three required layers without a second framework:

| Caller | Read | Write | Delete |
|---|---|---|---|
| global administrator | every row | every row | yes |
| group holding `READ_TON_OCCURRENCES` | shared rows | no | no |
| group holding `MANAGE_TON_OCCURRENCES` | shared rows | EDITOR rows | EDITOR rows |
| group manager, no TON token | nothing | nothing | no |
| zero junction rows | **denied** | **denied** | denied |

## ACL implementation

`backend/onyx/db/ton/acl.py`, in the Community tree. It composes the Plan 008a
primitives — `Permission`, `PermissionGrant`, `UserGroup`, `has_global_permission`,
`assert_global`, `within_managed_scope_clause` — and adds one resource-scope
predicate. No second authorization system.

### Fail-closed default

For a TON resource the junction is **authorizing**, not restricting. No clause has
an `is_public` branch, and no TON table has such a column, so the `Persona`
short-circuit — where `is_public` defaults to true and bypasses the whole group ACL
— is not merely disabled, it is inexpressible.

Evidence: `test_zero_junction_rows_denies_a_permitted_group` differs from
`test_one_junction_row_is_what_grants_access` only by the presence of one junction
row. Same actors, same token, same case. Also asserted for findings and evidence.

### Admin bypass

`is_ton_administrator` uses
`has_global_permission(user, Permission.FULL_ADMIN_PANEL_ACCESS)`, never
`has_permission`. A scoped group manager can therefore never trigger it, asserted
directly.

Holding `MANAGE_TON_OCCURRENCES` is a capability, **not** company-wide sight. If it
bypassed the ACL, granting a group the ability to manage its own occurrences would
hand it every other unit's as well. A test asserts a token-holding group reads
nothing without a junction row.

### Read filtering

`within_managed_scope_clause` is reused for the editable predicate with
`non_public_clause = sa.true()` — a TON resource is always non-public — and the
caller's own groups as the managed set. Its guarantee is the one that matters: in at
least one of those groups, and in **no** group outside them. So a case shared with a
group the caller cannot reach is not editable by them, and editing cannot become a
route to widening. An EDITOR junction row is required on top, because a VIEWER share
reads and nothing more.

Visibility is a conjunction: the occurrence junction **and** authorization for the
owning business unit when the case names one **and** for the contract when it names
one. That is the organizational context readiness §10 attaches to
`business_unit_id`, and it makes cross-unit denial hold even if an occurrence
junction row were created by mistake.

Every list helper applies the filter, and every helper returns `[]` for a caller
without the capability token.

### Direct-id lookups

`get_occurrence_for_user`, `get_finding_for_user` and
`get_finding_evidence_for_user` apply the **same** predicate as their list
counterparts, and raise the same error whether the row is absent or merely
forbidden — telling a caller that a case exists but is not theirs already leaks the
case. Every denial case asserts both paths.

### Write authorization

`assert_can_manage_occurrence` re-reads the current group relationships **inside the
transaction** with `FOR UPDATE` on the junction rows, and never trusts group ids
from the request. A dedicated test supplies a request state that *would* be within
scope and is refused because the stored state is not.

`set_occurrence_groups__no_commit` additionally refuses a non-administrator who
tries to attach a group they do not belong to, and refuses one who tries to remove
the last authorization — that would hide the case behind the fail-closed default and
lose their own access.

### Delete authorization

`assert_can_delete_occurrence` is the strictest gate: `assert_global` first, as
readiness §10 correction 5 requires, then the resource write gate for anyone who is
not an administrator. `assert_global` alone excludes a scoped manager but would let
a token-holding group destroy a case it could not read, and deleting a case cascades
its findings, events, impacts, assignments and notes. Tested for an administrator, a
group manager, a plain member, a VIEWER, a token holder out of scope, and a token
holder in scope.

Business-unit and contract authorizations are global-only: a unit's authorization
list decides who can see every case in that unit, so widening it is an
organizational act rather than a case-level one.

### Cross-scope denial

All five required cases are named tests: unit A cannot read a unit B occurrence; an
HR-scoped group cannot read a financial occurrence; contract access alone does not
imply occurrence access; group membership alone is not management authority; zero
junction rows denies. Differentiated sensitivity comes from which groups appear on
the junction, not from a second classification system.

### Community-tree regression

The readiness §10 trap: `onyx/db/persona.py`'s CE `update_persona_access` raises
`NotImplementedError("Onyx MIT does not support group-based sharing")`. Copying that
split for TON would be worse than a missing feature — with the fail-closed default,
a CE-resolved worker would write no junction rows and every TON resource would
silently become invisible.

Four tests close it: an ACL write and an ACL read both succeed with
`global_version.unset_ee()` and the dispatch cache cleared; the module resolves under
`onyx.db.ton`; and an `ast` walk over the module asserts it references no
`is_ee_version`, `global_version`, `fetch_versioned_implementation`,
`NotImplementedError`, `check_license` or `get_license`. No licence and no tier is
required anywhere.

## Constraints

| Constraint | Table | Guarantee |
|---|---|---|
| `identity_key` UNIQUE | `ton_occurrence` | the deduplication boundary |
| `uq_ton_occurrence_lineage_generation` | `ton_occurrence` | one row per lineage generation |
| `ck_ton_occurrence_first_generation_identity` | `ton_occurrence` | generation 1 carries the pure canonical digest |
| `ck_ton_occurrence_critical_requires_human_closure` | `ton_occurrence` | TON cannot close a critical case |
| `ck_ton_occurrence_resolved_requires_timestamp` | `ton_occurrence` | a resolved case says when |
| `ck_ton_occurrence_no_self_supersede` | `ton_occurrence` | a case cannot supersede itself |
| `ck_ton_occurrence_detection_order` | `ton_occurrence` | detection timestamps cannot run backwards |
| `uq_ton_finding_run_rule_version_identity` | `ton_finding` | a retry inside one analysis is idempotent |
| `ck_ton_occurrence_event_human_only_transitions` | `ton_occurrence_event` | readiness §9, verbatim |
| `ck_ton_occurrence_event_resolution_requires_user` | `ton_occurrence_event` | closing a case needs a person |
| `ck_ton_occurrence_event_user_actor_identified` | `ton_occurrence_event` | SYSTEM cannot pose as a person |
| `uq_ton_occurrence_event_sequence` | `ton_occurrence_event` | one canonical replay order |
| `ck_ton_finding_interpretation_completed_has_summary` | `ton_finding_interpretation` | no empty successful interpretation |
| `ck_ton_finding_interpretation_completed_has_provenance` | `ton_finding_interpretation` | a result names its provider and model |
| `ck_ton_finding_interpretation_failed_has_class` | `ton_finding_interpretation` | a failure names its class |
| `ck_ton_finding_interpretation_class_only_on_failure` | `ton_finding_interpretation` | only a failure carries one |
| `uq_ton_finding_interpretation_attempt` | `ton_finding_interpretation` | one row per attempt |
| `ck_ton_occurrence_impact_realized_requires_verification` | `ton_occurrence_impact` | §13.3: only verified savings are realised |
| `ck_ton_occurrence_impact_has_an_amount` | `ton_occurrence_impact` | an impact row carries a number |
| `ck_ton_occurrence_impact_unit_cost_source_required` | `ton_occurrence_impact` | §9's formula names a real reference cost |
| `ck_ton_occurrence_assignment_completed_has_timestamp` | `ton_occurrence_assignment` | a closed assignment says when |

`ON DELETE` decisions, all asserted by test:

- **RESTRICT** where deletion would break the audit chain — the run and rule version
  behind a finding, the rule and version behind an occurrence, a snapshot cited by
  evidence, and `ton_occurrence_event.actor_user_id`;
- **CASCADE** where the child has no independent meaning — everything under an
  occurrence, evidence and interpretations under a finding, and both sides of every
  junction;
- **SET NULL** for a provenance-only user reference and for the Onyx storage links.

A companion test asserts the TON foreign-key set is *exactly* the expected list, so
a foreign key added without a recorded `ondelete` decision fails.

## Money and numeric types

Covered under OccurrenceImpact above. In summary: `Numeric(30, 10, asdecimal=True)`
throughout, `float` refused at every write boundary, no `double precision` anywhere
in the TON schema, and the token-cost `asdecimal=False` pattern deliberately not
reused.

## No-seed decision

The migration creates schema only. It inserts **zero** rows in all twelve tables,
asserted per table and again per junction on a freshly migrated database.

No Prompt Mestre value becomes production configuration: no criticality percentage,
no NC mapping, no deadline, no payroll band, no travel limit, no budget count, no
publication ceiling, no S-rule and no T-rule value. Criticality bands stay
`ton_rule_version.severity_mapping` data, and 003b's
`ck_ton_rule_version_active_requires_approval` still makes an accidental activation
impossible.

Test fixtures use obviously synthetic values (`SYN-RULE-…`, `SYN-UNIT-…`,
`SYN-ATA-…`, `synthetic_…`, currency `XTS`) so no real code or figure exists anywhere
in the slice.

## Tests and evidence

| Suite | Command | Result |
|---|---|---|
| Repository migration gate | `pytest tests/integration/tests/migrations/` | 15 passed, 1 skipped |
| TON schema spec | `pytest tests/external_dependency_unit/ton/test_domain_schema.py` | 94 passed |
| Occurrence lifecycle spec | `pytest tests/external_dependency_unit/ton/test_occurrence_lifecycle.py` | 46 passed |
| Interpretation lifecycle spec | `pytest tests/external_dependency_unit/ton/test_interpretation_lifecycle.py` | 28 passed |
| ACL spec | `pytest tests/external_dependency_unit/ton/test_ton_acl.py` | 42 passed |
| Impact / assignment / note spec | `pytest tests/external_dependency_unit/ton/test_occurrence_impact.py` | 33 passed |
| Whole TON external-dependency directory | `pytest tests/external_dependency_unit/ton` | 305 passed |
| Pure-domain spec | `pytest tests/unit/ton` | 455 passed, 1 pre-existing failure |
| Both TON directories together | `pytest tests/external_dependency_unit/ton tests/unit/ton` | 760 passed, 1 pre-existing failure |
| Authorization regression | scoped permissions, permission projection, permission recompute, agent group sharing | 76 passed |
| 008a / 003a / 003b regression | `test_group_capability.py`, `test_provider_secret_encryption.py` | 25 passed |
| Permission and auth unit regression | `test_permissions.py`, `test_scoped_pat_route_gate.py`, `tests/unit/ton`, `test_assign_default_groups.py` | 531 passed, 1 pre-existing failure |

New files:

- `backend/tests/external_dependency_unit/ton/test_occurrence_lifecycle.py`
- `backend/tests/external_dependency_unit/ton/test_interpretation_lifecycle.py`
- `backend/tests/external_dependency_unit/ton/test_ton_acl.py`
- `backend/tests/external_dependency_unit/ton/test_occurrence_impact.py`
- `backend/tests/unit/ton/test_occurrence_projection.py`

Extended: `test_domain_schema.py`, `scratch_db.py`, `factories.py`,
`tests/unit/ton/test_rule_versioning.py`.

`ruff check`, `ruff format --check` and `ty check` are clean on every touched file.
`alembic check` was not used as a gate and `alembic -n schema_private upgrade head`
was not run — readiness §17.3 proved both inappropriate for this deployment.

### The pre-existing failure

`tests/unit/ton/test_contract_matrix.py::test_vale_norte_report_remains_candidate_evidence`
fails at the baseline commit and after this slice, identically. It reads
`plans/ton/decision-log.md` while the file is at
`plans/ton/backend/decision-log.md` — the path drift already recorded in the 003a
and 003b results. No file it touches was changed here.

### Placement, and why it differs from readiness §20

Readiness §20 suggested `backend/tests/integration/ton/`. 003c adds no HTTP surface,
and every test in `backend/tests/integration` runs against a deployed Onyx through
its API. These are therefore external-dependency unit tests: real PostgreSQL,
functions called directly, which is what `backend/AGENTS.md` describes for exactly
this case. The API-level tests arrive with the API.

`scratch_db.py` builds a template database from the repository migrations once per
session and clones it per test, so every assertion runs on a throwaway database.

### Verification environment

The deployment PostgreSQL container publishes no host port, so it is unreachable
from the host and could not be mutated even by accident. All database work ran
against a disposable `postgres:15.2-alpine` container on host port 55432, removed
afterwards.

One environment note worth recording: on a Windows host,
`tests/integration/tests/migrations/test_run_multitenant_migrations.py` fails with
`UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'` because
`alembic/run_multitenant_migrations.py` prints a ✓ to a cp1252 stdout. Setting
`PYTHONUTF8=1` makes the directory report 15 passed, 1 skipped — matching 003b. The
failure is a console-encoding artifact of the host, not a migration defect, and the
same run reported the head as `6b0ca4eb29fb` correctly.

## Operational migration note

**The running development database was not migrated.** It remains at
`ad99acb9be41`, one revision behind 003a and three behind 003c.

Applying 003c to a real deployment requires 003a's operational steps first, since
003a is an ancestor:

1. Inject `ENCRYPTION_KEY_SECRET` for the api_server, the workers and the process
   that runs `alembic upgrade`, using the same value.
2. Confirm EE resolution is active in the migrating process. The default
   `LICENSE_ENFORCEMENT_ENABLED=true` already satisfies this; no licence is needed.
3. Take a database backup. 003a's downgrade cannot restore provider configuration
   values.
4. Apply the migrations from `backend/`:

   ```bash
   cd backend
   uv run alembic upgrade head
   ```

5. Restart the application processes together with the upgrade.

003c itself needs no key, no licence and no data transition: it only adds empty
tables and one sequence. Its downgrade is `alembic downgrade faee7eaa921e` and drops
exactly the twelve TON tables and the sequence.

One operational rule this slice introduces: an account that authorized a human-only
TON transition cannot be hard-deleted, because
`ton_occurrence_event.actor_user_id` is `RESTRICT`. Deactivate such an account
instead.

## Boundaries

| Slice | Owns | Not touched here |
|---|---|---|
| **003d** | TonReport, TonReportRevision, the report join tables, `TonReport__UserGroup`, TonAuditEvent, and the `ton-canon-1` canonicalisation | no such table exists after 003c, asserted by name and by substring; existing stdout audit emission is unchanged |
| **Plan 004** | ingestion — PDF and Excel parsing, MarkItDown, normalization, NG/Keevo, import jobs | `SourceSnapshot` and `FindingEvidence` establish the provenance contract only |
| **Plan 005** | agents — TON Central, CFO, COO, Frota, Contratos, Auditor, RH, supervisor, handoffs, prompts, real provider calls | the interpretation lifecycle primitives are transactional only; no provider is contacted |
| **Plan 006** | schedules — R1–R9, Celery Beat, alerts, recurring analysis, publication ceilings | nothing here caps detection or schedules a run |
| **Frontend** | FE-004, VIS-000+, occurrence UI, report UI, agent UI | no file under `web/`, `desktop/` or `mobile/` was changed |
| **HTTP contract** | endpoint naming stays open (readiness §22) | no route, no `APIRouter`, no `/api/ton/occurrences`; asserted by test |

### Future API requirements, documented not implemented

Readiness §22 leaves endpoint naming open, so 003c invents none. What the data layer
already supports for TON-FE-008: server-side pagination with a stable
`(last_detected_at, id)` order; filters on status, criticality, domain, business
unit, contract and `ledger_kind`, all indexed; a detail read that applies the same
predicate as the list; `OccurrenceEvent` history; `FindingEvidence` with its
confidence level and locator; per-row share level through `user_share_permission`
so a UI can hide an edit affordance while the backend still refuses a direct call;
and decimal-string-capable impact values with currency, scale and confidence.

## Prerequisites for 003d

1. Chain from `6b0ca4eb29fb`, one new revision, one head after it.
2. Create `TonReport`, `TonReportRevision`, the five `TonReportRevision__*` join
   tables, `TonAuditEvent` — **and** `TonReport__UserGroup`, the fourth junction
   this slice deliberately deferred.
3. Add `READ_TON_REPORTS` and `MANAGE_TON_REPORTS` with `PERMISSION_REGISTRY`
   entries. Keep them out of `SCOPED_MANAGER_PERMISSIONS`, as every TON token is.
4. Reuse `onyx/db/ton/acl.py` for the report ACL rather than writing a second one.
   The fail-closed rule, the `FULL_ADMIN_PANEL_ACCESS` bypass and the
   `within_managed_scope_clause` usage all transfer unchanged.
5. Implement `ton-canon-1` per readiness §12, and populate
   `RuleVersion.definition_hash`, which 003b left nullable for exactly this reason.
6. A report revision must refuse a finding whose `interpretation_status` is not
   `COMPLETED` or `NOT_REQUIRED`. `interpretations.is_interpretation_final` is the
   predicate to call.
7. Monetary values serialise as decimal strings at the declared scale.
   `TON_AMOUNT` columns already return `Decimal`, and
   `FindingEvidence.extracted_value` is already a string.
8. `TonAuditEvent` is best-effort and must never raise into the caller. Domain
   history — `Finding`, `FindingInterpretation`, `OccurrenceEvent`,
   `OccurrenceAssignment`, `OccurrenceNote` — stays transactional and must raise.
   Store a reference to a domain row, never a copy of its payload.
9. Keep every TON table free of `is_public`. The inverse assertions in
   `test_domain_schema.py` and `test_occurrence_projection.py` need extending to the
   new tables, and `TON_TABLES_AT_HEAD` in `scratch_db.py` needs the 003d list.
10. Reuse `scratch_db.py` and the `ton_session` fixture. Do not point TON DB tests
    at the deployment database.
11. Business rule values remain unapproved. 003d must seed nothing either.

## Confirmations

- Zero rows are seeded in all twelve tables, asserted per table on a freshly
  migrated database.
- No `TonReport`, `TonReportRevision`, `TonReport__UserGroup` or `TonAuditEvent`
  table or model was created, asserted by name and by substring. Existing stdout
  audit emission is unchanged.
- No real LLM or provider call was implemented. `onyx/db/ton/` imports no LiteLLM,
  opens no socket and contains no prompt text; the interpretation tests inject a
  fake boundary that raises.
- No agent, prompt, handoff or supervisor was implemented, and a test asserts no
  such module exists in the TON package.
- No ingestion, parsing, normalization or NG/Keevo work occurred.
- No scheduler, Celery Beat entry or alert was added.
- No HTTP route was added, asserted by test over the whole TON package.
- No frontend file was changed.
- No write path to any source system exists. No column name in the twenty-one TON
  tables contains `glosa`, `erp_write`, `billing_write`, `measurement_write`,
  `push_to_` or `sync_to_`.
- No TON table has `is_public`, `public`, `is_global` or `public_permission`.
- No TON column is `double precision` or `real`.
- No commercial tier, licence or Enterprise Edition code path is required.
- The running development database was not migrated, stamped, downgraded or
  repaired. It is not reachable from the host.
- No existing table was altered or deleted.
- No business value from the Prompt Mestre or the Vale Norte report appears in any
  changed file.
