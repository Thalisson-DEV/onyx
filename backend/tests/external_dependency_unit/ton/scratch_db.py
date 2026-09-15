"""Disposable-database helpers for TON schema and domain tests.

The shared ``db_session`` fixture points at the running development database,
which Plan 003a deliberately left un-migrated. TON DB behaviour is therefore
verified against throwaway databases built from the repository migrations, and
the running database is never read for schema evidence and never written to.

Every test database is created from a template that was migrated once, so a
module pays the base-to-head cost a single time rather than per test. The same
approach as ``test_provider_secret_encryption.py``, lifted into a shared module
now that two TON test files need it.

Requires ``cwd`` to be ``backend/``: ``alembic.ini`` and ``script_location`` are
relative paths, matching how the repository runs Alembic.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from onyx.db.engine.shard_registry import ALEMBIC_TARGET_URL_ATTRIBUTE
from onyx.db.engine.sql_engine import SYNC_DB_API, build_connection_string

# Plan 003b's revision and the 003a head it chains from.
REVISION_003B = "faee7eaa921e"
REVISION_003A = "714172b66b07"

# The nine tables Plan 003b introduces, in creation order. Used both to assert
# what the migration creates and to assert what its downgrade removes.
TON_003B_TABLES: tuple[str, ...] = (
    "ton_business_unit",
    "ton_contract",
    "ton_rule",
    "ton_rule_version",
    "ton_source_snapshot",
    "ton_analysis_run",
    "ton_analysis_run_rule_version",
    "ton_analysis_run__source_snapshot",
    "ton_analysis_step",
)


def admin_engine() -> Engine:
    """AUTOCOMMIT engine: CREATE/DROP DATABASE cannot run inside a transaction."""
    return create_engine(
        build_connection_string(db_api=SYNC_DB_API), isolation_level="AUTOCOMMIT"
    )


def create_database(name: str, template: str | None = None) -> None:
    engine = admin_engine()
    try:
        with engine.connect() as connection:
            statement = f'CREATE DATABASE "{name}"'
            if template is not None:
                statement += f' TEMPLATE "{template}"'
            connection.execute(text(statement))
    finally:
        engine.dispose()


def drop_database(name: str) -> None:
    engine = admin_engine()
    try:
        with engine.connect() as connection:
            # Other backends must go first, or DROP DATABASE refuses — and a
            # template with a live connection cannot be cloned either.
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    finally:
        engine.dispose()


@contextmanager
def scratch_database(template: str | None = None) -> Iterator[str]:
    """Yield a throwaway database name, dropped afterwards."""
    name = f"onyx_ton_003b_{uuid4().hex[:12]}"
    create_database(name, template=template)
    try:
        yield name
    finally:
        drop_database(name)


def alembic_config(database: str) -> AlembicConfig:
    config = AlembicConfig("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.attributes[ALEMBIC_TARGET_URL_ATTRIBUTE] = build_connection_string(
        db=database
    )
    config.attributes["configure_logger"] = False
    return config


def upgrade(database: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(database), revision)


def downgrade(database: str, revision: str) -> None:
    command.downgrade(alembic_config(database), revision)


def sync_engine(database: str) -> Engine:
    return create_engine(build_connection_string(db_api=SYNC_DB_API, db=database))


@contextmanager
def scratch_session(database: str) -> Iterator[Session]:
    """A plain Session on *database*, with its engine disposed afterwards.

    Deliberately not the application's ``get_session_with_current_tenant``: that
    resolves the configured deployment database, which is exactly what these
    tests must not touch.
    """
    engine = sync_engine(database)
    try:
        with sessionmaker(bind=engine, expire_on_commit=False)() as session:
            yield session
    finally:
        engine.dispose()


def table_names(database: str, prefix: str | None = None) -> set[str]:
    engine = sync_engine(database)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            ).all()
    finally:
        engine.dispose()
    names = {str(row[0]) for row in rows}
    if prefix is None:
        return names
    return {name for name in names if name.startswith(prefix)}


def column_names(database: str, table: str) -> set[str]:
    engine = sync_engine(database)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :table"
                ),
                {"table": table},
            ).all()
    finally:
        engine.dispose()
    return {str(row[0]) for row in rows}


def query_all(
    database: str, sql: str, params: dict[str, Any] | None = None
) -> list[Any]:
    engine = sync_engine(database)
    try:
        with engine.connect() as connection:
            return list(connection.execute(text(sql), params or {}).all())
    finally:
        engine.dispose()
