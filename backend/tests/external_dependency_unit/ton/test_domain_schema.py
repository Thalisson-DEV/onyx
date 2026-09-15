"""TON domain schema spec — Plan 003b, revision ``faee7eaa921e``.

Verifies what the migration actually built, not what the models declare. Real
PostgreSQL is required: a unique constraint, an ``ON DELETE`` rule and a CHECK
constraint only exist once the migration ran, and a mock cannot show any of them.

Every case runs against a throwaway database cloned from a template at head. The
running development database is never written to, and is never read as schema
evidence.

Run with::

    uv run pytest backend/tests/external_dependency_unit/ton/test_domain_schema.py
"""

import datetime
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    AnalysisStepBlockedReason,
    AnalysisStepCode,
    AnalysisStepStatus,
    RuleDomain,
    RuleVersionOutcome,
    RuleVersionStatus,
)
from onyx.db.ton.models import AnalysisRunRuleVersion, AnalysisStep
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.scratch_db import (
    REVISION_003A,
    TON_003B_TABLES,
    column_names,
    downgrade,
    query_all,
    table_names,
    upgrade,
)

# Tables that belong to later slices. Their absence is part of this slice's
# contract: 003b must not reach into 003c or 003d.
LATER_SLICE_TABLES: tuple[str, ...] = (
    # 003c
    "ton_finding",
    "ton_finding_evidence",
    "ton_finding_interpretation",
    "ton_occurrence",
    "ton_occurrence_event",
    "ton_occurrence_impact",
    "ton_occurrence_assignment",
    "ton_occurrence_note",
    "ton_occurrence_impacted_domain",
    "ton_business_unit__user_group",
    "ton_contract__user_group",
    "ton_occurrence__user_group",
    # 003d
    "ton_report",
    "ton_report_revision",
    "ton_report__user_group",
    "ton_audit_event",
)

# (table, column, referenced table, expected delete rule)
EXPECTED_FOREIGN_KEYS: tuple[tuple[str, str, str, str], ...] = (
    ("ton_contract", "business_unit_id", "ton_business_unit", "RESTRICT"),
    ("ton_rule", "created_by", "user", "SET NULL"),
    ("ton_rule_version", "rule_id", "ton_rule", "CASCADE"),
    ("ton_rule_version", "approved_by", "user", "SET NULL"),
    ("ton_rule_version", "created_by", "user", "SET NULL"),
    ("ton_source_snapshot", "ingested_by", "user", "SET NULL"),
    ("ton_analysis_run", "triggered_by_user_id", "user", "SET NULL"),
    ("ton_analysis_run", "business_unit_id", "ton_business_unit", "RESTRICT"),
    (
        "ton_analysis_run_rule_version",
        "analysis_run_id",
        "ton_analysis_run",
        "CASCADE",
    ),
    (
        "ton_analysis_run_rule_version",
        "rule_version_id",
        "ton_rule_version",
        "RESTRICT",
    ),
    (
        "ton_analysis_run__source_snapshot",
        "analysis_run_id",
        "ton_analysis_run",
        "CASCADE",
    ),
    (
        "ton_analysis_run__source_snapshot",
        "source_snapshot_id",
        "ton_source_snapshot",
        "RESTRICT",
    ),
    ("ton_analysis_step", "analysis_run_id", "ton_analysis_run", "CASCADE"),
    ("ton_analysis_step", "business_unit_id", "ton_business_unit", "RESTRICT"),
    ("ton_analysis_step", "blocked_by_step_id", "ton_analysis_step", "CASCADE"),
)

_FOREIGN_KEY_SQL = """
SELECT tc.table_name,
       kcu.column_name,
       ccu.table_name AS referenced_table,
       rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON kcu.constraint_name = tc.constraint_name
 AND kcu.constraint_schema = tc.constraint_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.constraint_schema = tc.constraint_schema
JOIN information_schema.referential_constraints rc
  ON rc.constraint_name = tc.constraint_name
 AND rc.constraint_schema = tc.constraint_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND tc.table_name LIKE 'ton\\_%'
"""

_CONSTRAINT_NAME_SQL = """
SELECT conname
FROM pg_constraint
JOIN pg_class ON pg_class.oid = pg_constraint.conrelid
WHERE pg_class.relname = :table
"""

