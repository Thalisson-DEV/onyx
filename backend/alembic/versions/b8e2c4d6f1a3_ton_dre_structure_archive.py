"""ton dre structure archive events

Revision ID: b8e2c4d6f1a3
Revises: a7d3f9b1c5e8
Create Date: 2026-10-22 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b8e2c4d6f1a3"
down_revision = "a7d3f9b1c5e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DRE history is immutable, so archiving a DRE is an event of its own; the
    # latest event per structure says whether it is archived.
    op.create_table(
        "ton_dre_structure_archive",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "structure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_dre_structure.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
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
        "ix_ton_dre_structure_archive_structure",
        "ton_dre_structure_archive",
        ["structure_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ton_dre_structure_archive_structure",
        table_name="ton_dre_structure_archive",
    )
    op.drop_table("ton_dre_structure_archive")
