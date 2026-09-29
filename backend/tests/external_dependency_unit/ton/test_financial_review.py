"""DATA-003 persistence, lineage, lifecycle, verification, ACL and migration.

Synthetic workbooks go through the real DATA-001 capture and DATA-002 parser, so
every review here runs on production-shaped parsed records.
"""

import datetime
import logging
from collections.abc import Sequence
from dataclasses import replace
from io import BytesIO
from typing import Any, cast
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User, UserGroup
from onyx.db.ton import financial_review as repository
from onyx.db.ton import import_profiles, sources
from onyx.db.ton.enums import (
    OccurrenceStatus,
    OccurrenceVerificationResult,
    RuleVersionOutcome,
    RuleVersionStatus,
)
from onyx.db.ton.models import (
    AnalysisRun,
    AnalysisRunRuleVersion,
    Finding,
    FindingEvidence,
    ImportProfileExecution,
    Occurrence,
    ParsedSourceRecord,
    ReviewDecision,
    ReviewRecommendation,
    ReviewRun,
    Rule,
    RuleVersion,
    SourceSnapshot,
    TonAuditEvent,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.financial_review import service
from onyx.ton.financial_review.catalog import DEFAULT_CATALOG
from onyx.ton.financial_review.models import (
    JustificationCategory,
    RecommendationKind,
    ReviewDecisionKind,
    ReviewDecisionRequest,
    ReviewDisposition,
    ReviewRunView,
)
from onyx.ton.financial_review.rules import DEFAULT_EXECUTORS
from onyx.ton.ng_financial.service import execute_ng_profile
from onyx.ton.sources.models import SourceCreate, SourceFormat
from onyx.ton.sources.service import import_file
from onyx.ton.sources.validation import MEDIA_TYPES
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import (
    downgrade,
    scratch_database,
    scratch_session,
    table_names,
    upgrade,
)

DATA_002_REVISION = "9d2c8f0a7e31"
DATA_003_TABLES = {"ton_review_run", "ton_review_recommendation", "ton_review_decision"}
DAY = [datetime.date(2026, 1, day) for day in range(1, 29)]
SECRET_HISTORY = "Synthetic confidential history 7731"
SECRET_UNIT = "901 - Synthetic secret unit"
SECRET_DOCUMENT = "SYN-DOC-55501"
Row = list[object]


def launch(
    account: str | None = None,
    day: object = None,
    unit: str | None = SECRET_UNIT,
    document: str | None = SECRET_DOCUMENT,
    history: str = SECRET_HISTORY,
    movement: object = 123,
    interest: object = 0,
) -> Row:
    return [
        account,
        day,
        unit,
        document,
        history,
        movement,
        0,
        movement,
        None,
        None,
        interest,
        0,
        0,
        0,
        0,
        0,
        movement,
    ]


def book(rows: Sequence[Row], sheet: str = "Jan") -> bytes:
    workbook = Workbook()
    worksheet = cast(Worksheet, workbook.active)
    worksheet.title = sheet
    for row in rows:
        worksheet.append(list(row))
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def original_rows(extra_clean: int = 0) -> list[Row]:
    """Row 2 lacks a unit, rows 3-4 are identical, row 5 is rejected."""
    rows = [
        launch("1.1 - Synthetic account", DAY[0], document="D-1"),
        launch(None, DAY[1], unit=None, document="D-2", movement=40),
        launch(None, DAY[2], document="D-3", movement=70),
        launch(None, None, document="D-3", movement=70),
        launch(None, DAY[3], document="D-5", interest="not-a-number"),
    ]
    rows += [
        launch(None, DAY[4 + index % 20], document=f"C-{index}", movement=index + 1)
        for index in range(extra_clean)
    ]
    return rows


def corrected_rows() -> list[Row]:
    """Row 2 now has a unit, the duplicate is gone, the rejection remains."""
    return [
        launch("1.1 - Synthetic account", DAY[0], document="D-1"),
        launch(None, DAY[1], document="D-2", movement=40),
        launch(None, DAY[2], document="D-3", movement=70),
        launch(None, DAY[3], document="D-5", interest="not-a-number"),
    ]


@pytest.fixture
def admin(ton_session: Session) -> User:
    user = factories.make_user(ton_session)
    group = factories.make_group(ton_session)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.FULL_ADMIN_PANEL_ACCESS]
    )
    factories.add_member(ton_session, group=group, user=user)
    ton_session.commit()
    return user


@pytest.fixture
def store() -> Mock:
    blobs: dict[str, bytes] = {}
    result = Mock(spec=FileStore)

    def save(content: BytesIO, *, file_id: str, **_kwargs: object) -> str:
        blobs[file_id] = content.read()
        return file_id

    result.save_file.side_effect = save
    result.read_file.side_effect = lambda key: BytesIO(blobs[key])
    result.delete_file.side_effect = lambda key, **_kwargs: blobs.pop(key, None)
    return result


