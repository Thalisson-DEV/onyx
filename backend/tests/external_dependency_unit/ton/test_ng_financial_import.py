"""DATA-002 persistence, versioning, and source ACL contracts."""

import logging
from datetime import date
from io import BytesIO
from typing import Any, cast
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.dml import Insert

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import import_profiles, sources
from onyx.db.ton.models import (
    ImportProfile,
    ImportProfileExecution,
    ImportRun,
    ParsedSourceRecord,
    SourceSnapshot,
    TonAuditEvent,
)
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.ng_financial import service as ng_service
from onyx.ton.ng_financial.service import execute_ng_profile
from onyx.ton.sources.models import ImportStatus, SourceCreate, SourceFormat
from onyx.ton.sources.service import import_file
from onyx.ton.sources.validation import MEDIA_TYPES
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import (
    downgrade,
    query_all,
    scratch_database,
    scratch_session,
    table_names,
    upgrade,
)

DATA_001_REVISION = "6be7c77e49ce"
DATA_002_REVISION = "9d2c8f0a7e31"
DATA_002_TABLES = {
    "ton_import_profile",
    "ton_import_profile_execution",
    "ton_parsed_source_record",
}


@pytest.fixture
def source_user(ton_session: Session) -> User:
    user = factories.make_user(ton_session)
    group = factories.make_group(ton_session)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.FULL_ADMIN_PANEL_ACCESS]
    )
    factories.add_member(ton_session, group=group, user=user)
    ton_session.commit()
    return user


@pytest.fixture
def store() -> Mock:
    blobs: dict[str, bytes] = {}
    result = Mock(spec=FileStore)

    def save(content: BytesIO, *, file_id: str, **_kwargs: object) -> str:
        blobs[file_id] = content.read()
        return file_id

    result.save_file.side_effect = save
    result.read_file.side_effect = lambda key: BytesIO(blobs[key])
    result.delete_file.side_effect = lambda key, **_kwargs: blobs.pop(key, None)
    return result


def synthetic_workbook(*, malformed: bool = False, count: int = 2) -> bytes:
    workbook = Workbook()
    sheet = cast(Worksheet, workbook.active)
    sheet.title = "Jul ok"
    for code in ("1 - Parent", "1.1 - Leaf"):
        for index in range(count):
            sheet.append(
                [
                    code if index == 0 else None,
                    date(2026, 7, 1) if index == 0 else None,
                    "001 - Synthetic unit" if index == 0 else None,
                    f"S-{index}",
                    "001 - Synthetic history",
                    "zz-invalid-amount"
                    if malformed and code.startswith("1.1") and index == 1
                    else 10,
                    0,
                    10,
                    None,
                    None,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    10,
                ]
            )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def setup_source(
    session: Session, user: User, store: FileStore, content: bytes
) -> tuple[UUID, UUID, UUID]:
    source = sources.create_source(
        session,
        user,
        SourceCreate(
            key="financial_launches",
            display_name="Synthetic NG source",
            acquisition_type="FILE_UPLOAD",
            status="ACTIVE",
        ),
    )
    session.commit()
    snapshot = import_file(
        session,
        user,
        source.id,
        BytesIO(content),
        "synthetic.xlsx",
        MEDIA_TYPES[SourceFormat.XLSX],
        store,
    )
    profile = import_profiles.create_ng_profile_v1(session, user, source.id)
    session.commit()
    return source.id, snapshot.id, profile.id


def test_profile_versioning_and_source_association(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, _, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook()
    )
    profile = import_profiles.get_profile(
        ton_session, source_user, source_id, profile_id
    )
    assert profile.version == 1 and profile.key == "ng_financial_export"
    assert profile.format == SourceFormat.XLSX
    assert profile.column_map["K"] == "interest_amount"
    assert (
        import_profiles.create_ng_profile_v1(ton_session, source_user, source_id).id
        == profile_id
    )
    second = ImportProfile(
        source_id=source_id,
        key=profile.key,
        version=2,
        format=SourceFormat.XLSX,
        column_map=profile.column_map,
    )
    ton_session.add(second)
    ton_session.commit()
    assert [
        item.version
        for item in import_profiles.list_profiles(ton_session, source_user, source_id)
    ] == [1, 2]
    profile.column_map = {"A": "changed"}
    with pytest.raises(ValueError, match="immutable"):
        ton_session.flush()
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(
            text("UPDATE ton_import_profile SET version = 3 WHERE id = :id"),
            {"id": profile_id},
        )
    ton_session.rollback()


def test_parse_persistence_replay_and_lineage(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook(count=3)
    )
    first = execute_ng_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    second = execute_ng_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    assert first.status == second.status == "SUCCEEDED"
    assert first.statistics["detail_records_parsed"] == 3
    assert first.statistics["hierarchy_rows_ignored"] == 3
    records = import_profiles.list_records(
        ton_session, source_user, source_id, first.id, 100, 0
    )
    replay = import_profiles.list_records(
        ton_session, source_user, source_id, second.id, 100, 0
    )
    assert len(records) == len(replay) == 3
    assert [(row.sheet_name, row.source_row_number) for row in records] == [
        ("Jul ok", 4),
        ("Jul ok", 5),
        ("Jul ok", 6),
    ]
    assert [row.fingerprint for row in records] == [row.fingerprint for row in replay]
    assert all(
        row.snapshot_id == snapshot_id and row.source_id == source_id for row in records
    )
    assert all(
        row.source_values["I"] is None and row.interest_amount == 0 for row in records
    )
    snapshot = ton_session.get(SourceSnapshot, snapshot_id)
    assert snapshot is not None and snapshot.import_run_id is not None


