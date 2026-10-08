"""TON steps: read the TON read models (with the owner's visibility) and
publish notices in the TON bell."""

from typing import Any

from onyx.ton.automations.definition import AutomationKind
from onyx.ton.automations.expressions import to_number, to_text
from onyx.ton.automations.nodes.common import (
    ACCOUNT_ITEM_FIELDS,
    BY_UNIT_FIELDS,
    INCONSISTENCY_ITEM_FIELDS,
    by_unit,
    inconsistency_item,
    list_outputs,
    review_note,
    summarize,
)
from onyx.ton.automations.nodes.triggers import account_rows
from onyx.ton.automations.registry import (
    ActionContext,
    ActionError,
    NodeSpec,
    OutputSpec,
    ParamSpec,
    register,
)
from onyx.ton.email_flows.catalog import ITEM_STATE_LABELS, ItemState

_STATES = tuple((state.value, ITEM_STATE_LABELS[state].capitalize()) for state in ItemState)
_OPEN_STATES = [s.value for s in ItemState if s is not ItemState.CORRECTED]


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [to_text(v).strip() for v in value if to_text(v).strip()]
    return [part.strip() for part in to_text(value).split(",") if part.strip()]


def _inconsistencies(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    from onyx.db.ton import email_flows as flow_repository

    session, owner = ctx.require_db()
    snapshot = flow_repository.inconsistencies(session, owner, now=ctx.now)
    states = set(_list(params.get("situations")) or _OPEN_STATES)
    units = {unit.casefold() for unit in _list(params.get("units"))}
    rules = {rule.casefold() for rule in _list(params.get("rules"))}
    minimum = to_number(params.get("min_value"))
    items = []
    for raw in snapshot.items:
        item = inconsistency_item(raw)
        if item["situacao"] not in states:
            continue
        if units and str(item["unidade"]).casefold() not in units:
            continue
        if rules and str(item["regra"]).casefold() not in rules:
            continue
        if minimum is not None and minimum > 0 and abs(item["valor"]) < float(minimum):
            continue
        items.append(item)
    return {**summarize(items), "by_unit": by_unit(items), "note": review_note(snapshot.last_review_at)}


register(
    NodeSpec(
        type="ton.inconsistencies",
        group="ton",
        label="Buscar inconsistências do NG",
        description="Lista as inconsistências do NG no TON, com evidência, unidade, valor, o que corrigir e semanas em aberto.",
        icon="alert",
        params=(
            ParamSpec("situations", "Situações", "multiselect", default=_OPEN_STATES, dynamic=False, options=_STATES),
            ParamSpec("units", "Só estas unidades (opcional)", "list", default=[]),
            ParamSpec("rules", "Só estas regras (opcional)", "list", default=[], placeholder="NGF-DUP-DOC"),
            ParamSpec("min_value", "Valor mínimo (R$)", "number", default=0, min=0),
        ),
        outputs=(
            *list_outputs(INCONSISTENCY_ITEM_FIELDS, "inconsistências"),
            OutputSpec("by_unit", "Por unidade", "array", item_fields=BY_UNIT_FIELDS),
            OutputSpec("note", "Nota da última extração", "string"),
        ),
        executor=_inconsistencies,
        keywords=("ng", "erros", "pendências", "duplicidade", "inconsistência"),
    )
)


def _accounts(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    ctx.require_db()
    return summarize(account_rows(ctx, None))


register(
    NodeSpec(
        type="ton.accounts_unclassified",
        group="ton",
        label="Buscar contas sem classificação",
        description="Lista as contas do NG que ainda não têm natureza confirmada no TON.",
        icon="tag",
        outputs=list_outputs(ACCOUNT_ITEM_FIELDS, "contas"),
        executor=_accounts,
        keywords=("classificação", "natureza", "contas"),
    )
)


def _notify(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    from onyx.db.ton import automations as repository

    session, _owner = ctx.require_db()
    title = to_text(params.get("title")).strip()
    if not title:
        raise ActionError("Informe o título do aviso")
    link = to_text(params.get("link")).strip()
    if link and not (link.startswith("/ton") or link.startswith("https://")):
        raise ActionError("Link: use um caminho do TON (/ton/...) ou um endereço https://")
    notice = repository.add_notice__no_commit(
        session,
        automation_id=ctx.automation_id,
        run_id=ctx.run_id,
        title=title[:200],
        message=to_text(params.get("message"))[:4000],
        severity=str(params.get("severity") or "INFO"),
        link=link[:500] or None,
        is_test=ctx.is_test,
    )
    session.flush()
    return {"notice_id": str(notice.id)}


register(
    NodeSpec(
        type="ton.notify",
        group="ton",
        label="Avisar no TON",
        description="Publica um aviso no sino do TON para a equipe, com link para a tela certa.",
        icon="bell",
        params=(
            ParamSpec("title", "Título", "text", required=True, placeholder="{{ trigger.outputs.count }} inconsistências novas"),
            ParamSpec("message", "Mensagem", "textarea"),
            ParamSpec("severity", "Importância", "select", default="INFO", dynamic=False, options=(("INFO", "Informativo"), ("WARNING", "Atenção"), ("CRITICAL", "Crítico"))),
            ParamSpec("link", "Link", "text", placeholder="/ton/pendencias"),
        ),
        outputs=(OutputSpec("notice_id", "Id do aviso", "string"),),
        executor=_notify,
        side_effect=True,
        satisfies=(AutomationKind.ALERT,),
        keywords=("sino", "notificação", "alerta", "aviso"),
    )
)
