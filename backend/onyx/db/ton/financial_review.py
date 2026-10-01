"""DATA-003 persistence: rule registration, review runs, findings, decisions.

Reuses the 003b/003c spine. Rules become ``Rule``/``RuleVersion`` rows, a review
is an ``AnalysisRun`` plus its ``ReviewRun`` extension, every detection goes
through ``record_detection__no_commit`` into ``Finding``/``Occurrence``, and
human decisions append ``OccurrenceEvent`` rows through
``apply_transition__no_commit``. Callers own commits.
"""

import datetime
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import import_profiles
from onyx.db.ton.acl import (
    assert_can_manage_occurrence,
    finding_visible_clause,
    get_finding_for_user,
    get_occurrence_for_user,
    holds_ton_read_capability,
    is_ton_administrator,
)
from onyx.db.ton.analysis_runs import (
    attach_source_snapshot__no_commit,
    get_or_create_analysis_run__no_commit,
)
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import (
    AnalysisRunErrorClass,
    AnalysisRunStatus,
    AnalysisSpecialist,
    AnalysisTrigger,
    EvidenceConfidenceLevel,
    FindingKind,
    OccurrenceActorKind,
    OccurrenceCriticality,
    OccurrenceLedgerKind,
    OccurrenceStatus,
    OccurrenceTransition,
    OccurrenceVerificationResult,
    RedactionLevel,
    RuleDomain,
    RuleKind,
    RuleVersionOutcome,
    SourceType,
    TonAuditResourceKind,
    TonSharePermission,
)
from onyx.db.ton.findings import create_finding__no_commit
from onyx.db.ton.identity import compute_identity_key
from onyx.db.ton.models import (
    AnalysisRun,
    AnalysisRunRuleVersion,
    Finding,
    FindingEvidence,
    ImportProfileExecution,
    Occurrence,
    Occurrence__UserGroup,
    OccurrenceEvent,
    ParsedSourceRecord,
    ReviewDecision,
    ReviewRecommendation,
    ReviewRun,
    Rule,
    RuleVersion,
    Source__UserGroup,
    SourceSnapshot,
)
from onyx.db.ton.occurrences import (
    OPEN_STATUSES,
    apply_transition__no_commit,
    record_detection__no_commit,
    record_verification__no_commit,
    resolve_occurrence__no_commit,
)
from onyx.db.ton.rule_versions import compute_definition_hash
from onyx.db.ton.sources import check_page, get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.financial_review.adapters import review_record
from onyx.ton.financial_review.catalog import (
    ENGINE_VERSION,
    IDENTITY_COMPONENTS,
    RuleCatalog,
    RuleDefinition,
    rule_version_fields,
)
from onyx.ton.financial_review.dataset import EventFact, FindingState, state_as_of
from onyx.ton.financial_review.models import (
    Detection,
    DetectionScope,
    EngineRuleStatus,
    EvaluatedDetection,
    ReviewDecisionKind,
    ReviewDecisionRequest,
    ReviewEvaluationResult,
    ReviewRecord,
    ReviewRunStatus,
    VerificationReason,
)
from onyx.ton.financial_review.rules import VerificationMode
from onyx.ton.ng_financial.models import ParseDiagnostic, ProfileExecutionStatus
from onyx.ton.ng_financial.parser import AMOUNT_FIELDS
from onyx.utils.audit import AuditAction, AuditOutcome

FINDING_SCHEMA = "ngf-finding-1"
EVIDENCE_BATCH = 500
REVIEWABLE_EXECUTION_STATUSES = frozenset(
    {ProfileExecutionStatus.SUCCEEDED, ProfileExecutionStatus.PARTIAL}
)
# A RUNNING review older than this is treated as abandoned by a crashed process.
STALE_RUNNING_AFTER = datetime.timedelta(minutes=15)
# Human closures that a repeated detection under the same rule version keeps.
STICKY_HUMAN_STATUSES = frozenset(
    {OccurrenceStatus.RISK_ACCEPTED, OccurrenceStatus.DISMISSED}
)


class RuleCatalogConflict(Exception):
    """A stored rule version no longer matches its code definition."""


@dataclass(frozen=True)
class RegisteredRule:
    definition: RuleDefinition
    rule: Rule
    rule_version: RuleVersion


# ---------------------------------------------------------------------------
# Rule registration
# ---------------------------------------------------------------------------


def register_catalog__no_commit(
    session: Session, catalog: RuleCatalog
) -> dict[str, RegisteredRule]:
    """Insert missing Rule/RuleVersion rows and verify stored definitions.

    Concurrency-safe: both inserts use ``ON CONFLICT DO NOTHING`` and re-read.
    A stored version with a different definition hash refuses the whole catalog.
    """
    definitions = list(catalog)
    kinds = {item.key: item.rule_kind for item in definitions}
    session.execute(
        pg_insert(Rule)
        .values(
            [
                {
                    "id": uuid4(),
                    "code": item.key,
                    "domain": RuleDomain.FINANCIAL,
                    "kind": item.rule_kind,
                }
                for item in definitions
            ]
        )
        .on_conflict_do_nothing(index_elements=["code"])
    )
    rules = {
        rule.code: rule
        for rule in session.scalars(sa.select(Rule).where(Rule.code.in_(kinds)))
    }
    for code, rule in rules.items():
        if rule.domain is not RuleDomain.FINANCIAL or rule.kind is not kinds[code]:
            raise RuleCatalogConflict(f"Rule {code} has a different domain or kind")

    expected: dict[str, tuple[dict[str, Any], str]] = {}
    for item in definitions:
        fields = rule_version_fields(item)
        transient = RuleVersion(rule_id=rules[item.key].id, **fields)
        expected[item.key] = (
            fields,
            compute_definition_hash(transient, rule_code=item.key),
        )
    session.execute(
        pg_insert(RuleVersion)
        .values(
            [
                {
                    "id": uuid4(),
                    "rule_id": rules[item.key].id,
                    "definition_hash": expected[item.key][1],
                    **expected[item.key][0],
                }
                for item in definitions
            ]
        )
        .on_conflict_do_nothing(constraint="uq_ton_rule_version_rule_version")
    )
    stored = session.scalars(
        sa.select(RuleVersion).where(
            sa.tuple_(RuleVersion.rule_id, RuleVersion.version).in_(
                [(rules[item.key].id, item.version) for item in definitions]
            )
        )
    ).all()
    by_rule = {version.rule_id: version for version in stored}
    registered: dict[str, RegisteredRule] = {}
    for item in definitions:
        rule_version = by_rule[rules[item.key].id]
        if rule_version.definition_hash != expected[item.key][1]:
            raise RuleCatalogConflict(
                f"{item.key} v{item.version} differs from its stored definition"
            )
        registered[item.key] = RegisteredRule(item, rules[item.key], rule_version)
    return registered


