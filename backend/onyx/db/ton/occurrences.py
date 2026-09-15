"""Occurrence deduplication, recurrence and lifecycle projection (Plan 003c).

The persistent business case. Three things are settled here and must stay
settled:

**1. Deduplication is a database property.** ``UNIQUE(identity_key)`` is the
boundary, and :func:`_insert_occurrence_if_absent` uses
``INSERT … ON CONFLICT DO NOTHING`` followed by a re-read. Two concurrent
detector workers converge on one row: the loser's insert blocks until the winner
commits, returns no row, and the following ``SELECT`` — a fresh snapshot under
READ COMMITTED — sees the committed winner. An application-level "check then
insert" cannot give that guarantee (readiness §7).

**2. History is authoritative; status is a projection.**
:func:`apply_transition__no_commit` is the only writer of ``status``,
``open_cycle_count``, ``detection_count`` and ``resolved_at``. It appends the
:class:`OccurrenceEvent` and updates the projection in the same call, so the two
cannot drift. :func:`project_from_events` recomputes the projection from history
alone, and :func:`projection_matches_history` compares them — the test that keeps
the convenience columns honest.

**3. The human-decision boundary is structural.** §12.1's reserved decisions are
refused for a ``SYSTEM`` actor here *and* by a CHECK constraint on the event
table, so a future writer that bypasses this module still cannot record an
unauthorized closure. A critical occurrence can only be closed through
``RESOLVE_CRITICAL``, which requires an identified user and an authorization
reference.

There is no write path to any source system in this module. No transition
contests a glosa, alters a measurement, changes billing or contacts a
contracting authority: the advisory boundary of §12.1 is enforced by absence.
"""

import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    FindingKind,
    InterpretationStatus,
    OccurrenceActorKind,
    OccurrenceCriticality,
    OccurrenceLedgerKind,
    OccurrenceStatus,
    OccurrenceTransition,
    OccurrenceVerificationResult,
    PostResolutionPolicy,
    RuleDomain,
)
from onyx.db.ton.findings import create_finding__no_commit
from onyx.db.ton.identity import compute_identity_key
from onyx.db.ton.models import Finding, Occurrence, OccurrenceEvent, Rule, RuleVersion

# Statuses in which a case is still an open, unresolved issue. A detection
# arriving while the case is in one of these is a repeat, not a recurrence.
OPEN_STATUSES: frozenset[OccurrenceStatus] = frozenset(
    {
        OccurrenceStatus.NEW,
        OccurrenceStatus.REOPENED,
        OccurrenceStatus.CONFIRMED,
    }
)

# Statuses that end the case. A detection arriving in one of these is a
# recurrence and is resolved by `RuleVersion.post_resolution_policy`.
CLOSED_STATUSES: frozenset[OccurrenceStatus] = frozenset(
    {
        OccurrenceStatus.RESOLVED,
        OccurrenceStatus.RISK_ACCEPTED,
        OccurrenceStatus.DISMISSED,
        OccurrenceStatus.SUPERSEDED,
    }
)

# The status each transition leaves behind. A transition absent from this map
# records something real without moving the case — an escalation changes
# criticality, a verification records an outcome, a repeat bumps the counters.
TRANSITION_RESULTING_STATUS: dict[OccurrenceTransition, OccurrenceStatus] = {
    OccurrenceTransition.DETECT: OccurrenceStatus.NEW,
    OccurrenceTransition.REOPENED: OccurrenceStatus.REOPENED,
    OccurrenceTransition.SUPERSEDE: OccurrenceStatus.SUPERSEDED,
    OccurrenceTransition.RESOLVED: OccurrenceStatus.RESOLVED,
    OccurrenceTransition.RESOLVE_CRITICAL: OccurrenceStatus.RESOLVED,
    OccurrenceTransition.ACCEPT_RISK: OccurrenceStatus.RISK_ACCEPTED,
    OccurrenceTransition.DISMISS: OccurrenceStatus.DISMISSED,
    OccurrenceTransition.ASSERT_NONCOMPLIANCE: OccurrenceStatus.CONFIRMED,
}

# Prompt Mestre §12.1: what TON may do alone — read, test, calculate, classify,
# draft, alert, write to the ledger. §10 additionally says the criticality scale
# is applied "sem consultar ninguém", which is why escalation is here.
SYSTEM_ALLOWED_TRANSITIONS: frozenset[OccurrenceTransition] = frozenset(
    {
        OccurrenceTransition.DETECT,
        OccurrenceTransition.REPEAT_DETECTED,
        OccurrenceTransition.REOPENED,
        OccurrenceTransition.ESCALATE_BY_CYCLE_RULE,
        OccurrenceTransition.VERIFICATION_PASSED,
        OccurrenceTransition.VERIFICATION_FAILED,
        OccurrenceTransition.SUPERSEDE,
    }
)

