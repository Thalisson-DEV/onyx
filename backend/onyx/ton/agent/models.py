"""Bounded inputs for the TON chat tools."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from onyx.ton.sources.models import SourceView


class ToolQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID | None = None
    finding_id: UUID | None = None
    review_run_id: UUID | None = None
    normalization_run_id: UUID | None = None
    structure_version_id: UUID | None = None
    run_id: UUID | None = None
    request_id: UUID | None = None
    period: date | None = None
    unit_id: UUID | None = None
    blocking: bool | None = None
    limit: int = Field(default=10, ge=1, le=25)
    offset: int = Field(default=0, ge=0, le=10000)


class StoredDreContext(BaseModel):
    run_id: UUID
    period: date
    unit_id: UUID | None
    structure_version_id: UUID
    status: str


class FinancialBaseContext(BaseModel):
    normalization_run_id: UUID
    source_id: UUID
    review_run_id: UUID
    periods: list[date]
    source_name: str
    stored_dre_results: list[StoredDreContext]


class FinancialContext(BaseModel):
    bases: list[FinancialBaseContext]
    structure_version_ids: list[UUID]


class ImportExecutionSummary(BaseModel):
    execution_id: UUID
    snapshot_id: UUID
    status: str
    finished_at: datetime | None
    imported_records: int | None
    rejected_records: int | None
    warnings: int | None
    errors: int | None


class SourceToolStatus(BaseModel):
    source: SourceView
    last_successful_import_at: datetime | None
    executions: list[ImportExecutionSummary]
    review_run_ids: list[UUID]
