"""Pure rules of the account classification module."""

import datetime
import io
from decimal import Decimal
from uuid import uuid4

from openpyxl import load_workbook

from onyx.ton.account_classification.logic import (
    BriefingItem,
    SuggestionInput,
    batches,
    build_briefing_prompt,
    build_prompt,
    code_prefixes,
    default_status,
    infer_origin,
    parse_briefing,
    parse_suggestions,
    prefix_pattern,
)
from onyx.ton.account_classification.models import (
    ClassificationOrigin,
    ClassificationRow,
    ClassificationStatus,
    ClassificationTable,
    NatureView,
    SuggestionConfidence,
)
from onyx.ton.account_classification.xlsx_export import build_workbook

NATURES = ["FOLHA", "DESPESAS ADMINISTRATIVAS", "MOVIMENTOS NÃO GERENCIAIS"]


def test_origin_from_setup_reasons() -> None:
    analogy = (
        "Natureza FOLHA: folha paga no NG; a controladoria usa a folha FG "
        "(conta ausente do BANCO DE DADOS da controladoria)"
    )
    workbook = (
        "Natureza DESPESAS COM FROTA conforme aba BANCO DE DADOS da planilha "
        "Banco de Dados (Vale Norte).xlsm da controladoria"
    )
    assert infer_origin(analogy) is ClassificationOrigin.ANALOGY
    assert infer_origin(workbook) is ClassificationOrigin.CONTROLLER_WORKBOOK
    assert infer_origin("Reclassificado pela Luyla") is ClassificationOrigin.MANUAL
    assert infer_origin(None) is ClassificationOrigin.MANUAL
    assert (
        default_status(ClassificationOrigin.ANALOGY)
        is ClassificationStatus.AWAITING_CONFIRMATION
    )
    assert (
        default_status(ClassificationOrigin.CONTROLLER_WORKBOOK)
        is ClassificationStatus.CONFIRMED
    )


def test_prefix_pattern_uses_deepest_prefix_and_ignores_itself() -> None:
    assert code_prefixes("8.4.0013") == ["8.4", "8"]
    assert code_prefixes("4.1") == ["4"]
    confirmed = [
        ("8.4.0001", "DESPESAS ADMINISTRATIVAS"),
        ("8.4.0004", "DESPESAS ADMINISTRATIVAS"),
        ("8.4.0005", "LOCAÇÃO"),
        ("8.1.0001", "LOCAÇÃO"),
        ("8.4.0013", "FOLHA"),
    ]
    pattern = prefix_pattern("8.4.0013", confirmed)
    assert pattern is not None
    assert (pattern.prefix, pattern.natureza, pattern.matches, pattern.total) == (
        "8.4",
        "DESPESAS ADMINISTRATIVAS",
        2,
        3,
    )
    fallback = prefix_pattern("8.9.0001", confirmed)
    assert fallback is not None and fallback.prefix == "8"
    assert prefix_pattern("4.1", confirmed) is None


def test_parse_keeps_only_known_codes_and_natures() -> None:
    text = """```json
    {"sugestoes": [
      {"codigo": "3.1.0001", "natureza": "folha", "confianca": "ALTA",
       "justificativa": "Salário pago no NG.",
       "pergunta": "Salário líquido   pago no NG entra como FOLHA?"},
      {"codigo": "4.1", "natureza": "MÚTUO", "confianca": "ALTA",
       "justificativa": "Natureza inventada."},
      {"codigo": "9.9.9999", "natureza": "FOLHA", "confianca": "ALTA",
       "justificativa": "Código não pedido."},
      {"codigo": "7.2", "natureza": "MOVIMENTOS NÃO GERENCIAIS",
       "confianca": "média", "justificativa": "Fundo fixo é adiantamento."}
    ]}
    ```"""
    outcome = parse_suggestions(text, ["3.1.0001", "4.1", "7.2"], NATURES)
    assert [
        (item.code, item.natureza, item.confidence) for item in outcome.suggestions
    ] == [
        ("3.1.0001", "FOLHA", SuggestionConfidence.HIGH),
        ("7.2", "MOVIMENTOS NÃO GERENCIAIS", SuggestionConfidence.MEDIUM),
    ]
    assert outcome.rejected == ["4.1"]
    assert outcome.suggestions[0].question == (
        "Salário líquido pago no NG entra como FOLHA?"
    )
    assert outcome.suggestions[1].question is None


