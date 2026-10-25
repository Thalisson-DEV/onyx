"""Unit payables: titles sent by the units, conferred and released by finance."""

import datetime
from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import payables as service
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.payables.models import (
    BatchActionRequest,
    BatchActionResult,
    BatchRequest,
    CheckDecisionRequest,
    DocumentReadView,
    PayablesContext,
    SupplierInput,
    SupplierReview,
    SupplierView,
    TitleActionRequest,
    TitleDetail,
    TitleInput,
    TitleRow,
)

router = APIRouter(prefix="/ton/payables", tags=["TON payables"])
# Unit managers and finance both hold the TON source read token; what each one
# may do is decided per unit and per step in the service.
_member = require_permission(Permission.READ_TON_SOURCES)


@router.get("/context")
def get_context(
    user: User = Depends(_member), session: Session = Depends(get_session)
) -> PayablesContext:
    return service.context(session, user)


@router.get("/titles")
def list_titles(
    unit_id: UUID | None = None,
    status: list[str] | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    due_from: datetime.date | None = None,
    due_to: datetime.date | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> list[TitleRow]:
    return service.list_titles(
        session, user, unit_id, status, q, due_from, due_to, limit
    )


@router.post("/titles")
def create_title(
    request: TitleInput,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> TitleDetail:
    return service.create_title(session, user, request)


@router.get("/titles/{title_id}")
def get_title(
    title_id: UUID,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> TitleDetail:
    return service.get_title(session, user, title_id)


@router.put("/titles/{title_id}")
def update_title(
    title_id: UUID,
    request: TitleInput,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> TitleDetail:
    return service.update_title(session, user, title_id, request)


@router.post("/titles/{title_id}/actions")
def act(
    title_id: UUID,
    request: TitleActionRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> TitleDetail:
    return service.act(session, user, title_id, request)


@router.post("/titles/{title_id}/decisions")
def decide_check(
    title_id: UUID,
    request: CheckDecisionRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> TitleDetail:
    return service.decide_check(session, user, title_id, request)


@router.post("/titles/{title_id}/attachments")
async def add_attachment(
    title_id: UUID,
    role: Literal["INVOICE", "BOLETO", "RECEIPT", "OTHER"] = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> TitleDetail:
    data = await file.read(service.MAX_ATTACHMENT_BYTES + 1)
    if len(data) > service.MAX_ATTACHMENT_BYTES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Arquivo maior que 10 MB.")
    return service.add_attachment(
        session,
        user,
        title_id,
        role,
        file.filename or "anexo",
        file.content_type or "",
        data,
    )


@router.delete("/titles/{title_id}/attachments/{attachment_id}")
def remove_attachment(
    title_id: UUID,
    attachment_id: UUID,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> TitleDetail:
    return service.remove_attachment(session, user, title_id, attachment_id)


@router.get("/titles/{title_id}/attachments/{attachment_id}")
def download_attachment(
    title_id: UUID,
    attachment_id: UUID,
    inline: bool = False,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> Response:
    attachment = service.get_attachment(session, user, title_id, attachment_id)
    disposition = "inline" if inline else "attachment"
    return Response(
        content=attachment.data,
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": (
                f"{disposition}; filename*=UTF-8''{quote(attachment.stored_name)}"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/read-document")
async def read_document(
    file: UploadFile = File(...),
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> DocumentReadView:
    data = await file.read(service.MAX_ATTACHMENT_BYTES + 1)
    return service.read_document(
        session, user, file.filename or "anexo", file.content_type or "", data
    )


@router.post("/titles/batch-actions")
def batch_act(
    request: BatchActionRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> BatchActionResult:
    return service.batch_act(session, user, request)


def _download(content: bytes, media_type: str, name: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


@router.post("/titles/payment-batch")
def payment_batch(
    request: BatchRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> Response:
    content = service.payment_batch_xlsx(session, user, request.ids)
    return _download(
        content,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"lote-de-pagamento-{datetime.date.today():%Y-%m-%d}.xlsx",
    )


@router.post("/titles/attachments-zip")
def attachments_zip(
    request: BatchRequest,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> Response:
    content = service.attachments_zip(session, user, request.ids)
    return _download(
        content,
        "application/zip",
        f"notas-e-boletos-{datetime.date.today():%Y-%m-%d}.zip",
    )


@router.get("/suppliers")
def list_suppliers(
    q: str | None = Query(default=None, max_length=100),
    status: str | None = None,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> list[SupplierView]:
    return service.list_suppliers(session, user, q, status)


@router.post("/suppliers")
def create_supplier(
    request: SupplierInput,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> SupplierView:
    return service.create_supplier(session, user, request)


@router.put("/suppliers/{supplier_id}")
def update_supplier(
    supplier_id: UUID,
    request: SupplierInput,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> SupplierView:
    return service.update_supplier(session, user, supplier_id, request)


@router.post("/suppliers/{supplier_id}/review")
def review_supplier(
    supplier_id: UUID,
    request: SupplierReview,
    user: User = Depends(_member),
    session: Session = Depends(get_session),
) -> SupplierView:
    return service.review_supplier(session, user, supplier_id, request)
