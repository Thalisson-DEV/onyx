"""Report schema, revision history, immutability and reproducibility (003d).

External-dependency-unit rather than integration: real PostgreSQL is required —
the constraints, the ``ON DELETE`` rules and the JSONB round trip are the subject —
but the functions are called directly. Every test runs against a throwaway
database cloned from a migrated template, so the running development database is
never read for schema evidence and never written to.
"""

import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.db.ton.canonical import (
    CANONICALIZATION_VERSION,
    HASH_ALGORITHM,
    ScaledDecimal,
    compute_content_hash,
)
from onyx.db.ton.enums import (
    InterpretationInputScope,
    InterpretationStatus,
    OccurrenceActorKind,
    OccurrenceTransition,
    TonReportType,
)
from onyx.db.ton.interpretations import begin_interpretation, complete_interpretation
from onyx.db.ton.models import (
    AnalysisRun,
    Finding,
    Occurrence,
    Rule,
    RuleVersion,
    SourceSnapshot,
    TonReport,
    TonReportRevision,
)
from onyx.db.ton.occurrences import apply_transition__no_commit
from onyx.db.ton.reports import (
    PinnedInputs,
    build_canonical_payload,
    get_revision,
    latest_revision,
    next_revision_no,
    pinned_inputs,
    publish_report_revision__no_commit,
    recompute_content_hash,
    revisions_using_finding,
    revisions_using_occurrence,
    revisions_using_rule_version,
    revisions_using_source_snapshot,
    supersede_revision__no_commit,
    verify_revision_hash,
)
from onyx.db.ton.rule_versions import (
    backfill_definition_hashes__no_commit,
    compute_definition_hash,
    create_rule__no_commit,
    create_rule_version__no_commit,
    definition_hash_matches,
)
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import (
    REVISION_003C,
    TON_003D_TABLES,
    TON_REPORT_LINK_TABLES,
    TON_TABLES_AT_HEAD,
    column_names,
    constraint_names,
    downgrade,
    query_all,
    table_names,
    upgrade,
)

# (table, column, referenced table, expected delete rule). RESTRICT wherever a
# published report would otherwise be left with a number whose evidence vanished.
EXPECTED_FOREIGN_KEYS: tuple[tuple[str, str, str, str], ...] = (
    ("ton_report", "business_unit_id", "ton_business_unit", "RESTRICT"),
    ("ton_report", "created_by", "user", "SET NULL"),
    ("ton_report_revision", "report_id", "ton_report", "CASCADE"),
    ("ton_report_revision", "generated_by", "user", "SET NULL"),
    (
        "ton_report_revision",
        "superseded_by_revision_id",
        "ton_report_revision",
        "SET NULL",
    ),
    ("ton_report_revision", "file_record_id", "file_record", "SET NULL"),
    (
        "ton_report_revision__analysis_run",
        "report_revision_id",
        "ton_report_revision",
        "CASCADE",
    ),
    (
        "ton_report_revision__analysis_run",
        "analysis_run_id",
        "ton_analysis_run",
        "RESTRICT",
    ),
    (
        "ton_report_revision__occurrence",
        "occurrence_id",
        "ton_occurrence",
        "RESTRICT",
    ),
    ("ton_report_revision__finding", "finding_id", "ton_finding", "RESTRICT"),
    (
        "ton_report_revision__rule_version",
        "rule_version_id",
        "ton_rule_version",
        "RESTRICT",
    ),
    (
        "ton_report_revision__source_snapshot",
        "source_snapshot_id",
        "ton_source_snapshot",
        "RESTRICT",
    ),
    ("ton_report__user_group", "report_id", "ton_report", "CASCADE"),
    ("ton_report__user_group", "user_group_id", "user_group", "CASCADE"),
    ("ton_audit_event", "actor_user_id", "user", "SET NULL"),
)

_FOREIGN_KEY_SQL = """
SELECT rc.delete_rule, ccu.table_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.referential_constraints rc
  ON tc.constraint_name = rc.constraint_name
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name = :table
  AND kcu.column_name = :column
"""


class _Detection(NamedTuple):
    """The rows one synthetic detection produces, named so they stay typed."""

    rule: Rule
    rule_version: RuleVersion
    run: AnalysisRun
    occurrence: Occurrence
    finding: Finding


def _detection(db_session: Session) -> _Detection:
    """One rule version, run, occurrence and finding, through production paths."""
    rule, rule_version = factories.make_occurrence_rule_version(db_session)
    run = factories.make_analysis_run(db_session)
    result = factories.record_synthetic_detection(
        db_session, rule=rule, rule_version=rule_version, analysis_run=run
    )
    return _Detection(rule, rule_version, run, result.occurrence, result.finding)


