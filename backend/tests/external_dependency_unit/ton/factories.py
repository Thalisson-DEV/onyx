"""Synthetic fixtures for TON domain tests.

Every value here is invented for the test. No Prompt Mestre threshold, no NC
mapping, no Vale Norte figure and no real rule code appears in this file — that
is the point: the schema must be exercisable without any unapproved business
value existing anywhere.
"""

import datetime
import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from onyx.db.enums import AccountType
from onyx.db.models import User
from onyx.db.ton.enums import (
    AnalysisSpecialist,
    AnalysisStepCode,
    AnalysisStepStatus,
    AnalysisTrigger,
    BusinessUnitKind,
    ContractStatus,
    EvidenceConfidenceLevel,
    MissingDataBehavior,
    PostResolutionPolicy,
    RuleDomain,
    RuleKind,
    RuleProvenance,
    RuleVersionStatus,
    SourceType,
)
from onyx.db.ton.models import (
    AnalysisRun,
    AnalysisStep,
    BusinessUnit,
    Contract,
    Rule,
    RuleVersion,
    SourceSnapshot,
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
