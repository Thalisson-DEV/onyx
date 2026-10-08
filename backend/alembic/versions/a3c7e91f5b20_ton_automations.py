"""TON automations: definitions v3, durable runs with step rows, approvals,
notices and data files.

Revision ID: a3c7e91f5b20
Revises: 60d6efcc39b2
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a3c7e91f5b20"
down_revision = "60d6efcc39b2"
branch_labels = None
depends_on = None


def _uuid(name: str, **kwargs: object) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)  # type: ignore[arg-type]


def _user_fk(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )


def _now(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.func.now() if not nullable else None,
        nullable=nullable,
    )


def upgrade() -> None:
    op.create_table(
        "ton_automation",
        _uuid("id", primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("trigger_type", sa.String(48), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("seed_key", sa.String(64), unique=True),
        _uuid("legacy_flow_id", unique=True),
        sa.Column("suggestion_reason", sa.String(1000)),
        sa.Column("suggestion_model", sa.String(200)),
        _user_fk("owner_id"),
        sa.Column("active_since", sa.DateTime(timezone=True)),
        _user_fk("created_by"),
        _user_fk("updated_by"),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint(
            "kind IN ('EMAIL', 'ALERT', 'ROUTINE', 'APPROVAL', 'DATA_AI', 'GENERAL')",
            name="ck_ton_automation_kind",
        ),
        sa.CheckConstraint(
            "origin IN ('USER', 'TON_SUGGESTED', 'SYSTEM', 'MIGRATED')",
            name="ck_ton_automation_origin",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'PAUSED', 'ARCHIVED')",
            name="ck_ton_automation_status",
        ),
    )
    op.create_index(
        "ix_ton_automation_status_trigger", "ton_automation", ["status", "trigger_type"]
    )

    op.create_table(
        "ton_automation_version",
        _uuid("id", primary_key=True),
        sa.Column(
            "automation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_automation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("note", sa.String(300)),
        _user_fk("created_by"),
        _now("created_at"),
        sa.UniqueConstraint("automation_id", "version", name="uq_ton_automation_version"),
    )

    op.create_table(
        "ton_automation_run",
        _uuid("id", primary_key=True),
        sa.Column(
            "automation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_automation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_automation_version.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("trigger_key", sa.String(240), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("trigger_output", postgresql.JSONB(), nullable=False),
        sa.Column("error", sa.String(1000)),
        sa.Column("message", sa.String(500)),
        sa.Column("waiting_on", sa.String(16)),
        _user_fk("triggered_by"),
        _uuid("resubmitted_from"),
        _now("created_at"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("resume_at", sa.DateTime(timezone=True)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_owner", sa.String(80)),
        sa.Column("executions", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "mode IN ('LIVE', 'MANUAL', 'TEST', 'RESUBMIT')",
            name="ck_ton_automation_run_mode",
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'WAITING', 'SUCCEEDED', 'FAILED', "
            "'CANCELLED', 'TIMED_OUT')",
            name="ck_ton_automation_run_status",
        ),
    )
    op.create_index(
        "uq_ton_automation_run_trigger",
        "ton_automation_run",
        ["automation_id", "trigger_key"],
        unique=True,
        postgresql_where=sa.text("mode = 'LIVE'"),
    )
    op.create_index(
        "ix_ton_automation_run_open",
        "ton_automation_run",
        ["status", "resume_at"],
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING', 'WAITING')"),
    )
    op.create_index(
        "ix_ton_automation_run_automation",
        "ton_automation_run",
        ["automation_id", "created_at"],
    )

    op.create_table(
        "ton_automation_step_run",
        _uuid("id", primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_automation_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(40), nullable=False),
        sa.Column("iteration", sa.String(400), nullable=False, server_default=""),
        sa.Column("node_type", sa.String(48), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inputs", postgresql.JSONB()),
        sa.Column("outputs", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'WAITING', 'SUCCEEDED', 'FAILED', 'SKIPPED', "
            "'TIMED_OUT', 'CANCELLED')",
            name="ck_ton_automation_step_run_status",
        ),
        sa.UniqueConstraint(
            "run_id", "node_id", "iteration", name="uq_ton_automation_step_run"
        ),
    )

    op.create_table(
        "ton_automation_approval",
        _uuid("id", primary_key=True),
        sa.Column(
            "automation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_automation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_automation_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(40), nullable=False),
        sa.Column("iteration", sa.String(400), nullable=False, server_default=""),
        sa.Column("approvers", postgresql.JSONB(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("details", sa.Text()),
        sa.Column("options", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(120)),
        sa.Column("comment", sa.String(1000)),
        _user_fk("decided_by"),
        sa.Column("decided_by_email", sa.String(320)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        _now("created_at"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'DONE', 'EXPIRED', 'CANCELLED')",
            name="ck_ton_automation_approval_status",
        ),
    )
    op.create_index(
        "ix_ton_automation_approval_pending",
        "ton_automation_approval",
        ["created_at"],
        postgresql_where=sa.text("status = 'PENDING'"),
    )

    op.create_table(
        "ton_automation_notice",
        _uuid("id", primary_key=True),
        sa.Column(
            "automation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_automation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_automation_run.id", ondelete="SET NULL"),
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("link", sa.String(500)),
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()),
        _now("created_at"),
        sa.CheckConstraint(
            "severity IN ('INFO', 'WARNING', 'CRITICAL')",
            name="ck_ton_automation_notice_severity",
        ),
    )
    op.create_index(
        "ix_ton_automation_notice_created", "ton_automation_notice", ["created_at"]
    )

    op.create_table(
        "ton_automation_file",
        _uuid("id", primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        _user_fk("created_by"),
        _now("created_at"),
        sa.CheckConstraint("size_bytes <= 5242880", name="ck_ton_automation_file_size"),
    )


def downgrade() -> None:
    op.drop_table("ton_automation_file")
    op.drop_index("ix_ton_automation_notice_created", table_name="ton_automation_notice")
    op.drop_table("ton_automation_notice")
    op.drop_index("ix_ton_automation_approval_pending", table_name="ton_automation_approval")
    op.drop_table("ton_automation_approval")
    op.drop_table("ton_automation_step_run")
    op.drop_index("ix_ton_automation_run_automation", table_name="ton_automation_run")
    op.drop_index("ix_ton_automation_run_open", table_name="ton_automation_run")
    op.drop_index("uq_ton_automation_run_trigger", table_name="ton_automation_run")
    op.drop_table("ton_automation_run")
    op.drop_table("ton_automation_version")
    op.drop_index("ix_ton_automation_status_trigger", table_name="ton_automation")
    op.drop_table("ton_automation")
