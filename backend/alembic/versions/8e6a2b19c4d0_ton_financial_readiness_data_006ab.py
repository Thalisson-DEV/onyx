"""Financial readiness decisions and pinned configuration revisions.

Revision ID: 8e6a2b19c4d0
Revises: 7da5b31c624e
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "8e6a2b19c4d0"
down_revision = "7da5b31c624e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ton_financial_mapping_revision", sa.Column("reason", sa.String(500)))
    op.add_column("ton_dre_structure_version", sa.Column("reason", sa.String(500)))
    op.add_column(
        "ton_financial_budget_fact",
        sa.Column(
            "period_mapping_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_mapping.id", ondelete="RESTRICT"),
        ),
    )
    op.drop_constraint(
        "uq_ton_financial_budget_run_record",
        "ton_financial_budget_fact",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_ton_financial_budget_run_record_period",
        "ton_financial_budget_fact",
        ["run_id", "source_record_id", "calendar_period"],
    )
    op.add_column(
        "ton_financial_normalization_run",
        sa.Column(
            "amount_basis_revision_number",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "ton_financial_normalization_run",
        sa.Column(
            "reconciliation_decision_number",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_table(
        "ton_financial_candidate_decision",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True)),
        sa.Column("evidence", sa.String(64), nullable=False),
        sa.Column("reference_digest", sa.String(64)),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(evidence = 'EXACT_CODE' AND target_id IS NOT NULL AND reference_digest IS NULL) "
            "OR (evidence = 'LEGACY_REFERENCE' AND target_id IS NULL AND reference_digest IS NOT NULL)",
            name="ck_ton_financial_candidate_decision_shape",
        ),
    )
    op.create_index(
        "ix_ton_financial_candidate_key",
        "ton_financial_candidate_decision",
        ["source_id", "kind", "source_key"],
    )
    op.create_table(
        "ton_financial_legacy_candidate",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("suggested_code", sa.String(100), nullable=False),
        sa.Column("suggested_label", sa.String(500)),
        sa.Column("reference_digest", sa.String(64), nullable=False),
        sa.Column("reference_label", sa.String(255), nullable=False),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_id",
            "kind",
            "source_key",
            "suggested_code",
            "reference_digest",
            name="uq_ton_financial_legacy_candidate",
        ),
    )
    op.create_index(
        "ix_ton_financial_legacy_candidate_key",
        "ton_financial_legacy_candidate",
        ["source_id", "kind", "source_key"],
    )
    op.create_table(
        "ton_financial_amount_basis_revision",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("basis", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("number > 0", name="ck_ton_financial_basis_revision_number"),
        sa.CheckConstraint(
            "basis IN ('MOVEMENT', 'FINAL')",
            name="ck_ton_financial_basis_revision_basis",
        ),
    )
    op.create_index(
        "ix_ton_financial_basis_account",
        "ton_financial_amount_basis_revision",
        ["account_id", "number"],
    )
    op.create_table(
        "ton_financial_reconciliation_decision",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "actual_source_record_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_parsed_source_record.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "billing_source_record_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_operational_source_record.id", ondelete="RESTRICT"),
        ),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "number > 0", name="ck_ton_financial_reconciliation_decision_number"
        ),
        sa.CheckConstraint(
            "actual_source_record_id IS NOT NULL OR billing_source_record_id IS NOT NULL",
            name="ck_ton_financial_reconciliation_decision_source",
        ),
        sa.CheckConstraint(
            "decision IN ('NG_AUTHORITATIVE', 'SUPPLEMENTAL', 'EXPECTED_DIFFERENCE', 'NOT_SAME_EVENT')",
            name="ck_ton_financial_reconciliation_decision_value",
        ),
    )
    op.create_index(
        "ix_ton_financial_reconciliation_decision_source",
        "ton_financial_reconciliation_decision",
        ["actual_source_record_id", "billing_source_record_id", "number"],
    )
    for table in (
        "ton_financial_candidate_decision",
        "ton_financial_legacy_candidate",
        "ton_financial_amount_basis_revision",
        "ton_financial_reconciliation_decision",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION ton_financial_immutable()"
        )


def downgrade() -> None:
    for table in (
        "ton_financial_reconciliation_decision",
        "ton_financial_amount_basis_revision",
        "ton_financial_legacy_candidate",
        "ton_financial_candidate_decision",
    ):
        op.drop_table(table)
    op.drop_column("ton_financial_normalization_run", "reconciliation_decision_number")
    op.drop_column("ton_financial_normalization_run", "amount_basis_revision_number")
    op.drop_constraint(
        "uq_ton_financial_budget_run_record_period",
        "ton_financial_budget_fact",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_ton_financial_budget_run_record",
        "ton_financial_budget_fact",
        ["run_id", "source_record_id"],
    )
    op.drop_column("ton_financial_budget_fact", "period_mapping_id")
    op.drop_column("ton_financial_mapping_revision", "reason")
    op.drop_column("ton_dre_structure_version", "reason")
