"""Pure flow logic: condition evaluation, recipient batching, schedule windows
and the plain-language sentences shown in the flows table. No database."""

import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from onyx.ton.email_flows.catalog import (
    ITEM_STATE_LABELS,
    OPERATOR_LABELS,
    TEMPLATE_LABELS,
    TRIGGERS,
    FieldType,
    ItemState,
    Operator,
    TriggerKind,
)
from onyx.ton.email_flows.models import (
    ConditionClause,
    EmailAction,
    FlowBranch,
    FlowDefinition,
    FlowTrigger,
)

BRASILIA = ZoneInfo("America/Sao_Paulo")
WEEKDAYS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")


@dataclass(frozen=True)
class FlowItem:
    """One listed thing (an inconsistency, an account) with the fields
    conditions read and the columns templates print."""

    key: str
    fields: Mapping[str, Any]
    columns: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FlowEvent:
    """What a trigger hands to a flow: an idempotency key, summary fields and
    the items it is about."""

    kind: TriggerKind
    key: str
    occurred_at: datetime.datetime
    fields: Mapping[str, Any] = field(default_factory=dict)
    items: Sequence[FlowItem] = ()
    note: str | None = None


@dataclass(frozen=True)
class Evaluation:
    branch: FlowBranch
    items: list[FlowItem]
    fields: dict[str, Any]
    reason: str


def _matches(value: Any, clause: ConditionClause) -> bool:
    if value is None:
        return False
    if clause.operator in (Operator.GT, Operator.GTE) or isinstance(
        clause.value, float
    ):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return False
        target = float(clause.value)  # type: ignore[arg-type]
        if clause.operator is Operator.GT:
            return number > target
        if clause.operator is Operator.GTE:
            return number >= target
        return number == target
    text = str(value).strip().casefold()
    if clause.operator is Operator.IN:
        return text in {str(item).strip().casefold() for item in clause.value}  # type: ignore[union-attr]
    return text == str(clause.value).strip().casefold()


def evaluate(definition: FlowDefinition, event: FlowEvent) -> Evaluation:
    """Item clauses filter the items; summary clauses (quantity, total, event
    fields) are then tested on what is left. All clauses must hold."""
    spec = TRIGGERS[definition.trigger.kind]
    item_clauses = []
    summary_clauses = []
    for clause in definition.conditions:
        target = spec.field(clause.field)
        assert target is not None
        (item_clauses if target.per_item else summary_clauses).append(clause)
    items = [
        item
        for item in event.items
        if all(_matches(item.fields.get(c.field), c) for c in item_clauses)
    ]
    total = sum(
        (Decimal(str(item.fields.get("valor") or 0)) for item in items), Decimal(0)
    )
    fields: dict[str, Any] = {
        **dict(event.fields),
        "itens": len(items),
        "valor_total": float(total),
    }
    failed = [c for c in summary_clauses if not _matches(fields.get(c.field), c)]
    if failed:
        return Evaluation(
            FlowBranch.NO, items, fields, f"Condição não atendida: {describe_clause(definition.trigger, failed[0])}"
        )
    if item_clauses and not items:
        return Evaluation(
            FlowBranch.NO, items, fields, f"Nenhum(a) {spec.item_noun} atende às condições"
        )
    return Evaluation(FlowBranch.YES, items, fields, "Condição atendida")


# ---------------------------------------------------------------------------
# Recipients
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecipientBatch:
    to: list[str]
    cc: list[str]
    bcc: list[str]


def batch_recipients(action: EmailAction, limit: int) -> list[RecipientBatch]:
    """One message with everyone, unless the provider's per-message limit is
    exceeded: then To repeats in each batch and Cc/Bcc are shared out."""
    limit = max(1, limit)
    if len(action.recipients()) <= limit:
        return [RecipientBatch(list(action.to), list(action.cc), list(action.bcc))]
    if len(action.to) >= limit:
        # To alone overflows: split it too, and copy people only once.
        to_chunks = [action.to[i : i + limit] for i in range(0, len(action.to), limit)]
        batches = [RecipientBatch(chunk, [], []) for chunk in to_chunks]
        rest = [("cc", item) for item in action.cc] + [("bcc", item) for item in action.bcc]
        for kind, address in rest:
            target = next((b for b in batches if len(b.to) + len(b.cc) + len(b.bcc) < limit), None)
            if target is None:
                target = RecipientBatch([], [], [])
                batches.append(target)
            (target.cc if kind == "cc" else target.bcc).append(address)
        return [b if b.to else RecipientBatch([action.to[0]], b.cc, b.bcc) for b in batches]
    room = limit - len(action.to)
    copies = [("cc", item) for item in action.cc] + [("bcc", item) for item in action.bcc]
    batches = []
    for start in range(0, len(copies), room):
        chunk = copies[start : start + room]
        batches.append(
            RecipientBatch(
                list(action.to),
                [address for kind, address in chunk if kind == "cc"],
                [address for kind, address in chunk if kind == "bcc"],
            )
        )
    return batches


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


def _slot(trigger: FlowTrigger, day: datetime.date) -> datetime.datetime:
    assert trigger.time is not None
    hour, minute = (int(part) for part in trigger.time.split(":"))
    return datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=BRASILIA)


def window_key(trigger: FlowTrigger, slot: datetime.datetime) -> str:
    local = slot.astimezone(BRASILIA)
    if trigger.frequency == "WEEKLY":
        year, week, _ = local.isocalendar()
        return f"schedule:{year}-W{week:02d}"
    return f"schedule:{local.date().isoformat()}"


