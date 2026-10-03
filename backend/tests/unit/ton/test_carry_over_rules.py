"""Pure carry-over rules: evidence fingerprint and classification."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from onyx.db.ton.enums import OccurrenceStatus
from onyx.ton.financial_review.adapters import review_record
from onyx.ton.financial_review.carry_over import (
    CarryOutcome,
    classify,
    evidence_fingerprint,
)
from onyx.ton.financial_review.models import Detection, DetectionScope, ReviewRecord
from onyx.ton.ng_financial.parser import AMOUNT_FIELDS


def record(row: int, amount: str = "10", history: str = "Synthetic") -> ReviewRecord:
    return review_record(
        record_id=uuid4(),
        sheet_name="Jan",
        row_number=row,
        sheet_month=1,
        account_code="1.1",
        account_label="Synthetic account",
        emission_date=date(2026, 1, 5),
        administrative_unit=None,
        document_number="D-1",
        history=history,
        amounts={name: Decimal(amount) for name in AMOUNT_FIELDS},
        physical_date="05/01/2026",
        physical_unit=None,
        fingerprint="f",
        duplicate_ordinal=1,
    )


def detection(*items: ReviewRecord, scope: DetectionScope) -> Detection:
    return Detection(
        rule_key="NGF-UNIT-MISSING",
        rule_version=1,
        scope=scope,
        review_key="k",
        base_key="k",
        base_key_count=1,
        sheet_month=1,
        record_ids=tuple(item.id for item in items),
    )


def test_fingerprint_ignores_position_but_not_content() -> None:
    first, moved, changed = record(2), record(9), record(2, amount="11")
    fingerprint = evidence_fingerprint(
        detection(first, scope=DetectionScope.RECORD), {first.id: first}
    )
    assert fingerprint == evidence_fingerprint(
        detection(moved, scope=DetectionScope.RECORD), {moved.id: moved}
    )
    assert fingerprint != evidence_fingerprint(
        detection(changed, scope=DetectionScope.RECORD), {changed.id: changed}
    )


def test_location_only_findings_have_no_fingerprint() -> None:
    assert evidence_fingerprint(detection(scope=DetectionScope.DIAGNOSTIC), {}) is None


@pytest.mark.parametrize(
    ("status", "same_version", "prior", "current", "expected"),
    [
        (None, False, None, "a", CarryOutcome.NEW),
        (OccurrenceStatus.NEW, True, "a", "a", CarryOutcome.STILL_OPEN),
        (OccurrenceStatus.CONFIRMED, True, "a", "b", CarryOutcome.STILL_OPEN),
        (OccurrenceStatus.RISK_ACCEPTED, True, "a", "a", CarryOutcome.CARRIED_OVER),
        (OccurrenceStatus.DISMISSED, True, None, "a", CarryOutcome.CARRIED_OVER),
        (OccurrenceStatus.RISK_ACCEPTED, True, "a", "b", CarryOutcome.EVIDENCE_CHANGED),
        (OccurrenceStatus.RISK_ACCEPTED, False, "a", "a", CarryOutcome.REOPENED),
        (OccurrenceStatus.RESOLVED, True, "a", "a", CarryOutcome.REOPENED),
    ],
)
def test_classify(
    status: OccurrenceStatus | None,
    same_version: bool,
    prior: str | None,
    current: str | None,
    expected: CarryOutcome,
) -> None:
    assert (
        classify(
            prior_status=status,
            same_rule_version=same_version,
            prior_fingerprint=prior,
            fingerprint=current,
        )
        is expected
    )
