"""Analysis-run behaviour spec — Plan 003b.

The centre of this file is :class:`TestDomainScopedBlocking`, the named
anti-defect test. The original TON defect was global blocking: one failed base
validation silenced every specialist. Prompt Mestre §5 reads that way in prose,
and readiness §5 fixes the software reading — failure blocks only the affected
``(step_code, domain, business_unit_id)`` and its dependents.

Real PostgreSQL is required and the deployment database is never touched: each
test gets a throwaway database cloned from a template at head. There is no HTTP
surface in 003b, so these are external-dependency unit tests calling the domain
functions directly rather than integration tests.

Run with::

    uv run pytest backend/tests/external_dependency_unit/ton/test_analysis_run.py
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.db.ton.analysis_runs import (
    attach_source_snapshot__no_commit,
    finalize_analysis_run__no_commit,
    get_analysis_runs_for_snapshot,
    get_or_create_analysis_run__no_commit,
    get_rule_version_outcomes,
    record_rule_version_outcome__no_commit,
)
from onyx.db.ton.analysis_steps import (
    block_step__no_commit,
    fail_step__no_commit,
    pass_step__no_commit,
    reprove_base__no_commit,
)
from onyx.db.ton.enums import (
    AnalysisRunStatus,
    AnalysisSpecialist,
    AnalysisStepBlockedReason,
    AnalysisStepCode,
    AnalysisStepStatus,
    AnalysisTrigger,
    RuleDomain,
    RuleVersionOutcome,
)
from onyx.db.ton.models import AnalysisRun, AnalysisStep, BusinessUnit
from tests.external_dependency_unit.ton import factories

# The dependent steps of BASE_VALIDATION, in protocol order.
AFTER_BASE_VALIDATION: tuple[AnalysisStepCode, ...] = (
    AnalysisStepCode.CHAIN_RECONCILIATION,
    AnalysisStepCode.DETECTION,
    AnalysisStepCode.QUANTIFICATION,
    AnalysisStepCode.PRIORITIZATION,
    AnalysisStepCode.PUBLICATION,
)


def _scheduled_audit_run(
    db_session: Session, idempotency_key: str
) -> tuple[AnalysisRun, bool]:
    """One fixed logical run, so a repeat call differs only in nothing at all."""
    return get_or_create_analysis_run__no_commit(
        db_session,
        idempotency_key=idempotency_key,
        trigger=AnalysisTrigger.SCHEDULED,
        specialist=AnalysisSpecialist.AUDITOR,
        domain=RuleDomain.AUDIT,
        period_start=factories.SYNTHETIC_PERIOD_START,
        period_end=factories.SYNTHETIC_PERIOD_END,
        executor_version="synthetic-executor-0",
    )


def _build_scoped_steps(
    db_session: Session,
    *,
    run: AnalysisRun,
    domain: RuleDomain,
    unit: BusinessUnit,
) -> dict[AnalysisStepCode, AnalysisStep]:
    """One pending step per protocol code, all in a single (domain, unit) scope."""
    return {
        step_code: factories.make_step(
            db_session,
            run=run,
            step_code=step_code,
            domain=domain,
            business_unit=unit,
        )
        for step_code in (
            AnalysisStepCode.BASE_VALIDATION,
            *AFTER_BASE_VALIDATION,
        )
    }


class TestDomainScopedBlocking:
    """The anti-defect test. A failure in one (domain, unit) must not stop the rest.

    Mirrors the worked example in readiness §5: financial base validation fails in
    one unit, and financial detection and publication are blocked *in that unit
    only*. Fleet, contracts and HR in the same unit keep going, financial analysis
    in the other unit keeps going, and the run reports partial success.
    """

    def test_failure_blocks_only_its_own_domain_and_unit(
        self, ton_session: Session
    ) -> None:
        mossoro = factories.make_business_unit(ton_session, code="SYN-UNIT-A")
        itabirito = factories.make_business_unit(ton_session, code="SYN-UNIT-B")
        run = factories.make_analysis_run(ton_session, domain=RuleDomain.FINANCIAL)

        # The scope that will fail.
        financial_a = _build_scoped_steps(
            ton_session, run=run, domain=RuleDomain.FINANCIAL, unit=mossoro
        )
        # Sibling domains in the same unit.
        siblings = {
            domain: factories.make_step(
                ton_session,
                run=run,
                step_code=AnalysisStepCode.DETECTION,
                domain=domain,
                business_unit=mossoro,
            )
            for domain in (RuleDomain.FLEET, RuleDomain.CONTRACT, RuleDomain.HR)
        }
        # The same domain in a sibling unit.
        financial_b_detection = factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.DETECTION,
            domain=RuleDomain.FINANCIAL,
            business_unit=itabirito,
        )

        blocked = fail_step__no_commit(
            ton_session,
            step=financial_a[AnalysisStepCode.BASE_VALIDATION],
            blocked_reason=AnalysisStepBlockedReason.BASE_REPROVED,
        )

        # Only the five dependents of the failed scope were blocked.
        assert {step.step_code for step in blocked} == set(AFTER_BASE_VALIDATION)
        assert all(step.domain is RuleDomain.FINANCIAL for step in blocked)
        assert all(step.business_unit_id == mossoro.id for step in blocked)

        assert (
            financial_a[AnalysisStepCode.BASE_VALIDATION].status
            is AnalysisStepStatus.FAILED
        )
        for step_code in AFTER_BASE_VALIDATION:
            step = financial_a[step_code]
            assert step.status is AnalysisStepStatus.BLOCKED
            assert step.blocked_reason is AnalysisStepBlockedReason.BASE_REPROVED
            assert (
                step.blocked_by_step_id
                == financial_a[AnalysisStepCode.BASE_VALIDATION].id
            )

        # Everything else is untouched and can still run to a verdict.
        for domain, step in siblings.items():
            assert step.status is AnalysisStepStatus.PENDING, (
                f"{domain.value} in the same unit must not be blocked"
            )
            pass_step__no_commit(ton_session, step=step)
            assert step.status is AnalysisStepStatus.PASSED

        assert financial_b_detection.status is AnalysisStepStatus.PENDING
        pass_step__no_commit(ton_session, step=financial_b_detection)
        assert financial_b_detection.status is AnalysisStepStatus.PASSED

        ton_session.commit()

    def test_a_partially_blocked_run_completes_with_blocked_domains(
        self, ton_session: Session
    ) -> None:
        """Not FAILED. This is the whole point: successful specialist results
        must survive a sibling's failure."""
        mossoro = factories.make_business_unit(ton_session, code="SYN-UNIT-A")
        itabirito = factories.make_business_unit(ton_session, code="SYN-UNIT-B")
        run = factories.make_analysis_run(ton_session, domain=RuleDomain.FINANCIAL)

        financial_a = _build_scoped_steps(
            ton_session, run=run, domain=RuleDomain.FINANCIAL, unit=mossoro
        )
        survivors = [
            factories.make_step(
                ton_session,
                run=run,
                step_code=AnalysisStepCode.DETECTION,
                domain=domain,
                business_unit=unit,
            )
            for domain, unit in (
                (RuleDomain.FLEET, mossoro),
                (RuleDomain.CONTRACT, mossoro),
                (RuleDomain.HR, mossoro),
                (RuleDomain.FINANCIAL, itabirito),
            )
        ]

        fail_step__no_commit(
            ton_session,
            step=financial_a[AnalysisStepCode.BASE_VALIDATION],
            blocked_reason=AnalysisStepBlockedReason.BASE_REPROVED,
        )
        for step in survivors:
            pass_step__no_commit(ton_session, step=step)

        status = finalize_analysis_run__no_commit(ton_session, analysis_run=run)
        ton_session.commit()

        assert status is AnalysisRunStatus.COMPLETED_WITH_BLOCKED_DOMAINS
        assert run.status is AnalysisRunStatus.COMPLETED_WITH_BLOCKED_DOMAINS
        assert run.status is not AnalysisRunStatus.FAILED

    def test_a_run_with_no_surviving_step_is_failed(self, ton_session: Session) -> None:
        """Full failure still reports FAILED — the two states stay distinct."""
        unit = factories.make_business_unit(ton_session)
        run = factories.make_analysis_run(ton_session)
        steps = _build_scoped_steps(
            ton_session, run=run, domain=RuleDomain.FINANCIAL, unit=unit
        )

        fail_step__no_commit(ton_session, step=steps[AnalysisStepCode.BASE_VALIDATION])

        status = finalize_analysis_run__no_commit(ton_session, analysis_run=run)
        ton_session.commit()

        assert status is AnalysisRunStatus.FAILED

    def test_a_fully_successful_run_is_completed(self, ton_session: Session) -> None:
        unit = factories.make_business_unit(ton_session)
        run = factories.make_analysis_run(ton_session)
        steps = _build_scoped_steps(
            ton_session, run=run, domain=RuleDomain.FINANCIAL, unit=unit
        )
        for step in steps.values():
            pass_step__no_commit(ton_session, step=step)

        status = finalize_analysis_run__no_commit(ton_session, analysis_run=run)
        ton_session.commit()

        assert status is AnalysisRunStatus.COMPLETED

    def test_a_run_wide_failure_may_block_every_domain(
        self, ton_session: Session
    ) -> None:
        """The containment rule is scope-based, not domain-blind: a genuinely
        run-wide ingestion failure legitimately blocks narrower scopes."""
        unit = factories.make_business_unit(ton_session)
        run = factories.make_analysis_run(ton_session)
        ingestion = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.INGESTION
        )
        scoped = [
            factories.make_step(
                ton_session,
                run=run,
                step_code=AnalysisStepCode.DETECTION,
                domain=domain,
                business_unit=unit,
            )
            for domain in (RuleDomain.FINANCIAL, RuleDomain.FLEET)
        ]

        blocked = fail_step__no_commit(
            ton_session,
            step=ingestion,
            blocked_reason=AnalysisStepBlockedReason.MISSING_SOURCE,
        )

        assert {step.id for step in blocked} == {step.id for step in scoped}
        ton_session.commit()

    def test_a_scoped_failure_never_blocks_a_run_wide_step(
        self, ton_session: Session
    ) -> None:
        """The reverse containment: a single domain must not stop the whole run."""
        unit = factories.make_business_unit(ton_session)
        run = factories.make_analysis_run(ton_session)
        scoped_base = factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.BASE_VALIDATION,
            domain=RuleDomain.FINANCIAL,
            business_unit=unit,
        )
        run_wide_publication = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.PUBLICATION
        )

        blocked = fail_step__no_commit(ton_session, step=scoped_base)

        assert blocked == []
        assert run_wide_publication.status is AnalysisStepStatus.PENDING
        ton_session.commit()

    def test_an_already_decided_step_is_never_rewritten(
        self, ton_session: Session
    ) -> None:
        """A PASSED sibling keeps its verdict; blocking only touches pending work."""
        unit = factories.make_business_unit(ton_session)
        run = factories.make_analysis_run(ton_session)
        steps = _build_scoped_steps(
            ton_session, run=run, domain=RuleDomain.FINANCIAL, unit=unit
        )
        pass_step__no_commit(
            ton_session, step=steps[AnalysisStepCode.CHAIN_RECONCILIATION]
        )

        fail_step__no_commit(ton_session, step=steps[AnalysisStepCode.BASE_VALIDATION])

        assert (
            steps[AnalysisStepCode.CHAIN_RECONCILIATION].status
            is AnalysisStepStatus.PASSED
        )
        assert steps[AnalysisStepCode.DETECTION].status is AnalysisStepStatus.BLOCKED
        ton_session.commit()


