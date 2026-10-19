"""Client-facing financial source catalog and import entry point."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.file_store.file_store import get_default_file_store
from onyx.ton.client_import.models import (
    ClientImportView,
    ClientSourceView,
    PastedTable,
    PastedValidation,
    ProblemRowsView,
    ReimportPreviewView,
)
from onyx.ton.client_import.service import (
    get_client_import,
    get_problem_rows as problem_rows,
    list_client_sources,
    paste_client_table,
    preview_client_import,
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


@router.post("/{key}/paste")
def paste_financial_table(
    key: str,
    table: PastedTable,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> PastedValidation:
    """Rows pasted into the TON grid: checked, or imported like a file."""
    return paste_client_table(session, user, key, table, get_default_file_store())


@router.post("/{key}/imports/preview")
def preview_financial_source(
    key: str,
    file: UploadFile,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ReimportPreviewView:
    return preview_client_import(
        session,
        user,
        key,
        file.file,
        file.filename or "",
        file.content_type or "",
    )


@router.get("/{key}/imports/{execution_id}")
def get_financial_import(
    key: str,
    execution_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ClientImportView:
    return get_client_import(session, user, key, execution_id)


@router.get("/{key}/imports/{execution_id}/problems")
def get_problem_rows(
    key: str,
    execution_id: UUID,
    code: str = Query(min_length=1, max_length=100),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ProblemRowsView:
    return problem_rows(
        session, user, key, execution_id, code, get_default_file_store()
    )
