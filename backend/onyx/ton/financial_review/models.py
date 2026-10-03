"""Vocabularies, engine inputs/outputs and API views for DATA-003.

Nothing here carries a source value in a log-safe field. Records keep their
parsed values for rule evaluation only; detections carry record ids, locations,
codes and counts.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from onyx.db.ton.enums import (
    OccurrenceCriticality,
    OccurrenceStatus,
    OccurrenceVerificationResult,
    RuleKind,
    RuleVersionOutcome,
)
from onyx.ton.ng_financial.models import ParseDiagnostic


class ReviewRunStatus(StrEnum):
    """RUNNING is committed before evaluation. Both terminal states are final."""

    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EngineRuleStatus(StrEnum):
    """Engine enablement. Governance approval stays on RuleVersion.status."""

    ACTIVE = "ACTIVE"
    EXPERIMENTAL = "EXPERIMENTAL"
    BLOCKED = "BLOCKED"
    DISABLED = "DISABLED"


class RuleType(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    HEURISTIC = "HEURISTIC"
    STATISTICAL = "STATISTICAL"
    CROSS_SOURCE = "CROSS_SOURCE"


class ReviewCategory(StrEnum):
    """Controladoria POP categories, plus two non-POP buckets."""

    POP_01 = "POP_01"
    POP_02 = "POP_02"
    POP_03 = "POP_03"
    POP_04 = "POP_04"
    POP_05 = "POP_05"
    POP_06 = "POP_06"
    POP_07 = "POP_07"
    POP_08 = "POP_08"
    POP_09 = "POP_09"
    POP_10 = "POP_10"
    POP_11 = "POP_11"
    POP_12 = "POP_12"
    POP_13 = "POP_13"
    POP_14 = "POP_14"
    TECHNICAL_SOURCE_QUALITY = "TECHNICAL_SOURCE_QUALITY"
    NOT_IN_POP = "NOT_IN_POP"


class CapabilityStatus(StrEnum):
    IMPLEMENTABLE_NOW = "IMPLEMENTABLE_NOW"
    PARTIAL = "PARTIAL"
    REQUIRES_HISTORY = "REQUIRES_HISTORY"
    REQUIRES_DOTACAO = "REQUIRES_DOTACAO"
    REQUIRES_ZEEV = "REQUIRES_ZEEV"
    REQUIRES_DOCUMENT_SOURCE = "REQUIRES_DOCUMENT_SOURCE"
    REQUIRES_ACCOUNTING_SOURCE = "REQUIRES_ACCOUNTING_SOURCE"
    REQUIRES_PAYROLL = "REQUIRES_PAYROLL"
    REQUIRES_HUMAN_CONTEXT = "REQUIRES_HUMAN_CONTEXT"
    BLOCKED_BY_SOURCE = "BLOCKED_BY_SOURCE"


class SourceRequirement(StrEnum):
    """Inputs a rule needs. Only NG_FINANCIAL_EXPORT exists today."""

    NG_FINANCIAL_EXPORT = "NG_FINANCIAL_EXPORT"
    FINANCIAL_HISTORY = "FINANCIAL_HISTORY"
    DOTACAO = "DOTACAO"
    ZEEV_WORKFLOW = "ZEEV_WORKFLOW"
    SUPPORTING_DOCUMENTS = "SUPPORTING_DOCUMENTS"
    ACCOUNTING_LEDGER = "ACCOUNTING_LEDGER"
    CHART_OF_ACCOUNTS = "CHART_OF_ACCOUNTS"
    BILLING = "BILLING"
    PAYROLL = "PAYROLL"
    BANK_STATEMENT = "BANK_STATEMENT"
    HUMAN_CONTEXT = "HUMAN_CONTEXT"


class IssueOrigin(StrEnum):
    """Who most plausibly caused the issue. UNRESOLVED when evidence is silent."""

    SOURCE_BUSINESS_ERROR = "SOURCE_BUSINESS_ERROR"
    EXPORT_STRUCTURE = "EXPORT_STRUCTURE"
    UNRESOLVED = "UNRESOLVED"


class DetectionScope(StrEnum):
    RECORD = "RECORD"
    RECORD_GROUP = "RECORD_GROUP"
    ACCOUNT = "ACCOUNT"
    UNIT = "UNIT"
    DIAGNOSTIC = "DIAGNOSTIC"
    EXECUTION = "EXECUTION"


class RecommendationKind(StrEnum):
    DETERMINISTIC_CORRECTION = "DETERMINISTIC_CORRECTION"
    SOURCE_CORRECTION_REQUIRED = "SOURCE_CORRECTION_REQUIRED"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    REQUEST_JUSTIFICATION = "REQUEST_JUSTIFICATION"
    REVIEW_CLASSIFICATION = "REVIEW_CLASSIFICATION"
    NO_SAFE_RECOMMENDATION = "NO_SAFE_RECOMMENDATION"


class RecommendationEvidenceLevel(StrEnum):
    """Strength of a suggested action. Never a percentage."""

    DETERMINISTIC = "DETERMINISTIC"
    HIGH_EVIDENCE = "HIGH_EVIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class DiagnosticTreatment(StrEnum):
    TECHNICAL_ONLY = "TECHNICAL_ONLY"
    REVIEW_RELEVANT = "REVIEW_RELEVANT"
    FINDING_ELIGIBLE = "FINDING_ELIGIBLE"
    EXPERIMENTAL = "EXPERIMENTAL"
    BLOCKED = "BLOCKED"


class ImpactStatus(StrEnum):
    EXACT = "EXACT"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


class ReviewDecisionKind(StrEnum):
    ACKNOWLEDGE = "ACKNOWLEDGE"
    REQUEST_SOURCE_CORRECTION = "REQUEST_SOURCE_CORRECTION"
    JUSTIFY_EXCEPTION = "JUSTIFY_EXCEPTION"
    MARK_FALSE_POSITIVE = "MARK_FALSE_POSITIVE"
    ACCEPT_RECOMMENDATION = "ACCEPT_RECOMMENDATION"
    REJECT_RECOMMENDATION = "REJECT_RECOMMENDATION"
    CONFIRM_SOURCE_CORRECTION = "CONFIRM_SOURCE_CORRECTION"


class JustificationCategory(StrEnum):
    LEGITIMATE_REPETITION = "LEGITIMATE_REPETITION"
    BUSINESS_EXCEPTION = "BUSINESS_EXCEPTION"
    EXPORT_ARTIFACT = "EXPORT_ARTIFACT"
    IMMATERIAL = "IMMATERIAL"
    OTHER = "OTHER"


class ReviewDisposition(StrEnum):
    """Downstream disposition of a parsed record or a rejected source row."""

    ACCEPTED = "ACCEPTED"
    JUSTIFIED_EXCEPTION = "JUSTIFIED_EXCEPTION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    SUPERSEDED_BY_CORRECTION = "SUPERSEDED_BY_CORRECTION"
    EXCLUDED_SOURCE_ERROR = "EXCLUDED_SOURCE_ERROR"


DOWNSTREAM_SAFE_DISPOSITIONS: frozenset[ReviewDisposition] = frozenset(
    {ReviewDisposition.ACCEPTED, ReviewDisposition.JUSTIFIED_EXCEPTION}
)


class VerificationReason(StrEnum):
    VIOLATION_ABSENT_UNIQUE_MATCH = "VIOLATION_ABSENT_UNIQUE_MATCH"
    NO_CORRESPONDING_RECORD = "NO_CORRESPONDING_RECORD"
    AMBIGUOUS_CORRESPONDENCE = "AMBIGUOUS_CORRESPONDENCE"
    LOCATION_ONLY_IDENTITY = "LOCATION_ONLY_IDENTITY"


# ---------------------------------------------------------------------------
# Engine inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """Rule input projected from one immutable ParsedSourceRecord."""

    id: UUID
    sheet_name: str
    row_number: int
    sheet_month: int
    account_code: str
    account_label: str
    emission_date: date
    administrative_unit: str | None
    document_number: str | None
    history: str
    amounts: Mapping[str, Decimal | None]
    # Physical B and C cells were blank; the value came from group carry-forward.
    physical_date_blank: bool
    physical_unit_blank: bool
    fingerprint: str
    duplicate_ordinal: int


@dataclass(frozen=True)
class RuleContext:
    """Deterministic run context. No clock, no randomness, no reviewed file."""

    source_id: UUID
    snapshot_id: UUID
    execution_id: UUID
    execution_status: str
    execution_statistics: Mapping[str, int]
    available_sources: frozenset[SourceRequirement] = frozenset(
        {SourceRequirement.NG_FINANCIAL_EXPORT}
    )
    # Optional authoritative code -> label mapping. None is configured today.
    account_label_reference: Mapping[str, str] | None = None


# ---------------------------------------------------------------------------
# Engine outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImpactFact:
    status: ImpactStatus
    method: str | None = None
    basis: str | None = None
    amount: Decimal | None = None


UNKNOWN_IMPACT = ImpactFact(status=ImpactStatus.UNKNOWN)

FactValue = str | int | bool | None


@dataclass(frozen=True)
class Detection:
    """One rule violation. Structured facts only; no explanation text."""

    rule_key: str
    rule_version: int
    scope: DetectionScope
    # Identity component: stable across re-parses, excludes correctable fields.
    review_key: str
    # Same key without the duplicate ordinal. Used for cross-import matching.
    base_key: str
    base_key_count: int
    sheet_month: int | None
    record_ids: tuple[UUID, ...] = ()
    diagnostics: tuple[ParseDiagnostic, ...] = ()
    facts: Mapping[str, FactValue] = field(default_factory=dict)
    # Candidate correct values. Only a unique authoritative one may be suggested.
    candidate_values: tuple[str, ...] = ()
    authoritative_value: str | None = None
    impact: ImpactFact = UNKNOWN_IMPACT


@dataclass(frozen=True)
class RecommendationDraft:
    kind: RecommendationKind
    evidence_level: RecommendationEvidenceLevel
    rationale_code: str
    explanation: str
    target_field: str | None = None
    suggested_value: str | None = None
    candidate_count: int | None = None


@dataclass(frozen=True)
class EvaluatedDetection:
    detection: Detection
    explanation: str
    recommendation: RecommendationDraft


@dataclass(frozen=True)
class RuleEvaluation:
    rule_key: str
    rule_version: int
    engine_status: EngineRuleStatus
    outcome: RuleVersionOutcome
    detection_count: int
    observations: Mapping[str, int] = field(default_factory=dict)
    skip_reason: str | None = None


@dataclass(frozen=True)
class ReviewEvaluationResult:
    evaluations: tuple[RuleEvaluation, ...]
    detections: tuple[EvaluatedDetection, ...]
    diagnostic_summary: Mapping[str, Mapping[str, str | int]]
    statistics: Mapping[str, int]
    # rule_key -> base_key -> count in this import, for cross-import verification.
    verification_index: Mapping[str, Mapping[str, int]]


# ---------------------------------------------------------------------------
# API views and requests
# ---------------------------------------------------------------------------


class RuleCatalogEntryView(BaseModel):
    rule_key: str
    version: int
    name: str
    description: str
    category: ReviewCategory
    related_categories: list[ReviewCategory]
    rule_type: RuleType
    rule_kind: RuleKind
    status: EngineRuleStatus
    required_sources: list[SourceRequirement]
    required_fields: list[str]
    severity: OccurrenceCriticality
    blocking: bool
    origin: IssueOrigin
    recommendation_capability: list[RecommendationKind]
    known_limitations: list[str]


class PopCapabilityView(BaseModel):
    category: ReviewCategory
    name: str
    status: CapabilityStatus
    rule_keys: list[str]
    rationale: str


class DiagnosticPolicyView(BaseModel):
    code: str
    level: str | None
    treatment: DiagnosticTreatment
    rule_key: str | None
    rationale: str


class RuleCatalogView(BaseModel):
    engine_version: str
    dataset_policy_version: str
    rules: list[RuleCatalogEntryView]
    pop_capabilities: list[PopCapabilityView]
    diagnostic_policy: list[DiagnosticPolicyView]


class ReviewRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    analysis_run_id: UUID
    source_id: UUID
    snapshot_id: UUID
    execution_id: UUID
    status: ReviewRunStatus
    attempt_no: int
    engine_version: str
    rule_set_digest: str
    statistics: dict[str, int]
    error_code: str | None
    started_at: datetime
    finished_at: datetime | None
    # True when an existing successful run for the same input and rule set was returned.
    reused: bool = False


class RuleEvaluationView(BaseModel):
    rule_key: str
    rule_version: int
    engine_status: EngineRuleStatus
    outcome: RuleVersionOutcome
    finding_count: int
    observations: dict[str, int]
    skip_reason: str | None


class RecommendationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    finding_id: UUID
    kind: RecommendationKind
    evidence_level: RecommendationEvidenceLevel
    rationale_code: str
    explanation: str
    target_field: str | None
    suggested_value: str | None
    candidate_count: int | None
    created_at: datetime


class FindingSummaryView(BaseModel):
    id: UUID
    occurrence_id: UUID
    occurrence_short_code: str
    occurrence_status: OccurrenceStatus
    criticality: OccurrenceCriticality
    verification_result: OccurrenceVerificationResult | None
    review_run_id: UUID | None
    rule_key: str
    rule_version: int
    category: str
    origin: str
    scope: str
    blocking: bool
    sheet_month: int | None
    record_count: int
    explanation: str
    detected_at: datetime


class FindingDetailView(FindingSummaryView):
    facts: dict[str, FactValue]
    impact: dict[str, str | None]
    related_categories: list[str]
    recommendations: list[RecommendationView]


class EvidenceView(BaseModel):
    id: UUID
    finding_id: UUID
    kind: str
    source_snapshot_id: UUID | None
    import_execution_id: UUID | None
    parsed_record_id: UUID | None
    sheet_name: str | None
    row_number: int | None
    column: str | None
    diagnostic_code: str | None
    role: str | None
    confidence_level: str


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ReviewDecisionKind
    reason: str = Field(min_length=1, max_length=2000)
    comment: str | None = Field(default=None, max_length=4000)
    justification_category: JustificationCategory | None = None
    recommendation_id: UUID | None = None
    authorization_reference: str | None = Field(
        default=None, min_length=1, max_length=200
    )


class ReviewDecisionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    occurrence_id: UUID
    kind: ReviewDecisionKind
    justification_category: JustificationCategory | None
    recommendation_id: UUID | None
    reason: str
    comment: str | None
    authorization_reference: str | None
    # None on a carried-over decision; its author is carried_from_actor_user_id.
    actor_user_id: UUID | None
    occurrence_event_id: UUID | None
    created_at: datetime
    # HUMAN, or CARRIED_OVER when a new import kept an earlier human decision.
    basis: str = "HUMAN"
    carried_from_decision_id: UUID | None = None
    carried_from_actor_user_id: UUID | None = None
    carried_from_at: datetime | None = None


class MonthDatasetView(BaseModel):
    sheet_month: int
    records: int
    downstream_safe: int
    not_downstream_safe: int
    excluded_source_rows: int
    complete: bool


class ReviewedDatasetSummaryView(BaseModel):
    review_run_id: UUID
    source_id: UUID
    snapshot_id: UUID
    execution_id: UUID
    rule_set_digest: str
    dataset_policy_version: str
    dataset_revision: str
    as_of: datetime
    total_records: int
    dispositions: dict[ReviewDisposition, int]
    downstream_safe_records: int
    excluded_source_rows: int
    downstream_ready: bool
    months: list[MonthDatasetView]


class ReviewedRecordView(BaseModel):
    parsed_record_id: UUID
    sheet_name: str
    row_number: int
    sheet_month: int
    account_code: str
    disposition: ReviewDisposition
    downstream_safe: bool
    rule_keys: list[str]
    open_blocking_findings: int
    open_non_blocking_findings: int
