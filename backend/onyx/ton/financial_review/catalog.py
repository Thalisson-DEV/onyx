"""Canonical DATA-003 rule catalog, POP capability matrix and diagnostic policy.

The catalog in code is the single definition. A review registers each entry as
an immutable ``Rule`` / ``RuleVersion`` pair and refuses to run when a stored
version no longer matches its code definition: changing a rule requires a new
version, so historical findings keep their meaning.

No client name, unit, supplier, document number or amount appears here.
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from onyx.db.ton.enums import (
    EvidenceConfidenceLevel,
    MissingDataBehavior,
    OccurrenceCriticality,
    PostResolutionPolicy,
    RuleKind,
    RuleProvenance,
    RuleVersionStatus,
)
from onyx.ton.financial_review.models import (
    CapabilityStatus,
    DiagnosticTreatment,
    EngineRuleStatus,
    IssueOrigin,
    RecommendationKind,
    ReviewCategory,
    RuleType,
    SourceRequirement,
)
from onyx.ton.ng_financial.models import DiagnosticCode, DiagnosticLevel

ENGINE_VERSION = "ng-financial-review-1"
DATASET_POLICY_VERSION = "ng-reviewed-dataset-policy-1"

# Identity dimensions every DATA-003 occurrence uses. The rule version is never
# one of them, so a new rule version keeps recurrence on the same case.
IDENTITY_COMPONENTS: tuple[str, ...] = (
    "rule_code",
    "source_system",
    "period",
    "source_record_key",
)

POP_NAMES: dict[ReviewCategory, str] = {
    ReviewCategory.POP_01: "Lançamento Duplicado",
    ReviewCategory.POP_02: "Competência Incorreta",
    ReviewCategory.POP_03: "Classificação Contábil/Gerencial Incorreta",
    ReviewCategory.POP_04: "Centro de Custo ou Unidade Incorreta",
    ReviewCategory.POP_05: "Omissão de Despesas Recorrentes",
    ReviewCategory.POP_06: "Pagamento em Duplicidade",
    ReviewCategory.POP_07: "Valores Atípicos ou Fora do Padrão",
    ReviewCategory.POP_08: "Informações Incompletas ou Ausentes",
    ReviewCategory.POP_09: "Despesas sem Formalização ou Aprovação",
    ReviewCategory.POP_10: "Folha de Pagamento com Risco de Duplicidade",
    ReviewCategory.POP_11: "Ocorrências, Sinistros e Perdas Não Registrados",
    ReviewCategory.POP_12: "Divergência entre Financeiro e Contábil",
    ReviewCategory.POP_13: "Documentação de Suporte Ausente",
    ReviewCategory.POP_14: "Receitas Não Registradas ou Classificadas Incorretamente",
}

AVAILABLE_SOURCES: frozenset[SourceRequirement] = frozenset(
    {SourceRequirement.NG_FINANCIAL_EXPORT}
)


@dataclass(frozen=True)
class RuleDefinition:
    """The explicit contract of one versioned review rule."""

    key: str
    version: int
    name: str
    description: str
    category: ReviewCategory
    rule_type: RuleType
    rule_kind: RuleKind
    status: EngineRuleStatus
    severity: OccurrenceCriticality
    blocking: bool
    origin: IssueOrigin
    required_sources: tuple[SourceRequirement, ...] = (
        SourceRequirement.NG_FINANCIAL_EXPORT,
    )
    required_fields: tuple[str, ...] = ()
    related_categories: tuple[ReviewCategory, ...] = ()
    recommendation_capability: tuple[RecommendationKind, ...] = ()
    # Fields a correction would change. Excluded from the record identity so a
    # corrected record in a later import still corresponds to the original.
    correctable_fields: tuple[str, ...] = ()
    diagnostic_codes: tuple[DiagnosticCode, ...] = ()
    verification_criterion: str | None = None
    known_limitations: tuple[str, ...] = field(default_factory=tuple)

    @property
    def executor_key(self) -> str:
        return f"{self.key}.v{self.version}"

    @property
    def produces_findings(self) -> bool:
        return self.status is EngineRuleStatus.ACTIVE

    def missing_sources(
        self, available: frozenset[SourceRequirement]
    ) -> tuple[SourceRequirement, ...]:
        return tuple(item for item in self.required_sources if item not in available)


# Engine status -> governance status of a newly registered RuleVersion. ACTIVE
# still needs an owner approval before report publication (is_publishable).
REGISTERED_VERSION_STATUS: dict[EngineRuleStatus, RuleVersionStatus] = {
    EngineRuleStatus.ACTIVE: RuleVersionStatus.PENDING_APPROVAL,
    EngineRuleStatus.EXPERIMENTAL: RuleVersionStatus.TEST_ONLY,
    EngineRuleStatus.BLOCKED: RuleVersionStatus.DRAFT,
    EngineRuleStatus.DISABLED: RuleVersionStatus.SUSPENDED,
}


def rule_version_fields(definition: RuleDefinition) -> dict[str, Any]:
    """Code definition as ``RuleVersion`` column values. Part of the hash."""
    parameters: dict[str, Any] = {
        "engine_status": definition.status.value,
        "rule_type": definition.rule_type.value,
        "category": definition.category.value,
        "related_categories": [item.value for item in definition.related_categories],
        "required_sources": [item.value for item in definition.required_sources],
        "required_fields": list(definition.required_fields),
        "blocking": definition.blocking,
        "origin": definition.origin.value,
        "correctable_fields": list(definition.correctable_fields),
        "diagnostic_codes": [item.value for item in definition.diagnostic_codes],
        "recommendation_capability": [
            item.value for item in definition.recommendation_capability
        ],
        "engine_version": ENGINE_VERSION,
    }
    return {
        "version": definition.version,
        "title": definition.name,
        "description": definition.description,
        "executor_key": definition.executor_key,
        "parameters": parameters,
        "applicability": {"source_profile": "ng_financial_export"},
        "provenance": RuleProvenance.DERIVED,
        "source_reference": (
            f"POP Controladoria {definition.category.value}"
            if definition.category.value.startswith("POP_")
            else f"DATA-003 {definition.category.value}"
        ),
        "missing_data_behavior": (
            MissingDataBehavior.BLOCK
            if definition.status is EngineRuleStatus.BLOCKED
            else MissingDataBehavior.SKIP_WITH_NOTE
        ),
        "evidence_requirements": {
            "lineage": ["parsed_source_record", "parse_diagnostic"],
        },
        "min_confidence_level": EvidenceConfidenceLevel.B,
        "severity_mapping": {"default": definition.severity.value},
        "identity_components": list(IDENTITY_COMPONENTS),
        "post_resolution_policy": PostResolutionPolicy.REOPEN_SAME_OCCURRENCE,
        "status": REGISTERED_VERSION_STATUS[definition.status],
    }


class RuleCatalog:
    """An ordered, versioned set of rule definitions."""

    def __init__(self, definitions: Iterable[RuleDefinition]) -> None:
        self._definitions = tuple(sorted(definitions, key=lambda item: item.key))
        keys = [item.key for item in self._definitions]
        if len(keys) != len(set(keys)):
            raise ValueError("A rule catalog holds one version per rule key.")
        self._by_key = {item.key: item for item in self._definitions}

    def __iter__(self) -> Iterator[RuleDefinition]:
        return iter(self._definitions)

    def __len__(self) -> int:
        return len(self._definitions)

    def get(self, key: str) -> RuleDefinition:
        return self._by_key[key]

    def keys(self) -> frozenset[str]:
        return frozenset(self._by_key)

    def replace(self, definition: RuleDefinition) -> "RuleCatalog":
        """A catalog with one rule moved to another version."""
        return RuleCatalog(
            [item for item in self._definitions if item.key != definition.key]
            + [definition]
        )


_ROW_REJECTION_CODES: tuple[DiagnosticCode, ...] = (
    DiagnosticCode.UNKNOWN_ROW,
    DiagnosticCode.INVALID_DATE,
    DiagnosticCode.INHERITED_DATE_INVALID,
    DiagnosticCode.MISSING_DATE,
    DiagnosticCode.INVALID_AMOUNT,
    DiagnosticCode.MISSING_AMOUNTS,
    DiagnosticCode.FORMULA_UNSUPPORTED,
)

_ACTIVE: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        key="NGF-SRC-ROW-REJECTED",
        version=1,
        name="Linha financeira rejeitada na importação",
        description=(
            "A detail row of a terminal account block could not become a parsed "
            "record: invalid or missing date, invalid or missing amounts, a "
            "formula, or an unrecognised structure. The row's value is absent "
            "from the reviewed dataset."
        ),
        category=ReviewCategory.POP_08,
        rule_type=RuleType.DETERMINISTIC,
        rule_kind=RuleKind.SANITY,
        status=EngineRuleStatus.ACTIVE,
        severity=OccurrenceCriticality.HIGH,
        blocking=True,
        origin=IssueOrigin.UNRESOLVED,
        required_fields=("parse_diagnostics",),
        recommendation_capability=(RecommendationKind.SOURCE_CORRECTION_REQUIRED,),
        diagnostic_codes=_ROW_REJECTION_CODES,
        verification_criterion=(
            "Uma importação posterior não rejeita a linha correspondente. A "
            "correspondência é apenas por localização e exige confirmação humana."
        ),
        known_limitations=(
            "Diagnostics carry location only, so a later import cannot be matched "
            "by content. Verification is never automatic.",
            "The engine cannot tell whether the invalid cell comes from NG data "
            "entry or from the export.",
        ),
    ),
    RuleDefinition(
        key="NGF-UNIT-MISSING",
        version=1,
        name="Lançamento sem unidade administrativa",
        description=(
            "A parsed detail record has no administrative unit. The managerial "
            "close attributes every launch to a unit or contract, so the record "
            "cannot be attributed."
        ),
        category=ReviewCategory.POP_08,
        related_categories=(ReviewCategory.POP_04,),
        rule_type=RuleType.DETERMINISTIC,
        rule_kind=RuleKind.SANITY,
        status=EngineRuleStatus.ACTIVE,
        severity=OccurrenceCriticality.MEDIUM,
        blocking=True,
        origin=IssueOrigin.SOURCE_BUSINESS_ERROR,
        required_fields=("administrative_unit",),
        recommendation_capability=(
            RecommendationKind.SOURCE_CORRECTION_REQUIRED,
            RecommendationKind.DETERMINISTIC_CORRECTION,
        ),
        correctable_fields=("administrative_unit",),
        diagnostic_codes=(DiagnosticCode.UNIT_BLANK,),
        verification_criterion=(
            "Uma importação posterior contém exatamente um lançamento "
            "correspondente, agora com unidade administrativa."
        ),
        known_limitations=(
            "No unit is inferred from history, supplier or document text.",
            "Correspondence across imports excludes the unit and requires every "
            "other field to stay unchanged.",
        ),
    ),
    RuleDefinition(
        key="NGF-DUP-EXACT",
        version=1,
        name="Candidato a lançamento duplicado (conteúdo idêntico)",
        description=(
            "Two or more preserved records in the same monthly sheet share the "
            "complete content fingerprint: account, label, effective date, unit, "
            "document, history, all twelve amounts and extra cells. The records "
            "may be legitimate repetitions; all are kept."
        ),
        category=ReviewCategory.POP_01,
        related_categories=(ReviewCategory.POP_06,),
        rule_type=RuleType.DETERMINISTIC,
        rule_kind=RuleKind.DETECTION,
        status=EngineRuleStatus.ACTIVE,
        severity=OccurrenceCriticality.HIGH,
        blocking=True,
        origin=IssueOrigin.UNRESOLVED,
        required_fields=("fingerprint", "duplicate_ordinal"),
        recommendation_capability=(RecommendationKind.REQUEST_JUSTIFICATION,),
        verification_criterion=(
            "Uma importação posterior contém uma única ocorrência desse conteúdo "
            "no mesmo mês, ou o Financeiro justifica a repetição."
        ),
        known_limitations=(
            "Equal content is not proof of duplication; no record is removed.",
            "Repetitions across different monthly sheets are not evaluated.",
        ),
    ),
    RuleDefinition(
        key="NGF-DUP-DOC",
        version=2,
        name="Lançamento duplicado com o documento em outro formato",
        description=(
            "Two or more records in one monthly sheet share account, effective "
            "date, gross movement amount and the same invoice number, written once "
            "as the plain number and once as the two-digit year followed by the "
            "zero-padded number. Every copy after the "
            "first in sheet order is flagged; the first is kept."
        ),
        category=ReviewCategory.POP_01,
        related_categories=(ReviewCategory.POP_06,),
        rule_type=RuleType.DETERMINISTIC,
        rule_kind=RuleKind.DETECTION,
        status=EngineRuleStatus.ACTIVE,
        severity=OccurrenceCriticality.HIGH,
        blocking=True,
        origin=IssueOrigin.SOURCE_BUSINESS_ERROR,
        required_fields=("document_number",),
        recommendation_capability=(RecommendationKind.SOURCE_CORRECTION_REQUIRED,),
        verification_criterion=(
            "Uma importação posterior contém um único lançamento desse documento "
            "no mês."
        ),
        known_limitations=(
            "Only the year-prefixed invoice notation is recognized.",
            "Retention and net amounts may differ between the copies.",
            "A confirmed copy leaves the reviewed dataset; the first copy stays.",
        ),
    ),
    RuleDefinition(
        key="NGF-ACCT-LABEL-DRIFT",
        version=1,
        name="Código de conta com mais de uma descrição",
        description=(
            "One account code appears with more than one label inside one "
            "import. The classification is not changed."
        ),
        category=ReviewCategory.POP_03,
        rule_type=RuleType.DETERMINISTIC,
        rule_kind=RuleKind.SANITY,
        status=EngineRuleStatus.ACTIVE,
        severity=OccurrenceCriticality.MONITORING,
        blocking=False,
        origin=IssueOrigin.UNRESOLVED,
        required_fields=("account_code", "account_label"),
        recommendation_capability=(
            RecommendationKind.REVIEW_CLASSIFICATION,
            RecommendationKind.DETERMINISTIC_CORRECTION,
        ),
        correctable_fields=("account_label",),
        verification_criterion=(
            "Uma importação posterior mostra uma única descrição para o código."
        ),
        known_limitations=(
            "A chart-of-accounts rename inside the period is legitimate.",
            "A correction is suggested only with an authoritative mapping, and "
            "no mapping is configured.",
        ),
    ),
    RuleDefinition(
        key="NGF-UNIT-LABEL-DRIFT",
        version=1,
        name="Código de unidade com mais de uma descrição",
        description=(
            "An administrative unit written as 'code - label' appears with more "
            "than one label for the same code inside one import."
        ),
        category=ReviewCategory.POP_04,
        rule_type=RuleType.DETERMINISTIC,
        rule_kind=RuleKind.SANITY,
        status=EngineRuleStatus.ACTIVE,
        severity=OccurrenceCriticality.MONITORING,
        blocking=False,
        origin=IssueOrigin.UNRESOLVED,
        required_fields=("administrative_unit",),
        recommendation_capability=(RecommendationKind.REQUEST_INFORMATION,),
        correctable_fields=("administrative_unit",),
        verification_criterion=(
            "Uma importação posterior mostra uma única descrição para o código."
        ),
        known_limitations=(
            "Applies only to units written as 'code - label'.",
            "The correctness of the unit assigned to a launch needs a unit or "
            "contract master that does not exist yet.",
        ),
    ),
)

_EXPERIMENTAL: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        key="NGF-HIER-RECONCILIATION",
        version=1,
        name="Reconciliação hierárquica (diagnóstico)",
        description=(
            "Counts DATA-002 parent/child reconciliation differences per sheet "
            "and relates them to rejected rows. Produces no finding until the "
            "export semantics of parent blocks are confirmed."
        ),
        category=ReviewCategory.TECHNICAL_SOURCE_QUALITY,
        rule_type=RuleType.HEURISTIC,
        rule_kind=RuleKind.SANITY,
        status=EngineRuleStatus.EXPERIMENTAL,
        severity=OccurrenceCriticality.MONITORING,
        blocking=False,
        origin=IssueOrigin.EXPORT_STRUCTURE,
        required_fields=("parse_diagnostics",),
        diagnostic_codes=(
            DiagnosticCode.PARENT_ROW_WITHOUT_CHILD_MATCH,
            DiagnosticCode.CHILD_ROW_WITHOUT_PARENT_MATCH,
        ),
        known_limitations=(
            "Parent-block semantics in the NG export are not documented.",
        ),
    ),
    RuleDefinition(
        key="NGF-DUP-NEAR",
        version=1,
        name="Quase duplicados (diagnóstico)",
        description=(
            "Counts records in one sheet with the same account, effective date, "
            "document and all amounts but a different history or unit."
        ),
        category=ReviewCategory.POP_06,
        related_categories=(ReviewCategory.POP_01,),
        rule_type=RuleType.HEURISTIC,
        rule_kind=RuleKind.DETECTION,
        status=EngineRuleStatus.EXPERIMENTAL,
        severity=OccurrenceCriticality.MONITORING,
        blocking=False,
        origin=IssueOrigin.UNRESOLVED,
        required_fields=("document_number",),
        known_limitations=("Split launches legitimately share document and amounts.",),
    ),
    RuleDefinition(
        key="NGF-DATE-EMISSION-AFTER-SHEET",
        version=1,
        name="Emissão posterior ao mês da planilha (diagnóstico)",
        description=(
            "Counts records whose emission month is later than the month of the "
            "sheet that lists them. The meaning of the sheet month is not "
            "confirmed, so no competence conclusion is drawn."
        ),
        category=ReviewCategory.POP_02,
        rule_type=RuleType.HEURISTIC,
        rule_kind=RuleKind.DETECTION,
        status=EngineRuleStatus.EXPERIMENTAL,
        severity=OccurrenceCriticality.MONITORING,
        blocking=False,
        origin=IssueOrigin.UNRESOLVED,
        required_fields=("emission_date", "sheet_month"),
        known_limitations=(
            "The sheet has no year. The dominant emission year of the sheet is used.",
        ),
    ),
    RuleDefinition(
        key="NGF-AMT-FINAL-ABSENT",
        version=1,
        name="Valor final ausente ou zero com movimento (diagnóstico)",
        description=(
            "Counts records with a non-zero movement amount and a zero or blank "
            "final amount."
        ),
        category=ReviewCategory.POP_08,
        rule_type=RuleType.HEURISTIC,
        rule_kind=RuleKind.SANITY,
        status=EngineRuleStatus.EXPERIMENTAL,
        severity=OccurrenceCriticality.MONITORING,
        blocking=False,
        origin=IssueOrigin.UNRESOLVED,
        required_fields=("movement_amount", "final_amount"),
        known_limitations=(
            "Retentions settled at invoicing can legitimately zero the final amount.",
        ),
    ),
    RuleDefinition(
        key="NGF-DOC-MISSING",
        version=1,
        name="Lançamento sem número de documento (diagnóstico)",
        description="Counts detail records without a document number.",
        category=ReviewCategory.POP_13,
        rule_type=RuleType.HEURISTIC,
        rule_kind=RuleKind.SANITY,
        status=EngineRuleStatus.EXPERIMENTAL,
        severity=OccurrenceCriticality.MONITORING,
        blocking=False,
        origin=IssueOrigin.UNRESOLVED,
        required_fields=("document_number",),
        known_limitations=(
            "Some launch types have no document. Support documents are another source.",
        ),
    ),
)


def _blocked(
    key: str,
    name: str,
    description: str,
    category: ReviewCategory,
    rule_type: RuleType,
    sources: tuple[SourceRequirement, ...],
    limitation: str,
) -> RuleDefinition:
    return RuleDefinition(
        key=key,
        version=1,
        name=name,
        description=description,
        category=category,
        rule_type=rule_type,
        rule_kind=RuleKind.DETECTION,
        status=EngineRuleStatus.BLOCKED,
        severity=OccurrenceCriticality.MONITORING,
        blocking=False,
        origin=IssueOrigin.UNRESOLVED,
        required_sources=(SourceRequirement.NG_FINANCIAL_EXPORT, *sources),
        known_limitations=(limitation,),
    )


_BLOCKED: tuple[RuleDefinition, ...] = (
    _blocked(
        "NGF-HIST-RECURRING-OMISSION",
        "Omissão de despesa recorrente",
        "Expected recurring launch absent from a period.",
        ReviewCategory.POP_05,
        RuleType.STATISTICAL,
        (SourceRequirement.FINANCIAL_HISTORY,),
        "Needs a normalised history (ideally 2025 onwards) to define recurrence.",
    ),
    _blocked(
        "NGF-HIST-ATYPICAL-VALUE",
        "Valor atípico",
        "Amount outside a historical baseline (median/MAD, IQR, rolling).",
        ReviewCategory.POP_07,
        RuleType.STATISTICAL,
        (SourceRequirement.FINANCIAL_HISTORY,),
        "Six months of one year is not a baseline.",
    ),
    _blocked(
        "NGF-XS-DOTACAO-OVERRUN",
        "Gasto fora da dotação",
        "Spending outside the expected dotação of a unit or contract.",
        ReviewCategory.NOT_IN_POP,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.DOTACAO,),
        "Needs normalised dotação data.",
    ),
    _blocked(
        "NGF-XS-APPROVAL-MISSING",
        "Despesa sem aprovação formal",
        "Launch without a matching approved workflow.",
        ReviewCategory.POP_09,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.ZEEV_WORKFLOW,),
        "Needs a normalised approval workflow source. Zeev SLA rules stay outside.",
    ),
    _blocked(
        "NGF-XS-SUPPORT-DOC",
        "Documentação de suporte ausente",
        "Launch without an invoice or receipt in a document source.",
        ReviewCategory.POP_13,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.SUPPORTING_DOCUMENTS,),
        "Needs an invoice or receipt source.",
    ),
    _blocked(
        "NGF-XS-PAYROLL-DUP",
        "Folha com risco de duplicidade",
        "Payroll payment repeated across payroll and financial launches.",
        ReviewCategory.POP_10,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.PAYROLL,),
        "Payroll sheets are out of scope until NG Folha is ingested.",
    ),
    _blocked(
        "NGF-XS-UNRECORDED-LOSS",
        "Ocorrência, sinistro ou perda não registrada",
        "Event that should have a launch but has none.",
        ReviewCategory.POP_11,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.HUMAN_CONTEXT,),
        "An absent launch cannot be proven from the financial export alone.",
    ),
    _blocked(
        "NGF-XS-FIN-VS-ACCOUNTING",
        "Divergência entre financeiro e contábil",
        "Financial launch without the matching accounting entry.",
        ReviewCategory.POP_12,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.ACCOUNTING_LEDGER,),
        "Needs the accounting ledger.",
    ),
    _blocked(
        "NGF-XS-REVENUE-CLASSIFICATION",
        "Receita não registrada ou mal classificada",
        "Billing without a revenue launch, or revenue in the wrong account.",
        ReviewCategory.POP_14,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.BILLING, SourceRequirement.ACCOUNTING_LEDGER),
        "Needs billing and accounting sources.",
    ),
    _blocked(
        "NGF-XS-PAYMENT-DUP-BANK",
        "Pagamento em duplicidade no extrato",
        "Same payee and amount paid twice according to the bank statement.",
        ReviewCategory.POP_06,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.BANK_STATEMENT,),
        "Needs detailed bank statements.",
    ),
    _blocked(
        "NGF-XS-COMPETENCE",
        "Competência do serviço incorreta",
        "Launch recorded in a month other than the service competence.",
        ReviewCategory.POP_02,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.SUPPORTING_DOCUMENTS,),
        "The export has no service-competence field.",
    ),
    _blocked(
        "NGF-XS-CLASSIFICATION-NATURE",
        "Natureza gerencial incorreta",
        "Account mapped to the wrong managerial nature.",
        ReviewCategory.POP_03,
        RuleType.CROSS_SOURCE,
        (SourceRequirement.CHART_OF_ACCOUNTS,),
        "Needs an approved account-to-nature mapping.",
    ),
    _blocked(
        "NGF-AMT-COMPOSITION",
        "Composição dos valores F:Q",
        "Arithmetic consistency between movement, retention, net and final.",
        ReviewCategory.TECHNICAL_SOURCE_QUALITY,
        RuleType.DETERMINISTIC,
        (SourceRequirement.HUMAN_CONTEXT,),
        "Finance has not confirmed the formula or the sign convention.",
    ),
)

DEFAULT_CATALOG = RuleCatalog((*_ACTIVE, *_EXPERIMENTAL, *_BLOCKED))


@dataclass(frozen=True)
class PopCapability:
    category: ReviewCategory
    status: CapabilityStatus
    rationale: str

    @property
    def name(self) -> str:
        return POP_NAMES[self.category]


POP_CAPABILITIES: tuple[PopCapability, ...] = (
    PopCapability(
        ReviewCategory.POP_01,
        CapabilityStatus.PARTIAL,
        "Exact in-sheet content duplicates are flagged as candidates. Proof needs "
        "Finance confirmation.",
    ),
    PopCapability(
        ReviewCategory.POP_02,
        CapabilityStatus.REQUIRES_DOCUMENT_SOURCE,
        "The export has no service competence. Emission versus sheet month is "
        "diagnostic only.",
    ),
    PopCapability(
        ReviewCategory.POP_03,
        CapabilityStatus.PARTIAL,
        "Label drift of an account code is detectable. Nature mapping needs the "
        "chart of accounts.",
    ),
    PopCapability(
        ReviewCategory.POP_04,
        CapabilityStatus.PARTIAL,
        "Missing unit and unit label drift are detectable. Whether an assigned "
        "unit is wrong needs a unit or contract master.",
    ),
    PopCapability(
        ReviewCategory.POP_05,
        CapabilityStatus.REQUIRES_HISTORY,
        "Recurrence needs a historical baseline.",
    ),
    PopCapability(
        ReviewCategory.POP_06,
        CapabilityStatus.PARTIAL,
        "Identical launches are flagged. Paid-twice needs bank statements.",
    ),
    PopCapability(
        ReviewCategory.POP_07,
        CapabilityStatus.REQUIRES_HISTORY,
        "Outliers need sufficient history; six months is not enough.",
    ),
    PopCapability(
        ReviewCategory.POP_08,
        CapabilityStatus.IMPLEMENTABLE_NOW,
        "Rejected rows and missing units are deterministic.",
    ),
    PopCapability(
        ReviewCategory.POP_09,
        CapabilityStatus.REQUIRES_ZEEV,
        "Approval evidence lives in the workflow source.",
    ),
    PopCapability(
        ReviewCategory.POP_10,
        CapabilityStatus.REQUIRES_PAYROLL,
        "Payroll is not ingested.",
    ),
    PopCapability(
        ReviewCategory.POP_11,
        CapabilityStatus.REQUIRES_HUMAN_CONTEXT,
        "An unrecorded event leaves no trace in the financial export.",
    ),
    PopCapability(
        ReviewCategory.POP_12,
        CapabilityStatus.REQUIRES_ACCOUNTING_SOURCE,
        "Needs the accounting ledger.",
    ),
    PopCapability(
        ReviewCategory.POP_13,
        CapabilityStatus.REQUIRES_DOCUMENT_SOURCE,
        "Needs an invoice or receipt source. Blank document numbers are counted only.",
    ),
    PopCapability(
        ReviewCategory.POP_14,
        CapabilityStatus.REQUIRES_ACCOUNTING_SOURCE,
        "Needs billing and accounting sources.",
    ),
)


@dataclass(frozen=True)
class DiagnosticPolicy:
    code: DiagnosticCode
    # None applies to every level of the code.
    level: DiagnosticLevel | None
    treatment: DiagnosticTreatment
    rule_key: str | None
    rationale: str


DIAGNOSTIC_POLICY: tuple[DiagnosticPolicy, ...] = (
    DiagnosticPolicy(
        DiagnosticCode.SHEET_OUT_OF_SCOPE,
        None,
        DiagnosticTreatment.TECHNICAL_ONLY,
        None,
        "Payroll and other sheets are outside the financial profile.",
    ),
    DiagnosticPolicy(
        DiagnosticCode.MONTH_SHEET_EMPTY,
        None,
        DiagnosticTreatment.REVIEW_RELEVANT,
        None,
        "An empty month is reported in the dataset summary; no launch exists to review.",
    ),
    DiagnosticPolicy(
        DiagnosticCode.ACCOUNT_SECTION_REPEATED,
        None,
        DiagnosticTreatment.REVIEW_RELEVANT,
        None,
        "Structural anomaly counted in the run statistics.",
    ),
    DiagnosticPolicy(
        DiagnosticCode.CELL_OUTSIDE_CONTRACT,
        None,
        DiagnosticTreatment.TECHNICAL_ONLY,
        None,
        "Cells outside A:Q have no known meaning and are not interpreted.",
    ),
    DiagnosticPolicy(
        DiagnosticCode.FORMULA_UNSUPPORTED,
        DiagnosticLevel.ERROR,
        DiagnosticTreatment.FINDING_ELIGIBLE,
        "NGF-SRC-ROW-REJECTED",
        "A detail row with a formula was rejected.",
    ),
    DiagnosticPolicy(
        DiagnosticCode.FORMULA_UNSUPPORTED,
        None,
        DiagnosticTreatment.TECHNICAL_ONLY,
        None,
        "A formula on a hierarchy row changes no record.",
    ),
    *(
        DiagnosticPolicy(
            code,
            None,
            DiagnosticTreatment.FINDING_ELIGIBLE,
            "NGF-SRC-ROW-REJECTED",
            "The detail row was rejected and its value is absent.",
        )
        for code in (
            DiagnosticCode.UNKNOWN_ROW,
            DiagnosticCode.INVALID_DATE,
            DiagnosticCode.INHERITED_DATE_INVALID,
            DiagnosticCode.MISSING_DATE,
            DiagnosticCode.INVALID_AMOUNT,
            DiagnosticCode.MISSING_AMOUNTS,
        )
    ),
    DiagnosticPolicy(
        DiagnosticCode.UNIT_BLANK,
        None,
        DiagnosticTreatment.FINDING_ELIGIBLE,
        "NGF-UNIT-MISSING",
        "Evaluated on the parsed record itself; the diagnostic corroborates it.",
    ),
    DiagnosticPolicy(
        DiagnosticCode.PARENT_ROW_WITHOUT_CHILD_MATCH,
        None,
        DiagnosticTreatment.EXPERIMENTAL,
        "NGF-HIER-RECONCILIATION",
        "Parent-block semantics are unproven; never promoted to a finding.",
    ),
    DiagnosticPolicy(
        DiagnosticCode.CHILD_ROW_WITHOUT_PARENT_MATCH,
        None,
        DiagnosticTreatment.EXPERIMENTAL,
        "NGF-HIER-RECONCILIATION",
        "Parent-block semantics are unproven; never promoted to a finding.",
    ),
)


def diagnostic_policy_for(
    code: DiagnosticCode, level: DiagnosticLevel
) -> DiagnosticPolicy:
    exact = [
        item for item in DIAGNOSTIC_POLICY if item.code is code and item.level is level
    ]
    if exact:
        return exact[0]
    generic = [
        item for item in DIAGNOSTIC_POLICY if item.code is code and item.level is None
    ]
    if not generic:
        raise KeyError(f"No diagnostic policy for {code.value}")
    return generic[0]
