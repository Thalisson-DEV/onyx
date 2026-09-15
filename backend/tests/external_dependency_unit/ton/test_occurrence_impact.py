"""Impact, assignment, note and impacted-domain spec — Plan 003c.

Real PostgreSQL matters most here for the decimal cases: the point is that a value
survives a round trip *through the database*, which a mock cannot show. A
``NUMERIC`` column returning a ``Decimal`` is the whole guarantee — Prompt Mestre
§6 exists because arithmetic in this data is already wrong by cents.

Run with::

    uv run pytest backend/tests/external_dependency_unit/ton/test_occurrence_impact.py
"""

import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    AssignmentStatus,
    ImpactCategory,
    ImpactConfidence,
    ImpactMethod,
    OccurrenceActorKind,
    RedactionLevel,
    RuleDomain,
    UnitCostSource,
)
from onyx.db.ton.models import Occurrence, OccurrenceImpact
from onyx.db.ton.occurrence_records import (
    ROI_ELIGIBLE_CONFIDENCE,
    add_note__no_commit,
    assign_responsible__no_commit,
    complete_assignment__no_commit,
    current_assignment,
    fetch_assignments,
    fetch_impacts,
    fetch_notes,
    is_roi_eligible,
    record_impact__no_commit,
    set_impacted_domains__no_commit,
    verify_impact__no_commit,
)
from tests.external_dependency_unit.ton import factories

VERIFIED_AT = datetime.datetime(2001, 5, 1, 9, 0, tzinfo=datetime.UTC)


def _occurrence(db_session: Session, *, domain: RuleDomain = RuleDomain.FINANCIAL):
    rule, rule_version = factories.make_occurrence_rule_version(db_session)
    run = factories.make_analysis_run(db_session)
    result = factories.record_synthetic_detection(
        db_session,
        rule=rule,
        rule_version=rule_version,
        analysis_run=run,
        owning_domain=domain,
    )
    return result.occurrence


class TestDecimalRoundTrip:
    def test_a_predicted_amount_survives_the_database_unchanged(
        self, ton_session: Session
    ) -> None:
        occurrence = _occurrence(ton_session)
        amount = Decimal("1234567.8901234567")

        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.EXCESS_COST,
            confidence=ImpactConfidence.ALTA,
            method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
            unit_cost_source=UnitCostSource.NOT_APPLICABLE,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=amount,
        )
        ton_session.commit()
        impact_id = impact.id
        ton_session.expire_all()

        stored = ton_session.get_one(OccurrenceImpact, impact_id)
        assert stored.predicted_amount == amount
        assert isinstance(stored.predicted_amount, Decimal)

    def test_a_value_that_a_float_would_corrupt_is_preserved(
        self, ton_session: Session
    ) -> None:
        """``0.1 + 0.2`` is the canonical float failure. The exact cent value must
        come back byte-identical."""
        occurrence = _occurrence(ton_session)
        amount = Decimal("0.3000000000")

        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.POTENTIAL_SAVING,
            confidence=ImpactConfidence.MEDIA,
            method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
            unit_cost_source=UnitCostSource.NOT_APPLICABLE,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=amount,
        )
        ton_session.commit()
        ton_session.expire_all()

        stored = ton_session.get_one(OccurrenceImpact, impact.id)
        assert stored.predicted_amount == Decimal("0.3")
        assert stored.predicted_amount != Decimal(str(0.1 + 0.2))

    def test_the_formula_factors_round_trip_together(
        self, ton_session: Session
    ) -> None:
        """§9's ``impact = operational difference × reference unit cost``. Keeping
        both factors lets a reviewer recompute rather than trust."""
        occurrence = _occurrence(ton_session)

        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.EXCESS_COST,
            confidence=ImpactConfidence.ALTA,
            method=ImpactMethod.OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST,
            unit_cost_source=UnitCostSource.CONTRACT_DOTACAO,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            quantity=Decimal("137.5000000000"),
            quantity_unit="synthetic_unit",
            unit_cost=Decimal("12.3456789000"),
            predicted_amount=Decimal("1697.5308487500"),
        )
        ton_session.commit()
        ton_session.expire_all()

        stored = ton_session.get_one(OccurrenceImpact, impact.id)
        assert stored.quantity is not None
        assert stored.unit_cost is not None
        assert stored.quantity * stored.unit_cost == stored.predicted_amount

    def test_a_float_amount_is_refused(self, ton_session: Session) -> None:
        occurrence = _occurrence(ton_session)

        with pytest.raises(TypeError, match="Decimal"):
            record_impact__no_commit(
                ton_session,
                occurrence=occurrence,
                category=ImpactCategory.EXCESS_COST,
                confidence=ImpactConfidence.ALTA,
                method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
                unit_cost_source=UnitCostSource.NOT_APPLICABLE,
                currency=factories.SYNTHETIC_CURRENCY,
                scale=2,
                predicted_amount=1234.56,  # ty: ignore[invalid-argument-type]
            )

    def test_the_sensitivity_percentage_is_a_decimal(
        self, ton_session: Session
    ) -> None:
        occurrence = _occurrence(ton_session)

        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.MARGIN_OPPORTUNITY,
            confidence=ImpactConfidence.BAIXA,
            method=ImpactMethod.VALUE_AT_RISK,
            unit_cost_source=UnitCostSource.COMPARABLE_UNIT_MEDIAN,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=Decimal("1000.0000000000"),
            premise="Synthetic premise",
            sensitivity_pct=Decimal("12.5000"),
        )
        ton_session.commit()
        ton_session.expire_all()

        stored = ton_session.get_one(OccurrenceImpact, impact.id)
        assert stored.sensitivity_pct == Decimal("12.5")
        assert isinstance(stored.sensitivity_pct, Decimal)


