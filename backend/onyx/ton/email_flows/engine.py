"""Interpreter for flow definitions v2.

Runs the step tree over the items a trigger produced. A condition splits the
items (those that match go "Sim", the rest "Não"); "para cada unidade"
repeats its steps per unit; "esperar" and "aprovação" suspend the run with a
cursor so it can resume later from the next step, re-reading the data and
keeping only the items still open. No database access here: sending is a
callback, so the engine is testable on its own.
"""

import datetime
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from onyx.ton.email_flows.catalog import TRIGGERS, TriggerKind
from onyx.ton.email_flows.logic import BRASILIA, FlowItem, _matches
from onyx.ton.email_flows.steps import (
    ApprovalStep,
    ConditionStep,
    FlowDefinitionV2,
    ForEachUnitStep,
    SendEmailStep,
    WaitStep,
)

# A step address: indexes into lists and the branch names between them,
# e.g. [2, "then", 0] = first step of the Sim branch of the third step.
Path = list[int | str]


@dataclass(frozen=True)
class Frame:
    """Where to continue at one nesting level, and with which items."""

    path: Path
    next_index: int
    item_keys: list[str]

    def dump(self) -> dict[str, Any]:
        return {"path": self.path, "next_index": self.next_index, "item_keys": self.item_keys}

    @classmethod
    def load(cls, raw: dict[str, Any]) -> "Frame":
        return cls(list(raw["path"]), int(raw["next_index"]), list(raw["item_keys"]))


@dataclass(frozen=True)
class SendRequest:
    step: SendEmailStep
    items: list[FlowItem]
    fields: dict[str, Any]
    unit: str | None
    unit_emails: list[str]


@dataclass
class Suspension:
    reason: str
    resume_at: datetime.datetime | None
    approval: ApprovalStep | None
    frames: list[Frame]


@dataclass
class Outcome:
    suspension: Suspension | None = None
    trace: list[str] = field(default_factory=list)


class _Suspend(Exception):
    def __init__(self, suspension: Suspension) -> None:
        self.suspension = suspension


def summary_fields(items: Sequence[FlowItem], base: dict[str, Any] | None = None) -> dict[str, Any]:
    total = sum((Decimal(str(item.fields.get("valor") or 0)) for item in items), Decimal(0))
    return {**(base or {}), "itens": len(items), "valor_total": float(total)}


def split(
    step: ConditionStep, definition: FlowDefinitionV2, items: list[FlowItem], base: dict[str, Any]
) -> tuple[list[FlowItem] | None, list[FlowItem] | None]:
    """(items for Sim, items for Não); ``None`` = that branch does not run."""
    spec = TRIGGERS[definition.trigger.kind]
    item_clauses = []
    summary_clauses = []
    for clause in step.conditions:
        target = spec.field(clause.field)
        assert target is not None
        (item_clauses if target.per_item else summary_clauses).append(clause)
    if item_clauses:
        matched = [i for i in items if all(_matches(i.fields.get(c.field), c) for c in item_clauses)]
        rest = [i for i in items if i not in matched]
    else:
        matched, rest = list(items), []
    fields = summary_fields(matched, base)
    if not all(_matches(fields.get(c.field), c) for c in summary_clauses):
        return None, list(items)
    if item_clauses:
        return (matched or None), (rest or None)
    return matched, None


def wait_until(step: WaitStep, now: datetime.datetime) -> datetime.datetime:
    if step.mode == "duration":
        return now + datetime.timedelta(days=step.days, hours=step.hours)
    assert step.weekday is not None and step.time is not None
    local = now.astimezone(BRASILIA)
    hour, minute = (int(part) for part in step.time.split(":"))
    for offset in range(0, 8):
        day = local.date() + datetime.timedelta(days=offset)
        if day.weekday() != step.weekday:
            continue
        slot = datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=BRASILIA)
        if slot > local:
            return slot
    raise AssertionError("a slot exists within eight days")