class TestReportSchema:
    def test_head_holds_exactly_the_expected_ton_tables(
        self, ton_database: str
    ) -> None:
        assert table_names(ton_database, "ton_") == set(TON_TABLES_AT_HEAD)

    def test_003d_adds_exactly_nine_tables(self, ton_database: str) -> None:
        """Measured, not asserted from a list: downgrade to 003c and diff. This is
        what catches a table smuggled into 003d without a recorded decision."""
        at_head = table_names(ton_database)

        downgrade(ton_database, REVISION_003C)

        assert at_head - table_names(ton_database) == set(TON_003D_TABLES)

    def test_003d_downgrade_leaves_every_earlier_structure_intact(
        self, ton_database: str
    ) -> None:
        """A 003d rollback must not touch the rule, analysis or occurrence
        layers."""
        earlier = [
            table for table in TON_TABLES_AT_HEAD if table not in TON_003D_TABLES
        ]
        constraints_before = {
            table: constraint_names(ton_database, table) for table in earlier
        }
        columns_before = {table: column_names(ton_database, table) for table in earlier}

        downgrade(ton_database, REVISION_003C)

        for table in earlier:
            assert constraint_names(ton_database, table) == constraints_before[table]
            assert column_names(ton_database, table) == columns_before[table]

    def test_003d_downgrade_keeps_definition_hash_nullable(
        self, ton_database: str
    ) -> None:
        """003d writes the column but does not alter it. Making it NOT NULL would
        demand a value for a legitimate row whose parameters cannot be
        canonicalised, and a fabricated hash defeats the column's purpose."""
        nullable = query_all(
            ton_database,
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'ton_rule_version' AND column_name = 'definition_hash'",
        )
        assert nullable == [("YES",)]

        downgrade(ton_database, REVISION_003C)

        assert "definition_hash" in column_names(ton_database, "ton_rule_version")

    def test_downgrade_then_upgrade_restores_the_same_tables(
        self, ton_database: str
    ) -> None:
        before = table_names(ton_database)

        downgrade(ton_database, REVISION_003C)
        upgrade(ton_database, "head")

        assert table_names(ton_database) == before

    def test_the_migration_seeds_nothing(self, ton_database: str) -> None:
        """Zero rows in all nine tables on a freshly migrated database."""
        for table in TON_003D_TABLES:
            rows = query_all(ton_database, f"SELECT count(*) FROM {table}")
            assert rows == [(0,)], f"{table} must be empty after the migration"

    @pytest.mark.parametrize(
        ("table", "column", "referenced", "delete_rule"), EXPECTED_FOREIGN_KEYS
    )
    def test_delete_rules_are_the_declared_ones(
        self,
        ton_database: str,
        table: str,
        column: str,
        referenced: str,
        delete_rule: str,
    ) -> None:
        rows = query_all(
            ton_database, _FOREIGN_KEY_SQL, {"table": table, "column": column}
        )
        assert rows, f"{table}.{column} has no foreign key"
        assert {(row[0], row[1]) for row in rows} == {(delete_rule, referenced)}

    def test_no_report_table_has_a_permissive_visibility_column(
        self, ton_database: str
    ) -> None:
        """The inverse assertion, extended to 003d. Zero junction rows means
        DENIED, so a permissive short-circuit must be inexpressible."""
        forbidden = {"is_public", "public", "is_global", "public_permission"}
        for table in TON_003D_TABLES:
            assert column_names(ton_database, table) & forbidden == set()

    def test_the_four_acl_junctions_now_exist(self, ton_database: str) -> None:
        """003c created three; ``ton_report__user_group`` arrives here with its
        table (decision D-043)."""
        junctions = {
            name for name in table_names(ton_database, "ton_") if "__user_group" in name
        }
        assert junctions == {
            "ton_business_unit__user_group",
            "ton_contract__user_group",
            "ton_occurrence__user_group",
            "ton_report__user_group",
        }

    def test_a_revision_has_no_acl_junction_of_its_own(self, ton_database: str) -> None:
        """A revision inherits its report's authorization. Two ACLs over one
        published document would eventually disagree."""
        assert "ton_report_revision__user_group" not in table_names(ton_database)

    def test_no_roi_or_scheduler_table_was_added(self, ton_database: str) -> None:
        """ROI stays a derived aggregation (readiness §13); scheduling, alerting
        and publication ceilings are Plan 006. Scoped to ``ton_`` because the
        wider schema has unrelated scheduling tables of its own."""
        present = table_names(ton_database, "ton_")
        for fragment in ("roi", "schedule", "ceiling", "alert"):
            assert not {name for name in present if fragment in name}