def test_partial_rows_are_quarantined(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook(malformed=True)
    )
    execution = execute_ng_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    assert execution.status == "PARTIAL"
    assert execution.error_code is None and execution.finished_at is not None
    assert execution.statistics["records_rejected"] == 1
    assert execution.statistics["detail_records_parsed"] == 1
    assert execution.statistics["diagnostic.INVALID_AMOUNT"] == 1
    assert execution.diagnostics[0].code == "INVALID_AMOUNT"
    assert execution.diagnostics[0].row_number == 4
    assert execution.diagnostics[0].column == "F"
    assert (
        len(
            import_profiles.list_records(
                ton_session, source_user, source_id, execution.id, 100, 0
            )
        )
        == 1
    )


def test_profile_failure_keeps_raw_snapshot_and_no_records(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    workbook = Workbook()
    cast(Worksheet, workbook.active).append(["wrong workbook"])
    output = BytesIO()
    workbook.save(output)
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, output.getvalue()
    )
    with pytest.raises(OnyxError):
        execute_ng_profile(
            ton_session, source_user, source_id, snapshot_id, profile_id, store
        )
    execution = ton_session.scalar(
        select(ImportProfileExecution).where(
            ImportProfileExecution.snapshot_id == snapshot_id
        )
    )
    assert execution is not None and execution.status == "FAILED"
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(ParsedSourceRecord)
            .where(ParsedSourceRecord.execution_id == execution.id)
        )
        == 0
    )
    snapshot = ton_session.get(SourceSnapshot, snapshot_id)
    assert snapshot is not None
    # DATA-001 capture status is independent of the parse outcome.
    run = ton_session.get(ImportRun, snapshot.import_run_id)
    assert run is not None and run.status == ImportStatus.SUCCEEDED
    assert execution.error_code == "INVALID_INPUT"


def test_new_profile_version_is_refused_and_v1_reparses_old_snapshot(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook()
    )
    v1 = import_profiles.get_profile(ton_session, source_user, source_id, profile_id)
    v2 = ImportProfile(
        source_id=source_id,
        key=v1.key,
        version=2,
        format=SourceFormat.XLSX,
        column_map=v1.column_map,
    )
    ton_session.add(v2)
    ton_session.commit()
    with pytest.raises(OnyxError):
        execute_ng_profile(
            ton_session, source_user, source_id, snapshot_id, v2.id, store
        )
    # No parser is pinned to v2, so no execution row exists for it.
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(ImportProfileExecution)
            .where(ImportProfileExecution.profile_id == v2.id)
        )
        == 0
    )
    replay = execute_ng_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    assert replay.status == "SUCCEEDED" and replay.profile_id == profile_id


def test_records_cannot_be_added_to_a_terminal_execution(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook()
    )
    execution = execute_ng_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    record = import_profiles.list_records(
        ton_session, source_user, source_id, execution.id, 1, 0
    )[0]
    with pytest.raises(DBAPIError, match="running execution"):
        ton_session.execute(
            text(
                "INSERT INTO ton_parsed_source_record "
                "SELECT gen_random_uuid(), source_id, snapshot_id, execution_id, "
                "sheet_name, source_row_number + 1000, sheet_month, account_code, "
                "account_label, emission_date, administrative_unit, document_number, "
                "history, movement_amount, movement_retention_amount, "
                "movement_net_amount, installment_retention_amount, "
                "installment_net_amount, interest_amount, penalty_amount, "
                "discount_amount, expense_amount, loss_amount, "
                "other_deduction_amount, final_amount, source_values, fingerprint, "
                "duplicate_ordinal FROM ton_parsed_source_record WHERE id = :id"
            ),
            {"id": record.id},
        )
    ton_session.rollback()


def test_logs_carry_identifiers_not_source_values(
    ton_session: Session,
    source_user: User,
    store: FileStore,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook(malformed=True)
    )
    # The Onyx logger does not propagate to caplog, so capture its calls too.
    with (
        caplog.at_level(logging.DEBUG),
        patch.object(ng_service, "logger") as service_logger,
    ):
        execute_ng_profile(
            ton_session, source_user, source_id, snapshot_id, profile_id, store
        )
    calls = [
        str(argument) for call in service_logger.method_calls for argument in call.args
    ]
    text_logged = "\n".join(
        [*calls, *(record.getMessage() for record in caplog.records)]
    )
    assert "execution_id=" in text_logged
    for secret in (
        "Synthetic history",
        "Synthetic unit",
        "zz-invalid-amount",
        "1 - Parent",
    ):
        assert secret not in text_logged


