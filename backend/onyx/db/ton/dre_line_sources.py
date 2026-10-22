"""Values of DRE lines that read billing invoices or Controladoria adjustments."""

import datetime
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.ton.models import (
    DreAdjustment,
    DreStructureVersion,
    FinancialBillingFact,
    OperationalSourceRecord,
)
from onyx.ton.dre.models import (
    BillingField,
    BillingPeriodBasis,
    DreLineDefinition,
    DreLineSource,
    DreLineType,
)

# Amounts kept on the billing fact; the others are read from the source record.
FACT_FIELDS = {
    BillingField.SERVICE_AMOUNT: "service_amount",
    BillingField.INVOICE_NET_AMOUNT: "invoice_net_amount",
    BillingField.TOTAL_RETAINED: "total_retained",
    BillingField.ISS_RETAINED: "iss_retained",
    BillingField.IR_RETAINED: "ir_retained",
    BillingField.INSS_RETAINED: "inss_retained",
}

BILLING_FIELD_LABELS = {
    BillingField.SERVICE_AMOUNT: "valor do serviço (bruto)",
    BillingField.INVOICE_NET_AMOUNT: "líquido da nota",
    BillingField.TOTAL_RETAINED: "total retido",
    BillingField.ISS_RETAINED: "ISS retido",
    BillingField.IR_RETAINED: "IR retido",
    BillingField.INSS_RETAINED: "INSS retido",
    BillingField.ISS_INVOICE: "ISS da nota",
    BillingField.INSS_INVOICE: "INSS da nota",
    BillingField.IR_INVOICE: "IR da nota",
    BillingField.DEDUCTION_AMOUNT: "deduções",
}


def billing_amount(
    fact: FinancialBillingFact,
    numeric: dict[str, str | None],
    field: BillingField,
) -> Decimal:
    attribute = FACT_FIELDS.get(field)
    if attribute is not None:
        value = getattr(fact, attribute)
        return value if value is not None else Decimal(0)
    raw = numeric.get(field.value)
    return Decimal(raw) if raw else Decimal(0)


def percent_text(value: Decimal) -> str:
    return f"{value.normalize():f}".replace(".", ",") + "%"


def billing_fields_text(
    line: DreLineDefinition, fields: list[BillingField] | None = None
) -> str:
    """What a billing line reads, as the Controladoria says it: "2% de valor
    do serviço (bruto)"."""
    text = ", ".join(BILLING_FIELD_LABELS[item] for item in (fields or line.billing_fields))
    if line.billing_percent is not None:
        return f"{percent_text(line.billing_percent)} de {text}"
    return text


def billing_share(amount: Decimal, line: DreLineDefinition) -> Decimal:
    """The part of an invoice amount a billing line takes, signed for the DRE."""
    if line.billing_percent is not None:
        amount = amount * line.billing_percent / 100
    return -amount if line.negate else amount


def billing_month(
    fact: FinancialBillingFact, basis: BillingPeriodBasis
) -> datetime.date:
    if basis == BillingPeriodBasis.COMPETENCE and fact.competence_period is not None:
        return fact.competence_period.replace(day=1)
    return fact.emission_date.replace(day=1)


def billing_facts(
    session: Session,
    normalization_run_id: UUID,
    year: int,
    unit_id: UUID | None,
) -> list[tuple[FinancialBillingFact, OperationalSourceRecord]]:
    """Invoices of the year (by emission or competence) for one scope.

    A unit DRE reads the unit's invoices; the consolidated DRE reads all,
    including invoices whose unit is not known.
    """
    start = datetime.date(year - 1, 12, 1)
    end = datetime.date(year + 1, 1, 31)
    query = (
        sa.select(FinancialBillingFact, OperationalSourceRecord)
        .join(
            OperationalSourceRecord,
            OperationalSourceRecord.id == FinancialBillingFact.source_record_id,
        )
        .where(
            FinancialBillingFact.run_id == normalization_run_id,
            sa.or_(
                FinancialBillingFact.emission_date.between(start, end),
                FinancialBillingFact.competence_period.between(start, end),
            ),
        )
        .order_by(FinancialBillingFact.emission_date, FinancialBillingFact.id)
    )
    if unit_id is not None:
        query = query.where(FinancialBillingFact.unit_id == unit_id)
    return [(fact, record) for fact, record in session.execute(query).tuples()]


