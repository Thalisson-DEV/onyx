"""TON report ACL spec — Plan 003d.

The fourth junction, on the same fail-closed contract 003c established for
occurrences. Real PostgreSQL is required because the predicates are SQL: an
``EXISTS`` over ``ton_report__user_group``, a ``NOT IN`` over a managed-group
subquery, and a ``FOR UPDATE`` re-read inside the write gate.

The two properties that fail quietly get the most attention:

* **Zero junction rows means DENIED.** Several cases here differ from a passing
  case only by the absence of one junction row.
* **The direct-id path denies exactly like the list path.** A filtered list beside
  an unfiltered detail fetch is the classic ACL failure, so every denial case
  asserts both.

Nothing here needs a licence, a tier or an Enterprise Edition code path, and
``TestCommunityResolution`` proves the report write path works with the versioned
dispatch resolved to Community — the trap readiness §10 flags, where a CE-resolved
worker writes no junction rows and every report silently becomes invisible.

Run with::

    cd backend && uv run pytest tests/external_dependency_unit/ton/test_ton_report_acl.py
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from onyx.auth.permissions import (
    PERMISSION_REGISTRY,
    SCOPED_MANAGER_PERMISSIONS,
    SCOPED_MANAGER_PERMISSIONS_EXPANDED,
)
from onyx.db.enums import Permission, PermissionAuthority
from onyx.db.models import User, UserGroup
from onyx.db.ton.acl import (
    assert_can_delete_report,
    assert_can_manage_report,
    fetch_report_revisions_for_user,
    fetch_reports_for_user,
    get_report_for_user,
    get_report_revision_for_user,
    holds_ton_report_manage_capability,
    holds_ton_report_read_capability,
    is_ton_administrator,
    report_group_ids,
    set_report_groups__no_commit,
    ton_permission_authority,
    user_report_share_permission,
)
from onyx.db.ton.enums import TonSharePermission
from onyx.db.ton.models import BusinessUnit, TonReport, TonReportRevision
from onyx.error_handling.exceptions import OnyxError
from onyx.utils.variable_functionality import (
    fetch_versioned_implementation,
    global_version,
)
from tests.external_dependency_unit.ton import factories

REPORT_TOKENS: tuple[Permission, ...] = (
    Permission.READ_TON_REPORTS,
    Permission.MANAGE_TON_REPORTS,
)


class _Case:
    """One report with a published revision, plus its organizational context."""

    def __init__(self, db_session: Session, *, with_unit: bool = True):
        self.unit: BusinessUnit | None = (
            factories.make_business_unit(db_session) if with_unit else None
        )
        self.report: TonReport = factories.make_report(
            db_session, business_unit=self.unit
        )
        self.revision: TonReportRevision = factories.publish_synthetic_revision(
            db_session, report=self.report
        )
        db_session.flush()


def _authorize_whole_chain(
    db_session: Session,
    *,
    group: UserGroup,
    case: _Case,
    permission: TonSharePermission = TonSharePermission.VIEWER,
) -> None:
    """Grant the group the report *and* its owning unit.

    Visibility is the conjunction of both: the resource ACL plus authorization for
    the business unit the report names. A test granting only the report row would
    be asserting a different rule.
    """
    factories.authorize_group(
        db_session,
        group=group,
        report=case.report,
        business_unit=case.unit,
        permission=permission,
    )


def _reader(db_session: Session, *, group: UserGroup, manage: bool = False) -> User:
    """A user in *group*, holding the TON report read (or manage) token."""
    factories.grant_permissions(
        db_session,
        group=group,
        permissions=[
            Permission.MANAGE_TON_REPORTS if manage else Permission.READ_TON_REPORTS
        ],
    )
    user = factories.make_user(db_session)
    factories.add_member(db_session, group=group, user=user)
    return user


class TestPermissionTokens:
    def test_the_two_003d_tokens_exist(self) -> None:
        assert Permission.READ_TON_REPORTS.value == "read:ton_reports"
        assert Permission.MANAGE_TON_REPORTS.value == "manage:ton_reports"

    def test_manage_implies_read(self) -> None:
        from onyx.auth.permissions import IMPLIED_PERMISSIONS

        implied = IMPLIED_PERMISSIONS[Permission.MANAGE_TON_REPORTS.value]
        assert Permission.READ_TON_REPORTS.value in implied

    def test_both_tokens_are_grantable_through_the_registry(self) -> None:
        registered = {
            permission
            for entry in PERMISSION_REGISTRY
            for permission in entry.permissions
        }
        for token in REPORT_TOKENS:
            assert token in registered

    def test_neither_token_is_scopable(self) -> None:
        """The documented decision: both report tokens are GLOBAL-or-NONE
        capability tokens. Group-manager scope is a different axis from a TON
        share level, and overlapping them would let managing a group confer
        authority over reports merely shared with it."""
        for token in REPORT_TOKENS:
            assert token not in SCOPED_MANAGER_PERMISSIONS
            assert token.value not in SCOPED_MANAGER_PERMISSIONS_EXPANDED

    def test_a_report_token_never_resolves_scoped_authority(
        self, ton_session: Session
    ) -> None:
        group = factories.make_group(ton_session)
        manager = factories.make_user(ton_session)
        factories.add_member(ton_session, group=group, user=manager, is_manager=True)
        ton_session.commit()

        for token in REPORT_TOKENS:
            assert ton_permission_authority(manager, token) is PermissionAuthority.NONE

    def test_a_granted_token_resolves_global_authority(
        self, ton_session: Session
    ) -> None:
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        ton_session.commit()

        assert (
            ton_permission_authority(user, Permission.MANAGE_TON_REPORTS)
            is PermissionAuthority.GLOBAL
        )
        assert holds_ton_report_manage_capability(user)
        assert holds_ton_report_read_capability(user)

    def test_neither_token_is_implied(self) -> None:
        """An implied token is never persisted, so a TON capability must be an
        explicit grant."""
        for token in REPORT_TOKENS:
            assert token not in Permission.IMPLIED


class TestGlobalAdministrator:
    def test_an_administrator_reads_every_report(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        assert is_ton_administrator(admin)
        assert [item.id for item in fetch_reports_for_user(ton_session, admin)] == [
            case.report.id
        ]
        assert (
            get_report_for_user(ton_session, admin, case.report.id).id == case.report.id
        )

    def test_an_administrator_reads_a_report_with_no_junction_row(
        self, ton_session: Session
    ) -> None:
        """The bypass is what makes an unshared report administrable at all."""
        case = _Case(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        assert report_group_ids(ton_session, case.report.id) == set()
        assert fetch_reports_for_user(ton_session, admin)

    def test_holding_the_report_token_is_not_administrator_authority(
        self, ton_session: Session
    ) -> None:
        """Granting a group MANAGE_TON_REPORTS must not let it read every other
        unit's reports."""
        _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        ton_session.commit()

        assert not is_ton_administrator(user)
        assert fetch_reports_for_user(ton_session, user) == []


