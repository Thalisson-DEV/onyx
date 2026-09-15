"""Shared fixtures for TON database tests.

The template database is built once per session and cloned per test, so the
base-to-head migration chain replays a single time. Cloning is cheap; replaying
444 revisions per test is not.
"""

from collections.abc import Generator, Iterator
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from tests.external_dependency_unit.ton.scratch_db import (
    create_database,
    drop_database,
    scratch_database,
    scratch_session,
    upgrade,
)


@pytest.fixture(scope="session")
def ton_head_template() -> Generator[str, None, None]:
    """A database migrated to the current head, used as a clone source."""
    name = f"onyx_ton_003b_tmpl_{uuid4().hex[:8]}"
    create_database(name)
    try:
        upgrade(name, "head")
        yield name
    finally:
        drop_database(name)


@pytest.fixture()
def ton_database(ton_head_template: str) -> Iterator[str]:
    """A throwaway database at head, dropped after the test."""
    with scratch_database(template=ton_head_template) as database:
        yield database


@pytest.fixture()
def ton_session(ton_database: str) -> Iterator[Session]:
    """A session on a throwaway database at head."""
    with scratch_session(ton_database) as session:
        yield session
