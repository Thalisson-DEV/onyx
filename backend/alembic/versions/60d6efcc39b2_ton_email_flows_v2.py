"""TON email flows v2: resumable runs, per-step deliveries, approvals, assets.

Revision ID: 60d6efcc39b2
Revises: e5b8c2d4f1a7
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "60d6efcc39b2"
down_revision = "e5b8c2d4f1a7"
branch_labels = None
depends_on = None

_RUN_STATUSES_V1 = "('RUNNING', 'SENT', 'SILENT', 'PARTIAL', 'FAILED', 'NOT_CONFIGURED')"
_RUN_STATUSES_V2 = (
    "('RUNNING', 'WAITING', 'SENT', 'SILENT', 'PARTIAL', 'FAILED', 'NOT_CONFIGURED', 'STOPPED')"
)


def upgrade() -> None:
    op.add_column(
        "ton_email_flow_run", sa.Column("resume_at", sa.DateTime(timezone=True))
    )
    op.add_column("ton_email_flow_run", sa.Column("cursor", postgresql.JSONB()))
    op.drop_constraint("ck_ton_email_flow_run_status", "ton_email_flow_run")
    op.create_check_constraint(
        "ck_ton_email_flow_run_status",
        "ton_email_flow_run",
        f"status IN {_RUN_STATUSES_V2}",
    )
    op.create_index(
        "ix_ton_email_flow_run_waiting",
        "ton_email_flow_run",
        ["resume_at"],
        postgresql_where=sa.text("status = 'WAITING'"),
    )

    op.add_column("ton_email_flow_delivery", sa.Column("step_id", sa.String(40)))
    op.add_column("ton_email_flow_delivery", sa.Column("unit", sa.String(120)))
    op.create_index(
        "uq_ton_email_flow_delivery_step",
        "ton_email_flow_delivery",
        ["run_id", "step_id", sa.text("coalesce(unit, '')"), "batch_no"],
        unique=True,
        postgresql_where=sa.text("step_id IS NOT NULL"),
    )

    op.create_table(
        "ton_email_flow_approval",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_email_flow_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_id", sa.String(40), nullable=False),
        sa.Column("approvers", postgresql.JSONB(), nullable=False),
        sa.Column("message", sa.String(1000)),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "decided_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("note", sa.String(1000)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_ton_email_flow_approval_status",
        ),
    )
    op.create_index(
        "ix_ton_email_flow_approval_pending",
        "ton_email_flow_approval",
        ["created_at"],
        postgresql_where=sa.text("status = 'PENDING'"),
    )

    op.create_table(
        "ton_email_asset",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("seed_key", sa.String(64), unique=True),
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
        sa.CheckConstraint(
            "content_type IN ('image/png', 'image/jpeg', 'image/gif')",
            name="ck_ton_email_asset_type",
        ),
        sa.CheckConstraint("size_bytes <= 1048576", name="ck_ton_email_asset_size"),
    )


def downgrade() -> None:
    op.drop_table("ton_email_asset")
    op.drop_index(
        "ix_ton_email_flow_approval_pending", table_name="ton_email_flow_approval"
    )
    op.drop_table("ton_email_flow_approval")
    op.drop_index(
        "uq_ton_email_flow_delivery_step", table_name="ton_email_flow_delivery"
    )
    op.drop_column("ton_email_flow_delivery", "unit")
    op.drop_column("ton_email_flow_delivery", "step_id")
    op.drop_index("ix_ton_email_flow_run_waiting", table_name="ton_email_flow_run")
    op.execute(
        "UPDATE ton_email_flow_run SET status = 'FAILED' "
        "WHERE status IN ('WAITING', 'STOPPED')"
    )
    op.drop_constraint("ck_ton_email_flow_run_status", "ton_email_flow_run")
    op.create_check_constraint(
        "ck_ton_email_flow_run_status",
        "ton_email_flow_run",
        f"status IN {_RUN_STATUSES_V1}",
    )
    op.drop_column("ton_email_flow_run", "cursor")
    op.drop_column("ton_email_flow_run", "resume_at")
