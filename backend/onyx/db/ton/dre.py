"""Persistence and authorization for DATA-005 DRE versions and results."""

import dataclasses
import datetime
import hashlib
import json
from collections import Counter, defaultdict
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from uuid import UUID
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import financial_domain
from onyx.db.ton.acl import business_unit_visible_clause, is_ton_administrator
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.closing_treatments import versions_in_force
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import (
    BusinessUnit,
    ClosingTreatment,
    DreAccountMapping,
    DreCalculationRun,
    DreResultLine,
    DreStructure,
    DreStructureVersion,
    FinancialAccount,
    FinancialActualFact,
    FinancialBudgetFact,
    FinancialNormalizationRun,
    ImportProfileExecution,
    OperationalSourceRecord,
    ParsedSourceRecord,
    ReviewRun,
    Source,
    SourceSnapshot,
)
from onyx.db.ton.sources import check_page, get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.dre.engine import ENGINE_VERSION, calculate, calculation_order
from onyx.ton.dre.models import (
    DreAccountAssignment,
    DreAssignmentApproval,
    DreContributorPage,
    DreContributorView,
    DreLineDefinition,
    DreLineType,
    DreOperation,
    DrePeriodPoint,
    DreReadinessView,
    DreResultLineView,
    DreRunView,
    DreScope,
    DreStatementView,
    DreStructureCreate,
    DreStructureView,
    DreVersionCreate,
    DreVersionView,
)
from onyx.ton.dre.xlsx_export import (
    BaseEntry,
    DreWorkbookInput,
    Premise,
    ScopeBlock,
    build_workbook,
    expected_values,
    month_label,
)
from onyx.ton.financial_domain.models import DreInputDataset
from onyx.utils.audit import AuditAction, AuditOutcome

RESULT_SCALE = Decimal("1e-25")
SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def _require_admin(user: User) -> None:
    if not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "DRE configuration requires admin access"
        )


def _version_view(session: Session, version: DreStructureVersion) -> DreVersionView:
    assignments = list(
        session.scalars(
            sa.select(DreAccountMapping)
            .where(DreAccountMapping.version_id == version.id)
            .order_by(DreAccountMapping.account_id)
        )
    )
    return DreVersionView(
        id=version.id,
        structure_id=version.structure_id,
        number=version.number,
        lines=[DreLineDefinition.model_validate(item) for item in version.lines],
        assignments=[
            {
                "account_id": item.account_id,
                "line_code": item.line_code,
                "status": item.status,
            }
            for item in assignments
        ],
        created_at=version.created_at,
    )


def _create_version(
    session: Session,
    user: User,
    structure: DreStructure,
    number: int,
    request: DreVersionCreate,
) -> DreVersionView:
    try:
        calculation_order(request.lines)
    except ValueError as error:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, str(error)) from error
    source_lines = {
        item.code for item in request.lines if item.line_type == DreLineType.SOURCE_SUM
    }
    account_ids = [item.account_id for item in request.assignments]
    if len(account_ids) != len(set(account_ids)) or any(
        item.line_code not in source_lines for item in request.assignments
    ):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid DRE account assignment")
    found = set(
        session.scalars(
            sa.select(FinancialAccount.id).where(FinancialAccount.id.in_(account_ids))
        )
    )
    if found != set(account_ids):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Unknown DRE account")
    version = DreStructureVersion(
        structure_id=structure.id,
        number=number,
        lines=[item.model_dump(mode="json") for item in request.lines],
        created_by=user.id,
        reason=request.reason,
    )
    session.add(version)
    session.flush()
    session.add_all(
        DreAccountMapping(
            version_id=version.id,
            account_id=item.account_id,
            line_code=item.line_code,
            status=item.status,
        )
        for item in request.assignments
    )
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_DRE_STRUCTURE_VERSION,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.DRE_STRUCTURE_VERSION,
        resource_id=version.id,
    )
    return _version_view(session, version)


def create_structure(
    session: Session, user: User, request: DreStructureCreate
) -> DreVersionView:
    _require_admin(user)
    if session.scalar(
        sa.select(DreStructure.id).where(DreStructure.key == request.key)
    ):
        raise OnyxError(OnyxErrorCode.CONFLICT, "DRE structure key exists")
    structure = DreStructure(key=request.key, label=request.label)
    session.add(structure)
    session.flush()
    return _create_version(session, user, structure, 1, request)


def create_version(
    session: Session, user: User, structure_id: UUID, request: DreVersionCreate
) -> DreVersionView:
    _require_admin(user)
    session.execute(sa.text("SELECT pg_advisory_xact_lock(4433006)"))
    structure = session.get(DreStructure, structure_id)
    if structure is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "DRE structure not found")
    latest = session.scalar(
        sa.select(sa.func.max(DreStructureVersion.number)).where(
            DreStructureVersion.structure_id == structure_id
        )
    )
    return _create_version(session, user, structure, int(latest or 0) + 1, request)


