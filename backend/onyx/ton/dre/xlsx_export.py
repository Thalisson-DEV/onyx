"""Excel workbook of a persisted DRE: formulas over the contributing entries.

The DRE sheet computes each line with SUMIFS over the Base table and with the
structure's declarative formulas translated to cell references. Every formula
also carries its cached value, so viewers that do not recalculate show the
same figure. The module is pure: the caller supplies already authorized data.
"""

import datetime
import io
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell
from xlsxwriter.worksheet import Worksheet

from onyx.ton.dre.engine import calculation_order, evaluate_lines
from onyx.ton.dre.models import DreLineDefinition, DreLineType, DreOperation

MONTH_NAMES = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)
BASE_TABLE = "Base"
NO_UNIT_LABEL = "Sem unidade"
MONEY_FORMAT = "#,##0.00;[Red]-#,##0.00"
AMOUNT_BASIS_LABELS = {"MOVEMENT": "Movimento", "FINAL": "Valor final"}
REVIEW_LABELS = {
    "ACCEPTED": "Aceito",
    "JUSTIFIED_EXCEPTION": "Exceção justificada",
}

# Base columns, in order. Formulas reference the first five by name.
BASE_COLUMNS: tuple[tuple[str, int], ...] = (
    ("Competência", 12),
    ("Unidade", 12),
    ("Linha DRE", 10),
    ("Valor", 16),
    ("Data", 12),
    ("Nome da unidade", 28),
    ("Descrição da linha", 34),
    ("Natureza", 30),
    ("Conta NG", 12),
    ("Descrição da conta NG", 34),
    ("Documento", 16),
    ("Histórico", 50),
    ("Base do valor", 13),
    ("Situação na revisão", 20),
    ("Arquivo", 30),
    ("Planilha · linha", 18),
)


@dataclass(frozen=True)
class BaseEntry:
    """One NG entry that composes a DRE source line."""

    competence: datetime.date
    unit_code: str | None
    unit_name: str | None
    line_code: str
    amount: Decimal
    record_date: datetime.date | None
    nature: str
    ng_account_code: str | None
    ng_account_label: str | None
    document: str | None
    history: str | None
    amount_basis: str
    review_status: str | None
    source_file: str
    sheet_name: str
    row_number: int


@dataclass(frozen=True)
class ScopeBlock:
    """Consolidated (unit_code None) or one unit, with its READY months."""

    unit_code: str | None
    label: str
    ready_months: frozenset[int]


@dataclass(frozen=True)
class Premise:
    topic: str
    status: str
    effect: str


@dataclass(frozen=True)
class DreWorkbookInput:
    structure_label: str
    structure_version: int
    lines: list[DreLineDefinition]
    year: int
    last_month: int
    scopes: list[ScopeBlock]
    entries: list[BaseEntry]
    header: list[tuple[str, str]]
    premises: list[Premise] = field(default_factory=list)


ScopeValues = dict[tuple[int | None, str], Decimal | None]
"""(month, line code) to value; month None is the year to date."""


def expected_values(data: DreWorkbookInput) -> dict[str | None, ScopeValues]:
    """The values every formula of the DRE sheet evaluates to, per scope."""
    totals: dict[str | None, dict[int, dict[str, Decimal]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(Decimal))
    )
    for entry in data.entries:
        month = entry.competence.month
        totals[None][month][entry.line_code] += entry.amount
        if entry.unit_code is not None:
            totals[entry.unit_code][month][entry.line_code] += entry.amount
    result: dict[str | None, ScopeValues] = {}
    for scope in data.scopes:
        by_month = totals[scope.unit_code]
        values: ScopeValues = {}
        year_to_date: dict[str, Decimal] = defaultdict(Decimal)
        for month in range(1, data.last_month + 1):
            for code, amount in by_month[month].items():
                year_to_date[code] += amount
            for code, value in evaluate_lines(data.lines, by_month[month]).items():
                values[(month, code)] = value
        for code, value in evaluate_lines(data.lines, year_to_date).items():
            values[(None, code)] = value
        result[scope.unit_code] = values
    return result


def _depths(lines: list[DreLineDefinition]) -> dict[str, int]:
    by_code = {line.code: line for line in lines}
    depths: dict[str, int] = {}
    for line in lines:
        depth = 0
        parent = line.parent_code
        while parent is not None:
            depth += 1
            parent = by_code[parent].parent_code
        depths[line.code] = depth
    return depths


def _cell_formula(
    line: DreLineDefinition,
    children: dict[str, list[str]],
    row_of: dict[str, int],
    column: int,
) -> str:
    def ref(code: str) -> str:
        return xl_rowcol_to_cell(row_of[code], column)

    if line.operation in (DreOperation.SUM_CHILDREN, DreOperation.SUM_LINES):
        operands = (
            children[line.code]
            if line.operation == DreOperation.SUM_CHILDREN
            else line.operands
        )
        return "=" + "+".join(ref(code) for code in operands)
    if line.operation == DreOperation.SUBTRACT:
        return f"={ref(line.operands[0])}-{ref(line.operands[1])}"
    numerator, denominator = ref(line.operands[0]), ref(line.operands[1])
    return f'=IF({denominator}=0,"",{numerator}/{denominator}*100)'


