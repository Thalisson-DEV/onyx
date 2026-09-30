"""Client-facing financial source catalog and import entry point."""

from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.file_store.file_store import get_default_file_store
from onyx.ton.client_import.models import ClientImportView, ClientSourceView
from onyx.ton.client_import.service import (
    get_client_import,
    list_client_sources,
    upload_client_source,
)

router = APIRouter(prefix="/ton/data-sources", tags=["TON Data Sources"])


@router.get("")
def list_data_sources(
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[ClientSourceView]:
    return list_client_sources(session, user)


@router.post("/{key}/imports")
def upload_financial_source(
    key: str,
    file: UploadFile,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ClientImportView:
    return upload_client_source(
        session,
        user,
        key,
        file.file,
        file.filename or "",
        file.content_type or "",
        get_default_file_store(),
    )


@router.get("/{key}/imports/{execution_id}")
def get_financial_import(
    key: str,
    execution_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ClientImportView:
    return get_client_import(session, user, key, execution_id)