def test_briefing_prompt_and_parse() -> None:
    items = [
        BriefingItem(
            code="3.1.0020",
            description="Emprestimo Consignado",
            current="FOLHA",
            current_group="2 CUSTOS MÃO DE OBRA",
            suggested="MOVIMENTOS NÃO GERENCIAIS",
            suggested_group="Fora do resultado",
            confidence=SuggestionConfidence.MEDIUM,
            total_amount="-928548.04",
            question="Consignado é custo ou repasse?",
        ),
        BriefingItem(
            code="4.1",
            description="Delta Park (R)",
            current="MOVIMENTOS NÃO GERENCIAIS",
            current_group="Fora do resultado",
            suggested="MOVIMENTOS NÃO GERENCIAIS",
            suggested_group="Fora do resultado",
            confidence=SuggestionConfidence.HIGH,
            total_amount="172380.66",
            question="Mútuo fica fora?",
        ),
    ]
    prompt = build_briefing_prompt(items)
    assert "3.1.0020" in prompt and "| diverge" in prompt and "| concorda" in prompt
    assert "pergunta: Consignado é custo ou repasse?" in prompt
    assert "Mútuo fica fora?" not in prompt
    assert parse_briefing('{"resumo": "  Tudo certo.  "}') == "Tudo certo."
    assert parse_briefing("sem json") is None
    assert parse_briefing('{"resumo": ""}') is None


def test_parse_rejects_everything_on_garbage() -> None:
    outcome = parse_suggestions("não sei", ["3.1.0001"], NATURES)
    assert outcome.suggestions == []
    assert outcome.rejected == ["3.1.0001"]


def _target(code: str) -> SuggestionInput:
    return SuggestionInput(
        code=code,
        description="Fundo fixo",
        current_natureza="MOVIMENTOS NÃO GERENCIAIS",
        entries=6,
        total_amount="-23731.37",
        units=["TOLEDO-PR"],
        history=["REPOSICAO FUNDO FIXO " + "X" * 300],
        pattern=None,
    )


def test_prompt_carries_evidence_and_truncates_history() -> None:
    prompt = build_prompt(
        [_target("7.2")],
        [("FOLHA", "2 CUSTOS MÃO DE OBRA")],
        [("3.1.0005", "Salário", "FOLHA")],
    )
    assert "- FOLHA -> 2 CUSTOS MÃO DE OBRA" in prompt
    assert "- 3.1.0005 | Salário | FOLHA" in prompt
    assert "## 7.2 | Fundo fixo" in prompt
    assert "ainda não confirmada: MOVIMENTOS NÃO GERENCIAIS" in prompt
    history_line = next(line for line in prompt.splitlines() if "FUNDO FIXO" in line)
    assert len(history_line) <= len("Histórico: ") + 140
    assert [len(batch) for batch in batches([_target(str(i)) for i in range(12)])] == [
        5,
        5,
        2,
    ]


def test_workbook_lists_rows_with_review_columns() -> None:
    nature = NatureView(
        account_id=uuid4(),
        code="2.01",
        natureza="FOLHA",
        dre_group="2 CUSTOS MÃO DE OBRA",
        dre_group_code="g2",
        accounts=1,
    )
    table = ClassificationTable(
        source_id=uuid4(),
        source_name="NG Vale Norte",
        normalization_run_id=None,
        periods=["2026-05", "2026-06"],
        natures=[nature],
        groups=[],
        briefing=None,
        changes_since_calculation=0,
        rows=[
            ClassificationRow(
                account_code="3.1.0001",
                description="Salarios (Liquido)",
                account_id=nature.account_id,
                natureza="FOLHA",
                dre_group=nature.dre_group,
                status=ClassificationStatus.AWAITING_CONFIRMATION,
                origin=ClassificationOrigin.ANALOGY,
                reason="Folha paga no NG",
                decided_by=None,
                decided_at=None,
                decided_by_person=False,
                entries=2,
                total_amount=Decimal("-10.50"),
                monthly={"2026-05": Decimal("-4"), "2026-06": Decimal("-6.5")},
                units=["TOLEDO-PR"],
                pattern=None,
                suggestion=None,
            )
        ],
    )
    content = build_workbook(table, datetime.datetime(2026, 10, 4, 12, 0))
    book = load_workbook(io.BytesIO(content))
    sheet = book["Classificação"]
    header = [cell.value for cell in sheet[4]]
    assert header[:3] == ["Código", "Descrição da conta no NG", "Natureza no TON"]
    assert header[-3:] == [
        "Confere?",
        "Natureza correta (se não confere)",
        "Observação",
    ]
    assert "Mai/26 (R$)" in header and "Jun/26 (R$)" in header
    row = [cell.value for cell in sheet[5]]
    assert row[0] == "3.1.0001"
    assert row[4] == "Aguardando confirmação"
    assert row[header.index("Total (R$)")] == -10.5
    assert book["Naturezas"]["A2"].value == "FOLHA"