# Readiness §9, verbatim. Mirrored by
# `ck_ton_occurrence_event_human_only_transitions`, so the rule holds even for a
# writer that never calls this module.
HUMAN_ONLY_TRANSITIONS: frozenset[OccurrenceTransition] = frozenset(
    {
        OccurrenceTransition.RESOLVE_CRITICAL,
        OccurrenceTransition.ACCEPT_RISK,
        OccurrenceTransition.DISMISS,
        OccurrenceTransition.ASSERT_NONCOMPLIANCE,
        OccurrenceTransition.PROMOTE_INTERPRETATION,
        OccurrenceTransition.OVERRIDE_DETERMINISTIC_VALUE,
    }
)

# Requires an identified account but no separate authorization record. Closing a
# case is absent from §12.1's autonomous list, so TON cannot do it alone.
USER_REQUIRED_TRANSITIONS: frozenset[OccurrenceTransition] = frozenset(
    {OccurrenceTransition.RESOLVED}
)

# A detection happened, so a finding exists and `detection_count` moves. REOPENED
# belongs here as well as in the open-cycle set: a recurrence after resolution is
# a real detection with its own finding, not only a state change.
_DETECTION_TRANSITIONS: frozenset[OccurrenceTransition] = frozenset(
    {
        OccurrenceTransition.DETECT,
        OccurrenceTransition.REPEAT_DETECTED,
        OccurrenceTransition.REOPENED,
    }
)

# A new open cycle began. Drives §10's "🟠 open two cycles → 🔴 on the third".
_OPEN_CYCLE_TRANSITIONS: frozenset[OccurrenceTransition] = frozenset(
    {OccurrenceTransition.DETECT, OccurrenceTransition.REOPENED}
)

_RESOLVING_TRANSITIONS: frozenset[OccurrenceTransition] = frozenset(
    {OccurrenceTransition.RESOLVED, OccurrenceTransition.RESOLVE_CRITICAL}
)


class DetectionOutcome(str, PyEnum):
    """What :func:`record_detection__no_commit` did.

    Named outcomes rather than a boolean: readiness §7 defines four distinct
    results, and a caller that can only distinguish "created" from "not created"
    cannot tell a repeat from a recurrence.
    """

    NEW = "NEW"
    REPEATED = "REPEATED"
    REOPENED = "REOPENED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class DetectionResult:
    """The occurrence a detection landed on, its finding, and what happened."""

    occurrence: Occurrence
    finding: Finding
    outcome: DetectionOutcome
    # Set only for SUPERSEDED: the case that was closed and replaced.
    superseded_occurrence: Occurrence | None = None


@dataclass(frozen=True)
class OccurrenceProjection:
    """The values :class:`Occurrence` caches from its event history."""

    status: OccurrenceStatus
    detection_count: int
    open_cycle_count: int
    resolved_at: datetime.datetime | None


def project_from_events(
    events: Sequence[OccurrenceEvent],
) -> OccurrenceProjection | None:
    """Recompute the projection from history alone.

    Returns ``None`` for an empty history — a case with no events has no
    projectable state, and inventing ``NEW`` here would hide the anomaly.

    This is the definition the stored columns must match. Nothing in it reads the
    occurrence row, so it cannot be fooled by a drifted projection.
    """
    ordered = sorted(events, key=lambda event: event.sequence_no)
    if not ordered:
        return None

    status = OccurrenceStatus.NEW
    detection_count = 0
    open_cycle_count = 0
    resolved_at: datetime.datetime | None = None

    for event in ordered:
        transition = event.transition
        if transition in _DETECTION_TRANSITIONS:
            detection_count += 1
        if transition in _OPEN_CYCLE_TRANSITIONS:
            open_cycle_count += 1
        if transition in _RESOLVING_TRANSITIONS:
            resolved_at = event.occurred_at
        elif transition is OccurrenceTransition.REOPENED:
            resolved_at = None
        status = TRANSITION_RESULTING_STATUS.get(transition, status)

    return OccurrenceProjection(
        status=status,
        detection_count=detection_count,
        open_cycle_count=open_cycle_count,
        resolved_at=resolved_at,
    )


