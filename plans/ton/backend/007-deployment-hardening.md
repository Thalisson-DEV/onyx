# Plan 007: Harden TON deployment credentials and generated artifacts

> **Executor instructions**: Run this P0 hardening slice after Plans 001 and
> 002. It changes deployment configuration only. Do not print credential
> values, edit generated output by hand, or remove shared workers/services.
>
> **Drift check (run first)**: from the repository root, run `git status --short`
> and `git diff --stat -- deployment cli`. Compare all changes with the
> `a0370f232b` baseline. Stop if unrelated deployment or CLI changes are found.

## Status

- **State**: PARTIAL. Deployment credential hardening and generated artifact
  synchronization are DONE. `LLMProvider.custom_config` encryption at rest is
  BLOCKED on a migration and key-management prerequisite; see
  "Provider secret storage" below. Nothing claims that finding is fixed.
- **Priority**: P0
- **Effort**: M
- **Risk**: CRITICAL
- **Depends on**: `001-baseline-contracts.md`, `002-security-privacy.md`
- **Category**: security
- **Planned at**: commit `a0370f232b`, 2026-09-13
- **Executed at**: commit `80e76cfb12`, 2026-09-14

## Why this matters

The compose template and generated files contain fallback credential
configuration. A copied development default can expose search or object
storage. This slice removes fallback behavior, keeps service dependencies
needed by the web and workers, and proves generated deployment copies stay in
sync.

## Current state

- `deployment/docker_compose/docker-compose.template.yml:100-115,640-643` is
  the compose source of truth and contains credential fallback configuration.
- `deployment/docker_compose/docker-compose.yml:46-127,369-540` starts API,
  database, OpenSearch, Redis/cache, model and FileStore services.
- `backend/supervisord.conf:30-142` defines primary, indexing, file,
  scheduled-task, beat, monitoring and integration workers.
- `deployment/README.md:6-26` requires `ods generate-compose --write` and says
  CLI embedded copies under `cli/internal/deploy/deployfiles/embedded/` must
  stay synchronized. `cli/internal/deploy/deployfiles/sync_test.go` checks that
  synchronization.
- Credential names are configuration evidence only. Never copy or expose their
  values. Existing environments require operational rotation outside this plan.

## Implementation strategy

1. Add a non-secret configuration check before changing the template. Require
   external injection for every credential used by compose variants. Preserve
   API, PostgreSQL, Redis, OpenSearch, FileStore, model, Celery, beat,
   monitoring and health dependencies.
2. Update only `docker-compose.template.yml`, then regenerate the documented
   default, production and no-Let's-Encrypt compose files and CLI embedded
   copies.
3. Validate that missing required credentials fail closed and that all intended
   service names, health checks, volumes, queues and worker processes remain.
   Do not rotate live values in the repository or deployment environment.

## Scope

**In scope**:

- `deployment/docker_compose/docker-compose.template.yml`;
- generated compose outputs refreshed by the generator:
  `docker-compose.yml`, `docker-compose.prod.yml`,
  `docker-compose.prod-no-letsencrypt.yml`;
- synchronized embedded files under
  `cli/internal/deploy/deployfiles/embedded/docker_compose/`;
- `backend/tests/unit/ton/test_deployment_profile.py` (create, non-secret
  configuration assertions);
- `cli/internal/deploy/deployfiles/sync_test.go` only if synchronization needs
  a test update.

**Out of scope**:

- web surface changes, backend domain behavior, workers or supervisor redesign;
- mobile, desktop, widget and extension removal;
- Telegram, WhatsApp and NG/Keevo integrations;
- live credential rotation, secret values and external infrastructure mutation;
- hand edits to generated compose or embedded files.

## Commands you will need

Run the following from the repository root:

```text
git status --short
git diff --stat -- deployment cli
uv run pytest backend/tests/unit/ton/test_deployment_profile.py -xv
ods generate-compose --write
git diff --check
```

Then run from `cli/`:

```text
go test ./...
```

Expected result: the non-secret profile test passes; compose generation changes
only intended generated copies; `git diff --check` is clean; and the CLI sync
tests pass. A deployment configuration check must report missing credentials as
an error without printing values.

## Tests

