from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from onyx.ton.sources.models import SourceLocator


class RowKind(StrEnum):
    HEADER = "HEADER"
    REPEATED_HEADER = "REPEATED_HEADER"
    SECTION = "SECTION"
    HIERARCHY = "HIERARCHY"
    DETAIL = "DETAIL"
    SUBTOTAL = "SUBTOTAL"
    TOTAL = "TOTAL"
    BLANK = "BLANK"
    UNKNOWN = "UNKNOWN"


class DiagnosticLevel(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class DiagnosticCode(StrEnum):
    SHEET_OUT_OF_SCOPE = "SHEET_OUT_OF_SCOPE"
    MONTH_SHEET_EMPTY = "MONTH_SHEET_EMPTY"
    ACCOUNT_SECTION_REPEATED = "ACCOUNT_SECTION_REPEATED"
    CELL_OUTSIDE_CONTRACT = "CELL_OUTSIDE_CONTRACT"
    FORMULA_UNSUPPORTED = "FORMULA_UNSUPPORTED"
    UNKNOWN_ROW = "UNKNOWN_ROW"
    INVALID_DATE = "INVALID_DATE"
    INHERITED_DATE_INVALID = "INHERITED_DATE_INVALID"
    MISSING_DATE = "MISSING_DATE"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    MISSING_AMOUNTS = "MISSING_AMOUNTS"
    UNIT_BLANK = "UNIT_BLANK"
    PARENT_ROW_WITHOUT_CHILD_MATCH = "PARENT_ROW_WITHOUT_CHILD_MATCH"
    CHILD_ROW_WITHOUT_PARENT_MATCH = "CHILD_ROW_WITHOUT_PARENT_MATCH"


# Each of these rejects exactly one source row; they never co-occur on a row.
REJECTION_CODES: frozenset[DiagnosticCode] = frozenset(
    {
        DiagnosticCode.UNKNOWN_ROW,
        DiagnosticCode.INVALID_DATE,
        DiagnosticCode.INHERITED_DATE_INVALID,
        DiagnosticCode.MISSING_DATE,
        DiagnosticCode.INVALID_AMOUNT,
        DiagnosticCode.MISSING_AMOUNTS,
    }
)


class ProfileExecutionStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ParseDiagnostic(BaseModel):
    """Location-only. Never carries a source cell value."""

    model_config = ConfigDict(frozen=True)
    level: DiagnosticLevel
    code: DiagnosticCode
    sheet_name: str | None = None
    row_number: int | None = None
    column: str | None = None


class ParsedSourceRecordData(BaseModel):
    model_config = ConfigDict(frozen=True)

    locator: SourceLocator
    sheet_month: int
    account_code: str
    account_label: str
    emission_date: date
    administrative_unit: str | None
    document_number: str | None
    history: str
    movement_amount: Decimal | None
    movement_retention_amount: Decimal | None
    movement_net_amount: Decimal | None
    installment_retention_amount: Decimal | None
    installment_net_amount: Decimal | None
    interest_amount: Decimal | None
    penalty_amount: Decimal | None
    discount_amount: Decimal | None
    expense_amount: Decimal | None
    loss_amount: Decimal | None
    other_deduction_amount: Decimal | None
    final_amount: Decimal | None
    # Physical cells by Excel letter, including blanks in A:Q and any
    # non-empty cell outside the v1 contract.
    source_values: dict[str, str | None]
    # Import-local content hash. Not a Keevo identifier.
    fingerprint: str
    # 1-based occurrence of the same fingerprint within the sheet.
    duplicate_ordinal: int


class SheetSummary(BaseModel):
    name: str
    month: int | None
    accepted: bool
    physical_rows: int
    classifications: dict[RowKind, int]
    row_spans: dict[RowKind, list[tuple[int, int]]]


class ParsedImportResult(BaseModel):
    profile_key: str
    profile_version: int
    snapshot_id: UUID
    records: list[ParsedSourceRecordData]
    diagnostics: list[ParseDiagnostic]
    sheets: list[SheetSummary]

    @property
    def warning_count(self) -> int:
        return sum(item.level == DiagnosticLevel.WARNING for item in self.diagnostics)

    @property
    def error_count(self) -> int:
        return sum(item.level == DiagnosticLevel.ERROR for item in self.diagnostics)


class RecordLocation(BaseModel):
    model_config = ConfigDict(frozen=True)
    month: int
    sheet_name: str
    row_number: int


class ChangedPair(BaseModel):
    model_config = ConfigDict(frozen=True)
    left: RecordLocation
    right: RecordLocation
    fields: tuple[str, ...]


class MonthDiff(BaseModel):
    month: int
    left_records: int
    right_records: int
    unchanged: int
    changed: int
    added: int
    removed: int
    ambiguous: int


class SourceDiff(BaseModel):
    """Structural comparison only. It never decides which side is correct."""

    months: list[MonthDiff]
    changed_pairs: list[ChangedPair]
    added: list[RecordLocation]
    removed: list[RecordLocation]
    changed_fields: dict[str, int]

    @property
    def unchanged(self) -> int:
        return sum(item.unchanged for item in self.months)

    @property
    def changed(self) -> int:
        return len(self.changed_pairs)

    @property
    def ambiguous(self) -> int:
        return sum(item.ambiguous for item in self.months)


class ImportProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    key: str
    version: int
    format: str
    column_map: dict[str, str]
    created_at: datetime


class ImportProfileExecutionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    snapshot_id: UUID
    profile_id: UUID
    status: ProfileExecutionStatus
    error_code: str | None
    statistics: dict[str, int]
    diagnostics: list[ParseDiagnostic]
    sheet_summaries: list[SheetSummary]
    started_at: datetime
    finished_at: datetime | None


class ParsedSourceRecordView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    snapshot_id: UUID
    execution_id: UUID
    sheet_name: str
    source_row_number: int
    sheet_month: int
    account_code: str
    account_label: str
    emission_date: date
    administrative_unit: str | None
    document_number: str | None
    history: str
    movement_amount: Decimal | None
    movement_retention_amount: Decimal | None
    movement_net_amount: Decimal | None
    installment_retention_amount: Decimal | None
    installment_net_amount: Decimal | None
    interest_amount: Decimal | None
    penalty_amount: Decimal | None
    discount_amount: Decimal | None
    expense_amount: Decimal | None
    loss_amount: Decimal | None
    other_deduction_amount: Decimal | None
    final_amount: Decimal | None
    source_values: dict[str, str | None]
    fingerprint: str
    duplicate_ordinal: int
