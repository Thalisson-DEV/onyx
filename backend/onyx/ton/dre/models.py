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


class DreVersionView(BaseModel):
    id: UUID
    structure_id: UUID
    number: int
    lines: list[DreLineDefinition]
    assignments: list[DreAccountAssignment]
    created_at: datetime


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


class DreContributorPage(BaseModel):
    total: int
    rows: list[DreContributorView]


class DreStatementView(BaseModel):
    run: DreRunView
    version: DreVersionView
    lines: list[DreResultLineView]


class DrePeriodPoint(BaseModel):
    period: date
    result_id: UUID
    realizado: Decimal
    orcado: Decimal
    variance: Decimal