The named profile test must assert required service names, health checks,
credential injection references, absence of fallback defaults, and preservation
of API, PostgreSQL, Redis, OpenSearch, FileStore, model, worker, beat and
monitoring services. The existing CLI sync test must cover every refreshed
embedded copy.

## Done criteria

- [x] Required credentials use external injection in every owned compose
      variant; no fallback value is committed or logged.
- [x] Shared web and worker services, queues, storage, health checks and
      monitoring remain present.
- [x] Generated compose files and CLI embedded copies are synchronized.
- [x] Named profile and CLI tests pass.
- [x] `plans/README.md` and `plans/ton/roadmap.md` still identify this as the
      only generated-deployment plan.

## STOP conditions

- Stop if a required credential cannot fail closed without exposing its value.
- Stop if the generator changes unrelated files or embedded assets.
- Stop if a proposed cleanup removes Redis, PostgreSQL, OpenSearch, FileStore,
  Celery, beat, monitoring, health checks or a shared worker dependency.
- Stop if live credential rotation or external infrastructure mutation is
  required; report the credential type and file path only.

## Maintenance notes

Run the generator and CLI sync test whenever the compose template changes.
Review service dependencies before any later TON web-only cleanup.

---

# Execution result

Baseline commit `80e76cfb12`. The drift check found no local deployment or CLI
changes: every difference from `a0370f232b` under `deployment/` and `cli/` comes
from upstream commits (`16247eec9d`, `dd22ca103c`, `0fed336c6b`, `2e7bb6c6d5`).

## Generated-file ownership, confirmed before editing

| Role | Location |
|---|---|
| Source template | `deployment/docker_compose/docker-compose.template.yml` |
| Generator | `ods generate-compose --write` (`tools/ods/internal/composegen`) |
| Generated outputs | `docker-compose.yml`, `docker-compose.prod.yml`, `docker-compose.prod-no-letsencrypt.yml` |
| Synced copies | `cli/internal/deploy/deployfiles/embedded/**` (manifest `deployfiles.All`) |
| Drift gates | `ods generate-compose` check mode; `cli/internal/deploy/deployfiles` Go tests; `docker-compose-sync` pre-commit hook |

This matches the planning documents, so no STOP was triggered. Every edit went
into the template first, then through the generator. No generated file was
hand-edited.

## Deployment credential audit

`GENERATED?` means the guided installers create the value. `INJECTED?` means the
deployment reads it from outside the repository. "was" describes the state at the
baseline commit.

| Credential | Source | Default (was → now) | Production behavior | Development behavior | Generated? | Injected? | Logged? | Test coverage |
|---|---|---|---|---|---|---|---|---|
| `POSTGRES_PASSWORD` | `.env` → compose + app | `password` → none | default variant fails closed; prod/no-letsencrypt read `.env` or use `USE_IAM_AUTH` | must be generated once; unchanged on rerun | yes, both installers | yes | no | profile test + CLI install test |
| `POSTGRES_USER` | `.env` | `postgres` (kept) | identifier, not a secret | same | no | yes | no | profile test asserts it stays defaulted |
| `DB_READONLY_PASSWORD` | `.env` | `password` → none | operator-supplied; delete the key when unused | not used | no | yes | no | prod env template assertion |
| `OPENSEARCH_ADMIN_PASSWORD` | `.env` → compose + app | `StrongPassword123!` → none | all variants fail closed | must be generated once | yes, both installers | yes | no | profile test + CLI strength test |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `.env` → compose | `minioadmin` → none | all variants fail closed | must be generated once | yes, both installers | yes | no | profile test + CLI install test |
| `S3_AWS_ACCESS_KEY_ID` / `S3_AWS_SECRET_ACCESS_KEY` | `.env` → compose + app | `minioadmin` → none | all variants fail closed | must be generated once | yes, both installers | yes | no | profile test + CLI install test |
| `USER_AUTH_SECRET` | `.env` → app | empty; app already fails closed (`verify_user_auth_secret`, `backend/onyx/auth/users.py:216`) | api_server refuses to start | warning only under `DEV_MODE` / `INTEGRATION_TESTS_MODE` | yes, both installers | yes | no | existing `test_verify_auth_setting.py`; prod env template assertion |
| `ENCRYPTION_KEY_SECRET` | `.env` → app | optional, no default | prod/no-letsencrypt fail closed | optional; default variant unchanged | yes, both installers | yes | no | profile test (prod required, default optional) |
| `METRICS_AUTH_TOKEN` | `.env` → app | unset; `/metrics` returns 401 unless `DISABLE_METRICS_AUTH` | already fail-closed upstream | same | no | yes | no | unchanged |
| Redis password | `.env` → app | empty; no auth on the compose-internal cache | unchanged, see remaining risks | same | no | yes | no | none |
| SMTP credentials | `.env` → app | `SMTP_PASS` example value removed from the prod template | operator-supplied, optional | optional | no | yes | no | none |
| Legacy OAuth client secrets | `.env` → app | unset | operator-supplied; SSO now lives in provider rows | unset | no | yes | no | unchanged |
| Connector credentials | `credential.credential_json` | n/a | `EncryptedJson`; plaintext bytes when `ENCRYPTION_KEY_SECRET` is unset | same | no | n/a | no | existing rotation tests |
| Provider `api_key` | `llm_provider.api_key` | n/a | `EncryptedString`; same caveat | same | no | n/a | no | existing rotation tests |
| Provider `custom_config` | `llm_provider.custom_config` | n/a | **plain JSONB, unresolved** | same | no | n/a | no | see the blocker below |

