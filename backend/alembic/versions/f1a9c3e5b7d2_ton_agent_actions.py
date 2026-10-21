"""ton agent actions and dre adjustments

Revision ID: f1a9c3e5b7d2
Revises: e4b8d2f6a0c3
Create Date: 2026-10-21 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f1a9c3e5b7d2"
down_revision = "e4b8d2f6a0c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ton_dre_adjustment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "structure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_dre_structure.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("line_code", sa.String(100), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(50, 25), nullable=False),
        sa.Column("justification", sa.String(2000), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ton_dre_adjustment_scope",
        "ton_dre_adjustment",
        ["structure_id", "period", "line_code", "created_at"],
    )
    op.create_table(
        "ton_agent_action",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chat_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_session.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("preview", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(1000), nullable=True),
        sa.Column(
            "proposed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "decided_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'APPLIED', 'CANCELLED', 'EXPIRED', 'UNDONE', 'FAILED')",
            name="ck_ton_agent_action_status",
        ),
    )
    op.create_index(
        "ix_ton_agent_action_session",
        "ton_agent_action",
        ["chat_session_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ton_agent_action_session", table_name="ton_agent_action")
    op.drop_table("ton_agent_action")
    op.drop_index("ix_ton_dre_adjustment_scope", table_name="ton_dre_adjustment")
    op.drop_table("ton_dre_adjustment")
