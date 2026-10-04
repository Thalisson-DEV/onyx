"""TON account classification review and pre-classification suggestions.

Also marks the NG account codes classified by analogy (absent from the
controller's "Banco de Dados" workbook) as awaiting confirmation.

Revision ID: b8e1d5c3a7f4
Revises: a3c9e51d7f20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b8e1d5c3a7f4"
down_revision = "a3c9e51d7f20"
branch_labels = None
depends_on = None

# Reason suffix the real-data setup wrote on every mapping it had to classify
# by analogy because the code is missing from the controller's workbook.
ANALOGY_REASON = "%ausente do BANCO DE DADOS%"


def upgrade() -> None:
    op.create_table(
        "ton_account_classification_review",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("account_code", sa.String(100), nullable=False),
        sa.Column(
            "mapping_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_mapping.id", ondelete="RESTRICT"),
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('AWAITING_CONFIRMATION', 'CONFIRMED')",
            name="ck_ton_account_classification_review_status",
        ),
        sa.CheckConstraint(
            "origin IN ('CONTROLLER_WORKBOOK', 'ANALOGY', 'MANUAL')",
            name="ck_ton_account_classification_review_origin",
        ),
    )
    op.create_index(
        "ix_ton_account_classification_review_key",
        "ton_account_classification_review",
        ["source_id", "account_code", "created_at"],
    )
    op.create_table(
        "ton_account_classification_suggestion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_source.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("account_code", sa.String(100), nullable=False),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("rationale", sa.String(1000), nullable=False),
        sa.Column("model_name", sa.String(200)),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
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
        sa.CheckConstraint(
            "method IN ('AI')", name="ck_ton_account_classification_suggestion_method"
        ),
        sa.CheckConstraint(
            "confidence IN ('HIGH', 'MEDIUM', 'LOW')",
            name="ck_ton_account_classification_suggestion_confidence",
        ),
    )
    op.create_index(
        "ix_ton_account_classification_suggestion_key",
        "ton_account_classification_suggestion",
        ["source_id", "account_code", "created_at"],
    )
    # Task 1.2 of account-classification-admin: the analogy-classified codes
    # wait for the Controladoria. Latest ACCOUNT mapping per code only.
    op.execute(
        sa.text(
            """
            INSERT INTO ton_account_classification_review
                (id, source_id, account_code, mapping_id, status, origin, note)
            SELECT gen_random_uuid(), m.source_id, m.source_key, m.id,
                   'AWAITING_CONFIRMATION', 'ANALOGY',
                   'Classificada por semelhança na carga da base real; '
                   || 'aguarda confirmação da Controladoria'
            FROM (
                SELECT DISTINCT ON (m.source_id, m.source_key) m.*, r.reason
                FROM ton_financial_mapping m
                JOIN ton_financial_mapping_revision r ON r.id = m.revision_id
                WHERE m.kind = 'ACCOUNT'
                ORDER BY m.source_id, m.source_key, r.number DESC
            ) m
            WHERE m.reason LIKE :analogy
            """
        ).bindparams(analogy=ANALOGY_REASON)
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ton_account_classification_suggestion_key",
        table_name="ton_account_classification_suggestion",
    )
    op.drop_table("ton_account_classification_suggestion")
    op.drop_index(
        "ix_ton_account_classification_review_key",
        table_name="ton_account_classification_review",
    )
    op.drop_table("ton_account_classification_review")