## Credential fallbacks removed

Removed from the template and therefore from all three generated variants and
the two embedded copies:

- `OPENSEARCH_ADMIN_PASSWORD` no longer falls back to a published value, at all
  three references (api_server, background, and the OpenSearch bootstrap
  variable). This was the one credential that still carried its fallback in the
  production variants.
- `S3_AWS_ACCESS_KEY_ID`, `S3_AWS_SECRET_ACCESS_KEY`, `MINIO_ROOT_USER` and
  `MINIO_ROOT_PASSWORD` no longer fall back in the default variant. The
  production variants already required them, so the per-variant `#!value`
  directives collapsed into one required line each.
- `POSTGRES_PASSWORD` no longer falls back in the default variant.

Removed from the env templates:

- `env.template`: the database and object-storage credential values.
- `env.prod.template`: the database, read-only-database and example SMTP
  password values. These were committed credentials in a production template.

Each variable is now declared with `${NAME:?...}`, so Docker Compose refuses to
render and names the missing variable. No message contains a value.

## Required external secret configuration

Supply these from `.env`, Docker secrets, or a platform secret store:

```text
POSTGRES_PASSWORD
OPENSEARCH_ADMIN_PASSWORD
MINIO_ROOT_USER
MINIO_ROOT_PASSWORD
S3_AWS_ACCESS_KEY_ID
S3_AWS_SECRET_ACCESS_KEY
USER_AUTH_SECRET
ENCRYPTION_KEY_SECRET          (required by the production variants)
```

Keep `S3_AWS_ACCESS_KEY_ID` / `S3_AWS_SECRET_ACCESS_KEY` equal to
`MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`: the application authenticates to
MinIO with its root credentials.

`OPENSEARCH_ADMIN_PASSWORD` must satisfy the OpenSearch strength rules, so a bare
hex string is rejected. Both installers append a fixed suffix that supplies the
missing character classes.

## Development behavior

The development path stays usable and is explicitly scoped:

- `docker-compose.dev.yml` (port publishing) and the local `backend/` workflow
  are unchanged.
- An existing gitignored `.env` still renders, because the required variables are
  already present in it.
- A fresh install generates every required credential: `onyx-cli`
  (`cli/internal/deploy/install/install.go`) and `install.ps1`. Neither ships a
  value, so no environment can inherit one.
- `ENCRYPTION_KEY_SECRET` is the only credential-bearing variable the default
  variant leaves optional. A dedicated test asserts that boundary, so widening or
  narrowing it has to be a deliberate edit.

The development allowance is a generator, not a shipped default. There is no
"safe because developers know about it" default left in the owned artifacts.

## Production / private behavior

A missing required credential is a configuration failure before any container
starts. Compose reports the variable name and nothing else. The affected service
does not start, so there is no path where a missing secret resolves to a known
value and production comes up anyway.