class TestVerificationSemantics:
    def test_a_realized_amount_requires_verification(
        self, ton_session: Session
    ) -> None:
        """§13.3: only a verified saving is realised."""
        occurrence = _occurrence(ton_session)

        with pytest.raises(ValueError, match="verified_at"):
            record_impact__no_commit(
                ton_session,
                occurrence=occurrence,
                category=ImpactCategory.POTENTIAL_SAVING,
                confidence=ImpactConfidence.ALTA,
                method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
                unit_cost_source=UnitCostSource.NOT_APPLICABLE,
                currency=factories.SYNTHETIC_CURRENCY,
                scale=2,
                realized_amount=Decimal("500.0000000000"),
            )

    def test_the_database_refuses_a_realized_amount_without_verification(
        self, ton_session: Session
    ) -> None:
        occurrence = _occurrence(ton_session)
        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.POTENTIAL_SAVING,
            confidence=ImpactConfidence.ALTA,
            method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
            unit_cost_source=UnitCostSource.NOT_APPLICABLE,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=Decimal("500.0000000000"),
        )
        ton_session.commit()

        impact.realized_amount = Decimal("480.0000000000")
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_occurrence_impact_realized_requires_verification" in str(
            exc_info.value
        )

    def test_verifying_keeps_the_prediction_alongside_the_outcome(
        self, ton_session: Session
    ) -> None:
        """Keeping both is what lets a later report show forecast error rather
        than quietly replacing the estimate."""
        occurrence = _occurrence(ton_session)
        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.POTENTIAL_SAVING,
            confidence=ImpactConfidence.ALTA,
            method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
            unit_cost_source=UnitCostSource.NOT_APPLICABLE,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=Decimal("500.0000000000"),
        )

        verify_impact__no_commit(
            ton_session,
            impact=impact,
            realized_amount=Decimal("477.7700000000"),
            verified_at=VERIFIED_AT,
        )
        ton_session.commit()
        ton_session.expire_all()

        stored = ton_session.get_one(OccurrenceImpact, impact.id)
        assert stored.predicted_amount == Decimal("500")
        assert stored.realized_amount == Decimal("477.77")
        assert stored.verified_at == VERIFIED_AT

    def test_an_impact_row_needs_an_amount(self, ton_session: Session) -> None:
        occurrence = _occurrence(ton_session)

        with pytest.raises(ValueError, match="predicted or a realised amount"):
            record_impact__no_commit(
                ton_session,
                occurrence=occurrence,
                category=ImpactCategory.EXCESS_COST,
                confidence=ImpactConfidence.ALTA,
                method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
                unit_cost_source=UnitCostSource.NOT_APPLICABLE,
                currency=factories.SYNTHETIC_CURRENCY,
                scale=2,
            )


