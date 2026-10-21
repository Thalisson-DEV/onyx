"""ton controller rules remembered by the chat

Revision ID: a7d3f9b1c5e8
Revises: f1a9c3e5b7d2
Create Date: 2026-10-21 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a7d3f9b1c5e8"
down_revision = "f1a9c3e5b7d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ton_controller_rule",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_key", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("text", sa.String(2000), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "chat_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_session.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        sa.UniqueConstraint("rule_key", "version", name="uq_ton_controller_rule_version"),
    )


def downgrade() -> None:
    op.drop_table("ton_controller_rule")