def approve_assignment(
    session: Session, user: User, structure_id: UUID, request: DreAssignmentApproval
) -> DreVersionView:
    _require_admin(user)
    structure = get_structure(session, user, structure_id)
    version = session.scalar(
        sa.select(DreStructureVersion)
        .where(DreStructureVersion.structure_id == structure.id)
        .order_by(DreStructureVersion.number.desc())
        .limit(1)
    )
    assert version is not None
    current = _version_view(session, version)
    assignments = [
        item for item in current.assignments if item.account_id != request.account_id
    ]
    assignments.append(
        DreAccountAssignment(
            account_id=request.account_id,
            line_code=request.line_code,
            status=request.status,
        )
    )
    return create_version(
        session,
        user,
        structure_id,
        DreVersionCreate(
            lines=current.lines, assignments=assignments, reason=request.reason
        ),
    )


def list_structures(
    session: Session, _user: User, limit: int, offset: int
) -> list[DreStructureView]:
    check_page(limit, offset)
    rows = session.execute(
        sa.select(DreStructure, sa.func.max(DreStructureVersion.number))
        .join(DreStructureVersion)
        .group_by(DreStructure.id)
        .order_by(DreStructure.key)
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        DreStructureView(
            id=structure.id,
            key=structure.key,
            label=structure.label,
            latest_version=number,
        )
        for structure, number in rows
    ]


def get_structure(
    session: Session, _user: User, structure_id: UUID
) -> DreStructureView:
    structure = session.get(DreStructure, structure_id)
    if structure is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "DRE structure not found")
    number = session.scalar(
        sa.select(sa.func.max(DreStructureVersion.number)).where(
            DreStructureVersion.structure_id == structure_id
        )
    )
    return DreStructureView(
        id=structure.id,
        key=structure.key,
        label=structure.label,
        latest_version=int(number or 0),
    )


def get_version(session: Session, _user: User, version_id: UUID) -> DreVersionView:
    version = session.get(DreStructureVersion, version_id)
    if version is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "DRE version not found")
    return _version_view(session, version)


def get_latest_version(
    session: Session, user: User, structure_id: UUID
) -> DreVersionView:
    get_structure(session, user, structure_id)
    version = session.scalar(
        sa.select(DreStructureVersion)
        .where(DreStructureVersion.structure_id == structure_id)
        .order_by(DreStructureVersion.number.desc())
        .limit(1)
    )
    assert version is not None
    return _version_view(session, version)


def _inputs(
    session: Session, user: User, scope: DreScope, *, write: bool
) -> tuple[DreVersionView, FinancialNormalizationRun, list[DreInputDataset]]:
    run = financial_domain.get_run(session, user, scope.normalization_run_id)
    version_row = session.get(DreStructureVersion, scope.structure_version_id)
    if version_row is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "DRE version not found")
    version = _version_view(session, version_row)
    if run.status != "SUCCEEDED":
        raise OnyxError(OnyxErrorCode.CONFLICT, "Normalization did not succeed")
    if scope.period.day != 1:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Period must start on day one")
    if scope.unit_id is not None:
        unit = session.scalar(
            sa.select(BusinessUnit.id).where(
                BusinessUnit.id == scope.unit_id, business_unit_visible_clause(user)
            )
        )
        if unit is None:
            raise OnyxError(OnyxErrorCode.NOT_FOUND, "Business unit not found")
    elif not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "Consolidated DRE requires admin access"
        )
    if write:
        permission = Permission.IMPORT_TON_SOURCES
        review = session.get(ReviewRun, run.review_run_id)
        assert review is not None
        get_source(session, user, review.source_id, permission)
        for execution_id in [
            run.billing_execution_id,
            *(UUID(item) for item in run.budget_execution_ids),
        ]:
            execution = session.get(ImportProfileExecution, execution_id)
            assert execution is not None
            get_source(session, user, execution.source_id, permission)
    datasets = [
        financial_domain.load_dre_input_dataset(
            session,
            user,
            scope.normalization_run_id,
            datetime.date(scope.period.year, month, 1),
            scope.unit_id,
        )
        for month in range(1, scope.period.month + 1)
    ]
    return version, run, datasets


