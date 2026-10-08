"""Automations persistence: definitions and versions, runs with leases,
step checkpoints, approvals, notices and data files."""

import datetime
from collections.abc import Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, defer

from onyx.db.models import User
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.email_flows import can_manage, can_read, require_manage, require_read
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import (
    TonAutomation,
    TonAutomationApproval,
    TonAutomationFile,
    TonAutomationNotice,
    TonAutomationRun,
    TonAutomationStepRun,
    TonAutomationVersion,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.automations.definition import (
    AutomationDefinition,
    AutomationKind,
    AutomationOrigin,
    AutomationStatus,
    RunMode,
    RunStatus,
)
from onyx.utils.audit import AuditAction, AuditOutcome

__all__ = ["can_manage", "can_read", "require_manage", "require_read"]

LEASE = datetime.timedelta(minutes=5)


def audit(
    session: Session,
    user: User | None,
    action: AuditAction,
    automation: TonAutomation,
    extra: dict[str, Any],
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
) -> None:
    emit_ton_audit_event(
        session,
        action=action,
        outcome=outcome,
        actor_user_id=user.id if user else None,
        resource_kind=TonAuditResourceKind.AUTOMATION,
        resource_id=automation.id,
        extra={"automation_name": automation.name, **extra},
    )


# ---------------------------------------------------------------------------
# Automations
# ---------------------------------------------------------------------------


def get_automation(session: Session, automation_id: UUID) -> TonAutomation:
    automation = session.get(TonAutomation, automation_id)
    if automation is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Automação não encontrada")
    return automation


def current_version(session: Session, automation: TonAutomation) -> TonAutomationVersion:
    version = session.scalar(
        sa.select(TonAutomationVersion).where(
            TonAutomationVersion.automation_id == automation.id,
            TonAutomationVersion.version == automation.current_version,
        )
    )
    assert version is not None
    return version


def list_automations(
    session: Session, *, include_archived: bool = False
) -> list[tuple[TonAutomation, TonAutomationVersion]]:
    query = sa.select(TonAutomation, TonAutomationVersion).join(
        TonAutomationVersion,
        sa.and_(
            TonAutomationVersion.automation_id == TonAutomation.id,
            TonAutomationVersion.version == TonAutomation.current_version,
        ),
    )
    if not include_archived:
        query = query.where(TonAutomation.status != AutomationStatus.ARCHIVED.value)
    rows = session.execute(query.order_by(TonAutomation.updated_at.desc())).all()
    return [(row[0], row[1]) for row in rows]


def active_by_trigger(
    session: Session, trigger_types: Sequence[str]
) -> list[tuple[TonAutomation, TonAutomationVersion]]:
    if not trigger_types:
        return []
    rows = session.execute(
        sa.select(TonAutomation, TonAutomationVersion)
        .join(
            TonAutomationVersion,
            sa.and_(
                TonAutomationVersion.automation_id == TonAutomation.id,
                TonAutomationVersion.version == TonAutomation.current_version,
            ),
        )
        .where(
            TonAutomation.status == AutomationStatus.ACTIVE.value,
            TonAutomation.trigger_type.in_(list(trigger_types)),
        )
    ).all()
    return [(row[0], row[1]) for row in rows]


def versions(session: Session, automation_id: UUID) -> list[TonAutomationVersion]:
    return list(
        session.scalars(
            sa.select(TonAutomationVersion)
            .where(TonAutomationVersion.automation_id == automation_id)
            .options(defer(TonAutomationVersion.definition))
            .order_by(TonAutomationVersion.version.desc())
            .limit(50)
        )
    )


def get_version(session: Session, automation_id: UUID, version: int) -> TonAutomationVersion:
    row = session.scalar(
        sa.select(TonAutomationVersion).where(
            TonAutomationVersion.automation_id == automation_id,
            TonAutomationVersion.version == version,
        )
    )
    if row is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Versão não encontrada")
    return row


def create__no_commit(
    session: Session,
    user: User | None,
    *,
    name: str,
    description: str | None,
    kind: AutomationKind,
    definition: AutomationDefinition,
    origin: AutomationOrigin,
    status: AutomationStatus,
    now: datetime.datetime,
    suggestion_reason: str | None = None,
    suggestion_model: str | None = None,
    seed_key: str | None = None,
    legacy_flow_id: UUID | None = None,
    owner_id: UUID | None = None,
    active_since: datetime.datetime | None = None,
) -> TonAutomation:
    active = status is AutomationStatus.ACTIVE
    automation = TonAutomation(
        name=name,
        description=description,
        kind=kind.value,
        origin=origin.value,
        status=status.value,
        trigger_type=definition.trigger.type,
        current_version=1,
        seed_key=seed_key,
        legacy_flow_id=legacy_flow_id,
        suggestion_reason=suggestion_reason,
        suggestion_model=suggestion_model,
        owner_id=owner_id or (user.id if user and active else None),
        active_since=active_since or (now if active else None),
        created_by=user.id if user else None,
        updated_by=user.id if user else None,
        updated_at=now,
    )
    session.add(automation)
    session.flush()
    session.add(
        TonAutomationVersion(
            automation_id=automation.id,
            version=1,
            name=name,
            definition=definition.dump(),
            note="Criada",
            created_by=user.id if user else None,
        )
    )
    audit(session, user, AuditAction.TON_AUTOMATION_CHANGE, automation, {"change": "created", "origin": origin.value, "status": status.value})
    return automation


def add_version__no_commit(
    session: Session,
    user: User | None,
    automation: TonAutomation,
    *,
    name: str,
    description: str | None,
    kind: AutomationKind,
    definition: AutomationDefinition,
    now: datetime.datetime,
    note: str | None = None,
) -> TonAutomationVersion:
    if automation.status == AutomationStatus.ARCHIVED.value:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Automação arquivada não pode ser editada")
    automation.current_version += 1
    automation.name = name
    automation.description = description
    automation.kind = kind.value
    automation.trigger_type = definition.trigger.type
    automation.updated_at = now
    automation.updated_by = user.id if user else None
    version = TonAutomationVersion(
        automation_id=automation.id,
        version=automation.current_version,
        name=name,
        definition=definition.dump(),
        note=note,
        created_by=user.id if user else None,
    )
    session.add(version)
    audit(session, user, AuditAction.TON_AUTOMATION_CHANGE, automation, {"change": "new_version", "version": automation.current_version})
    return version


_TRANSITIONS: dict[AutomationStatus, set[AutomationStatus]] = {
    AutomationStatus.DRAFT: {AutomationStatus.ACTIVE, AutomationStatus.ARCHIVED},
    AutomationStatus.ACTIVE: {AutomationStatus.PAUSED},
    AutomationStatus.PAUSED: {AutomationStatus.ACTIVE, AutomationStatus.ARCHIVED},
    AutomationStatus.ARCHIVED: {AutomationStatus.PAUSED},
}


def set_status__no_commit(
    session: Session,
    user: User,
    automation: TonAutomation,
    status: AutomationStatus,
    now: datetime.datetime,
) -> None:
    previous = AutomationStatus(automation.status)
    if status not in _TRANSITIONS[previous]:
        raise OnyxError(OnyxErrorCode.CONFLICT, f"Não é possível passar de {previous.value} para {status.value}")
    automation.status = status.value
    automation.updated_at = now
    automation.updated_by = user.id
    if status is AutomationStatus.ACTIVE:
        # Who turns it on answers for it and lends their visibility.
        automation.owner_id = user.id
        automation.active_since = now
    audit(session, user, AuditAction.TON_AUTOMATION_CHANGE, automation, {"change": "status", "from": previous.value, "to": status.value})


def seeded(session: Session, seed_key: str) -> TonAutomation | None:
    return session.scalar(sa.select(TonAutomation).where(TonAutomation.seed_key == seed_key))


def migrated_flow_ids(session: Session) -> set[UUID]:
    return {
        row
        for row in session.scalars(
            sa.select(TonAutomation.legacy_flow_id).where(TonAutomation.legacy_flow_id.is_not(None))
        )
        if row is not None
    }


def names_by_id(session: Session, ids: Sequence[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    return dict(session.execute(sa.select(TonAutomation.id, TonAutomation.name).where(TonAutomation.id.in_(list(ids)))).all())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


def create_run__no_commit(
    session: Session,
    *,
    automation: TonAutomation,
    version: TonAutomationVersion,
    trigger_key: str,
    mode: RunMode,
    trigger_output: dict[str, Any],
    triggered_by: UUID | None,
    now: datetime.datetime,
    resubmitted_from: UUID | None = None,
) -> TonAutomationRun | None:
    """Queue a run. A live run is unique per (automation, trigger key):
    ``None`` when that window or event already started one."""
    values: dict[str, Any] = dict(
        automation_id=automation.id,
        version_id=version.id,
        trigger_key=trigger_key[:240],
        mode=mode.value,
        status=RunStatus.QUEUED.value,
        trigger_output=trigger_output,
        triggered_by=triggered_by,
        resubmitted_from=resubmitted_from,
        created_at=now,
        executions=0,
    )
    if mode is not RunMode.LIVE:
        run = TonAutomationRun(**values)
        session.add(run)
        session.flush()
        return run
    run_id = session.scalar(
        insert(TonAutomationRun)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=["automation_id", "trigger_key"],
            index_where=sa.text("mode = 'LIVE'"),
        )
        .returning(TonAutomationRun.id)
    )
    return session.get(TonAutomationRun, run_id) if run_id else None


def live_run_exists(session: Session, automation_id: UUID, trigger_key: str) -> bool:
    return bool(
        session.scalar(
            sa.select(sa.literal(True)).where(
                TonAutomationRun.automation_id == automation_id,
                TonAutomationRun.trigger_key == trigger_key[:240],
                TonAutomationRun.mode == RunMode.LIVE.value,
            )
        )
    )


def get_run(session: Session, run_id: UUID) -> TonAutomationRun:
    run = session.get(TonAutomationRun, run_id)
    if run is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Execução não encontrada")
    return run


def claim_run__no_commit(
    session: Session, run_id: UUID, owner: str, now: datetime.datetime
) -> TonAutomationRun | None:
    """Take the run for this worker if nobody holds a live lease on it."""
    claimed = session.scalar(
        sa.update(TonAutomationRun)
        .where(
            TonAutomationRun.id == run_id,
            TonAutomationRun.status.in_([RunStatus.QUEUED.value, RunStatus.RUNNING.value]),
            sa.or_(TonAutomationRun.lease_until.is_(None), TonAutomationRun.lease_until < now),
        )
        .values(
            status=RunStatus.RUNNING.value,
            lease_owner=owner,
            lease_until=now + LEASE,
            started_at=sa.func.coalesce(TonAutomationRun.started_at, now),
            executions=TonAutomationRun.executions + 1,
        )
        .returning(TonAutomationRun.id)
    )
    if claimed is None:
        return None
    return session.get(TonAutomationRun, run_id, populate_existing=True)


def extend_lease(session: Session, run_id: UUID, owner: str, now: datetime.datetime) -> None:
    session.execute(
        sa.update(TonAutomationRun)
        .where(TonAutomationRun.id == run_id, TonAutomationRun.lease_owner == owner)
        .values(lease_until=now + LEASE)
    )


def run_status(session: Session, run_id: UUID) -> str | None:
    return session.scalar(sa.select(TonAutomationRun.status).where(TonAutomationRun.id == run_id))


def runnable_run_ids(session: Session, now: datetime.datetime, limit: int = 50) -> list[UUID]:
    """Queued runs nobody holds, waiting runs whose time came, and running
    runs whose worker stopped (lease expired)."""
    rows = session.scalars(
        sa.select(TonAutomationRun.id)
        .where(
            sa.or_(
                sa.and_(
                    TonAutomationRun.status == RunStatus.QUEUED.value,
                    sa.or_(TonAutomationRun.lease_until.is_(None), TonAutomationRun.lease_until < now),
                ),
                sa.and_(
                    TonAutomationRun.status == RunStatus.WAITING.value,
                    TonAutomationRun.resume_at.is_not(None),
                    TonAutomationRun.resume_at <= now,
                ),
                sa.and_(
                    TonAutomationRun.status == RunStatus.RUNNING.value,
                    TonAutomationRun.lease_until < now,
                ),
            )
        )
        .order_by(TonAutomationRun.created_at)
        .limit(limit)
    )
    return list(rows)


def open_runs_started_before(session: Session, cutoff_by_automation: dict[UUID, datetime.datetime]) -> list[TonAutomationRun]:
    if not cutoff_by_automation:
        return []
    rows = session.scalars(
        sa.select(TonAutomationRun).where(
            TonAutomationRun.status.in_([RunStatus.WAITING.value, RunStatus.QUEUED.value]),
            TonAutomationRun.automation_id.in_(list(cutoff_by_automation)),
        )
    ).all()
    return [run for run in rows if run.created_at < cutoff_by_automation[run.automation_id]]


def runs_for(
    session: Session, automation_ids: Sequence[UUID], per_automation: int, *, since: datetime.datetime | None = None
) -> dict[UUID, list[TonAutomationRun]]:
    if not automation_ids:
        return {}
    ranked = (
        sa.select(
            TonAutomationRun.id,
            sa.func.row_number()
            .over(partition_by=TonAutomationRun.automation_id, order_by=TonAutomationRun.created_at.desc())
            .label("position"),
        )
        .where(TonAutomationRun.automation_id.in_(list(automation_ids)))
    )
    if since is not None:
        ranked = ranked.where(TonAutomationRun.created_at >= since)
    subquery = ranked.subquery()
    rows = session.scalars(
        sa.select(TonAutomationRun)
        .join(subquery, subquery.c.id == TonAutomationRun.id)
        .where(subquery.c.position <= per_automation)
        .options(defer(TonAutomationRun.trigger_output))
        .order_by(TonAutomationRun.created_at.desc())
    ).all()
    result: dict[UUID, list[TonAutomationRun]] = {}
    for run in rows:
        result.setdefault(run.automation_id, []).append(run)
    return result


def run_counts(session: Session, automation_ids: Sequence[UUID], since: datetime.datetime) -> dict[UUID, dict[str, int]]:
    if not automation_ids:
        return {}
    rows = session.execute(
        sa.select(TonAutomationRun.automation_id, TonAutomationRun.status, sa.func.count())
        .where(
            TonAutomationRun.automation_id.in_(list(automation_ids)),
            TonAutomationRun.created_at >= since,
            TonAutomationRun.mode != RunMode.TEST.value,
        )
        .group_by(TonAutomationRun.automation_id, TonAutomationRun.status)
    ).all()
    result: dict[UUID, dict[str, int]] = {}
    for automation_id, status, count in rows:
        result.setdefault(automation_id, {})[status] = int(count)
    return result


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def step_rows(session: Session, run_id: UUID) -> list[TonAutomationStepRun]:
    return list(
        session.scalars(
            sa.select(TonAutomationStepRun)
            .where(TonAutomationStepRun.run_id == run_id)
            .order_by(TonAutomationStepRun.started_at.nulls_last(), TonAutomationStepRun.node_id)
        )
    )


def upsert_step__no_commit(session: Session, run_id: UUID, values: dict[str, Any]) -> None:
    row = {"run_id": run_id, **values}
    update = {key: value for key, value in row.items() if key not in ("run_id", "node_id", "iteration")}
    session.execute(
        insert(TonAutomationStepRun)
        .values(**row)
        .on_conflict_do_update(constraint="uq_ton_automation_step_run", set_=update)
    )


def get_step(session: Session, run_id: UUID, node_id: str, iteration: str) -> TonAutomationStepRun | None:
    return session.scalar(
        sa.select(TonAutomationStepRun).where(
            TonAutomationStepRun.run_id == run_id,
            TonAutomationStepRun.node_id == node_id,
            TonAutomationStepRun.iteration == iteration,
        )
    )


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


def create_approval__no_commit(session: Session, **values: Any) -> TonAutomationApproval:
    approval = TonAutomationApproval(status="PENDING", **values)
    session.add(approval)
    session.flush()
    return approval


def get_approval(session: Session, approval_id: UUID) -> TonAutomationApproval:
    approval = session.get(TonAutomationApproval, approval_id)
    if approval is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Aprovação não encontrada")
    return approval


def pending_approvals(session: Session) -> list[tuple[TonAutomationApproval, TonAutomation]]:
    rows = session.execute(
        sa.select(TonAutomationApproval, TonAutomation)
        .join(TonAutomation, TonAutomation.id == TonAutomationApproval.automation_id)
        .where(TonAutomationApproval.status == "PENDING")
        .order_by(TonAutomationApproval.created_at)
    ).all()
    return [(row[0], row[1]) for row in rows]


def cancel_approvals__no_commit(
    session: Session, now: datetime.datetime, *, run_id: UUID | None = None, automation_id: UUID | None = None
) -> None:
    query = sa.update(TonAutomationApproval).where(TonAutomationApproval.status == "PENDING")
    if run_id is not None:
        query = query.where(TonAutomationApproval.run_id == run_id)
    if automation_id is not None:
        query = query.where(TonAutomationApproval.automation_id == automation_id)
    session.execute(query.values(status="CANCELLED", decided_at=now))


# ---------------------------------------------------------------------------
# Notices and files
# ---------------------------------------------------------------------------


def add_notice__no_commit(
    session: Session,
    *,
    automation_id: str,
    run_id: str,
    title: str,
    message: str,
    severity: str,
    link: str | None,
    is_test: bool,
) -> TonAutomationNotice:
    notice = TonAutomationNotice(
        automation_id=UUID(automation_id),
        run_id=UUID(run_id) if run_id else None,
        title=title,
        message=message or None,
        severity=severity if severity in ("INFO", "WARNING", "CRITICAL") else "INFO",
        link=link,
        is_test=is_test,
    )
    session.add(notice)
    return notice


def recent_notices(session: Session, limit: int = 30) -> list[tuple[TonAutomationNotice, str]]:
    rows = session.execute(
        sa.select(TonAutomationNotice, TonAutomation.name)
        .join(TonAutomation, TonAutomation.id == TonAutomationNotice.automation_id)
        .where(TonAutomationNotice.is_test.is_(False))
        .order_by(TonAutomationNotice.created_at.desc())
        .limit(limit)
    ).all()
    return [(row[0], row[1]) for row in rows]


def create_file__no_commit(session: Session, user: User, *, name: str, content_type: str, data: bytes) -> TonAutomationFile:
    stored = TonAutomationFile(
        name=name[:200],
        content_type=content_type[:120],
        size_bytes=len(data),
        data=data,
        created_by=user.id,
    )
    session.add(stored)
    session.flush()
    return stored


def get_file(session: Session, file_id: str) -> TonAutomationFile | None:
    try:
        return session.get(TonAutomationFile, UUID(file_id))
    except ValueError:
        return None


def user_emails(session: Session, user_ids: Sequence[UUID | None]) -> dict[UUID, str]:
    ids = [user_id for user_id in user_ids if user_id]
    if not ids:
        return {}
    return dict(session.execute(sa.select(User.id, User.email).where(User.id.in_(ids))).all())  # type: ignore[call-overload,attr-defined,arg-type]