def latest_slot(trigger: FlowTrigger, now: datetime.datetime) -> datetime.datetime:
    """The most recent scheduled moment at or before ``now``."""
    local = now.astimezone(BRASILIA)
    day = local.date()
    for offset in range(0, 8):
        candidate_day = day - datetime.timedelta(days=offset)
        if trigger.frequency == "WEEKLY" and candidate_day.weekday() != trigger.weekday:
            continue
        slot = _slot(trigger, candidate_day)
        if slot <= local:
            return slot
    raise AssertionError("a slot exists within eight days")


def next_slot(trigger: FlowTrigger, now: datetime.datetime) -> datetime.datetime:
    local = now.astimezone(BRASILIA)
    day = local.date()
    for offset in range(0, 9):
        candidate_day = day + datetime.timedelta(days=offset)
        if trigger.frequency == "WEEKLY" and candidate_day.weekday() != trigger.weekday:
            continue
        slot = _slot(trigger, candidate_day)
        if slot > local:
            return slot
    raise AssertionError("a slot exists within nine days")


def due_window(
    trigger: FlowTrigger,
    now: datetime.datetime,
    active_since: datetime.datetime,
    grace: datetime.timedelta = datetime.timedelta(hours=12),
) -> str | None:
    """The window to run now, if any. Never one before activation, and a
    window missed by more than ``grace`` is skipped instead of sent late."""
    if trigger.kind is not TriggerKind.SCHEDULE:
        return None
    slot = latest_slot(trigger, now)
    if slot < active_since or now - slot > grace:
        return None
    return window_key(trigger, slot)


# ---------------------------------------------------------------------------
# Sentences
# ---------------------------------------------------------------------------


def describe_trigger(trigger: FlowTrigger) -> str:
    if trigger.kind is TriggerKind.SCHEDULE:
        if trigger.frequency == "WEEKLY":
            assert trigger.weekday is not None
            return f"Toda {WEEKDAYS[trigger.weekday]} às {trigger.time}"
        return f"Todo dia às {trigger.time}"
    if trigger.kind is TriggerKind.NG_OCCURRENCE_CHANGED:
        changes = ", ".join(ITEM_STATE_LABELS[c] for c in trigger.changes)
        return f"Inconsistência {changes}"
    return TRIGGERS[trigger.kind].label


def _value_text(trigger: FlowTrigger, clause: ConditionClause) -> str:
    target = TRIGGERS[trigger.kind].field(clause.field)
    assert target is not None
    labels = dict(target.choices)
    values = clause.value if isinstance(clause.value, list) else [clause.value]
    if target.type is FieldType.MONEY:
        return ", ".join(format_money(Decimal(str(v))) for v in values)
    if target.type is FieldType.NUMBER:
        return ", ".join(f"{float(v):g}" for v in values)
    return ", ".join(labels.get(str(v), str(v)) for v in values)


def describe_clause(trigger: FlowTrigger, clause: ConditionClause) -> str:
    target = TRIGGERS[trigger.kind].field(clause.field)
    assert target is not None
    return f"{target.label.lower()} {OPERATOR_LABELS[clause.operator]} {_value_text(trigger, clause)}"


def describe_conditions(definition: FlowDefinition) -> str:
    if not definition.conditions:
        return "sempre"
    return " e ".join(describe_clause(definition.trigger, c) for c in definition.conditions)


def describe_action(action: EmailAction) -> str:
    if action.kind == "NONE":
        return "Não fazer nada"
    people = len(action.recipients())
    template = TEMPLATE_LABELS[action.template].split(" (")[0] if action.template else ""
    who = (
        f"{people} {'pessoa' if people == 1 else 'pessoas'}" if people else "sem destinatários"
    )
    return f"E-mail para {who} · {template}"


def format_money(value: Decimal | float | None) -> str:
    if value is None:
        return "—"
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    sign = "-" if amount < 0 else ""
    whole, cents = f"{abs(amount):.2f}".split(".")
    groups = []
    while whole:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    return f"{sign}R$ {'.'.join(groups)},{cents}"


def render_subject(subject: str, fields: Mapping[str, Any], when: datetime.datetime) -> str:
    local = when.astimezone(BRASILIA)
    values = {
        "semana": str(local.isocalendar()[1]),
        "data": local.strftime("%d/%m/%Y"),
        "total": str(fields.get("itens", 0)),
        "valor_total": format_money(fields.get("valor_total")),
    }
    for marker, value in values.items():
        subject = subject.replace("{" + marker + "}", value)
    return subject


def state_of(
    status_open: bool,
    first_detected_at: datetime.datetime,
    last_detected_at: datetime.datetime,
    verification: str | None,
    verification_checked_at: datetime.datetime | None,
    passed_before_last_detection: bool,
    latest_review_at: datetime.datetime | None,
) -> ItemState | None:
    """Where an open case stands after the latest import; ``None`` = not an
    open inconsistency (closed by a person). ``latest_review_at`` is when the
    latest review of the source started: a case first seen since then is new."""
    if not status_open:
        return None
    checked_after = (
        verification_checked_at is not None and verification_checked_at > last_detected_at
    )
    if checked_after and verification == "PASSED":
        return ItemState.CORRECTED
    if checked_after:
        return ItemState.CHECK_MANUALLY
    if passed_before_last_detection:
        return ItemState.REAPPEARED
    if latest_review_at is not None and first_detected_at >= latest_review_at:
        return ItemState.NEW
    return ItemState.OPEN
