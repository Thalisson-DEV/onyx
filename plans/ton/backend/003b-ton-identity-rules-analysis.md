# Plan 003b — TON identity, rules and analysis core

> **Executor instructions**: This is the first TON-owned domain schema, split out
> of Plan 003 by `003-readiness.md` §21. It chains from 003a and creates no
> Finding, Occurrence, report or audit table.
>
> **Drift check (run first)**: `git status --short`. Then read the current
> main-chain head from `backend/alembic/versions` — take the revision no other
> file names as `down_revision`. Do not hardcode a head.

## Status

- **State**: DONE
- **Priority**: P1
- **Effort**: L
- **Risk**: MEDIUM (nine new tables; no existing table is altered)
- **Depends on**: `003-readiness.md`, `003a-provider-secret-encryption.md`,
  `008a-capability-gates.md`
- **Blocks**: `003c` uses this revision as its `down_revision`
- **Category**: direction
- **Baseline commit**: `fc6b252baea03793636b33c4d7464bf16384152d` (`main`)
- **Executed at**: 2026-09-15

## Issues to Address

TON had no first-class organizational identity, no versioned rule definition and
no execution envelope. Without them a threshold change silently reinterprets
history, a retried run duplicates itself, and a failure in one domain cannot be
distinguished from a failure of the whole analysis.

The last item is the original TON defect. Prompt Mestre §5 says a failed step
blocks the following ones. Read literally in software, one failed financial base
validation would silence fleet, contracts and HR, and one failed unit would
silence every other unit. This slice makes that outcome structurally
unreachable.

## Alembic chain

| | |
|---|---|
| Previous head | `714172b66b07` (003a) |
| New revision | `faee7eaa921e` |
| `down_revision` | `714172b66b07` |
| Heads after the change | one (`alembic heads` → `faee7eaa921e`) |

Pre-flight confirmed a single main-chain head across 444 revision files, that
`714172b66b07` is present in the working tree, and that the environment held zero
TON tables.

## Schema introduced

Nine tables, all prefixed `ton_`. The prefix is deliberate: this checkout tracks
`upstream/main`, `rule`, `contract` and `business_unit` are names upstream could
plausibly take in the shared `public` schema, and the prefix matches the
`TonReport` naming the readiness gate already uses for 003d. Class names follow
the readiness names.

| Table | Purpose |
|---|---|
| `ton_business_unit` | stable organizational identity |
| `ton_contract` | contract identity, as far as named rules need it |
| `ton_rule` | the immutable rule spine |
| `ton_rule_version` | versioned, approvable rule configuration |
| `ton_source_snapshot` | provenance receipt for input material |
| `ton_analysis_run` | execution and audit envelope |
| `ton_analysis_run_rule_version` | which rule versions ran, and what became of each |
| `ton_analysis_run__source_snapshot` | which snapshots fed a run |
| `ton_analysis_step` | domain-scoped execution and blocking |

Primary keys are UUIDs with a Python-side `uuid4` default, matching the sixteen
existing UUID-keyed tables. Timestamps are `DateTime(timezone=True)` with
`server_default=func.now()`. JSON is `JSONB`. Enums are
`Enum(..., native_enum=False)`, the repository convention.

Files:

- `backend/onyx/db/ton/__init__.py`
- `backend/onyx/db/ton/enums.py`
- `backend/onyx/db/ton/models.py`
- `backend/onyx/db/ton/identity.py`
- `backend/onyx/db/ton/rule_versions.py`
- `backend/onyx/db/ton/analysis_runs.py`
- `backend/onyx/db/ton/analysis_steps.py`
- `backend/alembic/versions/faee7eaa921e_ton_identity_rules_and_analysis_core.py`

Modified: `backend/onyx/db/enums.py` (three permission tokens),
`backend/onyx/auth/permissions.py` (three registry entries),
`backend/alembic/env.py` (import the TON models so `target_metadata` is
complete — otherwise a future autogenerate would propose dropping them).

Everything sits in the Community tree. No TON behaviour resolves through EE
dispatch or a tier gate.

## BusinessUnit decision

Identity only, per readiness §15: `code` UNIQUE, `name`, `kind`, `is_active`,
`external_ref`, timestamps.

