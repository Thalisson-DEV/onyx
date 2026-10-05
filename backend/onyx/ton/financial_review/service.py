"""DATA-003 application service. Owns commits and transaction boundaries.

execute_review has three transactions:

1. register the catalog and commit a RUNNING ReviewRun, so a crash stays visible;
2. evaluate in memory, then persist every finding, evidence row,
   recommendation, rule outcome, verification and the SUCCEEDED state at once;
3. on any failure, roll back step 2 entirely and mark the run FAILED.

A review therefore never leaves half its findings behind, and it never changes
a ParsedSourceRecord or a SourceSnapshot.
"""

import datetime
import time
from collections import Counter
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import financial_review as repository
from onyx.db.ton.canonical import compute_content_hash
from onyx.db.ton.email_flows import emit_flow_event__no_commit
from onyx.db.ton.models import ReviewRun
from onyx.db.ton.sources import check_page
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.financial_review.catalog import (
    DATASET_POLICY_VERSION,
    DEFAULT_CATALOG,
    DIAGNOSTIC_POLICY,
    ENGINE_VERSION,
    POP_CAPABILITIES,
    RuleCatalog,
)
from onyx.ton.financial_review.dataset import (
    dataset_revision,
    excluded_rows,
    record_dispositions,
)
from onyx.ton.email_flows.catalog import EVENT_KIND_NG_IMPORT
from onyx.ton.financial_review.engine import FinancialReviewEngine
from onyx.ton.financial_review.models import (
    DOWNSTREAM_SAFE_DISPOSITIONS,
    DiagnosticPolicyView,
    EvidenceView,
    FindingDetailView,
    FindingSummaryView,
    MonthDatasetView,
    PopCapabilityView,
    RecommendationView,
    ReviewDecisionRequest,
    ReviewDecisionView,
    ReviewDisposition,
    ReviewedDatasetSummaryView,
    ReviewedRecordView,
    ReviewRunStatus,
    ReviewRunView,
    RuleCatalogEntryView,
    RuleCatalogView,
    RuleContext,
    RuleEvaluationView,
)
from onyx.ton.financial_review.rules import DEFAULT_EXECUTORS, RuleExecutor
from onyx.utils.logger import setup_logger

logger = setup_logger()


def rule_set_digest(registered: dict[str, repository.RegisteredRule]) -> str:
    payload = {
        "engine_version": ENGINE_VERSION,
        "rules": [
            {
                "rule_key": key,
                "version": item.definition.version,
                "definition_hash": item.rule_version.definition_hash or "",
            }
            for key, item in sorted(registered.items())
        ],
    }
    return f"sha256:{compute_content_hash(payload)}"


def _view(run: ReviewRun, reused: bool = False) -> ReviewRunView:
    view = ReviewRunView.model_validate(run)
    return view.model_copy(update={"reused": reused})