_INDEX_SQL = """
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = :table
"""


class TestMigrationShape:
    """What revision faee7eaa921e creates, and what it must leave alone."""

    def test_creates_exactly_the_nine_expected_tables(self, ton_database: str) -> None:
        assert table_names(ton_database, "ton_") == set(TON_003B_TABLES)

    def test_creates_no_later_slice_table(self, ton_database: str) -> None:
        present = table_names(ton_database)
        for table in LATER_SLICE_TABLES:
            assert table not in present, (
                f"{table} belongs to a later slice and must not exist after 003b"
            )

    def test_creates_no_finding_or_occurrence_table(self, ton_database: str) -> None:
        """An inverse assertion by substring, so a differently named Finding or
        Occurrence table cannot slip past the explicit list above."""
        forbidden = {
            name
            for name in table_names(ton_database)
            if "finding" in name or "occurrence" in name
        }
        assert forbidden == set()

    def test_creates_no_report_or_audit_table(self, ton_database: str) -> None:
        forbidden = {
            name
            for name in table_names(ton_database, "ton_")
            if "report" in name or "audit" in name
        }
        assert forbidden == set()

    def test_downgrade_removes_only_003b_structures(self, ton_database: str) -> None:
        before = table_names(ton_database)

        downgrade(ton_database, REVISION_003A)

        after = table_names(ton_database)
        assert before - after == set(TON_003B_TABLES)
        assert after - before == set(), "downgrade must not create anything"
        assert query_all(ton_database, "SELECT version_num FROM alembic_version") == [
            (REVISION_003A,)
        ]

    def test_downgrade_then_upgrade_restores_the_same_tables(
        self, ton_database: str
    ) -> None:
        before = table_names(ton_database)

        downgrade(ton_database, REVISION_003A)
        upgrade(ton_database, "head")

        assert table_names(ton_database) == before


class TestFailClosedPreparation:
    """The inverse assertion that keeps the fail-closed decision durable."""

    def test_no_ton_table_has_an_is_public_column(self, ton_database: str) -> None:
        """``Persona.is_public`` defaults to true and short-circuits the whole
        group ACL. A TON table must not have the column at all — a column that
        does not exist cannot be short-circuited by future code."""
        offenders = {
            table
            for table in TON_003B_TABLES
            if "is_public" in column_names(ton_database, table)
        }
        assert offenders == set()

    def test_no_ton_table_has_a_permissive_visibility_column(
        self, ton_database: str
    ) -> None:
        """Also rejects the near-misses that would reintroduce fail-open
        visibility under another name."""
        forbidden = {"is_public", "public", "is_global", "public_permission"}
        for table in TON_003B_TABLES:
            assert column_names(ton_database, table) & forbidden == set()


class TestUniqueness:
    def test_rule_code_is_unique(self, ton_session: Session) -> None:
        shared_code = f"SYN-DUP-{factories.unique_suffix()}"
        factories.make_rule(ton_session, code=shared_code)

        with pytest.raises(IntegrityError):
            factories.make_rule(ton_session, code=shared_code)

    def test_rule_id_and_version_are_unique_together(
        self, ton_session: Session
    ) -> None:
        rule = factories.make_rule(ton_session)
        factories.make_rule_version(ton_session, rule=rule, version=1)

        with pytest.raises(IntegrityError):
            factories.make_rule_version(ton_session, rule=rule, version=1)

    def test_the_same_version_number_is_free_on_a_different_rule(
        self, ton_session: Session
    ) -> None:
        first = factories.make_rule(ton_session)
        second = factories.make_rule(ton_session)

        factories.make_rule_version(ton_session, rule=first, version=1)
        factories.make_rule_version(ton_session, rule=second, version=1)

        ton_session.commit()

    def test_analysis_run_idempotency_key_is_unique(self, ton_session: Session) -> None:
        key = f"syn-idem-{factories.unique_suffix()}"
        factories.make_analysis_run(ton_session, idempotency_key=key)

        with pytest.raises(IntegrityError):
            factories.make_analysis_run(ton_session, idempotency_key=key)

    def test_analysis_step_scope_is_unique_including_run_wide(
        self, ton_session: Session
    ) -> None:
        """``NULLS NOT DISTINCT``: the run-wide scope is one row, not many.

        Without it Postgres treats each NULL as distinct, and a run could hold
        several rows for the same step in the same scope — which would make the
        blocking decision non-deterministic.
        """
        run = factories.make_analysis_run(ton_session)
        factories.make_step(ton_session, run=run, step_code=AnalysisStepCode.INGESTION)

        with pytest.raises(IntegrityError):
            factories.make_step(
                ton_session, run=run, step_code=AnalysisStepCode.INGESTION
            )

    def test_analysis_step_scope_allows_sibling_domains(
        self, ton_session: Session
    ) -> None:
        run = factories.make_analysis_run(ton_session)
        unit = factories.make_business_unit(ton_session)

        factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.DETECTION,
            domain=RuleDomain.FINANCIAL,
            business_unit=unit,
        )
        factories.make_step(
            ton_session,
            run=run,
            step_code=AnalysisStepCode.DETECTION,
            domain=RuleDomain.FLEET,
            business_unit=unit,
        )

        ton_session.commit()


