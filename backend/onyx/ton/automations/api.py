"""API shapes of automations."""

import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from onyx.ton.automations.definition import (
    AutomationDefinition,
    AutomationKind,
    AutomationOrigin,
    AutomationStatus,
    RunMode,
    RunStatus,
    StepStatus,
)

# -- catalog -----------------------------------------------------------------


class FieldView(BaseModel):
    key: str
    label: str
    kind: str
    options: list[tuple[str, str]] = Field(default_factory=list)
    placeholder: str | None = None


class ParamView(BaseModel):
    key: str
    label: str
    kind: str
    required: bool
    default: Any = None
    help: str | None = None
    placeholder: str | None = None
    options: list[tuple[str, str]] = Field(default_factory=list)
    dynamic: bool
    min: float | None = None
    max: float | None = None
    item_fields: list[FieldView] = Field(default_factory=list)
    show_if: tuple[str, list[str]] | None = None
    advanced: bool = False


class OutputView(BaseModel):
    key: str
    label: str
    type: str
    description: str = ""
    item_fields: list["OutputView"] = Field(default_factory=list)


class RetryView(BaseModel):
    policy: str
    count: int
    interval_seconds: int


class NodeTypeView(BaseModel):
    type: str
    group: str
    label: str
    description: str
    icon: str
    params: list[ParamView]
    outputs: list[OutputView]
    container: str | None
    is_trigger: bool
    side_effect: bool
    ai: bool
    satisfies: list[AutomationKind]
    dynamic_outputs: str | None
    default_retry: RetryView
    keywords: list[str]


class KindView(BaseModel):
    key: AutomationKind
    label: str
    description: str


class TemplateView(BaseModel):
    key: str
    name: str
    description: str
    kind: AutomationKind
    trigger_type: str


class AssetView(BaseModel):
    id: UUID
    name: str


class AutomationRef(BaseModel):
    id: UUID
    name: str


class CatalogView(BaseModel):
    nodes: list[NodeTypeView]
    groups: dict[str, str]
    kinds: list[KindView]
    templates: list[TemplateView]
    functions: dict[str, str]
    operators: dict[str, str]
    blocks: dict[str, str]
    assets: list[AssetView]
    automations: list[AutomationRef]
    provider_ready: bool
    sender: str | None
    llm_ready: bool


# -- automations ---------------------------------------------------------------


class IssueView(BaseModel):
    severity: str
    message: str
    node_id: str | None = None
    param: str | None = None


class RunSummary(BaseModel):
    id: UUID
    status: RunStatus
    mode: RunMode
    trigger_key: str
    version: int | None = None
    error: str | None = None
    message: str | None = None
    waiting_on: str | None = None
    resume_at: datetime.datetime | None = None
    created_at: datetime.datetime
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    duration_ms: int | None = None
    triggered_by: str | None = None


class AutomationSummary(BaseModel):
    id: UUID
    name: str
    description: str | None
    kind: AutomationKind
    status: AutomationStatus
    origin: AutomationOrigin
    trigger_type: str
    trigger_label: str
    when: str
    version: int
    steps_count: int
    last_run: RunSummary | None
    next_run_at: datetime.datetime | None
    runs_28d: dict[str, int]
    problems: list[str]
    suggestion_reason: str | None
    updated_at: datetime.datetime


class ApprovalView(BaseModel):
    id: UUID
    automation_id: UUID
    automation_name: str
    run_id: UUID
    node_id: str
    title: str
    details: str | None
    options: list[str]
    approvers: list[str]
    status: str
    outcome: str | None
    comment: str | None
    decided_by: str | None
    decided_at: datetime.datetime | None
    expires_at: datetime.datetime | None
    created_at: datetime.datetime
    can_decide: bool


class AutomationTable(BaseModel):
    automations: list[AutomationSummary]
    approvals: list[ApprovalView]
    can_manage: bool
    provider_ready: bool


class VersionView(BaseModel):
    version: int
    name: str
    note: str | None
    created_by: str | None
    created_at: datetime.datetime


class AutomationDetail(AutomationSummary):
    definition: AutomationDefinition
    issues: list[IssueView]
    owner: str | None
    created_by: str | None
    updated_by: str | None
    created_at: datetime.datetime
    active_since: datetime.datetime | None
    versions: list[VersionView]
    runs: list[RunSummary]
    can_manage: bool
    average_duration_ms: int | None


class StepView(BaseModel):
    node_id: str
    iteration: str
    node_type: str
    status: StepStatus
    attempt: int
    inputs: dict[str, Any] | None
    outputs: dict[str, Any] | None
    error: str | None
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    next_retry_at: datetime.datetime | None
    duration_ms: int | None


class RunDetail(RunSummary):
    automation_id: UUID
    automation_name: str
    definition: AutomationDefinition
    trigger_output: dict[str, Any]
    steps: list[StepView]
    approvals: list[ApprovalView]
    can_cancel: bool
    can_resubmit: bool


class NoticeView(BaseModel):
    id: UUID
    automation_id: UUID
    automation_name: str
    run_id: UUID | None
    title: str
    message: str | None
    severity: str
    link: str | None
    created_at: datetime.datetime


# -- requests ------------------------------------------------------------------


class AutomationCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    kind: AutomationKind = AutomationKind.GENERAL
    definition: AutomationDefinition | None = None
    template: str | None = None


class AutomationUpdate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    kind: AutomationKind
    definition: AutomationDefinition
    note: str | None = Field(default=None, max_length=300)


class StatusRequest(BaseModel):
    status: AutomationStatus


class RunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class ValidateRequest(BaseModel):
    definition: dict[str, Any]
    kind: AutomationKind = AutomationKind.GENERAL


class ValidateResult(BaseModel):
    issues: list[IssueView]
    problems: list[str]
    structure_error: str | None = None
    suggested_kind: AutomationKind | None = None


class DecisionRequest(BaseModel):
    outcome: str = Field(min_length=1, max_length=120)
    comment: str | None = Field(default=None, max_length=1000)


class DraftRequest(BaseModel):
    request: str = Field(min_length=5, max_length=4000)
    automation_id: UUID | None = None
    definition: AutomationDefinition | None = None


class DraftResult(BaseModel):
    automation_id: UUID
    name: str
    kind: AutomationKind
    status: AutomationStatus
    created: bool
    summary: str
    when: str
    steps_text: list[str]
    problems: list[str]
    missing: list[str]
    editor_url: str
    definition: AutomationDefinition


class PreviewRequest(BaseModel):
    definition: AutomationDefinition
    node_id: str
    automation_id: UUID | None = None
    name: str | None = None


class PreviewResult(BaseModel):
    subject: str | None
    html: str | None
    reason: str
    outputs_sample: dict[str, Any] = Field(default_factory=dict)


class FileView(BaseModel):
    id: UUID
    name: str
    size_bytes: int
