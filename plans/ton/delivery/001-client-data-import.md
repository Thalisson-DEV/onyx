# DELIVERY-001: Client data import

## Issues to Address

Clients need one place to find financial sources, upload supported workbooks, and inspect each import.

## Important Notes

- DATA-001 stores files and import runs. DATA-002 parses NG. DATA-003 reviews NG records. DATA-004 parses billing and budget.
- DATA-006 controls mappings and readiness decisions. This workflow does not approve those decisions.
- Source access uses TON permissions and source group scope. The request uses the tenant database session.
- The parsers read workbook data. They do not run macros, Excel automation, or external links.

## Implementation Strategy

The primary page is `/ton/data-sources`. It lists three logical sources: NG, billing, and budget.
Each source shows status, import method, last attempt, last successful import, latest file, counts, and history.
The navigation links the page to financial readiness and DRE.

The page accepts NG XLSX, billing XLS, and budget XLSX files. It sends one file to
`POST /api/ton/data-sources/{key}/imports`. The server checks permission, source state,
file size, media type, extension, and workbook structure before capture. It uses the
existing parser to identify the profile. A file that matches no profile returns a clear error.

The server creates a logical source on the first valid upload by a TON administrator.
It then creates the required import profile and calls the existing capture and parser services.
NG also runs the existing financial review service. When all required inputs exist,
the server requests normalization and readiness refresh through DATA-006.
It does not approve configuration or make the DRE ready.

The upload request is synchronous. The page shows one honest processing state until the response arrives.
It does not display simulated pipeline stages. The result shows imported and rejected records,
warnings, records that need review, records available for analysis, diagnostics, and downstream impact.
The history shows the last 20 attempts per source, including failed captures.
The last successful update uses the full execution history, even when the list is full.
The detail view shows file metadata and the same result. It never shows FileStore paths or raw JSON.

The API provides `GET /api/ton/data-sources` and
`GET /api/ton/data-sources/{key}/imports/{execution_id}` for list and detail.
The frontend maps diagnostic codes to client terms in one file. Unknown codes use a safe generic label.

Read access requires `READ_TON_SOURCES`. Upload requires `IMPORT_TON_SOURCES` and source write access.
The frontend hides upload for readers, and the backend checks access again.
Existing TON audit events record capture start, success, and failure.
They also record parser success, partial success, failure, review, and normalization.
Audit events contain no workbook contents.

## Dev Fixture Isolation

Synthetic READY and NOT_READY records are created in `backend/tests/external_dependency_unit/ton`.
Those tests use `scratch_db.py` to create disposable databases. Production TON modules do not import
the fixture modules. The new API reads only the tenant session and never creates synthetic finance records.
The empty catalog test checks that an administrator sees no source data before an upload.
No new runtime fixture switch or demo endpoint is needed.

## Tests

Focused backend tests use synthetic workbooks. They cover the three sources, both budget profiles,
valid imports, partial import, wrong profile, invalid bytes, inactive source, failed capture,
history, detail, audit, read and import permissions, tenant isolation, and the HTTP route.
Focused frontend tests cover upload, errors, result counts, and navigation.
Chrome DevTools visual checks use the Docker frontend at `http://localhost:3000`.

## Real Smoke

The connected Drive search found no client NG, billing, or budget workbooks.
No real client file was downloaded or imported. No client values were written to tests, logs, or Git.
Real NG, billing, and budget smoke remains pending until those files are available.

The Docker frontend and API were rebuilt from this repository. A Chrome DevTools test at
`http://localhost:3000/ton/data-sources` used the dev account and real API, with no request mocks.
Synthetic NG XLSX, billing XLS, and budget XLSX uploads all completed. The result view showed
2, 1, and 2 imported records, respectively, with no rejected rows or warnings. Each import
appeared in history and linked to financial readiness and DRE. Readiness was refreshed without
approving financial configuration. The synthetic files stayed in the dev database only.

## Known Limitations

- The history list shows the latest 20 attempts. The detail API can retrieve an older attempt by ID.
- Readiness refresh groups budget updates by original filename. Distinct filenames for the same logical
  budget can produce overlapping inputs. Confirm budget file identity before a real client run.
- Historical import details show the import result. Their readiness state is not recalculated on each read.
- A valid import can leave readiness or DRE with pending configuration. Users must resolve those items
  in the governed financial workflow.
- A partial budget import leaves the readiness refresh pending. It does not reuse an older version
  of the same file as current input.
