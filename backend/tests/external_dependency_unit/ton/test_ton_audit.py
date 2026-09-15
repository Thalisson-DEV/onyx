"""Persistent TON audit spec — Plan 003d.

The subject is the **division of guarantees** readiness §11 sets out, so most of
these tests are pairs: the same kind of failure, once against domain history and
once against the audit table, asserting opposite outcomes.

======================================== ==============================
Failure                                  Required outcome
======================================== ==============================
a ``TonReportRevision`` write fails       publication **fails**
an ``OccurrenceEvent`` write fails        the transition **fails**
a ``TonAuditEvent`` write fails           the business operation **continues**
======================================== ==============================

Real PostgreSQL is required: the best-effort guarantee rests on a SAVEPOINT, and a
mock cannot show that a failed INSERT left the caller's transaction usable — which
is the entire point. In PostgreSQL a failed statement aborts the whole
transaction, so a plain ``try/except`` would swallow the exception and still
destroy the business operation.

Run with::

    cd backend && uv run pytest tests/external_dependency_unit/ton/test_ton_audit.py
"""

import logging
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.db.ton.audit import (
    MAX_VALUE_LENGTH,
    REDACTED,
    SENSITIVE_KEY_FRAGMENTS,
    emit_ton_audit_event,
    fetch_audit_events,
    sanitize_audit_metadata,
)
from onyx.db.ton.enums import (
    OccurrenceActorKind,
    OccurrenceTransition,
    TonAuditResourceKind,
)
from onyx.db.ton.models import (
    OccurrenceEvent,
    TonAuditEvent,
    TonReport,
    TonReportRevision,
)
from onyx.db.ton.occurrences import apply_transition__no_commit
from onyx.db.ton.reports import publish_report_revision__no_commit
from onyx.utils.audit import (
    AUDIT_HANDLER_NAME,
    AUDIT_LOGGER_ROOT,
    AUDIT_SCHEMA_VERSION,
    AuditAction,
    AuditActor,
    AuditOutcome,
    OCSFEventClass,
    emit_audit_event,
    ocsf_class_for,
)
from tests.external_dependency_unit.ton import factories

# The four actions readiness §11 assigns to this table rather than to a domain
# history table.
TON_AUDIT_ACTIONS: tuple[AuditAction, ...] = (
    AuditAction.TON_REPORT_GENERATE,
    AuditAction.TON_RULE_VERSION_CHANGE,
    AuditAction.TON_MANUAL_OVERRIDE,
    AuditAction.TON_HUMAN_APPROVAL,
)


def _audit_row_count(db_session: Session) -> int:
    return int(db_session.scalar(select(func.count()).select_from(TonAuditEvent)) or 0)


def _revision_count(db_session: Session) -> int:
    return int(
        db_session.scalar(select(func.count()).select_from(TonReportRevision)) or 0
    )