`relational_db` in the production variants deliberately keeps no inline
`environment` block: `USE_IAM_AUTH=true` deployments have no password to
interpolate. The credential arrives through `env_file`, and the profile test
asserts that no production variant gives `POSTGRES_PASSWORD` an inline fallback.

## Deployment invariants

- `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` stays `false`. Setting it true
  without a license puts the application into gated access
  (`backend/ee/onyx/server/settings/api.py:126-131`). No compose variant sets it.
- `LICENSE_ENFORCEMENT_ENABLED` stays unset, at its `true` default. That default
  keeps the EE implementation tree loaded, which is what computes group-aware
  document access (`backend/onyx/utils/variable_functionality.py:42-72`). No
  deployment artifact sets it, and the profile test enforces that.
- EE/CE dispatch is untouched. `variable_functionality.py`,
  `fetch_versioned_implementation` and everything under `backend/ee` are
  unmodified.
- `MULTI_TENANT` stays false. No owned variant sets it or references the control
  plane.
- Absence of a license is not an application-wide failure. Nothing in this slice
  changes tier resolution or any gate.

## Telemetry and external exposure

Verified, not reimplemented. Plan 002 set the defaults; this slice confirms the
deployment configuration preserves them. No owned artifact sets
`DISABLE_TELEMETRY=false`, a PostHog key, or a HubSpot tracking URL, and the
profile test asserts that. No credential variable is passed to a telemetry,
tracing, or analytics service, and no compose `command` echoes one.

## Model weights on first boot

Decision: keep controlled first-boot download and document the private path.
The model server is not redesigned.

- The image sets `HF_HOME=/app/.cache/huggingface`
  (`backend/Dockerfile.model_server:18,78`) and both model servers mount named
  volumes there, so weights are fetched once per volume.
- For a deterministic or disconnected deployment, point `HF_ENDPOINT` at an
  approved internal mirror. `deployment/docker_compose/docker-compose.airgap-test.yml`
  is the working reference: it sets `HF_ENDPOINT` and an `internal: true` network.
- Alternatively, pre-seed `model_cache_huggingface` and
  `indexing_huggingface_model_cache` from an approved artifact store before the
  first start.
- The `inference_model_server` health check keeps its 600 s `start_period` to
  absorb the first download.

This is not an Onyx paid dependency and involves no Onyx-operated service.

## Provider secret storage — `LLMProvider.custom_config`

**Result: deferred as an explicit blocker. The values are still plaintext at
rest. This is not fixed.**

Traced paths:

- Model: `backend/onyx/db/models.py:3624-3626` declares `custom_config` as plain
  `postgresql.JSONB()`. The sibling `api_key` at `:3617-3619` is
  `EncryptedString()`. The live column type is `jsonb`; encrypted columns are
  `bytea`.
- Single ORM write: `backend/onyx/db/llm.py:357` in `upsert_llm_provider`. Only
  empty values are pruned; keys are never validated.
- Write callers: `PUT /admin/llm/provider`
  (`backend/onyx/server/manage/llm/api.py:590-700`), EE seeding
  (`backend/ee/onyx/server/seeding.py:118-140`), multi-tenant provisioning
  (`backend/ee/onyx/server/tenants/provisioning.py:476-494`, which writes a
  service-account JSON blob), and the image-generation shadow providers
  (`backend/onyx/server/manage/image_generation/api.py:71-164`).
  `backend/onyx/setup.py:296` passes `custom_config=None`. Auto mode
  (`recommended-models.json`) never touches it.
- Migrations: created plaintext by `401c1ac29467`; `1e0a3e4226f7` moved
  `OLLAMA_API_KEY` out of it into the encrypted `api_key` column, stating that
  `custom_config` stores plaintext. No migration encrypts it.
- Read paths: `backend/onyx/llm/factory.py:390` → `DefaultMultiLLM`;
  `backend/onyx/llm/multi_llm.py:466-519` maps recognized keys to LiteLLM kwargs
  and injects the rest into `os.environ` for the duration of a call, under a
  lock, when the `llm_custom_config_env_injection` security setting allows it.
  Validation reads it in `POST /admin/llm/test` and in the Bedrock and LM Studio
  model-fetch helpers (`api.py:191-216`). Background workers reach it through the
  same factory.
