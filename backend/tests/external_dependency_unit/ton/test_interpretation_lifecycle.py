"""AI-interpretation lifecycle spec — Plan 003c.

**No provider is contacted anywhere in this file.** The failure modes are injected
at the boundary the production caller will use: ``begin_interpretation`` returns,
a fake provider raises, and ``fail_interpretation`` records the outcome. That is
the whole point of splitting the lifecycle from the call — the durability
ordering becomes testable without a network.

The load-bearing case is
``TestPendingIsCommittedBeforeTheProvider``: it reads
``Finding.interpretation_status`` from a **second, independent connection** while
the first is still mid-flight. Only a committed value is visible there, so the
assertion cannot pass unless PENDING really was durable before the provider could
have started.

Run with::

    uv run pytest backend/tests/external_dependency_unit/ton/test_interpretation_lifecycle.py
"""

import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    InterpretationFailureClass,
    InterpretationInputScope,
    InterpretationStatus,
    OccurrenceCriticality,
)
from onyx.db.ton.interpretations import (
    begin_interpretation,
    complete_interpretation,
    fail_interpretation,
    fetch_interpretations,
    is_interpretation_final,
    latest_interpretation,
    mark_interpretation_running,
)
from onyx.db.ton.models import Finding, FindingInterpretation
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import scratch_session

PROMPT_KEY = "synthetic_interpretation_prompt"
PROMPT_VERSION = "syn-1"
PROVIDER = "synthetic-provider"
MODEL = "synthetic-model-0"


def _finding_with_pending_interpretation(
    db_session: Session,
) -> tuple[Finding, FindingInterpretation]:
    rule, rule_version = factories.make_occurrence_rule_version(db_session)
    run = factories.make_analysis_run(db_session)
    result = factories.record_synthetic_detection(
        db_session,
        rule=rule,
        rule_version=rule_version,
        analysis_run=run,
        expected_value=Decimal("100.0000000000"),
        actual_value=Decimal("140.0000000000"),
    )
    db_session.commit()
    attempt = begin_interpretation(
        db_session,
        finding=result.finding,
        prompt_key=PROMPT_KEY,
        prompt_version=PROMPT_VERSION,
        input_scope=InterpretationInputScope.STRUCTURED_ONLY,
        llm_provider=PROVIDER,
        model_name=MODEL,
    )
    return result.finding, attempt


class TestPendingIsCommittedBeforeTheProvider:
    """The durability invariant, verified across connections."""

    def test_pending_is_visible_to_another_connection_before_any_provider_work(
        self, ton_database: str
    ) -> None:
        with scratch_session(ton_database) as writer:
            finding, attempt = _finding_with_pending_interpretation(writer)
            finding_id = finding.id
            attempt_id = attempt.id

            # A second connection sees only committed data. If `begin_interpretation`
            # had left PENDING in an open transaction, this read would still show
            # NOT_REQUIRED and a crash during the provider call would leave no
            # trace that it was ever attempted.
            with scratch_session(ton_database) as observer:
                observed = observer.get_one(Finding, finding_id)
                assert observed.interpretation_status is InterpretationStatus.PENDING
                observed_attempt = observer.get_one(FindingInterpretation, attempt_id)
                assert observed_attempt.status is InterpretationStatus.PENDING
                assert observed_attempt.finished_at is None

    def test_a_crash_after_pending_leaves_a_visible_non_final_record(
        self, ton_database: str
    ) -> None:
        """Simulates the provider call never returning: the writer's session is
        discarded without closing the attempt."""
        with scratch_session(ton_database) as writer:
            finding, _ = _finding_with_pending_interpretation(writer)
            finding_id = finding.id

        with scratch_session(ton_database) as reader:
            recovered = reader.get_one(Finding, finding_id)
            assert recovered.interpretation_status is InterpretationStatus.PENDING
            assert not is_interpretation_final(recovered)
            attempt = latest_interpretation(reader, finding_id)
            assert attempt is not None
            assert attempt.status is InterpretationStatus.PENDING

    def test_pending_records_provenance_but_no_prompt_body(
        self, ton_session: Session
    ) -> None:
        _, attempt = _finding_with_pending_interpretation(ton_session)

        assert attempt.prompt_key == PROMPT_KEY
        assert attempt.prompt_version == PROMPT_VERSION
        assert attempt.llm_provider == PROVIDER
        assert not hasattr(attempt, "prompt_body")
        assert not hasattr(attempt, "raw_response")