class TestConfidenceIsNeverPromoted:
    def test_a_low_confidence_impact_stays_representable(
        self, ton_session: Session
    ) -> None:
        """Excluded from ROI, not excluded from the ledger. §9 requires the number
        to be publishable with its label, not suppressed."""
        occurrence = _occurrence(ton_session)

        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.FINANCIAL_RISK,
            confidence=ImpactConfidence.BAIXA,
            method=ImpactMethod.VALUE_AT_RISK,
            unit_cost_source=UnitCostSource.NOT_APPLICABLE,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=Decimal("9999.0000000000"),
            premise="Two synthetic premises",
            sensitivity_pct=Decimal("30.0000"),
        )
        ton_session.commit()

        assert impact.confidence is ImpactConfidence.BAIXA
        assert fetch_impacts(ton_session, occurrence.id) == [impact]

    def test_repeating_a_low_confidence_impact_never_promotes_it(
        self, ton_session: Session
    ) -> None:
        occurrence = _occurrence(ton_session)
        for _ in range(4):
            record_impact__no_commit(
                ton_session,
                occurrence=occurrence,
                category=ImpactCategory.FINANCIAL_RISK,
                confidence=ImpactConfidence.BAIXA,
                method=ImpactMethod.VALUE_AT_RISK,
                unit_cost_source=UnitCostSource.NOT_APPLICABLE,
                currency=factories.SYNTHETIC_CURRENCY,
                scale=2,
                predicted_amount=Decimal("100.0000000000"),
            )
        ton_session.commit()

        impacts = fetch_impacts(ton_session, occurrence.id)
        assert len(impacts) == 4
        assert {item.confidence for item in impacts} == {ImpactConfidence.BAIXA}

    def test_a_low_confidence_impact_is_never_roi_eligible(
        self, ton_session: Session
    ) -> None:
        occurrence = _occurrence(ton_session)
        low = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.POTENTIAL_SAVING,
            confidence=ImpactConfidence.BAIXA,
            method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
            unit_cost_source=UnitCostSource.NOT_APPLICABLE,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=Decimal("100.0000000000"),
            realized_amount=Decimal("100.0000000000"),
            verified_at=VERIFIED_AT,
        )
        high = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.POTENTIAL_SAVING,
            confidence=ImpactConfidence.ALTA,
            method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
            unit_cost_source=UnitCostSource.NOT_APPLICABLE,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=Decimal("100.0000000000"),
            realized_amount=Decimal("100.0000000000"),
            verified_at=VERIFIED_AT,
        )
        ton_session.commit()

        assert not is_roi_eligible(low)
        assert is_roi_eligible(high)
        assert ImpactConfidence.BAIXA not in ROI_ELIGIBLE_CONFIDENCE

    def test_an_unverified_impact_is_never_roi_eligible(
        self, ton_session: Session
    ) -> None:
        occurrence = _occurrence(ton_session)
        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.POTENTIAL_SAVING,
            confidence=ImpactConfidence.ALTA,
            method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
            unit_cost_source=UnitCostSource.NOT_APPLICABLE,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=Decimal("100.0000000000"),
        )
        ton_session.commit()

        assert not is_roi_eligible(impact)


