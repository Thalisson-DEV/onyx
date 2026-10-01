"""Bounded inputs for the TON chat tools."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from onyx.ton.sources.models import SourceView


class ToolQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID | None = None
    finding_id: UUID | None = None
    occurrence_id: UUID | None = None
    review_run_id: UUID | None = None
    normalization_run_id: UUID | None = None
    structure_version_id: UUID | None = None
    run_id: UUID | None = None
    request_id: UUID | None = None
    period: date | None = None
    unit_id: UUID | None = None
    blocking: bool | None = None
    blocker: str | None = Field(default=None, min_length=1, max_length=100)
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


class OccurrenceSummary(BaseModel):
    occurrence_id: UUID
    reference: str
    title: str
    status: str
    criticality: str
    open_cycles: int
    last_detected_at: datetime
    owner: str | None
    deadline: date | None
    assignment_status: str | None
    overdue: bool
    requires_human_closure: bool
    verification_criterion: str | None


class OccurrencePage(BaseModel):
    as_of: date
    items: list[OccurrenceSummary]
    has_more: bool
    next_offset: int | None
    scope: str = "Ocorrências autorizadas; página não representa o total."
    recommendation: str = (
        "Confirmar ação, responsável e prazo. Nenhuma ocorrência foi encerrada."
    )