def rule_set_entries(registered: Mapping[str, RegisteredRule]) -> list[dict[str, Any]]:
    return [
        {
            "rule_key": key,
            "version": item.definition.version,
            "engine_status": item.definition.status.value,
            "rule_version_id": str(item.rule_version.id),
            "governance_status": item.rule_version.status.value,
            "definition_hash": item.rule_version.definition_hash,
        }
        for key, item in sorted(registered.items())
    ]


# ---------------------------------------------------------------------------
# Review run lifecycle
# ---------------------------------------------------------------------------


def get_execution_for_review(
    session: Session, user: User, source_id: UUID, execution_id: UUID
) -> ImportProfileExecution:
    execution = import_profiles.get_execution(
        session, user, source_id, execution_id, Permission.IMPORT_TON_SOURCES
    )
    if execution.status not in REVIEWABLE_EXECUTION_STATUSES:
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "Only a finished parse execution can be reviewed"
        )
    return execution


def find_reusable_run(
    session: Session, execution_id: UUID, digest: str
) -> ReviewRun | None:
    return session.scalar(
        sa.select(ReviewRun)
        .where(
            ReviewRun.execution_id == execution_id,
            ReviewRun.rule_set_digest == digest,
            ReviewRun.status == ReviewRunStatus.SUCCEEDED,
        )
        .order_by(ReviewRun.attempt_no)
        .limit(1)
    )


def claim_attempt__no_commit(
    session: Session, execution_id: UUID, digest: str, now: datetime.datetime
) -> int:
    """Next attempt number. Refuses while a live attempt is RUNNING."""
    runs = session.scalars(
        sa.select(ReviewRun)
        .where(
            ReviewRun.execution_id == execution_id,
            ReviewRun.rule_set_digest == digest,
        )
        .with_for_update()
    ).all()
    for run in runs:
        if run.status is ReviewRunStatus.RUNNING:
            if now - run.started_at < STALE_RUNNING_AFTER:
                raise OnyxError(
                    OnyxErrorCode.CONFLICT, "A review of this execution is running"
                )
            _finish_failed(session, run, "ABANDONED", now)
    return max((run.attempt_no for run in runs), default=0) + 1


def _finish_failed(
    session: Session, run: ReviewRun, error_code: str, now: datetime.datetime
) -> None:
    run.status = ReviewRunStatus.FAILED
    run.error_code = error_code
    run.finished_at = now
    analysis_run = session.get(AnalysisRun, run.analysis_run_id)
    if analysis_run is not None:
        analysis_run.status = AnalysisRunStatus.FAILED
        analysis_run.error_class = AnalysisRunErrorClass.RULE_EXECUTION_ERROR
        analysis_run.finished_at = now
    session.flush()


def start_review_run__no_commit(
    session: Session,
    *,
    user: User,
    execution: ImportProfileExecution,
    registered: Mapping[str, RegisteredRule],
    digest: str,
    attempt_no: int,
    now: datetime.datetime,
) -> ReviewRun:
    snapshot = session.get(SourceSnapshot, execution.snapshot_id)
    assert snapshot is not None
    period = session.execute(
        sa.select(
            sa.func.min(ParsedSourceRecord.emission_date),
            sa.func.max(ParsedSourceRecord.emission_date),
        ).where(ParsedSourceRecord.execution_id == execution.id)
    ).one()
    fallback = snapshot.extracted_at.date()
    analysis_run, _created = get_or_create_analysis_run__no_commit(
        session,
        idempotency_key=f"ton-review:{execution.id}:{digest}:{attempt_no}",
        trigger=AnalysisTrigger.INTERACTIVE,
        specialist=AnalysisSpecialist.AUDITOR,
        domain=RuleDomain.FINANCIAL,
        period_start=period[0] or fallback,
        period_end=period[1] or fallback,
        executor_version=ENGINE_VERSION,
        triggered_by_user_id=user.id,
        routine_code="DATA-003",
    )
    analysis_run.status = AnalysisRunStatus.RUNNING
    analysis_run.started_at = now
    attach_source_snapshot__no_commit(
        session, analysis_run=analysis_run, source_snapshot=snapshot
    )
    run = ReviewRun(
        analysis_run_id=analysis_run.id,
        source_id=execution.source_id,
        snapshot_id=execution.snapshot_id,
        execution_id=execution.id,
        status=ReviewRunStatus.RUNNING,
        attempt_no=attempt_no,
        engine_version=ENGINE_VERSION,
        rule_set_digest=digest,
        rule_set=rule_set_entries(registered),
        rule_evaluations=[],
        diagnostic_summary={},
        statistics={},
        triggered_by=user.id,
        started_at=now,
    )
    session.add(run)
    session.flush()
    _audit_run(session, user, run, AuditAction.TON_REVIEW_START)
    return run


def _audit_run(
    session: Session,
    user: User | None,
    run: ReviewRun,
    action: AuditAction,
    extra: Mapping[str, Any] | None = None,
) -> None:
    emit_ton_audit_event(
        session,
        action=action,
        outcome=AuditOutcome.FAILURE
        if action is AuditAction.TON_REVIEW_FAIL
        else AuditOutcome.SUCCESS,
        actor_user_id=user.id if user is not None else None,
        resource_kind=TonAuditResourceKind.REVIEW_RUN,
        resource_id=run.id,
        extra=extra,
    )


