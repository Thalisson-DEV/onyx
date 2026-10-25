"""The payment batch workbook: what whoever pays needs, one row per title.

It replaces printing the invoice and the boleto: payee, CPF/CNPJ, how to pay,
amount and due date, with a subtotal per day. The attachments go in a .zip
with the same standard names the "Boleto" column lists.
"""

import datetime
import io
from dataclasses import dataclass
from decimal import Decimal
from itertools import groupby

import xlsxwriter

GREEN = "#145C42"


@dataclass(frozen=True)
class BatchRow:
    due_date: datetime.date
    number: str
    unit: str
    payee: str
    tax_id: str
    method: str
    pix_key: str
    bank: str
    document: str
    installment: str
    nature: str
    amount: Decimal
    ng_history: str
    boleto_file: str


COLUMNS = (
    ("Vencimento", 12),
    ("Título", 12),
    ("Unidade", 18),
    ("Favorecido", 34),
    ("CPF/CNPJ", 20),
    ("Pagar por", 12),
    ("Chave PIX", 26),
    ("Banco · agência · conta", 24),
    ("Documento", 16),
    ("Parcela", 8),
    ("Natureza", 24),
    ("Valor (R$)", 14),
    ("Histórico para o NG", 60),
    ("Arquivo do boleto", 44),
    ("Pago em", 12),
)


def build_xlsx(
    rows: list[BatchRow], generated_at: datetime.datetime | None = None
) -> bytes:
    generated_at = generated_at or datetime.datetime.now()
    output = io.BytesIO()
    book = xlsxwriter.Workbook(output, {"in_memory": True})
    title = book.add_format({"bold": True, "font_size": 14, "font_color": GREEN})
    header = book.add_format(
        {"bold": True, "bg_color": GREEN, "font_color": "#FFFFFF", "valign": "top"}
    )
    payer = book.add_format({"bold": True, "bg_color": "#FFE699"})
    date = book.add_format({"num_format": "dd/mm/yyyy"})
    money = book.add_format({"num_format": "#,##0.00"})
    day = book.add_format({"bold": True, "bg_color": "#E7F1EC"})
    day_money = book.add_format(
        {"bold": True, "bg_color": "#E7F1EC", "num_format": "#,##0.00"}
    )
    total_format = book.add_format({"bold": True, "top": 1, "num_format": "#,##0.00"})
    bold = book.add_format({"bold": True, "top": 1})

    sheet = book.add_worksheet("Lote de pagamento")
    sheet.write(0, 0, "TON · Lote de pagamento", title)
    sheet.write(
        1,
        0,
        f"Gerado em {generated_at:%d/%m/%Y %H:%M} · {len(rows)} títulos. "
        "A coluna amarela é para quem paga marcar a data do pagamento.",
    )
    row = 3
    for index, (name, width) in enumerate(COLUMNS):
        sheet.write(row, index, name, payer if name == "Pago em" else header)
        sheet.set_column(index, index, width)
    sheet.freeze_panes(row + 1, 0)
    amount_col = [name for name, _ in COLUMNS].index("Valor (R$)")

    total = Decimal(0)
    for due, group in groupby(rows, key=lambda item: item.due_date):
        items = list(group)
        subtotal = sum((item.amount for item in items), Decimal(0))
        total += subtotal
        row += 1
        sheet.write(row, 0, f"{due:%d/%m/%Y} · {len(items)} título(s)", day)
        for column in range(1, len(COLUMNS)):
            if column == amount_col:
                sheet.write_number(row, column, float(subtotal), day_money)
            else:
                sheet.write_blank(row, column, None, day)
        for item in items:
            row += 1
            sheet.write_datetime(
                row,
                0,
                datetime.datetime.combine(item.due_date, datetime.time()),
                date,
            )
            values = (
                item.number,
                item.unit,
                item.payee,
                item.tax_id,
                item.method,
                item.pix_key,
                item.bank,
                item.document,
                item.installment,
                item.nature,
            )
            for offset, value in enumerate(values, start=1):
                sheet.write_string(row, offset, value)
            sheet.write_number(row, amount_col, float(item.amount), money)
            sheet.write_string(row, amount_col + 1, item.ng_history)
            sheet.write_string(row, amount_col + 2, item.boleto_file)
    row += 1
    sheet.write(row, amount_col - 1, "Total do lote", bold)
    sheet.write_number(row, amount_col, float(total), total_format)
    book.close()
    return output.getvalue()
