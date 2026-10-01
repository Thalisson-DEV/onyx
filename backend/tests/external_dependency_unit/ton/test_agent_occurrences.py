"""Bounded action queries against synthetic occurrence and assignment history."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.permissions import recompute_user_permissions__no_commit
from onyx.db.ton.enums import AssignmentStatus, OccurrenceActorKind
from onyx.db.ton.models import OccurrenceAssignment
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.models import OccurrencePage, ToolQuery
from onyx.ton.agent.service import query_domain
from tests.external_dependency_unit.ton import factories


def test_overdue_uses_current_assignment_and_resource_acl(ton_session: Session) -> None:
    admin = factories.make_admin(ton_session)
    rule, version = factories.make_occurrence_rule_version(ton_session)
    run = factories.make_analysis_run(ton_session)
    now = datetime.now(UTC)
    cases = [
        factories.record_synthetic_detection(
            ton_session,
            rule=rule,
            rule_version=version,
            analysis_run=run,
            identity_values={"period": f"2001-{index + 1:02d}"},
        ).occurrence
        for index in range(4)
    ]
    for index, case in enumerate(cases):
        ton_session.add(
            OccurrenceAssignment(
                occurrence_id=case.id,
                sequence_no=1,
                responsible_label="Synthetic controller",
                assigned_at=now,
                actor_kind=OccurrenceActorKind.USER,
                status=AssignmentStatus.OPEN,
                deadline=now.date() - timedelta(days=1) if index != 3 else None,
            )
        )
    ton_session.add(
        OccurrenceAssignment(
            occurrence_id=cases[2].id,
            sequence_no=2,
            responsible_label="Synthetic reassigned controller",
            assigned_at=now,
            actor_kind=OccurrenceActorKind.USER,
            status=AssignmentStatus.OPEN,
            deadline=now.date() + timedelta(days=1),
        )
    )
    ton_session.commit()
    page = query_domain(
        ton_session, admin, "ton_list_overdue_actions", ToolQuery(limit=1)
    )
    assert isinstance(page, OccurrencePage)
    assert len(page.items) == 1 and page.has_more and page.next_offset == 1
    second = query_domain(
        ton_session, admin, "ton_list_overdue_actions", ToolQuery(limit=1, offset=1)
    )
    assert isinstance(second, OccurrencePage)
    assert len(second.items) == 1 and not second.has_more
    assert {page.items[0].occurrence_id, second.items[0].occurrence_id} == {
        cases[0].id,
        cases[1].id,
    }
    detail = query_domain(
        ton_session, admin, "ton_get_occurrence", ToolQuery(occurrence_id=cases[2].id)
    )
    assert isinstance(detail, OccurrencePage)
    assert detail.items[0].owner == "Synthetic reassigned controller"
    assert not detail.items[0].overdue
    assert all(case.resolved_at is None for case in cases)

    user = factories.make_user(ton_session)
    group = factories.make_group(ton_session)
    factories.add_member(ton_session, group=group, user=user)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.READ_TON_OCCURRENCES]
    )
    factories.authorize_group(ton_session, group=group, occurrence=cases[0])
    recompute_user_permissions__no_commit(user.id, ton_session)
    ton_session.refresh(user)
    ton_session.commit()
    visible = query_domain(ton_session, user, "ton_list_overdue_actions", ToolQuery())
    assert isinstance(visible, OccurrencePage)
    assert [item.occurrence_id for item in visible.items] == [cases[0].id]
    with pytest.raises(OnyxError):
        query_domain(
            ton_session,
            user,
            "ton_get_occurrence",
            ToolQuery(occurrence_id=cases[1].id),
        )
    outsider = factories.make_user(ton_session)
    with pytest.raises(OnyxError):
        query_domain(ton_session, outsider, "ton_list_occurrences", ToolQuery())
