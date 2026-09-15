"""Pure-domain spec for the TON rule and step contracts — Plan 003b.

No database, no session, no LLM. What lives here is the logic that must hold
before anything is persisted: the closed identity vocabulary, effective-date
selection, the placement of mutable data on ``RuleVersion`` rather than
``Rule``, the fixed seven-step order, blocking scope containment, the run-status
roll-up, and the permission-token boundaries.

The database-level counterparts — approval and blocked-cause constraints,
uniqueness, foreign keys — are in
``tests/external_dependency_unit/ton/test_domain_schema.py``, because a
constraint only exists once the migration ran.
"""

import datetime
from typing import cast
from uuid import uuid4

import pytest

from onyx.auth.permissions import (
    PERMISSION_REGISTRY,
    SCOPED_MANAGER_PERMISSIONS,
    SCOPED_MANAGER_PERMISSIONS_EXPANDED,
)
from onyx.db.enums import Permission
from onyx.db.models import Base
from onyx.db.ton import models as ton_models
from onyx.db.ton.analysis_steps import (
    STEP_ORDER,
    StepScope,
    downstream_step_codes,
    is_upstream_of,
    resolve_run_status,
)
from onyx.db.ton.enums import (
    AnalysisRunStatus,
    AnalysisSpecialist,
    AnalysisStepBlockedReason,
    AnalysisStepCode,
    AnalysisStepStatus,
    BusinessUnitKind,
    ContractStatus,
    IdentityComponent,
    RuleDomain,
    RuleKind,
    RuleVersionStatus,
)
from onyx.db.ton.identity import (
    ALLOWED_IDENTITY_COMPONENTS,
    validate_identity_components,
)
from onyx.db.ton.models import AnalysisStep, Rule, RuleVersion
from onyx.db.ton.rule_versions import (
    is_in_force_on,
    is_publishable,
    select_effective_rule_version,
)

# The nine tables this slice introduced. The whole-schema inverse assertions moved
# to `test_occurrence_projection.py` when 003c added twelve more; what stays here
# is the 003b subset, so a 003b regression is still named as one.
TON_TABLE_NAMES: tuple[str, ...] = (
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


def _rule_version(
    *,
    version: int,
    status: RuleVersionStatus,
    effective_from: datetime.date | None = None,
    effective_to: datetime.date | None = None,
) -> RuleVersion:
    """An unpersisted rule version. Enough for the pure selection logic."""
    return RuleVersion(
        version=version,
        status=status,
        effective_from=effective_from,
        effective_to=effective_to,
    )


def _step(
    *,
    status: AnalysisStepStatus,
    step_code: AnalysisStepCode = AnalysisStepCode.DETECTION,
) -> AnalysisStep:
    return AnalysisStep(step_code=step_code, status=status)


class TestIdentityComponentVocabulary:
    """``identity_components`` uses a closed vocabulary (readiness §7)."""

    def test_an_approved_subset_is_accepted(self) -> None:
        assert validate_identity_components(
            ["rule_code", "business_unit_id", "period"]
        ) == ["rule_code", "business_unit_id", "period"]

    def test_the_result_is_in_canonical_order(self) -> None:
        """Declaration order must not change the identity a rule produces."""
        assert validate_identity_components(
            ["period", "rule_code", "supplier_key", "business_unit_id"]
        ) == ["rule_code", "business_unit_id", "period", "supplier_key"]

    def test_the_full_vocabulary_is_accepted(self) -> None:
        every = [component.value for component in IdentityComponent]
        assert set(validate_identity_components(every)) == ALLOWED_IDENTITY_COMPONENTS

    def test_an_unknown_dimension_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="not an approved identity component"):
            validate_identity_components(["rule_code", "invented_dimension"])

    @pytest.mark.parametrize(
        "llm_flavoured",
        ["summary", "probable_cause", "title", "description", "interpretation"],
    )
    def test_interpretation_text_can_never_be_an_identity_input(
        self, llm_flavoured: str
    ) -> None:
        """Text similarity is not a deduplication mechanism here, so no
        LLM-produced field may enter the vocabulary."""
        with pytest.raises(ValueError, match="not an approved identity component"):
            validate_identity_components(["rule_code", llm_flavoured])

    def test_a_duplicate_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="more than once"):
            validate_identity_components(["rule_code", "rule_code"])

    def test_an_empty_list_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_identity_components([])

    def test_none_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="is required"):
            validate_identity_components(None)

    def test_a_non_string_entry_is_rejected(self) -> None:
        # A caller that ignores the annotation still gets a domain error rather
        # than a malformed JSONB value.
        malformed = cast(list[str], ["rule_code", 7])
        with pytest.raises(ValueError, match="must be strings"):
            validate_identity_components(malformed)

    def test_the_version_is_not_an_identity_component(self) -> None:
        """If the version were part of identity, every threshold change would
        reset recurrence tracking on every open case (readiness §7)."""
        assert "rule_version" not in ALLOWED_IDENTITY_COMPONENTS
        assert "rule_version_id" not in ALLOWED_IDENTITY_COMPONENTS


