"""Occurrence lifecycle, deduplication and recurrence spec — Plan 003c.

The behavioural counterpart of ``test_domain_schema.py``. Real PostgreSQL is
required for every case here, and two of them could not exist without it: the
concurrency test needs two genuine connections racing on one unique index, and
the projection test needs the history the database actually stored rather than the
one the ORM thinks it stored.

Every case runs against a throwaway database cloned from a template at head. The
running development database is never touched.

Run with::

    uv run pytest backend/tests/external_dependency_unit/ton/test_occurrence_lifecycle.py
"""

import datetime
import threading
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    EvidenceConfidenceLevel,
    FindingKind,
    OccurrenceActorKind,
    OccurrenceCriticality,
    OccurrenceStatus,
    OccurrenceTransition,
    OccurrenceVerificationResult,
    PostResolutionPolicy,
    RedactionLevel,
    RuleDomain,
    SourceType,
)
from onyx.db.ton.findings import (
    add_finding_evidence__no_commit,
    highest_evidence_confidence,
)
from onyx.db.ton.models import Finding, Occurrence, Rule, RuleVersion
from onyx.db.ton.occurrences import (
    DetectionOutcome,
    apply_transition__no_commit,
    escalate_by_cycle_rule__no_commit,
    fetch_occurrence_events,
    project_from_events,
    projection_matches_history,
    promote_interpretation__no_commit,
    record_detection__no_commit,
    record_verification__no_commit,
    resolve_occurrence__no_commit,
    resolve_post_resolution_policy,
)
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import scratch_session

LATER = datetime.datetime(2001, 3, 15, 12, 0, tzinfo=datetime.UTC)
LATEST = datetime.datetime(2001, 4, 15, 12, 0, tzinfo=datetime.UTC)


def _count_occurrences(db_session: Session) -> int:
    return db_session.query(Occurrence).count()


def _count_findings(db_session: Session) -> int:
    return db_session.query(Finding).count()


class TestNewDetection:
    def test_a_first_detection_creates_one_finding_and_one_occurrence(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        assert result.outcome is DetectionOutcome.NEW
        assert _count_occurrences(ton_session) == 1
        assert _count_findings(ton_session) == 1
        assert result.occurrence.status is OccurrenceStatus.NEW
        assert result.occurrence.detection_count == 1
        assert result.occurrence.open_cycle_count == 1
        assert result.finding.occurrence_id == result.occurrence.id

    def test_the_first_generation_identity_equals_the_logical_key(
        self, ton_session: Session
    ) -> None:
        """A case that was never superseded carries the pure canonical digest, so
        the ordinary path is exactly the readiness §7 contract."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        assert result.occurrence.supersede_generation == 1
        assert result.occurrence.identity_key == result.occurrence.logical_identity_key

    def test_the_detection_appends_a_system_detect_event(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        events = fetch_occurrence_events(ton_session, result.occurrence.id)
        assert [event.transition for event in events] == [OccurrenceTransition.DETECT]
        assert events[0].actor_kind is OccurrenceActorKind.SYSTEM
        assert events[0].actor_user_id is None
        assert events[0].finding_id == result.finding.id
        assert events[0].rule_version_id == rule_version.id

    def test_a_short_code_is_allocated(self, ton_session: Session) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)

        first = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            identity_values={"period": "2001-01"},
        )
        second = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            identity_values={"period": "2001-02"},
        )
        ton_session.commit()

        assert first.occurrence.short_code.startswith("OC-")
        assert second.occurrence.short_code != first.occurrence.short_code

    def test_a_critical_detection_requires_human_closure(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            criticality=OccurrenceCriticality.CRITICAL,
        )
        ton_session.commit()

        assert result.occurrence.requires_human_closure is True


class TestRepeatedDetection:
    def test_a_repeat_reuses_the_occurrence_and_adds_a_finding(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        first_run = factories.make_analysis_run(ton_session)
        second_run = factories.make_analysis_run(ton_session)

        first = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=first_run
        )
        second = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=second_run,
            detected_at=LATER,
        )
        ton_session.commit()

        assert second.outcome is DetectionOutcome.REPEATED
        assert second.occurrence.id == first.occurrence.id
        assert _count_occurrences(ton_session) == 1
        assert _count_findings(ton_session) == 2
        assert second.finding.id != first.finding.id

    def test_a_repeat_increments_detection_count_and_moves_last_detected_at(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        first_run = factories.make_analysis_run(ton_session)
        second_run = factories.make_analysis_run(ton_session)

        factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=first_run
        )
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=second_run,
            detected_at=LATER,
        )
        ton_session.commit()

        assert result.occurrence.detection_count == 2
        assert result.occurrence.last_detected_at == LATER
        assert result.occurrence.first_detected_at == factories.SYNTHETIC_DETECTED_AT

    def test_a_repeat_appends_a_repeat_detected_event(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        first_run = factories.make_analysis_run(ton_session)
        second_run = factories.make_analysis_run(ton_session)

        factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=first_run
        )
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=second_run,
            detected_at=LATER,
        )
        ton_session.commit()

        events = fetch_occurrence_events(ton_session, result.occurrence.id)
        assert [event.transition for event in events] == [
            OccurrenceTransition.DETECT,
            OccurrenceTransition.REPEAT_DETECTED,
        ]
        assert [event.sequence_no for event in events] == [1, 2]

    def test_a_repeat_does_not_open_a_second_cycle(self, ton_session: Session) -> None:
        """§10 escalation counts open *cycles*, not detections. A case detected
        twice inside one open cycle has not been open for two cycles."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        first_run = factories.make_analysis_run(ton_session)
        second_run = factories.make_analysis_run(ton_session)

        factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=first_run
        )
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=second_run,
            detected_at=LATER,
        )
        ton_session.commit()

        assert result.occurrence.open_cycle_count == 1

    def test_the_same_run_and_rule_version_converges_instead_of_duplicating(
        self, ton_session: Session
    ) -> None:
        """A retry inside one logical analysis. The unique constraint on
        ``(run, rule_version, identity_key)`` is the guarantee, so the second
        attempt fails rather than producing a second finding."""
        from sqlalchemy.exc import IntegrityError

        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)

        factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        with pytest.raises(IntegrityError):
            factories.record_synthetic_detection(
                ton_session, rule=rule, rule_version=rule_version, analysis_run=run
            )
        ton_session.rollback()

        assert _count_occurrences(ton_session) == 1
        assert _count_findings(ton_session) == 1


