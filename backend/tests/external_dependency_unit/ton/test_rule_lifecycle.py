"""Rule and rule-version lifecycle spec — Plan 003b.

Exercises the service path in ``onyx.db.ton.rule_versions`` against real
PostgreSQL: append a version, record an approval, activate, and select the
version in force on a date. The point being protected is that changing a
threshold creates a new row and never reinterprets an older one.

Throwaway databases only; the deployment database is untouched.

Run with::

    uv run pytest backend/tests/external_dependency_unit/ton/test_rule_lifecycle.py
"""

import datetime

import pytest
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    EvidenceConfidenceLevel,
    MissingDataBehavior,
    PostResolutionPolicy,
    RuleDomain,
    RuleKind,
    RuleProvenance,
    RuleVersionStatus,
)
from onyx.db.ton.models import Rule, RuleVersion
from onyx.db.ton.rule_versions import (
    activate_rule_version__no_commit,
    approve_rule_version__no_commit,
    create_rule__no_commit,
    create_rule_version__no_commit,
    get_effective_rule_version,
    is_publishable,
    next_version_number,
)
from tests.external_dependency_unit.ton import factories

# Synthetic, so no unapproved business value exists anywhere in the tests.
FIRST_PARAMETERS: dict[str, object] = {"synthetic_threshold": "0.25"}
SECOND_PARAMETERS: dict[str, object] = {"synthetic_threshold": "0.75"}


def _append_version(
    db_session: Session,
    *,
    rule: Rule,
    parameters: dict[str, object],
    effective_from: datetime.date | None = None,
    effective_to: datetime.date | None = None,
    status: RuleVersionStatus = RuleVersionStatus.DRAFT,
) -> RuleVersion:
    return create_rule_version__no_commit(
        db_session,
        rule=rule,
        title="Synthetic rule version",
        executor_key=factories.SYNTHETIC_EXECUTOR_KEY,
        provenance=RuleProvenance.DERIVED,
        missing_data_behavior=MissingDataBehavior.SKIP_WITH_NOTE,
        min_confidence_level=EvidenceConfidenceLevel.B,
        post_resolution_policy=PostResolutionPolicy.REOPEN_SAME_OCCURRENCE,
        identity_components=["period", "rule_code", "business_unit_id"],
        parameters=parameters,
        effective_from=effective_from,
        effective_to=effective_to,
        status=status,
    )


class TestVersionAppending:
    def test_versions_are_numbered_in_sequence(self, ton_session: Session) -> None:
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.FINANCIAL,
            kind=RuleKind.DETECTION,
        )

        first = _append_version(ton_session, rule=rule, parameters=FIRST_PARAMETERS)
        second = _append_version(ton_session, rule=rule, parameters=SECOND_PARAMETERS)
        ton_session.commit()

        assert (first.version, second.version) == (1, 2)
        assert next_version_number(ton_session, rule.id) == 3

    def test_a_new_version_leaves_the_previous_one_untouched(
        self, ton_session: Session
    ) -> None:
        """The guarantee historical consumers depend on: a threshold change is a
        new row, so a finding that pinned version 1 still measures against
        version 1's parameters."""
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.FINANCIAL,
            kind=RuleKind.DETECTION,
        )
        first = _append_version(ton_session, rule=rule, parameters=FIRST_PARAMETERS)
        first_id = first.id
        ton_session.commit()

        _append_version(ton_session, rule=rule, parameters=SECOND_PARAMETERS)
        ton_session.commit()
        ton_session.expire_all()

        reloaded = ton_session.get(RuleVersion, first_id)
        assert reloaded is not None
        assert reloaded.parameters == FIRST_PARAMETERS
        assert reloaded.version == 1

    def test_the_identity_component_order_is_normalised_on_write(
        self, ton_session: Session
    ) -> None:
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.FLEET,
            kind=RuleKind.DETECTION,
        )

        rule_version = _append_version(
            ton_session, rule=rule, parameters=FIRST_PARAMETERS
        )
        ton_session.commit()

        assert rule_version.identity_components == [
            "rule_code",
            "business_unit_id",
            "period",
        ]

    def test_an_unapproved_identity_component_is_refused_before_the_write(
        self, ton_session: Session
    ) -> None:
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.HR,
            kind=RuleKind.BLIND_SPOT,
        )

        with pytest.raises(ValueError, match="not an approved identity component"):
            create_rule_version__no_commit(
                ton_session,
                rule=rule,
                title="Synthetic rule version",
                executor_key=factories.SYNTHETIC_EXECUTOR_KEY,
                provenance=RuleProvenance.DERIVED,
                missing_data_behavior=MissingDataBehavior.BLOCK,
                min_confidence_level=EvidenceConfidenceLevel.D,
                post_resolution_policy=(
                    PostResolutionPolicy.SUPERSEDE_WITH_NEW_OCCURRENCE
                ),
                identity_components=["rule_code", "llm_summary"],
            )

        assert ton_session.query(RuleVersion).filter_by(rule_id=rule.id).count() == 0


