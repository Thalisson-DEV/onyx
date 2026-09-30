"""DELIVERY-001 client import path with synthetic workbooks only."""

from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import sources
from onyx.db.ton.models import TonAuditEvent
from onyx.error_handling.exceptions import OnyxError, register_onyx_exception_handlers
from onyx.file_store.file_store import FileStore
from onyx.server.ton.client_import import router
from onyx.ton.client_import.models import ClientImportView
from onyx.ton.client_import.service import (
    get_client_import,
    list_client_sources,
    upload_client_source,
)
from onyx.ton.operational_import.parser import BUDGET_ANNUAL_KEY, BUDGET_TERM_KEY
from onyx.ton.sources.models import (
    ImportStatus,
    ImportTrigger,
    SourceCreate,
    SourceFormat,
)
from onyx.ton.sources.validation import MEDIA_TYPES
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import (
    scratch_database,
    scratch_session,
)
from tests.external_dependency_unit.ton.test_ng_financial_import import (
    synthetic_workbook,
)
from tests.unit.ton.test_operational_import_parser import (
    billing_book,
    budget_book,
    invoice,
)


@pytest.fixture
def importer(ton_session: Session) -> User:
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


def upload(
    session: Session,
    user: User,
    store: FileStore,
    key: str,
    content: bytes,
    format: SourceFormat,
) -> ClientImportView:
    return upload_client_source(
        session,
        user,
        key,
        BytesIO(content),
        f"synthetic.{format.value.lower()}",
        MEDIA_TYPES[format],
        store,
    )


def test_catalog_imports_history_and_detail(
    ton_session: Session, importer: User, store: FileStore
) -> None:
    catalog = list_client_sources(ton_session, importer)
    assert [source.key for source in catalog] == [
        "financial_launches",
        "billing_invoices",
        "budget",
    ]
    assert all(source.status == "UNCONFIGURED" for source in catalog)

    ng = upload(
        ton_session,
        importer,
        store,
        "financial_launches",
        synthetic_workbook(),
        SourceFormat.XLSX,
    )
    billing = upload(
        ton_session,
        importer,
        store,
        "billing_invoices",
        billing_book([invoice()]),
        SourceFormat.XLS,
    )
    budget = upload(
        ton_session,
        importer,
        store,
        "budget",
        budget_book(BUDGET_ANNUAL_KEY),
        SourceFormat.XLSX,
    )
    assert ng.imported > 0
    assert ng.available_for_analysis is not None
    assert billing.imported == 1
    assert budget.imported > 0
    assert budget.readiness_status == "UPDATED"
    assert budget.readiness_run_id is not None
    catalog = list_client_sources(ton_session, importer)
    assert all(source.source_id is not None for source in catalog)
    assert all(source.history for source in catalog)
    assert (
        get_client_import(ton_session, importer, "billing_invoices", billing.id).id
        == billing.id
    )
    assert ton_session.scalar(select(func.count()).select_from(TonAuditEvent)) > 0


def test_partial_and_both_budget_profiles(
    ton_session: Session, importer: User, store: FileStore
) -> None:
    partial = upload(
        ton_session,
        importer,
        store,
        "billing_invoices",
        billing_book([invoice(), invoice(gross="bad")]),
        SourceFormat.XLS,
    )
    assert partial.status == "PARTIAL"
    assert partial.imported == 1
    assert partial.rejected == 1
    assert partial.diagnostics
    second = upload(
        ton_session,
        importer,
        store,
        "budget",
        budget_book(BUDGET_TERM_KEY),
        SourceFormat.XLSX,
    )
    assert second.imported > 0


def test_partial_budget_does_not_use_stale_readiness(
    ton_session: Session, importer: User, store: FileStore
) -> None:
    upload(
        ton_session,
        importer,
        store,
        "financial_launches",
        synthetic_workbook(),
        SourceFormat.XLSX,
    )
    upload(
        ton_session,
        importer,
        store,
        "billing_invoices",
        billing_book([invoice()]),
        SourceFormat.XLS,
    )
    complete = upload(
        ton_session,
        importer,
        store,
        "budget",
        budget_book(BUDGET_ANNUAL_KEY),
        SourceFormat.XLSX,
    )
    assert complete.readiness_status == "UPDATED"
    partial = upload(
        ton_session,
        importer,
        store,
        "budget",
        budget_book(BUDGET_ANNUAL_KEY, malformed=True),
        SourceFormat.XLSX,
    )
    assert partial.status == "PARTIAL"
    assert partial.readiness_status == "PENDING_INPUTS"
    assert partial.readiness_run_id is None


