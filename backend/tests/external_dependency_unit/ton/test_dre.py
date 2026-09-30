"""Synthetic DRE persistence, readiness, ACL, and immutable revisions."""

import datetime
import time
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import dre as repository
from onyx.db.ton.models import DreCalculationRun, DreResultLine, TonAuditEvent
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.server.ton.dre import calculate as calculate_route
from onyx.ton.dre.models import (
    DreAccountAssignment,
    DreLineDefinition,
    DreLineType,
    DreOperation,
    DreScope,
    DreStructureCreate,
    DreVersionCreate,
)
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.test_financial_domain import (
    build_complete_synthetic_scope,
)

pytest_plugins = ("tests.external_dependency_unit.ton.test_financial_domain",)


def _lines() -> list[DreLineDefinition]:
    return [
        DreLineDefinition(
            code="gross",
            label="Gross revenue",
            position=1,
            line_type=DreLineType.SUBTOTAL,
            operation=DreOperation.SUM_CHILDREN,
        ),
        DreLineDefinition(
            code="service",
            label="Service",
            position=2,
            parent_code="gross",
            line_type=DreLineType.SOURCE_SUM,
        ),
        DreLineDefinition(
            code="cost",
            label="Cost",
            position=3,
            line_type=DreLineType.SOURCE_SUM,
        ),
        DreLineDefinition(
            code="result",
            label="Result",
            position=4,
            line_type=DreLineType.RESULT,
            operation=DreOperation.SUBTRACT,
            operands=["gross", "cost"],
        ),
    ]