def fail_review_run__no_commit(
    session: Session, user: User, run_id: UUID, error_code: str
) -> None:
    run = session.get(ReviewRun, run_id, populate_existing=True)
    if run is None or run.status is not ReviewRunStatus.RUNNING:
        return
    _finish_failed(session, run, error_code, datetime.datetime.now(datetime.UTC))
    _audit_run(session, user, run, AuditAction.TON_REVIEW_FAIL, {"error": error_code})


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def load_review_inputs(
    session: Session, execution: ImportProfileExecution
) -> tuple[list[ReviewRecord], list[ParseDiagnostic]]:
    """One query for every record; only the columns rules need."""
    table = ParsedSourceRecord
    amount_columns = [table.__table__.c[name] for name in AMOUNT_FIELDS]
    rows = session.execute(
        sa.select(
            table.id,
            table.sheet_name,
            table.source_row_number,
            table.sheet_month,
            table.account_code,
            table.account_label,
            table.emission_date,
            table.administrative_unit,
            table.document_number,
            table.history,
            table.fingerprint,
            table.duplicate_ordinal,
            table.source_values.op("->>")("B").label("physical_date"),
            table.source_values.op("->>")("C").label("physical_unit"),
            *amount_columns,
        )
        .where(table.execution_id == execution.id)
        .order_by(table.sheet_month, table.source_row_number)
    ).all()
    records = [
        review_record(
            record_id=row.id,
            sheet_name=row.sheet_name,
            row_number=row.source_row_number,
            sheet_month=row.sheet_month,
            account_code=row.account_code,
            account_label=row.account_label,
            emission_date=row.emission_date,
            administrative_unit=row.administrative_unit,
            document_number=row.document_number,
            history=row.history,
            amounts={name: row._mapping[name] for name in AMOUNT_FIELDS},
            physical_date=row.physical_date,
            physical_unit=row.physical_unit,
            fingerprint=row.fingerprint,
            duplicate_ordinal=row.duplicate_ordinal,
        )
        for row in rows
    ]
    diagnostics = [
        ParseDiagnostic.model_validate(item) for item in execution.diagnostics
    ]
    return records, diagnostics


# ---------------------------------------------------------------------------
# Result persistence
# ---------------------------------------------------------------------------


def _identity_values(
    source_id: UUID, detection_month: int | None, review_key: str
) -> dict[str, object | None]:
    return {
        "source_system": f"ton-source:{source_id}",
        "period": None if detection_month is None else f"month-{detection_month:02d}",
        "source_record_key": review_key,
    }


def _finding_kind(definition: RuleDefinition, scope: DetectionScope) -> FindingKind:
    if scope is DetectionScope.EXECUTION:
        return FindingKind.BLIND_SPOT
    if definition.rule_kind is RuleKind.SANITY:
        return FindingKind.SANITY_VIOLATION
    return FindingKind.DETECTION


def _payload(
    item: EvaluatedDetection, definition: RuleDefinition, run: ReviewRun
) -> dict[str, Any]:
    detection = item.detection
    impact = detection.impact
    return {
        "schema": FINDING_SCHEMA,
        "rule_key": definition.key,
        "rule_version": definition.version,
        "rule_type": definition.rule_type.value,
        "category": definition.category.value,
        "related_categories": [value.value for value in definition.related_categories],
        "origin": definition.origin.value,
        "blocking": definition.blocking,
        "scope": detection.scope.value,
        "review_run_id": str(run.id),
        "source_id": str(run.source_id),
        "snapshot_id": str(run.snapshot_id),
        "execution_id": str(run.execution_id),
        "sheet_month": detection.sheet_month,
        "review_key": detection.review_key,
        "base_key": detection.base_key,
        "base_key_count": detection.base_key_count,
        "record_count": len(detection.record_ids),
        "diagnostic_count": len(detection.diagnostics),
        "facts": dict(detection.facts),
        "impact": {
            "status": impact.status.value,
            "method": impact.method,
            "basis": impact.basis,
            "amount": None if impact.amount is None else format(impact.amount, "f"),
        },
        "explanation": item.explanation,
        "explanation_code": f"{definition.key}.v{definition.version}",
    }


def _latest_occurrences(
    session: Session, logical_keys: Sequence[str]
) -> dict[str, Occurrence]:
    if not logical_keys:
        return {}
    rows = session.scalars(
        sa.select(Occurrence)
        .where(Occurrence.logical_identity_key.in_(logical_keys))
        .order_by(Occurrence.logical_identity_key, Occurrence.supersede_generation)
    ).all()
    return {row.logical_identity_key: row for row in rows}


def _sticky_repeat(
    session: Session,
    *,
    occurrence: Occurrence,
    analysis_run_id: UUID,
    rule_version: RuleVersion,
    finding_kind: FindingKind,
    detected_at: datetime.datetime,
    payload: dict[str, Any],
) -> Finding:
    """Record a repeat without reopening a justified or dismissed case."""
    finding = create_finding__no_commit(
        session,
        analysis_run_id=analysis_run_id,
        rule_version=rule_version,
        occurrence=occurrence,
        identity_key=occurrence.identity_key,
        finding_kind=finding_kind,
        domain=RuleDomain.FINANCIAL,
        detected_at=detected_at,
        deterministic_payload=payload,
        nc_code=rule_version.nc_code,
    )
    apply_transition__no_commit(
        session,
        occurrence=occurrence,
        transition=OccurrenceTransition.REPEAT_DETECTED,
        actor_kind=OccurrenceActorKind.SYSTEM,
        reason="Detected again; the human decision under this rule version stands.",
        finding_id=finding.id,
        rule_version_id=rule_version.id,
        occurred_at=detected_at,
    )
    return finding


@dataclass
class PersistedReview:
    finding_ids: list[UUID]
    detected_occurrence_ids: set[UUID]
    statistics: dict[str, int]


