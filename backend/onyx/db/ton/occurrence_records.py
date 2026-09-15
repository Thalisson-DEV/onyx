"""Impact, assignment, note and impacted-domain writes (Plan 003c).

The records that hang off a business case and are not lifecycle transitions.
All four are domain history: a failure to persist one fails the business
operation. None of them is best-effort, and none is wrapped in a swallowing
``except`` — that behaviour belongs to the generic audit table in 003d, not here.

Money is :class:`~decimal.Decimal` throughout. A ``float`` argument raises rather
than being coerced.

**There is no ROI table and no ROI function here.** Realised ROI is a later
aggregation over verified impact rows; this module only makes the underlying
verified data recordable. :data:`ROI_ELIGIBLE_CONFIDENCE` states the §9 rule the
aggregation will apply so the two cannot disagree.
"""

import datetime
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    AssignmentStatus,
    ImpactCategory,
    ImpactConfidence,
    ImpactMethod,
    OccurrenceActorKind,
    RedactionLevel,
    RuleDomain,
    UnitCostSource,
)
from onyx.db.ton.models import (
    Occurrence,
    OccurrenceAssignment,
    OccurrenceImpact,
    OccurrenceImpactedDomain,
    OccurrenceNote,
)

# Prompt Mestre §9: an impact of BAIXA confidence never enters a target or a
# realised ROI. Stated here as the single definition the later aggregation reads,
# rather than repeated as a literal at each call site.
ROI_ELIGIBLE_CONFIDENCE: frozenset[ImpactConfidence] = frozenset(
    {ImpactConfidence.ALTA, ImpactConfidence.MEDIA}
)


def record_impact__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    category: ImpactCategory,
    confidence: ImpactConfidence,
    method: ImpactMethod,
    unit_cost_source: UnitCostSource,
    currency: str,
    scale: int,
    predicted_amount: Decimal | None = None,
    realized_amount: Decimal | None = None,
    quantity: Decimal | None = None,
    quantity_unit: str | None = None,
    unit_cost: Decimal | None = None,
    verified_at: datetime.datetime | None = None,
    verified_by: UUID | None = None,
    premise: str | None = None,
    sensitivity_pct: Decimal | None = None,
    period_start: datetime.date | None = None,
    period_end: datetime.date | None = None,
) -> OccurrenceImpact:
    """Record one quantification of *occurrence*.

    ``unit_cost_source`` has no default: §9's "diga sempre qual usou" means the
    caller states it, including stating ``NOT_APPLICABLE`` for a method that uses
    no reference unit cost.

    A realised amount requires ``verified_at``. §13.3 counts only savings
    verified against the following period, and the database enforces it too, so a
    caller cannot record a realised figure that nobody checked.

    Nothing here promotes confidence. A ``BAIXA`` row stays ``BAIXA`` however many
    times it is recorded, and it stays representable — excluded from ROI, not
    excluded from the ledger.
    """
    for name, amount in (
        ("predicted_amount", predicted_amount),
        ("realized_amount", realized_amount),
        ("quantity", quantity),
        ("unit_cost", unit_cost),
        ("sensitivity_pct", sensitivity_pct),
    ):
        if isinstance(amount, float):
            raise TypeError(
                f"{name} must be a Decimal, not a float. An IEEE-754 round-trip "
                "would make the published amount irreproducible."
            )

    if realized_amount is not None and verified_at is None:
        raise ValueError(
            "A realized_amount requires verified_at: Prompt Mestre §13.3 counts "
            "only a verified saving as realised."
        )
    if predicted_amount is None and realized_amount is None:
        raise ValueError(
            "An impact row must carry a predicted or a realised amount. A case "
            "with no quantification records no impact row at all."
        )
    if (
        method is ImpactMethod.OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST
        and unit_cost_source is UnitCostSource.NOT_APPLICABLE
    ):
        raise ValueError(
            "The §9 formula multiplies by a reference unit cost, so it cannot "
            "declare unit_cost_source = NOT_APPLICABLE."
        )

    impact = OccurrenceImpact(
        occurrence_id=occurrence.id,
        category=category,
        confidence=confidence,
        method=method,
        unit_cost_source=unit_cost_source,
        predicted_amount=predicted_amount,
        realized_amount=realized_amount,
        quantity=quantity,
        quantity_unit=quantity_unit,
        unit_cost=unit_cost,
        currency=currency,
        scale=scale,
        verified_at=verified_at,
        verified_by=verified_by,
        premise=premise,
        sensitivity_pct=sensitivity_pct,
        period_start=period_start,
        period_end=period_end,
    )
    db_session.add(impact)
    db_session.flush()
    return impact


