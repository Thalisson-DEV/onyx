"""Parse a captured snapshot with a pinned NG profile."""

import hashlib
from uuid import UUID

from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import import_profiles as repository
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.ng_financial import installments
from onyx.ton.ng_financial.models import (
    ImportProfileExecutionView,
    ParsedImportResult,
    ProfileExecutionStatus,
)
from onyx.ton.ng_financial.parser import (
    COLUMN_MAP,
    MAX_WORKBOOK_BYTES,
    PROFILE_KEY,
    PROFILE_VERSION,
    NgFinancialExportParser,
)
from onyx.ton.sources.models import SourceFormat
from onyx.utils.audit import AuditAction
from onyx.utils.logger import setup_logger

logger = setup_logger()

# Each profile version is pinned to one parser and its stored column
# contract. A new layout adds a version.
PARSERS: dict[
    tuple[str, int],
    tuple[
        type[NgFinancialExportParser] | type[installments.InstallmentTableParser],
        dict[str, str],
    ],
] = {
    (PROFILE_KEY, PROFILE_VERSION): (NgFinancialExportParser, COLUMN_MAP),
    (installments.PROFILE_KEY, installments.PROFILE_VERSION): (
        installments.InstallmentTableParser,
        installments.COLUMN_MAP,
    ),
}


def execute_ng_profile(
    session: Session,
    user: User,
    source_id: UUID,
    snapshot_id: UUID,
    profile_id: UUID,
    store: FileStore,
) -> ImportProfileExecutionView:
    """Own commits. Failure keeps a status row and no parsed records."""
    profile = repository.get_profile(
        session, user, source_id, profile_id, Permission.IMPORT_TON_SOURCES
    )
    snapshot = repository.get_snapshot_for_parse(session, user, source_id, snapshot_id)
    pinned = PARSERS.get((profile.key, profile.version))
    # The stored contract must be the one the pinned parser implements.
    if (
        pinned is None
        or profile.format != SourceFormat.XLSX
        or profile.column_map != pinned[1]
        or snapshot.format != SourceFormat.XLSX
    ):
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Unsupported NG profile or snapshot format"
        )
    execution = repository.start_execution(
        session, user, source_id, snapshot_id, profile_id
    )
    execution_id = execution.id
    storage_file_id = snapshot.storage_file_id
    checksum = snapshot.checksum
    # The RUNNING row is durable before parsing, so a crash stays visible.
    session.commit()
    result: ParsedImportResult | None = None
    try:
        assert storage_file_id is not None and checksum is not None
        with store.read_file(storage_file_id) as stream:
            content = stream.read(MAX_WORKBOOK_BYTES + 1)
        if (
            len(content) > MAX_WORKBOOK_BYTES
            or hashlib.sha256(content).hexdigest() != checksum
        ):
            raise OnyxError(OnyxErrorCode.SOURCE_INTEGRITY_ERROR)
        result = pinned[0]().parse(content, snapshot_id)
        execution = repository.get_execution(
            session, user, source_id, execution_id, Permission.IMPORT_TON_SOURCES
        )
        repository.finish_execution(session, execution, result)
        repository.audit_execution(
            session,
            user,
            execution,
            AuditAction.TON_PROFILE_PARTIAL
            if execution.status == ProfileExecutionStatus.PARTIAL
            else AuditAction.TON_PROFILE_SUCCEED,
        )
        view = ImportProfileExecutionView.model_validate(execution)
        session.commit()
        logger.info(
            "TON NG parse source_id=%s snapshot_id=%s execution_id=%s records=%s",
            source_id,
            snapshot_id,
            execution_id,
            len(result.records),
        )
        return view
    except Exception as error:
        session.rollback()
        code = (
            error.error_code.name
            if isinstance(error, OnyxError)
            else "SOURCE_IMPORT_FAILED"
        )
        try:
            execution = repository.get_execution(
                session, user, source_id, execution_id, Permission.IMPORT_TON_SOURCES
            )
            repository.fail_execution(session, execution, code, result)
            repository.audit_execution(
                session, user, execution, AuditAction.TON_PROFILE_FAIL
            )
            session.commit()
        except Exception:
            session.rollback()
            logger.warning(
                "TON NG parse recovery required execution_id=%s", execution_id
            )
        raise OnyxError(
            OnyxErrorCode.SOURCE_IMPORT_FAILED,
            f"NG profile execution failed; execution_id={execution_id}",
        ) from None
