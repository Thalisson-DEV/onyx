# Plan 007: Harden TON deployment credentials and generated artifacts

> **Executor instructions**: Run this P0 hardening slice after Plans 001 and
> 002. It changes deployment configuration only. Do not print credential
> values, edit generated output by hand, or remove shared workers/services.
>
> **Drift check (run first)**: from the repository root, run `git status --short`
> and `git diff --stat -- deployment cli`. Compare all changes with the
> `a0370f232b` baseline. Stop if unrelated deployment or CLI changes are found.

## Status

- **Priority**: P0
- **Effort**: M
- **Risk**: CRITICAL
- **Depends on**: `001-baseline-contracts.md`, `002-security-privacy.md`
- **Category**: security
- **Planned at**: commit `a0370f232b`, 2026-09-13

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

- [ ] Required credentials use external injection in every owned compose
      variant; no fallback value is committed or logged.
- [ ] Shared web and worker services, queues, storage, health checks and
      monitoring remain present.
- [ ] Generated compose files and CLI embedded copies are synchronized.
- [ ] Named profile and CLI tests pass.
- [ ] `plans/README.md` and `plans/ton/roadmap.md` still identify this as the
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
