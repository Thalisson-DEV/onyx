"""Recurrence of the schedule trigger, in Brasília time.

``latest_slot`` gives the most recent planned moment up to now (the tick
fires it once, keyed by the slot); ``next_slot`` the next one (shown in the
screens). Minutes and hours are aligned to local midnight, days to
2026-01-01, so the same parameters always give the same slots."""

import datetime
from typing import Any

from onyx.ton.automations.expressions import BRASILIA

FREQUENCIES = ("minute", "hour", "day", "week", "month")
MIN_MINUTES = 5
WEEKDAY_NAMES = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
_ANCHOR = datetime.date(2026, 1, 1)


def _time(params: dict[str, Any]) -> tuple[int, int]:
    raw = str(params.get("time") or "08:00")
    try:
        hour, minute = (int(part) for part in raw.split(":", 1))
    except ValueError:
        raise ValueError("Horário inválido; use HH:MM") from None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Horário inválido; use HH:MM")
    return hour, minute


def _interval(params: dict[str, Any]) -> int:
    try:
        value = int(params.get("interval") or 1)
    except (TypeError, ValueError):
        raise ValueError("Intervalo inválido") from None
    if value < 1 or value > 1000:
        raise ValueError("Intervalo entre 1 e 1000")
    return value


def check(params: dict[str, Any]) -> None:
    frequency = params.get("frequency") or "week"
    if frequency not in FREQUENCIES:
        raise ValueError("Frequência inválida")
    interval = _interval(params)
    if frequency == "minute" and interval < MIN_MINUTES:
        raise ValueError(f"A cada no mínimo {MIN_MINUTES} minutos")
    _time(params)
    if frequency == "week":
        days = params.get("weekdays") or []
        if not days or any(int(day) not in range(7) for day in days):
            raise ValueError("Escolha ao menos um dia da semana")
    if frequency == "month":
        day = int(params.get("day_of_month") or 1)
        if not 1 <= day <= 28:
            raise ValueError("Dia do mês entre 1 e 28")


def _day_slots(params: dict[str, Any], day: datetime.date) -> list[datetime.datetime]:
    frequency = params.get("frequency") or "week"
    hour, minute = _time(params)
    interval = _interval(params)
    midnight = datetime.datetime(day.year, day.month, day.day, tzinfo=BRASILIA)
    if frequency == "minute":
        step = max(MIN_MINUTES, interval)
        return [midnight + datetime.timedelta(minutes=m) for m in range(0, 24 * 60, step)]
    if frequency == "hour":
        return [
            midnight + datetime.timedelta(hours=h, minutes=minute)
            for h in range(0, 24, interval)
        ]
    at = midnight.replace(hour=hour, minute=minute)
    if frequency == "day":
        return [at] if (day - _ANCHOR).days % interval == 0 else []
    if frequency == "week":
        days = {int(value) for value in params.get("weekdays") or [0]}
        return [at] if day.weekday() in days else []
    day_of_month = int(params.get("day_of_month") or 1)
    return [at] if day.day == day_of_month else []


def latest_slot(params: dict[str, Any], now: datetime.datetime) -> datetime.datetime | None:
    local = now.astimezone(BRASILIA)
    for offset in range(0, 40):
        day = local.date() - datetime.timedelta(days=offset)
        slots = [slot for slot in _day_slots(params, day) if slot <= local]
        if slots:
            return slots[-1]
    return None


def next_slot(params: dict[str, Any], now: datetime.datetime) -> datetime.datetime | None:
    local = now.astimezone(BRASILIA)
    for offset in range(0, 40):
        day = local.date() + datetime.timedelta(days=offset)
        slots = [slot for slot in _day_slots(params, day) if slot > local]
        if slots:
            return slots[0]
    return None


def grace(params: dict[str, Any]) -> datetime.timedelta:
    """How late a slot may still fire (the worker may have been down)."""
    frequency = params.get("frequency") or "week"
    if frequency == "minute":
        return datetime.timedelta(minutes=max(MIN_MINUTES, _interval(params)))
    if frequency == "hour":
        return datetime.timedelta(hours=1)
    return datetime.timedelta(hours=6)


def describe(params: dict[str, Any]) -> str:
    frequency = params.get("frequency") or "week"
    interval = _interval(params) if params.get("interval") else 1
    hour, minute = _time(params)
    at = f"{hour:02d}:{minute:02d}"
    if frequency == "minute":
        return f"A cada {interval} minutos"
    if frequency == "hour":
        return "A cada hora" if interval == 1 else f"A cada {interval} horas"
    if frequency == "day":
        return f"Todo dia às {at}" if interval == 1 else f"A cada {interval} dias às {at}"
    if frequency == "week":
        days = sorted({int(value) for value in params.get("weekdays") or [0]})
        if days == [0, 1, 2, 3, 4]:
            names = "dia útil"
        else:
            names = ", ".join(WEEKDAY_NAMES[day] for day in days)
        return f"Toda {names} às {at}"
    return f"Todo dia {int(params.get('day_of_month') or 1)} do mês às {at}"
