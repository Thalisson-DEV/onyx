"""Source-level billing and budget records.

Revision ID: 3ac487f2d901
Revises: 4b7e2d9c1a36
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3ac487f2d901"
down_revision = "4b7e2d9c1a36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ton_operational_source_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sheet_name", sa.String(255), nullable=False),
        sa.Column("source_row_number", sa.Integer, nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("identifier", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("record_date", sa.Date),
        sa.Column("competence", sa.Date),
        sa.Column("amount", sa.Numeric(50, 25)),
        sa.Column("period_basis", sa.String(32)),
        sa.Column("numeric_values", postgresql.JSONB, nullable=False),
        sa.Column("typed_values", postgresql.JSONB, nullable=False),
        sa.Column("source_values", postgresql.JSONB, nullable=False),
        sa.Column("formula_cached", sa.Boolean, nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("duplicate_ordinal", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "source_id"],
            ["ton_source_snapshot.id", "ton_source_snapshot.source_id"],
            ondelete="RESTRICT",
            name="fk_ton_operational_record_snapshot_source",
        ),
        sa.ForeignKeyConstraint(
            ["execution_id", "snapshot_id"],
            [
                "ton_import_profile_execution.id",
                "ton_import_profile_execution.snapshot_id",
            ],
            ondelete="RESTRICT",
            name="fk_ton_operational_record_execution_snapshot",
        ),
        sa.UniqueConstraint(
            "execution_id",
            "sheet_name",
            "source_row_number",
            name="uq_ton_operational_record_locator",
        ),
        sa.CheckConstraint(
            "kind IN ('BILLING', 'BUDGET')", name="ck_ton_operational_record_kind"
        ),
        sa.CheckConstraint(
            "source_row_number >= 1 AND duplicate_ordinal >= 1",
            name="ck_ton_operational_record_positive",
        ),
    )
    op.create_index(
        "ix_ton_operational_record_execution_order",
        "ton_operational_source_record",
        ["execution_id", "sheet_name", "source_row_number"],
    )
    op.create_index(
        "ix_ton_operational_record_fingerprint",
        "ton_operational_source_record",
        ["execution_id", "fingerprint"],
    )
    op.execute(
        """
        CREATE FUNCTION ton_protect_operational_record() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM ton_import_profile_execution
                    WHERE id = NEW.execution_id AND status = 'RUNNING'
                ) THEN
                    RAISE EXCEPTION 'Operational records require a running execution';
                END IF;
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'Operational source records are immutable';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER ton_operational_record_immutable "
        "BEFORE INSERT OR UPDATE OR DELETE ON ton_operational_source_record "
        "FOR EACH ROW EXECUTE FUNCTION ton_protect_operational_record()"
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM ton_operational_source_record)")
    ):
        raise RuntimeError("Archive operational records before downgrade")
    op.execute(
        "DROP TRIGGER ton_operational_record_immutable ON ton_operational_source_record"
    )
    op.execute("DROP FUNCTION ton_protect_operational_record()")
    op.drop_index(
        "ix_ton_operational_record_fingerprint",
        table_name="ton_operational_source_record",
    )
    op.drop_index(
        "ix_ton_operational_record_execution_order",
        table_name="ton_operational_source_record",
    )
    op.drop_table("ton_operational_source_record")