class TestBlockingApiRefusals:
    """Widening the blast radius is not expressible through the API."""

    def test_a_sibling_domain_cannot_be_blocked(self, ton_session: Session) -> None:
        unit = factories.make_business_unit(ton_session)
        run = factories.make_analysis_run(ton_session)
        financial_base = factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.BASE_VALIDATION,
            domain=RuleDomain.FINANCIAL,
            business_unit=unit,
        )
        fleet_detection = factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.DETECTION,
            domain=RuleDomain.FLEET,
            business_unit=unit,
        )

        with pytest.raises(ValueError, match="Blocking is scoped"):
            block_step__no_commit(
                ton_session,
                step=fleet_detection,
                caused_by=financial_base,
                reason=AnalysisStepBlockedReason.BASE_REPROVED,
            )

    def test_a_sibling_unit_cannot_be_blocked(self, ton_session: Session) -> None:
        first = factories.make_business_unit(ton_session, code="SYN-UNIT-A")
        second = factories.make_business_unit(ton_session, code="SYN-UNIT-B")
        run = factories.make_analysis_run(ton_session)
        base_first = factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.BASE_VALIDATION,
            domain=RuleDomain.FINANCIAL,
            business_unit=first,
        )
        detection_second = factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.DETECTION,
            domain=RuleDomain.FINANCIAL,
            business_unit=second,
        )

        with pytest.raises(ValueError, match="Blocking is scoped"):
            block_step__no_commit(
                ton_session,
                step=detection_second,
                caused_by=base_first,
                reason=AnalysisStepBlockedReason.BASE_REPROVED,
            )

    def test_blocking_cannot_run_backwards(self, ton_session: Session) -> None:
        run = factories.make_analysis_run(ton_session)
        publication = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.PUBLICATION
        )
        ingestion = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.INGESTION
        )

        with pytest.raises(ValueError, match="does not precede"):
            block_step__no_commit(
                ton_session,
                step=ingestion,
                caused_by=publication,
                reason=AnalysisStepBlockedReason.PREREQUISITE_FAILED,
            )

    def test_blocking_cannot_cross_runs(self, ton_session: Session) -> None:
        first_run = factories.make_analysis_run(ton_session)
        second_run = factories.make_analysis_run(ton_session)
        cause = factories.make_step(
            ton_session, run=first_run, step_code=AnalysisStepCode.BASE_VALIDATION
        )
        target = factories.make_step(
            ton_session, run=second_run, step_code=AnalysisStepCode.DETECTION
        )

        with pytest.raises(ValueError, match="same analysis run"):
            block_step__no_commit(
                ton_session,
                step=target,
                caused_by=cause,
                reason=AnalysisStepBlockedReason.PREREQUISITE_FAILED,
            )

    def test_every_blocked_step_names_its_cause(self, ton_session: Session) -> None:
        """No silent blocking, checked on the rows the API produced."""
        unit = factories.make_business_unit(ton_session)
        run = factories.make_analysis_run(ton_session)
        steps = _build_scoped_steps(
            ton_session, run=run, domain=RuleDomain.FINANCIAL, unit=unit
        )

        fail_step__no_commit(ton_session, step=steps[AnalysisStepCode.BASE_VALIDATION])
        ton_session.commit()

        blocked_rows = (
            ton_session.query(AnalysisStep)
            .filter(
                AnalysisStep.analysis_run_id == run.id,
                AnalysisStep.status == AnalysisStepStatus.BLOCKED,
            )
            .all()
        )
        assert blocked_rows
        for row in blocked_rows:
            assert row.blocked_by_step_id is not None
            assert row.blocked_reason is not None


