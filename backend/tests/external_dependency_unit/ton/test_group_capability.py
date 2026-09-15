"""TON Plan 008a — the Groups capability against a real PostgreSQL, with no license.

`tests/unit/ton/test_capability_gates.py` proves the commercial gate is gone and
the authorization gates are intact. This suite proves the capability actually
works end to end in the data layer under the intended TON deployment state:

- no license row exists;
- the EE implementation tree is loaded, so document ACLs are group-aware;
- an administrator configures a group and its permission grants, and members
  gain exactly the granted tokens;
- a scoped group manager acts only inside the groups they manage;
- group membership reaches the document access filter.

Every call goes through the production EE DB functions. Nothing here touches a
tier, a license, Redis or any Onyx-operated service.

Run against a disposable PostgreSQL, never a live deployment database:

    POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=<disposable> \\
      pytest backend/tests/external_dependency_unit/ton/test_group_capability.py
"""

from collections.abc import Callable, Generator, Iterator
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from ee.onyx.db.user_group import (
    add_users_to_user_group,
    fetch_user_group,
    insert_user_group,
    make_group_manager,
    set_group_permissions_bulk__no_commit,
)
from ee.onyx.server.user_group.models import UserGroupCreate
from onyx.access.access import get_acl_for_user
from onyx.access.utils import prefix_user_email, prefix_user_group
from onyx.configs.constants import PUBLIC_DOC_PAT
from onyx.db.enums import Permission
from onyx.db.models import PermissionGrant, User, User__UserGroup, UserGroup
from onyx.db.permissions import recompute_user_permissions__no_commit
from onyx.error_handling.exceptions import OnyxError
from onyx.utils.variable_functionality import (
    fetch_versioned_implementation,
    global_version,
)
from tests.external_dependency_unit.conftest import create_test_user, delete_test_user


@pytest.fixture(autouse=True)
def ee_dispatch_active() -> Iterator[None]:
    """TON boots with `LICENSE_ENFORCEMENT_ENABLED` at its true default, which
    loads the EE tree. Reproduce that here and restore the process afterwards;
    `fetch_versioned_implementation` is lru_cached, so clear it on both sides."""
    was_ee = global_version.is_ee_version()
    fetch_versioned_implementation.cache_clear()
    global_version.set_ee()
    try:
        yield
    finally:
        if not was_ee:
            global_version.unset_ee()
        fetch_versioned_implementation.cache_clear()


GroupFactory = Callable[[str], UserGroup]


@pytest.fixture
def group_factory(db_session: Session) -> Generator[GroupFactory, None, None]:
    """Create groups through the production insert path and remove them after."""
    created: list[int] = []

    def make(name_prefix: str) -> UserGroup:
        group = insert_user_group(
            db_session,
            UserGroupCreate(
                name=f"{name_prefix}-{uuid4().hex[:8]}", user_ids=[], cc_pair_ids=[]
            ),
        )
        # The document-index sync task normally flips this. Nothing in this suite
        # runs Celery, and membership edits refuse a syncing group.
        group.is_up_to_date = True
        db_session.commit()
        created.append(group.id)
        return group

    yield make

    for group_id in created:
        db_session.execute(
            delete(User__UserGroup).where(User__UserGroup.user_group_id == group_id)
        )
        db_session.execute(
            delete(PermissionGrant).where(PermissionGrant.group_id == group_id)
        )
        db_session.execute(delete(UserGroup).where(UserGroup.id == group_id))
    db_session.commit()


def _add_member(db_session: Session, group_id: int, user: User) -> None:
    db_session.add(User__UserGroup(user_id=user.id, user_group_id=group_id))
    db_session.flush()
    recompute_user_permissions__no_commit([user.id], db_session)
    db_session.commit()
    db_session.refresh(user)


def test_deployment_has_no_license_row(db_session: Session) -> None:
    """States the premise for everything below: the capability is exercised with
    zero paid Onyx entitlement."""
    license_count = db_session.execute(
        text("select count(*) from license")
    ).scalar_one()
    assert license_count == 0


