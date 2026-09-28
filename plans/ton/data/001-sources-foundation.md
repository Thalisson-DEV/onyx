# DATA-001: Sources foundation

## Issues to Address

Preserve original input bytes and acquisition history. Keep logical source identity independent from filenames and providers.

## Important Notes

The existing `ton_source_snapshot` table already supports findings, analysis runs, and report revisions.
DATA-001 extends it. Legacy receipts keep their IDs and nullable raw-capture fields.
The existing FileStore supports PostgreSQL large objects, S3, Azure, and GCS.
Tenant sessions select the tenant schema and database. Sources use that boundary.

## Implementation strategy

`Source -> ImportRun -> SourceSnapshot` is the persistent chain.
Source keys are stable and unique within a tenant. Update requests exclude them.
ORM and database guards reject key changes.
Acquisition can change between FILE_UPLOAD, API, DATABASE, MANUAL, and CONNECTED_SERVICE.
Source status is ACTIVE, INACTIVE, CONFIGURING, or ERROR.
Sensitivity is INTERNAL, CONFIDENTIAL, or RESTRICTED. Default: RESTRICTED.
Only active FILE_UPLOAD sources accept assisted uploads.
Active API, DATABASE, MANUAL, and CONNECTED_SERVICE sources accept internal JSON capture.
An adapter supplies bytes later. DATA-001 does not connect to any provider.

Runs transition from PENDING to RUNNING, then SUCCEEDED or FAILED.
PENDING can also fail. A successful run requires exactly one snapshot.
Each run preserves the acquisition method and initiating user.
The run ID is the correlation reference. No scheduler runs in this slice.

Each upload receives a new snapshot and private storage object.
SHA-256 covers the original bytes. The stored bytes are read back and verified before success.
An exact duplicate links to the earliest matching snapshot of the same source.
The source lock serializes final duplicate selection, not storage transfers.
Different bytes create a new version, even when the filename is unchanged.
This choice preserves every upload action. It does not save duplicate storage space.

Raw snapshots reject ORM changes and database UPDATE/DELETE operations.
Legacy receipts retain their previous behavior.
Raw completeness and schema conformity remain false until future validation exists.
SourceLocator supports snapshot ID, sheet, row, page, source key, and JSON pointer.
ImportProfile is deferred to DATA-002. No column mappings or business records exist here.

## Storage and failure handling

FileStore stores bytes. The database stores IDs, metadata, SHA-256, and lineage.
Storage IDs are generated internally and excluded from API responses.
A committed run reserves its storage ID before writing bytes.
Storage failure or metadata failure marks the run FAILED and attempts object deletion.
Failed deletion leaves cleanup_required=true. The cleanup endpoint permits retries.
A database outage leaves a visible incomplete run and its reservation.
After confirming the importing process stopped, an operator can fail the run through the repository state transition, then retry cleanup.
Never clean an active importer. Never clean a successful run.
A lost commit acknowledgement requires inspecting run status before retrying.

## Security and RBAC

Real client files are sensitive. Raw uploads are untrusted inputs.
XLS, XLSX, XLSM, CSV, and PDF have bounded format checks.
Connected JSON has a bounded byte check and a container prefix check. Business fields are not parsed.
CSV currently accepts UTF-8 only. OOXML checks container metadata without reading business rows.
Macros, VBA, external workbook links, scripts, and embedded programs are never executed.
The 50 MiB limit applies to original bytes. ZIP metadata has separate expansion limits.
Raw source bytes remain immutable. There is no raw download endpoint.

Sources use existing PermissionGrant and UserGroup memberships.
READ_TON_SOURCES permits source and history reads.
MANAGE_TON_SOURCES permits creation and metadata changes.
IMPORT_TON_SOURCES permits upload and failed-object cleanup.
A capability alone grants no source access. Explicit group sharing is also required.
Writers must belong to every group sharing the source. Global administrators use the existing TON bypass.
Runs and snapshots inherit source access. Request bodies cannot select another tenant.
Group grants are supplied at creation. Group reassignment is deferred.

Existing TonAuditEvent records source creation/update, import start/success/failure, capture, and duplicate detection.
Audit attribution remains best-effort under the existing contract.
The immutable snapshot and durable run provide domain history.
Application logs contain IDs, format, and size. They exclude business content and exception payloads.
LLM access is not enabled at the RAW stage. The chat file route denies TON_SOURCE objects.

## Tests

Use synthetic inputs and migrated disposable PostgreSQL databases.
Test identity, status, acquisition switching, pagination, state transitions, hashes, duplicates, lineage, immutability, ACL, failures, cleanup, format validation, XLSM safety, API validation, and audit.
Run existing TON and Zeev regressions. Preserve the known missing decision-log baseline debt.
Run Ruff, format, static types, migration checks, and git diff --check.

## Temporary-file policy and real smoke

Download only required source files outside tracked paths.
Do not use customer bytes as fixtures. Do not print or document business values.
Delete task downloads after validation. Keep only intentional application storage.
Smoke validation records filename, hash identity, snapshot IDs, run status, and storage verification.
The bounded smoke used two files named `Completo - Jan-Jun 2026 - Lan?amentos Financeiros.xlsx`.
The first had 1,630,737 bytes and SHA-256 `00c6abc19b915d841a7c8cfb8616780f9a6f7c2c30233d6544157029498bbe76`.
The second had 1,631,395 bytes and SHA-256 `b8eb3ebef21fe7ccefd1cebfe995f93949c74b8c146050fd1342bb208e07b71a`.
The first capture was snapshot `0562210f-93b3-46b2-8d18-a5a95a3984f2`.
The second capture was snapshot `fa4bc120-1a5b-44cb-a539-d639c646a057`.
The repeated first file was snapshot `528148d9-1fcb-41c0-a030-b35e1eba70b5`.
It linked to the first capture. All three runs succeeded in the isolated local test database.
The FileStore readback matched each original SHA-256. No worksheet rows were read.
The application log recorded IDs, format, and size only.
The Google Drive fetch tool unexpectedly included worksheet text in its tool output during download.
That output was not copied into code, tests, docs, or application logs.
Temporary downloads are deleted before completion.

## Boundaries and handoff to DATA-002

No parsing of business rows, normalization, corrections, DRE calculations, PBIX ingestion, or agent tools.
Zeev is representable as an API source. Existing Zeev catalog code stays independent.
Keevo can replace file acquisition without changing Source.id or Source.key.
DATA-002 can attach structural profiles and locators to immutable snapshot IDs.
Downgrade refuses while Source rows exist, because it would erase lineage and orphan raw objects.