def persist_review_result__no_commit(
    session: Session,
    *,
    run: ReviewRun,
    registered: Mapping[str, RegisteredRule],
    result: ReviewEvaluationResult,
    records: Mapping[UUID, ReviewRecord],
    now: datetime.datetime,
) -> PersistedReview:
    analysis_run = session.get(AnalysisRun, run.analysis_run_id)
    assert analysis_run is not None
    logical_keys = {
        id(item): compute_identity_key(
            rule_code=item.detection.rule_key,
            components=IDENTITY_COMPONENTS,
            values=_identity_values(
                run.source_id, item.detection.sheet_month, item.detection.review_key
            ),
        )
        for item in result.detections
    }
    existing = _latest_occurrences(session, sorted(set(logical_keys.values())))
    outcomes: Counter[str] = Counter()
    new_occurrence_ids: set[UUID] = set()
    detected: set[UUID] = set()
    evidence_rows: list[dict[str, Any]] = []
    recommendation_rows: list[dict[str, Any]] = []
    finding_ids: list[UUID] = []
    per_rule: Counter[str] = Counter()

    for item in result.detections:
        detection = item.detection
        entry = registered[detection.rule_key]
        definition = entry.definition
        payload = _payload(item, definition, run)
        kind = _finding_kind(definition, detection.scope)
        prior = existing.get(logical_keys[id(item)])
        if (
            prior is not None
            and prior.status in STICKY_HUMAN_STATUSES
            and prior.current_rule_version_id == entry.rule_version.id
        ):
            finding = _sticky_repeat(
                session,
                occurrence=prior,
                analysis_run_id=analysis_run.id,
                rule_version=entry.rule_version,
                finding_kind=kind,
                detected_at=now,
                payload=payload,
            )
            occurrence_id = prior.id
            outcomes["REPEATED_HUMAN_DECISION_KEPT"] += 1
        else:
            outcome = record_detection__no_commit(
                session,
                analysis_run_id=analysis_run.id,
                rule=entry.rule,
                rule_version=entry.rule_version,
                identity_values=_identity_values(
                    run.source_id, detection.sheet_month, detection.review_key
                ),
                finding_kind=kind,
                title=definition.name,
                owning_domain=RuleDomain.FINANCIAL,
                ledger_kind=OccurrenceLedgerKind.EXCEPTION,
                criticality=definition.severity,
                detected_at=now,
                verification_criterion=definition.verification_criterion,
                deterministic_payload=payload,
            )
            finding = outcome.finding
            occurrence_id = outcome.occurrence.id
            outcomes[outcome.outcome.value] += 1
            if outcome.outcome.value in ("NEW", "SUPERSEDED"):
                new_occurrence_ids.add(occurrence_id)
        detected.add(occurrence_id)
        finding_ids.append(finding.id)
        per_rule[definition.key] += 1
        evidence_rows.extend(_evidence_rows(finding.id, detection, records, run))
        recommendation = item.recommendation
        recommendation_rows.append(
            {
                "id": uuid4(),
                "finding_id": finding.id,
                "review_run_id": run.id,
                "kind": recommendation.kind,
                "evidence_level": recommendation.evidence_level,
                "rationale_code": recommendation.rationale_code,
                "explanation": recommendation.explanation,
                "target_field": recommendation.target_field,
                "suggested_value": recommendation.suggested_value,
                "candidate_count": recommendation.candidate_count,
                "created_at": now,
            }
        )

    evidence_table = cast(sa.Table, FindingEvidence.__table__)
    for start in range(0, len(evidence_rows), EVIDENCE_BATCH):
        session.execute(
            sa.insert(evidence_table), evidence_rows[start : start + EVIDENCE_BATCH]
        )
    if recommendation_rows:
        session.execute(
            sa.insert(cast(sa.Table, ReviewRecommendation.__table__)),
            recommendation_rows,
        )
    _share_new_occurrences(session, run.source_id, new_occurrence_ids)
    _record_outcomes(session, analysis_run.id, registered, result, per_rule)
    session.flush()
    statistics = {
        "findings_created": len(finding_ids),
        "evidence_rows": len(evidence_rows),
        "recommendations_created": len(recommendation_rows),
        **{f"occurrences_{name.lower()}": count for name, count in outcomes.items()},
    }
    return PersistedReview(finding_ids, detected, statistics)


def _evidence_rows(
    finding_id: UUID,
    detection: Detection,
    records: Mapping[UUID, ReviewRecord],
    run: ReviewRun,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    role = {
        DetectionScope.RECORD: "subject",
        DetectionScope.RECORD_GROUP: "member",
    }.get(detection.scope, "representative")
    base = {
        "finding_id": finding_id,
        "source_snapshot_id": run.snapshot_id,
        "source_type": SourceType.NG_KEEVO,
        "confidence_level": EvidenceConfidenceLevel.A,
        "record_key": None,
        "file_record_id": None,
        "document_id": None,
        "chat_message_id": None,
        "extracted_value": None,
        "value_scale": None,
        "value_unit": None,
        "value_currency": None,
        "is_non_standard_source": False,
        "redaction_level": RedactionLevel.NONE,
        "import_execution_id": run.execution_id,
    }
    for record_id in detection.record_ids:
        record = records[record_id]
        rows.append(
            {
                **base,
                "id": uuid4(),
                "parsed_record_id": record_id,
                "locator": {
                    "kind": "parsed_record",
                    "role": role,
                    "sheet": record.sheet_name,
                    "row": record.row_number,
                    "sheet_month": record.sheet_month,
                    "execution_id": str(run.execution_id),
                    "parsed_record_id": str(record_id),
                },
            }
        )
    rows.extend(
        {
            **base,
            "id": uuid4(),
            "parsed_record_id": None,
            "locator": {
                "kind": "parse_diagnostic",
                "role": "subject",
                "sheet": diagnostic.sheet_name,
                "row": diagnostic.row_number,
                "column": diagnostic.column,
                "diagnostic_code": diagnostic.code.value,
                "diagnostic_level": diagnostic.level.value,
                "execution_id": str(run.execution_id),
            },
        }
        for diagnostic in detection.diagnostics
    )
    if not rows:
        rows.append(
            {
                **base,
                "id": uuid4(),
                "parsed_record_id": None,
                "locator": {
                    "kind": "parse_execution",
                    "role": "scope",
                    "execution_id": str(run.execution_id),
                },
            }
        )
    return rows


def _share_new_occurrences(
    session: Session, source_id: UUID, occurrence_ids: set[UUID]
) -> None:
    """New cases inherit the source groups. Existing cases keep their ACL."""
    if not occurrence_ids:
        return
    groups = list(
        session.scalars(
            sa.select(Source__UserGroup.user_group_id).where(
                Source__UserGroup.source_id == source_id
            )
        )
    )
    if not groups:
        return
    session.execute(
        pg_insert(Occurrence__UserGroup)
        .values(
            [
                {
                    "occurrence_id": occurrence_id,
                    "user_group_id": group_id,
                    "permission": TonSharePermission.EDITOR,
                }
                for occurrence_id in sorted(occurrence_ids, key=str)
                for group_id in groups
            ]
        )
        .on_conflict_do_nothing()
    )


def _record_outcomes(
    session: Session,
    analysis_run_id: UUID,
    registered: Mapping[str, RegisteredRule],
    result: ReviewEvaluationResult,
    per_rule: Mapping[str, int],
) -> None:
    statement = pg_insert(AnalysisRunRuleVersion).values(
        [
            {
                "analysis_run_id": analysis_run_id,
                "rule_version_id": registered[item.rule_key].rule_version.id,
                "outcome": item.outcome,
                "finding_count": per_rule.get(item.rule_key, 0)
                if item.outcome is RuleVersionOutcome.EXECUTED
                else 0,
            }
            for item in result.evaluations
        ]
    )
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[
                AnalysisRunRuleVersion.analysis_run_id,
                AnalysisRunRuleVersion.rule_version_id,
            ],
            set_={
                "outcome": statement.excluded.outcome,
                "finding_count": statement.excluded.finding_count,
            },
        )
    )