class TestForeignKeys:
    def test_every_expected_foreign_key_exists_with_its_delete_rule(
        self, ton_database: str
    ) -> None:
        rows = query_all(ton_database, _FOREIGN_KEY_SQL)
        actual: set[tuple[Any, ...]] = {
            (row[0], row[1], row[2], row[3]) for row in rows
        }

        for expected in EXPECTED_FOREIGN_KEYS:
            assert expected in actual, f"missing or wrong ondelete: {expected}"

    def test_no_unexpected_ton_foreign_key_exists(self, ton_database: str) -> None:
        """Catches a foreign key added without a recorded ``ondelete`` decision."""
        rows = query_all(ton_database, _FOREIGN_KEY_SQL)
        actual = {(row[0], row[1], row[2], row[3]) for row in rows}
        assert actual == set(EXPECTED_FOREIGN_KEYS)

    def test_a_rule_version_used_by_a_run_cannot_be_deleted(
        self, ton_session: Session
    ) -> None:
        """``RESTRICT`` keeps the audit trail whole: what a run measured against
        stays referenceable."""
        run = factories.make_analysis_run(ton_session)
        rule = factories.make_rule(ton_session)
        rule_version = factories.make_rule_version(ton_session, rule=rule)
        ton_session.add(
            AnalysisRunRuleVersion(
                analysis_run_id=run.id,
                rule_version_id=rule_version.id,
                outcome=RuleVersionOutcome.EXECUTED,
                finding_count=0,
            )
        )
        ton_session.commit()

        ton_session.delete(rule_version)
        with pytest.raises(IntegrityError):
            ton_session.commit()

    def test_deleting_a_run_removes_its_steps_and_links(
        self, ton_session: Session
    ) -> None:
        """The database cascade does the work, so the envelope never leaves
        orphaned steps or provenance links behind."""
        run = factories.make_analysis_run(ton_session)
        cause = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.BASE_VALIDATION
        )
        blocked = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.DETECTION
        )
        blocked.status = AnalysisStepStatus.BLOCKED
        blocked.blocked_by_step_id = cause.id
        blocked.blocked_reason = AnalysisStepBlockedReason.PREREQUISITE_FAILED
        ton_session.commit()
        run_id = run.id

        ton_session.delete(run)
        ton_session.commit()

        remaining = (
            ton_session.query(AnalysisStep).filter_by(analysis_run_id=run_id).count()
        )
        assert remaining == 0


