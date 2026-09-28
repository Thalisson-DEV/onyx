"""Application boundary for raw capture and recoverable storage failures."""

import hashlib
from collections.abc import Callable
from io import BytesIO
from typing import BinaryIO
from uuid import UUID

from sqlalchemy.orm import Session

from onyx.configs.constants import FileOrigin
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import sources as repository
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.sources.models import (
    ImportRunView,
    ImportStatus,
    ImportTrigger,
    SnapshotView,
)
from onyx.ton.sources.validation import (
    MAX_UPLOAD_BYTES,
    ValidatedUpload,
    validate_connected_json,
    validate_upload,
)
from onyx.utils.audit import AuditAction
from onyx.utils.logger import setup_logger

logger = setup_logger()


def import_file(
    session: Session,
    user: User,
    source_id: UUID,
    stream: BinaryIO,
    filename: str,
    media_type: str,
    store: FileStore,
) -> SnapshotView:
    return _import_payload(
        session,
        user,
        source_id,
        stream,
        store,
        ImportTrigger.MANUAL_UPLOAD,
        lambda payload: validate_upload(payload, filename, media_type),
    )


def import_connected_json(
    session: Session, user: User, source_id: UUID, stream: BinaryIO, store: FileStore
) -> SnapshotView:
    """Internal entry for a future API, database, or service adapter."""
    return _import_payload(
        session,
        user,
        source_id,
        stream,
        store,
        ImportTrigger.API_SYNC,
        validate_connected_json,
    )


def _import_payload(
    session: Session,
    user: User,
    source_id: UUID,
    stream: BinaryIO,
    store: FileStore,
    trigger: ImportTrigger,
    validate: Callable[[BinaryIO], ValidatedUpload],
) -> SnapshotView:
    """Own commits. Call with a dedicated tenant session, never a caller transaction."""
    run = repository.start_import_run(session, user, source_id, trigger)
    run_id, file_id = run.id, run.storage_file_id
    repository.transition_run(run, ImportStatus.RUNNING)
    repository.audit(
        session,
        user,
        AuditAction.TON_IMPORT_START,
        run_id,
        TonAuditResourceKind.IMPORT_RUN,
    )
    session.commit()
    failure = OnyxErrorCode.SOURCE_IMPORT_FAILED
    result: SnapshotView | None = None
    try:
        upload = validate(stream)
        failure = OnyxErrorCode.SOURCE_STORAGE_ERROR
        stored_id = store.save_file(
            BytesIO(upload.content),
            display_name=file_id,
            file_origin=FileOrigin.TON_SOURCE,
            file_type=upload.media_type,
            file_id=file_id,
        )
        if stored_id != file_id:
            raise OnyxError(OnyxErrorCode.SOURCE_INTEGRITY_ERROR)
        # Verify the stored bytes before metadata can claim success.
        with store.read_file(file_id) as captured:
            stored = captured.read(MAX_UPLOAD_BYTES + 1)
        if (
            len(stored) != len(upload.content)
            or hashlib.sha256(stored).hexdigest() != upload.checksum
        ):
            raise OnyxError(OnyxErrorCode.SOURCE_INTEGRITY_ERROR)
        failure = OnyxErrorCode.SOURCE_IMPORT_FAILED
        snapshot = repository.capture_snapshot(session, user, source_id, run_id, upload)
        result = SnapshotView.model_validate(snapshot)
        session.commit()
        logger.info(
            "TON raw capture source_id=%s run_id=%s snapshot_id=%s format=%s size=%s",
            source_id,
            run_id,
            result.id,
            result.format,
            result.size_bytes,
        )
        return result
    except Exception as error:
        # Do not attach exception text: drivers can include SQL parameters or bytes.
        if isinstance(error, OnyxError):
            failure = error.error_code
        try:
            session.rollback()
            # A lost commit acknowledgement can mean success. Keep that blob.
            current = repository.get_run(session, user, source_id, run_id, lock=True)
            if current.status != ImportStatus.SUCCEEDED:
                repository.transition_run(current, ImportStatus.FAILED, failure.name)
                current.cleanup_required = True
                repository.audit(
                    session,
                    user,
                    AuditAction.TON_IMPORT_FAIL,
                    run_id,
                    TonAuditResourceKind.IMPORT_RUN,
                )
                session.commit()
                cleanup_failed_import(session, user, source_id, run_id, store)
            else:
                session.rollback()
                if result is not None:
                    return result
        except Exception:
            # Keep the reservation if recovery cannot reach the database.
            logger.warning(
                "TON import requires recovery source_id=%s run_id=%s", source_id, run_id
            )
        raise OnyxError(failure, f"Source import failed; run_id={run_id}") from None


def cleanup_failed_import(
    session: Session, user: User, source_id: UUID, run_id: UUID, store: FileStore
) -> ImportRunView:
    repository.get_source(session, user, source_id, Permission.IMPORT_TON_SOURCES)
    run = repository.get_run(session, user, source_id, run_id, lock=True)
    if run.status != ImportStatus.FAILED:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Only failed imports can be cleaned")
    if run.cleanup_required:
        try:
            store.delete_file(run.storage_file_id, error_on_missing=False)
        except Exception:
            logger.warning(
                "TON import cleanup pending source_id=%s run_id=%s", source_id, run_id
            )
        else:
            run.cleanup_required = False
        session.commit()
    return ImportRunView.model_validate(run)