class TestConcurrentDeduplication:
    """Genuine concurrency. A sequential test proves nothing here.

    Two threads, two connections, two transactions, released together by a
    barrier. ``INSERT … ON CONFLICT DO NOTHING`` plus a re-read is what makes them
    converge: the loser blocks on the winner's row lock, writes nothing, and then
    reads the committed winner under a fresh READ COMMITTED snapshot.
    """

    def test_two_concurrent_workers_converge_on_one_occurrence(
        self, ton_database: str
    ) -> None:
        with scratch_session(ton_database) as setup_session:
            rule, rule_version = factories.make_occurrence_rule_version(setup_session)
            first_run = factories.make_analysis_run(setup_session)
            second_run = factories.make_analysis_run(setup_session)
            setup_session.commit()
            rule_id = rule.id
            rule_version_id = rule_version.id
            run_ids = [first_run.id, second_run.id]

        barrier = threading.Barrier(2)
        outcomes: list[tuple[UUID, DetectionOutcome]] = []
        failures: list[BaseException] = []
        lock = threading.Lock()

        def worker(run_id: UUID) -> None:
            try:
                with scratch_session(ton_database) as session:
                    worker_rule = session.get_one(Rule, rule_id)
                    worker_version = session.get_one(RuleVersion, rule_version_id)
                    # Both threads reach the INSERT at the same moment; without
                    # the barrier one would simply finish first and the race
                    # would never happen.
                    barrier.wait(timeout=30)
                    result = record_detection__no_commit(
                        session,
                        analysis_run_id=run_id,
                        rule=worker_rule,
                        rule_version=worker_version,
                        identity_values={"period": "2001-01"},
                        finding_kind=FindingKind.DETECTION,
                        title="Concurrent detection",
                        owning_domain=RuleDomain.FINANCIAL,
                        ledger_kind=factories.OccurrenceLedgerKind.EXCEPTION,
                        criticality=OccurrenceCriticality.MEDIUM,
                        detected_at=factories.SYNTHETIC_DETECTED_AT,
                    )
                    occurrence_id = result.occurrence.id
                    outcome = result.outcome
                    session.commit()
                with lock:
                    outcomes.append((occurrence_id, outcome))
            except BaseException as exc:  # noqa: BLE001 - re-raised below
                with lock:
                    failures.append(exc)

        threads = [
            threading.Thread(target=worker, args=(run_id,)) for run_id in run_ids
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        assert not failures, f"a concurrent worker raised: {failures[0]!r}"
        assert len(outcomes) == 2

        with scratch_session(ton_database) as verify_session:
            assert _count_occurrences(verify_session) == 1
            # Both detections were recorded; only the business case was shared.
            assert _count_findings(verify_session) == 2
            occurrence = verify_session.query(Occurrence).one()
            assert occurrence.detection_count == 2
            events = fetch_occurrence_events(verify_session, occurrence.id)
            assert [event.transition for event in events] == [
                OccurrenceTransition.DETECT,
                OccurrenceTransition.REPEAT_DETECTED,
            ]
            assert projection_matches_history(occurrence, events)

        # Both workers ended up on the same row, and exactly one of them created it.
        assert {occurrence_id for occurrence_id, _ in outcomes} == {occurrence.id}
        assert sorted(outcome.value for _, outcome in outcomes) == ["NEW", "REPEATED"]


class TestResolution:
    def test_resolving_records_history_and_the_projection_agrees(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )

        resolve_occurrence__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            reason="Synthetic resolution",
            resolved_at=LATER,
        )
        ton_session.commit()

        events = fetch_occurrence_events(ton_session, result.occurrence.id)
        assert result.occurrence.status is OccurrenceStatus.RESOLVED
        assert result.occurrence.resolved_at == LATER
        assert projection_matches_history(result.occurrence, events)
        assert events[-1].transition is OccurrenceTransition.RESOLVED
        assert events[-1].actor_user_id == actor.id

    def test_resolving_a_critical_case_uses_the_authorized_transition(
        self, ton_session: Session
    ) -> None:
        """TON may propose closing a critical occurrence; only a person with a
        recorded authorization may close one."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            criticality=OccurrenceCriticality.CRITICAL,
        )

        event = resolve_occurrence__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            reason="Deliberated in synthetic ata",
            authorization_reference="SYN-ATA-1",
        )
        ton_session.commit()

        assert event.transition is OccurrenceTransition.RESOLVE_CRITICAL
        assert event.authorization_reference == "SYN-ATA-1"
        assert result.occurrence.status is OccurrenceStatus.RESOLVED

    def test_resolving_a_critical_case_without_authorization_is_refused(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            criticality=OccurrenceCriticality.CRITICAL,
        )

        with pytest.raises(ValueError, match="authorization_reference"):
            resolve_occurrence__no_commit(
                ton_session,
                occurrence=result.occurrence,
                actor_user_id=actor.id,
                reason="No authorization recorded",
            )

    def test_no_finding_is_created_to_represent_an_absent_detection(
        self, ton_session: Session
    ) -> None:
        """Readiness §7: a case not recurring produces nothing. Verification is
        how absence is recorded, and it creates no finding."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        resolve_occurrence__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            reason="Synthetic resolution",
        )
        ton_session.commit()
        findings_before = _count_findings(ton_session)

        record_verification__no_commit(
            ton_session,
            occurrence=result.occurrence,
            result=OccurrenceVerificationResult.PASSED,
            checked_at=LATER,
        )
        ton_session.commit()

        assert _count_findings(ton_session) == findings_before
        assert result.occurrence.verification_result is (
            OccurrenceVerificationResult.PASSED
        )
        assert result.occurrence.verification_checked_at == LATER
        assert result.occurrence.status is OccurrenceStatus.RESOLVED


