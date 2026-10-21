"""Investigations the TON chat runs on the real base: search, suppliers and the
Prompt Mestre financial tests (T1, T2, T3, T4, T6, T8, T9, T10).

Every test is read-only and on demand. Its parameters come back with the
result as "parâmetros do teste": no threshold here is an approved rule, and a
hit is a candidate for a person to check, never a conclusion.
"""

import dataclasses
import datetime
import re
import statistics
import unicodedata
from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import dre
from onyx.db.ton import financial_domain
from onyx.db.ton.acl import business_unit_visible_clause, is_ton_administrator
from onyx.db.ton.agent import financial_context
from onyx.db.ton.agent_overview import resolve_unit, visible_units
from onyx.db.ton.models import (
    BusinessUnit,
    DreAccountMapping,
    FinancialAccount,
    FinancialActualFact,
    FinancialBillingFact,
    FinancialNormalizationRun,
    ParsedSourceRecord,
    SourceSnapshot,
)
from onyx.ton.dre.models import DreLineDefinition, DreLineType

MAX_ITEMS = 30
SUPPLIERS = (
    re.compile(r"PAGAMENTO\s+A\s+(.+?)(?:\s+REF\b|\s*$)", re.IGNORECASE),
    re.compile(r"\bNF\s*\d+\s+DE\s+(.+?)(?:\s+REF\b|\s*$)", re.IGNORECASE),
    re.compile(r"^(?:DEVOLU[ÇC][ÃA]O|ESTORNO)\s+DE\s+(.+?)(?:\s+REF\b|\s*$)", re.IGNORECASE),
)
CODE_PREFIX = re.compile(r"^\s*\d+\s*-\s*")
COMPETENCE = re.compile(r"COMP(?:ET[ÊE]NCIA)?\.?\s*:?\s*(\d{1,2})\s*/\s*(\d{4})", re.IGNORECASE)


@dataclasses.dataclass(frozen=True)
class Entry:
    fact_id: UUID
    period: datetime.date
    emission_date: datetime.date
    unit_id: UUID | None
    unit: str
    nature_code: str
    nature: str
    ng_account: str
    document: str | None
    history: str
    supplier: str | None
    amount: Decimal
    file: str
    sheet: str
    row: int


class InvestigationError(ValueError):
    """A request the investigation cannot answer; the message is for the person."""


def _fold(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(char)
    )


def supplier_of(history: str) -> str | None:
    text = CODE_PREFIX.sub("", history or "")
    match = next(
        (found for found in (pattern.search(text) for pattern in SUPPLIERS) if found),
        None,
    )
    if not match:
        return None
    name = re.sub(r"\s+", " ", match.group(1)).strip(" .-:")
    return name.upper() or None


def _money(value: Decimal) -> str:
    text = f"{value:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def _month(value: datetime.date) -> str:
    return f"{value.month:02d}/{value.year}"