class TestS10ScopedPublicationBlocking:
    """S10: no margin published on a reproved base — for that scope only."""

    def test_a_reproved_base_blocks_publication_for_its_scope_only(
        self, ton_session: Session
    ) -> None:
        reproved_unit = factories.make_business_unit(ton_session, code="SYN-UNIT-A")
        healthy_unit = factories.make_business_unit(ton_session, code="SYN-UNIT-B")
        run = factories.make_analysis_run(ton_session, domain=RuleDomain.FINANCIAL)

        reproved = _build_scoped_steps(
            ton_session,
            run=run,
            domain=RuleDomain.FINANCIAL,
            unit=reproved_unit,
        )
        healthy_publication = factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.PUBLICATION,
            domain=RuleDomain.FINANCIAL,
            business_unit=healthy_unit,
        )
        fleet_publication = factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.PUBLICATION,
            domain=RuleDomain.FLEET,
            business_unit=reproved_unit,
        )

        reprove_base__no_commit(
            ton_session, step=reproved[AnalysisStepCode.BASE_VALIDATION]
        )

        publication = reproved[AnalysisStepCode.PUBLICATION]
        assert publication.status is AnalysisStepStatus.BLOCKED
        assert publication.blocked_reason is AnalysisStepBlockedReason.BASE_REPROVED

        # S10 is not a run-wide flag.
        assert healthy_publication.status is AnalysisStepStatus.PENDING
        assert fleet_publication.status is AnalysisStepStatus.PENDING
        assert run.status is not AnalysisRunStatus.FAILED
        ton_session.commit()

    def test_s10_applies_only_to_base_validation(self, ton_session: Session) -> None:
        run = factories.make_analysis_run(ton_session)
        detection = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.DETECTION
        )

        with pytest.raises(ValueError, match="S10 applies to BASE_VALIDATION"):
            reprove_base__no_commit(ton_session, step=detection)