class TestRuleVersionApprovalConstraint:
    """``ACTIVE`` requires a recorded approval — as a database property."""

    def test_active_without_approval_is_rejected(self, ton_session: Session) -> None:
        rule = factories.make_rule(ton_session)

        with pytest.raises(IntegrityError) as exc_info:
            factories.make_rule_version(
                ton_session,
                rule=rule,
                status=RuleVersionStatus.ACTIVE,
                approved_by=None,
                approved_at=None,
            )
        assert "ck_ton_rule_version_active_requires_approval" in str(exc_info.value)

    def test_active_with_only_an_approver_is_rejected(
        self, ton_session: Session
    ) -> None:
        """Half an approval record is not an approval."""
        user = factories.make_user(ton_session)
        rule = factories.make_rule(ton_session)

        with pytest.raises(IntegrityError):
            factories.make_rule_version(
                ton_session,
                rule=rule,
                status=RuleVersionStatus.ACTIVE,
                approved_by=user.id,
                approved_at=None,
            )

    def test_active_with_a_full_approval_is_accepted(
        self, ton_session: Session
    ) -> None:
        user = factories.make_user(ton_session)
        rule = factories.make_rule(ton_session)

        rule_version = factories.make_rule_version(
            ton_session,
            rule=rule,
            status=RuleVersionStatus.ACTIVE,
            approved_by=user.id,
            approved_at=datetime.datetime(2001, 3, 1, tzinfo=datetime.UTC),
            approval_reference="synthetic-approval-1",
        )
        ton_session.commit()

        assert rule_version.status is RuleVersionStatus.ACTIVE

    def test_a_draft_needs_no_approval(self, ton_session: Session) -> None:
        rule = factories.make_rule(ton_session)
        factories.make_rule_version(
            ton_session, rule=rule, status=RuleVersionStatus.DRAFT
        )
        ton_session.commit()

    def test_test_only_needs_no_approval_and_stays_distinguishable(
        self, ton_session: Session
    ) -> None:
        """A TEST_ONLY version is runnable without approval, and must remain
        distinct from ACTIVE so it can never reach a business audience."""
        rule = factories.make_rule(ton_session)
        rule_version = factories.make_rule_version(
            ton_session, rule=rule, status=RuleVersionStatus.TEST_ONLY
        )
        ton_session.commit()

        assert rule_version.status is RuleVersionStatus.TEST_ONLY
        assert rule_version.status is not RuleVersionStatus.ACTIVE

    def test_effective_range_must_not_run_backwards(self, ton_session: Session) -> None:
        rule = factories.make_rule(ton_session)

        with pytest.raises(IntegrityError) as exc_info:
            factories.make_rule_version(
                ton_session,
                rule=rule,
                effective_from=datetime.date(2001, 6, 1),
                effective_to=datetime.date(2001, 5, 1),
            )
        assert "ck_ton_rule_version_effective_order" in str(exc_info.value)


class TestAnalysisStepBlockedConstraint:
    """A blocked step always names its cause — as a database property."""

    def test_blocked_without_cause_or_reason_is_rejected(
        self, ton_session: Session
    ) -> None:
        run = factories.make_analysis_run(ton_session)
        step = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.DETECTION
        )
        ton_session.commit()

        step.status = AnalysisStepStatus.BLOCKED
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_analysis_step_blocked_requires_cause" in str(exc_info.value)

    def test_blocked_with_a_reason_but_no_cause_is_rejected(
        self, ton_session: Session
    ) -> None:
        run = factories.make_analysis_run(ton_session)
        step = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.DETECTION
        )
        ton_session.commit()

        step.status = AnalysisStepStatus.BLOCKED
        step.blocked_reason = AnalysisStepBlockedReason.BASE_REPROVED
        with pytest.raises(IntegrityError):
            ton_session.commit()

    def test_blocked_with_a_cause_but_no_reason_is_rejected(
        self, ton_session: Session
    ) -> None:
        run = factories.make_analysis_run(ton_session)
        cause = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.BASE_VALIDATION
        )
        step = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.DETECTION
        )
        ton_session.commit()

        step.status = AnalysisStepStatus.BLOCKED
        step.blocked_by_step_id = cause.id
        with pytest.raises(IntegrityError):
            ton_session.commit()

    def test_blocked_with_both_is_accepted(self, ton_session: Session) -> None:
        run = factories.make_analysis_run(ton_session)
        cause = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.BASE_VALIDATION
        )
        step = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.DETECTION
        )

        step.status = AnalysisStepStatus.BLOCKED
        step.blocked_by_step_id = cause.id
        step.blocked_reason = AnalysisStepBlockedReason.BASE_REPROVED
        ton_session.commit()

        assert step.blocked_by_step_id == cause.id

    def test_a_step_cannot_be_its_own_cause(self, ton_session: Session) -> None:
        run = factories.make_analysis_run(ton_session)
        step = factories.make_step(
            ton_session, run=run, step_code=AnalysisStepCode.DETECTION
        )
        ton_session.commit()

        step.status = AnalysisStepStatus.BLOCKED
        step.blocked_by_step_id = step.id
        step.blocked_reason = AnalysisStepBlockedReason.PREREQUISITE_FAILED
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_analysis_step_no_self_block" in str(exc_info.value)


