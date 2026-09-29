"""Reviewed-dataset policy: a derived, reproducible disposition per record.

Nothing is materialised. A disposition is a pure function of the findings of one
review run and the occurrence history up to an ``as_of`` instant, so the same
run and the same decision history always give the same dataset revision.

Policy ``ng-reviewed-dataset-policy-1``:

* only findings of BLOCKING rules change a disposition;
* an open blocking finding makes the record REVIEW_REQUIRED;
* a confirmed one (correction requested) makes it CORRECTION_REQUIRED;
* a resolved or verified one means the source was corrected, so this import is
  stale: SUPERSEDED_BY_CORRECTION;
* a justified one (risk accepted) is JUSTIFIED_EXCEPTION;
* a dismissed one (false positive) no longer counts;
* the worst state wins.

ACCEPTED and JUSTIFIED_EXCEPTION are downstream-safe. Rows rejected by the
parser never become records; they are EXCLUDED_SOURCE_ERROR and make their
month incomplete until justified, dismissed or corrected.
"""

import datetime
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from onyx.db.ton.canonical import compute_content_hash
from onyx.db.ton.enums import OccurrenceStatus, OccurrenceVerificationResult
from onyx.ton.financial_review.catalog import DATASET_POLICY_VERSION
from onyx.ton.financial_review.models import (
    DOWNSTREAM_SAFE_DISPOSITIONS,
    ReviewDisposition,
)

OPEN = frozenset(
    {OccurrenceStatus.NEW, OccurrenceStatus.REOPENED, OccurrenceStatus.CONFIRMED}
)

# Worst first.
PRECEDENCE: tuple[ReviewDisposition, ...] = (
    ReviewDisposition.REVIEW_REQUIRED,
    ReviewDisposition.CORRECTION_REQUIRED,
    ReviewDisposition.SUPERSEDED_BY_CORRECTION,
    ReviewDisposition.JUSTIFIED_EXCEPTION,
    ReviewDisposition.ACCEPTED,
)


@dataclass(frozen=True)
class FindingState:
    finding_id: UUID
    occurrence_id: UUID
    rule_key: str
    blocking: bool
    scope: str
    sheet_month: int | None
    record_ids: tuple[UUID, ...]
    status: OccurrenceStatus
    verification: OccurrenceVerificationResult | None


@dataclass(frozen=True)
class RecordDisposition:
    disposition: ReviewDisposition
    rule_keys: tuple[str, ...]
    open_blocking: int
    open_non_blocking: int

    @property
    def downstream_safe(self) -> bool:
        return self.disposition in DOWNSTREAM_SAFE_DISPOSITIONS


ACCEPTED_CLEAN = RecordDisposition(ReviewDisposition.ACCEPTED, (), 0, 0)


def finding_disposition(state: FindingState) -> ReviewDisposition:
    """What one finding does to the rows it concerns."""
    if not state.blocking or state.status is OccurrenceStatus.DISMISSED:
        return ReviewDisposition.ACCEPTED
    if state.status is OccurrenceStatus.RISK_ACCEPTED:
        return ReviewDisposition.JUSTIFIED_EXCEPTION
    if (
        state.status is OccurrenceStatus.RESOLVED
        or state.verification is OccurrenceVerificationResult.PASSED
    ):
        return ReviewDisposition.SUPERSEDED_BY_CORRECTION
    if state.status is OccurrenceStatus.CONFIRMED:
        return ReviewDisposition.CORRECTION_REQUIRED
    # NEW, REOPENED and SUPERSEDED: the issue is still unresolved here.
    return ReviewDisposition.REVIEW_REQUIRED


def combine(states: Iterable[FindingState]) -> RecordDisposition:
    items = list(states)
    if not items:
        return ACCEPTED_CLEAN
    dispositions = {finding_disposition(item) for item in items}
    worst = next(item for item in PRECEDENCE if item in dispositions)
    return RecordDisposition(
        disposition=worst,
        rule_keys=tuple(sorted({item.rule_key for item in items})),
        open_blocking=sum(item.blocking and item.status in OPEN for item in items),
        open_non_blocking=sum(
            (not item.blocking) and item.status in OPEN for item in items
        ),
    )


def record_dispositions(
    states: Iterable[FindingState],
) -> dict[UUID, RecordDisposition]:
    """Dispositions for records that carry at least one finding."""
    by_record: dict[UUID, list[FindingState]] = {}
    for state in states:
        for record_id in state.record_ids:
            by_record.setdefault(record_id, []).append(state)
    return {record_id: combine(items) for record_id, items in by_record.items()}


@dataclass(frozen=True)
class ExcludedRow:
    sheet_month: int | None
    disposition: ReviewDisposition


def excluded_rows(states: Iterable[FindingState]) -> list[ExcludedRow]:
    """Rejected source rows, located or not, with their current disposition."""
    rows: list[ExcludedRow] = []
    for state in states:
        if state.record_ids or state.scope not in ("DIAGNOSTIC", "EXECUTION"):
            continue
        disposition = finding_disposition(state)
        rows.append(
            ExcludedRow(
                sheet_month=state.sheet_month,
                disposition=(
                    ReviewDisposition.EXCLUDED_SOURCE_ERROR
                    if disposition not in DOWNSTREAM_SAFE_DISPOSITIONS
                    else disposition
                ),
            )
        )
    return rows


def dataset_revision(
    *,
    review_run_id: UUID,
    event_watermark: Mapping[UUID, int],
) -> str:
    """Identity of a dataset state: the run plus the decision history it saw."""
    payload = {
        "policy": DATASET_POLICY_VERSION,
        "review_run_id": review_run_id,
        "occurrences": [
            {"occurrence_id": occurrence_id, "last_sequence_no": sequence}
            for occurrence_id, sequence in sorted(
                event_watermark.items(), key=lambda item: str(item[0])
            )
        ],
    }
    return f"{DATASET_POLICY_VERSION}:{compute_content_hash(payload)}"


@dataclass(frozen=True)
class EventFact:
    occurrence_id: UUID
    sequence_no: int
    transition: str
    resulting_status: OccurrenceStatus
    occurred_at: datetime.datetime
    verification_result: str | None


def state_as_of(
    events: Sequence[EventFact], as_of: datetime.datetime
) -> tuple[OccurrenceStatus | None, OccurrenceVerificationResult | None, int]:
    """Status, verification and last sequence number seen at *as_of*."""
    status: OccurrenceStatus | None = None
    verification: OccurrenceVerificationResult | None = None
    last = 0
    for event in sorted(events, key=lambda item: item.sequence_no):
        if event.occurred_at > as_of:
            break
        status = event.resulting_status
        last = event.sequence_no
        if event.verification_result is not None:
            verification = OccurrenceVerificationResult(event.verification_result)
        if event.transition == "REOPENED":
            verification = None
    return status, verification, last