def test_admin_configures_group_and_member_gains_exactly_granted_permissions(
    db_session: Session, group_factory: GroupFactory
) -> None:
    """Group create, permission grant and membership, through the production DB
    layer. The member must end up with the granted tokens and nothing else."""
    admin = create_test_user(db_session, "ton-admin", is_admin=True)
    member = create_test_user(db_session, "ton-controladoria")
    group = group_factory("controladoria")

    try:
        change = set_group_permissions_bulk__no_commit(
            group_id=group.id,
            desired_permissions={
                Permission.MANAGE_DOCUMENT_SETS,
                Permission.MANAGE_AGENTS,
            },
            granted_by=admin.id,
            db_session=db_session,
        )
        db_session.commit()

        assert set(change.added) == {
            Permission.MANAGE_DOCUMENT_SETS,
            Permission.MANAGE_AGENTS,
        }
        assert Permission.BASIC_ACCESS in change.enabled

        _add_member(db_session, group.id, member)

        granted = set(member.effective_permissions)
        assert Permission.MANAGE_DOCUMENT_SETS.value in granted
        assert Permission.MANAGE_AGENTS.value in granted
        # No amplification: the group never granted full admin.
        assert Permission.FULL_ADMIN_PANEL_ACCESS.value not in granted

        # Revoking one grant narrows the member again.
        set_group_permissions_bulk__no_commit(
            group_id=group.id,
            desired_permissions={Permission.MANAGE_DOCUMENT_SETS},
            granted_by=admin.id,
            db_session=db_session,
        )
        db_session.commit()
        db_session.refresh(member)
        assert Permission.MANAGE_AGENTS.value not in member.effective_permissions
        assert Permission.MANAGE_DOCUMENT_SETS.value in member.effective_permissions
    finally:
        delete_test_user(db_session, admin, member)
        db_session.commit()


def test_scoped_manager_adds_users_only_inside_a_managed_group(
    db_session: Session, group_factory: GroupFactory
) -> None:
    """GATE 2 in the DB layer. A manager of one group must not reach another."""
    managed = group_factory("frota")
    unmanaged = group_factory("contratos")
    manager = create_test_user(db_session, "ton-gestor")
    newcomer = create_test_user(db_session, "ton-operacional")

    try:
        _add_member(db_session, managed.id, manager)
        make_group_manager(db_session, manager.id, managed.id)
        recompute_user_permissions__no_commit([manager.id], db_session)
        db_session.commit()
        db_session.refresh(manager)
        assert manager.is_group_manager is True
        # Scoped only: the manager holds no global groups token.
        assert Permission.MANAGE_USER_GROUPS.value not in manager.effective_permissions

        add_users_to_user_group(
            db_session=db_session,
            user=manager,
            user_group_id=managed.id,
            user_ids=[newcomer.id],
        )
        db_session.commit()
        refreshed = fetch_user_group(db_session, managed.id)
        assert refreshed is not None
        assert newcomer.id in {member.id for member in refreshed.users}

        with pytest.raises(OnyxError):
            add_users_to_user_group(
                db_session=db_session,
                user=manager,
                user_group_id=unmanaged.id,
                user_ids=[newcomer.id],
            )
        db_session.rollback()

        out_of_scope = db_session.execute(
            select(func.count())
            .select_from(User__UserGroup)
            .where(
                User__UserGroup.user_group_id == unmanaged.id,
                User__UserGroup.user_id == newcomer.id,
            )
        ).scalar_one()
        assert out_of_scope == 0
    finally:
        delete_test_user(db_session, manager, newcomer)
        db_session.commit()


def test_plain_member_cannot_edit_group_membership(
    db_session: Session, group_factory: GroupFactory
) -> None:
    """Group membership alone is never authority. Only a manager edge is."""
    group = group_factory("leitura")
    member = create_test_user(db_session, "ton-leitura")
    other = create_test_user(db_session, "ton-outsider")

    try:
        _add_member(db_session, group.id, member)
        assert member.is_group_manager is False

        with pytest.raises(OnyxError):
            add_users_to_user_group(
                db_session=db_session,
                user=member,
                user_group_id=group.id,
                user_ids=[other.id],
            )
        db_session.rollback()
    finally:
        delete_test_user(db_session, member, other)
        db_session.commit()


def test_group_membership_reaches_the_document_access_filter(
    db_session: Session, group_factory: GroupFactory
) -> None:
    """The invariant the whole slice puts at risk: `user -> group membership ->
    group ACL`. A member's ACL must name the group; a non-member's must not.
    Public and per-email entries stay exactly as they were."""
    group = group_factory("acl-unit")
    member = create_test_user(db_session, "ton-acl-member")
    stranger = create_test_user(db_session, "ton-acl-stranger")

    try:
        _add_member(db_session, group.id, member)

        member_acl = get_acl_for_user(member, db_session)
        stranger_acl = get_acl_for_user(stranger, db_session)

        assert prefix_user_group(group.name) in member_acl
        assert prefix_user_group(group.name) not in stranger_acl

        # Unchanged CE behavior alongside the group entry.
        assert prefix_user_email(member.email) in member_acl
        assert PUBLIC_DOC_PAT in member_acl
        assert prefix_user_email(stranger.email) in stranger_acl
        assert PUBLIC_DOC_PAT in stranger_acl

        # A group ACL is not a wildcard: the member does not inherit the
        # stranger's per-email entry.
        assert prefix_user_email(stranger.email) not in member_acl
    finally:
        delete_test_user(db_session, member, stranger)
        db_session.commit()


def test_acl_computation_runs_the_ee_implementation() -> None:
    """If this resolves to the CE module, group restrictions silently disappear
    from the index-level access filter."""
    resolved = fetch_versioned_implementation("onyx.access.access", "_get_acl_for_user")
    assert resolved.__module__ == "ee.onyx.access.access"
