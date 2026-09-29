"""Deterministic pt-BR explanations rendered from structured facts only.

Templates never include a source value other than structural codes (sheet,
row, column, account or unit code). No LLM is involved.
"""

from collections.abc import Callable

from onyx.ton.financial_review.models import Detection, DetectionScope

_REJECTION_REASONS: dict[str, str] = {
    "INVALID_AMOUNT": "a coluna {column} contém conteúdo que não é um valor monetário válido",
    "MISSING_AMOUNTS": "nenhuma coluna monetária está preenchida",
    "INVALID_DATE": "a data de emissão é inválida",
    "INHERITED_DATE_INVALID": "a linha herda a data de um grupo cuja data é inválida",
    "MISSING_DATE": "não há data de emissão aplicável à linha",
    "UNKNOWN_ROW": "a estrutura da linha não corresponde ao contrato do export",
    "FORMULA_UNSUPPORTED": "a coluna {column} contém fórmula, que o TON não avalia",
}


def _fact(detection: Detection, name: str) -> str:
    value = detection.facts.get(name)
    return "-" if value is None else str(value)


def _rejected(detection: Detection) -> str:
    if detection.scope is DetectionScope.EXECUTION:
        return (
            f"{_fact(detection, 'unlocated_rows')} linhas rejeitadas não puderam ser "
            "localizadas individualmente porque excederam o limite de diagnósticos "
            "armazenados. Os valores dessas linhas não estão no conjunto revisado."
        )
    code = _fact(detection, "diagnostic_code")
    reason = _REJECTION_REASONS.get(code, "a linha não pôde ser interpretada").format(
        column=_fact(detection, "column")
    )
    return (
        f"A linha {_fact(detection, 'row_number')} da planilha "
        f"{_fact(detection, 'sheet_name')} não gerou lançamento porque {reason}. "
        "O valor não foi importado e fica fora do conjunto revisado até ser "
        "corrigido na origem ou justificado."
    )


def _unit_missing(detection: Detection) -> str:
    del detection
    return (
        "Este lançamento não possui unidade administrativa, necessária para "
        "atribuição ao contrato/unidade no fechamento gerencial."
    )


def _duplicate(detection: Detection) -> str:
    document = (
        ""
        if detection.facts.get("document_present")
        else " Os lançamentos não têm número de documento."
    )
    return (
        f"{_fact(detection, 'occurrences')} lançamentos preservados na planilha "
        f"{_fact(detection, 'sheet_name')} têm conteúdo idêntico: conta, data "
        "efetiva, unidade, documento, histórico e todos os valores. Podem ser "
        "lançamentos legítimos repetidos ou duplicidade; a confirmação depende "
        f"do Financeiro. Nenhum lançamento foi removido.{document}"
    )


def _account_drift(detection: Detection) -> str:
    return (
        f"O código de conta {_fact(detection, 'account_code')} aparece com "
        f"{_fact(detection, 'label_count')} descrições diferentes nesta importação. "
        "A classificação não foi alterada."
    )


def _unit_drift(detection: Detection) -> str:
    return (
        f"O código de unidade {_fact(detection, 'unit_code')} aparece com "
        f"{_fact(detection, 'label_count')} descrições diferentes nesta importação. "
        "A unidade dos lançamentos não foi alterada."
    )


EXPLAINERS: dict[str, Callable[[Detection], str]] = {
    "NGF-SRC-ROW-REJECTED": _rejected,
    "NGF-UNIT-MISSING": _unit_missing,
    "NGF-DUP-EXACT": _duplicate,
    "NGF-ACCT-LABEL-DRIFT": _account_drift,
    "NGF-UNIT-LABEL-DRIFT": _unit_drift,
}


def explain(detection: Detection) -> str:
    explainer = EXPLAINERS.get(detection.rule_key)
    if explainer is None:
        return "A regra registrou uma ocorrência que exige revisão humana."
    return explainer(detection)


def explanation_code(detection: Detection) -> str:
    return f"{detection.rule_key}.v{detection.rule_version}"