class TestUnitCostSourceIsAlwaysStated:
    def test_the_formula_cannot_declare_a_missing_unit_cost_source(
        self, ton_session: Session
    ) -> None:
        """§9: "diga sempre qual usou". The escape hatch exists only for methods
        that use no reference unit cost."""
        occurrence = _occurrence(ton_session)

        with pytest.raises(ValueError, match="reference unit cost"):
            record_impact__no_commit(
                ton_session,
                occurrence=occurrence,
                category=ImpactCategory.EXCESS_COST,
                confidence=ImpactConfidence.ALTA,
                method=ImpactMethod.OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST,
                unit_cost_source=UnitCostSource.NOT_APPLICABLE,
                currency=factories.SYNTHETIC_CURRENCY,
                scale=2,
                predicted_amount=Decimal("100.0000000000"),
            )

    def test_the_database_enforces_the_same_rule(self, ton_session: Session) -> None:
        occurrence = _occurrence(ton_session)
        ton_session.commit()

        ton_session.add(
            OccurrenceImpact(
                occurrence_id=occurrence.id,
                category=ImpactCategory.EXCESS_COST,
                confidence=ImpactConfidence.ALTA,
                method=ImpactMethod.OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST,
                unit_cost_source=UnitCostSource.NOT_APPLICABLE,
                currency=factories.SYNTHETIC_CURRENCY,
                scale=2,
                predicted_amount=Decimal("100.0000000000"),
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_occurrence_impact_unit_cost_source_required" in str(
            exc_info.value
        )

    @pytest.mark.parametrize(
        "source",
        [
            UnitCostSource.CONTRACT_DOTACAO,
            UnitCostSource.OWN_UNIT_TRAILING_3M,
            UnitCostSource.COMPARABLE_UNIT_MEDIAN,
        ],
    )
    def test_each_preference_order_member_is_recordable(
        self, ton_session: Session, source: UnitCostSource
    ) -> None:
        occurrence = _occurrence(ton_session)

        impact = record_impact__no_commit(
            ton_session,
            occurrence=occurrence,
            category=ImpactCategory.EXCESS_COST,
            confidence=ImpactConfidence.ALTA,
            method=ImpactMethod.OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST,
            unit_cost_source=source,
            currency=factories.SYNTHETIC_CURRENCY,
            scale=2,
            predicted_amount=Decimal("100.0000000000"),
        )
        ton_session.commit()

        assert impact.unit_cost_source is source


class TestNoRoiRegistry:
    def test_no_roi_table_exists(self) -> None:
        """Realised ROI is derived, not stored (readiness §13)."""
        from onyx.db.models import Base

        assert not [name for name in Base.metadata.tables if "roi" in name]

    def test_roi_eligibility_is_a_predicate_over_impact_rows(
        self, ton_session: Session
    ) -> None:
        """The aggregation Plan 006 will run: verified, non-BAIXA, realised."""
        occurrence = _occurrence(ton_session)
        for confidence, verified in (
            (ImpactConfidence.ALTA, True),
            (ImpactConfidence.MEDIA, True),
            (ImpactConfidence.BAIXA, True),
            (ImpactConfidence.ALTA, False),
        ):
            record_impact__no_commit(
                ton_session,
                occurrence=occurrence,
                category=ImpactCategory.POTENTIAL_SAVING,
                confidence=confidence,
                method=ImpactMethod.DIRECT_SOURCE_AMOUNT,
                unit_cost_source=UnitCostSource.NOT_APPLICABLE,
                currency=factories.SYNTHETIC_CURRENCY,
                scale=2,
                predicted_amount=Decimal("10.0000000000"),
                realized_amount=Decimal("10.0000000000") if verified else None,
                verified_at=VERIFIED_AT if verified else None,
            )
        ton_session.commit()

        eligible = [
            item
            for item in fetch_impacts(ton_session, occurrence.id)
            if is_roi_eligible(item)
        ]
        assert len(eligible) == 2
        assert {item.confidence for item in eligible} == {
            ImpactConfidence.ALTA,
            ImpactConfidence.MEDIA,
        }


class TestAssignmentHistory:
    def test_reassignment_appends_and_supersedes_rather_than_overwriting(
        self, ton_session: Session
    ) -> None:
        """§10 escalation and §12 R9 need the history of responsibility and
        deadlines, not the latest value."""
        occurrence = _occurrence(ton_session)
        actor = factories.make_user(ton_session)

        first = assign_responsible__no_commit(
            ton_session,
            occurrence=occurrence,
            responsible_label="First owner",
            assigned_by_user_id=actor.id,
            deadline=datetime.date(2001, 3, 1),
        )
        second = assign_responsible__no_commit(
            ton_session,
            occurrence=occurrence,
            responsible_label="Second owner",
            assigned_by_user_id=actor.id,
            deadline=datetime.date(2001, 4, 1),
        )
        ton_session.commit()

        history = fetch_assignments(ton_session, occurrence.id)
        assert [item.sequence_no for item in history] == [1, 2]
        # The first deadline survives, which is the point.
        assert history[0].deadline == datetime.date(2001, 3, 1)
        assert history[0].responsible_label == "First owner"
        assert history[0].status is AssignmentStatus.SUPERSEDED
        assert history[0].superseded_at is not None
        assert history[1].status is AssignmentStatus.OPEN
        assert current_assignment(ton_session, occurrence.id) == second
        assert first.id != second.id

    def test_completing_an_assignment_records_when(self, ton_session: Session) -> None:
        occurrence = _occurrence(ton_session)
        actor = factories.make_user(ton_session)
        assignment = assign_responsible__no_commit(
            ton_session,
            occurrence=occurrence,
            responsible_label="Owner",
            assigned_by_user_id=actor.id,
        )

        complete_assignment__no_commit(ton_session, assignment=assignment)
        ton_session.commit()

        assert assignment.status is AssignmentStatus.COMPLETED
        assert assignment.completed_at is not None

    def test_the_database_refuses_a_completed_assignment_with_no_timestamp(
        self, ton_session: Session
    ) -> None:
        occurrence = _occurrence(ton_session)
        actor = factories.make_user(ton_session)
        assignment = assign_responsible__no_commit(
            ton_session,
            occurrence=occurrence,
            responsible_label="Owner",
            assigned_by_user_id=actor.id,
        )
        ton_session.commit()

        assignment.status = AssignmentStatus.COMPLETED
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_occurrence_assignment_completed_has_timestamp" in str(
            exc_info.value
        )

    def test_a_responsible_label_is_required(self, ton_session: Session) -> None:
        occurrence = _occurrence(ton_session)
        actor = factories.make_user(ton_session)

        with pytest.raises(ValueError, match="responsible_label is required"):
            assign_responsible__no_commit(
                ton_session,
                occurrence=occurrence,
                responsible_label="   ",
                assigned_by_user_id=actor.id,
            )

    def test_a_system_assignment_needs_no_account(self, ton_session: Session) -> None:
        """A rule may nominate an owner from configuration; no HR integration is
        involved and no account is invented."""
        occurrence = _occurrence(ton_session)

        assignment = assign_responsible__no_commit(
            ton_session,
            occurrence=occurrence,
            responsible_label="Synthetic role owner",
            actor_kind=OccurrenceActorKind.SYSTEM,
        )
        ton_session.commit()

        assert assignment.actor_kind is OccurrenceActorKind.SYSTEM
        assert assignment.assigned_by_user_id is None