class TestIdempotency:
    """A retry of the same logical run converges instead of duplicating."""

    def test_the_same_key_converges_on_one_run(self, ton_session: Session) -> None:
        key = f"syn-idem-{factories.unique_suffix()}"

        first, created_first = _scheduled_audit_run(ton_session, key)
        second, created_second = _scheduled_audit_run(ton_session, key)
        ton_session.commit()

        assert created_first is True
        assert created_second is False
        assert first.id == second.id
        assert (
            ton_session.query(AnalysisRun).filter_by(idempotency_key=key).count() == 1
        )

    def test_a_different_key_creates_a_second_run(self, ton_session: Session) -> None:
        first, _ = _scheduled_audit_run(ton_session, "syn-idem-x")
        second, created = _scheduled_audit_run(ton_session, "syn-idem-y")
        ton_session.commit()

        assert created is True
        assert first.id != second.id

    def test_a_raw_duplicate_insert_is_refused_by_the_database(
        self, ton_session: Session
    ) -> None:
        """The convergence above is not a bare ``SELECT`` first: uniqueness is a
        database property, so two concurrent writers cannot both win."""
        key = f"syn-idem-{factories.unique_suffix()}"
        factories.make_analysis_run(ton_session, idempotency_key=key)
        ton_session.commit()

        with pytest.raises(IntegrityError):
            factories.make_analysis_run(ton_session, idempotency_key=key)
        ton_session.rollback()

        assert (
            ton_session.query(AnalysisRun).filter_by(idempotency_key=key).count() == 1
        )


