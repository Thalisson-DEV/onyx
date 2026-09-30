"""Safe projections for financial readiness review."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from onyx.ton.dre.models import DreReadinessView


class ReadinessOverview(BaseModel):
    normalization_run_id: UUID
    structure_version_id: UUID
    periods: list[DreReadinessView]


class CandidateView(BaseModel):
    target_id: UUID
    code: str
    label: str
    evidence: Literal["EXACT_CODE", "APPROVED_MAPPING"]


class LegacyEvidenceView(BaseModel):
    suggested_code: str
    suggested_label: str | None
    reference_label: str
    reference_digest: str


class LegacyCandidateImportRow(BaseModel):
    source_key: str = Field(min_length=1, max_length=500)
    suggested_code: str = Field(min_length=1, max_length=100)
    suggested_label: str | None = Field(default=None, max_length=500)


class LegacyCandidateImport(BaseModel):
    source_id: UUID
    kind: Literal["UNIT", "ACCOUNT"]
    reference_label: str = Field(min_length=1, max_length=255)
    reference_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    rows: list[LegacyCandidateImportRow] = Field(min_length=1, max_length=500)


class BlockerRow(BaseModel):
    source_id: UUID | None = None
    source_key: str | None = None
    account_id: UUID | None = None
    item_id: UUID | None = None
    record_count: int
    periods: list[date] = Field(default_factory=list)
    status: Literal["UNMAPPED", "CANDIDATE", "APPROVED", "UNRESOLVED"]
    candidate: CandidateView | None = None
    legacy_evidence: LegacyEvidenceView | None = None
    line_candidate: str | None = None
    paired: bool | None = None
    evidence: str | None = None


class BlockerPage(BaseModel):
    blocker: str
    total: int
    limit: int
    offset: int
    rows: list[BlockerRow]


class CandidateRejection(BaseModel):
    source_id: UUID
    kind: Literal["UNIT", "ACCOUNT"]
    source_key: str = Field(min_length=1, max_length=500)
    target_id: UUID | None = None
    evidence: Literal["EXACT_CODE", "LEGACY_REFERENCE"]
    reference_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reason: str = Field(min_length=1, max_length=500)


class ReconciliationApproval(BaseModel):
    decision: Literal[
        "NG_AUTHORITATIVE", "SUPPLEMENTAL", "EXPECTED_DIFFERENCE", "NOT_SAME_EVENT"
    ]
    reason: str = Field(min_length=1, max_length=500)