def projection_matches_history(
    occurrence: Occurrence, events: Sequence[OccurrenceEvent]
) -> bool:
    """Whether the cached columns equal the event-derived values."""
    derived = project_from_events(events)
    if derived is None:
        return False
    return (
        occurrence.status is derived.status
        and occurrence.detection_count == derived.detection_count
        and occurrence.open_cycle_count == derived.open_cycle_count
        and occurrence.resolved_at == derived.resolved_at
    )


def fetch_occurrence_events(
    db_session: Session, occurrence_id: UUID
) -> list[OccurrenceEvent]:
    """The full history of one case, in replay order."""
    return list(
        db_session.scalars(
            select(OccurrenceEvent)
            .where(OccurrenceEvent.occurrence_id == occurrence_id)
            .order_by(OccurrenceEvent.sequence_no)
        ).all()
    )


def apply_transition__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    transition: OccurrenceTransition,
    actor_kind: OccurrenceActorKind,
    actor_user_id: UUID | None = None,
    authorization_reference: str | None = None,
    reason: str | None = None,
    context: Mapping[str, Any] | None = None,
    finding_id: UUID | None = None,
    rule_version_id: UUID | None = None,
    occurred_at: datetime.datetime | None = None,
) -> OccurrenceEvent:
    """Append one event and update the projection. The only path to either.

    Refuses, before writing anything:

    * a ``SYSTEM`` actor on a transition §12.1 reserves for a human;
    * a human-only transition without an identified user and an authorization
      reference — the same rule the database CHECK enforces, raised here as a
      domain error so the caller learns what is missing;
    * ``RESOLVED`` on a case flagged ``requires_human_closure``, which must go
      through ``RESOLVE_CRITICAL`` instead. TON may propose closing a critical
      occurrence; it may not close one.

    The event and the projection update land in one flush. A failure to persist
    the history therefore fails the business operation — domain history is
    transactional, not best-effort.
    """
    now = occurred_at or datetime.datetime.now(datetime.UTC)

    if actor_kind is OccurrenceActorKind.SYSTEM:
        if transition not in SYSTEM_ALLOWED_TRANSITIONS:
            raise ValueError(
                f"{transition.value} is not a transition TON may perform alone. "
                "Prompt Mestre §12.1 reserves it for a human decision."
            )
    elif actor_user_id is None:
        raise ValueError("A USER transition must name the account that performed it.")

    if transition in HUMAN_ONLY_TRANSITIONS:
        if actor_kind is not OccurrenceActorKind.USER or actor_user_id is None:
            raise ValueError(
                f"{transition.value} requires an identified user (readiness §9)."
            )
        if not authorization_reference:
            raise ValueError(
                f"{transition.value} requires an authorization_reference: the "
                "record of authority for the decision, not just its author."
            )

    if transition in USER_REQUIRED_TRANSITIONS and (
        actor_kind is not OccurrenceActorKind.USER or actor_user_id is None
    ):
        raise ValueError(
            f"{transition.value} requires an identified user. Closing a case is "
            "not in Prompt Mestre §12.1's autonomous list."
        )

    if (
        transition is OccurrenceTransition.RESOLVED
        and occurrence.requires_human_closure
    ):
        raise ValueError(
            "This occurrence requires human closure, so it must be resolved "
            "through RESOLVE_CRITICAL with a recorded authorization."
        )

    if transition in _DETECTION_TRANSITIONS:
        occurrence.detection_count += 1
        occurrence.last_detected_at = now
    if transition in _OPEN_CYCLE_TRANSITIONS:
        occurrence.open_cycle_count += 1
    if transition in _RESOLVING_TRANSITIONS:
        occurrence.resolved_at = now
    elif transition is OccurrenceTransition.REOPENED:
        occurrence.resolved_at = None

    occurrence.status = TRANSITION_RESULTING_STATUS.get(transition, occurrence.status)

    event = OccurrenceEvent(
        occurrence_id=occurrence.id,
        sequence_no=_next_sequence_no(db_session, occurrence.id),
        transition=transition,
        resulting_status=occurrence.status,
        actor_kind=actor_kind,
        actor_user_id=actor_user_id,
        authorization_reference=authorization_reference,
        reason=reason,
        context=dict(context) if context is not None else {},
        finding_id=finding_id,
        rule_version_id=rule_version_id,
        occurred_at=now,
    )
    db_session.add(event)
    db_session.flush()
    return event