class TestRuleVersionParticipation:
    """What ran, and what did not, with the reason."""

    def test_skipped_outcomes_are_recorded_with_their_reason(
        self, ton_session: Session
    ) -> None:
        run = factories.make_analysis_run(ton_session)
        executed = factories.make_rule_version(
            ton_session, rule=factories.make_rule(ton_session)
        )
        not_applicable = factories.make_rule_version(
            ton_session, rule=factories.make_rule(ton_session)
        )
        missing_data = factories.make_rule_version(
            ton_session, rule=factories.make_rule(ton_session)
        )
        errored = factories.make_rule_version(
            ton_session, rule=factories.make_rule(ton_session)
        )

        record_rule_version_outcome__no_commit(
            ton_session,
            analysis_run=run,
            rule_version=executed,
            outcome=RuleVersionOutcome.EXECUTED,
            finding_count=3,
        )
        for rule_version, outcome in (
            (not_applicable, RuleVersionOutcome.SKIPPED_NOT_APPLICABLE),
            (missing_data, RuleVersionOutcome.SKIPPED_MISSING_DATA),
            (errored, RuleVersionOutcome.ERRORED),
        ):
            record_rule_version_outcome__no_commit(
                ton_session,
                analysis_run=run,
                rule_version=rule_version,
                outcome=outcome,
            )
        ton_session.commit()

        outcomes = {
            row.rule_version_id: row
            for row in get_rule_version_outcomes(ton_session, analysis_run_id=run.id)
        }
        assert len(outcomes) == 4
        assert outcomes[executed.id].outcome is RuleVersionOutcome.EXECUTED
        assert outcomes[executed.id].finding_count == 3
        assert (
            outcomes[not_applicable.id].outcome
            is RuleVersionOutcome.SKIPPED_NOT_APPLICABLE
        )
        assert (
            outcomes[missing_data.id].outcome is RuleVersionOutcome.SKIPPED_MISSING_DATA
        )
        assert outcomes[errored.id].outcome is RuleVersionOutcome.ERRORED
        assert all(
            outcomes[rule_version.id].finding_count == 0
            for rule_version in (not_applicable, missing_data, errored)
        )

    def test_a_skipped_rule_cannot_claim_findings(self, ton_session: Session) -> None:
        run = factories.make_analysis_run(ton_session)
        rule_version = factories.make_rule_version(
            ton_session, rule=factories.make_rule(ton_session)
        )

        with pytest.raises(ValueError, match="did not execute"):
            record_rule_version_outcome__no_commit(
                ton_session,
                analysis_run=run,
                rule_version=rule_version,
                outcome=RuleVersionOutcome.SKIPPED_MISSING_DATA,
                finding_count=1,
            )

    def test_a_replayed_run_refines_the_recorded_outcome(
        self, ton_session: Session
    ) -> None:
        run = factories.make_analysis_run(ton_session)
        rule_version = factories.make_rule_version(
            ton_session, rule=factories.make_rule(ton_session)
        )

        record_rule_version_outcome__no_commit(
            ton_session,
            analysis_run=run,
            rule_version=rule_version,
            outcome=RuleVersionOutcome.SKIPPED_MISSING_DATA,
        )
        record_rule_version_outcome__no_commit(
            ton_session,
            analysis_run=run,
            rule_version=rule_version,
            outcome=RuleVersionOutcome.EXECUTED,
            finding_count=2,
        )
        ton_session.commit()

        outcomes = get_rule_version_outcomes(ton_session, analysis_run_id=run.id)
        assert len(outcomes) == 1
        assert outcomes[0].outcome is RuleVersionOutcome.EXECUTED
        assert outcomes[0].finding_count == 2


