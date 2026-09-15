# Plan 003d — TON reports, canonicalisation and persistent audit

> **Executor instructions**: This is the final TON-owned domain schema slice, split
> out of Plan 003 by `003-readiness.md` §21. It chains from 003c and completes the
> persistent Plan 003 domain chain.
>
> **Drift check (run first)**: `git status --short`. Then read the current
> main-chain head from `backend/alembic/versions` — take the revision no other file
> names as `down_revision`. Do not hardcode a head.

## Status

- **State**: DONE
- **Priority**: P1
- **Effort**: L
- **Risk**: MEDIUM (nine new tables; no existing table is altered)
- **Depends on**: `003-readiness.md`, `003c-findings-occurrences-acl.md`,
  `008a-capability-gates.md`
- **Blocks**: nothing. Plans 004, 005 and 006 consume this slice but are not
  gated on further Plan 003 work.
- **Category**: direction
- **Baseline commit**: `3de088cbd7896399022c7e49aef6dd8ba12bcb35` (`main`, FE-004)
- **Executed at**: 2026-09-15

## Issues to Address

After 003c, TON could detect a problem, deduplicate it into a business case and
control who may read it. It could not **publish** anything.

Without this slice there is no immutable published output, so a figure shown to a
board in January cannot be re-derived in April — the rules, the findings, the
cases and the sources behind it have all moved on. There is no canonical
serialisation, so no hash over a payload is reproducible across platforms and
`RuleVersion.definition_hash` stays permanently unwritable. There is no report ACL,
so a published report would be either unreachable or visible to everyone. And there
is no persistent actor attribution, so "who generated this?" is answerable only
from a stdout stream that guarantees no delivery.

## Alembic chain

| | |
|---|---|
| Previous head | `6b0ca4eb29fb` (003c) |
| This revision | `440b8984f851` |
| File | `backend/alembic/versions/440b8984f851_ton_reports_canonical_snapshots_and_.py` |
| Heads after | exactly one — `440b8984f851` |

Verified against a disposable PostgreSQL: empty database reaches head; downgrade to
`6b0ca4eb29fb` removes exactly the nine 003d tables and nothing else; every 003b
and 003c column and constraint survives the rollback byte for byte; re-upgrade
restores the same table set.

**No existing table is altered in either direction.**
`ton_rule_version.definition_hash` keeps the nullable `String` column 003b created —
see *definition_hash* below for why it stays nullable.

## Tables created

Nine, in creation order.

| Table | Role |
|---|---|
| `ton_report` | the stable logical report identity |
| `ton_report_revision` | the immutable published snapshot |
| `ton_report_revision__analysis_run` | pinned input |
| `ton_report_revision__occurrence` | pinned input |
| `ton_report_revision__finding` | pinned input |
| `ton_report_revision__rule_version` | pinned input |
| `ton_report_revision__source_snapshot` | pinned input |
| `ton_report__user_group` | the fourth fail-closed ACL junction |
| `ton_audit_event` | persistent best-effort actor attribution |

This closes the persistent Plan 003 chain:

```
ton_rule_version -> ton_analysis_run -> ton_finding -> ton_occurrence -> ton_report
```

## Enums introduced

Two, both `str` enums with name equal to value, stored via
`Enum(..., native_enum=False)` — the repository convention.

| Enum | Members |
|---|---|
| `TonReportType` | `EXCEPTION_CARD`, `EXECUTIVE`, `ISC`, `HIDDEN_MONEY_PANEL`, `MONTHLY_CLOSE`, `RECONCILIATION`, `FORECAST`, `ROI` |
| `TonAuditResourceKind` | `REPORT`, `REPORT_REVISION`, `OCCURRENCE`, `FINDING`, `RULE_VERSION`, `ANALYSIS_RUN`, `BUSINESS_UNIT`, `CONTRACT` |

`TonReportType` is exactly the readiness §12 vocabulary plus `ROI`, which readiness
§13 names for a frozen ROI statement. **Only the identity exists**: no ROI table, no
ROI verification logic, no ROI schedule. ROI stays a derived aggregation over
verified `OccurrenceImpact` rows.