def _blockers(
    version: DreVersionView,
    normalization: FinancialNormalizationRun,
    datasets: list[DreInputDataset],
    unit_id: UUID | None,
) -> dict[str, int]:
    mapping = {item.account_id: item for item in version.assignments}
    blockers: Counter[str] = Counter()
    global_keys = {
        "BUDGET_UNMAPPED_ACCOUNT",
        "BUDGET_UNMAPPED_UNIT",
        "BUDGET_PERIOD_UNRESOLVED",
        "REVIEW_UNRESOLVED",
        "EXCLUDED_SOURCE_ROWS",
    }
    # The DRE reads NG actuals and budgets only. Billing-derived facts never
    # enter it, so their derivation gaps stay in Financial Readiness.
    billing_derivation_keys = {
        "BILLING_COMPETENCE_UNRESOLVED",
        "UNSUPPORTED_DERIVATION",
        "IR_RETENTION_UNRESOLVED",
    }
    if datasets:
        blockers.update(
            {
                key: value
                for key, value in datasets[0].readiness.blockers.items()
                if key in global_keys
            }
        )
    for dataset in datasets:
        blockers.update(
            {
                key: value
                for key, value in dataset.readiness.blockers.items()
                if key not in global_keys
                and key not in billing_derivation_keys
                and key != "UNCLASSIFIED_ACCOUNT"
            }
        )
        for fact in [*dataset.actuals, *dataset.budgets]:
            if fact.account_id is None:
                continue
            assignment = mapping.get(fact.account_id)
            if assignment is None:
                blockers["DRE_ACCOUNT_UNMAPPED"] += 1
            elif assignment.status != "APPROVED":
                blockers["DRE_MAPPING_PENDING_APPROVAL"] += 1
    if unit_id is not None and normalization.statistics.get("actual_unmapped_unit", 0):
        blockers["ACTUAL_UNIT_SCOPE_UNRESOLVED"] = normalization.statistics[
            "actual_unmapped_unit"
        ]
    return {key: value for key, value in blockers.items() if value}


def _calculated_lines(
    version: DreVersionView, datasets: list[DreInputDataset], month: int
) -> list[DreResultLineView]:
    assignments = {
        item.account_id: item.line_code
        for item in version.assignments
        if item.status == "APPROVED"
    }
    actual_by_period: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    budget_by_period: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    for dataset in datasets:
        current_month = dataset.readiness.period.month
        for fact in dataset.actuals:
            assert fact.account_id is not None and fact.amount is not None
            actual_by_period[current_month][assignments[fact.account_id]] += fact.amount
        for fact in dataset.budgets:
            assert fact.account_id is not None and fact.amount is not None
            budget_by_period[current_month][assignments[fact.account_id]] += fact.amount
    return calculate(version.lines, actual_by_period, budget_by_period, month)


def _formula_blocker(error: ValueError) -> str:
    return (
        "FORMULA_DENOMINATOR_ZERO"
        if str(error) == "DRE ratio denominator is zero"
        else "DRE_STRUCTURE_INVALID"
    )


def readiness(session: Session, user: User, scope: DreScope) -> DreReadinessView:
    version, run, datasets = _inputs(session, user, scope, write=False)
    blockers = _blockers(version, run, datasets, scope.unit_id)
    if not blockers:
        try:
            _calculated_lines(version, datasets, scope.period.month)
        except ValueError as error:
            blockers[_formula_blocker(error)] = 1
    return DreReadinessView(
        status="NOT_READY" if blockers else "READY",
        scope=scope,
        blockers=blockers,
        checked_periods=[item.readiness.period for item in datasets],
    )