class TestNotes:
    def test_notes_are_append_only_and_ordered(self, ton_session: Session) -> None:
        occurrence = _occurrence(ton_session)
        author = factories.make_user(ton_session)

        for body in ("First note", "Second note"):
            add_note__no_commit(
                ton_session,
                occurrence=occurrence,
                body=body,
                redaction_level=RedactionLevel.NONE,
                author_user_id=author.id,
            )
        ton_session.commit()

        notes = fetch_notes(ton_session, occurrence.id)
        assert [item.sequence_no for item in notes] == [1, 2]
        assert [item.body for item in notes] == ["First note", "Second note"]

    def test_a_note_states_its_redaction_level(self, ton_session: Session) -> None:
        """A note may carry PII, so the writer says how much identity it holds."""
        occurrence = _occurrence(ton_session)
        author = factories.make_user(ton_session)

        note = add_note__no_commit(
            ton_session,
            occurrence=occurrence,
            body="Synthetic note naming a role only",
            redaction_level=RedactionLevel.ROLE_ONLY,
            author_user_id=author.id,
        )
        ton_session.commit()

        assert note.redaction_level is RedactionLevel.ROLE_ONLY

    def test_the_note_table_has_no_permissive_visibility_column(self) -> None:
        """Notes inherit the occurrence ACL; there is no separate, more permissive
        access mechanism."""
        from onyx.db.ton.models import OccurrenceNote

        columns = set(OccurrenceNote.__table__.columns.keys())
        assert columns & {"is_public", "public", "is_global", "public_permission"} == (
            set()
        )

    def test_a_user_note_names_its_author(self, ton_session: Session) -> None:
        occurrence = _occurrence(ton_session)

        with pytest.raises(ValueError, match="must name its author"):
            add_note__no_commit(
                ton_session,
                occurrence=occurrence,
                body="Anonymous note",
                redaction_level=RedactionLevel.NONE,
            )


