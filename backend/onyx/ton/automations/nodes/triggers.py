"""Triggers: what starts a run, and the output it freezes for the steps.

``prepare`` runs once when the run is created, with the owner's visibility;
its result is stored on the run, so a resumed run sees the same data.
Returning ``None`` means "no run" (e.g. no inconsistency changed)."""

import datetime
from typing import Any

from onyx.ton.automations.expressions import BRASILIA, format_money, to_number, to_text
from onyx.ton.automations.nodes.common import (
    ACCOUNT_ITEM_FIELDS,
    BY_UNIT_FIELDS,
    INCONSISTENCY_ITEM_FIELDS,
    by_unit,
    inconsistency_item,
    list_outputs,
    optional_uuid,
    review_note,
    summarize,
)
from onyx.ton.automations.registry import (
    FieldSpec,
    OutputSpec,
    ParamSpec,
    NodeSpec,
    TriggerContext,
    register,
)
from onyx.ton.automations import schedule as recurrence
from onyx.ton.email_flows.catalog import (
    EVENT_KIND_DRE,
    EVENT_KIND_NG_IMPORT,
    ITEM_STATE_LABELS,
    ItemState,
)

EVENT_KIND_AUTOMATION_FAILED = "AUTOMATION_RUN_FAILED"

_WEEKDAYS = tuple((str(index), name.capitalize()) for index, name in enumerate(recurrence.WEEKDAY_NAMES))
_CHANGES = tuple(
    (state.value, ITEM_STATE_LABELS[state].capitalize())
    for state in (ItemState.NEW, ItemState.CORRECTED, ItemState.REAPPEARED)
)


def _date_outputs(moment: datetime.datetime) -> dict[str, Any]:
    local = moment.astimezone(BRASILIA)
    return {
        "data": local.strftime("%d/%m/%Y"),
        "hora": local.strftime("%H:%M"),
        "semana": local.isocalendar()[1],
        "mes": local.month,
        "ano": local.year,
        "dia_da_semana": recurrence.WEEKDAY_NAMES[local.weekday()],
    }


_DATE_OUTPUTS = (
    OutputSpec("data", "Data (dd/mm/aaaa)", "string"),
    OutputSpec("hora", "Hora (hh:mm)", "string"),
    OutputSpec("semana", "Semana do ano", "number"),
    OutputSpec("mes", "Mês", "number"),
    OutputSpec("ano", "Ano", "number"),
    OutputSpec("dia_da_semana", "Dia da semana", "string"),
)


# -- manual ------------------------------------------------------------------


