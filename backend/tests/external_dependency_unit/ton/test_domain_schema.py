"""TON domain schema spec — Plans 003b (``faee7eaa921e``) and 003c
(``6b0ca4eb29fb``).

Verifies what the migrations actually built, not what the models declare. Real
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
    OCCURRENCE_SHORT_CODE_SEQUENCE,
    REVISION_003A,
    REVISION_003B,
    TON_003B_TABLES,
    TON_003C_TABLES,
    TON_TABLES_AT_HEAD,
    column_names,
    column_types,
    constraint_names,
    downgrade,
    query_all,
    sequence_exists,
    table_names,
    upgrade,
)

# Tables that belong to 003d. Their absence is part of this slice's contract:
# 003c must not reach into the report or audit slice.
#
# The readiness gate historically said 003c creates "four ``*__UserGroup``
# junctions". ``TonReport`` does not exist until 003d, so its junction goes with
# it and ``ton_report__user_group`` is listed here rather than in the 003c set.
LATER_SLICE_TABLES: tuple[str, ...] = (
    "ton_report",
    "ton_report_revision",
    "ton_report__user_group",
    "ton_report_revision__analysis_run",
    "ton_report_revision__occurrence",
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
    # 003c. RESTRICT wherever deletion would break the audit chain, CASCADE where
    # the child has no meaning without its parent, SET NULL for a provenance-only
    # user reference.
    ("ton_occurrence", "rule_id", "ton_rule", "RESTRICT"),
    ("ton_occurrence", "current_rule_version_id", "ton_rule_version", "RESTRICT"),
    ("ton_occurrence", "business_unit_id", "ton_business_unit", "RESTRICT"),
    ("ton_occurrence", "contract_id", "ton_contract", "RESTRICT"),
    ("ton_occurrence", "superseded_by_occurrence_id", "ton_occurrence", "SET NULL"),
    ("ton_finding", "analysis_run_id", "ton_analysis_run", "RESTRICT"),
    ("ton_finding", "rule_version_id", "ton_rule_version", "RESTRICT"),
    ("ton_finding", "occurrence_id", "ton_occurrence", "CASCADE"),
    ("ton_finding", "business_unit_id", "ton_business_unit", "RESTRICT"),
    ("ton_finding", "contract_id", "ton_contract", "RESTRICT"),
    ("ton_finding_evidence", "finding_id", "ton_finding", "CASCADE"),
    (
        "ton_finding_evidence",
        "source_snapshot_id",
        "ton_source_snapshot",
        "RESTRICT",
    ),
    ("ton_finding_evidence", "file_record_id", "file_record", "SET NULL"),
    ("ton_finding_evidence", "document_id", "document", "SET NULL"),
    ("ton_finding_evidence", "chat_message_id", "chat_message", "SET NULL"),
    ("ton_finding_interpretation", "finding_id", "ton_finding", "CASCADE"),
    ("ton_occurrence_event", "occurrence_id", "ton_occurrence", "CASCADE"),
    # The one exception to the SET NULL convention. See
    # TestOccurrenceEventActorReference for why.
    ("ton_occurrence_event", "actor_user_id", "user", "RESTRICT"),
    ("ton_occurrence_event", "finding_id", "ton_finding", "SET NULL"),
    ("ton_occurrence_event", "rule_version_id", "ton_rule_version", "RESTRICT"),
    ("ton_occurrence_impact", "occurrence_id", "ton_occurrence", "CASCADE"),
    ("ton_occurrence_impact", "verified_by", "user", "SET NULL"),
    ("ton_occurrence_assignment", "occurrence_id", "ton_occurrence", "CASCADE"),
    ("ton_occurrence_assignment", "responsible_user_id", "user", "SET NULL"),
    ("ton_occurrence_assignment", "assigned_by_user_id", "user", "SET NULL"),
    ("ton_occurrence_note", "occurrence_id", "ton_occurrence", "CASCADE"),
    ("ton_occurrence_note", "author_user_id", "user", "SET NULL"),
    ("ton_occurrence_impacted_domain", "occurrence_id", "ton_occurrence", "CASCADE"),
    (
        "ton_business_unit__user_group",
        "business_unit_id",
        "ton_business_unit",
        "CASCADE",
    ),
    ("ton_business_unit__user_group", "user_group_id", "user_group", "CASCADE"),
    ("ton_contract__user_group", "contract_id", "ton_contract", "CASCADE"),
    ("ton_contract__user_group", "user_group_id", "user_group", "CASCADE"),
    ("ton_occurrence__user_group", "occurrence_id", "ton_occurrence", "CASCADE"),
    ("ton_occurrence__user_group", "user_group_id", "user_group", "CASCADE"),
)

# Monetary and quantity columns. Every one must be ``numeric``: a
# ``double precision`` here would make a published amount irreproducible, and the
# existing ``Numeric(18, 6, asdecimal=False)`` token-cost pattern must not spread
# into this domain.
EXPECTED_DECIMAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("ton_finding", "expected_value"),
    ("ton_finding", "actual_value"),
    ("ton_finding", "deviation_value"),
    ("ton_finding", "computed_impact_amount"),
    ("ton_occurrence_impact", "predicted_amount"),
    ("ton_occurrence_impact", "realized_amount"),
    ("ton_occurrence_impact", "quantity"),
    ("ton_occurrence_impact", "unit_cost"),
    ("ton_occurrence_impact", "sensitivity_pct"),
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
    """What the TON revisions create, and what they must leave alone."""

    def test_head_holds_exactly_the_expected_ton_tables(
        self, ton_database: str
    ) -> None:
        assert table_names(ton_database, "ton_") == set(TON_TABLES_AT_HEAD)

    def test_003c_adds_exactly_twelve_tables(self, ton_database: str) -> None:
        """Measured, not asserted from a list: downgrade to 003b and diff.

        This is the assertion that catches a table smuggled into 003c without a
        recorded decision, and the one that proves 003b's nine survive.
        """
        at_head = table_names(ton_database)

        downgrade(ton_database, REVISION_003B)

        at_003b = table_names(ton_database)
        assert at_head - at_003b == set(TON_003C_TABLES)
        assert table_names(ton_database, "ton_") == set(TON_003B_TABLES)

    def test_003c_downgrade_leaves_every_003b_structure_intact(
        self, ton_database: str
    ) -> None:
        """A 003c rollback must not touch the rule and analysis spine."""
        constraints_before = {
            table: constraint_names(ton_database, table) for table in TON_003B_TABLES
        }
        columns_before = {
            table: column_names(ton_database, table) for table in TON_003B_TABLES
        }

        downgrade(ton_database, REVISION_003B)

        for table in TON_003B_TABLES:
            assert constraint_names(ton_database, table) == constraints_before[table]
            assert column_names(ton_database, table) == columns_before[table]

    def test_003c_downgrade_removes_the_short_code_sequence(
        self, ton_database: str
    ) -> None:
        """A sequence left behind would make a re-upgrade fail on second run."""
        assert sequence_exists(ton_database, OCCURRENCE_SHORT_CODE_SEQUENCE)

        downgrade(ton_database, REVISION_003B)

        assert not sequence_exists(ton_database, OCCURRENCE_SHORT_CODE_SEQUENCE)

    def test_creates_no_later_slice_table(self, ton_database: str) -> None:
        present = table_names(ton_database)
        for table in LATER_SLICE_TABLES:
            assert table not in present, (
                f"{table} belongs to 003d and must not exist after 003c"
            )

    def test_creates_no_report_or_audit_table(self, ton_database: str) -> None:
        """An inverse assertion by substring, so a differently named report or
        audit table cannot slip past the explicit list above."""
        forbidden = {
            name
            for name in table_names(ton_database, "ton_")
            if "report" in name or "audit" in name
        }
        assert forbidden == set()

    def test_creates_no_roi_table(self, ton_database: str) -> None:
        """Realised ROI is a derived aggregation over verified impact rows, not a
        registry (readiness §13)."""
        forbidden = {name for name in table_names(ton_database) if "roi" in name}
        assert forbidden == set()

    def test_downgrade_to_003a_removes_every_ton_table(self, ton_database: str) -> None:
        before = table_names(ton_database)

        downgrade(ton_database, REVISION_003A)

        after = table_names(ton_database)
        assert before - after == set(TON_TABLES_AT_HEAD)
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


class TestFailClosedSchema:
    """The inverse assertions that keep the fail-closed decision durable.

    They run over every TON table at head, not just the current slice's, so a
    table added later cannot escape them by being listed elsewhere.
    """

    def test_no_ton_table_has_an_is_public_column(self, ton_database: str) -> None:
        """``Persona.is_public`` defaults to true and short-circuits the whole
        group ACL. A TON table must not have the column at all — a column that
        does not exist cannot be short-circuited by future code."""
        offenders = {
            table
            for table in TON_TABLES_AT_HEAD
            if "is_public" in column_names(ton_database, table)
        }
        assert offenders == set()

    def test_no_ton_table_has_a_permissive_visibility_column(
        self, ton_database: str
    ) -> None:
        """Also rejects the near-misses that would reintroduce fail-open
        visibility under another name."""
        forbidden = {"is_public", "public", "is_global", "public_permission"}
        for table in TON_TABLES_AT_HEAD:
            assert column_names(ton_database, table) & forbidden == set()

    def test_the_three_acl_junctions_exist(self, ton_database: str) -> None:
        """Three, not four. ``ton_report__user_group`` arrives with its table in
        003d — a junction to a table that does not exist would authorize
        nothing."""
        junctions = {
            name for name in table_names(ton_database, "ton_") if "__user_group" in name
        }
        assert junctions == {
            "ton_business_unit__user_group",
            "ton_contract__user_group",
            "ton_occurrence__user_group",
        }

    def test_finding_and_evidence_have_no_acl_junction(self, ton_database: str) -> None:
        """Their visibility derives from the owning occurrence. Two independent
        ACLs over one analytical case would eventually disagree (readiness
        §10)."""
        present = table_names(ton_database)
        assert "ton_finding__user_group" not in present
        assert "ton_finding_evidence__user_group" not in present


class TestNoSourceSystemWrites:
    """The advisory boundary of Prompt Mestre §12.1, enforced by absence."""

    def test_no_ton_column_writes_back_to_a_source_system(
        self, ton_database: str
    ) -> None:
        forbidden_fragments = (
            "glosa",
            "erp_write",
            "billing_write",
            "measurement_write",
            "push_to_",
            "sync_to_",
        )
        for table in TON_TABLES_AT_HEAD:
            for column in column_names(ton_database, table):
                assert not any(
                    fragment in column for fragment in forbidden_fragments
                ), f"{table}.{column} suggests a write back into a source system"


class TestNoRawModelOutputIsStored:
    """No chain-of-thought, no raw prompt body, no response transcript."""

    def test_interpretation_has_no_transcript_column(self, ton_database: str) -> None:
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
        columns = column_names(ton_database, "ton_finding_interpretation")
        for column in columns:
            assert not any(fragment in column for fragment in forbidden_fragments), (
                f"ton_finding_interpretation.{column} could hold hidden model "
                "output; only the business-facing interpretation is persisted"
            )

    def test_interpretation_stores_prompt_identity_not_prompt_content(
        self, ton_database: str
    ) -> None:
        """Reproducibility comes from the key and version, not the body."""
        columns = column_names(ton_database, "ton_finding_interpretation")
        assert {"prompt_key", "prompt_version"} <= columns


class TestDecimalColumns:
    """Money is exact. No monetary column is a floating-point type."""

    def test_every_amount_column_is_numeric(self, ton_database: str) -> None:
        for table, column in EXPECTED_DECIMAL_COLUMNS:
            actual = column_types(ton_database, table)[column]
            assert actual == "numeric", f"{table}.{column} is {actual}, not numeric"

    def test_no_ton_table_holds_a_floating_point_column(
        self, ton_database: str
    ) -> None:
        """An inverse assertion: the token-cost ``asdecimal=False`` pattern must
        not spread into this domain under any column name."""
        floating = {"double precision", "real"}
        for table in TON_TABLES_AT_HEAD:
            offenders = {
                name
                for name, sql_type in column_types(ton_database, table).items()
                if sql_type in floating
            }
            assert offenders == set(), f"{table} has floating-point columns"

    def test_evidence_extracted_value_stays_a_string(self, ton_database: str) -> None:
        """It records what the source stated, at the source's own scale."""
        assert (
            column_types(ton_database, "ton_finding_evidence")["extracted_value"]
            == "character varying"
        )


