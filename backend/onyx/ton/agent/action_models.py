"""Changes the TON chat proposes and a person applies with one click."""

import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from onyx.ton.agent.structure_ops import LineOperation
from onyx.ton.financial_domain.models import TreatmentEffect, TreatmentStatus


class ActionKind(StrEnum):
    DRE_STRUCTURE_CHANGE = "DRE_STRUCTURE_CHANGE"
    DRE_ADJUSTMENT = "DRE_ADJUSTMENT"
    CLOSING_TREATMENT = "CLOSING_TREATMENT"
    DRE_RECALCULATE = "DRE_RECALCULATE"
    SOURCE_IMPORT = "SOURCE_IMPORT"
    ACCOUNT_CLASSIFICATION = "ACCOUNT_CLASSIFICATION"
    CLASSIFICATION_CONFIRM = "CLASSIFICATION_CONFIRM"
    REVIEW_DECISION = "REVIEW_DECISION"
    UNIT_ASSIGNMENT = "UNIT_ASSIGNMENT"
    AUTOMATION_STATUS = "AUTOMATION_STATUS"
    AUTOMATION_RUN = "AUTOMATION_RUN"
    CONTROLLER_RULE = "CONTROLLER_RULE"
    LEDGER_REGISTER = "LEDGER_REGISTER"
    OCCURRENCE_ASSIGN = "OCCURRENCE_ASSIGN"
    R1_SCHEDULE = "R1_SCHEDULE"


class ActionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPLIED = "APPLIED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    UNDONE = "UNDONE"
    FAILED = "FAILED"


class ScopeInput(BaseModel):
    """Month and unit the preview shows; empty means the latest month, consolidated."""

    model_config = ConfigDict(extra="forbid")
    period: datetime.date | None = None
    unit: str | None = Field(default=None, max_length=100)


class StructureChangePayload(ScopeInput):
    # Empty: the managerial structure.
    structure_id: UUID | None = None
    operations: list[LineOperation] = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=3, max_length=500)


class AdjustmentValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: datetime.date
    # Unit name or code; empty is the consolidated DRE only.
    unit: str | None = Field(default=None, max_length=100)
    amount: Decimal = Field(max_digits=20, decimal_places=2)


class AdjustmentPayload(ScopeInput):
    structure_id: UUID | None = None
    line_code: str = Field(min_length=1, max_length=100)
    values: list[AdjustmentValue] = Field(min_length=1, max_length=60)
    justification: str = Field(min_length=3, max_length=2000)


class TreatmentPayload(ScopeInput):
    treatment_key: str = Field(
        min_length=1, max_length=100, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$"
    )
    title: str = Field(min_length=1, max_length=200)
    status: TreatmentStatus = TreatmentStatus.ACTIVE
    effect: TreatmentEffect
    nature_code: str = Field(min_length=1, max_length=100)
    target_nature_code: str | None = Field(default=None, max_length=100)
    treatment_unit: str | None = Field(default=None, max_length=100)
    period_from: datetime.date | None = None
    period_to: datetime.date | None = None
    required_source: str | None = Field(default=None, max_length=500)
    justification: str = Field(min_length=1, max_length=2000)
    evidence: str = Field(min_length=1, max_length=1000)


class RecalculatePayload(ScopeInput):
    structure_id: UUID | None = None
    # Units to recalculate besides the consolidated DRE; "todas" means every unit.
    units: list[str] = Field(default_factory=list, max_length=60)


class SourceImportPayload(ScopeInput):
    # File attached to the conversation: its id or its name. With neither, the
    # only spreadsheet attached is used.
    file_id: UUID | None = None
    file_name: str | None = Field(default=None, max_length=300)
    source_key: Literal[
        "financial_launches", "billing_invoices", "budget", "installments"
    ]


class ClassificationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # NG account code, as in the export (ex.: 8.1.0001).
    account_code: str = Field(min_length=1, max_length=100)
    # Natureza code (ex.: 3.03) or name (ex.: LOCAÇÃO).
    natureza: str = Field(min_length=1, max_length=200)


class ClassificationPayload(ScopeInput):
    items: list[ClassificationItem] = Field(min_length=1, max_length=100)
    reason: str = Field(default="", max_length=500)


