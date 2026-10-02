"""Decision loop read models: evidence, decision log and run comparison."""

import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import decision_loop, dre, financial_domain, financial_readiness
from onyx.db.ton.enums import BusinessUnitKind
from onyx.db.ton.models import BusinessUnit
from onyx.file_store.file_store import FileStore
from onyx.ton.dre.models import (
    DreAssignmentApproval,
    DreLineDefinition,
    DreLineType,
    DreStructureCreate,
)
from onyx.ton.financial_domain.models import (
    AccountCreate,
    BudgetInput,
    MappingKind,
    NormalizationRequest,
)
from onyx.ton.financial_review.service import dataset_summary
from onyx.ton.operational_import.parser import BILLING_KEY, BUDGET_ANNUAL_KEY
from onyx.ton.sources.models import SourceFormat
from tests.external_dependency_unit.ton.test_financial_domain import (
    _map,
    _operational_execution,
)
from tests.external_dependency_unit.ton.test_financial_review import (
    Pipeline,
    book,
    launch,
)
from tests.unit.ton.test_operational_import_parser import (
    billing_book,
    budget_book,
    invoice,
)

pytest_plugins = ("tests.external_dependency_unit.ton.test_financial_domain",)

UNIT_KEY = "Synthetic administrative unit"


def _unresolved_scope(
    session: Session,
    admin: User,
    store: FileStore,
    day: datetime.date = datetime.date(2026, 1, 10),
) -> tuple[UUID, UUID, UUID, UUID]:
    """A base with one unmapped unit and an NG record no invoice matches."""
    pipeline = Pipeline(session, admin, store)
    execution_id = pipeline.parse(
        book(
            [
                launch(
                    "1.1 - Synthetic account",
                    day,
                    unit=UNIT_KEY,
                    document="101",
                    movement=100.25,
                )
            ]
        )
    )
    review = pipeline.review(execution_id)
    reviewed = dataset_summary(session, admin, pipeline.source_id, review.id)
    billing_source_id, billing_execution_id = _operational_execution(
        session,
        admin,
        store,
        key="billing_invoices",
        content=billing_book([invoice(number=999, gross=80)]),
        format=SourceFormat.XLS,
        profile_key=BILLING_KEY,
    )
    budget_source_id, budget_execution_id = _operational_execution(
        session,
        admin,
        store,
        key="budget",
        content=budget_book(),
        format=SourceFormat.XLSX,
        profile_key=BUDGET_ANNUAL_KEY,
    )
    account = financial_domain.create_account(
        session,
        admin,
        AccountCreate(
            code="SYN-LOOP", label="Synthetic revenue", dre_classification="REVENUE"
        ),
    )
    unit = BusinessUnit(
        code="SYN-LOOP-UNIT", name="Synthetic unit", kind=BusinessUnitKind.OPERATIONAL
    )
    session.add(unit)
    session.commit()
    _map(
        session,
        admin,
        pipeline.source_id,
        MappingKind.ACCOUNT,
        "1.1",
        account_id=account.id,
    )
    run = financial_domain.normalize(
        session,
        admin,
        NormalizationRequest(
            ng_source_id=pipeline.source_id,
            review_run_id=review.id,
            billing_source_id=billing_source_id,
            billing_execution_id=billing_execution_id,
            budgets=[
                BudgetInput(
                    source_id=budget_source_id, execution_id=budget_execution_id
                )
            ],
        ),
        reviewed.dataset_revision,
        reviewed.as_of,
    )
    version = dre.create_structure(
        session,
        admin,
        DreStructureCreate(
            key="synthetic-loop",
            label="Synthetic loop",
            lines=[
                DreLineDefinition(
                    code="service",
                    label="Service",
                    position=1,
                    line_type=DreLineType.SOURCE_SUM,
                )
            ],
        ),
    )
    session.commit()
    return run.id, version.id, pipeline.source_id, unit.id


