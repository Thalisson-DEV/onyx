# BE-004A: Zeev read-only foundation

## Issues to Address

TON needs a server-side Zeev source adapter. It must read real flow, form, request, and task metadata without changing the customer's data.

## Important Notes

- The tenant publishes Swagger 2.0 at `https://nucleo.zeev.it/api/2/docs`. See [the API audit](zeev-api-audit.md).
- The available account has write rights. The adapter must reject non-allowlisted operations before network I/O.
- The public login is `POST /api/2/tokens`. The internal login endpoint has no place in this adapter.
- Local secrets belong in ignored `.vscode/.env` or process environment. `ZEEV_TOKEN` takes priority over username and password.
- Data types describe Zeev source records. No TON specialist reads raw Zeev responses.

## Implementation strategy

Add an isolated, typed source adapter under `backend/onyx/ton/zeev`. Give its transport a fixed operation allowlist. Cache temporary tokens in memory. Apply bounded retry, pagination, and date ranges. Add a redacted discovery command for development.

The adapter exposes Zeev source DTOs. It does not create SourceSnapshot, normalization, specialists, or file ingestion. Those layers can consume this adapter later without depending on Zeev HTTP details.

The adapter uses `httpx`, which is already in the backend. It verifies TLS, sets separate connect and read timeouts, and retries at most three times. It caps `Retry-After` at 30 seconds. Temporary tokens are cached for eight minutes, below the documented ten minute lifetime. A 401 triggers at most one controlled refresh. All response bodies stay out of logs.

## Tests

Use local transport tests to prove the mutation firewall before the first authenticated request. Cover auth, token refresh, retries, pagination, parsing, health, and log safety. Then run a small live smoke with local credentials. Run Ruff, formatting, type checks, and `git diff --check`.

The live smoke passed on 2026-09-23. It read flows, services, form definitions, a small instance sample, task records, and pending assignments. See the audit for method and path counts. No mutation was sent.