class TestImpactedDomains:
    def test_other_affected_domains_are_listed_not_duplicated(
        self, ton_session: Session
    ) -> None:
        """Prompt Mestre §15: one domain owns the case, recorded at the link where
        the quantity changed. The rest are listed."""
        occurrence = _occurrence(ton_session, domain=RuleDomain.FINANCIAL)

        rows = set_impacted_domains__no_commit(
            ton_session,
            occurrence=occurrence,
            domains=[RuleDomain.FLEET, RuleDomain.CONTRACT],
            note="Synthetic handoff note",
        )
        ton_session.commit()

        assert {row.domain for row in rows} == {RuleDomain.FLEET, RuleDomain.CONTRACT}
        # One occurrence, not three.
        assert ton_session.query(Occurrence).count() == 1

    def test_the_owning_domain_cannot_be_listed_as_impacted(
        self, ton_session: Session
    ) -> None:
        occurrence = _occurrence(ton_session, domain=RuleDomain.FINANCIAL)

        with pytest.raises(ValueError, match="already owns this occurrence"):
            set_impacted_domains__no_commit(
                ton_session,
                occurrence=occurrence,
                domains=[RuleDomain.FINANCIAL, RuleDomain.FLEET],
            )

    def test_replacing_the_list_removes_the_previous_rows(
        self, ton_session: Session
    ) -> None:
        from onyx.db.ton.models import OccurrenceImpactedDomain

        occurrence = _occurrence(ton_session, domain=RuleDomain.FINANCIAL)
        set_impacted_domains__no_commit(
            ton_session, occurrence=occurrence, domains=[RuleDomain.FLEET]
        )
        ton_session.commit()

        set_impacted_domains__no_commit(
            ton_session, occurrence=occurrence, domains=[RuleDomain.HR]
        )
        ton_session.commit()

        rows = ton_session.scalars(
            select(OccurrenceImpactedDomain).where(
                OccurrenceImpactedDomain.occurrence_id == occurrence.id
            )
        ).all()
        assert [row.domain for row in rows] == [RuleDomain.HR]

    def test_a_repeated_domain_is_recorded_once(self, ton_session: Session) -> None:
        occurrence = _occurrence(ton_session, domain=RuleDomain.FINANCIAL)

        rows = set_impacted_domains__no_commit(
            ton_session,
            occurrence=occurrence,
            domains=[RuleDomain.FLEET, RuleDomain.FLEET],
        )
        ton_session.commit()

        assert len(rows) == 1