`kind` (`OPERATIONAL`, `IMPLANTATION`, `PROSPECT`, `NON_OPERATIONAL`) is included
now because §3.3's consolidation rule — a non-operational cost centre never
enters a profitability ranking or an inter-municipal benchmark — cannot be
expressed without it.

Excluded: financials, dotação, headcount, fleet sizing.

**No unit is seeded.** The membership of the seven operational, six implantation
and nine non-operational lists still needs owner and source validation. The
schema provides structure only.

## Contract identity decision

Identity only. A §4 field is included only when a named S-rule or T-rule cannot
be expressed without it. Two qualify:

- `status` (`DRAFT`, `BIDDING`, `UNDER_JUDGEMENT`, `SIGNED`, `ACTIVE`,
  `SUSPENDED`, `ENDED`) — rule S7 excludes an unsigned contract from backlog,
  revenue and projection. `UNDER_JUDGEMENT` is the state §6.2 shows going wrong
  when it is absent;
- `start_date` / `end_date` — T19 vigência milestones.

Also present: `code` UNIQUE, `business_unit_id`, `contracting_authority`,
`object_summary`.

Deferred to later ingestion and domain slices: full economics, amendment
economics, fleet sizing, crew sizing, headcount sizing, dotação, BDI, ABC curve,
CCT, guarantees, penalties, detailed measurement, detailed billing.

`object_summary`, `start_date` and `end_date` are nullable. A contract is often
identified before those are captured, and recording the absence is better than
inventing a value.

## Rule and RuleVersion implementation

`Rule` holds `id`, `code` UNIQUE, `domain`, `kind`, `created_at`, `created_by`
and nothing else. A test asserts the column set exactly, so a threshold or a
status cannot drift onto it. There is no `updated_at`: the row is not meant to
change.

`RuleVersion` holds the full readiness §3 contract: `rule_id`, `version`,
`title`, `description`, `executor_key`, `parameters`, `unit`, `currency`,
`scale`, `rounding_mode`, `applicability`, `effective_from`, `effective_to`,
`status`, `source_reference`, `provenance`, `approved_by`, `approved_at`,
`approval_reference`, `missing_data_behavior`, `evidence_requirements`,
`min_confidence_level`, `severity_mapping`, `nc_code`, `identity_components`,
`post_resolution_policy`, `definition_hash`.

`UNIQUE(rule_id, version)` gives the ordered history. Historical consumers
reference `rule_version_id`, so changing a threshold cannot reinterpret a
published number.

Three deliberate choices where readiness left the detail open:

- **`unit`, `currency`, `scale` and `rounding_mode` are plain strings, not
  enums.** Readiness §23 still lists accepted units, currencies, rounding and
  precision as pending owner approval. Freezing a vocabulary in code would turn
  an unresolved business decision into a schema constraint.
- **`min_confidence_level` is NOT NULL with no default.** Every version must
  state its §3.4 confidence floor. There is no approved default to fall back on.
- **`definition_hash` is nullable.** The canonical serialisation (`ton-canon-1`)
  is specified in readiness §12 but implemented in 003d. Writing a hash under a
  different scheme now would make the recorded value meaningless.

`executor_key` is a stable deterministic identifier such as
`deviation_vs_trailing_mean.v1`. It is not a Python import path, not serialised
code and not a prompt. **No deterministic executor is implemented in this
slice** — the canonical plan does not assign them here, and schema and contracts
come first.

## Value vocabularies added

All in `backend/onyx/db/ton/enums.py`. Member name equals member value
throughout, so the CHECK constraints written against literal strings stay correct
whichever storage convention a later reader assumes.

