"""Deterministic NG financial review: review runs, recommendations, decisions.

Findings, evidence and occurrences reuse the 003c tables. Evidence gains two
nullable lineage pointers to the DATA-002 parsed record and parse execution.

Revision ID: 4b7e2d9c1a36
Revises: 9d2c8f0a7e31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "4b7e2d9c1a36"
down_revision = "9d2c8f0a7e31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ton_finding_evidence",
        sa.Column(
            "parsed_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_parsed_source_record.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "ton_finding_evidence",
        sa.Column(
            "import_execution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_import_profile_execution.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_ton_finding_evidence_parsed_record_id",
        "ton_finding_evidence",
        ["parsed_record_id"],
    )

    op.create_table(
        "ton_review_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_analysis_run.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt_no", sa.Integer, nullable=False),
        sa.Column("engine_version", sa.String(64), nullable=False),
        sa.Column("rule_set_digest", sa.String(100), nullable=False),
        sa.Column("rule_set", postgresql.JSONB, nullable=False),
        sa.Column("rule_evaluations", postgresql.JSONB, nullable=False),
        sa.Column("diagnostic_summary", postgresql.JSONB, nullable=False),
        sa.Column("statistics", postgresql.JSONB, nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column(
            "triggered_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["execution_id", "snapshot_id"],
            [
                "ton_import_profile_execution.id",
                "ton_import_profile_execution.snapshot_id",
            ],
            ondelete="RESTRICT",
            name="fk_ton_review_run_execution_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "source_id"],
            ["ton_source_snapshot.id", "ton_source_snapshot.source_id"],
            ondelete="RESTRICT",
            name="fk_ton_review_run_snapshot_source",
        ),
        sa.UniqueConstraint(
            "execution_id",
            "rule_set_digest",
            "attempt_no",
            name="uq_ton_review_run_attempt",
        ),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ton_review_run_status",
        ),
        sa.CheckConstraint(
            "(status = 'RUNNING') = (finished_at IS NULL)",
            name="ck_ton_review_run_finished",
        ),
        sa.CheckConstraint(
            "(status = 'FAILED') = (error_code IS NOT NULL)",
            name="ck_ton_review_run_error",
        ),
        sa.CheckConstraint("attempt_no >= 1", name="ck_ton_review_run_attempt"),
    )
    op.create_index(
        "ix_ton_review_run_source_started",
        "ton_review_run",
        ["source_id", "started_at"],
    )
    op.create_index("ix_ton_review_run_execution", "ton_review_run", ["execution_id"])
    # A RUNNING review can finish once. Terminal rows and identity never change.
    op.execute(
        """
        CREATE FUNCTION ton_protect_review_run() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Review runs are append-only';
            END IF;
            IF OLD.status <> 'RUNNING' THEN
                RAISE EXCEPTION 'Terminal review runs are immutable';
            END IF;
            IF NEW.id <> OLD.id OR NEW.analysis_run_id <> OLD.analysis_run_id
                OR NEW.source_id <> OLD.source_id
                OR NEW.snapshot_id <> OLD.snapshot_id
                OR NEW.execution_id <> OLD.execution_id
                OR NEW.attempt_no <> OLD.attempt_no
                OR NEW.engine_version <> OLD.engine_version
                OR NEW.rule_set_digest <> OLD.rule_set_digest
                OR NEW.rule_set <> OLD.rule_set
                OR NEW.started_at <> OLD.started_at THEN
                RAISE EXCEPTION 'Review run identity is immutable';
            END IF;
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER ton_review_run_protected "
        "BEFORE UPDATE OR DELETE ON ton_review_run "
        "FOR EACH ROW EXECUTE FUNCTION ton_protect_review_run()"
    )

    op.create_table(
        "ton_review_recommendation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_finding.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "review_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_review_run.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("evidence_level", sa.String(32), nullable=False),
        sa.Column("rationale_code", sa.String(64), nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("target_field", sa.String(64)),
        sa.Column("suggested_value", sa.Text),
        sa.Column("candidate_count", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(kind = 'DETERMINISTIC_CORRECTION') = (suggested_value IS NOT NULL)",
            name="ck_ton_review_recommendation_value_only_when_deterministic",
        ),
        sa.CheckConstraint(
            "kind <> 'DETERMINISTIC_CORRECTION' OR evidence_level = 'DETERMINISTIC'",
            name="ck_ton_review_recommendation_deterministic_level",
        ),
        sa.CheckConstraint(
            "candidate_count IS NULL OR candidate_count >= 0",
            name="ck_ton_review_recommendation_candidates",
        ),
    )
    op.create_index(
        "ix_ton_review_recommendation_run",
        "ton_review_recommendation",
        ["review_run_id"],
    )

    op.create_table(
        "ton_review_decision",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "occurrence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_occurrence.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recommendation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_review_recommendation.id", ondelete="CASCADE"),
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("justification_category", sa.String(32)),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column("authorization_reference", sa.String(200)),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "occurrence_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_occurrence_event.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind <> 'JUSTIFY_EXCEPTION' OR justification_category IS NOT NULL",
            name="ck_ton_review_decision_justification_category",
        ),
        sa.CheckConstraint(
            "(kind IN ('ACCEPT_RECOMMENDATION', 'REJECT_RECOMMENDATION')) "
            "= (recommendation_id IS NOT NULL)",
            name="ck_ton_review_decision_recommendation",
        ),
    )
    op.create_index(
        "ix_ton_review_decision_occurrence",
        "ton_review_decision",
        ["occurrence_id", "created_at"],
    )
    # Recommendations and decisions never change. Deletes stay possible only
    # through the occurrence cascade, which is an administrator act.
    op.execute(
        """
        CREATE FUNCTION ton_protect_review_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% rows are immutable', TG_TABLE_NAME;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER ton_review_recommendation_immutable "
        "BEFORE UPDATE ON ton_review_recommendation "
        "FOR EACH ROW EXECUTE FUNCTION ton_protect_review_append_only()"
    )
    op.execute(
        "CREATE TRIGGER ton_review_decision_immutable "
        "BEFORE UPDATE ON ton_review_decision "
        "FOR EACH ROW EXECUTE FUNCTION ton_protect_review_append_only()"
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM ton_review_run)")):
        raise RuntimeError("Remove or archive review runs before downgrading DATA-003")
    op.execute("DROP TRIGGER ton_review_decision_immutable ON ton_review_decision")
    op.execute(
        "DROP TRIGGER ton_review_recommendation_immutable ON ton_review_recommendation"
    )
    op.execute("DROP FUNCTION ton_protect_review_append_only()")
    op.drop_index("ix_ton_review_decision_occurrence", table_name="ton_review_decision")
    op.drop_table("ton_review_decision")
    op.drop_index(
        "ix_ton_review_recommendation_run", table_name="ton_review_recommendation"
    )
    op.drop_table("ton_review_recommendation")
    op.execute("DROP TRIGGER ton_review_run_protected ON ton_review_run")
    op.execute("DROP FUNCTION ton_protect_review_run()")
    op.drop_index("ix_ton_review_run_execution", table_name="ton_review_run")
    op.drop_index("ix_ton_review_run_source_started", table_name="ton_review_run")
    op.drop_table("ton_review_run")
    op.drop_index(
        "ix_ton_finding_evidence_parsed_record_id", table_name="ton_finding_evidence"
    )
    op.drop_column("ton_finding_evidence", "import_execution_id")
    op.drop_column("ton_finding_evidence", "parsed_record_id")