def _cached(value: Decimal | None) -> float | str:
    return "" if value is None else float(value)


class _Formats:
    def __init__(self, workbook: xlsxwriter.Workbook) -> None:
        self.title = workbook.add_format({"bold": True, "font_size": 14})
        self.note = workbook.add_format({"italic": True, "font_color": "#595959"})
        self.block = workbook.add_format(
            {"bold": True, "font_size": 12, "bg_color": "#DDEBF7"}
        )
        self.header = workbook.add_format(
            {"bold": True, "bottom": 1, "bg_color": "#F2F2F2"}
        )
        self.month = workbook.add_format(
            {
                "bold": True,
                "bottom": 1,
                "bg_color": "#F2F2F2",
                "num_format": "mmm/yyyy",
                "align": "right",
            }
        )
        self.status_ready = workbook.add_format(
            {"font_color": "#375623", "align": "right", "italic": True}
        )
        self.status_blocked = workbook.add_format(
            {"font_color": "#C00000", "align": "right", "italic": True}
        )
        self.money = workbook.add_format({"num_format": MONEY_FORMAT})
        self.money_bold = workbook.add_format(
            {"num_format": MONEY_FORMAT, "bold": True}
        )
        self.money_muted = workbook.add_format(
            {"num_format": MONEY_FORMAT, "font_color": "#A6A6A6", "italic": True}
        )
        self.percent = workbook.add_format({"num_format": "0.00"})
        self.text_bold = workbook.add_format({"bold": True})
        self.indent = [workbook.add_format({"indent": level}) for level in range(4)]
        self.date = workbook.add_format({"num_format": "dd/mm/yyyy"})
        self.competence = workbook.add_format({"num_format": "mm/yyyy"})
        self.wrap = workbook.add_format({"text_wrap": True, "valign": "top"})
        self.wrap_bold = workbook.add_format(
            {"text_wrap": True, "valign": "top", "bold": True}
        )


def _write_header(
    sheet: Worksheet, formats: _Formats, title: str, data: DreWorkbookInput
) -> int:
    sheet.write(0, 0, title, formats.title)
    row = 1
    for label, value in data.header:
        sheet.write(row, 0, label, formats.note)
        sheet.write(row, 1, value, formats.note)
        row += 1
    return row + 1


def _write_dre_sheet(
    workbook: xlsxwriter.Workbook,
    formats: _Formats,
    data: DreWorkbookInput,
    expected: dict[str | None, ScopeValues],
) -> None:
    sheet = workbook.add_worksheet("DRE")
    sheet.set_column(0, 0, 10)
    sheet.set_column(1, 1, 44)
    sheet.set_column(2, data.last_month + 2, 15)
    sheet.freeze_panes(0, 2)
    row = _write_header(sheet, formats, f"DRE gerencial — {data.structure_label}", data)
    sheet.write(
        row - 1,
        0,
        "Realizado em R$. As linhas somam a aba Base; você pode acrescentar "
        "linhas, colunas e cálculos próprios.",
        formats.note,
    )
    row += 1
    lines = sorted(data.lines, key=lambda item: item.position)
    calculation_order(lines)
    depths = _depths(lines)
    children: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        if line.parent_code is not None:
            children[line.parent_code].append(line.code)
    months = list(range(1, data.last_month + 1))
    ytd_column = data.last_month + 2
    value_columns = 1 + data.last_month
    for scope in data.scopes:
        values = expected[scope.unit_code]
        block_row = row
        sheet.write(block_row, 0, scope.unit_code or "Consolidado", formats.block)
        sheet.write(block_row, 1, scope.label, formats.block)
        for column in range(2, ytd_column + 1):
            sheet.write_blank(block_row, column, None, formats.block)
        status_row = block_row + 1
        sheet.write(status_row, 1, "Situação da DRE no TON", formats.note)
        for month in months:
            ready = month in scope.ready_months
            sheet.write(
                status_row,
                month + 1,
                "Pronta" if ready else "Não pronta",
                formats.status_ready if ready else formats.status_blocked,
            )
        header_row = block_row + 2
        sheet.write(header_row, 0, "Código", formats.header)
        sheet.write(header_row, 1, "Linha", formats.header)
        for month in months:
            sheet.write_datetime(
                header_row,
                month + 1,
                datetime.datetime(data.year, month, 1),
                formats.month,
            )
        sheet.write(header_row, ytd_column, "Acumulado", formats.header)
        row_of = {line.code: header_row + 1 + index for index, line in enumerate(lines)}
        unit_criterion = (
            f",{BASE_TABLE}[Unidade],{xl_rowcol_to_cell(block_row, 0, True, True)}"
            if scope.unit_code is not None
            else ""
        )
        for line in lines:
            line_row = row_of[line.code]
            is_source = line.line_type == DreLineType.SOURCE_SUM
            is_ratio = line.operation == DreOperation.RATIO
            sheet.write(line_row, 0, line.code)
            sheet.write(
                line_row,
                1,
                line.label,
                formats.indent[min(depths[line.code], 3)]
                if is_source
                else formats.text_bold,
            )
            for month in months:
                column = month + 1
                if is_source:
                    month_cell = xl_rowcol_to_cell(header_row, column, True, False)
                    formula = (
                        f"=SUMIFS({BASE_TABLE}[Valor],"
                        f"{BASE_TABLE}[Linha DRE],{xl_rowcol_to_cell(line_row, 0, False, True)},"
                        f"{BASE_TABLE}[Competência],{month_cell}{unit_criterion})"
                    )
                else:
                    formula = _cell_formula(line, children, row_of, column)
                cell_format = (
                    formats.percent
                    if is_ratio
                    else formats.money_muted
                    if month not in scope.ready_months
                    else formats.money
                    if is_source
                    else formats.money_bold
                )
                sheet.write_formula(
                    line_row,
                    column,
                    formula,
                    cell_format,
                    _cached(values[(month, line.code)]),
                )
            if is_source:
                first = xl_col_to_name(2)
                last = xl_col_to_name(value_columns)
                ytd_formula = f"=SUM({first}{line_row + 1}:{last}{line_row + 1})"
            else:
                ytd_formula = _cell_formula(line, children, row_of, ytd_column)
            sheet.write_formula(
                line_row,
                ytd_column,
                ytd_formula,
                formats.percent
                if is_ratio
                else formats.money
                if is_source
                else formats.money_bold,
                _cached(values[(None, line.code)]),
            )
        row = header_row + len(lines) + 2


