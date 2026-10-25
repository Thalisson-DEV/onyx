import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CaseOrigin(BaseModel):
    system: str
    file_name: str | None
    imported_at: datetime.datetime | None
    sheets: list[str]


class CaseRow(BaseModel):
    id: UUID
    number: int
    rule_code: str
    title: str
    summary: str
    owner_area: str | None
    owner_name: str | None
    suggested_area: str
    due_date: datetime.date | None
    situation: str
    situation_label: str
    criticality: str
    criticality_label: str
    criticality_reason: str
    impact_open: Decimal
    impact_total: Decimal
    has_amount: bool
    member_count: int
    open_count: int
    fixed_count: int
    months: list[str]
    recurring: bool
    origin: CaseOrigin
    first_detected_at: datetime.datetime
    last_detected_at: datetime.datetime
    verified_at: datetime.datetime | None
    # How Pendências treated the same lines for the closing ("aceito", …).
    closing_note: str | None
    in_board_summary: bool


class EvidenceRow(BaseModel):
    occurrence_code: str
    status: Literal["OPEN", "FIXED"]
    sheet: str | None
    row: int | None
    column: str | None
    emission: datetime.date | None
    unit: str | None
    document: str | None
    history: str | None
    account: str | None
    amount: Decimal | None
    # Rows of one duplicate pair share it.
    group: str | None


class TimelineItem(BaseModel):
    at: datetime.datetime
    kind: Literal["DETECTED", "SEEN_AGAIN", "VERIFIED", "PEOPLE"]
    label: str
    detail: str | None
    actor: str | None


class CaseDetail(CaseRow):
    found: str
    matters: str
    cause: str
    action: str
    action_is_default: bool
    verify: str
    impact_basis: str
    rule_title: str
    decision_reason: str | None
    evidence: list[EvidenceRow]
    evidence_total: int
    timeline: list[TimelineItem]
    owner_areas: list[str]


class OwnerRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)
    owner_area: str = Field(min_length=2, max_length=60)
    owner_name: str | None = Field(default=None, max_length=120)
    # None: the régua's deadline for each case's level.
    due_date: datetime.date | None = None


class ActionRequest(BaseModel):
    action_text: str | None = Field(default=None, max_length=1000)


class DecisionRequest(BaseModel):
    decision: Literal["ACCEPT_RISK", "REOPEN"]
    reason: str = Field(min_length=5, max_length=1000)


class BoardRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)
    include: bool


class ReminderRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)


class ReminderDraft(BaseModel):
    owner: str
    subject: str
    body: str
    can_send: bool
    why_not: str | None


class BoardItem(BaseModel):
    case_id: UUID
    number: int
    criticality: str
    result: str
    problem: str
    impact: str
    cause: str
    action: str
    verified: bool


class BoardSummary(BaseModel):
    open_amount: Decimal
    verified_amount: Decimal
    recurring: int
    unassigned: int
    overdue: int
    items: list[BoardItem]
