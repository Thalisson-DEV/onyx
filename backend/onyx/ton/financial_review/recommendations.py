"""Recommendation policy, separate from detection.

A detection states that something needs attention. A recommendation states
what the evidence supports doing. A replacement value is suggested only when
one authoritative value exists; several candidates stay ambiguous.
"""

from onyx.ton.financial_review.catalog import RuleDefinition
from onyx.ton.financial_review.models import (
    Detection,
    DetectionScope,
    RecommendationDraft,
    RecommendationEvidenceLevel,
    RecommendationKind,
)
from onyx.ton.ng_financial.parser import COLUMN_MAP


def _value_recommendation(
    definition: RuleDefinition,
    detection: Detection,
    *,
    target_field: str,
    ambiguous_kind: RecommendationKind,
    ambiguous_explanation: str,
) -> RecommendationDraft:
    candidates = len(detection.candidate_values)
    authoritative = detection.authoritative_value
    if (
        authoritative is not None
        and RecommendationKind.DETERMINISTIC_CORRECTION
        in definition.recommendation_capability
    ):
        return RecommendationDraft(
            kind=RecommendationKind.DETERMINISTIC_CORRECTION,
            evidence_level=RecommendationEvidenceLevel.DETERMINISTIC,
            rationale_code="AUTHORITATIVE_MAPPING",
            explanation=(
                "Um mapeamento autoritativo configurado determina um único valor. "
                "A correção deve ser feita no NG; o TON não altera a origem."
            ),
            target_field=target_field,
            suggested_value=authoritative,
            candidate_count=candidates or None,
        )
    return RecommendationDraft(
        kind=ambiguous_kind,
        evidence_level=(
            RecommendationEvidenceLevel.AMBIGUOUS
            if candidates > 1
            else RecommendationEvidenceLevel.INSUFFICIENT_EVIDENCE
        ),
        rationale_code=(
            "MULTIPLE_CANDIDATES_NO_AUTHORITY" if candidates > 1 else "NO_CANDIDATE"
        ),
        explanation=ambiguous_explanation,
        target_field=target_field,
        candidate_count=candidates or None,
    )


def build_recommendation(
    definition: RuleDefinition, detection: Detection
) -> RecommendationDraft:
    key = definition.key
    if key == "NGF-SRC-ROW-REJECTED":
        if detection.scope is DetectionScope.EXECUTION:
            return RecommendationDraft(
                kind=RecommendationKind.SOURCE_CORRECTION_REQUIRED,
                evidence_level=RecommendationEvidenceLevel.INSUFFICIENT_EVIDENCE,
                rationale_code="ROWS_NOT_LOCATED",
                explanation=(
                    "Revise as linhas rejeitadas na origem e gere nova exportação. "
                    "As linhas não foram localizadas individualmente."
                ),
            )
        column = detection.facts.get("column")
        return RecommendationDraft(
            kind=RecommendationKind.SOURCE_CORRECTION_REQUIRED,
            evidence_level=RecommendationEvidenceLevel.HIGH_EVIDENCE,
            rationale_code="ROW_NOT_PARSEABLE",
            explanation=(
                "Corrija o lançamento no NG e gere nova exportação. O TON não "
                "infere nem preenche o valor ausente."
            ),
            target_field=COLUMN_MAP.get(column) if isinstance(column, str) else None,
        )
    if key == "NGF-UNIT-MISSING":
        return _value_recommendation(
            definition,
            detection,
            target_field="administrative_unit",
            ambiguous_kind=RecommendationKind.SOURCE_CORRECTION_REQUIRED,
            ambiguous_explanation=(
                "Informe a unidade administrativa no NG. Nenhum valor é sugerido "
                "porque não há evidência estruturada que determine uma única unidade."
            ),
        )
    if key == "NGF-DUP-EXACT":
        return RecommendationDraft(
            kind=RecommendationKind.REQUEST_JUSTIFICATION,
            evidence_level=RecommendationEvidenceLevel.AMBIGUOUS,
            rationale_code="IDENTICAL_CONTENT_NOT_PROOF",
            explanation=(
                "Confirme com o Financeiro se os lançamentos são repetições "
                "legítimas. Se houver duplicidade, o estorno deve ser feito no NG."
            ),
            candidate_count=len(detection.record_ids),
        )
    if key == "NGF-ACCT-LABEL-DRIFT":
        return _value_recommendation(
            definition,
            detection,
            target_field="account_label",
            ambiguous_kind=RecommendationKind.REVIEW_CLASSIFICATION,
            ambiguous_explanation=(
                "Confirme no plano de contas qual descrição vale para o código. "
                "Há mais de uma descrição possível e nenhuma referência autoritativa."
            ),
        )
    if key == "NGF-UNIT-LABEL-DRIFT":
        return _value_recommendation(
            definition,
            detection,
            target_field="administrative_unit",
            ambiguous_kind=RecommendationKind.REQUEST_INFORMATION,
            ambiguous_explanation=(
                "Confirme no cadastro de unidades qual descrição vale para o código."
            ),
        )
    return RecommendationDraft(
        kind=RecommendationKind.NO_SAFE_RECOMMENDATION,
        evidence_level=RecommendationEvidenceLevel.INSUFFICIENT_EVIDENCE,
        rationale_code="NO_POLICY",
        explanation="Não há evidência suficiente para recomendar uma ação.",
    )
