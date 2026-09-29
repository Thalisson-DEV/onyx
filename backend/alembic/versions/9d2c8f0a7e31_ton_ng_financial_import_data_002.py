"""Versioned NG financial import profiles and parsed source records.

Revision ID: 9d2c8f0a7e31
Revises: 6be7c77e49ce
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import SchemaItem

revision = "9d2c8f0a7e31"
down_revision = "6be7c77e49ce"
branch_labels = None
depends_on = None

AMOUNT_COLUMNS = (
    "movement_amount",
    "movement_retention_amount",
    "movement_net_amount",
    "installment_retention_amount",
    "installment_net_amount",
    "interest_amount",
    "penalty_amount",
    "discount_amount",
    "expense_amount",
    "loss_amount",
    "other_deduction_amount",
    "final_amount",
)


def upgrade() -> None:
    op.create_table(
        "ton_import_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("column_map", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_id",
            "key",
            "version",
            name="uq_ton_import_profile_source_key_version",
        ),
        sa.UniqueConstraint("id", "source_id", name="uq_ton_import_profile_id_source"),
        sa.CheckConstraint("version >= 1", name="ck_ton_import_profile_version"),
    )
    op.execute(
        """
        CREATE FUNCTION ton_protect_import_profile() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Import profiles are immutable';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER ton_import_profile_immutable "
        "BEFORE UPDATE OR DELETE ON ton_import_profile "
        "FOR EACH ROW EXECUTE FUNCTION ton_protect_import_profile()"
    )

    op.create_table(
        "ton_import_profile_execution",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("statistics", postgresql.JSONB, nullable=False),
        sa.Column("diagnostics", postgresql.JSONB, nullable=False),
        sa.Column("sheet_summaries", postgresql.JSONB, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "source_id"],
            ["ton_source_snapshot.id", "ton_source_snapshot.source_id"],
            ondelete="RESTRICT",
            name="fk_ton_profile_execution_snapshot_source",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "source_id"],
            ["ton_import_profile.id", "ton_import_profile.source_id"],
            ondelete="RESTRICT",
            name="fk_ton_profile_execution_profile_source",
        ),
        sa.UniqueConstraint(
            "id", "snapshot_id", name="uq_ton_profile_execution_id_snapshot"
        ),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SUCCEEDED', 'PARTIAL', 'FAILED')",
            name="ck_ton_profile_execution_status",
        ),
        sa.CheckConstraint(
            "(status = 'RUNNING') = (finished_at IS NULL)",
            name="ck_ton_profile_execution_finished",
        ),
        sa.CheckConstraint(
            "(status = 'FAILED') = (error_code IS NOT NULL)",
            name="ck_ton_profile_execution_error",
        ),
    )
    op.create_index(
        "ix_ton_profile_execution_snapshot",
        "ton_import_profile_execution",
        ["snapshot_id"],
    )
    # A RUNNING execution can finish once. Terminal rows never change.
    op.execute(
        """
        CREATE FUNCTION ton_protect_terminal_profile_execution() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status <> 'RUNNING' THEN
                RAISE EXCEPTION 'Terminal profile executions are immutable';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Profile executions are append-only';
            END IF;
            IF NEW.id <> OLD.id OR NEW.source_id <> OLD.source_id
                OR NEW.snapshot_id <> OLD.snapshot_id
                OR NEW.profile_id <> OLD.profile_id
                OR NEW.started_at <> OLD.started_at THEN
                RAISE EXCEPTION 'Profile execution identity is immutable';
            END IF;
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER ton_profile_execution_terminal "
        "BEFORE UPDATE OR DELETE ON ton_import_profile_execution "
        "FOR EACH ROW EXECUTE FUNCTION ton_protect_terminal_profile_execution()"
    )

    columns: list[SchemaItem] = [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sheet_name", sa.String(255), nullable=False),
        sa.Column("source_row_number", sa.Integer, nullable=False),
        sa.Column("sheet_month", sa.Integer, nullable=False),
        sa.Column("account_code", sa.String(100), nullable=False),
        sa.Column("account_label", sa.Text, nullable=False),
        sa.Column("emission_date", sa.Date, nullable=False),
        sa.Column("administrative_unit", sa.Text),
        sa.Column("document_number", sa.Text),
        sa.Column("history", sa.Text, nullable=False),
    ]
    columns.extend(sa.Column(name, sa.Numeric(30, 10)) for name in AMOUNT_COLUMNS)
    columns.extend(
        [
            sa.Column("source_values", postgresql.JSONB, nullable=False),
            sa.Column("fingerprint", sa.String(64), nullable=False),
            sa.Column("duplicate_ordinal", sa.Integer, nullable=False),
            sa.ForeignKeyConstraint(
                ["snapshot_id", "source_id"],
                ["ton_source_snapshot.id", "ton_source_snapshot.source_id"],
                ondelete="RESTRICT",
                name="fk_ton_parsed_record_snapshot_source",
            ),
            sa.ForeignKeyConstraint(
                ["execution_id", "snapshot_id"],
                [
                    "ton_import_profile_execution.id",
                    "ton_import_profile_execution.snapshot_id",
                ],
                ondelete="RESTRICT",
                name="fk_ton_parsed_record_execution_snapshot",
            ),
            sa.UniqueConstraint(
                "execution_id",
                "sheet_name",
                "source_row_number",
                name="uq_ton_parsed_record_locator",
            ),
            sa.CheckConstraint(
                "sheet_month BETWEEN 1 AND 12", name="ck_ton_parsed_record_month"
            ),
            sa.CheckConstraint(
                "source_row_number >= 1 AND duplicate_ordinal >= 1",
                name="ck_ton_parsed_record_positive",
            ),
        ]
    )
    op.create_table("ton_parsed_source_record", *columns)
    op.create_index(
        "ix_ton_parsed_record_execution_order",
        "ton_parsed_source_record",
        ["execution_id", "sheet_month", "source_row_number"],
    )
    op.create_index(
        "ix_ton_parsed_record_fingerprint",
        "ton_parsed_source_record",
        ["execution_id", "fingerprint"],
    )
    # Records may be inserted only while their execution is RUNNING.
    op.execute(
        """
        CREATE FUNCTION ton_protect_parsed_record() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM ton_import_profile_execution
                    WHERE id = NEW.execution_id AND status = 'RUNNING'
                ) THEN
                    RAISE EXCEPTION 'Parsed records require a running execution';
                END IF;
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'Parsed source records are immutable';
        END $$
        """
    )
    op.execute(
        "CREATE TRIGGER ton_parsed_record_immutable "
        "BEFORE INSERT OR UPDATE OR DELETE ON ton_parsed_source_record "
        "FOR EACH ROW EXECUTE FUNCTION ton_protect_parsed_record()"
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM ton_import_profile)")
    ):
        raise RuntimeError(
            "Remove or archive import profiles before downgrading DATA-002"
        )
    op.execute("DROP TRIGGER ton_parsed_record_immutable ON ton_parsed_source_record")
    op.execute("DROP FUNCTION ton_protect_parsed_record()")
    op.drop_index(
        "ix_ton_parsed_record_fingerprint", table_name="ton_parsed_source_record"
    )
    op.drop_index(
        "ix_ton_parsed_record_execution_order", table_name="ton_parsed_source_record"
    )
    op.drop_table("ton_parsed_source_record")
    op.execute(
        "DROP TRIGGER ton_profile_execution_terminal ON ton_import_profile_execution"
    )
    op.execute("DROP FUNCTION ton_protect_terminal_profile_execution()")
    op.drop_index(
        "ix_ton_profile_execution_snapshot", table_name="ton_import_profile_execution"
    )
    op.drop_table("ton_import_profile_execution")
    op.execute("DROP TRIGGER ton_import_profile_immutable ON ton_import_profile")
    op.execute("DROP FUNCTION ton_protect_import_profile()")
    op.drop_table("ton_import_profile")
