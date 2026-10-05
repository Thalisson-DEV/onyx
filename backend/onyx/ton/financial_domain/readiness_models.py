"""Safe projections for financial readiness review."""

from datetime import date, datetime
from decimal import Decimal
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


class EvidenceRecordView(BaseModel):
    """One source record behind a blocker, as the source states it."""

    origin: Literal["NG", "BILLING"]
    document: str | None = None
    emission_date: date | None = None
    period: date | None = None
    account: str | None = None
    unit: str | None = None
    counterparty: str | None = None
    description: str | None = None
    movement_amount: Decimal | None = None
    final_amount: Decimal | None = None
    service_amount: Decimal | None = None
    net_amount: Decimal | None = None
    sheet: str | None = None
    row: int | None = None


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
    records: list[EvidenceRecordView] = Field(default_factory=list)


class BlockerPage(BaseModel):
    blocker: str
    total: int
    limit: int
    offset: int
    rows: list[BlockerRow]
    # Months the base already has, when the blocker is about missing months.
    covered_periods: list[date] = Field(default_factory=list)


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


class PeriodChange(BaseModel):
    period: date
    status_before: Literal["READY", "NOT_READY"] | None
    status_after: Literal["READY", "NOT_READY"]
    blockers_before: dict[str, int]
    blockers_after: dict[str, int]


class DecisionVersions(BaseModel):
    mapping: int
    amount_basis: int
    reconciliation: int
    treatment: int = 0


class ReadinessChanges(BaseModel):
    """Deterministic readiness of one base against the base it replaced."""

    run_id: UUID
    run_started_at: datetime
    previous_run_id: UUID | None
    previous_started_at: datetime | None
    applied: DecisionVersions
    previous_applied: DecisionVersions | None
    current: DecisionVersions
    pending_decisions: int
    periods: list[PeriodChange]


DecisionKind = Literal[
    "UNIT_MAPPING",
    "ACCOUNT_MAPPING",
    "BUDGET_ACCOUNT_MAPPING",
    "BUDGET_UNIT_MAPPING",
    "BUDGET_PERIOD",
    "AMOUNT_BASIS",
    "RECONCILIATION",
    "CANDIDATE_REJECTION",
    "DRE_ASSIGNMENT",
    "REVIEW_DECISION",
    "REVIEW_CARRIED_OVER",
    "CLOSING_TREATMENT",
]


class DecisionEntry(BaseModel):
    kind: DecisionKind
    subject: str
    outcome: str
    reason: str | None
    decided_by: str | None
    decided_at: datetime
    version: int | None
    # False only for decisions a base recompute still has to fold in.
    applied: bool | None


class DecisionLog(BaseModel):
    pending_decisions: int
    entries: list[DecisionEntry]


RequiredActionKind = Literal[
    "DECISION_IN_PENDING", "IMPORT_IN_SOURCES", "DATA_OR_CONFIGURATION_FIX"
]


class RequiredAction(BaseModel):
    blocker: str
    count: int
    action: RequiredActionKind


class RecentChanges(BaseModel):
    """What the assistant reports for "what changed after the decisions"."""

    changes: ReadinessChanges
    decisions: DecisionLog
    # What each remaining blocker of the latest period needs, by rule.
    required_actions: list[RequiredAction]
