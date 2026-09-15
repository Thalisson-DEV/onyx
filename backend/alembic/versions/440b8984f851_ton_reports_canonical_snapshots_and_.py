"""ton reports canonical snapshots and persistent audit

Revision ID: 440b8984f851
Revises: 6b0ca4eb29fb
Create Date: 2026-09-15 17:21:11.236328

Plan 003d — the published-evidence layer. Creates nine tables and nothing else:

- ``ton_report`` — the stable logical report identity;
- ``ton_report_revision`` — the immutable published snapshot;
- ``ton_report_revision__analysis_run``, ``__occurrence``, ``__finding``,
  ``__rule_version``, ``__source_snapshot`` — the exact inputs a revision was
  built from, pinned by id;
- ``ton_report__user_group`` — the fourth fail-closed ACL junction, deferred here
  from 003c because ``ton_report`` did not exist yet (decision D-043);
- ``ton_audit_event`` — persistent, best-effort, actor-attributed audit.

Together with 003b and 003c this closes the persistent chain
``ton_rule_version -> ton_analysis_run -> ton_finding -> ton_occurrence ->
ton_report``.

**This revision seeds nothing.** Zero rows in all nine tables. No report, no
report revision, no rule, no rule version, no occurrence, no finding, no
threshold, no publication ceiling, no business unit, no contract and no audit
event. Schema only.

**No existing table is altered, in either direction.** In particular
``ton_rule_version.definition_hash`` keeps the nullable ``String`` column 003b
created. 003d now writes it — via ``ton-canon-1`` in
``onyx.db.ton.rule_versions`` — but making it NOT NULL would demand a value for
every legitimate pre-existing row, including one whose ``parameters`` hold a JSON
float that cannot be canonicalised exactly. Fabricating a hash under a scheme that
cannot re-derive it would defeat the column's whole purpose, so the column stays
nullable and the backfill reports what it could not hash.

Four constraints carry the domain guarantees this slice exists for:

- ``uq_ton_report_revision_report_revision`` — ``UNIQUE(report_id, revision_no)``
  is the append-only history. Publishing again takes revision N+1; it cannot reuse
  N, so a published figure cannot be rewritten.
- ``ck_ton_report_revision_superseded_requires_reason`` — a correction must record
  why. A changed published figure with no recorded reason is the audit gap
  revisions exist to close.
- ``ON DELETE RESTRICT`` on every pinned input — ``analysis_run_id``,
  ``occurrence_id``, ``finding_id``, ``rule_version_id``, ``source_snapshot_id``
  and ``ton_report.business_unit_id``. A published report must not be left with a
  number whose evidence has vanished, so the database refuses the delete rather
  than cascading it for cleanup convenience.
- ``ck_ton_audit_event_resource_reference_complete`` — a resource pointer is
  complete or absent. Half a pointer silently drops an event out of a resource's
  history.

Two schema decisions a reader of the DDL alone would otherwise have to infer:

**``ton_audit_event.action``, ``outcome`` and ``ocsf_class`` are plain
``String``, not ``Enum(..., native_enum=False)``.** ``AuditAction`` is a
repository-wide append-only vocabulary that grows with unrelated features; a
non-native enum column would attach a CHECK constraint that turns "someone added
an audit action elsewhere" into a failed INSERT here until a TON migration caught
up. Storing the dotted ``.value`` also keeps the table comparable with the
existing stdout audit stream, which writes the same strings.

**``ton_audit_event.domain_event_id`` has no foreign key.** It points at whichever
authoritative row the event attributes — an ``ton_occurrence_event``, a
``ton_report_revision``, a ``ton_rule_version`` — and one column cannot have a
foreign key to several tables. It is a reference, per readiness §11's
anti-duplication rule; the domain table remains the source of truth.

No monetary column appears in this slice. Published amounts live inside
``ton_report_revision.canonical_payload`` as decimal **strings** under
``ton-canon-1``, never as JSON floats, so a published figure round-trips exactly
and the ``content_hash`` over it is reproducible.

No ``is_public``, ``public``, ``is_global`` or ``public_permission`` column exists
on any table here. For a TON report, zero ``ton_report__user_group`` rows means
DENIED, so a permissive short-circuit is not merely disabled — it is
inexpressible.

``downgrade`` drops exactly these nine tables and nothing else. Every 003b and
003c structure survives it intact.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.enums import TonReportType
from onyx.db.ton.enums import TonSharePermission

# revision identifiers, used by Alembic.
revision = "440b8984f851"
down_revision = "6b0ca4eb29fb"
branch_labels = None
depends_on = None


# Ordered for creation; downgrade walks it in reverse so no foreign key is left
# pointing at a dropped table.
TON_TABLES: tuple[str, ...] = (
    "ton_report",
    "ton_report_revision",
    "ton_report_revision__analysis_run",
    "ton_report_revision__occurrence",
    "ton_report_revision__finding",
    "ton_report_revision__rule_version",
    "ton_report_revision__source_snapshot",
    "ton_report__user_group",
    "ton_audit_event",
)


def upgrade() -> None:
    op.create_table(
        "ton_report",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column(
            "report_type", sa.Enum(TonReportType, native_enum=False), nullable=False
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["business_unit_id"], ["ton_business_unit.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_ton_report_code"),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_ton_report_period_order",
        ),
    )
    op.create_index(
        "ix_ton_report_type_period", "ton_report", ["report_type", "period_start"]
    )
    op.create_index(
        "ix_ton_report_business_unit_id", "ton_report", ["business_unit_id"]
    )

    op.create_table(
        "ton_report_revision",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        # The frozen content, already reduced to ton-canon-1's JSON-native form:
        # decimal strings, RFC 3339 UTC timestamps, enum values, absent keys
        # omitted. Written once, never updated.
        sa.Column("canonical_payload", postgresql.JSONB(), nullable=False),
        # NOT NULL with no default on all four. A snapshot whose scheme,
        # algorithm, digest or generator identity is unknown is not evidence of
        # anything, and storing the first two as data means a future change to
        # either cannot invalidate a hash already recorded.
        sa.Column("canonicalization_version", sa.String(), nullable=False),
        sa.Column("hash_algorithm", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("generator_version", sa.String(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "superseded_by_revision_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("correction_reason", sa.Text(), nullable=True),
        sa.Column("file_record_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # CASCADE, matching ton_rule_version -> ton_rule: a revision has no
        # meaning without its logical report. The RESTRICTs on the join tables
        # below still refuse to let a pinned input vanish under a live revision.
        sa.ForeignKeyConstraint(["report_id"], ["ton_report.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by"], ["user.id"], ondelete="SET NULL"),
        # SET NULL: losing the successor must not delete the record of what was
        # published before it.
        sa.ForeignKeyConstraint(
            ["superseded_by_revision_id"],
            ["ton_report_revision.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["file_record_id"], ["file_record.file_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_id", "revision_no", name="uq_ton_report_revision_report_revision"
        ),
        sa.CheckConstraint("revision_no >= 1", name="ck_ton_report_revision_positive"),
        sa.CheckConstraint(
            "superseded_by_revision_id IS NULL OR superseded_by_revision_id <> id",
            name="ck_ton_report_revision_no_self_supersede",
        ),
        sa.CheckConstraint(
            "superseded_by_revision_id IS NULL OR correction_reason IS NOT NULL",
            name="ck_ton_report_revision_superseded_requires_reason",
        ),
    )
    op.create_index(
        "ix_ton_report_revision_report_id", "ton_report_revision", ["report_id"]
    )
    op.create_index(
        "ix_ton_report_revision_content_hash", "ton_report_revision", ["content_hash"]
    )
    op.create_index(
        "ix_ton_report_revision_generated_at",
        "ton_report_revision",
        ["generated_at", "id"],
    )

    # The five pinned-input join tables. Explicit association rows rather than a
    # JSONB array of ids: readiness §12 requires "which report revision used
    # finding X?" to stay relationally answerable, and an array answers it only
    # with a scan and with no referential integrity. RESTRICT on the resource so a
    # published report cannot lose its evidence; CASCADE on the revision because
    # the link has no meaning without it. The composite primary key is the
    # uniqueness rule: one input appears at most once in one revision.
    for table_name, resource_column, resource_table, index_suffix in (
        (
            "ton_report_revision__analysis_run",
            "analysis_run_id",
            "ton_analysis_run",
            "run_id",
        ),
        (
            "ton_report_revision__occurrence",
            "occurrence_id",
            "ton_occurrence",
            "occurrence_id",
        ),
        ("ton_report_revision__finding", "finding_id", "ton_finding", "finding_id"),
        (
            "ton_report_revision__rule_version",
            "rule_version_id",
            "ton_rule_version",
            "rule_version_id",
        ),
        (
            "ton_report_revision__source_snapshot",
            "source_snapshot_id",
            "ton_source_snapshot",
            "snapshot_id",
        ),
    ):
        op.create_table(
            table_name,
            sa.Column(
                "report_revision_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column(resource_column, postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["report_revision_id"],
                ["ton_report_revision.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                [resource_column], [f"{resource_table}.id"], ondelete="RESTRICT"
            ),
            sa.PrimaryKeyConstraint("report_revision_id", resource_column),
        )
        op.create_index(
            f"ix_{table_name}_{index_suffix}", table_name, [resource_column]
        )

    # The fourth fail-closed ACL junction, shaped exactly like the three 003c
    # created. Restrictive, not additive: zero rows means DENIED.
    op.create_table(
        "ton_report__user_group",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["report_id"], ["ton_report.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_group_id"], ["user_group.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("report_id", "user_group_id"),
    )
    op.create_index(
        "ix_ton_report__user_group_group_id",
        "ton_report__user_group",
        ["user_group_id"],
    )

    op.create_table(
        "ton_audit_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audit_schema_version", sa.String(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Plain String, not Enum. See the module docstring.
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("ocsf_class", sa.String(), nullable=True),
        sa.Column("tenant_id", sa.String(), nullable=True),
        # The four AuditActor fields. SET NULL so removing an account never
        # deletes the audit row; the textual identity beside it keeps attribution
        # readable afterwards. actor_api_key_id is the key's id, never its value.
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(), nullable=True),
        sa.Column("actor_api_key_id", sa.String(), nullable=True),
        sa.Column("actor_auth_type", sa.String(), nullable=True),
        sa.Column(
            "resource_kind",
            sa.Enum(TonAuditResourceKind, native_enum=False),
            nullable=True,
        ),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        # No foreign key, deliberately. See the module docstring.
        sa.Column("domain_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("authorization_reference", sa.String(), nullable=True),
        sa.Column("endpoint", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("source_ip", sa.String(), nullable=True),
        # Before/after *metadata* for a manual correction or override — which
        # field changed and between which recorded values, not a copy of the row.
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column(
            "extra",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(resource_kind IS NULL) = (resource_id IS NULL)",
            name="ck_ton_audit_event_resource_reference_complete",
        ),
    )
    op.create_index(
        "ix_ton_audit_event_resource",
        "ton_audit_event",
        ["resource_kind", "resource_id"],
    )
    op.create_index("ix_ton_audit_event_action", "ton_audit_event", ["action"])
    op.create_index(
        "ix_ton_audit_event_actor_user_id", "ton_audit_event", ["actor_user_id"]
    )
    op.create_index(
        "ix_ton_audit_event_occurred_at", "ton_audit_event", ["occurred_at", "id"]
    )


def downgrade() -> None:
    # Reverse creation order. Indexes go with their tables, so DROP TABLE is
    # enough; only the 003d tables are touched, so every 003b and 003c structure
    # survives intact. No sequence is created by this revision, and no existing
    # column is altered in either direction.
    for table_name in reversed(TON_TABLES):
        op.drop_table(table_name)
