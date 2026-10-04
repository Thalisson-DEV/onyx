"""Excel workbook of the classification table for the Controladoria to check.

Yellow columns are for the reviewer, mirroring the conferência workbook sent on
2026-10-03. The module is pure: the caller supplies an authorized table.
"""

import datetime
import io

import xlsxwriter

from onyx.ton.account_classification.models import (
    ClassificationOrigin,
    ClassificationStatus,
    ClassificationTable,
    SuggestionConfidence,
)

STATUS_LABELS = {
    ClassificationStatus.PENDING: "Sem classificação",
    ClassificationStatus.AWAITING_CONFIRMATION: "Aguardando confirmação",
    ClassificationStatus.CONFIRMED: "Confirmada",
}
ORIGIN_LABELS = {
    ClassificationOrigin.CONTROLLER_WORKBOOK: "Planilha da Controladoria",
    ClassificationOrigin.ANALOGY: "Semelhança (TON)",
    ClassificationOrigin.MANUAL: "Decisão manual",
}
CONFIDENCE_LABELS = {
    SuggestionConfidence.HIGH: "Alta",
    SuggestionConfidence.MEDIUM: "Média",
    SuggestionConfidence.LOW: "Baixa",
}
MONTHS = (
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
)


def _month_label(period: str) -> str:
    year, month = period.split("-")
    return f"{MONTHS[int(month) - 1]}/{year[2:]} (R$)"


def build_workbook(
    table: ClassificationTable, generated_at: datetime.datetime
) -> bytes:
    output = io.BytesIO()
    book = xlsxwriter.Workbook(output, {"in_memory": True})
    header = book.add_format(
        {
            "bold": True,
            "bg_color": "#1F3A5F",
            "font_color": "#FFFFFF",
            "text_wrap": True,
            "valign": "top",
        }
    )
    review = book.add_format(
        {"bold": True, "bg_color": "#FFE699", "text_wrap": True, "valign": "top"}
    )
    fill = book.add_format({"bg_color": "#FFF2CC"})
    money = book.add_format({"num_format": "#,##0.00;[Red]-#,##0.00"})
    wrap = book.add_format({"text_wrap": True, "valign": "top"})
    title = book.add_format({"bold": True, "font_size": 14})

    sheet = book.add_worksheet("Classificação")
    sheet.write(
        0, 0, f"TON · Classificação das contas do NG · {table.source_name}", title
    )
    sheet.write(
        1,
        0,
        f"Gerado em {generated_at:%d/%m/%Y %H:%M}. Colunas amarelas: para a Controladoria preencher.",
    )
    columns = [
        ("Código", 11),
        ("Descrição da conta no NG", 34),
        ("Natureza no TON", 26),
        ("Grupo da DRE", 22),
        ("Situação", 20),
        ("Origem", 22),
        ("Motivo / decisão", 48),
        ("Padrão do prefixo", 30),
        ("Sugestão do assistente", 26),
        ("Confiança", 10),
        ("Justificativa da sugestão", 52),
        ("Lançamentos", 11),
        ("Total (R$)", 15),
        *[(_month_label(period), 14) for period in table.periods],
        ("Unidades", 40),
    ]
    reviewer = [
        ("Confere?", 10),
        ("Natureza correta (se não confere)", 26),
        ("Observação", 40),
    ]
    row = 3
    for index, (name, width) in enumerate(columns):
        sheet.write(row, index, name, header)
        sheet.set_column(index, index, width)
    first_review = len(columns)
    for offset, (name, width) in enumerate(reviewer):
        sheet.write(row, first_review + offset, name, review)
        sheet.set_column(first_review + offset, first_review + offset, width)
    sheet.freeze_panes(row + 1, 2)

    for item in table.rows:
        row += 1
        suggestion = item.suggestion
        pattern = (
            f"{item.pattern.prefix}: {item.pattern.matches}/{item.pattern.total} "
            f"{item.pattern.natureza}"
            if item.pattern
            else ""
        )
        values: list[object] = [
            item.account_code,
            item.description,
            item.natureza or "",
            item.dre_group or "",
            STATUS_LABELS[item.status],
            ORIGIN_LABELS[item.origin] if item.origin else "",
            item.reason or "",
            pattern,
            suggestion.natureza if suggestion else "",
            CONFIDENCE_LABELS[suggestion.confidence] if suggestion else "",
            suggestion.rationale if suggestion else "",
            item.entries,
        ]
        for index, value in enumerate(values):
            sheet.write(row, index, value, wrap if isinstance(value, str) else None)
        column = len(values)
        sheet.write_number(row, column, float(item.total_amount), money)
        for period in table.periods:
            column += 1
            sheet.write_number(row, column, float(item.monthly.get(period, 0)), money)
        sheet.write(row, column + 1, ", ".join(item.units), wrap)
        for offset in range(len(reviewer)):
            sheet.write_blank(row, first_review + offset, None, fill)
    if table.rows:
        sheet.autofilter(3, 0, row, first_review + len(reviewer) - 1)
        sheet.data_validation(
            4,
            first_review,
            row,
            first_review,
            {"validate": "list", "source": ["Sim", "Não"]},
        )
        sheet.data_validation(
            4,
            first_review + 1,
            row,
            first_review + 1,
            {
                "validate": "list",
                "source": "=Naturezas!$A$2:$A$" + str(len(table.natures) + 1),
            },
        )

    natures = book.add_worksheet("Naturezas")
    natures.write_row(0, 0, ["Natureza", "Grupo da DRE"], header)
    natures.set_column(0, 1, 32)
    for index, nature in enumerate(table.natures, start=1):
        natures.write_row(index, 0, [nature.natureza, nature.dre_group])
    book.close()
    return output.getvalue()