class TestApprovalGate:
    def test_a_version_cannot_be_created_active(self, ton_session: Session) -> None:
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.FINANCIAL,
            kind=RuleKind.SANITY,
        )

        with pytest.raises(ValueError, match="cannot be created ACTIVE"):
            _append_version(
                ton_session,
                rule=rule,
                parameters=FIRST_PARAMETERS,
                status=RuleVersionStatus.ACTIVE,
            )

    def test_activation_without_an_approval_is_refused(
        self, ton_session: Session
    ) -> None:
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.FINANCIAL,
            kind=RuleKind.SANITY,
        )
        rule_version = _append_version(
            ton_session, rule=rule, parameters=FIRST_PARAMETERS
        )

        with pytest.raises(ValueError, match="requires both approved_by"):
            activate_rule_version__no_commit(ton_session, rule_version=rule_version)

        assert rule_version.status is RuleVersionStatus.DRAFT

    def test_approval_then_activation_succeeds(self, ton_session: Session) -> None:
        user = factories.make_user(ton_session)
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.FINANCIAL,
            kind=RuleKind.SANITY,
            created_by=user.id,
        )
        rule_version = _append_version(
            ton_session,
            rule=rule,
            parameters=FIRST_PARAMETERS,
            effective_from=datetime.date(2001, 1, 1),
        )

        approve_rule_version__no_commit(
            ton_session,
            rule_version=rule_version,
            approved_by=user.id,
            approval_reference="synthetic-approval-1",
        )
        activate_rule_version__no_commit(ton_session, rule_version=rule_version)
        ton_session.commit()

        assert rule_version.status is RuleVersionStatus.ACTIVE
        assert rule_version.approved_by == user.id
        assert rule_version.approved_at is not None
        assert rule_version.approval_reference == "synthetic-approval-1"
        assert is_publishable(rule_version)

    def test_approval_alone_does_not_activate(self, ton_session: Session) -> None:
        """Approval and activation are separate acts: an approved version may
        still be waiting for its effective date."""
        user = factories.make_user(ton_session)
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.CONTRACT,
            kind=RuleKind.DETECTION,
        )
        rule_version = _append_version(
            ton_session, rule=rule, parameters=FIRST_PARAMETERS
        )

        approve_rule_version__no_commit(
            ton_session,
            rule_version=rule_version,
            approved_by=user.id,
            approval_reference="synthetic-approval-2",
        )
        ton_session.commit()

        assert rule_version.status is RuleVersionStatus.DRAFT
        assert not is_publishable(rule_version)