- Serialization: `LLMProviderView.from_model` copies the raw dict;
  `_mask_provider_credentials` (`api.py:250-264`) masks it on
  `GET /admin/llm/provider` and `GET /admin/llm/provider/{id}`. The non-admin
  `LLMProviderDescriptor` has no `custom_config` field at all.
- Logging: values are masked in the config dump (`multi_llm.py:577-586`) and in
  env-injection logs (`mask_env_value_for_logging`). LiteLLM exception text is
  scrubbed by `scrub_sensitive_values` (`onyx/llm/utils.py:373-405`). No
  telemetry or tracing path reads the dict.

Key semantics. The schema is open: the Pydantic type is `dict[str, str] | None`
with no allowlist, so an admin can store any key.

- Credential-bearing: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
  `AWS_SESSION_TOKEN`, `AWS_BEARER_TOKEN_BEDROCK`, `AZURE_AD_TOKEN`,
  `vertex_credentials` (a whole service-account JSON), `LM_STUDIO_API_KEY`, and
  any generic `<PROVIDER>_API_KEY`.
- Safe metadata: `AWS_REGION_NAME`, `vertex_location`, `vertex_project`,
  `vertex_auth_method`, `<PROVIDER>_API_BASE`, `BEDROCK_AUTH_METHOD`, and the
  surface-selection keys.
- Masking is a key-name heuristic
  (`SENSITIVE_CUSTOM_CONFIG_KEY_FRAGMENTS`, `onyx/llm/utils.py:348-362`), so a
  secret stored under a key that matches no fragment is returned unmasked.

Encryption decision. A repository-native abstraction exists and would be reused,
not reinvented: `EncryptedJson` (`models.py:231-249`) over
`encrypt_string_to_bytes` / `decrypt_bytes_to_string`, keyed by
`ENCRYPTION_KEY_SECRET`, with `SensitiveValue` guarding accidental serialization
and `backend/onyx/db/rotate_encryption_key.py` discovering new encrypted columns
automatically. No new cryptography is needed.

Why it is blocked here rather than implemented:

1. `jsonb` cannot become `bytea` without a schema migration plus an
   application-level data rewrite of existing provider rows. Postgres cannot cast
   between them in a way that yields app-encrypted bytes.
2. The only precedent for this exact conversion,
   `backend/alembic/versions/b4950827c0dd_encrypt_external_app_credentials.py`,
   avoided migrating data by deleting the rows. That is not available here:
   existing deployments would lose Bedrock and Vertex credentials.
3. Plan 003 has not started and the live local database still reports an unknown
   Alembic revision `6e8f0a2b1c35`, so this slice must not author a
   migration-bearing change.
4. Backward compatibility cannot be guaranteed without the key lifecycle being
   settled. Under CE, or with `ENCRYPTION_KEY_SECRET` unset, the "encrypted"
   bytes are plain UTF-8, so the migration's output depends on which
   implementation resolves while it runs.

Per the plan's STOP conditions, that implementation path stopped. API masking is
left intact. The non-invasive protections added instead are the deployment-level
ones: the production variants now require `ENCRYPTION_KEY_SECRET`, so the columns
that *are* encrypted stop silently degrading to plaintext, and both installers
generate a key on a fresh install.

### Follow-up prerequisite: TON-SEC-007-A

Blocks on Plan 003 readiness (the Alembic revision must be resolved first).

1. Add `custom_config_encrypted` as `sa.LargeBinary()`, nullable.
2. Backfill inside the migration with `encrypt_string_to_bytes(json.dumps(cfg))`,
   the pattern already used by `2e0b2b146de1`, `f3a9c1d4b7e2`, `8f3b2c91d4e7`
   and `3c9a65f1207f`. Require `ENCRYPTION_KEY_SECRET` to be present, and refuse
   to run without it rather than writing plaintext bytes.
3. Drop the JSONB column, rename, restore nullability.
4. Switch the ORM type to `EncryptedJson()` with
   `Mapped[SensitiveValue[dict[str, str]] | None]`, then update every reader to
   `get_value(apply_mask=False)`: `server/manage/llm/models.py:116,220,230`,
   `server/manage/llm/api.py:207-216,250-264,459-478,618-631`,
   `llm/factory.py:390`, and the Bedrock and LM Studio fetch helpers.
   `SensitiveValue` raises on subscript and iteration, so a missed reader fails
   loudly instead of silently.