def execute_review(
    session: Session,
    user: User,
    source_id: UUID,
    execution_id: UUID,
    *,
    catalog: RuleCatalog = DEFAULT_CATALOG,
    executors: dict[str, RuleExecutor] | None = None,
) -> ReviewRunView:
    engine = FinancialReviewEngine(catalog, executors or DEFAULT_EXECUTORS)
    execution = repository.get_execution_for_review(
        session, user, source_id, execution_id
    )
    try:
        registered = repository.register_catalog__no_commit(session, catalog)
    except repository.RuleCatalogConflict:
        session.rollback()
        raise OnyxError(
            OnyxErrorCode.CONFLICT,
            "Rule catalog differs from a registered rule version; bump the version",
        ) from None
    digest = rule_set_digest(registered)
    reusable = repository.find_reusable_run(session, execution.id, digest)
    if reusable is not None:
        session.commit()
        return _view(reusable, reused=True)

    now = datetime.datetime.now(datetime.UTC)
    try:
        attempt = repository.claim_attempt__no_commit(
            session, execution.id, digest, now
        )
        run = repository.start_review_run__no_commit(
            session,
            user=user,
            execution=execution,
            registered=registered,
            digest=digest,
            attempt_no=attempt,
            now=now,
        )
        run_id = run.id
        session.commit()
    except IntegrityError:
        session.rollback()
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "A review of this execution is running"
        ) from None
    except OnyxError:
        session.rollback()
        raise

    started = time.monotonic()
    try:
        records, diagnostics = repository.load_review_inputs(session, execution)
        context = RuleContext(
            source_id=execution.source_id,
            snapshot_id=execution.snapshot_id,
            execution_id=execution.id,
            execution_status=execution.status.value,
            execution_statistics={
                key: value
                for key, value in execution.statistics.items()
                if isinstance(value, int)
            },
        )
        result = engine.evaluate(records, diagnostics, context)
        finished = datetime.datetime.now(datetime.UTC)
        persisted = repository.persist_review_result__no_commit(
            session,
            run=run,
            registered=registered,
            result=result,
            records={record.id: record for record in records},
            now=finished,
        )
        verification = repository.verify_prior_occurrences__no_commit(
            session,
            user=user,
            run=run,
            registered=registered,
            result=result,
            detected=persisted.detected_occurrence_ids,
            now=finished,
        )
        statistics = {
            **dict(result.statistics),
            **persisted.statistics,
            **verification,
            "input_records": len(records),
            "input_records_rejected": int(
                execution.statistics.get("records_rejected", 0)
            ),
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
        repository.finish_review_run__no_commit(
            session,
            user=user,
            run=run,
            result=result,
            statistics=statistics,
            now=finished,
        )
        view = _view(run)
        # Email flows listen to finished imports; the event commits with the run.
        emit_flow_event__no_commit(
            session,
            kind=EVENT_KIND_NG_IMPORT,
            event_key=str(run.id),
            payload={"review_run_id": str(run.id), "source_id": str(run.source_id)},
        )
        session.commit()
    except Exception as error:
        session.rollback()
        code = (
            error.error_code.name
            if isinstance(error, OnyxError)
            else f"REVIEW_EXECUTION_FAILED:{type(error).__name__}"
        )
        try:
            repository.fail_review_run__no_commit(session, user, run_id, code)
            session.commit()
        except Exception:
            session.rollback()
            logger.warning("TON review recovery required review_run_id=%s", run_id)
        logger.warning(
            "TON review failed review_run_id=%s execution_id=%s error=%s",
            run_id,
            execution_id,
            type(error).__name__,
        )
        raise OnyxError(
            OnyxErrorCode.REVIEW_FAILED,
            f"Financial review failed; review_run_id={run_id}",
        ) from None
    logger.info(
        "TON review review_run_id=%s execution_id=%s records=%s findings=%s "
        "rules=%s duration_ms=%s",
        run_id,
        execution_id,
        statistics["input_records"],
        statistics.get("findings_created", 0),
        statistics.get("rules_executed", 0),
        statistics["duration_ms"],
    )
    return view


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


def catalog_view(catalog: RuleCatalog = DEFAULT_CATALOG) -> RuleCatalogView:
    return RuleCatalogView(
        engine_version=ENGINE_VERSION,
        dataset_policy_version=DATASET_POLICY_VERSION,
        rules=[
            RuleCatalogEntryView(
                rule_key=item.key,
                version=item.version,
                name=item.name,
                description=item.description,
                category=item.category,
                related_categories=list(item.related_categories),
                rule_type=item.rule_type,
                rule_kind=item.rule_kind,
                status=item.status,
                required_sources=list(item.required_sources),
                required_fields=list(item.required_fields),
                severity=item.severity,
                blocking=item.blocking,
                origin=item.origin,
                recommendation_capability=list(item.recommendation_capability),
                known_limitations=list(item.known_limitations),
            )
            for item in catalog
        ],
        pop_capabilities=[
            PopCapabilityView(
                category=item.category,
                name=item.name,
                status=item.status,
                rule_keys=sorted(
                    rule.key
                    for rule in catalog
                    if rule.category is item.category
                    or item.category in rule.related_categories
                ),
                rationale=item.rationale,
            )
            for item in POP_CAPABILITIES
        ],
        diagnostic_policy=[
            DiagnosticPolicyView(
                code=item.code.value,
                level=item.level.value if item.level else None,
                treatment=item.treatment,
                rule_key=item.rule_key,
                rationale=item.rationale,
            )
            for item in DIAGNOSTIC_POLICY
        ],
    )


def rule_evaluations(
    session: Session,
    user: User,
    source_id: UUID,
    review_run_id: UUID,
    limit: int,
    offset: int,
) -> list[RuleEvaluationView]:
    run = repository.get_review_run(session, user, source_id, review_run_id)
    check_page(limit, offset)
    counts = repository.rule_outcome_counts(session, run)
    version_ids = {item["rule_key"]: item["rule_version_id"] for item in run.rule_set}
    views = [
        RuleEvaluationView(
            rule_key=item["rule_key"],
            rule_version=item["rule_version"],
            engine_status=item["engine_status"],
            outcome=item["outcome"],
            finding_count=counts.get(UUID(version_ids[item["rule_key"]]), 0),
            observations=item["observations"],
            skip_reason=item["skip_reason"],
        )
        for item in run.rule_evaluations
    ]
    return views[offset : offset + limit]


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


def _summary(row: repository.FindingRow) -> FindingSummaryView:
    payload = row.finding.deterministic_payload
    return FindingSummaryView(
        id=row.finding.id,
        occurrence_id=row.occurrence.id,
        occurrence_short_code=row.occurrence.short_code,
        occurrence_status=row.occurrence.status,
        criticality=row.occurrence.criticality,
        verification_result=row.occurrence.verification_result,
        review_run_id=row.review_run_id,
        rule_key=row.rule_key,
        rule_version=row.rule_version,
        category=str(payload.get("category")),
        origin=str(payload.get("origin")),
        scope=str(payload.get("scope")),
        blocking=bool(payload.get("blocking")),
        sheet_month=payload.get("sheet_month"),
        record_count=int(payload.get("record_count") or 0),
        explanation=str(payload.get("explanation")),
        detected_at=row.finding.detected_at,
    )


def list_findings(
    session: Session,
    user: User,
    filters: repository.FindingFilters,
    limit: int,
    offset: int,
) -> list[FindingSummaryView]:
    return [
        _summary(row)
        for row in repository.list_findings_for_user(
            session, user, filters, limit, offset
        )
    ]


def get_finding(session: Session, user: User, finding_id: UUID) -> FindingDetailView:
    row = repository.get_review_finding_for_user(session, user, finding_id)
    payload = row.finding.deterministic_payload
    recommendations = repository.list_recommendations(session, [row.finding.id])
    return FindingDetailView(
        **_summary(row).model_dump(),
        facts=dict(payload.get("facts") or {}),
        impact=dict(payload.get("impact") or {}),
        related_categories=list(payload.get("related_categories") or []),
        recommendations=[
            RecommendationView.model_validate(item) for item in recommendations
        ],
    )


def list_evidence(
    session: Session, user: User, finding_id: UUID, limit: int, offset: int
) -> list[EvidenceView]:
    return [
        EvidenceView(
            id=item.id,
            finding_id=item.finding_id,
            kind=str(item.locator.get("kind")),
            source_snapshot_id=item.source_snapshot_id,
            import_execution_id=item.import_execution_id,
            parsed_record_id=item.parsed_record_id,
            sheet_name=item.locator.get("sheet"),
            row_number=item.locator.get("row"),
            column=item.locator.get("column"),
            diagnostic_code=item.locator.get("diagnostic_code"),
            role=item.locator.get("role"),
            confidence_level=item.confidence_level.value,
        )
        for item in repository.list_evidence_for_user(
            session, user, finding_id, limit, offset
        )
    ]


# ---------------------------------------------------------------------------
# Human decisions
# ---------------------------------------------------------------------------


def record_decision(
    session: Session,
    user: User,
    occurrence_id: UUID,
    request: ReviewDecisionRequest,
    catalog: RuleCatalog = DEFAULT_CATALOG,
) -> ReviewDecisionView:
    try:
        decision = repository.record_review_decision__no_commit(
            session, user, occurrence_id, request, catalog
        )
        view = ReviewDecisionView.model_validate(decision)
        session.commit()
        return view
    except ValueError:
        # A domain guard in the occurrence module refused the transition.
        session.rollback()
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "The decision is not allowed for this occurrence"
        ) from None
    except Exception:
        session.rollback()
        raise


