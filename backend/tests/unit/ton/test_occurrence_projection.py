"""Pure identity and projection logic for TON occurrences — Plan 003c.

No database, no session, no LLM. What lives here is the logic that must hold
before anything is persisted: the deterministic identity digest, its
canonicalisation, the event-to-status projection, the closed vocabularies, and the
model-level inverse assertions.

The database-level counterparts — uniqueness, the human-only CHECK, decimal column
types, the ACL predicates — are in ``tests/external_dependency_unit/ton/``, because
a constraint only exists once the migration ran.
"""

import datetime
import inspect
from uuid import uuid4

import pytest

from onyx.auth.permissions import (
    IMPLIED_PERMISSIONS,
    PERMISSION_REGISTRY,
    SCOPED_MANAGER_PERMISSIONS,
    SCOPED_MANAGER_PERMISSIONS_EXPANDED,
    resolve_effective_permissions,
)
from onyx.db.enums import Permission
from onyx.db.models import Base
from onyx.db.ton import models as ton_models
from onyx.db.ton.enums import (
    AssignmentStatus,
    FindingKind,
    ImpactCategory,
    ImpactConfidence,
    ImpactMethod,
    InterpretationFailureClass,
    InterpretationInputScope,
    OccurrenceActorKind,
    OccurrenceCriticality,
    OccurrenceLedgerKind,
    OccurrenceStatus,
    OccurrenceTransition,
    OccurrenceVerificationResult,
    RedactionLevel,
    TonSharePermission,
    UnitCostSource,
)
from onyx.db.ton.identity import (
    CASE_INSENSITIVE_COMPONENTS,
    IDENTITY_SCHEME,
    canonical_identity_payload,
    canonicalize_identity_value,
    compute_identity_key,
)
from onyx.db.ton.models import (
    Finding,
    FindingInterpretation,
    Occurrence,
    OccurrenceEvent,
)
from onyx.db.ton.occurrences import (
    CLOSED_STATUSES,
    HUMAN_ONLY_TRANSITIONS,
    OPEN_STATUSES,
    SYSTEM_ALLOWED_TRANSITIONS,
    TRANSITION_RESULTING_STATUS,
    USER_REQUIRED_TRANSITIONS,
    project_from_events,
    projection_matches_history,
    resolve_post_resolution_policy,
)

# The twelve tables Plan 003c adds, plus the nine from 003b and the nine from
# 003d. The inverse assertions run over the whole set, so a table added by a later
# slice cannot escape them by being listed only in that slice's own file.
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
TON_TABLE_NAMES: tuple[str, ...] = TON_003B_TABLES + TON_003C_TABLES + TON_003D_TABLES

BASE_COMPONENTS = ["rule_code", "business_unit_id", "period"]
BASE_VALUES: dict[str, object | None] = {
    "business_unit_id": "11111111-1111-1111-1111-111111111111",
    "period": "2001-01",
}


def _event(
    transition: OccurrenceTransition,
    *,
    sequence_no: int,
    occurred_at: datetime.datetime | None = None,
    resulting_status: OccurrenceStatus = OccurrenceStatus.NEW,
) -> OccurrenceEvent:
    """An unpersisted event. Enough for the pure projection logic."""
    return OccurrenceEvent(
        sequence_no=sequence_no,
        transition=transition,
        resulting_status=resulting_status,
        actor_kind=OccurrenceActorKind.SYSTEM,
        occurred_at=occurred_at
        or datetime.datetime(2001, 1, sequence_no, tzinfo=datetime.UTC),
    )


