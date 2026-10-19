"""ton dre structures derived from the managerial one

Revision ID: e4b8d2f6a0c3
Revises: d2f6a8c4e1b9
Create Date: 2026-10-19 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e4b8d2f6a0c3"
down_revision = "d2f6a8c4e1b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ton_dre_structure",
        sa.Column(
            "base_structure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "ton_dre_structure.id",
                ondelete="RESTRICT",
                name="fk_ton_dre_structure_base",
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "ton_dre_structure", sa.Column("template_key", sa.String(50), nullable=True)
    )
    op.create_check_constraint(
        "ck_ton_dre_structure_derived",
        "ton_dre_structure",
        "(base_structure_id IS NULL) = (template_key IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ton_dre_structure_derived", "ton_dre_structure")
    op.drop_column("ton_dre_structure", "template_key")
    op.drop_constraint(
        "fk_ton_dre_structure_base", "ton_dre_structure", type_="foreignkey"
    )
    op.drop_column("ton_dre_structure", "base_structure_id")
