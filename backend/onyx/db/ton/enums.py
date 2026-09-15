"""Closed value vocabularies for the TON domain (Plan 003b).

Every member here is fixed by `plans/ton/backend/003-readiness.md` or by the TON
VALE Prompt Mestre v2.0 section it cites. None of them is a business *value*:
thresholds, tolerances, baselines and deadlines are data in
``RuleVersion.parameters``, never a member of an enum and never a column.

Name and value are identical on purpose. The repository stores non-native enums
as VARCHAR, and ``Enum(..., native_enum=False)`` persists the member *name*
unless ``values_callable`` says otherwise. Keeping them equal removes that
ambiguity, so a ``CHECK`` constraint written against the literal string stays
correct whichever convention a later reader assumes.
"""

from enum import Enum as PyEnum


class RuleDomain(str, PyEnum):
    """Business domain a rule belongs to (readiness §3).

    A scoping vocabulary, not a role system: authorization stays with
    ``Permission`` and ``UserGroup``.
    """

    FINANCIAL = "FINANCIAL"
    OPERATIONAL = "OPERATIONAL"
    CONTRACT = "CONTRACT"
    FLEET = "FLEET"
    HR = "HR"
    PROCUREMENT = "PROCUREMENT"
    COMPLIANCE = "COMPLIANCE"
    AUDIT = "AUDIT"
    QUALITY = "QUALITY"


class RuleKind(str, PyEnum):
    """What kind of check a rule performs (readiness §3).

    SANITY covers Prompt Mestre §6 (S-rules), DETECTION covers §7-§8 (T-rules)
    and BLIND_SPOT covers §11, where a data gap is itself a first-class finding.
    """

    SANITY = "SANITY"
    DETECTION = "DETECTION"
    BLIND_SPOT = "BLIND_SPOT"


class RuleVersionStatus(str, PyEnum):
    """Lifecycle of one versioned rule configuration (readiness §3).

    ``status`` belongs to the version, never to ``Rule``: activating a new
    threshold must not reinterpret findings produced under the old one.
    ``ACTIVE`` additionally requires a recorded approval, enforced by a database
    CHECK constraint rather than by review habit.
    """

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"
    TEST_ONLY = "TEST_ONLY"


class RuleProvenance(str, PyEnum):
    """Where a rule version's definition came from (readiness §3)."""

    PAD_CTRL_001 = "PAD_CTRL_001"
    PROMPT_MESTRE_V2 = "PROMPT_MESTRE_V2"
    VALE_NORTE_REPORT_2026 = "VALE_NORTE_REPORT_2026"
    OWNER_APPROVED = "OWNER_APPROVED"
    DERIVED = "DERIVED"


class MissingDataBehavior(str, PyEnum):
    """What a rule version does when its inputs did not arrive (readiness §3)."""

    BLOCK = "BLOCK"
    FINDING_BLIND_SPOT = "FINDING_BLIND_SPOT"
    SKIP_WITH_NOTE = "SKIP_WITH_NOTE"