No report category was invented for Plan 006's future operational packages.

## TonReport — the logical identity

`TonReport` answers "which report is this?" and holds no content. There is no
payload column on it at all, so "one mutable row carrying the latest generated
report" is not expressible.

| Column | Note |
|---|---|
| `code` | UNIQUE. The stable reference an owner recognises, on the `BusinessUnit.code` / `Contract.code` convention. Regenerating must not change it, and two generators asked for the same logical report converge on one row. |
| `report_type` | `TonReportType` |
| `title` | wording of the logical report |
| `business_unit_id` | nullable (a consolidated corporate report has no unit), `RESTRICT` |
| `period_start`, `period_end` | nullable, ordered by `ck_ton_report_period_order` |
| `created_at`, `updated_at`, `created_by` | provenance |

No lifecycle status column: readiness approves none, and a status here would compete
with the revision history for authority over what was published. No `is_public`.

## TonReportRevision — the immutable snapshot

Append-only. `uq_ton_report_revision_report_revision` — `UNIQUE(report_id,
revision_no)` — is the history contract: a later generation takes revision *N+1* and
cannot reuse *N*.

| Column | Note |
|---|---|
| `canonical_payload` JSONB | the frozen content, already in `ton-canon-1` JSON-native form |
| `canonicalization_version` | NOT NULL, e.g. `ton-canon-1` |
| `hash_algorithm` | NOT NULL, e.g. `sha256` |
| `content_hash` | NOT NULL, over the canonical bytes |
| `generator_version` | NOT NULL, code identity |
| `generated_at`, `generated_by` | provenance; `generated_by` is `SET NULL` |
| `superseded_by_revision_id`, `correction_reason` | a correction is a new revision |
| `file_record_id` | optional rendered artifact, `SET NULL` |

Storing the scheme and the algorithm **as data** means a future change to either
cannot invalidate a hash already recorded: the old row still names what produced it.

### Revision immutability — three layers

Readiness §12 asks for three, and all three are present.

1. **No update path.** `backend/onyx/db/ton/reports.py` exposes no `update_*` or
   `delete_*` function; a named test asserts the absence.
2. **A model guard.** `_reject_report_revision_content_change`, a SQLAlchemy
   `before_update` listener on `TonReportRevision` in `onyx/db/ton/models.py`,
   raises if any content column changed. Bypassing the reports module does not
   bypass the rule. Registered beside the model, not in the service, so it is
   active whenever the model is importable.
3. **Hash recomputation on read.** `verify_revision_hash` re-canonicalises the
   stored payload, so an UPDATE that bypassed both layers — hand-written SQL, a
   restored backup — is still detectable. It returns `False` for an unknown
   canonicalisation scheme or hash algorithm, because this process cannot
   re-derive such a digest.

**The two exceptions, stated deliberately.** `superseded_by_revision_id` and
`correction_reason` are writable exactly once, only by
`supersede_revision__no_commit`. A revision cannot name its successor at publication
time — the successor does not exist yet — so this is forward-only linkage, and
neither column is covered by the content hash. What revision *N* published, and its
digest, are untouched by being corrected.

`ck_ton_report_revision_superseded_requires_reason` makes the database refuse a
supersession pointer with no recorded reason.

## Report associations

Five explicit association tables, not a JSON id list. Readiness §12 requires "which
report revision used finding X?" to stay relationally answerable; a JSONB array
answers it only with a scan and carries no referential integrity.

- **Cardinality/uniqueness**: composite primary key `(report_revision_id,
  <resource>_id)`. One input appears at most once in one revision.
- **Revision side**: `CASCADE` — the link has no meaning without the revision.
- **Resource side**: `RESTRICT` — see delete semantics below.
- Each carries an index on the resource column, so the reverse question is a
  lookup rather than a scan.

`onyx.db.ton.reports` exposes `pinned_inputs`, plus
`revisions_using_finding` / `_occurrence` / `_rule_version` / `_source_snapshot` /
`_analysis_run`.

## Delete semantics

