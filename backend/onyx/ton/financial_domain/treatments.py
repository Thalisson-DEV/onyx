"""Which closing treatment applies to an actual fact. Pure and deterministic."""

import datetime
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from onyx.ton.financial_domain.models import TreatmentEffect, TreatmentStatus


@dataclass(frozen=True)
class TreatmentRule:
    id: UUID
    number: int
    treatment_key: str
    status: TreatmentStatus
    effect: TreatmentEffect
    account_id: UUID | None
    unit_id: UUID | None
    period_from: datetime.date | None
    period_to: datetime.date | None
    target_account_id: UUID | None

    def matches(
        self, account_id: UUID | None, unit_id: UUID | None, period: datetime.date
    ) -> bool:
        return (
            account_id is not None
            and self.account_id == account_id
            and (self.unit_id is None or self.unit_id == unit_id)
            and (self.period_from is None or self.period_from <= period)
            and (self.period_to is None or period <= self.period_to)
        )


def in_force(versions: Iterable[TreatmentRule]) -> list[TreatmentRule]:
    """Latest version per key; only ACTIVE ones change facts.

    Most recent decision first, so the newest treatment wins when two scopes
    overlap.
    """
    latest: dict[str, TreatmentRule] = {}
    for version in versions:
        current = latest.get(version.treatment_key)
        if current is None or version.number > current.number:
            latest[version.treatment_key] = version
    return sorted(
        (rule for rule in latest.values() if rule.status is TreatmentStatus.ACTIVE),
        key=lambda rule: rule.number,
        reverse=True,
    )


def find(
    rules: list[TreatmentRule],
    account_id: UUID | None,
    unit_id: UUID | None,
    period: datetime.date,
) -> TreatmentRule | None:
    return next(
        (rule for rule in rules if rule.matches(account_id, unit_id, period)), None
    )