class TestRunningLifecycle:
    def test_a_pending_attempt_can_be_marked_running(
        self, ton_session: Session
    ) -> None:
        finding, attempt = _finding_with_pending_interpretation(ton_session)

        mark_interpretation_running(ton_session, finding=finding, attempt=attempt)

        assert attempt.status is InterpretationStatus.RUNNING
        assert finding.interpretation_status is InterpretationStatus.RUNNING
        assert not is_interpretation_final(finding)

    def test_a_terminal_attempt_cannot_be_restarted(self, ton_session: Session) -> None:
        finding, attempt = _finding_with_pending_interpretation(ton_session)
        fail_interpretation(
            ton_session,
            finding=finding,
            attempt=attempt,
            failure_class=InterpretationFailureClass.TIMEOUT,
            retry_eligible=True,
        )

        with pytest.raises(ValueError, match="Only a PENDING attempt"):
            mark_interpretation_running(ton_session, finding=finding, attempt=attempt)


class TestSuccessfulInterpretation:
    def test_a_completed_attempt_carries_the_business_facing_output(
        self, ton_session: Session
    ) -> None:
        finding, attempt = _finding_with_pending_interpretation(ton_session)

        complete_interpretation(
            ton_session,
            finding=finding,
            attempt=attempt,
            summary="Synthetic summary",
            probable_cause="Synthetic cause",
            recommended_action="Synthetic action",
            impact_narrative="Synthetic narrative",
        )

        assert attempt.status is InterpretationStatus.COMPLETED
        assert attempt.summary == "Synthetic summary"
        assert attempt.finished_at is not None
        assert attempt.failure_class is None
        assert finding.interpretation_status is InterpretationStatus.COMPLETED
        assert is_interpretation_final(finding)

    def test_an_empty_summary_is_refused(self, ton_session: Session) -> None:
        """The guard against laundering a provider failure into a success."""
        finding, attempt = _finding_with_pending_interpretation(ton_session)

        with pytest.raises(ValueError, match="needs a summary"):
            complete_interpretation(
                ton_session, finding=finding, attempt=attempt, summary="   "
            )

    def test_the_database_refuses_a_completed_attempt_with_no_summary(
        self, ton_session: Session
    ) -> None:
        """The same rule, for a writer that bypasses the module."""
        finding, attempt = _finding_with_pending_interpretation(ton_session)

        attempt.status = InterpretationStatus.COMPLETED
        attempt.finished_at = datetime.datetime.now(datetime.UTC)
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_finding_interpretation_completed_has_summary" in str(
            exc_info.value
        )

    def test_a_completed_attempt_must_name_its_provider_and_model(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()
        attempt = begin_interpretation(
            ton_session,
            finding=result.finding,
            prompt_key=PROMPT_KEY,
            prompt_version=PROMPT_VERSION,
            input_scope=InterpretationInputScope.STRUCTURED_ONLY,
        )

        with pytest.raises(ValueError, match="which provider and model"):
            complete_interpretation(
                ton_session,
                finding=result.finding,
                attempt=attempt,
                summary="Synthetic summary",
            )


class TestFailureIsDurable:
    """Every provider failure mode leaves a durable, operator-visible FAILED."""

    @pytest.mark.parametrize(
        ("failure_class", "retry_eligible"),
        [
            (InterpretationFailureClass.PROVIDER_UNAVAILABLE, True),
            (InterpretationFailureClass.TIMEOUT, True),
            (InterpretationFailureClass.MALFORMED_OUTPUT, True),
            (InterpretationFailureClass.POLICY_REFUSAL, False),
            (InterpretationFailureClass.INSUFFICIENT_EVIDENCE, False),
        ],
    )
    def test_a_failure_is_recorded_and_survives_the_session(
        self,
        ton_database: str,
        failure_class: InterpretationFailureClass,
        retry_eligible: bool,
    ) -> None:
        with scratch_session(ton_database) as writer:
            finding, attempt = _finding_with_pending_interpretation(writer)
            finding_id = finding.id
            attempt_id = attempt.id

            # The injected provider boundary. No network, no LiteLLM, no prompt.
            def fake_provider_call() -> None:
                raise RuntimeError("synthetic provider failure")

            with pytest.raises(RuntimeError):
                fake_provider_call()

            fail_interpretation(
                writer,
                finding=finding,
                attempt=attempt,
                failure_class=failure_class,
                retry_eligible=retry_eligible,
            )

        with scratch_session(ton_database) as reader:
            recovered = reader.get_one(Finding, finding_id)
            recovered_attempt = reader.get_one(FindingInterpretation, attempt_id)
            assert recovered.interpretation_status is InterpretationStatus.FAILED
            assert not is_interpretation_final(recovered)
            assert recovered_attempt.status is InterpretationStatus.FAILED
            assert recovered_attempt.failure_class is failure_class
            assert recovered_attempt.retry_eligible is retry_eligible
            # A failure is never an empty success.
            assert recovered_attempt.summary is None

    def test_the_database_refuses_a_failure_without_a_class(
        self, ton_session: Session
    ) -> None:
        finding, attempt = _finding_with_pending_interpretation(ton_session)

        attempt.status = InterpretationStatus.FAILED
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_finding_interpretation_failed_has_class" in str(exc_info.value)

    def test_the_database_refuses_a_failure_class_on_a_non_failure(
        self, ton_session: Session
    ) -> None:
        finding, attempt = _finding_with_pending_interpretation(ton_session)

        attempt.failure_class = InterpretationFailureClass.TIMEOUT
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_finding_interpretation_class_only_on_failure" in str(
            exc_info.value
        )

    def test_no_failure_message_or_payload_is_stored(
        self, ton_session: Session
    ) -> None:
        """The failure class is the whole record — no message, no traceback, no
        provider payload."""
        finding, attempt = _finding_with_pending_interpretation(ton_session)
        fail_interpretation(
            ton_session,
            finding=finding,
            attempt=attempt,
            failure_class=InterpretationFailureClass.PROVIDER_UNAVAILABLE,
            retry_eligible=True,
        )

        columns = set(FindingInterpretation.__table__.columns.keys())
        assert "error_message" not in columns
        assert "traceback" not in columns
        assert "provider_response" not in columns