class TestRecurrence:
    def _resolved_case(
        self, ton_session: Session, *, policy: PostResolutionPolicy
    ) -> tuple[Rule, RuleVersion, Occurrence]:
        rule, rule_version = factories.make_occurrence_rule_version(
            ton_session, post_resolution_policy=policy
        )
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        resolve_occurrence__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            reason="Synthetic resolution",
            resolved_at=LATER,
        )
        ton_session.commit()
        return rule, rule_version, result.occurrence

    def test_reopen_same_occurrence_keeps_one_case(self, ton_session: Session) -> None:
        rule, rule_version, occurrence = self._resolved_case(
            ton_session, policy=PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )
        later_run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=later_run,
            detected_at=LATEST,
        )
        ton_session.commit()

        assert result.outcome is DetectionOutcome.REOPENED
        assert result.occurrence.id == occurrence.id
        assert _count_occurrences(ton_session) == 1
        assert result.occurrence.status is OccurrenceStatus.REOPENED
        assert result.occurrence.resolved_at is None
        assert result.occurrence.open_cycle_count == 2
        assert result.occurrence.detection_count == 2

    def test_reopen_appends_history_and_the_projection_agrees(
        self, ton_session: Session
    ) -> None:
        rule, rule_version, _ = self._resolved_case(
            ton_session, policy=PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )
        later_run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=later_run,
            detected_at=LATEST,
        )
        ton_session.commit()

        events = fetch_occurrence_events(ton_session, result.occurrence.id)
        assert [event.transition for event in events] == [
            OccurrenceTransition.DETECT,
            OccurrenceTransition.RESOLVED,
            OccurrenceTransition.REOPENED,
        ]
        assert projection_matches_history(result.occurrence, events)

    def test_supersede_with_new_occurrence_opens_a_second_generation(
        self, ton_session: Session
    ) -> None:
        rule, rule_version, previous = self._resolved_case(
            ton_session, policy=PostResolutionPolicy.SUPERSEDE_WITH_NEW_OCCURRENCE
        )
        previous_id = previous.id
        later_run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=later_run,
            detected_at=LATEST,
        )
        ton_session.commit()

        assert result.outcome is DetectionOutcome.SUPERSEDED
        assert result.occurrence.id != previous_id
        assert _count_occurrences(ton_session) == 2
        assert result.occurrence.supersede_generation == 2
        assert result.occurrence.logical_identity_key == previous.logical_identity_key
        # The generation is what makes UNIQUE(identity_key) and supersede
        # coexist: the successor's key differs while the lineage key does not.
        assert result.occurrence.identity_key != previous.identity_key

    def test_supersede_links_and_closes_the_previous_case(
        self, ton_session: Session
    ) -> None:
        rule, rule_version, previous = self._resolved_case(
            ton_session, policy=PostResolutionPolicy.SUPERSEDE_WITH_NEW_OCCURRENCE
        )
        later_run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=later_run,
            detected_at=LATEST,
        )
        ton_session.commit()

        assert previous.superseded_by_occurrence_id == result.occurrence.id
        assert previous.status is OccurrenceStatus.SUPERSEDED
        previous_events = fetch_occurrence_events(ton_session, previous.id)
        assert previous_events[-1].transition is OccurrenceTransition.SUPERSEDE
        assert previous_events[-1].actor_kind is OccurrenceActorKind.SYSTEM
        assert projection_matches_history(previous, previous_events)

    def test_a_changed_rule_version_forces_supersede_over_the_policy(
        self, ton_session: Session
    ) -> None:
        """Two detections measured against different thresholds are not the same
        measurement, so reopening is not offered whatever the policy says."""
        rule, first_version, previous = self._resolved_case(
            ton_session, policy=PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )
        second_version = factories.make_rule_version(
            ton_session,
            rule=rule,
            version=2,
            identity_components=first_version.identity_components,
        )
        second_version.post_resolution_policy = (
            PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )
        ton_session.flush()
        later_run = factories.make_analysis_run(ton_session)

        assert (
            resolve_post_resolution_policy(
                occurrence=previous, detecting_rule_version=second_version
            )
            is PostResolutionPolicy.SUPERSEDE_WITH_NEW_OCCURRENCE
        )

        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=second_version,
            analysis_run=later_run,
            detected_at=LATEST,
        )
        ton_session.commit()

        assert result.outcome is DetectionOutcome.SUPERSEDED
        assert result.occurrence.id != previous.id
        assert result.occurrence.current_rule_version_id == second_version.id
        assert previous.status is OccurrenceStatus.SUPERSEDED

    def test_the_same_rule_version_honours_the_declared_policy(
        self, ton_session: Session
    ) -> None:
        """The control for the case above: unchanged version, policy applies."""
        rule, rule_version, previous = self._resolved_case(
            ton_session, policy=PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )
        assert (
            resolve_post_resolution_policy(
                occurrence=previous, detecting_rule_version=rule_version
            )
            is PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )
        assert rule.code