class TestSourceSnapshotProvenance:
    """Input provenance is relational, not an opaque blob on the run."""

    def test_which_analyses_used_a_snapshot_is_answerable(
        self, ton_session: Session
    ) -> None:
        snapshot = factories.make_source_snapshot(ton_session)
        other_snapshot = factories.make_source_snapshot(ton_session)
        first_run = factories.make_analysis_run(ton_session)
        second_run = factories.make_analysis_run(ton_session)
        unrelated_run = factories.make_analysis_run(ton_session)

        attach_source_snapshot__no_commit(
            ton_session, analysis_run=first_run, source_snapshot=snapshot
        )
        attach_source_snapshot__no_commit(
            ton_session, analysis_run=second_run, source_snapshot=snapshot
        )
        attach_source_snapshot__no_commit(
            ton_session, analysis_run=unrelated_run, source_snapshot=other_snapshot
        )
        ton_session.commit()

        found = get_analysis_runs_for_snapshot(
            ton_session, source_snapshot_id=snapshot.id
        )

        assert {run.id for run in found} == {first_run.id, second_run.id}

    def test_attaching_the_same_snapshot_twice_is_idempotent(
        self, ton_session: Session
    ) -> None:
        snapshot = factories.make_source_snapshot(ton_session)
        run = factories.make_analysis_run(ton_session)

        attach_source_snapshot__no_commit(
            ton_session, analysis_run=run, source_snapshot=snapshot
        )
        attach_source_snapshot__no_commit(
            ton_session, analysis_run=run, source_snapshot=snapshot
        )
        ton_session.commit()

        assert len(run.source_snapshot_links) == 1

    def test_an_incomplete_snapshot_records_what_did_not_arrive(
        self, ton_session: Session
    ) -> None:
        """Prompt Mestre §5 Passo 1: the absence has to be recorded, not implied."""
        snapshot = factories.make_source_snapshot(
            ton_session,
            is_complete=False,
            missing_inputs=["synthetic_missing_input"],
            is_schema_conformant=False,
        )
        ton_session.commit()

        assert snapshot.is_complete is False
        assert snapshot.missing_inputs == ["synthetic_missing_input"]
        assert snapshot.is_schema_conformant is False
