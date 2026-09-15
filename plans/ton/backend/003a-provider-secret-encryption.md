# Plan 003a — provider secret encryption

> **Executor instructions**: This is the security prerequisite slice split out of
> Plan 003 by `003-readiness.md` §18 and §21. It touches existing
> credential-bearing tables and creates no TON domain table. Run it before 003b.
>
> **Drift check (run first)**: from the repository root, run `git status --short`.
> Then read the current Alembic head from `backend/alembic/versions` — take the
> revision no other file names as `down_revision`. Do not hardcode a head.

## Status

- **State**: DONE
- **Priority**: P0
- **Effort**: M
- **Risk**: HIGH (an existing table holding live credentials)
- **Depends on**: `001-baseline-contracts.md`, `002-security-privacy.md`,
  `007-deployment-hardening.md`, `003-readiness.md`, decision 7a
- **Blocks**: `003b` uses this revision as its `down_revision`
- **Category**: security
- **Closes**: SECURITY-08 / TON-SEC-007-A, readiness blocker B4
- **Baseline commit**: `73b8ec4d34c34eb90abc784bcff542117164f515` (`main`, equal to
  `origin/main`)
- **Executed at**: 2026-09-15

## Issues to Address

`LLMProvider.custom_config` and `VoiceProvider.custom_config` stored provider
credentials as plaintext `JSONB`. The dict holds AWS Bedrock keys, Vertex
service-account JSON and LM Studio bearer tokens, while the sibling `api_key`
column on the same tables was already encrypted. Anything with database access
could read the values with a plain `SELECT`.

API masking was not a substitute. It decided what to hide from a key-name
substring list, and `custom_config` accepts arbitrary keys, so a secret stored
under an unrecognised key name was returned in full.

## Storage change

| | Before | After |
|---|---|---|
| `llm_provider.custom_config` | `jsonb`, nullable | `bytea`, nullable, `EncryptedJson` |
| `voice_provider.custom_config` | `jsonb`, nullable | `bytea`, nullable, `EncryptedJson` |

The ORM columns are now
`Mapped[SensitiveValue[dict[str, str]] | None]` and
`Mapped[SensitiveValue[dict[str, Any]] | None]`, matching the
`Credential.credential_json` precedent. Nullability, the Python dict write
contract and the `{}`-versus-`None` distinction are unchanged.

No new cryptography, library, key variable or rotation mechanism was introduced.
The existing `EncryptedJson` type decorator and `ENCRYPTION_KEY_SECRET` carry the
work.

## Alembic chain

| | |
|---|---|
| Previous head | `ad99acb9be41` |
| New revision | `714172b66b07` |
| `down_revision` | `ad99acb9be41` |
| Heads after the change | one |

Pre-flight confirmed a single main-chain head, and that the live database
reported `ad99acb9be41` — a revision present in the repository — with 151 public
tables and zero TON tables.

## Migration strategy

Follows revision `0a98909f2757`, per readiness §18.3:

1. count rows holding a non-null configuration;
2. if any exist, prove encryption is real (below) and abort otherwise;
3. add a temporary `LargeBinary` column;
4. read each plaintext value through a lightweight `sa.Table` literal — the
   application ORM is not imported into the migration;
5. re-encrypt with `encrypt_string_to_bytes(json.dumps(...))`;
6. assert no plaintext row is left without an encrypted counterpart;
7. drop the plaintext column and rename the encrypted one over it.

Existing rows transition in place. No provider row is deleted, no credential is
reset, and no operator has to recreate providers during upgrade. Postgres DDL is
transactional and the whole revision runs in one Alembic transaction, so any
failure — including step 6 — rolls the slice back rather than half-converting.
The delete-the-rows shortcut used by `b4950827c0dd` was rejected: that feature
had no production data, this one does.

## Two execution guards

`require_real_encryption()` runs before any credential row is written. Both
invariants are required, then proved:

1. `global_version.is_ee_version()` must be true;
2. the resolved `_encrypt_string` must come from `ee.onyx.utils.encryption`;
3. `ENCRYPTION_KEY_SECRET` must be set;
4. a fixed probe string must encrypt to something other than its own bytes and
   decrypt back.

Check 2 exists because `fetch_versioned_implementation` silently falls back to
the Community module when the `ee` package is absent, so the flag alone is not
proof. Checks 3 and 4 exist because the Community `_encrypt_string` returns
`input_str.encode()` and the EE read path decodes such a row without raising —
a cleartext row would read back perfectly, with no read-time signal. Converting
under either condition is worse than leaving the column as `JSONB`.

The guards are gated on there being at least one row to convert. A database with
no stored configuration has no credential at risk, so CI and a fresh install
reach head without a key. `backend/alembic/env.py` already calls
`set_is_ee_based_on_env_variable()`, so the edition a migration sees matches the
application processes.

## Downgrade