class TestFindingPinsTheRuleVersion:
    def test_finding_has_a_rule_version_id_and_no_rule_id(
        self, ton_database: str
    ) -> None:
        """Readiness §3: history references the version, never the rule alone.

        A ``rule_id`` column here could disagree with ``rule_version_id``, and a
        threshold change would then be able to reinterpret a published detection.
        """
        columns = column_names(ton_database, "ton_finding")
        assert "rule_version_id" in columns
        assert "rule_id" not in columns

    def test_finding_has_no_lifecycle_status_column(self, ton_database: str) -> None:
        """Lifecycle belongs to the occurrence. ``interpretation_status`` tracks
        the interpretation attempt, not the business case."""
        columns = column_names(ton_database, "ton_finding")
        assert "status" not in columns
        assert "resolved_at" not in columns
        assert "resolution" not in columns
        assert "interpretation_status" in columns


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


class TestOccurrenceUniqueness:
    """``UNIQUE(identity_key)`` is the deduplication boundary."""

    def test_identity_key_is_unique(self, ton_database: str) -> None:
        constraints = query_all(
            ton_database,
            "SELECT conname FROM pg_constraint c "
            "JOIN pg_class t ON t.oid = c.conrelid "
            "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey) "
            "WHERE t.relname = 'ton_occurrence' AND c.contype = 'u' "
            "AND a.attname = 'identity_key'",
        )
        assert constraints, "ton_occurrence.identity_key must be UNIQUE"

    def test_a_second_occurrence_with_the_same_identity_key_is_refused(
        self, ton_session: Session
    ) -> None:
        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        first = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        ton_session.add(
            _clone_occurrence_row(first.occurrence, rule.id, rule_version.id)
        )
        with pytest.raises(IntegrityError):
            ton_session.commit()

    def test_a_lineage_generation_pair_is_unique(self, ton_database: str) -> None:
        assert "uq_ton_occurrence_lineage_generation" in constraint_names(
            ton_database, "ton_occurrence"
        )


