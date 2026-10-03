"""Carrying review decisions over re-imports (change carry-over-decisions-on-reimport).

A new NG import of the same evidence keeps the human decisions, recorded as
system decisions that point back to the original. Changed evidence goes back to
a person. Decided cases a new import no longer shows get a verification event.
The preview computes the same outcome without persisting anything.
"""

import datetime
from io import BytesIO
from unittest.mock import Mock
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import financial_domain
from onyx.db.ton.enums import OccurrenceStatus, OccurrenceTransition
from onyx.db.ton.models import (
    FinancialNormalizationRun,
    FinancialReconciliationItem,
    Finding,
    ImportProfileExecution,
    Occurrence,
    OccurrenceEvent,
    ReviewDecision,
    ReviewRun,
    SourceSnapshot,
)
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.client_import.service import preview_client_import
from onyx.ton.financial_domain.models import InputPolicy
from onyx.ton.financial_review import service
from onyx.ton.financial_review.models import (
    JustificationCategory,
    ReviewDecisionKind,
)
from onyx.ton.financial_review.service import dataset_summary
from onyx.ton.ng_financial.service import execute_ng_profile
from onyx.ton.sources.models import SourceFormat
from onyx.ton.sources.validation import MEDIA_TYPES
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.test_financial_domain import (
    build_complete_synthetic_scope,
)
from tests.external_dependency_unit.ton.test_financial_review import (
    DAY,
    Pipeline,
    book,
    decide,
    finding_for,
    launch,
    original_rows,
)


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


def shifted_rows() -> list[list[object]]:
    """The original evidence, two rows lower: a cleaned export shifts rows."""
    return [
        launch("1.1 - Synthetic account", DAY[10], document="NEW-1", movement=11),
        launch(None, DAY[11], document="NEW-2", movement=12),
        *original_rows(),
    ]


def justify(session: Session, user: User, occurrence_id: UUID) -> None:
    decide(
        session,
        user,
        occurrence_id,
        ReviewDecisionKind.JUSTIFY_EXCEPTION,
        authorization_reference="SYN-TICKET-1",
        justification_category=JustificationCategory.BUSINESS_EXCEPTION,
    )


def preview(session: Session, user: User, content: bytes) -> dict[str, int]:
    view = preview_client_import(
        session,
        user,
        "financial_launches",
        BytesIO(content),
        "synthetic.xlsx",
        MEDIA_TYPES[SourceFormat.XLSX],
    )
    return {
        "carried_over": view.carried_over,
        "evidence_changed": view.evidence_changed,
        "still_open": view.still_open,
        "reopened": view.reopened,
        "new": view.new,
        "not_detected": view.not_detected,
    }