class EvidenceConfidenceLevel(str, PyEnum):
    """Prompt Mestre §3.4 confidence hierarchy.

    A is a primary source, D is an unverified assertion. Repetition never
    promotes a level.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class PostResolutionPolicy(str, PyEnum):
    """What happens when a resolved case is detected again (readiness §7).

    Mandatory per rule version. There is no global default, because the executor
    must not choose silently.
    """

    REOPEN_SAME_OCCURRENCE = "REOPEN_SAME_OCCURRENCE"
    SUPERSEDE_WITH_NEW_OCCURRENCE = "SUPERSEDE_WITH_NEW_OCCURRENCE"


class IdentityComponent(str, PyEnum):
    """Closed vocabulary for ``RuleVersion.identity_components`` (readiness §7).

    Values are lowercase because they are dimension names inside a JSONB list,
    not a column type. Interpretation output is deliberately absent: no LLM text
    may ever become part of a logical identity.
    """

    RULE_CODE = "rule_code"
    BUSINESS_UNIT_ID = "business_unit_id"
    CONTRACT_ID = "contract_id"
    PERIOD = "period"
    SOURCE_SYSTEM = "source_system"
    SOURCE_RECORD_KEY = "source_record_key"
    NATURE_GROUP = "nature_group"
    VEHICLE_KEY = "vehicle_key"
    SUPPLIER_KEY = "supplier_key"
    EMPLOYEE_KEY_MASKED = "employee_key_masked"


class BusinessUnitKind(str, PyEnum):
    """Prompt Mestre §3.3 unit category (readiness §15).

    Required now, not later: §3.3's consolidation rule keeps a non-operational
    cost centre out of profitability rankings and inter-municipal benchmarks,
    and that rule cannot be expressed without this column.
    """

    OPERATIONAL = "OPERATIONAL"
    IMPLANTATION = "IMPLANTATION"
    PROSPECT = "PROSPECT"
    NON_OPERATIONAL = "NON_OPERATIONAL"


class ContractStatus(str, PyEnum):
    """Contract lifecycle state (readiness §15).

    Required now because rule S7 excludes an unsigned contract from backlog,
    revenue and projection. ``UNDER_JUDGEMENT`` is the state Prompt Mestre §6.2
    shows going wrong when it is missing.
    """

    DRAFT = "DRAFT"
    BIDDING = "BIDDING"
    UNDER_JUDGEMENT = "UNDER_JUDGEMENT"
    SIGNED = "SIGNED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ENDED = "ENDED"


class SourceType(str, PyEnum):
    """Class of input material a snapshot receipts (readiness §14).

    Source-agnostic by design. ``NG_KEEVO`` exists so evidence can be labelled;
    no NG/Keevo field mapping exists anywhere (decision D-009).
    """

    NG_KEEVO = "NG_KEEVO"
    UPLOADED_SPREADSHEET = "UPLOADED_SPREADSHEET"
    CONTRACT_DOCUMENT = "CONTRACT_DOCUMENT"
    DOCUMENT_CHUNK = "DOCUMENT_CHUNK"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    CALCULATED_AGGREGATE = "CALCULATED_AGGREGATE"
    BANK_STATEMENT = "BANK_STATEMENT"
    PAYROLL_EXPORT = "PAYROLL_EXPORT"


class AnalysisTrigger(str, PyEnum):
    """What started an analysis run (readiness §4).

    ``SCHEDULED`` is an identity only. Dispatch belongs to Plan 006.
    """

    INTERACTIVE = "INTERACTIVE"
    SCHEDULED = "SCHEDULED"
    BACKFILL = "BACKFILL"
    MANUAL_REPLAY = "MANUAL_REPLAY"


class AnalysisSpecialist(str, PyEnum):
    """The nine Prompt Mestre §15 subagents, as persisted identity only.

    Mapping to the source names, which are Portuguese:

    ============ =================
    Member       Prompt Mestre §15
    ============ =================
    CFO          TON CFO
    COO          TON COO
    FLEET        TON FROTA
    CONTRACTS    TON CONTRATOS
    COMPLIANCE   TON COMPLIANCE
    PROCUREMENT  TON PROCUREMENT
    HR           TON RH
    AUDITOR      TON AUDITOR
    CEO          TON CEO
    ============ =================

    No agent is implemented here. Plan 005 owns agent behaviour, prompts,
    handoffs and supervision.
    """

    CFO = "CFO"
    COO = "COO"
    FLEET = "FLEET"
    CONTRACTS = "CONTRACTS"
    COMPLIANCE = "COMPLIANCE"
    PROCUREMENT = "PROCUREMENT"
    HR = "HR"
    AUDITOR = "AUDITOR"
    CEO = "CEO"


class AnalysisRunStatus(str, PyEnum):
    """Terminal and non-terminal states of an analysis run (readiness §4).

    ``COMPLETED_WITH_BLOCKED_DOMAINS`` is the state that keeps successful
    specialist results alive when a sibling domain or unit failed. Collapsing it
    into ``FAILED`` is the original TON defect.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_BLOCKED_DOMAINS = "COMPLETED_WITH_BLOCKED_DOMAINS"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class AnalysisRunErrorClass(str, PyEnum):
    """Safe failure classification for a run.

    Readiness §4 requires a "safe enum" here and forbids a stack trace, but does
    not fix the members, so this is an executor-defined technical vocabulary
    aligned with :class:`AnalysisStepBlockedReason`. It carries no message, no
    traceback and no source value (SECURITY-01 / SECURITY-02).
    """

    MISSING_SOURCE = "MISSING_SOURCE"
    MISSING_CONTRACT_MASTER = "MISSING_CONTRACT_MASTER"
    SOURCE_VALIDATION_FAILED = "SOURCE_VALIDATION_FAILED"
    RULE_EXECUTION_ERROR = "RULE_EXECUTION_ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class InterpretationStatus(str, PyEnum):
    """AI interpretation state (readiness §8).

    On ``AnalysisRun`` it is a roll-up over child findings. Findings arrive in
    003c, so a 003b run stays ``NOT_REQUIRED`` until then.
    """

    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisStepCode(str, PyEnum):
    """The fixed seven-step execution protocol of Prompt Mestre §5.

    A closed enum, deliberately not a workflow graph. The order in
    :data:`onyx.db.ton.analysis_steps.STEP_ORDER` is the dependency chain, and
    nothing may extend it at runtime.
    """

    INGESTION = "INGESTION"
    BASE_VALIDATION = "BASE_VALIDATION"
    CHAIN_RECONCILIATION = "CHAIN_RECONCILIATION"
    DETECTION = "DETECTION"
    QUANTIFICATION = "QUANTIFICATION"
    PRIORITIZATION = "PRIORITIZATION"
    PUBLICATION = "PUBLICATION"