class TestFindingUniqueness:
    """A rerun of the same logical analysis is idempotent."""

    def test_the_run_rule_version_identity_triple_is_unique(
        self, ton_database: str
    ) -> None:
        assert "uq_ton_finding_run_rule_version_identity" in constraint_names(
            ton_database, "ton_finding"
        )

    def test_retrying_a_detection_in_the_same_run_is_refused_by_the_database(
        self, ton_session: Session
    ) -> None:
        """Asserted at the database, bypassing the domain resolution path.

        The domain path returns the existing occurrence instead of duplicating,
        and this is the guarantee underneath it: even a writer that skips the
        module cannot record the same detection twice.
        """
        from onyx.db.ton.models import Finding

        rule, rule_version = factories.make_occurrence_rule_version(ton_session)
        run = factories.make_analysis_run(ton_session)
        result = factories.record_synthetic_detection(
            ton_session, rule=rule, rule_version=rule_version, analysis_run=run
        )
        ton_session.commit()

        ton_session.add(
            Finding(
                analysis_run_id=run.id,
                rule_version_id=rule_version.id,
                occurrence_id=result.occurrence.id,
                identity_key=result.finding.identity_key,
                finding_kind=result.finding.finding_kind,
                domain=result.finding.domain,
                detected_at=result.finding.detected_at,
            )
        )
        with pytest.raises(IntegrityError):
            ton_session.commit()