def test_wrong_source_unsupported_file_and_isolation(
    ton_session: Session, importer: User, store: FileStore
) -> None:
    with pytest.raises(OnyxError):
        upload(
            ton_session,
            importer,
            store,
            "financial_launches",
            budget_book(),
            SourceFormat.XLSX,
        )
    with pytest.raises(OnyxError):
        upload(ton_session, importer, store, "budget", b"synthetic", SourceFormat.XLSX)
    sources.create_source(
        ton_session,
        importer,
        SourceCreate(
            key="budget",
            display_name="Synthetic inactive budget",
            acquisition_type="FILE_UPLOAD",
            status="INACTIVE",
        ),
    )
    ton_session.commit()
    with pytest.raises(OnyxError):
        upload(
            ton_session,
            importer,
            store,
            "budget",
            budget_book(),
            SourceFormat.XLSX,
        )
    result = upload(
        ton_session,
        importer,
        store,
        "billing_invoices",
        billing_book([invoice()]),
        SourceFormat.XLS,
    )
    outsider = factories.make_user(ton_session)
    ton_session.commit()
    assert all(
        source.source_id is None
        for source in list_client_sources(ton_session, outsider)
    )
    with pytest.raises(OnyxError):
        get_client_import(ton_session, outsider, "billing_invoices", result.id)
    with pytest.raises(OnyxError):
        upload(
            ton_session,
            outsider,
            store,
            "billing_invoices",
            billing_book([invoice()]),
            SourceFormat.XLS,
        )


def test_failed_capture_stays_in_history(
    ton_session: Session, importer: User, store: Mock
) -> None:
    store.save_file.side_effect = RuntimeError("synthetic storage failure")
    with pytest.raises(OnyxError):
        upload(
            ton_session,
            importer,
            store,
            "billing_invoices",
            billing_book([invoice()]),
            SourceFormat.XLS,
        )
    source = next(
        item
        for item in list_client_sources(ton_session, importer)
        if item.key == "billing_invoices"
    )
    assert source.status == "FAILED"
    assert source.latest is not None
    assert source.latest.failure_reason == "PROCESSING_ERROR"
    assert (
        get_client_import(
            ton_session, importer, "billing_invoices", source.latest.id
        ).status
        == "FAILED"
    )


def test_last_success_survives_history_limit(
    ton_session: Session, importer: User, store: FileStore
) -> None:
    result = upload(
        ton_session,
        importer,
        store,
        "billing_invoices",
        billing_book([invoice()]),
        SourceFormat.XLS,
    )
    for _ in range(21):
        run = sources.start_import_run(
            ton_session, importer, result.source_id, ImportTrigger.MANUAL_UPLOAD
        )
        sources.transition_run(run, ImportStatus.FAILED, "INVALID_INPUT")
    ton_session.commit()
    source = next(
        item
        for item in list_client_sources(ton_session, importer)
        if item.key == "billing_invoices"
    )
    assert len(source.history) == 20
    assert source.latest is not None
    assert source.latest.status == "FAILED"
    assert source.last_success_at == result.finished_at