class TestRetryAppends:
    def test_a_retry_creates_a_new_attempt_and_keeps_the_failed_one(
        self, ton_session: Session
    ) -> None:
        finding, first = _finding_with_pending_interpretation(ton_session)
        fail_interpretation(
            ton_session,
            finding=finding,
            attempt=first,
            failure_class=InterpretationFailureClass.TIMEOUT,
            retry_eligible=True,
        )

        second = begin_interpretation(
            ton_session,
            finding=finding,
            prompt_key=PROMPT_KEY,
            prompt_version=PROMPT_VERSION,
            input_scope=InterpretationInputScope.STRUCTURED_ONLY,
            llm_provider=PROVIDER,
            model_name=MODEL,
        )
        complete_interpretation(
            ton_session,
            finding=finding,
            attempt=second,
            summary="Synthetic summary on retry",
        )

        attempts = fetch_interpretations(ton_session, finding.id)
        assert [item.attempt_no for item in attempts] == [1, 2]
        assert attempts[0].status is InterpretationStatus.FAILED
        assert attempts[0].failure_class is InterpretationFailureClass.TIMEOUT
        assert attempts[1].status is InterpretationStatus.COMPLETED
        assert finding.interpretation_status is InterpretationStatus.COMPLETED

    def test_a_duplicate_attempt_number_is_refused(self, ton_session: Session) -> None:
        finding, first = _finding_with_pending_interpretation(ton_session)

        ton_session.add(
            FindingInterpretation(
                finding_id=finding.id,
                attempt_no=first.attempt_no,
                status=InterpretationStatus.PENDING,
                prompt_key=PROMPT_KEY,
                prompt_version=PROMPT_VERSION,
                input_scope=InterpretationInputScope.STRUCTURED_ONLY,
                started_at=datetime.datetime.now(datetime.UTC),
            )
        )
        with pytest.raises(IntegrityError):
            ton_session.commit()