class TestEvidenceConfidenceIsRequired:
    def test_confidence_level_is_not_nullable(self, ton_database: str) -> None:
        """Prompt Mestre §3.4: a published number without its A/B/C/D level is a
        defect, so the column cannot be null."""
        rows = query_all(
            ton_database,
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'ton_finding_evidence' "
            "AND column_name = 'confidence_level'",
        )
        assert rows == [("NO",)]

    def test_redaction_level_is_not_nullable(self, ton_database: str) -> None:
        rows = query_all(
            ton_database,
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'ton_finding_evidence' "
            "AND column_name = 'redaction_level'",
        )
        assert rows == [("NO",)]

    def test_redaction_level_has_no_server_default(self, ton_database: str) -> None:
        """The writer states how much identity a row carries; it is not assumed."""
        rows = query_all(
            ton_database,
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = 'ton_finding_evidence' "
            "AND column_name = 'redaction_level'",
        )
        assert rows == [(None,)]


class TestOccurrenceEventActorReference:
    """Why ``actor_user_id`` breaks the SET NULL convention.

    The human-only CHECK requires the column to be non-null for an authorized
    decision. ``SET NULL`` would void that guarantee the first time an account was
    hard deleted, so the reference is ``RESTRICT`` and an authorizing account stays
    referenceable.
    """

    def test_actor_user_id_is_restrict_not_set_null(self, ton_database: str) -> None:
        rows = query_all(ton_database, _FOREIGN_KEY_SQL)
        actual = {
            (row[0], row[1], row[3])
            for row in rows
            if row[0] == "ton_occurrence_event" and row[1] == "actor_user_id"
        }
        assert actual == {("ton_occurrence_event", "actor_user_id", "RESTRICT")}


