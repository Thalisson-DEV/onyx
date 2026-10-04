"""Account classification table: NG account code -> natureza -> DRE group."""

import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ClassificationStatus(str, Enum):
    PENDING = "PENDING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"


class ClassificationOrigin(str, Enum):
    CONTROLLER_WORKBOOK = "CONTROLLER_WORKBOOK"
    ANALOGY = "ANALOGY"
    MANUAL = "MANUAL"


class SuggestionConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NatureView(BaseModel):
    account_id: UUID
    code: str
    natureza: str
    dre_group: str
    dre_group_code: str | None
    accounts: int


class DreGroupView(BaseModel):
    """A DRE subtotal a new natureza can be placed under."""

    code: str
    label: str


class PrefixPattern(BaseModel):
    """What the confirmed codes under the same NG prefix are classified as."""

    prefix: str
    natureza: str
    matches: int
    total: int


class SuggestionView(BaseModel):
    account_id: UUID
    natureza: str
    confidence: SuggestionConfidence
    rationale: str
    question: str | None
    model_name: str | None
    created_at: datetime.datetime
    agrees_with_current: bool


class ClassificationRow(BaseModel):
    account_code: str
    description: str
    account_id: UUID | None
    natureza: str | None
    dre_group: str | None
    status: ClassificationStatus
    origin: ClassificationOrigin | None
    reason: str | None
    decided_by: str | None
    decided_at: datetime.datetime | None
    decided_by_person: bool
    entries: int
    total_amount: Decimal
    monthly: dict[str, Decimal]
    units: list[str]
    pattern: PrefixPattern | None
    suggestion: SuggestionView | None


class ClassificationTable(BaseModel):
    source_id: UUID
    source_name: str
    normalization_run_id: UUID | None
    periods: list[str]
    natures: list[NatureView]
    groups: list[DreGroupView]
    rows: list[ClassificationRow]
    briefing: "BriefingView | None"
    changes_since_calculation: int


class BriefingView(BaseModel):
    summary: str
    model_name: str | None
    created_at: datetime.datetime


class ClassificationConfirm(BaseModel):
    account_code: str = Field(min_length=1, max_length=100)
    note: str | None = Field(None, max_length=1000)


class ClassificationChange(BaseModel):
    account_code: str = Field(min_length=1, max_length=100)
    account_id: UUID
    reason: str = Field(min_length=3, max_length=500)


class ClassificationConfirmBatch(BaseModel):
    account_codes: list[str] = Field(min_length=1, max_length=500)
    note: str | None = Field(None, max_length=1000)


class NatureCreate(BaseModel):
    """A natureza the Controladoria adds, as in the AUXILIARES sheet."""

    natureza: str = Field(min_length=2, max_length=100)
    dre_group_code: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=500)


class EntryView(BaseModel):
    date: datetime.date
    unit: str | None
    document: str | None
    history: str
    amount: Decimal | None


class SuggestionRequest(BaseModel):
    """Empty list means every pending or awaiting code."""

    account_codes: list[str] = Field(default_factory=list, max_length=200)
    # The screen sends small chunks and asks for the briefing once at the end.
    briefing: bool = True


class SuggestionRunResult(BaseModel):
    requested: int
    suggested: int
    skipped: list[str]
    model_name: str | None
    briefing: bool


ClassificationTable.model_rebuild()