class TestMutabilityPlacement:
    """Rule holds only what must never change."""

    @pytest.mark.parametrize(
        "forbidden",
        [
            "status",
            "threshold",
            "parameters",
            "effective_from",
            "effective_to",
            "title",
            "description",
            "approved_by",
            "approved_at",
            "severity_mapping",
            "nc_code",
        ],
    )
    def test_rule_has_no_mutable_column(self, forbidden: str) -> None:
        assert forbidden not in Rule.__table__.columns

    def test_rule_holds_only_the_stable_identity(self) -> None:
        assert set(Rule.__table__.columns.keys()) == {
            "id",
            "code",
            "domain",
            "kind",
            "created_at",
            "created_by",
        }

    @pytest.mark.parametrize(
        "expected",
        [
            "status",
            "parameters",
            "effective_from",
            "effective_to",
            "title",
            "description",
            "approved_by",
            "approved_at",
            "approval_reference",
            "severity_mapping",
            "nc_code",
            "identity_components",
            "post_resolution_policy",
            "executor_key",
            "definition_hash",
        ],
    )
    def test_rule_version_carries_the_mutable_contract(self, expected: str) -> None:
        assert expected in RuleVersion.__table__.columns

    def test_a_historical_version_stays_independently_referenceable(self) -> None:
        """003c pins ``rule_version_id``, so the primary key must live on the
        version rather than being derived from the rule."""
        assert [column.name for column in RuleVersion.__table__.primary_key] == ["id"]


