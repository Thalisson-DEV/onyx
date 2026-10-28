"""Unit payables: the unit sends each title, finance confers and releases it.

Who does what:

* **Finance** (a TON administrator) sees every unit, confers, returns,
  releases, records the NG booking and approves suppliers.
* **A unit manager** sends and corrects the titles of the units they see and
  proposes suppliers; nothing they send is released without finance.

Paid status is never typed here: it will come from the NG settlement or a
reconciled bank statement. The TON does not write to the NG.
"""

import datetime
import difflib
import io
import re
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton.acl import business_unit_visible_clause, is_ton_administrator
from onyx.db.ton.models import (
    BusinessUnit,
    FinancialAccount,
    PayableAttachment,
    PayableCheckDecision,
    PayableEvent,
    PayableSupplier,
    PayableTitle,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.payables import checks as rules
from onyx.ton.payables import payment_batch
from onyx.ton.payables.ai_reading import AiDocumentReader
from onyx.ton.payables.documents import read_attachment
from onyx.ton.payables.identifiers import (
    digits,
    document_key,
    format_tax_id,
    name_key,
    plate,
    tax_id,
)
from onyx.ton.payables.models import (
    AccountOption,
    AttachmentView,
    BatchActionRequest,
    BatchActionResult,
    BatchFailure,
    CheckDecisionRequest,
    CheckView,
    ConfirmationView,
    DocumentReadView,
    EventView,
    InstallmentView,
    PayablesContext,
    RelatedTitle,
    SupplierInput,
    SupplierRef,
    SupplierReview,
    SupplierView,
    TitleAction,
    TitleActionRequest,
    TitleDetail,
    TitleInput,
    TitleRow,
    UnitOption,
)

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = (".pdf", ".xml", ".jpg", ".jpeg", ".png")
# The unit may still change the title; finance has not conferred it.
EDITABLE = frozenset(
    {"WAITING_ATTACHMENT", "WAITING_SUPPLIER", "RECEIVED", "RETURNED", "ESTIMATE_OPEN"}
)
CLOSED = frozenset({"BOOKED", "PAID", "CANCELLED", "ESTIMATE_REPLACED"})
_FINANCE_ACTIONS: dict[str, frozenset[str]] = {
    "CONFER": frozenset({"RECEIVED"}),
    "RETURN": frozenset(
        {"WAITING_ATTACHMENT", "WAITING_SUPPLIER", "RECEIVED", "CONFERRED"}
    ),
    "RELEASE": frozenset({"CONFERRED"}),
    "UNDO_RELEASE": frozenset({"RELEASED"}),
    "BOOK": frozenset({"RELEASED"}),
    "CANCEL": frozenset(EDITABLE | {"CONFERRED", "RELEASED"}),
}
_ACTION_TARGET = {
    "CONFER": "CONFERRED",
    "RETURN": "RETURNED",
    "RELEASE": "RELEASED",
    "UNDO_RELEASE": "CONFERRED",
    "BOOK": "BOOKED",
    "CANCEL": "CANCELLED",
}
_DOC_LABEL = {
    "NF": "NF",
    "NFSE": "NFS-e",
    "FATURA": "Fatura",
    "RECIBO": "Recibo",
    "BOLETO": "Boleto",
    "CONTRATO": "Contrato",
    "OUTRO": "Documento",
}
_ROLE_FILE = {
    "INVOICE": "NOTA",
    "BOLETO": "BOLETO",
    "RECEIPT": "RECIBO",
    "OTHER": "ANEXO",
}


def _invalid(message: str) -> OnyxError:
    return OnyxError(OnyxErrorCode.INVALID_INPUT, message)


def _not_found(message: str) -> OnyxError:
    return OnyxError(OnyxErrorCode.NOT_FOUND, message)


def _today() -> datetime.date:
    return (
        datetime.datetime.now(datetime.UTC)
        .astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
        .date()
    )


# ---------------------------------------------------------------- access


def is_finance(user: User) -> bool:
    return is_ton_administrator(user)


def _visible_units(session: Session, user: User) -> list[BusinessUnit]:
    query = sa.select(BusinessUnit).where(BusinessUnit.is_active.is_(True))
    if not is_finance(user):
        query = query.where(business_unit_visible_clause(user))
    return list(session.scalars(query.order_by(BusinessUnit.name)))


def _visible_unit_ids(session: Session, user: User) -> set[UUID]:
    return {unit.id for unit in _visible_units(session, user)}


def _require_finance(user: User) -> None:
    if not is_finance(user):
        raise OnyxError(
            OnyxErrorCode.INSUFFICIENT_PERMISSIONS,
            "Somente o financeiro faz esta etapa.",
        )


def _get_title(session: Session, user: User, title_id: UUID) -> PayableTitle:
    title = session.get(PayableTitle, title_id)
    if title is None or (
        not is_finance(user) and title.unit_id not in _visible_unit_ids(session, user)
    ):
        raise _not_found("Título não encontrado.")
    return title


# ---------------------------------------------------------------- context


def context(session: Session, user: User) -> PayablesContext:
    # Group 1 is revenue and taxes on billing: never a unit payable.
    accounts = session.scalars(
        sa.select(FinancialAccount)
        .where(
            FinancialAccount.dre_classification == "EXPENSE",
            ~FinancialAccount.code.startswith("1."),
        )
        .order_by(FinancialAccount.code)
    )
    return PayablesContext(
        is_finance=is_finance(user),
        units=[
            UnitOption(id=unit.id, code=unit.code, name=unit.name)
            for unit in _visible_units(session, user)
            if unit.code != "SEM-UNIDADE"
        ],
        accounts=[
            AccountOption(id=account.id, code=account.code, label=account.label)
            for account in accounts
        ],
        notice_business_days=rules.NOTICE_BUSINESS_DAYS,
    )


# ---------------------------------------------------------------- suppliers


def _supplier_name(supplier: PayableSupplier) -> str:
    return supplier.trade_name or supplier.legal_name


def _ref(supplier: PayableSupplier) -> SupplierRef:
    return SupplierRef(
        id=supplier.id,
        name=_supplier_name(supplier),
        tax_id=format_tax_id(supplier.tax_id),
    )


def _pix_norm(supplier: PayableSupplier) -> str | None:
    if not supplier.pix_key:
        return None
    if supplier.pix_key_type in ("CPF", "CNPJ", "PHONE"):
        return digits(supplier.pix_key)
    return supplier.pix_key.strip().lower()


def _bank_norm(supplier: PayableSupplier) -> tuple[str, str, str] | None:
    if not (supplier.bank_code and supplier.bank_agency and supplier.bank_account):
        return None
    return (
        digits(supplier.bank_code),
        digits(supplier.bank_agency),
        digits(supplier.bank_account),
    )


def _shared_account(
    supplier: PayableSupplier, everyone: Iterable[PayableSupplier]
) -> list[PayableSupplier]:
    pix = _pix_norm(supplier)
    bank = _bank_norm(supplier)
    if pix is None and bank is None:
        return []
    return [
        other
        for other in everyone
        if other.id != supplier.id
        and other.status != "REJECTED"
        and (
            (pix is not None and _pix_norm(other) == pix)
            or (bank is not None and _bank_norm(other) == bank)
        )
    ]


def _similar(
    supplier: PayableSupplier, everyone: Iterable[PayableSupplier]
) -> list[PayableSupplier]:
    keys = {name_key(supplier.legal_name)}
    if supplier.trade_name:
        keys.add(name_key(supplier.trade_name))
    keys.discard("")
    found = []
    for other in everyone:
        if other.id == supplier.id or other.tax_id == supplier.tax_id:
            continue
        other_keys = {name_key(other.legal_name)}
        if other.trade_name:
            other_keys.add(name_key(other.trade_name))
        if any(
            difflib.SequenceMatcher(None, mine, theirs).ratio() >= 0.82
            or (min(len(mine), len(theirs)) >= 5 and (mine in theirs or theirs in mine))
            for mine in keys
            for theirs in other_keys
            if theirs
        ):
            found.append(other)
    return found[:5]


def _supplier_view(
    session: Session,
    supplier: PayableSupplier,
    everyone: list[PayableSupplier] | None = None,
    open_titles: int = 0,
) -> SupplierView:
    pool = (
        everyone
        if everyone is not None
        else list(session.scalars(sa.select(PayableSupplier)))
    )
    return SupplierView(
        id=supplier.id,
        tax_id=supplier.tax_id,
        tax_id_display=format_tax_id(supplier.tax_id),
        legal_name=supplier.legal_name,
        trade_name=supplier.trade_name,
        kind=supplier.kind,  # type: ignore[arg-type]
        status=supplier.status,
        default_account_id=supplier.default_account_id,
        pix_key_type=supplier.pix_key_type,  # type: ignore[arg-type]
        pix_key=supplier.pix_key,
        bank_code=supplier.bank_code,
        bank_agency=supplier.bank_agency,
        bank_account=supplier.bank_account,
        review_note=supplier.review_note,
        created_at=supplier.created_at,
        similar=[_ref(other) for other in _similar(supplier, pool)]
        if supplier.status == "PENDING"
        else [],
        shared_account=[_ref(other) for other in _shared_account(supplier, pool)],
        open_titles=open_titles,
    )


def list_suppliers(
    session: Session, user: User, search: str | None, status: str | None
) -> list[SupplierView]:
    everyone = list(session.scalars(sa.select(PayableSupplier)))
    finance = is_finance(user)
    open_counts: dict[UUID, int] = {
        supplier_id: count
        for supplier_id, count in session.execute(
            sa.select(PayableTitle.supplier_id, sa.func.count())
            .where(PayableTitle.status.not_in(CLOSED))
            .group_by(PayableTitle.supplier_id)
        ).tuples()
    }
    needle = name_key(search) if search else ""
    needle_digits = digits(search or "")
    result = []
    for supplier in everyone:
        if status and supplier.status != status:
            continue
        # A unit sees the approved registry and what it proposed itself.
        if (
            not finance
            and supplier.status != "ACTIVE"
            and supplier.created_by != user.id
        ):
            continue
        if search:
            names = (
                name_key(supplier.legal_name)
                + " "
                + name_key(supplier.trade_name or "")
            )
            if needle not in names and not (
                needle_digits and needle_digits in supplier.tax_id
            ):
                continue
        result.append(
            _supplier_view(session, supplier, everyone, open_counts.get(supplier.id, 0))
        )
    result.sort(
        key=lambda view: (
            view.status != "PENDING",
            (view.trade_name or view.legal_name).upper(),
        )
    )
    return result


def _apply_supplier(supplier: PayableSupplier, request: SupplierInput) -> None:
    supplier.legal_name = request.legal_name.strip()
    supplier.trade_name = (request.trade_name or "").strip() or None
    supplier.kind = request.kind
    supplier.default_account_id = request.default_account_id
    pix = (request.pix_key or "").strip() or None
    if pix and request.pix_key_type is None:
        raise _invalid("Informe o tipo da chave PIX.")
    if pix and request.pix_key_type in ("CPF", "CNPJ") and tax_id(pix) is None:
        raise _invalid("A chave PIX não é um CPF ou CNPJ válido.")
    supplier.pix_key_type = request.pix_key_type if pix else None
    supplier.pix_key = pix
    bank = [
        (request.bank_code or "").strip(),
        (request.bank_agency or "").strip(),
        (request.bank_account or "").strip(),
    ]
    if any(bank) and not all(bank):
        raise _invalid("Para conta bancária, informe banco, agência e conta.")
    supplier.bank_code, supplier.bank_agency, supplier.bank_account = (
        value or None for value in bank
    )
    if not pix and not all(bank):
        raise _invalid("Informe a chave PIX ou a conta bancária do fornecedor.")


def create_supplier(
    session: Session, user: User, request: SupplierInput
) -> SupplierView:
    number = tax_id(request.tax_id)
    if number is None:
        raise _invalid("CPF ou CNPJ inválido. Confira os dígitos.")
    existing = session.scalar(
        sa.select(PayableSupplier).where(PayableSupplier.tax_id == number)
    )
    if existing is not None:
        raise OnyxError(
            OnyxErrorCode.CONFLICT,
            f"{format_tax_id(number)} já está cadastrado como {_supplier_name(existing)}.",
        )
    finance = is_finance(user)
    supplier = PayableSupplier(
        tax_id=number,
        status="ACTIVE" if finance else "PENDING",
        created_by=user.id,
        approved_by=user.id if finance else None,
        approved_at=datetime.datetime.now(datetime.UTC) if finance else None,
    )
    _apply_supplier(supplier, request)
    session.add(supplier)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise OnyxError(OnyxErrorCode.CONFLICT, "Fornecedor já cadastrado.")
    return _supplier_view(session, supplier)


def update_supplier(
    session: Session, user: User, supplier_id: UUID, request: SupplierInput
) -> SupplierView:
    supplier = session.get(PayableSupplier, supplier_id)
    if supplier is None:
        raise _not_found("Fornecedor não encontrado.")
    own_pending = supplier.status == "PENDING" and supplier.created_by == user.id
    if not (is_finance(user) or own_pending):
        _require_finance(user)
    if tax_id(request.tax_id) != supplier.tax_id:
        raise _invalid("O CPF/CNPJ não muda. Cadastre outro fornecedor.")
    _apply_supplier(supplier, request)
    session.commit()
    _refresh_supplier_titles(session, user, supplier)
    return _supplier_view(session, supplier)


def review_supplier(
    session: Session, user: User, supplier_id: UUID, request: SupplierReview
) -> SupplierView:
    _require_finance(user)
    supplier = session.get(PayableSupplier, supplier_id)
    if supplier is None:
        raise _not_found("Fornecedor não encontrado.")
    if not request.approve and not (request.note or "").strip():
        raise _invalid("Diga o motivo da recusa.")
    supplier.status = "ACTIVE" if request.approve else "REJECTED"
    supplier.review_note = (request.note or "").strip() or None
    supplier.approved_by = user.id
    supplier.approved_at = datetime.datetime.now(datetime.UTC)
    session.commit()
    _refresh_supplier_titles(session, user, supplier)
    return _supplier_view(session, supplier)


# ---------------------------------------------------------------- titles


def _event(
    session: Session,
    title: PayableTitle,
    user: User,
    action: str,
    from_status: str | None,
    reason: str | None = None,
) -> None:
    session.add(
        PayableEvent(
            title_id=title.id,
            action=action,
            from_status=from_status,
            to_status=title.status,
            reason=reason,
            actor_id=user.id,
        )
    )


def _intake_status(session: Session, title: PayableTitle) -> str:
    if title.kind == "ESTIMATE":
        return "ESTIMATE_OPEN"
    supplier = session.get(PayableSupplier, title.supplier_id)
    assert supplier is not None
    if supplier.status != "ACTIVE":
        return "WAITING_SUPPLIER"
    has_attachment = session.scalar(
        sa.select(sa.func.count())
        .select_from(PayableAttachment)
        .where(PayableAttachment.title_id == title.id)
    )
    return "RECEIVED" if has_attachment else "WAITING_ATTACHMENT"


def _refresh_intake(
    session: Session, user: User, title: PayableTitle, action: str
) -> None:
    # A returned title waits for the unit to send it again (RESUBMIT).
    if title.status not in ("WAITING_ATTACHMENT", "WAITING_SUPPLIER", "RECEIVED"):
        return
    before = title.status
    title.status = _intake_status(session, title)
    if title.status != before:
        # The step that caused it (an attachment, an approval) is its own event.
        _event(session, title, user, "STATUS", before, action)


def _refresh_supplier_titles(
    session: Session, user: User, supplier: PayableSupplier
) -> None:
    titles = session.scalars(
        sa.select(PayableTitle).where(
            PayableTitle.supplier_id == supplier.id,
            PayableTitle.status.in_(
                ("WAITING_SUPPLIER", "RECEIVED", "WAITING_ATTACHMENT")
            ),
        )
    )
    for title in titles:
        _refresh_intake(session, user, title, "SUPPLIER_REVIEWED")
    session.commit()


def _validate(
    session: Session, user: User, request: TitleInput, title: PayableTitle | None
) -> dict:
    if request.unit_id not in _visible_unit_ids(session, user):
        raise _invalid("Você não envia contas desta unidade.")
    supplier = session.get(PayableSupplier, request.supplier_id)
    if supplier is None or supplier.status in ("REJECTED", "INACTIVE"):
        raise _invalid("Escolha um fornecedor do cadastro.")
    account = session.get(FinancialAccount, request.account_id)
    if account is None:
        raise _invalid("Escolha a natureza.")
    real = request.kind == "REAL"
    if real:
        missing = [
            label
            for label, value in (
                ("tipo do documento", request.document_type),
                ("número do documento", (request.document_number or "").strip()),
                ("data de emissão", request.issue_date),
            )
            if not value
        ]
        if missing:
            raise _invalid("Falta informar: " + ", ".join(missing) + ".")
    elif request.estimate_until is None:
        raise _invalid("Informe até quando vale a estimativa.")
    today = _today()
    if request.issue_date and request.issue_date > today:
        raise _invalid("A data de emissão não pode ser no futuro.")
    if request.issue_date and request.due_date < request.issue_date:
        raise _invalid("O vencimento é anterior à emissão.")
    if request.installment_number > request.installment_count:
        raise _invalid("A parcela não pode passar do total de parcelas.")
    if request.amount > request.purchase_total:
        raise _invalid("O valor do título é maior que o total da compra.")
    if request.installment_count == 1 and request.amount != request.purchase_total:
        raise _invalid("Em parcela única, o valor do título é o total da compra.")
    plates: list[str] = []
    if request.destination_kind == "VEHICLE":
        invalid = [raw for raw in request.vehicle_plates if plate(raw) is None]
        if invalid:
            raise _invalid("Placa inválida: " + ", ".join(invalid) + ".")
        plates = sorted({plate(raw) or "" for raw in request.vehicle_plates})
        if not plates:
            raise _invalid("Informe a placa de ao menos um veículo.")
    note = (request.destination_note or "").strip() or None
    if request.destination_kind == "SITE" and not note:
        raise _invalid("Informe a obra ou o local.")
    estimate: PayableTitle | None = None
    if request.replaces_estimate_id:
        estimate = session.get(PayableTitle, request.replaces_estimate_id)
        if (
            estimate is None
            or estimate.kind != "ESTIMATE"
            or estimate.unit_id != request.unit_id
            or estimate.supplier_id != request.supplier_id
            or (
                estimate.status != "ESTIMATE_OPEN"
                and (title is None or estimate.id != title.replaces_estimate_id)
            )
        ):
            raise _invalid("A estimativa escolhida não é desta unidade e fornecedor.")
        if not real:
            raise _invalid("Só uma conta real substitui uma estimativa.")
    return {
        "unit_id": request.unit_id,
        "kind": request.kind,
        "supplier_id": supplier.id,
        "account_id": account.id,
        "document_type": request.document_type,
        "document_number": (request.document_number or "").strip() or None,
        "document_key": document_key(request.document_number),
        "issue_date": request.issue_date,
        "competence": request.competence.replace(day=1),
        "due_date": request.due_date,
        "installment_number": request.installment_number,
        "installment_count": request.installment_count,
        "purchase_total": request.purchase_total,
        "amount": request.amount,
        "destination_kind": request.destination_kind,
        "vehicle_plates": plates,
        "destination_note": note,
        "description": request.description.strip(),
        "zeev_request": (request.zeev_request or "").strip() or None,
        "estimate_until": request.estimate_until if not real else None,
        "replaces_estimate_id": estimate.id if estimate else None,
        "_estimate": estimate,
    }


def create_title(session: Session, user: User, request: TitleInput) -> TitleDetail:
    values = _validate(session, user, request, None)
    estimate: PayableTitle | None = values.pop("_estimate")
    title = PayableTitle(**values, status="RECEIVED", created_by=user.id)
    session.add(title)
    session.flush()
    title.status = _intake_status(session, title)
    _event(session, title, user, "SUBMITTED", None)
    if estimate is not None:
        before = estimate.status
        estimate.status = "ESTIMATE_REPLACED"
        _event(
            session,
            estimate,
            user,
            "REPLACED",
            before,
            f"Substituída por CP-{title.number:06d}",
        )
    session.commit()
    return get_title(session, user, title.id)


def update_title(
    session: Session, user: User, title_id: UUID, request: TitleInput
) -> TitleDetail:
    title = _get_title(session, user, title_id)
    if title.status not in EDITABLE:
        raise _invalid(
            "Este título já foi conferido. Peça ao financeiro para devolvê-lo."
        )
    if request.kind != title.kind:
        raise _invalid(
            "Uma estimativa não vira conta real por edição: envie a conta e escolha a estimativa que ela substitui."
        )
    values = _validate(session, user, request, title)
    estimate: PayableTitle | None = values.pop("_estimate")
    previous_estimate = title.replaces_estimate_id
    for key, value in values.items():
        setattr(title, key, value)
    if previous_estimate and previous_estimate != title.replaces_estimate_id:
        old = session.get(PayableTitle, previous_estimate)
        if old is not None and old.status == "ESTIMATE_REPLACED":
            old.status = "ESTIMATE_OPEN"
            _event(
                session,
                old,
                user,
                "REOPENED",
                "ESTIMATE_REPLACED",
                f"CP-{title.number:06d} deixou de substituí-la",
            )
    if estimate is not None and estimate.status == "ESTIMATE_OPEN":
        estimate.status = "ESTIMATE_REPLACED"
        _event(
            session,
            estimate,
            user,
            "REPLACED",
            "ESTIMATE_OPEN",
            f"Substituída por CP-{title.number:06d}",
        )
    _event(session, title, user, "EDITED", title.status)
    _refresh_intake(session, user, title, "EDITED")
    session.commit()
    return get_title(session, user, title.id)


def _stored_name(
    session: Session, title: PayableTitle, role: str, filename: str
) -> str:
    unit = session.get(BusinessUnit, title.unit_id)
    assert unit is not None
    extension = ""
    match = re.search(r"\.[A-Za-z0-9]{1,5}$", filename)
    if match:
        extension = match.group(0).lower()
    unit_part = re.sub(r"[^A-Z0-9]+", "-", name_key(unit.name)).strip("-")
    doc = f"{_DOC_LABEL.get(title.document_type or '', 'DOC')}-{title.document_key or 'SN'}"
    doc = re.sub(r"[^A-Za-z0-9-]+", "-", doc).upper()
    return (
        f"{unit_part}_CP{title.number:06d}_{doc}_P{title.installment_number}-"
        f"{title.installment_count}_{_ROLE_FILE[role]}{extension}"
    )[:255]


def add_attachment(
    session: Session,
    user: User,
    title_id: UUID,
    role: str,
    filename: str,
    content_type: str,
    data: bytes,
) -> TitleDetail:
    title = _get_title(session, user, title_id)
    if title.status not in EDITABLE and not is_finance(user):
        raise _invalid("Este título já foi conferido; o anexo não muda mais.")
    if title.status in CLOSED:
        raise _invalid("Título encerrado.")
    if role not in _ROLE_FILE:
        raise _invalid("Tipo de anexo inválido.")
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise _invalid("Envie PDF, XML ou foto (JPG ou PNG).")
    if not data:
        raise _invalid("Arquivo vazio.")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise _invalid("Arquivo maior que 10 MB.")
    supplier = session.get(PayableSupplier, title.supplier_id)
    assert supplier is not None
    reading = read_attachment(
        data, content_type, filename, supplier.tax_id, AiDocumentReader()
    )
    attachment = PayableAttachment(
        title_id=title.id,
        role=role,
        original_name=filename[:255],
        stored_name=_stored_name(session, title, role, filename),
        content_type=(content_type or "application/octet-stream")[:120],
        size_bytes=len(data),
        data=data,
        read_kind=reading.kind,
        read_amount=reading.amount,
        read_tax_id=reading.tax_id,
        read_document_number=reading.document_number,
        read_due_date=reading.due_date,
        read_source=reading.source if reading.is_read else None,
        created_by=user.id,
    )
    session.add(attachment)
    session.flush()
    _event(session, title, user, "ATTACHED", title.status, attachment.stored_name)
    _refresh_intake(session, user, title, "ATTACHED")
    session.commit()
    return get_title(session, user, title.id)


def remove_attachment(
    session: Session, user: User, title_id: UUID, attachment_id: UUID
) -> TitleDetail:
    title = _get_title(session, user, title_id)
    if title.status not in EDITABLE:
        raise _invalid("Este título já foi conferido; o anexo não muda mais.")
    attachment = session.get(PayableAttachment, attachment_id)
    if attachment is None or attachment.title_id != title.id:
        raise _not_found("Anexo não encontrado.")
    name = attachment.stored_name
    session.delete(attachment)
    session.flush()
    _event(session, title, user, "DETACHED", title.status, name)
    _refresh_intake(session, user, title, "DETACHED")
    session.commit()
    return get_title(session, user, title.id)


def get_attachment(
    session: Session, user: User, title_id: UUID, attachment_id: UUID
) -> PayableAttachment:
    title = _get_title(session, user, title_id)
    attachment = session.get(PayableAttachment, attachment_id)
    if attachment is None or attachment.title_id != title.id:
        raise _not_found("Anexo não encontrado.")
    return attachment


def act(
    session: Session, user: User, title_id: UUID, request: TitleActionRequest
) -> TitleDetail:
    title = _get_title(session, user, title_id)
    action = request.action
    reason = (request.reason or "").strip() or None
    if action == "RESUBMIT":
        if title.status != "RETURNED":
            raise _invalid("Só um título devolvido é reenviado.")
        before = title.status
        title.status = _intake_status(session, title)
        _event(session, title, user, "RESUBMITTED", before, reason)
        session.commit()
        return get_title(session, user, title.id)
    unit_cancel = (
        action == "CANCEL" and not is_finance(user) and title.status in EDITABLE
    )
    if not unit_cancel:
        _require_finance(user)
    if title.status not in _FINANCE_ACTIONS[action]:
        raise _invalid("Esta etapa não vale para o título na situação atual.")
    if action in ("RETURN", "CANCEL", "UNDO_RELEASE") and not reason:
        raise _invalid("Diga o motivo.")
    if action == "RELEASE":
        blocking = [
            check
            for check in _checks(session, [title])[title.id]
            if check.blocks_release
        ]
        if blocking:
            raise _invalid(
                "Resolva antes de liberar: "
                + "; ".join(check.title for check in blocking)
                + "."
            )
    if action == "BOOK":
        title.ng_reference = (request.ng_reference or "").strip() or None
    before = title.status
    title.status = _ACTION_TARGET[action]
    if action == "CANCEL" and title.replaces_estimate_id:
        estimate = session.get(PayableTitle, title.replaces_estimate_id)
        if estimate is not None and estimate.status == "ESTIMATE_REPLACED":
            estimate.status = "ESTIMATE_OPEN"
            _event(
                session,
                estimate,
                user,
                "REOPENED",
                "ESTIMATE_REPLACED",
                f"CP-{title.number:06d} cancelado",
            )
    _event(session, title, user, action, before, reason or title.ng_reference)
    session.commit()
    return get_title(session, user, title.id)


def decide_check(
    session: Session, user: User, title_id: UUID, request: CheckDecisionRequest
) -> TitleDetail:
    _require_finance(user)
    title = _get_title(session, user, title_id)
    if request.check_code not in rules.DECIDABLE:
        raise _invalid("Esta conferência não se dispensa: corrija o título.")
    current = _checks(session, [title])[title.id]
    if not any(
        check.code == request.check_code and check.subject == request.subject
        for check in current
    ):
        raise _invalid("Esta conferência não está mais aberta.")
    session.add(
        PayableCheckDecision(
            title_id=title.id,
            check_code=request.check_code,
            subject=request.subject,
            reason=request.reason.strip(),
            decided_by=user.id,
        )
    )
    _event(session, title, user, "CHECK_DECIDED", title.status, request.reason.strip())
    session.commit()
    return get_title(session, user, title.id)


# ---------------------------------------------------------------- reading


def _checks(
    session: Session, titles: list[PayableTitle]
) -> dict[UUID, list[rules.CheckResult]]:
    today = _today()
    return {
        title_id: rules.evaluate(facts, today)
        for title_id, facts in _facts(session, titles).items()
    }


def _facts(
    session: Session, titles: list[PayableTitle]
) -> dict[UUID, rules.TitleFacts]:
    """What the checks read for each title, with a fixed number of queries."""
    if not titles:
        return {}
    ids = [title.id for title in titles]
    suppliers = {
        supplier.id: supplier
        for supplier in session.scalars(sa.select(PayableSupplier))
    }
    accounts = {
        account.id: account.code
        for account in session.scalars(
            sa.select(FinancialAccount).where(
                FinancialAccount.id.in_({title.account_id for title in titles})
            )
        )
    }
    units = {unit.id: unit.name for unit in session.scalars(sa.select(BusinessUnit))}
    attachments: dict[UUID, list[rules.AttachmentFacts]] = defaultdict(list)
    for row in session.execute(
        sa.select(
            PayableAttachment.id,
            PayableAttachment.title_id,
            PayableAttachment.role,
            PayableAttachment.original_name,
            PayableAttachment.read_kind,
            PayableAttachment.read_amount,
            PayableAttachment.read_tax_id,
            PayableAttachment.read_due_date,
            PayableAttachment.read_source,
        ).where(PayableAttachment.title_id.in_(ids))
    ):
        attachments[row.title_id].append(
            rules.AttachmentFacts(
                id=row.id,
                role=row.role,
                name=row.original_name,
                read_kind=row.read_kind,
                read_amount=row.read_amount,
                read_tax_id=row.read_tax_id,
                read_due_date=row.read_due_date,
                read_source=row.read_source,
            )
        )
    pairs = {
        (title.supplier_id, title.document_key)
        for title in titles
        if title.kind == "REAL" and title.document_key
    }
    same: dict[tuple[UUID, str], list[PayableTitle]] = defaultdict(list)
    if pairs:
        for other in session.scalars(
            sa.select(PayableTitle).where(
                PayableTitle.kind == "REAL",
                sa.tuple_(PayableTitle.supplier_id, PayableTitle.document_key).in_(
                    list(pairs)
                ),
            )
        ):
            assert other.document_key is not None
            same[(other.supplier_id, other.document_key)].append(other)
    decisions: dict[UUID, set[tuple[str, str]]] = defaultdict(set)
    for decision in session.scalars(
        sa.select(PayableCheckDecision).where(PayableCheckDecision.title_id.in_(ids))
    ):
        decisions[decision.title_id].add((decision.check_code, decision.subject))
    shared_cache: dict[UUID, tuple[str, ...]] = {}
    everyone = list(suppliers.values())
    result = {}
    for title in titles:
        supplier = suppliers[title.supplier_id]
        if supplier.id not in shared_cache:
            shared_cache[supplier.id] = tuple(
                _supplier_name(other) for other in _shared_account(supplier, everyone)
            )
        siblings = [
            rules.OtherTitle(
                id=other.id,
                number=other.number,
                unit_name=units.get(other.unit_id, ""),
                installment_number=other.installment_number,
                installment_count=other.installment_count,
                amount=other.amount,
                status=other.status,
            )
            for other in same.get((title.supplier_id, title.document_key or ""), [])
            if other.id != title.id
        ]
        result[title.id] = rules.TitleFacts(
            id=title.id,
            kind=title.kind,
            status=title.status,
            # The key drops words the unit typed ("NF 055514" reads "NF 55514").
            document_label=f"{_DOC_LABEL.get(title.document_type or '', 'Documento')} {title.document_key or ''}".strip(),
            account_code=accounts.get(title.account_id, ""),
            amount=title.amount,
            purchase_total=title.purchase_total,
            installment_number=title.installment_number,
            installment_count=title.installment_count,
            due_date=title.due_date,
            submitted_on=title.submitted_at.astimezone(
                datetime.timezone(datetime.timedelta(hours=-3))
            ).date(),
            estimate_until=title.estimate_until,
            supplier=rules.SupplierFacts(
                tax_id=supplier.tax_id,
                status=supplier.status,
                pix_key_type=supplier.pix_key_type,
                pix_key=supplier.pix_key,
                shared_with=shared_cache[supplier.id],
            ),
            attachments=tuple(attachments.get(title.id, [])),
            same_document=tuple(siblings),
            decisions=frozenset(decisions.get(title.id, set())),
        )
    return result


def _payment_method(supplier: PayableSupplier, has_boleto: bool) -> str:
    if has_boleto:
        return "Boleto"
    if supplier.pix_key:
        return f"PIX {supplier.pix_key_type or ''}".strip()
    return "Transferência" if supplier.bank_account else "—"


def _ng_history(
    title: PayableTitle, supplier: PayableSupplier, unit: BusinessUnit
) -> str:
    """A ready "Histórico" for the NG entry, in the order the team reads it."""
    parts = [_supplier_name(supplier).upper()]
    if title.document_number:
        doc = f"{_DOC_LABEL.get(title.document_type or '', 'DOC')} {title.document_number}"
        if title.installment_count > 1:
            doc += f" {title.installment_number}/{title.installment_count}"
        parts.append(doc)
    parts.append(title.description)
    if title.vehicle_plates:
        parts.append(" ".join(title.vehicle_plates))
    elif title.destination_note:
        parts.append(title.destination_note)
    parts.append(unit.name)
    return " · ".join(part for part in parts if part)[:500]


def _row_values(
    title: PayableTitle,
    units: dict[UUID, BusinessUnit],
    suppliers: dict[UUID, PayableSupplier],
    accounts: dict[UUID, FinancialAccount],
    attachment_count: int,
    checks: list[rules.CheckResult],
    has_boleto: bool,
) -> dict:
    supplier = suppliers[title.supplier_id]
    account = accounts[title.account_id]
    top = next(
        (
            check
            for check in checks
            if not check.decided and check.severity != rules.INFO
        ),
        None,
    )
    return {
        "payment_method": _payment_method(supplier, has_boleto),
        "top_issue": top.title if top else None,
        "top_issue_severity": top.severity if top else None,
        "id": title.id,
        "number": title.number,
        "kind": title.kind,
        "status": title.status,
        "unit_id": title.unit_id,
        "unit_name": units[title.unit_id].name,
        "supplier_id": supplier.id,
        "supplier_name": _supplier_name(supplier),
        "supplier_tax_id": format_tax_id(supplier.tax_id),
        "account_code": account.code,
        "account_label": account.label,
        "document_type": title.document_type,
        "document_number": title.document_number,
        "installment_number": title.installment_number,
        "installment_count": title.installment_count,
        "amount": title.amount,
        "competence": title.competence,
        "due_date": title.due_date,
        "description": title.description,
        "vehicle_plates": list(title.vehicle_plates or []),
        "attachment_count": attachment_count,
        "blocking": sum(1 for check in checks if check.blocks_release),
        "attention": sum(
            1
            for check in checks
            if check.severity == rules.ATTENTION and not check.decided
        ),
        "submitted_at": title.submitted_at,
    }


def list_titles(
    session: Session,
    user: User,
    unit_id: UUID | None,
    statuses: list[str] | None,
    search: str | None,
    due_from: datetime.date | None,
    due_to: datetime.date | None,
    limit: int,
) -> list[TitleRow]:
    visible = _visible_unit_ids(session, user)
    query = sa.select(PayableTitle)
    if not is_finance(user):
        query = query.where(PayableTitle.unit_id.in_(visible))
    if unit_id:
        query = query.where(PayableTitle.unit_id == unit_id)
    if statuses:
        query = query.where(PayableTitle.status.in_(statuses))
    if due_from:
        query = query.where(PayableTitle.due_date >= due_from)
    if due_to:
        query = query.where(PayableTitle.due_date <= due_to)
    if search and search.strip():
        term = f"%{search.strip()}%"
        number = digits(search)
        conditions = [
            PayableTitle.description.ilike(term),
            PayableTitle.document_number.ilike(term),
            PayableTitle.supplier_id.in_(
                sa.select(PayableSupplier.id).where(
                    sa.or_(
                        PayableSupplier.legal_name.ilike(term),
                        PayableSupplier.trade_name.ilike(term),
                        PayableSupplier.tax_id.like(f"%{number}%")
                        if number
                        else sa.false(),
                    )
                )
            ),
            sa.cast(PayableTitle.vehicle_plates, sa.String).ilike(
                f"%{re.sub(r'[^A-Za-z0-9]', '', search).upper()}%"
            ),
        ]
        if number:
            conditions.append(
                sa.cast(PayableTitle.number, sa.String) == number.lstrip("0")
            )
        query = query.where(sa.or_(*conditions))
    titles = list(
        session.scalars(
            query.order_by(PayableTitle.due_date, PayableTitle.number).limit(limit)
        )
    )
    if not titles:
        return []
    units = {unit.id: unit for unit in session.scalars(sa.select(BusinessUnit))}
    suppliers = {
        supplier.id: supplier
        for supplier in session.scalars(
            sa.select(PayableSupplier).where(
                PayableSupplier.id.in_({title.supplier_id for title in titles})
            )
        )
    }
    accounts = {
        account.id: account
        for account in session.scalars(
            sa.select(FinancialAccount).where(
                FinancialAccount.id.in_({title.account_id for title in titles})
            )
        )
    }
    counts: dict[UUID, int] = {
        title_id: count
        for title_id, count in session.execute(
            sa.select(PayableAttachment.title_id, sa.func.count())
            .where(PayableAttachment.title_id.in_([title.id for title in titles]))
            .group_by(PayableAttachment.title_id)
        ).tuples()
    }
    with_boleto = set(
        session.scalars(
            sa.select(PayableAttachment.title_id).where(
                PayableAttachment.title_id.in_([title.id for title in titles]),
                PayableAttachment.role == "BOLETO",
            )
        )
    )
    all_checks = _checks(session, titles)
    return [
        TitleRow(
            **_row_values(
                title,
                units,
                suppliers,
                accounts,
                counts.get(title.id, 0),
                all_checks[title.id],
                title.id in with_boleto,
            )
        )
        for title in titles
    ]


def _actions_for(user: User, title: PayableTitle) -> list[TitleAction]:
    actions: list[TitleAction] = ["RESUBMIT"] if title.status == "RETURNED" else []
    if not is_finance(user):
        return [*actions, "CANCEL"] if title.status in EDITABLE else actions
    for action, allowed in _FINANCE_ACTIONS.items():
        if title.status in allowed:
            actions.append(action)  # type: ignore[arg-type]
    return actions


def get_title(session: Session, user: User, title_id: UUID) -> TitleDetail:
    title = _get_title(session, user, title_id)
    units = {unit.id: unit for unit in session.scalars(sa.select(BusinessUnit))}
    supplier = session.get(PayableSupplier, title.supplier_id)
    account = session.get(FinancialAccount, title.account_id)
    assert supplier is not None and account is not None
    attachments = list(
        session.scalars(
            sa.select(PayableAttachment)
            .where(PayableAttachment.title_id == title.id)
            .order_by(PayableAttachment.created_at)
        )
    )
    facts = _facts(session, [title])[title.id]
    checks = rules.evaluate(facts, _today())
    decisions = {
        (decision.check_code, decision.subject): decision.reason
        for decision in session.scalars(
            sa.select(PayableCheckDecision).where(
                PayableCheckDecision.title_id == title.id
            )
        )
    }
    people = {
        person.id: person.personal_name or person.email
        for person in session.scalars(
            sa.select(User).where(
                User.id.in_(
                    sa.select(PayableEvent.actor_id).where(
                        PayableEvent.title_id == title.id
                    )
                )
                | (User.id == title.created_by)
            )
        ).unique()
    }
    events = list(
        session.scalars(
            sa.select(PayableEvent)
            .where(PayableEvent.title_id == title.id)
            .order_by(PayableEvent.created_at.desc())
        )
    )
    same = (
        list(
            session.scalars(
                sa.select(PayableTitle)
                .where(
                    PayableTitle.supplier_id == title.supplier_id,
                    PayableTitle.document_key == title.document_key,
                    PayableTitle.kind == "REAL",
                    PayableTitle.id != title.id,
                )
                .order_by(PayableTitle.installment_number)
            )
        )
        if title.document_key
        else []
    )
    replaced_by = session.scalar(
        sa.select(PayableTitle.id).where(
            PayableTitle.replaces_estimate_id == title.id,
            PayableTitle.status != "CANCELLED",
        )
    )
    row = _row_values(
        title,
        units,
        {supplier.id: supplier},
        {account.id: account},
        len(attachments),
        checks,
        any(attachment.role == "BOLETO" for attachment in attachments),
    )
    return TitleDetail(
        **row,
        account_id=account.id,
        issue_date=title.issue_date,
        purchase_total=title.purchase_total,
        destination_kind=title.destination_kind,  # type: ignore[arg-type]
        destination_note=title.destination_note,
        zeev_request=title.zeev_request,
        estimate_until=title.estimate_until,
        replaces_estimate_id=title.replaces_estimate_id,
        replaced_by_id=replaced_by,
        ng_reference=title.ng_reference,
        created_by=people.get(title.created_by) if title.created_by else None,
        supplier=_supplier_view(session, supplier),
        attachments=[
            AttachmentView(
                id=attachment.id,
                role=attachment.role,  # type: ignore[arg-type]
                original_name=attachment.original_name,
                stored_name=attachment.stored_name,
                content_type=attachment.content_type,
                size_bytes=attachment.size_bytes,
                read_kind=attachment.read_kind,
                read_amount=attachment.read_amount,
                read_tax_id=attachment.read_tax_id,
                read_document_number=attachment.read_document_number,
                read_due_date=attachment.read_due_date,
                read_source=attachment.read_source,
                created_at=attachment.created_at,
            )
            for attachment in attachments
        ],
        checks=[
            CheckView(
                code=check.code,
                severity=check.severity,  # type: ignore[arg-type]
                title=check.title,
                detail=check.detail,
                subject=check.subject,
                decided=check.decided,
                decidable=check.code in rules.DECIDABLE,
                decision_reason=decisions.get((check.code, check.subject)),
            )
            for check in checks
        ],
        events=[
            EventView(
                id=event.id,
                action=event.action,
                from_status=event.from_status,
                to_status=event.to_status,
                reason=event.reason,
                actor=people.get(event.actor_id) if event.actor_id else None,
                created_at=event.created_at,
            )
            for event in events
        ],
        same_document=[
            RelatedTitle(
                id=other.id,
                number=other.number,
                unit_name=units[other.unit_id].name,
                installment_number=other.installment_number,
                installment_count=other.installment_count,
                amount=other.amount,
                due_date=other.due_date,
                status=other.status,
            )
            for other in same
        ],
        can_edit=title.status in EDITABLE,
        actions=_actions_for(user, title),
        confirmations=[
            ConfirmationView(label=item.label, value=item.value, state=item.state)  # type: ignore[arg-type]
            for item in rules.confirmations(facts)
        ],
        ng_history=_ng_history(title, supplier, units[title.unit_id]),
    )


# ---------------------------------------------------------------- documents


def read_document(
    session: Session, user: User, filename: str, content_type: str, data: bytes
) -> DocumentReadView:
    """Read a file before the title exists, so the form fills itself."""
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise _invalid("Envie PDF, XML ou foto (JPG ou PNG).")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise _invalid("Arquivo maior que 10 MB.")
    reading = read_attachment(data, content_type, filename, None, AiDocumentReader())
    supplier = (
        session.scalar(
            sa.select(PayableSupplier).where(PayableSupplier.tax_id == reading.tax_id)
        )
        if reading.tax_id
        else None
    )
    visible = (
        supplier is not None
        and supplier.status != "REJECTED"
        and (
            is_finance(user)
            or supplier.status == "ACTIVE"
            or supplier.created_by == user.id
        )
    )
    return DocumentReadView(
        kind=reading.kind,
        source=reading.source if reading.is_read else None,
        amount=reading.amount,
        tax_id=reading.tax_id,
        tax_id_display=format_tax_id(reading.tax_id) if reading.tax_id else None,
        document_type=reading.document_type,
        document_number=reading.document_number,
        issue_date=reading.issue_date,
        due_date=reading.due_date,
        issuer_name=reading.issuer_name,
        installments=[
            InstallmentView(
                number=item.number, due_date=item.due_date, amount=item.amount
            )
            for item in reading.installments
        ],
        supplier=_ref(supplier) if supplier is not None and visible else None,
        supplier_status=supplier.status if supplier is not None and visible else None,
    )


# ---------------------------------------------------------------- batches


def batch_act(
    session: Session, user: User, request: BatchActionRequest
) -> BatchActionResult:
    """Run one step on many titles; each title succeeds or fails on its own."""
    _require_finance(user)
    done: list[UUID] = []
    failed: list[BatchFailure] = []
    for title_id in dict.fromkeys(request.ids):
        title = session.get(PayableTitle, title_id)
        if title is None:
            continue
        number = title.number
        try:
            act(session, user, title_id, TitleActionRequest(action=request.action))
            done.append(title_id)
        except OnyxError as error:
            session.rollback()
            failed.append(
                BatchFailure(id=title_id, number=number, message=error.detail)
            )
    return BatchActionResult(done=done, failed=failed)


def _batch_titles(session: Session, user: User, ids: list[UUID]) -> list[PayableTitle]:
    titles = [_get_title(session, user, title_id) for title_id in dict.fromkeys(ids)]
    return sorted(titles, key=lambda title: (title.due_date, title.number))


def payment_batch_xlsx(session: Session, user: User, ids: list[UUID]) -> bytes:
    """The sheet whoever pays works from: one row per title, payee data included."""
    _require_finance(user)
    titles = _batch_titles(session, user, ids)
    units = {unit.id: unit for unit in session.scalars(sa.select(BusinessUnit))}
    suppliers = {
        supplier.id: supplier
        for supplier in session.scalars(sa.select(PayableSupplier))
    }
    accounts = {
        account.id: account for account in session.scalars(sa.select(FinancialAccount))
    }
    boletos = {
        attachment.title_id: attachment
        for attachment in session.scalars(
            sa.select(PayableAttachment).where(
                PayableAttachment.title_id.in_([title.id for title in titles]),
                PayableAttachment.role == "BOLETO",
            )
        )
    }
    rows = []
    for title in titles:
        supplier = suppliers[title.supplier_id]
        boleto = boletos.get(title.id)
        rows.append(
            payment_batch.BatchRow(
                due_date=title.due_date,
                number=f"CP-{title.number:06d}",
                unit=units[title.unit_id].name,
                payee=supplier.legal_name,
                tax_id=format_tax_id(supplier.tax_id),
                method=_payment_method(supplier, boleto is not None),
                pix_key=supplier.pix_key or "",
                bank=" · ".join(
                    value
                    for value in (
                        supplier.bank_code,
                        supplier.bank_agency,
                        supplier.bank_account,
                    )
                    if value
                ),
                document=f"{_DOC_LABEL.get(title.document_type or '', '')} {title.document_number or ''}".strip(),
                installment=f"{title.installment_number}/{title.installment_count}",
                nature=f"{accounts[title.account_id].code} {accounts[title.account_id].label}",
                amount=title.amount,
                ng_history=_ng_history(title, supplier, units[title.unit_id]),
                boleto_file=boleto.stored_name if boleto else "",
            )
        )
    return payment_batch.build_xlsx(rows)


def attachments_zip(session: Session, user: User, ids: list[UUID]) -> bytes:
    """Every attachment of the chosen titles, under their standard names."""
    titles = _batch_titles(session, user, ids)
    attachments = list(
        session.scalars(
            sa.select(PayableAttachment)
            .where(PayableAttachment.title_id.in_([title.id for title in titles]))
            .order_by(PayableAttachment.stored_name)
        )
    )
    if not attachments:
        raise _invalid("Os títulos escolhidos não têm anexos.")
    buffer = io.BytesIO()
    used: set[str] = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for attachment in attachments:
            name = attachment.stored_name
            stem, dot, extension = name.rpartition(".")
            counter = 2
            while name in used:
                name = f"{stem}_{counter}.{extension}" if dot else f"{stem}_{counter}"
                counter += 1
            used.add(name)
            archive.writestr(name, attachment.data)
    return buffer.getvalue()