class TestInterpreterCannotMutateDeterministicData:
    def test_the_lifecycle_leaves_every_deterministic_value_untouched(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            expected_value=Decimal("500.1234500000"),
            actual_value=Decimal("620.0000000000"),
            deviation_value=Decimal("119.8765500000"),
            computed_impact_amount=Decimal("119.8765500000"),
            value_currency=factories.SYNTHETIC_CURRENCY,
        )
        ton_session.commit()
        before = {
            "expected_value": result.finding.expected_value,
            "actual_value": result.finding.actual_value,
            "deviation_value": result.finding.deviation_value,
            "computed_impact_amount": result.finding.computed_impact_amount,
            "rule_version_id": result.finding.rule_version_id,
            "identity_key": result.finding.identity_key,
            "nc_code": result.finding.nc_code,
        }
        occurrence_criticality = result.occurrence.criticality

        attempt = begin_interpretation(
            ton_session,
            finding=result.finding,
            prompt_key=PROMPT_KEY,
            prompt_version=PROMPT_VERSION,
            input_scope=InterpretationInputScope.STRUCTURED_ONLY,
            llm_provider=PROVIDER,
            model_name=MODEL,
        )
        complete_interpretation(
            ton_session,
            finding=result.finding,
            attempt=attempt,
            summary="Synthetic summary",
            proposed_criticality=OccurrenceCriticality.CRITICAL,
            proposed_nc_code="SYN-NC-PROPOSED",
        )
        ton_session.expire_all()

        stored = ton_session.get_one(Finding, result.finding.id)
        for name, value in before.items():
            assert getattr(stored, name) == value, f"{name} changed"  # noqa: B009
        # The proposal alone changes nothing on the case.
        ton_session.refresh(result.occurrence)
        assert result.occurrence.criticality is occurrence_criticality
        assert result.occurrence.nc_code == before["nc_code"]

    def test_the_module_exposes_no_write_path_to_a_deterministic_field(self) -> None:
        """An inverse assertion over the source: no function in the interpretation
        module assigns a deterministic ``Finding`` attribute."""
        import ast
        import inspect

        from onyx.db.ton import interpretations
        from onyx.db.ton.findings import IMMUTABLE_FINDING_COLUMNS

        tree = ast.parse(inspect.getsource(interpretations))
        assigned: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AugAssign):
                targets = [node.target]
            else:
                continue
            for target in targets:
                if isinstance(target, ast.Attribute):
                    assigned.add(target.attr)

        assert assigned & IMMUTABLE_FINDING_COLUMNS == set(), (
            "the interpretation module must not assign a deterministic Finding "
            f"field: {sorted(assigned & IMMUTABLE_FINDING_COLUMNS)}"
        )

    def test_a_proposal_needs_an_authorized_promotion_to_take_effect(
        self, ton_session: Session
    ) -> None:
        from onyx.db.ton.occurrences import promote_interpretation__no_commit

        finding, attempt = _finding_with_pending_interpretation(ton_session)
        occurrence = finding.occurrence
        complete_interpretation(
            ton_session,
            finding=finding,
            attempt=attempt,
            summary="Synthetic summary",
            proposed_criticality=OccurrenceCriticality.CRITICAL,
        )
        assert occurrence.criticality is not OccurrenceCriticality.CRITICAL

        actor = factories.make_user(ton_session)
        event = promote_interpretation__no_commit(
            ton_session,
            occurrence=occurrence,
            actor_user_id=actor.id,
            authorization_reference="SYN-ATA-4",
            criticality=attempt.proposed_criticality,
        )
        ton_session.commit()

        assert occurrence.criticality is OccurrenceCriticality.CRITICAL
        assert occurrence.requires_human_closure is True
        assert event.authorization_reference == "SYN-ATA-4"


