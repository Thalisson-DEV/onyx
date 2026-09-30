from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DiagnosticSummary(BaseModel):
    code: str
    count: int


class ClientImportView(BaseModel):
    id: UUID
    source_id: UUID
    status: str
    filename: str
    format: str
    size_bytes: int
    started_at: datetime
    finished_at: datetime | None
    imported: int
    rejected: int
    warnings: int
    errors: int
    needs_review: int | None = None
    available_for_analysis: int | None = None
    diagnostics: list[DiagnosticSummary]
    downstream: list[str]
    readiness_status: str = "UNKNOWN"
    readiness_run_id: UUID | None = None
    failure_reason: str | None = None


class ClientSourceView(BaseModel):
    key: str
    name: str
    description: str
    format: str
    source_id: UUID | None
    can_import: bool
    status: str
    last_success_at: datetime | None
    last_attempt_at: datetime | None
    latest: ClientImportView | None
    history: list[ClientImportView]