class TestIdentityStability:
    def test_identity_survives_a_title_and_interpretation_change(
        self, ton_session: Session
    ) -> None:
        """The guard against LLM-derived identity. Text is never an identity
        input, so changing every human-facing string leaves the key alone."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()
        original_identity = result.occurrence.identity_key
        original_logical = result.occurrence.logical_identity_key

        result.occurrence.title = "A completely different title"
        promote_interpretation__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            authorization_reference="SYN-ATA-2",
            criticality=OccurrenceCriticality.HIGH,
            nc_code="SYN-NC-9",
            reason="Synthetic promotion",
        )
        ton_session.commit()

        assert result.occurrence.identity_key == original_identity
        assert result.occurrence.logical_identity_key == original_logical

    def test_a_later_detection_with_a_new_title_lands_on_the_same_case(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        first_run = factories.make_analysis_run(ton_session)
        second_run = factories.make_analysis_run(ton_session)

        first = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=first_run,
            title="First wording",
        )
        second = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=second_run,
            title="Entirely different wording",
            detected_at=LATER,
        )
        ton_session.commit()

        assert second.occurrence.id == first.occurrence.id
        assert _count_occurrences(ton_session) == 1


class TestBlindSpot:
    def test_a_blind_spot_is_valid_with_no_impact_and_no_source_row(
        self, ton_session: Session
    ) -> None:
        """Prompt Mestre §11: a data gap is a first-class finding. Nothing here
        requires a number or an evidence row."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            finding_kind=FindingKind.BLIND_SPOT,
            criticality=OccurrenceCriticality.MONITORING,
        )
        ton_session.commit()

        assert result.finding.finding_kind is FindingKind.BLIND_SPOT
        assert result.finding.expected_value is None
        assert result.finding.actual_value is None
        assert result.finding.computed_impact_amount is None
        assert result.finding.evidence == []
        assert result.occurrence.status is OccurrenceStatus.NEW

    def test_a_blind_spot_can_still_be_assigned_to_a_named_owner(
        self, ton_session: Session
    ) -> None:
        """§11 publishes a gap as "indisponível — pendente de informação de
        campo", with a named owner."""
        from onyx.db.ton.occurrence_records import assign_responsible__no_commit

        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            finding_kind=FindingKind.BLIND_SPOT,
        )

        assignment = assign_responsible__no_commit(
            ton_session,
            occurrence=result.occurrence,
            responsible_label="Synthetic field owner",
            assigned_by_user_id=actor.id,
        )
        ton_session.commit()

        assert assignment.responsible_label == "Synthetic field owner"
        assert assignment.responsible_user_id is None


