"""Domain-scoped execution blocking (Plan 003b).

This module is the anti-regression guard for the original TON defect. Prompt
Mestre §5 says a failed step blocks the following ones. Read literally in
software, one failed financial base validation would silence fleet, contracts
and HR, and one failed unit would silence every other unit. That is the defect.

The correct reading, fixed by readiness §5: **failure blocks only the affected
``(step_code, domain, business_unit_id)`` scope and its declared dependents.**
A run that mixes failures and successes ends
``COMPLETED_WITH_BLOCKED_DOMAINS``, never ``FAILED``, so the specialist results
that did succeed survive.

Three properties make that structural rather than conventional:

1. :func:`block_step__no_commit` is the only way to reach ``BLOCKED``, and it
   refuses a cause whose scope does not contain the blocked step's scope. Widening
   the blast radius is not expressible through this API.
2. It also refuses a cause that is not upstream of the blocked step in
   :data:`STEP_ORDER`, so blocking cannot run backwards.
3. ``ck_ton_analysis_step_blocked_requires_cause`` means a BLOCKED row always
   names its cause and reason in the database, even if a future writer bypasses
   this module.

Not a workflow engine. The seven step codes and their order are fixed by §5;
there is no dependency graph to configure, no retry policy and no dispatch. Plan
006 owns Celery scheduling.

No LLM participates in blocking. Every decision here is deterministic.
"""

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    AnalysisRunStatus,
    AnalysisStepBlockedReason,
    AnalysisStepCode,
    AnalysisStepStatus,
    RuleDomain,
)
from onyx.db.ton.models import AnalysisRun, AnalysisStep

# The fixed Prompt Mestre §5 protocol. Position in this tuple *is* the dependency
# relation: every step depends on all steps before it, within its own scope.
STEP_ORDER: tuple[AnalysisStepCode, ...] = (
    AnalysisStepCode.INGESTION,
    AnalysisStepCode.BASE_VALIDATION,
    AnalysisStepCode.CHAIN_RECONCILIATION,
    AnalysisStepCode.DETECTION,
    AnalysisStepCode.QUANTIFICATION,
    AnalysisStepCode.PRIORITIZATION,
    AnalysisStepCode.PUBLICATION,
)

_STEP_POSITION: dict[AnalysisStepCode, int] = {
    step_code: position for position, step_code in enumerate(STEP_ORDER)
}

# Statuses a step can still be moved out of. A step that already reached a
# verdict is not retroactively blocked, so a PASSED sibling is never rewritten.
_BLOCKABLE_STATUSES: frozenset[AnalysisStepStatus] = frozenset(
    {AnalysisStepStatus.PENDING}
)

_NON_TERMINAL_STATUSES: frozenset[AnalysisStepStatus] = frozenset(
    {AnalysisStepStatus.PENDING, AnalysisStepStatus.RUNNING}
)


@dataclass(frozen=True)
class StepScope:
    """The blocking unit: a domain and a business unit, either of them run-wide.

    ``None`` means run-wide, not unknown. A run-wide scope contains every
    narrower one; two different domains contain neither.
    """

    domain: RuleDomain | None
    business_unit_id: UUID | None

    def contains(self, other: "StepScope") -> bool:
        if self.domain is not None and self.domain != other.domain:
            return False
        if (
            self.business_unit_id is not None
            and self.business_unit_id != other.business_unit_id
        ):
            return False
        return True


def scope_of(step: AnalysisStep) -> StepScope:
    return StepScope(domain=step.domain, business_unit_id=step.business_unit_id)


def downstream_step_codes(step_code: AnalysisStepCode) -> tuple[AnalysisStepCode, ...]:
    """Step codes that depend on *step_code*, in protocol order."""
    return STEP_ORDER[_STEP_POSITION[step_code] + 1 :]


def is_upstream_of(candidate: AnalysisStepCode, step_code: AnalysisStepCode) -> bool:
    return _STEP_POSITION[candidate] < _STEP_POSITION[step_code]


