"""Read-only occurrence tools, with current assignment and resource ACL."""

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Session, aliased

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import acl
from onyx.db.ton.enums import AssignmentStatus, OccurrenceStatus
from onyx.db.ton.models import Occurrence, OccurrenceAssignment
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.labels import business_label
from onyx.ton.agent.models import OccurrencePage, OccurrenceSummary, ToolQuery

TERMINAL = (
    OccurrenceStatus.RESOLVED,
    OccurrenceStatus.RISK_ACCEPTED,
    OccurrenceStatus.DISMISSED,
    OccurrenceStatus.SUPERSEDED,
)


def query_occurrences(
    session: Session, user: User, operation: str, query: ToolQuery
) -> OccurrencePage:
    acl.assert_global(user, permission=Permission.READ_TON_OCCURRENCES)
    today = datetime.now(UTC).date()
    previous = aliased(OccurrenceAssignment)
    latest_sequence = (
        sa.select(sa.func.max(previous.sequence_no))
        .where(previous.occurrence_id == Occurrence.id)
        .correlate(Occurrence)
        .scalar_subquery()
    )
    statement = (
        sa.select(Occurrence, OccurrenceAssignment)
        .outerjoin(
            OccurrenceAssignment,
            sa.and_(
                OccurrenceAssignment.occurrence_id == Occurrence.id,
                OccurrenceAssignment.sequence_no == latest_sequence,
            ),
        )
        .where(acl.occurrence_visible_clause(user))
    )
    if operation == "ton_get_occurrence":
        if query.occurrence_id is None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Informe occurrence_id.")
        acl.get_occurrence_for_user(session, user, query.occurrence_id)
        statement = statement.where(Occurrence.id == query.occurrence_id)
    if operation == "ton_list_overdue_actions":
        statement = statement.where(
            Occurrence.status.not_in(TERMINAL),
            OccurrenceAssignment.status == AssignmentStatus.OPEN,
            OccurrenceAssignment.deadline < today,
        )
    rows = session.execute(
        statement.order_by(
            OccurrenceAssignment.deadline.asc().nulls_last(),
            Occurrence.last_detected_at.desc(),
            Occurrence.id,
        )
        .offset(query.offset if operation != "ton_get_occurrence" else 0)
        .limit(query.limit + 1 if operation != "ton_get_occurrence" else 1)
    ).all()
    items = []
    for occurrence, assignment in rows[: query.limit]:
        overdue = bool(
            assignment is not None
            and assignment.deadline is not None
            and assignment.deadline < today
            and assignment.status == AssignmentStatus.OPEN
            and occurrence.status not in TERMINAL
        )
        items.append(
            OccurrenceSummary(
                occurrence_id=occurrence.id,
                reference=occurrence.short_code,
                title=occurrence.title[:500],
                status=business_label(occurrence.status.value),
                criticality=business_label(occurrence.criticality.value),
                open_cycles=occurrence.open_cycle_count,
                last_detected_at=occurrence.last_detected_at,
                owner=assignment.responsible_label[:200] if assignment else None,
                deadline=assignment.deadline if assignment else None,
                assignment_status=business_label(assignment.status.value)
                if assignment
                else None,
                overdue=overdue,
                requires_human_closure=occurrence.requires_human_closure,
                verification_criterion=occurrence.verification_criterion[:500]
                if occurrence.verification_criterion
                else None,
            )
        )
    has_more = len(rows) > query.limit
    return OccurrencePage(
        as_of=today,
        items=items,
        has_more=has_more,
        next_offset=query.offset + query.limit if has_more else None,
    )