def _run_view(run: DreCalculationRun) -> DreRunView:
    if run.status not in ("READY", "NOT_READY"):
        raise OnyxError(OnyxErrorCode.CONFLICT, "Invalid DRE calculation status")
    return DreRunView(
        id=run.id,
        status=run.status,
        scope=DreScope(
            normalization_run_id=run.normalization_run_id,
            structure_version_id=run.structure_version_id,
            period=run.period,
            unit_id=run.unit_id,
        ),
        blockers=run.blockers,
        input_digest=run.input_digest,
        engine_version=run.engine_version,
        provenance=run.provenance,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _stored_result_line(run_id: UUID, line: DreResultLineView) -> DreResultLine:
    values = line.model_dump()
    with localcontext() as context:
        context.prec = 100
        for key in (
            "realizado",
            "orcado",
            "variance",
            "variance_percent",
            "realizado_ytd",
            "orcado_ytd",
            "variance_ytd",
            "variance_percent_ytd",
        ):
            value = values[key]
            if value is not None:
                values[key] = value.quantize(RESULT_SCALE, rounding=ROUND_HALF_EVEN)
    return DreResultLine(run_id=run_id, **values)


def execute(session: Session, user: User, scope: DreScope) -> DreRunView:
    started_at = datetime.datetime.now(datetime.timezone.utc)
    version, normalization, datasets = _inputs(session, user, scope, write=True)
    digest = hashlib.sha256(
        json.dumps(
            {"scope": scope.model_dump(mode="json"), "engine": ENGINE_VERSION},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    session.execute(
        sa.text("SELECT pg_advisory_xact_lock(4433007, hashtext(:digest))"),
        {"digest": digest},
    )
    previous = session.scalar(
        sa.select(DreCalculationRun).where(DreCalculationRun.input_digest == digest)
    )
    if previous is not None:
        return _run_view(previous)
    blockers = _blockers(version, normalization, datasets, scope.unit_id)
    result_lines: list[DreResultLineView] = []
    if not blockers:
        try:
            result_lines = _calculated_lines(version, datasets, scope.period.month)
        except ValueError as error:
            blockers[_formula_blocker(error)] = 1
    review = session.get(ReviewRun, normalization.review_run_id)
    assert review is not None
    executions = [
        session.get(ImportProfileExecution, execution_id)
        for execution_id in [
            normalization.billing_execution_id,
            *(UUID(item) for item in normalization.budget_execution_ids),
        ]
    ]
    assert all(item is not None for item in executions)
    provenance = {
        "normalization_run_id": str(normalization.id),
        "normalization_input_digest": normalization.input_digest,
        "review_run_id": str(normalization.review_run_id),
        "dataset_revision": normalization.dataset_revision,
        "dataset_as_of": normalization.dataset_as_of.isoformat(),
        "ng_source_snapshot_id": str(review.snapshot_id),
        "billing_execution_id": str(normalization.billing_execution_id),
        "budget_execution_ids": normalization.budget_execution_ids,
        "operational_source_snapshot_ids": [
            str(item.snapshot_id) for item in executions if item is not None
        ],
        "financial_mapping_revision": normalization.mapping_revision_number,
        "amount_basis_revision": normalization.amount_basis_revision_number,
        "reconciliation_decision_revision": normalization.reconciliation_decision_number,
        "dre_structure_version_id": str(version.id),
        "dre_structure_version_number": version.number,
        "authority_policy_version": normalization.authority_policy_version,
        "derivation_version": normalization.derivation_version,
        "engine_version": ENGINE_VERSION,
    }
    run = DreCalculationRun(
        input_digest=digest,
        status="NOT_READY" if blockers else "READY",
        normalization_run_id=normalization.id,
        structure_version_id=version.id,
        period=scope.period,
        unit_id=scope.unit_id,
        blockers=blockers,
        provenance=provenance,
        engine_version=ENGINE_VERSION,
        started_at=started_at,
        finished_at=datetime.datetime.now(datetime.timezone.utc),
    )
    session.add(run)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_DRE_CALCULATE_START,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.DRE_CALCULATION_RUN,
        resource_id=run.id,
    )
    if not blockers:
        session.add_all(_stored_result_line(run.id, line) for line in result_lines)
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_DRE_CALCULATE_BLOCKED
        if blockers
        else AuditAction.TON_DRE_CALCULATE_SUCCEED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.DRE_CALCULATION_RUN,
        resource_id=run.id,
    )
    session.commit()
    return _run_view(run)


def get_calculation(session: Session, user: User, run_id: UUID) -> DreRunView:
    run = session.get(DreCalculationRun, run_id)
    if run is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "DRE calculation not found")
    financial_domain.get_run(session, user, run.normalization_run_id)
    if run.unit_id is None and not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "Consolidated DRE requires admin access"
        )
    if (
        run.unit_id is not None
        and session.scalar(
            sa.select(BusinessUnit.id).where(
                BusinessUnit.id == run.unit_id,
                business_unit_visible_clause(user),
            )
        )
        is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Business unit not found")
    return _run_view(run)


def list_result_lines(
    session: Session, user: User, run_id: UUID, limit: int, offset: int
) -> list[DreResultLineView]:
    get_calculation(session, user, run_id)
    check_page(limit, offset)
    rows = session.scalars(
        sa.select(DreResultLine)
        .where(DreResultLine.run_id == run_id)
        .order_by(DreResultLine.position)
        .limit(limit)
        .offset(offset)
    )
    return [
        DreResultLineView.model_validate(item, from_attributes=True) for item in rows
    ]


def get_statement(session: Session, user: User, run_id: UUID) -> DreStatementView:
    run = get_calculation(session, user, run_id)
    if run.status != "READY":
        raise OnyxError(OnyxErrorCode.CONFLICT, "DRE result is not ready")
    version = get_version(session, user, run.scope.structure_version_id)
    lines = [
        DreResultLineView.model_validate(item, from_attributes=True)
        for item in session.scalars(
            sa.select(DreResultLine)
            .where(DreResultLine.run_id == run_id)
            .order_by(DreResultLine.position)
        )
    ]
    return DreStatementView(run=run, version=version, lines=lines)


def get_period_series(
    session: Session,
    user: User,
    normalization_run_id: UUID,
    structure_version_id: UUID,
    year: int,
    unit_id: UUID | None,
    line_code: str,
) -> list[DrePeriodPoint]:
    financial_domain.get_run(session, user, normalization_run_id)
    if unit_id is None and not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "Consolidated DRE requires admin access"
        )
    if (
        unit_id is not None
        and session.scalar(
            sa.select(BusinessUnit.id).where(
                BusinessUnit.id == unit_id, business_unit_visible_clause(user)
            )
        )
        is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Business unit not found")
    start = datetime.date(year, 1, 1)
    end = datetime.date(year + 1, 1, 1)
    rows = session.execute(
        sa.select(DreCalculationRun, DreResultLine)
        .join(DreResultLine, DreResultLine.run_id == DreCalculationRun.id)
        .where(
            DreCalculationRun.normalization_run_id == normalization_run_id,
            DreCalculationRun.structure_version_id == structure_version_id,
            DreCalculationRun.unit_id == unit_id,
            DreCalculationRun.status == "READY",
            DreCalculationRun.period >= start,
            DreCalculationRun.period < end,
            DreResultLine.code == line_code,
        )
        .order_by(DreCalculationRun.period)
    ).all()
    return [
        DrePeriodPoint(
            period=run.period,
            result_id=run.id,
            realizado=line.realizado,
            orcado=line.orcado,
            variance=line.variance,
        )
        for run, line in rows
    ]


def list_calculations(
    session: Session,
    user: User,
    period: datetime.date,
    unit_id: UUID | None,
    limit: int,
    offset: int,
) -> list[DreRunView]:
    check_page(limit, offset)
    if period.day != 1:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Period must start on day one")
    if unit_id is None and not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "Consolidated DRE requires admin access"
        )
    if (
        unit_id is not None
        and session.scalar(
            sa.select(BusinessUnit.id).where(
                BusinessUnit.id == unit_id, business_unit_visible_clause(user)
            )
        )
        is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Business unit not found")
    query = (
        sa.select(DreCalculationRun)
        .where(DreCalculationRun.period == period, DreCalculationRun.unit_id == unit_id)
        .order_by(DreCalculationRun.finished_at.desc(), DreCalculationRun.id.desc())
    )
    visible: list[DreRunView] = []
    for run in session.scalars(query):
        try:
            financial_domain.get_run(session, user, run.normalization_run_id)
        except OnyxError as error:
            if error.error_code == OnyxErrorCode.NOT_FOUND:
                continue
            raise
        visible.append(_run_view(run))
        if len(visible) >= offset + limit:
            break
    return visible[offset : offset + limit]


def _treatments_by_id(
    session: Session, ids: set[UUID | None]
) -> dict[UUID, ClosingTreatment]:
    wanted = {item for item in ids if item is not None}
    if not wanted:
        return {}
    return {
        item.id: item
        for item in session.scalars(
            sa.select(ClosingTreatment).where(ClosingTreatment.id.in_(wanted))
        )
    }


def list_contributors(
    session: Session,
    user: User,
    run_id: UUID,
    line_code: str,
    fact_type: str,
    limit: int,
    offset: int,
) -> DreContributorPage:
    run = get_calculation(session, user, run_id)
    if run.status != "READY":
        raise OnyxError(OnyxErrorCode.CONFLICT, "DRE result is not ready")
    check_page(limit, offset)
    definition = session.get(DreStructureVersion, run.scope.structure_version_id)
    assert definition is not None
    line = next((item for item in definition.lines if item["code"] == line_code), None)
    if line is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "DRE line not found")
    if line["line_type"] != DreLineType.SOURCE_SUM:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Only source lines have direct contributors"
        )
    if fact_type not in ("ACTUAL", "BUDGET"):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Unknown contributor type")
    fact_model = FinancialActualFact if fact_type == "ACTUAL" else FinancialBudgetFact
    source_model = (
        ParsedSourceRecord if fact_type == "ACTUAL" else OperationalSourceRecord
    )
    source_id_column = (
        fact_model.parsed_record_id
        if fact_type == "ACTUAL"
        else fact_model.source_record_id
    )
    conditions = [
        fact_model.run_id == run.scope.normalization_run_id,
        fact_model.calendar_period == run.scope.period,
        DreAccountMapping.version_id == run.scope.structure_version_id,
        DreAccountMapping.line_code == line_code,
        DreAccountMapping.status == "APPROVED",
    ]
    if run.scope.unit_id is not None:
        conditions.append(fact_model.unit_id == run.scope.unit_id)
    joined = (
        sa.select(
            fact_model,
            source_model,
            FinancialAccount,
            BusinessUnit,
            Source,
            SourceSnapshot,
        )
        .join(DreAccountMapping, DreAccountMapping.account_id == fact_model.account_id)
        .join(source_model, source_model.id == source_id_column)
        .join(FinancialAccount, FinancialAccount.id == fact_model.account_id)
        .join(BusinessUnit, BusinessUnit.id == fact_model.unit_id)
        .join(Source, Source.id == source_model.source_id)
        .join(SourceSnapshot, SourceSnapshot.id == source_model.snapshot_id)
        .where(*conditions)
    )
    total = (
        session.scalar(sa.select(sa.func.count()).select_from(joined.subquery())) or 0
    )
    date_column = (
        fact_model.emission_date if fact_type == "ACTUAL" else source_model.record_date
    )
    rows = session.execute(
        joined.order_by(date_column.asc().nulls_last(), fact_model.id)
        .limit(limit)
        .offset(offset)
    ).all()
    normalization = session.get(
        FinancialNormalizationRun, run.scope.normalization_run_id
    )
    assert normalization is not None
    basis_index = (
        financial_domain._basis_index(
            session, normalization.amount_basis_revision_number
        )
        if fact_type == "ACTUAL"
        else {}
    )
    accounts = (
        {item.id: item for item in session.scalars(sa.select(FinancialAccount))}
        if fact_type == "ACTUAL"
        else {}
    )
    treatments = _treatments_by_id(
        session,
        {row[0].treatment_id for row in rows if fact_type == "ACTUAL"},
    )
    contributors: list[DreContributorView] = []
    for fact, source, account, unit, source_info, snapshot in rows:
        treatment = None
        original_amount = None
        original_account = None
        if fact_type == "ACTUAL":
            basis, amount, original_amount = financial_domain.actual_amounts(
                fact, basis_index, accounts
            )
            treatment = treatments.get(fact.treatment_id) if fact.treatment_id else None
            original_account = (
                accounts.get(fact.original_account_id)
                if fact.original_account_id
                else None
            )
            reference = source.document_number
            review_status = fact.disposition
            record_date = fact.emission_date
            source_account_code = source.account_code
            source_account_label = source.account_label
            description = source.history
        else:
            basis = fact.period_basis
            amount = fact.amount
            reference = source.identifier
            review_status = None
            record_date = source.record_date
            source_account_code = source.identifier
            source_account_label = None
            description = source.description
        assert amount is not None and basis is not None
        contributors.append(
            DreContributorView(
                id=fact.id,
                fact_type=fact_type,
                period=run.scope.period,
                account_code=account.code,
                account_label=account.label,
                unit_code=unit.code,
                amount=amount,
                amount_basis=basis,
                record_date=record_date,
                source_name=source_info.display_name,
                original_filename=snapshot.original_filename or "",
                source_id=source.source_id,
                source_snapshot_id=source.snapshot_id,
                source_execution_id=source.execution_id,
                sheet_name=source.sheet_name,
                source_row_number=source.source_row_number,
                reference=reference,
                review_status=review_status,
                unit_name=unit.name,
                source_account_code=source_account_code,
                source_account_label=source_account_label,
                description=description,
                treatment_title=treatment.title if treatment else None,
                treatment_effect=treatment.effect if treatment else None,
                treatment_version=treatment.version if treatment else None,
                original_amount=original_amount if treatment else None,
                original_account_label=(
                    original_account.label if original_account else None
                ),
            )
        )
    return DreContributorPage(total=total, rows=contributors)