class TestEffectiveDateSelection:
    def test_exactly_one_version_is_selected_for_a_date(self) -> None:
        first = _rule_version(
            version=1,
            status=RuleVersionStatus.ACTIVE,
            effective_from=datetime.date(2001, 1, 1),
            effective_to=datetime.date(2001, 6, 30),
        )
        second = _rule_version(
            version=2,
            status=RuleVersionStatus.ACTIVE,
            effective_from=datetime.date(2001, 7, 1),
        )

        assert (
            select_effective_rule_version([first, second], datetime.date(2001, 3, 15))
            is first
        )
        assert (
            select_effective_rule_version([first, second], datetime.date(2001, 9, 1))
            is second
        )

    def test_the_boundary_days_are_inclusive(self) -> None:
        version = _rule_version(
            version=1,
            status=RuleVersionStatus.ACTIVE,
            effective_from=datetime.date(2001, 1, 1),
            effective_to=datetime.date(2001, 1, 31),
        )

        assert is_in_force_on(version, datetime.date(2001, 1, 1))
        assert is_in_force_on(version, datetime.date(2001, 1, 31))
        assert not is_in_force_on(version, datetime.date(2000, 12, 31))
        assert not is_in_force_on(version, datetime.date(2001, 2, 1))

    def test_a_date_before_any_version_selects_nothing(self) -> None:
        version = _rule_version(
            version=1,
            status=RuleVersionStatus.ACTIVE,
            effective_from=datetime.date(2001, 5, 1),
        )
        assert (
            select_effective_rule_version([version], datetime.date(2001, 4, 30)) is None
        )

    def test_overlapping_active_versions_raise(self) -> None:
        """Silently picking the newest would hide a misconfiguration that changes
        which threshold a published number was measured against."""
        first = _rule_version(
            version=1,
            status=RuleVersionStatus.ACTIVE,
            effective_from=datetime.date(2001, 1, 1),
        )
        second = _rule_version(
            version=2,
            status=RuleVersionStatus.ACTIVE,
            effective_from=datetime.date(2001, 2, 1),
        )

        with pytest.raises(ValueError, match="all in force"):
            select_effective_rule_version([first, second], datetime.date(2001, 3, 1))

    @pytest.mark.parametrize(
        "status",
        [
            RuleVersionStatus.DRAFT,
            RuleVersionStatus.PENDING_APPROVAL,
            RuleVersionStatus.SUSPENDED,
            RuleVersionStatus.RETIRED,
            RuleVersionStatus.TEST_ONLY,
        ],
    )
    def test_only_an_active_version_is_ever_in_force(
        self, status: RuleVersionStatus
    ) -> None:
        version = _rule_version(
            version=1, status=status, effective_from=datetime.date(2001, 1, 1)
        )
        assert not is_in_force_on(version, datetime.date(2001, 2, 1))

    def test_an_undated_version_is_not_in_force(self) -> None:
        """An undated version would otherwise apply retroactively to every
        historical period."""
        version = _rule_version(version=1, status=RuleVersionStatus.ACTIVE)
        assert not is_in_force_on(version, datetime.date(2001, 2, 1))

    def test_test_only_is_never_publishable(self) -> None:
        assert not is_publishable(
            _rule_version(version=1, status=RuleVersionStatus.TEST_ONLY)
        )
        assert is_publishable(_rule_version(version=1, status=RuleVersionStatus.ACTIVE))


class TestSevenStepProtocol:
    def test_the_order_is_the_prompt_mestre_protocol(self) -> None:
        assert STEP_ORDER == (
            AnalysisStepCode.INGESTION,
            AnalysisStepCode.BASE_VALIDATION,
            AnalysisStepCode.CHAIN_RECONCILIATION,
            AnalysisStepCode.DETECTION,
            AnalysisStepCode.QUANTIFICATION,
            AnalysisStepCode.PRIORITIZATION,
            AnalysisStepCode.PUBLICATION,
        )

    def test_the_vocabulary_is_closed_at_seven(self) -> None:
        assert len(STEP_ORDER) == 7
        assert set(STEP_ORDER) == set(AnalysisStepCode)

    def test_publication_has_no_dependents(self) -> None:
        assert downstream_step_codes(AnalysisStepCode.PUBLICATION) == ()

    def test_base_validation_dependents_include_publication(self) -> None:
        """This is what makes S10 expressible as a blocked publication step."""
        assert downstream_step_codes(AnalysisStepCode.BASE_VALIDATION) == (
            AnalysisStepCode.CHAIN_RECONCILIATION,
            AnalysisStepCode.DETECTION,
            AnalysisStepCode.QUANTIFICATION,
            AnalysisStepCode.PRIORITIZATION,
            AnalysisStepCode.PUBLICATION,
        )

    def test_upstream_relation_is_strict(self) -> None:
        assert is_upstream_of(AnalysisStepCode.INGESTION, AnalysisStepCode.PUBLICATION)
        assert not is_upstream_of(
            AnalysisStepCode.PUBLICATION, AnalysisStepCode.INGESTION
        )
        assert not is_upstream_of(
            AnalysisStepCode.DETECTION, AnalysisStepCode.DETECTION
        )