def test_blockers_carry_source_records(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    run_id, version_id, _source_id, _unit_id = _unresolved_scope(
        ton_session, admin, store
    )
    units = financial_readiness.list_blockers(
        ton_session, admin, run_id, version_id, "UNMAPPED_UNIT", 10, 0, None
    )
    assert units.total == 1
    record = units.rows[0].records[0]
    assert record.origin == "NG"
    assert record.document == "101"
    assert record.unit == UNIT_KEY
    assert record.movement_amount == Decimal("100.25")
    assert record.row is not None

    reconciliation = financial_readiness.list_blockers(
        ton_session,
        admin,
        run_id,
        version_id,
        "SOURCE_RECONCILIATION_UNRESOLVED",
        10,
        0,
        None,
    )
    origins = {item.origin for row in reconciliation.rows for item in row.records}
    assert origins == {"NG", "BILLING"}
    billing = next(
        item
        for row in reconciliation.rows
        for item in row.records
        if item.origin == "BILLING"
    )
    assert billing.document == "999"
    assert billing.service_amount == Decimal("80")


def test_decision_is_pending_until_recompute_then_shows_consequence(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    first_id, version_id, source_id, unit_id = _unresolved_scope(
        ton_session, admin, store
    )
    initial = decision_loop.readiness_changes(
        ton_session, admin, first_id, version_id, None
    )
    assert initial.previous_run_id is None
    assert initial.pending_decisions == 0
    assert initial.periods[0].status_before is None
    assert initial.periods[0].blockers_after["UNMAPPED_UNIT"] == 1

    _map(
        ton_session,
        admin,
        source_id,
        MappingKind.UNIT,
        UNIT_KEY,
        unit_id=unit_id,
    )
    log = decision_loop.decision_log(ton_session, admin, 20)
    assert log.pending_decisions == 1
    latest = log.entries[0]
    assert latest.kind == "UNIT_MAPPING"
    assert latest.subject == UNIT_KEY
    assert latest.outcome == "SYN-LOOP-UNIT — Synthetic unit"
    assert latest.decided_by == admin.email
    assert latest.applied is False
    assert (
        decision_loop.readiness_changes(
            ton_session, admin, first_id, version_id, None
        ).pending_decisions
        == 1
    )

    first = financial_domain.get_run(ton_session, admin, first_id)
    second = financial_domain.normalize(
        ton_session,
        admin,
        financial_domain.normalization_request_for_run(ton_session, admin, first_id),
        first.dataset_revision,
        first.dataset_as_of,
    )
    assert second.id != first_id
    changes = decision_loop.readiness_changes(
        ton_session, admin, second.id, version_id, None
    )
    assert changes.previous_run_id == first_id
    assert changes.pending_decisions == 0
    assert changes.applied.mapping > changes.previous_applied.mapping  # type: ignore[union-attr]
    period = changes.periods[0]
    assert period.blockers_before["UNMAPPED_UNIT"] == 1
    assert "UNMAPPED_UNIT" not in period.blockers_after
    assert decision_loop.decision_log(ton_session, admin, 20).entries[0].applied

    # An unchanged recompute is idempotent and reports nothing new.
    again = financial_domain.normalize(
        ton_session,
        admin,
        financial_domain.normalization_request_for_run(ton_session, admin, second.id),
        second.dataset_revision,
        second.dataset_as_of,
    )
    assert again.id == second.id


def test_dre_classification_is_logged_by_account_and_line(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    _run_id, version_id, _source_id, _unit_id = _unresolved_scope(
        ton_session, admin, store
    )
    version = dre.get_version(ton_session, admin, version_id)
    account = financial_domain.list_accounts(ton_session, admin, 10, 0, "SYN-LOOP")[0]
    dre.approve_assignment(
        ton_session,
        admin,
        version.structure_id,
        DreAssignmentApproval(
            account_id=account.id,
            line_code="service",
            status="APPROVED",
            reason="Revenue belongs to service line",
        ),
    )
    ton_session.commit()
    entry = decision_loop.decision_log(ton_session, admin, 20).entries[0]
    assert entry.kind == "DRE_ASSIGNMENT"
    assert entry.subject == "SYN-LOOP — Synthetic revenue"
    assert entry.outcome == "Service"
    assert entry.version == 2
    assert entry.applied is True


def test_missing_actual_months_are_listed_for_year_to_date(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    run_id, version_id, _source_id, _unit_id = _unresolved_scope(
        ton_session, admin, store, datetime.date(2026, 3, 10)
    )
    readiness = financial_readiness.overview(
        ton_session, admin, run_id, version_id, None
    )
    assert readiness.periods[0].blockers["NO_ACTUAL"] == 2
    page = financial_readiness.list_blockers(
        ton_session, admin, run_id, version_id, "NO_ACTUAL", 10, 0, None
    )
    assert page.total == 2
    assert [row.periods for row in page.rows] == [
        [datetime.date(2026, 1, 1)],
        [datetime.date(2026, 2, 1)],
    ]
    assert page.covered_periods == [datetime.date(2026, 3, 1)]


def test_assistant_tool_reports_changes_and_decisions(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    from onyx.ton.agent.models import ToolQuery
    from onyx.ton.agent.service import query_domain
    from onyx.ton.financial_domain.readiness_models import RecentChanges

    _run_id, _version_id, source_id, unit_id = _unresolved_scope(
        ton_session, admin, store
    )
    _map(ton_session, admin, source_id, MappingKind.UNIT, UNIT_KEY, unit_id=unit_id)
    result = query_domain(ton_session, admin, "ton_get_recent_changes", ToolQuery())
    assert isinstance(result, RecentChanges)
    assert result.changes.pending_decisions == 1
    assert result.decisions.entries[0].kind == "UNIT_MAPPING"
    assert result.decisions.entries[0].applied is False
    actions = {item.blocker: item.action for item in result.required_actions}
    assert actions["SOURCE_RECONCILIATION_UNRESOLVED"] == "DECISION_IN_PENDING"