def _export_entries(
    session: Session,
    user: User,
    run: DreRunView,
    lines: dict[str, DreLineDefinition],
) -> list[BaseEntry]:
    """Every ACTUAL fact of the year to date that a source line sums."""
    normalization = session.get(
        FinancialNormalizationRun, run.scope.normalization_run_id
    )
    assert normalization is not None
    conditions = [
        FinancialActualFact.run_id == run.scope.normalization_run_id,
        FinancialActualFact.calendar_period >= run.scope.period.replace(month=1),
        FinancialActualFact.calendar_period <= run.scope.period,
        DreAccountMapping.version_id == run.scope.structure_version_id,
        DreAccountMapping.status == "APPROVED",
    ]
    if not is_ton_administrator(user):
        conditions.append(business_unit_visible_clause(user))
    rows = session.execute(
        sa.select(
            FinancialActualFact,
            ParsedSourceRecord,
            FinancialAccount,
            BusinessUnit,
            DreAccountMapping.line_code,
            SourceSnapshot.original_filename,
        )
        .join(
            DreAccountMapping,
            DreAccountMapping.account_id == FinancialActualFact.account_id,
        )
        .join(
            ParsedSourceRecord,
            ParsedSourceRecord.id == FinancialActualFact.parsed_record_id,
        )
        .join(FinancialAccount, FinancialAccount.id == FinancialActualFact.account_id)
        .outerjoin(BusinessUnit, BusinessUnit.id == FinancialActualFact.unit_id)
        .join(SourceSnapshot, SourceSnapshot.id == ParsedSourceRecord.snapshot_id)
        .where(*conditions)
    ).all()
    basis_index = financial_domain._basis_index(
        session, normalization.amount_basis_revision_number
    )
    accounts = {item.id: item for item in session.scalars(sa.select(FinancialAccount))}
    treatments = _treatments_by_id(session, {row[0].treatment_id for row in rows})
    entries: list[BaseEntry] = []
    for fact, source, account, unit, line_code, filename in rows:
        if lines[line_code].line_type != DreLineType.SOURCE_SUM:
            continue
        basis, amount, original = financial_domain.actual_amounts(
            fact, basis_index, accounts
        )
        assert amount is not None and basis is not None
        treatment = treatments.get(fact.treatment_id) if fact.treatment_id else None
        entries.append(
            BaseEntry(
                competence=fact.calendar_period,
                unit_code=unit.code if unit else None,
                unit_name=unit.name if unit else None,
                line_code=line_code,
                amount=amount,
                record_date=fact.emission_date,
                nature=account.label,
                ng_account_code=source.account_code,
                ng_account_label=source.account_label,
                document=source.document_number,
                history=source.history,
                amount_basis=basis,
                review_status=fact.disposition,
                source_file=filename or "",
                sheet_name=source.sheet_name,
                row_number=source.source_row_number,
                treatment=(
                    f"{treatment.title} (versão {treatment.version})"
                    if treatment is not None
                    else None
                ),
                original_amount=original if treatment is not None else None,
            )
        )
    return entries


