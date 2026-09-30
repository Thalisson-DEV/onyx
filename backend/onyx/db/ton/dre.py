"""Persistence and authorization for DATA-005 DRE versions and results."""

import datetime
import hashlib
import json
from collections import Counter, defaultdict
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import financial_domain
from onyx.db.ton.acl import business_unit_visible_clause, is_ton_administrator
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import (
    BusinessUnit,
    DreAccountMapping,
    DreCalculationRun,
    DreResultLine,
    DreStructure,
    DreStructureVersion,
    FinancialAccount,
    FinancialNormalizationRun,
    ImportProfileExecution,
    ReviewRun,
)
from onyx.db.ton.sources import check_page, get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.dre.engine import ENGINE_VERSION, calculate, calculation_order
from onyx.ton.dre.models import (
    DreLineDefinition,
    DreLineType,
    DreReadinessView,
    DreResultLineView,
    DreRunView,
    DreScope,
    DreStructureCreate,
    DreStructureView,
    DreVersionCreate,
    DreVersionView,
)
from onyx.ton.financial_domain.models import DreInputDataset
from onyx.utils.audit import AuditAction, AuditOutcome

RESULT_SCALE = Decimal("1e-25")


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


def list_structures(
    session: Session, user: User, limit: int, offset: int
) -> list[DreStructureView]:
    _require_admin(user)
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


def get_structure(session: Session, user: User, structure_id: UUID) -> DreStructureView:
    _require_admin(user)
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


def get_version(session: Session, user: User, version_id: UUID) -> DreVersionView:
    _require_admin(user)
    version = session.get(DreStructureVersion, version_id)
    if version is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "DRE version not found")
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
        "BILLING_COMPETENCE_UNRESOLVED",
        "UNSUPPORTED_DERIVATION",
        "IR_RETENTION_UNRESOLVED",
        "SOURCE_RECONCILIATION_AMBIGUOUS",
        "SOURCE_RECONCILIATION_UNRESOLVED",
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
                if key not in global_keys and key != "UNCLASSIFIED_ACCOUNT"
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


def audit_failed_calculation(session: Session, user: User, version_id: UUID) -> None:
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_DRE_CALCULATE_FAIL,
        outcome=AuditOutcome.FAILURE,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.DRE_STRUCTURE_VERSION,
        resource_id=version_id,
    )
