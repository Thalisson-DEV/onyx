"""TON account classification: question per suggestion and assistant briefing.

Revision ID: c4f2a9e6b1d3
Revises: b8e1d5c3a7f4
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c4f2a9e6b1d3"
down_revision = "b8e1d5c3a7f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ton_account_classification_suggestion",
        sa.Column("question", sa.String(300)),
    )
    op.create_table(
        "ton_account_classification_briefing",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("summary", sa.String(1500), nullable=False),
        sa.Column("model_name", sa.String(200)),
        sa.Column("account_codes", postgresql.JSONB(), nullable=False),
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
    )
    op.create_index(
        "ix_ton_account_classification_briefing_source",
        "ton_account_classification_briefing",
        ["source_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ton_account_classification_briefing_source",
        table_name="ton_account_classification_briefing",
    )
    op.drop_table("ton_account_classification_briefing")
    op.drop_column("ton_account_classification_suggestion", "question")