def list_decisions(
    session: Session, user: User, occurrence_id: UUID, limit: int, offset: int
) -> list[ReviewDecisionView]:
    decisions = repository.list_decisions_for_user(
        session, user, occurrence_id, limit, offset
    )
    origins = repository.decision_origins(
        session,
        [item.carried_from_decision_id for item in decisions],
    )
    views: list[ReviewDecisionView] = []
    for item in decisions:
        view = ReviewDecisionView.model_validate(item)
        origin = origins.get(item.carried_from_decision_id)
        if origin is not None:
            view = view.model_copy(
                update={
                    "carried_from_actor_user_id": origin.actor_user_id,
                    "carried_from_at": origin.created_at,
                }
            )
        views.append(view)
    return views


# ---------------------------------------------------------------------------
# Reviewed dataset
# ---------------------------------------------------------------------------


def _succeeded_run(
    session: Session, user: User, source_id: UUID, review_run_id: UUID
) -> ReviewRun:
    run = repository.get_review_run(session, user, source_id, review_run_id)
    if run.status is not ReviewRunStatus.SUCCEEDED:
        raise OnyxError(OnyxErrorCode.CONFLICT, "The review run did not succeed")
    return run


def dataset_summary(
    session: Session,
    user: User,
    source_id: UUID,
    review_run_id: UUID,
    as_of: datetime.datetime | None = None,
) -> ReviewedDatasetSummaryView:
    run = _succeeded_run(session, user, source_id, review_run_id)
    instant = as_of or datetime.datetime.now(datetime.UTC)
    states, watermark = repository.load_finding_states(session, run, instant)
    flagged = record_dispositions(states)
    rejected = excluded_rows(states)
    per_month = repository.records_per_month(session, run.execution_id)
    total = sum(per_month.values())
    dispositions: Counter[ReviewDisposition] = Counter()
    unsafe_by_month: Counter[int] = Counter()
    month_of = {
        record_id: state.sheet_month
        for state in states
        for record_id in state.record_ids
    }
    for record_id, item in flagged.items():
        dispositions[item.disposition] += 1
        if not item.downstream_safe:
            unsafe_by_month[month_of.get(record_id) or 0] += 1
    dispositions[ReviewDisposition.ACCEPTED] += total - sum(dispositions.values())
    excluded = [
        item
        for item in rejected
        if item.disposition is ReviewDisposition.EXCLUDED_SOURCE_ERROR
    ]
    dispositions[ReviewDisposition.EXCLUDED_SOURCE_ERROR] = len(excluded)
    excluded_by_month = Counter(item.sheet_month or 0 for item in excluded)
    unlocated_open = any(item.sheet_month is None for item in excluded)
    months = [
        MonthDatasetView(
            sheet_month=month,
            records=count,
            downstream_safe=count - unsafe_by_month[month],
            not_downstream_safe=unsafe_by_month[month],
            excluded_source_rows=excluded_by_month[month],
            complete=excluded_by_month[month] == 0 and not unlocated_open,
        )
        for month, count in sorted(per_month.items())
    ]
    safe = sum(
        count
        for disposition, count in dispositions.items()
        if disposition in DOWNSTREAM_SAFE_DISPOSITIONS
    )
    return ReviewedDatasetSummaryView(
        review_run_id=run.id,
        source_id=run.source_id,
        snapshot_id=run.snapshot_id,
        execution_id=run.execution_id,
        rule_set_digest=run.rule_set_digest,
        dataset_policy_version=DATASET_POLICY_VERSION,
        dataset_revision=dataset_revision(
            review_run_id=run.id, event_watermark=watermark
        ),
        as_of=instant,
        total_records=total,
        dispositions={item: dispositions.get(item, 0) for item in ReviewDisposition},
        downstream_safe_records=safe,
        excluded_source_rows=len(excluded),
        downstream_ready=safe == total and not excluded,
        months=months,
    )


