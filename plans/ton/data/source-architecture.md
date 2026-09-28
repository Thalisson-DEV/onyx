# Source architecture

Connected sources and assisted sources share one logical Source identity.

```text
CONNECTED SOURCE or ASSISTED SOURCE
  -> Source
  -> ImportRun
  -> SourceSnapshot
  -> future ImportProfile execution
  -> future Raw Records
  -> future Validation
  -> future Normalization
  -> future Domain
  -> future Findings
  -> future Specialists
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
DATA-001 stops at captured inputs. Profiles, business validation, and normalization belong to later slices.