def test_downgrade_refuses_while_profiles_exist(ton_database: str) -> None:
    with scratch_session(ton_database) as session:
        user = factories.make_user(session)
        group = factories.make_group(session)
        factories.grant_permissions(
            session, group=group, permissions=[Permission.FULL_ADMIN_PANEL_ACCESS]
        )
        factories.add_member(session, group=group, user=user)
        session.commit()
        source = sources.create_source(
            session,
            user,
            SourceCreate(
                key="financial_launches",
                display_name="Synthetic NG source",
                acquisition_type="FILE_UPLOAD",
                status="ACTIVE",
            ),
        )
        import_profiles.create_ng_profile_v1(session, user, source.id)
        session.commit()
    with pytest.raises(RuntimeError, match="DATA-002"):
        downgrade(ton_database, DATA_001_REVISION)
    assert "ton_parsed_source_record" in table_names(ton_database)


def test_data_002_downgrade_and_upgrade_from_empty_state(ton_database: str) -> None:
    # Later slices are removed first so this measures DATA-002 alone.
    downgrade(ton_database, DATA_002_REVISION)
    before = table_names(ton_database, "ton_")
    downgrade(ton_database, DATA_001_REVISION)
    after = table_names(ton_database, "ton_")
    assert before - after == DATA_002_TABLES
    assert {"ton_source", "ton_import_run", "ton_source_snapshot"} <= after
    functions = query_all(
        ton_database,
        "SELECT proname FROM pg_proc WHERE proname IN "
        "('ton_protect_import_profile', 'ton_protect_terminal_profile_execution', "
        "'ton_protect_parsed_record')",
    )
    assert functions == []
    upgrade(ton_database, DATA_002_REVISION)
    assert table_names(ton_database, "ton_") == before
    upgrade(ton_database, "head")


def test_batch_insert_and_access_boundary(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook(count=501)
    )
    inserts: list[str] = []

    def record_insert(*args: Any) -> None:
        statement = str(args[2])
        if statement.startswith("INSERT INTO ton_parsed_source_record"):
            inserts.append(statement)

    engine = ton_session.get_bind()
    event.listen(engine, "before_cursor_execute", record_insert)
    try:
        execution = execute_ng_profile(
            ton_session, source_user, source_id, snapshot_id, profile_id, store
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_insert)
    assert execution.statistics["detail_records_parsed"] == 501
    # One executemany per 500-row batch, not one statement per row.
    assert len(inserts) == 2
    outsider = factories.make_user(ton_session)
    ton_session.commit()
    with pytest.raises(OnyxError):
        import_profiles.get_execution(ton_session, outsider, source_id, execution.id)
    with pytest.raises(OnyxError):
        import_profiles.list_records(
            ton_session, outsider, source_id, execution.id, 10, 0
        )


def test_second_batch_failure_rolls_back_all_records(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook(count=501)
    )
    original_execute = ton_session.execute
    batches = 0

    def fail_second_batch(statement: Executable, *args: Any, **kwargs: Any) -> object:
        nonlocal batches
        if (
            isinstance(statement, Insert)
            and statement.table.name == "ton_parsed_source_record"
        ):
            batches += 1
            if batches == 2:
                raise RuntimeError("synthetic persistence failure")
        return original_execute(statement, *args, **kwargs)

    with patch.object(ton_session, "execute", side_effect=fail_second_batch):
        with pytest.raises(OnyxError):
            execute_ng_profile(
                ton_session, source_user, source_id, snapshot_id, profile_id, store
            )
    execution = ton_session.scalar(
        select(ImportProfileExecution).where(
            ImportProfileExecution.snapshot_id == snapshot_id
        )
    )
    assert execution is not None and execution.status == "FAILED"
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(ParsedSourceRecord)
            .where(ParsedSourceRecord.execution_id == execution.id)
        )
        == 0
    )


def test_profile_execution_is_tenant_scoped(
    ton_head_template: str, ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook()
    )
    execution = execute_ng_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    with scratch_database(template=ton_head_template) as database:
        with scratch_session(database) as other:
            with pytest.raises(OnyxError):
                import_profiles.get_profile(other, source_user, source_id, profile_id)
            with pytest.raises(OnyxError):
                import_profiles.get_execution(
                    other, source_user, source_id, execution.id
                )
    actions = set(ton_session.scalars(select(TonAuditEvent.action)))
    assert "ton_sources.profile_create" in actions
    assert "ton_sources.profile_execute" in actions
    assert "ton_sources.profile_succeed" in actions


def test_parsed_history_is_immutable(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session, source_user, store, synthetic_workbook()
    )
    execution = execute_ng_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    record = import_profiles.list_records(
        ton_session, source_user, source_id, execution.id, 1, 0
    )[0]
    record.history = "changed"
    with pytest.raises(ValueError, match="immutable"):
        ton_session.flush()
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(
            text(
                "UPDATE ton_parsed_source_record SET history = 'changed' WHERE id = :id"
            ),
            {"id": record.id},
        )
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(
            text(
                "UPDATE ton_import_profile_execution SET status = 'FAILED' WHERE id = :id"
            ),
            {"id": execution.id},
        )
    ton_session.rollback()
