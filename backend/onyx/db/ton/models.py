"""TON domain tables — Plan 003b, the identity, rule and analysis spine.

Scope of this module, exactly:

* stable organizational identity — :class:`BusinessUnit`, :class:`Contract`;
* versioned deterministic rule definitions — :class:`Rule`,
  :class:`RuleVersion`;
* input provenance — :class:`SourceSnapshot`;
* execution envelopes — :class:`AnalysisRun`, :class:`AnalysisRunRuleVersion`,
  :class:`AnalysisRun__SourceSnapshot`;
* domain-scoped execution blocking — :class:`AnalysisStep`.

Deliberately absent, with the slice that owns them: Finding, FindingEvidence,
FindingInterpretation, Occurrence and its history tables plus the resource ACL
junctions (003c); TonReport, TonReportRevision and TonAuditEvent (003d);
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
    BusinessUnitKind,
    ContractStatus,
    EvidenceConfidenceLevel,
    InterpretationStatus,
    MissingDataBehavior,
    PostResolutionPolicy,
    RuleDomain,
    RuleKind,
    RuleProvenance,
    RuleVersionOutcome,
    RuleVersionStatus,
    SourceType,
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
