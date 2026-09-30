"""Allow audit resource kinds added after the TON audit table.

Revision ID: d4e6f72a1c09
Revises: 8e6a2b19c4d0
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e6f72a1c09"
down_revision = "8e6a2b19c4d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "ton_audit_event",
        "resource_kind",
        existing_type=sa.String(length=15),
        type_=sa.String(length=64),
        existing_nullable=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_long_values = connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM ton_audit_event "
            "WHERE length(resource_kind) > 15)"
        )
    )
    if has_long_values:
        raise RuntimeError(
            "Audit resource kinds exceed the previous 15-character limit"
        )
    op.alter_column(
        "ton_audit_event",
        "resource_kind",
        existing_type=sa.String(length=64),
        type_=sa.String(length=15),
        existing_nullable=True,
    )