def record_detection__no_commit(
    db_session: Session,
    *,
    analysis_run_id: UUID,
    rule: Rule,
    rule_version: RuleVersion,
    identity_values: Mapping[str, object | None],
    finding_kind: FindingKind,
    title: str,
    owning_domain: RuleDomain,
    ledger_kind: OccurrenceLedgerKind,
    criticality: OccurrenceCriticality,
    detected_at: datetime.datetime | None = None,
    business_unit_id: UUID | None = None,
    contract_id: UUID | None = None,
    verification_criterion: str | None = None,
    legal_review_required: bool = False,
    interpretation_status: InterpretationStatus = InterpretationStatus.NOT_REQUIRED,
    **finding_fields: Any,
) -> DetectionResult:
    """Resolve one detection to exactly one occurrence, and record the finding.

    The four readiness §7 outcomes, all deterministic:

    ``NEW``
        No case carries this identity. Create the occurrence and the finding, and
        append ``DETECT``.
    ``REPEATED``
        The case is open. Create a *new* finding against the *same* occurrence,
        bump the counters and append ``REPEAT_DETECTED``. Never a second
        occurrence.
    ``REOPENED``
        The case was closed and its ``post_resolution_policy`` is
        ``REOPEN_SAME_OCCURRENCE``. Append ``REOPENED``, increment
        ``open_cycle_count``, keep the history.
    ``SUPERSEDED``
        The case was closed and either the policy is
        ``SUPERSEDE_WITH_NEW_OCCURRENCE`` **or** the detecting rule version
        differs from the one attributed to the resolved case. The second
        condition wins over the policy: two detections measured against different
        thresholds are not the same measurement, so the old case is closed with
        ``SUPERSEDE`` and a new generation is opened.

    The absence of a detection produces nothing at all. No finding is created to
    represent a case not recurring; that is what a verification event is for.
    """
    now = detected_at or datetime.datetime.now(datetime.UTC)
    components = rule_version.identity_components
    logical_identity_key = compute_identity_key(
        rule_code=rule.code, components=components, values=identity_values
    )

    current = _latest_generation(db_session, logical_identity_key)

    if current is None:
        occurrence = _insert_occurrence_if_absent(
            db_session,
            identity_key=logical_identity_key,
            logical_identity_key=logical_identity_key,
            supersede_generation=1,
            rule_id=rule.id,
            current_rule_version_id=rule_version.id,
            owning_domain=owning_domain,
            ledger_kind=ledger_kind,
            criticality=criticality,
            nc_code=rule_version.nc_code,
            business_unit_id=business_unit_id,
            contract_id=contract_id,
            title=title,
            detected_at=now,
            verification_criterion=verification_criterion,
            legal_review_required=legal_review_required,
        )
        if _has_events(db_session, occurrence.id):
            # A concurrent worker won the insert and already appended DETECT.
            # This detection is therefore a repeat of a case created moments ago.
            return _repeat(
                db_session,
                occurrence=occurrence,
                analysis_run_id=analysis_run_id,
                rule_version=rule_version,
                finding_kind=finding_kind,
                owning_domain=owning_domain,
                business_unit_id=business_unit_id,
                contract_id=contract_id,
                detected_at=now,
                interpretation_status=interpretation_status,
                finding_fields=finding_fields,
            )
        return _first_detection(
            db_session,
            occurrence=occurrence,
            analysis_run_id=analysis_run_id,
            rule_version=rule_version,
            finding_kind=finding_kind,
            owning_domain=owning_domain,
            business_unit_id=business_unit_id,
            contract_id=contract_id,
            detected_at=now,
            interpretation_status=interpretation_status,
            finding_fields=finding_fields,
        )

    if current.status in OPEN_STATUSES:
        return _repeat(
            db_session,
            occurrence=current,
            analysis_run_id=analysis_run_id,
            rule_version=rule_version,
            finding_kind=finding_kind,
            owning_domain=owning_domain,
            business_unit_id=business_unit_id,
            contract_id=contract_id,
            detected_at=now,
            interpretation_status=interpretation_status,
            finding_fields=finding_fields,
        )

    policy = resolve_post_resolution_policy(
        occurrence=current, detecting_rule_version=rule_version
    )
    if policy is PostResolutionPolicy.REOPEN_SAME_OCCURRENCE:
        return _reopen(
            db_session,
            occurrence=current,
            analysis_run_id=analysis_run_id,
            rule_version=rule_version,
            finding_kind=finding_kind,
            owning_domain=owning_domain,
            business_unit_id=business_unit_id,
            contract_id=contract_id,
            detected_at=now,
            interpretation_status=interpretation_status,
            finding_fields=finding_fields,
        )

    return _supersede(
        db_session,
        previous=current,
        analysis_run_id=analysis_run_id,
        rule=rule,
        rule_version=rule_version,
        identity_values=identity_values,
        logical_identity_key=logical_identity_key,
        finding_kind=finding_kind,
        title=title,
        owning_domain=owning_domain,
        ledger_kind=ledger_kind,
        criticality=criticality,
        business_unit_id=business_unit_id,
        contract_id=contract_id,
        verification_criterion=verification_criterion,
        legal_review_required=legal_review_required,
        detected_at=now,
        interpretation_status=interpretation_status,
        finding_fields=finding_fields,
    )


