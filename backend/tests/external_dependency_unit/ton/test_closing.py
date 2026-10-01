"""Persisted specialist closing on synthetic, disposable financial inputs."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.permissions import recompute_user_permissions__no_commit
from onyx.db.ton import dre, reports
from onyx.db.ton.acl import report_group_ids
from onyx.db.ton.closing import analyze_closing, execute_closing, read_publication
from onyx.db.ton.enums import AnalysisStepStatus, AnalysisTrigger
from onyx.db.ton.models import (
    AnalysisRun,
    AnalysisStep,
    BusinessUnit__UserGroup,
    Source,
    Source__UserGroup,
    TonAuditEvent,
    TonReport,
)
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.agent.closing_models import ClosingRequest
from onyx.ton.agent.rendering import render_markdown
from onyx.ton.dre.models import DreStructureCreate
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.test_dre import _lines
from tests.external_dependency_unit.ton.test_financial_domain import (
    build_complete_synthetic_scope,
)

pytest_plugins = ("tests.external_dependency_unit.ton.test_financial_domain",)


def test_interactive_analysis_records_steps_without_report_permission(
    ton_session: Session,
) -> None:
    reader = factories.make_user(ton_session)
    group = factories.make_group(ton_session)
    factories.add_member(ton_session, group=group, user=reader)
    factories.grant_permissions(
        ton_session,
        group=group,
        permissions=[Permission.READ_TON_SOURCES, Permission.READ_TON_OCCURRENCES],
    )
    recompute_user_permissions__no_commit(reader.id, ton_session)
    ton_session.refresh(reader)
    ton_session.commit()
    result = analyze_closing(
        ton_session, reader, ClosingRequest(request_id=uuid4(), period=date(2026, 1, 1))
    )
    run = ton_session.get(AnalysisRun, result.run_id)
    assert run is not None and run.trigger == AnalysisTrigger.INTERACTIVE
    assert run.triggered_by_user_id == reader.id
    assert len(result.steps) == 21
    assert any(
        step["specialist"] == "CEO" and step["status"] == "Concluído"
        for step in result.steps
    )
    assert ton_session.scalar(select(func.count()).select_from(TonReport)) == 0
    with pytest.raises(OnyxError):
        execute_closing(ton_session, reader, ClosingRequest(request_id=uuid4()))


def test_r3_blocked_finance_keeps_audit_and_publication(
    ton_session: Session, admin: User, store: FileStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TON_DEMO_SYNTHETIC_DATA", "true")
    normalization_id, _, unit_id = build_complete_synthetic_scope(
        ton_session, admin, store
    )
    version = dre.create_structure(
        ton_session,
        admin,
        DreStructureCreate(
            key="synthetic-closing", label="Synthetic closing", lines=_lines()
        ),
    )
    ton_session.commit()
    request = ClosingRequest(
        request_id=uuid4(),
        normalization_run_id=normalization_id,
        structure_version_id=version.id,
        period=date(2026, 1, 1),
        unit_id=unit_id,
    )
    first = execute_closing(
        ton_session,
        admin,
        request,
        trigger=AnalysisTrigger.MANUAL_REPLAY,
        routine_code="R3",
    )
    repeated = execute_closing(
        ton_session,
        admin,
        request,
        trigger=AnalysisTrigger.MANUAL_REPLAY,
        routine_code="R3",
    )
    assert first.revision_id == repeated.revision_id
    assert first.output.dre_status == "Pendente"
    assert first.output.blockers
    assert "sintéticos" in first.output.data_context
    assert {item.key for item in first.output.specialists} == {
        "CFO",
        "AUDITOR",
        "CEO",
        "COO",
        "FLEET",
        "CONTRACTS",
        "COMPLIANCE",
        "PROCUREMENT",
        "HR",
    }
    assert (
        next(item for item in first.output.specialists if item.key == "CFO").status
        == "Parcial"
    )
    assert (
        next(item for item in first.output.specialists if item.key == "AUDITOR").status
        == "Operacional"
    )
    assert (
        next(item for item in first.output.specialists if item.key == "CEO").facts
        == first.output.executive_brief
    )
    assert any(
        item["specialist"] == "CFO" and item["status"] == "Bloqueado"
        for item in first.steps
    )
    assert any(
        item["specialist"] == "AUDITOR" and item["status"] == "Concluído"
        for item in first.steps
    )
    assert any(
        item["status"] == "Não executado" and item["reason"] for item in first.steps
    )
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(AnalysisStep)
            .where(AnalysisStep.analysis_run_id == first.run_id)
        )
        == 21
    )
    assert ton_session.get(AnalysisRun, first.run_id).routine_code == "R3"
    revision = reports.latest_revision(ton_session, first.report_id)
    assert reports.verify_revision_hash(revision)
    assert reports.pinned_inputs(
        ton_session, revision_id=revision.id
    ).source_snapshot_ids
    ton_session.expire_all()
    restored = read_publication(ton_session, admin, first.revision_id)
    assert restored.output == first.output
    assert restored.run_id == first.run_id
    document = render_markdown(restored)
    assert "sintéticos" in document
    assert "Concluído com bloqueios" in document
    assert "NOT_READY" not in document
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(TonAuditEvent)
            .where(TonAuditEvent.resource_id == first.revision_id)
        )
        == 1
    )
    outsider = factories.make_user(ton_session)
    with pytest.raises(OnyxError):
        read_publication(ton_session, outsider, first.revision_id)
    with pytest.raises(OnyxError):
        execute_closing(ton_session, outsider, request)


def test_no_base_publishes_explicit_gaps(ton_session: Session, admin: User) -> None:
    result = execute_closing(
        ton_session,
        admin,
        ClosingRequest(request_id=uuid4(), period=date(2026, 1, 1), executive=True),
    )
    assert result.output.normalization_run_id is None
    assert result.output.dre_status == "Não verificada"
    assert result.output.findings == []
    assert "Não quantificado" in result.output.executive_brief["IMPACTO"]
    assert result.status == "Concluído com bloqueios"
    assert "Nenhum achado retornado" in render_markdown(result)
    assert ton_session.get(TonReport, result.report_id).title == "Resumo executivo"
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(AnalysisStep)
            .where(
                AnalysisStep.analysis_run_id == result.run_id,
                AnalysisStep.status == AnalysisStepStatus.PENDING,
            )
        )
        == 0
    )


def test_scoped_publisher_cannot_share_outside_all_input_groups(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    normalization_id, _, unit_id = build_complete_synthetic_scope(
        ton_session, admin, store
    )
    version = dre.create_structure(
        ton_session,
        admin,
        DreStructureCreate(
            key="synthetic-scoped-closing",
            label="Synthetic scoped closing",
            lines=_lines(),
        ),
    )
    publisher = factories.make_user(ton_session)
    authorized = factories.make_group(ton_session)
    unrelated = factories.make_group(ton_session)
    factories.add_member(ton_session, group=authorized, user=publisher)
    factories.add_member(ton_session, group=unrelated, user=publisher)
    factories.grant_permissions(
        ton_session,
        group=authorized,
        permissions=[
            Permission.READ_TON_SOURCES,
            Permission.READ_TON_OCCURRENCES,
            Permission.READ_TON_REPORTS,
            Permission.MANAGE_TON_REPORTS,
        ],
    )
    for source in ton_session.scalars(select(Source)):
        ton_session.add(
            Source__UserGroup(source_id=source.id, user_group_id=authorized.id)
        )
    ton_session.add(
        BusinessUnit__UserGroup(business_unit_id=unit_id, user_group_id=authorized.id)
    )
    recompute_user_permissions__no_commit(publisher.id, ton_session)
    ton_session.refresh(publisher)
    ton_session.commit()
    result = execute_closing(
        ton_session,
        publisher,
        ClosingRequest(
            request_id=uuid4(),
            normalization_run_id=normalization_id,
            structure_version_id=version.id,
            unit_id=unit_id,
            period=date(2026, 1, 1),
        ),
    )
    assert report_group_ids(ton_session, result.report_id) == {authorized.id}
    assert (
        read_publication(ton_session, publisher, result.revision_id).revision_id
        == result.revision_id
    )
    outsider = factories.make_user(ton_session)
    factories.add_member(ton_session, group=unrelated, user=outsider)
    factories.grant_permissions(
        ton_session, group=unrelated, permissions=[Permission.READ_TON_REPORTS]
    )
    recompute_user_permissions__no_commit(outsider.id, ton_session)
    ton_session.refresh(outsider)
    ton_session.commit()
    with pytest.raises(OnyxError):
        read_publication(ton_session, outsider, result.revision_id)
    ton_session.execute(
        delete(BusinessUnit__UserGroup).where(
            BusinessUnit__UserGroup.business_unit_id == unit_id,
            BusinessUnit__UserGroup.user_group_id == authorized.id,
        )
    )
    ton_session.commit()
    with pytest.raises(OnyxError):
        read_publication(ton_session, publisher, result.revision_id)