def test_read_only_user_can_inspect_but_cannot_upload(
    ton_session: Session, importer: User, store: FileStore
) -> None:
    group = factories.make_group(ton_session)
    reader = factories.make_user(ton_session)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.READ_TON_SOURCES]
    )
    factories.add_member(ton_session, group=group, user=reader)
    sources.create_source(
        ton_session,
        importer,
        SourceCreate(
            key="billing_invoices",
            display_name="Synthetic billing",
            acquisition_type="FILE_UPLOAD",
            status="ACTIVE",
            group_ids=[group.id],
        ),
    )
    ton_session.commit()
    result = upload(
        ton_session,
        importer,
        store,
        "billing_invoices",
        billing_book([invoice()]),
        SourceFormat.XLS,
    )
    visible = next(
        item
        for item in list_client_sources(ton_session, reader)
        if item.key == "billing_invoices"
    )
    assert visible.source_id == result.source_id
    assert not visible.can_import
    assert (
        get_client_import(ton_session, reader, "billing_invoices", result.id).id
        == result.id
    )
    with pytest.raises(OnyxError):
        upload(
            ton_session,
            reader,
            store,
            "billing_invoices",
            billing_book([invoice()]),
            SourceFormat.XLS,
        )


def test_import_capable_group_user_can_process(
    ton_session: Session, importer: User, store: FileStore
) -> None:
    group = factories.make_group(ton_session)
    writer = factories.make_user(ton_session)
    factories.grant_permissions(
        ton_session,
        group=group,
        permissions=[Permission.READ_TON_SOURCES, Permission.IMPORT_TON_SOURCES],
    )
    factories.add_member(ton_session, group=group, user=writer)
    sources.create_source(
        ton_session,
        importer,
        SourceCreate(
            key="billing_invoices",
            display_name="Synthetic billing",
            acquisition_type="FILE_UPLOAD",
            status="ACTIVE",
            group_ids=[group.id],
        ),
    )
    ton_session.commit()
    visible = next(
        item
        for item in list_client_sources(ton_session, writer)
        if item.key == "billing_invoices"
    )
    assert visible.can_import
    result = upload(
        ton_session,
        writer,
        store,
        "billing_invoices",
        billing_book([invoice()]),
        SourceFormat.XLS,
    )
    assert result.status == "SUCCEEDED"
    assert result.imported == 1


def test_separate_tenant_database_does_not_expose_import(
    ton_session: Session,
    ton_head_template: str,
    importer: User,
    store: FileStore,
) -> None:
    result = upload(
        ton_session,
        importer,
        store,
        "billing_invoices",
        billing_book([invoice()]),
        SourceFormat.XLS,
    )
    with scratch_database(template=ton_head_template) as other_database:
        with scratch_session(other_database) as other_session:
            other_user = factories.make_user(other_session)
            other_group = factories.make_group(other_session)
            factories.grant_permissions(
                other_session,
                group=other_group,
                permissions=[Permission.FULL_ADMIN_PANEL_ACCESS],
            )
            factories.add_member(other_session, group=other_group, user=other_user)
            other_session.commit()
            assert all(
                item.source_id is None
                for item in list_client_sources(other_session, other_user)
            )
            with pytest.raises(OnyxError):
                get_client_import(
                    other_session, other_user, "billing_invoices", result.id
                )


def test_client_api_upload_history_and_detail(
    ton_session: Session, importer: User, store: FileStore
) -> None:
    app = FastAPI()
    app.include_router(router)
    register_onyx_exception_handlers(app)
    app.dependency_overrides[get_session] = lambda: ton_session
    for route in router.routes:
        assert isinstance(route, APIRoute)
        for dependency in route.dependant.dependencies:
            if dependency.name == "user":
                assert dependency.call is not None
                app.dependency_overrides[dependency.call] = lambda: importer
    with TestClient(app) as client:
        catalog = client.get("/ton/data-sources")
        assert catalog.status_code == 200
        assert len(catalog.json()) == 3
        with patch(
            "onyx.server.ton.client_import.get_default_file_store",
            return_value=store,
        ):
            response = client.post(
                "/ton/data-sources/billing_invoices/imports",
                files={
                    "file": (
                        "synthetic.xls",
                        billing_book([invoice()]),
                        MEDIA_TYPES[SourceFormat.XLS],
                    )
                },
            )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["imported"] == 1
        assert "storage_file_id" not in payload
        assert (
            client.get(
                f"/ton/data-sources/billing_invoices/imports/{payload['id']}"
            ).status_code
            == 200
        )
        history = client.get("/ton/data-sources").json()
        assert history[1]["history"][0]["id"] == payload["id"]