class ClassificationConfirmPayload(ScopeInput):
    # NG account codes whose suggested natureza the person confirms.
    account_codes: list[str] = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=1000)


class ReviewDecisionPayload(ScopeInput):
    occurrence_ids: list[UUID] = Field(min_length=1, max_length=50)
    decision: Literal[
        "ACKNOWLEDGE",
        "REQUEST_SOURCE_CORRECTION",
        "JUSTIFY_EXCEPTION",
        "MARK_FALSE_POSITIVE",
        "CONFIRM_SOURCE_CORRECTION",
    ]
    reason: str = Field(min_length=3, max_length=2000)
    justification_category: (
        Literal[
            "LEGITIMATE_REPETITION",
            "BUSINESS_EXCEPTION",
            "EXPORT_ARTIFACT",
            "IMMATERIAL",
            "OTHER",
        ]
        | None
    ) = None


class UnitAssignmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    occurrence_id: UUID
    # Unit name or code; empty undoes an earlier assignment.
    unit: str | None = Field(default=None, max_length=100)


class UnitAssignmentPayload(ScopeInput):
    items: list[UnitAssignmentItem] = Field(min_length=1, max_length=100)
    reason: str = Field(default="", max_length=500)


class AutomationStatusPayload(ScopeInput):
    automation: str = Field(min_length=1, max_length=200)
    status: Literal["ACTIVE", "PAUSED"]


class AutomationRunPayload(ScopeInput):
    automation: str = Field(min_length=1, max_length=200)
    test: bool = True


class ControllerRulePayload(ScopeInput):
    # Short subject (ex.: "Parcelamentos", "Receita") to group the rules.
    topic: str = Field(min_length=2, max_length=100)
    # The rule in the Controladoria's words.
    text: str = Field(min_length=5, max_length=2000)
    # Key of a rule to replace or archive; empty creates a new rule.
    rule_key: str | None = Field(default=None, max_length=100)
    archive: bool = False


TestCode = Literal["T1", "T2", "T3", "T4", "T6", "T8", "T9", "T10"]
Criticality = Literal["CRITICAL", "HIGH", "MEDIUM", "MONITORING"]


class LedgerRegisterPayload(ScopeInput):
    test: TestCode
    # The same parameters the test ran with (period, unit, min_amount, …).
    test_parameters: dict[str, str | int | float | None] = Field(default_factory=dict)
    # "chave" of the hits to record; empty records every hit of the test.
    keys: list[str] = Field(default_factory=list, max_length=50)
    # Overrides the suggested criticality for every case.
    criticality: Criticality | None = None
    # PAD-CTRL-001 bands, % of the unit's revenue: critical, high, medium.
    bands: list[float] = Field(default_factory=lambda: [1.0, 0.3, 0.1], min_length=3, max_length=3)
    responsible: str | None = Field(default=None, max_length=200)
    deadline: datetime.date | None = None
    note: str | None = Field(default=None, max_length=2000)


class OccurrenceAssignPayload(ScopeInput):
    occurrence_ids: list[UUID] = Field(min_length=1, max_length=50)
    # Who answers for the cases (name or role); free text, as in the ledger.
    responsible: str | None = Field(default=None, max_length=200)
    deadline: datetime.date | None = None
    note: str | None = Field(default=None, max_length=2000)


class R1SchedulePayload(ScopeInput):
    enabled: bool
    tests: list[TestCode] = Field(
        default_factory=lambda: ["T1", "T2", "T3", "T4", "T6", "T8", "T9", "T10"]
    )
    hour: int = Field(default=7, ge=0, le=23)
    bands: list[float] = Field(default_factory=lambda: [1.0, 0.3, 0.1], min_length=3, max_length=3)


class PreviewLine(BaseModel):
    label: str
    antes: Decimal | None
    depois: Decimal | None
    total: bool = False


class ActionPreview(BaseModel):
    resumo: list[str]
    escopo: str | None = None
    linhas: list[PreviewLine] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
    pode_desfazer: bool = False


class AgentActionView(BaseModel):
    id: UUID
    kind: ActionKind
    title: str
    status: ActionStatus
    preview: ActionPreview
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime.datetime
    decided_at: datetime.datetime | None
    expires_at: datetime.datetime