| Enum | Members |
|---|---|
| `RuleDomain` | FINANCIAL, OPERATIONAL, CONTRACT, FLEET, HR, PROCUREMENT, COMPLIANCE, AUDIT, QUALITY |
| `RuleKind` | SANITY, DETECTION, BLIND_SPOT |
| `RuleVersionStatus` | DRAFT, PENDING_APPROVAL, ACTIVE, SUSPENDED, RETIRED, TEST_ONLY |
| `RuleProvenance` | PAD_CTRL_001, PROMPT_MESTRE_V2, VALE_NORTE_REPORT_2026, OWNER_APPROVED, DERIVED |
| `MissingDataBehavior` | BLOCK, FINDING_BLIND_SPOT, SKIP_WITH_NOTE |
| `EvidenceConfidenceLevel` | A, B, C, D |
| `PostResolutionPolicy` | REOPEN_SAME_OCCURRENCE, SUPERSEDE_WITH_NEW_OCCURRENCE |
| `IdentityComponent` | rule_code, business_unit_id, contract_id, period, source_system, source_record_key, nature_group, vehicle_key, supplier_key, employee_key_masked |
| `BusinessUnitKind` | OPERATIONAL, IMPLANTATION, PROSPECT, NON_OPERATIONAL |
| `ContractStatus` | DRAFT, BIDDING, UNDER_JUDGEMENT, SIGNED, ACTIVE, SUSPENDED, ENDED |
| `SourceType` | NG_KEEVO, UPLOADED_SPREADSHEET, CONTRACT_DOCUMENT, DOCUMENT_CHUNK, MANUAL_ENTRY, CALCULATED_AGGREGATE, BANK_STATEMENT, PAYROLL_EXPORT |
| `AnalysisTrigger` | INTERACTIVE, SCHEDULED, BACKFILL, MANUAL_REPLAY |
| `AnalysisSpecialist` | CFO, COO, FLEET, CONTRACTS, COMPLIANCE, PROCUREMENT, HR, AUDITOR, CEO |
| `AnalysisRunStatus` | QUEUED, RUNNING, COMPLETED, COMPLETED_WITH_BLOCKED_DOMAINS, FAILED, TIMED_OUT, CANCELLED |
| `AnalysisRunErrorClass` | MISSING_SOURCE, MISSING_CONTRACT_MASTER, SOURCE_VALIDATION_FAILED, RULE_EXECUTION_ERROR, TIMEOUT, CANCELLED, INTERNAL_ERROR |
| `InterpretationStatus` | NOT_REQUIRED, PENDING, RUNNING, COMPLETED, FAILED |
| `AnalysisStepCode` | INGESTION, BASE_VALIDATION, CHAIN_RECONCILIATION, DETECTION, QUANTIFICATION, PRIORITIZATION, PUBLICATION |
| `AnalysisStepStatus` | PENDING, RUNNING, PASSED, FAILED, BLOCKED, SKIPPED |
| `AnalysisStepBlockedReason` | PREREQUISITE_FAILED, MISSING_SOURCE, MISSING_CONTRACT_MASTER, BASE_REPROVED, AWAITING_HUMAN_DECISION |
| `RuleVersionOutcome` | EXECUTED, SKIPPED_NOT_APPLICABLE, SKIPPED_MISSING_DATA, ERRORED |

The nine specialists map to Prompt Mestre §15 as TON CFO, TON COO, TON FROTA,
TON CONTRATOS, TON COMPLIANCE, TON PROCUREMENT, TON RH, TON AUDITOR and TON CEO.
The mapping is recorded in the enum docstring and pinned by a test.

`AnalysisRunErrorClass` is the one vocabulary readiness left open — §4 asks for a
"safe enum" without fixing its members. It is executor-defined, aligned with
`AnalysisStepBlockedReason`, and carries no message, traceback or source value.

## Constraints

| Constraint | Table | Guarantee |
|---|---|---|
| `ck_ton_rule_version_active_requires_approval` | `ton_rule_version` | `ACTIVE` requires `approved_by` **and** `approved_at`. No unapproved threshold reaches production. |
| `uq_ton_rule_version_rule_version` | `ton_rule_version` | one row per `(rule_id, version)` |
| `ck_ton_rule_version_effective_order` | `ton_rule_version` | an effective range cannot run backwards |
| `ck_ton_rule_version_positive` | `ton_rule_version` | versions start at 1 |
| `ton_rule.code` UNIQUE | `ton_rule` | the stable identifier is unique |
| `ton_analysis_run.idempotency_key` UNIQUE | `ton_analysis_run` | a retry converges instead of duplicating |
| `ck_ton_analysis_run_period_order` | `ton_analysis_run` | competência cannot run backwards |
| `ck_ton_analysis_run_finished_requires_start` | `ton_analysis_run` | a run cannot finish without starting |
| `ck_ton_analysis_run_attempt_positive` | `ton_analysis_run` | attempts start at 1 |
| `ck_ton_analysis_step_blocked_requires_cause` | `ton_analysis_step` | a BLOCKED step always names both the causing step and a reason |
| `ck_ton_analysis_step_no_self_block` | `ton_analysis_step` | a step cannot be its own cause |
| `uq_ton_analysis_step_scope` | `ton_analysis_step` | one row per `(run, step_code, domain, business_unit)`, `NULLS NOT DISTINCT` so the run-wide scope is unique too |
| `ck_ton_analysis_run_rule_version_skipped_has_no_findings` | `ton_analysis_run_rule_version` | a rule that did not execute reports zero findings |
| `ck_ton_contract_date_order`, `ck_ton_source_snapshot_period_order` | — | date ranges cannot run backwards |

