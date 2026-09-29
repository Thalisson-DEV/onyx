"""Execute a pinned operational profile on a captured source snapshot."""

import hashlib
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import import_profiles as common_repository
from onyx.db.ton import operational_import as repository
from onyx.db.ton.sources import get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.operational_import.models import (
    OperationalExecutionView,
    OperationalParseResult,
)
from onyx.ton.operational_import.parser import (
    BILLING_KEY,
    BUDGET_ANNUAL_KEY,
    BUDGET_TERM_KEY,
    MAX_BYTES,
    PROFILE_VERSION,
    BillingParser,
    BudgetParser,
    identify_profile,
)
from onyx.utils.audit import AuditAction
from onyx.utils.logger import setup_logger

logger = setup_logger()
PARSERS: dict[str, Callable[[], BillingParser | BudgetParser]] = {
    BILLING_KEY: BillingParser,
    BUDGET_ANNUAL_KEY: lambda: BudgetParser(BUDGET_ANNUAL_KEY),
    BUDGET_TERM_KEY: lambda: BudgetParser(BUDGET_TERM_KEY),
}


def select_operational_profile(
    session: Session,
    user: User,
    source_id: UUID,
    snapshot_id: UUID,
    store: FileStore,
) -> str:
    source = get_source(session, user, source_id, Permission.IMPORT_TON_SOURCES)
    snapshot = common_repository.get_snapshot_for_parse(
        session, user, source_id, snapshot_id
    )
    assert snapshot.storage_file_id is not None and snapshot.checksum is not None
    with store.read_file(snapshot.storage_file_id) as stream:
        content = stream.read(MAX_BYTES + 1)
    if (
        len(content) > MAX_BYTES
        or hashlib.sha256(content).hexdigest() != snapshot.checksum
    ):
        raise OnyxError(OnyxErrorCode.SOURCE_INTEGRITY_ERROR)
    if snapshot.format is None:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Snapshot format absent")
    key = identify_profile(content, snapshot.format)
    if repository.PROFILE_CONTRACTS[key][0] != source.key:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Snapshot source differs")
    return key


def execute_operational_profile(
    session: Session,
    user: User,
    source_id: UUID,
    snapshot_id: UUID,
    profile_id: UUID,
    store: FileStore,
) -> OperationalExecutionView:
    profile = common_repository.get_profile(
        session, user, source_id, profile_id, Permission.IMPORT_TON_SOURCES
    )
    snapshot = common_repository.get_snapshot_for_parse(
        session, user, source_id, snapshot_id
    )
    contract = repository.PROFILE_CONTRACTS.get(profile.key)
    if (
        contract is None
        or profile.version != PROFILE_VERSION
        or profile.format != contract[1]
        or profile.column_map != contract[2]
        or snapshot.format != contract[1]
    ):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Unsupported operational profile")
    execution = common_repository.start_execution(
        session, user, source_id, snapshot_id, profile_id
    )
    execution_id = execution.id
    session.commit()
    result: OperationalParseResult | None = None
    try:
        assert snapshot.storage_file_id is not None and snapshot.checksum is not None
        with store.read_file(snapshot.storage_file_id) as stream:
            content = stream.read(MAX_BYTES + 1)
        if (
            len(content) > MAX_BYTES
            or hashlib.sha256(content).hexdigest() != snapshot.checksum
        ):
            raise OnyxError(OnyxErrorCode.SOURCE_INTEGRITY_ERROR)
        result = PARSERS[profile.key]().parse(content, snapshot_id)
        execution = common_repository.get_execution(
            session, user, source_id, execution_id, Permission.IMPORT_TON_SOURCES
        )
        repository.finish_operational_execution(session, execution, result)
        common_repository.audit_execution(
            session,
            user,
            execution,
            AuditAction.TON_PROFILE_PARTIAL
            if result.error_count
            else AuditAction.TON_PROFILE_SUCCEED,
        )
        view = OperationalExecutionView.model_validate(execution)
        session.commit()
        logger.info(
            "TON operational parse source_id=%s snapshot_id=%s execution_id=%s records=%s",
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
            execution = common_repository.get_execution(
                session, user, source_id, execution_id, Permission.IMPORT_TON_SOURCES
            )
            common_repository.fail_execution(session, execution, code)
            common_repository.audit_execution(
                session, user, execution, AuditAction.TON_PROFILE_FAIL
            )
            session.commit()
        except Exception:
            session.rollback()
            logger.warning(
                "TON operational parse recovery required execution_id=%s",
                execution_id,
            )
        raise OnyxError(
            OnyxErrorCode.SOURCE_IMPORT_FAILED,
            f"Operational profile execution failed; execution_id={execution_id}",
        ) from None