`RESTRICT` on every pinned input and on `ton_report.business_unit_id`. A published
report must not be left holding a number whose evidence has vanished, so the
database refuses the delete rather than cascading it for cleanup convenience.
Asserted per key by test, both at the schema level and behaviourally.

| Relationship | Rule | Why |
|---|---|---|
| revision → report | `CASCADE` | matches `RuleVersion` → `Rule`; a revision has no meaning without its logical report, and deleting a report is a global-authority act |
| link → revision | `CASCADE` | the link is the relationship |
| link → analysis run / occurrence / finding / rule version / source snapshot | `RESTRICT` | the evidence chain |
| report → business unit | `RESTRICT` | a unit named by a published report stays referenceable |
| revision → superseding revision | `SET NULL` | losing the successor must not delete the record of what was published before it |
| revision → user, report → user, audit → user | `SET NULL` | provenance only; removing an account must not delete published evidence or an audit row |
| revision → file record | `SET NULL` | the canonical payload, not the file, is the authoritative content |

## Reproducibility

A revision stays reproducible after a later `RuleVersion` exists, an `Occurrence`
changes state, a new `Finding` arrives, a source is re-imported, an interpretation is
appended and a later revision is published. Each is a named test.

The mechanism: `canonical_payload` holds the values **as published**, and the join
tables pin the exact inputs by id. Nothing resolves "latest" when reading an old
revision — the pinned `RuleVersion` rows are append-only, the pinned
`SourceSnapshot` rows are receipts of one extraction, and a later interpretation or
resolution appends a row elsewhere.

`§14.3` is covered: a not-assessed ISC dimension and the redistributed weights
survive the snapshot, asserted by test.

## ton-canon-1

`backend/onyx/db/ton/canonical.py`. Pure — no session, no I/O — so a test can assert
the serialisation rather than only the digest.

RFC 8785 JSON Canonicalization Scheme as the base (UTF-8, no insignificant
whitespace, keys ordered by UTF-16 code unit) with readiness §12's four domain rules
and two this slice adds because the four are not by themselves sufficient for
uniqueness.

| # | Rule |
|---|---|
| 1 | money, quantities and percentages are decimal **strings**, never JSON numbers |
| 2 | timestamps are RFC 3339 UTC with an explicit `Z`, at fixed microsecond precision |
| 3 | absent keys are **omitted**, never emitted as `null` |
| 4 | enums serialise as their `.value` string |
| 5 | strings and keys are Unicode **NFC** — RFC 8785 fixes escaping but not composition, so without this one visible text yields two digests. Same precedent `ton-id-1` set. |
| 6 | a bare `Decimal` is normalised (trailing fractional zeros dropped); a `ScaledDecimal` is fixed at its declared scale |

### Canonical decimal behaviour

`ScaledDecimal(value: Decimal, scale: int)` carries the scale a value is *published*
at, because for money the scale is part of the contract: an amount published as
`10.50` must never canonicalise as `10.5`.

- padding is lossless, so `Decimal("10.5")` at scale 2 is `"10.50"`;
- **rounding is refused, not performed**: `Decimal("10.555")` at scale 2 raises.
  Quietly dropping a digit from a published figure is exactly the class of error
  Prompt Mestre §6 exists for. Implemented by trapping `decimal.Inexact`.
- `-0.00` and `0.00` are one number, so they get one representation;
- a bare `Decimal` normalises, so numerically equal values agree;
- two different declared scales are two different published values and hash
  differently — correct, because the precision claim differs.

### No float

A `float` anywhere in a payload is **rejected**, never coerced. `0.1 + 0.2` must not
become a supposedly exact decimal: an IEEE-754 round trip would make the hash
platform-dependent. `bytes` are rejected too — an audit or report row references
source material, it does not embed it. A `float` reaching `RuleVersion.parameters`
through JSONB therefore makes `compute_definition_hash` raise rather than record
tamper evidence that cannot be re-derived.

### Canonical timestamp behaviour

Timezone-aware only. A naive datetime is refused rather than assumed UTC, because
assuming makes the canonical form depend on where the process happened to run.
Offset-equivalent instants canonicalise identically. Precision is fixed at six
fractional digits, so `12:00:00` and `12:00:00.000000` are one payload.