class TestScopeContainment:
    """The containment rule behind domain-scoped blocking."""

    def test_a_scope_contains_itself(self) -> None:
        unit = uuid4()
        scope = StepScope(domain=RuleDomain.FINANCIAL, business_unit_id=unit)
        assert scope.contains(scope)

    def test_run_wide_contains_every_narrower_scope(self) -> None:
        run_wide = StepScope(domain=None, business_unit_id=None)
        assert run_wide.contains(
            StepScope(domain=RuleDomain.FLEET, business_unit_id=uuid4())
        )

    def test_a_narrower_scope_does_not_contain_run_wide(self) -> None:
        narrow = StepScope(domain=RuleDomain.FLEET, business_unit_id=uuid4())
        assert not narrow.contains(StepScope(domain=None, business_unit_id=None))

    def test_sibling_domains_contain_neither(self) -> None:
        unit = uuid4()
        financial = StepScope(domain=RuleDomain.FINANCIAL, business_unit_id=unit)
        fleet = StepScope(domain=RuleDomain.FLEET, business_unit_id=unit)
        assert not financial.contains(fleet)
        assert not fleet.contains(financial)

    def test_sibling_units_contain_neither(self) -> None:
        first = StepScope(domain=RuleDomain.FINANCIAL, business_unit_id=uuid4())
        second = StepScope(domain=RuleDomain.FINANCIAL, business_unit_id=uuid4())
        assert not first.contains(second)
        assert not second.contains(first)

    def test_a_domain_wide_scope_contains_that_domain_in_every_unit(self) -> None:
        domain_wide = StepScope(domain=RuleDomain.HR, business_unit_id=None)
        assert domain_wide.contains(
            StepScope(domain=RuleDomain.HR, business_unit_id=uuid4())
        )
        assert not domain_wide.contains(
            StepScope(domain=RuleDomain.FINANCIAL, business_unit_id=uuid4())
        )


class TestRunStatusRollUp:
    def test_mixed_success_and_failure_is_partial_not_failed(self) -> None:
        status = resolve_run_status(
            [
                _step(status=AnalysisStepStatus.PASSED),
                _step(status=AnalysisStepStatus.FAILED),
                _step(status=AnalysisStepStatus.BLOCKED),
            ]
        )
        assert status is AnalysisRunStatus.COMPLETED_WITH_BLOCKED_DOMAINS

    def test_only_failure_is_failed(self) -> None:
        status = resolve_run_status(
            [
                _step(status=AnalysisStepStatus.FAILED),
                _step(status=AnalysisStepStatus.BLOCKED),
            ]
        )
        assert status is AnalysisRunStatus.FAILED

    def test_all_passed_is_completed(self) -> None:
        assert (
            resolve_run_status([_step(status=AnalysisStepStatus.PASSED)])
            is AnalysisRunStatus.COMPLETED
        )

    def test_skipped_steps_do_not_make_a_run_fail(self) -> None:
        status = resolve_run_status(
            [
                _step(status=AnalysisStepStatus.PASSED),
                _step(status=AnalysisStepStatus.SKIPPED),
            ]
        )
        assert status is AnalysisRunStatus.COMPLETED

    def test_an_unfinished_step_keeps_the_run_running(self) -> None:
        for pending in (AnalysisStepStatus.PENDING, AnalysisStepStatus.RUNNING):
            status = resolve_run_status(
                [_step(status=AnalysisStepStatus.PASSED), _step(status=pending)]
            )
            assert status is AnalysisRunStatus.RUNNING

    def test_a_run_with_no_step_is_queued(self) -> None:
        assert resolve_run_status([]) is AnalysisRunStatus.QUEUED