class TestFailClosedDefault:
    def test_zero_junction_rows_denies_a_permitted_group(
        self, ton_session: Session
    ) -> None:
        """The core invariant. No report is readable by default."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        ton_session.commit()

        assert report_group_ids(ton_session, case.report.id) == set()
        assert fetch_reports_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_report_for_user(ton_session, user, case.report.id)

    def test_one_junction_row_is_the_whole_difference(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        ton_session.commit()

        assert fetch_reports_for_user(ton_session, user) == []

        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        assert [item.id for item in fetch_reports_for_user(ton_session, user)] == [
            case.report.id
        ]

    def test_a_user_without_the_token_reads_nothing_even_when_shared(
        self, ton_session: Session
    ) -> None:
        """A junction row is necessary, not sufficient: the capability token is
        still required."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = factories.make_user(ton_session)
        factories.add_member(ton_session, group=group, user=user)
        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        assert not holds_ton_report_read_capability(user)
        assert fetch_reports_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_report_for_user(ton_session, user, case.report.id)

    def test_no_report_table_declares_a_permissive_visibility_column(self) -> None:
        """A column that does not exist cannot be short-circuited by future
        code."""
        forbidden = {"is_public", "public", "is_global", "public_permission"}
        for model in (TonReport, TonReportRevision):
            assert set(model.__table__.columns.keys()) & forbidden == set()

    def test_a_report_with_no_unit_still_needs_a_junction_row(
        self, ton_session: Session
    ) -> None:
        """A consolidated corporate report has no business unit, so the unit leg
        of the predicate passes. The resource ACL must still deny it."""
        case = _Case(ton_session, with_unit=False)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        ton_session.commit()

        assert case.report.business_unit_id is None
        assert fetch_reports_for_user(ton_session, user) == []


