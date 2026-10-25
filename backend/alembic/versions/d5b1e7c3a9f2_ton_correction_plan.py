"""ton correction plan: cases over the occurrence ledger

Revision ID: d5b1e7c3a9f2
Revises: c4f8a2d6e1b7
Create Date: 2026-10-24 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d5b1e7c3a9f2"
down_revision = "c4f8a2d6e1b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE ton_correction_case_number_seq")
    op.create_table(
        "ton_correction_case",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "number",
            sa.Integer(),
            server_default=sa.text("nextval('ton_correction_case_number_seq')"),
            nullable=False,
            unique=True,
        ),
        sa.Column("case_key", sa.String(200), nullable=False, unique=True),
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_rule.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("owner_area", sa.String(60), nullable=True),
        sa.Column("owner_name", sa.String(120), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("action_text", sa.String(1000), nullable=True),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("decision_reason", sa.String(1000), nullable=True),
        sa.Column(
            "in_board_summary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision = 'RISK_ACCEPTED'",
            name="ck_ton_correction_case_decision",
        ),
    )
    op.execute(
        "ALTER SEQUENCE ton_correction_case_number_seq "
        "OWNED BY ton_correction_case.number"
    )
    op.create_table(
        "ton_correction_case_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_correction_case.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("detail", sa.String(1000), nullable=True),
        sa.Column(
            "actor_id",
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
        "ix_ton_correction_case_event_case",
        "ton_correction_case_event",
        ["case_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ton_correction_case_event_case", table_name="ton_correction_case_event"
    )
    op.drop_table("ton_correction_case_event")
    op.drop_table("ton_correction_case")