class TestEvidence:
    def test_confidence_is_preserved_per_evidence_row(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        snapshot = factories.make_source_snapshot(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )

        for level in (
            EvidenceConfidenceLevel.D,
            EvidenceConfidenceLevel.D,
            EvidenceConfidenceLevel.C,
        ):
            add_finding_evidence__no_commit(
                ton_session,
                finding=result.finding,
                source_type=SourceType.UPLOADED_SPREADSHEET,
                confidence_level=level,
                redaction_level=RedactionLevel.NONE,
                source_snapshot_id=snapshot.id,
                locator={"sheet": "synthetic", "row": 4},
                extracted_value="12.3400000000",
            )
        ton_session.commit()

        levels = [item.confidence_level for item in result.finding.evidence]
        assert levels.count(EvidenceConfidenceLevel.D) == 2
        assert levels.count(EvidenceConfidenceLevel.C) == 1

    def test_repeated_low_confidence_evidence_is_never_promoted(
        self, ton_session: Session
    ) -> None:
        """§3.4 forbids converting D into A by repetition. The aggregate reads the
        best level present; it never combines levels into a better one."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        for _ in range(5):
            add_finding_evidence__no_commit(
                ton_session,
                finding=result.finding,
                source_type=SourceType.MANUAL_ENTRY,
                confidence_level=EvidenceConfidenceLevel.D,
                redaction_level=RedactionLevel.ROLE_ONLY,
            )
        ton_session.commit()

        assert (
            highest_evidence_confidence(list(result.finding.evidence))
            is EvidenceConfidenceLevel.D
        )

    def test_the_locator_stays_source_agnostic(self, ton_session: Session) -> None:
        """One generic field serves a spreadsheet, a PDF and a chunk."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )

        for locator in (
            {"sheet": "synthetic", "row": 12, "column": "D", "cell": "D12"},
            {"page": 4, "line": 17},
            {"chunk_id": "synthetic-chunk", "char_span": [10, 42]},
        ):
            evidence = add_finding_evidence__no_commit(
                ton_session,
                finding=result.finding,
                source_type=SourceType.CONTRACT_DOCUMENT,
                confidence_level=EvidenceConfidenceLevel.B,
                redaction_level=RedactionLevel.NONE,
                locator=locator,
            )
            assert evidence.locator == locator
        ton_session.commit()

    def test_an_extracted_float_is_refused(self, ton_session: Session) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )

        with pytest.raises(TypeError, match="decimal string"):
            add_finding_evidence__no_commit(
                ton_session,
                finding=result.finding,
                source_type=SourceType.MANUAL_ENTRY,
                confidence_level=EvidenceConfidenceLevel.C,
                redaction_level=RedactionLevel.NONE,
                extracted_value=12.34,  # ty: ignore[invalid-argument-type]
            )