5. Replace the key-name masking heuristic with `mask_credential_dict` so an
   unrecognized key cannot leak.
6. Tests: create a provider with a synthetic secret and assert the raw column is
   binary and not plaintext; round-trip through the runtime; assert API output
   stays masked; assert update preserves protection; assert a missing or wrong
   key fails safely; assert logs and serialization do not expose the value;
   assert a background worker can still read it. Rotation and its invariant test
   pick the column up with no edit.

An alternative narrower fix, already precedented by `1e0a3e4226f7`, is to move
each known secret key out of `custom_config` into a dedicated encrypted column.
It still needs a migration, so it carries the same prerequisite.

## Encryption key management

- The key comes only from `ENCRYPTION_KEY_SECRET`. It is not in source, has no
  production default, and is not derived from public data.
- The EE implementation rejects a key shorter than 16 bytes
  (`backend/ee/onyx/utils/encryption.py:16-29`).
- The production compose variants now fail closed when it is absent.
- Introducing the key on an existing database is read-compatible: decryption
  falls back to a raw UTF-8 decode for rows written without it. New writes are
  encrypted. Sweep the remainder with
  `python -m onyx.db.rotate_encryption_key`, passing the previous key.
- Rotation implication: rotating the key requires that command with the old key
  before the new key becomes the only one in use. Automatic rotation is not
  implemented and is not introduced here.

## Operational rotation required

Code hardening does not rotate anything already in use outside the repository.
Rotate these where a deployment ever started with a published default. Values
stay outside this repository.

| Credential class | Affected service | Reason | Safe sequence |
|---|---|---|---|
| OpenSearch admin password | `opensearch`, api_server, background | published default was reachable | set the new value, restart the app containers, then update the OpenSearch internal user; a fresh volume takes it at bootstrap |
| Object-storage root credentials | `minio`, api_server, background | published default was reachable | rotate the MinIO root pair and the matching `S3_AWS_*` pair together, then restart the app containers |
| Database password | `relational_db`, api_server, background | published default was reachable | `ALTER ROLE <user> WITH PASSWORD '<new>'`, update `.env`, restart the app containers |
| Read-only database password | `relational_db` | published default was in the prod template | same as above, if the role exists |
| `USER_AUTH_SECRET` | api_server | rotating invalidates sessions and pending reset links | rotate during a maintenance window |
| `ENCRYPTION_KEY_SECRET` | api_server, workers | only if a key was ever shared | set the new key, then run the rotation command with the old key |
| Provider credentials in `custom_config` | api_server, workers | stored plaintext at rest | re-enter through the admin UI after the follow-up lands; rotate at the provider if the database was ever exposed |

No Vale Norte credential was read, printed, or rotated by this slice.

## Remaining risks

1. `LLMProvider.custom_config` and `VoiceProvider.custom_config` are still
   plaintext JSONB. Tracked as TON-SEC-007-A above.
2. Application-level code fallbacks remain outside this slice's scope:
   `OPENSEARCH_ADMIN_PASSWORD` still defaults to a published value at
   `backend/onyx/configs/app_configs.py:470`, and `POSTGRES_PASSWORD` defaults to
   `password` at `:637`. No compose path can reach them now, because every owned
   variant injects an explicit value, but a process started outside compose can.
   Recommended follow-up: a startup validator in `backend/onyx/main.py` modelled
   on `verify_user_auth_secret`, which warns under `DEV_MODE` /
   `INTEGRATION_TESTS_MODE` and raises otherwise. That is a backend change and
   needs its own slice.
3. `ENCRYPTION_KEY_SECRET` is optional in the default variant, so a deployment
   run from `docker-compose.yml` without it still stores encrypted columns as
   plaintext bytes. The installers generate one; a hand-written `.env` may not.
4. The compose-internal Redis has no password. It is not published to the host in
   any owned variant. Out of scope here.
5. `docker-compose.search-testing.yml` still carries the published OpenSearch
   default and `docker-compose.airgap-test.yml` carries a clearly labelled
   CI-only dummy auth secret. Both are test-only, non-owned artifacts on internal
   networks. Left unchanged deliberately; changing them would alter CI behavior
   without a security gain.
