# Plan 004: Implement TON file lifecycle and knowledge ingestion boundaries

> **Executor instructions**: Read `architecture-map.md`, `gap-analysis.md` and
> `target-architecture.md`. This slice depends on the domain contract. Preserve
> document ACLs and spreadsheet structure. Do not implement NG/Keevo mapping
> until its contract is supplied.
>
> **Drift check (run first)**:
> `git status --short; git diff --stat -- backend/onyx/file_processing backend/onyx/connectors backend/onyx/indexing backend/onyx/server/features/projects; git diff --cached --stat -- backend/onyx/file_processing backend/onyx/connectors backend/onyx/indexing backend/onyx/server/features/projects`

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: HIGH
- **Depends on**: `001-baseline-contracts.md`, `002-security-privacy.md`, `003-domain-rules-findings.md`
- **Category**: direction
- **Planned at**: commit `a0370f232b`, 2026-09-13

## Issues to Address

TON needs persistent and temporary file semantics, evidence-preserving
ingestion, quality extension points and a private knowledge boundary. Onyx
already supplies FileStore, UserFile, connectors, extraction, chunking,
embedding and OpenSearch, but `.xls` and quality semantics are not validated.

## Important Notes

- `backend/onyx/db/models.py:5558-5645` tracks UserFile status, incognito,
  project/persona links and cleanup indexes.
- `backend/onyx/file_processing/file_types.py:20-100` includes PDF, DOCX,
  CSV, JSON, images, text, XLSX and XLSM. `.xls` is absent from the current
  extension set.
- `backend/onyx/file_processing/extract_file_text.py:829-890` supports
  structured text/images/metadata and an optional external parser.
- `backend/onyx/server/documents/connector.py:325-350` expands ZIP members with
  full reads. Plan 002 must bound this before TON uploads are enabled.
- `backend/onyx/connectors/interfaces.py:45-110` and
  `backend/onyx/connectors/models.py:196-247` are the native source boundary.
- `backend/onyx/indexing/indexing_pipeline.py:1463-1568` and
  `backend/onyx/indexing/chunking/document_chunker.py:25-128` provide the
  ingestion path. `backend/onyx/connectors/file/connector.py:282-373` adapts
  stored files.

## Implementation strategy

Add an explicit TON file lifecycle around existing storage records. Keep
temporary data private and apply no-index/no-retrieval/no-report flags at every
consumer. Preserve sheet, row and column evidence for tabular input. Add
quality results as extension points after normalization. Define only a
read-only NG/Keevo interface; leave it blocked without real access and schema.

## Scope

In scope:

- `backend/onyx/db/models.py` lifecycle fields/relations approved by Plan 003;
- `backend/onyx/db/ton.py` TON file operations;
- `backend/onyx/ton/file_lifecycle.py` (create);
- `backend/onyx/ton/knowledge.py` (create);
- `backend/onyx/ton/integrations.py` (create, interface only);
- `backend/onyx/file_processing/file_types.py` and
  `backend/onyx/file_processing/extract_file_text.py` for approved format work;
- `backend/onyx/server/features/projects/projects_file_utils.py` and
  `backend/onyx/server/documents/connector.py` for bounded uploads;
- `backend/onyx/connectors/interfaces.py`, `backend/onyx/connectors/models.py`,
  `backend/onyx/connectors/file/connector.py` for adapter boundaries;
- `backend/onyx/indexing/indexing_pipeline.py`, chunker, embedder, vector writer
  and user-file adapter only for evidence/lifecycle integration;
- `backend/tests/unit/ton/test_file_lifecycle.py` (create);
- `backend/tests/external_dependency_unit/ton/test_ingestion_formats.py` (create);
- `backend/tests/integration/ton/test_temporary_file_isolation.py` (create).

Out of scope:

- NG/Keevo field mapping or live connector; it remains BLOCKED.
- Telegram, web UX, agent routing, scheduled jobs and generated deployment files.
- Source-system writes or changes to unrelated connectors.

## Commands you will need

Create the named test files first, then run:

```text
uv run pytest backend/tests/unit/ton/test_file_lifecycle.py -xv
uv run --env-file .vscode/.env pytest backend/tests/external_dependency_unit/ton/test_ingestion_formats.py -xv
uv run --env-file .vscode/.env pytest backend/tests/integration/ton/test_temporary_file_isolation.py -xv
```

Expected results: all supported-format, lifecycle, cleanup, promotion,
reconciliation and isolation tests pass. The format specification must include
PDF, XLSX, XLS, CSV, DOCX, images, text, JSON and ZIP. If `.xls` cannot be
handled by an approved parser, mark it unsupported and stop before changing the
public contract.

## Tests

Test the states `uploaded`, `processing`, `ready_temporary`, `ready_persistent`,
`promoted`, `failed`, `deleting`, `deleted` and `orphaned`. Test idempotent
cleanup, safe operational reversal, orphan reconciliation, duplicate uploads,
ZIP limits, password-protected PDF, malformed data, image size, spreadsheet
structure, missing content, source ACL, no-index/no-retrieval/no-report and
temporary-to-persistent promotion authorization.

## Done criteria

- [ ] File lifecycle states and retention policy are explicit.
- [ ] Promotion is an authorized, audited action.
- [ ] Cleanup is idempotent and orphan reconciliation is observable.
- [ ] Temporary files cannot be indexed, retrieved or included in reports when policy forbids it.
- [ ] PDF, XLSX, CSV, DOCX, image, text and JSON fixtures pass.
- [ ] `.xls` is either supported by an approved parser and fixture or clearly rejected.
- [ ] ZIP expansion is bounded before accumulation.
- [ ] Sheet/row/column evidence survives normalization.
- [ ] NG/Keevo interface has no field mapping and remains BLOCKED.
- [ ] Named tests pass.

## STOP conditions

- Stop if temporary content can reach persistent search or report evidence.
- Stop if a source ACL is lost during normalization.
- Stop if `.xls` support is promised without a parser and fixture.
- Stop if NG/Keevo fields or access are invented.
- Stop if cleanup cannot converge after retry or orphan state is ambiguous.

