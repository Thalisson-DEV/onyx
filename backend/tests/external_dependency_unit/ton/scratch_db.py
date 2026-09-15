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

# The TON revision chain, oldest first.
REVISION_003A = "714172b66b07"
REVISION_003B = "faee7eaa921e"
REVISION_003C = "6b0ca4eb29fb"
REVISION_003D = "440b8984f851"

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

# The twelve tables Plan 003c introduces, in creation order.
TON_003C_TABLES: tuple[str, ...] = (
    "ton_occurrence",
    "ton_finding",
    "ton_finding_evidence",
    "ton_finding_interpretation",
    "ton_occurrence_event",
    "ton_occurrence_impact",
    "ton_occurrence_assignment",
    "ton_occurrence_note",
    "ton_occurrence_impacted_domain",
    "ton_business_unit__user_group",
    "ton_contract__user_group",
    "ton_occurrence__user_group",
)

# The nine tables Plan 003d introduces, in creation order. ``ton_report__user_group``
# is the fourth ACL junction, deferred from 003c because ``ton_report`` did not
# exist yet (decision D-043).
TON_003D_TABLES: tuple[str, ...] = (
    "ton_report",
    "ton_report_revision",
    "ton_report_revision__analysis_run",
    "ton_report_revision__occurrence",
    "ton_report_revision__finding",
    "ton_report_revision__rule_version",
    "ton_report_revision__source_snapshot",
    "ton_report__user_group",
    "ton_audit_event",
)

# The five join tables that pin a revision's inputs. Named separately because the
# reproducibility assertions walk them as a set.
TON_REPORT_LINK_TABLES: tuple[str, ...] = (
    "ton_report_revision__analysis_run",
    "ton_report_revision__occurrence",
    "ton_report_revision__finding",
    "ton_report_revision__rule_version",
    "ton_report_revision__source_snapshot",
)

# Every TON table that exists at head. The inverse assertions run over this set,
# so a new table cannot escape the no-``is_public`` and no-source-write checks by
# being added to a later slice's list only.
TON_TABLES_AT_HEAD: tuple[str, ...] = (
    TON_003B_TABLES + TON_003C_TABLES + TON_003D_TABLES
)

OCCURRENCE_SHORT_CODE_SEQUENCE = "ton_occurrence_short_code_seq"


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
    name = f"onyx_ton_{uuid4().hex[:12]}"
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


def sequence_exists(database: str, name: str) -> bool:
    """Whether a PostgreSQL sequence exists in the public schema."""
    rows = query_all(
        database,
        "SELECT count(*) FROM pg_class WHERE relkind = 'S' AND relname = :name",
        {"name": name},
    )
    return bool(rows[0][0])


def constraint_names(database: str, table: str) -> set[str]:
    """Every constraint name on *table*, whatever its kind."""
    rows = query_all(
        database,
        "SELECT conname FROM pg_constraint "
        "JOIN pg_class ON pg_class.oid = pg_constraint.conrelid "
        "WHERE pg_class.relname = :table",
        {"table": table},
    )
    return {str(row[0]) for row in rows}


def column_types(database: str, table: str) -> dict[str, str]:
    """Column name to SQL type for *table*.

    Used to assert that no monetary column is a floating-point type: the check
    has to read the built schema, because a model annotation cannot prove what the
    migration actually created.
    """
    rows = query_all(
        database,
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = :table",
        {"table": table},
    )
    return {str(row[0]): str(row[1]) for row in rows}
