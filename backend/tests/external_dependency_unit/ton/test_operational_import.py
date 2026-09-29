"""DATA-004A/B persistence and source access on disposable PostgreSQL."""

from io import BytesIO
from typing import Any
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import Insert

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import operational_import, sources
from onyx.db.ton.models import (
    ImportProfile,
    ImportProfileExecution,
    OperationalSourceRecord,
    TonAuditEvent,
)
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.operational_import import service as operational_service
from onyx.ton.operational_import.parser import (
    BILLING_KEY,
    BUDGET_ANNUAL_KEY,
    BUDGET_TERM_KEY,
)
from onyx.ton.operational_import.service import (
    execute_operational_profile,
    select_operational_profile,
)
from onyx.ton.sources.models import SourceCreate, SourceFormat
from onyx.ton.sources.service import import_file
from onyx.ton.sources.validation import MEDIA_TYPES
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import (
    downgrade,
    scratch_database,
    scratch_session,
    table_names,
    upgrade,
)
from tests.unit.ton.test_operational_import_parser import (
    billing_book,
    budget_book,
    invoice,
)


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


def setup_source(
    session: Session,
    user: User,
    store: FileStore,
    *,
    source_key: str,
    content: bytes,
    format: SourceFormat,
    profile_key: str,
) -> tuple[UUID, UUID, UUID]:
    source = sources.create_source(
        session,
        user,
        SourceCreate(
            key=source_key,
            display_name="Synthetic source",
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
        f"synthetic.{format.value.lower()}",
        MEDIA_TYPES[format],
        store,
    )
    profile = operational_import.create_operational_profile(
        session, user, source.id, profile_key
    )
    session.commit()
    return source.id, snapshot.id, profile.id


def test_billing_partial_replay_lineage_and_acl(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    content = billing_book([invoice(), invoice(), invoice(gross="bad")])
    source_id, snapshot_id, profile_id = setup_source(
        ton_session,
        source_user,
        store,
        source_key="billing_invoices",
        content=content,
        format=SourceFormat.XLS,
        profile_key=BILLING_KEY,
    )
    assert (
        select_operational_profile(
            ton_session, source_user, source_id, snapshot_id, store
        )
        == BILLING_KEY
    )
    with patch.object(operational_service, "logger") as service_logger:
        first = execute_operational_profile(
            ton_session, source_user, source_id, snapshot_id, profile_id, store
        )
    logged = " ".join(
        str(argument) for call in service_logger.method_calls for argument in call.args
    )
    assert "Synthetic payer" not in logged
    second = execute_operational_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    assert first.status == second.status == "PARTIAL"
    assert first.statistics["detail_records_parsed"] == 2
    assert first.statistics["records_rejected"] == 1
    assert first.statistics["duplicate_candidates"] == 1
    records = operational_import.list_operational_records(
        ton_session, source_user, source_id, first.id, 100, 0
    )
    replay = operational_import.list_operational_records(
        ton_session, source_user, source_id, second.id, 100, 0
    )
    assert [row.source_row_number for row in records] == [4, 5]
    assert [row.fingerprint for row in records] == [row.fingerprint for row in replay]
    assert all(
        row.snapshot_id == snapshot_id and row.source_id == source_id for row in records
    )
    outsider = factories.make_user(ton_session)
    ton_session.commit()
    with pytest.raises(OnyxError):
        operational_import.list_operational_records(
            ton_session, outsider, source_id, first.id, 100, 0
        )


@pytest.mark.parametrize("key", [BUDGET_ANNUAL_KEY, BUDGET_TERM_KEY])
def test_budget_profile_and_aggregate_exclusion(
    ton_session: Session, source_user: User, store: FileStore, key: str
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session,
        source_user,
        store,
        source_key="budget",
        content=budget_book(key),
        format=SourceFormat.XLSX,
        profile_key=key,
    )
    assert (
        select_operational_profile(
            ton_session, source_user, source_id, snapshot_id, store
        )
        == key
    )
    execution = execute_operational_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    assert execution.status == "SUCCEEDED"
    assert execution.statistics["detail_records_parsed"] == 2
    assert execution.statistics["aggregates_excluded"] == 2
    assert execution.statistics["physical_rows_inspected"] == 35
    records = operational_import.list_operational_records(
        ton_session, source_user, source_id, execution.id, 1, 0
    )
    assert len(records) == 1
    assert records[0].source_row_number == 12
    assert records[0].amount == 10
    assert records[0].formula_cached


def test_atomic_failure_and_batch_insert(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session,
        source_user,
        store,
        source_key="billing_invoices",
        content=billing_book([invoice(index + 1) for index in range(501)]),
        format=SourceFormat.XLS,
        profile_key=BILLING_KEY,
    )
    inserts = 0
    original_execute = ton_session.execute

    def count_and_fail(statement: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal inserts
        if (
            isinstance(statement, Insert)
            and statement.table.name == "ton_operational_source_record"
        ):
            inserts += 1
            if inserts == 2:
                raise RuntimeError("synthetic insert failure")
        return original_execute(statement, *args, **kwargs)

    with patch.object(ton_session, "execute", side_effect=count_and_fail):
        with pytest.raises(OnyxError):
            execute_operational_profile(
                ton_session, source_user, source_id, snapshot_id, profile_id, store
            )
    execution = ton_session.scalar(
        select(ImportProfileExecution).where(
            ImportProfileExecution.snapshot_id == snapshot_id
        )
    )
    assert execution is not None and execution.status == "FAILED"
    assert inserts == 2
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(OperationalSourceRecord)
            .where(OperationalSourceRecord.execution_id == execution.id)
        )
        == 0
    )


def test_budget_partial_and_profile_version(
    ton_session: Session, source_user: User, store: FileStore
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session,
        source_user,
        store,
        source_key="budget",
        content=budget_book(malformed=True),
        format=SourceFormat.XLSX,
        profile_key=BUDGET_ANNUAL_KEY,
    )
    profile = ton_session.get(ImportProfile, profile_id)
    assert profile is not None
    second = ImportProfile(
        source_id=source_id,
        key=profile.key,
        version=2,
        format=profile.format,
        column_map=profile.column_map,
    )
    ton_session.add(second)
    ton_session.commit()
    with pytest.raises(OnyxError):
        execute_operational_profile(
            ton_session, source_user, source_id, snapshot_id, second.id, store
        )
    result = execute_operational_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    assert result.status == "PARTIAL"
    assert result.statistics["records_rejected"] == 1
    assert result.statistics["detail_records_parsed"] == 1


def test_migration_downgrade_and_reupgrade(ton_database: str) -> None:
    assert "ton_operational_source_record" in table_names(ton_database)
    downgrade(ton_database, "4b7e2d9c1a36")
    assert "ton_operational_source_record" not in table_names(ton_database)
    upgrade(ton_database, "head")
    assert "ton_operational_source_record" in table_names(ton_database)


def test_tenant_boundary_and_audit(
    ton_head_template: str,
    ton_session: Session,
    source_user: User,
    store: FileStore,
) -> None:
    source_id, snapshot_id, profile_id = setup_source(
        ton_session,
        source_user,
        store,
        source_key="billing_invoices",
        content=billing_book([invoice()]),
        format=SourceFormat.XLS,
        profile_key=BILLING_KEY,
    )
    execution = execute_operational_profile(
        ton_session, source_user, source_id, snapshot_id, profile_id, store
    )
    with scratch_database(template=ton_head_template) as database:
        with scratch_session(database) as other:
            with pytest.raises(OnyxError):
                operational_import.list_operational_records(
                    other, source_user, source_id, execution.id, 100, 0
                )
    actions = set(ton_session.scalars(select(TonAuditEvent.action)))
    assert "ton_sources.profile_create" in actions
    assert "ton_sources.profile_execute" in actions
    assert "ton_sources.profile_succeed" in actions
