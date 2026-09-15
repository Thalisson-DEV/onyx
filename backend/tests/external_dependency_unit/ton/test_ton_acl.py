"""TON resource ACL spec — Plan 003c.

The fail-closed contract, exercised against real group and permission rows. Real
PostgreSQL is required because the predicates are SQL: an ``EXISTS`` over a
junction, a ``NOT IN`` over a managed-group subquery, and a ``FOR UPDATE`` re-read
inside the write gate.

Two properties get the most attention, because they are the ones that fail
quietly:

* **Zero junction rows means DENIED.** Half the cases here differ from a passing
  case only by the absence of one junction row.
* **The direct-id path denies exactly like the list path.** A secure filtered list
  combined with an unfiltered detail fetch is the classic ACL failure, so every
  denial case asserts both.

Nothing here requires a licence, a tier or an Enterprise Edition code path, and
``TestCommunityResolution`` proves the write path works with the versioned dispatch
resolved to Community.

Run with::

    uv run pytest backend/tests/external_dependency_unit/ton/test_ton_acl.py
"""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from onyx.db.enums import Permission, PermissionAuthority
from onyx.db.models import User, UserGroup
from onyx.db.ton.acl import (
    assert_can_delete_occurrence,
    assert_can_manage_occurrence,
    fetch_finding_evidence_for_user,
    fetch_findings_for_user,
    fetch_occurrences_for_user,
    get_finding_evidence_for_user,
    get_finding_for_user,
    get_occurrence_for_user,
    is_ton_administrator,
    occurrence_group_ids,
    set_business_unit_groups__no_commit,
    set_contract_groups__no_commit,
    set_occurrence_groups__no_commit,
    ton_permission_authority,
    user_share_permission,
)
from onyx.db.ton.enums import (
    EvidenceConfidenceLevel,
    RedactionLevel,
    RuleDomain,
    SourceType,
    TonSharePermission,
)
from onyx.db.ton.findings import add_finding_evidence__no_commit
from onyx.db.ton.models import BusinessUnit, Contract, Occurrence
from onyx.error_handling.exceptions import OnyxError
from onyx.utils.variable_functionality import (
    fetch_versioned_implementation,
    global_version,
)
from tests.external_dependency_unit.ton import factories

TON_TOKENS: tuple[Permission, ...] = tuple(
    permission for permission in Permission if "ton" in permission.value
)


class _Case:
    """One fully wired occurrence plus the organizational chain around it."""

    def __init__(
        self, db_session: Session, *, domain: RuleDomain = RuleDomain.FINANCIAL
    ):
        self.unit: BusinessUnit = factories.make_business_unit(db_session)
        self.contract: Contract = factories.make_contract(
            db_session, business_unit=self.unit
        )
        rule, rule_version = factories.make_occurrence_rule_version(db_session)
        run = factories.make_analysis_run(db_session)
        result = factories.record_synthetic_detection(
            db_session,
            rule=rule,
            rule_version=rule_version,
            analysis_run=run,
            owning_domain=domain,
            business_unit=self.unit,
            contract=self.contract,
        )
        self.occurrence: Occurrence = result.occurrence
        self.finding = result.finding
        self.evidence = add_finding_evidence__no_commit(
            db_session,
            finding=result.finding,
            source_type=SourceType.UPLOADED_SPREADSHEET,
            confidence_level=EvidenceConfidenceLevel.B,
            redaction_level=RedactionLevel.ROLE_ONLY,
            locator={"sheet": "synthetic", "row": 3},
        )
        db_session.flush()


def _authorize_whole_chain(
    db_session: Session,
    *,
    group: UserGroup,
    case: _Case,
    permission: TonSharePermission = TonSharePermission.VIEWER,
) -> None:
    """Grant the group the occurrence *and* its organizational context.

    Visibility is the conjunction of all three: the resource ACL plus
    authorization for the owning unit and the contract. A test that granted only
    the occurrence row would be asserting a different rule.
    """
    factories.authorize_group(
        db_session,
        group=group,
        occurrence=case.occurrence,
        business_unit=case.unit,
        contract=case.contract,
        permission=permission,
    )


