"""DATA-001 contracts against migrated PostgreSQL and synthetic inputs."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from unittest.mock import Mock, patch
from uuid import UUID, uuid4
from zipfile import ZipFile

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import sources
from onyx.db.ton.models import SourceSnapshot, TonAuditEvent
from onyx.error_handling.exceptions import OnyxError, register_onyx_exception_handlers
from onyx.file_store.file_store import FileStore
from onyx.ton.sources.models import (
    AcquisitionType,
    ImportStatus,
    SnapshotView,
    SourceCreate,
    SourceFormat,
    SourceLocator,
    SourceStatus,
    SourceUpdate,
)
from onyx.ton.sources.service import (
    cleanup_failed_import,
    import_connected_json,
    import_file,
)
from onyx.ton.sources.validation import MEDIA_TYPES, validate_upload
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import (
    scratch_database,
    scratch_session,
    sync_engine,
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
    storage: dict[str, bytes] = {}
    result = Mock(spec=FileStore)

    def save(content: BytesIO, *, file_id: str, **_kwargs: object) -> str:
        assert file_id not in storage
        storage[file_id] = content.read()
        return file_id

    result.save_file.side_effect = save
    result.read_file.side_effect = lambda key: BytesIO(storage[key])
    result.delete_file.side_effect = lambda key, **_kwargs: storage.pop(key, None)
    return result


def create(session: Session, user: User, **kwargs: object) -> UUID:
    request = SourceCreate.model_validate(
        {
            "key": "synthetic_source",
            "display_name": "Synthetic source",
            "acquisition_type": "FILE_UPLOAD",
            "status": "ACTIVE",
            **kwargs,
        }
    )
    source = sources.create_source(session, user, request)
    session.commit()
    return source.id


def capture(
    session: Session,
    user: User,
    source_id: UUID,
    store: FileStore,
    content: bytes = b"column\nsynthetic\n",
) -> SnapshotView:
    return import_file(
        session, user, source_id, BytesIO(content), "synthetic.csv", "text/csv", store
    )


def test_capture_versions_lineage_audit(
    ton_session: Session,
    source_user: User,
    store: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source_id = create(ton_session, source_user)
    first = capture(ton_session, source_user, source_id, store)
    duplicate = capture(ton_session, source_user, source_id, store)
    changed = capture(ton_session, source_user, source_id, store, b"column\nchanged\n")
    assert first.checksum == hashlib.sha256(b"column\nsynthetic\n").hexdigest()
    assert duplicate.checksum == first.checksum
    assert duplicate.duplicate_of_id == first.id
    assert changed.checksum != first.checksum and changed.id != first.id
    assert changed.original_filename == first.original_filename
    assert changed.duplicate_of_id is None
    for snapshot in (first, duplicate, changed):
        run = sources.get_run(
            ton_session, source_user, source_id, snapshot.import_run_id
        )
        assert run.status == ImportStatus.SUCCEEDED and run.snapshot_count == 1
        assert run.finished_at is not None
    assert len(sources.list_snapshots(ton_session, source_user, source_id, 1, 1)) == 1
    assert len(sources.list_runs(ton_session, source_user, source_id, 2, 1)) == 2
    actions = set(ton_session.scalars(select(TonAuditEvent.action)))
    assert {
        "ton_sources.source_create",
        "ton_sources.import_start",
        "ton_sources.snapshot_capture",
        "ton_sources.import_succeed",
        "ton_sources.duplicate_detect",
    } <= actions
    assert "column\nsynthetic" not in caplog.text
    assert "storage_file_id" not in first.model_dump()


def test_identity_acquisition_status_pagination(
    ton_session: Session, source_user: User
) -> None:
    source_id = create(ton_session, source_user)
    request = SourceUpdate(
        display_name="Connected financial input",
        description=None,
        acquisition_type=AcquisitionType.API,
        status=SourceStatus.ACTIVE,
        sensitivity="RESTRICTED",
    )
    updated = sources.update_source(ton_session, source_user, source_id, request)
    ton_session.commit()
    assert updated.id == source_id and updated.key == "synthetic_source"
    assert sources.list_sources(ton_session, source_user, 1, 1) == []
    assert sources.list_sources(ton_session, source_user, 1, 0)[0].id == source_id
    with pytest.raises(OnyxError):
        sources.create_run(ton_session, source_user, source_id)
    zeev = create(ton_session, source_user, key="zeev", acquisition_type="API")
    assert (
        sources.get_source(ton_session, source_user, zeev).acquisition_type
        == AcquisitionType.API
    )
    with pytest.raises(OnyxError):
        sources.list_sources(ton_session, source_user, 101, 0)


@pytest.mark.parametrize("status", ["INACTIVE", "CONFIGURING", "ERROR"])
def test_disabled(ton_session: Session, source_user: User, status: str) -> None:
    source_id = create(ton_session, source_user, status=status)
    with pytest.raises(OnyxError):
        sources.create_run(ton_session, source_user, source_id)


def test_state_machine(ton_session: Session, source_user: User) -> None:
    source_id = create(ton_session, source_user)
    run = sources.create_run(ton_session, source_user, source_id)
    assert run.status == ImportStatus.PENDING
    with pytest.raises(OnyxError):
        sources.transition_run(run, ImportStatus.SUCCEEDED)
    sources.transition_run(run, ImportStatus.RUNNING)
    with pytest.raises(OnyxError):
        sources.transition_run(run, ImportStatus.SUCCEEDED)
    sources.transition_run(run, ImportStatus.FAILED, "SYNTHETIC_FAILURE")
    with pytest.raises(OnyxError):
        sources.transition_run(run, ImportStatus.RUNNING)


def test_snapshot_immutable_orm_and_sql(
    ton_session: Session, source_user: User, store: Mock
) -> None:
    source_id = create(ton_session, source_user)
    snapshot = capture(ton_session, source_user, source_id, store)
    row = ton_session.get(SourceSnapshot, snapshot.id)
    assert row
    row.checksum = "f" * 64
    with pytest.raises(ValueError, match="immutable"):
        ton_session.flush()
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(
            text("UPDATE ton_source_snapshot SET source_id = NULL WHERE id = :id"),
            {"id": snapshot.id},
        )
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(
            text("DELETE FROM ton_source_snapshot WHERE id = :id"), {"id": snapshot.id}
        )
    ton_session.rollback()


@pytest.mark.parametrize("failure", ["storage", "integrity", "database", "validation"])
def test_failure_cleanup(
    ton_session: Session, source_user: User, store: Mock, failure: str
) -> None:
    source_id = create(ton_session, source_user)
    if failure == "storage":
        store.save_file.side_effect = RuntimeError("sensitive driver detail")
    if failure == "integrity":
        store.read_file.side_effect = lambda _key: BytesIO(b"corrupted")
    with (
        patch.object(
            sources,
            "capture_snapshot",
            side_effect=RuntimeError("sensitive SQL detail"),
        )
        if failure == "database"
        else patch.object(sources, "capture_snapshot", wraps=sources.capture_snapshot)
    ):
        with pytest.raises(OnyxError) as error:
            capture(
                ton_session,
                source_user,
                source_id,
                store,
                b"\x00" if failure == "validation" else b"column\nsynthetic\n",
            )
    assert "sensitive" not in str(error.value)
    run = sources.list_runs(ton_session, source_user, source_id, 10, 0)[0]
    assert run.status == ImportStatus.FAILED and not run.cleanup_required
    assert sources.list_snapshots(ton_session, source_user, source_id, 10, 0) == []
    assert store.delete_file.called
    assert "ton_sources.import_fail" in set(
        ton_session.scalars(select(TonAuditEvent.action))
    )


def test_cleanup_retry(ton_session: Session, source_user: User, store: Mock) -> None:
    source_id = create(ton_session, source_user)
    store.save_file.side_effect = RuntimeError()
    store.delete_file.side_effect = RuntimeError()
    with pytest.raises(OnyxError):
        capture(ton_session, source_user, source_id, store)
    run = sources.list_runs(ton_session, source_user, source_id, 1, 0)[0]
    assert run.cleanup_required
    store.delete_file.side_effect = None
    assert not cleanup_failed_import(
        ton_session, source_user, source_id, run.id, store
    ).cleanup_required


@pytest.mark.parametrize("acknowledged", [False, True])
def test_commit_failure_preserves_storage_consistency(
    ton_session: Session, source_user: User, store: Mock, acknowledged: bool
) -> None:
    source_id = create(ton_session, source_user)
    commit = ton_session.commit
    calls = 0

    def fail_second_commit() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            if acknowledged:
                commit()
            raise RuntimeError("synthetic connection failure")
        commit()

    with patch.object(ton_session, "commit", side_effect=fail_second_commit):
        if acknowledged:
            assert capture(ton_session, source_user, source_id, store).id
        else:
            with pytest.raises(OnyxError):
                capture(ton_session, source_user, source_id, store)
    run = sources.list_runs(ton_session, source_user, source_id, 1, 0)[0]
    assert run.status == (
        ImportStatus.SUCCEEDED if acknowledged else ImportStatus.FAILED
    )
    assert store.delete_file.called != acknowledged


def test_source_acl(ton_session: Session, source_user: User, store: Mock) -> None:
    group = factories.make_group(ton_session)
    viewer = factories.make_user(ton_session)
    outsider = factories.make_user(ton_session)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.READ_TON_SOURCES]
    )
    factories.add_member(ton_session, group=group, user=viewer)
    source_id = create(ton_session, source_user, group_ids=[group.id])
    capture(ton_session, source_user, source_id, store)
    assert len(sources.list_sources(ton_session, viewer, 10, 0)) == 1
    assert len(sources.list_snapshots(ton_session, viewer, source_id, 10, 0)) == 1
    with pytest.raises(OnyxError):
        sources.create_run(ton_session, viewer, source_id)
    assert sources.list_sources(ton_session, outsider, 10, 0) == []
    with pytest.raises(OnyxError):
        sources.list_runs(ton_session, outsider, source_id, 10, 0)
    with pytest.raises(OnyxError):
        sources.list_snapshots(ton_session, outsider, source_id, 10, 0)


def test_api_validation(ton_session: Session, source_user: User, store: Mock) -> None:
    from onyx.db.engine.sql_engine import get_session
    from onyx.server.ton.sources import router

    app = FastAPI()
    app.include_router(router)
    register_onyx_exception_handlers(app)
    app.dependency_overrides[get_session] = lambda: ton_session
    for route in router.routes:
        assert isinstance(route, APIRoute)
        for dependency in route.dependant.dependencies:
            if dependency.name == "user":
                assert dependency.call is not None
                app.dependency_overrides[dependency.call] = lambda: source_user
    with TestClient(app) as client:
        assert client.get("/ton/sources?limit=101").status_code == 422
        assert client.post("/ton/sources", json={"key": "a.xlsx"}).status_code == 422
        response = client.post(
            "/ton/sources",
            json={
                "key": "api_source",
                "display_name": "Synthetic",
                "acquisition_type": "FILE_UPLOAD",
                "status": "ACTIVE",
            },
        )
        assert response.status_code == 200
        source_id = response.json()["id"]
        with patch(
            "onyx.server.ton.sources.get_default_file_store", return_value=store
        ):
            result = client.post(
                f"/ton/sources/{source_id}/imports",
                files={"file": ("synthetic.csv", b"a\n1\n", "text/csv")},
            )
        assert result.status_code == 200, result.text
        assert "storage_file_id" not in result.json()
        assert client.get(f"/ton/sources/{uuid4()}/runs").status_code == 404


def test_safe_xlsm_and_locator() -> None:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types><Override PartName="/xl/workbook.xml" ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml" /></Types>',
        )
        archive.writestr("xl/workbook.xml", "<workbook/>")
        archive.writestr("xl/vbaProject.bin", b"synthetic inert marker")
    content = output.getvalue()
    with patch("subprocess.run", side_effect=AssertionError("No execution permitted")):
        result = validate_upload(
            BytesIO(content), "synthetic.xlsm", MEDIA_TYPES[SourceFormat.XLSM]
        )
    assert result.content == content
    with pytest.raises(OnyxError):
        validate_upload(
            BytesIO(content), "synthetic.xlsx", MEDIA_TYPES[SourceFormat.XLSX]
        )
    locator = SourceLocator(snapshot_id=uuid4(), row_number=1, sheet_name="Synthetic")
    assert locator.row_number == 1


@pytest.mark.parametrize(
    ("filename", "media_type", "content"),
    [
        ("data.exe", "application/octet-stream", b"MZ"),
        ("data.csv", "application/pdf", b"a,b"),
        ("data.xlsx", MEDIA_TYPES[SourceFormat.XLSX], b"not zip"),
        ("data.pdf", "application/pdf", b"not pdf"),
        ("data.xls", MEDIA_TYPES[SourceFormat.XLS], b"not ole"),
        ("data.csv", "text/csv", b""),
        ("../data.csv", "text/csv", b"a"),
        ("data.csv", "text/csv", b"<script>alert(1)</script>"),
        ("data.json", "application/json", b"{}"),
    ],
)
def test_invalid_files(filename: str, media_type: str, content: bytes) -> None:
    with pytest.raises(OnyxError):
        validate_upload(BytesIO(content), filename, media_type)


def test_real_storage_and_concurrent_duplicates(
    ton_database: str, ton_session: Session, source_user: User
) -> None:
    from onyx.file_store.postgres_file_store import PostgresBackedFileStore

    source_id = create(ton_session, source_user)
    user_id = source_user.id

    def capture_in_session() -> SnapshotView:
        with scratch_session(ton_database) as session:
            user = session.get(User, user_id)
            assert user
            return capture(session, user, source_id, PostgresBackedFileStore())

    with patch(
        "onyx.file_store.postgres_file_store.get_session_with_current_tenant_if_none",
        side_effect=lambda _session: scratch_session(ton_database),
    ):
        with ThreadPoolExecutor(max_workers=2) as executor:
            first, second = list(executor.map(lambda _: capture_in_session(), range(2)))
        assert first.id != second.id and first.checksum == second.checksum
        assert (first.duplicate_of_id == second.id) != (
            second.duplicate_of_id == first.id
        )
        for snapshot in (first, second):
            row = ton_session.get(SourceSnapshot, snapshot.id)
            assert row and row.storage_file_id
            with PostgresBackedFileStore().read_file(row.storage_file_id) as content:
                assert hashlib.sha256(content.read()).hexdigest() == snapshot.checksum
            from onyx.access.access import user_can_access_chat_file

            assert not user_can_access_chat_file(
                row.storage_file_id, source_user, ton_session
            )


def test_cross_tenant_database_denial(
    ton_head_template: str, ton_session: Session, source_user: User, store: Mock
) -> None:
    source_id = create(ton_session, source_user)
    snapshot = capture(ton_session, source_user, source_id, store)
    with scratch_database(template=ton_head_template) as database:
        with scratch_session(database) as other:
            # Even the first tenant's administrator cannot resolve its IDs here.
            assert sources.list_sources(other, source_user, 10, 0) == []
            with pytest.raises(OnyxError):
                sources.get_source(other, source_user, source_id)
            with pytest.raises(OnyxError):
                sources.get_run(other, source_user, source_id, snapshot.import_run_id)
            with pytest.raises(OnyxError):
                sources.list_snapshots(other, source_user, source_id, 10, 0)
            with pytest.raises(OnyxError):
                capture(other, source_user, source_id, store)


def test_cross_tenant_schema_denial(
    ton_database: str, ton_session: Session, source_user: User, store: Mock
) -> None:
    source_id = create(ton_session, source_user)
    snapshot = capture(ton_session, source_user, source_id, store)
    # Empty tenant tables with the same migrated shape, without copying any rows.
    ton_session.execute(text("CREATE SCHEMA tenant_data001"))
    for table in ("ton_source", "ton_import_run", "ton_source_snapshot"):
        ton_session.execute(
            text(
                f"CREATE TABLE tenant_data001.{table} (LIKE public.{table} INCLUDING ALL)"
            )
        )
    ton_session.commit()
    engine = sync_engine(ton_database)
    try:
        with engine.connect().execution_options(
            schema_translate_map={None: "tenant_data001"}
        ) as connection:
            with Session(connection) as other:
                assert sources.list_sources(other, source_user, 10, 0) == []
                with pytest.raises(OnyxError):
                    sources.get_run(
                        other, source_user, source_id, snapshot.import_run_id
                    )
                with pytest.raises(OnyxError):
                    sources.list_snapshots(other, source_user, source_id, 10, 0)
    finally:
        engine.dispose()


def test_import_capability_is_separate_from_management(
    ton_session: Session, source_user: User, store: Mock
) -> None:
    group = factories.make_group(ton_session)
    importer = factories.make_user(ton_session)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.IMPORT_TON_SOURCES]
    )
    factories.add_member(ton_session, group=group, user=importer)
    source_id = create(ton_session, source_user, group_ids=[group.id])
    capture(ton_session, importer, source_id, store)
    with pytest.raises(OnyxError):
        sources.get_source(
            ton_session, importer, source_id, Permission.MANAGE_TON_SOURCES
        )
    hidden = create(ton_session, source_user, key="not_shared")
    with pytest.raises(OnyxError):
        capture(ton_session, importer, hidden, store)
    other_group = factories.make_group(ton_session)
    shared = create(
        ton_session, source_user, key="shared", group_ids=[group.id, other_group.id]
    )
    with pytest.raises(OnyxError):
        capture(ton_session, importer, shared, store)


def test_malformed_and_oversized_containers() -> None:
    from onyx.ton.sources.validation import MAX_UPLOAD_BYTES

    with pytest.raises(OnyxError):
        validate_upload(
            BytesIO(b"a" * (MAX_UPLOAD_BYTES + 1)), "synthetic.csv", "text/csv"
        )
    content = BytesIO()
    with ZipFile(content, "w") as archive:
        archive.writestr("../unsafe", "synthetic")
    with pytest.raises(OnyxError):
        validate_upload(
            BytesIO(content.getvalue()),
            "synthetic.xlsx",
            MEDIA_TYPES[SourceFormat.XLSX],
        )
    pdf = b"%PDF-1.4\n% synthetic metadata only\n%%EOF"
    assert (
        validate_upload(BytesIO(pdf), "synthetic.pdf", "application/pdf").content == pdf
    )


def test_source_key_cannot_be_changed_by_request() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SourceUpdate.model_validate(
            {
                "key": "changed",
                "display_name": "Synthetic",
                "acquisition_type": "API",
                "status": "ACTIVE",
                "sensitivity": "RESTRICTED",
            }
        )


def test_source_key_immutable_in_orm_and_database(
    ton_session: Session, source_user: User
) -> None:
    source_id = create(ton_session, source_user)
    source = sources.get_source(ton_session, source_user, source_id)
    source.key = "changed"
    with pytest.raises(ValueError, match="immutable"):
        ton_session.flush()
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(
            text("UPDATE ton_source SET key = 'changed' WHERE id = :id"),
            {"id": source_id},
        )
    ton_session.rollback()


def test_connected_snapshot_and_acquisition_switch(
    ton_session: Session, source_user: User, store: Mock
) -> None:
    source_id = create(ton_session, source_user)
    first = capture(ton_session, source_user, source_id, store)
    request = SourceUpdate(
        display_name="Connected input",
        description=None,
        acquisition_type=AcquisitionType.DATABASE,
        status=SourceStatus.ACTIVE,
        sensitivity="RESTRICTED",
    )
    sources.update_source(ton_session, source_user, source_id, request)
    ton_session.commit()
    with pytest.raises(OnyxError):
        capture(ton_session, source_user, source_id, store)
    raw_json = b'{"synthetic_record": 1}'
    second = import_connected_json(
        ton_session, source_user, source_id, BytesIO(raw_json), store
    )
    assert second.source_id == first.source_id and second.format == SourceFormat.JSON
    assert second.checksum == hashlib.sha256(raw_json).hexdigest()
    assert (
        sources.get_run(
            ton_session, source_user, source_id, second.import_run_id
        ).trigger
        == "API_SYNC"
    )
    row = ton_session.get(SourceSnapshot, second.id)
    assert row and row.source_type.value == "API_PAYLOAD"
    zeev = create(ton_session, source_user, key="zeev", acquisition_type="API")
    assert (
        import_connected_json(
            ton_session, source_user, zeev, BytesIO(b"[]"), store
        ).format
        == SourceFormat.JSON
    )


def test_invalid_connected_payload(
    ton_session: Session, source_user: User, store: Mock
) -> None:
    source_id = create(ton_session, source_user, acquisition_type="API")
    with pytest.raises(OnyxError):
        import_connected_json(
            ton_session, source_user, source_id, BytesIO(b"<html>"), store
        )
    assert (
        sources.list_runs(ton_session, source_user, source_id, 10, 0)[0].status
        == ImportStatus.FAILED
    )