def _months_text(months: list[int]) -> str:
    return ", ".join(month_label(month) for month in months)


def _treatment_premise(treatment: ClosingTreatment) -> Premise:
    decided = (
        f"Decidido pela Controladoria (versão {treatment.version}, "
        f"{treatment.created_at.astimezone(SAO_PAULO):%d/%m/%Y}): "
        f"{treatment.justification}"
    )
    if treatment.status == "BLOCKED":
        return Premise(
            topic=treatment.title,
            status=f"{decided}\nAinda não aplicado: falta {treatment.required_source}.",
            effect="Os valores aparecem como lançados no NG até a fonte existir.",
        )
    return Premise(
        topic=treatment.title,
        status=decided,
        effect="Aplicado: veja as colunas Valor no NG e Tratamento da Controladoria "
        "na aba Base.",
    )


def _export_premises(
    data_scopes: list[ScopeBlock],
    last_month: int,
    entries: list[BaseEntry],
    budget_present: bool,
    treatments: list[ClosingTreatment],
) -> list[Premise]:
    premises = [
        _treatment_premise(treatment)
        for treatment in treatments
        if treatment.status != "REVOKED"
    ]
    if not treatments:
        premises.append(
            Premise(
                topic="Parcelamentos",
                status="Decidido em 03/10/2026: entra só a parcela paga, no mês "
                "do pagamento. Ainda não aplicado: o TON usa o valor lançado no NG.",
                effect="As naturezas com parcelamentos mostram o valor integral do "
                "NG até a limpeza no NG ou a aprovação do tratamento.",
            )
        )
    premises += [
        Premise(
            topic="PIS/COFINS",
            status="O TON ainda não calcula PIS/COFINS. Os valores vêm como "
            "lançados no NG.",
            effect="Aguarda a planilha de apuração da Controladoria.",
        ),
        Premise(
            topic="Receita",
            status="A base da receita (valor do NG ou faturamento bruto com "
            "impostos como dedução) está em definição com a Controladoria.",
            effect="A receita aparece como lançada no NG.",
        ),
        Premise(
            topic="Orçado",
            status="Há orçado aprovado nesta base."
            if budget_present
            else "Nenhuma dotação aprovada está carregada: o orçado está zerado.",
            effect="Esta planilha mostra só o Realizado; o orçado fica na tela da DRE."
            if budget_present
            else "Esta planilha mostra só o Realizado.",
        ),
    ]
    pending = [
        f"{scope.unit_code or 'Consolidado'} {scope.label}: "
        + _months_text(
            [
                month
                for month in range(1, last_month + 1)
                if month not in scope.ready_months
            ]
        )
        for scope in data_scopes
        if len(scope.ready_months) < last_month
    ]
    premises.append(
        Premise(
            topic="Unidades/filiais sem DRE pronta",
            status="\n".join(pending)
            if pending
            else "Todas as unidades estão prontas em todos os meses.",
            effect="Os valores desses meses aparecem em cinza: vêm da Base, mas o "
            "TON não publicou a DRE da unidade no mês (por exemplo, mês sem "
            "lançamento)."
            if pending
            else "Nenhum.",
        )
    )
    without_unit = [entry for entry in entries if entry.unit_code is None]
    if without_unit:
        premises.append(
            Premise(
                topic="Lançamentos sem unidade",
                status=f"{len(without_unit)} lançamentos não têm unidade/filial.",
                effect="Entram no consolidado e em nenhuma unidade.",
            )
        )
    return premises


