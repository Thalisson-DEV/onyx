## ADDED Requirements

### Requirement: Declared budget workbook identity
A dotação import SHALL declare its business unit and version date (data-base) explicitly at upload, and the system SHALL group budget versions by that declared identity, never by file name.

#### Scenario: Same workbook with a different file name
- **WHEN** "DOTACAO (JUAZEIRO BA) 30032026 (1).xlsx" is uploaded with the same content as an existing version
- **THEN** the import is rejected as duplicate content (same hash) and no new budget is created

#### Scenario: New version of a unit budget
- **WHEN** a workbook with a different hash is uploaded for Juazeiro-BA with a newer data-base
- **THEN** it becomes a new version of the Juazeiro-BA budget and the previous version stays readable
