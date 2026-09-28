"""TON logical sources and immutable raw captures (DATA-001)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "6be7c77e49ce"
down_revision = "440b8984f851"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ton_source",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("acquisition_type", sa.String(17), nullable=False),
        sa.Column("status", sa.String(11), nullable=False),
        sa.Column("sensitivity", sa.String(12), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("key ~ '^[a-z][a-z0-9_]*$'", name="ck_ton_source_key"),
    )
    op.create_table(
        "ton_source__user_group",
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "user_group_id",
            sa.Integer,
            sa.ForeignKey("user_group.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_ton_source_group", "ton_source__user_group", ["user_group_id"])
    op.create_table(
        "ton_import_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(9), nullable=False),
        sa.Column("trigger", sa.String(13), nullable=False),
        sa.Column("acquisition_type", sa.String(17), nullable=False),
        sa.Column(
            "initiated_by",
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
        sa.Column("snapshot_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("storage_file_id", sa.String, nullable=False, unique=True),
        sa.Column(
            "cleanup_required",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint("id", "source_id", name="uq_ton_import_id_source"),
        sa.CheckConstraint("snapshot_count IN (0, 1)", name="ck_ton_import_count"),
        sa.CheckConstraint(
            "(status IN ('PENDING', 'RUNNING') AND finished_at IS NULL AND snapshot_count = 0) OR (status = 'SUCCEEDED' AND finished_at IS NOT NULL AND snapshot_count = 1 AND error_code IS NULL AND NOT cleanup_required) OR (status = 'FAILED' AND finished_at IS NOT NULL AND snapshot_count = 0 AND error_code IS NOT NULL)",
            name="ck_ton_import_state",
        ),
    )
    op.create_index(
        "ix_ton_import_source_started", "ton_import_run", ["source_id", "started_at"]
    )
    for column in (
        sa.Column("source_id", postgresql.UUID(as_uuid=True)),
        sa.Column("import_run_id", postgresql.UUID(as_uuid=True)),
        sa.Column("storage_file_id", sa.String),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("media_type", sa.String(150)),
        sa.Column("format", sa.String(4)),
        sa.Column("size_bytes", sa.Integer),
        sa.Column("duplicate_of_id", postgresql.UUID(as_uuid=True)),
    ):
        op.add_column("ton_source_snapshot", column)
    op.create_foreign_key(
        "fk_ton_snapshot_source",
        "ton_source_snapshot",
        "ton_source",
        ["source_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_ton_snapshot_id_source", "ton_source_snapshot", ["id", "source_id"]
    )
    op.create_unique_constraint(
        "uq_ton_snapshot_run", "ton_source_snapshot", ["import_run_id"]
    )
    op.create_unique_constraint(
        "uq_ton_snapshot_storage", "ton_source_snapshot", ["storage_file_id"]
    )
    op.create_foreign_key(
        "fk_ton_snapshot_run_source",
        "ton_source_snapshot",
        "ton_import_run",
        ["import_run_id", "source_id"],
        ["id", "source_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_ton_snapshot_duplicate_source",
        "ton_source_snapshot",
        "ton_source_snapshot",
        ["duplicate_of_id", "source_id"],
        ["id", "source_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_ton_snapshot_raw_capture",
        "ton_source_snapshot",
        "(source_id IS NULL AND import_run_id IS NULL AND storage_file_id IS NULL AND duplicate_of_id IS NULL) OR (source_id IS NOT NULL AND import_run_id IS NOT NULL AND storage_file_id IS NOT NULL AND original_filename IS NOT NULL AND media_type IS NOT NULL AND format IS NOT NULL AND size_bytes IS NOT NULL AND size_bytes > 0 AND checksum IS NOT NULL AND checksum ~ '^[0-9a-f]{64}$')",
    )
    op.create_index(
        "ix_ton_snapshot_source_hash", "ton_source_snapshot", ["source_id", "checksum"]
    )
    # Raw snapshots can also be referenced by older evidence APIs. Protect bulk SQL.
    op.execute("""CREATE FUNCTION ton_protect_raw_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF OLD.source_id IS NOT NULL OR (TG_OP = 'UPDATE' AND NEW.source_id IS NOT NULL) THEN
            RAISE EXCEPTION 'Raw source snapshots are immutable';
        END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
        RETURN NEW;
    END; $$""")
    op.execute(
        "CREATE TRIGGER ton_raw_snapshot_immutable BEFORE UPDATE OR DELETE ON ton_source_snapshot FOR EACH ROW EXECUTE FUNCTION ton_protect_raw_snapshot()"
    )
    op.execute("""CREATE FUNCTION ton_protect_source_key() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.key <> OLD.key THEN
            RAISE EXCEPTION 'Logical source key is immutable';
        END IF;
        RETURN NEW;
    END; $$""")
    op.execute(
        "CREATE TRIGGER ton_source_key_immutable BEFORE UPDATE ON ton_source FOR EACH ROW EXECUTE FUNCTION ton_protect_source_key()"
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM ton_source)")):
        raise RuntimeError("Remove or archive source data before downgrading DATA-001")
    op.execute("DROP TRIGGER ton_source_key_immutable ON ton_source")
    op.execute("DROP FUNCTION ton_protect_source_key()")
    op.execute("DROP TRIGGER ton_raw_snapshot_immutable ON ton_source_snapshot")
    op.execute("DROP FUNCTION ton_protect_raw_snapshot()")
    for name in (
        "fk_ton_snapshot_duplicate_source",
        "fk_ton_snapshot_run_source",
        "fk_ton_snapshot_source",
        "uq_ton_snapshot_id_source",
        "uq_ton_snapshot_run",
        "uq_ton_snapshot_storage",
        "ck_ton_snapshot_raw_capture",
    ):
        op.drop_constraint(name, "ton_source_snapshot")
    op.drop_index("ix_ton_snapshot_source_hash", table_name="ton_source_snapshot")
    for name in (
        "duplicate_of_id",
        "size_bytes",
        "format",
        "media_type",
        "original_filename",
        "storage_file_id",
        "import_run_id",
        "source_id",
    ):
        op.drop_column("ton_source_snapshot", name)
    op.drop_table("ton_import_run")
    op.drop_table("ton_source__user_group")
    op.drop_table("ton_source")
