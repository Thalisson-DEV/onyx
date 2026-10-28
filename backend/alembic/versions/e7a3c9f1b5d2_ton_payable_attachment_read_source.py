"""ton payables: who read the attachment (the file itself or AI)

Revision ID: e7a3c9f1b5d2
Revises: d5b1e7c3a9f2
Create Date: 2026-10-28 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e7a3c9f1b5d2"
down_revision = "d5b1e7c3a9f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ton_payable_attachment",
        sa.Column("read_source", sa.String(8), nullable=True),
    )
    # Every reading so far came from the file itself (XML or boleto line).
    op.execute(
        "UPDATE ton_payable_attachment SET read_source = 'FILE' "
        "WHERE read_kind IS NOT NULL"
    )
    op.create_check_constraint(
        "ck_ton_payable_attachment_read_source",
        "ton_payable_attachment",
        "read_source IS NULL OR read_source IN ('FILE', 'AI')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_ton_payable_attachment_read_source",
        "ton_payable_attachment",
        type_="check",
    )
    op.drop_column("ton_payable_attachment", "read_source")
