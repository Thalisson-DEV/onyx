"""Canonical financial domain, DATA-004C/D.

Revision ID: 6bc4d2e908fa
Revises: 3ac487f2d901
"""

from alembic import op
import sqlalchemy as sa

revision = "6bc4d2e908fa"
down_revision = "3ac487f2d901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE ton_financial_account (\n\tid UUID NOT NULL, \n\tcode VARCHAR(100) NOT NULL, \n\tlabel TEXT NOT NULL, \n\tdre_classification VARCHAR(100), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)"
    )
    op.execute(
        'CREATE TABLE ton_financial_mapping_revision (\n\tid UUID NOT NULL, \n\tnumber INTEGER NOT NULL, \n\tcreated_by UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_ton_financial_mapping_revision_number CHECK (number > 0), \n\tUNIQUE (number), \n\tFOREIGN KEY(created_by) REFERENCES "user" (id) ON DELETE SET NULL\n)'
    )
    op.execute(
        "CREATE TABLE ton_financial_mapping (\n\tid UUID NOT NULL, \n\trevision_id UUID NOT NULL, \n\tsource_id UUID NOT NULL, \n\tsource_snapshot_id UUID, \n\tkind VARCHAR(32) NOT NULL, \n\tsource_key TEXT NOT NULL, \n\taccount_id UUID, \n\tunit_id UUID, \n\teffective_from DATE, \n\teffective_to DATE, \n\tcalendar_period DATE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_ton_financial_mapping_kind CHECK (kind IN ('ACCOUNT', 'UNIT', 'ENTITY', 'BUDGET_ACCOUNT', 'BUDGET_UNIT', 'BILLING_ACCOUNT', 'BILLING_TAX_ACCOUNT', 'BUDGET_PERIOD')), \n\tCONSTRAINT ck_ton_financial_mapping_period CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from), \n\tFOREIGN KEY(revision_id) REFERENCES ton_financial_mapping_revision (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(source_id) REFERENCES ton_source (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(source_snapshot_id) REFERENCES ton_source_snapshot (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(account_id) REFERENCES ton_financial_account (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(unit_id) REFERENCES ton_business_unit (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE INDEX ix_ton_financial_mapping_lookup ON ton_financial_mapping (source_id, kind, source_key)"
    )
    op.execute(
        "CREATE TABLE ton_financial_normalization_run (\n\tid UUID NOT NULL, \n\tinput_digest VARCHAR(64) NOT NULL, \n\tattempt_no INTEGER NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\treview_run_id UUID NOT NULL, \n\tdataset_revision VARCHAR(150) NOT NULL, \n\tdataset_as_of TIMESTAMP WITH TIME ZONE NOT NULL, \n\tbilling_execution_id UUID NOT NULL, \n\tbudget_execution_ids JSONB NOT NULL, \n\tmapping_revision_number INTEGER NOT NULL, \n\tderivation_version VARCHAR(100) NOT NULL, \n\tauthority_policy_version VARCHAR(100) NOT NULL, \n\tstatistics JSONB NOT NULL, \n\terror_code VARCHAR(100), \n\tstarted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tfinished_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_ton_financial_normalization_attempt UNIQUE (input_digest, attempt_no), \n\tCONSTRAINT ck_ton_financial_normalization_status CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED')), \n\tCONSTRAINT ck_ton_financial_normalization_finished CHECK ((status = 'RUNNING') = (finished_at IS NULL)), \n\tFOREIGN KEY(review_run_id) REFERENCES ton_review_run (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(billing_execution_id) REFERENCES ton_import_profile_execution (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE ton_financial_actual_fact (\n\tid UUID NOT NULL, \n\trun_id UUID NOT NULL, \n\tparsed_record_id UUID NOT NULL, \n\taccount_id UUID, \n\tunit_id UUID, \n\taccount_mapping_id UUID, \n\tunit_mapping_id UUID, \n\temission_date DATE NOT NULL, \n\tcalendar_period DATE NOT NULL, \n\tsource_sheet_month INTEGER NOT NULL, \n\tmovement_amount NUMERIC(50, 25), \n\tfinal_amount NUMERIC(50, 25), \n\tdisposition VARCHAR(32) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_ton_financial_actual_run_record UNIQUE (run_id, parsed_record_id), \n\tFOREIGN KEY(run_id) REFERENCES ton_financial_normalization_run (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(parsed_record_id) REFERENCES ton_parsed_source_record (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(account_id) REFERENCES ton_financial_account (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(unit_id) REFERENCES ton_business_unit (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(account_mapping_id) REFERENCES ton_financial_mapping (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(unit_mapping_id) REFERENCES ton_financial_mapping (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE INDEX ix_ton_financial_actual_scope ON ton_financial_actual_fact (run_id, calendar_period, unit_id, account_id)"
    )
    op.execute(
        "CREATE TABLE ton_financial_billing_fact (\n\tid UUID NOT NULL, \n\trun_id UUID NOT NULL, \n\tsource_record_id UUID NOT NULL, \n\taccount_id UUID, \n\tunit_id UUID, \n\taccount_mapping_id UUID, \n\tunit_mapping_id UUID, \n\temission_date DATE NOT NULL, \n\tcompetence_period DATE, \n\tservice_amount NUMERIC(50, 25) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_ton_financial_billing_run_record UNIQUE (run_id, source_record_id), \n\tFOREIGN KEY(run_id) REFERENCES ton_financial_normalization_run (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(source_record_id) REFERENCES ton_operational_source_record (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(account_id) REFERENCES ton_financial_account (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(unit_id) REFERENCES ton_business_unit (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(account_mapping_id) REFERENCES ton_financial_mapping (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(unit_mapping_id) REFERENCES ton_financial_mapping (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE INDEX ix_ton_financial_billing_scope ON ton_financial_billing_fact (run_id, competence_period, unit_id, account_id)"
    )
    op.add_column(
        "ton_financial_billing_fact",
        sa.Column("invoice_number", sa.Text, nullable=False),
    )
    op.add_column("ton_financial_billing_fact", sa.Column("payer_text", sa.Text))
    for name in (
        "ir_retained",
        "iss_retained",
        "inss_retained",
        "total_retained",
        "invoice_net_amount",
        "net_after_discount",
    ):
        op.add_column("ton_financial_billing_fact", sa.Column(name, sa.Numeric(50, 25)))
    op.execute(
        "CREATE TABLE ton_financial_derived_fact (\n\tid UUID NOT NULL, \n\trun_id UUID NOT NULL, \n\tbilling_fact_id UUID NOT NULL, \n\trule_key VARCHAR(100) NOT NULL, \n\trule_version INTEGER NOT NULL, \n\torigin VARCHAR(32) NOT NULL, \n\taccount_id UUID NOT NULL, \n\tunit_id UUID NOT NULL, \n\tcompetence_period DATE NOT NULL, \n\tamount NUMERIC(50, 25) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_ton_financial_derived_rule UNIQUE (run_id, billing_fact_id, rule_key), \n\tFOREIGN KEY(run_id) REFERENCES ton_financial_normalization_run (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(billing_fact_id) REFERENCES ton_financial_billing_fact (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(account_id) REFERENCES ton_financial_account (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(unit_id) REFERENCES ton_business_unit (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE ton_financial_budget_fact (\n\tid UUID NOT NULL, \n\trun_id UUID NOT NULL, \n\tsource_record_id UUID NOT NULL, \n\taccount_id UUID, \n\tunit_id UUID, \n\taccount_mapping_id UUID, \n\tunit_mapping_id UUID, \n\tperiod_basis VARCHAR(32) NOT NULL, \n\tcalendar_period DATE, \n\tamount NUMERIC(50, 25) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_ton_financial_budget_run_record UNIQUE (run_id, source_record_id), \n\tFOREIGN KEY(run_id) REFERENCES ton_financial_normalization_run (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(source_record_id) REFERENCES ton_operational_source_record (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(account_id) REFERENCES ton_financial_account (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(unit_id) REFERENCES ton_business_unit (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(account_mapping_id) REFERENCES ton_financial_mapping (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(unit_mapping_id) REFERENCES ton_financial_mapping (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE INDEX ix_ton_financial_budget_scope ON ton_financial_budget_fact (run_id, calendar_period, unit_id, account_id)"
    )
    op.execute(
        "CREATE TABLE ton_financial_reconciliation_item (\n\tid UUID NOT NULL, \n\trun_id UUID NOT NULL, \n\tactual_fact_id UUID, \n\tbilling_fact_id UUID, \n\tstatus VARCHAR(32) NOT NULL, \n\tevidence_key VARCHAR(64), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(run_id) REFERENCES ton_financial_normalization_run (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(actual_fact_id) REFERENCES ton_financial_actual_fact (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(billing_fact_id) REFERENCES ton_financial_billing_fact (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE INDEX ix_ton_financial_reconciliation_run_status ON ton_financial_reconciliation_item (run_id, status)"
    )
    op.add_column(
        "ton_financial_account", sa.Column("actual_amount_basis", sa.String(16))
    )
    op.create_check_constraint(
        "ck_ton_financial_account_amount_basis",
        "ton_financial_account",
        "actual_amount_basis IN ('MOVEMENT', 'FINAL')",
    )
    op.create_check_constraint(
        "ck_ton_financial_normalization_error",
        "ton_financial_normalization_run",
        "(status = 'FAILED') = (error_code IS NOT NULL)",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_ton_financial_normalization_active_digest "
        "ON ton_financial_normalization_run (input_digest) "
        "WHERE status IN ('RUNNING', 'SUCCEEDED')"
    )
    op.create_check_constraint(
        "ck_ton_financial_mapping_target",
        "ton_financial_mapping",
        "(kind IN ('ACCOUNT', 'BUDGET_ACCOUNT', 'BILLING_ACCOUNT', 'BILLING_TAX_ACCOUNT') AND account_id IS NOT NULL AND unit_id IS NULL AND calendar_period IS NULL) OR "
        "(kind IN ('UNIT', 'ENTITY', 'BUDGET_UNIT') AND unit_id IS NOT NULL AND account_id IS NULL AND calendar_period IS NULL) OR "
        "(kind = 'BUDGET_PERIOD' AND calendar_period IS NOT NULL AND account_id IS NULL AND unit_id IS NULL)",
    )
    op.execute(
        "CREATE FUNCTION ton_financial_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'canonical financial history is immutable'; END $$"
    )
    for table in (
        "ton_financial_account",
        "ton_financial_mapping_revision",
        "ton_financial_mapping",
        "ton_financial_actual_fact",
        "ton_financial_billing_fact",
        "ton_financial_derived_fact",
        "ton_financial_budget_fact",
        "ton_financial_reconciliation_item",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION ton_financial_immutable()"
        )
    op.execute(
        "CREATE FUNCTION ton_financial_run_transition() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF TG_OP = 'DELETE' OR OLD.status <> 'RUNNING' OR "
        "NEW.status NOT IN ('SUCCEEDED', 'FAILED') OR "
        "(to_jsonb(NEW) - 'status' - 'statistics' - 'error_code' - 'finished_at') "
        "<> (to_jsonb(OLD) - 'status' - 'statistics' - 'error_code' - 'finished_at') "
        "THEN RAISE EXCEPTION 'normalization run is immutable'; END IF; RETURN NEW; END $$"
    )
    op.execute(
        "CREATE TRIGGER ton_financial_normalization_transition "
        "BEFORE UPDATE OR DELETE ON ton_financial_normalization_run "
        "FOR EACH ROW EXECUTE FUNCTION ton_financial_run_transition()"
    )


def downgrade() -> None:
    op.drop_table("ton_financial_reconciliation_item")
    op.drop_table("ton_financial_budget_fact")
    op.drop_table("ton_financial_derived_fact")
    op.drop_table("ton_financial_billing_fact")
    op.drop_table("ton_financial_actual_fact")
    op.drop_table("ton_financial_normalization_run")
    op.drop_table("ton_financial_mapping")
    op.drop_table("ton_financial_mapping_revision")
    op.drop_table("ton_financial_account")
    op.execute("DROP FUNCTION ton_financial_run_transition()")
    op.execute("DROP FUNCTION ton_financial_immutable()")