def _shift(period: datetime.date, months: int) -> datetime.date:
    index = period.year * 12 + period.month - 1 + months
    return datetime.date(index // 12, index % 12 + 1, 1)


@dataclasses.dataclass
class Base:
    normalization_run_id: UUID
    latest_period: datetime.date
    periods: list[datetime.date]


def _base(session: Session, user: User) -> Base:
    context = financial_context(session, user, 1, 0)
    if not context.bases or not context.bases[0].periods:
        raise InvestigationError("Não há base financeira com lançamentos")
    base = context.bases[0]
    return Base(base.normalization_run_id, max(base.periods), sorted(base.periods))


def _unit(session: Session, user: User, text: str | None) -> tuple[UUID | None, str | None]:
    if not text or _fold(text) in ("consolidado", "todas", "geral"):
        return None, None
    units = visible_units(session, user)
    matches = resolve_unit(units, text)
    if len(matches) != 1:
        names = ", ".join(item.name for item in (matches or units)[:15])
        raise InvestigationError(f"Unidade “{text}” não identificada. Opções: {names}")
    return matches[0].unit_id, matches[0].name


def load_entries(
    session: Session,
    user: User,
    normalization_run_id: UUID,
    period_from: datetime.date,
    period_to: datetime.date,
    unit_id: UUID | None = None,
) -> list[Entry]:
    """NG entries of the base with the amount the DRE uses (treatments applied)."""
    normalization = session.get(FinancialNormalizationRun, normalization_run_id)
    assert normalization is not None
    conditions = [
        FinancialActualFact.run_id == normalization_run_id,
        FinancialActualFact.calendar_period >= period_from,
        FinancialActualFact.calendar_period <= period_to,
    ]
    if unit_id is not None:
        conditions.append(FinancialActualFact.unit_id == unit_id)
    query = (
        sa.select(
            FinancialActualFact,
            ParsedSourceRecord,
            BusinessUnit,
            SourceSnapshot.original_filename,
        )
        .join(ParsedSourceRecord, ParsedSourceRecord.id == FinancialActualFact.parsed_record_id)
        .outerjoin(BusinessUnit, BusinessUnit.id == FinancialActualFact.unit_id)
        .join(SourceSnapshot, SourceSnapshot.id == ParsedSourceRecord.snapshot_id)
        .where(*conditions)
    )
    if not is_ton_administrator(user):
        query = query.where(business_unit_visible_clause(user))
    basis_index = financial_domain._basis_index(
        session, normalization.amount_basis_revision_number
    )
    accounts = {item.id: item for item in session.scalars(sa.select(FinancialAccount))}
    entries: list[Entry] = []
    for fact, record, unit, filename in session.execute(query).tuples():
        _, amount, _ = financial_domain.actual_amounts(fact, basis_index, accounts)
        if amount is None:
            continue
        account = accounts.get(fact.account_id) if fact.account_id else None
        entries.append(
            Entry(
                fact_id=fact.id,
                period=fact.calendar_period,
                emission_date=fact.emission_date,
                unit_id=fact.unit_id,
                unit=unit.name if unit else "Sem unidade",
                nature_code=account.code if account else "",
                nature=account.label if account else "Sem natureza",
                ng_account=f"{record.account_code} {record.account_label}",
                document=(record.document_number or "").strip() or None,
                history=CODE_PREFIX.sub("", record.history or "").strip(),
                supplier=supplier_of(record.history or ""),
                amount=amount,
                file=filename or "",
                sheet=record.sheet_name,
                row=record.source_row_number,
            )
        )
    return entries


def _row(entry: Entry, **extra: Any) -> dict[str, Any]:
    return {
        "data": entry.emission_date.isoformat(),
        "mes": _month(entry.period),
        "unidade": entry.unit,
        "natureza": f"{entry.nature_code} {entry.nature}".strip(),
        "fornecedor": entry.supplier,
        "documento": entry.document,
        "historico": entry.history[:140],
        "valor": _money(entry.amount),
        "evidencia": f"{entry.file} · {entry.sheet} · linha {entry.row}",
        **extra,
    }


def _case(
    item: dict[str, Any],
    key: str,
    unit: str | None,
    amount: Decimal,
    title: str,
    period: datetime.date | None,
) -> dict[str, Any]:
    """A hit with the stable key and raw values the ledger needs.

    ``chave`` identifies the same case across runs; ``_ledger`` never reaches
    the model or the screen.
    """
    item["chave"] = key
    item["_ledger"] = {
        "chave": key,
        "unidade": unit,
        "valor": abs(amount),
        "titulo": title[:300],
        "periodo": period,
    }
    return item


def public(result: dict[str, Any]) -> dict[str, Any]:
    """The result without the raw ledger fields."""

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: clean(item)
                for key, item in value.items()
                if key not in ("_ledger", "_todos")
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return clean(result)


def _result(
    test: str,
    description: str,
    parameters: dict[str, Any],
    items: list[dict[str, Any]],
    summary: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "kind": "investigation",
        "codigo": test.split(" ")[0] if test.startswith("T") else None,
        "teste": test,
        "o_que_procura": description,
        "parametros_do_teste": parameters,
        "resumo": summary,
        "total_encontrado": len(items),
        "itens": items[:MAX_ITEMS],
        "_todos": items,
        "aviso": "Candidatos para conferência humana. Parâmetros do teste, não regra aprovada. Não afirme fraude nem erro.",
        **extra,
    }


# ------------------------------------------------------------------ search


def search_entries(
    session: Session,
    user: User,
    *,
    text: str | None = None,
    document: str | None = None,
    nature: str | None = None,
    unit: str | None = None,
    period_from: datetime.date | None = None,
    period_to: datetime.date | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
) -> dict[str, Any]:
    base = _base(session, user)
    unit_id, unit_name = _unit(session, user, unit)
    start = period_from or base.latest_period.replace(month=1)
    end = period_to or base.latest_period
    entries = load_entries(session, user, base.normalization_run_id, start, end, unit_id)
    words = [_fold(word) for word in (text or "").split() if word]
    nature_text = _fold(nature or "")
    found = [
        entry
        for entry in entries
        if all(word in _fold(f"{entry.history} {entry.supplier or ''}") for word in words)
        and (not document or (entry.document or "").lstrip("0").endswith(document.lstrip("0")))
        and (
            not nature_text
            or entry.nature_code.startswith(nature or "")
            or nature_text in _fold(entry.nature)
            or nature_text in _fold(entry.ng_account)
        )
        and (min_amount is None or abs(entry.amount) >= min_amount)
        and (max_amount is None or abs(entry.amount) <= max_amount)
    ]
    found.sort(key=lambda entry: -abs(entry.amount))
    total = sum((entry.amount for entry in found), Decimal(0))
    return _result(
        "Busca de lançamentos",
        "Lançamentos do NG que atendem aos filtros",
        {
            "texto": text,
            "documento": document,
            "natureza": nature,
            "unidade": unit_name or "todas",
            "periodo": f"{_month(start)} a {_month(end)}",
            "valor_minimo": str(min_amount) if min_amount is not None else None,
        },
        [_row(entry) for entry in found],
        f"{len(found)} lançamentos, soma {_money(total)}",
        soma=_money(total),
    )


def supplier_summary(
    session: Session,
    user: User,
    *,
    nature: str | None = None,
    unit: str | None = None,
    period_from: datetime.date | None = None,
    period_to: datetime.date | None = None,
) -> dict[str, Any]:
    base = _base(session, user)
    unit_id, unit_name = _unit(session, user, unit)
    start = period_from or base.latest_period.replace(month=1)
    end = period_to or base.latest_period
    entries = load_entries(session, user, base.normalization_run_id, start, end, unit_id)
    nature_text = _fold(nature or "")
    totals: dict[str, Decimal] = defaultdict(Decimal)
    counts: dict[str, int] = defaultdict(int)
    units: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        if nature_text and not (
            entry.nature_code.startswith(nature or "") or nature_text in _fold(entry.nature)
        ):
            continue
        key = entry.supplier or "(histórico sem fornecedor)"
        totals[key] += entry.amount
        counts[key] += 1
        units[key].add(entry.unit)
    ranked = sorted(totals, key=lambda key: -abs(totals[key]))
    items = [
        {
            "fornecedor": key,
            "valor": _money(totals[key]),
            "lancamentos": counts[key],
            "unidades": sorted(units[key])[:8],
        }
        for key in ranked
    ]
    return _result(
        "Resumo por fornecedor",
        "Maiores fornecedores pelo valor no período",
        {"natureza": nature, "unidade": unit_name or "todas", "periodo": f"{_month(start)} a {_month(end)}"},
        items,
        f"{len(items)} fornecedores",
    )


# ------------------------------------------------------------------ tests


def _target(base: Base, period: datetime.date | None) -> datetime.date:
    return period.replace(day=1) if period else base.latest_period


def _structure_groups(session: Session, user: User) -> tuple[dict[UUID, str], dict[str, str]]:
    """Line of each natureza and the top group label of each line."""
    structure = dre._primary_structure(session)
    if structure is None:
        return {}, {}
    version = dre.get_latest_version(session, user, structure.id)
    lines = {line.code: line for line in version.lines}

    def top(line: DreLineDefinition) -> str:
        while line.parent_code and line.parent_code in lines:
            line = lines[line.parent_code]
        return line.label

    return (
        {
            item.account_id: item.line_code
            for item in session.scalars(
                sa.select(DreAccountMapping).where(DreAccountMapping.version_id == version.id)
            )
        },
        {code: top(line) for code, line in lines.items() if line.line_type == DreLineType.SOURCE_SUM},
    )


def test_moving_average(
    session: Session,
    user: User,
    period: datetime.date | None,
    unit: str | None,
    min_amount: Decimal,
    min_percent: Decimal,
) -> dict[str, Any]:
    base = _base(session, user)
    target = _target(base, period)
    unit_id, unit_name = _unit(session, user, unit)
    entries = load_entries(session, user, base.normalization_run_id, _shift(target, -3), target, unit_id)
    sums: dict[tuple[str, str], dict[datetime.date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for entry in entries:
        sums[(entry.unit, f"{entry.nature_code} {entry.nature}")][entry.period] += entry.amount
    items = []
    for (unit_label, nature), by_month in sums.items():
        previous = [by_month.get(_shift(target, -offset), Decimal(0)) for offset in (1, 2, 3)]
        if sum(1 for value in previous if value) < 2:
            continue
        mean = sum(previous, Decimal(0)) / 3
        current = by_month.get(target, Decimal(0))
        difference = current - mean
        if abs(difference) < min_amount or not mean:
            continue
        percent = abs(difference) / abs(mean) * 100
        if percent < min_percent:
            continue
        items.append(
            _case(
                {
                    "unidade": unit_label,
                    "natureza": nature,
                    "mes": _money(current),
                    "media_3_meses": _money(mean),
                    "diferenca": _money(difference),
                    "variacao_percentual": f"{percent:.0f}%",
                    "_abs": abs(difference),
                },
                f"T2|{unit_label}|{nature}|{target.isoformat()}",
                unit_label,
                difference,
                f"{nature} fora da média em {unit_label} ({_month(target)})",
                target,
            )
        )
    items.sort(key=lambda item: -item.pop("_abs"))
    return _result(
        "T2 Desvio de média móvel",
        "Natureza × unidade cujo mês se afasta da média dos 3 meses anteriores",
        {"mes": _month(target), "unidade": unit_name or "todas", "diferenca_minima": _money(min_amount), "variacao_minima": f"{min_percent}%"},
        items,
        f"{len(items)} combinações fora da média em {_month(target)}",
    )


def test_duplicates(
    session: Session,
    user: User,
    period_from: datetime.date | None,
    period_to: datetime.date | None,
    unit: str | None,
    min_amount: Decimal,
) -> dict[str, Any]:
    base = _base(session, user)
    unit_id, unit_name = _unit(session, user, unit)
    start = period_from or base.latest_period.replace(month=1)
    end = period_to or base.latest_period
    entries = [
        entry
        for entry in load_entries(session, user, base.normalization_run_id, start, end, unit_id)
        if abs(entry.amount) >= min_amount
    ]
    by_document: dict[tuple[str, Decimal], list[Entry]] = defaultdict(list)
    by_supplier: dict[tuple[str, Decimal, datetime.date], list[Entry]] = defaultdict(list)
    for entry in entries:
        if entry.document:
            by_document[(entry.document.lstrip("0"), abs(entry.amount))].append(entry)
        if entry.supplier:
            by_supplier[(entry.supplier, abs(entry.amount), entry.emission_date)].append(entry)
    items = []
    for (document, amount), group in by_document.items():
        suppliers = {entry.supplier for entry in group if entry.supplier}
        if len(group) > 1 and len(suppliers) > 1:
            items.append(
                _case(
                    {
                        "tipo": "Mesmo documento e valor com fornecedores diferentes",
                        "documento": document,
                        "valor": _money(amount),
                        "fornecedores": sorted(suppliers),
                        "lancamentos": [_row(entry) for entry in group[:5]],
                        "_abs": amount,
                    },
                    f"T3|documento|{document}|{amount}",
                    group[0].unit,
                    amount,
                    f"Documento {document} com fornecedores diferentes ({_money(amount)})",
                    group[0].period,
                )
            )
    for (supplier, amount, day), group in by_supplier.items():
        documents = {entry.document for entry in group}
        if len(group) > 1 and len(documents) > 1:
            items.append(
                _case(
                    {
                        "tipo": "Mesmo fornecedor, valor e data com documentos diferentes",
                        "fornecedor": supplier,
                        "valor": _money(amount),
                        "data": day.isoformat(),
                        "lancamentos": [_row(entry) for entry in group[:5]],
                        "_abs": amount,
                    },
                    f"T3|fornecedor|{supplier}|{amount}|{day.isoformat()}",
                    group[0].unit,
                    amount,
                    f"{supplier}: {len(group)} pagamentos de {_money(amount)} em {day:%d/%m/%Y}",
                    group[0].period,
                )
            )
    items.sort(key=lambda item: -item.pop("_abs"))
    return _result(
        "T3 Duplicidade",
        "Pagamentos que parecem o mesmo documento lançado mais de uma vez",
        {"periodo": f"{_month(start)} a {_month(end)}", "unidade": unit_name or "todas", "valor_minimo": _money(min_amount)},
        items,
        f"{len(items)} grupos candidatos a duplicidade",
    )


def test_inverted_sign(
    session: Session, user: User, period: datetime.date | None, unit: str | None
) -> dict[str, Any]:
    base = _base(session, user)
    target = _target(base, period)
    unit_id, unit_name = _unit(session, user, unit)
    line_of, group_of = _structure_groups(session, user)
    accounts = {
        item.code: item.id for item in session.scalars(sa.select(FinancialAccount))
    }
    entries = load_entries(session, user, base.normalization_run_id, target, target, unit_id)
    sums: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    for entry in entries:
        account_id = accounts.get(entry.nature_code)
        line = line_of.get(account_id) if account_id else None
        group = group_of.get(line or "", "")
        revenue = "RECEITA" in group.upper()
        if "NÃO GERENC" in group.upper() or not group:
            continue
        if (revenue and entry.amount < 0) or (not revenue and entry.amount > 0):
            sums[(entry.unit, f"{entry.nature_code} {entry.nature}", group)] += entry.amount
    items = [
        _case(
            {"unidade": key[0], "natureza": key[1], "grupo": key[2], "valor_com_sinal_trocado": _money(value)},
            f"T6|{key[0]}|{key[1]}|{target.isoformat()}",
            key[0],
            value,
            f"{key[1]} com sinal invertido em {key[0]} ({_month(target)})",
            target,
        )
        for key, value in sorted(sums.items(), key=lambda kv: -abs(kv[1]))
        if value
    ]
    return _result(
        "T6 Sinal invertido",
        "Receita com valor negativo ou custo com valor positivo (estornos legítimos também aparecem)",
        {"mes": _month(target), "unidade": unit_name or "todas"},
        items,
        f"{len(items)} naturezas com sinal invertido em {_month(target)}",
    )


def test_supplier_unit(
    session: Session,
    user: User,
    period: datetime.date | None,
    min_amount: Decimal,
    min_units: int,
) -> dict[str, Any]:
    base = _base(session, user)
    target = _target(base, period)
    entries = load_entries(session, user, base.normalization_run_id, _shift(target, -6), target, None)
    history: dict[str, set[str]] = defaultdict(set)
    current: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    units_now: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        if not entry.supplier:
            continue
        if entry.period < target:
            history[entry.supplier].add(entry.unit)
        else:
            current[(entry.supplier, entry.unit)] += entry.amount
            units_now[entry.supplier].add(entry.unit)
    items = []
    for (supplier, unit_label), amount in current.items():
        if history[supplier] and unit_label not in history[supplier] and abs(amount) >= min_amount:
            items.append(
                _case(
                    {
                        "tipo": "Fornecedor novo nesta unidade",
                        "fornecedor": supplier,
                        "unidade": unit_label,
                        "valor_no_mes": _money(amount),
                        "unidades_anteriores": sorted(history[supplier])[:6],
                        "_abs": abs(amount),
                    },
                    f"T8|novo|{supplier}|{unit_label}|{target.isoformat()}",
                    unit_label,
                    amount,
                    f"{supplier} novo em {unit_label} ({_month(target)})",
                    target,
                )
            )
    for supplier, units in units_now.items():
        if len(units) >= min_units:
            total = sum((current[(supplier, item)] for item in units), Decimal(0))
            items.append(
                _case(
                    {
                        "tipo": "Fornecedor pago por muitas unidades no mês",
                        "fornecedor": supplier,
                        "unidades": sorted(units),
                        "valor_no_mes": _money(total),
                        "_abs": abs(total),
                    },
                    f"T8|muitas|{supplier}|{target.isoformat()}",
                    None,
                    total,
                    f"{supplier} pago por {len(units)} unidades ({_month(target)})",
                    target,
                )
            )
    items.sort(key=lambda item: -item.pop("_abs"))
    return _result(
        "T8 Fornecedor × unidade",
        "Fornecedor que aparece numa unidade onde não atuava nos 6 meses anteriores, ou em muitas unidades",
        {"mes": _month(target), "valor_minimo": _money(min_amount), "unidades_minimas": min_units},
        items,
        f"{len(items)} casos em {_month(target)}",
    )


def test_retroactive_competence(
    session: Session, user: User, period: datetime.date | None, unit: str | None, min_months: int
) -> dict[str, Any]:
    base = _base(session, user)
    target = _target(base, period)
    unit_id, unit_name = _unit(session, user, unit)
    entries = load_entries(session, user, base.normalization_run_id, target, target, unit_id)
    items = []
    by_unit: dict[str, Decimal] = defaultdict(Decimal)
    for entry in entries:
        match = COMPETENCE.search(entry.history)
        if not match:
            continue
        month, year = int(match.group(1)), int(match.group(2))
        if not 1 <= month <= 12:
            continue
        competence = datetime.date(year, month, 1)
        gap = (entry.period.year - competence.year) * 12 + entry.period.month - competence.month
        if gap >= min_months:
            by_unit[entry.unit] += entry.amount
            items.append(
                _case(
                    _row(entry, competencia=_month(competence), meses_de_atraso=gap, _abs=abs(entry.amount)),
                    f"T9|{entry.file}|{entry.sheet}|{entry.row}",
                    entry.unit,
                    entry.amount,
                    f"{entry.nature} de {_month(competence)} lançado em {_month(entry.period)} ({entry.unit})",
                    entry.period,
                )
            )
    items.sort(key=lambda item: -item.pop("_abs"))
    return _result(
        "T9 Competência retroativa",
        "Lançamento cujo histórico cita competência anterior ao mês em que entrou",
        {"mes": _month(target), "unidade": unit_name or "todas", "meses_minimos": min_months},
        items,
        f"{len(items)} lançamentos de competência anterior em {_month(target)}",
        por_unidade={key: _money(value) for key, value in sorted(by_unit.items(), key=lambda kv: kv[1])},
    )


def test_non_recurring(
    session: Session,
    user: User,
    period: datetime.date | None,
    unit: str | None,
    factor: Decimal,
    min_amount: Decimal,
) -> dict[str, Any]:
    base = _base(session, user)
    target = _target(base, period)
    unit_id, unit_name = _unit(session, user, unit)
    entries = load_entries(session, user, base.normalization_run_id, _shift(target, -6), target, unit_id)
    previous: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    for entry in entries:
        if entry.period < target and entry.amount:
            previous[(entry.nature_code, entry.unit)].append(abs(entry.amount))
    items = []
    for entry in entries:
        if entry.period != target or abs(entry.amount) < min_amount:
            continue
        sample = previous.get((entry.nature_code, entry.unit), [])
        if len(sample) < 3:
            continue
        median = Decimal(statistics.median(sample))
        # A monthly invoice or payroll of the usual size is recurring, however
        # far above the median of the small entries of the same natureza.
        if (
            median
            and abs(entry.amount) >= median * factor
            and abs(entry.amount) > max(sample) * Decimal("1.5")
        ):
            items.append(
                _case(
                    _row(entry, mediana_da_natureza=_money(median), vezes=f"{abs(entry.amount) / median:.0f}×", _abs=abs(entry.amount)),
                    f"T10|{entry.file}|{entry.sheet}|{entry.row}",
                    entry.unit,
                    entry.amount,
                    f"{entry.nature} atípico em {entry.unit}: {_money(entry.amount)} ({_month(entry.period)})",
                    entry.period,
                )
            )
    items.sort(key=lambda item: -item.pop("_abs"))
    return _result(
        "T10 Evento não recorrente",
        "Lançamento muito acima do valor típico da natureza nos 6 meses anteriores",
        {"mes": _month(target), "unidade": unit_name or "todas", "fator": f"{factor}× a mediana e 1,5× o maior valor anterior", "valor_minimo": _money(min_amount)},
        items,
        f"{len(items)} lançamentos atípicos em {_month(target)}",
    )


def test_revenue_vs_billing(
    session: Session, user: User, period: datetime.date | None, min_amount: Decimal
) -> dict[str, Any]:
    base = _base(session, user)
    target = _target(base, period)
    line_of, group_of = _structure_groups(session, user)
    accounts = {item.code: item.id for item in session.scalars(sa.select(FinancialAccount))}
    revenue: dict[str, Decimal] = defaultdict(Decimal)
    for entry in load_entries(session, user, base.normalization_run_id, target, target, None):
        account_id = accounts.get(entry.nature_code)
        group = group_of.get(line_of.get(account_id) or "", "") if account_id else ""
        if "RECEITA" in group.upper() and entry.amount > 0:
            revenue[entry.unit] += entry.amount
    units = {item.id: item.name for item in session.scalars(sa.select(BusinessUnit))}
    billing_net: dict[str, Decimal] = defaultdict(Decimal)
    billing_gross: dict[str, Decimal] = defaultdict(Decimal)
    for fact in session.scalars(
        sa.select(FinancialBillingFact).where(
            FinancialBillingFact.run_id == base.normalization_run_id,
            FinancialBillingFact.emission_date >= target,
            FinancialBillingFact.emission_date < _shift(target, 1),
        )
    ):
        name = units.get(fact.unit_id, "Sem unidade") if fact.unit_id else "Sem unidade"
        billing_gross[name] += fact.service_amount
        billing_net[name] += (
            fact.invoice_net_amount
            if fact.invoice_net_amount is not None
            else fact.service_amount - (fact.total_retained or Decimal(0))
        )
    items = []
    for name in sorted(set(revenue) | set(billing_net)):
        difference = revenue.get(name, Decimal(0)) - billing_net.get(name, Decimal(0))
        if abs(difference) < min_amount:
            continue
        items.append(
            _case(
                {
                    "unidade": name,
                    "receita_ng": _money(revenue.get(name, Decimal(0))),
                    "faturamento_liquido_notas": _money(billing_net.get(name, Decimal(0))),
                    "faturamento_bruto_notas": _money(billing_gross.get(name, Decimal(0))),
                    "diferenca": _money(difference),
                    "_abs": abs(difference),
                },
                f"T4|{name}|{target.isoformat()}",
                name,
                difference,
                f"Receita do NG × notas fiscais em {name} ({_month(target)})",
                target,
            )
        )
    items.sort(key=lambda item: -item.pop("_abs"))
    return _result(
        "T4 Receita NG × notas fiscais",
        "Receita lançada no NG × faturamento líquido das notas emitidas no mês, por unidade",
        {"mes": _month(target), "diferenca_minima": _money(min_amount), "base_das_notas": "mês de emissão"},
        items,
        f"{len(items)} unidades com diferença em {_month(target)}",
        hipoteses="Diferença pode vir de recebimento em outro mês, retenções ou nota sem lançamento; confirmar com a Controladoria.",
    )


def test_zeroed_lines(
    session: Session, user: User, period: datetime.date | None, unit: str | None
) -> dict[str, Any]:
    base = _base(session, user)
    target = _target(base, period)
    unit_id, unit_name = _unit(session, user, unit)
    line_of, _ = _structure_groups(session, user)
    structure = dre._primary_structure(session)
    assert structure is not None
    labels = {line.code: line.label for line in dre.get_latest_version(session, user, structure.id).lines}
    accounts = {item.code: item.id for item in session.scalars(sa.select(FinancialAccount))}
    sums: dict[tuple[str, str], dict[datetime.date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for entry in load_entries(session, user, base.normalization_run_id, _shift(target, -3), target, unit_id):
        account_id = accounts.get(entry.nature_code)
        line = line_of.get(account_id) if account_id else None
        if line:
            sums[(entry.unit, line)][entry.period] += entry.amount
    items = []
    for (unit_label, line), by_month in sums.items():
        previous = [by_month.get(_shift(target, -offset), Decimal(0)) for offset in (1, 2, 3)]
        if all(previous) and not by_month.get(target):
            items.append(
                _case(
                    {
                        "unidade": unit_label,
                        "linha": labels.get(line, line),
                        "media_3_meses": _money(sum(previous, Decimal(0)) / 3),
                        "_abs": abs(sum(previous, Decimal(0))),
                    },
                    f"T1|{unit_label}|{line}|{target.isoformat()}",
                    unit_label,
                    sum(previous, Decimal(0)) / 3,
                    f"{labels.get(line, line)} zerada em {unit_label} ({_month(target)})",
                    target,
                )
            )
    items.sort(key=lambda item: -item.pop("_abs"))
    return _result(
        "T1 Grupo zerado",
        "Linha da DRE sem valor no mês, mas com valor nos 3 meses anteriores (lançamento atrasado ou faltando)",
        {"mes": _month(target), "unidade": unit_name or "todas"},
        items,
        f"{len(items)} linhas zeradas em {_month(target)}",
    )


# ------------------------------------------------------------------ DRE reads


def compare_dre(
    session: Session,
    user: User,
    periods: list[datetime.date],
    units: list[str],
) -> dict[str, Any]:
    """Stored DRE values of the primary structure for several months and units."""
    from onyx.db.ton.agent import stored_result_for_scope
    from onyx.ton.dre.models import DreScope

    base = _base(session, user)
    structure = dre._primary_structure(session)
    if structure is None:
        raise InvestigationError("Não há estrutura de DRE")
    version = dre.get_latest_version(session, user, structure.id)
    scopes: list[tuple[UUID | None, str]] = []
    for text in units or ["consolidado"]:
        unit_id, name = _unit(session, user, text)
        scopes.append((unit_id, name or "Consolidado"))
    months = [item.replace(day=1) for item in (periods or [base.latest_period])][:12]
    columns: list[str] = []
    values: dict[str, dict[str, str]] = defaultdict(dict)
    missing: list[str] = []
    labels = {line.code: line for line in version.lines}
    for unit_id, name in scopes[:8]:
        for month in months:
            column = f"{name} {_month(month)}"
            stored = stored_result_for_scope(
                session,
                user,
                DreScope(
                    normalization_run_id=base.normalization_run_id,
                    structure_version_id=version.id,
                    period=month,
                    unit_id=unit_id,
                ),
            )
            if stored is None or stored.status != "READY":
                missing.append(column)
                continue
            columns.append(column)
            for line in dre.list_result_lines(session, user, stored.run_id, 100, 0):
                definition = labels.get(line.code)
                if definition is None or definition.hidden:
                    continue
                values[line.label][column] = _money(line.realizado)
    return {
        "kind": "dre_comparison",
        "estrutura": structure.label,
        "colunas": columns,
        "linhas": [{"linha": label, **cells} for label, cells in values.items()],
        "sem_calculo": missing,
        "observacao": "Valores da DRE calculada (os mesmos da tela). Escopos sem cálculo precisam de recálculo.",
    }


def line_entries(
    session: Session,
    user: User,
    line: str,
    period: datetime.date | None,
    unit: str | None,
) -> dict[str, Any]:
    """Entries behind one DRE line, by its code or name."""
    from onyx.db.ton.agent import stored_result_for_scope
    from onyx.ton.dre.models import DreScope

    base = _base(session, user)
    structure = dre._primary_structure(session)
    if structure is None:
        raise InvestigationError("Não há estrutura de DRE")
    version = dre.get_latest_version(session, user, structure.id)
    wanted = _fold(line)
    matches = [
        item
        for item in version.lines
        if item.line_type == DreLineType.SOURCE_SUM
        and (item.code == line or wanted in _fold(item.label))
    ]
    if len(matches) != 1:
        options = ", ".join(item.label for item in version.lines if item.line_type == DreLineType.SOURCE_SUM)
        raise InvestigationError(f"Linha “{line}” não identificada. Linhas com lançamentos: {options}")
    unit_id, name = _unit(session, user, unit)
    month = _target(base, period)
    stored = stored_result_for_scope(
        session,
        user,
        DreScope(
            normalization_run_id=base.normalization_run_id,
            structure_version_id=version.id,
            period=month,
            unit_id=unit_id,
        ),
    )
    if stored is None or stored.status != "READY":
        raise InvestigationError("A DRE desse mês e escopo não está calculada; proponha o recálculo")
    page = dre.list_contributors(session, user, stored.run_id, matches[0].code, "ACTUAL", 25, 0)
    rows = sorted(page.rows, key=lambda row: -abs(row.amount))
    return {
        "kind": "line_entries",
        "linha": matches[0].label,
        "escopo": f"{_month(month)} · {name or 'Consolidado'}",
        "total_de_lancamentos": page.total,
        "maiores": [
            {
                "data": row.record_date.isoformat() if row.record_date else None,
                "unidade": row.unit_name or row.unit_code,
                "documento": row.reference,
                "historico": (row.description or "")[:140],
                "valor": _money(row.amount),
                "tratamento": row.treatment_title,
                "evidencia": f"{row.original_filename} · {row.sheet_name} · linha {row.source_row_number}",
            }
            for row in rows
        ],
        "observacao": "Mostra até 25 lançamentos da primeira página; a tela DRE tem a lista completa.",
    }


TESTS = ("T1", "T2", "T3", "T4", "T6", "T8", "T9", "T10")


def _decimal(value: Any, default: str) -> Decimal:
    return Decimal(str(value)) if value not in (None, "") else Decimal(default)


def _date(value: Any) -> datetime.date | None:
    if not value:
        return None
    text = str(value)
    if len(text) == 7:
        text = f"{text}-01"
    return datetime.date.fromisoformat(text[:10]).replace(day=1)


def run_test(session: Session, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Run one test from the parameters the chat or a routine passes."""
    test = params.get("test")
    period = _date(params.get("period"))
    unit = params.get("unit")
    if test == "T1":
        return test_zeroed_lines(session, user, period, unit)
    if test == "T2":
        return test_moving_average(
            session, user, period, unit,
            _decimal(params.get("min_amount"), "50000"),
            _decimal(params.get("min_percent"), "50"),
        )
    if test == "T3":
        return test_duplicates(
            session, user, _date(params.get("period_from")) or period,
            _date(params.get("period_to")) or period, unit,
            _decimal(params.get("min_amount"), "1000"),
        )
    if test == "T4":
        return test_revenue_vs_billing(session, user, period, _decimal(params.get("min_amount"), "10000"))
    if test == "T6":
        return test_inverted_sign(session, user, period, unit)
    if test == "T8":
        return test_supplier_unit(
            session, user, period,
            _decimal(params.get("min_amount"), "20000"),
            int(params.get("min_units") or 5),
        )
    if test == "T9":
        return test_retroactive_competence(session, user, period, unit, int(params.get("min_months") or 2))
    if test == "T10":
        return test_non_recurring(
            session, user, period, unit,
            _decimal(params.get("factor"), "10"),
            _decimal(params.get("min_amount"), "20000"),
        )
    raise InvestigationError("Teste desconhecido; use T1, T2, T3, T4, T6, T8, T9 ou T10")


def unit_revenue(
    session: Session, user: User, period: datetime.date, unit_name: str | None
) -> Decimal:
    """Revenue the NG booked in the month, for one unit or the whole company."""
    base = _base(session, user)
    line_of, group_of = _structure_groups(session, user)
    accounts = {item.code: item.id for item in session.scalars(sa.select(FinancialAccount))}
    total = Decimal(0)
    for entry in load_entries(session, user, base.normalization_run_id, period, period, None):
        if unit_name and entry.unit != unit_name:
            continue
        account_id = accounts.get(entry.nature_code)
        group = group_of.get(line_of.get(account_id) or "", "") if account_id else ""
        if "RECEITA" in group.upper() and entry.amount > 0:
            total += entry.amount
    return total
