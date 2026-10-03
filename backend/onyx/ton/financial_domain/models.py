from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MappingKind(StrEnum):
    ACCOUNT = "ACCOUNT"
    UNIT = "UNIT"
    ENTITY = "ENTITY"
    BUDGET_ACCOUNT = "BUDGET_ACCOUNT"
    BUDGET_UNIT = "BUDGET_UNIT"
    BILLING_ACCOUNT = "BILLING_ACCOUNT"
    BILLING_TAX_ACCOUNT = "BILLING_TAX_ACCOUNT"
    BUDGET_PERIOD = "BUDGET_PERIOD"


class AccountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=500)
    dre_classification: str | None = Field(default=None, max_length=100)
    actual_amount_basis: Literal["MOVEMENT", "FINAL"] | None = None


class AccountView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    label: str
    dre_classification: str | None
    actual_amount_basis: Literal["MOVEMENT", "FINAL"] | None


class UnitView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str


class MappingCreate(BaseModel):
    source_id: UUID
    kind: MappingKind
    source_key: str = Field(min_length=1, max_length=500)
    account_id: UUID | None = None
    unit_id: UUID | None = None
    calendar_period: date | None = None
    source_snapshot_id: UUID | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=500)


class MappingView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision_id: UUID
    source_id: UUID
    kind: MappingKind
    source_key: str
    account_id: UUID | None
    unit_id: UUID | None
    calendar_period: date | None
    source_snapshot_id: UUID | None
    effective_from: date | None
    effective_to: date | None
    revision_number: int


class AmountBasisApproval(BaseModel):
    basis: Literal["MOVEMENT", "FINAL"]
    reason: str = Field(min_length=1, max_length=500)


class AmountBasisRevisionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    number: int
    account_id: UUID
    basis: Literal["MOVEMENT", "FINAL"]
    reason: str
    created_by: UUID | None
    created_at: datetime


class BudgetInput(BaseModel):
    source_id: UUID
    execution_id: UUID


class InputPolicy(StrEnum):
    """What a normalization run may read besides the reviewed NG actuals."""

    ACTUAL_ONLY = "ACTUAL_ONLY"
    ACTUAL_AND_APPROVED_BUDGET = "ACTUAL_AND_APPROVED_BUDGET"


class NormalizationRequest(BaseModel):
    ng_source_id: UUID
    review_run_id: UUID
    billing_source_id: UUID
    billing_execution_id: UUID
    # Empty means an Actual-only run: Orçado stays zero and budget coverage
    # is not evaluated.
    budgets: list[BudgetInput] = Field(default_factory=list)
    # Which inputs the run may read. None derives it from ``budgets``: budget
    # workbooks named explicitly are budgets someone approved for this run.
    input_policy: InputPolicy | None = None

    @property
    def effective_input_policy(self) -> InputPolicy:
        if self.input_policy is not None:
            return self.input_policy
        return (
            InputPolicy.ACTUAL_AND_APPROVED_BUDGET
            if self.budgets
            else InputPolicy.ACTUAL_ONLY
        )


class NormalizationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    input_digest: str
    attempt_no: int
    status: str
    review_run_id: UUID
    dataset_revision: str
    dataset_as_of: datetime
    billing_execution_id: UUID
    budget_execution_ids: list[str]
    input_policy: str = "ACTUAL_ONLY"
    mapping_revision_number: int
    amount_basis_revision_number: int
    reconciliation_decision_number: int
    derivation_version: str
    authority_policy_version: str
    statistics: dict[str, int]
    error_code: str | None
    started_at: datetime
    finished_at: datetime | None


class FactView(BaseModel):
    id: UUID
    source_record_id: UUID
    source_id: UUID
    source_snapshot_id: UUID
    source_execution_id: UUID
    fact_type: str
    account_id: UUID | None
    account_classification: str | None
    unit_id: UUID | None
    unit_code: str | None
    unit_kind: str | None
    period: date | None
    amount: Decimal | None
    amount_basis: str
    authority_role: str


class ReconciliationItemView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    run_id: UUID
    actual_fact_id: UUID | None
    billing_fact_id: UUID | None
    status: str
    evidence_key: str | None


class ReadinessView(BaseModel):
    run_id: UUID
    period: date
    unit_id: UUID | None
    ready: bool
    blockers: dict[str, int]
    actual_count: int
    billing_count: int
    derived_count: int
    budget_count: int
    actual_budget_aligned_count: int
    reconciliation: dict[str, int]
    authority_policy_version: str
    dataset_revision: str
    mapping_revision_number: int
    derivation_version: str


class DreInputDataset(BaseModel):
    """Scoped DATA-004 boundary for the DRE engine."""

    readiness: ReadinessView
    actuals: list[FactView]
    budgets: list[FactView]
