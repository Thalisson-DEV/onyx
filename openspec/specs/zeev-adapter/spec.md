# zeev-adapter Specification

## Purpose
Linha de base da integração com o Zeev (sistema de processos/workflow da Vale Norte, tenant
`https://nucleo.zeev.it`, API REST v2). Entregue em BE-004A (`8259239cf0`) e BE-004B (`c38c3692e1`):
adaptador somente leitura e catálogo de fontes. Ainda **não** há sincronização para `SourceSnapshot`,
tabelas, mapeamento de domínio, ferramenta de especialista nem ingestão de arquivos (BE-004C pendente,
change `zeev-integration`). Código: `backend/onyx/ton/zeev/{client,discover,catalog,catalog_cli,models}.py`;
testes `backend/tests/unit/ton/test_zeev_{readonly,catalog}.py`; documentos
`plans/ton/integrations/{004a-zeev-readonly-foundation,004b-zeev-source-discovery,zeev-api-audit,zeev-source-catalog}.md`.
Na cobertura do produto o Zeev aparece como `SOURCE_ZEEV` PARCIAL ("contexto de processos").

## Requirements

### Requirement: Read-only transport firewall
The Zeev client SHALL reject any operation outside a fixed read-only allowlist before any network I/O, even though the available account has write rights; impersonation, integration execution, file write and password routes SHALL be blocked.

#### Scenario: Write operation attempted
- **WHEN** code calls a non-allowlisted operation such as completing an assignment
- **THEN** the client raises before sending any request

### Requirement: Authentication, retry and log safety
The client SHALL authenticate with `ZEEV_TOKEN` or login/password through `POST /api/2/tokens`, cache temporary tokens below their ten-minute lifetime, refresh once after a 401, retry at most three times with `Retry-After` capped at 30 seconds, verify TLS, and never log tokens, response bodies or form values.

#### Scenario: Expired token
- **WHEN** a request returns 401
- **THEN** the client refreshes the token once and retries, failing if the second attempt is also 401

### Requirement: Value-free source catalog
The catalog service SHALL list startable and editable flows joined by numeric flow ID, their form fields and task design elements, value-free shape profiles of a bounded instance sample, and keyword-based candidate areas marked as human-review hints, without storing form values, personal data or file contents.

#### Scenario: Catalog run
- **WHEN** the catalog CLI runs against the tenant
- **THEN** it reports flows, fields and design elements with method/path counts only, and stores no instance values