class TestReportRevisionHistory:
    def test_a_report_and_its_first_revision_are_created(
        self, ton_session: Session
    ) -> None:
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)

        assert revision.report_id == report.id
        assert revision.revision_no == 1
        assert revision.canonicalization_version == CANONICALIZATION_VERSION
        assert revision.hash_algorithm == HASH_ALGORITHM
        assert revision.content_hash
        assert revision.generator_version == factories.SYNTHETIC_GENERATOR_VERSION

    def test_a_second_publication_appends_revision_two(
        self, ton_session: Session
    ) -> None:
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)
        second = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="2000.00"),
        )

        assert (first.revision_no, second.revision_no) == (1, 2)
        assert next_revision_no(ton_session, report.id) == 3
        newest = latest_revision(ton_session, report.id)
        assert newest is not None
        assert newest.id == second.id

    def test_revision_one_stays_byte_and_hash_stable_after_a_second(
        self, ton_session: Session
    ) -> None:
        """Requirement 4. Publishing again must not touch what was already
        published."""
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)
        original_payload = dict(first.canonical_payload)
        original_hash = first.content_hash

        factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="9999.99"),
        )
        ton_session.expire_all()

        reloaded = get_revision(ton_session, report_id=report.id, revision_no=1)
        assert reloaded is not None
        assert reloaded.canonical_payload == original_payload
        assert reloaded.content_hash == original_hash
        assert verify_revision_hash(reloaded) is True

    def test_a_duplicate_revision_number_is_refused_by_the_database(
        self, ton_session: Session
    ) -> None:
        """Requirement 2. An application pre-check cannot guarantee one history;
        ``uq_ton_report_revision_report_revision`` can."""
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)

        ton_session.add(
            TonReportRevision(
                report_id=report.id,
                revision_no=first.revision_no,
                canonical_payload={"a": "1"},
                canonicalization_version=CANONICALIZATION_VERSION,
                hash_algorithm=HASH_ALGORITHM,
                content_hash="deadbeef",
                generator_version="synthetic",
                generated_at=factories.SYNTHETIC_GENERATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            ton_session.flush()
        ton_session.rollback()

    def test_a_zero_revision_number_is_refused(self, ton_session: Session) -> None:
        report = factories.make_report(ton_session)
        ton_session.add(
            TonReportRevision(
                report_id=report.id,
                revision_no=0,
                canonical_payload={},
                canonicalization_version=CANONICALIZATION_VERSION,
                hash_algorithm=HASH_ALGORITHM,
                content_hash="deadbeef",
                generator_version="synthetic",
                generated_at=factories.SYNTHETIC_GENERATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            ton_session.flush()
        ton_session.rollback()

    def test_a_report_code_is_unique(self, ton_session: Session) -> None:
        factories.make_report(ton_session, code="SYN-REP-FIXED")
        with pytest.raises(IntegrityError):
            factories.make_report(ton_session, code="SYN-REP-FIXED")
        ton_session.rollback()

    def test_a_report_holds_no_payload_column(self) -> None:
        """The structural half of the decision: one mutable row cannot hold the
        latest generated payload, because there is nowhere to put it."""
        columns = set(TonReport.__table__.columns.keys())
        assert "canonical_payload" not in columns
        assert "content_hash" not in columns
        assert not {name for name in columns if "payload" in name}


class TestRevisionImmutability:
    def test_the_reports_module_exposes_no_update_or_delete(self) -> None:
        """Readiness §12's first layer: immutability by absence of a write path."""
        from onyx.db.ton import reports

        for name in dir(reports):
            assert not name.startswith("update_"), f"{name} would mutate a revision"
            assert not name.startswith("delete_"), f"{name} would remove a revision"

    def test_mutating_a_published_payload_raises(self, ton_session: Session) -> None:
        """Readiness §12's second layer. Bypassing the reports module does not
        bypass the rule."""
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)

        revision.canonical_payload = {"tampered": "yes"}
        with pytest.raises(ValueError, match="immutable"):
            ton_session.flush()
        ton_session.rollback()

    @pytest.mark.parametrize(
        ("column", "value"),
        (
            ("content_hash", "0" * 64),
            ("revision_no", 99),
            ("canonicalization_version", "ton-canon-2"),
            ("hash_algorithm", "md5"),
            ("generator_version", "rewritten"),
            (
                "generated_at",
                datetime.datetime(2030, 1, 1, tzinfo=datetime.UTC),
            ),
        ),
    )
    def test_mutating_any_content_column_raises(
        self, ton_session: Session, column: str, value: object
    ) -> None:
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)

        setattr(revision, column, value)
        with pytest.raises(ValueError, match="immutable"):
            ton_session.flush()
        ton_session.rollback()

    def test_a_correction_creates_a_new_revision_and_links_the_prior_one(
        self, ton_session: Session
    ) -> None:
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)
        original_hash = first.content_hash

        second = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="2500.00"),
            corrects=first,
            correction_reason="Synthetic reconciliation correction",
        )

        assert second.revision_no == 2
        assert first.superseded_by_revision_id == second.id
        assert first.correction_reason == "Synthetic reconciliation correction"
        # The correction records that a figure changed without erasing it.
        assert first.content_hash == original_hash
        assert verify_revision_hash(first) is True

    def test_a_correction_without_a_reason_is_refused(
        self, ton_session: Session
    ) -> None:
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)

        with pytest.raises(ValueError, match="must record why"):
            factories.publish_synthetic_revision(
                ton_session, report=report, corrects=first
            )

    def test_a_revision_cannot_be_superseded_twice(self, ton_session: Session) -> None:
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)
        second = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="2.00"),
            corrects=first,
            correction_reason="Synthetic first correction",
        )
        third = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="3.00"),
        )

        with pytest.raises(ValueError, match="already superseded"):
            supersede_revision__no_commit(
                ton_session,
                superseded=first,
                replacement=third,
                correction_reason="Synthetic second correction",
            )
        assert first.superseded_by_revision_id == second.id

    def test_a_revision_cannot_supersede_itself(self, ton_session: Session) -> None:
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)

        with pytest.raises(ValueError, match="cannot supersede itself"):
            supersede_revision__no_commit(
                ton_session,
                superseded=revision,
                replacement=revision,
                correction_reason="Synthetic",
            )

    def test_an_earlier_revision_cannot_correct_a_later_one(
        self, ton_session: Session
    ) -> None:
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)
        second = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="2.00"),
        )

        with pytest.raises(ValueError, match="must be a later revision"):
            supersede_revision__no_commit(
                ton_session,
                superseded=second,
                replacement=first,
                correction_reason="Synthetic",
            )

    def test_a_supersession_pointer_without_a_reason_is_refused_by_the_database(
        self, ton_session: Session
    ) -> None:
        """The guarantee does not depend on the Python guard above."""
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)
        second = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="2.00"),
        )

        first.superseded_by_revision_id = second.id
        with pytest.raises(IntegrityError):
            ton_session.flush()
        ton_session.rollback()

    def test_hash_verification_detects_a_payload_edited_behind_the_orm(
        self, ton_session: Session
    ) -> None:
        """Readiness §12's third layer: an UPDATE that bypassed both the module
        and the model guard still shows up."""
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)
        revision_id = revision.id
        ton_session.commit()

        ton_session.execute(
            update(TonReportRevision)
            .where(TonReportRevision.id == revision_id)
            .values(canonical_payload={"tampered": "yes"})
        )
        ton_session.commit()
        ton_session.expire_all()

        reloaded = ton_session.get(TonReportRevision, revision_id)
        assert reloaded is not None
        assert verify_revision_hash(reloaded) is False

    def test_verification_refuses_an_unknown_canonicalisation_scheme(
        self, ton_session: Session
    ) -> None:
        """Storing the scheme as data is what makes this answerable at all: this
        process cannot re-derive a digest produced by a scheme it does not have."""
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)
        revision_id = revision.id
        ton_session.commit()

        ton_session.execute(
            update(TonReportRevision)
            .where(TonReportRevision.id == revision_id)
            .values(canonicalization_version="ton-canon-99")
        )
        ton_session.commit()
        ton_session.expire_all()

        reloaded = ton_session.get(TonReportRevision, revision_id)
        assert reloaded is not None
        assert verify_revision_hash(reloaded) is False


