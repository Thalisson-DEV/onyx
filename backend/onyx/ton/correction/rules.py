"""PAD-CTRL-001 criticality, deadlines and the situation of a correction case."""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from onyx.ton.payables.identifiers import business_days_between

# Share of the month's billed revenue (Prompt Mestre §10).
CRITICAL_SHARE = Decimal("1.0")
HIGH_SHARE = Decimal("0.3")
MEDIUM_SHARE = Decimal("0.1")

CRITICALITY_LABEL = {
    "CRITICAL": "Crítica",
    "HIGH": "Alta",
    "MEDIUM": "Média",
    "MONITORING": "Monitoramento",
}
CRITICALITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "MONITORING": 3}


@dataclass(frozen=True)
class Criticality:
    level: str
    # Largest monthly share of revenue, in percent; None without amount.
    share: Decimal | None
    reason: str


def criticality(
    monthly: dict[datetime.date, tuple[Decimal, Decimal]], months_seen: int
) -> Criticality:
    """``monthly``: month -> (impact, billed revenue of the month).

    The worst month decides. A case seen in two or more months is at least
    high: the régua treats a repeated error as high whatever its size.
    """
    share: Decimal | None = None
    worst: datetime.date | None = None
    for month, (impact, revenue) in monthly.items():
        if not revenue or not impact:
            continue
        value = impact / revenue * 100
        if share is None or value > share:
            share, worst = value, month
    if share is not None and share >= CRITICAL_SHARE:
        level = "CRITICAL"
    elif share is not None and share >= HIGH_SHARE:
        level = "HIGH"
    elif share is not None and share >= MEDIUM_SHARE:
        level = "MEDIUM"
    else:
        level = "MONITORING"
    reason = (
        f"{_pct(share)} da receita faturada de {worst:%m/%Y}"
        if share is not None and worst
        else "sem valor medido"
    )
    if months_seen >= 2 and CRITICALITY_ORDER[level] > CRITICALITY_ORDER["HIGH"]:
        level = "HIGH"
        reason = f"aparece em {months_seen} meses"
    elif months_seen >= 2:
        reason = f"{reason}; aparece em {months_seen} meses"
    return Criticality(level=level, share=share, reason=reason)


def _pct(value: Decimal | None) -> str:
    if value is None:
        return "—"
    text = f"{value:.1f}" if value >= Decimal("0.1") else f"{value:.2f}"
    return text.replace(".", ",") + "%"


def default_due_date(level: str, start: datetime.date) -> datetime.date:
    """Deadline the régua gives each level, counted from the assignment."""
    if level == "CRITICAL":
        day = start
        added = 0
        while added < 5:
            day += datetime.timedelta(days=1)
            if day.weekday() < 5:
                added += 1
        return day
    if level == "HIGH":
        return start + datetime.timedelta(days=15)
    return start + datetime.timedelta(days=30)


@dataclass(frozen=True)
class Situation:
    code: str
    label: str


def situation(
    *,
    open_count: int,
    fixed_count: int,
    decision: str | None,
    owner: str | None,
    due_date: datetime.date | None,
    today: datetime.date,
) -> Situation:
    if open_count == 0 and fixed_count > 0:
        return Situation("VERIFIED", "Corrigida e verificada")
    if decision == "RISK_ACCEPTED":
        return Situation("ACCEPTED", "Risco aceito")
    if not owner:
        return Situation("UNASSIGNED", "Sem responsável")
    if due_date is not None and due_date < today:
        days = business_days_between(due_date, today)
        return Situation(
            "OVERDUE",
            f"Prazo vencido há {days} {'dia útil' if days == 1 else 'dias úteis'}"
            if days
            else "Prazo vencido",
        )
    return Situation("ASSIGNED", "Em correção")