`downgrade()` exists, executes, and is deliberately lossy. It drops the encrypted
column and recreates an empty nullable `JSONB` column, matching the pre-upgrade
schema contract. It never decrypts: a downgrade must not become a
credential-decryption oracle. Provider rows themselves survive.

**Operators must re-enter provider custom configuration through the admin UI
after a downgrade** — Bedrock keys, Vertex credentials, LM Studio tokens and
Azure voice settings included.

## Whole-dict API masking

The key-name heuristic is replaced by an allow-list inversion in
`backend/onyx/llm/custom_config_masking.py`. Every value is masked unless its key
is a known setting; an unknown key name is treated as credential material.

Allowed through unmasked: the UI-only form-state keys
(`UI_ONLY_CONFIG_KEYS`, which covers `BEDROCK_AUTH_METHOD` and the API-surface
selectors), `aws_region_name` / `AWS_REGION_NAME` / `AWS_REGION`,
`vertex_auth_method`, `vertex_location`, `vertex_project`, and the voice keys
`speech_region` and `stt_languages`.

Structure is preserved: every key stays present, so a client can still see that
configuration exists and which entries are set. Only values are hidden. Nested
dicts and lists are masked recursively.

`restore_masked_custom_config` is the exact inverse and is applied on the write
path, so resubmitting an unmodified form cannot persist a placeholder over a real
credential. The LLM admin API already had this restore step; the voice upsert
endpoint gained one, because its view now masks values it previously returned in
the clear.

No frontend file was changed. The admin forms keep receiving the same shape —
real values for the settings they drive, masked strings for everything else.

## Writers and readers

Writes still accept a plain dict. Encryption is a storage concern, so no API
shape changed. Verified writers: the admin provider create/update path
(`db/llm.py::upsert_llm_provider`), voice provider management
(`db/voice.py::upsert_voice_provider`), image-generation shadow providers, EE
seeding, tenant provisioning, and the non-persisted test-connection providers.
No core-SQL or `bulk_insert_mappings` write to either column exists.

Reads unwrap at the boundary via a new `read_sensitive_dict` helper in
`onyx/utils/sensitive.py`. `LLMProviderView.from_model` and
`LLMProviderDescriptor.from_model` are the choke points that cover the LLM
factory, `MultiLLM` initialisation, model-fetch endpoints and Celery workers,
which all reach providers through the view. Direct ORM readers were updated
individually: the Bedrock bearer-token and LM Studio resolvers, the test-LLM and
upsert handlers, the contextual-cost endpoint, image generation, the
image-generation admin API, `tool_constructor`, and the voice factory. The helper
also accepts a plain dict, so a temporary in-memory provider still works.

`SensitiveValue` raises on `str()`, iteration and subscript, so a missed reader
fails loudly instead of silently degrading.

## Wrong key behaviour

A wrong key raises `ValueError` (or `UnicodeDecodeError`) from the existing EE
decrypt path. It does not return garbage as valid JSON, does not fall back to
plaintext, does not overwrite or clear the row, and does not expose raw
ciphertext. Verified with a raw-bytes comparison before and after the failed
read.

## Rotation

`rotate_encryption_key::_discover_encrypted_columns()` walks the mappers and
collects every `EncryptedJson` / `EncryptedString` column, so both converted
columns joined rotation with no change to the rotation architecture. Two
regression tests pin this — one in the SECURITY-08 file, one in
`test_rotate_encryption_key.py` where rotation invariants live — so reverting
either column to `JSONB` fails a test instead of silently dropping it from
rotation.

Rotation stays manual: `python -m onyx.db.rotate_encryption_key`, passing the
previous key. No automatic rotation was added.

`backend/scripts/rotate_llm_provider_keys.py` needs no change; it rotates a
provider's own API key, not the encryption key.

## Decision 7a — encryption key custody (recorded, not implemented)

`ENCRYPTION_KEY_SECRET` is a Vale Norte deployment secret owned by the
infrastructure owner. It is not application source code and not a
developer-owned credential. It is never committed, never embedded in a generated
artifact, never logged and never written into documentation.

It is injected externally at deployment time, preferring an existing deployment
secret mechanism. Where the initial self-hosted deployment has no secret manager,
an operator-controlled environment or secret file outside the repository with
restrictive filesystem permissions is acceptable. This slice invents no new
secret-management platform.

The infrastructure owner retains a secure backup and custody procedure: losing
the key can make encrypted provider credentials unrecoverable. An authorized
deployment engineer may configure or inject the value; it must not persist in
source control, fixtures, documentation, chat logs or application logs.

Rotation is manual, using the repository's existing mechanism. Rotate
immediately after suspected exposure, and when administrative custody materially
changes where the infrastructure owner requires it. Planned periodic rotation is
an operational choice.

**No key value is recorded anywhere in this repository.**

## Capability and edition boundaries