class TestEffectiveSelectionThroughTheDatabase:
    def test_the_version_in_force_is_selected_by_date(
        self, ton_session: Session
    ) -> None:
        user = factories.make_user(ton_session)
        code = f"SYN-{factories.unique_suffix()}"
        rule = create_rule__no_commit(
            ton_session,
            code=code,
            domain=RuleDomain.FINANCIAL,
            kind=RuleKind.DETECTION,
        )

        first = _append_version(
            ton_session,
            rule=rule,
            parameters=FIRST_PARAMETERS,
            effective_from=datetime.date(2001, 1, 1),
            effective_to=datetime.date(2001, 6, 30),
        )
        second = _append_version(
            ton_session,
            rule=rule,
            parameters=SECOND_PARAMETERS,
            effective_from=datetime.date(2001, 7, 1),
        )
        for rule_version in (first, second):
            approve_rule_version__no_commit(
                ton_session,
                rule_version=rule_version,
                approved_by=user.id,
                approval_reference="synthetic-approval-3",
            )
            activate_rule_version__no_commit(ton_session, rule_version=rule_version)
        ton_session.commit()

        march = get_effective_rule_version(
            ton_session, rule_code=code, on_date=datetime.date(2001, 3, 1)
        )
        september = get_effective_rule_version(
            ton_session, rule_code=code, on_date=datetime.date(2001, 9, 1)
        )

        assert march is not None
        assert september is not None
        assert march.id == first.id
        assert september.id == second.id
        # The historical version keeps its own parameters, unchanged.
        assert march.parameters == FIRST_PARAMETERS
        assert september.parameters == SECOND_PARAMETERS

    def test_a_draft_is_never_selected(self, ton_session: Session) -> None:
        code = f"SYN-{factories.unique_suffix()}"
        rule = create_rule__no_commit(
            ton_session,
            code=code,
            domain=RuleDomain.PROCUREMENT,
            kind=RuleKind.DETECTION,
        )
        _append_version(
            ton_session,
            rule=rule,
            parameters=FIRST_PARAMETERS,
            effective_from=datetime.date(2001, 1, 1),
        )
        ton_session.commit()

        assert (
            get_effective_rule_version(
                ton_session, rule_code=code, on_date=datetime.date(2001, 2, 1)
            )
            is None
        )

    def test_a_test_only_version_is_never_selected(self, ton_session: Session) -> None:
        code = f"SYN-{factories.unique_suffix()}"
        rule = create_rule__no_commit(
            ton_session,
            code=code,
            domain=RuleDomain.AUDIT,
            kind=RuleKind.SANITY,
        )
        rule_version = _append_version(
            ton_session,
            rule=rule,
            parameters=FIRST_PARAMETERS,
            effective_from=datetime.date(2001, 1, 1),
            status=RuleVersionStatus.TEST_ONLY,
        )
        ton_session.commit()

        assert (
            get_effective_rule_version(
                ton_session, rule_code=code, on_date=datetime.date(2001, 2, 1)
            )
            is None
        )
        assert not is_publishable(rule_version)

    def test_overlapping_active_versions_are_reported_not_guessed(
        self, ton_session: Session
    ) -> None:
        user = factories.make_user(ton_session)
        code = f"SYN-{factories.unique_suffix()}"
        rule = create_rule__no_commit(
            ton_session,
            code=code,
            domain=RuleDomain.FINANCIAL,
            kind=RuleKind.DETECTION,
        )
        for parameters, effective_from in (
            (FIRST_PARAMETERS, datetime.date(2001, 1, 1)),
            (SECOND_PARAMETERS, datetime.date(2001, 2, 1)),
        ):
            rule_version = _append_version(
                ton_session,
                rule=rule,
                parameters=parameters,
                effective_from=effective_from,
            )
            approve_rule_version__no_commit(
                ton_session,
                rule_version=rule_version,
                approved_by=user.id,
                approval_reference="synthetic-approval-4",
            )
            activate_rule_version__no_commit(ton_session, rule_version=rule_version)
        ton_session.commit()

        with pytest.raises(ValueError, match="all in force"):
            get_effective_rule_version(
                ton_session, rule_code=code, on_date=datetime.date(2001, 3, 1)
            )


class TestRuleImmutability:
    def test_rule_carries_no_threshold_or_status(self, ton_session: Session) -> None:
        """Asserted against the migrated table, not only the model."""
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.QUALITY,
            kind=RuleKind.DETECTION,
        )
        ton_session.commit()

        for forbidden in ("status", "parameters", "threshold", "effective_from"):
            assert not hasattr(rule, forbidden)

    def test_a_rule_deletion_cascades_to_its_unused_versions(
        self, ton_session: Session
    ) -> None:
        """A version has no meaning without its rule. A version that a run used
        is protected separately, by the RESTRICT on the participation table."""
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-{factories.unique_suffix()}",
            domain=RuleDomain.OPERATIONAL,
            kind=RuleKind.DETECTION,
        )
        _append_version(ton_session, rule=rule, parameters=FIRST_PARAMETERS)
        ton_session.commit()
        rule_id = rule.id

        ton_session.delete(rule)
        ton_session.commit()

        assert ton_session.query(RuleVersion).filter_by(rule_id=rule_id).count() == 0