class TestSuccessfulEmission:
    def test_an_event_persists(self, ton_session: Session) -> None:
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)

        event = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
            resource_kind=TonAuditResourceKind.REPORT,
            resource_id=report.id,
            domain_event_id=revision.id,
        )
        ton_session.commit()

        assert event is not None
        assert event.action == "ton_report.generate"
        assert event.outcome == "success"
        assert event.audit_schema_version == AUDIT_SCHEMA_VERSION
        assert event.resource_kind is TonAuditResourceKind.REPORT
        assert event.resource_id == report.id
        assert event.domain_event_id == revision.id

    @pytest.mark.parametrize("action", TON_AUDIT_ACTIONS)
    def test_each_required_ton_action_persists(
        self, ton_session: Session, action: AuditAction
    ) -> None:
        event = emit_ton_audit_event(
            ton_session, action=action, outcome=AuditOutcome.SUCCESS
        )
        ton_session.commit()

        assert event is not None
        assert event.action == action.value

    def test_the_ocsf_class_matches_the_stdout_stream(
        self, ton_session: Session
    ) -> None:
        """The table and the stream stay one schema, so a consumer reading both
        routes by the same class."""
        event = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_HUMAN_APPROVAL,
            outcome=AuditOutcome.SUCCESS,
        )
        ton_session.commit()

        assert event is not None
        assert event.ocsf_class == OCSFEventClass.API_ACTIVITY.value
        assert (
            ocsf_class_for(AuditAction.TON_HUMAN_APPROVAL)
            is OCSFEventClass.API_ACTIVITY
        )

    def test_every_audit_action_has_an_ocsf_class(self) -> None:
        """The import-time guard in ``onyx.utils.audit`` already enforces this; the
        assertion states it so a reader knows an unmapped action cannot ship."""
        unmapped = [
            action.value for action in AuditAction if ocsf_class_for(action) is None
        ]
        assert unmapped == []

    def test_the_actor_is_recorded(self, ton_session: Session) -> None:
        user = factories.make_user(ton_session)
        ton_session.flush()

        event = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_HUMAN_APPROVAL,
            outcome=AuditOutcome.SUCCESS,
            actor=AuditActor(
                user_id=str(user.id), email=user.email, auth_type="password"
            ),
            actor_user_id=user.id,
            authorization_reference="SYN-AUTH-1",
        )
        ton_session.commit()

        assert event is not None
        assert event.actor_user_id == user.id
        assert event.actor_email == user.email
        assert event.actor_auth_type == "password"
        assert event.authorization_reference == "SYN-AUTH-1"

    def test_a_non_uuid_actor_identity_does_not_break_emission(
        self, ton_session: Session
    ) -> None:
        """A service or API-key actor may carry a non-UUID identity. The textual
        columns still record it; the foreign key stays empty."""
        event = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
            actor=AuditActor(user_id="service-account", api_key_id="key-1"),
        )
        ton_session.commit()

        assert event is not None
        assert event.actor_user_id is None
        assert event.actor_api_key_id == "key-1"

    def test_events_are_queryable_by_resource(self, ton_session: Session) -> None:
        report = factories.make_report(ton_session)
        other = factories.make_report(ton_session)
        emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
            resource_kind=TonAuditResourceKind.REPORT,
            resource_id=report.id,
        )
        emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
            resource_kind=TonAuditResourceKind.REPORT,
            resource_id=other.id,
        )
        ton_session.commit()

        rows = fetch_audit_events(
            ton_session,
            resource_kind=TonAuditResourceKind.REPORT,
            resource_id=report.id,
        )
        assert [row.resource_id for row in rows] == [report.id]

    def test_an_audit_row_survives_the_deletion_of_its_actor(
        self, ton_session: Session
    ) -> None:
        """SET NULL, not CASCADE: removing an account must not erase the record
        that something was done."""
        user = factories.make_user(ton_session)
        ton_session.flush()
        user_id = user.id
        user_email = user.email
        event = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_MANUAL_OVERRIDE,
            outcome=AuditOutcome.SUCCESS,
            actor=AuditActor(user_id=str(user_id), email=user_email),
            actor_user_id=user_id,
        )
        ton_session.commit()
        assert event is not None
        event_id = event.id

        from onyx.db.models import User as UserModel

        account = ton_session.get(UserModel, user_id)
        assert account is not None
        ton_session.delete(account)
        ton_session.commit()
        ton_session.expire_all()

        reloaded = ton_session.get(TonAuditEvent, event_id)
        assert reloaded is not None
        assert reloaded.actor_user_id is None
        assert reloaded.actor_email == user_email