### canonical_document, and why it exists

`canonical_document(payload)` reduces a payload to JSON-native types only (`dict`,
`list`, `str`, `int`, `bool`). `canonical_text` is defined *in terms of* it, so the
stored form and the hashed form cannot drift: there is one set of rules, applied
once. That is what makes hash verification on read exact — PostgreSQL reorders JSONB
keys, and the canonicalisation sorts them again.

### Hash

`sha256` over `canonical_bytes`. Bare hex digest, because a revision stores its
scheme and algorithm in their own columns.

The hash covers the **published content**: the canonicalisation scheme, the report
identity, type and scope, the sorted pinned input ids and the caller's body.
`revision_no`, `generated_at`, `generated_by`, `generator_version`,
`file_record_id` and `correction_reason` are provenance recorded in columns and stay
out. So republishing identical figures yields the same hash — "did anything actually
change?" is answerable — and a business-value change is the only thing that moves
it.

## RuleVersion.definition_hash

003b created the column nullable and left it unwritten on purpose: the canonical
serialisation was specified but not implemented, and a hash under an ad-hoc scheme
would have been meaningless. 003d owns it.

`compute_definition_hash(rule_version, *, rule_code)` is scheme-prefixed —
`ton-canon-1:<sha256>` — unlike `content_hash`, because `definition_hash` has no
companion version column, so the scheme travels inside the value.

**Canonical field set** (business definition only): `rule_code`, `version`, `title`,
`description`, `executor_key`, `parameters`, `unit`, `currency`, `scale`,
`rounding_mode`, `applicability`, `effective_from`, `effective_to`,
`source_reference`, `provenance`, `missing_data_behavior`, `evidence_requirements`,
`min_confidence_level`, `severity_mapping`, `nc_code`, `identity_components`,
`post_resolution_policy`.

**Excluded, with the reason:**

- `id`, `rule_id` — database surrogates; `rule_code` is the business identity and
  Prompt Mestre §7 forbids renaming it;
- `status`, `approved_by`, `approved_at`, `approval_reference` — approval
  *execution* state. Readiness does not include it, and including it would make one
  unchanged definition hash differently before and after approval, defeating the
  tamper check;
- `created_at`, `updated_at`, `created_by` — facts about the row, not the rule.
  These are the mutable runtime database facts that must not make the same
  definition hash differently merely because it was stored at another time;
- `definition_hash` — itself.

An inverse test asserts every `RuleVersion` column is classified in or out, so a
column added later cannot be silently omitted. `identity_components` is
re-normalised, so declaration order does not change the hash.

**Writers.** `create_rule_version__no_commit` now sets it, so every new row is
hashed. `set_definition_hash__no_commit` sets it for one row;
`definition_hash_matches` is the tamper check and returns `False` for an unhashed
row — absence of evidence is not evidence of integrity.

**The column stays nullable, deliberately.** Production seeded zero rule versions,
so there is nothing to backfill there. For a development or disposable database that
holds legitimate pre-003d rows, `backfill_definition_hashes__no_commit` writes only
`definition_hash`, leaves an already-hashed row alone, and **reports** a row it
cannot canonicalise instead of fabricating a value. Making the column `NOT NULL`
would demand a value for such a row — a rule version whose `parameters` hold a JSON
float — and inventing one would defeat the column's purpose. Readiness requires no
`NOT NULL` here, so nullable plus a reported backfill is the safe shape. Nothing is
deleted or recreated.

## Final-interpretation gate

`publish_report_revision__no_commit` refuses a revision containing a finding whose
interpretation is not final. It calls
`onyx.db.ton.interpretations.is_interpretation_final` — the 003c primitive, reused
rather than reimplemented — so only `COMPLETED` and `NOT_REQUIRED` are eligible.
`PENDING`, `RUNNING` and `FAILED` each have a named negative test, and the refusal
message names the offending status.

## Report ACL

`TonReport__UserGroup`, deferred from 003c because `TonReport` did not exist yet
(decision D-043). Shape and semantics are the other three junctions unchanged:
composite primary key, `TonSharePermission` (`VIEWER` / `EDITOR`), `CASCADE` both
sides, index on `user_group_id`.

