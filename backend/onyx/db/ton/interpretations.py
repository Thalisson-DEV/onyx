"""AI-interpretation lifecycle primitives (Plan 003c).

**No provider is contacted here.** This module holds the transactional lifecycle
that a later agent caller (Plan 005) drives: it opens an attempt, marks it
running, and closes it as completed or failed. There is no LiteLLM import, no
HTTP call and no prompt text, which is what makes the ordering below testable
without a network.

The durability invariant, and the reason :func:`begin_interpretation` commits:

    ``Finding.interpretation_status = PENDING`` is committed **before** any
    provider request could begin.

A crash between the request and the response must leave a visible non-final
record rather than a silent gap. That is only true if PENDING is durable at the
moment the caller is handed control, so the commit is inside this function rather
than left to a caller who might forget it.

What is never stored: no chain-of-thought, no hidden reasoning, no raw prompt
body, no raw response transcript. Only the business-facing interpretation plus
the provenance needed to reproduce the call *shape*. There is no parameter here
that could carry a transcript, and an inverse test asserts no such column exists.

What an interpretation can never change: a deterministic value, a source
identifier, ``rule_version_id``, ``identity_key`` or an impact amount. This
module writes to :class:`FindingInterpretation` and to
``Finding.interpretation_status`` — nothing else. ``proposed_criticality`` and
``proposed_nc_code`` are proposals; promoting one is
:func:`onyx.db.ton.occurrences.promote_interpretation__no_commit`, an audited
transition requiring an authorization reference.
"""

import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.configs.app_configs import TON_TRACE_CONTENT_MODE
from onyx.db.ton.enums import (
    InterpretationFailureClass,
    InterpretationInputScope,
    InterpretationStatus,
    OccurrenceCriticality,
)
from onyx.db.ton.models import Finding, FindingInterpretation

# Scopes that put raw evidence in front of a provider. Refused when the
# deployment is configured for metadata-only content (Plan 002, D-015): a
# deployment that promised not to send content must not be able to persist an
# attempt that did.
_CONTENT_BEARING_SCOPES: frozenset[InterpretationInputScope] = frozenset(
    {InterpretationInputScope.FULL_EVIDENCE}
)

# Statuses from which a new attempt may be opened. A RUNNING attempt is excluded:
# opening a second one concurrently would make `attempt_no` meaningless and hide
# whichever attempt lost.
_ATTEMPTABLE_STATUSES: frozenset[InterpretationStatus] = frozenset(
    {
        InterpretationStatus.NOT_REQUIRED,
        InterpretationStatus.PENDING,
        InterpretationStatus.FAILED,
        InterpretationStatus.COMPLETED,
    }
)


def begin_interpretation(
    db_session: Session,
    *,
    finding: Finding,
    prompt_key: str,
    prompt_version: str,
    input_scope: InterpretationInputScope,
    llm_provider: str | None = None,
    model_name: str | None = None,
    evidence_reference_ids: Sequence[UUID] | None = None,
    started_at: datetime.datetime | None = None,
) -> FindingInterpretation:
    """Open an attempt and **commit** it before any provider work may start.

    Returns the PENDING attempt row. The caller may then contact a provider and
    must close the attempt with :func:`complete_interpretation` or
    :func:`fail_interpretation`.

    This function commits, unlike the ``__no_commit`` functions elsewhere in the
    TON package. The commit *is* the guarantee: without it, a crash during the
    provider call would roll back the record that the call was ever attempted.
    The name carries no ``__no_commit`` suffix precisely so the difference is
    visible at the call site.

    Refuses ``FULL_EVIDENCE`` when ``TON_TRACE_CONTENT_MODE`` is ``metadata``.
    """
    if input_scope in _CONTENT_BEARING_SCOPES and TON_TRACE_CONTENT_MODE == "metadata":
        raise ValueError(
            "This deployment is configured for metadata-only content "
            "(TON_TRACE_CONTENT_MODE=metadata), so an interpretation may not "
            "receive FULL_EVIDENCE. Use STRUCTURED_ONLY or MASKED_EXCERPT."
        )
    if finding.interpretation_status not in _ATTEMPTABLE_STATUSES:
        raise ValueError(
            "An interpretation attempt is already in flight for this finding "
            f"(status {finding.interpretation_status.value})."
        )

    attempt = FindingInterpretation(
        finding_id=finding.id,
        attempt_no=next_attempt_no(db_session, finding.id),
        status=InterpretationStatus.PENDING,
        llm_provider=llm_provider,
        model_name=model_name,
        prompt_key=prompt_key,
        prompt_version=prompt_version,
        evidence_reference_ids=[
            str(reference) for reference in (evidence_reference_ids or [])
        ],
        input_scope=input_scope,
        started_at=started_at or datetime.datetime.now(datetime.UTC),
    )
    finding.interpretation_status = InterpretationStatus.PENDING
    db_session.add(attempt)
    db_session.commit()
    return attempt


def mark_interpretation_running(
    db_session: Session, *, finding: Finding, attempt: FindingInterpretation
) -> FindingInterpretation:
    """Move a committed PENDING attempt to RUNNING, and commit that too.

    Optional in the lifecycle — a caller that hands off to a provider
    synchronously may go straight from PENDING to a terminal state. It exists so
    a long-running attempt is distinguishable from one that never started.
    """
    if attempt.status is not InterpretationStatus.PENDING:
        raise ValueError(
            f"Only a PENDING attempt may start running, not {attempt.status.value}."
        )
    attempt.status = InterpretationStatus.RUNNING
    finding.interpretation_status = InterpretationStatus.RUNNING
    db_session.commit()
    return attempt


