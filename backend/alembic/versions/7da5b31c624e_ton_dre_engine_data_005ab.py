"""Versioned DRE structure and immutable calculation results.

Revision ID: 7da5b31c624e
Revises: 6bc4d2e908fa
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "7da5b31c624e"
down_revision = "6bc4d2e908fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ton_dre_structure",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("label", sa.String(500), nullable=False),
    )
    op.create_table(
        "ton_dre_structure_version",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "structure_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_dre_structure.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("lines", JSONB, nullable=False),
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
            "structure_id", "number", name="uq_ton_dre_structure_version"
        ),
    )
    op.create_table(
        "ton_dre_account_mapping",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_dre_structure_version.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("line_code", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.UniqueConstraint(
            "version_id", "account_id", name="uq_ton_dre_account_mapping"
        ),
        sa.CheckConstraint(
            "status IN ('APPROVED', 'PENDING_APPROVAL')",
            name="ck_ton_dre_mapping_status",
        ),
    )
    op.create_table(
        "ton_dre_calculation_run",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("input_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "normalization_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_normalization_run.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "structure_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_dre_structure_version.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("period", sa.Date, nullable=False),
        sa.Column(
            "unit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
        ),
        sa.Column("blockers", JSONB, nullable=False),
        sa.Column("provenance", JSONB, nullable=False),
        sa.Column("engine_version", sa.String(32), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('READY', 'NOT_READY')", name="ck_ton_dre_run_status"
        ),
    )
    op.create_table(
        "ton_dre_result_line",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ton_dre_calculation_run.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("realizado", sa.Numeric(50, 25), nullable=False),
        sa.Column("orcado", sa.Numeric(50, 25), nullable=False),
        sa.Column("variance", sa.Numeric(50, 25), nullable=False),
        sa.Column("variance_percent", sa.Numeric(50, 25)),
        sa.Column("realizado_ytd", sa.Numeric(50, 25), nullable=False),
        sa.Column("orcado_ytd", sa.Numeric(50, 25), nullable=False),
        sa.Column("variance_ytd", sa.Numeric(50, 25), nullable=False),
        sa.Column("variance_percent_ytd", sa.Numeric(50, 25)),
        sa.UniqueConstraint("run_id", "code", name="uq_ton_dre_result_line"),
    )
    op.execute(
        "CREATE FUNCTION ton_dre_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'DRE history is immutable'; END $$"
    )
    for table in (
        "ton_dre_structure",
        "ton_dre_structure_version",
        "ton_dre_account_mapping",
        "ton_dre_calculation_run",
        "ton_dre_result_line",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION ton_dre_immutable()"
        )


def downgrade() -> None:
    op.drop_table("ton_dre_result_line")
    op.drop_table("ton_dre_calculation_run")
    op.drop_table("ton_dre_account_mapping")
    op.drop_table("ton_dre_structure_version")
    op.drop_table("ton_dre_structure")
    op.execute("DROP FUNCTION ton_dre_immutable()")