# ---------------------------------------------------------------------------
# Cross-import correction verification
# ---------------------------------------------------------------------------


def verify_prior_occurrences__no_commit(
    session: Session,
    *,
    user: User,
    run: ReviewRun,
    registered: Mapping[str, RegisteredRule],
    result: ReviewEvaluationResult,
    detected: set[UUID],
    now: datetime.datetime,
) -> dict[str, int]:
    """Check open cases from earlier snapshots that this import did not re-detect.

    PASSED only when the correspondence is unique on both sides. Location-only
    and ambiguous cases are INCONCLUSIVE and stay with a human.
    """
    active = {
        item.rule.id: key
        for key, item in registered.items()
        if item.definition.status is EngineRuleStatus.ACTIVE
    }
    if not active:
        return {}
    current = session.get(SourceSnapshot, run.snapshot_id)
    assert current is not None
    latest = (
        sa.select(
            Finding.occurrence_id,
            Finding.deterministic_payload,
            ReviewRun.snapshot_id,
            SourceSnapshot.created_at,
        )
        .join(ReviewRun, ReviewRun.analysis_run_id == Finding.analysis_run_id)
        .join(Occurrence, Occurrence.id == Finding.occurrence_id)
        .join(SourceSnapshot, SourceSnapshot.id == ReviewRun.snapshot_id)
        .where(
            ReviewRun.source_id == run.source_id,
            Occurrence.rule_id.in_(active),
            Occurrence.status.in_(list(OPEN_STATUSES)),
        )
        .order_by(Finding.occurrence_id, Finding.detected_at.desc(), Finding.id.desc())
        .distinct(Finding.occurrence_id)
    )
    candidates = [
        row
        for row in session.execute(latest).all()
        if row.occurrence_id not in detected
        and row.snapshot_id != run.snapshot_id
        and row.created_at < current.created_at
    ]
    counts: Counter[str] = Counter()
    if not candidates:
        return {}
    occurrences = {
        row.id: row
        for row in session.scalars(
            sa.select(Occurrence).where(
                Occurrence.id.in_([row.occurrence_id for row in candidates])
            )
        )
    }
    for row in candidates:
        payload = row.deterministic_payload
        rule_key = str(payload.get("rule_key"))
        mode = (payload.get("facts") or {}).get("verification_mode")
        present = result.verification_index.get(rule_key, {}).get(
            str(payload.get("base_key")), 0
        )
        verdict, reason = _verdict(
            mode, int(payload.get("base_key_count") or 0), present
        )
        occurrence = occurrences[row.occurrence_id]
        record_verification__no_commit(
            session,
            occurrence=occurrence,
            result=verdict,
            checked_at=now,
            reason=reason.value,
        )
        counts[f"verification_{verdict.value.lower()}"] += 1
        if verdict is OccurrenceVerificationResult.PASSED:
            emit_ton_audit_event(
                session,
                action=AuditAction.TON_REVIEW_VERIFY,
                outcome=AuditOutcome.SUCCESS,
                actor_user_id=user.id,
                resource_kind=TonAuditResourceKind.OCCURRENCE,
                resource_id=occurrence.id,
                extra={"review_run_id": str(run.id), "reason": reason.value},
            )
    return dict(counts)


def _verdict(
    mode: object, count_before: int, count_now: int
) -> tuple[OccurrenceVerificationResult, VerificationReason]:
    if mode == VerificationMode.LOCATION or mode is None:
        return (
            OccurrenceVerificationResult.INCONCLUSIVE,
            VerificationReason.LOCATION_ONLY_IDENTITY,
        )
    if count_now == 0:
        return (
            OccurrenceVerificationResult.INCONCLUSIVE,
            VerificationReason.NO_CORRESPONDING_RECORD,
        )
    unique_before = mode != VerificationMode.RECORD or count_before == 1
    if count_now == 1 and unique_before:
        return (
            OccurrenceVerificationResult.PASSED,
            VerificationReason.VIOLATION_ABSENT_UNIQUE_MATCH,
        )
    return (
        OccurrenceVerificationResult.INCONCLUSIVE,
        VerificationReason.AMBIGUOUS_CORRESPONDENCE,
    )