class Pipeline:
    """DATA-001 capture and DATA-002 parse for one synthetic source."""

    def __init__(
        self,
        session: Session,
        user: User,
        store: FileStore,
        group_ids: Sequence[int] = (),
    ) -> None:
        self.session = session
        self.user = user
        self.store = store
        source = sources.create_source(
            session,
            user,
            SourceCreate(
                key="financial_launches",
                display_name="Synthetic NG source",
                acquisition_type="FILE_UPLOAD",
                status="ACTIVE",
                group_ids=list(group_ids),
            ),
        )
        session.commit()
        self.source_id = source.id
        self.profile_id = import_profiles.create_ng_profile_v1(
            session, user, source.id
        ).id
        session.commit()

    def parse(self, content: bytes) -> UUID:
        snapshot = import_file(
            self.session,
            self.user,
            self.source_id,
            BytesIO(content),
            "synthetic.xlsx",
            MEDIA_TYPES[SourceFormat.XLSX],
            self.store,
        )
        return self.reparse(snapshot.id)

    def reparse(self, snapshot_id: UUID) -> UUID:
        execution = execute_ng_profile(
            self.session,
            self.user,
            self.source_id,
            snapshot_id,
            self.profile_id,
            self.store,
        )
        return execution.id

    def review(self, execution_id: UUID, **kwargs: Any) -> ReviewRunView:
        return service.execute_review(
            self.session, self.user, self.source_id, execution_id, **kwargs
        )


def findings_of(session: Session, run: ReviewRunView) -> list[Finding]:
    return list(
        session.scalars(
            select(Finding)
            .where(Finding.analysis_run_id == run.analysis_run_id)
            .order_by(Finding.id)
        )
    )


def finding_for(session: Session, run: ReviewRunView, rule_key: str) -> Finding:
    matches = [
        item
        for item in findings_of(session, run)
        if item.deterministic_payload["rule_key"] == rule_key
    ]
    assert len(matches) == 1, (rule_key, len(matches))
    return matches[0]


def decide(
    session: Session,
    user: User,
    occurrence_id: UUID,
    kind: ReviewDecisionKind,
    **fields: Any,
) -> None:
    service.record_decision(
        session,
        user,
        occurrence_id,
        ReviewDecisionRequest(kind=kind, reason="Synthetic reason", **fields),
    )


def record_state(session: Session) -> dict[Any, Any]:
    return {
        row[0]: row[1]
        for row in session.execute(
            text(
                "SELECT id, md5(row_to_json(r)::text) FROM ton_parsed_source_record r "
                "ORDER BY id"
            )
        )
    }


def snapshot_state(session: Session) -> dict[Any, Any]:
    return {
        row[0]: row[1]
        for row in session.execute(
            text(
                "SELECT id, md5(row_to_json(s)::text) FROM ton_source_snapshot s "
                "ORDER BY id"
            )
        )
    }


# ---------------------------------------------------------------------------
# Review execution, lineage and reproducibility
# ---------------------------------------------------------------------------


