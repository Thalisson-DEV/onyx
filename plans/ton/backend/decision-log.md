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
- Execution baseline: `6e4b2a066459e3bd7217341b6f2fa5af4eb4bc4f`.
- `plans/ton/Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt` is available
  and is incorporated into `domain-rules.md` as report-derived candidates.
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
| D-025 | `LLMProvider.custom_config` encryption at rest is deferred, not fixed. | BLOCKED on Plan 003 readiness | Needs a `jsonb` → `bytea` migration plus a data rewrite while the live database still references unknown revision `6e8f0a2b1c35`. Design recorded as TON-SEC-007-A. |
| D-017 | Preserve OpenSearch, FileStore, PostgreSQL, Redis, Celery, permissions and active shared APIs. | Decided | They are G-class removal risks. |
| D-018 | LangGraph is not introduced without a measured native limitation. | Recommended | Native Deep Research/ToolCall/parallel runner exists. |
| D-019 | The Vale Norte report is a domain-evidence input, not an executable rule catalog. | Decided | Report is present under `plans/`; source validation and owner approval remain required. |
| D-020 | Report arithmetic and policy conflicts stay visible as unresolved data until reconciled. | Decided | Parcelamento, mutual, supplier-total, payroll-total and revenue-baseline values conflict; budget coverage and travel deadlines also conflict. |
| D-021 | The six material-source conflicts are gates, not business corrections. | Decided | The exact values and the nine-versus-eight section count are recorded below and in `domain-rules.md`. |

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
7a. Approve the encryption-key lifecycle before TON-SEC-007-A: who holds
    `ENCRYPTION_KEY_SECRET`, where it is stored, and the rotation window. The
    migration must refuse to run without it.
8. Reconcile the report's conflicting totals and budget coverage before source
   snapshots can support production rules.
9. Resolve the travel settlement proposal (48 hours versus five business days)
   and approve posting, duplicate, budget and fuel control policies.
10. Reconcile all six source-material gates above against the underlying
    workbook, DRE and supporting evidence. Do not apply business corrections
    while any gate remains open.

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
