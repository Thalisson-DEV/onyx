"""TON email flows: flow, immutable version, event outbox, run and delivery.

Revision ID: e5b8c2d4f1a7
Revises: d7a1e4c9b2f6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e5b8c2d4f1a7"
down_revision = "d7a1e4c9b2f6"
branch_labels = None
depends_on = None


def _uuid(name: str, *, primary_key: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), primary_key=primary_key)


def _user(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("user.id", ondelete="SET NULL"),
    )


def _now(name: str) -> sa.Column:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "ton_email_flow",
        _uuid("id", primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("seed_key", sa.String(64), unique=True),
        sa.Column("suggestion_reason", sa.String(1000)),
        sa.Column("suggestion_model", sa.String(200)),
        _user("owner_id"),
        sa.Column("active_since", sa.DateTime(timezone=True)),
        _user("created_by"),
        _user("approved_by"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        _user("discarded_by"),
        sa.Column("discarded_at", sa.DateTime(timezone=True)),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint(
            "origin IN ('USER', 'TON_SUGGESTED', 'SYSTEM')",
            name="ck_ton_email_flow_origin",
        ),
        sa.CheckConstraint(
            "status IN ('SUGGESTED', 'ACTIVE', 'PAUSED', 'DISCARDED')",
            name="ck_ton_email_flow_status",
        ),
    )
    op.create_index("ix_ton_email_flow_status", "ton_email_flow", ["status"])

    op.create_table(
        "ton_email_flow_version",
        _uuid("id", primary_key=True),
        sa.Column(
            "flow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_email_flow.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("trigger_kind", sa.String(32), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        _user("created_by"),
        _now("created_at"),
        sa.UniqueConstraint("flow_id", "version", name="uq_ton_email_flow_version"),
    )

    op.create_table(
        "ton_email_flow_event",
        _uuid("id", primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("event_key", sa.String(200), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        _now("created_at"),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("kind", "event_key", name="uq_ton_email_flow_event_key"),
    )
    op.create_index(
        "ix_ton_email_flow_event_pending",
        "ton_email_flow_event",
        ["created_at"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )

    op.create_table(
        "ton_email_flow_run",
        _uuid("id", primary_key=True),
        sa.Column(
            "flow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_email_flow.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_email_flow_version.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_key", sa.String(200), nullable=False),
        sa.Column("is_test", sa.Boolean(), nullable=False),
        sa.Column("branch", sa.String(8)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        _user("triggered_by"),
        _now("started_at"),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "branch IS NULL OR branch IN ('YES', 'NO')",
            name="ck_ton_email_flow_run_branch",
        ),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SENT', 'SILENT', 'PARTIAL', 'FAILED', 'NOT_CONFIGURED')",
            name="ck_ton_email_flow_run_status",
        ),
    )
    op.create_index(
        "uq_ton_email_flow_run_event",
        "ton_email_flow_run",
        ["flow_id", "event_key"],
        unique=True,
        postgresql_where=sa.text("NOT is_test"),
    )
    op.create_index(
        "ix_ton_email_flow_run_flow", "ton_email_flow_run", ["flow_id", "started_at"]
    )

    op.create_table(
        "ton_email_flow_delivery",
        _uuid("id", primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_email_flow_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(16)),
        sa.Column("to_addresses", postgresql.JSONB(), nullable=False),
        sa.Column("cc_addresses", postgresql.JSONB(), nullable=False),
        sa.Column("bcc_addresses", postgresql.JSONB(), nullable=False),
        sa.Column("batch_no", sa.Integer(), nullable=False),
        sa.Column("batch_count", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=False),
        sa.Column("provider_message_id", sa.String(300)),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(500)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        _now("created_at"),
        sa.CheckConstraint(
            "status IN ('SENT', 'FAILED', 'NOT_CONFIGURED')",
            name="ck_ton_email_flow_delivery_status",
        ),
    )
    op.create_index(
        "ix_ton_email_flow_delivery_run", "ton_email_flow_delivery", ["run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_ton_email_flow_delivery_run", table_name="ton_email_flow_delivery")
    op.drop_table("ton_email_flow_delivery")
    op.drop_index("ix_ton_email_flow_run_flow", table_name="ton_email_flow_run")
    op.drop_index("uq_ton_email_flow_run_event", table_name="ton_email_flow_run")
    op.drop_table("ton_email_flow_run")
    op.drop_index("ix_ton_email_flow_event_pending", table_name="ton_email_flow_event")
    op.drop_table("ton_email_flow_event")
    op.drop_table("ton_email_flow_version")
    op.drop_index("ix_ton_email_flow_status", table_name="ton_email_flow")
    op.drop_table("ton_email_flow")