def test_review_on_original_persists_findings_with_full_lineage(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(book(original_rows()))
    execution = ton_session.get(ImportProfileExecution, execution_id)
    assert execution is not None and execution.status == "PARTIAL"

    run = pipeline.review(execution_id)
    assert run.status == "SUCCEEDED" and not run.reused
    assert run.statistics["findings_created"] == 3
    assert run.statistics["input_records"] == 4
    assert run.statistics["input_records_rejected"] == 1

    unit = finding_for(ton_session, run, "NGF-UNIT-MISSING")
    [evidence] = ton_session.scalars(
        select(FindingEvidence).where(FindingEvidence.finding_id == unit.id)
    ).all()
    record = ton_session.get(ParsedSourceRecord, evidence.parsed_record_id)
    assert record is not None
    assert record.execution_id == execution_id
    assert record.snapshot_id == evidence.source_snapshot_id == run.snapshot_id
    assert (record.sheet_name, record.source_row_number) == ("Jan", 2)
    assert evidence.locator["sheet"] == "Jan" and evidence.locator["row"] == 2
    assert evidence.import_execution_id == execution_id
    assert evidence.extracted_value is None
    snapshot = ton_session.get(SourceSnapshot, record.snapshot_id)
    assert snapshot is not None and snapshot.source_id == pipeline.source_id

    rejected = finding_for(ton_session, run, "NGF-SRC-ROW-REJECTED")
    [diagnostic] = ton_session.scalars(
        select(FindingEvidence).where(FindingEvidence.finding_id == rejected.id)
    ).all()
    assert diagnostic.parsed_record_id is None
    assert diagnostic.import_execution_id == execution_id
    assert diagnostic.locator == {
        "kind": "parse_diagnostic",
        "role": "subject",
        "sheet": "Jan",
        "row": 5,
        "column": "K",
        "diagnostic_code": "INVALID_AMOUNT",
        "diagnostic_level": "ERROR",
        "execution_id": str(execution_id),
    }

    duplicate = finding_for(ton_session, run, "NGF-DUP-EXACT")
    members = ton_session.scalars(
        select(FindingEvidence.parsed_record_id).where(
            FindingEvidence.finding_id == duplicate.id
        )
    ).all()
    assert len(members) == 2

    # Every finding pins its rule version and has one recommendation.
    for finding in findings_of(ton_session, run):
        version = ton_session.get(RuleVersion, finding.rule_version_id)
        assert version is not None
        assert version.version == finding.deterministic_payload["rule_version"]
        [recommendation] = ton_session.scalars(
            select(ReviewRecommendation).where(
                ReviewRecommendation.finding_id == finding.id
            )
        ).all()
        assert recommendation.suggested_value is None
    # Every catalog rule is recorded with its outcome, including blocked ones.
    outcomes = {
        row.rule_version_id: row.outcome
        for row in ton_session.scalars(
            select(AnalysisRunRuleVersion).where(
                AnalysisRunRuleVersion.analysis_run_id == run.analysis_run_id
            )
        )
    }
    assert len(outcomes) == len(DEFAULT_CATALOG)
    assert RuleVersionOutcome.SKIPPED_MISSING_DATA in outcomes.values()
    statuses = {
        rule.code: version.status
        for rule, version in ton_session.execute(
            select(Rule, RuleVersion).join(RuleVersion, RuleVersion.rule_id == Rule.id)
        )
    }
    assert statuses["NGF-UNIT-MISSING"] is RuleVersionStatus.PENDING_APPROVAL
    assert statuses["NGF-HIER-RECONCILIATION"] is RuleVersionStatus.TEST_ONLY
    assert statuses["NGF-XS-DOTACAO-OVERRUN"] is RuleVersionStatus.DRAFT
    analysis = ton_session.get(AnalysisRun, run.analysis_run_id)
    assert analysis is not None and analysis.status.value == "COMPLETED"
    actions = set(ton_session.scalars(select(TonAuditEvent.action)))
    assert {"ton_review.start", "ton_review.succeed"} <= actions


def test_rerun_is_idempotent_and_sources_stay_immutable(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(book(original_rows()))
    records_before = record_state(ton_session)
    snapshots_before = snapshot_state(ton_session)

    first = pipeline.review(execution_id)
    again = pipeline.review(execution_id)
    assert again.reused and again.id == first.id
    assert len(findings_of(ton_session, first)) == 3
    occurrences = ton_session.scalar(select(func.count()).select_from(Occurrence))

    # A re-parse of the same snapshot is a new input; the cases stay the same.
    execution = ton_session.get(ImportProfileExecution, execution_id)
    assert execution is not None
    second_execution = pipeline.reparse(execution.snapshot_id)
    second = pipeline.review(second_execution)
    assert second.id != first.id
    assert ton_session.scalar(select(func.count()).select_from(Occurrence)) == (
        occurrences
    )
    for finding in findings_of(ton_session, second):
        occurrence = ton_session.get(Occurrence, finding.occurrence_id)
        assert occurrence is not None and occurrence.detection_count == 2

    records_after = record_state(ton_session)
    snapshots_after = snapshot_state(ton_session)
    assert {key: records_after[key] for key in records_before} == records_before
    assert {key: snapshots_after[key] for key in snapshots_before} == snapshots_before

    stored = ton_session.get(ReviewRun, first.id)
    assert stored is not None
    stored.error_code = "changed"
    with pytest.raises(ValueError, match="immutable"):
        ton_session.flush()
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(
            text("UPDATE ton_review_run SET statistics = '{}' WHERE id = :id"),
            {"id": first.id},
        )
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(
            text("UPDATE ton_review_recommendation SET explanation = 'x'")
        )
    ton_session.rollback()


def test_new_rule_version_keeps_history_and_unbumped_change_is_refused(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(book(original_rows()))
    first = pipeline.review(execution_id)
    unit = DEFAULT_CATALOG.get("NGF-UNIT-MISSING")

    edited = DEFAULT_CATALOG.replace(replace(unit, description="Edited wording"))
    with pytest.raises(OnyxError) as refused:
        pipeline.review(execution_id, catalog=edited)
    assert refused.value.error_code is OnyxErrorCode.CONFLICT

    bumped = DEFAULT_CATALOG.replace(replace(unit, version=2))
    executors = {
        **DEFAULT_EXECUTORS,
        "NGF-UNIT-MISSING.v2": DEFAULT_EXECUTORS["NGF-UNIT-MISSING.v1"],
    }
    second = pipeline.review(execution_id, catalog=bumped, executors=executors)
    assert second.id != first.id and second.rule_set_digest != first.rule_set_digest
    old = finding_for(ton_session, first, "NGF-UNIT-MISSING")
    new = finding_for(ton_session, second, "NGF-UNIT-MISSING")
    assert old.deterministic_payload["rule_version"] == 1
    assert new.deterministic_payload["rule_version"] == 2
    assert old.rule_version_id != new.rule_version_id
    assert old.occurrence_id == new.occurrence_id
    stored = ton_session.get(ReviewRun, first.id)
    assert stored is not None
    assert {item["rule_key"]: item["version"] for item in stored.rule_set}[
        "NGF-UNIT-MISSING"
    ] == 1


def test_failure_leaves_no_partial_review(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(book(original_rows()))
    records_before = record_state(ton_session)
    with patch.object(
        repository,
        "verify_prior_occurrences__no_commit",
        side_effect=RuntimeError("synthetic failure"),
    ):
        with pytest.raises(OnyxError) as failed:
            pipeline.review(execution_id)
    assert failed.value.error_code is OnyxErrorCode.REVIEW_FAILED
    run = ton_session.scalar(select(ReviewRun))
    assert run is not None and run.status == "FAILED"
    assert run.error_code == "REVIEW_EXECUTION_FAILED:RuntimeError"
    assert ton_session.scalar(select(func.count()).select_from(Finding)) == 0
    assert ton_session.scalar(select(func.count()).select_from(Occurrence)) == 0
    analysis = ton_session.get(AnalysisRun, run.analysis_run_id)
    assert analysis is not None and analysis.status.value == "FAILED"
    assert record_state(ton_session) == records_before
    # A later attempt succeeds as a new attempt number.
    retry = pipeline.review(execution_id)
    assert retry.status == "SUCCEEDED" and retry.attempt_no == 2


def test_statement_count_does_not_grow_with_clean_records(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    counts: list[int] = []
    engine = ton_session.get_bind()
    pipeline = Pipeline(ton_session, admin, store)
    for extra in (0, 300):
        execution_id = pipeline.parse(book(original_rows(extra)))
        statements: list[str] = []

        def count(*args: Any, sink: list[str] = statements) -> None:
            sink.append(str(args[2]))

        event.listen(engine, "before_cursor_execute", count)
        try:
            run = pipeline.review(execution_id)
        finally:
            event.remove(engine, "before_cursor_execute", count)
        assert run.status == "SUCCEEDED"
        counts.append(len(statements))
        assert (
            sum(1 for item in statements if "FROM ton_parsed_source_record" in item)
            <= 3
        )
    # Same findings, 300 more records: the statement count must not scale.
    assert abs(counts[1] - counts[0]) <= 10, counts


def test_logs_carry_no_business_values(
    ton_session: Session,
    admin: User,
    store: FileStore,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(book(original_rows()))
    with caplog.at_level(logging.DEBUG):
        pipeline.review(execution_id)
    text_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "TON review" in text_logs
    for value in (SECRET_HISTORY, SECRET_UNIT, SECRET_DOCUMENT, "123", "not-a-number"):
        assert value not in text_logs


# ---------------------------------------------------------------------------
# Human decisions and the reviewed dataset
# ---------------------------------------------------------------------------


def test_human_decisions_and_dataset_dispositions(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(book(original_rows()))
    run = pipeline.review(execution_id)
    summary = service.dataset_summary(ton_session, admin, pipeline.source_id, run.id)
    assert summary.total_records == 4
    assert summary.dispositions[ReviewDisposition.ACCEPTED] == 1
    assert summary.dispositions[ReviewDisposition.REVIEW_REQUIRED] == 3
    assert summary.excluded_source_rows == 1
    assert not summary.downstream_ready
    assert summary.months[0].complete is False
    initial_revision = summary.dataset_revision
    before_decisions = datetime.datetime.now(datetime.UTC)

    unit = finding_for(ton_session, run, "NGF-UNIT-MISSING")
    duplicate = finding_for(ton_session, run, "NGF-DUP-EXACT")
    rejected = finding_for(ton_session, run, "NGF-SRC-ROW-REJECTED")
    [unit_recommendation] = repository.list_recommendations(ton_session, [unit.id])
    assert unit_recommendation.kind is RecommendationKind.SOURCE_CORRECTION_REQUIRED

    decide(ton_session, admin, unit.occurrence_id, ReviewDecisionKind.ACKNOWLEDGE)
    occurrence = ton_session.get(Occurrence, unit.occurrence_id)
    assert occurrence is not None and occurrence.status is OccurrenceStatus.NEW
    decide(
        ton_session,
        admin,
        unit.occurrence_id,
        ReviewDecisionKind.ACCEPT_RECOMMENDATION,
        recommendation_id=unit_recommendation.id,
    )
    decide(
        ton_session,
        admin,
        unit.occurrence_id,
        ReviewDecisionKind.REJECT_RECOMMENDATION,
        recommendation_id=unit_recommendation.id,
    )
    with pytest.raises(OnyxError) as missing_reference:
        decide(
            ton_session,
            admin,
            unit.occurrence_id,
            ReviewDecisionKind.REQUEST_SOURCE_CORRECTION,
        )
    assert missing_reference.value.error_code is OnyxErrorCode.INVALID_INPUT
    decide(
        ton_session,
        admin,
        unit.occurrence_id,
        ReviewDecisionKind.REQUEST_SOURCE_CORRECTION,
        authorization_reference="SYN-TICKET-1",
    )
    with pytest.raises(OnyxError) as no_category:
        decide(
            ton_session,
            admin,
            duplicate.occurrence_id,
            ReviewDecisionKind.JUSTIFY_EXCEPTION,
            authorization_reference="SYN-TICKET-2",
        )
    assert no_category.value.error_code is OnyxErrorCode.INVALID_INPUT
    decide(
        ton_session,
        admin,
        duplicate.occurrence_id,
        ReviewDecisionKind.JUSTIFY_EXCEPTION,
        authorization_reference="SYN-TICKET-2",
        justification_category=JustificationCategory.LEGITIMATE_REPETITION,
        comment="Synthetic comment",
    )
    decide(
        ton_session,
        admin,
        rejected.occurrence_id,
        ReviewDecisionKind.MARK_FALSE_POSITIVE,
        authorization_reference="SYN-TICKET-3",
    )
    with pytest.raises(OnyxError) as closed:
        decide(
            ton_session, admin, rejected.occurrence_id, ReviewDecisionKind.ACKNOWLEDGE
        )
    assert closed.value.error_code is OnyxErrorCode.CONFLICT

    statuses = {
        item.id: item.status for item in ton_session.scalars(select(Occurrence))
    }
    assert statuses[unit.occurrence_id] is OccurrenceStatus.CONFIRMED
    assert statuses[duplicate.occurrence_id] is OccurrenceStatus.RISK_ACCEPTED
    assert statuses[rejected.occurrence_id] is OccurrenceStatus.DISMISSED
    decisions = service.list_decisions(ton_session, admin, unit.occurrence_id, 50, 0)
    assert [item.kind for item in decisions] == [
        ReviewDecisionKind.ACKNOWLEDGE,
        ReviewDecisionKind.ACCEPT_RECOMMENDATION,
        ReviewDecisionKind.REJECT_RECOMMENDATION,
        ReviewDecisionKind.REQUEST_SOURCE_CORRECTION,
    ]
    assert decisions[-1].occurrence_event_id is not None

    summary = service.dataset_summary(ton_session, admin, pipeline.source_id, run.id)
    assert summary.dispositions[ReviewDisposition.CORRECTION_REQUIRED] == 1
    assert summary.dispositions[ReviewDisposition.JUSTIFIED_EXCEPTION] == 2
    assert summary.dispositions[ReviewDisposition.EXCLUDED_SOURCE_ERROR] == 0
    assert summary.months[0].complete
    assert summary.dataset_revision != initial_revision
    replay = service.dataset_summary(
        ton_session, admin, pipeline.source_id, run.id, as_of=before_decisions
    )
    assert replay.dataset_revision == initial_revision
    assert replay.dispositions[ReviewDisposition.REVIEW_REQUIRED] == 3

    required = service.dataset_records(
        ton_session,
        admin,
        pipeline.source_id,
        run.id,
        disposition=ReviewDisposition.CORRECTION_REQUIRED,
        sheet_month=None,
        account_code=None,
        administrative_unit=None,
        unit_missing=None,
        limit=10,
        offset=0,
    )
    assert [(item.row_number, item.rule_keys) for item in required] == [
        (2, ["NGF-UNIT-MISSING"])
    ]
    accepted = service.dataset_records(
        ton_session,
        admin,
        pipeline.source_id,
        run.id,
        disposition=ReviewDisposition.ACCEPTED,
        sheet_month=1,
        account_code=None,
        administrative_unit=None,
        unit_missing=False,
        limit=10,
        offset=0,
    )
    assert [item.row_number for item in accepted] == [1]
    assert all(item.downstream_safe for item in accepted)

    # Close the confirmed case once the source is corrected.
    decide(
        ton_session,
        admin,
        unit.occurrence_id,
        ReviewDecisionKind.CONFIRM_SOURCE_CORRECTION,
    )
    occurrence = ton_session.get(Occurrence, unit.occurrence_id)
    assert occurrence is not None and occurrence.status is OccurrenceStatus.RESOLVED
    decision = ton_session.scalar(select(ReviewDecision))
    assert decision is not None
    decision.reason = "changed"
    with pytest.raises(ValueError, match="append-only"):
        ton_session.flush()
    ton_session.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        ton_session.execute(text("UPDATE ton_review_decision SET reason = 'x'"))
    ton_session.rollback()
    actions = set(ton_session.scalars(select(TonAuditEvent.action)))
    assert {
        "ton_review.acknowledge",
        "ton_review.recommendation_accept",
        "ton_review.recommendation_reject",
        "ton_review.request_correction",
        "ton_review.justify",
        "ton_review.false_positive",
        "ton_review.confirm_correction",
    } <= actions


def test_justified_exception_survives_a_rerun(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(book(original_rows()))
    first = pipeline.review(execution_id)
    duplicate = finding_for(ton_session, first, "NGF-DUP-EXACT")
    decide(
        ton_session,
        admin,
        duplicate.occurrence_id,
        ReviewDecisionKind.JUSTIFY_EXCEPTION,
        authorization_reference="SYN-TICKET-9",
        justification_category=JustificationCategory.LEGITIMATE_REPETITION,
    )
    execution = ton_session.get(ImportProfileExecution, execution_id)
    assert execution is not None
    second = pipeline.review(pipeline.reparse(execution.snapshot_id))
    repeated = finding_for(ton_session, second, "NGF-DUP-EXACT")
    assert repeated.occurrence_id == duplicate.occurrence_id
    occurrence = ton_session.get(Occurrence, duplicate.occurrence_id)
    assert occurrence is not None
    assert occurrence.status is OccurrenceStatus.RISK_ACCEPTED
    assert second.statistics["occurrences_repeated_human_decision_kept"] == 1
    records = service.dataset_records(
        ton_session,
        admin,
        pipeline.source_id,
        second.id,
        disposition=ReviewDisposition.JUSTIFIED_EXCEPTION,
        sheet_month=None,
        account_code=None,
        administrative_unit=None,
        unit_missing=None,
        limit=10,
        offset=0,
    )
    assert len(records) == 2


def test_later_import_verifies_corrections_conservatively(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    first = pipeline.review(pipeline.parse(book(original_rows())))
    unit = finding_for(ton_session, first, "NGF-UNIT-MISSING")
    duplicate = finding_for(ton_session, first, "NGF-DUP-EXACT")
    rejected = finding_for(ton_session, first, "NGF-SRC-ROW-REJECTED")

    second = pipeline.review(pipeline.parse(book(corrected_rows())))
    assert second.statistics["verification_passed"] == 2
    assert second.statistics["verification_inconclusive"] == 1
    results = {
        item.id: item.verification_result
        for item in ton_session.scalars(select(Occurrence))
    }
    assert results[unit.occurrence_id] is OccurrenceVerificationResult.PASSED
    assert results[duplicate.occurrence_id] is OccurrenceVerificationResult.PASSED
    assert results[rejected.occurrence_id] is OccurrenceVerificationResult.INCONCLUSIVE
    # Verification never closes a case; a person does.
    occurrence = ton_session.get(Occurrence, unit.occurrence_id)
    assert occurrence is not None and occurrence.status is OccurrenceStatus.NEW
    assert "ton_review.verify_correction" in set(
        ton_session.scalars(select(TonAuditEvent.action))
    )
    summary = service.dataset_summary(ton_session, admin, pipeline.source_id, first.id)
    assert summary.dispositions[ReviewDisposition.SUPERSEDED_BY_CORRECTION] == 3
    assert summary.excluded_source_rows == 1
    later = service.dataset_summary(ton_session, admin, pipeline.source_id, second.id)
    assert later.dispositions[ReviewDisposition.ACCEPTED] == 3


def test_unresolved_or_ambiguous_later_import_is_not_verified(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    twin = launch(None, DAY[5], unit=None, document="T-1", movement=9)
    base = [launch("1.1 - Synthetic account", DAY[0], document="D-1"), twin, twin]
    # Two identical blank-unit records: one detection per record, one group.
    first = pipeline.review(pipeline.parse(book(base)))
    unit_findings = [
        item
        for item in findings_of(ton_session, first)
        if item.deterministic_payload["rule_key"] == "NGF-UNIT-MISSING"
    ]
    assert len(unit_findings) == 2

    # Still blank: detected again, never verified.
    unchanged = pipeline.review(
        pipeline.parse(book([*base, launch(None, DAY[9], document="NEW-1")]))
    )
    assert "verification_passed" not in unchanged.statistics
    for finding in unit_findings:
        occurrence = ton_session.get(Occurrence, finding.occurrence_id)
        assert occurrence is not None and occurrence.verification_result is None

    # One twin corrected: which one is ambiguous, so no unit case passes.
    fixed = launch(None, None, unit="902 - Unit", document="T-1", movement=9)
    partial = pipeline.review(pipeline.parse(book([base[0], twin, fixed])))
    assert partial.statistics["verification_inconclusive"] == 1
    results = [
        ton_session.get(Occurrence, finding.occurrence_id) for finding in unit_findings
    ]
    assert all(item is not None for item in results)
    verdicts = {item.verification_result for item in results if item is not None}
    assert OccurrenceVerificationResult.PASSED not in verdicts
    assert OccurrenceVerificationResult.INCONCLUSIVE in verdicts


# ---------------------------------------------------------------------------
# Access control and tenancy
# ---------------------------------------------------------------------------


def member(
    session: Session, group: UserGroup, permissions: Sequence[Permission]
) -> User:
    user = factories.make_user(session)
    own = factories.make_group(session)
    factories.grant_permissions(session, group=own, permissions=list(permissions))
    factories.add_member(session, group=own, user=user)
    factories.add_member(session, group=group, user=user)
    session.commit()
    return user


def test_access_follows_source_and_occurrence_acl(
    ton_head_template: str, ton_session: Session, store: FileStore
) -> None:
    finance = factories.make_group(ton_session)
    ton_session.commit()
    importer = member(
        ton_session,
        finance,
        [
            Permission.MANAGE_TON_SOURCES,
            Permission.IMPORT_TON_SOURCES,
            Permission.READ_TON_OCCURRENCES,
        ],
    )
    reviewer = member(
        ton_session,
        finance,
        [Permission.READ_TON_OCCURRENCES, Permission.MANAGE_TON_OCCURRENCES],
    )
    outsider = member(
        ton_session,
        factories.make_group(ton_session),
        [
            Permission.READ_TON_SOURCES,
            Permission.IMPORT_TON_SOURCES,
            Permission.READ_TON_OCCURRENCES,
            Permission.MANAGE_TON_OCCURRENCES,
        ],
    )
    pipeline = Pipeline(ton_session, importer, store, group_ids=[finance.id])
    execution_id = pipeline.parse(book(original_rows()))
    run = pipeline.review(execution_id)

    for call in (
        lambda: service.execute_review(
            ton_session, outsider, pipeline.source_id, execution_id
        ),
        lambda: repository.get_review_run(
            ton_session, outsider, pipeline.source_id, run.id
        ),
        lambda: service.dataset_summary(
            ton_session, outsider, pipeline.source_id, run.id
        ),
    ):
        with pytest.raises(OnyxError) as denied:
            call()
        assert denied.value.error_code is OnyxErrorCode.NOT_FOUND
        ton_session.rollback()

    visible = service.list_findings(
        ton_session, reviewer, repository.FindingFilters(review_run_id=run.id), 50, 0
    )
    assert len(visible) == 3
    assert (
        service.list_findings(ton_session, outsider, repository.FindingFilters(), 50, 0)
        == []
    )
    target = visible[0]
    with pytest.raises(OnyxError):
        service.get_finding(ton_session, outsider, target.id)
    ton_session.rollback()
    with pytest.raises(OnyxError):
        decide(
            ton_session, outsider, target.occurrence_id, ReviewDecisionKind.ACKNOWLEDGE
        )
    with pytest.raises(OnyxError):
        decide(
            ton_session, importer, target.occurrence_id, ReviewDecisionKind.ACKNOWLEDGE
        )
    decide(ton_session, reviewer, target.occurrence_id, ReviewDecisionKind.ACKNOWLEDGE)
    detail = service.get_finding(ton_session, reviewer, target.id)
    assert detail.recommendations and detail.explanation
    evidence = service.list_evidence(ton_session, reviewer, target.id, 50, 0)
    assert evidence and all(
        item.source_snapshot_id == run.snapshot_id for item in evidence
    )

    filtered = service.list_findings(
        ton_session,
        reviewer,
        repository.FindingFilters(
            rule_key="NGF-UNIT-MISSING", sheet_month=1, blocking=True
        ),
        50,
        0,
    )
    assert [item.rule_key for item in filtered] == ["NGF-UNIT-MISSING"]
    paged = service.list_findings(
        ton_session, reviewer, repository.FindingFilters(), 2, 0
    ) + service.list_findings(ton_session, reviewer, repository.FindingFilters(), 2, 2)
    assert len({item.id for item in paged}) == 3
    with pytest.raises(OnyxError):
        service.list_findings(
            ton_session, reviewer, repository.FindingFilters(), 101, 0
        )

    # Another tenant's schema holds none of this.
    with scratch_database(template=ton_head_template) as database:
        with scratch_session(database) as other:
            with pytest.raises(OnyxError):
                repository.get_review_run(other, importer, pipeline.source_id, run.id)
            assert (
                service.list_findings(
                    other, reviewer, repository.FindingFilters(), 50, 0
                )
                == []
            )


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def test_data_003_downgrade_and_reupgrade(ton_database: str) -> None:
    before = table_names(ton_database, "ton_")
    downgrade(ton_database, DATA_002_REVISION)
    after = table_names(ton_database, "ton_")
    assert before - after == DATA_003_TABLES
    with scratch_session(ton_database) as session:
        columns = {
            row[0]
            for row in session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'ton_finding_evidence'"
                )
            )
        }
    assert "parsed_record_id" not in columns
    upgrade(ton_database, "head")
    assert table_names(ton_database, "ton_") == before


def test_downgrade_refuses_while_review_runs_exist(
    ton_database: str, store: FileStore
) -> None:
    with scratch_session(ton_database) as session:
        user = factories.make_admin(session)
        session.commit()
        pipeline = Pipeline(session, user, store)
        pipeline.review(pipeline.parse(book(original_rows())))
    with pytest.raises(RuntimeError, match="DATA-003"):
        downgrade(ton_database, DATA_002_REVISION)
    assert DATA_003_TABLES <= table_names(ton_database, "ton_")


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_api_endpoints_are_bounded_and_expose_no_storage_or_values(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    from fastapi.routing import APIRoute

    from onyx.server.ton import financial_review as api

    paths = {route.path for route in api.router.routes if isinstance(route, APIRoute)}
    assert "/ton/financial-review/findings" in paths
    assert "/ton/financial-review/occurrences/{occurrence_id}/decisions" in paths

    catalog = api.get_rule_catalog(_user=admin)
    assert len(catalog.pop_capabilities) == 14
    assert {item.status for item in catalog.rules} >= {"ACTIVE", "BLOCKED"}

    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(book(original_rows()))
    run = api.run_review(
        pipeline.source_id, execution_id, user=admin, session=ton_session
    )
    listed = api.list_reviews(
        pipeline.source_id,
        execution_id=None,
        status=None,
        limit=50,
        offset=0,
        user=admin,
        session=ton_session,
    )
    assert [item.id for item in listed] == [run.id]
    assert (
        api.get_review(
            pipeline.source_id, run.id, user=admin, session=ton_session
        ).rule_set_digest
        == run.rule_set_digest
    )
    evaluations = api.list_rule_evaluations(
        pipeline.source_id, run.id, limit=100, offset=0, user=admin, session=ton_session
    )
    assert len(evaluations) == len(DEFAULT_CATALOG)
    by_key = {item.rule_key: item for item in evaluations}
    assert by_key["NGF-UNIT-MISSING"].finding_count == 1
    assert by_key["NGF-HIER-RECONCILIATION"].finding_count == 0

    findings = api.list_findings(
        source_id=pipeline.source_id,
        review_run_id=run.id,
        execution_id=None,
        rule_key=None,
        category=None,
        criticality=None,
        status=None,
        sheet_month=None,
        blocking=None,
        limit=50,
        offset=0,
        user=admin,
        session=ton_session,
    )
    assert len(findings) == 3
    detail = api.get_finding(findings[0].id, user=admin, session=ton_session)
    evidence = api.list_finding_evidence(
        findings[0].id, limit=50, offset=0, user=admin, session=ton_session
    )
    decision = api.record_decision(
        findings[0].occurrence_id,
        ReviewDecisionRequest(kind=ReviewDecisionKind.ACKNOWLEDGE, reason="Seen"),
        user=admin,
        session=ton_session,
    )
    decisions = api.list_decisions(
        findings[0].occurrence_id, limit=50, offset=0, user=admin, session=ton_session
    )
    assert [item.id for item in decisions] == [decision.id]
    summary = api.get_reviewed_dataset(
        pipeline.source_id, run.id, as_of=None, user=admin, session=ton_session
    )
    records = api.list_reviewed_records(
        pipeline.source_id,
        run.id,
        disposition=None,
        sheet_month=None,
        account_code=None,
        administrative_unit=None,
        unit_missing=None,
        as_of=None,
        limit=2,
        offset=0,
        user=admin,
        session=ton_session,
    )
    assert summary.total_records == 4 and len(records) == 2

    serialised = "\n".join(
        item.model_dump_json()
        for item in (run, *listed, *findings, detail, *evidence, summary, *records)
    )
    assert "storage_file_id" not in serialised and "ton-source/" not in serialised
    for value in (SECRET_HISTORY, SECRET_UNIT, SECRET_DOCUMENT):
        assert value not in serialised