def _manual(ctx: TriggerContext, params: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    given = payload.get("inputs") or {}
    inputs: dict[str, Any] = {}
    for field in params.get("inputs") or []:
        name = str(field.get("name") or "").strip()
        if not name:
            continue
        value = given.get(name, field.get("default"))
        if field.get("required") and value in (None, ""):
            raise ValueError(f"Preencha '{field.get('label') or name}'")
        kind = field.get("type") or "text"
        if kind == "number":
            value = to_number(value)
        elif kind == "boolean":
            value = to_text(value).strip().casefold() in ("true", "sim", "1") if not isinstance(value, bool) else value
        inputs[name] = value
    return {
        "inputs": inputs,
        "triggered_by": payload.get("user_email"),
        **_date_outputs(ctx.now),
    }


register(
    NodeSpec(
        type="trigger.manual",
        group="trigger",
        label="Executar manualmente",
        description="Roda quando alguém clica em Executar no TON ou pede no chat. Pode pedir informações antes.",
        icon="play",
        is_trigger=True,
        params=(
            ParamSpec(
                "inputs",
                "Informações pedidas ao executar",
                "fields",
                default=[],
                dynamic=False,
                item_fields=(
                    FieldSpec("name", "Nome (sem espaço)", placeholder="fornecedor"),
                    FieldSpec("label", "Pergunta", placeholder="Qual fornecedor?"),
                    FieldSpec(
                        "type",
                        "Tipo",
                        "select",
                        (("text", "Texto"), ("longtext", "Texto longo"), ("number", "Número"), ("boolean", "Sim/Não"), ("date", "Data"), ("email", "E-mail")),
                    ),
                    FieldSpec("required", "Obrigatório", "boolean"),
                ),
            ),
        ),
        outputs=(
            OutputSpec("inputs", "Informações preenchidas", "object"),
            OutputSpec("triggered_by", "Quem executou", "string"),
            *_DATE_OUTPUTS,
        ),
        dynamic_outputs="inputs",
        prepare=_manual,
        keywords=("botão", "instantâneo", "manual"),
    )
)


# -- schedule ------------------------------------------------------------------


def _scheduled(ctx: TriggerContext, params: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("scheduled_for")
    moment = datetime.datetime.fromisoformat(str(raw)) if raw else ctx.now
    return {"scheduled_for": moment.isoformat(), **_date_outputs(moment)}


register(
    NodeSpec(
        type="trigger.schedule",
        group="trigger",
        label="Recorrência",
        description="Roda numa agenda: a cada minutos, horas, dias, semanas ou meses, no horário de Brasília.",
        icon="calendar",
        is_trigger=True,
        params=(
            ParamSpec(
                "frequency",
                "Repetir",
                "select",
                required=True,
                default="week",
                dynamic=False,
                options=(("minute", "A cada minutos"), ("hour", "A cada horas"), ("day", "Diariamente"), ("week", "Semanalmente"), ("month", "Mensalmente")),
            ),
            ParamSpec("interval", "A cada", "number", default=1, dynamic=False, min=1, max=1000, show_if=("frequency", ("minute", "hour", "day"))),
            ParamSpec("weekdays", "Dias da semana", "weekdays", default=[0], dynamic=False, options=_WEEKDAYS, show_if=("frequency", ("week",))),
            ParamSpec("day_of_month", "Dia do mês", "number", default=1, dynamic=False, min=1, max=28, show_if=("frequency", ("month",))),
            ParamSpec("time", "Horário (Brasília)", "time", default="08:00", dynamic=False, show_if=("frequency", ("hour", "day", "week", "month")), help="Na frequência por hora, só os minutos contam."),
        ),
        outputs=(OutputSpec("scheduled_for", "Momento planejado", "string"), *_DATE_OUTPUTS),
        prepare=_scheduled,
        keywords=("agenda", "agendamento", "cron", "semanal", "diário", "mensal"),
        summary=lambda params: recurrence.describe(params),
    )
)


# -- NG import -----------------------------------------------------------------


def _snapshot(ctx: TriggerContext, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    from onyx.db.ton import email_flows as flow_repository

    if ctx.session is None or ctx.owner is None:
        return [], "Sem acesso ao banco."
    snapshot = flow_repository.inconsistencies(
        ctx.session,
        ctx.owner,
        now=ctx.now,
        review_run_id=optional_uuid(payload.get("review_run_id")),
    )
    return [inconsistency_item(item) for item in snapshot.items], review_note(snapshot.last_review_at)


_IMPORT_OUTPUTS = (
    *list_outputs(INCONSISTENCY_ITEM_FIELDS, "inconsistências"),
    OutputSpec("open_count", "Inconsistências abertas", "number"),
    OutputSpec("by_unit", "Por unidade", "array", item_fields=BY_UNIT_FIELDS),
    OutputSpec("note", "Nota da última extração", "string"),
    OutputSpec("review_run_id", "Id da revisão NG", "string"),
    OutputSpec("source_id", "Id da fonte", "string"),
)


def _ng_import(ctx: TriggerContext, params: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    items, note = _snapshot(ctx, payload)
    open_items = [item for item in items if item["situacao"] != ItemState.CORRECTED.value]
    return {
        **summarize(items),
        "open_count": len(open_items),
        "by_unit": by_unit(open_items),
        "note": note,
        "review_run_id": payload.get("review_run_id"),
        "source_id": payload.get("source_id"),
    }


register(
    NodeSpec(
        type="trigger.ng_import",
        group="trigger",
        label="Importação do NG concluída",
        description="Ao terminar a revisão de uma nova extração do NG. Traz cada inconsistência com a situação após a importação.",
        icon="upload",
        is_trigger=True,
        outputs=_IMPORT_OUTPUTS,
        prepare=_ng_import,
        event_kinds=(EVENT_KIND_NG_IMPORT,),
        keywords=("extração", "importação", "ng", "revisão"),
    )
)


def _ng_changed(ctx: TriggerContext, params: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
    wanted = {str(value) for value in params.get("changes") or [state for state, _ in _CHANGES]}
    items, note = _snapshot(ctx, payload)
    changed: list[dict[str, Any]] = []
    for item in items:
        change = item.get("mudou")
        if change is None and item["situacao"] == ItemState.CORRECTED.value:
            change = ItemState.CORRECTED.value
        if change in wanted:
            changed.append({**item, "mudou": change, "situacao_label": ITEM_STATE_LABELS[ItemState(change)]})
    if not changed:
        return None
    return {
        **summarize(changed),
        "by_unit": by_unit(changed),
        "note": note,
        "review_run_id": payload.get("review_run_id"),
        "source_id": payload.get("source_id"),
    }


register(
    NodeSpec(
        type="trigger.ng_occurrence_changed",
        group="trigger",
        label="Inconsistência nova, corrigida ou reaparecida",
        description="Ao terminar uma importação, só quando alguma inconsistência mudou de situação.",
        icon="alert",
        is_trigger=True,
        params=(
            ParamSpec("changes", "Mudanças", "multiselect", required=True, default=[state for state, _ in _CHANGES], dynamic=False, options=_CHANGES),
        ),
        outputs=(
            *list_outputs(INCONSISTENCY_ITEM_FIELDS, "inconsistências que mudaram"),
            OutputSpec("by_unit", "Por unidade", "array", item_fields=BY_UNIT_FIELDS),
            OutputSpec("note", "Nota da última extração", "string"),
            OutputSpec("review_run_id", "Id da revisão NG", "string"),
        ),
        prepare=_ng_changed,
        event_kinds=(EVENT_KIND_NG_IMPORT,),
        keywords=("ocorrência", "corrigida", "nova", "reapareceu"),
    )
)


def account_rows(ctx: TriggerContext | Any, source_id: Any) -> list[dict[str, Any]]:
    from onyx.db.ton.account_classification import classification_table
    from onyx.ton.account_classification.models import ClassificationStatus

    if ctx.session is None or ctx.owner is None:
        return []
    table = classification_table(ctx.session, ctx.owner, optional_uuid(source_id))
    return [
        {
            "conta": row.account_code,
            "descricao": row.description,
            "valor": float(row.total_amount),
            "valor_formatado": format_money(row.total_amount),
            "lancamentos": row.entries,
        }
        for row in table.rows
        if row.status is not ClassificationStatus.CONFIRMED
    ]


def _accounts(ctx: TriggerContext, params: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
    rows = account_rows(ctx, payload.get("source_id"))
    if not rows and params.get("skip_when_empty", True):
        return None
    return {**summarize(rows), "source_id": payload.get("source_id")}


register(
    NodeSpec(
        type="trigger.account_unclassified",
        group="trigger",
        label="Conta sem classificação",
        description="Ao terminar uma importação, quando há contas do NG sem natureza confirmada.",
        icon="tag",
        is_trigger=True,
        params=(ParamSpec("skip_when_empty", "Não rodar quando não houver contas", "boolean", default=True, dynamic=False),),
        outputs=(*list_outputs(ACCOUNT_ITEM_FIELDS, "contas"), OutputSpec("source_id", "Id da fonte", "string")),
        prepare=_accounts,
        event_kinds=(EVENT_KIND_NG_IMPORT,),
        keywords=("classificação", "natureza", "conta"),
    )
)


def _dre(ctx: TriggerContext, params: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    months = sorted(str(item) for item in payload.get("competencias") or [])
    units = [str(unit) for unit in payload.get("unidades") or []]
    latest = datetime.date.fromisoformat(months[-1]) if months else None
    first = datetime.date.fromisoformat(months[0]) if months else None
    span = ""
    if first and latest:
        span = f"{first:%m/%Y}" if first == latest else f"{first:%m/%Y} a {latest:%m/%Y}"
    return {
        "competencias": months,
        "ultimo_mes": latest.month if latest else None,
        "periodo": span,
        "unidades": units,
        "consolidado": "consolidado" in units,
        "note": f"Meses recalculados: {span}." if span else "",
    }


register(
    NodeSpec(
        type="trigger.dre_recalculated",
        group="trigger",
        label="DRE recalculada",
        description="Quando a DRE de um ou mais meses é recalculada (agrupado: recalcular o ano dispara uma vez).",
        icon="chart",
        is_trigger=True,
        outputs=(
            OutputSpec("competencias", "Meses recalculados (aaaa-mm-dd)", "array"),
            OutputSpec("ultimo_mes", "Último mês", "number"),
            OutputSpec("periodo", "Período (mm/aaaa a mm/aaaa)", "string"),
            OutputSpec("unidades", "Unidades", "array"),
            OutputSpec("consolidado", "Inclui o consolidado", "boolean"),
            OutputSpec("note", "Resumo", "string"),
        ),
        prepare=_dre,
        event_kinds=(EVENT_KIND_DRE,),
        keywords=("dre", "fechamento", "resultado"),
    )
)


def _automation_failed(ctx: TriggerContext, params: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
    wanted = {str(value) for value in params.get("automations") or []}
    if payload.get("automation_id") == ctx.automation_id:
        return None
    if wanted and str(payload.get("automation_id")) not in wanted:
        return None
    return {
        "automation_id": payload.get("automation_id"),
        "automation_name": payload.get("automation_name"),
        "run_id": payload.get("run_id"),
        "error": payload.get("error"),
        "link": payload.get("link"),
        **_date_outputs(ctx.now),
    }


register(
    NodeSpec(
        type="trigger.automation_failed",
        group="trigger",
        label="Uma automação falhou",
        description="Quando uma execução de outra automação termina com falha. Bom para avisar quem cuida.",
        icon="warning",
        is_trigger=True,
        params=(
            ParamSpec("automations", "Quais automações (vazio = todas)", "automations", default=[], dynamic=False),
        ),
        outputs=(
            OutputSpec("automation_name", "Automação", "string"),
            OutputSpec("automation_id", "Id da automação", "string"),
            OutputSpec("run_id", "Id da execução", "string"),
            OutputSpec("error", "Erro", "string"),
            OutputSpec("link", "Link da execução", "string"),
            *_DATE_OUTPUTS,
        ),
        prepare=_automation_failed,
        event_kinds=(EVENT_KIND_AUTOMATION_FAILED,),
        keywords=("erro", "falha", "monitorar"),
    )
)
