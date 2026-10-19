import datetime
from io import BytesIO

from openpyxl import Workbook

from onyx.ton.client_import.row_preview import read_rows
from onyx.ton.ng_financial.parser import HEADER
from onyx.ton.sources.models import SourceFormat


def _xlsx(rows: dict[str, list[list[object]]]) -> bytes:
    book = Workbook()
    book.remove(book.active)
    for name, values in rows.items():
        sheet = book.create_sheet(name)
        for row in values:
            sheet.append(row)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def test_billing_row_uses_the_header_above_it() -> None:
    content = _xlsx(
        {
            "FILIAL": [
                ["Tomador", "Nº da Nota", "Data de Emissão", "Valor", "ISS"],
                ["MOSSORÓ", 30, "24/04 2017", 261687.29, 0],
                ["Tomador", "Número", "Emissão", "Valor", "ISS"],
                ["NATAL", 31, datetime.datetime(2026, 5, 2), 10.0, 0],
            ]
        }
    )
    rows = read_rows(content, SourceFormat.XLSX, {"FILIAL": {2, 4}})
    first = {cell.column: cell for cell in rows[("FILIAL", 2)]}
    assert first["C"].header == "Data de Emissão"
    assert first["C"].value == "24/04 2017"
    assert first["D"].value == "261687,29"
    second = {cell.column: cell for cell in rows[("FILIAL", 4)]}
    assert second["C"].header == "Emissão"
    assert second["C"].value == "02/05/2026"


def test_ng_row_gets_named_columns_and_its_block_account() -> None:
    content = _xlsx(
        {
            "Jan Fin": [
                ["8.1.0001 - Locação", datetime.datetime(2026, 1, 30), "ADM", 1, "A"],
                [None, datetime.datetime(2026, 1, 31), None, 2, "B"],
            ]
        }
    )
    cells = read_rows(content, SourceFormat.XLSX, {"Jan Fin": {2}}, HEADER)[
        ("Jan Fin", 2)
    ]
    assert cells[0].header == f"{HEADER[0]} (bloco)"
    assert cells[0].value == "8.1.0001 - Locação"
    assert {cell.header for cell in cells[1:]} >= {"Emissão", "Número"}


def test_missing_sheet_or_row_is_left_out() -> None:
    content = _xlsx({"A": [["x"]]})
    assert read_rows(content, SourceFormat.XLSX, {"B": {1}, "A": {5}}) == {}
