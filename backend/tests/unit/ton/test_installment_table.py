import datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

import pytest
from openpyxl import Workbook

from onyx.error_handling.exceptions import OnyxError
from onyx.ton.ng_financial.installments import (
    DEFAULT_ACCOUNT,
    InstallmentTableParser,
    parse_month,
)

SNAPSHOT = UUID(int=7)


def _book(sheets: dict[str, list[list[object]]]) -> bytes:
    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def test_rows_become_outflows_by_month_and_unit() -> None:
    content = _book(
        {
            "Como preencher": [["Preencha a aba Parcelamentos."]],
            "Parcelamentos": [
                ["Parcelamentos pagos 2026"],
                [
                    "Mês",
                    "Data de pagamento",
                    "Unidade",
                    "Conta NG",
                    "Credor",
                    "Nº do parcelamento",
                    "Parcela",
                    "Valor pago",
                ],
                [
                    "01/2026",
                    datetime.datetime(2026, 1, 30),
                    "000001 - ADMINISTRAÇÃO CENTRAL",
                    "2.4.0002 - Parcelamento Tributos",
                    "Receita Federal",
                    "123",
                    "3/60",
                    12345.67,
                ],
                ["fev/26", None, "000009", None, "PGFN", None, None, "R$ 1.000,00"],
                [None, None, None, None, None, None, None, None],
                ["Total", None, None, None, None, None, None, 13345.67],
            ],
        }
    )
    result = InstallmentTableParser().parse(content, SNAPSHOT)
    assert [record.account_code for record in result.records] == [
        "2.4.0002",
        DEFAULT_ACCOUNT,
    ]
    first, second = result.records
    assert first.account_label == "Parcelamento Tributos"
    assert first.emission_date == datetime.date(2026, 1, 30)
    assert first.sheet_month == 1
    assert first.movement_amount == first.final_amount == Decimal("-12345.67")
    assert first.history == "Receita Federal · parcela 3/60"
    assert first.document_number == "123"
    assert first.administrative_unit == "000001 - ADMINISTRAÇÃO CENTRAL"
    assert first.locator.row_number == 3
    assert second.emission_date == datetime.date(2026, 2, 1)
    assert second.final_amount == Decimal("-1000.00")
    assert {item.code for item in result.diagnostics} == {"SHEET_OUT_OF_SCOPE"}


def test_bad_rows_are_reported_where_they_are() -> None:
    content = _book(
        {
            "P": [
                ["Unidade", "Mês", "Valor"],
                ["000001", "13/2026", 10],
                ["000001", "03/2026", "dez reais"],
                [None, "03/2026", 5],
            ]
        }
    )
    result = InstallmentTableParser().parse(content, SNAPSHOT)
    assert len(result.records) == 1
    assert {(item.code, item.row_number, item.column) for item in result.diagnostics} == {
        ("INVALID_DATE", 2, "B"),
        ("INVALID_AMOUNT", 3, "C"),
        ("UNIT_BLANK", 4, "A"),
    }


def test_a_workbook_without_the_table_is_refused() -> None:
    with pytest.raises(OnyxError):
        InstallmentTableParser().parse(_book({"X": [["a", "b"], [1, 2]]}), SNAPSHOT)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("01/2026", datetime.date(2026, 1, 1)),
        ("2026-09", datetime.date(2026, 9, 1)),
        ("set/26", datetime.date(2026, 9, 1)),
        ("Setembro de 2026", datetime.date(2026, 9, 1)),
        (datetime.datetime(2026, 5, 17), datetime.date(2026, 5, 1)),
        ("15/07/2026", datetime.date(2026, 7, 1)),
    ],
)
def test_months_in_the_ways_people_write_them(
    value: object, expected: datetime.date
) -> None:
    assert parse_month(value) == expected


def test_pasted_rows_read_like_the_template() -> None:
    from onyx.ton.client_import.models import PastedTable
    from onyx.ton.client_import.service import _pasted_workbook

    table = PastedTable(
        rows=[
            ["Mês", "Unidade", "Conta NG", "Valor pago"],
            ["01/2026", "000001 - ADMINISTRAÇÃO CENTRAL", "2.4.0002", "45.000,00"],
            ["fev/26", "000009", "", "R$ 1.000,50"],
            ["13/2026", "000009", "", "10"],
        ]
    )
    result = InstallmentTableParser().parse(_pasted_workbook(table), SNAPSHOT)
    assert [record.final_amount for record in result.records] == [
        Decimal("-45000.00"),
        Decimal("-1000.50"),
    ]
    assert [(item.code, item.row_number) for item in result.diagnostics] == [
        ("INVALID_DATE", 4)
    ]