def create_analysis_step__no_commit(
    db_session: Session,
    *,
    analysis_run: AnalysisRun,
    step_code: AnalysisStepCode,
    domain: RuleDomain | None = None,
    business_unit_id: UUID | None = None,
    status: AnalysisStepStatus = AnalysisStepStatus.PENDING,
) -> AnalysisStep:
    """Create one step in one scope.

    A step may not be created ``BLOCKED``: blocking requires a cause, and a cause
    is another step in the same run. Use :func:`block_step__no_commit`.
    """
    if status is AnalysisStepStatus.BLOCKED:
        raise ValueError(
            "A step cannot be created BLOCKED. Blocking must name the step that "
            "caused it, so it goes through block_step__no_commit."
        )

    step = AnalysisStep(
        analysis_run_id=analysis_run.id,
        step_code=step_code,
        domain=domain,
        business_unit_id=business_unit_id,
        status=status,
    )
    db_session.add(step)
    db_session.flush()
    return step


def start_step__no_commit(
    db_session: Session,
    *,
    step: AnalysisStep,
    started_at: datetime.datetime | None = None,
) -> AnalysisStep:
    step.status = AnalysisStepStatus.RUNNING
    step.started_at = started_at or datetime.datetime.now(datetime.UTC)
    db_session.flush()
    return step


def pass_step__no_commit(
    db_session: Session,
    *,
    step: AnalysisStep,
    finished_at: datetime.datetime | None = None,
) -> AnalysisStep:
    now = finished_at or datetime.datetime.now(datetime.UTC)
    if step.started_at is None:
        step.started_at = now
    step.status = AnalysisStepStatus.PASSED
    step.finished_at = now
    db_session.flush()
    return step


def block_step__no_commit(
    db_session: Session,
    *,
    step: AnalysisStep,
    caused_by: AnalysisStep,
    reason: AnalysisStepBlockedReason,
) -> AnalysisStep:
    """Block *step* because *caused_by* failed. The only path to ``BLOCKED``.

    Four refusals keep the blast radius contained:

    * a cause from a different run — blocking never crosses run boundaries;
    * a step blocking itself;
    * a cause whose scope does not contain the step's scope — this is the
      anti-defect guard, and it is why a Mossoró financial failure cannot block
      Itabirito or fleet;
    * a cause that is not upstream in :data:`STEP_ORDER`.
    """
    if step.analysis_run_id != caused_by.analysis_run_id:
        raise ValueError(
            "A step may only be blocked by a step in the same analysis run."
        )
    if step.id == caused_by.id:
        raise ValueError("A step cannot block itself.")

    cause_scope = scope_of(caused_by)
    step_scope = scope_of(step)
    if not cause_scope.contains(step_scope):
        raise ValueError(
            "Blocking is scoped. A failure in "
            f"(domain={_render(cause_scope.domain)}, "
            f"unit={_render(cause_scope.business_unit_id)}) cannot block "
            f"(domain={_render(step_scope.domain)}, "
            f"unit={_render(step_scope.business_unit_id)}): a domain or unit "
            "failure must not stop an unrelated domain or unit."
        )
    if not is_upstream_of(caused_by.step_code, step.step_code):
        raise ValueError(
            f"{caused_by.step_code.value} does not precede {step.step_code.value} "
            "in the seven-step protocol, so it cannot block it."
        )

    step.status = AnalysisStepStatus.BLOCKED
    step.blocked_by_step_id = caused_by.id
    step.blocked_reason = reason
    db_session.flush()
    return step


def fail_step__no_commit(
    db_session: Session,
    *,
    step: AnalysisStep,
    blocked_reason: AnalysisStepBlockedReason = (
        AnalysisStepBlockedReason.PREREQUISITE_FAILED
    ),
    finished_at: datetime.datetime | None = None,
) -> list[AnalysisStep]:
    """Mark *step* FAILED and block its dependents in the same scope.

    Returns the steps that became BLOCKED. Steps in a sibling domain or a sibling
    unit are untouched, and a step that already reached a verdict is never
    rewritten.
    """
    now = finished_at or datetime.datetime.now(datetime.UTC)
    if step.started_at is None:
        step.started_at = now
    step.status = AnalysisStepStatus.FAILED
    step.finished_at = now
    db_session.flush()

    return block_dependents__no_commit(
        db_session, failed_step=step, reason=blocked_reason
    )