class Engine:
    def __init__(
        self,
        definition: FlowDefinitionV2,
        *,
        base_fields: dict[str, Any],
        send: Callable[[SendRequest], None],
        now: datetime.datetime,
        simulate: bool = False,
    ) -> None:
        # simulate: preview and test sends walk past waits and approvals.
        self.simulate = simulate
        self.definition = definition
        self.base_fields = base_fields
        self.send = send
        self.now = now
        self.trace: list[str] = []

    # -- public ------------------------------------------------------------

    def run(self, items: list[FlowItem]) -> Outcome:
        try:
            self._run_list(self.definition.steps, items, [], 0, unit=None, unit_emails=[])
        except _Suspend as suspended:
            return Outcome(suspended.suspension, self.trace)
        return Outcome(None, self.trace)

    def resume(self, frames: list[Frame], fresh: list[FlowItem]) -> Outcome:
        """Continue after a suspension. ``frames`` go innermost first; each
        keeps only the items still present in ``fresh``."""
        by_key = {item.key: item for item in fresh}
        for position, frame in enumerate(frames):
            items = [by_key[key] for key in frame.item_keys if key in by_key]
            try:
                self._run_list(self._steps_at(frame.path), items, frame.path, frame.next_index, unit=None, unit_emails=[])
            except _Suspend as suspended:
                suspended.suspension.frames.extend(frames[position + 1 :])
                return Outcome(suspended.suspension, self.trace)
        return Outcome(None, self.trace)

    # -- internals ---------------------------------------------------------

    def _steps_at(self, path: Path) -> list[Any]:
        steps: list[Any] = self.definition.steps
        index = 0
        while index < len(path):
            step = steps[int(path[index])]
            branch = path[index + 1]
            if isinstance(step, ConditionStep):
                steps = step.then if branch == "then" else step.otherwise
            elif isinstance(step, ForEachUnitStep):
                steps = step.steps
            index += 2
        return steps

    def _run_list(
        self,
        steps: list[Any],
        items: list[FlowItem],
        path: Path,
        start: int,
        *,
        unit: str | None,
        unit_emails: list[str],
    ) -> None:
        for index in range(start, len(steps)):
            step = steps[index]
            here = [*path, index]
            try:
                self._run_step(step, items, here, unit=unit, unit_emails=unit_emails)
            except _Suspend as suspended:
                # Inner frames first; this level continues after the step.
                suspended.suspension.frames.append(
                    Frame(path, index + 1, [item.key for item in items])
                )
                raise

    def _run_step(
        self,
        step: Any,
        items: list[FlowItem],
        here: Path,
        *,
        unit: str | None,
        unit_emails: list[str],
    ) -> None:
        if isinstance(step, SendEmailStep):
            fields = summary_fields(items, self.base_fields)
            self.send(SendRequest(step, list(items), fields, unit, unit_emails))
            self.trace.append(f"{step.id}: e-mail ({len(items)} itens)")
            return
        if isinstance(step, ConditionStep):
            yes, no = split(step, self.definition, items, self.base_fields)
            self.trace.append(
                f"{step.id}: Sim {len(yes) if yes is not None else '-'} / Não {len(no) if no is not None else '-'}"
            )
            if yes is not None:
                try:
                    self._run_list(step.then, yes, [*here, "then"], 0, unit=unit, unit_emails=unit_emails)
                except _Suspend as suspended:
                    # The Não branch still has to run after the Sim branch resumes.
                    if no is not None:
                        suspended.suspension.frames.append(
                            Frame([*here, "else"], 0, [item.key for item in no])
                        )
                    raise
            if no is not None:
                self._run_list(step.otherwise, no, [*here, "else"], 0, unit=unit, unit_emails=unit_emails)
            return
        if isinstance(step, ForEachUnitStep):
            by_unit: dict[str, list[FlowItem]] = defaultdict(list)
            for item in items:
                by_unit[str(item.fields.get("unidade") or "Sem unidade")].append(item)
            for name in sorted(by_unit):
                self.trace.append(f"{step.id}: unidade {name} ({len(by_unit[name])})")
                self._run_list(step.steps, by_unit[name], [*here, "steps"], 0, unit=name, unit_emails=step.emails_for(name))
            return
        itemless = self.definition.trigger.kind is TriggerKind.DRE_RECALCULATED
        if isinstance(step, WaitStep):
            if not items and not itemless:
                self.trace.append(f"{step.id}: nada a esperar")
                return
            resume_at = wait_until(step, self.now)
            self.trace.append(f"{step.id}: esperar até {resume_at.isoformat()}")
            if self.simulate:
                return
            raise _Suspend(Suspension("wait", resume_at, None, []))
        if isinstance(step, ApprovalStep):
            if not items and not itemless:
                self.trace.append(f"{step.id}: nada a aprovar")
                return
            self.trace.append(f"{step.id}: aguardando aprovação")
            if self.simulate:
                return
            raise _Suspend(Suspension("approval", None, step, []))
        raise AssertionError(f"unknown step {type(step).__name__}")