class TestBestEffortFailure:
    def test_a_failed_audit_write_returns_none_instead_of_raising(
        self, ton_session: Session
    ) -> None:
        """A half-complete resource pointer violates
        ``ck_ton_audit_event_resource_reference_complete``, so this is a real
        database failure, not a mocked one."""
        result = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
            resource_kind=TonAuditResourceKind.REPORT,
            resource_id=None,
        )
        assert result is None

    def test_a_failed_audit_write_leaves_the_business_operation_intact(
        self, ton_session: Session
    ) -> None:
        """The requirement, end to end: the published revision must survive, and
        the caller's transaction must still be committable.

        This is what the SAVEPOINT buys. Without it the failed INSERT would abort
        the whole transaction and the revision would be lost with it.
        """
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)
        revision_id = revision.id

        failed = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
            resource_kind=TonAuditResourceKind.REPORT,
            resource_id=None,
        )
        ton_session.commit()
        ton_session.expire_all()

        assert failed is None
        assert ton_session.get(TonReportRevision, revision_id) is not None
        assert _audit_row_count(ton_session) == 0

    def test_a_failed_audit_write_does_not_prevent_a_later_one(
        self, ton_session: Session
    ) -> None:
        """A poisoned transaction would make every subsequent write fail too."""
        assert (
            emit_ton_audit_event(
                ton_session,
                action=AuditAction.TON_REPORT_GENERATE,
                outcome=AuditOutcome.SUCCESS,
                resource_kind=TonAuditResourceKind.REPORT,
                resource_id=None,
            )
            is None
        )
        recovered = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
        )
        ton_session.commit()

        assert recovered is not None
        assert _audit_row_count(ton_session) == 1

    def test_a_failure_is_logged_for_an_operator(
        self, ton_session: Session, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Silent is not the same as swallowed: the caller is protected, the
        operator is told."""
        with caplog.at_level(logging.WARNING):
            emit_ton_audit_event(
                ton_session,
                action=AuditAction.TON_REPORT_GENERATE,
                outcome=AuditOutcome.SUCCESS,
                resource_kind=TonAuditResourceKind.REPORT,
                resource_id=None,
            )
        assert "could not be persisted" in caplog.text


class TestDomainHistoryStaysTransactional:
    def test_a_failed_report_revision_write_fails_the_publication(
        self, ton_session: Session
    ) -> None:
        """The opposite guarantee. A revision pointing at a report that does not
        exist violates the foreign key, and the failure must reach the caller."""
        detached = TonReport(
            id=uuid4(),
            code=f"SYN-REP-{factories.unique_suffix()}",
            report_type=factories.TonReportType.MONTHLY_CLOSE,
            title="Synthetic detached report",
        )

        with pytest.raises(IntegrityError):
            publish_report_revision__no_commit(
                ton_session,
                report=detached,
                body={"headline": "should not persist"},
                generator_version=factories.SYNTHETIC_GENERATOR_VERSION,
                generated_at=factories.SYNTHETIC_GENERATED_AT,
            )
        ton_session.rollback()

        assert _revision_count(ton_session) == 0

    def test_a_failed_occurrence_event_write_fails_the_transition(
        self, ton_session: Session
    ) -> None:
        """``OccurrenceEvent`` is authoritative history, so a rejected write must
        raise rather than be dropped."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )

        with pytest.raises(ValueError):
            apply_transition__no_commit(
                ton_session,
                occurrence=result.occurrence,
                # Human-only: it requires an identified user and an authorization
                # reference, neither of which is supplied.
                transition=OccurrenceTransition.ACCEPT_RISK,
                actor_kind=OccurrenceActorKind.SYSTEM,
            )

    def test_the_database_refuses_a_human_only_event_from_the_system(
        self, ton_session: Session
    ) -> None:
        """The guarantee does not depend on the Python guard above."""
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.flush()

        ton_session.add(
            OccurrenceEvent(
                occurrence_id=result.occurrence.id,
                sequence_no=99,
                transition=OccurrenceTransition.ACCEPT_RISK,
                resulting_status=result.occurrence.status,
                actor_kind=OccurrenceActorKind.SYSTEM,
                occurred_at=factories.SYNTHETIC_DETECTED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            ton_session.flush()
        ton_session.rollback()

    def test_only_the_audit_module_swallows_a_write_failure(self) -> None:
        """An inverse assertion: no domain-history module may adopt the
        best-effort contract by importing the audit emitter into its write path."""
        import inspect

        from onyx.db.ton import (
            interpretations,
            occurrence_records,
            occurrences,
            reports,
        )

        for module in (occurrences, occurrence_records, interpretations, reports):
            source = inspect.getsource(module)
            assert "emit_ton_audit_event" not in source, (
                f"{module.__name__} is authoritative history and must not depend "
                "on a best-effort sink"
            )


class TestPayloadIsAReferenceNotACopy:
    def test_a_published_payload_is_never_copied_into_the_audit_row(
        self, ton_session: Session
    ) -> None:
        """Readiness §11's anti-duplication rule. The domain table stays the
        source of truth."""
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)

        event = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
            resource_kind=TonAuditResourceKind.REPORT_REVISION,
            resource_id=revision.id,
            domain_event_id=revision.id,
            extra={"canonical_payload": revision.canonical_payload},
        )
        ton_session.commit()

        assert event is not None
        assert event.extra["canonical_payload"] == REDACTED
        assert event.resource_id == revision.id
        assert event.domain_event_id == revision.id

    def test_the_audit_table_holds_no_content_columns(self) -> None:
        """Structural: there is nowhere to put a copy of a domain row."""
        columns = set(TonAuditEvent.__table__.columns.keys())
        for forbidden in (
            "canonical_payload",
            "content_hash",
            "summary",
            "evidence",
            "extracted_value",
        ):
            assert forbidden not in columns

    @pytest.mark.parametrize("fragment", SENSITIVE_KEY_FRAGMENTS)
    def test_every_declared_sensitive_fragment_is_redacted(self, fragment: str) -> None:
        sanitized = sanitize_audit_metadata({f"field_{fragment}_value": "leak"})
        assert sanitized == {f"field_{fragment}_value": REDACTED}

    def test_a_nested_secret_is_redacted_too(self) -> None:
        """A nested mapping hides a key just as well as a top-level one."""
        sanitized = sanitize_audit_metadata(
            {"outer": {"api_key": "leak", "safe": "kept"}}
        )
        assert sanitized == {"outer": {"api_key": REDACTED, "safe": "kept"}}

    def test_a_secret_inside_a_list_of_mappings_is_redacted(self) -> None:
        sanitized = sanitize_audit_metadata({"items": [{"password": "leak"}]})
        assert sanitized == {"items": [{"password": REDACTED}]}

    def test_long_free_text_is_truncated_so_the_row_stays_a_reference(self) -> None:
        sanitized = sanitize_audit_metadata({"note": "x" * (MAX_VALUE_LENGTH + 50)})
        assert sanitized is not None
        assert sanitized["note"].endswith("[truncated]")
        assert len(sanitized["note"]) == MAX_VALUE_LENGTH + len("[truncated]")

    def test_absent_metadata_stays_absent(self) -> None:
        assert sanitize_audit_metadata(None) is None

    def test_before_and_after_metadata_is_sanitized(self, ton_session: Session) -> None:
        event = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_MANUAL_OVERRIDE,
            outcome=AuditOutcome.SUCCESS,
            before_state={"criticality": "MEDIUM", "raw_evidence_content": "leak"},
            after_state={"criticality": "HIGH"},
        )
        ton_session.commit()

        assert event is not None
        assert event.before_state == {
            "criticality": "MEDIUM",
            "raw_evidence_content": REDACTED,
        }
        assert event.after_state == {"criticality": "HIGH"}

    def test_a_resource_pointer_must_be_complete(self, ton_session: Session) -> None:
        """Half a pointer silently drops an event out of a resource's history, so
        the database refuses it."""
        ton_session.add(
            TonAuditEvent(
                audit_schema_version=AUDIT_SCHEMA_VERSION,
                action="ton_report.generate",
                outcome="success",
                resource_kind=TonAuditResourceKind.REPORT,
                resource_id=None,
            )
        )
        with pytest.raises(IntegrityError):
            ton_session.flush()
        ton_session.rollback()


