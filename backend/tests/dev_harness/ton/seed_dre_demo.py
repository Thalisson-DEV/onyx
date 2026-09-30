"""Populate the isolated local DRE demo database with synthetic evidence."""

import datetime
import os
from io import BytesIO
from unittest.mock import Mock

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import dre
from onyx.db.ton.models import Source
from onyx.file_store.file_store import FileStore
from onyx.ton.dre.models import (
    DreAccountAssignment,
    DreScope,
    DreStructureCreate,
    DreVersionCreate,
)
from tests.external_dependency_unit.ton.scratch_db import scratch_session
from tests.external_dependency_unit.ton.test_dre import _lines
from tests.external_dependency_unit.ton.test_financial_domain import (
    build_complete_synthetic_scope,
)

DEMO_DATABASE = "onyx_dre_demo"
DEMO_EMAIL = "admin_user@example.com"
PERIOD = datetime.date(2026, 1, 1)


def synthetic_store() -> FileStore:
    blobs: dict[str, bytes] = {}
    store = Mock(spec=FileStore)

    def save(content: BytesIO, *, file_id: str, **_kwargs: object) -> str:
        blobs[file_id] = content.read()
        return file_id

    store.save_file.side_effect = save
    store.read_file.side_effect = lambda key: BytesIO(blobs[key])
    store.delete_file.side_effect = lambda key, **_kwargs: blobs.pop(key, None)
    return store


def seed(session: Session, admin: User) -> None:
    if session.scalar(sa.select(sa.func.count()).select_from(Source)):
        raise RuntimeError("Demo database already has sources")
    normalization_id, account_id, unit_id = build_complete_synthetic_scope(
        session, admin, synthetic_store()
    )
    assignments = [
        DreAccountAssignment(
            account_id=account_id, line_code="service", status="APPROVED"
        )
    ]
    ready_version = dre.create_structure(
        session,
        admin,
        DreStructureCreate(
            key="demo-01-ready",
            label="Demonstração sintética: DRE pronta",
            lines=_lines(),
            assignments=assignments,
            reason="Synthetic local demo",
        ),
    )
    session.commit()
    for scope_unit_id in (None, unit_id):
        first = dre.execute(
            session,
            admin,
            DreScope(
                normalization_run_id=normalization_id,
                structure_version_id=ready_version.id,
                period=PERIOD,
                unit_id=scope_unit_id,
            ),
        )
        assert first.status == "READY"
    renamed_lines = _lines()
    renamed_lines[1].label = "Serviço sintético revisado"
    latest_version = dre.create_version(
        session,
        admin,
        ready_version.structure_id,
        DreVersionCreate(
            lines=renamed_lines,
            assignments=assignments,
            reason="Synthetic historical revision",
        ),
    )
    session.commit()
    for scope_unit_id in (None, unit_id):
        current = dre.execute(
            session,
            admin,
            DreScope(
                normalization_run_id=normalization_id,
                structure_version_id=latest_version.id,
                period=PERIOD,
                unit_id=scope_unit_id,
            ),
        )
        assert current.status == "READY"
    blocked_version = dre.create_structure(
        session,
        admin,
        DreStructureCreate(
            key="demo-02-blocked",
            label="Demonstração sintética: pendências",
            lines=_lines(),
            reason="Synthetic blocked scope",
        ),
    )
    session.commit()
    blocked = dre.execute(
        session,
        admin,
        DreScope(
            normalization_run_id=normalization_id,
            structure_version_id=blocked_version.id,
            period=PERIOD,
            unit_id=None,
        ),
    )
    assert blocked.status == "NOT_READY"
    print("Seeded synthetic READY and NOT_READY scopes in", DEMO_DATABASE)


def main() -> None:
    if os.environ.get("TON_DRE_DEMO_SEED") != "1":
        raise RuntimeError("Set TON_DRE_DEMO_SEED=1")
    if os.environ.get("POSTGRES_DB") != DEMO_DATABASE:
        raise RuntimeError("Seeder only accepts the isolated demo database")
    host = os.environ.get("POSTGRES_HOST")
    local_hosts = {"localhost", "127.0.0.1"}
    if os.path.exists("/.dockerenv"):
        local_hosts.add("relational_db")
    if host not in local_hosts:
        raise RuntimeError("Seeder only accepts a local PostgreSQL host")
    with scratch_session(DEMO_DATABASE) as session:
        admin = session.scalar(sa.select(User).where(User.email == DEMO_EMAIL))
        if admin is None:
            raise RuntimeError("Register the demo administrator before seeding")
        seed(session, admin)


if __name__ == "__main__":
    main()
