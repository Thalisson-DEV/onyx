"""Synthetic fixtures for TON domain tests.

Every value here is invented for the test. No Prompt Mestre threshold, no NC
mapping, no Vale Norte figure and no real rule code appears in this file — that
is the point: the schema must be exercisable without any unapproved business
value existing anywhere.
"""

import datetime
import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from onyx.db.enums import AccountType, GrantSource, Permission
from onyx.db.models import PermissionGrant, User, User__UserGroup, UserGroup
from onyx.db.permissions import recompute_user_permissions__no_commit
from onyx.db.ton.canonical import ScaledDecimal
from onyx.db.ton.enums import (
    AnalysisSpecialist,
    AnalysisStepCode,
    AnalysisStepStatus,
    AnalysisTrigger,
    BusinessUnitKind,
    ContractStatus,
    EvidenceConfidenceLevel,
    FindingKind,
    MissingDataBehavior,
    OccurrenceCriticality,
    OccurrenceLedgerKind,
    PostResolutionPolicy,
    RuleDomain,
    RuleKind,
    RuleProvenance,
    RuleVersionStatus,
    SourceType,
    TonReportType,
    TonSharePermission,
)
from onyx.db.ton.models import (
    AnalysisRun,
    AnalysisStep,
    BusinessUnit,
    BusinessUnit__UserGroup,
    Contract,
    Contract__UserGroup,
    Finding,
    Occurrence,
    Occurrence__UserGroup,
    Rule,
    RuleVersion,
    SourceSnapshot,
    TonReport,
    TonReport__UserGroup,
    TonReportRevision,
)
from onyx.db.ton.occurrences import DetectionResult, record_detection__no_commit
from onyx.db.ton.reports import (
    create_report__no_commit,
    publish_report_revision__no_commit,
)

# Obviously synthetic. Named so a reader cannot mistake them for approved
# configuration.
SYNTHETIC_PARAMETERS: dict[str, object] = {
    "synthetic_threshold": "0.5",
    "synthetic_window": 7,
}
SYNTHETIC_EXECUTOR_KEY = "synthetic_noop_executor.v1"
SYNTHETIC_PERIOD_START = datetime.date(2001, 1, 1)
SYNTHETIC_PERIOD_END = datetime.date(2001, 1, 31)


def unique_suffix() -> str:
    return uuid.uuid4().hex[:10]


def make_user(db_session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"ton-003b-{unique_suffix()}@example.invalid",
        hashed_password="not-a-real-hash",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        account_type=AccountType.STANDARD,
    )
    db_session.add(user)
    db_session.flush()
    return user


def make_business_unit(
    db_session: Session,
    *,
    code: str | None = None,
    kind: BusinessUnitKind = BusinessUnitKind.OPERATIONAL,
    is_active: bool = True,
) -> BusinessUnit:
    unit = BusinessUnit(
        code=code or f"SYN-UNIT-{unique_suffix()}",
        name="Synthetic Unit",
        kind=kind,
        is_active=is_active,
    )
    db_session.add(unit)
    db_session.flush()
    return unit