class TestPinnedInputs:
    def test_the_exact_inputs_are_pinned_relationally(
        self, ton_session: Session
    ) -> None:
        """Requirement 5. Explicit association rows, not an opaque JSON list."""
        _, rule_version, run, occurrence, finding = _detection(ton_session)
        snapshot = factories.make_source_snapshot(ton_session)
        report = factories.make_report(ton_session)

        revision = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            findings=[finding],
            occurrences=[occurrence],
            analysis_runs=[run],
            rule_versions=[rule_version],
            source_snapshots=[snapshot],
        )

        assert pinned_inputs(ton_session, revision.id) == PinnedInputs(
            analysis_run_ids=(run.id,),
            occurrence_ids=(occurrence.id,),
            finding_ids=(finding.id,),
            rule_version_ids=(rule_version.id,),
            source_snapshot_ids=(snapshot.id,),
        )

    def test_which_revision_used_a_finding_is_relationally_answerable(
        self, ton_session: Session
    ) -> None:
        """The question readiness §12 names, and the reason these are join tables
        rather than a JSONB array."""
        _, rule_version, run, occurrence, finding = _detection(ton_session)
        snapshot = factories.make_source_snapshot(ton_session)
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            findings=[finding],
            occurrences=[occurrence],
            analysis_runs=[run],
            rule_versions=[rule_version],
            source_snapshots=[snapshot],
        )

        assert [row.id for row in revisions_using_finding(ton_session, finding.id)] == [
            revision.id
        ]
        assert [
            row.id for row in revisions_using_occurrence(ton_session, occurrence.id)
        ] == [revision.id]
        assert [
            row.id for row in revisions_using_rule_version(ton_session, rule_version.id)
        ] == [revision.id]
        assert [
            row.id for row in revisions_using_source_snapshot(ton_session, snapshot.id)
        ] == [revision.id]

    def test_an_unrelated_finding_pins_nothing(self, ton_session: Session) -> None:
        assert revisions_using_finding(ton_session, uuid4()) == []

    def test_input_order_does_not_change_the_hash(self, ton_session: Session) -> None:
        """Readiness: the same logical content hashes identically across two
        orderings of input."""
        _, rule_version, run, occurrence, finding = _detection(ton_session)
        first_snapshot = factories.make_source_snapshot(ton_session)
        second_snapshot = factories.make_source_snapshot(ton_session)
        report = factories.make_report(ton_session)

        forward = build_canonical_payload(
            report=report,
            body=factories.synthetic_report_body(),
            source_snapshot_ids=[first_snapshot.id, second_snapshot.id],
        )
        backward = build_canonical_payload(
            report=report,
            body=factories.synthetic_report_body(),
            source_snapshot_ids=[second_snapshot.id, first_snapshot.id],
        )
        assert compute_content_hash(forward) == compute_content_hash(backward)

    def test_a_repeated_input_is_pinned_once(self, ton_session: Session) -> None:
        """The composite primary key would refuse a duplicate row; passing the
        same finding twice means one inclusion, not an error."""
        _, _, _, _, finding = _detection(ton_session)
        report = factories.make_report(ton_session)

        revision = factories.publish_synthetic_revision(
            ton_session, report=report, findings=[finding, finding]
        )
        assert pinned_inputs(ton_session, revision.id).finding_ids == (finding.id,)

    def test_a_pinned_finding_cannot_be_deleted(self, ton_session: Session) -> None:
        """RESTRICT, not CASCADE. A published report must not lose its evidence
        for the convenience of a cleanup job."""
        _, _, _, _, finding = _detection(ton_session)
        report = factories.make_report(ton_session)
        factories.publish_synthetic_revision(
            ton_session, report=report, findings=[finding]
        )
        ton_session.commit()

        with pytest.raises(IntegrityError, match="violates foreign key constraint"):
            ton_session.execute(delete(Finding).where(Finding.id == finding.id))
        ton_session.rollback()

    def test_a_pinned_source_snapshot_cannot_be_deleted(
        self, ton_session: Session
    ) -> None:
        snapshot = factories.make_source_snapshot(ton_session)
        report = factories.make_report(ton_session)
        factories.publish_synthetic_revision(
            ton_session, report=report, source_snapshots=[snapshot]
        )
        ton_session.commit()

        with pytest.raises(IntegrityError, match="violates foreign key constraint"):
            ton_session.execute(
                delete(SourceSnapshot).where(SourceSnapshot.id == snapshot.id)
            )
        ton_session.rollback()

    def test_every_link_table_is_covered_by_these_assertions(self) -> None:
        """An inverse assertion, so a sixth link table cannot arrive untested."""
        assert len(TON_REPORT_LINK_TABLES) == 5
        assert set(TON_REPORT_LINK_TABLES) <= set(TON_003D_TABLES)