def finish_review_run__no_commit(
    session: Session,
    *,
    user: User,
    run: ReviewRun,
    result: ReviewEvaluationResult,
    statistics: Mapping[str, int],
    now: datetime.datetime,
) -> None:
    run.status = ReviewRunStatus.SUCCEEDED
    run.finished_at = now
    run.statistics = dict(sorted(statistics.items()))
    run.rule_evaluations = [
        {
            "rule_key": item.rule_key,
            "rule_version": item.rule_version,
            "engine_status": item.engine_status.value,
            "outcome": item.outcome.value,
            "detection_count": item.detection_count,
            "observations": dict(item.observations),
            "skip_reason": item.skip_reason,
        }
        for item in result.evaluations
    ]
    run.diagnostic_summary = {
        key: dict(value) for key, value in result.diagnostic_summary.items()
    }
    analysis_run = session.get(AnalysisRun, run.analysis_run_id)
    assert analysis_run is not None
    analysis_run.status = AnalysisRunStatus.COMPLETED
    analysis_run.finished_at = now
    session.flush()
    _audit_run(
        session,
        user,
        run,
        AuditAction.TON_REVIEW_SUCCEED,
        {
            "findings_created": statistics.get("findings_created", 0),
            "recommendations_created": statistics.get("recommendations_created", 0),
        },
    )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def get_review_run(
    session: Session, user: User, source_id: UUID, review_run_id: UUID
) -> ReviewRun:
    get_source(session, user, source_id)
    run = session.scalar(
        sa.select(ReviewRun)
        .where(ReviewRun.id == review_run_id, ReviewRun.source_id == source_id)
        .execution_options(populate_existing=True)
    )
    if run is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Review run not found")
    return run


def list_review_runs(
    session: Session,
    user: User,
    source_id: UUID,
    limit: int,
    offset: int,
    *,
    execution_id: UUID | None = None,
    status: ReviewRunStatus | None = None,
) -> list[ReviewRun]:
    get_source(session, user, source_id)
    check_page(limit, offset)
    query = sa.select(ReviewRun).where(ReviewRun.source_id == source_id)
    if execution_id is not None:
        query = query.where(ReviewRun.execution_id == execution_id)
    if status is not None:
        query = query.where(ReviewRun.status == status)
    return list(
        session.scalars(
            query.order_by(ReviewRun.started_at.desc(), ReviewRun.id)
            .limit(limit)
            .offset(offset)
        )
    )


def rule_outcome_counts(session: Session, run: ReviewRun) -> dict[UUID, int]:
    return {
        row.rule_version_id: row.finding_count
        for row in session.scalars(
            sa.select(AnalysisRunRuleVersion).where(
                AnalysisRunRuleVersion.analysis_run_id == run.analysis_run_id
            )
        )
    }


def _payload_text(name: str) -> sa.ColumnElement[str]:
    return Finding.deterministic_payload.op("->>")(name)


@dataclass(frozen=True)
class FindingFilters:
    source_id: UUID | None = None
    review_run_id: UUID | None = None
    execution_id: UUID | None = None
    rule_key: str | None = None
    category: str | None = None
    criticality: OccurrenceCriticality | None = None
    status: OccurrenceStatus | None = None
    sheet_month: int | None = None
    blocking: bool | None = None


@dataclass(frozen=True)
class FindingRow:
    finding: Finding
    occurrence: Occurrence
    rule_key: str
    rule_version: int
    review_run_id: UUID | None


# Aliased so the ACL EXISTS subquery keeps its own occurrence FROM instead of
# auto-correlating to the joined row.
_CASE = aliased(Occurrence)


def _finding_query(user: User) -> sa.Select[Any]:
    return (
        sa.select(Finding, _CASE, Rule.code, RuleVersion.version, ReviewRun.id)
        .select_from(Finding)
        .join(_CASE, _CASE.id == Finding.occurrence_id)
        .join(RuleVersion, RuleVersion.id == Finding.rule_version_id)
        .join(Rule, Rule.id == RuleVersion.rule_id)
        .outerjoin(ReviewRun, ReviewRun.analysis_run_id == Finding.analysis_run_id)
        .where(
            _payload_text("schema") == FINDING_SCHEMA,
            finding_visible_clause(user),
        )
    )