def complete_interpretation(
    db_session: Session,
    *,
    finding: Finding,
    attempt: FindingInterpretation,
    summary: str,
    probable_cause: str | None = None,
    recommended_action: str | None = None,
    impact_narrative: str | None = None,
    proposed_criticality: OccurrenceCriticality | None = None,
    proposed_nc_code: str | None = None,
    llm_provider: str | None = None,
    model_name: str | None = None,
    finished_at: datetime.datetime | None = None,
) -> FindingInterpretation:
    """Close an attempt as COMPLETED with its business-facing output.

    ``summary`` is required and must be non-empty. An empty successful
    interpretation is how a provider failure gets laundered into an apparent
    success, so it is refused here and by
    ``ck_ton_finding_interpretation_completed_has_summary``.

    ``proposed_criticality`` and ``proposed_nc_code`` are recorded as proposals.
    They change nothing on the occurrence: promotion is a separate authorized
    transition.
    """
    if attempt.status not in (
        InterpretationStatus.PENDING,
        InterpretationStatus.RUNNING,
    ):
        raise ValueError(
            f"A {attempt.status.value} attempt is already terminal. A retry "
            "appends a new attempt rather than rewriting this one."
        )
    if not summary.strip():
        raise ValueError(
            "A COMPLETED interpretation needs a summary. A provider failure must "
            "stay FAILED rather than become an empty success."
        )

    if llm_provider is not None:
        attempt.llm_provider = llm_provider
    if model_name is not None:
        attempt.model_name = model_name
    if attempt.llm_provider is None or attempt.model_name is None:
        raise ValueError(
            "A COMPLETED interpretation must record which provider and model "
            "produced it."
        )

    attempt.status = InterpretationStatus.COMPLETED
    attempt.summary = summary
    attempt.probable_cause = probable_cause
    attempt.recommended_action = recommended_action
    attempt.impact_narrative = impact_narrative
    attempt.proposed_criticality = proposed_criticality
    attempt.proposed_nc_code = proposed_nc_code
    attempt.failure_class = None
    attempt.retry_eligible = False
    attempt.finished_at = finished_at or datetime.datetime.now(datetime.UTC)

    finding.interpretation_status = InterpretationStatus.COMPLETED
    db_session.commit()
    return attempt


def fail_interpretation(
    db_session: Session,
    *,
    finding: Finding,
    attempt: FindingInterpretation,
    failure_class: InterpretationFailureClass,
    retry_eligible: bool,
    finished_at: datetime.datetime | None = None,
) -> FindingInterpretation:
    """Close an attempt as FAILED, durably.

    ``FAILED`` is a real outcome, visible to an operator, and it is never
    converted into an empty success. ``retry_eligible`` is explicit rather than
    inferred from the failure class: whether a policy refusal or a malformed
    response is worth retrying is a judgement the caller makes.

    No message, no traceback and no provider payload is stored — the failure class
    is the whole record, matching the SECURITY-01/02 boundary the analysis run
    already follows.
    """
    if attempt.status not in (
        InterpretationStatus.PENDING,
        InterpretationStatus.RUNNING,
    ):
        raise ValueError(
            f"A {attempt.status.value} attempt is already terminal. A retry "
            "appends a new attempt rather than rewriting this one."
        )

    attempt.status = InterpretationStatus.FAILED
    attempt.failure_class = failure_class
    attempt.retry_eligible = retry_eligible
    attempt.finished_at = finished_at or datetime.datetime.now(datetime.UTC)

    finding.interpretation_status = InterpretationStatus.FAILED
    db_session.commit()
    return attempt


def next_attempt_no(db_session: Session, finding_id: UUID) -> int:
    """Next free attempt number for a finding.

    Racy on its own; ``uq_ton_finding_interpretation_attempt`` is the guarantee,
    so a concurrent second opener gets an ``IntegrityError`` rather than a
    duplicated attempt number.
    """
    highest = db_session.scalar(
        select(func.max(FindingInterpretation.attempt_no)).where(
            FindingInterpretation.finding_id == finding_id
        )
    )
    return 1 if highest is None else int(highest) + 1


def fetch_interpretations(
    db_session: Session, finding_id: UUID
) -> list[FindingInterpretation]:
    """Every attempt against one finding, oldest first.

    A failed attempt stays next to the eventual success. That is the point of the
    append-only design: an operator can see that the first two attempts timed out.
    """
    return list(
        db_session.scalars(
            select(FindingInterpretation)
            .where(FindingInterpretation.finding_id == finding_id)
            .order_by(FindingInterpretation.attempt_no)
        ).all()
    )


def latest_interpretation(
    db_session: Session, finding_id: UUID
) -> FindingInterpretation | None:
    """The newest attempt, whatever its outcome."""
    return db_session.scalars(
        select(FindingInterpretation)
        .where(FindingInterpretation.finding_id == finding_id)
        .order_by(FindingInterpretation.attempt_no.desc())
        .limit(1)
    ).one_or_none()


def is_interpretation_final(finding: Finding) -> bool:
    """Whether *finding* may take part in a published output.

    Readiness §8, invariants 1 and 2: only ``COMPLETED`` or ``NOT_REQUIRED``
    counts as final. A ``PENDING``, ``RUNNING`` or ``FAILED`` interpretation keeps
    the finding out of a report revision, which 003d enforces when it builds a
    snapshot.
    """
    return finding.interpretation_status in (
        InterpretationStatus.COMPLETED,
        InterpretationStatus.NOT_REQUIRED,
    )