def test_synthetic_ready_revision_and_mapping_governance(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    normalization_id, account_id, unit_id = build_complete_synthetic_scope(
        ton_session, admin, store
    )
    first_version = repository.create_structure(
        ton_session,
        admin,
        DreStructureCreate(
            key="synthetic-dre",
            label="Synthetic DRE",
            lines=_lines(),
        ),
    )
    ton_session.commit()
    assert (
        repository.get_structure(
            ton_session, admin, first_version.structure_id
        ).latest_version
        == 1
    )
    scope = DreScope(
        normalization_run_id=normalization_id,
        structure_version_id=first_version.id,
        period=datetime.date(2026, 1, 1),
        unit_id=unit_id,
    )
    initial = repository.readiness(ton_session, admin, scope)
    assert initial.status == "NOT_READY"
    assert initial.blockers["DRE_ACCOUNT_UNMAPPED"] >= 1
    blocked = repository.execute(ton_session, admin, scope)
    assert blocked.status == "NOT_READY"
    assert repository.list_result_lines(ton_session, admin, blocked.id, 10, 0) == []

    pending = repository.create_version(
        ton_session,
        admin,
        first_version.structure_id,
        DreVersionCreate(
            lines=_lines(),
            assignments=[
                DreAccountAssignment(
                    account_id=account_id,
                    line_code="service",
                    status="PENDING_APPROVAL",
                )
            ],
        ),
    )
    ton_session.commit()
    scope.structure_version_id = pending.id
    assert (
        repository.readiness(ton_session, admin, scope).blockers[
            "DRE_MAPPING_PENDING_APPROVAL"
        ]
        >= 1
    )

    approved = repository.create_version(
        ton_session,
        admin,
        first_version.structure_id,
        DreVersionCreate(
            lines=_lines(),
            assignments=[
                DreAccountAssignment(
                    account_id=account_id, line_code="service", status="APPROVED"
                )
            ],
        ),
    )
    ton_session.commit()
    scope.structure_version_id = approved.id
    assert repository.readiness(ton_session, admin, scope).status == "READY"
    started = time.perf_counter()
    ready = repository.execute(ton_session, admin, scope)
    print("synthetic_dre_execute_ms", round((time.perf_counter() - started) * 1000))
    assert ready.status == "READY"
    assert repository.execute(ton_session, admin, scope).id == ready.id
    lines = repository.list_result_lines(ton_session, admin, ready.id, 10, 0)
    by_code = {line.code: line for line in lines}
    assert len(lines) == 4
    assert by_code["service"].realizado == Decimal("100.25")
    assert by_code["gross"].realizado == by_code["service"].realizado
    assert by_code["result"].realizado == Decimal("100.25")
    assert by_code["result"].orcado == by_code["service"].orcado
    assert by_code["result"].variance == (
        by_code["result"].realizado - by_code["result"].orcado
    )
    assert by_code["service"].realizado_ytd == Decimal("100.25")
    assert ready.provenance["normalization_run_id"] == str(normalization_id)
    assert ready.provenance["dre_structure_version_id"] == str(approved.id)
    assert ready.provenance["budget_execution_ids"]
    assert ready.provenance["ng_source_snapshot_id"]
    assert ready.id != blocked.id

    renamed_lines = _lines()
    renamed_lines[1].label = "Renamed service"
    renamed = repository.create_version(
        ton_session,
        admin,
        first_version.structure_id,
        DreVersionCreate(
            lines=renamed_lines,
            assignments=[
                DreAccountAssignment(
                    account_id=account_id, line_code="service", status="APPROVED"
                )
            ],
        ),
    )
    ton_session.commit()
    scope.structure_version_id = renamed.id
    renamed_run = repository.execute(ton_session, admin, scope)
    assert renamed_run.id != ready.id
    assert (
        repository.get_structure(
            ton_session, admin, first_version.structure_id
        ).latest_version
        == renamed.number
    )
    assert (
        repository.list_result_lines(ton_session, admin, ready.id, 10, 0)[1].label
        == "Service"
    )
    assert (
        repository.list_result_lines(ton_session, admin, renamed_run.id, 10, 0)[1].label
        == "Renamed service"
    )

    zero_ratio_lines = _lines()
    zero_ratio_lines.append(
        DreLineDefinition(
            code="ratio",
            label="Ratio",
            position=5,
            line_type=DreLineType.PERCENTAGE,
            operation=DreOperation.RATIO,
            operands=["gross", "cost"],
        )
    )
    zero_ratio = repository.create_version(
        ton_session,
        admin,
        first_version.structure_id,
        DreVersionCreate(
            lines=zero_ratio_lines,
            assignments=[
                DreAccountAssignment(
                    account_id=account_id, line_code="service", status="APPROVED"
                )
            ],
        ),
    )
    ton_session.commit()
    scope.structure_version_id = zero_ratio.id
    assert (
        repository.readiness(ton_session, admin, scope).blockers[
            "FORMULA_DENOMINATOR_ZERO"
        ]
        == 1
    )
    assert repository.execute(ton_session, admin, scope).status == "NOT_READY"

    with pytest.raises(OnyxError):
        calculate_route(
            DreScope(
                normalization_run_id=normalization_id,
                structure_version_id=approved.id,
                period=datetime.date(2026, 1, 2),
                unit_id=unit_id,
            ),
            admin,
            ton_session,
        )

    audit = list(
        ton_session.scalars(
            select(TonAuditEvent).where(TonAuditEvent.action.like("ton_dre.%"))
        )
    )
    assert audit
    assert any(item.action == "ton_dre.calculate_fail" for item in audit)
    assert all(item.before_state is None and item.after_state is None for item in audit)
    outsider = factories.make_user(ton_session)
    ton_session.commit()
    with pytest.raises(OnyxError):
        repository.get_calculation(ton_session, outsider, ready.id)
    with pytest.raises(DBAPIError):
        ton_session.execute(
            text("UPDATE ton_dre_result_line SET realizado = 0 WHERE run_id = :id"),
            {"id": ready.id},
        )
    ton_session.rollback()
    assert (
        ton_session.scalar(
            select(DreResultLine).where(DreResultLine.run_id == ready.id)
        )
        is not None
    )
    assert ton_session.get(DreCalculationRun, blocked.id) is not None


def test_invalid_structure_dependencies_rejected(
    ton_session: Session, admin: User
) -> None:
    with pytest.raises(OnyxError):
        repository.create_structure(
            ton_session,
            admin,
            DreStructureCreate(
                key="invalid",
                label="Invalid",
                lines=[
                    DreLineDefinition(
                        code="total",
                        label="Total",
                        position=1,
                        line_type=DreLineType.RESULT,
                        operation=DreOperation.SUM_LINES,
                        operands=["missing"],
                    )
                ],
            ),
        )