def verify_impact__no_commit(
    db_session: Session,
    *,
    impact: OccurrenceImpact,
    realized_amount: Decimal,
    verified_by: UUID | None = None,
    verified_at: datetime.datetime | None = None,
) -> OccurrenceImpact:
    """Record the verified outcome of a quantification.

    Sets the realised amount and its verification stamp together, so the pair
    cannot be written half-way. The predicted amount is left untouched: keeping
    both is what lets a later report show forecast error rather than quietly
    replacing the estimate.
    """
    if isinstance(realized_amount, float):
        raise TypeError("realized_amount must be a Decimal, not a float.")

    impact.realized_amount = realized_amount
    impact.verified_at = verified_at or datetime.datetime.now(datetime.UTC)
    impact.verified_by = verified_by
    db_session.flush()
    return impact


def fetch_impacts(db_session: Session, occurrence_id: UUID) -> list[OccurrenceImpact]:
    """Every quantification recorded against one case."""
    return list(
        db_session.scalars(
            select(OccurrenceImpact)
            .where(OccurrenceImpact.occurrence_id == occurrence_id)
            .order_by(OccurrenceImpact.created_at, OccurrenceImpact.id)
        ).all()
    )


def is_roi_eligible(impact: OccurrenceImpact) -> bool:
    """Whether an impact row may enter a realised-ROI aggregation.

    Verified, with a realised amount, and not ``BAIXA`` confidence. The predicate
    lives next to the data so the 003d/Plan 006 aggregation reads it rather than
    reimplementing §9.
    """
    return (
        impact.verified_at is not None
        and impact.realized_amount is not None
        and impact.confidence in ROI_ELIGIBLE_CONFIDENCE
    )


def assign_responsible__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    responsible_label: str,
    actor_kind: OccurrenceActorKind = OccurrenceActorKind.USER,
    responsible_user_id: UUID | None = None,
    assigned_by_user_id: UUID | None = None,
    deadline: datetime.date | None = None,
    assigned_at: datetime.datetime | None = None,
    notes: str | None = None,
) -> OccurrenceAssignment:
    """Append an assignment, superseding the open one.

    Reassignment does not overwrite. The previous open row is stamped
    ``SUPERSEDED`` with a timestamp and stays readable, so who was responsible
    and by when is answerable for every past cycle — which is what §10 escalation
    and §12 R9 need.

    ``responsible_label`` is required and free text. A §11 blind spot is published
    with a named field owner who may hold no Onyx account, and TON invents no HR
    directory to look them up in.
    """
    if not responsible_label.strip():
        raise ValueError(
            "responsible_label is required: Prompt Mestre §11 publishes a gap "
            "with a named owner, never anonymously."
        )
    if actor_kind is OccurrenceActorKind.USER and assigned_by_user_id is None:
        raise ValueError("A user assignment must name the account that made it.")

    now = assigned_at or datetime.datetime.now(datetime.UTC)

    for existing in _open_assignments(db_session, occurrence.id):
        existing.status = AssignmentStatus.SUPERSEDED
        existing.superseded_at = now

    assignment = OccurrenceAssignment(
        occurrence_id=occurrence.id,
        sequence_no=_next_assignment_sequence(db_session, occurrence.id),
        responsible_user_id=responsible_user_id,
        responsible_label=responsible_label.strip(),
        deadline=deadline,
        status=AssignmentStatus.OPEN,
        assigned_at=now,
        assigned_by_user_id=assigned_by_user_id,
        actor_kind=actor_kind,
        notes=notes,
    )
    db_session.add(assignment)
    db_session.flush()
    return assignment


def complete_assignment__no_commit(
    db_session: Session,
    *,
    assignment: OccurrenceAssignment,
    completed_at: datetime.datetime | None = None,
) -> OccurrenceAssignment:
    """Close one assignment. Its row keeps its own outcome; nothing is erased."""
    assignment.status = AssignmentStatus.COMPLETED
    assignment.completed_at = completed_at or datetime.datetime.now(datetime.UTC)
    db_session.flush()
    return assignment


