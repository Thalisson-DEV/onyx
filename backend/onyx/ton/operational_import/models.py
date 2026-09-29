from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from onyx.ton.ng_financial.models import DiagnosticLevel, ProfileExecutionStatus
from onyx.ton.sources.models import SourceLocator


class OperationalKind(StrEnum):
    BILLING = "BILLING"
    BUDGET = "BUDGET"


class SheetClass(StrEnum):
    DETAIL = "DETAIL"
    SUPPORT = "SUPPORT"
    REFERENCE = "REFERENCE"
    SUMMARY = "SUMMARY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNKNOWN = "UNKNOWN"


class OperationalDiagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)
    level: DiagnosticLevel
    code: str
    sheet_name: str | None = None
    row_number: int | None = None
    column: str | None = None


class OperationalSheetSummary(BaseModel):
    name: str
    classification: SheetClass
    physical_rows: int
    rows_inspected: int = 0
    accepted: int = 0
    rejected: int = 0
    aggregates_excluded: int = 0
    proposal_rows_excluded: int = 0


class OperationalRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    locator: SourceLocator
    kind: OperationalKind
    identifier: str
    description: str | None
    record_date: date | None
    competence: date | None
    amount: Decimal | None
    period_basis: str | None
    numeric_values: dict[str, Decimal | None]
    typed_values: dict[str, str | None]
    source_values: dict[str, str | None]
    formula_cached: bool = False
    fingerprint: str
    duplicate_ordinal: int


class OperationalParseResult(BaseModel):
    profile_key: str
    profile_version: int
    snapshot_id: UUID
    records: list[OperationalRecord]
    diagnostics: list[OperationalDiagnostic]
    sheets: list[OperationalSheetSummary]

    @property
    def error_count(self) -> int:
        return sum(d.level == DiagnosticLevel.ERROR for d in self.diagnostics)

    @property
    def warning_count(self) -> int:
        return sum(d.level == DiagnosticLevel.WARNING for d in self.diagnostics)


class OperationalRecordView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    snapshot_id: UUID
    execution_id: UUID
    sheet_name: str
    source_row_number: int
    kind: OperationalKind
    identifier: str
    description: str | None
    record_date: date | None
    competence: date | None
    amount: Decimal | None
    period_basis: str | None
    numeric_values: dict[str, Decimal | None]
    typed_values: dict[str, str | None]
    source_values: dict[str, str | None]
    formula_cached: bool
    fingerprint: str
    duplicate_ordinal: int


class OperationalExecutionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    snapshot_id: UUID
    profile_id: UUID
    status: ProfileExecutionStatus
    error_code: str | None
    statistics: dict[str, int]
    diagnostics: list[OperationalDiagnostic]
    sheet_summaries: list[OperationalSheetSummary]
    started_at: datetime
    finished_at: datetime | None
