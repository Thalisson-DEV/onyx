# Plan 006: Reports, schedules, alerts, and administration

Status: proposed. Priority: P1. Size: large. Risk: high.

Dependencies: Plans 001, 002, 003, 004, and 005. NG/Keevo stays future.
Telegram is the first external channel in Plan 009. WhatsApp follows later.

## Issues to Address

TON needs durable analysis schedules, reports, alerts, and administration. The
repository currently has scheduled task models at
`backend/onyx/db/models.py:6740-6915`, task dispatch and expiry at
`backend/onyx/background/celery/tasks/scheduled_tasks/tasks.py:88-186`, and
execution with `acks_late=False` and broad exception capture at `:209-243`.
Beat configuration is at `backend/onyx/background/celery/apps/beat.py:80-150`.
These are reusable boundaries, not a TON schedule or retry contract.

`backend/onyx/utils/audit.py:53-108` and `:261-310` provide audit patterns.
`backend/onyx/db/models.py:5443` shows the existing UsageReport coupling. TON
reports must not mutate source evidence or depend on Craft/admin-only models.
Plan 003 owns the immutable report snapshot service and its migrations. This
slice consumes that service and owns schedule, alert, projection and API work.

## Important Notes

Add `AnalysisSchedule` and `AnalysisRun` with an explicit business retry
policy. The current scheduled task has no V1 Celery retry: it uses late-ack
disabled, catches exceptions, and records task failure through existing logs.
Do not infer successful analysis from a Celery acknowledgement.

Every run needs an internal execution timeout, a queue expiry, a crash sweeper,
and durable states for queued, running, succeeded, partial, failed, expired,
and cancelled. Commit schedule state before enqueue, or use an outbox. Make
enqueue idempotent. Define overlap and misfire behavior before adding a
database constraint.

Final reports require completed AI interpretation from Plan 003. A detector may
create a candidate, but a report cannot publish a candidate or an
`interpretation_pending` result as final. An alert must point to a report,
Finding, or explicit specialist failure.

In scope:

- `backend/onyx/ton/scheduling.py` (new schedule and run service)
- `backend/onyx/ton/alerts.py` (new alert service)
- `backend/onyx/server/features/ton/api.py` (new web API boundary)
- `backend/onyx/db/models.py` and `backend/onyx/db/ton.py` for approved
  `AnalysisSchedule` and alert relations/operations only;
- `backend/alembic/versions/` and `backend/alembic_tenants/versions/` for the
  corresponding schedule/alert migrations;
- `backend/onyx/background/celery/tasks/scheduled_tasks/tasks.py` and
  `backend/onyx/background/celery/apps/beat.py` for shared task wiring only
- `backend/onyx/utils/audit.py` for TON audit events
- `web/src/app/ton/` and `web/src/sections/ton/` for the V1 web surface
- `backend/tests/integration/ton/test_scheduled_analysis.py`
- `backend/tests/integration/ton/test_alert_lifecycle.py`
- `web/src/ton/ton-admin-report.test.tsx`

Out of scope:

- Mobile, desktop, widget, extension, Telegram, WhatsApp, and NG/Keevo
  implementation
- Craft/admin UsageReport migration
- Generated compose files and CLI embedded deployment artifacts
- Source writes, arithmetic invention, or unapproved rule semantics

## Implementation strategy

1. Define schedule ownership, enabled state, cadence, timezone, target source
   scope, overlap policy, misfire policy, and next-run calculation.
2. Define `AnalysisRun` as the durable unit that references one schedule and
   one orchestration request. Persist commit, enqueue, start, terminal state,
   retry count, expiry, and failure reason.
3. Keep Celery delivery separate from business retry. A retry creates a new
   attempt under one run identity and uses an idempotency key. A crash sweeper
   moves stale running work to a retryable or failed state.
4. Compose reports from immutable canonical snapshots and Finding/Occurrence
   references. Use the append-only and hash policy in Plan 003.
5. Make alert creation, acknowledgement, suppression, and resolution
   idempotent. Preserve a full audit trail. Do not send an external alert until
   its delivery contract is approved.
6. Expose only web API routes needed by TON. Keep existing chat/session routes
   and shared schemas compatible for web, mobile, and desktop consumers.
7. Add administration for schedules, roles, source scope, retention, and
   report visibility. Enforce tenant and role checks at the API and service
   layers.

## Tests

Create the four named specs before running them. Cover:

- commit-before-enqueue, duplicate enqueue, queue expiry, and stale-run sweep;
- `acks_late=False` behavior without treating acknowledgement as success;
- business retry limits, internal timeout, crash, overlap, and misfire;
- successful, partial, failed, and interpretation-pending specialist runs;
- immutable report snapshots, hashes, correction records, and concurrent retry;
- alert deduplication, acknowledgement, resolution, and reappearance;
- tenant, role, schedule-owner, and report-reader authorization;
- web list/detail/report state rendering and API contract preservation.

Run from the repository root:

```text
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_scheduled_analysis.py
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_alert_lifecycle.py
cd web
bun run test -- src/ton/ton-admin-report.test.tsx --runInBand
```

Run migration checks from `backend`:

```text
cd backend
uv run alembic check
uv run alembic upgrade head
uv run alembic -n schema_private upgrade head
```

Expected result: named tests pass; terminal run state, retry, report projection,
alert, and access behavior are deterministic and durable. Plan 003 owns the
report immutability test and must already have passed.

Done criteria:

- Schedule, run, report, and alert contracts are documented and tenant-safe.
- Timeout, expiry, crash, retry, overlap, and misfire behavior is tested.
- Final report publication requires final interpretation.
- Reports are append-only and auditable.
- The named backend and web specs pass with migration checks.

STOP conditions:

- The desired cadence or overlap policy is not approved.
- A report requires mutating a source or inventing a field from NG/Keevo.
- Celery semantics cannot provide the required durable run state.
- A report or alert would expose data outside the actor's source scope.

Maintenance: update schedule, run, report, alert, API, and named specs together
when a state or retry rule changes.