def test_same_evidence_on_shifted_rows_keeps_the_decision(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    first = pipeline.review(pipeline.parse(book(original_rows())))
    unit = finding_for(ton_session, first, "NGF-UNIT-MISSING")
    duplicate = finding_for(ton_session, first, "NGF-DUP-EXACT")
    justify(ton_session, admin, unit.occurrence_id)
    justify(ton_session, admin, duplicate.occurrence_id)

    second = pipeline.review(pipeline.parse(book(shifted_rows())))

    assert second.statistics["occurrences_decisions_carried_over"] == 2
    for occurrence_id in (unit.occurrence_id, duplicate.occurrence_id):
        assert (
            finding_for(
                ton_session,
                second,
                "NGF-UNIT-MISSING"
                if occurrence_id == unit.occurrence_id
                else "NGF-DUP-EXACT",
            ).occurrence_id
            == occurrence_id
        )
        occurrence = ton_session.get(Occurrence, occurrence_id)
        assert occurrence is not None
        assert occurrence.status is OccurrenceStatus.RISK_ACCEPTED
        decisions = service.list_decisions(ton_session, admin, occurrence_id, 10, 0)
        assert [item.basis for item in decisions] == ["HUMAN", "CARRIED_OVER"]
        carried = decisions[1]
        assert carried.actor_user_id is None
        assert carried.carried_from_decision_id == decisions[0].id
        assert carried.carried_from_actor_user_id == admin.id
        assert carried.carried_from_at == decisions[0].created_at
        assert carried.kind is ReviewDecisionKind.JUSTIFY_EXCEPTION
    # The reviewed dataset of the new import is downstream-safe for both cases.
    summary = dataset_summary(ton_session, admin, pipeline.source_id, second.id)
    assert summary.dispositions.get("REVIEW_REQUIRED", 0) == 0


def test_changed_evidence_goes_back_to_a_person(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    first = pipeline.review(pipeline.parse(book(original_rows())))
    duplicate = finding_for(ton_session, first, "NGF-DUP-EXACT")
    justify(ton_session, admin, duplicate.occurrence_id)
    # Same duplicate group, now with a third copy: same case, new evidence.
    rows = original_rows()
    tripled = [*rows[:4], launch(None, DAY[2], document="D-3", movement=70), rows[4]]

    assert preview(ton_session, admin, book(tripled))["evidence_changed"] == 1
    second = pipeline.review(pipeline.parse(book(tripled)))

    assert second.statistics["occurrences_reopened_evidence_changed"] == 1
    assert "occurrences_decisions_carried_over" not in second.statistics
    occurrence = ton_session.get(Occurrence, duplicate.occurrence_id)
    assert occurrence is not None
    assert occurrence.status is OccurrenceStatus.REOPENED
    last = ton_session.scalar(
        select(OccurrenceEvent)
        .where(OccurrenceEvent.occurrence_id == duplicate.occurrence_id)
        .order_by(OccurrenceEvent.sequence_no.desc())
        .limit(1)
    )
    assert last is not None
    assert last.transition is OccurrenceTransition.REOPENED
    assert last.context["carry_over"] == "EVIDENCE_CHANGED"
    # The earlier human decision stays in the history as context.
    decisions = service.list_decisions(
        ton_session, admin, duplicate.occurrence_id, 10, 0
    )
    assert [item.basis for item in decisions] == ["HUMAN"]


def test_decided_case_absent_from_new_import_is_recorded(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    first = pipeline.review(pipeline.parse(book(original_rows())))
    duplicate = finding_for(ton_session, first, "NGF-DUP-EXACT")
    justify(ton_session, admin, duplicate.occurrence_id)
    without_copy = [row for index, row in enumerate(original_rows()) if index != 3]

    second = pipeline.review(pipeline.parse(book(without_copy)))

    assert second.statistics["decided_not_detected"] == 1
    snapshot_id = ton_session.scalar(
        select(ReviewRun.snapshot_id).where(ReviewRun.id == second.id)
    )
    event = ton_session.scalar(
        select(OccurrenceEvent)
        .where(OccurrenceEvent.occurrence_id == duplicate.occurrence_id)
        .order_by(OccurrenceEvent.sequence_no.desc())
        .limit(1)
    )
    assert event is not None
    assert event.transition in (
        OccurrenceTransition.VERIFICATION_PASSED,
        OccurrenceTransition.VERIFICATION_FAILED,
    )
    assert event.context["not_detected_in_snapshot_id"] == str(snapshot_id)
    occurrence = ton_session.get(Occurrence, duplicate.occurrence_id)
    assert occurrence is not None
    # Verification records; it never closes or reopens a decided case.
    assert occurrence.status is OccurrenceStatus.RISK_ACCEPTED


def test_preview_matches_the_import_and_persists_nothing(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    first = pipeline.review(pipeline.parse(book(original_rows())))
    unit = finding_for(ton_session, first, "NGF-UNIT-MISSING")
    justify(ton_session, admin, unit.occurrence_id)
    content = book(shifted_rows())

    def counts() -> tuple[int, ...]:
        return tuple(
            int(ton_session.scalar(select(func.count()).select_from(model)) or 0)
            for model in (
                SourceSnapshot,
                ImportProfileExecution,
                ReviewRun,
                Finding,
                OccurrenceEvent,
                ReviewDecision,
            )
        )

    before = counts()
    predicted = preview(ton_session, admin, content)
    assert counts() == before
    # The unit decision carries and the open duplicate stays open. A rejected
    # row is known only by its position (the parser keeps no cell values), so
    # shifting rows makes it a new case and the old one "not detected".
    assert predicted == {
        "carried_over": 1,
        "evidence_changed": 0,
        "still_open": 1,
        "reopened": 0,
        "new": 1,
        "not_detected": 1,
    }

    second = pipeline.review(pipeline.parse(content))
    assert second.statistics["occurrences_repeated_human_decision_kept"] == 1
    assert second.statistics["occurrences_repeated"] == 1
    assert second.statistics["occurrences_new"] == 1


def test_reconciliation_decision_follows_the_reimported_record(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    run_id, _account_id, _unit_id = build_complete_synthetic_scope(
        ton_session, admin, store
    )
    item = ton_session.scalar(
        select(FinancialReconciliationItem).where(
            FinancialReconciliationItem.run_id == run_id,
            FinancialReconciliationItem.actual_fact_id.is_not(None),
        )
    )
    assert item is not None
    financial_domain.decide_reconciliation(
        ton_session, admin, run_id, item.id, "NOT_SAME_EVENT", "Synthetic reason"
    )
    ton_session.commit()

    # Re-import the same NG file: new execution, new record ids, same content.
    request = financial_domain.normalization_request_for_run(ton_session, admin, run_id)
    previous = ton_session.get(ReviewRun, request.review_run_id)
    assert previous is not None
    execution = ton_session.get(ImportProfileExecution, previous.execution_id)
    assert execution is not None
    reparsed = execute_ng_profile(
        ton_session,
        admin,
        request.ng_source_id,
        execution.snapshot_id,
        execution.profile_id,
        store,
    )
    review = service.execute_review(
        ton_session, admin, request.ng_source_id, reparsed.id
    )
    reviewed = dataset_summary(ton_session, admin, request.ng_source_id, review.id)
    rerun = financial_domain.normalize(
        ton_session,
        admin,
        request.model_copy(update={"review_run_id": review.id}),
        reviewed.dataset_revision,
        reviewed.as_of,
    )
    ton_session.commit()

    assert rerun.id != run_id
    assert rerun.statistics["reconciliation_decisions_carried_over"] == 1
    statuses = set(
        ton_session.scalars(
            select(FinancialReconciliationItem.status).where(
                FinancialReconciliationItem.run_id == rerun.id,
                FinancialReconciliationItem.actual_fact_id.is_not(None),
            )
        )
    )
    assert statuses == {"NOT_SAME_EVENT"}
    stored = ton_session.get(FinancialNormalizationRun, rerun.id)
    assert stored is not None
    assert stored.input_policy == "ACTUAL_AND_APPROVED_BUDGET"


def test_actual_only_policy_refuses_budget_inputs(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    run_id, _account_id, _unit_id = build_complete_synthetic_scope(
        ton_session, admin, store
    )
    request = financial_domain.normalization_request_for_run(ton_session, admin, run_id)
    assert request.budgets
    with pytest.raises(OnyxError):
        financial_domain.normalize(
            ton_session,
            admin,
            request.model_copy(update={"input_policy": InputPolicy.ACTUAL_ONLY}),
            "unused",
            datetime.datetime.now(datetime.UTC),
        )