def resolve_post_resolution_policy(
    *, occurrence: Occurrence, detecting_rule_version: RuleVersion
) -> PostResolutionPolicy:
    """Which recurrence policy applies, including the forced case.

    ``RuleVersion.post_resolution_policy`` is mandatory and has no global
    default: readiness §7 requires the rule to state it rather than let an
    executor choose silently.

    One condition overrides it. If the version detecting the recurrence differs
    from the version attributed to the resolved case, the outcome is always
    ``SUPERSEDE_WITH_NEW_OCCURRENCE``. A changed threshold is a changed
    measurement, and silently reopening the old case would compare two different
    yardsticks — the same comparability principle as rule S9.
    """
    if detecting_rule_version.id != occurrence.current_rule_version_id:
        return PostResolutionPolicy.SUPERSEDE_WITH_NEW_OCCURRENCE
    return detecting_rule_version.post_resolution_policy


def resolve_occurrence__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    actor_user_id: UUID,
    reason: str,
    authorization_reference: str | None = None,
    resolved_at: datetime.datetime | None = None,
) -> OccurrenceEvent:
    """Close a case as a human act.

    Picks ``RESOLVE_CRITICAL`` when the case requires human closure, which the
    event table then forces to carry an authorization reference. A critical
    occurrence has no other route to a closed status.
    """
    if occurrence.requires_human_closure:
        return apply_transition__no_commit(
            db_session,
            occurrence=occurrence,
            transition=OccurrenceTransition.RESOLVE_CRITICAL,
            actor_kind=OccurrenceActorKind.USER,
            actor_user_id=actor_user_id,
            authorization_reference=authorization_reference,
            reason=reason,
            occurred_at=resolved_at,
        )
    return apply_transition__no_commit(
        db_session,
        occurrence=occurrence,
        transition=OccurrenceTransition.RESOLVED,
        actor_kind=OccurrenceActorKind.USER,
        actor_user_id=actor_user_id,
        authorization_reference=authorization_reference,
        reason=reason,
        occurred_at=resolved_at,
    )


def record_verification__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    result: OccurrenceVerificationResult,
    checked_at: datetime.datetime | None = None,
    reason: str | None = None,
    actor_user_id: UUID | None = None,
) -> OccurrenceEvent:
    """Record the §5 Passo 7 verification outcome.

    A system act: §12.1 lets TON test and calculate. It records the outcome and
    changes no status — a failed verification does not reopen a case on its own,
    because a new detection is what reopens it.
    """
    now = checked_at or datetime.datetime.now(datetime.UTC)
    occurrence.verification_result = result
    occurrence.verification_checked_at = now

    transition = (
        OccurrenceTransition.VERIFICATION_PASSED
        if result is OccurrenceVerificationResult.PASSED
        else OccurrenceTransition.VERIFICATION_FAILED
    )
    return apply_transition__no_commit(
        db_session,
        occurrence=occurrence,
        transition=transition,
        actor_kind=(
            OccurrenceActorKind.USER
            if actor_user_id is not None
            else OccurrenceActorKind.SYSTEM
        ),
        actor_user_id=actor_user_id,
        reason=reason,
        context={"verification_result": result.value},
        occurred_at=now,
    )


def escalate_by_cycle_rule__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    criticality: OccurrenceCriticality,
    reason: str | None = None,
    occurred_at: datetime.datetime | None = None,
) -> OccurrenceEvent:
    """Reclassify a case under the §10 escalation rule.

    A system act — §10 says the scale is applied "sem consultar ninguém". The
    *when* is not decided here: how many open cycles trigger an escalation is
    ``RuleVersion.severity_mapping`` data awaiting owner approval, so this
    function applies a criticality the caller determined and records why.

    Raising criticality to ``CRITICAL`` also sets ``requires_human_closure``,
    which the database CHECK requires and which removes TON's ability to close
    the case it just escalated.
    """
    occurrence.criticality = criticality
    if criticality is OccurrenceCriticality.CRITICAL:
        occurrence.requires_human_closure = True

    return apply_transition__no_commit(
        db_session,
        occurrence=occurrence,
        transition=OccurrenceTransition.ESCALATE_BY_CYCLE_RULE,
        actor_kind=OccurrenceActorKind.SYSTEM,
        reason=reason,
        context={
            "criticality": criticality.value,
            "open_cycle_count": occurrence.open_cycle_count,
        },
        occurred_at=occurred_at,
    )