`ON DELETE` decisions, all asserted by test:

- `RESTRICT` where deletion would break the audit chain — a business unit that
  still owns contracts, runs or steps; a rule version that took part in a run; a
  source snapshot that fed a run;
- `CASCADE` where the child has no independent meaning — rule versions under a
  rule, steps and links under a run, a blocked step under its cause;
- `SET NULL` for every `user.id` reference, so removing an account never destroys
  domain history.

`uq_ton_analysis_step_scope` needs PostgreSQL 15 or later for
`NULLS NOT DISTINCT`. The deployment runs 15.2 and CI uses
`postgres:15.2-alpine`.

## SourceSnapshot semantics

A receipt for material that was already extracted, not an ETL definition. It
carries `source_type`, `source_system_label`, `extracted_at`, `period_start`,
`period_end`, `units_covered`, `row_count`, `checksum`, `is_complete`,
`missing_inputs`, `is_schema_conformant`, `ingested_by` and `notes`.

Source-agnostic by construction: no NG/Keevo column name, no field mapping, no
transform definition, no scheduling and no parsing. `NG_KEEVO` exists as an enum
member so evidence can be labelled later; the field mapping stays BLOCKED under
D-009.

`is_complete` and `is_schema_conformant` are NOT NULL with no default. Prompt
Mestre §5 Passo 1 requires the caller to state what did not arrive rather than
let completeness be assumed.

Required in this slice, not deferred, for two reasons: without it a report is not
reproducible, and rule S10 is not expressible.

## Domain-scoped blocking

The blocking unit is the triple `(step_code, domain, business_unit_id)`, never
the run. `domain` and `business_unit_id` are nullable and `NULL` means run-wide.

Blocking propagates only from a scope that **contains** the blocked step's scope,
and only forward along the fixed seven-step order.
`onyx.db.ton.analysis_steps.block_step__no_commit` is the single path to
`BLOCKED` and refuses four cases: a cause in a different run, a step blocking
itself, a cause whose scope does not contain the target's, and a cause that is
not upstream in the protocol. A step that already reached a verdict is never
rewritten, so a `PASSED` sibling keeps its result.

`resolve_run_status` rolls the steps up. A run holding both a success and a
failure is `COMPLETED_WITH_BLOCKED_DOMAINS`. Only a run with no successful step
at all is `FAILED`.

Not a workflow engine, and it must not become one. The seven step codes and their
order are fixed by §5; there is no dependency graph to configure, no retry policy
and no dispatch. No LLM participates in blocking — every decision is
deterministic.

S10 is `reprove_base__no_commit`: a reproved `BASE_VALIDATION` blocks
`PUBLICATION` for that domain and unit, with `blocked_reason = BASE_REPROVED`. It
is never a run-wide flag and never an active rule version.

## Permission tokens

Three, added to the existing `Permission` enum. Because it is
`native_enum=False`, this needs no migration.

| Token | Value |
|---|---|
| `READ_TON_ANALYSIS` | `read:ton_analysis` |
| `MANAGE_TON_RULES` | `manage:ton_rules` |
| `MANAGE_TON_BUSINESS_UNITS` | `manage:ton_business_units` |

**Only the 003b tokens are added.** `READ_TON_OCCURRENCES`,
`MANAGE_TON_OCCURRENCES`, `READ_TON_REPORTS` and `MANAGE_TON_REPORTS` wait for
003c and 003d. The canonical plan does not require one registry change, and a
grantable permission whose resource does not exist authorizes nothing while
telling an administrator otherwise. A test asserts no occurrence or report token
appears early.

