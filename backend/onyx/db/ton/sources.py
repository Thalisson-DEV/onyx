"""Tenant-session repository and source ACL. All writes have explicit commit ownership."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.auth.permissions import has_global_permission
from onyx.db.enums import Permission
from onyx.db.models import User, UserGroup
from onyx.db.ton.acl import (
    fetch_user_group_ids,
    is_ton_administrator,
    user_group_ids_subquery,
)
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import SourceType, TonAuditResourceKind
from onyx.db.ton.models import ImportRun, Source, Source__UserGroup, SourceSnapshot
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.sources.models import (
    AcquisitionType,
    ImportStatus,
    ImportTrigger,
    SourceCreate,
    SourceStatus,
    SourceUpdate,
)
from onyx.ton.sources.validation import ValidatedUpload
from onyx.utils.audit import AuditAction, AuditOutcome


def source_access_clause(user: User, permission: Permission) -> sa.ColumnElement[bool]:
    if is_ton_administrator(user):
        return sa.true()
    if not has_global_permission(user, permission):
        return sa.false()
    shared = sa.exists(
        sa.select(Source__UserGroup.source_id).where(
            Source__UserGroup.source_id == Source.id,
            Source__UserGroup.user_group_id.in_(user_group_ids_subquery(user)),
        )
    )
    if permission == Permission.READ_TON_SOURCES:
        return shared
    # Writers must belong to every group sharing the source, as with TON reports.
    outside = sa.exists(
        sa.select(Source__UserGroup.source_id).where(
            Source__UserGroup.source_id == Source.id,
            Source__UserGroup.user_group_id.not_in(user_group_ids_subquery(user)),
        )
    )
    return sa.and_(shared, ~outside)


def get_source(
    session: Session,
    user: User,
    source_id: UUID,
    permission: Permission = Permission.READ_TON_SOURCES,
    *,
    lock: bool = False,
) -> Source:
    query = (
        sa.select(Source)
        .where(Source.id == source_id, source_access_clause(user, permission))
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    source = session.scalar(query)
    if source is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Source not found or inaccessible")
    return source


def list_sources(session: Session, user: User, limit: int, offset: int) -> list[Source]:
    check_page(limit, offset)
    return list(
        session.scalars(
            sa.select(Source)
            .where(source_access_clause(user, Permission.READ_TON_SOURCES))
            .order_by(Source.created_at.desc(), Source.id)
            .limit(limit)
            .offset(offset)
        )
    )


def check_page(limit: int, offset: int) -> None:
    if not 1 <= limit <= 100 or offset < 0:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid pagination")


def audit(
    session: Session,
    user: User,
    action: AuditAction,
    resource_id: UUID,
    kind: TonAuditResourceKind,
) -> None:
    emit_ton_audit_event(
        session,
        action=action,
        outcome=AuditOutcome.FAILURE
        if action == AuditAction.TON_IMPORT_FAIL
        else AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=kind,
        resource_id=resource_id,
    )


def create_source(session: Session, user: User, request: SourceCreate) -> Source:
    if not is_ton_administrator(user):
        if (
            not has_global_permission(user, Permission.MANAGE_TON_SOURCES)
            or not request.group_ids
            or not set(request.group_ids) <= fetch_user_group_ids(session, user)
        ):
            raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS)
    groups = set(
        session.scalars(
            sa.select(UserGroup.id).where(UserGroup.id.in_(request.group_ids))
        )
    )
    if groups != set(request.group_ids):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid source groups")
    source = Source(**request.model_dump(exclude={"group_ids"}))
    session.add(source)
    session.flush()
    session.add_all(
        Source__UserGroup(source_id=source.id, user_group_id=group) for group in groups
    )
    audit(
        session,
        user,
        AuditAction.TON_SOURCE_CREATE,
        source.id,
        TonAuditResourceKind.SOURCE,
    )
    return source


def update_source(
    session: Session, user: User, source_id: UUID, request: SourceUpdate
) -> Source:
    source = get_source(
        session, user, source_id, Permission.MANAGE_TON_SOURCES, lock=True
    )
    source.display_name = request.display_name
    source.description = request.description
    source.acquisition_type = request.acquisition_type
    source.status = request.status
    source.sensitivity = request.sensitivity
    session.flush()
    audit(
        session,
        user,
        AuditAction.TON_SOURCE_UPDATE,
        source.id,
        TonAuditResourceKind.SOURCE,
    )
    return source


def create_run(session: Session, user: User, source_id: UUID) -> ImportRun:
    return start_import_run(session, user, source_id, ImportTrigger.MANUAL_UPLOAD)


def start_import_run(
    session: Session, user: User, source_id: UUID, trigger: ImportTrigger
) -> ImportRun:
    source = get_source(
        session, user, source_id, Permission.IMPORT_TON_SOURCES, lock=True
    )
    if source.status != SourceStatus.ACTIVE:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Source is not active")
    is_assisted = source.acquisition_type == AcquisitionType.FILE_UPLOAD
    if (trigger == ImportTrigger.MANUAL_UPLOAD) != is_assisted:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Import trigger and acquisition differ")
    run = ImportRun(
        source_id=source.id,
        status=ImportStatus.PENDING,
        trigger=trigger,
        acquisition_type=source.acquisition_type,
        initiated_by=user.id,
        storage_file_id=f"ton-source/{uuid4()}",
        snapshot_count=0,
        cleanup_required=False,
    )
    session.add(run)
    session.flush()
    return run


def get_run(
    session: Session, user: User, source_id: UUID, run_id: UUID, *, lock: bool = False
) -> ImportRun:
    get_source(session, user, source_id)
    query = (
        sa.select(ImportRun)
        .where(ImportRun.source_id == source_id, ImportRun.id == run_id)
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    run = session.scalar(query)
    if run is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Import run not found")
    return run


def transition_run(
    run: ImportRun, status: ImportStatus, error_code: str | None = None
) -> None:
    allowed = {
        ImportStatus.PENDING: {ImportStatus.RUNNING, ImportStatus.FAILED},
        ImportStatus.RUNNING: {ImportStatus.SUCCEEDED, ImportStatus.FAILED},
    }
    if status not in allowed.get(run.status, set()):
        raise OnyxError(OnyxErrorCode.CONFLICT, "Invalid import transition")
    if status == ImportStatus.SUCCEEDED and run.snapshot_count != 1:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Import requires a captured snapshot")
    if status == ImportStatus.FAILED and error_code is None:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Failed import requires an error code"
        )
    run.status = status
    run.error_code = error_code
    if status in (ImportStatus.SUCCEEDED, ImportStatus.FAILED):
        run.finished_at = datetime.now(UTC)


def capture_snapshot(
    session: Session, user: User, source_id: UUID, run_id: UUID, upload: ValidatedUpload
) -> SourceSnapshot:
    # Only finalization is serialized. Independent storage transfers may overlap.
    get_source(session, user, source_id, Permission.IMPORT_TON_SOURCES, lock=True)
    run = get_run(session, user, source_id, run_id, lock=True)
    if run.status != ImportStatus.RUNNING:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Import is not running")
    if (run.acquisition_type == AcquisitionType.FILE_UPLOAD) == (
        upload.format.value == "JSON"
    ):
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "Snapshot format and acquisition differ"
        )
    previous = session.scalar(
        sa.select(SourceSnapshot)
        .where(
            SourceSnapshot.source_id == source_id,
            SourceSnapshot.checksum == upload.checksum,
        )
        .order_by(SourceSnapshot.created_at, SourceSnapshot.id)
        .limit(1)
    )
    snapshot = SourceSnapshot(
        source_id=source_id,
        import_run_id=run.id,
        storage_file_id=run.storage_file_id,
        original_filename=upload.filename,
        media_type=upload.media_type,
        format=upload.format,
        size_bytes=len(upload.content),
        checksum=upload.checksum,
        duplicate_of_id=previous.id if previous else None,
        extracted_at=datetime.now(UTC),
        source_type=(
            SourceType.API_PAYLOAD
            if upload.format.value == "JSON"
            else SourceType.UPLOADED_DOCUMENT
            if upload.format.value == "PDF"
            else SourceType.UPLOADED_SPREADSHEET
        ),
        is_complete=False,
        is_schema_conformant=False,
    )
    session.add(snapshot)
    session.flush()
    run.snapshot_count = 1
    transition_run(run, ImportStatus.SUCCEEDED)
    audit(
        session,
        user,
        AuditAction.TON_SNAPSHOT_CAPTURE,
        snapshot.id,
        TonAuditResourceKind.SOURCE_SNAPSHOT,
    )
    if previous:
        audit(
            session,
            user,
            AuditAction.TON_DUPLICATE_DETECT,
            snapshot.id,
            TonAuditResourceKind.SOURCE_SNAPSHOT,
        )
    audit(
        session,
        user,
        AuditAction.TON_IMPORT_SUCCEED,
        run.id,
        TonAuditResourceKind.IMPORT_RUN,
    )
    return snapshot


def list_runs(
    session: Session, user: User, source_id: UUID, limit: int, offset: int
) -> list[ImportRun]:
    get_source(session, user, source_id)
    check_page(limit, offset)
    return list(
        session.scalars(
            sa.select(ImportRun)
            .where(ImportRun.source_id == source_id)
            .order_by(ImportRun.started_at.desc(), ImportRun.id)
            .limit(limit)
            .offset(offset)
        )
    )


def list_snapshots(
    session: Session, user: User, source_id: UUID, limit: int, offset: int
) -> list[SourceSnapshot]:
    get_source(session, user, source_id)
    check_page(limit, offset)
    return list(
        session.scalars(
            sa.select(SourceSnapshot)
            .where(SourceSnapshot.source_id == source_id)
            .order_by(SourceSnapshot.created_at.desc(), SourceSnapshot.id)
            .limit(limit)
            .offset(offset)
        )
    )