def dataset_records(
    session: Session,
    user: User,
    source_id: UUID,
    review_run_id: UUID,
    *,
    disposition: ReviewDisposition | None,
    sheet_month: int | None,
    account_code: str | None,
    administrative_unit: str | None,
    unit_missing: bool | None,
    limit: int,
    offset: int,
    as_of: datetime.datetime | None = None,
) -> list[ReviewedRecordView]:
    run = _succeeded_run(session, user, source_id, review_run_id)
    instant = as_of or datetime.datetime.now(datetime.UTC)
    states, _watermark = repository.load_finding_states(session, run, instant)
    flagged = record_dispositions(states)
    include: list[UUID] | None = None
    exclude: list[UUID] | None = None
    if disposition is ReviewDisposition.EXCLUDED_SOURCE_ERROR:
        return []
    if disposition is ReviewDisposition.ACCEPTED:
        exclude = sorted(
            (
                record_id
                for record_id, item in flagged.items()
                if item.disposition is not ReviewDisposition.ACCEPTED
            ),
            key=str,
        )
    elif disposition is not None:
        include = sorted(
            (
                record_id
                for record_id, item in flagged.items()
                if item.disposition is disposition
            ),
            key=str,
        )
    rows = repository.list_record_rows(
        session,
        run.execution_id,
        include_ids=include,
        exclude_ids=exclude,
        sheet_month=sheet_month,
        account_code=account_code,
        administrative_unit=administrative_unit,
        unit_missing=unit_missing,
        limit=limit,
        offset=offset,
    )
    views: list[ReviewedRecordView] = []
    for row in rows:
        item = flagged.get(row.id)
        state = item.disposition if item else ReviewDisposition.ACCEPTED
        views.append(
            ReviewedRecordView(
                parsed_record_id=row.id,
                sheet_name=row.sheet_name,
                row_number=row.row_number,
                sheet_month=row.sheet_month,
                account_code=row.account_code,
                disposition=state,
                downstream_safe=state in DOWNSTREAM_SAFE_DISPOSITIONS,
                rule_keys=list(item.rule_keys) if item else [],
                open_blocking_findings=item.open_blocking if item else 0,
                open_non_blocking_findings=item.open_non_blocking if item else 0,
            )
        )
    return views
