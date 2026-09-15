"""ton findings, occurrences, evidence and resource acl

Revision ID: 6b0ca4eb29fb
Revises: faee7eaa921e
Create Date: 2026-09-15 11:47:01.248810

Plan 003c — the analytical result and business-case layer. Creates twelve tables
and one sequence, and nothing else:

- ``ton_occurrence`` — the persistent Prompt Mestre §13.1 business ledger;
- ``ton_finding`` — immutable deterministic detections;
- ``ton_finding_evidence`` — source pointers with a generic locator;
- ``ton_finding_interpretation`` — append-only AI-interpretation attempts;
- ``ton_occurrence_event`` — authoritative append-only lifecycle history;
- ``ton_occurrence_impact`` — normalised §9 quantification;
- ``ton_occurrence_assignment`` — responsibility and deadline history;
- ``ton_occurrence_note`` — human commentary;
- ``ton_occurrence_impacted_domain`` — the §15 handoff list;
- ``ton_business_unit__user_group``, ``ton_contract__user_group`` and
  ``ton_occurrence__user_group`` — the fail-closed resource ACL.

**This revision seeds nothing.** Zero rows in all twelve tables. No Prompt Mestre
threshold becomes production configuration here: no criticality percentage, no NC
mapping, no deadline, no payroll band, no publication ceiling. Criticality bands
stay ``ton_rule_version.severity_mapping`` data, and
``ck_ton_rule_version_active_requires_approval`` from 003b still makes an
accidental activation impossible.

Four constraints carry the domain guarantees this slice exists for:

- ``ton_occurrence.identity_key`` UNIQUE — the deduplication boundary. Two
  concurrent detector workers converge on one business case, which an
  application-level pre-check cannot guarantee.
- ``uq_ton_finding_run_rule_version_identity`` — retrying a detection inside one
  logical analysis cannot duplicate a finding.
- ``ck_ton_occurrence_event_human_only_transitions`` — the six transitions Prompt
  Mestre §12.1 reserves for a human require ``actor_kind = USER``, an identified
  ``actor_user_id`` and an ``authorization_reference``. Readiness §9, verbatim.
- ``ck_ton_occurrence_critical_requires_human_closure`` — a critical occurrence
  always requires human closure, so TON cannot close one on its own.

Two schema decisions worth stating here, because a reader of the DDL alone would
otherwise have to infer them:

**Supersede and uniqueness.** Readiness §7 requires both ``UNIQUE(identity_key)``
and ``SUPERSEDE_WITH_NEW_OCCURRENCE``. They only hold together if a superseding
case's canonical tuple differs, so ``logical_identity_key`` carries the
generation-free lineage digest and ``identity_key`` includes the generation.
``ck_ton_occurrence_first_generation_identity`` makes the two equal for
generation 1 — every case that was never superseded — so the ordinary path is
exactly the readiness contract.

**``ton_occurrence_event.actor_user_id`` uses ``ON DELETE RESTRICT``**, unlike
every other user reference in the TON schema, which uses ``SET NULL``. The
human-only CHECK requires the column to be non-null for an authorized decision,
and ``SET NULL`` would void that guarantee the first time an account was hard
deleted. An account that authorized a human-only TON decision therefore stays
referenceable; deactivate it rather than deleting it.

No monetary column is a float. Amounts are ``NUMERIC(30, 10)`` and map to Python
``Decimal``; ``ton_finding_evidence.extracted_value`` stays a decimal string so
the value a source stated survives verbatim.

No ``is_public``, ``public``, ``is_global`` or ``public_permission`` column exists
on any table here. For a TON resource, zero junction rows means DENIED, so a
permissive short-circuit is not merely disabled — it is inexpressible.

Not created here, with the slice that owns them: ``ton_report``,
``ton_report_revision``, ``ton_report__user_group`` and ``ton_audit_event``
(003d). The readiness gate historically said 003c creates "four ``*__UserGroup``
junctions"; ``TonReport`` does not exist until 003d, so the fourth junction goes
with it and this revision creates three.

``downgrade`` drops exactly these twelve tables and the sequence, and nothing
else. No existing table is altered in either direction.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from onyx.db.ton.enums import AssignmentStatus
from onyx.db.ton.enums import EvidenceConfidenceLevel
from onyx.db.ton.enums import FindingKind
from onyx.db.ton.enums import ImpactCategory
from onyx.db.ton.enums import ImpactConfidence
from onyx.db.ton.enums import ImpactMethod
from onyx.db.ton.enums import InterpretationFailureClass
from onyx.db.ton.enums import InterpretationInputScope
from onyx.db.ton.enums import InterpretationStatus
from onyx.db.ton.enums import OccurrenceActorKind
from onyx.db.ton.enums import OccurrenceCriticality
from onyx.db.ton.enums import OccurrenceLedgerKind
from onyx.db.ton.enums import OccurrenceStatus
from onyx.db.ton.enums import OccurrenceTransition
from onyx.db.ton.enums import OccurrenceVerificationResult
from onyx.db.ton.enums import RedactionLevel
from onyx.db.ton.enums import RuleDomain
from onyx.db.ton.enums import SourceType
from onyx.db.ton.enums import TonSharePermission
from onyx.db.ton.enums import UnitCostSource

# revision identifiers, used by Alembic.
revision = "6b0ca4eb29fb"
down_revision = "faee7eaa921e"
branch_labels = None
depends_on = None


# Ordered for creation; downgrade walks it in reverse so no foreign key is left
# pointing at a dropped table.
TON_TABLES: tuple[str, ...] = (
    "ton_occurrence",
    "ton_finding",
    "ton_finding_evidence",
    "ton_finding_interpretation",
    "ton_occurrence_event",
    "ton_occurrence_impact",
    "ton_occurrence_assignment",
    "ton_occurrence_note",
    "ton_occurrence_impacted_domain",
    "ton_business_unit__user_group",
    "ton_contract__user_group",
    "ton_occurrence__user_group",
)

SHORT_CODE_SEQUENCE = "ton_occurrence_short_code_seq"

# Money and quantities. NUMERIC, never DOUBLE PRECISION: an IEEE-754 round-trip
# would make a published amount irreproducible, and readiness §12 makes exact
# decimal serialisation the precondition for the 003d report hash.
AMOUNT = sa.Numeric(30, 10, asdecimal=True)
PERCENT = sa.Numeric(9, 4, asdecimal=True)


def upgrade() -> None:
    # Allocates the human-facing occurrence code. A sequence rather than a
    # Python counter: two concurrent detector workers must not compute the same
    # code, and a display-code gap is not a defect whereas a duplicate would be.
    op.execute(sa.text(f"CREATE SEQUENCE {SHORT_CODE_SEQUENCE}"))

    op.create_table(
        "ton_occurrence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "short_code",
            sa.String(),
            server_default=sa.text(
                f"'OC-' || lpad(nextval('{SHORT_CODE_SEQUENCE}')::text, 6, '0')"
            ),
            nullable=False,
        ),
        sa.Column("identity_key", sa.String(), nullable=False),
        sa.Column("logical_identity_key", sa.String(), nullable=False),
        sa.Column(
            "supersede_generation",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "current_rule_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "owning_domain", sa.Enum(RuleDomain, native_enum=False), nullable=False
        ),
        sa.Column(
            "ledger_kind",
            sa.Enum(OccurrenceLedgerKind, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "criticality",
            sa.Enum(OccurrenceCriticality, native_enum=False),
            nullable=False,
        ),
        sa.Column("nc_code", sa.String(), nullable=True),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(OccurrenceStatus, native_enum=False),
            server_default=OccurrenceStatus.NEW.value,
            nullable=False,
        ),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "detection_count", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column(
            "open_cycle_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_criterion", sa.Text(), nullable=True),
        sa.Column(
            "verification_result",
            sa.Enum(OccurrenceVerificationResult, native_enum=False),
            nullable=True,
        ),
        sa.Column("verification_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "legal_review_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "requires_human_closure",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "superseded_by_occurrence_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
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
        sa.ForeignKeyConstraint(["rule_id"], ["ton_rule.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["current_rule_version_id"], ["ton_rule_version.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["business_unit_id"], ["ton_business_unit.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"], ["ton_contract.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_occurrence_id"], ["ton_occurrence.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_code"),
        # The deduplication boundary.
        sa.UniqueConstraint("identity_key"),
        sa.UniqueConstraint(
            "logical_identity_key",
            "supersede_generation",
            name="uq_ton_occurrence_lineage_generation",
        ),
        sa.CheckConstraint(
            "supersede_generation >= 1", name="ck_ton_occurrence_generation_positive"
        ),
        sa.CheckConstraint(
            "supersede_generation > 1 OR identity_key = logical_identity_key",
            name="ck_ton_occurrence_first_generation_identity",
        ),
        sa.CheckConstraint(
            "last_detected_at >= first_detected_at",
            name="ck_ton_occurrence_detection_order",
        ),
        sa.CheckConstraint(
            "detection_count >= 1", name="ck_ton_occurrence_detection_count_positive"
        ),
        sa.CheckConstraint(
            "open_cycle_count >= 1", name="ck_ton_occurrence_open_cycle_positive"
        ),
        sa.CheckConstraint(
            "status <> 'RESOLVED' OR resolved_at IS NOT NULL",
            name="ck_ton_occurrence_resolved_requires_timestamp",
        ),
        # TON may propose closing a critical occurrence; it may not close one.
        sa.CheckConstraint(
            "criticality <> 'CRITICAL' OR requires_human_closure",
            name="ck_ton_occurrence_critical_requires_human_closure",
        ),
        sa.CheckConstraint(
            "superseded_by_occurrence_id IS NULL OR superseded_by_occurrence_id <> id",
            name="ck_ton_occurrence_no_self_supersede",
        ),
        sa.CheckConstraint(
            "verification_result IS NULL OR verification_checked_at IS NOT NULL",
            name="ck_ton_occurrence_verification_requires_timestamp",
        ),
    )
    op.create_index(
        "ix_ton_occurrence_logical_identity", "ton_occurrence", ["logical_identity_key"]
    )
    op.create_index(
        "ix_ton_occurrence_status_criticality",
        "ton_occurrence",
        ["status", "criticality"],
    )
    op.create_index(
        "ix_ton_occurrence_scope",
        "ton_occurrence",
        ["owning_domain", "business_unit_id"],
    )
    op.create_index("ix_ton_occurrence_contract_id", "ton_occurrence", ["contract_id"])
    op.create_index("ix_ton_occurrence_rule_id", "ton_occurrence", ["rule_id"])
    # `id` is the tiebreaker: `last_detected_at` alone is not a total order, and
    # an unstable sort makes server-side pagination repeat rows.
    op.create_index(
        "ix_ton_occurrence_last_detected", "ton_occurrence", ["last_detected_at", "id"]
    )

    # Immutable analytical output. No lifecycle status column: resolution belongs
    # to the occurrence, narrative to the interpretation.
    op.create_table(
        "ton_finding",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_key", sa.String(), nullable=False),
        sa.Column(
            "finding_kind", sa.Enum(FindingKind, native_enum=False), nullable=False
        ),
        sa.Column(
            "interpretation_status",
            sa.Enum(InterpretationStatus, native_enum=False),
            server_default=InterpretationStatus.NOT_REQUIRED.value,
            nullable=False,
        ),
        sa.Column("domain", sa.Enum(RuleDomain, native_enum=False), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("expected_value", AMOUNT, nullable=True),
        sa.Column("actual_value", AMOUNT, nullable=True),
        sa.Column("deviation_value", AMOUNT, nullable=True),
        sa.Column("computed_impact_amount", AMOUNT, nullable=True),
        sa.Column("value_scale", sa.Integer(), nullable=True),
        sa.Column("value_unit", sa.String(), nullable=True),
        sa.Column("value_currency", sa.String(length=3), nullable=True),
        sa.Column(
            "deterministic_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("nc_code", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # RESTRICT: the run and the version that produced a finding are part of
        # the audit chain. There is deliberately no `rule_id` column — history
        # references the version, never the rule alone.
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["ton_analysis_run.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["rule_version_id"], ["ton_rule_version.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["ton_occurrence.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["business_unit_id"], ["ton_business_unit.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"], ["ton_contract.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "rule_version_id",
            "identity_key",
            name="uq_ton_finding_run_rule_version_identity",
        ),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_ton_finding_period_order",
        ),
    )
    op.create_index("ix_ton_finding_occurrence_id", "ton_finding", ["occurrence_id"])
    op.create_index("ix_ton_finding_identity_key", "ton_finding", ["identity_key"])
    op.create_index(
        "ix_ton_finding_rule_version_id", "ton_finding", ["rule_version_id"]
    )
    op.create_index(
        "ix_ton_finding_interpretation_status", "ton_finding", ["interpretation_status"]
    )
    op.create_index(
        "ix_ton_finding_scope", "ton_finding", ["domain", "business_unit_id"]
    )

    # A pointer to source material, not an ETL schema. `locator` is the single
    # generic field; no NG/Keevo column name exists anywhere here (D-009).
    op.create_table(
        "ton_finding_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "source_type", sa.Enum(SourceType, native_enum=False), nullable=False
        ),
        # NOT NULL: Prompt Mestre §3.4 makes a published number without its
        # A/B/C/D level a defect.
        sa.Column(
            "confidence_level",
            sa.Enum(EvidenceConfidenceLevel, native_enum=False),
            nullable=False,
        ),
        sa.Column("record_key", sa.String(), nullable=True),
        sa.Column(
            "locator",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("file_record_id", sa.String(), nullable=True),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("chat_message_id", sa.Integer(), nullable=True),
        # A decimal string, not a numeric column: it records what the source
        # stated, at the source's own scale, without a float round-trip.
        sa.Column("extracted_value", sa.String(), nullable=True),
        sa.Column("value_scale", sa.Integer(), nullable=True),
        sa.Column("value_unit", sa.String(), nullable=True),
        sa.Column("value_currency", sa.String(length=3), nullable=True),
        sa.Column(
            "is_non_standard_source",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "redaction_level",
            sa.Enum(RedactionLevel, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["ton_finding.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"], ["ton_source_snapshot.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["file_record_id"], ["file_record.file_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["chat_message_id"], ["chat_message.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ton_finding_evidence_finding_id", "ton_finding_evidence", ["finding_id"]
    )
    op.create_index(
        "ix_ton_finding_evidence_source_snapshot_id",
        "ton_finding_evidence",
        ["source_snapshot_id"],
    )

    # One row per attempt, append-only. No chain-of-thought, no raw prompt body
    # and no response transcript: only the business-facing output and the
    # provenance needed to reproduce the call shape.
    op.create_table(
        "ton_finding_interpretation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.Enum(InterpretationStatus, native_enum=False), nullable=False
        ),
        sa.Column("llm_provider", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("prompt_key", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("probable_cause", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("impact_narrative", sa.Text(), nullable=True),
        # Proposals only. Promotion is a separate audited transition.
        sa.Column(
            "proposed_criticality",
            sa.Enum(OccurrenceCriticality, native_enum=False),
            nullable=True,
        ),
        sa.Column("proposed_nc_code", sa.String(), nullable=True),
        sa.Column(
            "evidence_reference_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "input_scope",
            sa.Enum(InterpretationInputScope, native_enum=False),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "failure_class",
            sa.Enum(InterpretationFailureClass, native_enum=False),
            nullable=True,
        ),
        sa.Column(
            "retry_eligible",
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
        sa.ForeignKeyConstraint(["finding_id"], ["ton_finding.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "finding_id", "attempt_no", name="uq_ton_finding_interpretation_attempt"
        ),
        sa.CheckConstraint(
            "attempt_no >= 1", name="ck_ton_finding_interpretation_attempt_positive"
        ),
        sa.CheckConstraint(
            "status <> 'FAILED' OR failure_class IS NOT NULL",
            name="ck_ton_finding_interpretation_failed_has_class",
        ),
        sa.CheckConstraint(
            "failure_class IS NULL OR status = 'FAILED'",
            name="ck_ton_finding_interpretation_class_only_on_failure",
        ),
        # Stops a provider failure being laundered into an empty success.
        sa.CheckConstraint(
            "status <> 'COMPLETED' "
            "OR (summary IS NOT NULL AND finished_at IS NOT NULL)",
            name="ck_ton_finding_interpretation_completed_has_summary",
        ),
        sa.CheckConstraint(
            "status <> 'COMPLETED' "
            "OR (llm_provider IS NOT NULL AND model_name IS NOT NULL)",
            name="ck_ton_finding_interpretation_completed_has_provenance",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR status IN ('COMPLETED', 'FAILED')",
            name="ck_ton_finding_interpretation_finished_is_terminal",
        ),
    )
    op.create_index(
        "ix_ton_finding_interpretation_finding_id",
        "ton_finding_interpretation",
        ["finding_id"],
    )
    # Not `ix_ton_finding_interpretation_status`: that name already indexes
    # `ton_finding.interpretation_status`, and index names are schema-unique.
    op.create_index(
        "ix_ton_finding_interpretation_attempt_status",
        "ton_finding_interpretation",
        ["status"],
    )

    # The authoritative lifecycle history. Occurrence.status and open_cycle_count
    # are projections maintained from these rows.
    op.create_table(
        "ton_occurrence_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column(
            "transition",
            sa.Enum(OccurrenceTransition, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "resulting_status",
            sa.Enum(OccurrenceStatus, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "actor_kind",
            sa.Enum(OccurrenceActorKind, native_enum=False),
            nullable=False,
        ),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("authorization_reference", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["ton_occurrence.id"], ondelete="CASCADE"
        ),
        # RESTRICT, not SET NULL: the human-only CHECK below requires this column
        # to stay non-null for an authorized decision.
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["finding_id"], ["ton_finding.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["rule_version_id"], ["ton_rule_version.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "occurrence_id", "sequence_no", name="uq_ton_occurrence_event_sequence"
        ),
        sa.CheckConstraint(
            "sequence_no >= 1", name="ck_ton_occurrence_event_sequence_positive"
        ),
        # Readiness §9, verbatim: the six transitions Prompt Mestre §12.1 reserves
        # for a human cannot be written by a system actor at all.
        sa.CheckConstraint(
            "transition NOT IN ("
            "'RESOLVE_CRITICAL', 'ACCEPT_RISK', 'DISMISS', "
            "'ASSERT_NONCOMPLIANCE', 'PROMOTE_INTERPRETATION', "
            "'OVERRIDE_DETERMINISTIC_VALUE') "
            "OR (actor_kind = 'USER' AND actor_user_id IS NOT NULL "
            "AND authorization_reference IS NOT NULL)",
            name="ck_ton_occurrence_event_human_only_transitions",
        ),
        sa.CheckConstraint(
            "transition <> 'RESOLVED' "
            "OR (actor_kind = 'USER' AND actor_user_id IS NOT NULL)",
            name="ck_ton_occurrence_event_resolution_requires_user",
        ),
        sa.CheckConstraint(
            "actor_kind <> 'USER' OR actor_user_id IS NOT NULL",
            name="ck_ton_occurrence_event_user_actor_identified",
        ),
    )
    op.create_index(
        "ix_ton_occurrence_event_occurrence_id",
        "ton_occurrence_event",
        ["occurrence_id"],
    )
    op.create_index(
        "ix_ton_occurrence_event_transition", "ton_occurrence_event", ["transition"]
    )
    op.create_index(
        "ix_ton_occurrence_event_actor_user_id",
        "ton_occurrence_event",
        ["actor_user_id"],
    )

    # Prompt Mestre §9 quantification. Every amount is NUMERIC; nothing is a float.
    op.create_table(
        "ton_occurrence_impact",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "category", sa.Enum(ImpactCategory, native_enum=False), nullable=False
        ),
        sa.Column(
            "confidence", sa.Enum(ImpactConfidence, native_enum=False), nullable=False
        ),
        sa.Column("method", sa.Enum(ImpactMethod, native_enum=False), nullable=False),
        # NOT NULL: §9's "diga sempre qual usou".
        sa.Column(
            "unit_cost_source",
            sa.Enum(UnitCostSource, native_enum=False),
            nullable=False,
        ),
        sa.Column("predicted_amount", AMOUNT, nullable=True),
        sa.Column("realized_amount", AMOUNT, nullable=True),
        sa.Column("quantity", AMOUNT, nullable=True),
        sa.Column("quantity_unit", sa.String(), nullable=True),
        sa.Column("unit_cost", AMOUNT, nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("scale", sa.Integer(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("premise", sa.Text(), nullable=True),
        sa.Column("sensitivity_pct", PERCENT, nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
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
            ["occurrence_id"], ["ton_occurrence.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["verified_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        # §13.3: only a verified saving is realised.
        sa.CheckConstraint(
            "realized_amount IS NULL OR verified_at IS NOT NULL",
            name="ck_ton_occurrence_impact_realized_requires_verification",
        ),
        sa.CheckConstraint(
            "predicted_amount IS NOT NULL OR realized_amount IS NOT NULL",
            name="ck_ton_occurrence_impact_has_an_amount",
        ),
        sa.CheckConstraint(
            "method <> 'OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST' "
            "OR unit_cost_source <> 'NOT_APPLICABLE'",
            name="ck_ton_occurrence_impact_unit_cost_source_required",
        ),
        sa.CheckConstraint(
            "sensitivity_pct IS NULL OR sensitivity_pct >= 0",
            name="ck_ton_occurrence_impact_sensitivity_non_negative",
        ),
        sa.CheckConstraint("scale >= 0", name="ck_ton_occurrence_impact_scale_valid"),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_ton_occurrence_impact_period_order",
        ),
    )
    op.create_index(
        "ix_ton_occurrence_impact_occurrence_id",
        "ton_occurrence_impact",
        ["occurrence_id"],
    )
    # Backs the later realised-ROI aggregation: verified, non-BAIXA rows.
    op.create_index(
        "ix_ton_occurrence_impact_roi",
        "ton_occurrence_impact",
        ["confidence", "verified_at"],
    )
    op.create_index(
        "ix_ton_occurrence_impact_category", "ton_occurrence_impact", ["category"]
    )

    # Responsibility and deadline history, not a mutable "current assignee" pair.
    op.create_table(
        "ton_occurrence_assignment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Required, and it survives an account deletion. §11 publishes a gap with
        # a named owner, who may hold no Onyx account.
        sa.Column("responsible_label", sa.String(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(AssignmentStatus, native_enum=False),
            server_default=AssignmentStatus.OPEN.value,
            nullable=False,
        ),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "actor_kind",
            sa.Enum(OccurrenceActorKind, native_enum=False),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["ton_occurrence.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["responsible_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "occurrence_id",
            "sequence_no",
            name="uq_ton_occurrence_assignment_sequence",
        ),
        sa.CheckConstraint(
            "sequence_no >= 1", name="ck_ton_occurrence_assignment_sequence_positive"
        ),
        sa.CheckConstraint(
            "status <> 'COMPLETED' OR completed_at IS NOT NULL",
            name="ck_ton_occurrence_assignment_completed_has_timestamp",
        ),
        sa.CheckConstraint(
            "status <> 'SUPERSEDED' OR superseded_at IS NOT NULL",
            name="ck_ton_occurrence_assignment_superseded_has_timestamp",
        ),
    )
    op.create_index(
        "ix_ton_occurrence_assignment_occurrence_id",
        "ton_occurrence_assignment",
        ["occurrence_id"],
    )
    op.create_index(
        "ix_ton_occurrence_assignment_deadline",
        "ton_occurrence_assignment",
        ["deadline"],
    )

    # Append-only. May carry PII, so it inherits the occurrence ACL and has no
    # separate, more permissive read path.
    op.create_table(
        "ton_occurrence_note",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "actor_kind",
            sa.Enum(OccurrenceActorKind, native_enum=False),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "redaction_level",
            sa.Enum(RedactionLevel, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["ton_occurrence.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["author_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "occurrence_id", "sequence_no", name="uq_ton_occurrence_note_sequence"
        ),
        sa.CheckConstraint(
            "sequence_no >= 1", name="ck_ton_occurrence_note_sequence_positive"
        ),
    )
    op.create_index(
        "ix_ton_occurrence_note_occurrence_id", "ton_occurrence_note", ["occurrence_id"]
    )

    # The §15 handoff list. One domain owns the case; the others are listed here
    # rather than duplicated as extra occurrences.
    op.create_table(
        "ton_occurrence_impacted_domain",
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.Enum(RuleDomain, native_enum=False), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["ton_occurrence.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("occurrence_id", "domain"),
    )

    # The three fail-closed ACL junctions. Restrictive, not additive: zero rows
    # means DENIED. TonReport__UserGroup belongs to 003d with its table.
    for table_name, resource_column, resource_table in (
        ("ton_business_unit__user_group", "business_unit_id", "ton_business_unit"),
        ("ton_contract__user_group", "contract_id", "ton_contract"),
        ("ton_occurrence__user_group", "occurrence_id", "ton_occurrence"),
    ):
        op.create_table(
            table_name,
            sa.Column(resource_column, postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_group_id", sa.Integer(), nullable=False),
            sa.Column(
                "permission",
                sa.Enum(TonSharePermission, native_enum=False),
                server_default=TonSharePermission.VIEWER.value,
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                [resource_column], [f"{resource_table}.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["user_group_id"], ["user_group.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint(resource_column, "user_group_id"),
        )
        op.create_index(f"ix_{table_name}_group_id", table_name, ["user_group_id"])


def downgrade() -> None:
    # Reverse creation order. Indexes go with their tables, so DROP TABLE is
    # enough; only the 003c tables and the sequence are touched, so every 003b
    # structure survives intact.
    for table_name in reversed(TON_TABLES):
        op.drop_table(table_name)
    op.execute(sa.text(f"DROP SEQUENCE IF EXISTS {SHORT_CODE_SEQUENCE}"))
