"""ton record unit assignment

Revision ID: b7e4c2a9d5f1
Revises: a3c7e91f5b20
Create Date: 2026-10-17

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b7e4c2a9d5f1"
down_revision = "a3c7e91f5b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ton_record_unit_assignment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("record_key", sa.String(100), nullable=False),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "occurrence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_occurrence.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("reason", sa.String(500), nullable=False),
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
        "ix_ton_record_unit_assignment_key",
        "ton_record_unit_assignment",
        ["source_id", "record_key", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ton_record_unit_assignment_key", table_name="ton_record_unit_assignment"
    )
    op.drop_table("ton_record_unit_assignment")