class TestFinalInterpretationGate:
    def test_a_not_required_interpretation_is_accepted(
        self, ton_session: Session
    ) -> None:
        _, _, _, _, finding = _detection(ton_session)
        assert finding.interpretation_status is InterpretationStatus.NOT_REQUIRED
        report = factories.make_report(ton_session)

        revision = factories.publish_synthetic_revision(
            ton_session, report=report, findings=[finding]
        )
        assert pinned_inputs(ton_session, revision.id).finding_ids == (finding.id,)

    def test_a_completed_interpretation_is_accepted(self, ton_session: Session) -> None:
        _, _, _, _, finding = _detection(ton_session)
        attempt = begin_interpretation(
            ton_session,
            finding=finding,
            prompt_key="synthetic_prompt",
            prompt_version="v0",
            input_scope=InterpretationInputScope.STRUCTURED_ONLY,
        )
        complete_interpretation(
            ton_session,
            finding=finding,
            attempt=attempt,
            summary="Synthetic interpretation summary",
            llm_provider="synthetic-provider",
            model_name="synthetic-model",
        )
        assert finding.interpretation_status is InterpretationStatus.COMPLETED
        report = factories.make_report(ton_session)

        revision = factories.publish_synthetic_revision(
            ton_session, report=report, findings=[finding]
        )
        assert pinned_inputs(ton_session, revision.id).finding_ids == (finding.id,)

    @pytest.mark.parametrize(
        "status",
        (
            InterpretationStatus.PENDING,
            InterpretationStatus.RUNNING,
            InterpretationStatus.FAILED,
        ),
    )
    def test_a_non_final_interpretation_is_refused(
        self, ton_session: Session, status: InterpretationStatus
    ) -> None:
        """Readiness §8: a figure whose narrative the system has not finished
        assessing must not reach a board. One named case per non-final state."""
        _, _, _, _, finding = _detection(ton_session)
        finding.interpretation_status = status
        ton_session.flush()
        report = factories.make_report(ton_session)

        with pytest.raises(ValueError, match="not.*final"):
            factories.publish_synthetic_revision(
                ton_session, report=report, findings=[finding]
            )

    def test_the_refusal_names_the_offending_status(self, ton_session: Session) -> None:
        _, _, _, _, finding = _detection(ton_session)
        finding.interpretation_status = InterpretationStatus.RUNNING
        ton_session.flush()
        report = factories.make_report(ton_session)

        with pytest.raises(ValueError, match="RUNNING"):
            factories.publish_synthetic_revision(
                ton_session, report=report, findings=[finding]
            )

    def test_the_gate_reuses_the_003c_predicate(self) -> None:
        """Not a second copy of the rule. 003c owns the definition of final."""
        import inspect

        from onyx.db.ton import reports

        assert "is_interpretation_final" in inspect.getsource(reports)


