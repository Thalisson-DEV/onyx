"""Tenant-scoped profile and parsed-record persistence."""

from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import (
    ImportProfile,
    ImportProfileExecution,
    ParsedSourceRecord,
    SourceSnapshot,
)
from onyx.db.ton.sources import get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.ng_financial.models import (
    REJECTION_CODES,
    ParsedImportResult,
    ProfileExecutionStatus,
    RowKind,
)
from onyx.ton.ng_financial.parser import (
    COLUMN_MAP,
    PROFILE_KEY,
    PROFILE_VERSION,
    SOURCE_KEY,
)
from onyx.ton.sources.models import SourceFormat
from onyx.utils.audit import AuditAction, AuditOutcome

BATCH_SIZE = 500
# Stored diagnostics are capped; statistics keep complete counts per code.
MAX_STORED_DIAGNOSTICS = 2000


def create_ng_profile_v1(
    session: Session,
    user: User,
    source_id: UUID,
    permission: Permission = Permission.MANAGE_TON_SOURCES,
) -> ImportProfile:
    """Idempotent: the v1 contract is fixed, so an existing row is returned."""
    source = get_source(session, user, source_id, permission, lock=True)
    if source.key != SOURCE_KEY:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "NG profile requires a financial launches source",
        )
    existing = session.scalar(
        sa.select(ImportProfile).where(
            ImportProfile.source_id == source_id,
            ImportProfile.key == PROFILE_KEY,
            ImportProfile.version == PROFILE_VERSION,
        )
    )
    if existing is not None:
        return existing
    profile = ImportProfile(
        source_id=source_id,
        key=PROFILE_KEY,
        version=PROFILE_VERSION,
        format=SourceFormat.XLSX,
        column_map=dict(COLUMN_MAP),
    )
    session.add(profile)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_PROFILE_CREATE,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.IMPORT_PROFILE,
        resource_id=profile.id,
    )
    return profile


def get_profile(
    session: Session,
    user: User,
    source_id: UUID,
    profile_id: UUID,
    permission: Permission = Permission.READ_TON_SOURCES,
) -> ImportProfile:
    get_source(session, user, source_id, permission)
    profile = session.scalar(
        sa.select(ImportProfile).where(
            ImportProfile.id == profile_id, ImportProfile.source_id == source_id
        )
    )
    if profile is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Import profile not found")
    return profile


def list_profiles(session: Session, user: User, source_id: UUID) -> list[ImportProfile]:
    get_source(session, user, source_id)
    return list(
        session.scalars(
            sa.select(ImportProfile)
            .where(ImportProfile.source_id == source_id)
            .order_by(ImportProfile.key, ImportProfile.version)
        )
    )