**One authorization framework.** The predicates live in the existing
`backend/onyx/db/ton/acl.py` and compose the same Plan 008a primitives — no second
module, no report-specific share level, no report-specific bypass. Tests assert
`onyx.db.ton.report_acl` and `onyx.db.ton.report_permissions` do not exist.

| Caller | Read | Write | Delete |
|---|---|---|---|
| global administrator | every row | every row | yes |
| group holding `READ_TON_REPORTS` | shared rows | no | no |
| group holding `MANAGE_TON_REPORTS` | shared rows | EDITOR rows | in scope only |
| anyone else | nothing | nothing | no |

- **Zero junction rows means DENIED.** No report is readable by default. No TON
  table has `is_public`, `public`, `is_global` or `public_permission` — the
  inverse assertions were extended to all nine new tables, at both model and
  database level.
- `report_visible_clause` additionally requires authorization for the owning
  business unit when the report names one, so cross-unit denial holds even if a
  junction row is created by mistake.
- `report_editable_clause` reuses `within_managed_scope_clause` with
  `non_public_clause = sa.true()` and the caller's own groups as the managed set, so
  editing cannot become a route to widening. An EDITOR row is required on top.
- **A revision inherits its report's authorization.** No junction on the revision:
  two ACLs over one published document would eventually disagree.
- Delete calls `assert_global` first — never `allow_scope` on a delete path — then
  the resource write gate.
- Writes re-read the junctions `FOR UPDATE` in-transaction and never trust group
  ids from the request.
- All of it lives in the Community tree unconditionally. A CE-resolved worker must
  not write zero junction rows, because with the fail-closed default that would make
  every report invisible. `TestCommunityResolution` proves it.

### Permission tokens

`READ_TON_REPORTS = "read:ton_reports"`, `MANAGE_TON_REPORTS = "manage:ton_reports"`.
No migration needed — `Permission` is `native_enum=False`.

- `PERMISSION_REGISTRY` entries `view_ton_reports` and `manage_ton_reports`,
  group 4, so an administrator can grant them.
- `MANAGE_TON_REPORTS` implies `READ_TON_REPORTS`.
- **Scoped-permission decision: both are GLOBAL-or-NONE.** Neither joins
  `SCOPED_MANAGER_PERMISSIONS`, matching every other TON token. Group-manager scope
  is a different axis from a TON share level; overlapping them would let managing a
  group confer authority over published reports merely shared with it.
  Resource-level authority comes from the junction. A named test asserts a group
  manager resolves `PermissionAuthority.NONE` for both, and a grantee resolves
  `GLOBAL`.
- Neither is in `Permission.IMPLIED`, so a TON capability is always an explicit
  grant.
- No role was added. `UserRole` stays a tombstone; classification is `AccountType`,
  authorization is `Permission`.

## TonAuditEvent

`backend/onyx/db/ton/audit.py`. The division readiness §11 sets out, enforced:

| Layer | Examples | Guarantee |
|---|---|---|
| **domain history** | `OccurrenceEvent`, `OccurrenceAssignment`, `OccurrenceNote`, `FindingInterpretation`, `RuleVersion`, `TonReportRevision` | **transactional** — part of the business transaction, **must raise** on failure |
| **`TonAuditEvent`** | actor attribution for those acts | **best-effort** — **never raises** into the caller |

A lost lifecycle transition is data loss, so it fails loudly. A lost audit line must
not break a user's action.

**Why a SAVEPOINT.** In PostgreSQL a failed statement aborts the whole transaction,
so a naive `try/except` around `session.add` would swallow the exception and still
destroy the business operation — just less visibly. `emit_ton_audit_event` writes
inside `db_session.begin_nested()`. On failure the savepoint rolls back, the failure
is logged for an operator, and the caller's transaction is left usable. Tests prove
a failed audit write leaves a published revision intact, that the transaction is
still committable, and that a *later* audit write still succeeds.

