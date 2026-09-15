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