def get_snapshot_for_parse(
    session: Session, user: User, source_id: UUID, snapshot_id: UUID
) -> SourceSnapshot:
    get_source(session, user, source_id, Permission.IMPORT_TON_SOURCES)
    snapshot = session.scalar(
        sa.select(SourceSnapshot).where(
            SourceSnapshot.id == snapshot_id, SourceSnapshot.source_id == source_id
        )
    )
    if (
        snapshot is None
        or snapshot.storage_file_id is None
        or snapshot.checksum is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Raw snapshot not found")
    return snapshot


def start_execution(
    session: Session, user: User, source_id: UUID, snapshot_id: UUID, profile_id: UUID
) -> ImportProfileExecution:
    execution = ImportProfileExecution(
        source_id=source_id,
        snapshot_id=snapshot_id,
        profile_id=profile_id,
        status=ProfileExecutionStatus.RUNNING,
        statistics={},
        diagnostics=[],
        sheet_summaries=[],
    )
    session.add(execution)
    session.flush()
    audit_execution(session, user, execution, AuditAction.TON_PROFILE_EXECUTE)
    return execution


def audit_execution(
    session: Session,
    user: User,
    execution: ImportProfileExecution,
    action: AuditAction,
) -> None:
    emit_ton_audit_event(
        session,
        action=action,
        outcome=AuditOutcome.FAILURE
        if action == AuditAction.TON_PROFILE_FAIL
        else AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.IMPORT_PROFILE_EXECUTION,
        resource_id=execution.id,
    )


def _store_result(
    execution: ImportProfileExecution, result: ParsedImportResult
) -> None:
    execution.statistics = statistics(result)
    execution.diagnostics = [
        item.model_dump(mode="json")
        for item in result.diagnostics[:MAX_STORED_DIAGNOSTICS]
    ]
    execution.sheet_summaries = [item.model_dump(mode="json") for item in result.sheets]


def finish_execution(
    session: Session, execution: ImportProfileExecution, result: ParsedImportResult
) -> None:
    """Insert every record in bounded batches. The caller owns the commit."""
    if execution.status != ProfileExecutionStatus.RUNNING:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Import profile execution is terminal")
    for start in range(0, len(result.records), BATCH_SIZE):
        batch = [
            {
                "id": uuid4(),
                "source_id": execution.source_id,
                "snapshot_id": execution.snapshot_id,
                "execution_id": execution.id,
                "sheet_name": record.locator.sheet_name,
                "source_row_number": record.locator.row_number,
                **record.model_dump(exclude={"locator"}),
            }
            for record in result.records[start : start + BATCH_SIZE]
        ]
        # Core insert keeps NULL columns in every row, so one batch stays one
        # executemany instead of splitting on each row's NULL pattern.
        session.execute(sa.insert(cast(sa.Table, ParsedSourceRecord.__table__)), batch)
    execution.status = (
        ProfileExecutionStatus.PARTIAL
        if result.error_count
        else ProfileExecutionStatus.SUCCEEDED
    )
    _store_result(execution, result)
    execution.finished_at = datetime.now(UTC)
    session.flush()


def fail_execution(
    session: Session,
    execution: ImportProfileExecution,
    error_code: str,
    result: ParsedImportResult | None = None,
) -> None:
    execution.status = ProfileExecutionStatus.FAILED
    execution.error_code = error_code
    execution.finished_at = datetime.now(UTC)
    if result is not None:
        _store_result(execution, result)
    session.flush()


def statistics(result: ParsedImportResult) -> dict[str, int]:
    codes = Counter(item.code for item in result.diagnostics)
    stats = {
        "sheets_inspected": len(result.sheets),
        "sheets_accepted": sum(item.accepted for item in result.sheets),
        "physical_rows_inspected": sum(item.physical_rows for item in result.sheets),
        "detail_records_parsed": len(result.records),
        "hierarchy_rows_ignored": sum(
            item.classifications.get(RowKind.HIERARCHY, 0) for item in result.sheets
        ),
        "subtotal_rows_ignored": sum(
            item.classifications.get(RowKind.SUBTOTAL, 0)
            + item.classifications.get(RowKind.TOTAL, 0)
            for item in result.sheets
        ),
        "warnings": result.warning_count,
        "errors": result.error_count,
        "records_rejected": sum(codes[code] for code in REJECTION_CODES),
        "diagnostics_total": len(result.diagnostics),
        "diagnostics_stored": min(len(result.diagnostics), MAX_STORED_DIAGNOSTICS),
    }
    stats.update({f"diagnostic.{code.value}": count for code, count in codes.items()})
    return stats


def get_execution(
    session: Session,
    user: User,
    source_id: UUID,
    execution_id: UUID,
    permission: Permission = Permission.READ_TON_SOURCES,
) -> ImportProfileExecution:
    get_source(session, user, source_id, permission)
    execution = session.scalar(
        sa.select(ImportProfileExecution).where(
            ImportProfileExecution.id == execution_id,
            ImportProfileExecution.source_id == source_id,
        )
    )
    if execution is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Import profile execution not found")
    return execution


def list_records(
    session: Session,
    user: User,
    source_id: UUID,
    execution_id: UUID,
    limit: int,
    offset: int,
) -> Sequence[ParsedSourceRecord]:
    get_execution(session, user, source_id, execution_id)
    if not 1 <= limit <= 100 or offset < 0:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid pagination")
    return list(
        session.scalars(
            sa.select(ParsedSourceRecord)
            .where(
                ParsedSourceRecord.execution_id == execution_id,
                ParsedSourceRecord.source_id == source_id,
            )
            .order_by(
                ParsedSourceRecord.sheet_month,
                ParsedSourceRecord.source_row_number,
                ParsedSourceRecord.id,
            )
            .limit(limit)
            .offset(offset)
        )
    )