class TestProjectionHonesty:
    def test_the_stored_projection_equals_the_event_derived_one(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        actor = factories.make_user(ton_session)
        first_run = factories.make_analysis_run(ton_session)
        second_run = factories.make_analysis_run(ton_session)
        third_run = factories.make_analysis_run(ton_session)

        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=first_run
        )
        factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=second_run,
            detected_at=LATER,
        )
        resolve_occurrence__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            reason="Synthetic resolution",
            resolved_at=LATER,
        )
        factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=third_run,
            detected_at=LATEST,
        )
        ton_session.commit()

        occurrence = result.occurrence
        events = fetch_occurrence_events(ton_session, occurrence.id)
        derived = project_from_events(events)

        assert derived is not None
        assert occurrence.status is derived.status
        assert occurrence.detection_count == derived.detection_count == 3
        assert occurrence.open_cycle_count == derived.open_cycle_count == 2
        assert occurrence.resolved_at == derived.resolved_at is None
        assert projection_matches_history(occurrence, events)

    def test_every_event_records_the_status_it_produced(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        resolve_occurrence__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            reason="Synthetic resolution",
        )
        ton_session.commit()

        events = fetch_occurrence_events(ton_session, result.occurrence.id)
        assert [event.resulting_status for event in events] == [
            OccurrenceStatus.NEW,
            OccurrenceStatus.RESOLVED,
        ]

    def test_an_escalation_records_history_without_moving_the_status(
        self, ton_session: Session
    ) -> None:
        """§10 says the scale is applied "sem consultar ninguém", and an
        escalation changes criticality rather than lifecycle state."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            criticality=OccurrenceCriticality.HIGH,
        )

        escalate_by_cycle_rule__no_commit(
            ton_session,
            occurrence=result.occurrence,
            criticality=OccurrenceCriticality.CRITICAL,
            reason="Synthetic escalation",
        )
        ton_session.commit()

        events = fetch_occurrence_events(ton_session, result.occurrence.id)
        assert result.occurrence.criticality is OccurrenceCriticality.CRITICAL
        # Escalating to critical removes TON's ability to close the case.
        assert result.occurrence.requires_human_closure is True
        assert result.occurrence.status is OccurrenceStatus.NEW
        assert events[-1].transition is OccurrenceTransition.ESCALATE_BY_CYCLE_RULE
        assert events[-1].actor_kind is OccurrenceActorKind.SYSTEM
        assert projection_matches_history(result.occurrence, events)


class TestHumanOnlyTransitions:
    """The §12.1 boundary, at the domain layer and at the database."""

    @pytest.mark.parametrize(
        "transition",
        [
            OccurrenceTransition.RESOLVE_CRITICAL,
            OccurrenceTransition.ACCEPT_RISK,
            OccurrenceTransition.DISMISS,
            OccurrenceTransition.ASSERT_NONCOMPLIANCE,
            OccurrenceTransition.PROMOTE_INTERPRETATION,
            OccurrenceTransition.OVERRIDE_DETERMINISTIC_VALUE,
        ],
    )
    def test_a_system_actor_is_refused(
        self, ton_session: Session, transition: OccurrenceTransition
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )

        with pytest.raises(ValueError, match="not a transition TON may perform"):
            apply_transition__no_commit(
                ton_session,
                occurrence=result.occurrence,
                transition=transition,
                actor_kind=OccurrenceActorKind.SYSTEM,
            )

    @pytest.mark.parametrize(
        "transition",
        [
            OccurrenceTransition.ACCEPT_RISK,
            OccurrenceTransition.DISMISS,
            OccurrenceTransition.ASSERT_NONCOMPLIANCE,
        ],
    )
    def test_a_user_without_an_authorization_reference_is_refused(
        self, ton_session: Session, transition: OccurrenceTransition
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )

        with pytest.raises(ValueError, match="authorization_reference"):
            apply_transition__no_commit(
                ton_session,
                occurrence=result.occurrence,
                transition=transition,
                actor_kind=OccurrenceActorKind.USER,
                actor_user_id=actor.id,
            )

    def test_the_database_refuses_a_human_only_event_written_directly(
        self, ton_session: Session
    ) -> None:
        """The guarantee that survives a writer bypassing the domain module."""
        from sqlalchemy.exc import IntegrityError

        from onyx.db.ton.models import OccurrenceEvent

        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        ton_session.add(
            OccurrenceEvent(
                occurrence_id=result.occurrence.id,
                sequence_no=99,
                transition=OccurrenceTransition.DISMISS,
                resulting_status=OccurrenceStatus.DISMISSED,
                actor_kind=OccurrenceActorKind.SYSTEM,
                occurred_at=LATER,
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_occurrence_event_human_only_transitions" in str(exc_info.value)

    def test_the_database_refuses_a_system_resolution(
        self, ton_session: Session
    ) -> None:
        from sqlalchemy.exc import IntegrityError

        from onyx.db.ton.models import OccurrenceEvent

        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        ton_session.add(
            OccurrenceEvent(
                occurrence_id=result.occurrence.id,
                sequence_no=99,
                transition=OccurrenceTransition.RESOLVED,
                resulting_status=OccurrenceStatus.RESOLVED,
                actor_kind=OccurrenceActorKind.SYSTEM,
                occurred_at=LATER,
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_occurrence_event_resolution_requires_user" in str(exc_info.value)

    def test_a_system_actor_may_still_record_the_operational_transitions(
        self, ton_session: Session
    ) -> None:
        """The control: §12.1 does let TON read, test, calculate and write to the
        ledger, so the boundary is not a blanket ban."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )

        for transition in (
            OccurrenceTransition.VERIFICATION_FAILED,
            OccurrenceTransition.ESCALATE_BY_CYCLE_RULE,
        ):
            event = apply_transition__no_commit(
                ton_session,
                occurrence=result.occurrence,
                transition=transition,
                actor_kind=OccurrenceActorKind.SYSTEM,
            )
            assert event.actor_kind is OccurrenceActorKind.SYSTEM
        ton_session.commit()


