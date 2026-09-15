"""ton identity rules and analysis core

Revision ID: faee7eaa921e
Revises: 714172b66b07
Create Date: 2026-09-15 09:39:42.357879

Plan 003b — the first TON-owned domain schema. Creates nine tables and nothing
else:

- ``ton_business_unit`` and ``ton_contract`` — stable organizational identity;
- ``ton_rule`` and ``ton_rule_version`` — versioned deterministic rule
  definitions;
- ``ton_source_snapshot`` — input provenance;
- ``ton_analysis_run``, ``ton_analysis_run_rule_version`` and
  ``ton_analysis_run__source_snapshot`` — execution envelopes;
- ``ton_analysis_step`` — domain-scoped execution blocking.

**This revision seeds nothing.** Zero ``ton_rule`` rows and zero
``ton_rule_version`` rows are inserted. No Prompt Mestre threshold becomes
production configuration here: not 15%, not 3%, not the 35-45% payroll band, not
48 hours, not five days, not 180/120/90/60 days, and no S-rule or T-rule value.
Every threshold is data in ``ton_rule_version.parameters``, and
``ck_ton_rule_version_active_requires_approval`` makes an accidental activation
impossible because ``ACTIVE`` requires a recorded approval.

Two constraints carry the domain guarantees this slice exists for:

- ``ck_ton_rule_version_active_requires_approval`` — no unapproved threshold
  reaches production;
- ``ck_ton_analysis_step_blocked_requires_cause`` — a blocked step always names
  the step that caused it and a reason from the closed vocabulary. There is no
  silent blocking.

``uq_ton_analysis_step_scope`` uses ``NULLS NOT DISTINCT`` so the run-wide scope
(``domain`` and ``business_unit_id`` both NULL) is unique as well. It needs
PostgreSQL 15 or later, which the deployment and CI already run.

Not created here, with the slice that owns them: Finding, FindingEvidence,
FindingInterpretation, Occurrence and its history and ACL tables (003c);
TonReport, TonReportRevision and TonAuditEvent (003d).

``downgrade`` drops exactly these nine tables and nothing else. It is lossless
for the rest of the schema: no existing table is altered, so nothing outside the
TON domain can be affected in either direction.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from onyx.db.ton.enums import AnalysisRunErrorClass
from onyx.db.ton.enums import AnalysisRunStatus
from onyx.db.ton.enums import AnalysisSpecialist
from onyx.db.ton.enums import AnalysisStepBlockedReason
from onyx.db.ton.enums import AnalysisStepCode
from onyx.db.ton.enums import AnalysisStepStatus
from onyx.db.ton.enums import AnalysisTrigger
from onyx.db.ton.enums import BusinessUnitKind
from onyx.db.ton.enums import ContractStatus
from onyx.db.ton.enums import EvidenceConfidenceLevel
from onyx.db.ton.enums import InterpretationStatus
from onyx.db.ton.enums import MissingDataBehavior
from onyx.db.ton.enums import PostResolutionPolicy
from onyx.db.ton.enums import RuleDomain
from onyx.db.ton.enums import RuleKind
from onyx.db.ton.enums import RuleProvenance
from onyx.db.ton.enums import RuleVersionOutcome
from onyx.db.ton.enums import RuleVersionStatus
from onyx.db.ton.enums import SourceType

# revision identifiers, used by Alembic.
revision = "faee7eaa921e"
down_revision = "714172b66b07"
branch_labels = None
depends_on = None


# Ordered for creation; downgrade walks it in reverse so no foreign key is left
# pointing at a dropped table.
TON_TABLES: tuple[str, ...] = (
    "ton_business_unit",
    "ton_contract",
    "ton_rule",
    "ton_rule_version",
    "ton_source_snapshot",
    "ton_analysis_run",
    "ton_analysis_run_rule_version",
    "ton_analysis_run__source_snapshot",
    "ton_analysis_step",
)


def upgrade() -> None:
    op.create_table(
        "ton_business_unit",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.Enum(BusinessUnitKind, native_enum=False), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("external_ref", sa.String(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "ton_contract",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contracting_authority", sa.String(), nullable=False),
        sa.Column("object_summary", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum(ContractStatus, native_enum=False), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["business_unit_id"], ["ton_business_unit.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_ton_contract_date_order",
        ),
    )
    op.create_index(
        "ix_ton_contract_business_unit_id", "ton_contract", ["business_unit_id"]
    )
    op.create_index("ix_ton_contract_status", "ton_contract", ["status"])

    # Rule holds only what must never change: no threshold, no status, no
    # effective date, no mutable title, no approval state.
    op.create_table(
        "ton_rule",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("domain", sa.Enum(RuleDomain, native_enum=False), nullable=False),
        sa.Column("kind", sa.Enum(RuleKind, native_enum=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_ton_rule_domain_kind", "ton_rule", ["domain", "kind"])

    op.create_table(
        "ton_rule_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("executor_key", sa.String(), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("scale", sa.Integer(), nullable=True),
        sa.Column("rounding_mode", sa.String(), nullable=True),
        sa.Column(
            "applicability",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(RuleVersionStatus, native_enum=False),
            server_default=RuleVersionStatus.DRAFT.value,
            nullable=False,
        ),
        sa.Column("source_reference", sa.String(), nullable=True),
        sa.Column(
            "provenance", sa.Enum(RuleProvenance, native_enum=False), nullable=False
        ),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_reference", sa.String(), nullable=True),
        sa.Column(
            "missing_data_behavior",
            sa.Enum(MissingDataBehavior, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "evidence_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "min_confidence_level",
            sa.Enum(EvidenceConfidenceLevel, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "severity_mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("nc_code", sa.String(), nullable=True),
        sa.Column(
            "identity_components",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "post_resolution_policy",
            sa.Enum(PostResolutionPolicy, native_enum=False),
            nullable=False,
        ),
        sa.Column("definition_hash", sa.String(), nullable=True),
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
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["rule_id"], ["ton_rule.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_id", "version", name="uq_ton_rule_version_rule_version"
        ),
        # No disputed number reaches production: a database property, not a
        # review habit.
        sa.CheckConstraint(
            "status <> 'ACTIVE' "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="ck_ton_rule_version_active_requires_approval",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL "
            "OR effective_from IS NULL "
            "OR effective_to >= effective_from",
            name="ck_ton_rule_version_effective_order",
        ),
        sa.CheckConstraint("version >= 1", name="ck_ton_rule_version_positive"),
    )
    op.create_index("ix_ton_rule_version_rule_id", "ton_rule_version", ["rule_id"])
    op.create_index("ix_ton_rule_version_status", "ton_rule_version", ["status"])

    # A receipt for material that was already extracted. No ETL, no field
    # mapping, no NG/Keevo schema.
    op.create_table(
        "ton_source_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_type", sa.Enum(SourceType, native_enum=False), nullable=False
        ),
        sa.Column("source_system_label", sa.String(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column(
            "units_covered",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(), nullable=True),
        sa.Column("is_complete", sa.Boolean(), nullable=False),
        sa.Column(
            "missing_inputs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_schema_conformant", sa.Boolean(), nullable=False),
        sa.Column("ingested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ingested_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_ton_source_snapshot_period_order",
        ),
    )
    op.create_index(
        "ix_ton_source_snapshot_source_type", "ton_source_snapshot", ["source_type"]
    )
    op.create_index(
        "ix_ton_source_snapshot_period",
        "ton_source_snapshot",
        ["period_start", "period_end"],
    )

    # The execution envelope. Deliberately without a resulting-finding array, a
    # report foreign key or a schedule_id.
    op.create_table(
        "ton_analysis_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "trigger", sa.Enum(AnalysisTrigger, native_enum=False), nullable=False
        ),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("routine_code", sa.String(), nullable=True),
        sa.Column(
            "specialist",
            sa.Enum(AnalysisSpecialist, native_enum=False),
            nullable=False,
        ),
        sa.Column("domain", sa.Enum(RuleDomain, native_enum=False), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(AnalysisRunStatus, native_enum=False),
            server_default=AnalysisRunStatus.QUEUED.value,
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column(
            "attempt_no", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column(
            "error_class",
            sa.Enum(AnalysisRunErrorClass, native_enum=False),
            nullable=True,
        ),
        sa.Column("executor_version", sa.String(), nullable=False),
        sa.Column(
            "interpretation_status",
            sa.Enum(InterpretationStatus, native_enum=False),
            server_default=InterpretationStatus.NOT_REQUIRED.value,
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
        sa.ForeignKeyConstraint(
            ["triggered_by_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["business_unit_id"], ["ton_business_unit.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        # Retry convergence: without this a Celery retry duplicates the envelope.
        sa.UniqueConstraint("idempotency_key"),
        sa.CheckConstraint(
            "period_end >= period_start", name="ck_ton_analysis_run_period_order"
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR started_at IS NOT NULL",
            name="ck_ton_analysis_run_finished_requires_start",
        ),
        sa.CheckConstraint(
            "attempt_no >= 1", name="ck_ton_analysis_run_attempt_positive"
        ),
    )
    op.create_index(
        "ix_ton_analysis_run_scope",
        "ton_analysis_run",
        ["domain", "business_unit_id"],
    )
    op.create_index("ix_ton_analysis_run_status", "ton_analysis_run", ["status"])
    op.create_index(
        "ix_ton_analysis_run_period",
        "ton_analysis_run",
        ["period_start", "period_end"],
    )

    # Which rule versions took part, and what became of each. No Finding foreign
    # key: Finding arrives in 003c.
    op.create_table(
        "ton_analysis_run_rule_version",
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum(RuleVersionOutcome, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "finding_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["ton_analysis_run.id"], ondelete="CASCADE"
        ),
        # RESTRICT: a rule version that took part in an analysis must stay
        # referenceable, or the audit trail develops holes.
        sa.ForeignKeyConstraint(
            ["rule_version_id"], ["ton_rule_version.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("analysis_run_id", "rule_version_id"),
        sa.CheckConstraint(
            "finding_count >= 0", name="ck_ton_analysis_run_rule_version_count"
        ),
        sa.CheckConstraint(
            "outcome = 'EXECUTED' OR finding_count = 0",
            name="ck_ton_analysis_run_rule_version_skipped_has_no_findings",
        ),
    )
    op.create_index(
        "ix_ton_analysis_run_rule_version_rule_version_id",
        "ton_analysis_run_rule_version",
        ["rule_version_id"],
    )

    # Explicit association rather than one opaque JSON blob on the run, so
    # "which analyses used snapshot X?" is a relational question.
    op.create_table(
        "ton_analysis_run__source_snapshot",
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["ton_analysis_run.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"], ["ton_source_snapshot.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("analysis_run_id", "source_snapshot_id"),
    )
    op.create_index(
        "ix_ton_analysis_run__source_snapshot_snapshot_id",
        "ton_analysis_run__source_snapshot",
        ["source_snapshot_id"],
    )

    # Where blocking lives. The scope is (step_code, domain, business_unit_id),
    # never the run.
    op.create_table(
        "ton_analysis_step",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "step_code", sa.Enum(AnalysisStepCode, native_enum=False), nullable=False
        ),
        sa.Column("domain", sa.Enum(RuleDomain, native_enum=False), nullable=True),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(AnalysisStepStatus, native_enum=False),
            server_default=AnalysisStepStatus.PENDING.value,
            nullable=False,
        ),
        sa.Column("blocked_by_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "blocked_reason",
            sa.Enum(AnalysisStepBlockedReason, native_enum=False),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["ton_analysis_run.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["business_unit_id"], ["ton_business_unit.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["blocked_by_step_id"], ["ton_analysis_step.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        # No silent blocking: a BLOCKED step always names its cause and reason.
        sa.CheckConstraint(
            "status <> 'BLOCKED' "
            "OR (blocked_by_step_id IS NOT NULL AND blocked_reason IS NOT NULL)",
            name="ck_ton_analysis_step_blocked_requires_cause",
        ),
        sa.CheckConstraint(
            "blocked_by_step_id IS NULL OR blocked_by_step_id <> id",
            name="ck_ton_analysis_step_no_self_block",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR started_at IS NOT NULL",
            name="ck_ton_analysis_step_finished_requires_start",
        ),
    )
    # NULLS NOT DISTINCT so the run-wide scope (both NULL) is unique too.
    op.create_index(
        "uq_ton_analysis_step_scope",
        "ton_analysis_step",
        ["analysis_run_id", "step_code", "domain", "business_unit_id"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "ix_ton_analysis_step_run_status",
        "ton_analysis_step",
        ["analysis_run_id", "status"],
    )
    op.create_index(
        "ix_ton_analysis_step_blocked_by",
        "ton_analysis_step",
        ["blocked_by_step_id"],
    )

    # No business rule is seeded. Rule and RuleVersion creation is an explicit,
    # audited admin action, never a migration side effect.


def downgrade() -> None:
    # Reverse creation order. Indexes go with their tables, so DROP TABLE is
    # enough; only the TON tables are touched.
    for table_name in reversed(TON_TABLES):
        op.drop_table(table_name)
