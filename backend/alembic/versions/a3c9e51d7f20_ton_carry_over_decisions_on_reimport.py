"""Carry review decisions over re-imports; explicit normalization input policy.

A review decision is either a human act or a system record that a human
decision still applies to a new import of the same evidence. The normalization
run records which inputs it was allowed to read, so importing a budget workbook
no longer changes the DRE input by accident.

Revision ID: a3c9e51d7f20
Revises: d4e6f72a1c09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a3c9e51d7f20"
down_revision = "d4e6f72a1c09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ton_review_decision",
        sa.Column(
            "basis", sa.String(length=16), nullable=False, server_default="HUMAN"
        ),
    )
    op.add_column(
        "ton_review_decision",
        sa.Column(
            "carried_from_decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_review_decision.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.alter_column(
        "ton_review_decision",
        "actor_user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_ton_review_decision_basis",
        "ton_review_decision",
        "basis IN ('HUMAN', 'CARRIED_OVER')",
    )
    # A human decision names its author; a carried-over one names its origin.
    op.create_check_constraint(
        "ck_ton_review_decision_basis_actor",
        "ton_review_decision",
        "(basis = 'HUMAN') = (actor_user_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_ton_review_decision_basis_origin",
        "ton_review_decision",
        "(basis = 'CARRIED_OVER') = (carried_from_decision_id IS NOT NULL)",
    )

    op.add_column(
        "ton_financial_normalization_run",
        sa.Column(
            "input_policy",
            sa.String(length=40),
            nullable=False,
            server_default="ACTUAL_ONLY",
        ),
    )
    op.create_check_constraint(
        "ck_ton_financial_normalization_input_policy",
        "ton_financial_normalization_run",
        "input_policy IN ('ACTUAL_ONLY', 'ACTUAL_AND_APPROVED_BUDGET', "
        "'LEGACY_ALL_AVAILABLE')",
    )
    # Runs made before the policy existed read every budget workbook available.
    # The run is otherwise immutable, so the backfill bypasses its trigger once.
    op.execute(
        "ALTER TABLE ton_financial_normalization_run "
        "DISABLE TRIGGER ton_financial_normalization_transition"
    )
    op.execute(
        "UPDATE ton_financial_normalization_run "
        "SET input_policy = 'LEGACY_ALL_AVAILABLE' "
        "WHERE budget_execution_ids <> '[]'::jsonb"
    )
    op.execute(
        "ALTER TABLE ton_financial_normalization_run "
        "ENABLE TRIGGER ton_financial_normalization_transition"
    )


def downgrade() -> None:
    connection = op.get_bind()
    carried = connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM ton_review_decision WHERE basis <> 'HUMAN')"
        )
    )
    if carried:
        raise RuntimeError("Carried-over review decisions exist")
    op.drop_constraint(
        "ck_ton_financial_normalization_input_policy",
        "ton_financial_normalization_run",
        type_="check",
    )
    op.drop_column("ton_financial_normalization_run", "input_policy")
    op.drop_constraint(
        "ck_ton_review_decision_basis_origin", "ton_review_decision", type_="check"
    )
    op.drop_constraint(
        "ck_ton_review_decision_basis_actor", "ton_review_decision", type_="check"
    )
    op.drop_constraint(
        "ck_ton_review_decision_basis", "ton_review_decision", type_="check"
    )
    op.alter_column(
        "ton_review_decision",
        "actor_user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("ton_review_decision", "carried_from_decision_id")
    op.drop_column("ton_review_decision", "basis")
