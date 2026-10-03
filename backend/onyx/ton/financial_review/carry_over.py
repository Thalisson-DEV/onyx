"""Carrying human review decisions over a new import. Pure functions.

A finding's identity says *which* case it is; its evidence fingerprint says
*what the source showed* when it was detected. A human decision is kept for a
new import only when both are the same: same case, same evidence. When the
evidence changed, the case goes back to a human.

TON never copies a decision onto a different case. Accepting a risk or
dismissing a finding is a human-only transition (readiness §9), so a decision
can only stay where it was taken.
"""

import hashlib
import json
from collections.abc import Mapping
from enum import Enum
from uuid import UUID

from onyx.db.ton.enums import OccurrenceStatus
from onyx.ton.financial_review.models import Detection, DetectionScope, ReviewRecord
from onyx.ton.financial_review.rules import record_base_key

EVIDENCE_SCHEME = "ngf-ev-1"

# Human closures a repeated detection keeps when the evidence is unchanged.
CARRIED_STATUSES = frozenset(
    {OccurrenceStatus.RISK_ACCEPTED, OccurrenceStatus.DISMISSED}
)
OPEN_STATUSES = frozenset(
    {OccurrenceStatus.NEW, OccurrenceStatus.REOPENED, OccurrenceStatus.CONFIRMED}
)


class CarryOutcome(str, Enum):
    NEW = "NEW"
    CARRIED_OVER = "CARRIED_OVER"
    EVIDENCE_CHANGED = "EVIDENCE_CHANGED"
    STILL_OPEN = "STILL_OPEN"
    REOPENED = "REOPENED"


def evidence_fingerprint(
    detection: Detection, records: Mapping[UUID, ReviewRecord]
) -> str | None:
    """What the source showed for this finding, without where it showed it.

    Row and sheet positions are left out: a cleaned export shifts rows. Findings
    that only know a location (rejected rows, the execution itself) have no
    content to compare and return None, which keeps the decision as before.
    """
    if detection.scope in (DetectionScope.DIAGNOSTIC, DetectionScope.EXECUTION):
        return None
    payload: dict[str, object] = {
        "scheme": EVIDENCE_SCHEME,
        "candidates": sorted(detection.candidate_values),
    }
    # Label findings point at one representative row per month, which grows
    # every month; their evidence is the set of labels alone.
    if detection.scope in (DetectionScope.RECORD, DetectionScope.RECORD_GROUP):
        payload["records"] = sorted(
            record_base_key(records[record_id], frozenset())
            for record_id in detection.record_ids
            if record_id in records
        )
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return f"ev:{digest}"


def classify(
    *,
    prior_status: OccurrenceStatus | None,
    same_rule_version: bool,
    prior_fingerprint: str | None,
    fingerprint: str | None,
) -> CarryOutcome:
    """What a new detection does to the case that already carries its identity."""
    if prior_status is None:
        return CarryOutcome.NEW
    if prior_status in OPEN_STATUSES:
        return CarryOutcome.STILL_OPEN
    if prior_status in CARRIED_STATUSES and same_rule_version:
        # A finding recorded before fingerprints existed keeps its decision.
        if (
            prior_fingerprint is None
            or fingerprint is None
            or prior_fingerprint == fingerprint
        ):
            return CarryOutcome.CARRIED_OVER
        return CarryOutcome.EVIDENCE_CHANGED
    return CarryOutcome.REOPENED