class TestReproducibility:
    def test_a_later_occurrence_transition_does_not_rewrite_an_old_revision(
        self, ton_session: Session
    ) -> None:
        _, _, _, occurrence, finding = _detection(ton_session)
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(
            ton_session, report=report, findings=[finding], occurrences=[occurrence]
        )
        published_hash = revision.content_hash
        published_payload = dict(revision.canonical_payload)

        apply_transition__no_commit(
            ton_session,
            occurrence=occurrence,
            transition=OccurrenceTransition.ESCALATE_BY_CYCLE_RULE,
            actor_kind=OccurrenceActorKind.SYSTEM,
        )
        ton_session.expire_all()

        reloaded = get_revision(ton_session, report_id=report.id, revision_no=1)
        assert reloaded is not None
        assert reloaded.content_hash == published_hash
        assert reloaded.canonical_payload == published_payload
        assert verify_revision_hash(reloaded) is True

    def test_a_later_interpretation_does_not_rewrite_an_old_revision(
        self, ton_session: Session
    ) -> None:
        _, _, _, _, finding = _detection(ton_session)
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(
            ton_session, report=report, findings=[finding]
        )
        published_hash = revision.content_hash

        attempt = begin_interpretation(
            ton_session,
            finding=finding,
            prompt_key="synthetic_prompt",
            prompt_version="v0",
            input_scope=InterpretationInputScope.STRUCTURED_ONLY,
        )
        complete_interpretation(
            ton_session,
            finding=finding,
            attempt=attempt,
            summary="A narrative written after publication",
            llm_provider="synthetic-provider",
            model_name="synthetic-model",
        )
        ton_session.expire_all()

        reloaded = get_revision(ton_session, report_id=report.id, revision_no=1)
        assert reloaded is not None
        assert reloaded.content_hash == published_hash
        assert verify_revision_hash(reloaded) is True

    def test_a_later_rule_version_does_not_alter_an_old_revision(
        self, ton_session: Session
    ) -> None:
        """``RuleVersion`` is append-only, and the revision pins the version it
        used, so activating a new threshold cannot reinterpret what was
        published."""
        rule, rule_version, _, _, _ = _detection(ton_session)
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(
            ton_session, report=report, rule_versions=[rule_version]
        )
        published_hash = revision.content_hash

        newer = factories.make_rule_version(
            ton_session,
            rule=rule,
            version=2,
            parameters={"synthetic_threshold": "0.9"},
        )
        ton_session.expire_all()

        reloaded = get_revision(ton_session, report_id=report.id, revision_no=1)
        assert reloaded is not None
        assert reloaded.content_hash == published_hash
        assert verify_revision_hash(reloaded) is True
        assert pinned_inputs(ton_session, reloaded.id).rule_version_ids == (
            rule_version.id,
        )
        assert newer.id != rule_version.id

    def test_a_re_imported_source_does_not_alter_an_old_revision(
        self, ton_session: Session
    ) -> None:
        """A snapshot is a receipt for one extraction, so a re-import is a new
        receipt rather than a change to the pinned one."""
        snapshot = factories.make_source_snapshot(ton_session)
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(
            ton_session, report=report, source_snapshots=[snapshot]
        )
        published_hash = revision.content_hash

        re_imported = factories.make_source_snapshot(ton_session)
        ton_session.expire_all()

        reloaded = get_revision(ton_session, report_id=report.id, revision_no=1)
        assert reloaded is not None
        assert reloaded.content_hash == published_hash
        assert pinned_inputs(ton_session, reloaded.id).source_snapshot_ids == (
            snapshot.id,
        )
        assert re_imported.id != snapshot.id

    def test_the_payload_survives_the_jsonb_round_trip(
        self, ton_session: Session
    ) -> None:
        """The property hash verification rests on. PostgreSQL reorders JSONB
        keys, and the canonicalisation sorts them again."""
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(ton_session, report=report)
        revision_id = revision.id
        expected = revision.content_hash
        ton_session.commit()
        ton_session.expire_all()

        reloaded = ton_session.get(TonReportRevision, revision_id)
        assert reloaded is not None
        assert recompute_content_hash(reloaded) == expected

    def test_a_published_amount_is_stored_as_a_decimal_string(
        self, ton_session: Session
    ) -> None:
        """Never a JSON float. This is what makes the value reproducible at all."""
        report = factories.make_report(ton_session)
        revision = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body={"total_amount": ScaledDecimal(Decimal("1234.5"), scale=2)},
        )
        stored = revision.canonical_payload["body"]["total_amount"]
        assert stored == "1234.50"
        assert isinstance(stored, str)

    def test_a_changed_monetary_value_changes_the_hash(
        self, ton_session: Session
    ) -> None:
        """Requirement 16."""
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="10.00"),
        )
        second = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body=factories.synthetic_report_body(total="10.01"),
        )
        assert first.content_hash != second.content_hash

    def test_republishing_identical_content_yields_the_same_hash(
        self, ton_session: Session
    ) -> None:
        """The hash covers the content, not the provenance, so "did anything
        actually change?" is answerable."""
        report = factories.make_report(ton_session)
        first = factories.publish_synthetic_revision(ton_session, report=report)
        second = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            generated_at=datetime.datetime(2002, 4, 5, tzinfo=datetime.UTC),
        )
        assert first.content_hash == second.content_hash
        assert first.revision_no != second.revision_no

    def test_a_float_in_a_report_body_is_refused(self, ton_session: Session) -> None:
        report = factories.make_report(ton_session)
        with pytest.raises(ValueError, match="no canonical form"):
            factories.publish_synthetic_revision(
                ton_session, report=report, body={"total_amount": 1234.5}
            )

    def test_a_naive_generation_timestamp_is_refused(
        self, ton_session: Session
    ) -> None:
        report = factories.make_report(ton_session)
        with pytest.raises(ValueError, match="timezone-aware"):
            factories.publish_synthetic_revision(
                ton_session,
                report=report,
                generated_at=datetime.datetime(2001, 3, 1, 8, 30),
            )

    def test_a_missing_generator_version_is_refused(self, ton_session: Session) -> None:
        report = factories.make_report(ton_session)
        with pytest.raises(ValueError, match="generator_version is required"):
            publish_report_revision__no_commit(
                ton_session,
                report=report,
                body={},
                generator_version="  ",
                generated_at=factories.SYNTHETIC_GENERATED_AT,
            )

    def test_a_not_assessed_isc_dimension_and_its_weights_survive(
        self, ton_session: Session
    ) -> None:
        """Readiness §14.3: publishing a caveat alongside a score requires the
        payload to record a not-assessed dimension and the redistributed weights."""
        report = factories.make_report(ton_session, report_type=TonReportType.ISC)
        revision = factories.publish_synthetic_revision(
            ton_session,
            report=report,
            body={
                "dimensions": [
                    {
                        "key": "synthetic_dimension_a",
                        "assessed": True,
                        "weight": ScaledDecimal(Decimal("60"), scale=2),
                    },
                    {
                        "key": "synthetic_dimension_b",
                        "assessed": False,
                        "weight": ScaledDecimal(Decimal("0"), scale=2),
                        "not_assessed_reason": "synthetic data gap",
                    },
                ],
                "redistributed_weight": ScaledDecimal(Decimal("40"), scale=2),
                "caveat": "Uma dimensão não avaliada",
            },
        )
        ton_session.commit()
        ton_session.expire_all()

        reloaded = ton_session.get(TonReportRevision, revision.id)
        assert reloaded is not None
        body = reloaded.canonical_payload["body"]
        assert body["dimensions"][1]["assessed"] is False
        assert body["dimensions"][1]["not_assessed_reason"] == "synthetic data gap"
        assert body["redistributed_weight"] == "40.00"
        assert verify_revision_hash(reloaded) is True


