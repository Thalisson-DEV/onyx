# TON decision log

This log records decisions and gates for the Onyx→TON transformation. It is
maintained under `plans/ton/`; implementation agents must not replace an open
decision with an assumption.

## Issues to Address

TON combines an existing multi-surface SaaS product with a Vale Norte
internal, advisory analysis product. The key decisions are boundary,
immutability, interpretation, integration and web-only removal decisions.

## Important Notes

- Discovery baseline: `a0370f232b`.
- Execution baseline: `73b8ec4d34c34eb90abc784bcff542117164f515`.
- `plans/ton/backend/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt` is
  available and is incorporated into `domain-rules.md` as report-derived candidates.
- `plans/ton/masterprompt.md` holds the TON VALE Prompt Mestre v2.0. Its coverage
  matrix is in `003-readiness.md` §2.
- The report's underlying workbook, DRE, contracts, bank extracts, payroll
  detail and NG/Keevo contract are not present. Candidates remain non-final.
- NG/Keevo has no validated schema/access in this checkout. It is BLOCKED.
- No Finding, Occurrence, Rule, RuleVersion or AnalysisRun model was found by
  the reproducible absence search documented in `gap-analysis.md`.

## Decisions

| ID | Decision | Status | Evidence or reason |
|---|---|---|---|
| D-001 | TON V1 ships only a web experience. | Decided | Product scope supplied by operator. |
| D-002 | Shared mobile/desktop/widget/extension contracts are not removed by UI absence alone. | Decided | Shared `/chat/*`, auth, origin and context contracts in `architecture-map.md`. |
| D-003 | Detection is deterministic and never depends on the LLM. | Decided | TON requirement; current Onyx Deep Research is LLM-oriented. |
| D-004 | AI interpretation is mandatory before final Finding/Report. | Decided | Final state is blocked until interpretation succeeds. |
| D-005 | Interpretation states are `candidate/detected`, `interpretation_pending`, `interpreted/final` and explicit failure. | Decided | Required lifecycle in `domain-rules.md`. |
| D-006 | No LLM arithmetic and no source-system writes. | Decided | TON is advisory and deterministic. |
| D-007 | Central/CEO, CFO, Frota, Contratos, Auditoria and RH have direct, explicitly authorized access. | Decided | Agent topology requires role and tenant/unit scope. |
| D-008 | Partial specialist execution persists result, timeout, error or insufficient-data. | Decided | Supervisor must preserve successful child results. |
| D-009 | NG/Keevo is future, read-only and BLOCKED until schema, access and limits arrive. | Decided | Do not invent fields or credentials. |
| D-010 | Telegram is the first planned external TON channel. WhatsApp follows later. Neither is a core dependency. | Decided | Web and Telegram consume the same channel-neutral application and domain capabilities. |
| D-011 | Final reports use append-only rows, canonical snapshot, hash and optional FileStore artifact. | Recommended; approval required before migration | Resolves reproducibility and auditability. |
| D-012 | Final snapshots cannot be silently mutated. | Decided | Corrections require an explicit new revision and audit event. |
| D-013 | Temporary files use explicit scope and no-index/no-retrieval/no-report policy where required. | Decided | Prevents leakage into knowledge and reports. |
| D-014 | Scheduled TON work uses AnalysisSchedule/AnalysisRun, internal timeout, business retry, expiry, crash sweeper and overlap/misfire policy. | Decided | Existing Craft task has `acks_late=False`, catches exceptions and has no retry. |
| D-015 | External telemetry is off by default; traces are metadata-only by default. | Decided; implemented by Plan 002 | Vale Norte privacy requirement and Plan 002 acceptance tests. |
| D-016 | Deployment credentials are externally injected; existing environments rotate credentials. | Decided; implemented by Plan 007 | Every owned compose variant now declares credentials as required; env templates ship no values; rotation is documented in `007-deployment-hardening.md`. |
| D-022 | `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` stays unset/false and `LICENSE_ENFORCEMENT_ENABLED` stays at its default in every deployment artifact. | Decided; enforced by Plan 007 tests | The paid flag without a license gates the whole application; the enforcement default keeps the EE tree loaded, which computes group-aware document access. |
| D-023 | The production compose variants require `ENCRYPTION_KEY_SECRET`; the development variant does not. | Decided; implemented by Plan 007 | Without the key every encrypted column is written as plaintext bytes. The development boundary is asserted explicitly so it cannot widen silently. |
| D-024 | Model weights keep controlled first-boot download. Private deployments point `HF_ENDPOINT` at an approved mirror or pre-seed the cache volumes. | Decided | `docker-compose.airgap-test.yml` already demonstrates the mechanism; the model server is not redesigned. |
| D-025 | `LLMProvider.custom_config` encryption at rest is deferred, not fixed. | Superseded by D-035. The Alembic prerequisite is resolved (D-026); the work is now scoped as Plan 003a and waits only on open decision 7a. | Needed a `jsonb` → `bytea` migration plus a data rewrite while the live database referenced unknown revision `6e8f0a2b1c35`. That revision is now identified. Design recorded as TON-SEC-007-A. |
| D-017 | Preserve OpenSearch, FileStore, PostgreSQL, Redis, Celery, permissions and active shared APIs. | Decided | They are G-class removal risks. |
| D-018 | LangGraph is not introduced without a measured native limitation. | Recommended | Native Deep Research/ToolCall/parallel runner exists. |
| D-019 | The Vale Norte report is a domain-evidence input, not an executable rule catalog. | Decided | Report is present under `plans/`; source validation and owner approval remain required. |
| D-020 | Report arithmetic and policy conflicts stay visible as unresolved data until reconciled. | Decided | Parcelamento, mutual, supplier-total, payroll-total and revenue-baseline values conflict; budget coverage and travel deadlines also conflict. |
| D-021 | The six material-source conflicts are gates, not business corrections. | Decided | The exact values and the nine-versus-eight section count are recorded below and in `domain-rules.md`. |
| D-026 | Alembic revision `6e8f0a2b1c35` is identified. It is an orphan merge migration from an earlier agent session, never committed, reachable only from Codex turn-diff tree refs. The blocker is closed. | Decided; evidence in `003-readiness.md` §17 | Blob `9cd983b327f7dd2d3c8dca707407651431fd3ede`. The repository history is linear with a single head `ad99acb9be41`. An empty disposable database reaches head cleanly. The live database was re-verified read-only and now reports `ad99acb9be41` with 151 tables, no `persona.ton_role` and zero TON tables, so it accepts a new migration. No remedy is required. |
| D-039 | Plan 003 passed its readiness gate. 003b, 003c and 003d are READY. 003a is DONE (revision `714172b66b07`, the new single head, which 003b takes as its `down_revision`). | Decided; `003-readiness.md` §1 | The architecture is settled by D-027 through D-038. 003a has no schema dependency on 003b, so the encryption-key decision does not hold the TON domain schema back. Rule activation stays blocked; schema creation does not, because every threshold is a `RuleVersion` row guarded by an approval CHECK constraint. |
| D-027 | Rule structure is code; rule parameter value is data. `Rule` holds stable identity; `RuleVersion` holds everything that can change, with provenance, approval and effective dates. | Decided | Lets the schema exist before Vale Norte approves any threshold. `ACTIVE` requires approval by CHECK constraint, so no disputed number can reach production. Eight parameterised executor shapes cover all 40 numbered tests. |
| D-028 | Failure blocks only the affected `(step, domain, business unit)` and its declared dependents. Blocking lives on `AnalysisStep` with a self-referencing cause. No generic workflow engine. | Decided | Prevents reproducing the original TON defect. A run with both failed and passed steps ends `COMPLETED_WITH_BLOCKED_DOMAINS`, never `FAILED`. §5 fixes seven steps and §15 fixes nine specialists, so closed enums suffice. |
| D-029 | Keep both `Finding` and `Occurrence`. `Finding` is one immutable detection with evidence. `Occurrence` is the persistent §13.1 ledger case. The user-facing entity is Occurrence. | Decided | Resolves the terminology conflict and matches `findings-ux-plan.md`, whose route is `/app/occurrences`. A single mutable entity would fail audit history and the many-findings-one-case requirement. |
| D-030 | Identity is an opaque digest over a closed component vocabulary declared per `RuleVersion`. It includes `rule_code`, never `rule_version`. LLM text is never an identity input. | Decided | Including the version would reset every open case on a threshold change. A version change at re-detection forces supersede instead. Dedup is enforced by database uniqueness, not application logic. |
| D-031 | Reuse the Plan 008a authorization primitives unchanged. Add permission tokens and four `*__UserGroup` junctions. No TON entity gets an `is_public` column. | Decided | The existing pattern is fail-closed on the scoped-manager path but fail-open at the resource default (`Persona.is_public` defaults true and short-circuits the group ACL). Omitting the column is stronger than defaulting it false. TON ACL writes stay in the Community tree so a CE-resolved process cannot silently skip them. |
| D-032 | TON needs both domain history tables and one `TonAuditEvent` table, with different guarantees. Domain history is transactional and must raise; audit events stay best-effort and never raise. | Decided | Confirms TON-CAP-007. `emit_audit_event` is stdout-only with no `db_session` and a `try/except: return` body. `TonAuditEvent` stores references to domain rows, never copies, so immutable history is not duplicated. |
| D-033 | Canonicalisation is decided before hashing: RFC 8785 plus four domain rules — decimal strings for money and quantities, RFC 3339 UTC timestamps, omitted keys never null, enum `.value`. `canonicalization_version` and `hash_algorithm` are persisted columns. | Decided; supersedes the open part of D-011 | §6 exists because this data is already wrong by cents. Float round-tripping would make a hash non-reproducible across platforms. Storing the algorithm as data keeps a future change from invalidating old hashes. |
| D-034 | The occurrence ledger ships now. Opportunity is a `ledger_kind` discriminator, not a table. The ROI registry is derived, not stored. | Decided | §13.2's fields are a near-subset of §13.1's. A separate table would triplicate the impact, verification and ACL logic. `ledger_kind` is a two-way door; two tables would not be. |
| D-035 | SECURITY-08 ships as a separate migration (Plan 003a) immediately before the TON domain chain, not inside it. | Decided; supersedes D-025's deferral | Different blast radius, rollback and approval gate. Coupling means a TON schema rollback un-encrypts credentials. The migration must abort when `ENCRYPTION_KEY_SECRET` is absent **and** when the Community implementation resolves, because CE `_encrypt_string` writes plaintext unconditionally. |
| D-036 | Plan 003 splits into 003a (security prerequisite), 003b (rules and analysis), 003c (findings, occurrences and ACL), 003d (report snapshot and audit). | Decided | Each is one Alembic revision, individually reversible, with its own test file. The split reduces migration and security risk and creates independently testable boundaries. |
| D-040 | `ENCRYPTION_KEY_SECRET` is a Vale Norte deployment secret held by the infrastructure owner, injected externally at deployment time, never committed and never logged. Rotation is manual through the existing `rotate_encryption_key` mechanism. This resolves open decision 7a and closes readiness blocker B4. | Decided; implemented by Plan 003a | The migration refuses to run without the key, so custody had to be settled before it could be authored. Where the initial self-hosted deployment has no secret manager, an operator-controlled secret file outside the repository with restrictive permissions is acceptable; this slice invents no new secret-management platform. Losing the key can make encrypted provider credentials unrecoverable, so the infrastructure owner keeps a backup and custody procedure. |
| D-041 | Provider `custom_config` masking is whole-dict by default. Every value is masked unless its key is on an explicit non-credential allow-list. | Decided; implemented by Plan 003a | `custom_config` accepts arbitrary keys, so the previous key-name substring heuristic returned a secret stored under an unrecognised name in full. Inverting to an allow-list keeps the admin forms working — regions, locations, projects, auth-method and surface selectors stay readable — while an unknown key is treated as credential material. The write path restores masked placeholders, so an unmodified form cannot overwrite a real credential. |
| D-042 | The 003a migration requires **both** EE encryption resolution and a usable `ENCRYPTION_KEY_SECRET`, and proves it with a probe round-trip, before converting any credential row. The guards are gated on there being a row to convert. | Decided; implemented by Plan 003a | The Community `_encrypt_string` returns `input_str.encode()` and the EE read path decodes such a row without raising, so a cleartext row would be undetectable at read time. One guard is not sufficient: EE without a key, and a key without EE, both store cleartext. Row-gating keeps CI and a fresh install able to reach head without a key, because a database with no stored configuration has no credential at risk. |
| D-037 | `alembic check` is not a verification gate. The repository gate is `pytest tests/integration/tests/migrations/`. | Decided; measured | `alembic check` reports over 470 operations against an untouched baseline, because `target_metadata` includes Celery's runtime tables and `compare_server_default=True` flags every Python-side default. CI enforces single head, up/down consistency and upgrade instead. |
| D-038 | `alembic -n schema_private upgrade head` must not run in this single-tenant deployment. | Decided; reproduced | `alembic_tenants/env.py` sets no `version_table_schema`, so it collides with the main chain's `alembic_version`. Observed: `Can't locate revision identified by 'ad99acb9be41'`. Record the environment fact; do not skip the migration review. |

## Material-source reconciliation gates

These gates preserve the report as evidence. They do not select an accounting
treatment, threshold or correction:
(`plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt:24-58,69-99,134-173,179-212,218-251,257-280`).

1. **1.1**: seven-row sum R$ 90,877,705.63; table total R$ 90,877,705.65;
   paid amount R$ 4,519.42; narrative/table difference R$ 4,519.40.
2. **1.3**: totals by origin R$ 4,210,512.00; monthly table total
   R$ 4,210,513.00; narrative total R$ 4,210,513.16.
3. **1.4**: visible rows R$ 473,552.00 versus stated R$ 473,827.00;
   difference R$ 275.00; completeness must be reconciled first.
4. **1.5**: visible unit sums payroll R$ 4,984,535.00 and charges
   R$ 2,827,183.00 versus declared payroll R$ 4,733,535.00 and charges
   R$ 2,936,450.00; the aggregate ratio is blocked.
5. **1.6**: calculated Jan-Mar average R$ 3,474,240.67 versus R$ 3,474,174;
   calculated fall approximately 87.13%, versus prose 87% and table −88.0%;
   baseline and rounding require approval.
6. **Summary versus section 1**: the summary declares nine types, while section
   1 contains eight numbered items, 1.1–1.8; coverage must be reconciled.

## Open decisions that block schema or production rules

1. Approve the append-only report shape, snapshot serialization and hash
   algorithm before migrations.
2. Approve logical identity components and post-resolution behavior for each
   domain. The generic implementation must remain opaque until then.
3. Approve domain thresholds, units, currencies, periods, rounding and
   missing-data behavior from Vale Norte owners.
4. Approve HR, finance, contract and fleet access roles and masking.
5. Approve retention for temporary files, persistent files, evidence, source
   snapshots and reports.
6. Resolved by Plan 002: use `TON_WEB_ONLY`, `TON_EXTERNAL_TELEMETRY_MODE`
   and `TON_TRACE_CONTENT_MODE`.
7. Approve which SaaS surfaces are replaced versus hidden for the deployment.
7a. **RESOLVED** by D-040. The encryption-key lifecycle is settled and recorded
    in `003a-provider-secret-encryption.md`; Plan 003a is DONE.
8. Reconcile the report's conflicting totals and budget coverage before source
   snapshots can support production rules.
9. Resolve the travel settlement proposal (48 hours versus five business days)
   and approve posting, duplicate, budget and fuel control policies.
10. Reconcile all six source-material gates above against the underlying
    workbook, DRE and supporting evidence. Do not apply business corrections
    while any gate remains open.
11. Reconcile the §8 test-code range of the Prompt Mestre. The heading says
    T13–T26; the body defines T13–T30. §7 forbids renaming codes, so `Rule.code`
    values cannot be fixed until an owner settles the range. Found by the Plan
    003 readiness gate.

Closed by the readiness gate: the local-database remedy question. The database
now reports the repository head `ad99acb9be41` (D-026), so no remedy is needed.

Decisions 1, 2 and the report-shape part of 3 are now closed by D-027 through
D-034. Decision 3's threshold values, decision 4's access scopes and decision 5's
retention remain open, but no longer block the migration: every one of them is a
row, not a column. See `003-readiness.md` §23.

## Rejected or deferred approaches

- Replacing the native supervisor with LangGraph without a demonstrated gap.
- Creating a fake NG/Keevo schema from unvalidated report evidence.
- Embedding Telegram or WhatsApp logic in core domain services.
- Deleting shared clients/routes because they are outside the V1 UX.
- Mutating final reports in place.
- Treating interpretation failure as an empty successful interpretation.

## Implementation strategy

Resolve decisions in dependency order: contract inputs, security/privacy,
immutability, domain identity, then schema and implementation. Record each
approval with evidence and do not let executor agents choose an open item.

## Scope

In scope: decisions, rationale, approval gates and rejected approaches.

Out of scope: source code, migrations, production rules, external integration
configuration, credentials and deployment mutation.

## Tests

Validate decision gates with reproducible searches:

```text
rg -n "Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte|non-final|BLOCKED|LangGraph|append-only|interpretation_pending" plans/ton
rg -n "class (Finding|Occurrence|Rule|RuleVersion|AnalysisRun)|__tablename__.*(finding|occurrence|rule|analysis|report)" backend/onyx/db/models.py backend/alembic/versions backend/alembic_tenants/versions
```

Expected result: every open decision is visible in this log; no production
rule is presented as approved; and the report file and unresolved conflicts
remain discoverable.

## Done criteria

- [ ] All blocking decisions have an owner and approval record.
- [ ] No implementation plan treats provisional rules as production rules.
- [ ] Immutability choice is approved before schema work.
- [ ] NG/Keevo remains blocked without external contract evidence.
- [ ] Web-only removal decisions retain shared API contracts until gated.
- [ ] Security and privacy defaults are explicit.

## STOP conditions

- Stop when an open decision is required to choose a field, threshold, identity key or retention rule.
- Stop when a source contract is missing or an implementation invents NG/Keevo fields.
- Stop when a report design permits silent final-state mutation.
- Stop when a plan bypasses the mandatory interpretation state.
- Stop when a product cleanup changes a shared client contract without a gate.
