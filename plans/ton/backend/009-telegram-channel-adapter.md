# Plan 009: Add the Telegram channel adapter

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: HIGH
- **Depends on**: 002, 005, 006
- **Category**: integration
- **Current state**: BLOCKED until the backend channel contract exists

## Issues to Address

Telegram is the first planned external TON channel. It needs a secure adapter
for authorized commands, status, delivery, and report responses.

The adapter must not own domain logic. Web and Telegram must use the same TON
application and domain capabilities.

## Important Notes

- WhatsApp follows later through the same channel boundary.
- Backend authorization applies to every Telegram request.
- Channel identity must map to an authorized TON user and tenant.
- Credentials, replay rules, rate limits, and delivery state need approval.
- This plan does not authorize Telegram work during the baseline phase.

## Implementation strategy

Define a channel port after Plans 002, 005, and 006 provide stable contracts.
Build Telegram as an adapter for that port. Keep transport types outside the
detector, findings lifecycle, reports lifecycle, and agent services.

Document frontend dependencies before any administration or status screen is
built. Keep credentials and enforcement on the server.

## Scope

In scope: the approved Telegram transport, identity mapping, delivery state,
audit events, and channel administration API.

Out of scope: TON core rules, Telegram-specific domain behavior, WhatsApp, and
frontend implementation.

## Tests

Create named contract and integration tests before implementation. Cover
authorization, tenant isolation, replay, rate limits, delivery failures, and
audit events. Prove that TON core imports and runs without Telegram.

## Done criteria

- [ ] The approved channel contract exists.
- [ ] Telegram uses shared TON application and domain capabilities.
- [ ] Server authorization protects every operation.
- [ ] Delivery and audit states are deterministic.
- [ ] TON core has no Telegram dependency.
- [ ] Frontend dependencies are documented for TON-FE-010.

## STOP conditions

- Stop if the backend channel contract is unavailable.
- Stop if identity, credential, replay, or delivery rules are unapproved.
- Stop if the adapter requires channel logic in TON core.
- Stop if work would start before Plans 002, 005, and 006 are complete.