**A reference, not a copy.** `resource_kind`, `resource_id` and `domain_event_id`
point at the authoritative row; the domain table stays the source of truth. There is
no content column on the table to put a copy in.
`ck_ton_audit_event_resource_reference_complete` makes a half-pointer impossible.
`domain_event_id` has no foreign key on purpose: it points at whichever domain row
an event attributes, and one column cannot key several tables.

**Sanitisation.** `sanitize_audit_metadata` recursively redacts keys matching
`SENSITIVE_KEY_FRAGMENTS` — secrets (`secret`, `password`, `token`, `api_key`,
`credential`, `private_key`, …) and raw business evidence (`canonical_payload`,
`raw_`, `evidence_content`, `excerpt`, `transcript`, `prompt`) — and truncates long
free text so the row stays a reference. A parametrised test covers every declared
fragment, plus nested mappings and lists.

**Schema reuse.** The columns mirror the stdout payload deliberately, so the table
and the stream stay one schema: `audit_schema_version`, `action`, `outcome`,
`ocsf_class`, `tenant_id`, the four `AuditActor` fields, `resource_kind`,
`resource_id`, `domain_event_id`, `authorization_reference`, `endpoint`,
`request_id`, `source_ip`, `before_state`, `after_state`, `extra`, `occurred_at`.

`action`, `outcome` and `ocsf_class` are plain `String` holding the dotted `.value`,
**not** `Enum(...)`. `AuditAction` is a repository-wide append-only vocabulary that
grows with unrelated features; a non-native enum column would attach a CHECK
constraint that turns "someone added an audit action elsewhere" into a failed INSERT
here until a TON migration caught up.

**New actions**, each with the `_OCSF_CLASS_BY_ACTION` entry the import-time
`RuntimeError` guard requires: `TON_REPORT_GENERATE`, `TON_RULE_VERSION_CHANGE`,
`TON_MANUAL_OVERRIDE`, `TON_HUMAN_APPROVAL` — the four events readiness §11 assigns
to this table rather than to a domain history table. A public accessor
`ocsf_class_for` was added to `onyx/utils/audit.py` so the second sink records the
same class instead of keeping a copy that could drift.

**The existing stdout stream is untouched.** `emit_audit_event` is unchanged, still
holds no session, and still writes its JSON line for SIEM export. This is a second
sink, not a replacement. No global logging refactor. A call site wanting both makes
both calls explicitly, and a test asserts the persistent sink writes no stdout line.

**Denials are not audited to the table.** `acl._deny` emits nothing persistent:
writing a row per refused authorization check would let a caller grow the table at
will. The stdout stream already carries `AuditAction.PERMISSION_DENIED`.

**Report generation** has both, as readiness §11 requires: `TonReportRevision` is
the authoritative immutable record, `TonAuditEvent` the actor attribution. A test
proves a failure of only the audit row does not roll back an otherwise valid
published revision, and that a `TonReportRevision` write failure *does* fail
publication.

## Tests

| Spec | Location | Count |
|---|---|---|
| canonicalisation + definition hash | `backend/tests/unit/ton/test_canonicalization.py` | 61 |
| report schema, revisions, immutability, reproducibility, definition-hash persistence | `backend/tests/external_dependency_unit/ton/test_report_immutability.py` | 79 |
| report ACL | `backend/tests/external_dependency_unit/ton/test_ton_report_acl.py` | 43 |
| audit behaviour | `backend/tests/external_dependency_unit/ton/test_ton_audit.py` | 48 |

Placement follows `backend/AGENTS.md`: `canonical.py` and the definition-hash
functions are pure, so they get unit tests; everything whose subject is a
constraint, an `ON DELETE` rule, a SAVEPOINT or a JSONB round trip needs real
PostgreSQL and is external-dependency-unit. The 003b/003c disposable harness is
reused unchanged — `scratch_db.py`, `ton_head_template`, `ton_database`,
`ton_session` — extended with `REVISION_003D`, `TON_003D_TABLES` and
`TON_REPORT_LINK_TABLES`.

