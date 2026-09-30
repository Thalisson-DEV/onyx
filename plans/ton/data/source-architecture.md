# Source architecture

Connected sources and assisted sources share one logical Source identity.

```text
CONNECTED SOURCE or ASSISTED SOURCE
  -> Source
  -> ImportRun
  -> SourceSnapshot
     +-> NG ImportProfileExecution -> ParsedSourceRecord + ParseDiagnostic
     |   -> ReviewRun (AnalysisRun extension)
     |   -> RuleEvaluation (AnalysisRunRuleVersion)
     |   -> Finding + FindingEvidence -> Occurrence
     |   -> Recommendation / Human Decision
     |   -> Reviewed Financial Dataset (derived projection)
     +-> Billing ImportProfileExecution -> Billing source records
     +-> Budget ImportProfileExecution -> Budget source records
  -> NormalizationRun + mapping revision (DATA-004C/D)
  -> Canonical Actual / Billing / Billing-Derived / Budget Facts
  -> Cross-source reconciliation
  -> DRE Input Dataset
  -> DRE Readiness + approved structure/account mapping version
  -> DRE Calculation Run
  -> Versioned DRE Result
  -> future dashboard / reports / specialists
```

Source.id and Source.key identify a logical input within its tenant.
Filenames identify presentations of captured inputs. Acquisition describes the current entry method.
Changing acquisition never changes logical identity.

ImportRun preserves each attempt and its terminal outcome.
SourceSnapshot preserves original bytes, SHA-256, capture metadata, and provenance.
A duplicate upload creates another receipt linked to the first matching snapshot.
A new hash means a new version, regardless of filename.

Existing secure FileStore owns raw objects. Source APIs never return storage paths.
Tenant sessions and existing group capabilities restrict access.
Runs and snapshots inherit their source ACL.
Raw snapshots are immutable. Recommendations must remain separate from source truth.
Sensitive client content never belongs in application logs or fixtures.
Macros and other uploaded code are never executed.
RAW data is unavailable to LLM tools.

A connected adapter can call the internal JSON capture service.
The service does not parse business fields.
File uploads accept XLS, XLSX, XLSM, CSV, and PDF. Connected capture accepts JSON bytes.
DATA-001 stops at captured inputs. DATA-002 adds an XLSX-only NG financial profile and source-level records.
The DATA-001 ImportRun status reports raw capture. ImportProfileExecution has a separate status for parsing.

DATA-004A/B adds BIFF/XLS billing and XLSX budget profiles on the same Source,
ImportRun, SourceSnapshot, and ImportProfileExecution spine. The billing_invoices
and budget keys each identify one logical source per tenant. Structural profile
selection is independent of filename and acquisition method. OperationalSourceRecord
holds only invoice or budget source detail with exact sheet and row lineage.
Billing reference sheets and budget support, reference, and summary sheets are
classified but produce no records. The budget cost composition uses cached
formula values without calculating formulas. It has no dated allocation.

DATA-003 reviews one parse execution with a versioned deterministic rule catalog.
ReviewRun has its own status and never changes the layers above it.
A ParseDiagnostic is a technical observation; only selected codes become findings.
Findings, evidence and occurrences reuse the TON domain tables.
Evidence points to the parsed record or to the diagnostic location.
Recommendations and human decisions are separate, append-only rows.
A later import can verify a correction; a person closes the case.
The reviewed dataset is a projection over one review run and the decision history.
Downstream consumers read only downstream-safe records and record the dataset revision.

DATA-004C/D joins three independent inputs: the reviewed NG projection, accepted
billing records, and accepted budget records. An append-only mapping revision
aligns source accounts and units to canonical identities. A normalization run
pins the review revision, source executions, mapping revision, derivation rules,
and authority policy. It writes separate canonical fact tables in one final
transaction. Reconciliation links exact structured revenue candidates. Billing
derived rows remain supplementary and do not add to NG actuals. Budget facts
remain independent and need an explicit calendar period before comparison.
The DRE input service returns paged facts and blockers. DATA-005A/B consumes
that boundary. A blocked scope produces no official result lines. A ready
calculation pins the normalization, DRE version, policy versions, and source
lineage in an immutable result revision. No dashboard is in this slice.

DATA-006A/B adds a financial readiness workspace above that boundary. It shows
period blockers and paged source evidence. Exact code and legacy reference
evidence remain candidates. Human mapping, amount basis, DRE assignment,
budget period, and reconciliation decisions create append-only revisions.
A new normalization pins those revisions. Readiness can change without
creating an official DRE result. DATA-005 calculation remains an explicit act.