class TestFailClosedMetadata:
    """The inverse assertion, at model level. Its database twin lives in the
    schema spec, so a hand-written migration cannot drift from the models."""

    def test_no_ton_table_declares_is_public(self) -> None:
        for table_name in TON_TABLE_NAMES:
            table = Base.metadata.tables[table_name]
            assert "is_public" not in table.columns

    def test_the_nine_003b_tables_are_still_mapped(self) -> None:
        """This slice's tables survive later slices. The exact whole-schema set is
        asserted in ``test_occurrence_projection.py``, which owns the 003c list."""
        ton_tables = {name for name in Base.metadata.tables if name.startswith("ton_")}
        assert set(TON_TABLE_NAMES) <= ton_tables

    def test_no_ton_model_writes_to_a_source_system(self) -> None:
        """The advisory boundary is enforced by absence: no column here can carry
        a write back into an ERP, a measurement, a billing record or a glosa."""
        forbidden_fragments = (
            "glosa",
            "erp_write",
            "billing_write",
            "measurement_write",
        )
        for table_name in TON_TABLE_NAMES:
            table = Base.metadata.tables[table_name]
            for column in table.columns:
                assert not any(
                    fragment in column.name for fragment in forbidden_fragments
                )


class TestClosedVocabularies:
    """Values fixed by readiness or the Prompt Mestre, asserted verbatim."""

    def test_rule_domain_vocabulary(self) -> None:
        assert {domain.value for domain in RuleDomain} == {
            "FINANCIAL",
            "OPERATIONAL",
            "CONTRACT",
            "FLEET",
            "HR",
            "PROCUREMENT",
            "COMPLIANCE",
            "AUDIT",
            "QUALITY",
        }

    def test_rule_kind_vocabulary(self) -> None:
        assert {kind.value for kind in RuleKind} == {
            "SANITY",
            "DETECTION",
            "BLIND_SPOT",
        }

    def test_rule_version_status_vocabulary(self) -> None:
        assert {status.value for status in RuleVersionStatus} == {
            "DRAFT",
            "PENDING_APPROVAL",
            "ACTIVE",
            "SUSPENDED",
            "RETIRED",
            "TEST_ONLY",
        }

    def test_nine_specialists_exactly(self) -> None:
        """Prompt Mestre §15: CFO, COO, FROTA, CONTRATOS, COMPLIANCE,
        PROCUREMENT, RH, AUDITOR, CEO."""
        assert {specialist.value for specialist in AnalysisSpecialist} == {
            "CFO",
            "COO",
            "FLEET",
            "CONTRACTS",
            "COMPLIANCE",
            "PROCUREMENT",
            "HR",
            "AUDITOR",
            "CEO",
        }
        assert len(AnalysisSpecialist) == 9

    def test_analysis_run_status_vocabulary(self) -> None:
        assert {status.value for status in AnalysisRunStatus} == {
            "QUEUED",
            "RUNNING",
            "COMPLETED",
            "COMPLETED_WITH_BLOCKED_DOMAINS",
            "FAILED",
            "TIMED_OUT",
            "CANCELLED",
        }

    def test_blocked_reason_vocabulary_is_not_broadened(self) -> None:
        assert {reason.value for reason in AnalysisStepBlockedReason} == {
            "PREREQUISITE_FAILED",
            "MISSING_SOURCE",
            "MISSING_CONTRACT_MASTER",
            "BASE_REPROVED",
            "AWAITING_HUMAN_DECISION",
        }

    def test_step_status_vocabulary(self) -> None:
        assert {status.value for status in AnalysisStepStatus} == {
            "PENDING",
            "RUNNING",
            "PASSED",
            "FAILED",
            "BLOCKED",
            "SKIPPED",
        }

    def test_business_unit_kind_distinguishes_non_operational(self) -> None:
        """§3.3's consolidation rule keeps a non-operational cost centre out of a
        profitability ranking, which needs this member to exist."""
        assert BusinessUnitKind.NON_OPERATIONAL in BusinessUnitKind
        assert {kind.value for kind in BusinessUnitKind} == {
            "OPERATIONAL",
            "IMPLANTATION",
            "PROSPECT",
            "NON_OPERATIONAL",
        }

    def test_contract_status_carries_under_judgement(self) -> None:
        """Rule S7 needs it: an unsigned contract must not enter backlog,
        revenue or projection."""
        assert ContractStatus.UNDER_JUDGEMENT in ContractStatus

    def test_enum_names_equal_their_values(self) -> None:
        """Keeps the CHECK constraints written against literal strings correct
        whichever storage convention a later reader assumes."""
        for enum_type in (
            RuleDomain,
            RuleKind,
            RuleVersionStatus,
            AnalysisRunStatus,
            AnalysisStepStatus,
            AnalysisStepBlockedReason,
            AnalysisStepCode,
            AnalysisSpecialist,
            BusinessUnitKind,
            ContractStatus,
        ):
            for member in enum_type:
                assert member.name == member.value