**003c assertions flipped, not deleted.** The 003c specs asserted the 003d tables,
models and tokens did *not* exist. Each now asserts the opposite, and the "later
slice" inverse assertions were re-pointed at what Plans 004/005/006 own
(`ton_report_schedule`, `ton_publication_ceiling`, `ton_alert`, `ton_agent_run`,
`ton_ingestion_job`, `ton_roi_registry`). `test_003c_adds_exactly_twelve_tables` now
steps down one revision at a time so a later slice's tables cannot be counted as
003c's.

**Zero seed, asserted.** Every one of the nine tables is empty on a freshly
migrated database, asserted per table.

## Boundaries

| Slice | Owns | Not touched here |
|---|---|---|
| **Plan 004** | ingestion — PDF and Excel parsing, MarkItDown, normalization, NG/Keevo, import jobs | a revision pins `SourceSnapshot` rows; nothing here parses or imports anything |
| **Plan 005** | agents — TON Central, CFO, COO, Frota, Contratos, Auditor, RH, supervisor, handoffs, prompts, real provider calls | no prompt, no LLM call, no orchestration; the interpretation gate only *reads* a status |
| **Plan 006** | R1–R9 routines, Celery Beat, automated monthly publication, alert dispatch, publication ceilings, ISC computation, executive ordering, hidden-money panel, forecast, ROI aggregation | 003d provides persistence and publication primitives only; a test asserts no `ton_*schedule*`, `*ceiling*` or `*alert*` table exists |
| **Frontend** | FE-009 report UI, VIS-000+ | no file under `web/`, `desktop/` or `mobile/` was changed |
| **HTTP contract** | endpoint naming stays open (readiness §22) | no route, no `APIRouter`, no `/api/ton/reports` was invented |

### Future API requirements, documented not implemented

What the data layer already supports for TON-FE-009: server-side pagination with a
stable `(period_start, code)` order on reports and `(revision_no, id)` on revisions;
a detail read applying the same predicate as the list; the full revision history
with its supersession chain and correction reasons; `verify_revision_hash` for a
tamper indicator; per-row share level through `user_report_share_permission` so a UI
can hide an affordance while the backend still refuses a direct call; the pinned
input ids for an evidence drill-down; and published amounts as exact decimal
strings, so no figure passes through a float on its way to a screen.

## Plan 003 status

**Plan 003 is COMPLETE.** The canonical roadmap defines 003a–003d as its entire
implementation scope, and all four are DONE:

| Slice | Revision | State |
|---|---|---|
| 003a provider secret encryption | `714172b66b07` | DONE |
| 003b identity, rules, analysis core | `faee7eaa921e` | DONE |
| 003c findings, occurrences, ACL | `6b0ca4eb29fb` | DONE |
| 003d reports, canonicalisation, audit | `440b8984f851` | DONE |

No later backend plan is complete. Plans 004, 005 and 006 remain TODO.

## Prerequisites for Plans 004, 005 and 006

**Plan 004 (ingestion)**

1. Create `SourceSnapshot` rows through a real extraction. The receipt contract is
   fixed: `is_complete` and `is_schema_conformant` are NOT NULL with no default, so
   an importer must *state* completeness rather than let it be assumed.
2. Point `FindingEvidence.source_snapshot_id` at those receipts. `RESTRICT` means an
   extraction referenced by evidence cannot be deleted.
3. A re-import is a **new** snapshot, never an edit to an existing one. A published
   revision pins the snapshot it used.
4. Any decimal an importer produces must be exact. `extracted_value` is a decimal
   string, and `ton-canon-1` rejects a float, so a parser emitting IEEE-754 doubles
   will fail at publication rather than silently corrupt a hash.

**Plan 005 (agents)**

1. Use the 003c interpretation lifecycle as-is: `begin_interpretation`,
   `mark_interpretation_running`, `complete_interpretation`, `fail_interpretation`.
   These commit deliberately.
2. A report refuses a non-final finding, so an agent must reach `COMPLETED` or
   `NOT_REQUIRED` before its output can be published.
3. Interpretation content never enters an identity key, a definition hash or an
   audit payload. `ton-canon-1` has no path for it and the audit sanitiser strips
   `prompt` and `transcript` keys.
4. Every provider call needs an `LLMFlow` span per `backend/AGENTS.md`. 003d
   contacts no provider.