class TestDefinitionHashPersistence:
    def test_a_new_rule_version_is_hashed_on_creation(
        self, ton_session: Session
    ) -> None:
        """003b left the column nullable for 003d. New rows now always carry a
        hash."""
        rule = create_rule__no_commit(
            ton_session,
            code=f"SYN-RULE-{factories.unique_suffix()}",
            domain=factories.RuleDomain.FINANCIAL,
            kind=factories.RuleKind.DETECTION,
        )
        rule_version = create_rule_version__no_commit(
            ton_session,
            rule=rule,
            title="Synthetic rule version",
            executor_key=factories.SYNTHETIC_EXECUTOR_KEY,
            provenance=factories.RuleProvenance.DERIVED,
            missing_data_behavior=factories.MissingDataBehavior.SKIP_WITH_NOTE,
            min_confidence_level=factories.EvidenceConfidenceLevel.C,
            post_resolution_policy=(
                factories.PostResolutionPolicy.REOPEN_SAME_OCCURRENCE
            ),
            identity_components=["rule_code", "period"],
            parameters={"synthetic_threshold": "0.5"},
        )

        assert rule_version.definition_hash is not None
        assert rule_version.definition_hash.startswith(f"{CANONICALIZATION_VERSION}:")
        assert definition_hash_matches(rule_version, rule_code=rule.code) is True

    def test_the_hash_survives_a_database_round_trip(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        expected = compute_definition_hash(rule_version, rule_code=rule.code)
        rule_version.definition_hash = expected
        ton_session.commit()
        ton_session.expire_all()

        reloaded = ton_session.get(RuleVersion, rule_version.id)
        assert reloaded is not None
        assert definition_hash_matches(reloaded, rule_code=rule.code) is True

    def test_the_backfill_hashes_only_unhashed_rows(self, ton_session: Session) -> None:
        """A development database may hold legitimate rows created before 003d.
        Nothing is deleted, recreated or overwritten."""
        _, already = factories.make_occurrence_rule_version(ton_session)
        already.definition_hash = "ton-canon-1:preexisting"
        rule, unhashed = factories.make_occurrence_rule_version(ton_session)
        unhashed.definition_hash = None
        ton_session.flush()

        result = backfill_definition_hashes__no_commit(ton_session)

        assert result.hashed == 1
        assert result.already_hashed == 1
        assert result.failed == []
        assert already.definition_hash == "ton-canon-1:preexisting"
        assert unhashed.definition_hash == compute_definition_hash(
            unhashed, rule_code=rule.code
        )

    def test_the_backfill_reports_a_row_it_cannot_hash_rather_than_faking_one(
        self, ton_session: Session
    ) -> None:
        """A float threshold cannot be canonicalised exactly. Recording a hash
        that cannot be re-derived would be worse than recording none, so the row
        is reported and left NULL."""
        _, broken = factories.make_occurrence_rule_version(ton_session)
        broken.definition_hash = None
        broken.parameters = {"synthetic_threshold": 0.5}
        ton_session.flush()

        result = backfill_definition_hashes__no_commit(ton_session)

        assert result.hashed == 0
        assert [row_id for row_id, _ in result.failed] == [broken.id]
        assert broken.definition_hash is None