Plan 008a's architecture is untouched. `LICENSE_ENFORCEMENT_ENABLED` keeps its
default, `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` stays unset, no paid Onyx
license is required, and EE dispatch stays active in the intended TON
deployment. No license was fabricated or installed. Encryption implementation
dispatch and commercial entitlement remain separate concerns: the migration
guard asserts which implementation resolves, never an entitlement.

## Tests

| Suite | Command | Result |
|---|---|---|
| Repository migration gate | `pytest tests/integration/tests/migrations/` | 15 passed, 1 skipped |
| SECURITY-08 | `pytest tests/external_dependency_unit/ton/test_provider_secret_encryption.py` | 19 passed |
| Rotation | `pytest tests/external_dependency_unit/db/test_rotate_encryption_key.py` | 16 passed |
| Affected unit suites | `pytest tests/unit/onyx/server/manage tests/unit/onyx/utils tests/unit/ton` | identical to the baseline at `HEAD` |

`backend/tests/external_dependency_unit/ton/test_provider_secret_encryption.py`
covers the readiness §20 list: raw bytes are not the plaintext; the ORM
round-trips the original dict; the API response is masked; masking also protects
a synthetic secret under an unknown key name; an update stays encrypted; a
missing key aborts the migration; a Community-resolved run aborts the migration;
a wrong key fails safely; `repr`, `str`, subscript, iteration and logging do not
expose the value; an independent session standing in for a worker decrypts the
configuration; and rotation discovery includes both columns.

The migration-level cases each run against their own throwaway database, cloned
from a template at the pre-003a revision, so the real `upgrade()` and
`downgrade()` execute without touching the test database.

### Negative control

On a disposable database seeded with synthetic providers, verified in
`test_plaintext_becomes_unreadable_and_survives_the_transition`:

- before 003a: the raw `custom_config` value contains the readable sentinel;
- after 003a: the column is `bytea`, the row is still present, and the sentinel
  value and sentinel key name are both absent from the stored bytes.

`alembic check` was not used as a gate, and
`alembic -n schema_private upgrade head` was not run — readiness §17.3 proved
both inappropriate here.

### Environment limitations during verification

`uv sync` cannot complete on this Windows host (`chonkie` needs MSVC build
tools) and `litellm==1.93.0` needs a Rust toolchain, so suites importing
`litellm` could not run locally. A baseline comparison against a clean `git
worktree` at `HEAD` showed the same 60 failures before and after this slice: 49
missing-`litellm` imports, 2 Windows process-isolation crash codes, and one
pre-existing path drift in `tests/unit/ton/test_contract_matrix.py`, which looks
for `plans/ton/decision-log.md` while the file is at
`plans/ton/backend/decision-log.md`. `ods check-getattr` and
`ods check-lazy-imports` have no Windows entry point; the touched files add no
`getattr` and no heavy module-level import. `ruff check`, `ruff format` and
`ty check` are clean apart from the same unresolved `litellm` import.

## Deferred, intentionally

Fields with the same shape that are still plaintext, recorded rather than pulled
into this migration:

- `InternetSearchProvider` configuration;
- `InternetContentProvider` configuration;
- tracing-provider configuration;
- hook configuration.

Also unchanged and pre-existing: AES-CBC here is unauthenticated, with no MAC or
AEAD, and the stored blob carries no key identifier or version byte. Neither
blocked SECURITY-08. Both remain follow-ups.

## Operational actions required before applying to a real deployment

1. Inject `ENCRYPTION_KEY_SECRET` for the api_server, the workers **and** the
   process that runs `alembic upgrade`, using the same value. The migration
   aborts rather than writing plaintext if it is missing.
2. Confirm EE resolution is active in the migrating process. The default
   `LICENSE_ENFORCEMENT_ENABLED=true` already satisfies this; no license is
   needed.
3. Take a database backup before upgrading. The downgrade cannot restore
   configuration values.
4. Apply the migration and restart the application processes together. A process
   running this code against an un-migrated database, or an un-migrated process
   against a migrated database, will fail on provider reads.
5. Record the key in the infrastructure owner's custody procedure, with a
   backup, before the first encrypted write.
6. If the database was ever exposed while these columns were plaintext, rotate
   the affected provider credentials at the provider. Encrypting at rest does not
   retroactively protect a value that already leaked.

## Confirmations

- No real credential value was read, written, printed or logged. Every
  credential-shaped value in the tests is a synthetic sentinel created inside the
  test.
- No TON domain table was created. The slice adds no table at all.
- No business rule was implemented or seeded. No S-rule, T-rule, threshold, NC
  mapping or Vale Norte value appears in any changed file.
- No frontend product work occurred. No file under `web/`, `desktop/` or
  `mobile/` was changed. FE-004 was not executed, navigation and visual design
  are untouched, and no occurrences or reports UI exists.
- The live development database was not migrated, stamped, downgraded or
  repaired. All verification ran against a disposable `postgres:15.2-alpine`
  container, removed afterwards.