class TestInputScopePrivacyContract:
    def test_full_evidence_is_refused_under_metadata_only_content_mode(
        self, ton_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Plan 002 / D-015: a deployment that promised not to send content must
        not be able to persist an attempt that did."""
        from onyx.db.ton import interpretations as module

        monkeypatch.setattr(module, "TON_TRACE_CONTENT_MODE", "metadata")
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        with pytest.raises(ValueError, match="metadata-only"):
            begin_interpretation(
                ton_session,
                finding=result.finding,
                prompt_key=PROMPT_KEY,
                prompt_version=PROMPT_VERSION,
                input_scope=InterpretationInputScope.FULL_EVIDENCE,
            )

    @pytest.mark.parametrize(
        "scope",
        [
            InterpretationInputScope.STRUCTURED_ONLY,
            InterpretationInputScope.MASKED_EXCERPT,
        ],
    )
    def test_the_narrower_scopes_stay_available_under_metadata_only(
        self,
        ton_session: Session,
        monkeypatch: pytest.MonkeyPatch,
        scope: InterpretationInputScope,
    ) -> None:
        from onyx.db.ton import interpretations as module

        monkeypatch.setattr(module, "TON_TRACE_CONTENT_MODE", "metadata")
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        attempt = begin_interpretation(
            ton_session,
            finding=result.finding,
            prompt_key=PROMPT_KEY,
            prompt_version=PROMPT_VERSION,
            input_scope=scope,
        )
        assert attempt.input_scope is scope

    def test_full_evidence_is_available_when_content_mode_permits_it(
        self, ton_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from onyx.db.ton import interpretations as module

        monkeypatch.setattr(module, "TON_TRACE_CONTENT_MODE", "full")
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        attempt = begin_interpretation(
            ton_session,
            finding=result.finding,
            prompt_key=PROMPT_KEY,
            prompt_version=PROMPT_VERSION,
            input_scope=InterpretationInputScope.FULL_EVIDENCE,
        )
        assert attempt.input_scope is InterpretationInputScope.FULL_EVIDENCE


class TestFinalityGate:
    def test_a_finding_is_final_only_when_completed_or_not_required(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        # NOT_REQUIRED: no interpretation was ever asked for.
        assert is_interpretation_final(result.finding)

        attempt = begin_interpretation(
            ton_session,
            finding=result.finding,
            prompt_key=PROMPT_KEY,
            prompt_version=PROMPT_VERSION,
            input_scope=InterpretationInputScope.STRUCTURED_ONLY,
            llm_provider=PROVIDER,
            model_name=MODEL,
        )
        assert not is_interpretation_final(result.finding)

        fail_interpretation(
            ton_session,
            finding=result.finding,
            attempt=attempt,
            failure_class=InterpretationFailureClass.TIMEOUT,
            retry_eligible=True,
        )
        assert not is_interpretation_final(result.finding)

        retry = begin_interpretation(
            ton_session,
            finding=result.finding,
            prompt_key=PROMPT_KEY,
            prompt_version=PROMPT_VERSION,
            input_scope=InterpretationInputScope.STRUCTURED_ONLY,
            llm_provider=PROVIDER,
            model_name=MODEL,
        )
        complete_interpretation(
            ton_session,
            finding=result.finding,
            attempt=retry,
            summary="Synthetic summary",
        )
        assert is_interpretation_final(result.finding)

    def test_non_final_findings_are_identifiable_for_an_operator(
        self, ton_session: Session
    ) -> None:
        """A FAILED interpretation must stay queryable, not disappear."""
        finding, attempt = _finding_with_pending_interpretation(ton_session)
        fail_interpretation(
            ton_session,
            finding=finding,
            attempt=attempt,
            failure_class=InterpretationFailureClass.POLICY_REFUSAL,
            retry_eligible=False,
        )

        stuck = ton_session.scalars(
            select(Finding).where(
                Finding.interpretation_status.in_(
                    [
                        InterpretationStatus.PENDING,
                        InterpretationStatus.RUNNING,
                        InterpretationStatus.FAILED,
                    ]
                )
            )
        ).all()
        assert [item.id for item in stuck] == [finding.id]
