"""TON closing treatments decided by the Controladoria.

Append-only treatment versions, the treatment number each normalization run
used, and the treatment applied to each actual fact.

Revision ID: d7a1e4c9b2f6
Revises: c4f2a9e6b1d3
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d7a1e4c9b2f6"
down_revision = "c4f2a9e6b1d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ton_closing_treatment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.Integer(), nullable=False, unique=True),
        sa.Column("treatment_key", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("effect", sa.String(32), nullable=False),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_account.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
        ),
        sa.Column("period_from", sa.Date()),
        sa.Column("period_to", sa.Date()),
        sa.Column(
            "target_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_account.id", ondelete="RESTRICT"),
        ),
        sa.Column("required_source", sa.String(500)),
        sa.Column("justification", sa.String(2000), nullable=False),
        sa.Column("evidence", sa.String(1000), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "treatment_key", "version", name="uq_ton_closing_treatment_version"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'BLOCKED', 'REVOKED')",
            name="ck_ton_closing_treatment_status",
        ),
        sa.CheckConstraint(
            "effect IN ('EXCLUDE', 'RECLASSIFY', 'REPLACE_BY_SOURCE')",
            name="ck_ton_closing_treatment_effect",
        ),
        sa.CheckConstraint(
            "status = 'REVOKED' OR account_id IS NOT NULL",
            name="ck_ton_closing_treatment_scope",
        ),
        sa.CheckConstraint(
            "(effect = 'RECLASSIFY') = (target_account_id IS NOT NULL)",
            name="ck_ton_closing_treatment_target",
        ),
        sa.CheckConstraint(
            "(status = 'BLOCKED') = (required_source IS NOT NULL)",
            name="ck_ton_closing_treatment_blocked",
        ),
        sa.CheckConstraint(
            "NOT (status = 'ACTIVE' AND effect = 'REPLACE_BY_SOURCE')",
            name="ck_ton_closing_treatment_source_effect",
        ),
        sa.CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
            name="ck_ton_closing_treatment_period",
        ),
    )
    # Same guard as the other financial decision tables (DATA-006ab).
    op.execute(
        "CREATE TRIGGER ton_closing_treatment_immutable "
        "BEFORE UPDATE OR DELETE ON ton_closing_treatment "
        "FOR EACH ROW EXECUTE FUNCTION ton_financial_immutable()"
    )
    op.add_column(
        "ton_financial_normalization_run",
        sa.Column("treatment_number", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ton_financial_actual_fact",
        sa.Column(
            "treatment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_closing_treatment.id", ondelete="RESTRICT"),
        ),
    )
    op.add_column(
        "ton_financial_actual_fact", sa.Column("treatment_effect", sa.String(32))
    )
    op.add_column(
        "ton_financial_actual_fact",
        sa.Column(
            "original_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_account.id", ondelete="RESTRICT"),
        ),
    )


def downgrade() -> None:
    op.drop_column("ton_financial_actual_fact", "original_account_id")
    op.drop_column("ton_financial_actual_fact", "treatment_effect")
    op.drop_column("ton_financial_actual_fact", "treatment_id")
    op.drop_column("ton_financial_normalization_run", "treatment_number")
    op.drop_table("ton_closing_treatment")
