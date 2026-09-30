"""Read-only queries for the client financial source catalog."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton.models import (
    ImportProfileExecution,
    ImportRun,
    ReviewRun,
    Source,
    SourceSnapshot,
)
from onyx.db.ton.sources import get_source, source_access_clause
from onyx.ton.financial_review.models import ReviewRunStatus
from onyx.ton.sources.models import ImportStatus


def visible_source(session: Session, user: User, key: str) -> Source | None:
    return session.scalar(
        sa.select(Source).where(
            Source.key == key,
            source_access_clause(user, Permission.READ_TON_SOURCES),
        )
    )


def source_by_key_for_import(session: Session, user: User, key: str) -> Source | None:
    return session.scalar(
        sa.select(Source).where(
            Source.key == key,
            source_access_clause(user, Permission.IMPORT_TON_SOURCES),
        )
    )


def import_history(
    session: Session, user: User, source_id: UUID, limit: int = 20
) -> list[tuple[ImportProfileExecution, SourceSnapshot]]:
    get_source(session, user, source_id)
    return list(
        session.execute(
            sa.select(ImportProfileExecution, SourceSnapshot)
            .join(
                SourceSnapshot,
                SourceSnapshot.id == ImportProfileExecution.snapshot_id,
            )
            .where(ImportProfileExecution.source_id == source_id)
            .order_by(
                ImportProfileExecution.started_at.desc(),
                ImportProfileExecution.id.desc(),
            )
            .limit(limit)
        ).all()
    )


def last_successful_at(
    session: Session, user: User, source_id: UUID
) -> datetime | None:
    get_source(session, user, source_id)
    return session.scalar(
        sa.select(ImportProfileExecution.finished_at)
        .where(
            ImportProfileExecution.source_id == source_id,
            ImportProfileExecution.status.in_(("SUCCEEDED", "PARTIAL")),
        )
        .order_by(
            ImportProfileExecution.finished_at.desc(),
            ImportProfileExecution.id.desc(),
        )
        .limit(1)
    )


def import_detail(
    session: Session, user: User, source_id: UUID, execution_id: UUID
) -> tuple[ImportProfileExecution, SourceSnapshot] | None:
    get_source(session, user, source_id)
    return session.execute(
        sa.select(ImportProfileExecution, SourceSnapshot)
        .join(SourceSnapshot, SourceSnapshot.id == ImportProfileExecution.snapshot_id)
        .where(
            ImportProfileExecution.source_id == source_id,
            ImportProfileExecution.id == execution_id,
        )
    ).one_or_none()


def successful_review(
    session: Session, user: User, source_id: UUID, execution_id: UUID
) -> ReviewRun | None:
    get_source(session, user, source_id, Permission.IMPORT_TON_SOURCES)
    return session.scalar(
        sa.select(ReviewRun)
        .where(
            ReviewRun.source_id == source_id,
            ReviewRun.execution_id == execution_id,
            ReviewRun.status == ReviewRunStatus.SUCCEEDED,
        )
        .order_by(ReviewRun.finished_at.desc(), ReviewRun.id.desc())
        .limit(1)
    )


def failed_captures(
    session: Session, user: User, source_id: UUID, limit: int = 20
) -> list[ImportRun]:
    get_source(session, user, source_id)
    return list(
        session.scalars(
            sa.select(ImportRun)
            .where(
                ImportRun.source_id == source_id,
                ImportRun.status == ImportStatus.FAILED,
            )
            .order_by(ImportRun.started_at.desc(), ImportRun.id.desc())
            .limit(limit)
        )
    )


def failed_capture_detail(
    session: Session, user: User, source_id: UUID, run_id: UUID
) -> ImportRun | None:
    get_source(session, user, source_id)
    return session.scalar(
        sa.select(ImportRun).where(
            ImportRun.source_id == source_id,
            ImportRun.id == run_id,
            ImportRun.status == ImportStatus.FAILED,
        )
    )