def make_contract(
    db_session: Session,
    *,
    business_unit: BusinessUnit,
    status: ContractStatus = ContractStatus.ACTIVE,
    code: str | None = None,
    start_date: datetime.date | None = SYNTHETIC_PERIOD_START,
    end_date: datetime.date | None = SYNTHETIC_PERIOD_END,
) -> Contract:
    contract = Contract(
        code=code or f"SYN-CT-{unique_suffix()}",
        business_unit_id=business_unit.id,
        contracting_authority="Synthetic Authority",
        object_summary="Synthetic object summary",
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    db_session.add(contract)
    db_session.flush()
    return contract


def make_rule(
    db_session: Session,
    *,
    code: str | None = None,
    domain: RuleDomain = RuleDomain.FINANCIAL,
    kind: RuleKind = RuleKind.DETECTION,
    created_by: UUID | None = None,
) -> Rule:
    rule = Rule(
        code=code or f"SYN-RULE-{unique_suffix()}",
        domain=domain,
        kind=kind,
        created_by=created_by,
    )
    db_session.add(rule)
    db_session.flush()
    return rule


def make_rule_version(
    db_session: Session,
    *,
    rule: Rule,
    version: int = 1,
    status: RuleVersionStatus = RuleVersionStatus.DRAFT,
    approved_by: UUID | None = None,
    approved_at: datetime.datetime | None = None,
    approval_reference: str | None = None,
    effective_from: datetime.date | None = None,
    effective_to: datetime.date | None = None,
    identity_components: list[str] | None = None,
    parameters: dict[str, object] | None = None,
    flush: bool = True,
) -> RuleVersion:
    """Build a rule version straight through the ORM.

    Deliberately bypasses ``create_rule_version__no_commit`` so that database
    constraints are exercised rather than the Python guards in front of them.
    """
    rule_version = RuleVersion(
        rule_id=rule.id,
        version=version,
        title="Synthetic rule version",
        executor_key=SYNTHETIC_EXECUTOR_KEY,
        parameters=parameters if parameters is not None else dict(SYNTHETIC_PARAMETERS),
        applicability={},
        effective_from=effective_from,
        effective_to=effective_to,
        status=status,
        provenance=RuleProvenance.DERIVED,
        approved_by=approved_by,
        approved_at=approved_at,
        approval_reference=approval_reference,
        missing_data_behavior=MissingDataBehavior.SKIP_WITH_NOTE,
        evidence_requirements={},
        min_confidence_level=EvidenceConfidenceLevel.C,
        severity_mapping={},
        identity_components=identity_components
        if identity_components is not None
        else ["rule_code", "business_unit_id", "period"],
        post_resolution_policy=PostResolutionPolicy.REOPEN_SAME_OCCURRENCE,
    )
    db_session.add(rule_version)
    if flush:
        db_session.flush()
    return rule_version


def make_source_snapshot(
    db_session: Session,
    *,
    source_type: SourceType = SourceType.UPLOADED_SPREADSHEET,
    is_complete: bool = True,
    missing_inputs: list[str] | None = None,
    is_schema_conformant: bool = True,
    period_start: datetime.date | None = SYNTHETIC_PERIOD_START,
    period_end: datetime.date | None = SYNTHETIC_PERIOD_END,
) -> SourceSnapshot:
    snapshot = SourceSnapshot(
        source_type=source_type,
        source_system_label="Synthetic source",
        extracted_at=datetime.datetime(2001, 2, 1, tzinfo=datetime.UTC),
        period_start=period_start,
        period_end=period_end,
        units_covered=["SYN-UNIT"],
        row_count=3,
        checksum="synthetic-checksum",
        is_complete=is_complete,
        missing_inputs=missing_inputs if missing_inputs is not None else [],
        is_schema_conformant=is_schema_conformant,
    )
    db_session.add(snapshot)
    db_session.flush()
    return snapshot


def make_analysis_run(
    db_session: Session,
    *,
    domain: RuleDomain = RuleDomain.FINANCIAL,
    business_unit: BusinessUnit | None = None,
    specialist: AnalysisSpecialist = AnalysisSpecialist.CFO,
    trigger: AnalysisTrigger = AnalysisTrigger.INTERACTIVE,
    idempotency_key: str | None = None,
) -> AnalysisRun:
    run = AnalysisRun(
        trigger=trigger,
        specialist=specialist,
        domain=domain,
        business_unit_id=business_unit.id if business_unit is not None else None,
        period_start=SYNTHETIC_PERIOD_START,
        period_end=SYNTHETIC_PERIOD_END,
        idempotency_key=idempotency_key or f"syn-idem-{unique_suffix()}",
        executor_version="synthetic-executor-0",
    )
    db_session.add(run)
    db_session.flush()
    return run


def make_step(
    db_session: Session,
    *,
    run: AnalysisRun,
    step_code: AnalysisStepCode,
    domain: RuleDomain | None = None,
    business_unit: BusinessUnit | None = None,
    status: AnalysisStepStatus = AnalysisStepStatus.PENDING,
) -> AnalysisStep:
    step = AnalysisStep(
        analysis_run_id=run.id,
        step_code=step_code,
        domain=domain,
        business_unit_id=business_unit.id if business_unit is not None else None,
        status=status,
    )
    db_session.add(step)
    db_session.flush()
    return step


# ---------------------------------------------------------------------------
# Plan 003c — findings, occurrences, ACL.
#
# Same rule as above: every value is invented. `SYN-` prefixes and
# `synthetic_` names make it impossible to mistake a fixture for approved
# configuration, and no Prompt Mestre threshold or Vale Norte figure appears
# anywhere below.
# ---------------------------------------------------------------------------

SYNTHETIC_DETECTED_AT = datetime.datetime(2001, 2, 15, 12, 0, tzinfo=datetime.UTC)
# A currency code that is not a real one, so no accepted-currency decision is
# pre-empted by a fixture.
SYNTHETIC_CURRENCY = "XTS"


def make_group(db_session: Session, *, name: str | None = None) -> UserGroup:
    """A user group, created directly rather than through the EE insert path.

    These suites run on a throwaway database with no Celery and no document
    index, so the group-sync bookkeeping the EE path performs has nothing to do.
    ``is_up_to_date`` is set for the same reason.
    """
    group = UserGroup(
        name=name or f"SYN-GROUP-{unique_suffix()}",
        is_up_to_date=True,
        is_up_for_deletion=False,
        is_default=False,
    )
    db_session.add(group)
    db_session.flush()
    return group


def grant_permissions(
    db_session: Session,
    *,
    group: UserGroup,
    permissions: Sequence[Permission],
) -> None:
    """Grant tokens to a group through the production grant table."""
    for permission in permissions:
        db_session.add(
            PermissionGrant(
                group_id=group.id,
                permission=permission,
                grant_source=GrantSource.USER,
            )
        )
    db_session.flush()


def add_member(
    db_session: Session, *, group: UserGroup, user: User, is_manager: bool = False
) -> None:
    """Add *user* to *group* and recompute their effective permissions.

    Uses the production recompute so the test exercises the same permission
    resolution the application does, rather than writing the JSONB column itself.
    """
    db_session.add(
        User__UserGroup(user_id=user.id, user_group_id=group.id, is_manager=is_manager)
    )
    db_session.flush()
    recompute_user_permissions__no_commit([user.id], db_session)
    db_session.flush()
    db_session.refresh(user)


def make_admin(db_session: Session) -> User:
    """A global administrator: the only actor that bypasses the TON resource ACL."""
    user = make_user(db_session)
    user.effective_permissions = [Permission.FULL_ADMIN_PANEL_ACCESS.value]
    db_session.flush()
    return user


def make_occurrence_rule_version(
    db_session: Session,
    *,
    identity_components: list[str] | None = None,
    post_resolution_policy: PostResolutionPolicy = (
        PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
    ),
    rule: Rule | None = None,
    version: int = 1,
    nc_code: str | None = None,
) -> tuple[Rule, RuleVersion]:
    """A rule plus one version, ready to produce findings."""
    rule = rule if rule is not None else make_rule(db_session)
    rule_version = make_rule_version(
        db_session,
        rule=rule,
        version=version,
        identity_components=identity_components or ["rule_code", "period"],
    )
    rule_version.post_resolution_policy = post_resolution_policy
    rule_version.nc_code = nc_code
    db_session.flush()
    return rule, rule_version


def record_synthetic_detection(
    db_session: Session,
    *,
    rule: Rule,
    rule_version: RuleVersion,
    analysis_run: AnalysisRun,
    identity_values: dict[str, object | None] | None = None,
    finding_kind: FindingKind = FindingKind.DETECTION,
    criticality: OccurrenceCriticality = OccurrenceCriticality.MEDIUM,
    ledger_kind: OccurrenceLedgerKind = OccurrenceLedgerKind.EXCEPTION,
    owning_domain: RuleDomain = RuleDomain.FINANCIAL,
    title: str = "Synthetic occurrence",
    business_unit: BusinessUnit | None = None,
    contract: Contract | None = None,
    detected_at: datetime.datetime | None = None,
    **finding_fields: Any,
) -> DetectionResult:
    """Drive one detection through the production resolution path."""
    return record_detection__no_commit(
        db_session,
        analysis_run_id=analysis_run.id,
        rule=rule,
        rule_version=rule_version,
        identity_values=identity_values or {"period": "2001-01"},
        finding_kind=finding_kind,
        title=title,
        owning_domain=owning_domain,
        ledger_kind=ledger_kind,
        criticality=criticality,
        detected_at=detected_at or SYNTHETIC_DETECTED_AT,
        business_unit_id=business_unit.id if business_unit is not None else None,
        contract_id=contract.id if contract is not None else None,
        **finding_fields,
    )


def authorize_group(
    db_session: Session,
    *,
    group: UserGroup,
    occurrence: Occurrence | None = None,
    business_unit: BusinessUnit | None = None,
    contract: Contract | None = None,
    report: TonReport | None = None,
    permission: TonSharePermission = TonSharePermission.VIEWER,
) -> None:
    """Write ACL junction rows directly, bypassing the write gate.

    Deliberate: the read tests need an arranged ACL state without also asserting
    the write gate, and the write gate has its own cases. Writing the rows here
    also proves the junction is what grants access — remove the call and the read
    is denied.
    """
    if occurrence is not None:
        db_session.add(
            Occurrence__UserGroup(
                occurrence_id=occurrence.id,
                user_group_id=group.id,
                permission=permission,
            )
        )
    if business_unit is not None:
        db_session.add(
            BusinessUnit__UserGroup(
                business_unit_id=business_unit.id,
                user_group_id=group.id,
                permission=permission,
            )
        )
    if contract is not None:
        db_session.add(
            Contract__UserGroup(
                contract_id=contract.id,
                user_group_id=group.id,
                permission=permission,
            )
        )
    if report is not None:
        db_session.add(
            TonReport__UserGroup(
                report_id=report.id,
                user_group_id=group.id,
                permission=permission,
            )
        )
    db_session.flush()


# ---------------------------------------------------------------------------
# Plan 003d — reports, canonicalisation, audit.
#
# Same rule again: every value is invented. No Prompt Mestre report layout, no
# ISC weight, no publication ceiling and no Vale Norte figure appears below.
# ---------------------------------------------------------------------------

SYNTHETIC_GENERATOR_VERSION = "synthetic-report-generator-0"
SYNTHETIC_GENERATED_AT = datetime.datetime(2001, 3, 1, 8, 30, tzinfo=datetime.UTC)


def make_report(
    db_session: Session,
    *,
    report_type: TonReportType = TonReportType.MONTHLY_CLOSE,
    code: str | None = None,
    title: str = "Synthetic report",
    business_unit: BusinessUnit | None = None,
    period_start: datetime.date | None = SYNTHETIC_PERIOD_START,
    period_end: datetime.date | None = SYNTHETIC_PERIOD_END,
    created_by: UUID | None = None,
) -> TonReport:
    """A logical report, created through the production path."""
    return create_report__no_commit(
        db_session,
        code=code or f"SYN-REP-{unique_suffix()}",
        report_type=report_type,
        title=title,
        business_unit_id=business_unit.id if business_unit is not None else None,
        period_start=period_start,
        period_end=period_end,
        created_by=created_by,
    )


def synthetic_report_body(
    *, total: str = "1234.50", percentage: str = "12.5000"
) -> dict[str, Any]:
    """A report body exercising the canonical decimal rules.

    Amounts arrive as ``ScaledDecimal`` so the published scale is part of the
    contract, which is what a monetary figure needs. Nothing here is a real
    Vale Norte number.
    """
    return {
        "headline": "Sintese sintética",
        "total_amount": ScaledDecimal(Decimal(total), scale=2),
        "deviation_percentage": ScaledDecimal(Decimal(percentage), scale=4),
        "counted_rows": 3,
        "currency": SYNTHETIC_CURRENCY,
    }


def publish_synthetic_revision(
    db_session: Session,
    *,
    report: TonReport,
    body: dict[str, Any] | None = None,
    findings: Sequence[Finding] = (),
    occurrences: Sequence[Occurrence] = (),
    analysis_runs: Sequence[AnalysisRun] = (),
    rule_versions: Sequence[RuleVersion] = (),
    source_snapshots: Sequence[SourceSnapshot] = (),
    generated_at: datetime.datetime | None = None,
    generated_by: UUID | None = None,
    corrects: TonReportRevision | None = None,
    correction_reason: str | None = None,
) -> TonReportRevision:
    """Publish one revision through the production path."""
    return publish_report_revision__no_commit(
        db_session,
        report=report,
        body=body if body is not None else synthetic_report_body(),
        generator_version=SYNTHETIC_GENERATOR_VERSION,
        generated_at=generated_at or SYNTHETIC_GENERATED_AT,
        generated_by=generated_by,
        findings=findings,
        occurrences=occurrences,
        analysis_runs=analysis_runs,
        rule_versions=rule_versions,
        source_snapshots=source_snapshots,
        corrects=corrects,
        correction_reason=correction_reason,
    )
