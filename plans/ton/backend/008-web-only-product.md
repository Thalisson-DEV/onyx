# Plan 008: Ship the TON web-only product surface

> **Executor instructions**: Run this final product slice only after Plans 001,
> 002, 006 and 007 are DONE. Preserve shared API, authentication, queue,
> storage, search, worker, beat, health and monitoring contracts. Do not remove
> mobile, desktop, widget or extension consumers from lack of V1 UI usage.
>
> **Drift check (run first)**: from the repository root, run `git status --short`
> and `git diff --stat -- web`. Stop if the current consumer matrix or cited
> contract differs from `architecture-map.md`.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: HIGH
- **Depends on**: `001-baseline-contracts.md`, `002-security-privacy.md`,
  `006-reports-schedules-admin.md`, `007-deployment-hardening.md`
- **Category**: direction
- **Planned at**: commit `a0370f232b`, 2026-09-13

## Why this matters

TON V1 ships one web experience. Onyx still exposes SaaS, billing, Craft and
non-web surfaces, while the web boot path initializes analytics and product
gates. This slice applies an explicit TON configuration at the edge and keeps
shared backend contracts and infrastructure available.

## Current state

- `web/src/app/layout.tsx:4-25,137-176` loads product providers, GTM,
  PostHog/custom analytics and gating.
- `web/src/app/providers.tsx:1-40` initializes PostHog and session recording.
- `web/src/providers/ProductGatingWrapper.tsx:7-25` gates by application status.
- `web/src/lib/constants.ts:18-67` contains auth, EE, analytics, GTM, cloud and
  registration flags.
- `web/src/lib/billing/svc.ts:1-70`, `web/src/app/admin/billing/page.tsx:1-32`
  and `web/src/components/errorPages/AccessRestrictedPage.tsx:20-68` expose
  billing/license flows that need an approved TON surface policy.
- `web/src/proxy.ts:138-145` and `web/src/lib/chat/hooks.ts:146-147` carry
  redirect or window-message boundaries that require allowlists.
- Shared contracts remain required: `/chat/*`, auth/session, stream resume,
  project/file upload, search, FileStore, PostgreSQL, Redis, OpenSearch,
  Celery workers, beat, health and monitoring.
- Mobile, desktop, widget and extension UX are out of scope. Telegram is the
  first planned external adapter. WhatsApp follows later. Neither is a core
  V1 dependency.

## Important Notes

Use the approved surface matrix in `architecture-map.md` and the configuration
contract in `target-architecture.md`. Proposed TON settings are
`TON_WEB_ONLY=true`, `TON_EXTERNAL_TELEMETRY_MODE=off`,
`TON_TRACE_CONTENT_MODE=metadata`, `TON_PRODUCT_SURFACES=ton`,
`TON_REPORTS_ENABLED=true`, `TON_EXTERNAL_CHANNELS` empty, and
`TON_SOURCE_WRITES=false`. Search existing names before adding settings and do
not make TON depend on PostHog.

## Implementation strategy

1. Freeze the surface matrix. Preserve web auth, chat, files, search, settings,
   permissions and operational health. Hide or replace only approved billing,
   Craft, SaaS and marketing UI. Keep shared contracts until consumer evidence
   and a deprecation gate support removal.
2. Make web boot work with PostHog absent. Default PostHog, session recording,
   GTM, custom scripts and Sentry content capture off or metadata-only. Redact
   query strings and validate `postMessage` source and origin.
3. Add TON web navigation and admin/report screens from Plan 006. Do not alter
   generated deployment files or backend domain behavior in this slice.

## Scope

**In scope**:

- `web/src/app/layout.tsx`, `web/src/app/providers.tsx`;
- `web/src/providers/ProductGatingWrapper.tsx`;
- `web/src/lib/constants.ts`;
- `web/src/lib/billing/svc.ts`, `web/src/app/admin/billing/page.tsx`,
  `web/src/components/errorPages/AccessRestrictedPage.tsx`;
- `web/src/sections/sidebar/AccountPopover.tsx`;
- `web/src/proxy.ts`, `web/src/lib/chat/hooks.ts`;
- `web/src/ton/ton-web-only.test.tsx` (create).

**Out of scope**:

- backend domain, connectors, Telegram, WhatsApp, NG/Keevo and source writes;
- mobile, desktop, widget and extension implementation or removal;
- generated compose, CLI embedded artifacts, Nginx, Supervisor and worker
  redesign;
- new analytics providers, customer-data exports and live infrastructure
  mutation.

## Commands you will need

Run each block from the repository root:

```text
cd web
bun run test -- src/ton/ton-web-only.test.tsx --runInBand
bun run types:check
bun run lint
bun run build
```

Expected result: the named web test, type check, lint and production build pass.
The test must verify TON-only navigation, hidden unsupported surfaces, preserved
chat/auth/file/project contracts, PostHog/GTM/session-recording defaults,
allowlisted redirects and accepted/rejected message origins.

## Tests

Create the named web spec before running it. Use the existing web test and E2E
patterns. Cover login, chat, upload, project/file access, report navigation,
admin authorization, analytics-off defaults, network payload redaction and
shared-contract preservation. Do not use a test that requires external
telemetry or a real secret.

## Done criteria

- [ ] TON has one supported web experience with explicit configuration.
- [ ] Shared API and authentication contracts remain compatible.
- [ ] Shared Redis, PostgreSQL, OpenSearch, FileStore, Celery, beat, health and
      monitoring dependencies are preserved.
- [ ] Unsupported SaaS surfaces are hidden only after the Plan 001 matrix and
      consumer gate pass.
- [ ] Browser analytics and content-bearing telemetry are off or metadata-only
      by default, with origin and network tests.
- [ ] Named web test, typecheck, lint and build pass.
- [ ] No mobile, desktop, widget, extension, Telegram or WhatsApp implementation
      is required for V1.

## STOP conditions

- Stop if a surface change breaks a shared API, auth, stream, file or project
  contract.
- Stop if preserving web behavior requires deleting shared services or workers.
- Stop if PostHog or another vendor is required for TON boot or content capture.
- Stop if a route or message origin cannot be allowlisted.
- Stop if mobile, desktop, widget or extension removal lacks consumer evidence
  and a deprecation release gate.

## Maintenance notes

Update the surface matrix and this test when a web route, shared contract,
analytics provider or deployment service changes. Re-run Plan 007's generated
artifact sync after any deployment change; do not modify those files here.
