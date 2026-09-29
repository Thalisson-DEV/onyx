from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import import_profiles as profile_repository
from onyx.db.ton import sources as repository
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import get_default_file_store
from onyx.ton.ng_financial.models import (
    ImportProfileExecutionView,
    ImportProfileView,
    ParsedSourceRecordView,
)
from onyx.ton.ng_financial.service import execute_ng_profile
from onyx.ton.sources.models import (
    ImportRunView,
    SnapshotView,
    SourceCreate,
    SourceUpdate,
    SourceView,
)
from onyx.ton.sources.service import cleanup_failed_import, import_file

router = APIRouter(prefix="/ton/sources", tags=["TON Sources"])


@router.get("")
def list_sources(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[SourceView]:
    return [
        SourceView.model_validate(source)
        for source in repository.list_sources(session, user, limit, offset)
    ]


@router.post("")
def create_source(
    request: SourceCreate,
    user: User = Depends(require_permission(Permission.MANAGE_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> SourceView:
    try:
        source = repository.create_source(session, user, request)
        result = SourceView.model_validate(source)
        session.commit()
        return result
    except IntegrityError:
        session.rollback()
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "Source key already exists or groups changed"
        ) from None


@router.get("/{source_id}")
def get_source(
    source_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> SourceView:
    return SourceView.model_validate(repository.get_source(session, user, source_id))


@router.put("/{source_id}")
def update_source(
    source_id: UUID,
    request: SourceUpdate,
    user: User = Depends(require_permission(Permission.MANAGE_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> SourceView:
    source = repository.update_source(session, user, source_id, request)
    result = SourceView.model_validate(source)
    session.commit()
    return result


@router.get("/{source_id}/runs")
def list_runs(
    source_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[ImportRunView]:
    return [
        ImportRunView.model_validate(run)
        for run in repository.list_runs(session, user, source_id, limit, offset)
    ]


@router.get("/{source_id}/runs/{run_id}")
def get_run(
    source_id: UUID,
    run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ImportRunView:
    return ImportRunView.model_validate(
        repository.get_run(session, user, source_id, run_id)
    )


@router.get("/{source_id}/snapshots")
def list_snapshots(
    source_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[SnapshotView]:
    return [
        SnapshotView.model_validate(snapshot)
        for snapshot in repository.list_snapshots(
            session, user, source_id, limit, offset
        )
    ]


@router.post("/{source_id}/imports")
def upload_source(
    source_id: UUID,
    file: UploadFile,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> SnapshotView:
    return import_file(
        session,
        user,
        source_id,
        file.file,
        file.filename or "",
        file.content_type or "",
        get_default_file_store(),
    )


@router.post("/{source_id}/runs/{run_id}/cleanup")
def cleanup_import(
    source_id: UUID,
    run_id: UUID,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ImportRunView:
    return cleanup_failed_import(
        session, user, source_id, run_id, get_default_file_store()
    )


@router.post("/{source_id}/profiles/ng-financial/v1")
def create_ng_financial_profile(
    source_id: UUID,
    user: User = Depends(require_permission(Permission.MANAGE_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ImportProfileView:
    profile = profile_repository.create_ng_profile_v1(session, user, source_id)
    result = ImportProfileView.model_validate(profile)
    session.commit()
    return result


@router.get("/{source_id}/profiles")
def list_import_profiles(
    source_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[ImportProfileView]:
    return [
        ImportProfileView.model_validate(profile)
        for profile in profile_repository.list_profiles(session, user, source_id)
    ]


@router.post("/{source_id}/snapshots/{snapshot_id}/profiles/{profile_id}/executions")
def run_import_profile(
    source_id: UUID,
    snapshot_id: UUID,
    profile_id: UUID,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ImportProfileExecutionView:
    return execute_ng_profile(
        session, user, source_id, snapshot_id, profile_id, get_default_file_store()
    )


@router.get("/{source_id}/profile-executions/{execution_id}")
def get_profile_execution(
    source_id: UUID,
    execution_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ImportProfileExecutionView:
    return ImportProfileExecutionView.model_validate(
        profile_repository.get_execution(session, user, source_id, execution_id)
    )


@router.get("/{source_id}/profile-executions/{execution_id}/records")
def list_profile_records(
    source_id: UUID,
    execution_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[ParsedSourceRecordView]:
    return [
        ParsedSourceRecordView.model_validate(record)
        for record in profile_repository.list_records(
            session, user, source_id, execution_id, limit, offset
        )
    ]