class TestReportGenerationAudit:
    def test_a_revision_and_its_audit_event_coexist(self, ton_session: Session) -> None:
        """Readiness §11 maps report generation to both: the revision is the
        authoritative immutable record, the audit row is the actor attribution."""
        user = factories.make_user(ton_session)
        report = factories.make_report(ton_session)
        ton_session.flush()

        revision = factories.publish_synthetic_revision(
            ton_session, report=report, generated_by=user.id
        )
        event = emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
            actor=AuditActor(user_id=str(user.id), email=user.email),
            actor_user_id=user.id,
            resource_kind=TonAuditResourceKind.REPORT_REVISION,
            resource_id=revision.id,
            domain_event_id=revision.id,
        )
        ton_session.commit()

        assert event is not None
        assert revision.generated_by == user.id
        assert _revision_count(ton_session) == 1
        assert _audit_row_count(ton_session) == 1

    def test_only_the_audit_row_failing_does_not_roll_back_the_revision(
        self, ton_session: Session
    ) -> None:
        """The explicit requirement: a failure to write only the audit event must
        not delete an otherwise valid published revision."""
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)
        revision_hash = revision.content_hash

        assert (
            emit_ton_audit_event(
                ton_session,
                action=AuditAction.TON_REPORT_GENERATE,
                outcome=AuditOutcome.SUCCESS,
                resource_kind=TonAuditResourceKind.REPORT_REVISION,
                resource_id=None,
            )
            is None
        )
        ton_session.commit()
        ton_session.expire_all()

        from onyx.db.ton.reports import get_revision, verify_revision_hash

        reloaded = get_revision(ton_session, report_id=report.id, revision_no=1)
        assert reloaded is not None
        assert reloaded.content_hash == revision_hash
        assert verify_revision_hash(reloaded) is True
        assert _audit_row_count(ton_session) == 0