class AnalysisStepStatus(str, PyEnum):
    """Per-step outcome (readiness §5)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class AnalysisStepBlockedReason(str, PyEnum):
    """Why a step is blocked (readiness §5).

    A BLOCKED step must always name one of these together with the step that
    caused it. There is no silent blocking, and the vocabulary is not to be
    broadened without a readiness decision.
    """

    PREREQUISITE_FAILED = "PREREQUISITE_FAILED"
    MISSING_SOURCE = "MISSING_SOURCE"
    MISSING_CONTRACT_MASTER = "MISSING_CONTRACT_MASTER"
    BASE_REPROVED = "BASE_REPROVED"
    AWAITING_HUMAN_DECISION = "AWAITING_HUMAN_DECISION"


class RuleVersionOutcome(str, PyEnum):
    """What happened to one rule version inside one run (readiness §4).

    Recording the skipped rules with their reason is what makes a report
    reproducible; a list of the rules that fired is not enough.
    """

    EXECUTED = "EXECUTED"
    SKIPPED_NOT_APPLICABLE = "SKIPPED_NOT_APPLICABLE"
    SKIPPED_MISSING_DATA = "SKIPPED_MISSING_DATA"
    ERRORED = "ERRORED"


# ---------------------------------------------------------------------------
# Plan 003c — findings, occurrences, evidence, interpretation and resource ACL.
#
# The same rule as above holds for every member below: none of them is a
# business *value*. Criticality bands, NC thresholds, deadlines and tolerances
# stay data in ``RuleVersion``.
# ---------------------------------------------------------------------------


class FindingKind(str, PyEnum):
    """What kind of detection a :class:`~onyx.db.ton.models.Finding` records.

    ``BLIND_SPOT`` is what makes Prompt Mestre §11's "lacuna de dado é achado de
    primeira classe" real rather than aspirational: a blind-spot finding is valid
    with no numeric impact and no source record, so missing data cannot be
    silently dropped for having nothing to quantify.
    """

    DETECTION = "DETECTION"
    SANITY_VIOLATION = "SANITY_VIOLATION"
    BLIND_SPOT = "BLIND_SPOT"


class OccurrenceLedgerKind(str, PyEnum):
    """Which Prompt Mestre §13 ledger an occurrence belongs to (readiness §13).

    A discriminator, deliberately not a second table. §13.2's opportunity fields
    are a near-subset of §13.1's, and duplicating the table would triplicate the
    impact, verification and ACL logic. Realised ROI stays a later aggregation
    over verified :class:`~onyx.db.ton.models.OccurrenceImpact` rows.
    """

    EXCEPTION = "EXCEPTION"
    OPPORTUNITY = "OPPORTUNITY"


class OccurrenceCriticality(str, PyEnum):
    """The single Prompt Mestre §10 criticality scale (PAD-CTRL-001).

    Four levels, mapping to the source markers:

    ============ ==================
    Member       Prompt Mestre §10
    ============ ==================
    CRITICAL     🔴 Crítico
    HIGH         🟠 Alto
    MEDIUM       🟡 Médio
    MONITORING   🟢 Monitoramento
    ============ ==================

    §10 forbids a parallel scale, so this is the only severity vocabulary in the
    TON domain. **The percentage bands are not here.** They are
    ``RuleVersion.severity_mapping`` data requiring owner approval; encoding
    ≥1%, 0.3-1% or 0.1-0.3% as a constant is exactly what this slice must not do.
    """

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    MONITORING = "MONITORING"


class OccurrenceStatus(str, PyEnum):
    """Lifecycle state of a persistent business case.

    A **cached projection** of :class:`OccurrenceTransition` history, never an
    independent field: every member here is produced by exactly one transition,
    and :mod:`onyx.db.ton.occurrences` is the only writer. See
    ``TRANSITION_RESULTING_STATUS`` there for the mapping.
    """

    NEW = "NEW"
    REOPENED = "REOPENED"
    CONFIRMED = "CONFIRMED"
    RESOLVED = "RESOLVED"
    RISK_ACCEPTED = "RISK_ACCEPTED"
    DISMISSED = "DISMISSED"
    SUPERSEDED = "SUPERSEDED"


class OccurrenceActorKind(str, PyEnum):
    """Who performed a transition (readiness §9).

    The boundary Prompt Mestre §12.1 draws. ``SYSTEM`` is permitted only for the
    operational transitions TON may take alone; the human-decision transitions
    require ``USER`` plus an identified account, enforced by a database CHECK.
    """

    USER = "USER"
    SYSTEM = "SYSTEM"


class OccurrenceTransition(str, PyEnum):
    """Append-only lifecycle vocabulary for :class:`OccurrenceEvent`.

    Three authorization classes, and the class is a database property rather
    than a convention (see ``ck_ton_occurrence_event_human_only_transitions`` and
    ``ck_ton_occurrence_event_resolution_requires_user``):

    * **System-allowed** — ``DETECT``, ``REPEAT_DETECTED``, ``REOPENED``,
      ``ESCALATE_BY_CYCLE_RULE``, ``VERIFICATION_PASSED``,
      ``VERIFICATION_FAILED``, ``SUPERSEDE``. Prompt Mestre §12.1 lets TON read,
      test, calculate, classify, draft, alert and write to the ledger, and §10
      says the criticality scale is applied "sem consultar ninguém".
    * **Requires an identified user** — ``RESOLVED``. Closing a case is a human
      act; §12.1's autonomous list does not include it.
    * **Human-only, with a recorded authorization** — ``RESOLVE_CRITICAL``,
      ``ACCEPT_RISK``, ``DISMISS``, ``ASSERT_NONCOMPLIANCE``,
      ``PROMOTE_INTERPRETATION``, ``OVERRIDE_DETERMINISTIC_VALUE``
      (readiness §9, verbatim).

    Nothing here writes to a source system. There is no transition for
    contesting a glosa, altering a measurement, changing billing or contacting a
    contracting authority: the advisory boundary is enforced by absence.
    """

    DETECT = "DETECT"
    REPEAT_DETECTED = "REPEAT_DETECTED"
    REOPENED = "REOPENED"
    ESCALATE_BY_CYCLE_RULE = "ESCALATE_BY_CYCLE_RULE"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    SUPERSEDE = "SUPERSEDE"
    RESOLVED = "RESOLVED"
    RESOLVE_CRITICAL = "RESOLVE_CRITICAL"
    ACCEPT_RISK = "ACCEPT_RISK"
    DISMISS = "DISMISS"
    ASSERT_NONCOMPLIANCE = "ASSERT_NONCOMPLIANCE"
    PROMOTE_INTERPRETATION = "PROMOTE_INTERPRETATION"
    OVERRIDE_DETERMINISTIC_VALUE = "OVERRIDE_DETERMINISTIC_VALUE"


class OccurrenceVerificationResult(str, PyEnum):
    """Outcome of the Prompt Mestre §5 Passo 7 verification criterion.

    Nullable on the occurrence: "not verified yet" is the absence of a row value,
    not a member, so there is one representation per state.
    """

    PASSED = "PASSED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ImpactCategory(str, PyEnum):
    """The seven Prompt Mestre §9 impact categories.

    They are the columns of the Dinheiro Escondido panel, so the vocabulary is
    closed and ordered as §9 lists it:

    ===================== ==========================
    Member                Prompt Mestre §9
    ===================== ==========================
    POTENTIAL_SAVING      economia potencial
    AVOIDED_LOSS          perda evitada
    RECOVERABLE_REVENUE   receita recuperável
    UNBILLED_REVENUE      receita não faturada
    EXCESS_COST           custo excedente
    FINANCIAL_RISK        risco financeiro
    MARGIN_OPPORTUNITY    oportunidade de margem
    ===================== ==========================
    """

    POTENTIAL_SAVING = "POTENTIAL_SAVING"
    AVOIDED_LOSS = "AVOIDED_LOSS"
    RECOVERABLE_REVENUE = "RECOVERABLE_REVENUE"
    UNBILLED_REVENUE = "UNBILLED_REVENUE"
    EXCESS_COST = "EXCESS_COST"
    FINANCIAL_RISK = "FINANCIAL_RISK"
    MARGIN_OPPORTUNITY = "MARGIN_OPPORTUNITY"


class ImpactConfidence(str, PyEnum):
    """Prompt Mestre §9 confidence in a quantification.

    Portuguese member names because readiness §13 states the ROI rule against
    these literals: a low-confidence impact never enters a target or a realised
    ROI, expressed as ``confidence <> 'BAIXA'``. Keeping the literal identical
    means the aggregation rule and the stored value cannot drift.

    ALTA is complete A/B evidence, MEDIA is B/C with one premise, BAIXA is two or
    more premises. Nothing promotes a level automatically.
    """

    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class ImpactMethod(str, PyEnum):
    """How an impact amount was arrived at.

    Readiness §9 fixes the standard formula
    (``impact = operational difference × reference unit cost``) but leaves the
    remaining members open, so this is an executor-defined vocabulary in the same
    position as :class:`AnalysisRunErrorClass`:

    * ``OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST`` — the §9 standard;
    * ``DIRECT_SOURCE_AMOUNT`` — the amount *is* the source value (a duplicated
      posting, an unbilled measurement), so no reference unit cost applies;
    * ``VALUE_AT_RISK`` — §9's *risco financeiro*: exposure, not a realised
      difference.
    """

    OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST = "OPERATIONAL_DIFFERENCE_TIMES_UNIT_COST"
    DIRECT_SOURCE_AMOUNT = "DIRECT_SOURCE_AMOUNT"
    VALUE_AT_RISK = "VALUE_AT_RISK"


class UnitCostSource(str, PyEnum):
    """Which reference unit cost a quantification used (Prompt Mestre §9).

    §9 fixes the preference order and adds "diga sempre qual usou", which is why
    the column is NOT NULL:

    1. ``CONTRACT_DOTACAO`` — the contract's own dotação cost composition;
    2. ``OWN_UNIT_TRAILING_3M`` — the unit's own trailing three-month actual;
    3. ``COMPARABLE_UNIT_MEDIAN`` — the median of comparable units.

    ``NOT_APPLICABLE`` exists so a method that uses no reference unit cost still
    has to say so explicitly rather than leaving the column null.
    ``ck_ton_occurrence_impact_unit_cost_source_required`` stops it being used as
    an escape hatch for the §9 formula.
    """

    CONTRACT_DOTACAO = "CONTRACT_DOTACAO"
    OWN_UNIT_TRAILING_3M = "OWN_UNIT_TRAILING_3M"
    COMPARABLE_UNIT_MEDIAN = "COMPARABLE_UNIT_MEDIAN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AssignmentStatus(str, PyEnum):
    """Outcome of one assignment row.

    Reassignment appends a new row and marks the previous one ``SUPERSEDED``, so
    every past responsible party and every past deadline survives. Prompt Mestre
    §10 escalation and §12 R9 need the history, not the latest value.
    """

    OPEN = "OPEN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class RedactionLevel(str, PyEnum):
    """How much personal identity a row carries (readiness §9).

    §12.1 forbids TON from imputing conduct to a named person, so evidence and
    notes record a role or cargo by default and person identity only behind the
    resource ACL. NOT NULL with no default: the writer must state the level
    rather than let it be assumed.

    * ``NONE`` — no personal data;
    * ``ROLE_ONLY`` — a role or cargo, no person identity (the §9 default);
    * ``MASKED_IDENTIFIER`` — an identity present but masked, e.g. the
      ``employee_key_masked`` identity dimension;
    * ``IDENTIFIED`` — person identity present. Only reachable behind the ACL.
    """

    NONE = "NONE"
    ROLE_ONLY = "ROLE_ONLY"
    MASKED_IDENTIFIER = "MASKED_IDENTIFIER"
    IDENTIFIED = "IDENTIFIED"


class InterpretationInputScope(str, PyEnum):
    """What an interpretation attempt was allowed to see (readiness §8).

    The privacy control, and it composes with ``TON_TRACE_CONTENT_MODE`` from
    Plan 002 (D-015): a deployment configured for metadata-only content must not
    be able to persist ``FULL_EVIDENCE``. Enforced in
    :mod:`onyx.db.ton.interpretations`, not left to the caller.
    """

    STRUCTURED_ONLY = "STRUCTURED_ONLY"
    MASKED_EXCERPT = "MASKED_EXCERPT"
    FULL_EVIDENCE = "FULL_EVIDENCE"


class InterpretationFailureClass(str, PyEnum):
    """Why an interpretation attempt failed (readiness §8).

    A failure is durable and operator-visible. It is never converted into an
    empty successful interpretation, which is why ``FAILED`` requires one of
    these and ``COMPLETED`` requires a summary.
    """

    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    POLICY_REFUSAL = "POLICY_REFUSAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class TonSharePermission(str, PyEnum):
    """Level granted by a TON resource ``*__UserGroup`` row (readiness §10).

    The junction is **restrictive**, not additive: for a TON resource, zero
    junction rows means DENIED. That inverts the ``Persona``/``Skill`` convention
    on purpose — ``Persona.is_public`` defaults to true and short-circuits the
    group ACL, and copying it would publish Vale Norte financial data. No TON
    table has an ``is_public`` column at all, so the short-circuit is not merely
    disabled, it is inexpressible.
    """

    VIEWER = "VIEWER"
    EDITOR = "EDITOR"
