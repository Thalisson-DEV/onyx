from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class DreLineType(StrEnum):
    SOURCE_SUM = "SOURCE_SUM"
    CALCULATED = "CALCULATED"
    SUBTOTAL = "SUBTOTAL"
    RESULT = "RESULT"
    PERCENTAGE = "PERCENTAGE"


class DreOperation(StrEnum):
    SUM_LINES = "SUM_LINES"
    SUM_CHILDREN = "SUM_CHILDREN"
    SUBTRACT = "SUBTRACT"
    RATIO = "RATIO"


class DreLineDefinition(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=500)
    position: int = Field(ge=0)
    parent_code: str | None = None
    line_type: DreLineType
    operation: DreOperation | None = None
    operands: list[str] = Field(default_factory=list)
    # Only the presentation: a hidden line still counts in every total that
    # sums it. The screen and the Excel leave it (and its children) out.
    hidden: bool = False
    # Out of the result: the group above does not add this line, which keeps
    # its own value (shown, and marked, on the screen and in the Excel).
    excluded: bool = False

    @model_validator(mode="after")
    def validate_behavior(self) -> "DreLineDefinition":
        if self.line_type == DreLineType.SOURCE_SUM:
            if self.operation is not None or self.operands:
                raise ValueError("Source lines cannot have formulas")
        elif self.operation is None:
            raise ValueError("Calculated lines require an operation")
        if self.operation == DreOperation.SUBTRACT and len(self.operands) != 2:
            raise ValueError("Subtraction requires two operands")
        if self.operation == DreOperation.RATIO and len(self.operands) != 2:
            raise ValueError("Ratio requires two operands")
        if self.operation == DreOperation.SUM_LINES and not self.operands:
            raise ValueError("SUM_LINES requires operands")
        if self.operation == DreOperation.SUM_CHILDREN and self.operands:
            raise ValueError("SUM_CHILDREN uses direct children")
        return self


class DreAccountAssignment(BaseModel):
    account_id: UUID
    line_code: str
    status: Literal["APPROVED", "PENDING_APPROVAL"]


class DreVersionCreate(BaseModel):
    lines: list[DreLineDefinition] = Field(min_length=1)
    assignments: list[DreAccountAssignment] = Field(default_factory=list)
    reason: str | None = Field(default=None, min_length=1, max_length=500)


class DreAssignmentApproval(BaseModel):
    account_id: UUID
    line_code: str = Field(min_length=1, max_length=100)
    status: Literal["APPROVED", "PENDING_APPROVAL"]
    reason: str = Field(min_length=1, max_length=500)


class DreStructureCreate(DreVersionCreate):
    key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=500)


class DreStructureView(BaseModel):
    id: UUID
    key: str
    label: str
    latest_version: int
    base_structure_id: UUID | None = None


class DreVersionView(BaseModel):
    id: UUID
    structure_id: UUID
    number: int
    lines: list[DreLineDefinition]
    assignments: list[DreAccountAssignment]
    created_at: datetime


class DreChangeKind(StrEnum):
    LINE_ADDED = "LINE_ADDED"
    LINE_REMOVED = "LINE_REMOVED"
    LINE_RENAMED = "LINE_RENAMED"
    LINE_MOVED = "LINE_MOVED"
    ORDER_CHANGED = "ORDER_CHANGED"
    INTO_RESULT = "INTO_RESULT"
    OUT_OF_RESULT = "OUT_OF_RESULT"
    FORMULA_CHANGED = "FORMULA_CHANGED"
    HIDDEN = "HIDDEN"
    SHOWN = "SHOWN"
    NATURE_LINKED = "NATURE_LINKED"
    NATURE_UNLINKED = "NATURE_UNLINKED"
    NATURE_RELINKED = "NATURE_RELINKED"


class DreChange(BaseModel):
    """One difference between two versions, in the Controladoria's words."""

    kind: DreChangeKind
    line: str
    before: str | None = None
    after: str | None = None


class DreVersionHistoryItem(BaseModel):
    id: UUID
    number: int
    created_at: datetime
    author: str | None
    reason: str | None
    changes: list[DreChange]


class DreRestoreRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=400)
    dry_run: bool = False


class DreRestoreView(BaseModel):
    """What going back to an earlier version changes, and the new version."""

    target_number: int
    changes: list[DreChange]
    left_out_natures: list[str]
    version: DreVersionView | None = None


class DreScope(BaseModel):
    normalization_run_id: UUID
    structure_version_id: UUID
    period: date
    unit_id: UUID | None = None


class DreReadinessView(BaseModel):
    status: Literal["READY", "NOT_READY"]
    scope: DreScope
    blockers: dict[str, int]
    checked_periods: list[date]


class DreResultLineView(BaseModel):
    code: str
    label: str
    position: int
    realizado: Decimal
    orcado: Decimal
    variance: Decimal
    variance_percent: Decimal | None
    realizado_ytd: Decimal
    orcado_ytd: Decimal
    variance_ytd: Decimal
    variance_percent_ytd: Decimal | None


class DreRunView(BaseModel):
    id: UUID
    status: Literal["READY", "NOT_READY"]
    scope: DreScope
    blockers: dict[str, int]
    input_digest: str
    engine_version: str
    provenance: dict[str, object]
    started_at: datetime
    finished_at: datetime


class DreContributorView(BaseModel):
    id: UUID
    fact_type: Literal["ACTUAL", "BUDGET"]
    period: date
    account_code: str
    account_label: str
    unit_code: str
    amount: Decimal
    amount_basis: str
    record_date: date | None
    source_name: str
    original_filename: str
    source_id: UUID
    source_snapshot_id: UUID
    source_execution_id: UUID
    sheet_name: str
    source_row_number: int
    reference: str | None
    review_status: str | None
    unit_name: str | None = None
    source_account_code: str | None = None
    source_account_label: str | None = None
    description: str | None = None
    # Closing treatment that changed this entry: ``amount`` is the treated
    # value, ``original_amount`` the NG value.
    treatment_title: str | None = None
    treatment_effect: str | None = None
    treatment_version: int | None = None
    original_amount: Decimal | None = None
    original_account_label: str | None = None


class DreContributorPage(BaseModel):
    total: int
    rows: list[DreContributorView]


class DreStatementView(BaseModel):
    run: DreRunView
    version: DreVersionView
    lines: list[DreResultLineView]


class DreYearMonth(BaseModel):
    """The latest READY result of one month, with all of its lines."""

    run: DreRunView
    lines: list[DreResultLineView]


class DreYearView(BaseModel):
    """Every calculated month of a year for one base, structure and scope."""

    version: DreVersionView
    months: list[DreYearMonth]


class DreUnitsYearMonth(BaseModel):
    """One month summed over the selected units that have a READY result."""

    period: date
    ready_unit_ids: list[UUID]
    missing_unit_ids: list[UUID]
    lines: list[DreResultLineView]


class DreUnitsYearView(BaseModel):
    """A year for a chosen set of units: each month is the sum of the units.

    Every line of the structure is additive (source sums, subtotals, results),
    so the sum of the units' persisted lines is the DRE of the set. A month is
    complete only when every selected unit has a READY result for it.
    """

    version: DreVersionView
    unit_ids: list[UUID]
    months: list[DreUnitsYearMonth]


class DrePeriodPoint(BaseModel):
    period: date
    result_id: UUID
    realizado: Decimal
    orcado: Decimal
    variance: Decimal