5. `InterpretationInputScope` composes with `TON_TRACE_CONTENT_MODE` (D-015);
   honour it.

**Plan 006 (reports, schedules, admin)**

1. Publish through `publish_report_revision__no_commit`. Do not write
   `ton_report_revision` directly — the model guard will refuse a content change,
   and a hand-built row can miss the interpretation gate.
2. Compute report bodies with `Decimal` / `ScaledDecimal`. A float raises.
3. ROI is an aggregation over `OccurrenceImpact` filtered by verification state,
   with `confidence <> 'BAIXA'` (readiness §9/§13). If a frozen statement is wanted,
   publish a revision with `report_type = ROI`. No new table.
4. ISC computation, executive ordering, the hidden-money panel and forecast are
   presentation and arithmetic over existing rows; the payload already supports a
   not-assessed dimension and redistributed weights.
5. R1–R9, Celery Beat schedules, alert dispatch and publication ceilings are new
   work. Follow the Celery rules in `backend/AGENTS.md` — `@shared_task`, always
   `expires=`, timeouts implemented inside the task because thread pools disable
   Celery's own.
6. Emit `TonAuditEvent` for an automated publication so a scheduled report still
   carries attribution. It is best-effort; do not make it transactional.
7. HTTP routes for FE-009 still need a naming decision (readiness §22). 003d
   invented none.

## Likely integration conflicts

1. **`onyx/db/enums.py` `Permission`** — two members added at the end of the TON
   block. Any branch adding a permission touches the same region.
2. **`onyx/auth/permissions.py`** — `IMPLIED_PERMISSIONS` and the tail of
   `PERMISSION_REGISTRY` (group 4). A branch adding a registry entry conflicts on
   the closing bracket.
3. **`onyx/utils/audit.py`** — `AuditAction` and `_OCSF_CLASS_BY_ACTION` both grew.
   The vocabulary is append-only, so a concurrent branch adding an action conflicts
   textually but not semantically. **The import-time guard means a resolution that
   keeps an action without its OCSF entry fails at import**, which is the intended
   safety net.
4. **`onyx/db/ton/models.py`** — nine classes and one event listener appended, plus
   the module docstring and the enum import list.
5. **`onyx/db/ton/acl.py`** — a section appended, plus the docstring and imports.
   `_deny` gained a `report_id` parameter; existing call sites are unchanged.
6. **`onyx/db/ton/rule_versions.py`** — `create_rule_version__no_commit` now sets
   `definition_hash` before returning. A branch changing that function conflicts.
7. **Alembic** — `440b8984f851` takes `6b0ca4eb29fb` as `down_revision`. A
   concurrent migration on the same parent produces two heads;
   `test_single_head_revision` catches it, and resolution means re-pointing the
   later revision's `down_revision`, not a merge revision.
8. **`scratch_db.py` `TON_TABLES_AT_HEAD`** and the mirrored `TON_TABLE_NAMES` in
   `tests/unit/ton/test_occurrence_projection.py` — a new TON table must be added
   to both, or the whole-schema inverse assertions fail.
9. **VIS-000** may be running concurrently in another worktree. It is frontend only,
   and 003d changed no frontend file, so no dependency exists in either direction.

## Confirmations

- Zero rows seeded in all nine tables, asserted per table on a freshly migrated
  database. No `Rule`, `RuleVersion`, report, revision, `Occurrence`, `Finding`,
  threshold, publication ceiling, business unit, contract or audit event.
- No `is_public`, `public`, `is_global` or `public_permission` column exists on any
  TON table, asserted at model and database level over all thirty.
- No HTTP route, `APIRouter` or endpoint was created.
- No scheduler, Celery task, beat entry or alert dispatch was created.
- No agent, prompt, supervisor, handoff or provider call was created.
- No ingestion, parser or import job was created.
- No file under `web/`, `desktop/` or `mobile/` was changed.
- The running development database was not migrated, stamped, repaired or
  downgraded. All database verification ran against disposable PostgreSQL
  databases created and dropped by the test harness.
- No write path to any source system exists; the inverse column-name assertion was
  extended to the nine new tables.
