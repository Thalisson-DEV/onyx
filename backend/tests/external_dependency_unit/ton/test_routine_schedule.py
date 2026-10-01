"""Scheduled closing uses synthetic calendars and disposable tenant data."""

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import KVStore
from onyx.db.permissions import recompute_user_permissions__no_commit
from onyx.db.ton.enums import AnalysisTrigger
from onyx.db.ton.models import AnalysisRun, AnalysisStep, TonReportRevision
from onyx.db.ton.routine_schedule import (
    SCHEDULE_KEY,
    configure_schedule,
    dispatch_due_r3,
    schedule_view,
)
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.scheduling import R3ScheduleRequest, R3ScheduleState
from tests.external_dependency_unit.ton import factories


def test_disabled_default_and_calendar_required(ton_session: Session) -> None:
    admin = factories.make_admin(ton_session)
    assert not schedule_view(ton_session, admin).enabled
    assert not dispatch_due_r3(ton_session)
    assert ton_session.get(KVStore, SCHEDULE_KEY) is None
    with pytest.raises(ValidationError):
        R3ScheduleRequest(enabled=True)
    with pytest.raises(OnyxError):
        configure_schedule(
            ton_session, factories.make_user(ton_session), R3ScheduleRequest()
        )


def test_schedule_publication_retry_and_calendar_expiry(
    ton_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = factories.make_admin(ton_session)
    config = R3ScheduleRequest(
        enabled=True,
        calendar_name="Synthetic calendar",
        nonworking_dates=[date(2026, 11, 2)],
        calendar_valid_through=date(2026, 12, 31),
    )
    before = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
    due = datetime(2026, 11, 3, 11, tzinfo=timezone.utc)
    view = configure_schedule(ton_session, admin, config, now=before)
    assert view.next_run_at == due
    reader = factories.make_user(ton_session)
    group = factories.make_group(ton_session)
    factories.add_member(ton_session, group=group, user=reader)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.READ_TON_SOURCES]
    )
    recompute_user_permissions__no_commit(reader.id, ton_session)
    ton_session.refresh(reader)
    reader_view = schedule_view(ton_session, reader)
    assert reader_view.schedule == view.schedule
    assert reader_view.enabled == view.enabled
    assert reader_view.next_run_at == due
    assert not dispatch_due_r3(
        ton_session, now=datetime(2026, 11, 3, 10, 59, tzinfo=timezone.utc)
    )
    # Simulate a crash after immutable publication, before saving the cursor.
    from onyx.db.ton import routine_schedule

    save = routine_schedule._save
    monkeypatch.setattr(
        routine_schedule,
        "_save",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("synthetic cursor failure")),
    )
    with pytest.raises(RuntimeError):
        dispatch_due_r3(ton_session, now=due)
    ton_session.rollback()
    monkeypatch.setattr(routine_schedule, "_save", save)
    assert dispatch_due_r3(ton_session, now=due)
    assert not dispatch_due_r3(ton_session, now=due)
    assert ton_session.scalar(select(func.count()).select_from(TonReportRevision)) == 1
    run = ton_session.scalar(select(AnalysisRun))
    assert run is not None and run.trigger == AnalysisTrigger.SCHEDULED
    assert run.routine_code == "R3" and run.period_start == date(2026, 10, 1)
    assert ton_session.scalar(select(func.count()).select_from(AnalysisStep)) == 21
    view = schedule_view(ton_session, admin)
    assert view.last_report_url and view.last_result
    assert view.next_run_at == datetime(2026, 12, 1, 11, tzinfo=timezone.utc)
    assert dispatch_due_r3(ton_session, now=view.next_run_at)
    view = schedule_view(ton_session, admin)
    assert not view.enabled and view.next_run_at is None
    assert "Calendário vencido" in view.reason


def test_schedule_disables_after_actor_revocation(ton_session: Session) -> None:
    admin = factories.make_admin(ton_session)
    configure_schedule(
        ton_session,
        admin,
        R3ScheduleRequest(
            enabled=True,
            calendar_name="Synthetic calendar",
            calendar_valid_through=date(2026, 12, 31),
        ),
        now=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    admin.is_active = False
    ton_session.commit()
    assert not dispatch_due_r3(
        ton_session, now=datetime(2026, 11, 2, 11, tzinfo=timezone.utc)
    )
    row = ton_session.get(KVStore, SCHEDULE_KEY)
    assert row is not None
    state = R3ScheduleState.model_validate(row.value)
    assert not state.enabled and state.failure_reason
    assert ton_session.scalar(select(func.count()).select_from(TonReportRevision)) == 0