class TestIdentityDigest:
    def test_the_digest_is_deterministic(self) -> None:
        first = compute_identity_key(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        second = compute_identity_key(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        assert first == second

    def test_the_digest_is_opaque_and_scheme_prefixed(self) -> None:
        """Opaque so nothing can parse a business value back out of it; prefixed so
        a future canonicalisation change breaks recurrence visibly rather than
        silently rematching cases under new rules."""
        key = compute_identity_key(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        assert key.startswith(f"{IDENTITY_SCHEME}:")
        assert "SYN-RULE-1" not in key
        assert "2001-01" not in key
        assert len(key) == len(IDENTITY_SCHEME) + 1 + 64

    def test_a_different_component_value_yields_a_different_digest(self) -> None:
        first = compute_identity_key(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        second = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=BASE_COMPONENTS,
            values={**BASE_VALUES, "period": "2001-02"},
        )
        assert first != second

    def test_a_different_rule_code_yields_a_different_digest(self) -> None:
        first = compute_identity_key(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        second = compute_identity_key(
            rule_code="SYN-RULE-2", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        assert first != second

    def test_declaring_the_components_in_a_different_order_is_the_same_identity(
        self,
    ) -> None:
        """The canonical order lives in the identity module, not in the caller, so
        two rule versions listing the same dimensions differently still produce one
        case."""
        forward = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=["rule_code", "business_unit_id", "period"],
            values=BASE_VALUES,
        )
        shuffled = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=["period", "business_unit_id", "rule_code"],
            values=BASE_VALUES,
        )
        assert forward == shuffled

    def test_rule_code_is_always_included(self) -> None:
        """Readiness §7: identity includes the rule code and never the rule
        version. It is emitted whether or not the version declared it."""
        payload = canonical_identity_payload(
            rule_code="SYN-RULE-1",
            components=["period"],
            values={"period": "2001-01"},
        )
        assert payload.startswith("rule_code=syn-rule-1")

    def test_the_rule_version_is_never_part_of_identity(self) -> None:
        """If it were, every threshold change would reset recurrence tracking on
        every open case."""
        payload = canonical_identity_payload(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        assert "rule_version" not in payload
        assert "version" not in payload


class TestIdentityCanonicalisation:
    def test_whitespace_is_trimmed(self) -> None:
        assert compute_identity_key(
            rule_code="SYN-RULE-1",
            components=BASE_COMPONENTS,
            values={**BASE_VALUES, "period": "  2001-01  "},
        ) == compute_identity_key(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )

    def test_unicode_is_normalised_to_nfc(self) -> None:
        """Two byte sequences for the same character must not become two cases."""
        decomposed = "Mossoro\u0301"  # o + combining acute
        composed = "Mossor\u00f3"  # precomposed ó
        components = ["rule_code", "source_system"]

        assert compute_identity_key(
            rule_code="SYN-RULE-1",
            components=components,
            values={"source_system": decomposed},
        ) == compute_identity_key(
            rule_code="SYN-RULE-1",
            components=components,
            values={"source_system": composed},
        )

    def test_a_case_insensitive_component_is_case_folded(self) -> None:
        components = ["rule_code", "nature_group"]
        assert compute_identity_key(
            rule_code="SYN-RULE-1",
            components=components,
            values={"nature_group": "Synthetic Group"},
        ) == compute_identity_key(
            rule_code="SYN-RULE-1",
            components=components,
            values={"nature_group": "synthetic group"},
        )

    def test_a_case_sensitive_component_keeps_its_case(self) -> None:
        """An opaque external key may distinguish two records by case, and merging
        two distinct source rows is worse than splitting one case in two."""
        components = ["rule_code", "source_record_key"]
        assert compute_identity_key(
            rule_code="SYN-RULE-1",
            components=components,
            values={"source_record_key": "ABC-1"},
        ) != compute_identity_key(
            rule_code="SYN-RULE-1",
            components=components,
            values={"source_record_key": "abc-1"},
        )

    def test_the_declared_case_insensitive_set_is_the_controlled_codes(self) -> None:
        from onyx.db.ton.enums import IdentityComponent

        assert CASE_INSENSITIVE_COMPONENTS == frozenset(
            {
                IdentityComponent.RULE_CODE,
                IdentityComponent.BUSINESS_UNIT_ID,
                IdentityComponent.CONTRACT_ID,
                IdentityComponent.NATURE_GROUP,
                IdentityComponent.SOURCE_SYSTEM,
            }
        )
        assert IdentityComponent.SOURCE_RECORD_KEY not in CASE_INSENSITIVE_COMPONENTS
        assert IdentityComponent.EMPLOYEE_KEY_MASKED not in CASE_INSENSITIVE_COMPONENTS

    def test_an_absent_component_is_omitted_not_emitted_empty(self) -> None:
        """Readiness §7. Otherwise "no contract" and "contract ''" would be two
        different cases."""
        payload = canonical_identity_payload(
            rule_code="SYN-RULE-1",
            components=["rule_code", "contract_id", "period"],
            values={"contract_id": None, "period": "2001-01"},
        )
        assert "contract_id" not in payload
        assert "=\x1f" not in payload

    def test_a_blank_component_is_treated_as_absent(self) -> None:
        with_blank = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=["rule_code", "contract_id", "period"],
            values={"contract_id": "   ", "period": "2001-01"},
        )
        with_none = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=["rule_code", "contract_id", "period"],
            values={"contract_id": None, "period": "2001-01"},
        )
        assert with_blank == with_none

    def test_the_separator_cannot_be_confused_with_a_value(self) -> None:
        """A printable separator such as ``|`` could appear inside a source record
        key and let two different tuples serialise identically."""
        payload = canonical_identity_payload(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        assert "\x1f" in payload

    def test_shifting_a_value_between_components_changes_the_digest(self) -> None:
        """The ``name=value`` serialisation is what makes this hold: bare values
        joined by a separator would collide."""
        first = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=["rule_code", "vehicle_key", "supplier_key"],
            values={"vehicle_key": "A", "supplier_key": "B"},
        )
        second = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=["rule_code", "vehicle_key", "supplier_key"],
            values={"vehicle_key": "B", "supplier_key": "A"},
        )
        assert first != second

    @pytest.mark.parametrize("value", [None, "", "   ", "\n\t"])
    def test_canonicalize_treats_empty_values_as_absent(
        self, value: str | None
    ) -> None:
        from onyx.db.ton.enums import IdentityComponent

        assert canonicalize_identity_value(IdentityComponent.PERIOD, value) is None


class TestIdentityRejectsInvalidInput:
    def test_an_undeclared_dimension_value_is_refused(self) -> None:
        """Identity follows ``RuleVersion.identity_components``, not the caller."""
        with pytest.raises(ValueError, match="does not\n?\\s*declare|not declare"):
            compute_identity_key(
                rule_code="SYN-RULE-1",
                components=["rule_code", "period"],
                values={"period": "2001-01", "vehicle_key": "smuggled"},
            )

    def test_a_dimension_outside_the_closed_vocabulary_is_refused(self) -> None:
        """The guard that stops an LLM-proposed identity dimension entering the
        domain."""
        with pytest.raises(ValueError, match="closed vocabulary|not an approved"):
            compute_identity_key(
                rule_code="SYN-RULE-1",
                components=["rule_code", "period"],
                values={"period": "2001-01", "ai_similarity_cluster": "x"},
            )

    def test_an_empty_component_list_is_refused(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            compute_identity_key(rule_code="SYN-RULE-1", components=[], values={})

    def test_a_blank_rule_code_is_refused(self) -> None:
        with pytest.raises(ValueError, match="rule_code is required"):
            compute_identity_key(
                rule_code="   ", components=BASE_COMPONENTS, values=BASE_VALUES
            )

    def test_a_generation_below_one_is_refused(self) -> None:
        with pytest.raises(ValueError, match="starts at 1"):
            compute_identity_key(
                rule_code="SYN-RULE-1",
                components=BASE_COMPONENTS,
                values=BASE_VALUES,
                supersede_generation=0,
            )

    def test_no_text_field_is_an_identity_input(self) -> None:
        """Text similarity is not a deduplication mechanism in this domain, so
        there is no parameter that could carry it."""
        signature = inspect.signature(compute_identity_key)
        for forbidden in (
            "title",
            "description",
            "summary",
            "probable_cause",
            "interpretation",
            "embedding",
        ):
            assert forbidden not in signature.parameters


class TestSupersedeGeneration:
    def test_generation_one_equals_the_plain_canonical_digest(self) -> None:
        """So the ordinary case — never superseded — is exactly the readiness §7
        contract."""
        plain = compute_identity_key(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        explicit = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=BASE_COMPONENTS,
            values=BASE_VALUES,
            supersede_generation=1,
        )
        assert plain == explicit

    def test_a_later_generation_yields_a_distinct_key(self) -> None:
        """What lets ``UNIQUE(identity_key)`` and SUPERSEDE_WITH_NEW_OCCURRENCE
        coexist."""
        first = compute_identity_key(
            rule_code="SYN-RULE-1", components=BASE_COMPONENTS, values=BASE_VALUES
        )
        second = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=BASE_COMPONENTS,
            values=BASE_VALUES,
            supersede_generation=2,
        )
        third = compute_identity_key(
            rule_code="SYN-RULE-1",
            components=BASE_COMPONENTS,
            values=BASE_VALUES,
            supersede_generation=3,
        )
        assert len({first, second, third}) == 3

    def test_the_generation_is_not_an_identity_component(self) -> None:
        """It is not a business dimension, so it stays out of the closed
        vocabulary that a rule version may declare."""
        from onyx.db.ton.enums import IdentityComponent

        assert "supersede_generation" not in {
            member.value for member in IdentityComponent
        }


class TestTransitionStatusProjection:
    def test_every_transition_is_classified(self) -> None:
        """No transition may be authorized by omission."""
        classified = (
            SYSTEM_ALLOWED_TRANSITIONS
            | HUMAN_ONLY_TRANSITIONS
            | USER_REQUIRED_TRANSITIONS
        )
        assert classified == set(OccurrenceTransition)

    def test_the_three_authorization_classes_are_disjoint(self) -> None:
        assert SYSTEM_ALLOWED_TRANSITIONS & HUMAN_ONLY_TRANSITIONS == set()
        assert SYSTEM_ALLOWED_TRANSITIONS & USER_REQUIRED_TRANSITIONS == set()
        assert HUMAN_ONLY_TRANSITIONS & USER_REQUIRED_TRANSITIONS == set()

    def test_the_human_only_set_matches_readiness_verbatim(self) -> None:
        assert {member.value for member in HUMAN_ONLY_TRANSITIONS} == {
            "RESOLVE_CRITICAL",
            "ACCEPT_RISK",
            "DISMISS",
            "ASSERT_NONCOMPLIANCE",
            "PROMOTE_INTERPRETATION",
            "OVERRIDE_DETERMINISTIC_VALUE",
        }

    def test_the_system_allowed_set_matches_the_prompt_mestre_boundary(self) -> None:
        assert {member.value for member in SYSTEM_ALLOWED_TRANSITIONS} == {
            "DETECT",
            "REPEAT_DETECTED",
            "REOPENED",
            "ESCALATE_BY_CYCLE_RULE",
            "VERIFICATION_PASSED",
            "VERIFICATION_FAILED",
            "SUPERSEDE",
        }

    def test_closing_a_case_is_not_a_system_transition(self) -> None:
        assert OccurrenceTransition.RESOLVED not in SYSTEM_ALLOWED_TRANSITIONS
        assert OccurrenceTransition.RESOLVED in USER_REQUIRED_TRANSITIONS

    def test_open_and_closed_statuses_partition_the_vocabulary(self) -> None:
        assert OPEN_STATUSES | CLOSED_STATUSES == set(OccurrenceStatus)
        assert OPEN_STATUSES & CLOSED_STATUSES == set()

    def test_every_status_is_reachable_by_some_transition(self) -> None:
        """A status nothing produces would be a projection the history cannot
        explain."""
        assert set(TRANSITION_RESULTING_STATUS.values()) == set(OccurrenceStatus)


class TestProjectFromEvents:
    def test_an_empty_history_projects_nothing(self) -> None:
        """Inventing ``NEW`` here would hide the anomaly of a case with no
        events."""
        assert project_from_events([]) is None
        assert not projection_matches_history(Occurrence(), [])

    def test_a_single_detection_projects_one_cycle(self) -> None:
        projection = project_from_events(
            [_event(OccurrenceTransition.DETECT, sequence_no=1)]
        )
        assert projection is not None
        assert projection.status is OccurrenceStatus.NEW
        assert projection.detection_count == 1
        assert projection.open_cycle_count == 1
        assert projection.resolved_at is None

    def test_repeats_bump_detections_without_opening_a_cycle(self) -> None:
        projection = project_from_events(
            [
                _event(OccurrenceTransition.DETECT, sequence_no=1),
                _event(OccurrenceTransition.REPEAT_DETECTED, sequence_no=2),
                _event(OccurrenceTransition.REPEAT_DETECTED, sequence_no=3),
            ]
        )
        assert projection is not None
        assert projection.detection_count == 3
        assert projection.open_cycle_count == 1

    def test_a_reopen_opens_a_cycle_and_clears_the_resolution(self) -> None:
        projection = project_from_events(
            [
                _event(OccurrenceTransition.DETECT, sequence_no=1),
                _event(OccurrenceTransition.RESOLVED, sequence_no=2),
                _event(OccurrenceTransition.REOPENED, sequence_no=3),
            ]
        )
        assert projection is not None
        assert projection.status is OccurrenceStatus.REOPENED
        assert projection.open_cycle_count == 2
        assert projection.detection_count == 2
        assert projection.resolved_at is None

    def test_a_resolution_records_when(self) -> None:
        resolved_at = datetime.datetime(2001, 6, 1, tzinfo=datetime.UTC)
        projection = project_from_events(
            [
                _event(OccurrenceTransition.DETECT, sequence_no=1),
                _event(
                    OccurrenceTransition.RESOLVED,
                    sequence_no=2,
                    occurred_at=resolved_at,
                ),
            ]
        )
        assert projection is not None
        assert projection.status is OccurrenceStatus.RESOLVED
        assert projection.resolved_at == resolved_at

    def test_the_projection_is_order_independent_of_the_input_list(self) -> None:
        """It sorts by ``sequence_no``, so a caller that hands the events over in
        the wrong order still gets the right answer."""
        events = [
            _event(OccurrenceTransition.REOPENED, sequence_no=3),
            _event(OccurrenceTransition.DETECT, sequence_no=1),
            _event(OccurrenceTransition.RESOLVED, sequence_no=2),
        ]
        assert project_from_events(events) == project_from_events(
            sorted(events, key=lambda event: event.sequence_no)
        )

    def test_an_escalation_does_not_move_the_status(self) -> None:
        projection = project_from_events(
            [
                _event(OccurrenceTransition.DETECT, sequence_no=1),
                _event(OccurrenceTransition.ESCALATE_BY_CYCLE_RULE, sequence_no=2),
            ]
        )
        assert projection is not None
        assert projection.status is OccurrenceStatus.NEW

    def test_a_verification_does_not_move_the_status(self) -> None:
        projection = project_from_events(
            [
                _event(OccurrenceTransition.DETECT, sequence_no=1),
                _event(OccurrenceTransition.RESOLVED, sequence_no=2),
                _event(OccurrenceTransition.VERIFICATION_PASSED, sequence_no=3),
            ]
        )
        assert projection is not None
        assert projection.status is OccurrenceStatus.RESOLVED

    @pytest.mark.parametrize(
        ("transition", "expected"),
        [
            (OccurrenceTransition.ACCEPT_RISK, OccurrenceStatus.RISK_ACCEPTED),
            (OccurrenceTransition.DISMISS, OccurrenceStatus.DISMISSED),
            (
                OccurrenceTransition.ASSERT_NONCOMPLIANCE,
                OccurrenceStatus.CONFIRMED,
            ),
            (OccurrenceTransition.SUPERSEDE, OccurrenceStatus.SUPERSEDED),
            (
                OccurrenceTransition.RESOLVE_CRITICAL,
                OccurrenceStatus.RESOLVED,
            ),
        ],
    )
    def test_each_terminal_transition_projects_its_status(
        self, transition: OccurrenceTransition, expected: OccurrenceStatus
    ) -> None:
        projection = project_from_events(
            [
                _event(OccurrenceTransition.DETECT, sequence_no=1),
                _event(transition, sequence_no=2),
            ]
        )
        assert projection is not None
        assert projection.status is expected


class TestForcedSupersede:
    def test_a_changed_rule_version_forces_supersede(self) -> None:
        """Two detections measured against different thresholds are not the same
        measurement, so the declared policy is overridden."""
        from onyx.db.ton.enums import PostResolutionPolicy
        from onyx.db.ton.models import RuleVersion

        resolved_version_id = uuid4()
        occurrence = Occurrence(current_rule_version_id=resolved_version_id)
        detecting = RuleVersion(
            post_resolution_policy=PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )
        detecting.id = uuid4()

        assert (
            resolve_post_resolution_policy(
                occurrence=occurrence, detecting_rule_version=detecting
            )
            is PostResolutionPolicy.SUPERSEDE_WITH_NEW_OCCURRENCE
        )

    def test_the_same_rule_version_honours_the_declared_policy(self) -> None:
        from onyx.db.ton.enums import PostResolutionPolicy
        from onyx.db.ton.models import RuleVersion

        version_id = uuid4()
        occurrence = Occurrence(current_rule_version_id=version_id)
        detecting = RuleVersion(
            post_resolution_policy=PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )
        detecting.id = version_id

        assert (
            resolve_post_resolution_policy(
                occurrence=occurrence, detecting_rule_version=detecting
            )
            is PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
        )

    def test_there_is_no_implicit_default_policy(self) -> None:
        """``post_resolution_policy`` is NOT NULL on the rule version, so the
        executor never chooses silently."""
        from onyx.db.ton.models import RuleVersion

        column = RuleVersion.__table__.columns["post_resolution_policy"]
        assert column.nullable is False
        assert column.default is None
        assert column.server_default is None


class TestFailClosedMetadata:
    """Model-level inverse assertions. Their database twins live in the schema
    spec, so a hand-written migration cannot drift from the models."""

    def test_no_ton_table_declares_is_public(self) -> None:
        for table_name in TON_TABLE_NAMES:
            table = Base.metadata.tables[table_name]
            assert "is_public" not in table.columns

    def test_no_ton_table_declares_a_permissive_visibility_column(self) -> None:
        forbidden = {"is_public", "public", "is_global", "public_permission"}
        for table_name in TON_TABLE_NAMES:
            table = Base.metadata.tables[table_name]
            assert set(table.columns.keys()) & forbidden == set()

    def test_the_metadata_holds_exactly_the_thirty_ton_tables(self) -> None:
        """Nine from 003b, twelve from 003c, nine from 003d. Measured against the
        mapper, so a model added without being classified fails here."""
        ton_tables = {name for name in Base.metadata.tables if name.startswith("ton_")}
        assert ton_tables == set(TON_TABLE_NAMES)
        assert len(TON_TABLE_NAMES) == 30

    def test_no_ton_model_writes_to_a_source_system(self) -> None:
        """The advisory boundary is enforced by absence: no column here can carry
        a write back into an ERP, a measurement, a billing record or a glosa."""
        forbidden_fragments = (
            "glosa",
            "erp_write",
            "billing_write",
            "measurement_write",
            "push_to_",
            "sync_to_",
        )
        for table_name in TON_TABLE_NAMES:
            table = Base.metadata.tables[table_name]
            for column in table.columns:
                assert not any(
                    fragment in column.name for fragment in forbidden_fragments
                )

    def test_exactly_four_acl_junctions_exist(self) -> None:
        """``TonReport__UserGroup`` arrived with its table in 003d, completing the
        set readiness §10 specifies (decision D-043)."""
        junctions = {
            name
            for name in Base.metadata.tables
            if name.startswith("ton_") and "__user_group" in name
        }
        assert junctions == {
            "ton_business_unit__user_group",
            "ton_contract__user_group",
            "ton_occurrence__user_group",
            "ton_report__user_group",
        }


class TestFindingImmutability:
    def test_finding_carries_no_lifecycle_status(self) -> None:
        """Lifecycle belongs to the occurrence, narrative to the interpretation."""
        columns = set(Finding.__table__.columns.keys())
        assert "status" not in columns
        assert "resolved_at" not in columns
        assert "criticality" not in columns
        assert "interpretation_status" in columns

    def test_finding_references_the_rule_version_not_the_rule(self) -> None:
        columns = set(Finding.__table__.columns.keys())
        assert "rule_version_id" in columns
        assert "rule_id" not in columns

    def test_the_findings_module_exposes_no_update_or_delete(self) -> None:
        """Immutability is enforced by the absence of a write path."""
        from onyx.db.ton import findings

        for name in dir(findings):
            assert not name.startswith("update_"), f"{name} would mutate a finding"
            assert not name.startswith("delete_"), f"{name} would remove a finding"


class TestInterpretationStoresNoHiddenOutput:
    def test_no_interpretation_column_could_hold_a_transcript(self) -> None:
        forbidden_fragments = (
            "chain_of_thought",
            "reasoning",
            "raw_response",
            "raw_prompt",
            "prompt_body",
            "prompt_text",
            "transcript",
            "completion",
            "messages",
            "thinking",
        )
        for column in FindingInterpretation.__table__.columns:
            assert not any(
                fragment in column.name for fragment in forbidden_fragments
            ), f"{column.name} could hold hidden model output"

    def test_proposals_are_named_as_proposals(self) -> None:
        """A field called ``criticality`` on an interpretation row would invite a
        caller to treat model output as decided."""
        columns = set(FindingInterpretation.__table__.columns.keys())
        assert "proposed_criticality" in columns
        assert "proposed_nc_code" in columns
        assert "criticality" not in columns
        assert "nc_code" not in columns

    def test_the_interpretation_states_are_the_readiness_vocabulary(self) -> None:
        from onyx.db.ton.enums import InterpretationStatus

        assert {status.value for status in InterpretationStatus} == {
            "NOT_REQUIRED",
            "PENDING",
            "RUNNING",
            "COMPLETED",
            "FAILED",
        }


class TestClosed003cVocabularies:
    def test_finding_kind_vocabulary(self) -> None:
        assert {kind.value for kind in FindingKind} == {
            "DETECTION",
            "SANITY_VIOLATION",
            "BLIND_SPOT",
        }

    def test_criticality_is_the_single_four_level_scale(self) -> None:
        """Prompt Mestre §10 forbids a parallel scale: 🔴 Crítico, 🟠 Alto,
        🟡 Médio, 🟢 Monitoramento."""
        assert {level.value for level in OccurrenceCriticality} == {
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "MONITORING",
        }
        assert len(OccurrenceCriticality) == 4

    def test_no_second_severity_scale_exists(self) -> None:
        """An inverse assertion over the TON enum module."""
        from onyx.db.ton import enums

        severity_enums = {
            name
            for name in dir(enums)
            if any(word in name.lower() for word in ("severity", "priority", "urgency"))
        }
        assert severity_enums == set()

    def test_ledger_kind_is_a_discriminator_not_a_table(self) -> None:
        assert {kind.value for kind in OccurrenceLedgerKind} == {
            "EXCEPTION",
            "OPPORTUNITY",
        }
        assert not [
            name for name in Base.metadata.tables if "opportunity" in name.lower()
        ]

    def test_the_seven_impact_categories(self) -> None:
        assert {category.value for category in ImpactCategory} == {
            "POTENTIAL_SAVING",
            "AVOIDED_LOSS",
            "RECOVERABLE_REVENUE",
            "UNBILLED_REVENUE",
            "EXCESS_COST",
            "FINANCIAL_RISK",
            "MARGIN_OPPORTUNITY",
        }
        assert len(ImpactCategory) == 7

    def test_impact_confidence_keeps_the_readiness_literals(self) -> None:
        """Readiness §13 states the ROI rule as ``confidence <> 'BAIXA'``, so the
        stored value and the aggregation rule cannot drift."""
        assert {level.value for level in ImpactConfidence} == {
            "ALTA",
            "MEDIA",
            "BAIXA",
        }

    def test_the_unit_cost_preference_order_is_representable(self) -> None:
        assert {source.value for source in UnitCostSource} == {
            "CONTRACT_DOTACAO",
            "OWN_UNIT_TRAILING_3M",
            "COMPARABLE_UNIT_MEDIAN",
            "NOT_APPLICABLE",
        }

    def test_impact_method_vocabulary(self) -> None:
        assert {method.value for method in ImpactMethod} == {
            "OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST",
            "DIRECT_SOURCE_AMOUNT",
            "VALUE_AT_RISK",
        }

    def test_interpretation_input_scope_vocabulary(self) -> None:
        assert {scope.value for scope in InterpretationInputScope} == {
            "STRUCTURED_ONLY",
            "MASKED_EXCERPT",
            "FULL_EVIDENCE",
        }

    def test_interpretation_failure_class_vocabulary(self) -> None:
        assert {failure.value for failure in InterpretationFailureClass} == {
            "PROVIDER_UNAVAILABLE",
            "TIMEOUT",
            "MALFORMED_OUTPUT",
            "POLICY_REFUSAL",
            "INSUFFICIENT_EVIDENCE",
        }

    def test_share_permission_is_viewer_or_editor(self) -> None:
        assert {level.value for level in TonSharePermission} == {"VIEWER", "EDITOR"}

    def test_actor_kind_is_user_or_system(self) -> None:
        assert {kind.value for kind in OccurrenceActorKind} == {"USER", "SYSTEM"}

    def test_003c_enum_names_equal_their_values(self) -> None:
        """Keeps the CHECK constraints written against literal strings correct
        whichever storage convention a later reader assumes."""
        for enum_type in (
            FindingKind,
            OccurrenceLedgerKind,
            OccurrenceCriticality,
            OccurrenceStatus,
            OccurrenceTransition,
            OccurrenceActorKind,
            OccurrenceVerificationResult,
            ImpactCategory,
            ImpactConfidence,
            ImpactMethod,
            UnitCostSource,
            AssignmentStatus,
            RedactionLevel,
            InterpretationInputScope,
            InterpretationFailureClass,
            TonSharePermission,
        ):
            for member in enum_type:
                assert member.name == member.value


class TestOccurrencePermissionTokens:
    def test_the_two_003c_tokens_exist(self) -> None:
        assert Permission.READ_TON_OCCURRENCES.value == "read:ton_occurrences"
        assert Permission.MANAGE_TON_OCCURRENCES.value == "manage:ton_occurrences"

    def test_manage_implies_read(self) -> None:
        implied = IMPLIED_PERMISSIONS[Permission.MANAGE_TON_OCCURRENCES.value]
        assert Permission.READ_TON_OCCURRENCES.value in implied

    def test_no_ton_token_is_scopable(self) -> None:
        """Group-manager scope is a different axis from a TON share level.
        Overlapping them would let managing a group confer authority over cases
        merely shared with it."""
        for permission in Permission:
            if "ton" not in permission.value:
                continue
            assert permission not in SCOPED_MANAGER_PERMISSIONS
            assert permission.value not in SCOPED_MANAGER_PERMISSIONS_EXPANDED

    def test_the_manage_implication_does_not_leak_into_the_scoped_bundle(self) -> None:
        assert (
            Permission.READ_TON_OCCURRENCES.value
            not in SCOPED_MANAGER_PERMISSIONS_EXPANDED
        )

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

    def test_the_report_tokens_arrived_with_their_table(self) -> None:
        """A grantable permission whose resource does not exist authorizes nothing
        while telling an administrator otherwise. The report tokens waited for
        003d, and ``ton_report`` now exists."""
        assert Permission.READ_TON_REPORTS.value == "read:ton_reports"
        assert Permission.MANAGE_TON_REPORTS.value == "manage:ton_reports"
        assert "ton_report" in Base.metadata.tables
        assert "ton_report__user_group" in Base.metadata.tables

    def test_manage_ton_rules_stays_out_of_the_scoped_bundle(self) -> None:
        """003b's decision, re-asserted: activating a threshold is a company-wide
        act."""
        assert Permission.MANAGE_TON_RULES not in SCOPED_MANAGER_PERMISSIONS
        assert (
            Permission.MANAGE_TON_RULES.value not in SCOPED_MANAGER_PERMISSIONS_EXPANDED
        )

    def test_admin_still_resolves_every_ton_token(self) -> None:
        expanded = resolve_effective_permissions(
            {Permission.FULL_ADMIN_PANEL_ACCESS.value}
        )
        for permission in Permission:
            if "ton" in permission.value:
                assert permission.value in expanded


class TestModuleBoundaries:
    def test_the_twelve_003c_models_exist(self) -> None:
        for expected in (
            "Finding",
            "FindingEvidence",
            "FindingInterpretation",
            "Occurrence",
            "OccurrenceEvent",
            "OccurrenceImpact",
            "OccurrenceAssignment",
            "OccurrenceNote",
            "OccurrenceImpactedDomain",
            "BusinessUnit__UserGroup",
            "Contract__UserGroup",
            "Occurrence__UserGroup",
        ):
            assert hasattr(ton_models, expected)

    def test_the_nine_003d_models_exist(self) -> None:
        for expected in (
            "TonReport",
            "TonReportRevision",
            "TonReportRevision__AnalysisRun",
            "TonReportRevision__Occurrence",
            "TonReportRevision__Finding",
            "TonReportRevision__RuleVersion",
            "TonReportRevision__SourceSnapshot",
            "TonReport__UserGroup",
            "TonAuditEvent",
        ):
            assert hasattr(ton_models, expected)

    def test_no_finding_or_evidence_acl_junction_model_exists(self) -> None:
        for forbidden in ("Finding__UserGroup", "FindingEvidence__UserGroup"):
            assert not hasattr(ton_models, forbidden), (
                f"{forbidden} would be a second ACL over one analytical case"
            )

    def test_no_agent_prompt_or_scheduler_module_was_added(self) -> None:
        """003c owns domain and data access only. Agents are Plan 005, ingestion
        Plan 004, scheduling Plan 006."""
        import onyx.db.ton as ton_package

        package_dir = inspect.getfile(ton_package)
        assert package_dir.endswith("__init__.py")

        forbidden_modules = (
            "agents",
            "prompts",
            "supervisor",
            "handoffs",
            "ingestion",
            "parsing",
            "schedules",
            "beat",
        )
        from pathlib import Path

        present = {path.stem for path in Path(package_dir).parent.glob("*.py")}
        assert present & set(forbidden_modules) == set()

    def test_the_ton_package_has_no_http_route(self) -> None:
        """Readiness §22 leaves endpoint naming open, so 003c invents none."""
        from pathlib import Path

        import onyx.db.ton as ton_package

        package_dir = Path(inspect.getfile(ton_package)).parent
        for path in package_dir.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "APIRouter" not in source, f"{path.name} declares an HTTP router"
            assert "@router." not in source, f"{path.name} declares an HTTP route"