**`MANAGE_TON_RULES` is not in `SCOPED_MANAGER_PERMISSIONS`.** Approving or
activating a rule version has company-wide effect, so a business-unit manager
must never resolve SCOPED authority for it. A test asserts this for every TON
token, against both the bundle and its expansion.

Each token has a `PERMISSION_REGISTRY` entry so the existing Groups and RBAC
administration can grant it. They form registry group 4. No role was added and
`UserRole` is untouched. **No frontend change was needed**: the admin section
types `permissions` as `string[]`, falls back to a generic icon for an unknown
entry id, and uses `group` only to draw a divider.

## No-seed decision

The migration creates schema only. It inserts **zero** `ton_rule` rows and
**zero** `ton_rule_version` rows, and zero rows in the other seven tables.

No Prompt Mestre threshold becomes production configuration: not 15%, not 3%, not
the 35–45% payroll band, not 48 hours, not five days, not 180/120/90/60 days, no
S-rule and no T-rule value, no NC default, no budget count. Every threshold is
data in `ton_rule_version.parameters`, and
`ck_ton_rule_version_active_requires_approval` makes an accidental activation
impossible.

Rule creation is an explicit, audited admin action. The `977e834c1427` default
group seeding is not a precedent: that is an authorization bootstrap the
deployment cannot function without, and a business rule is not in that category.

Test fixtures use obviously synthetic values (`synthetic_threshold`,
`SYN-RULE-…`, `synthetic_noop_executor.v1`) so no real code or figure exists
anywhere in the slice.

## Fail-closed preparation

No TON table has an `is_public` column — absent, not defaulted false. A column
that does not exist cannot be short-circuited by future code. Two inverse
assertions enforce it: one over the migrated tables in
`information_schema.columns`, one over `Base.metadata`, so a hand-written
migration cannot drift from the models. A second assertion rejects the near
misses `public`, `is_global` and `public_permission`.

The ACL junctions for `BusinessUnit` and `Contract` are assigned to 003c by
readiness §21, together with the occurrence and report junctions. This slice
therefore invents no temporary visibility semantics, and adds no read route that
would need one.

A further inverse assertion checks that no TON column name suggests a write back
into a source system. The advisory boundary of §12.1 is enforced by absence.

## Money and numeric types

**No monetary or quantity column exists in this slice.** Contract economics are
excluded by readiness §15, so none is needed. `Numeric` is not used at all, and
`float`/`double` appear nowhere.

The later decimal-string contract stays possible: `ton_rule_version` carries
`unit`, `currency`, `scale` and `rounding_mode` as explicit metadata, and
threshold values live in `parameters` as decimal strings rather than JSON
numbers, matching readiness §12 rule 1. Report canonicalisation is not
introduced.

## Timestamps and timezone

`DateTime(timezone=True)` with `server_default=func.now()` and `onupdate` where
the row is expected to change, matching the repository convention. No Vale Norte
timezone is baked into the schema. Business competence is explicit —
`period_start` / `period_end` on the run and the snapshot, `effective_from` /
`effective_to` on the rule version — and never derived from server local time.

## Tests and evidence

| Suite | Command | Result |
|---|---|---|
| Repository migration gate | `pytest tests/integration/tests/migrations/` | 15 passed, 1 skipped |
| TON schema spec | `pytest tests/external_dependency_unit/ton/test_domain_schema.py` | 49 passed |
| Analysis behaviour spec | `pytest tests/external_dependency_unit/ton/test_analysis_run.py` | 23 passed |
| Rule lifecycle spec | `pytest tests/external_dependency_unit/ton/test_rule_lifecycle.py` | 14 passed |
| Pure-domain spec | `pytest tests/unit/ton/test_rule_versioning.py` | 92 passed |
| Whole TON external-dependency directory | `pytest tests/external_dependency_unit/ton` | 111 passed |
| Targeted regression | permissions, scoped authorization, 008a capability gates, 003a encryption, rotation | 572 passed, 1 pre-existing failure |

New files:

- `backend/tests/external_dependency_unit/ton/scratch_db.py`
- `backend/tests/external_dependency_unit/ton/conftest.py`
- `backend/tests/external_dependency_unit/ton/factories.py`
- `backend/tests/external_dependency_unit/ton/test_domain_schema.py`
- `backend/tests/external_dependency_unit/ton/test_analysis_run.py`
- `backend/tests/external_dependency_unit/ton/test_rule_lifecycle.py`
- `backend/tests/unit/ton/test_rule_versioning.py`