class TestExistingStdoutAuditIsUntouched:
    @pytest.fixture()
    def audit_records(self) -> Iterator[list[str]]:
        """Collect what reaches the ``onyx.audit`` logger tree, then detach."""
        collected: list[str] = []

        class _Collector(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                collected.append(record.getMessage())

        handler = _Collector(level=logging.INFO)
        audit_root = logging.getLogger(AUDIT_LOGGER_ROOT)
        audit_root.addHandler(handler)
        try:
            yield collected
        finally:
            audit_root.removeHandler(handler)

    def test_the_stdout_emitter_still_works(self, audit_records: list[str]) -> None:
        """003d is additive. No global logging refactor, and the SIEM export path
        is unchanged.

        Observed by attaching a handler to the ``onyx.audit`` tree rather than by
        capturing output. ``caplog`` cannot see it — the audit root sets
        ``propagate = False`` deliberately — and the installed stdout handler binds
        whatever ``sys.stdout`` was at import time, which under pytest is the test
        runner's own capture object rather than the file descriptor.
        """
        emit_audit_event(
            AuditAction.TON_REPORT_GENERATE,
            AuditOutcome.SUCCESS,
            resource_type="ton_report",
            resource_id="synthetic",
        )
        assert any("ton_report.generate" in message for message in audit_records)

    def test_the_stdout_handler_is_still_installed(self) -> None:
        audit_root = logging.getLogger(AUDIT_LOGGER_ROOT)
        assert any(
            handler.name == AUDIT_HANDLER_NAME for handler in audit_root.handlers
        )
        assert audit_root.propagate is False

    def test_the_persistent_sink_writes_no_stdout_line(
        self, ton_session: Session, audit_records: list[str]
    ) -> None:
        """Two sinks, two calls. Emitting to the table must not double-log, and a
        call site that wants both makes both calls explicitly."""
        emit_ton_audit_event(
            ton_session,
            action=AuditAction.TON_REPORT_GENERATE,
            outcome=AuditOutcome.SUCCESS,
        )
        ton_session.commit()

        assert audit_records == []

    def test_the_stdout_emitter_takes_no_session(self) -> None:
        """It holds no ``db_session`` and must not grow one: that is what keeps it
        usable off the request path."""
        import inspect

        assert "db_session" not in inspect.signature(emit_audit_event).parameters