class TestCrossScopeDenial:
    def test_a_group_authorized_for_the_report_but_not_its_unit_is_denied(
        self, ton_session: Session
    ) -> None:
        """The organizational context leg. This is what keeps cross-unit denial
        holding even if a report junction row is created by mistake."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        factories.authorize_group(ton_session, group=group, report=case.report)
        ton_session.commit()

        assert report_group_ids(ton_session, case.report.id) == {group.id}
        assert fetch_reports_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_report_for_user(ton_session, user, case.report.id)

    def test_a_group_authorized_for_the_unit_but_not_the_report_is_denied(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        factories.authorize_group(ton_session, group=group, business_unit=case.unit)
        ton_session.commit()

        assert fetch_reports_for_user(ton_session, user) == []

    def test_an_unrelated_group_sees_nothing(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        authorized = factories.make_group(ton_session)
        _authorize_whole_chain(ton_session, group=authorized, case=case)

        outsider_group = factories.make_group(ton_session)
        outsider = _reader(ton_session, group=outsider_group)
        ton_session.commit()

        assert fetch_reports_for_user(ton_session, outsider) == []
        with pytest.raises(OnyxError):
            get_report_for_user(ton_session, outsider, case.report.id)

    def test_a_report_in_another_unit_stays_invisible(
        self, ton_session: Session
    ) -> None:
        mine = _Case(ton_session)
        theirs = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(ton_session, group=group, case=mine)
        ton_session.commit()

        visible = {item.id for item in fetch_reports_for_user(ton_session, user)}
        assert visible == {mine.report.id}
        with pytest.raises(OnyxError):
            get_report_for_user(ton_session, user, theirs.report.id)


class TestShareLevels:
    def test_a_viewer_reads(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        assert [item.id for item in fetch_reports_for_user(ton_session, user)] == [
            case.report.id
        ]
        assert (
            user_report_share_permission(
                ton_session, user=user, report_id=case.report.id
            )
            is TonSharePermission.VIEWER
        )

    def test_a_viewer_cannot_write(self, ton_session: Session) -> None:
        """A VIEWER share reads and nothing more, even with the manage token."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session, group=group, case=case, permission=TonSharePermission.VIEWER
        )
        ton_session.commit()

        assert fetch_reports_for_user(ton_session, user, editable=True) == []
        with pytest.raises(OnyxError):
            assert_can_manage_report(ton_session, user=user, report=case.report)

    def test_an_editor_within_scope_may_write(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session, group=group, case=case, permission=TonSharePermission.EDITOR
        )
        ton_session.commit()

        assert_can_manage_report(ton_session, user=user, report=case.report)
        assert [
            item.id for item in fetch_reports_for_user(ton_session, user, editable=True)
        ] == [case.report.id]
        assert (
            user_report_share_permission(
                ton_session, user=user, report_id=case.report.id
            )
            is TonSharePermission.EDITOR
        )

    def test_an_editor_without_the_manage_token_may_not_write(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(
            ton_session, group=group, case=case, permission=TonSharePermission.EDITOR
        )
        ton_session.commit()

        assert fetch_reports_for_user(ton_session, user, editable=True) == []
        with pytest.raises(OnyxError):
            assert_can_manage_report(ton_session, user=user, report=case.report)

    def test_no_share_level_reports_none(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        ton_session.commit()

        assert (
            user_report_share_permission(
                ton_session, user=user, report_id=case.report.id
            )
            is None
        )


class TestRevisionAccessDerivesFromTheReport:
    def test_a_revision_is_visible_when_its_report_is(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        assert [
            item.id for item in fetch_report_revisions_for_user(ton_session, user)
        ] == [case.revision.id]
        assert (
            get_report_revision_for_user(ton_session, user, case.revision.id).id
            == case.revision.id
        )

    def test_a_revision_is_denied_when_its_report_is(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        ton_session.commit()

        assert fetch_report_revisions_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_report_revision_for_user(ton_session, user, case.revision.id)

    def test_an_absent_revision_and_a_forbidden_one_raise_alike(
        self, ton_session: Session
    ) -> None:
        """Telling a caller that a revision exists but is not theirs already leaks
        the report."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        ton_session.commit()

        with pytest.raises(OnyxError) as forbidden:
            get_report_revision_for_user(ton_session, user, case.revision.id)
        with pytest.raises(OnyxError) as absent:
            get_report_revision_for_user(ton_session, user, uuid4())
        assert str(forbidden.value) == str(absent.value)

    def test_an_administrator_reads_every_revision(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        assert [
            item.id for item in fetch_report_revisions_for_user(ton_session, admin)
        ] == [case.revision.id]


class TestWriteGate:
    def test_an_unshared_report_is_writable_only_by_an_administrator(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        with pytest.raises(OnyxError):
            assert_can_manage_report(ton_session, user=user, report=case.report)
        assert_can_manage_report(ton_session, user=admin, report=case.report)

    def test_a_non_admin_cannot_widen_a_reports_groups(
        self, ton_session: Session
    ) -> None:
        """Reaching a report finance also sees, then adding a group finance cannot
        see, is not expressible."""
        case = _Case(ton_session)
        own_group = factories.make_group(ton_session)
        outside_group = factories.make_group(ton_session)
        user = _reader(ton_session, group=own_group, manage=True)
        _authorize_whole_chain(
            ton_session,
            group=own_group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        with pytest.raises(OnyxError):
            set_report_groups__no_commit(
                ton_session,
                user=user,
                report=case.report,
                group_permissions={
                    own_group.id: TonSharePermission.EDITOR,
                    outside_group.id: TonSharePermission.VIEWER,
                },
            )
        ton_session.rollback()

    def test_a_report_shared_beyond_the_callers_groups_is_not_writable(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        own_group = factories.make_group(ton_session)
        other_group = factories.make_group(ton_session)
        user = _reader(ton_session, group=own_group, manage=True)
        _authorize_whole_chain(
            ton_session,
            group=own_group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        factories.authorize_group(
            ton_session,
            group=other_group,
            report=case.report,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        with pytest.raises(OnyxError):
            assert_can_manage_report(ton_session, user=user, report=case.report)
        assert fetch_reports_for_user(ton_session, user, editable=True) == []

    def test_a_non_admin_cannot_orphan_a_report(self, ton_session: Session) -> None:
        """Removing the last authorization would hide the report behind the
        fail-closed default and lose the caller's own access with it."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session, group=group, case=case, permission=TonSharePermission.EDITOR
        )
        ton_session.commit()

        with pytest.raises(OnyxError):
            set_report_groups__no_commit(
                ton_session, user=user, report=case.report, group_permissions={}
            )
        ton_session.rollback()

    def test_an_administrator_may_share_a_report_with_any_group(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        set_report_groups__no_commit(
            ton_session,
            user=admin,
            report=case.report,
            group_permissions={group.id: TonSharePermission.EDITOR},
        )
        ton_session.commit()

        assert report_group_ids(ton_session, case.report.id) == {group.id}

    def test_replacing_the_group_set_removes_the_old_rows(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        first = factories.make_group(ton_session)
        second = factories.make_group(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        set_report_groups__no_commit(
            ton_session,
            user=admin,
            report=case.report,
            group_permissions={first.id: TonSharePermission.VIEWER},
        )
        set_report_groups__no_commit(
            ton_session,
            user=admin,
            report=case.report,
            group_permissions={second.id: TonSharePermission.EDITOR},
        )
        ton_session.commit()

        assert report_group_ids(ton_session, case.report.id) == {second.id}


class TestDeleteRequiresGlobalAuthority:
    def test_an_administrator_may_delete(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        assert_can_delete_report(ton_session, user=admin, report=case.report)

    def test_a_group_manager_may_not_delete(self, ton_session: Session) -> None:
        """``assert_global`` first, never an ``allow_scope`` shortcut on a delete
        path. A scoped manager resolves NONE for every TON token."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        manager = factories.make_user(ton_session)
        factories.add_member(ton_session, group=group, user=manager, is_manager=True)
        _authorize_whole_chain(
            ton_session, group=group, case=case, permission=TonSharePermission.EDITOR
        )
        ton_session.commit()

        with pytest.raises(OnyxError):
            assert_can_delete_report(ton_session, user=manager, report=case.report)

    def test_an_editor_within_scope_may_delete_but_an_outsider_may_not(
        self, ton_session: Session
    ) -> None:
        """Deleting a report destroys its published revisions, which are immutable
        evidence. The capability alone is not enough — resource scope is required
        too."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        editor = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session, group=group, case=case, permission=TonSharePermission.EDITOR
        )

        outsider_group = factories.make_group(ton_session)
        outsider = _reader(ton_session, group=outsider_group, manage=True)
        ton_session.commit()

        assert_can_delete_report(ton_session, user=editor, report=case.report)
        with pytest.raises(OnyxError):
            assert_can_delete_report(ton_session, user=outsider, report=case.report)


class TestCommunityResolution:
    """The CE trap readiness §10 flags, closed for reports too.

    If the report share-write path lived in an EE-only module, a CE-resolved
    worker would write no junction rows — and with the fail-closed default, every
    report would silently become invisible.
    """

    @pytest.fixture()
    def community_resolution(self) -> Iterator[None]:
        was_ee = global_version.is_ee_version()
        fetch_versioned_implementation.cache_clear()
        global_version.unset_ee()
        try:
            yield
        finally:
            if was_ee:
                global_version.set_ee()
            fetch_versioned_implementation.cache_clear()

    @pytest.mark.usefixtures("community_resolution")
    def test_report_acl_writes_work_with_community_implementations_resolved(
        self, ton_session: Session
    ) -> None:
        assert not global_version.is_ee_version()
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        set_report_groups__no_commit(
            ton_session,
            user=admin,
            report=case.report,
            group_permissions={group.id: TonSharePermission.EDITOR},
        )
        ton_session.commit()

        assert report_group_ids(ton_session, case.report.id) == {group.id}

    @pytest.mark.usefixtures("community_resolution")
    def test_report_acl_reads_work_with_community_implementations_resolved(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        assert [item.id for item in fetch_reports_for_user(ton_session, user)] == [
            case.report.id
        ]

    @pytest.mark.usefixtures("community_resolution")
    def test_publishing_a_revision_needs_no_licence(self, ton_session: Session) -> None:
        """Plan 008a established that a TON capability must not depend on edition
        or tier. Publishing is a Community-tree operation."""
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)
        ton_session.commit()

        assert revision.revision_no == 1


class TestNoSecondAuthorizationFramework:
    def test_the_report_acl_lives_in_the_003c_module(self) -> None:
        """Readiness forbids a second authorization mechanism. The report
        predicates are in the same module, composing the same primitives."""
        import inspect

        from onyx.db.ton import acl

        source = inspect.getsource(acl)
        assert "def report_visible_clause" in source
        assert "def report_editable_clause" in source
        assert "within_managed_scope_clause" in source

    def test_no_report_specific_acl_module_was_added(self) -> None:
        import importlib

        for name in ("onyx.db.ton.report_acl", "onyx.db.ton.report_permissions"):
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module(name)

    def test_the_report_junction_reuses_the_existing_share_enum(self) -> None:
        """Not a report-specific share level: the same ``TonSharePermission`` the
        other three junctions carry."""
        from sqlalchemy import Enum as SAEnum

        from onyx.db.ton.models import TonReport__UserGroup

        column_type = TonReport__UserGroup.__table__.columns["permission"].type
        assert isinstance(column_type, SAEnum)
        assert set(column_type.enums) == {member.value for member in TonSharePermission}
        assert column_type.enum_class is TonSharePermission