### Placement, and why it differs from readiness §20

Readiness §20 suggested `backend/tests/integration/ton/`. 003b adds no HTTP
surface, and every test in `backend/tests/integration` runs against a deployed
Onyx through its API. These are therefore external-dependency unit tests: real
PostgreSQL, functions called directly, which is what `backend/AGENTS.md`
describes for exactly this case. The API-level tests arrive with the API.

The shared `db_session` fixture points at the deployment database, which 003a
deliberately left at `ad99acb9be41`. `scratch_db.py` builds a template database
from the repository migrations once per session and clones it per test, so every
assertion runs on a throwaway database. `conftest.py` exposes `ton_database` and
`ton_session`.

### The named anti-defect test

`test_analysis_run.py::TestDomainScopedBlocking::test_failure_blocks_only_its_own_domain_and_unit`
reproduces the readiness §5 worked example. Financial base validation fails in
one unit. The result:

| Step scope | Status |
|---|---|
| `BASE_VALIDATION` / FINANCIAL / unit A | FAILED |
| `CHAIN_RECONCILIATION` … `PUBLICATION` / FINANCIAL / unit A | BLOCKED, `BASE_REPROVED` |
| `DETECTION` / FLEET / unit A | PASSED |
| `DETECTION` / CONTRACT / unit A | PASSED |
| `DETECTION` / HR / unit A | PASSED |
| `DETECTION` / FINANCIAL / unit B | PASSED |
| Run status | `COMPLETED_WITH_BLOCKED_DOMAINS` |

Companion cases assert that full failure still yields `FAILED`, that a run-wide
failure may legitimately block narrower scopes, that a scoped failure never
blocks a run-wide step, that a decided step is never rewritten, and that the API
refuses to block a sibling domain, a sibling unit, an upstream step or another
run.

### Verification environment

The deployment PostgreSQL container publishes no host port
(`{"5432/tcp": null}`), so it is unreachable from the host and could not be
mutated even by accident. All database work ran against a disposable
`postgres:15.2-alpine` container on host port 55432, removed afterwards. The
migration gate was run twice and passed both times on a clean database, matching
the CI condition. One intermediate run of the same directory reported two
`test_up_down_consistency` failures; that run reused a database already populated
by the whole regression suite, and one of the two failures was on the
`alembic_tenants` chain, which this slice does not touch. Recreating the database
and re-running the directory returned 15 passed, 1 skipped.

The
regression comparison ran the unit suites in a `git worktree` at the baseline
commit: 336 passed with the same single failure, against 428 with this slice —
a delta of exactly the 92 new unit tests. That failure,
`tests/unit/ton/test_contract_matrix.py::test_vale_norte_report_remains_candidate_evidence`,
is the pre-existing path drift already recorded in the 003a result: the test
reads `plans/ton/decision-log.md` while the file is at
`plans/ton/backend/decision-log.md`. No file it touches was changed here.

`ruff check`, `ruff format --check` and `ty check` are clean on every touched
file. `alembic check` was not used as a gate and
`alembic -n schema_private upgrade head` was not run — readiness §17.3 proved
both inappropriate for this deployment.

## Operational migration note

**The running development database was not migrated.** It remains at
`ad99acb9be41`, one revision behind 003a and two behind 003b.

Applying 003b to a real deployment requires 003a's operational steps first, since
003a is its parent:

1. Inject `ENCRYPTION_KEY_SECRET` for the api_server, the workers and the process
   that runs `alembic upgrade`, using the same value. 003a aborts rather than
   writing plaintext if it is missing and any provider row holds configuration.
2. Confirm EE resolution is active in the migrating process. The default
   `LICENSE_ENFORCEMENT_ENABLED=true` already satisfies this; no license is
   needed.
3. Take a database backup. 003a's downgrade cannot restore provider
   configuration values.
4. Apply the migrations from `backend/`:

   ```bash
   cd backend
   uv run alembic upgrade head
   ```

5. Restart the application processes together with the upgrade.