def _write_base_sheet(
    workbook: xlsxwriter.Workbook,
    formats: _Formats,
    data: DreWorkbookInput,
    line_labels: dict[str, str],
) -> None:
    sheet = workbook.add_worksheet("Base")
    for index, (_, width) in enumerate(BASE_COLUMNS):
        sheet.set_column(index, index, width)
    entries = sorted(
        data.entries,
        key=lambda item: (
            item.competence,
            item.unit_code or "",
            item.line_code,
            item.record_date or datetime.date.max,
            item.source_file,
            item.sheet_name,
            item.row_number,
        ),
    )
    rows = [
        [
            datetime.datetime.combine(entry.competence, datetime.time()),
            entry.unit_code or "",
            entry.line_code,
            float(entry.amount),
            datetime.datetime.combine(entry.record_date, datetime.time())
            if entry.record_date
            else "",
            entry.unit_name or NO_UNIT_LABEL,
            line_labels.get(entry.line_code, entry.line_code),
            entry.nature,
            entry.ng_account_code or "",
            entry.ng_account_label or "",
            entry.document or "",
            entry.history or "",
            AMOUNT_BASIS_LABELS.get(entry.amount_basis, entry.amount_basis),
            REVIEW_LABELS.get(entry.review_status or "", entry.review_status or ""),
            entry.source_file,
            f"{entry.sheet_name} · {entry.row_number}",
        ]
        for entry in entries
    ]
    columns: list[dict[str, object]] = [{"header": name} for name, _ in BASE_COLUMNS]
    columns[0]["format"] = formats.competence
    columns[3]["format"] = formats.money
    columns[4]["format"] = formats.date
    # A table needs at least one data row; an empty Base keeps one blank row.
    sheet.add_table(
        0,
        0,
        max(len(rows), 1),
        len(BASE_COLUMNS) - 1,
        {
            "name": BASE_TABLE,
            "style": "Table Style Light 9",
            "columns": columns,
            "data": rows,
        },
    )
    sheet.freeze_panes(1, 0)


def _write_premises_sheet(
    workbook: xlsxwriter.Workbook, formats: _Formats, data: DreWorkbookInput
) -> None:
    sheet = workbook.add_worksheet("Premissas")
    sheet.set_column(0, 0, 26)
    sheet.set_column(1, 1, 60)
    sheet.set_column(2, 2, 60)
    row = _write_header(sheet, formats, "Premissas e pontos em aberto", data)
    sheet.write(row, 0, "Tema", formats.header)
    sheet.write(row, 1, "Situação no TON", formats.header)
    sheet.write(row, 2, "Efeito nesta planilha", formats.header)
    for premise in data.premises:
        row += 1
        sheet.write(row, 0, premise.topic, formats.wrap_bold)
        sheet.write(row, 1, premise.status, formats.wrap)
        sheet.write(row, 2, premise.effect, formats.wrap)


def build_workbook(data: DreWorkbookInput) -> bytes:
    """Serialize the DRE, Base and Premissas sheets to an .xlsx file."""
    expected = expected_values(data)
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        # NG text such as "=..." or a URL stays text, never a formula or link.
        {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False},
    )
    workbook.set_properties({"title": f"DRE {data.year}", "author": "TON"})
    formats = _Formats(workbook)
    _write_dre_sheet(workbook, formats, data, expected)
    _write_base_sheet(
        workbook,
        formats,
        data,
        {line.code: line.label for line in data.lines},
    )
    _write_premises_sheet(workbook, formats, data)
    workbook.close()
    return output.getvalue()


def month_label(month: int) -> str:
    return MONTH_NAMES[month - 1]