def adjustments_in_force(
    session: Session,
    structure_id: UUID,
    year: int,
    unit_id: UUID | None,
) -> list[DreAdjustment]:
    """Latest adjustment per line, month and unit of the year, non-zero only."""
    rows = session.scalars(
        sa.select(DreAdjustment)
        .where(
            DreAdjustment.structure_id == structure_id,
            DreAdjustment.period.between(
                datetime.date(year, 1, 1), datetime.date(year, 12, 1)
            ),
        )
        .order_by(DreAdjustment.created_at.desc(), DreAdjustment.id.desc())
    )
    seen: set[tuple[str, datetime.date, UUID | None]] = set()
    result: list[DreAdjustment] = []
    for row in rows:
        key = (row.line_code, row.period, row.unit_id)
        if key in seen:
            continue
        seen.add(key)
        if unit_id is not None and row.unit_id != unit_id:
            continue
        if row.amount:
            result.append(row)
    return result


def has_extra_sources(lines: list[DreLineDefinition]) -> bool:
    return any(
        line.line_type == DreLineType.SOURCE_SUM
        and line.source != DreLineSource.NG_ACCOUNTS
        for line in lines
    )


def line_source_sums(
    session: Session,
    lines: list[DreLineDefinition],
    structure_id: UUID,
    normalization_run_id: UUID,
    year: int,
    unit_id: UUID | None,
    *,
    extra_adjustments: list[DreAdjustment] | None = None,
) -> tuple[dict[int, dict[str, Decimal]], list[str]]:
    """Per-month sums of the billing and adjustment lines, and their identity.

    The identity (adjustment ids and amounts) goes into the calculation digest,
    so a changed adjustment gives a new result. ``extra_adjustments`` replaces
    rows in force for a preview, without writing them.
    """
    sums: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    identity: list[str] = []
    billing_lines = [
        line
        for line in lines
        if line.line_type == DreLineType.SOURCE_SUM
        and line.source == DreLineSource.BILLING
    ]
    adjustment_lines = {
        line.code: line
        for line in lines
        if line.line_type == DreLineType.SOURCE_SUM
        and line.source == DreLineSource.ADJUSTMENT
    }
    if billing_lines:
        for fact, record in billing_facts(
            session, normalization_run_id, year, unit_id
        ):
            for line in billing_lines:
                month = billing_month(fact, line.billing_period)
                if month.year != year:
                    continue
                amount = sum(
                    (
                        billing_amount(fact, record.numeric_values, field)
                        for field in line.billing_fields
                    ),
                    Decimal(0),
                )
                sums[month.month][line.code] += billing_share(amount, line)
    if adjustment_lines:
        rows = adjustments_in_force(session, structure_id, year, unit_id)
        if extra_adjustments:
            replaced = {(row.line_code, row.period, row.unit_id) for row in extra_adjustments}
            rows = [
                row
                for row in rows
                if (row.line_code, row.period, row.unit_id) not in replaced
            ] + [
                row
                for row in extra_adjustments
                if row.amount and (unit_id is None or row.unit_id == unit_id)
            ]
        for row in rows:
            target = adjustment_lines.get(row.line_code)
            if target is None:
                continue
            sums[row.period.month][target.code] += (
                -row.amount if target.negate else row.amount
            )
            identity.append(f"{row.id}:{row.amount}")
    return sums, sorted(identity)


def structure_id_of(session: Session, version_id: UUID) -> UUID:
    version = session.get(DreStructureVersion, version_id)
    assert version is not None
    return version.structure_id
