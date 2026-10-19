"""ton normalization run reads the installment table

Revision ID: d2f6a8c4e1b9
Revises: b7e4c2a9d5f1
Create Date: 2026-10-19 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d2f6a8c4e1b9"
down_revision = "b7e4c2a9d5f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ton_financial_normalization_run",
        sa.Column(
            "installment_execution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "ton_import_profile_execution.id",
                ondelete="RESTRICT",
                name="fk_ton_normalization_run_installment_execution",
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ton_normalization_run_installment_execution",
        "ton_financial_normalization_run",
        type_="foreignkey",
    )
    op.drop_column("ton_financial_normalization_run", "installment_execution_id")
