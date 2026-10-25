import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TitleKind = Literal["REAL", "ESTIMATE"]
DocumentType = Literal["NF", "NFSE", "FATURA", "RECIBO", "BOLETO", "CONTRATO", "OUTRO"]
DestinationKind = Literal["VEHICLE", "SITE", "STOCK", "ADMINISTRATION"]
SupplierKind = Literal["COMPANY", "PERSON", "EMPLOYEE", "PUBLIC_BODY"]
PixKeyType = Literal["CPF", "CNPJ", "EMAIL", "PHONE", "RANDOM"]
AttachmentRole = Literal["INVOICE", "BOLETO", "RECEIPT", "OTHER"]
TitleAction = Literal[
    "RESUBMIT", "CONFER", "RETURN", "RELEASE", "UNDO_RELEASE", "BOOK", "CANCEL"
]


class UnitOption(BaseModel):
    id: UUID
    code: str
    name: str


class AccountOption(BaseModel):
    id: UUID
    code: str
    label: str


class PayablesContext(BaseModel):
    # Finance (TON administrator): confers, releases and approves suppliers.
    is_finance: bool
    units: list[UnitOption]
    accounts: list[AccountOption]
    notice_business_days: int


class SupplierInput(BaseModel):
    tax_id: str = Field(min_length=11, max_length=20)
    legal_name: str = Field(min_length=2, max_length=300)
    trade_name: str | None = Field(default=None, max_length=300)
    kind: SupplierKind = "COMPANY"
    default_account_id: UUID | None = None
    pix_key_type: PixKeyType | None = None
    pix_key: str | None = Field(default=None, max_length=140)
    bank_code: str | None = Field(default=None, max_length=8)
    bank_agency: str | None = Field(default=None, max_length=16)
    bank_account: str | None = Field(default=None, max_length=32)


class SupplierReview(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)


class SupplierRef(BaseModel):
    id: UUID
    name: str
    tax_id: str


class SupplierView(BaseModel):
    id: UUID
    tax_id: str
    tax_id_display: str
    legal_name: str
    trade_name: str | None
    kind: SupplierKind
    status: str
    default_account_id: UUID | None
    pix_key_type: PixKeyType | None
    pix_key: str | None
    bank_code: str | None
    bank_agency: str | None
    bank_account: str | None
    review_note: str | None
    created_at: datetime.datetime
    # Registered suppliers whose name looks like this one, with another tax ID.
    similar: list[SupplierRef] = Field(default_factory=list)
    # Registered suppliers that share this one's PIX key or bank account.
    shared_account: list[SupplierRef] = Field(default_factory=list)
    open_titles: int = 0


class TitleInput(BaseModel):
    unit_id: UUID
    kind: TitleKind = "REAL"
    supplier_id: UUID
    account_id: UUID
    document_type: DocumentType | None = None
    document_number: str | None = Field(default=None, max_length=60)
    issue_date: datetime.date | None = None
    competence: datetime.date
    due_date: datetime.date
    installment_number: int = Field(default=1, ge=1, le=120)
    installment_count: int = Field(default=1, ge=1, le=120)
    purchase_total: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    destination_kind: DestinationKind
    vehicle_plates: list[str] = Field(default_factory=list, max_length=40)
    destination_note: str | None = Field(default=None, max_length=300)
    description: str = Field(min_length=3, max_length=1000)
    zeev_request: str | None = Field(default=None, max_length=40)
    estimate_until: datetime.date | None = None
    replaces_estimate_id: UUID | None = None


class TitleActionRequest(BaseModel):
    action: TitleAction
    reason: str | None = Field(default=None, max_length=1000)
    ng_reference: str | None = Field(default=None, max_length=80)


class CheckDecisionRequest(BaseModel):
    check_code: str = Field(min_length=1, max_length=40)
    subject: str = Field(default="", max_length=120)
    reason: str = Field(min_length=5, max_length=1000)


class CheckView(BaseModel):
    code: str
    severity: Literal["BLOCK", "ATTENTION", "INFO"]
    title: str
    detail: str
    subject: str
    decided: bool
    decidable: bool
    decision_reason: str | None = None


class AttachmentView(BaseModel):
    id: UUID
    role: AttachmentRole
    original_name: str
    stored_name: str
    content_type: str
    size_bytes: int
    read_kind: str | None
    read_amount: Decimal | None
    read_tax_id: str | None
    read_document_number: str | None
    read_due_date: datetime.date | None
    created_at: datetime.datetime


class EventView(BaseModel):
    id: UUID
    action: str
    from_status: str | None
    to_status: str | None
    reason: str | None
    actor: str | None
    created_at: datetime.datetime


class RelatedTitle(BaseModel):
    id: UUID
    number: int
    unit_name: str
    installment_number: int
    installment_count: int
    amount: Decimal
    due_date: datetime.date
    status: str


class TitleRow(BaseModel):
    id: UUID
    number: int
    kind: TitleKind
    status: str
    unit_id: UUID
    unit_name: str
    supplier_id: UUID
    supplier_name: str
    supplier_tax_id: str
    account_code: str
    account_label: str
    document_type: str | None
    document_number: str | None
    installment_number: int
    installment_count: int
    amount: Decimal
    competence: datetime.date
    due_date: datetime.date
    description: str
    vehicle_plates: list[str]
    attachment_count: int
    blocking: int
    attention: int
    submitted_at: datetime.datetime
    # "PIX CNPJ", "Boleto" or "Transferência": how finance will pay it.
    payment_method: str
    # The most serious open finding, for the "O TON apontou" column.
    top_issue: str | None
    top_issue_severity: str | None


class TitleDetail(TitleRow):
    account_id: UUID
    issue_date: datetime.date | None
    purchase_total: Decimal
    destination_kind: DestinationKind
    destination_note: str | None
    zeev_request: str | None
    estimate_until: datetime.date | None
    replaces_estimate_id: UUID | None
    replaced_by_id: UUID | None
    ng_reference: str | None
    created_by: str | None
    supplier: SupplierView
    attachments: list[AttachmentView]
    checks: list[CheckView]
    events: list[EventView]
    same_document: list[RelatedTitle]
    can_edit: bool
    actions: list[TitleAction]
    confirmations: list["ConfirmationView"]
    # Text finance can paste into the NG "Histórico" field.
    ng_history: str


class ConfirmationView(BaseModel):
    label: str
    value: str
    state: Literal["OK", "ATTENTION", "MISMATCH", "UNKNOWN"]


class InstallmentView(BaseModel):
    number: int
    due_date: datetime.date
    amount: Decimal


class DocumentReadView(BaseModel):
    """What the TON read from a file before the title exists."""

    kind: str | None
    amount: Decimal | None
    tax_id: str | None
    tax_id_display: str | None
    document_type: str | None
    document_number: str | None
    issue_date: datetime.date | None
    due_date: datetime.date | None
    issuer_name: str | None
    installments: list[InstallmentView]
    # The registered supplier with the tax ID read, if any.
    supplier: SupplierRef | None
    supplier_status: str | None


class BatchRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=500)


class BatchActionRequest(BatchRequest):
    action: Literal["CONFER", "RELEASE", "BOOK"]


class BatchFailure(BaseModel):
    id: UUID
    number: int
    message: str


class BatchActionResult(BaseModel):
    done: list[UUID]
    failed: list[BatchFailure]


TitleDetail.model_rebuild()