003b itself needs no key, no license and no data transition: it only adds empty
tables. Its downgrade is `alembic downgrade 714172b66b07` and drops exactly the
nine TON tables.

## Boundaries

| Slice | Owns | Not touched here |
|---|---|---|
| **003c** | Finding, FindingEvidence, FindingInterpretation, Occurrence, OccurrenceEvent, OccurrenceImpact, OccurrenceAssignment, OccurrenceNote, OccurrenceImpactedDomain, and the four `*__UserGroup` junctions including `BusinessUnit__UserGroup` and `Contract__UserGroup` | no such table or column exists after 003b, asserted by test |
| **003d** | TonReport, TonReportRevision, the report join tables, TonAuditEvent, and the `ton-canon-1` canonicalisation | `definition_hash` is nullable and unwritten; existing audit emission is unchanged |
| **Plan 004** | ingestion — PDF and Excel parsing, MarkItDown, normalization, NG/Keevo, import jobs | `SourceSnapshot` establishes the provenance contract only |
| **Plan 005** | agents — TON Central, CFO, Frota, Contratos, Auditor, RH, supervisor, handoffs, prompts | `AnalysisRun.specialist` is domain identity only |
| **Plan 006** | schedules — R1–R9, Celery Beat, alerts, recurring tasks, publication policy | `AnalysisTrigger.SCHEDULED` and `routine_code` are identity only |
| **Frontend** | FE-004, FE-005, occurrences UI, reports UI | no file under `web/`, `desktop/` or `mobile/` was changed |

## Prerequisites for 003c

1. Chain from `faee7eaa921e`, one new revision, one head after it.
2. Consume `RuleVersion.identity_components` through
   `onyx.db.ton.identity.validate_identity_components` and
   `IDENTITY_COMPONENT_ORDER`. The vocabulary and canonical order are settled; do
   not re-open them. `identity_key` includes `rule_code`, never the version.
3. Pin `rule_version_id` on every `Finding`, never `rule_id`.
4. Add `BusinessUnit__UserGroup`, `Contract__UserGroup`, `Occurrence__UserGroup`
   with their share-level enum, and the fail-closed reading rule: zero junction
   rows means DENIED. Add `non_public_clause` to
   `within_managed_scope_clause` and pass `sa.true()` for TON.
5. Add `READ_TON_OCCURRENCES` and `MANAGE_TON_OCCURRENCES` with their
   `PERMISSION_REGISTRY` entries. Keep them out of
   `SCOPED_MANAGER_PERMISSIONS` unless a readiness decision says otherwise.
6. Keep every TON table free of `is_public`. The inverse assertions in
   `test_domain_schema.py` and `test_rule_versioning.py` need extending to the
   new tables.
7. Put the TON ACL write path in the Community tree. The CE
   `update_persona_access` raises `NotImplementedError`; copying that split would
   make every TON resource invisible under a CE-resolved worker.
8. Use `ON CONFLICT DO NOTHING` plus a re-read for occurrence deduplication, with
   `UNIQUE(identity_key)` on Occurrence and
   `UNIQUE(analysis_run_id, rule_version_id, identity_key)` on Finding.
9. Persist `interpretation_status = PENDING` and commit it **before** any
   provider request starts.
10. Reuse `scratch_db.py` and the `ton_session` fixture. Do not point TON DB
    tests at the deployment database.
11. Money arrives with `OccurrenceImpact`. Use `Numeric` with `asdecimal=True`,
    never `float`, and never the existing `Numeric(18, 6, asdecimal=False)`
    token-cost pattern.
12. Business rule values remain unapproved. 003c must seed nothing either.

## Confirmations

- Zero `Rule` and zero `RuleVersion` rows are seeded, asserted per table on a
  freshly migrated database.
- No Finding or Occurrence table was created, asserted by name and by substring.
- No report or TON audit table was created. Existing audit emission is unchanged.
- No agent, prompt, handoff or supervisor was implemented.
- No ingestion, parsing, normalization or NG/Keevo work occurred.
- No scheduler, Celery Beat entry or alert was added.
- No frontend file was changed.
- The running development database was not migrated, stamped, downgraded or
  repaired. It is not reachable from the host.
- No existing table was altered or deleted.
- No business value from the Prompt Mestre or the Vale Norte report appears in
  any changed file.