def list_findings_for_user(
    session: Session, user: User, filters: FindingFilters, limit: int, offset: int
) -> list[FindingRow]:
    check_page(limit, offset)
    if not holds_ton_read_capability(user) and not is_ton_administrator(user):
        return []
    query = _finding_query(user)
    if filters.source_id is not None:
        query = query.where(ReviewRun.source_id == filters.source_id)
    if filters.review_run_id is not None:
        query = query.where(ReviewRun.id == filters.review_run_id)
    if filters.execution_id is not None:
        query = query.where(ReviewRun.execution_id == filters.execution_id)
    if filters.rule_key is not None:
        query = query.where(Rule.code == filters.rule_key)
    if filters.category is not None:
        query = query.where(_payload_text("category") == filters.category)
    if filters.criticality is not None:
        query = query.where(_CASE.criticality == filters.criticality)
    if filters.status is not None:
        query = query.where(_CASE.status == filters.status)
    if filters.sheet_month is not None:
        query = query.where(_payload_text("sheet_month") == str(filters.sheet_month))
    if filters.blocking is not None:
        query = query.where(
            _payload_text("blocking") == ("true" if filters.blocking else "false")
        )
    rows = session.execute(
        query.order_by(Finding.detected_at.desc(), Finding.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return [FindingRow(row[0], row[1], row[2], row[3], row[4]) for row in rows]


def get_review_finding_for_user(
    session: Session, user: User, finding_id: UUID
) -> FindingRow:
    get_finding_for_user(session, user, finding_id)
    row = session.execute(
        _finding_query(user).where(Finding.id == finding_id)
    ).one_or_none()
    if row is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Review finding not found")
    return FindingRow(row[0], row[1], row[2], row[3], row[4])


def list_recommendations(
    session: Session, finding_ids: Sequence[UUID]
) -> list[ReviewRecommendation]:
    if not finding_ids:
        return []
    return list(
        session.scalars(
            sa.select(ReviewRecommendation)
            .where(ReviewRecommendation.finding_id.in_(finding_ids))
            .order_by(ReviewRecommendation.created_at, ReviewRecommendation.id)
        )
    )


def list_evidence_for_user(
    session: Session, user: User, finding_id: UUID, limit: int, offset: int
) -> list[FindingEvidence]:
    check_page(limit, offset)
    get_review_finding_for_user(session, user, finding_id)
    return list(
        session.scalars(
            sa.select(FindingEvidence)
            .where(FindingEvidence.finding_id == finding_id)
            .order_by(FindingEvidence.id)
            .limit(limit)
            .offset(offset)
        )
    )


def list_decisions_for_user(
    session: Session, user: User, occurrence_id: UUID, limit: int, offset: int
) -> list[ReviewDecision]:
    check_page(limit, offset)
    get_occurrence_for_user(session, user, occurrence_id)
    return list(
        session.scalars(
            sa.select(ReviewDecision)
            .where(ReviewDecision.occurrence_id == occurrence_id)
            .order_by(ReviewDecision.created_at, ReviewDecision.id)
            .limit(limit)
            .offset(offset)
        )
    )


# ---------------------------------------------------------------------------
# Human decisions
# ---------------------------------------------------------------------------

_DECISION_AUDIT: dict[ReviewDecisionKind, AuditAction] = {
    ReviewDecisionKind.ACKNOWLEDGE: AuditAction.TON_REVIEW_ACKNOWLEDGE,
    ReviewDecisionKind.REQUEST_SOURCE_CORRECTION: AuditAction.TON_REVIEW_REQUEST_CORRECTION,
    ReviewDecisionKind.JUSTIFY_EXCEPTION: AuditAction.TON_REVIEW_JUSTIFY,
    ReviewDecisionKind.MARK_FALSE_POSITIVE: AuditAction.TON_REVIEW_FALSE_POSITIVE,
    ReviewDecisionKind.CONFIRM_SOURCE_CORRECTION: AuditAction.TON_REVIEW_CONFIRM_CORRECTION,
    ReviewDecisionKind.ACCEPT_RECOMMENDATION: AuditAction.TON_RECOMMENDATION_ACCEPT,
    ReviewDecisionKind.REJECT_RECOMMENDATION: AuditAction.TON_RECOMMENDATION_REJECT,
}

_RECOMMENDATION_KINDS = frozenset(
    {ReviewDecisionKind.ACCEPT_RECOMMENDATION, ReviewDecisionKind.REJECT_RECOMMENDATION}
)
_AUTHORIZED_KINDS = frozenset(
    {
        ReviewDecisionKind.REQUEST_SOURCE_CORRECTION,
        ReviewDecisionKind.JUSTIFY_EXCEPTION,
        ReviewDecisionKind.MARK_FALSE_POSITIVE,
    }
)


def record_review_decision__no_commit(
    session: Session,
    user: User,
    occurrence_id: UUID,
    request: ReviewDecisionRequest,
    catalog: RuleCatalog,
) -> ReviewDecision:
    occurrence = get_occurrence_for_user(session, user, occurrence_id, editable=True)
    assert_can_manage_occurrence(session, user=user, occurrence=occurrence)
    rule = session.get(Rule, occurrence.rule_id)
    if rule is None or rule.code not in catalog.keys():
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Not a financial review occurrence"
        )
    kind = request.kind
    if occurrence.status not in OPEN_STATUSES:
        raise OnyxError(OnyxErrorCode.CONFLICT, "The occurrence is already closed")
    if (kind in _RECOMMENDATION_KINDS) != (request.recommendation_id is not None):
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "A recommendation id is required for, and only for, recommendation decisions",
        )
    if (kind is ReviewDecisionKind.JUSTIFY_EXCEPTION) != (
        request.justification_category is not None
    ):
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "A justification category is required for, and only for, a justification",
        )
    if kind in _AUTHORIZED_KINDS and request.authorization_reference is None:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "An authorization reference is required"
        )
    if (
        kind is ReviewDecisionKind.CONFIRM_SOURCE_CORRECTION
        and occurrence.requires_human_closure
        and request.authorization_reference is None
    ):
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "An authorization reference is required"
        )
    if request.recommendation_id is not None:
        owned = session.scalar(
            sa.select(ReviewRecommendation.id)
            .join(Finding, Finding.id == ReviewRecommendation.finding_id)
            .where(
                ReviewRecommendation.id == request.recommendation_id,
                Finding.occurrence_id == occurrence.id,
            )
        )
        if owned is None:
            raise OnyxError(OnyxErrorCode.NOT_FOUND, "Recommendation not found")

    context = {
        "review_decision_kind": kind.value,
        "justification_category": (
            request.justification_category.value
            if request.justification_category
            else None
        ),
    }
    event: OccurrenceEvent | None = None
    if kind is ReviewDecisionKind.REQUEST_SOURCE_CORRECTION:
        if occurrence.status is OccurrenceStatus.CONFIRMED:
            raise OnyxError(
                OnyxErrorCode.CONFLICT, "A correction was already requested"
            )
        event = _human_transition(
            session,
            occurrence,
            user,
            OccurrenceTransition.ASSERT_NONCOMPLIANCE,
            request,
            context,
        )
    elif kind is ReviewDecisionKind.JUSTIFY_EXCEPTION:
        event = _human_transition(
            session,
            occurrence,
            user,
            OccurrenceTransition.ACCEPT_RISK,
            request,
            context,
        )
    elif kind is ReviewDecisionKind.MARK_FALSE_POSITIVE:
        event = _human_transition(
            session, occurrence, user, OccurrenceTransition.DISMISS, request, context
        )
    elif kind is ReviewDecisionKind.CONFIRM_SOURCE_CORRECTION:
        event = resolve_occurrence__no_commit(
            session,
            occurrence=occurrence,
            actor_user_id=user.id,
            reason=request.reason,
            authorization_reference=request.authorization_reference,
        )

    decision = ReviewDecision(
        occurrence_id=occurrence.id,
        recommendation_id=request.recommendation_id,
        kind=kind,
        justification_category=request.justification_category,
        reason=request.reason,
        comment=request.comment,
        authorization_reference=request.authorization_reference,
        actor_user_id=user.id,
        occurrence_event_id=event.id if event is not None else None,
    )
    session.add(decision)
    session.flush()
    emit_ton_audit_event(
        session,
        action=_DECISION_AUDIT[kind],
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.OCCURRENCE,
        resource_id=occurrence.id,
        domain_event_id=decision.id,
        authorization_reference=request.authorization_reference,
        extra={"decision_kind": kind.value},
    )
    return decision