class TestDeterministicValuesAreImmutable:
    def test_a_finding_keeps_its_deterministic_values_across_the_lifecycle(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        actor = factories.make_user(ton_session)
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            expected_value=Decimal("1234.5678900000"),
            actual_value=Decimal("1300.0000000000"),
            value_currency=factories.SYNTHETIC_CURRENCY,
            value_scale=2,
        )
        ton_session.commit()
        finding_id = result.finding.id

        promote_interpretation__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            authorization_reference="SYN-ATA-3",
            criticality=OccurrenceCriticality.HIGH,
        )
        resolve_occurrence__no_commit(
            ton_session,
            occurrence=result.occurrence,
            actor_user_id=actor.id,
            reason="Synthetic resolution",
        )
        ton_session.commit()
        ton_session.expire_all()

        stored = ton_session.get_one(Finding, finding_id)
        assert stored.expected_value == Decimal("1234.5678900000")
        assert stored.actual_value == Decimal("1300.0000000000")
        assert stored.rule_version_id == rule_version.id
        assert stored.identity_key == result.occurrence.identity_key

    def test_a_float_deterministic_value_is_refused(self, ton_session: Session) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)

        with pytest.raises(TypeError, match="Decimal"):
            factories.record_synthetic_detection(
                ton_session,
                rule=rule,
                rule_version=rule_version,
                analysis_run=run,
                expected_value=1234.5678,
            )
