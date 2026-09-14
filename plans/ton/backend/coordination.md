# TON frontend and backend coordination

This document assigns cross-layer ownership. It does not replace either
roadmap.

## Ownership

### Frontend owns

- Visual presentation and copy.
- Navigation and TON terminology.
- Layout composition and client-side visibility.
- Product branding and existing frontend feature composition.
- Frontend states, routes, and screens.
- Accessibility, responsive behavior, dark theme, and user interaction.

### Backend owns

- Authorization, capabilities, and server-side access control.
- Persistence, domain entities, APIs, and validation.
- Deterministic rules and the findings or occurrences lifecycle.
- Reports lifecycle and agent execution.
- Source permissions and background execution.
- Integrations, telemetry and privacy enforcement, and business data.

## Shared contract

Frontend can hide a route or action for usability. Security must never depend
on frontend visibility.

For example, frontend can hide an administrative entry. The backend must still
reject unauthorized direct access.

Each roadmap records dependencies across this boundary. Frontend work does not
implement backend contracts. Backend work does not decide presentation or
interaction.

## Coordination matrix

| Backend plan | Frontend consumer | Contract relationship |
|---|---|---|
| 001 | TON-FE-000 | Both freeze the baseline and shared contract inventory. |
| 002 | All frontend slices | Frontend consumes security and privacy constraints. |
| 003 | TON-FE-008 and TON-FE-009 | Occurrence, finding, and report contracts precede UI. |
| 004 | TON-FE-006 and TON-FE-007 | File lifecycle and source contracts precede UX claims. |
| 005 | TON-FE-005 | Specialist UI consumes authorized agent capabilities. |
| 006 | TON-FE-008 and TON-FE-009 | Lifecycle, schedule, and reporting APIs precede UI. |
| 008 | TON-FE-003 | Backend gates remain authoritative when surfaces are hidden. |
| 009 | TON-FE-010 | Telegram administration waits for the channel contract. |

## Dependency rule

Record a cross-layer dependency in both roadmaps before implementation. Stop
when a task needs an unavailable contract from the other layer.