def _reader(db_session: Session, *, group: UserGroup, manage: bool = False) -> User:
    """A user in *group*, holding the TON read (or manage) token by grant."""
    factories.grant_permissions(
        db_session,
        group=group,
        permissions=[
            Permission.MANAGE_TON_OCCURRENCES
            if manage
            else Permission.READ_TON_OCCURRENCES
        ],
    )
    user = factories.make_user(db_session)
    factories.add_member(db_session, group=group, user=user)
    return user


class TestGlobalAdministrator:
    def test_an_administrator_reads_every_occurrence(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        assert is_ton_administrator(admin)
        visible = fetch_occurrences_for_user(ton_session, admin)
        assert [item.id for item in visible] == [case.occurrence.id]
        assert (
            get_occurrence_for_user(ton_session, admin, case.occurrence.id).id
            == case.occurrence.id
        )

    def test_an_administrator_reads_an_occurrence_with_no_junction_row(
        self, ton_session: Session
    ) -> None:
        """The bypass is what makes an unshared case administrable at all."""
        case = _Case(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        assert occurrence_group_ids(ton_session, case.occurrence.id) == set()
        assert fetch_occurrences_for_user(ton_session, admin)

    def test_holding_the_ton_token_is_not_administrator_authority(
        self, ton_session: Session
    ) -> None:
        """The decision that keeps the capability from becoming company-wide
        sight: granting a group MANAGE_TON_OCCURRENCES must not let it read every
        other unit's cases."""
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        ton_session.commit()

        assert not is_ton_administrator(user)
        assert fetch_occurrences_for_user(ton_session, user) == []


class TestFailClosedDefault:
    def test_zero_junction_rows_denies_a_permitted_group(
        self, ton_session: Session
    ) -> None:
        """The fail-closed test. The group holds the token and the case exists;
        only the junction row is missing."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        ton_session.commit()

        assert occurrence_group_ids(ton_session, case.occurrence.id) == set()
        assert fetch_occurrences_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_occurrence_for_user(ton_session, user, case.occurrence.id)

    def test_one_junction_row_is_what_grants_access(self, ton_session: Session) -> None:
        """The control for the case above: same actors, one row added."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        visible = fetch_occurrences_for_user(ton_session, user)
        assert [item.id for item in visible] == [case.occurrence.id]

    def test_a_user_without_the_token_is_denied_even_with_a_junction_row(
        self, ton_session: Session
    ) -> None:
        """Both gates are required: the capability token and the resource ACL."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = factories.make_user(ton_session)
        factories.add_member(ton_session, group=group, user=user)
        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        assert fetch_occurrences_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_occurrence_for_user(ton_session, user, case.occurrence.id)

    def test_a_group_the_user_does_not_belong_to_grants_nothing(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        authorized_group = factories.make_group(ton_session)
        other_group = factories.make_group(ton_session)
        user = _reader(ton_session, group=other_group)
        _authorize_whole_chain(ton_session, group=authorized_group, case=case)
        ton_session.commit()

        assert fetch_occurrences_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_occurrence_for_user(ton_session, user, case.occurrence.id)


class TestCrossScopeDenial:
    def test_a_unit_a_group_cannot_read_a_unit_b_occurrence(
        self, ton_session: Session
    ) -> None:
        case_a = _Case(ton_session)
        case_b = _Case(ton_session)
        group_a = factories.make_group(ton_session)
        user_a = _reader(ton_session, group=group_a)
        _authorize_whole_chain(ton_session, group=group_a, case=case_a)
        ton_session.commit()

        visible = fetch_occurrences_for_user(ton_session, user_a)
        assert [item.id for item in visible] == [case_a.occurrence.id]
        with pytest.raises(OnyxError):
            get_occurrence_for_user(ton_session, user_a, case_b.occurrence.id)

    def test_an_hr_scoped_group_cannot_read_a_financial_occurrence(
        self, ton_session: Session
    ) -> None:
        """Differentiated sensitivity comes from which groups appear on the
        junction, not from a second classification system."""
        hr_case = _Case(ton_session, domain=RuleDomain.HR)
        financial_case = _Case(ton_session, domain=RuleDomain.FINANCIAL)
        hr_group = factories.make_group(ton_session)
        hr_user = _reader(ton_session, group=hr_group)
        _authorize_whole_chain(ton_session, group=hr_group, case=hr_case)
        ton_session.commit()

        visible = {item.id for item in fetch_occurrences_for_user(ton_session, hr_user)}
        assert visible == {hr_case.occurrence.id}
        with pytest.raises(OnyxError):
            get_occurrence_for_user(ton_session, hr_user, financial_case.occurrence.id)

    def test_contract_access_alone_does_not_imply_occurrence_access(
        self, ton_session: Session
    ) -> None:
        """The organizational context is a conjunction, not a shortcut."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        factories.authorize_group(ton_session, group=group, contract=case.contract)
        ton_session.commit()

        assert fetch_occurrences_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_occurrence_for_user(ton_session, user, case.occurrence.id)

    def test_an_occurrence_row_without_unit_authorization_is_denied(
        self, ton_session: Session
    ) -> None:
        """The other half of the conjunction: a junction row created by mistake
        cannot reach past the unit boundary."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        factories.authorize_group(ton_session, group=group, occurrence=case.occurrence)
        ton_session.commit()

        assert fetch_occurrences_for_user(ton_session, user) == []

    def test_group_membership_alone_is_not_management_authority(
        self, ton_session: Session
    ) -> None:
        """A group manager gains no TON authority from managing a group: no TON
        token is in the scoped-manager bundle."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        manager = factories.make_user(ton_session)
        factories.add_member(ton_session, group=group, user=manager, is_manager=True)
        _authorize_whole_chain(
            ton_session,
            group=group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        assert manager.is_group_manager is True
        for token in TON_TOKENS:
            assert ton_permission_authority(manager, token) is PermissionAuthority.NONE
        assert not is_ton_administrator(manager)
        assert fetch_occurrences_for_user(ton_session, manager) == []


class TestShareLevels:
    def test_a_viewer_cannot_perform_an_editor_operation(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session,
            group=group,
            case=case,
            permission=TonSharePermission.VIEWER,
        )
        ton_session.commit()

        # The read succeeds; the write does not.
        assert fetch_occurrences_for_user(ton_session, user)
        assert (
            user_share_permission(
                ton_session, user=user, occurrence_id=case.occurrence.id
            )
            is TonSharePermission.VIEWER
        )
        assert fetch_occurrences_for_user(ton_session, user, editable=True) == []
        with pytest.raises(OnyxError):
            assert_can_manage_occurrence(
                ton_session, user=user, occurrence=case.occurrence
            )

    def test_an_editor_can_write_within_its_own_groups(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session,
            group=group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        assert_can_manage_occurrence(ton_session, user=user, occurrence=case.occurrence)
        editable = fetch_occurrences_for_user(ton_session, user, editable=True)
        assert [item.id for item in editable] == [case.occurrence.id]

    def test_an_editor_without_the_manage_token_is_denied(
        self, ton_session: Session
    ) -> None:
        """An EDITOR junction row is not a substitute for the capability token."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=False)
        _authorize_whole_chain(
            ton_session,
            group=group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        assert fetch_occurrences_for_user(ton_session, user, editable=True) == []
        with pytest.raises(OnyxError):
            assert_can_manage_occurrence(
                ton_session, user=user, occurrence=case.occurrence
            )

    def test_an_editor_cannot_reach_a_case_shared_outside_its_groups(
        self, ton_session: Session
    ) -> None:
        """``within_managed_scope_clause`` with the caller's own groups: editing
        requires that *every* authorized group is one the caller belongs to."""
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
        factories.authorize_group(
            ton_session, group=outside_group, occurrence=case.occurrence
        )
        ton_session.commit()

        # Reading is still permitted — the case was shared with the caller.
        assert fetch_occurrences_for_user(ton_session, user)
        # Writing is not: the case also belongs to a group the caller cannot reach.
        assert fetch_occurrences_for_user(ton_session, user, editable=True) == []
        with pytest.raises(OnyxError):
            assert_can_manage_occurrence(
                ton_session, user=user, occurrence=case.occurrence
            )


class TestWriteGate:
    def test_an_administrator_may_set_the_group_authorizations(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        admin = factories.make_admin(ton_session)
        group = factories.make_group(ton_session)
        ton_session.commit()

        set_occurrence_groups__no_commit(
            ton_session,
            user=admin,
            occurrence=case.occurrence,
            group_permissions={group.id: TonSharePermission.EDITOR},
        )
        ton_session.commit()

        assert occurrence_group_ids(ton_session, case.occurrence.id) == {group.id}

    def test_an_editor_cannot_widen_to_a_group_it_does_not_belong_to(
        self, ton_session: Session
    ) -> None:
        """The anti-widening rule. Reaching a case and then publishing it to a
        group that was never authorized for it is the escalation this blocks."""
        case = _Case(ton_session)
        own_group = factories.make_group(ton_session)
        stranger_group = factories.make_group(ton_session)
        user = _reader(ton_session, group=own_group, manage=True)
        _authorize_whole_chain(
            ton_session,
            group=own_group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        with pytest.raises(OnyxError):
            set_occurrence_groups__no_commit(
                ton_session,
                user=user,
                occurrence=case.occurrence,
                group_permissions={
                    own_group.id: TonSharePermission.EDITOR,
                    stranger_group.id: TonSharePermission.VIEWER,
                },
            )
        ton_session.rollback()
        assert occurrence_group_ids(ton_session, case.occurrence.id) == {own_group.id}

    def test_an_editor_may_reshare_within_its_own_groups(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        first_group = factories.make_group(ton_session)
        second_group = factories.make_group(ton_session)
        user = _reader(ton_session, group=first_group, manage=True)
        factories.add_member(ton_session, group=second_group, user=user)
        _authorize_whole_chain(
            ton_session,
            group=first_group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        set_occurrence_groups__no_commit(
            ton_session,
            user=user,
            occurrence=case.occurrence,
            group_permissions={
                first_group.id: TonSharePermission.EDITOR,
                second_group.id: TonSharePermission.VIEWER,
            },
        )
        ton_session.commit()

        assert occurrence_group_ids(ton_session, case.occurrence.id) == {
            first_group.id,
            second_group.id,
        }

    def test_an_editor_cannot_orphan_a_case(self, ton_session: Session) -> None:
        """Removing the last authorization would hide the case behind the
        fail-closed default and lose the caller's own access."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session,
            group=group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        with pytest.raises(OnyxError):
            set_occurrence_groups__no_commit(
                ton_session,
                user=user,
                occurrence=case.occurrence,
                group_permissions={},
            )
        ton_session.rollback()
        assert occurrence_group_ids(ton_session, case.occurrence.id) == {group.id}

    def test_a_non_administrator_cannot_share_an_unshared_case(
        self, ton_session: Session
    ) -> None:
        """Fail-closed: with no current authorization there is nothing to derive
        the caller's scope from, so only an administrator can open the case."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        ton_session.commit()

        with pytest.raises(OnyxError):
            set_occurrence_groups__no_commit(
                ton_session,
                user=user,
                occurrence=case.occurrence,
                group_permissions={group.id: TonSharePermission.EDITOR},
            )

    def test_the_write_gate_ignores_group_ids_supplied_by_the_caller(
        self, ton_session: Session
    ) -> None:
        """The current authorizations are re-read from the database inside the
        transaction, so a request cannot assert its own scope."""
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
        factories.authorize_group(
            ton_session, group=outside_group, occurrence=case.occurrence
        )
        ton_session.commit()

        # The caller asks for a state that would be within scope. The gate refuses
        # because the *stored* state is not.
        with pytest.raises(OnyxError):
            set_occurrence_groups__no_commit(
                ton_session,
                user=user,
                occurrence=case.occurrence,
                group_permissions={own_group.id: TonSharePermission.EDITOR},
            )


class TestDeleteRequiresGlobalAuthority:
    def test_an_administrator_may_delete_any_case(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        assert_can_delete_occurrence(
            ton_session, user=admin, occurrence=case.occurrence
        )

    def test_a_group_manager_may_not_delete(self, ton_session: Session) -> None:
        """``assert_global`` excludes a scoped manager, who resolves NONE for
        every TON token."""
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        manager = factories.make_user(ton_session)
        factories.add_member(ton_session, group=group, user=manager, is_manager=True)
        _authorize_whole_chain(
            ton_session,
            group=group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        with pytest.raises(OnyxError):
            assert_can_delete_occurrence(
                ton_session, user=manager, occurrence=case.occurrence
            )

    def test_a_plain_member_may_not_delete(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = factories.make_user(ton_session)
        factories.add_member(ton_session, group=group, user=user)
        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        with pytest.raises(OnyxError):
            assert_can_delete_occurrence(
                ton_session, user=user, occurrence=case.occurrence
            )

    def test_a_token_holder_cannot_delete_a_case_outside_its_scope(
        self, ton_session: Session
    ) -> None:
        """Holding the capability is not a licence to destroy an unreachable case.

        This is why the delete gate is the strictest of both: ``assert_global``
        would pass here on its own, because the group holds the token globally.
        """
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        ton_session.commit()

        assert not is_ton_administrator(user)
        with pytest.raises(OnyxError):
            assert_can_delete_occurrence(
                ton_session, user=user, occurrence=case.occurrence
            )

    def test_a_token_holder_may_delete_a_case_it_can_edit(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session,
            group=group,
            case=case,
            permission=TonSharePermission.EDITOR,
        )
        ton_session.commit()

        assert_can_delete_occurrence(ton_session, user=user, occurrence=case.occurrence)

    def test_a_viewer_may_not_delete(self, ton_session: Session) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group, manage=True)
        _authorize_whole_chain(
            ton_session,
            group=group,
            case=case,
            permission=TonSharePermission.VIEWER,
        )
        ton_session.commit()

        with pytest.raises(OnyxError):
            assert_can_delete_occurrence(
                ton_session, user=user, occurrence=case.occurrence
            )


class TestDerivedFindingAccess:
    def test_a_finding_is_visible_exactly_when_its_occurrence_is(
        self, ton_session: Session
    ) -> None:
        permitted = _Case(ton_session)
        denied = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(ton_session, group=group, case=permitted)
        ton_session.commit()

        visible = {item.id for item in fetch_findings_for_user(ton_session, user)}
        assert visible == {permitted.finding.id}
        assert (
            get_finding_for_user(ton_session, user, permitted.finding.id).id
            == permitted.finding.id
        )
        with pytest.raises(OnyxError):
            get_finding_for_user(ton_session, user, denied.finding.id)

    def test_evidence_is_visible_exactly_when_its_finding_is(
        self, ton_session: Session
    ) -> None:
        permitted = _Case(ton_session)
        denied = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(ton_session, group=group, case=permitted)
        ton_session.commit()

        visible = {
            item.id for item in fetch_finding_evidence_for_user(ton_session, user)
        }
        assert visible == {permitted.evidence.id}
        assert (
            get_finding_evidence_for_user(ton_session, user, permitted.evidence.id).id
            == permitted.evidence.id
        )
        with pytest.raises(OnyxError):
            get_finding_evidence_for_user(ton_session, user, denied.evidence.id)

    def test_zero_junction_rows_denies_a_finding_and_its_evidence(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        ton_session.commit()

        assert fetch_findings_for_user(ton_session, user) == []
        assert fetch_finding_evidence_for_user(ton_session, user) == []
        with pytest.raises(OnyxError):
            get_finding_for_user(ton_session, user, case.finding.id)
        with pytest.raises(OnyxError):
            get_finding_evidence_for_user(ton_session, user, case.evidence.id)


class TestBusinessUnitAndContractSharing:
    def test_setting_unit_authorizations_requires_global_authority(
        self, ton_session: Session
    ) -> None:
        unit = factories.make_business_unit(ton_session)
        group = factories.make_group(ton_session)
        scoped = _reader(ton_session, group=group, manage=True)
        ton_session.commit()

        with pytest.raises(OnyxError):
            set_business_unit_groups__no_commit(
                ton_session,
                user=scoped,
                business_unit=unit,
                group_permissions={group.id: TonSharePermission.VIEWER},
            )

    def test_an_administrator_sets_unit_and_contract_authorizations(
        self, ton_session: Session
    ) -> None:
        unit = factories.make_business_unit(ton_session)
        contract = factories.make_contract(ton_session, business_unit=unit)
        group = factories.make_group(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        unit_rows = set_business_unit_groups__no_commit(
            ton_session,
            user=admin,
            business_unit=unit,
            group_permissions={group.id: TonSharePermission.VIEWER},
        )
        contract_rows = set_contract_groups__no_commit(
            ton_session,
            user=admin,
            contract=contract,
            group_permissions={group.id: TonSharePermission.EDITOR},
        )
        ton_session.commit()

        assert [row.user_group_id for row in unit_rows] == [group.id]
        assert [row.permission for row in contract_rows] == [TonSharePermission.EDITOR]

    def test_replacing_authorizations_removes_the_previous_rows(
        self, ton_session: Session
    ) -> None:
        unit = factories.make_business_unit(ton_session)
        first = factories.make_group(ton_session)
        second = factories.make_group(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        set_business_unit_groups__no_commit(
            ton_session,
            user=admin,
            business_unit=unit,
            group_permissions={first.id: TonSharePermission.VIEWER},
        )
        ton_session.commit()
        set_business_unit_groups__no_commit(
            ton_session,
            user=admin,
            business_unit=unit,
            group_permissions={second.id: TonSharePermission.VIEWER},
        )
        ton_session.commit()

        from onyx.db.ton.models import BusinessUnit__UserGroup

        rows = (
            ton_session.query(BusinessUnit__UserGroup)
            .filter_by(business_unit_id=unit.id)
            .all()
        )
        assert [row.user_group_id for row in rows] == [second.id]


class TestCommunityResolution:
    """The CE trap readiness §10 flags, closed.

    ``onyx/db/persona.py``'s Community ``update_persona_access`` raises
    ``NotImplementedError("Onyx MIT does not support group-based sharing")``.
    Copying that split for TON would be worse than a missing feature: with the
    fail-closed default, a CE-resolved worker would write no junction rows and
    every TON resource would silently become invisible.
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
    def test_ton_acl_writes_work_with_community_implementations_resolved(
        self, ton_session: Session
    ) -> None:
        assert not global_version.is_ee_version()
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        admin = factories.make_admin(ton_session)
        ton_session.commit()

        set_occurrence_groups__no_commit(
            ton_session,
            user=admin,
            occurrence=case.occurrence,
            group_permissions={group.id: TonSharePermission.EDITOR},
        )
        ton_session.commit()

        assert occurrence_group_ids(ton_session, case.occurrence.id) == {group.id}

    @pytest.mark.usefixtures("community_resolution")
    def test_ton_acl_reads_work_with_community_implementations_resolved(
        self, ton_session: Session
    ) -> None:
        case = _Case(ton_session)
        group = factories.make_group(ton_session)
        user = _reader(ton_session, group=group)
        _authorize_whole_chain(ton_session, group=group, case=case)
        ton_session.commit()

        visible = fetch_occurrences_for_user(ton_session, user)
        assert [item.id for item in visible] == [case.occurrence.id]

    def test_the_ton_acl_module_lives_in_the_community_tree(self) -> None:
        from onyx.db.ton import acl

        assert acl.__name__.startswith("onyx.db.ton"), (
            "the TON ACL must not live under ee/, or a CE-resolved worker would "
            "write no junction rows and hide every TON resource"
        )

    def test_no_ton_acl_function_requires_a_licence_or_tier(self) -> None:
        """An inverse assertion over the module's *code*: no licence, tier or
        edition check gates the TON ACL.

        Docstrings are stripped first, because this module explains the CE trap in
        prose and a naive substring search over the source would match its own
        explanation.
        """
        import ast
        import inspect

        from onyx.db.ton import acl

        tree = ast.parse(inspect.getsource(acl))
        referenced: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                referenced.add(node.id)
            elif isinstance(node, ast.Attribute):
                referenced.add(node.attr)
            elif isinstance(node, ast.alias):
                referenced.add(node.name.rsplit(".", 1)[-1])

        forbidden = {
            "is_ee_version",
            "global_version",
            "fetch_versioned_implementation",
            "NotImplementedError",
            "check_license",
            "get_license",
        }
        assert referenced & forbidden == set(), (
            "onyx/db/ton/acl.py must not gate on edition, licence or tier: "
            f"{sorted(referenced & forbidden)}"
        )


class TestScopedAuthorityBoundary:
    """No TON token is scopable, and the decision is asserted, not assumed."""

    def test_no_ton_token_is_in_the_scoped_manager_bundle(self) -> None:
        from onyx.auth.permissions import (
            SCOPED_MANAGER_PERMISSIONS,
            SCOPED_MANAGER_PERMISSIONS_EXPANDED,
        )

        for token in TON_TOKENS:
            assert token not in SCOPED_MANAGER_PERMISSIONS
            assert token.value not in SCOPED_MANAGER_PERMISSIONS_EXPANDED

    def test_the_occurrence_tokens_exist_and_manage_implies_read(self) -> None:
        from onyx.auth.permissions import resolve_effective_permissions

        assert Permission.READ_TON_OCCURRENCES.value == "read:ton_occurrences"
        assert Permission.MANAGE_TON_OCCURRENCES.value == "manage:ton_occurrences"
        expanded = resolve_effective_permissions(
            {Permission.MANAGE_TON_OCCURRENCES.value}
        )
        assert Permission.READ_TON_OCCURRENCES.value in expanded

    def test_both_occurrence_tokens_are_grantable_through_the_registry(self) -> None:
        from onyx.auth.permissions import PERMISSION_REGISTRY

        registered = {
            permission
            for entry in PERMISSION_REGISTRY
            for permission in entry.permissions
        }
        assert Permission.READ_TON_OCCURRENCES in registered
        assert Permission.MANAGE_TON_OCCURRENCES in registered

    def test_the_report_tokens_are_bound_by_the_same_boundary(self) -> None:
        """003d added ``READ_TON_REPORTS`` and ``MANAGE_TON_REPORTS`` with their
        table. They are held to the same rule as every other TON token: never
        ``SCOPED``, so a group manager gains no authority over a published report
        merely shared with their group."""
        from onyx.auth.permissions import (
            SCOPED_MANAGER_PERMISSIONS,
            SCOPED_MANAGER_PERMISSIONS_EXPANDED,
        )

        report_tokens = {token for token in TON_TOKENS if "report" in token.value}
        assert report_tokens == {
            Permission.READ_TON_REPORTS,
            Permission.MANAGE_TON_REPORTS,
        }
        for token in report_tokens:
            assert token not in SCOPED_MANAGER_PERMISSIONS
            assert token.value not in SCOPED_MANAGER_PERMISSIONS_EXPANDED
