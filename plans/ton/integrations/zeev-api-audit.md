# Zeev API audit — BE-004A

## Source and scope

- Tenant documentation: https://nucleo.zeev.it/api/docs/index
- Swagger 2.0 contract: https://nucleo.zeev.it/api/2/docs
- Retrieved: 2026-09-23. API title: `API RESTFul versão 2.0`; API version: `2`.
- The tenant contract has 87 paths and 99 operations. Its host is `nucleo.zeev.it`, and its only declared scheme is HTTPS.
- The `Bearer` security definition uses the `Authorization` header. The token value must have the `Bearer ` prefix.
- The public login operation is `POST /api/2/tokens` with JSON `login` and `password`. It returns `temporaryToken`. The Zeev manual says temporary tokens last ten minutes. `GET /api/2/tokens` checks the current identity and returns a temporary token.
- No `/api/internal/` operation appears in this contract. The adapter must not call that API.

## Operation inventory

`Read` means documented query semantics. `Write` means a side effect. `Unsafe` means the endpoint has unclear or sensitive side effects. `Now` marks adapter operations. The Swagger response schemas and parameters remain authoritative at the link above.

| Method | Path | Meaning | Class | Pagination and key parameters | Response | TON |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/2/tokens` | Exchange login and password for temporary token | Auth | `login`, `password` | User and `temporaryToken` | Now |
| GET | `/api/2/tokens` | Check authenticated identity | Read | None | User and `temporaryToken` | Now |
| GET | `/api/2/requests/flows` | Flows the identity may start | Read | `teamId`, `keywords`, `appCode` | Flow array | Now |
| GET | `/api/2/requests/services` | Services the identity may start | Read | Same filters | Service array | Now |
| GET | `/api/2/flows/edit` | Flows the identity may edit | Read | `flowId`, `flowName`, `deploy` | Flow metadata | Now |
| GET | `/api/2/flows/{flowid}/design/form` | Form field definitions | Read | `flowid` | Field metadata | Now |
| GET | `/api/2/flows/{flowid}/design/elements` | Flow task design | Read | `flowid` | Task elements | Future |
| GET | `/api/2/flows/{flowid}/design/users` | Flow actors | Read | `flowid` | User metadata | Future |
| GET | `/api/2/flows/{flowid}/export` | Full flow export | Read, large | `flowid` | Export JSON | Future |
| GET | `/api/2/instances/{instanceid}` | One request and optional tasks | Read | `instanceid`, task flags | Instance object | Now |
| GET | `/api/2/instances/report` | Filtered request report | Read | Date pair or ID; `pageNumber` from 1; `recordsPerPage` 1–100 | Instance array | Now |
| POST | `/api/2/instances/report` | Filtered request report | Read | Same filters in JSON | Instance array | Now, tested with a local transport |
| POST | `/api/2/instances/report/count` | Count filtered requests | Read | JSON filters | Count | Future |
| GET | `/api/2/instances` | Own requests | Read | Contract has pagination parameters | Instance array | Future |
| GET | `/api/2/assignments` | Own pending tasks | Read | `pageNumber`, `recordsPerPage`, flow/service filters | Assignment array | Now |
| GET | `/api/2/assignments/{assignmentid}` | One assignment | Read | ID | Assignment | Future |
| GET | `/api/2/assignments/{assignmentid}/actions` | Available completion actions | Read | ID | Action list | Future |
| POST | `/api/2/assignments/report` | Filtered pending assignment report | Read | JSON filters | Assignment array | Future |
| POST | `/api/2/assignments/report/count` | Count filtered assignments | Read | JSON filters | Count | Future |
| GET | `/api/2/assignments/user/{userid}` | User tasks | Read | User ID | Assignment array | Future |
| GET | `/api/2/assignments/user/{username}` | User tasks | Read | Username | Assignment array | Future |
| GET | `/api/2/assignments/user/{username}/count` | User task count | Read | Username | Count | Future |
| GET | `/api/2/messages/instance/{instanceid}` | Instance messages | Read | ID | Message array | Future |
| GET | `/api/2/users`, `/api/2/users/{userid}`, `/api/2/users/username/{username}` | Users | Read | User filters or ID | User data | Future |
| GET | `/api/2/teams`, `/api/2/teams/{teamid}` | Teams | Read | Team filters or ID | Team data | Future |
| GET | `/api/2/positions`, `/api/2/positions/{positionid}` | Roles | Read | Role filters or ID | Role data | Future |
| GET | `/api/2/groups`, `/api/2/groups/{groupid}` | Maintenance groups | Read | Group filters or ID | Group data | Future |
| GET | `/api/2/services/{serviceid}` | Service export | Read | ID | Service JSON | Future |
| POST | `/api/2/instances`, `/api/2/instances/subprocess` | Create request | Write | JSON payload | Request | Block |
| PUT | `/api/2/assignments/{assignmentid}`, `/api/2/assignments/instance/{instanceid}/{code}` | Complete task | Write | IDs and payload | Task result | Block |
| POST | `/api/2/assignments/forward` | Forward task | Write | JSON payload | Task result | Block |
| PATCH | `/api/2/formvalues/*` | Update or copy form values | Write | IDs and payload | Form result | Block |
| PATCH | `/api/2/instances/{instanceid}/cancel*` | Cancel or restore request | Write | ID | Request result | Block |
| POST | `/api/2/messages*` | Send message | Write | JSON payload | Message | Block |
| POST | `/api/2/files/createfile`, `/api/2/files/instance-task` | Generate or attach file | Write | JSON or upload | File | Block |
| POST | `/api/2/flows/import`, `/api/2/services/import` | Import app or service | Write | Export JSON | App or service | Block |
| POST, PATCH, DELETE | `/api/2/users*`, `/api/2/teams*`, `/api/2/positions*` | Manage identities and roles | Write | IDs and payload | Varies | Block |
| GET | `/api/2/tokens/impersonate/*` | Create another user's token | Unsafe | User ID or name | Token | Block |
| GET, POST | `/api/2/integrations/{integrationuid}/execute` | Execute integration | Unsafe | Integration ID | Transformed data | Block |
| GET | `/api/2/users/{userid}/password/change-link` | Generate password reset key | Unsafe | User ID | Key | Block |

The contract also lists read endpoints for team positions, group users and permissions, user groups and positions, country/state/city lookup, and timezones. They are outside BE-004A. The adapter allowlist does not expose them.

## Contract details and limits

- `GET /api/2/instances/report` accepts `instanceId` or a paired start, end, or last-task date interval. The tenant Swagger marks these query parameters optional, while the linked Zeev manual specifies one filter set as required. The adapter requires an ID or a bounded date interval.
- `pageNumber` starts at 1. Swagger caps it at 1,000,000. `recordsPerPage` is 1–100. BE-004A applies smaller discovery limits.
- `showPendingInstanceTasks` and `showFinishedInstanceTasks` include tasks in instance reports. Form fields and assignees are optional. The adapter does not request open file URLs.
- Form metadata exposes `flowId`, `fieldId`, `name`, `label`, `typeName`, `required`, `attributes`, task links, and ordering.
- The API lists no read endpoint under `/api/2/files`. Instance form values may carry file metadata. Full attachment download is outside this slice.
- Documented error statuses include 400, 401, 403, 404, 429, and 500. Swagger does not state a rate quota or guarantee `Retry-After`. Observe response headers during the live smoke.
- The public Zeev manual describes a ten minute temporary token. The adapter uses a shorter cache period and refreshes once after a 401.

## Live observations

The local mutation firewall tests passed before the first authenticated request. A real smoke run on 2026-09-23 used only the following methods and path templates:

| Method | Path | Calls | Result |
| --- | --- | ---: | --- |
| POST | `/api/2/tokens` | 1 | Temporary token acquired |
| GET | `/api/2/tokens` | 1 | Authenticated health available |
| GET | `/api/2/requests/flows` | 1 | 5 startable flows |
| GET | `/api/2/flows/edit` | 1 | 35 editable flows |
| GET | `/api/2/requests/services` | 1 | 0 startable services |
| GET | `/api/2/flows/{flowid}/design/form` | 2 | 29 and 27 fields |
| GET | `/api/2/instances/report` | 2 | Two pages, 10 distinct recent instances |
| POST | `/api/2/instances/report` | 1 | One page, 2 recent instances; read semantics confirmed |
| GET | `/api/2/instances/{instanceid}` | 1 | Instance with 2 task records |
| GET | `/api/2/assignments` | 1 | No pending assignments for this user |

Non-sensitive name examples include `NÚCLEO - Chamados de TI` and `NÚCLEO - Solicitações da Gerência`. Task records contain ID, active flag, task descriptor, assignees, executor, timestamps, result, alias, and SLA fields. The live response did not include rate-limit or `Retry-After` headers. No 429 was induced. No business mutation was sent. Do not store response bodies, token values, or form values here.