def _human_transition(
    session: Session,
    occurrence: Occurrence,
    user: User,
    transition: OccurrenceTransition,
    request: ReviewDecisionRequest,
    context: Mapping[str, Any],
) -> OccurrenceEvent:
    return apply_transition__no_commit(
        session,
        occurrence=occurrence,
        transition=transition,
        actor_kind=OccurrenceActorKind.USER,
        actor_user_id=user.id,
        authorization_reference=request.authorization_reference,
        reason=request.reason,
        context=context,
    )


# ---------------------------------------------------------------------------
# Reviewed dataset inputs
# ---------------------------------------------------------------------------


def load_finding_states(
    session: Session, run: ReviewRun, as_of: datetime.datetime
) -> tuple[list[FindingState], dict[UUID, int]]:
    """Finding states of one run as of an instant, and the event watermark."""
    rows = session.execute(
        sa.select(
            Finding.id,
            Finding.occurrence_id,
            _payload_text("rule_key"),
            _payload_text("blocking"),
            _payload_text("scope"),
            _payload_text("sheet_month"),
        ).where(
            Finding.analysis_run_id == run.analysis_run_id,
            _payload_text("schema") == FINDING_SCHEMA,
        )
    ).all()
    record_links: dict[UUID, list[UUID]] = {row[0]: [] for row in rows}
    if record_links:
        for finding_id, record_id in session.execute(
            sa.select(FindingEvidence.finding_id, FindingEvidence.parsed_record_id)
            .join(Finding, Finding.id == FindingEvidence.finding_id)
            .where(
                Finding.analysis_run_id == run.analysis_run_id,
                FindingEvidence.parsed_record_id.is_not(None),
            )
        ).all():
            if finding_id in record_links and record_id is not None:
                record_links[finding_id].append(record_id)
    occurrence_ids = sorted({row[1] for row in rows}, key=str)
    events: dict[UUID, list[EventFact]] = {item: [] for item in occurrence_ids}
    if occurrence_ids:
        for event in session.execute(
            sa.select(
                OccurrenceEvent.occurrence_id,
                OccurrenceEvent.sequence_no,
                OccurrenceEvent.transition,
                OccurrenceEvent.resulting_status,
                OccurrenceEvent.occurred_at,
                OccurrenceEvent.context.op("->>")("verification_result"),
            )
            .where(OccurrenceEvent.occurrence_id.in_(occurrence_ids))
            .order_by(OccurrenceEvent.occurrence_id, OccurrenceEvent.sequence_no)
        ).all():
            events[event[0]].append(
                EventFact(
                    occurrence_id=event[0],
                    sequence_no=event[1],
                    transition=event[2].value,
                    resulting_status=event[3],
                    occurred_at=event[4],
                    verification_result=event[5],
                )
            )
    snapshots = {
        occurrence_id: state_as_of(items, as_of)
        for occurrence_id, items in events.items()
    }
    states: list[FindingState] = []
    for row in rows:
        status, verification, _last = snapshots[row[1]]
        if status is None:
            # The case did not exist yet at as_of.
            continue
        states.append(
            FindingState(
                finding_id=row[0],
                occurrence_id=row[1],
                rule_key=row[2],
                blocking=row[3] == "true",
                scope=row[4],
                sheet_month=int(row[5]) if row[5] is not None else None,
                record_ids=tuple(record_links[row[0]]),
                status=status,
                verification=verification,
            )
        )
    watermark = {
        occurrence_id: last
        for occurrence_id, (_status, _verification, last) in snapshots.items()
        if last
    }
    return states, watermark


def records_per_month(session: Session, execution_id: UUID) -> dict[int, int]:
    return {
        int(row[0]): int(row[1])
        for row in session.execute(
            sa.select(ParsedSourceRecord.sheet_month, sa.func.count())
            .where(ParsedSourceRecord.execution_id == execution_id)
            .group_by(ParsedSourceRecord.sheet_month)
        ).all()
    }


@dataclass(frozen=True)
class RecordRow:
    id: UUID
    sheet_name: str
    row_number: int
    sheet_month: int
    account_code: str


def list_record_rows(
    session: Session,
    execution_id: UUID,
    *,
    include_ids: Sequence[UUID] | None,
    exclude_ids: Sequence[UUID] | None,
    sheet_month: int | None,
    account_code: str | None,
    administrative_unit: str | None,
    unit_missing: bool | None,
    limit: int,
    offset: int,
) -> list[RecordRow]:
    check_page(limit, offset)
    table = ParsedSourceRecord
    query = sa.select(
        table.id,
        table.sheet_name,
        table.source_row_number,
        table.sheet_month,
        table.account_code,
    ).where(table.execution_id == execution_id)
    if include_ids is not None:
        if not include_ids:
            return []
        query = query.where(table.id.in_(include_ids))
    if exclude_ids:
        query = query.where(table.id.not_in(exclude_ids))
    if sheet_month is not None:
        query = query.where(table.sheet_month == sheet_month)
    if account_code is not None:
        query = query.where(table.account_code == account_code)
    if administrative_unit is not None:
        query = query.where(table.administrative_unit == administrative_unit)
    if unit_missing is not None:
        missing = sa.func.coalesce(sa.func.trim(table.administrative_unit), "") == ""
        query = query.where(missing if unit_missing else ~missing)
    rows = session.execute(
        query.order_by(table.sheet_month, table.source_row_number, table.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return [RecordRow(row[0], row[1], row[2], row[3], row[4]) for row in rows]
