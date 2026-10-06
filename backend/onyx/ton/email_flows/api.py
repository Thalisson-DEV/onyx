"""API models for email flows (definitions are v2: ``steps.FlowDefinitionV2``)."""

import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from onyx.ton.email_flows.catalog import FieldType, ItemState, Operator, TriggerKind
from onyx.ton.email_flows.models import (
    DeliveryStatus,
    FlowOrigin,
    FlowRunStatus,
    FlowStatus,
)
from onyx.ton.email_flows.steps import FlowDefinitionV2


class FlowCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    definition: FlowDefinitionV2
    activate: bool = False


class FlowUpdate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    definition: FlowDefinitionV2


class PreviewRequest(BaseModel):
    flow_id: UUID | None = None
    definition: FlowDefinitionV2 | None = None
    step_id: str | None = None
    flow_name: str | None = None


class TestRequest(BaseModel):
    step_id: str | None = None


class DecisionRequest(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=1000)


class LayoutView(BaseModel):
    brand_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    logo_asset_id: UUID | None
    footer: str = Field(max_length=600)


class DeliveryView(BaseModel):
    id: UUID
    status: DeliveryStatus
    provider: str | None
    to: list[str]
    cc: list[str]
    bcc: list[str]
    batch_no: int
    batch_count: int
    subject: str
    step_id: str | None
    unit: str | None
    error: str | None
    sent_at: datetime.datetime | None
    created_at: datetime.datetime


class RunView(BaseModel):
    id: UUID
    version: int
    event_key: str
    status: FlowRunStatus
    is_test: bool
    item_count: int
    reason: str | None
    resume_at: datetime.datetime | None
    started_at: datetime.datetime
    finished_at: datetime.datetime | None
    deliveries: list[DeliveryView]


class StepLine(BaseModel):
    """One step in plain language, indented by depth (chat card, table)."""

    depth: int
    text: str


class FlowSummary(BaseModel):
    id: UUID
    name: str
    origin: FlowOrigin
    status: FlowStatus
    version: int
    definition: FlowDefinitionV2
    when: str
    steps_text: list[StepLine]
    emails: int
    suggestion_reason: str | None
    problems: list[str]
    last_run: RunView | None
    next_run_at: datetime.datetime | None
    updated_at: datetime.datetime


class FlowDetail(FlowSummary):
    runs: list[RunView]
    created_by: str | None
    approved_by: str | None
    approved_at: datetime.datetime | None


class ApprovalView(BaseModel):
    id: UUID
    flow_id: UUID
    flow_name: str
    run_id: UUID
    step_id: str
    approvers: list[str]
    message: str | None
    item_count: int
    status: str
    can_decide: bool
    created_at: datetime.datetime


class FlowTable(BaseModel):
    flows: list[FlowSummary]
    approvals: list[ApprovalView]
    can_manage: bool
    provider_ready: bool


class FieldView(BaseModel):
    key: str
    label: str
    type: FieldType
    per_item: bool
    operators: list[Operator]
    choices: list[tuple[str, str]]


class TriggerView(BaseModel):
    kind: TriggerKind
    label: str
    description: str
    fields: list[FieldView]
    blocks: list[str]


class AssetView(BaseModel):
    id: UUID
    name: str
    content_type: str
    size_bytes: int


class CatalogView(BaseModel):
    triggers: list[TriggerView]
    operators: dict[Operator, str]
    changes: list[tuple[ItemState, str]]
    system_variables: dict[str, str]
    unit_variables: dict[str, str]
    blocks: dict[str, str]
    assets: list[AssetView]
    layout: LayoutView
    provider: str | None
    provider_ready: bool
    sender: str | None


class PreviewView(BaseModel):
    step_id: str | None
    unit: str | None
    reason: str
    item_count: int
    subject: str | None
    html: str | None
    to: list[str]
    cc: list[str]
    bcc: list[str]
    trace: list[str]


class DraftResult(BaseModel):
    """What the chat card shows for a flow drafted by TON."""

    flow_id: UUID
    name: str
    status: FlowStatus
    created: bool
    when: str
    steps_text: list[StepLine]
    problems: list[str]
    preview_subject: str | None
    editor_url: str
    can_activate: bool
