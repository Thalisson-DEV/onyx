"""Monthly R3 calendar. Holidays require an explicitly confirmed calendar."""

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

BRASILIA = ZoneInfo("America/Sao_Paulo")


class R3ScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    unit_id: UUID | None = None
    calendar_name: str = Field(default="", max_length=120)
    nonworking_dates: list[date] = Field(default_factory=list, max_length=400)
    calendar_valid_through: date | None = None

    @model_validator(mode="after")
    def confirmed_calendar(self) -> "R3ScheduleRequest":
        if self.enabled and (
            not self.calendar_name.strip() or self.calendar_valid_through is None
        ):
            raise ValueError(
                "Confirme o calendário e sua validade antes de ativar a R3."
            )
        return self


class R3ScheduleState(R3ScheduleRequest):
    revision: UUID
    actor_id: UUID
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_revision_id: UUID | None = None
    last_result: str | None = None
    failure_reason: str | None = None


class R3ScheduleView(BaseModel):
    enabled: bool = False
    schedule: str = (
        "Primeiro dia útil do mês, às 08:00 de Brasília. Calendário não confirmado."
    )
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_report_url: str | None = None
    last_result: str | None = None
    reason: str = (
        "Agendamento desativado. Confirme feriados, escopo e validade do calendário."
    )


def first_business_run(year: int, month: int, config: R3ScheduleRequest) -> datetime:
    day = date(year, month, 1)
    excluded = set(config.nonworking_dates)
    while day.weekday() >= 5 or day in excluded:
        day += timedelta(days=1)
        if day.month != month:
            raise ValueError("O calendário não contém um dia útil neste mês.")
    if config.calendar_valid_through is None or day > config.calendar_valid_through:
        raise ValueError("O calendário confirmado não cobre a próxima execução.")
    return datetime.combine(day, time(8), BRASILIA).astimezone(timezone.utc)


def next_business_run(after: datetime, config: R3ScheduleRequest) -> datetime:
    if after.tzinfo is None:
        raise ValueError("O horário deve conter um fuso.")
    local = after.astimezone(BRASILIA)
    candidate = first_business_run(local.year, local.month, config)
    if candidate > after:
        return candidate
    year, month = (
        (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
    )
    return first_business_run(year, month, config)


def closing_period(due: datetime) -> date:
    local = due.astimezone(BRASILIA)
    return (date(local.year, local.month, 1) - timedelta(days=1)).replace(day=1)
