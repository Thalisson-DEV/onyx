"""Analysis-run persistence (Plan 003b).

Covers the execution envelope: idempotent creation, source-snapshot provenance,
per-rule-version outcomes and the run-status roll-up.

No Celery, no scheduling, no dispatch. ``AnalysisTrigger.SCHEDULED`` is an
identity here; Plan 006 owns the beat schedule and the R1-R9 routines.
"""

import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from onyx.db.ton.analysis_steps import resolve_run_status
from onyx.db.ton.enums import (
    AnalysisRunErrorClass,
    AnalysisRunStatus,
    AnalysisSpecialist,
    AnalysisTrigger,
    RuleDomain,
    RuleVersionOutcome,
)
from onyx.db.ton.models import (
    AnalysisRun,
    AnalysisRun__SourceSnapshot,
    AnalysisRunRuleVersion,
    RuleVersion,
    SourceSnapshot,
)


def get_or_create_analysis_run__no_commit(
    db_session: Session,
    *,
    idempotency_key: str,
    trigger: AnalysisTrigger,
    specialist: AnalysisSpecialist,
    domain: RuleDomain,
    period_start: datetime.date,
    period_end: datetime.date,
    executor_version: str,
    business_unit_id: UUID | None = None,
    triggered_by_user_id: UUID | None = None,
    routine_code: str | None = None,
) -> tuple[AnalysisRun, bool]:
    """Return ``(run, created)`` for *idempotency_key*.

    Convergent by construction: ``INSERT ... ON CONFLICT DO NOTHING`` followed by
    a re-read, so a Celery retry and two concurrent workers all end on the same
    envelope instead of duplicating it. Uniqueness is enforced by the database,
    not by a prior ``SELECT``, which would race.
    """
    statement = (
        pg_insert(AnalysisRun)
        .values(
            idempotency_key=idempotency_key,
            trigger=trigger,
            specialist=specialist,
            domain=domain,
            business_unit_id=business_unit_id,
            triggered_by_user_id=triggered_by_user_id,
            routine_code=routine_code,
            period_start=period_start,
            period_end=period_end,
            executor_version=executor_version,
        )
        .on_conflict_do_nothing(index_elements=[AnalysisRun.idempotency_key])
        .returning(AnalysisRun.id)
    )
    inserted_id = db_session.execute(statement).scalar_one_or_none()

    if inserted_id is None:
        existing = db_session.execute(
            select(AnalysisRun).where(AnalysisRun.idempotency_key == idempotency_key)
        ).scalar_one()
        return existing, False

    created = db_session.execute(
        select(AnalysisRun).where(AnalysisRun.id == inserted_id)
    ).scalar_one()
    return created, True


def attach_source_snapshot__no_commit(
    db_session: Session,
    *,
    analysis_run: AnalysisRun,
    source_snapshot: SourceSnapshot,
) -> None:
    """Record that *source_snapshot* fed *analysis_run*.

    Idempotent, so re-running the ingestion step of a retried run does not fail on
    the association's primary key.
    """
    db_session.execute(
        pg_insert(AnalysisRun__SourceSnapshot)
        .values(
            analysis_run_id=analysis_run.id,
            source_snapshot_id=source_snapshot.id,
        )
        .on_conflict_do_nothing(
            index_elements=[
                AnalysisRun__SourceSnapshot.analysis_run_id,
                AnalysisRun__SourceSnapshot.source_snapshot_id,
            ]
        )
    )
    db_session.flush()


def get_analysis_runs_for_snapshot(
    db_session: Session, *, source_snapshot_id: UUID
) -> list[AnalysisRun]:
    """ "Which analyses used snapshot X?" — the question the association exists for."""
    return list(
        db_session.execute(
            select(AnalysisRun)
            .join(
                AnalysisRun__SourceSnapshot,
                AnalysisRun__SourceSnapshot.analysis_run_id == AnalysisRun.id,
            )
            .where(AnalysisRun__SourceSnapshot.source_snapshot_id == source_snapshot_id)
            .order_by(AnalysisRun.created_at, AnalysisRun.id)
        )
        .scalars()
        .all()
    )


def record_rule_version_outcome__no_commit(
    db_session: Session,
    *,
    analysis_run: AnalysisRun,
    rule_version: RuleVersion,
    outcome: RuleVersionOutcome,
    finding_count: int = 0,
) -> None:
    """Record what became of *rule_version* inside *analysis_run*.

    A skipped or errored rule must report zero findings; the database enforces it
    with ``ck_ton_analysis_run_rule_version_skipped_has_no_findings``, and the
    guard here names the contract instead of surfacing a constraint error.

    Upsert rather than insert, so a replayed run refines the recorded outcome
    instead of failing.
    """
    if outcome is not RuleVersionOutcome.EXECUTED and finding_count != 0:
        raise ValueError(
            f"outcome={outcome.value} cannot carry finding_count={finding_count}: "
            "a rule that did not execute produced no findings."
        )
    if finding_count < 0:
        raise ValueError("finding_count cannot be negative.")

    statement = pg_insert(AnalysisRunRuleVersion).values(
        analysis_run_id=analysis_run.id,
        rule_version_id=rule_version.id,
        outcome=outcome,
        finding_count=finding_count,
    )
    db_session.execute(
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
    db_session.flush()


def get_rule_version_outcomes(
    db_session: Session, *, analysis_run_id: UUID
) -> list[AnalysisRunRuleVersion]:
    return list(
        db_session.execute(
            select(AnalysisRunRuleVersion).where(
                AnalysisRunRuleVersion.analysis_run_id == analysis_run_id
            )
        )
        .scalars()
        .all()
    )


def finalize_analysis_run__no_commit(
    db_session: Session,
    *,
    analysis_run: AnalysisRun,
    error_class: AnalysisRunErrorClass | None = None,
    finished_at: datetime.datetime | None = None,
) -> AnalysisRunStatus:
    """Roll the run's steps up into its status and close it.

    The roll-up is the reason a partially blocked run is not reported as a
    failure: see :func:`onyx.db.ton.analysis_steps.resolve_run_status`.
    """
    db_session.flush()
    db_session.refresh(analysis_run)

    status = resolve_run_status(analysis_run.steps)
    now = finished_at or datetime.datetime.now(datetime.UTC)

    analysis_run.status = status
    if status in (
        AnalysisRunStatus.COMPLETED,
        AnalysisRunStatus.COMPLETED_WITH_BLOCKED_DOMAINS,
        AnalysisRunStatus.FAILED,
    ):
        if analysis_run.started_at is None:
            analysis_run.started_at = now
        analysis_run.finished_at = now
    if error_class is not None:
        analysis_run.error_class = error_class

    db_session.flush()
    return status