def block_dependents__no_commit(
    db_session: Session,
    *,
    failed_step: AnalysisStep,
    reason: AnalysisStepBlockedReason,
) -> list[AnalysisStep]:
    """Block every pending step that depends on *failed_step*, in scope only."""
    downstream = downstream_step_codes(failed_step.step_code)
    if not downstream:
        return []

    candidates = (
        db_session.execute(
            select(AnalysisStep).where(
                AnalysisStep.analysis_run_id == failed_step.analysis_run_id,
                AnalysisStep.step_code.in_(downstream),
                AnalysisStep.status.in_(_BLOCKABLE_STATUSES),
            )
        )
        .scalars()
        .all()
    )

    cause_scope = scope_of(failed_step)
    blocked: list[AnalysisStep] = []
    for candidate in candidates:
        if candidate.id == failed_step.id:
            continue
        if not cause_scope.contains(scope_of(candidate)):
            continue
        blocked.append(
            block_step__no_commit(
                db_session, step=candidate, caused_by=failed_step, reason=reason
            )
        )
    return blocked


def reprove_base__no_commit(
    db_session: Session,
    *,
    step: AnalysisStep,
    finished_at: datetime.datetime | None = None,
) -> list[AnalysisStep]:
    """Rule S10: a reproved base blocks publication for that scope only.

    Prompt Mestre §6 S10 forbids publishing a margin on a base that failed
    validation. It is expressed as a blocked PUBLICATION step in the reproved
    ``(domain, business unit)``, never as a run-wide flag and never as an active
    rule version.
    """
    if step.step_code is not AnalysisStepCode.BASE_VALIDATION:
        raise ValueError(
            "S10 applies to BASE_VALIDATION. Reproving "
            f"{step.step_code.value} is not the S10 semantics."
        )
    return fail_step__no_commit(
        db_session,
        step=step,
        blocked_reason=AnalysisStepBlockedReason.BASE_REPROVED,
        finished_at=finished_at,
    )


def resolve_run_status(steps: Sequence[AnalysisStep]) -> AnalysisRunStatus:
    """Roll a run's steps up into a run status.

    The distinction this function exists for: a run holding both a success and a
    failure is ``COMPLETED_WITH_BLOCKED_DOMAINS``. Only a run with no successful
    step at all is ``FAILED``.
    """
    if not steps:
        return AnalysisRunStatus.QUEUED

    statuses = [step.status for step in steps]
    if any(status in _NON_TERMINAL_STATUSES for status in statuses):
        return AnalysisRunStatus.RUNNING

    has_success = AnalysisStepStatus.PASSED in statuses
    has_failure = any(
        status in (AnalysisStepStatus.FAILED, AnalysisStepStatus.BLOCKED)
        for status in statuses
    )

    if has_failure and has_success:
        return AnalysisRunStatus.COMPLETED_WITH_BLOCKED_DOMAINS
    if has_failure:
        return AnalysisRunStatus.FAILED
    return AnalysisRunStatus.COMPLETED


def blocked_steps_for_scope(
    steps: Sequence[AnalysisStep],
    *,
    domain: RuleDomain | None,
    business_unit_id: UUID | None,
) -> list[AnalysisStep]:
    """Blocked steps whose scope is exactly ``(domain, business_unit_id)``."""
    return [
        step
        for step in steps
        if step.status is AnalysisStepStatus.BLOCKED
        and step.domain == domain
        and step.business_unit_id == business_unit_id
    ]


def _render(value: object | None) -> str:
    if value is None:
        return "run-wide"
    if isinstance(value, RuleDomain):
        return value.value
    return str(value)