def promote_interpretation__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    actor_user_id: UUID,
    authorization_reference: str,
    criticality: OccurrenceCriticality | None = None,
    nc_code: str | None = None,
    reason: str | None = None,
) -> OccurrenceEvent:
    """Adopt an interpretation's proposal onto the case.

    The audited act that a proposal alone is not. ``proposed_criticality`` and
    ``proposed_nc_code`` sit inertly on :class:`FindingInterpretation` until a
    person promotes them here, with an authorization reference the event table
    requires.

    Note what cannot be promoted: no deterministic value, no source identifier,
    no ``identity_key``, no ``rule_version_id`` and no impact amount. There is no
    parameter for any of them.
    """
    if criticality is not None:
        occurrence.criticality = criticality
        if criticality is OccurrenceCriticality.CRITICAL:
            occurrence.requires_human_closure = True
    if nc_code is not None:
        occurrence.nc_code = nc_code

    return apply_transition__no_commit(
        db_session,
        occurrence=occurrence,
        transition=OccurrenceTransition.PROMOTE_INTERPRETATION,
        actor_kind=OccurrenceActorKind.USER,
        actor_user_id=actor_user_id,
        authorization_reference=authorization_reference,
        reason=reason,
        context={
            "promoted_criticality": criticality.value if criticality else None,
            "promoted_nc_code": nc_code,
        },
    )


def get_occurrence_by_identity_key(
    db_session: Session, identity_key: str
) -> Occurrence | None:
    """The case carrying exactly this identity key, if any."""
    return db_session.scalars(
        select(Occurrence).where(Occurrence.identity_key == identity_key)
    ).one_or_none()


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _first_detection(
    db_session: Session,
    *,
    occurrence: Occurrence,
    analysis_run_id: UUID,
    rule_version: RuleVersion,
    finding_kind: FindingKind,
    owning_domain: RuleDomain,
    business_unit_id: UUID | None,
    contract_id: UUID | None,
    detected_at: datetime.datetime,
    interpretation_status: InterpretationStatus,
    finding_fields: Mapping[str, Any],
) -> DetectionResult:
    finding = create_finding__no_commit(
        db_session,
        analysis_run_id=analysis_run_id,
        rule_version=rule_version,
        occurrence=occurrence,
        identity_key=occurrence.identity_key,
        finding_kind=finding_kind,
        domain=owning_domain,
        detected_at=detected_at,
        interpretation_status=interpretation_status,
        business_unit_id=business_unit_id,
        contract_id=contract_id,
        nc_code=rule_version.nc_code,
        **finding_fields,
    )
    # DETECT sets detection_count and open_cycle_count to 1. The row was inserted
    # with the server defaults of 1, so reset before the transition counts.
    occurrence.detection_count = 0
    occurrence.open_cycle_count = 0
    apply_transition__no_commit(
        db_session,
        occurrence=occurrence,
        transition=OccurrenceTransition.DETECT,
        actor_kind=OccurrenceActorKind.SYSTEM,
        finding_id=finding.id,
        rule_version_id=rule_version.id,
        occurred_at=detected_at,
    )
    return DetectionResult(
        occurrence=occurrence, finding=finding, outcome=DetectionOutcome.NEW
    )


def _repeat(
    db_session: Session,
    *,
    occurrence: Occurrence,
    analysis_run_id: UUID,
    rule_version: RuleVersion,
    finding_kind: FindingKind,
    owning_domain: RuleDomain,
    business_unit_id: UUID | None,
    contract_id: UUID | None,
    detected_at: datetime.datetime,
    interpretation_status: InterpretationStatus,
    finding_fields: Mapping[str, Any],
) -> DetectionResult:
    finding = create_finding__no_commit(
        db_session,
        analysis_run_id=analysis_run_id,
        rule_version=rule_version,
        occurrence=occurrence,
        identity_key=occurrence.identity_key,
        finding_kind=finding_kind,
        domain=owning_domain,
        detected_at=detected_at,
        interpretation_status=interpretation_status,
        business_unit_id=business_unit_id,
        contract_id=contract_id,
        nc_code=rule_version.nc_code,
        **finding_fields,
    )
    apply_transition__no_commit(
        db_session,
        occurrence=occurrence,
        transition=OccurrenceTransition.REPEAT_DETECTED,
        actor_kind=OccurrenceActorKind.SYSTEM,
        finding_id=finding.id,
        rule_version_id=rule_version.id,
        occurred_at=detected_at,
    )
    return DetectionResult(
        occurrence=occurrence, finding=finding, outcome=DetectionOutcome.REPEATED
    )