class TestRunRuleVersionConstraint:
    def test_a_skipped_rule_cannot_report_findings(self, ton_session: Session) -> None:
        run = factories.make_analysis_run(ton_session)
        rule_version = factories.make_rule_version(
            ton_session, rule=factories.make_rule(ton_session)
        )

        ton_session.add(
            AnalysisRunRuleVersion(
                analysis_run_id=run.id,
                rule_version_id=rule_version.id,
                outcome=RuleVersionOutcome.SKIPPED_MISSING_DATA,
                finding_count=2,
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            ton_session.commit()
        assert "ck_ton_analysis_run_rule_version_skipped_has_no_findings" in str(
            exc_info.value
        )


class TestNoSeeding:
    """The migration creates schema only."""

    def test_no_rule_row_is_seeded(self, ton_database: str) -> None:
        assert query_all(ton_database, "SELECT count(*) FROM ton_rule") == [(0,)]

    def test_no_rule_version_row_is_seeded(self, ton_database: str) -> None:
        assert query_all(ton_database, "SELECT count(*) FROM ton_rule_version") == [
            (0,)
        ]

    def test_no_business_unit_or_contract_row_is_seeded(
        self, ton_database: str
    ) -> None:
        """The Vale Norte unit lists still need owner validation, so the schema
        provides structure only."""
        assert query_all(ton_database, "SELECT count(*) FROM ton_business_unit") == [
            (0,)
        ]
        assert query_all(ton_database, "SELECT count(*) FROM ton_contract") == [(0,)]

    def test_every_003b_table_is_empty(self, ton_database: str) -> None:
        for table in TON_003B_TABLES:
            count = query_all(ton_database, f"SELECT count(*) FROM {table}")  # noqa: S608
            assert count == [(0,)], f"{table} was seeded"


class TestExpectedConstraintNames:
    """The named constraints later slices and operators rely on."""

    @pytest.mark.parametrize(
        ("table", "constraint"),
        [
            ("ton_rule_version", "ck_ton_rule_version_active_requires_approval"),
            ("ton_rule_version", "ck_ton_rule_version_effective_order"),
            ("ton_rule_version", "ck_ton_rule_version_positive"),
            ("ton_rule_version", "uq_ton_rule_version_rule_version"),
            ("ton_contract", "ck_ton_contract_date_order"),
            ("ton_source_snapshot", "ck_ton_source_snapshot_period_order"),
            ("ton_analysis_run", "ck_ton_analysis_run_period_order"),
            ("ton_analysis_run", "ck_ton_analysis_run_finished_requires_start"),
            ("ton_analysis_run", "ck_ton_analysis_run_attempt_positive"),
            (
                "ton_analysis_run_rule_version",
                "ck_ton_analysis_run_rule_version_skipped_has_no_findings",
            ),
            ("ton_analysis_step", "ck_ton_analysis_step_blocked_requires_cause"),
            ("ton_analysis_step", "ck_ton_analysis_step_no_self_block"),
            ("ton_analysis_step", "ck_ton_analysis_step_finished_requires_start"),
        ],
    )
    def test_constraint_exists(
        self, ton_database: str, table: str, constraint: str
    ) -> None:
        names = {
            str(row[0])
            for row in query_all(ton_database, _CONSTRAINT_NAME_SQL, {"table": table})
        }
        assert constraint in names

    def test_scope_index_declares_nulls_not_distinct(self, ton_database: str) -> None:
        definitions = {
            str(row[0]): str(row[1])
            for row in query_all(
                ton_database, _INDEX_SQL, {"table": "ton_analysis_step"}
            )
        }
        assert "uq_ton_analysis_step_scope" in definitions
        assert "NULLS NOT DISTINCT" in definitions["uq_ton_analysis_step_scope"]

    def test_snapshot_association_is_queryable_in_reverse(
        self, ton_database: str
    ) -> None:
        """The reverse index is what makes "which analyses used snapshot X?"
        cheap; the composite primary key only covers the forward direction."""
        definitions = {
            str(row[0])
            for row in query_all(
                ton_database,
                _INDEX_SQL,
                {"table": "ton_analysis_run__source_snapshot"},
            )
        }
        assert "ix_ton_analysis_run__source_snapshot_snapshot_id" in definitions