6. The `api_base` re-entry guard for LLM providers is `MULTI_TENANT`-only, so a
   self-hosted admin can repoint a provider without re-entering its key. Recorded
   by the capability audit; unchanged here.
7. `deployment/helm` and `deployment/aws_ecs_fargate` were not hardened. They are
   not the TON deployment path and are outside this plan's scope.

## Alembic blocker

Unchanged and still open: the live local database references unknown revision
`6e8f0a2b1c35`. This slice did not stamp, upgrade, downgrade, repair, or read
`alembic_version`, and authored no migration. Carry it into the Plan 003
readiness process; TON-SEC-007-A depends on it.

## Live database

Untouched. No migration, no schema change, no data write, no `alembic` command.
The only database-adjacent action was a read-only `information_schema` type
lookup while tracing `custom_config`.

## Checks executed

| Check | Result |
|---|---|
| `pytest backend/tests/unit/ton/test_deployment_profile.py` | 100 passed |
| Same test against the unmodified baseline worktree | 48 failed — reproduces the unsafe state the slice removes |
| `pytest backend/tests/unit/ton` | 128 passed, 1 pre-existing failure |
| `ruff check` / `ruff format` / `ty check` on the new test | clean |
| `ods generate-compose --write` then check mode | exit 0, no drift |
| Second generator run | no further diff |
| `go test ./internal/deploy/deployfiles/...` | 3 passed, including the embedded drift gate |
| `go test -run TestRunInstallFreshLiteNoPrompt` | passed with the new credential assertions |
| `go test -run TestRerunRestartKeepsEnvUntouched` | passed — upgrade keeps generated secrets |
| `go vet ./internal/deploy/...` | clean |
| PowerShell parse of `install.ps1` | clean |
| Regex scan of all owned artifacts | no published default remains |
| `git diff --check` | clean |

End-to-end `docker compose config` runs, in a temporary directory so the local
`.env` and the running stack were untouched. Only clearly synthetic values were
used, and no value appears in any output:

| Scenario | Result |
|---|---|
| default variant, no credentials | exit 1, names `OPENSEARCH_ADMIN_PASSWORD`, no value shown |
| default variant, synthetic credentials | exit 0, every expected service renders |
| prod variant, no `ENCRYPTION_KEY_SECRET` | exit 1, names the variable |
| prod variant, synthetic credentials | exit 0 |
| prod variant, `USE_IAM_AUTH=true` and no `POSTGRES_PASSWORD` | exit 0 — the IAM path still renders |

Pre-existing failures, identical in a pristine `80e76cfb12` worktree and
unrelated to this slice:

- `backend/tests/unit/ton/test_contract_matrix.py::test_vale_norte_report_remains_candidate_evidence`
  looks for `plans/ton/decision-log.md`; the file is at
  `plans/ton/backend/decision-log.md`. Plan 001/002 documentation drift.
- `cli` `TestRerunAsksOnceAndCancels` and `internal/markdown` `TestGolden` fail on
  this Windows checkout, which stores the working tree with CRLF.

Environment notes: `uv` and `go` are not on PATH here. Python checks used the
repository `.venv`; the generator was run from the `ods` binary shipped in that
`.venv`; Go tests ran in a `golang:1.27.1-alpine` container with the repository
mounted. `pytest` ran with `-p no:cacheprovider` because the cache directory is
not writable.

## Scope confirmations

- No TON domain structure was created or modified. No `Rule`, `RuleVersion`,
  `AnalysisRun`, `Finding`, `Occurrence`, `Opportunity`, TON report, TON schedule,
  contract, unit, or specialist orchestration code was touched.
- No capability or tier-gate work. `license_enforcement_config.py`,
  `tier_gate.py`, `tier.py`, the `Tier` enum, the user-group gate, the branding
  gate and group availability are unmodified. That remains Plan 008a.
- No frontend product work. Nothing under `web/`, `mobile/`, `desktop/`,
  `widget/` or `extensions/` was touched. FE-004 was not executed.
- Plan 002 was not reimplemented. Telemetry defaults were verified, not changed.