def _reopen(
    db_session: Session,
    *,
    occurrence: Occurrence,
    analysis_run_id: UUID,
    rule_version: RuleVersion,
    finding_kind: FindingKind,
    owning_domain: RuleDomain,
    business_unit_id: UUID | None,
    contract_id: UUID | None,
    detected_at: datetime.datetime,
    interpretation_status: InterpretationStatus,
    finding_fields: Mapping[str, Any],
) -> DetectionResult:
    finding = create_finding__no_commit(
        db_session,
        analysis_run_id=analysis_run_id,
        rule_version=rule_version,
        occurrence=occurrence,
        identity_key=occurrence.identity_key,
        finding_kind=finding_kind,
        domain=owning_domain,
        detected_at=detected_at,
        interpretation_status=interpretation_status,
        business_unit_id=business_unit_id,
        contract_id=contract_id,
        nc_code=rule_version.nc_code,
        **finding_fields,
    )
    apply_transition__no_commit(
        db_session,
        occurrence=occurrence,
        transition=OccurrenceTransition.REOPENED,
        actor_kind=OccurrenceActorKind.SYSTEM,
        reason="Detected again after resolution under the same rule version.",
        finding_id=finding.id,
        rule_version_id=rule_version.id,
        occurred_at=detected_at,
    )
    return DetectionResult(
        occurrence=occurrence, finding=finding, outcome=DetectionOutcome.REOPENED
    )


def _supersede(
    db_session: Session,
    *,
    previous: Occurrence,
    analysis_run_id: UUID,
    rule: Rule,
    rule_version: RuleVersion,
    identity_values: Mapping[str, object | None],
    logical_identity_key: str,
    finding_kind: FindingKind,
    title: str,
    owning_domain: RuleDomain,
    ledger_kind: OccurrenceLedgerKind,
    criticality: OccurrenceCriticality,
    business_unit_id: UUID | None,
    contract_id: UUID | None,
    verification_criterion: str | None,
    legal_review_required: bool,
    detected_at: datetime.datetime,
    interpretation_status: InterpretationStatus,
    finding_fields: Mapping[str, Any],
) -> DetectionResult:
    generation = previous.supersede_generation + 1
    identity_key = compute_identity_key(
        rule_code=rule.code,
        components=rule_version.identity_components,
        values=identity_values,
        supersede_generation=generation,
    )
    successor = _insert_occurrence_if_absent(
        db_session,
        identity_key=identity_key,
        logical_identity_key=logical_identity_key,
        supersede_generation=generation,
        rule_id=rule.id,
        current_rule_version_id=rule_version.id,
        owning_domain=owning_domain,
        ledger_kind=ledger_kind,
        criticality=criticality,
        nc_code=rule_version.nc_code,
        business_unit_id=business_unit_id,
        contract_id=contract_id,
        title=title,
        detected_at=detected_at,
        verification_criterion=verification_criterion,
        legal_review_required=legal_review_required,
    )

    if _has_events(db_session, successor.id):
        # A concurrent worker already superseded and opened this generation.
        return _repeat(
            db_session,
            occurrence=successor,
            analysis_run_id=analysis_run_id,
            rule_version=rule_version,
            finding_kind=finding_kind,
            owning_domain=owning_domain,
            business_unit_id=business_unit_id,
            contract_id=contract_id,
            detected_at=detected_at,
            interpretation_status=interpretation_status,
            finding_fields=finding_fields,
        )

    if previous.status is not OccurrenceStatus.SUPERSEDED:
        previous.superseded_by_occurrence_id = successor.id
        apply_transition__no_commit(
            db_session,
            occurrence=previous,
            transition=OccurrenceTransition.SUPERSEDE,
            actor_kind=OccurrenceActorKind.SYSTEM,
            reason=(
                "Recurrence measured against a different rule version, or a "
                "post-resolution policy of SUPERSEDE_WITH_NEW_OCCURRENCE."
            ),
            rule_version_id=rule_version.id,
            context={"superseded_by_occurrence_id": str(successor.id)},
            occurred_at=detected_at,
        )

    result = _first_detection(
        db_session,
        occurrence=successor,
        analysis_run_id=analysis_run_id,
        rule_version=rule_version,
        finding_kind=finding_kind,
        owning_domain=owning_domain,
        business_unit_id=business_unit_id,
        contract_id=contract_id,
        detected_at=detected_at,
        interpretation_status=interpretation_status,
        finding_fields=finding_fields,
    )
    return DetectionResult(
        occurrence=successor,
        finding=result.finding,
        outcome=DetectionOutcome.SUPERSEDED,
        superseded_occurrence=previous,
    )


