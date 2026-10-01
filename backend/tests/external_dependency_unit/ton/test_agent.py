"""TON agent configuration and domain queries on disposable synthetic data."""

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.models import Persona, Tool, User
from onyx.db.ton import dre
from onyx.db.ton.agent import financial_context, provision_agent
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.agent.models import SourceToolStatus, ToolQuery
from onyx.ton.agent.service import query_domain
from onyx.ton.dre.models import DreScope, DreStructureCreate
from onyx.tools.tool_implementations.ton.ton_tool import TON_TOOL_CLASSES
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.test_dre import _lines
from tests.external_dependency_unit.ton.test_financial_domain import (
    build_complete_synthetic_scope,
)

pytest_plugins = ("tests.external_dependency_unit.ton.test_financial_domain",)


def test_provision_idempotent_and_denied(ton_session: Session, admin: User) -> None:
    first = provision_agent(ton_session, admin)
    second = provision_agent(ton_session, admin)
    assert first.id == second.id
    assert {tool.in_code_tool_id for tool in second.tools} == {
        tool.__name__ for tool in TON_TOOL_CLASSES
    }
    assert (
        ton_session.scalar(
            select(func.count()).select_from(Persona).where(Persona.name == "TON")
        )
        == 1
    )
    assert ton_session.scalar(
        select(func.count())
        .select_from(Tool)
        .where(Tool.in_code_tool_id.in_([tool.__name__ for tool in TON_TOOL_CLASSES]))
    ) == len(TON_TOOL_CLASSES)
    outsider = factories.make_user(ton_session)
    with pytest.raises(OnyxError):
        provision_agent(ton_session, outsider)
    with pytest.raises(OnyxError):
        query_domain(ton_session, outsider, "ton_list_sources", ToolQuery())


def test_tools_preserve_readiness_and_source_acl(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    normalization_id, _, unit_id = build_complete_synthetic_scope(
        ton_session, admin, store
    )
    version = dre.create_structure(
        ton_session,
        admin,
        DreStructureCreate(
            key="synthetic-agent-dre", label="Synthetic agent DRE", lines=_lines()
        ),
    )
    ton_session.commit()
    context = financial_context(ton_session, admin, 10, 0)
    base = next(
        item for item in context.bases if item.normalization_run_id == normalization_id
    )
    assert date(2026, 1, 1) in base.periods
    source = query_domain(
        ton_session, admin, "ton_get_source_status", ToolQuery(source_id=base.source_id)
    )
    assert isinstance(source, SourceToolStatus)
    assert base.review_run_id in source.review_run_ids
    assert source.executions
    readiness = query_domain(
        ton_session,
        admin,
        "ton_get_dre_readiness",
        ToolQuery(
            normalization_run_id=normalization_id,
            structure_version_id=version.id,
            period=date(2026, 1, 1),
            unit_id=unit_id,
        ),
    )
    assert readiness.model_dump()["status"] == "NOT_READY"
    blocked = dre.execute(
        ton_session,
        admin,
        DreScope(
            normalization_run_id=normalization_id,
            structure_version_id=version.id,
            period=date(2026, 1, 1),
            unit_id=unit_id,
        ),
    )
    result = query_domain(
        ton_session, admin, "ton_get_dre_result", ToolQuery(run_id=blocked.id)
    )
    assert not isinstance(result, list)
    assert result.model_dump()["status"] == "NOT_READY"
    outsider = factories.make_user(ton_session)
    group = factories.make_group(ton_session)
    from onyx.db.enums import Permission

    factories.add_member(ton_session, group=group, user=outsider)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.READ_TON_SOURCES]
    )
    ton_session.commit()
    with pytest.raises(OnyxError):
        query_domain(
            ton_session,
            outsider,
            "ton_get_source_status",
            ToolQuery(source_id=base.source_id),
        )
    assert financial_context(ton_session, outsider, 10, 0).bases == []
