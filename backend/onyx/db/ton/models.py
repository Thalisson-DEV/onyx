"""TON domain tables — Plans 003b and 003c.

Plan 003b, the identity, rule and analysis spine:

* stable organizational identity — :class:`BusinessUnit`, :class:`Contract`;
* versioned deterministic rule definitions — :class:`Rule`,
  :class:`RuleVersion`;
* input provenance — :class:`SourceSnapshot`;
* execution envelopes — :class:`AnalysisRun`, :class:`AnalysisRunRuleVersion`,
  :class:`AnalysisRun__SourceSnapshot`;
* domain-scoped execution blocking — :class:`AnalysisStep`.

Plan 003c, the analytical result and business-case layer:

* immutable deterministic detections — :class:`Finding`;
* source provenance for a detection — :class:`FindingEvidence`;
* durable AI-interpretation attempts — :class:`FindingInterpretation`;
* the persistent §13.1 business ledger — :class:`Occurrence`;
* append-only lifecycle history — :class:`OccurrenceEvent`;
* financial and operational impact — :class:`OccurrenceImpact`;
* responsibility and deadline history — :class:`OccurrenceAssignment`;
* human commentary — :class:`OccurrenceNote`;
* the §15 handoff list — :class:`OccurrenceImpactedDomain`;
* fail-closed resource ACL — :class:`BusinessUnit__UserGroup`,
  :class:`Contract__UserGroup`, :class:`Occurrence__UserGroup`.

Deliberately absent, with the slice that owns them: TonReport,
TonReportRevision, ``TonReport__UserGroup`` and TonAuditEvent (003d);
ingestion (Plan 004); agents (Plan 005); scheduling (Plan 006).

Two invariants hold for every table here and must keep holding:

1. **No ``is_public`` column, anywhere.** ``Persona.is_public`` defaults to true
   and short-circuits the whole group ACL. Copying that would leak Vale Norte
   financial data, so the column is absent rather than defaulted false — a
   column that does not exist cannot be short-circuited by future code
   (readiness §10).
2. **No write path to any source system.** The advisory boundary of Prompt
   Mestre §12.1 is enforced by absence: there is no column and no function here
   that writes to an ERP, a measurement, a billing record or a glosa
   (readiness §9).

Table names carry a ``ton_`` prefix. The classes keep the readiness names. This
checkout tracks ``upstream/main``, and ``rule``, ``contract`` and
``business_unit`` are names upstream could plausibly take in the shared
``public`` schema; the prefix also matches the ``TonReport`` naming the
readiness gate already uses for 003d.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from onyx.db.models import Base
from onyx.db.ton.enums import (
    AnalysisRunErrorClass,
    AnalysisRunStatus,
    AnalysisSpecialist,
    AnalysisStepBlockedReason,
    AnalysisStepCode,
    AnalysisStepStatus,
    AnalysisTrigger,
    AssignmentStatus,
    BusinessUnitKind,
    ContractStatus,
    EvidenceConfidenceLevel,
    FindingKind,
    ImpactCategory,
    ImpactConfidence,
    ImpactMethod,
    InterpretationFailureClass,
    InterpretationInputScope,
    InterpretationStatus,
    MissingDataBehavior,
    OccurrenceActorKind,
    OccurrenceCriticality,
    OccurrenceLedgerKind,
    OccurrenceStatus,
    OccurrenceTransition,
    OccurrenceVerificationResult,
    PostResolutionPolicy,
    RedactionLevel,
    RuleDomain,
    RuleKind,
    RuleProvenance,
    RuleVersionOutcome,
    RuleVersionStatus,
    SourceType,
    TonSharePermission,
    UnitCostSource,
)

# Money and quantity columns. `asdecimal=True` is stated rather than relied on:
# every monetary value in this domain round-trips as a Python `Decimal`, and
# readiness §12 makes exact decimal serialisation the precondition for the 003d
# report hash. 20 integer digits and 10 fractional ones cover a consolidated
# figure and a per-unit reference cost in the same type.
#
# This is deliberately **not** the existing `Numeric(18, 6, asdecimal=False)`
# token-cost pattern: that returns a float, and a float round-trip through
# IEEE-754 would make a published number irreproducible. Prompt Mestre §6 exists
# because arithmetic in this data is already wrong by cents.
TON_AMOUNT = Numeric(30, 10, asdecimal=True)
# Percentages carry their own, smaller scale: a sensitivity of ±12.5% needs no
# ten decimal places, and a narrower type documents the intent.
TON_PERCENT = Numeric(9, 4, asdecimal=True)

# Human-facing occurrence identifier. A sequence rather than a Python counter:
# two concurrent detector workers must not compute the same short code, and a
# sequence is the only allocation that is safe without a lock. Attached to the
# metadata so `create_all` knows about it; the migration creates and drops it.
OCCURRENCE_SHORT_CODE_SEQUENCE = Sequence(
    "ton_occurrence_short_code_seq", metadata=Base.metadata
)
OCCURRENCE_SHORT_CODE_DEFAULT = text(
    "'OC-' || lpad(nextval('ton_occurrence_short_code_seq')::text, 6, '0')"
)


class BusinessUnit(Base):
    """A stable Vale Norte organizational or operational unit.

    Identity only. This is not the future business-unit master: no financials,
    no dotação, no headcount, no fleet sizing (readiness §15). No migration
    seeds any row — the membership of the operational, implantation and
    non-operational lists in Prompt Mestre §3.3 still needs owner validation.
    """

    __tablename__ = "ton_business_unit"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # The stable reference an owner recognises. Renaming a unit must not change
    # it, which is why it is separate from `name`.
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[BusinessUnitKind] = mapped_column(
        Enum(BusinessUnitKind, native_enum=False), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    # Opaque external reference. Never a parsed NG/Keevo key.
    external_ref: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Contract(Base):
    """Contract identity, as far as the already-specified rules need it.

    A Prompt Mestre §4 field is included only when a named S-rule or T-rule
    cannot be expressed without it. Two qualify: ``status`` (rule S7 excludes an
    unsigned contract from backlog, revenue and projection) and the vigência
    dates (T19 milestones). Economics, amendment economics, fleet and crew
    sizing, headcount, dotação, BDI, ABC curve, CCT, guarantees, penalties and
    the measurement and billing detail are all later slices (readiness §15).
    """

    __tablename__ = "ton_contract"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    # RESTRICT: a unit that still owns contracts must not disappear, and a
    # cascade here would silently delete contract identity.
    business_unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contracting_authority: Mapped[str] = mapped_column(String, nullable=False)
    # Nullable: a contract is often identified before its object summary is
    # captured, and inventing one would be worse than recording its absence.
    object_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nullable: a DRAFT, BIDDING or UNDER_JUDGEMENT contract has no vigência yet.
    start_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, native_enum=False), nullable=False
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_ton_contract_date_order",
        ),
        Index("ix_ton_contract_business_unit_id", "business_unit_id"),
        Index("ix_ton_contract_status", "status"),
    )


class Rule(Base):
    """The immutable spine of a business rule.

    Holds only what must never change. There is deliberately no threshold, no
    status, no effective date, no mutable title or description and no approval
    state: all of those live on :class:`RuleVersion`, so that activating a new
    threshold cannot reinterpret a historical analysis. A retired rule is a rule
    whose versions are all retired.

    ``code`` is the stable identifier (``T2``, ``S1``, ``FIN-TAX-01``). Prompt
    Mestre §7 forbids renaming it. No migration seeds a row: neither S1-S10 nor
    T1-T30 exists as data until an owner approves it, and the §8 T-code range
    (T13-T26 versus T13-T30) is still an open conflict.
    """

    __tablename__ = "ton_rule"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    domain: Mapped[RuleDomain] = mapped_column(
        Enum(RuleDomain, native_enum=False), nullable=False
    )
    kind: Mapped[RuleKind] = mapped_column(
        Enum(RuleKind, native_enum=False), nullable=False
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Provenance of the rule itself. SET NULL so removing an account never
    # deletes rule identity. No `updated_at`: this row is not meant to change.
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    # `passive_deletes` hands the cascade to the database. Without it the ORM
    # would try to null a NOT NULL `rule_id` when a rule is deleted.
    versions: Mapped[list[RuleVersion]] = relationship(
        "RuleVersion",
        back_populates="rule",
        order_by="RuleVersion.version",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_ton_rule_domain_kind", "domain", "kind"),)


class RuleVersion(Base):
    """One versioned, approvable configuration of a :class:`Rule`.

    This is where every mutable part of a business rule lives, as data. A
    threshold is a value in ``parameters``, never a column and never a
    constraint, which is exactly why the schema can exist before Vale Norte
    approves the numbers.

    Two guarantees matter most:

    * ``UNIQUE(rule_id, version)`` gives an ordered history, and historical
      consumers reference ``rule_version_id`` rather than ``rule_id``, so
      changing a threshold cannot rewrite what was already published;
    * ``ACTIVE`` requires ``approved_by`` and ``approved_at``, enforced by
      ``ck_ton_rule_version_active_requires_approval``. An unapproved number
      cannot reach production even by accident.
    """

    __tablename__ = "ton_rule_version"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # CASCADE: a version has no meaning without its rule. Deleting a rule that
    # any run actually used is still refused, by the RESTRICT on
    # ton_analysis_run_rule_version.rule_version_id.
    rule_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_rule.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Wording as of this version. Mutating a title means a new version.
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Names a deterministic executor, for example `deviation_vs_trailing_mean.v1`.
    # Never a Python import path, never serialised code, never a prompt.
    executor_key: Mapped[str] = mapped_column(String, nullable=False)
    # Thresholds, windows and tolerances. Monetary and percentage values are
    # decimal strings at the declared `scale`, never JSON floats: the
    # canonicalisation contract (readiness §12) depends on exact round-tripping.
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # Measurement contract. Deliberately plain strings, not enums: readiness
    # §23 still lists accepted units, currencies, rounding and precision as
    # pending owner approval, so freezing a vocabulary in code here would turn an
    # unresolved business decision into a schema constraint.
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    scale: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rounding_mode: Mapped[str | None] = mapped_column(String, nullable=True)

    # Units, nature groups and contract classes this version applies to.
    applicability: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # Nullable: a DRAFT is not in force yet, and an open-ended version has no end.
    effective_from: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[RuleVersionStatus] = mapped_column(
        Enum(RuleVersionStatus, native_enum=False),
        nullable=False,
        default=RuleVersionStatus.DRAFT,
        server_default=RuleVersionStatus.DRAFT.value,
    )

    # `PAD-CTRL-001 T2`, `Prompt Mestre §7`, `Relatorio 1.6`, a law reference.
    source_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    provenance: Mapped[RuleProvenance] = mapped_column(
        Enum(RuleProvenance, native_enum=False), nullable=False
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approval_reference: Mapped[str | None] = mapped_column(String, nullable=True)

    missing_data_behavior: Mapped[MissingDataBehavior] = mapped_column(
        Enum(MissingDataBehavior, native_enum=False), nullable=False
    )
    evidence_requirements: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # NOT NULL with no default: every version must state the §3.4 confidence
    # floor its findings need. There is no approved default to fall back on.
    min_confidence_level: Mapped[EvidenceConfidenceLevel] = mapped_column(
        Enum(EvidenceConfidenceLevel, native_enum=False), nullable=False
    )
    # Prompt Mestre §10 criticality bands. A value, not a column per band.
    severity_mapping: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    nc_code: Mapped[str | None] = mapped_column(String, nullable=True)

    # Dedup dimensions, drawn from `IdentityComponent`. Validated in
    # `onyx.db.ton.identity`; 003c consumes the contract to build identity keys.
    identity_components: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    post_resolution_policy: Mapped[PostResolutionPolicy] = mapped_column(
        Enum(PostResolutionPolicy, native_enum=False), nullable=False
    )
    # Tamper evidence over the canonical version definition. Nullable in 003b:
    # the canonical serialisation (`ton-canon-1`) is specified in readiness §12
    # but its implementation belongs to 003d, and writing a hash under a
    # different scheme now would make the recorded one meaningless.
    definition_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    rule: Mapped[Rule] = relationship("Rule", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("rule_id", "version", name="uq_ton_rule_version_rule_version"),
        # The gate that keeps a disputed number out of production. A database
        # property, not a review habit.
        CheckConstraint(
            "status <> 'ACTIVE' "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="ck_ton_rule_version_active_requires_approval",
        ),
        CheckConstraint(
            "effective_to IS NULL "
            "OR effective_from IS NULL "
            "OR effective_to >= effective_from",
            name="ck_ton_rule_version_effective_order",
        ),
        CheckConstraint("version >= 1", name="ck_ton_rule_version_positive"),
        Index("ix_ton_rule_version_rule_id", "rule_id"),
        Index("ix_ton_rule_version_status", "status"),
    )


class SourceSnapshot(Base):
    """A receipt for input material that was already extracted.

    Source-agnostic on purpose: it encodes no NG/Keevo schema, no field mapping,
    no transform definition and no scheduling. It records *that* an extraction
    happened, what it covered and what did not arrive. Ingestion itself belongs
    to Plan 004.

    Required in this slice for two reasons: without it a report is not
    reproducible, and rule S10 — no margin published on a reproved base — is not
    expressible.
    """

    __tablename__ = "ton_source_snapshot"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False), nullable=False
    )
    # Free text identifying the source, e.g. `DRE Gerencial 2026`.
    source_system_label: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Competência covered. Nullable: a contract PDF covers no period.
    period_start: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    units_covered: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Tamper evidence / version reference for the extraction.
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    # NOT NULL without a default, both of them: Prompt Mestre §5 Passo 1
    # requires the caller to state completeness rather than let it be assumed.
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    missing_inputs: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    # Drives the §3 `[fonte não padronizada]` label.
    is_schema_conformant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ingested_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_ton_source_snapshot_period_order",
        ),
        Index("ix_ton_source_snapshot_source_type", "source_type"),
        Index("ix_ton_source_snapshot_period", "period_start", "period_end"),
    )


class AnalysisRun(Base):
    """The execution and audit envelope for one analysis.

    Carries who or what asked for it, the scope analysed, the period, the
    outcome and the retry identity. It deliberately does **not** carry a
    resulting-finding array (findings point at the run), a report foreign key (a
    report references runs, not the reverse) or a ``schedule_id`` (Plan 006 owns
    ``AnalysisSchedule``; a nullable FK to a table that does not exist would be
    worse than ``routine_code``).

    Input provenance is not a JSONB blob here either. It is
    :class:`AnalysisRun__SourceSnapshot` rows, so "which runs used the April
    extract" is answerable in SQL.
    """

    __tablename__ = "ton_analysis_run"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trigger: Mapped[AnalysisTrigger] = mapped_column(
        Enum(AnalysisTrigger, native_enum=False), nullable=False
    )
    # NULL for a scheduled run. SET NULL so deleting an account never destroys
    # the audit envelope.
    triggered_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    # Prompt Mestre §12 routine identity (R1-R9). A string, not an enum: Plan
    # 006 owns the routine catalogue and its cadence.
    routine_code: Mapped[str | None] = mapped_column(String, nullable=True)
    specialist: Mapped[AnalysisSpecialist] = mapped_column(
        Enum(AnalysisSpecialist, native_enum=False), nullable=False
    )
    domain: Mapped[RuleDomain] = mapped_column(
        Enum(RuleDomain, native_enum=False), nullable=False
    )
    # NULL for corporate scope.
    business_unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # Competência analysed. Explicit, never derived from server local time.
    period_start: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    period_end: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[AnalysisRunStatus] = mapped_column(
        Enum(AnalysisRunStatus, native_enum=False),
        nullable=False,
        default=AnalysisRunStatus.QUEUED,
        server_default=AnalysisRunStatus.QUEUED.value,
    )
    # Nullable so a QUEUED run is representable honestly.
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Retry convergence. Without this, a Celery retry duplicates the envelope.
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    attempt_no: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    error_class: Mapped[AnalysisRunErrorClass | None] = mapped_column(
        Enum(AnalysisRunErrorClass, native_enum=False), nullable=True
    )
    # Code identity, for reproducibility.
    executor_version: Mapped[str] = mapped_column(String, nullable=False)
    # Roll-up over child findings. Findings arrive in 003c, so a 003b run stays
    # NOT_REQUIRED.
    interpretation_status: Mapped[InterpretationStatus] = mapped_column(
        Enum(InterpretationStatus, native_enum=False),
        nullable=False,
        default=InterpretationStatus.NOT_REQUIRED,
        server_default=InterpretationStatus.NOT_REQUIRED.value,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # All three use `passive_deletes`: the database already cascades from
    # `ton_analysis_run`, and letting the ORM re-do it would only add a load and
    # a round trip per child.
    steps: Mapped[list[AnalysisStep]] = relationship(
        "AnalysisStep",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="AnalysisStep.analysis_run_id",
    )
    rule_versions: Mapped[list[AnalysisRunRuleVersion]] = relationship(
        "AnalysisRunRuleVersion",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    source_snapshot_links: Mapped[list[AnalysisRun__SourceSnapshot]] = relationship(
        "AnalysisRun__SourceSnapshot",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "period_end >= period_start", name="ck_ton_analysis_run_period_order"
        ),
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NOT NULL",
            name="ck_ton_analysis_run_finished_requires_start",
        ),
        CheckConstraint("attempt_no >= 1", name="ck_ton_analysis_run_attempt_positive"),
        Index("ix_ton_analysis_run_scope", "domain", "business_unit_id"),
        Index("ix_ton_analysis_run_status", "status"),
        Index("ix_ton_analysis_run_period", "period_start", "period_end"),
    )


class AnalysisRunRuleVersion(Base):
    """Which rule versions participated in a run, and what became of each.

    Recording the skipped rules with their reason is the point. A report is only
    reproducible if it can say which rules ran *and* which did not, and why.

    ``rule_version_id`` uses ``RESTRICT``: a version that took part in an
    analysis must not be deletable, or the audit trail would develop holes.
    There is no ``Finding`` foreign key here — ``finding_count`` is a plain
    counter, because Finding does not exist until 003c.
    """

    __tablename__ = "ton_analysis_run_rule_version"

    analysis_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_analysis_run.id", ondelete="CASCADE"),
        primary_key=True,
    )
    rule_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_rule_version.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    outcome: Mapped[RuleVersionOutcome] = mapped_column(
        Enum(RuleVersionOutcome, native_enum=False), nullable=False
    )
    finding_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analysis_run: Mapped[AnalysisRun] = relationship(
        "AnalysisRun", back_populates="rule_versions"
    )
    rule_version: Mapped[RuleVersion] = relationship("RuleVersion")

    __table_args__ = (
        CheckConstraint(
            "finding_count >= 0", name="ck_ton_analysis_run_rule_version_count"
        ),
        # A skipped or errored rule produced nothing. Keeps the counter honest
        # before Finding exists to cross-check it.
        CheckConstraint(
            "outcome = 'EXECUTED' OR finding_count = 0",
            name="ck_ton_analysis_run_rule_version_skipped_has_no_findings",
        ),
        Index(
            "ix_ton_analysis_run_rule_version_rule_version_id",
            "rule_version_id",
        ),
    )


class AnalysisRun__SourceSnapshot(Base):
    """Which source snapshots fed a run.

    An explicit association rather than one opaque JSON blob on the run, so that
    "which analyses used snapshot X?" is a relational question. ``RESTRICT`` on
    the snapshot side keeps the provenance chain intact.
    """

    __tablename__ = "ton_analysis_run__source_snapshot"

    analysis_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_analysis_run.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_source_snapshot.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analysis_run: Mapped[AnalysisRun] = relationship(
        "AnalysisRun", back_populates="source_snapshot_links"
    )
    source_snapshot: Mapped[SourceSnapshot] = relationship("SourceSnapshot")

    __table_args__ = (
        # The composite primary key already indexes (run, snapshot); this is the
        # reverse direction, which is the question the association exists for.
        Index(
            "ix_ton_analysis_run__source_snapshot_snapshot_id",
            "source_snapshot_id",
        ),
    )


class AnalysisStep(Base):
    """One step of the Prompt Mestre §5 protocol, in one scope.

    This is where blocking lives, and the scope is the triple
    ``(step_code, domain, business_unit_id)`` — never the run. A financial base
    failure in Mossoró blocks financial detection and publication in Mossoró; it
    leaves fleet, contracts and HR in Mossoró alone, and it leaves financial
    analysis in Itabirito alone. The run then ends
    ``COMPLETED_WITH_BLOCKED_DOMAINS``, not ``FAILED``.

    ``domain`` and ``business_unit_id`` are nullable, and ``NULL`` means
    run-wide. Blocking propagates only from a wider or equal scope to a narrower
    or equal one; :mod:`onyx.db.ton.analysis_steps` refuses anything else.

    ``ck_ton_analysis_step_blocked_requires_cause`` makes the rule structural: a
    BLOCKED step always names both the step that caused it and a reason from the
    closed vocabulary. There is no silent blocking.

    This is not a workflow engine and must not become one. The seven step codes
    and their order are fixed; retry, scheduling and dependency dispatch belong
    to Plan 006.
    """

    __tablename__ = "ton_analysis_step"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_analysis_run.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_code: Mapped[AnalysisStepCode] = mapped_column(
        Enum(AnalysisStepCode, native_enum=False), nullable=False
    )
    # NULL means run-wide rather than "unknown".
    domain: Mapped[RuleDomain | None] = mapped_column(
        Enum(RuleDomain, native_enum=False), nullable=True
    )
    business_unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[AnalysisStepStatus] = mapped_column(
        Enum(AnalysisStepStatus, native_enum=False),
        nullable=False,
        default=AnalysisStepStatus.PENDING,
        server_default=AnalysisStepStatus.PENDING.value,
    )
    # CASCADE: cause and consequence live and die with the same run, and a
    # dangling cause would leave a BLOCKED row that cannot explain itself.
    blocked_by_step_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_analysis_step.id", ondelete="CASCADE"),
        nullable=True,
    )
    blocked_reason: Mapped[AnalysisStepBlockedReason | None] = mapped_column(
        Enum(AnalysisStepBlockedReason, native_enum=False), nullable=True
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    analysis_run: Mapped[AnalysisRun] = relationship(
        "AnalysisRun", back_populates="steps", foreign_keys=[analysis_run_id]
    )
    blocked_by_step: Mapped[AnalysisStep | None] = relationship(
        "AnalysisStep", remote_side=[id], foreign_keys=[blocked_by_step_id]
    )

    __table_args__ = (
        CheckConstraint(
            "status <> 'BLOCKED' "
            "OR (blocked_by_step_id IS NOT NULL AND blocked_reason IS NOT NULL)",
            name="ck_ton_analysis_step_blocked_requires_cause",
        ),
        CheckConstraint(
            "blocked_by_step_id IS NULL OR blocked_by_step_id <> id",
            name="ck_ton_analysis_step_no_self_block",
        ),
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NOT NULL",
            name="ck_ton_analysis_step_finished_requires_start",
        ),
        # One row per (run, step, domain, unit). `nulls_not_distinct` is what
        # makes the run-wide scope (both NULL) unique too — Postgres would
        # otherwise treat every NULL as distinct and allow duplicates.
        Index(
            "uq_ton_analysis_step_scope",
            "analysis_run_id",
            "step_code",
            "domain",
            "business_unit_id",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_ton_analysis_step_run_status", "analysis_run_id", "status"),
        Index("ix_ton_analysis_step_blocked_by", "blocked_by_step_id"),
    )


# ---------------------------------------------------------------------------
# Plan 003c — findings, occurrences, evidence, interpretation and resource ACL.
# ---------------------------------------------------------------------------


class Occurrence(Base):
    """One persistent business case — the Prompt Mestre §13.1 ledger row.

    The user-facing entity. :class:`Finding` is the internal detection evidence
    that feeds it; the UI, the API and the report vocabulary say *occurrence*
    (readiness §6). Many findings point at one occurrence, and the occurrence is
    what carries a lifecycle.

    Three properties are load-bearing:

    * ``UNIQUE(identity_key)`` is the deduplication boundary. Application-level
      pre-checks are insufficient, so the database is the authority: two
      concurrent detector workers converge on one row (readiness §7).
    * ``status`` and ``open_cycle_count`` are **cached projections** of
      :class:`OccurrenceEvent` history. :mod:`onyx.db.ton.occurrences` is the
      only writer, and a named test asserts the stored value equals the
      event-derived one.
    * ``requires_human_closure`` is a database property, not a UI habit:
      ``ck_ton_occurrence_critical_requires_human_closure`` makes it true
      whenever ``criticality`` is ``CRITICAL``, and the only transition that can
      resolve such a case is ``RESOLVE_CRITICAL``, which the event table forces
      to carry an identified user and an authorization reference.

    There is no ``is_public`` column, and no column that writes to a source
    system. Both absences are asserted by inverse tests.

    **Supersede and uniqueness.** Readiness §7 requires both ``UNIQUE(identity_key)``
    and ``SUPERSEDE_WITH_NEW_OCCURRENCE``, which are only simultaneously
    satisfiable if the superseding case's canonical tuple differs. So
    ``logical_identity_key`` is the generation-free digest that identifies the
    logical case across its whole lineage, ``supersede_generation`` counts the
    supersessions, and ``identity_key`` is the digest of the canonical tuple
    including that generation. For generation 1 — every case that was never
    superseded — the two keys are equal, enforced by
    ``ck_ton_occurrence_first_generation_identity``.
    """

    __tablename__ = "ton_occurrence"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Human-facing reference. Sequence-allocated server-side; see
    # OCCURRENCE_SHORT_CODE_SEQUENCE for why it is not computed in Python.
    short_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        server_default=OCCURRENCE_SHORT_CODE_DEFAULT,
    )
    # The deduplication boundary. An opaque deterministic digest of the canonical
    # tuple declared by RuleVersion.identity_components — never a title, never a
    # description, never model output. See onyx.db.ton.identity.
    identity_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    # The same digest without the supersede generation: the lineage key. Indexed,
    # not unique, because a superseded case and its successor share it.
    logical_identity_key: Mapped[str] = mapped_column(String, nullable=False)
    supersede_generation: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )

    # RESTRICT on both: an occurrence names the rule that found it and the
    # version in force, and neither may vanish from under a published case.
    rule_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_rule.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # The version currently attributed to the case. Changing it is what triggers
    # forced supersede on recurrence: two detections under different thresholds
    # are not the same measurement (readiness §7, mirroring rule S9).
    current_rule_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_rule_version.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # §15 handoff rule: exactly one domain owns the case, recorded at the link
    # where the quantity changed. Other affected domains are listed in
    # OccurrenceImpactedDomain rather than duplicated as extra occurrences.
    owning_domain: Mapped[RuleDomain] = mapped_column(
        Enum(RuleDomain, native_enum=False), nullable=False
    )
    ledger_kind: Mapped[OccurrenceLedgerKind] = mapped_column(
        Enum(OccurrenceLedgerKind, native_enum=False), nullable=False
    )
    criticality: Mapped[OccurrenceCriticality] = mapped_column(
        Enum(OccurrenceCriticality, native_enum=False), nullable=False
    )
    # Pinned from the rule version at detection time. Nullable: not every rule
    # maps to an NC code, and the NC catalogue is still owner-validated.
    nc_code: Mapped[str | None] = mapped_column(String, nullable=True)

    # Both nullable by readiness §15: a corporate finding has no unit, and a
    # finding may precede contract identification.
    business_unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
        nullable=True,
    )
    contract_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_contract.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Deterministic, caller-supplied. Never an identity input: a named test
    # asserts identity_key is unchanged when the title changes.
    title: Mapped[str] = mapped_column(String, nullable=False)

    status: Mapped[OccurrenceStatus] = mapped_column(
        Enum(OccurrenceStatus, native_enum=False),
        nullable=False,
        default=OccurrenceStatus.NEW,
        server_default=OccurrenceStatus.NEW.value,
    )
    first_detected_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_detected_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Projections over the event history. `detection_count` counts every event
    # that carries a finding — DETECT, REPEAT_DETECTED and REOPENED —, while
    # `open_cycle_count` counts DETECT and REOPENED and so drives the §10
    # escalation rule: two repeats inside one open cycle are not two cycles.
    detection_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    open_cycle_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # §5 Passo 7: publishing a finding includes defining how it will be verified.
    verification_criterion: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_result: Mapped[OccurrenceVerificationResult | None] = mapped_column(
        Enum(OccurrenceVerificationResult, native_enum=False), nullable=True
    )
    verification_checked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # §16: TON records the flag and stops. It never reaches a legal conclusion,
    # and there is no column here that could hold one.
    legal_review_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    requires_human_closure: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # SET NULL rather than CASCADE: losing the successor must not delete the
    # superseded case, which is the record of what was measured before.
    superseded_by_occurrence_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_occurrence.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    rule: Mapped[Rule] = relationship("Rule")
    current_rule_version: Mapped[RuleVersion] = relationship("RuleVersion")
    # `passive_deletes` throughout: the database already cascades the aggregate,
    # and letting the ORM re-do it would add a load per child.
    findings: Mapped[list[Finding]] = relationship(
        "Finding",
        back_populates="occurrence",
        order_by="Finding.detected_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    events: Mapped[list[OccurrenceEvent]] = relationship(
        "OccurrenceEvent",
        back_populates="occurrence",
        order_by="OccurrenceEvent.sequence_no",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    impacts: Mapped[list[OccurrenceImpact]] = relationship(
        "OccurrenceImpact",
        back_populates="occurrence",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    assignments: Mapped[list[OccurrenceAssignment]] = relationship(
        "OccurrenceAssignment",
        back_populates="occurrence",
        order_by="OccurrenceAssignment.sequence_no",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notes: Mapped[list[OccurrenceNote]] = relationship(
        "OccurrenceNote",
        back_populates="occurrence",
        order_by="OccurrenceNote.sequence_no",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    impacted_domains: Mapped[list[OccurrenceImpactedDomain]] = relationship(
        "OccurrenceImpactedDomain",
        back_populates="occurrence",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    group_shares: Mapped[list[Occurrence__UserGroup]] = relationship(
        "Occurrence__UserGroup",
        back_populates="occurrence",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "logical_identity_key",
            "supersede_generation",
            name="uq_ton_occurrence_lineage_generation",
        ),
        CheckConstraint(
            "supersede_generation >= 1", name="ck_ton_occurrence_generation_positive"
        ),
        # A case that was never superseded carries the pure canonical digest, so
        # the common path is exactly the readiness §7 contract.
        CheckConstraint(
            "supersede_generation > 1 OR identity_key = logical_identity_key",
            name="ck_ton_occurrence_first_generation_identity",
        ),
        CheckConstraint(
            "last_detected_at >= first_detected_at",
            name="ck_ton_occurrence_detection_order",
        ),
        CheckConstraint(
            "detection_count >= 1", name="ck_ton_occurrence_detection_count_positive"
        ),
        CheckConstraint(
            "open_cycle_count >= 1", name="ck_ton_occurrence_open_cycle_positive"
        ),
        CheckConstraint(
            "status <> 'RESOLVED' OR resolved_at IS NOT NULL",
            name="ck_ton_occurrence_resolved_requires_timestamp",
        ),
        # Readiness §9: a critical occurrence requires human closure. TON may
        # propose actions; it may not close this case on its own.
        CheckConstraint(
            "criticality <> 'CRITICAL' OR requires_human_closure",
            name="ck_ton_occurrence_critical_requires_human_closure",
        ),
        CheckConstraint(
            "superseded_by_occurrence_id IS NULL OR superseded_by_occurrence_id <> id",
            name="ck_ton_occurrence_no_self_supersede",
        ),
        CheckConstraint(
            "verification_result IS NULL OR verification_checked_at IS NOT NULL",
            name="ck_ton_occurrence_verification_requires_timestamp",
        ),
        Index("ix_ton_occurrence_logical_identity", "logical_identity_key"),
        Index("ix_ton_occurrence_status_criticality", "status", "criticality"),
        Index("ix_ton_occurrence_scope", "owning_domain", "business_unit_id"),
        Index("ix_ton_occurrence_contract_id", "contract_id"),
        Index("ix_ton_occurrence_rule_id", "rule_id"),
        # The stable list order the frontend needs: `last_detected_at` alone is
        # not a total order, so `id` is the tiebreaker (readiness §22).
        Index("ix_ton_occurrence_last_detected", "last_detected_at", "id"),
    )


class Finding(Base):
    """One immutable deterministic detection.

    Append-only analytical output, not business state. It pins the analysis run,
    the **rule version** (never merely the rule) and the identity key, so a later
    threshold change cannot reinterpret what was already detected.

    ``UNIQUE(analysis_run_id, rule_version_id, identity_key)`` makes retrying a
    detection inside the same logical analysis idempotent.

    Deliberately absent: any lifecycle status. There is no ``RESOLVED`` here —
    resolution belongs to :class:`Occurrence`, narrative belongs to
    :class:`FindingInterpretation`. ``interpretation_status`` is the one mutable
    column, and it tracks the interpretation attempt rather than the business
    case.

    A ``BLIND_SPOT`` finding is valid with no numeric value and no evidence row.
    That is the whole point of Prompt Mestre §11: a data gap is a first-class
    finding, so nothing here requires a number.

    **No ACL junction.** Visibility derives from the owning occurrence and its
    organizational context (readiness §10). Two independent ACLs over one
    analytical case would eventually disagree.
    """

    __tablename__ = "ton_finding"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # RESTRICT: a run that produced findings is part of the audit chain and must
    # stay referenceable, exactly as ton_analysis_run_rule_version does.
    analysis_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_analysis_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # The version, never the rule. This is what stops a threshold change from
    # rewriting history, and a schema test asserts no `rule_id` column exists.
    rule_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_rule_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # CASCADE: a finding has no meaning without its case. Deleting a case is a
    # global-authority act (see onyx.db.ton.acl), not a routine operation.
    occurrence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_occurrence.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The occurrence's effective identity key, so a retry inside one run cannot
    # produce a second finding for the same case generation.
    identity_key: Mapped[str] = mapped_column(String, nullable=False)
    finding_kind: Mapped[FindingKind] = mapped_column(
        Enum(FindingKind, native_enum=False), nullable=False
    )
    interpretation_status: Mapped[InterpretationStatus] = mapped_column(
        Enum(InterpretationStatus, native_enum=False),
        nullable=False,
        default=InterpretationStatus.NOT_REQUIRED,
        server_default=InterpretationStatus.NOT_REQUIRED.value,
    )

    domain: Mapped[RuleDomain] = mapped_column(
        Enum(RuleDomain, native_enum=False), nullable=False
    )
    business_unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_business_unit.id", ondelete="RESTRICT"),
        nullable=True,
    )
    contract_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_contract.id", ondelete="RESTRICT"),
        nullable=True,
    )
    detected_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Competência the detection covers. Nullable: a contract-document finding
    # covers no accounting period.
    period_start: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)

    # The deterministic measurement. All nullable because a BLIND_SPOT has none.
    # No interpreter may change these: FindingInterpretation holds no write path
    # to them, asserted by test.
    expected_value: Mapped[Decimal | None] = mapped_column(TON_AMOUNT, nullable=True)
    actual_value: Mapped[Decimal | None] = mapped_column(TON_AMOUNT, nullable=True)
    deviation_value: Mapped[Decimal | None] = mapped_column(TON_AMOUNT, nullable=True)
    computed_impact_amount: Mapped[Decimal | None] = mapped_column(
        TON_AMOUNT, nullable=True
    )
    value_scale: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    value_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # Remaining deterministic outputs of the executor, as decimal strings rather
    # than JSON numbers (readiness §12 rule 1). A JSONB field instead of a column
    # per rule shape: eight executor shapes cover forty tests, and their outputs
    # differ.
    deterministic_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # Pinned from the rule version at detection time, so a later NC remap cannot
    # relabel a published detection.
    nc_code: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    occurrence: Mapped[Occurrence] = relationship(
        "Occurrence", back_populates="findings"
    )
    rule_version: Mapped[RuleVersion] = relationship("RuleVersion")
    evidence: Mapped[list[FindingEvidence]] = relationship(
        "FindingEvidence",
        back_populates="finding",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    interpretations: Mapped[list[FindingInterpretation]] = relationship(
        "FindingInterpretation",
        back_populates="finding",
        order_by="FindingInterpretation.attempt_no",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # Readiness §7: a rerun of the same logical analysis is idempotent.
        UniqueConstraint(
            "analysis_run_id",
            "rule_version_id",
            "identity_key",
            name="uq_ton_finding_run_rule_version_identity",
        ),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_ton_finding_period_order",
        ),
        Index("ix_ton_finding_occurrence_id", "occurrence_id"),
        Index("ix_ton_finding_identity_key", "identity_key"),
        Index("ix_ton_finding_rule_version_id", "rule_version_id"),
        Index("ix_ton_finding_interpretation_status", "interpretation_status"),
        Index("ix_ton_finding_scope", "domain", "business_unit_id"),
    )


class FindingEvidence(Base):
    """A pointer to the source material behind a detection.

    Source-agnostic by construction. ``locator`` is the single generic field that
    lets one table serve spreadsheets, PDFs, document chunks, manual entries and
    computed aggregates: it may carry ``page``, ``sheet``, ``row``, ``column``,
    ``cell``, ``chunk_id``, ``char_span`` or ``line``. There is deliberately no
    ``ng_account_id`` and no ``keevo_document_number`` — this is a pointer, not
    an ETL schema, and NG/Keevo field mapping stays BLOCKED under D-009.

    ``confidence_level`` is NOT NULL. Prompt Mestre §3.4 makes a published number
    without its A/B/C/D level a defect. Confidence is per source and immutable:
    nothing aggregates D evidence into A.

    ``extracted_value`` is a decimal **string**, not a numeric column. It records
    what the source said, at the source's own scale, without a float round-trip
    (readiness §12 and §14).
    """

    __tablename__ = "ton_finding_evidence"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finding_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_finding.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Nullable: a BLIND_SPOT records the absence of a source, and a manual entry
    # or a computed aggregate may have no extraction receipt. RESTRICT keeps the
    # provenance chain intact where one does exist.
    source_snapshot_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_source_snapshot.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False), nullable=False
    )
    confidence_level: Mapped[EvidenceConfidenceLevel] = mapped_column(
        Enum(EvidenceConfidenceLevel, native_enum=False), nullable=False
    )
    # Opaque source row key. Never a parsed NG/Keevo column name.
    record_key: Mapped[str | None] = mapped_column(String, nullable=True)
    locator: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # Links into existing Onyx storage. SET NULL on all three: losing the stored
    # artifact must not delete the record that it was cited.
    file_record_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("file_record.file_id", ondelete="SET NULL"), nullable=True
    )
    document_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )
    chat_message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_message.id", ondelete="SET NULL"), nullable=True
    )

    extracted_value: Mapped[str | None] = mapped_column(String, nullable=True)
    value_scale: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    value_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # Renders the Prompt Mestre §3 `[fonte não padronizada]` label.
    is_non_standard_source: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # NOT NULL with no default: the writer states how much identity this row
    # carries rather than letting it be assumed (readiness §9).
    redaction_level: Mapped[RedactionLevel] = mapped_column(
        Enum(RedactionLevel, native_enum=False), nullable=False
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    finding: Mapped[Finding] = relationship("Finding", back_populates="evidence")
    source_snapshot: Mapped[SourceSnapshot | None] = relationship("SourceSnapshot")

    __table_args__ = (
        Index("ix_ton_finding_evidence_finding_id", "finding_id"),
        Index("ix_ton_finding_evidence_source_snapshot_id", "source_snapshot_id"),
    )


class FindingInterpretation(Base):
    """One AI-interpretation attempt against one finding. Append-only.

    A row per attempt, never an update: a retry appends
    ``attempt_no + 1`` so a provider failure stays visible next to the eventual
    success. ``FAILED`` is durable and operator-visible, and
    ``ck_ton_finding_interpretation_completed_has_summary`` stops a failure being
    laundered into an empty success.

    **Proposals only.** ``proposed_criticality`` and ``proposed_nc_code`` change
    nothing by themselves. Promoting one is a separate ``PROMOTE_INTERPRETATION``
    transition that the event table forces to carry an identified user and an
    authorization reference.

    **What is never stored:** no chain-of-thought, no hidden reasoning, no raw
    prompt body, no raw response transcript. Only the business-facing
    interpretation plus the provenance needed to reproduce the call *shape* —
    provider, model, prompt key and version. An inverse test asserts no column
    name here could hold a transcript.
    """

    __tablename__ = "ton_finding_interpretation"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finding_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_finding.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InterpretationStatus] = mapped_column(
        Enum(InterpretationStatus, native_enum=False), nullable=False
    )

    # Provenance, not content. Nullable because a PENDING attempt is committed
    # before the provider is contacted, and a COMPLETED one must have them
    # (ck_ton_finding_interpretation_completed_has_provenance).
    llm_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    # Reproducibility without storing the prompt body.
    prompt_key: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)

    # The business-facing output. Nothing here is an identity input.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    probable_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    proposed_criticality: Mapped[OccurrenceCriticality | None] = mapped_column(
        Enum(OccurrenceCriticality, native_enum=False), nullable=True
    )
    proposed_nc_code: Mapped[str | None] = mapped_column(String, nullable=True)

    # Which evidence rows were shown, as a list of FindingEvidence ids.
    evidence_reference_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    input_scope: Mapped[InterpretationInputScope] = mapped_column(
        Enum(InterpretationInputScope, native_enum=False), nullable=False
    )

    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_class: Mapped[InterpretationFailureClass | None] = mapped_column(
        Enum(InterpretationFailureClass, native_enum=False), nullable=True
    )
    # Explicit, never inferred from the failure class.
    retry_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    finding: Mapped[Finding] = relationship("Finding", back_populates="interpretations")

    __table_args__ = (
        UniqueConstraint(
            "finding_id", "attempt_no", name="uq_ton_finding_interpretation_attempt"
        ),
        CheckConstraint(
            "attempt_no >= 1", name="ck_ton_finding_interpretation_attempt_positive"
        ),
        # A failure names its class, and only a failure carries one.
        CheckConstraint(
            "status <> 'FAILED' OR failure_class IS NOT NULL",
            name="ck_ton_finding_interpretation_failed_has_class",
        ),
        CheckConstraint(
            "failure_class IS NULL OR status = 'FAILED'",
            name="ck_ton_finding_interpretation_class_only_on_failure",
        ),
        # The invariant that keeps a provider failure from becoming an empty
        # success: a COMPLETED attempt must actually carry an interpretation.
        CheckConstraint(
            "status <> 'COMPLETED' "
            "OR (summary IS NOT NULL AND finished_at IS NOT NULL)",
            name="ck_ton_finding_interpretation_completed_has_summary",
        ),
        CheckConstraint(
            "status <> 'COMPLETED' "
            "OR (llm_provider IS NOT NULL AND model_name IS NOT NULL)",
            name="ck_ton_finding_interpretation_completed_has_provenance",
        ),
        CheckConstraint(
            "finished_at IS NULL OR status IN ('COMPLETED', 'FAILED')",
            name="ck_ton_finding_interpretation_finished_is_terminal",
        ),
        Index("ix_ton_finding_interpretation_finding_id", "finding_id"),
        # Not `ix_ton_finding_interpretation_status`: that name already indexes
        # `ton_finding.interpretation_status`, and index names are unique per
        # schema in PostgreSQL.
        Index("ix_ton_finding_interpretation_attempt_status", "status"),
    )


class OccurrenceEvent(Base):
    """The authoritative lifecycle history of one occurrence. Append-only.

    ``Occurrence.status`` and ``Occurrence.open_cycle_count`` are projections
    maintained *from* these rows. Replacing immutable history with mutable status
    updates alone is the failure mode this table exists to prevent, so the event
    is written in the same transaction as the projection update and a failure to
    persist it fails the business operation.

    The human-decision boundary of Prompt Mestre §12.1 is a database property
    here, not a UI convention:

    * ``ck_ton_occurrence_event_human_only_transitions`` — the six readiness §9
      transitions require ``actor_kind = USER``, an identified
      ``actor_user_id`` and an ``authorization_reference``;
    * ``ck_ton_occurrence_event_resolution_requires_user`` — closing a case
      requires an identified user even when no separate authorization is
      recorded;
    * ``ck_ton_occurrence_event_user_actor_identified`` — a ``USER`` actor is
      always identified, so ``SYSTEM`` cannot masquerade as a person.

    ``actor_user_id`` uses ``ON DELETE RESTRICT``, unlike every other user
    reference in the TON schema. The readiness §9 CHECK requires the column to be
    non-null for an authorized decision, and ``SET NULL`` would quietly void that
    guarantee the first time an account was deleted. An account that authorized a
    human-only TON decision therefore stays referenceable; deactivate it instead
    of deleting it.
    """

    __tablename__ = "ton_occurrence_event"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    occurrence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_occurrence.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Dense per-occurrence ordering, so the history has one canonical replay
    # order independent of clock skew between workers.
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    transition: Mapped[OccurrenceTransition] = mapped_column(
        Enum(OccurrenceTransition, native_enum=False), nullable=False
    )
    # The occurrence status after this event. Recorded rather than only derived,
    # so the projection can be checked against history without replaying the
    # transition table.
    resulting_status: Mapped[OccurrenceStatus] = mapped_column(
        Enum(OccurrenceStatus, native_enum=False), nullable=False
    )

    actor_kind: Mapped[OccurrenceActorKind] = mapped_column(
        Enum(OccurrenceActorKind, native_enum=False), nullable=False
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # The record of authority for a human-only decision — an ata reference, a
    # ticket, a deliberation id. Free text on purpose: TON does not own the
    # governance system that issues it.
    authorization_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # Which detection and which threshold were in force. SET NULL / RESTRICT
    # respectively: the finding may be superseded, the version may not vanish.
    finding_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_finding.id", ondelete="SET NULL"),
        nullable=True,
    )
    rule_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_rule_version.id", ondelete="RESTRICT"),
        nullable=True,
    )

    occurred_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    occurrence: Mapped[Occurrence] = relationship("Occurrence", back_populates="events")

    __table_args__ = (
        UniqueConstraint(
            "occurrence_id", "sequence_no", name="uq_ton_occurrence_event_sequence"
        ),
        CheckConstraint(
            "sequence_no >= 1", name="ck_ton_occurrence_event_sequence_positive"
        ),
        # Readiness §9, verbatim. The six transitions Prompt Mestre §12.1 reserves
        # for a human cannot be written by a system actor at all.
        CheckConstraint(
            "transition NOT IN ("
            "'RESOLVE_CRITICAL', 'ACCEPT_RISK', 'DISMISS', "
            "'ASSERT_NONCOMPLIANCE', 'PROMOTE_INTERPRETATION', "
            "'OVERRIDE_DETERMINISTIC_VALUE') "
            "OR (actor_kind = 'USER' AND actor_user_id IS NOT NULL "
            "AND authorization_reference IS NOT NULL)",
            name="ck_ton_occurrence_event_human_only_transitions",
        ),
        # Closing a case is not in §12.1's autonomous list either, so it needs an
        # identified person even without a separate authorization record.
        CheckConstraint(
            "transition <> 'RESOLVED' "
            "OR (actor_kind = 'USER' AND actor_user_id IS NOT NULL)",
            name="ck_ton_occurrence_event_resolution_requires_user",
        ),
        CheckConstraint(
            "actor_kind <> 'USER' OR actor_user_id IS NOT NULL",
            name="ck_ton_occurrence_event_user_actor_identified",
        ),
        Index("ix_ton_occurrence_event_occurrence_id", "occurrence_id"),
        Index("ix_ton_occurrence_event_transition", "transition"),
        Index("ix_ton_occurrence_event_actor_user_id", "actor_user_id"),
    )


class OccurrenceImpact(Base):
    """One quantification of an occurrence, per Prompt Mestre §9.

    Normalised out of the ledger because §9 requires a category, a confidence
    level, a method, a named reference unit-cost source, a premise and a
    sensitivity — and because an impact is re-estimated as better data arrives.
    Several rows per occurrence are expected: a monthly and an annual view, a
    predicted and a later verified figure.

    ``unit_cost_source`` is NOT NULL because §9 says "diga sempre qual usou".
    ``NOT_APPLICABLE`` is available for a method that uses no reference unit cost
    and is refused for the §9 formula itself.

    ``realized_amount`` requires ``verified_at``: §13.3 counts only verified
    savings as realised, and that is enforced here rather than left to the
    aggregation. **There is no ROI table.** Realised ROI is a later derived
    aggregation over these rows, filtered by verification state and by
    ``confidence <> 'BAIXA'``.

    Every amount is ``Numeric(30, 10)`` with ``asdecimal=True``. No column here
    is a float.
    """

    __tablename__ = "ton_occurrence_impact"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    occurrence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_occurrence.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[ImpactCategory] = mapped_column(
        Enum(ImpactCategory, native_enum=False), nullable=False
    )
    confidence: Mapped[ImpactConfidence] = mapped_column(
        Enum(ImpactConfidence, native_enum=False), nullable=False
    )
    method: Mapped[ImpactMethod] = mapped_column(
        Enum(ImpactMethod, native_enum=False), nullable=False
    )
    unit_cost_source: Mapped[UnitCostSource] = mapped_column(
        Enum(UnitCostSource, native_enum=False), nullable=False
    )

    predicted_amount: Mapped[Decimal | None] = mapped_column(TON_AMOUNT, nullable=True)
    realized_amount: Mapped[Decimal | None] = mapped_column(TON_AMOUNT, nullable=True)
    # The two factors of the §9 formula, kept so a reviewer can recompute the
    # amount instead of trusting it.
    quantity: Mapped[Decimal | None] = mapped_column(TON_AMOUNT, nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(TON_AMOUNT, nullable=True)

    # NOT NULL: an amount without a currency and a scale is not a publishable
    # number. No currency is defaulted — the deployment's accepted currency list
    # is still owner-approved (readiness §23).
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    scale: Mapped[int] = mapped_column(Integer, nullable=False)

    verified_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    # §9: "Estimativa é sempre rotulada. premissa: [x]; sensibilidade: ±[y]%."
    premise: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity_pct: Mapped[Decimal | None] = mapped_column(TON_PERCENT, nullable=True)

    # Which period the amount refers to, so a monthly and an annual figure are
    # two rows rather than two columns.
    period_start: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    occurrence: Mapped[Occurrence] = relationship(
        "Occurrence", back_populates="impacts"
    )

    __table_args__ = (
        # §13.3: only a verified saving is realised.
        CheckConstraint(
            "realized_amount IS NULL OR verified_at IS NOT NULL",
            name="ck_ton_occurrence_impact_realized_requires_verification",
        ),
        CheckConstraint(
            "predicted_amount IS NOT NULL OR realized_amount IS NOT NULL",
            name="ck_ton_occurrence_impact_has_an_amount",
        ),
        # §9's formula must name a real reference cost; the escape hatch exists
        # only for the methods that use none.
        CheckConstraint(
            "method <> 'OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST' "
            "OR unit_cost_source <> 'NOT_APPLICABLE'",
            name="ck_ton_occurrence_impact_unit_cost_source_required",
        ),
        CheckConstraint(
            "sensitivity_pct IS NULL OR sensitivity_pct >= 0",
            name="ck_ton_occurrence_impact_sensitivity_non_negative",
        ),
        CheckConstraint("scale >= 0", name="ck_ton_occurrence_impact_scale_valid"),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_ton_occurrence_impact_period_order",
        ),
        Index("ix_ton_occurrence_impact_occurrence_id", "occurrence_id"),
        # Backs the later realised-ROI aggregation: verified, non-BAIXA rows.
        Index("ix_ton_occurrence_impact_roi", "confidence", "verified_at"),
        Index("ix_ton_occurrence_impact_category", "category"),
    )


class OccurrenceAssignment(Base):
    """Who is responsible for an occurrence, and by when. Append-oriented.

    Prompt Mestre §10 escalation and §12 R9 need the *history* of responsibility
    and deadlines, not the latest value, so this is a table rather than two
    mutable columns on the ledger. Reassignment appends a new row and marks the
    previous one ``SUPERSEDED``; the current assignment is the highest
    ``sequence_no``.

    ``responsible_label`` is NOT NULL and ``responsible_user_id`` is optional: a
    §11 blind spot is published with a named field owner who may hold no Onyx
    account. There is no HR integration here and no external directory lookup.
    """

    __tablename__ = "ton_occurrence_assignment"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    occurrence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_occurrence.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)

    responsible_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    # The nominal responsible party as published. Survives an account deletion,
    # which is why it is separate from the foreign key.
    responsible_label: Mapped[str] = mapped_column(String, nullable=False)
    # Nullable: a §10 deadline depends on criticality bands that are still
    # unapproved rule data, so no deadline is ever computed here by default.
    deadline: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, native_enum=False),
        nullable=False,
        default=AssignmentStatus.OPEN,
        server_default=AssignmentStatus.OPEN.value,
    )

    assigned_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    assigned_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    actor_kind: Mapped[OccurrenceActorKind] = mapped_column(
        Enum(OccurrenceActorKind, native_enum=False), nullable=False
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    superseded_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    occurrence: Mapped[Occurrence] = relationship(
        "Occurrence", back_populates="assignments"
    )

    __table_args__ = (
        UniqueConstraint(
            "occurrence_id",
            "sequence_no",
            name="uq_ton_occurrence_assignment_sequence",
        ),
        CheckConstraint(
            "sequence_no >= 1", name="ck_ton_occurrence_assignment_sequence_positive"
        ),
        CheckConstraint(
            "status <> 'COMPLETED' OR completed_at IS NOT NULL",
            name="ck_ton_occurrence_assignment_completed_has_timestamp",
        ),
        CheckConstraint(
            "status <> 'SUPERSEDED' OR superseded_at IS NOT NULL",
            name="ck_ton_occurrence_assignment_superseded_has_timestamp",
        ),
        Index("ix_ton_occurrence_assignment_occurrence_id", "occurrence_id"),
        Index("ix_ton_occurrence_assignment_deadline", "deadline"),
    )


class OccurrenceNote(Base):
    """Human commentary on an occurrence. Append-only.

    A note may carry sensitive business content or PII, so it inherits the
    occurrence ACL and carries its own ``redaction_level``. There is deliberately
    no separate, more permissive read path for notes, and no ``is_public``
    column: :mod:`onyx.db.ton.acl` is the only way to reach them.
    """

    __tablename__ = "ton_occurrence_note"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    occurrence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_occurrence.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    author_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    actor_kind: Mapped[OccurrenceActorKind] = mapped_column(
        Enum(OccurrenceActorKind, native_enum=False), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    redaction_level: Mapped[RedactionLevel] = mapped_column(
        Enum(RedactionLevel, native_enum=False), nullable=False
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    occurrence: Mapped[Occurrence] = relationship("Occurrence", back_populates="notes")

    __table_args__ = (
        UniqueConstraint(
            "occurrence_id", "sequence_no", name="uq_ton_occurrence_note_sequence"
        ),
        CheckConstraint(
            "sequence_no >= 1", name="ck_ton_occurrence_note_sequence_positive"
        ),
        Index("ix_ton_occurrence_note_occurrence_id", "occurrence_id"),
    )


class OccurrenceImpactedDomain(Base):
    """A domain affected by an occurrence it does not own.

    The Prompt Mestre §15 handoff rule. One domain owns the case —
    ``Occurrence.owning_domain``, the link where the quantity changed — and every
    other affected domain is listed here. That is what keeps a single issue from
    being recorded once per specialist, which ``UNIQUE(identity_key)`` on the
    occurrence already makes structurally impossible.

    The owning domain must not appear here. That is a cross-row rule, so
    :mod:`onyx.db.ton.occurrence_records` refuses it and a named test covers it.
    """

    __tablename__ = "ton_occurrence_impacted_domain"

    occurrence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_occurrence.id", ondelete="CASCADE"),
        primary_key=True,
    )
    domain: Mapped[RuleDomain] = mapped_column(
        Enum(RuleDomain, native_enum=False), primary_key=True
    )
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    occurrence: Mapped[Occurrence] = relationship(
        "Occurrence", back_populates="impacted_domains"
    )


class BusinessUnit__UserGroup(Base):
    """Authorizes a user group to reach one business unit.

    **Restrictive, not additive.** Zero rows means DENIED — the opposite of the
    ``Persona__UserGroup`` convention, where a resource with no junction rows is
    visible to everyone. Vale Norte unit financials cannot default to
    organization-wide, so the junction is the grant rather than the restriction
    (readiness §10, corrections 1 and 3).

    ``CASCADE`` on both sides: the row is a relationship, and it has no meaning
    once either end is gone.
    """

    __tablename__ = "ton_business_unit__user_group"

    business_unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_business_unit.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_group.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission: Mapped[TonSharePermission] = mapped_column(
        Enum(TonSharePermission, native_enum=False),
        nullable=False,
        default=TonSharePermission.VIEWER,
        server_default=TonSharePermission.VIEWER.value,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    business_unit: Mapped[BusinessUnit] = relationship("BusinessUnit")

    __table_args__ = (
        Index("ix_ton_business_unit__user_group_group_id", "user_group_id"),
    )


class Contract__UserGroup(Base):
    """Authorizes a user group to reach one contract. Restrictive; zero rows
    means DENIED, as for every TON resource."""

    __tablename__ = "ton_contract__user_group"

    contract_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_contract.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_group.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission: Mapped[TonSharePermission] = mapped_column(
        Enum(TonSharePermission, native_enum=False),
        nullable=False,
        default=TonSharePermission.VIEWER,
        server_default=TonSharePermission.VIEWER.value,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contract: Mapped[Contract] = relationship("Contract")

    __table_args__ = (Index("ix_ton_contract__user_group_group_id", "user_group_id"),)


class Occurrence__UserGroup(Base):
    """Authorizes a user group to reach one occurrence.

    The authoritative resource ACL for the business case, and by derivation for
    its findings, evidence, events, impacts, assignments and notes. Restrictive:
    zero rows means DENIED.

    Differentiated sensitivity — financial versus payroll versus contract — is
    expressed by which groups appear here, not by a second classification
    system. :mod:`onyx.db.ton.acl` refuses a write that would attach a group the
    caller cannot already reach.
    """

    __tablename__ = "ton_occurrence__user_group"

    occurrence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ton_occurrence.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_group.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission: Mapped[TonSharePermission] = mapped_column(
        Enum(TonSharePermission, native_enum=False),
        nullable=False,
        default=TonSharePermission.VIEWER,
        server_default=TonSharePermission.VIEWER.value,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    occurrence: Mapped[Occurrence] = relationship(
        "Occurrence", back_populates="group_shares"
    )

    __table_args__ = (Index("ix_ton_occurrence__user_group_group_id", "user_group_id"),)