def _insert_occurrence_if_absent(
    db_session: Session,
    *,
    identity_key: str,
    logical_identity_key: str,
    supersede_generation: int,
    rule_id: UUID,
    current_rule_version_id: UUID,
    owning_domain: RuleDomain,
    ledger_kind: OccurrenceLedgerKind,
    criticality: OccurrenceCriticality,
    nc_code: str | None,
    business_unit_id: UUID | None,
    contract_id: UUID | None,
    title: str,
    detected_at: datetime.datetime,
    verification_criterion: str | None,
    legal_review_required: bool,
) -> Occurrence:
    """``INSERT … ON CONFLICT DO NOTHING`` then re-read. The dedup primitive.

    Concurrency-safe without a lock. When another transaction has inserted the
    same ``identity_key`` but not yet committed, this INSERT blocks on its row
    lock; once that transaction commits, ``DO NOTHING`` writes nothing and the
    ``SELECT`` below — a new snapshot under READ COMMITTED — reads the committed
    winner. Both workers therefore return the same occurrence.

    ``short_code`` is intentionally omitted so the sequence-backed server default
    allocates it. Two concurrent inserts consume two sequence values and the
    loser's is discarded; a gap in a display code is not a defect, whereas a
    duplicated one would be.
    """
    values: dict[str, Any] = {
        "id": uuid4(),
        "identity_key": identity_key,
        "logical_identity_key": logical_identity_key,
        "supersede_generation": supersede_generation,
        "rule_id": rule_id,
        "current_rule_version_id": current_rule_version_id,
        "owning_domain": owning_domain,
        "ledger_kind": ledger_kind,
        "criticality": criticality,
        "nc_code": nc_code,
        "business_unit_id": business_unit_id,
        "contract_id": contract_id,
        "title": title,
        "status": OccurrenceStatus.NEW,
        "first_detected_at": detected_at,
        "last_detected_at": detected_at,
        "detection_count": 1,
        "open_cycle_count": 1,
        "verification_criterion": verification_criterion,
        "legal_review_required": legal_review_required,
        # Readiness §9: a critical case requires human closure, and the CHECK
        # constraint refuses the row otherwise.
        "requires_human_closure": criticality is OccurrenceCriticality.CRITICAL,
    }

    db_session.execute(
        pg_insert(Occurrence)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["identity_key"])
    )
    # Not `.returning(...)` on the insert: on conflict it yields nothing, and the
    # re-read is required either way to pick up the winner's row.
    return db_session.scalars(
        select(Occurrence).where(Occurrence.identity_key == identity_key)
    ).one()


def _latest_generation(
    db_session: Session, logical_identity_key: str
) -> Occurrence | None:
    """The newest generation of a logical case, or ``None`` if it is unknown."""
    return db_session.scalars(
        select(Occurrence)
        .where(Occurrence.logical_identity_key == logical_identity_key)
        .order_by(Occurrence.supersede_generation.desc())
        .limit(1)
    ).one_or_none()


def _has_events(db_session: Session, occurrence_id: UUID) -> bool:
    return bool(
        db_session.scalar(
            select(func.count())
            .select_from(OccurrenceEvent)
            .where(OccurrenceEvent.occurrence_id == occurrence_id)
        )
    )


def _next_sequence_no(db_session: Session, occurrence_id: UUID) -> int:
    """Next free sequence number for a case's history.

    Racy on its own; ``uq_ton_occurrence_event_sequence`` is what guarantees a
    single ordering, so a concurrent second writer gets an ``IntegrityError``
    rather than a duplicated position in the history.
    """
    highest = db_session.scalar(
        select(func.max(OccurrenceEvent.sequence_no)).where(
            OccurrenceEvent.occurrence_id == occurrence_id
        )
    )
    return 1 if highest is None else int(highest) + 1
