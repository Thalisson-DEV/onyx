"""ton unit payables: suppliers, titles, attachments, history

Revision ID: c4f8a2d6e1b7
Revises: b8e2c4d6f1a3
Create Date: 2026-10-24 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c4f8a2d6e1b7"
down_revision = "b8e2c4d6f1a3"
branch_labels = None
depends_on = None


def _user_fk(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )


def _now(name: str) -> sa.Column:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "ton_payable_supplier",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tax_id", sa.String(14), nullable=False, unique=True),
        sa.Column("legal_name", sa.String(300), nullable=False),
        sa.Column("trade_name", sa.String(300), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "default_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_account.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("pix_key_type", sa.String(16), nullable=True),
        sa.Column("pix_key", sa.String(140), nullable=True),
        sa.Column("bank_code", sa.String(8), nullable=True),
        sa.Column("bank_agency", sa.String(16), nullable=True),
        sa.Column("bank_account", sa.String(32), nullable=True),
        sa.Column("review_note", sa.String(500), nullable=True),
        _user_fk("created_by"),
        _user_fk("approved_by"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint(
            "kind IN ('COMPANY', 'PERSON', 'EMPLOYEE', 'PUBLIC_BODY')",
            name="ck_ton_payable_supplier_kind",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'PENDING', 'REJECTED', 'INACTIVE')",
            name="ck_ton_payable_supplier_status",
        ),
        sa.CheckConstraint(
            "length(tax_id) IN (11, 14)", name="ck_ton_payable_supplier_tax_id"
        ),
    )

    op.execute("CREATE SEQUENCE ton_payable_title_number_seq")
    op.create_table(
        "ton_payable_title",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "number",
            sa.Integer(),
            server_default=sa.text("nextval('ton_payable_title_number_seq')"),
            nullable=False,
            unique=True,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_payable_supplier.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_financial_account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(16), nullable=True),
        sa.Column("document_number", sa.String(60), nullable=True),
        sa.Column("document_key", sa.String(60), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("competence", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("installment_count", sa.Integer(), nullable=False),
        sa.Column("purchase_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("destination_kind", sa.String(16), nullable=False),
        sa.Column(
            "vehicle_plates",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("destination_note", sa.String(300), nullable=True),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("zeev_request", sa.String(40), nullable=True),
        sa.Column("estimate_until", sa.Date(), nullable=True),
        sa.Column(
            "replaces_estimate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_payable_title.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("ng_reference", sa.String(80), nullable=True),
        _now("submitted_at"),
        _user_fk("created_by"),
        _now("updated_at"),
        sa.CheckConstraint(
            "kind IN ('REAL', 'ESTIMATE')", name="ck_ton_payable_title_kind"
        ),
        sa.CheckConstraint(
            "status IN ('WAITING_ATTACHMENT', 'WAITING_SUPPLIER', 'RECEIVED', "
            "'RETURNED', 'CONFERRED', 'RELEASED', 'BOOKED', 'PAID', "
            "'ESTIMATE_OPEN', 'ESTIMATE_REPLACED', 'CANCELLED')",
            name="ck_ton_payable_title_status",
        ),
        sa.CheckConstraint(
            "destination_kind IN ('VEHICLE', 'SITE', 'STOCK', 'ADMINISTRATION')",
            name="ck_ton_payable_title_destination",
        ),
        sa.CheckConstraint(
            "installment_number >= 1 AND installment_number <= installment_count",
            name="ck_ton_payable_title_installment",
        ),
        sa.CheckConstraint("amount > 0", name="ck_ton_payable_title_amount"),
    )
    op.execute(
        "ALTER SEQUENCE ton_payable_title_number_seq OWNED BY ton_payable_title.number"
    )
    op.create_index(
        "ix_ton_payable_title_unit_due", "ton_payable_title", ["unit_id", "due_date"]
    )
    op.create_index("ix_ton_payable_title_status", "ton_payable_title", ["status"])
    op.create_index(
        "ix_ton_payable_title_document",
        "ton_payable_title",
        ["supplier_id", "document_key"],
    )

    op.create_table(
        "ton_payable_attachment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "title_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_payable_title.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("read_kind", sa.String(16), nullable=True),
        sa.Column("read_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("read_tax_id", sa.String(14), nullable=True),
        sa.Column("read_document_number", sa.String(60), nullable=True),
        sa.Column("read_due_date", sa.Date(), nullable=True),
        _user_fk("created_by"),
        _now("created_at"),
        sa.CheckConstraint(
            "role IN ('INVOICE', 'BOLETO', 'RECEIPT', 'OTHER')",
            name="ck_ton_payable_attachment_role",
        ),
        sa.CheckConstraint(
            "size_bytes <= 10485760", name="ck_ton_payable_attachment_size"
        ),
    )
    op.create_index(
        "ix_ton_payable_attachment_title", "ton_payable_attachment", ["title_id"]
    )

    op.create_table(
        "ton_payable_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "title_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_payable_title.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=True),
        sa.Column("reason", sa.String(1000), nullable=True),
        _user_fk("actor_id"),
        _now("created_at"),
    )
    op.create_index(
        "ix_ton_payable_event_title", "ton_payable_event", ["title_id", "created_at"]
    )

    op.create_table(
        "ton_payable_check_decision",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "title_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ton_payable_title.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("check_code", sa.String(40), nullable=False),
        sa.Column("subject", sa.String(120), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        _user_fk("decided_by"),
        _now("created_at"),
        sa.UniqueConstraint(
            "title_id", "check_code", "subject", name="uq_ton_payable_check_decision"
        ),
    )


def downgrade() -> None:
    op.drop_table("ton_payable_check_decision")
    op.drop_index("ix_ton_payable_event_title", table_name="ton_payable_event")
    op.drop_table("ton_payable_event")
    op.drop_index(
        "ix_ton_payable_attachment_title", table_name="ton_payable_attachment"
    )
    op.drop_table("ton_payable_attachment")
    op.drop_index("ix_ton_payable_title_document", table_name="ton_payable_title")
    op.drop_index("ix_ton_payable_title_status", table_name="ton_payable_title")
    op.drop_index("ix_ton_payable_title_unit_due", table_name="ton_payable_title")
    op.drop_table("ton_payable_title")
    op.drop_table("ton_payable_supplier")