class TestPermissionTokens:
    def test_the_three_003b_tokens_exist(self) -> None:
        assert Permission.READ_TON_ANALYSIS.value == "read:ton_analysis"
        assert Permission.MANAGE_TON_RULES.value == "manage:ton_rules"
        assert Permission.MANAGE_TON_BUSINESS_UNITS.value == "manage:ton_business_units"

    def test_no_003d_token_is_added_early(self) -> None:
        """A grantable permission whose resource does not exist authorizes
        nothing and misleads an administrator.

        The occurrence tokens arrived with their tables in 003c. The report tokens
        wait for 003d.
        """
        for permission in Permission:
            if "ton" not in permission.value:
                continue
            assert "report" not in permission.value

    def test_manage_ton_rules_is_not_a_scoped_manager_permission(self) -> None:
        """Approving or activating a rule version has company-wide effect, so a
        business-unit manager must never resolve SCOPED authority for it."""
        assert Permission.MANAGE_TON_RULES not in SCOPED_MANAGER_PERMISSIONS
        assert (
            Permission.MANAGE_TON_RULES.value not in SCOPED_MANAGER_PERMISSIONS_EXPANDED
        )

    def test_no_ton_token_is_scopable(self) -> None:
        for permission in Permission:
            if "ton" not in permission.value:
                continue
            assert permission not in SCOPED_MANAGER_PERMISSIONS
            assert permission.value not in SCOPED_MANAGER_PERMISSIONS_EXPANDED

    def test_every_ton_token_is_grantable_through_the_registry(self) -> None:
        registered = {
            permission
            for entry in PERMISSION_REGISTRY
            for permission in entry.permissions
        }
        for permission in Permission:
            if "ton" not in permission.value:
                continue
            assert permission in registered, (
                f"{permission.value} has no PERMISSION_REGISTRY entry, so the "
                "Groups administration cannot grant it"
            )

    def test_no_ton_token_is_implied(self) -> None:
        """Implied tokens are never persisted, so a TON capability must be an
        explicit grant."""
        for permission in Permission:
            if "ton" in permission.value:
                assert permission not in Permission.IMPLIED


class TestModuleBoundaries:
    def test_no_report_or_audit_model_exists(self) -> None:
        for forbidden in (
            "TonReport",
            "TonReportRevision",
            "TonReport__UserGroup",
            "TonAuditEvent",
        ):
            assert not hasattr(ton_models, forbidden), f"{forbidden} belongs to 003d"

    def test_the_nine_003b_models_exist(self) -> None:
        for expected in (
            "BusinessUnit",
            "Contract",
            "Rule",
            "RuleVersion",
            "SourceSnapshot",
            "AnalysisRun",
            "AnalysisRunRuleVersion",
            "AnalysisRun__SourceSnapshot",
            "AnalysisStep",
        ):
            assert hasattr(ton_models, expected)
