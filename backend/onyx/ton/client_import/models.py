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


class ReimportPreviewItem(BaseModel):
    rule_key: str
    # CARRIED_OVER, EVIDENCE_CHANGED, STILL_OPEN, REOPENED or NEW.
    outcome: str
    sheet_month: int | None
    sheet_name: str | None = None
    row_number: int | None = None


class ReimportPreviewView(BaseModel):
    """What importing this file would do, computed without persisting it."""

    key: str
    filename: str
    imported: int
    rejected: int
    # The source already has reviewed imports whose decisions can carry over.
    has_previous_review: bool
    # Human decisions that stay, because the same case shows the same evidence.
    carried_over: int
    # Same case, different evidence: back to a human decision.
    evidence_changed: int
    # Cases still waiting for a decision or a source correction.
    still_open: int
    # Cases closed before that this file shows again.
    reopened: int
    # Findings never seen before.
    new: int
    # Earlier cases this file no longer shows; verified after the import.
    not_detected: int
    # Only the cases that need a person, at most 50.
    attention: list[ReimportPreviewItem]
    # Importing this source changes the actual (Realizado) base.
    changes_actuals: bool