def export_workbook(
    session: Session, user: User, run_id: UUID
) -> tuple[DreRunView, bytes]:
    """Excel of the year to date for the run's base: consolidated and units."""
    anchor = get_calculation(session, user, run_id)
    if anchor.status != "READY":
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "Only ready DRE results can be exported"
        )
    version = get_version(session, user, anchor.scope.structure_version_id)
    structure = session.get(DreStructure, version.structure_id)
    normalization = session.get(
        FinancialNormalizationRun, anchor.scope.normalization_run_id
    )
    assert structure is not None and normalization is not None
    period = anchor.scope.period
    lines = {line.code: line for line in version.lines}
    runs = list(
        session.scalars(
            sa.select(DreCalculationRun)
            .where(
                DreCalculationRun.normalization_run_id
                == anchor.scope.normalization_run_id,
                DreCalculationRun.structure_version_id
                == anchor.scope.structure_version_id,
                DreCalculationRun.status == "READY",
                DreCalculationRun.period >= period.replace(month=1),
                DreCalculationRun.period <= period,
            )
            .order_by(DreCalculationRun.finished_at.desc())
        )
    )
    entries = _export_entries(session, user, anchor, lines)
    unit_rows = session.execute(
        sa.select(BusinessUnit.id, BusinessUnit.code, BusinessUnit.name)
        .where(
            BusinessUnit.code.in_(
                {entry.unit_code for entry in entries if entry.unit_code}
            ),
            business_unit_visible_clause(user),
        )
        .order_by(BusinessUnit.code)
    ).all()
    run_by_scope: dict[tuple[UUID | None, int], DreCalculationRun] = {}
    for run in runs:
        run_by_scope.setdefault((run.unit_id, run.period.month), run)
    scopes: list[ScopeBlock] = []
    scope_units: list[UUID | None] = []
    if is_ton_administrator(user):
        scopes.append(
            ScopeBlock(
                unit_code=None,
                label="Consolidado — todas as unidades/filiais",
                ready_months=frozenset(
                    month for unit_id, month in run_by_scope if unit_id is None
                ),
            )
        )
        scope_units.append(None)
    for unit_id, code, name in unit_rows:
        scopes.append(
            ScopeBlock(
                unit_code=code,
                label=name,
                ready_months=frozenset(
                    month for scope_unit, month in run_by_scope if scope_unit == unit_id
                ),
            )
        )
        scope_units.append(unit_id)
    budget_present = False
    data = DreWorkbookInput(
        structure_label=structure.label,
        structure_version=version.number,
        lines=version.lines,
        year=period.year,
        last_month=period.month,
        scopes=scopes,
        entries=entries,
        header=[],
    )
    expected = expected_values(data)
    cent = Decimal("0.01")
    for scope, unit_id in zip(scopes, scope_units, strict=True):
        for month in scope.ready_months:
            run = run_by_scope[(unit_id, month)]
            for stored in session.scalars(
                sa.select(DreResultLine).where(DreResultLine.run_id == run.id)
            ):
                budget_present = budget_present or bool(
                    stored.orcado or stored.orcado_ytd
                )
                checks = [(month, stored.realizado)]
                if month == period.month:
                    checks.append((None, stored.realizado_ytd))
                for column, persisted in checks:
                    value = expected[scope.unit_code][(column, stored.code)]
                    if (
                        lines[stored.code].operation == DreOperation.RATIO
                        and value is None
                    ):
                        continue
                    if value is None or value.quantize(cent) != persisted.quantize(
                        cent
                    ):
                        raise OnyxError(
                            OnyxErrorCode.CONFLICT,
                            "DRE export does not match the persisted calculation",
                        )
    local_now = datetime.datetime.now(SAO_PAULO)
    as_of = normalization.dataset_as_of.astimezone(SAO_PAULO)
    header = [
        (
            "Período",
            f"{month_label(1)} a {month_label(period.month)}/{period.year}"
            if period.month > 1
            else f"{month_label(1)}/{period.year}",
        ),
        ("Importação NG", as_of.strftime("%d/%m/%Y %H:%M")),
        ("Estrutura", f"{structure.label} · versão {version.number}"),
        ("Lançamentos na Base", f"{len(entries)}"),
        ("Gerado em", local_now.strftime("%d/%m/%Y %H:%M")),
    ]
    data = dataclasses.replace(
        data,
        header=header,
        premises=_export_premises(
            scopes,
            period.month,
            entries,
            budget_present,
            versions_in_force(session, normalization.treatment_number),
        ),
    )
    return anchor, build_workbook(data)


def audit_export(session: Session, user: User, run_id: UUID) -> None:
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_DRE_EXPORT,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.DRE_CALCULATION_RUN,
        resource_id=run_id,
    )


def audit_failed_calculation(session: Session, user: User, version_id: UUID) -> None:
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_DRE_CALCULATE_FAIL,
        outcome=AuditOutcome.FAILURE,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.DRE_STRUCTURE_VERSION,
        resource_id=version_id,
    )
