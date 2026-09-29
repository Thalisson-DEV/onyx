"""Tenant-scoped persistence for source-level billing and budget records."""

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
from onyx.db.ton.import_profiles import get_execution
from onyx.db.ton.models import (
    ImportProfile,
    ImportProfileExecution,
    OperationalSourceRecord,
)
from onyx.db.ton.sources import get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.ng_financial.models import ProfileExecutionStatus
from onyx.ton.operational_import.models import OperationalParseResult
from onyx.ton.operational_import.parser import (
    BILLING_COLUMNS,
    BILLING_KEY,
    BILLING_SOURCE_KEY,
    BUDGET_ANNUAL_KEY,
    BUDGET_COLUMNS,
    BUDGET_SOURCE_KEY,
    BUDGET_TERM_KEY,
    PROFILE_VERSION,
)
from onyx.ton.sources.models import SourceFormat
from onyx.utils.audit import AuditAction, AuditOutcome

BATCH_SIZE = 500
MAX_STORED_DIAGNOSTICS = 2000
PROFILE_CONTRACTS: dict[str, tuple[str, SourceFormat, dict[str, str]]] = {
    BILLING_KEY: (BILLING_SOURCE_KEY, SourceFormat.XLS, BILLING_COLUMNS),
    BUDGET_ANNUAL_KEY: (BUDGET_SOURCE_KEY, SourceFormat.XLSX, BUDGET_COLUMNS),
    BUDGET_TERM_KEY: (BUDGET_SOURCE_KEY, SourceFormat.XLSX, BUDGET_COLUMNS),
}


def create_operational_profile(
    session: Session, user: User, source_id: UUID, key: str
) -> ImportProfile:
    contract = PROFILE_CONTRACTS.get(key)
    if contract is None:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Unknown operational profile")
    source = get_source(
        session, user, source_id, Permission.MANAGE_TON_SOURCES, lock=True
    )
    source_key, format, column_map = contract
    if source.key != source_key:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Profile source key differs")
    existing = session.scalar(
        sa.select(ImportProfile).where(
            ImportProfile.source_id == source_id,
            ImportProfile.key == key,
            ImportProfile.version == PROFILE_VERSION,
        )
    )
    if existing is not None:
        return existing
    profile = ImportProfile(
        source_id=source_id,
        key=key,
        version=PROFILE_VERSION,
        format=format,
        column_map=dict(column_map),
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


def statistics(result: OperationalParseResult) -> dict[str, int]:
    codes = Counter(item.code for item in result.diagnostics)
    stats = {
        "sheets_inspected": len(result.sheets),
        "sheets_accepted": sum(
            item.classification == "DETAIL" for item in result.sheets
        ),
        "physical_rows_in_workbook": sum(item.physical_rows for item in result.sheets),
        "physical_rows_inspected": sum(item.rows_inspected for item in result.sheets),
        "detail_records_parsed": len(result.records),
        "records_rejected": sum(item.rejected for item in result.sheets),
        "aggregates_excluded": sum(item.aggregates_excluded for item in result.sheets),
        "proposal_rows_excluded": sum(
            item.proposal_rows_excluded for item in result.sheets
        ),
        "warnings": result.warning_count,
        "errors": result.error_count,
        "duplicate_candidates": sum(
            item.duplicate_ordinal > 1 for item in result.records
        ),
        "diagnostics_total": len(result.diagnostics),
        "diagnostics_stored": min(len(result.diagnostics), MAX_STORED_DIAGNOSTICS),
    }
    stats.update({f"diagnostic.{code}": count for code, count in codes.items()})
    return stats


def finish_operational_execution(
    session: Session, execution: ImportProfileExecution, result: OperationalParseResult
) -> None:
    if execution.status != ProfileExecutionStatus.RUNNING:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Import execution is terminal")
    for start in range(0, len(result.records), BATCH_SIZE):
        batch = [
            {
                "id": uuid4(),
                "source_id": execution.source_id,
                "snapshot_id": execution.snapshot_id,
                "execution_id": execution.id,
                "sheet_name": record.locator.sheet_name,
                "source_row_number": record.locator.row_number,
                "record_date": record.record_date,
                "competence": record.competence,
                "amount": record.amount,
                **record.model_dump(
                    mode="json",
                    exclude={"locator", "record_date", "competence", "amount"},
                ),
            }
            for record in result.records[start : start + BATCH_SIZE]
        ]
        session.execute(
            sa.insert(cast(sa.Table, OperationalSourceRecord.__table__)), batch
        )
    execution.status = (
        ProfileExecutionStatus.PARTIAL
        if result.error_count
        else ProfileExecutionStatus.SUCCEEDED
    )
    execution.statistics = statistics(result)
    execution.diagnostics = [
        item.model_dump(mode="json")
        for item in result.diagnostics[:MAX_STORED_DIAGNOSTICS]
    ]
    execution.sheet_summaries = [item.model_dump(mode="json") for item in result.sheets]
    execution.finished_at = datetime.now(UTC)
    session.flush()


def list_operational_records(
    session: Session,
    user: User,
    source_id: UUID,
    execution_id: UUID,
    limit: int,
    offset: int,
) -> Sequence[OperationalSourceRecord]:
    get_execution(session, user, source_id, execution_id)
    if not 1 <= limit <= 100 or offset < 0:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid pagination")
    return list(
        session.scalars(
            sa.select(OperationalSourceRecord)
            .where(
                OperationalSourceRecord.source_id == source_id,
                OperationalSourceRecord.execution_id == execution_id,
            )
            .order_by(
                OperationalSourceRecord.sheet_name,
                OperationalSourceRecord.source_row_number,
                OperationalSourceRecord.id,
            )
            .limit(limit)
            .offset(offset)
        )
    )
