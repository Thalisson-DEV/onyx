"""What each trigger hands a flow: items and summary fields, read from the
TON read models with the reader's visibility."""

import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import email_flows as repository
from onyx.db.ton.account_classification import classification_table
from onyx.ton.account_classification.models import ClassificationStatus
from onyx.ton.email_flows.catalog import ITEM_STATE_LABELS, ItemState, TriggerKind
from onyx.ton.email_flows.logic import BRASILIA, FlowEvent, FlowItem
from onyx.ton.email_flows.models import FlowTrigger


def _review_note(last_review_at: datetime.datetime | None) -> str | None:
    if last_review_at is None:
        return "Nenhuma extração do NG conferida ainda."
    local = last_review_at.astimezone(BRASILIA)
    return f"Última extração do NG conferida em {local:%d/%m/%Y às %H:%M}."


def _dre_note(payload: dict[str, object]) -> tuple[int | None, str | None]:
    months = sorted(str(item) for item in payload.get("competencias") or [])  # type: ignore[union-attr]
    units = [str(unit) for unit in payload.get("unidades") or []]  # type: ignore[union-attr]
    if not months:
        return None, None
    first = datetime.date.fromisoformat(months[0])
    latest = datetime.date.fromisoformat(months[-1])
    span = f"{first:%m/%Y}" if first == latest else f"{first:%m/%Y} a {latest:%m/%Y}"
    others = len([unit for unit in units if unit != "consolidado"])
    scope = " + ".join(
        part
        for part in (
            "consolidado" if "consolidado" in units else "",
            f"{others} {'unidade' if others == 1 else 'unidades'}" if others else "",
        )
        if part
    )
    return latest.month, f"Meses recalculados: {span} ({scope})."


def build_event(
    session: Session,
    reader: User,
    trigger: FlowTrigger,
    *,
    event_key: str,
    payload: dict[str, object],
    now: datetime.datetime,
) -> FlowEvent:
    kind = trigger.kind
    if kind in (
        TriggerKind.SCHEDULE,
        TriggerKind.NG_IMPORT_COMPLETED,
        TriggerKind.NG_OCCURRENCE_CHANGED,
    ):
        review_run_id = payload.get("review_run_id")
        snapshot = repository.inconsistencies(
            session,
            reader,
            now=now,
            review_run_id=UUID(str(review_run_id)) if review_run_id else None,
        )
        items = snapshot.items
        if kind is TriggerKind.SCHEDULE:
            items = [i for i in items if i.fields["situacao"] != ItemState.CORRECTED.value]
        elif kind is TriggerKind.NG_OCCURRENCE_CHANGED:
            wanted = {change.value for change in trigger.changes}
            items = [
                FlowItem(
                    i.key,
                    i.fields,
                    {**i.columns, "situacao": ITEM_STATE_LABELS[ItemState(i.fields["mudou"])]},
                )
                for i in items
                if i.fields.get("mudou") in wanted
            ]
        return FlowEvent(kind, event_key, now, {}, items, _review_note(snapshot.last_review_at))
    if kind is TriggerKind.ACCOUNT_UNCLASSIFIED:
        source_id = payload.get("source_id")
        table = classification_table(session, reader, UUID(str(source_id)) if source_id else None)
        items = [
            FlowItem(
                row.account_code,
                {"conta": row.account_code, "valor": float(row.total_amount), "lancamentos": row.entries},
                {"descricao": row.description},
            )
            for row in table.rows
            if row.status is not ClassificationStatus.CONFIRMED
        ]
        return FlowEvent(kind, event_key, now, {}, items)
    competencia, note = _dre_note(payload)
    return FlowEvent(kind, event_key, now, {"competencia": competencia}, (), note)