class TestNoSeeding:
    """The migration creates schema only."""

    def test_every_003c_table_is_empty(self, ton_database: str) -> None:
        for table in TON_003C_TABLES:
            count = query_all(ton_database, f"SELECT count(*) FROM {table}")  # noqa: S608
            assert count == [(0,)], f"{table} was seeded"

    def test_no_acl_junction_row_is_seeded(self, ton_database: str) -> None:
        """A seeded junction row would grant access nobody decided to grant."""
        for table in (
            "ton_business_unit__user_group",
            "ton_contract__user_group",
            "ton_occurrence__user_group",
        ):
            assert query_all(ton_database, f"SELECT count(*) FROM {table}") == [  # noqa: S608
                (0,)
            ]

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
            # 003c — the constraints that carry this slice's guarantees.
            (
                "ton_occurrence_event",
                "ck_ton_occurrence_event_human_only_transitions",
            ),
            (
                "ton_occurrence_event",
                "ck_ton_occurrence_event_resolution_requires_user",
            ),
            (
                "ton_occurrence_event",
                "ck_ton_occurrence_event_user_actor_identified",
            ),
            ("ton_occurrence_event", "uq_ton_occurrence_event_sequence"),
            (
                "ton_occurrence",
                "ck_ton_occurrence_critical_requires_human_closure",
            ),
            ("ton_occurrence", "ck_ton_occurrence_first_generation_identity"),
            ("ton_occurrence", "ck_ton_occurrence_resolved_requires_timestamp"),
            ("ton_occurrence", "ck_ton_occurrence_no_self_supersede"),
            ("ton_occurrence", "ck_ton_occurrence_detection_order"),
            ("ton_occurrence", "uq_ton_occurrence_lineage_generation"),
            ("ton_finding", "uq_ton_finding_run_rule_version_identity"),
            ("ton_finding", "ck_ton_finding_period_order"),
            (
                "ton_finding_interpretation",
                "ck_ton_finding_interpretation_completed_has_summary",
            ),
            (
                "ton_finding_interpretation",
                "ck_ton_finding_interpretation_failed_has_class",
            ),
            (
                "ton_finding_interpretation",
                "ck_ton_finding_interpretation_class_only_on_failure",
            ),
            (
                "ton_finding_interpretation",
                "uq_ton_finding_interpretation_attempt",
            ),
            (
                "ton_occurrence_impact",
                "ck_ton_occurrence_impact_realized_requires_verification",
            ),
            ("ton_occurrence_impact", "ck_ton_occurrence_impact_has_an_amount"),
            (
                "ton_occurrence_impact",
                "ck_ton_occurrence_impact_unit_cost_source_required",
            ),
            (
                "ton_occurrence_assignment",
                "ck_ton_occurrence_assignment_completed_has_timestamp",
            ),
            ("ton_occurrence_note", "uq_ton_occurrence_note_sequence"),
            # 003b — unchanged by this slice, asserted so a 003c downgrade or a
            # future edit cannot quietly drop one.
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


def _clone_occurrence_row(occurrence: Any, rule_id: Any, rule_version_id: Any) -> Any:
    """A second occurrence carrying an existing ``identity_key``.

    Built by hand rather than through the domain path: the point is to prove the
    database refuses the duplicate, not that the module avoids creating one.
    """
    from onyx.db.ton.models import Occurrence

    return Occurrence(
        identity_key=occurrence.identity_key,
        logical_identity_key=occurrence.logical_identity_key,
        supersede_generation=occurrence.supersede_generation,
        rule_id=rule_id,
        current_rule_version_id=rule_version_id,
        owning_domain=occurrence.owning_domain,
        ledger_kind=occurrence.ledger_kind,
        criticality=occurrence.criticality,
        title="Duplicate identity attempt",
        first_detected_at=occurrence.first_detected_at,
        last_detected_at=occurrence.last_detected_at,
    )