def current_assignment(
    db_session: Session, occurrence_id: UUID
) -> OccurrenceAssignment | None:
    """The newest assignment for a case, whatever its status."""
    return db_session.scalars(
        select(OccurrenceAssignment)
        .where(OccurrenceAssignment.occurrence_id == occurrence_id)
        .order_by(OccurrenceAssignment.sequence_no.desc())
        .limit(1)
    ).one_or_none()


def fetch_assignments(
    db_session: Session, occurrence_id: UUID
) -> list[OccurrenceAssignment]:
    """The full assignment history, oldest first."""
    return list(
        db_session.scalars(
            select(OccurrenceAssignment)
            .where(OccurrenceAssignment.occurrence_id == occurrence_id)
            .order_by(OccurrenceAssignment.sequence_no)
        ).all()
    )


def add_note__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    body: str,
    redaction_level: RedactionLevel,
    actor_kind: OccurrenceActorKind = OccurrenceActorKind.USER,
    author_user_id: UUID | None = None,
) -> OccurrenceNote:
    """Append a note. Append-only: there is no edit and no delete.

    ``redaction_level`` is required because a note may carry PII. The note
    inherits the occurrence ACL — :mod:`onyx.db.ton.acl` is the only read path,
    and there is no separate, more permissive one.
    """
    if not body.strip():
        raise ValueError("A note needs a body.")
    if actor_kind is OccurrenceActorKind.USER and author_user_id is None:
        raise ValueError("A user note must name its author.")

    note = OccurrenceNote(
        occurrence_id=occurrence.id,
        sequence_no=_next_note_sequence(db_session, occurrence.id),
        author_user_id=author_user_id,
        actor_kind=actor_kind,
        body=body,
        redaction_level=redaction_level,
    )
    db_session.add(note)
    db_session.flush()
    return note


def fetch_notes(db_session: Session, occurrence_id: UUID) -> list[OccurrenceNote]:
    """The note history, oldest first."""
    return list(
        db_session.scalars(
            select(OccurrenceNote)
            .where(OccurrenceNote.occurrence_id == occurrence_id)
            .order_by(OccurrenceNote.sequence_no)
        ).all()
    )


def set_impacted_domains__no_commit(
    db_session: Session,
    *,
    occurrence: Occurrence,
    domains: Sequence[RuleDomain],
    note: str | None = None,
) -> list[OccurrenceImpactedDomain]:
    """Declare the other domains this case affects.

    The Prompt Mestre §15 handoff rule: one domain owns the case — the link where
    the quantity changed — and the rest are listed. Recording the same issue once
    per specialist is what this prevents.

    The owning domain is refused. It is already ``Occurrence.owning_domain``, and
    listing it here would make "who owns this" answerable two ways.
    """
    requested = list(dict.fromkeys(domains))
    if occurrence.owning_domain in requested:
        raise ValueError(
            f"{occurrence.owning_domain.value} already owns this occurrence. "
            "Prompt Mestre §15 records the issue once, at the link where the "
            "quantity changed; the impacted list is for the other domains."
        )

    for existing in db_session.scalars(
        select(OccurrenceImpactedDomain).where(
            OccurrenceImpactedDomain.occurrence_id == occurrence.id
        )
    ).all():
        db_session.delete(existing)
    db_session.flush()

    rows = [
        OccurrenceImpactedDomain(occurrence_id=occurrence.id, domain=domain, note=note)
        for domain in requested
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


def _open_assignments(
    db_session: Session, occurrence_id: UUID
) -> list[OccurrenceAssignment]:
    return list(
        db_session.scalars(
            select(OccurrenceAssignment).where(
                OccurrenceAssignment.occurrence_id == occurrence_id,
                OccurrenceAssignment.status == AssignmentStatus.OPEN,
            )
        ).all()
    )


def _next_assignment_sequence(db_session: Session, occurrence_id: UUID) -> int:
    highest = db_session.scalar(
        select(func.max(OccurrenceAssignment.sequence_no)).where(
            OccurrenceAssignment.occurrence_id == occurrence_id
        )
    )
    return 1 if highest is None else int(highest) + 1


def _next_note_sequence(db_session: Session, occurrence_id: UUID) -> int:
    highest = db_session.scalar(
        select(func.max(OccurrenceNote.sequence_no)).where(
            OccurrenceNote.occurrence_id == occurrence_id
        )
    )
    return 1 if highest is None else int(highest) + 1
