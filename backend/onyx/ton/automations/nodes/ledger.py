"""Financial tests and the occurrence ledger as automation nodes.

A routine can run the Prompt Mestre tests (T1 … T10), record the hits in the
ledger and react to cases recorded by the chat or by the R1 sweep.
"""

from decimal import Decimal
from typing import Any

from onyx.ton.automations.expressions import format_money, to_number, to_text
from onyx.ton.automations.nodes.common import by_unit, summarize
from onyx.ton.automations.registry import (
    ActionContext,
    ActionError,
    NodeSpec,
    OutputSpec,
    ParamSpec,
    TriggerContext,
    register,
)

EVENT_KIND_LEDGER = "TON_LEDGER_CASES_RECORDED"

TEST_OPTIONS = (
    ("T1", "T1 · Grupo zerado"),
    ("T2", "T2 · Desvio de média"),
    ("T3", "T3 · Duplicidade"),
    ("T4", "T4 · Receita NG × notas fiscais"),
    ("T6", "T6 · Sinal invertido"),
    ("T8", "T8 · Fornecedor × unidade"),
    ("T9", "T9 · Competência retroativa"),
    ("T10", "T10 · Evento não recorrente"),
)
ALL_TESTS = [code for code, _ in TEST_OPTIONS]
CRITICALITY_OPTIONS = (
    ("MONITORING", "Monitoramento ou acima"),
    ("MEDIUM", "Médio ou acima"),
    ("HIGH", "Alto ou acima"),
    ("CRITICAL", "Só crítico"),
)
CRITICALITY_RANK = {"MONITORING": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
CRITICALITY_LABEL = {"Monitoramento": "MONITORING", "Médio": "MEDIUM", "Alto": "HIGH", "Crítico": "CRITICAL"}

CASE_FIELDS = (
    OutputSpec("codigo", "Código da ocorrência", "string"),
    OutputSpec("titulo", "Caso", "string"),
    OutputSpec("teste", "Teste", "string"),
    OutputSpec("unidade", "Unidade", "string"),
    OutputSpec("criticidade", "Criticidade", "string"),
    OutputSpec("situacao", "Novo ou repetido", "string"),
    OutputSpec("valor", "Impacto", "number"),
    OutputSpec("valor_formatado", "Impacto (R$)", "string"),
    OutputSpec("link", "Link", "string"),
)
HIT_FIELDS = (
    OutputSpec("chave", "Chave do caso", "string"),
    OutputSpec("titulo", "Caso", "string"),
    OutputSpec("unidade", "Unidade", "string"),
    OutputSpec("valor", "Impacto", "number"),
    OutputSpec("valor_formatado", "Impacto (R$)", "string"),
)
SITUATION_TEXT = {"NEW": "Novo", "SUPERSEDED": "Novo", "REPEATED": "Repetido", "REOPENED": "Reaberto"}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [to_text(item).strip() for item in value if to_text(item).strip()]
    return [part.strip() for part in to_text(value).split(",") if part.strip()]


def _bands(params: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    values = [to_number(params.get(key)) for key in ("band_critical", "band_high", "band_medium")]
    first, second, third = (
        Decimal(str(value if value is not None else default))
        for value, default in zip(values, (1.0, 0.3, 0.1), strict=True)
    )
    if not first > second > third > 0:
        raise ActionError("Faixas da régua: crítico > alto > médio > 0")
    return first, second, third


def case_item(outcome: dict[str, Any], test: str, impact: Decimal) -> dict[str, Any]:
    return {
        "chave": outcome["ocorrencia"],
        "codigo": outcome.get("codigo") or "",
        "titulo": outcome.get("titulo") or "",
        "teste": test,
        "unidade": outcome.get("unidade") or "Consolidado",
        "criticidade": outcome.get("criticidade") or "",
        "situacao": SITUATION_TEXT.get(str(outcome.get("situacao")), str(outcome.get("situacao"))),
        "valor": float(impact),
        "valor_formatado": format_money(impact),
        "link": "/ton/ocorrencias",
    }


# -- step: run one test ------------------------------------------------------


def _hits(ctx: ActionContext, test: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    from onyx.db.ton import agent_investigations as inv

    session, owner = ctx.require_db()
    query: dict[str, Any] = {"test": test}
    period = to_text(params.get("period")).strip()
    if period:
        query["period"] = period
    unit = to_text(params.get("unit")).strip()
    if unit:
        query["unit"] = unit
    try:
        result = inv.run_test(session, owner, query)
    except inv.InvestigationError as error:
        raise ActionError(str(error)) from error
    hits = []
    for item in result["_todos"]:
        ledger = item.get("_ledger")
        if not ledger:
            continue
        hits.append(
            {
                "chave": ledger["chave"],
                "titulo": ledger["titulo"],
                "unidade": ledger["unidade"] or "Consolidado",
                "valor": float(ledger["valor"]),
                "valor_formatado": format_money(ledger["valor"]),
            }
        )
    return hits


def _record(
    ctx: ActionContext,
    test: str,
    params: dict[str, Any],
    routine: str,
    *,
    emit_event: bool = True,
) -> list[dict[str, Any]]:
    from onyx.db.ton import agent_ledger
    from onyx.db.ton.enums import AnalysisTrigger

    session, owner = ctx.require_db()
    query: dict[str, Any] = {}
    period = to_text(params.get("period")).strip()
    if period:
        query["period"] = period
    unit = to_text(params.get("unit")).strip()
    if unit:
        query["unit"] = unit
    try:
        plan = agent_ledger.plan_cases(session, owner, test, query, None, _bands(params))
    except ValueError as error:
        raise ActionError(str(error)) from error
    outcomes = agent_ledger.register_plan__no_commit(
        session,
        owner,
        plan,
        trigger=AnalysisTrigger.SCHEDULED,
        idempotency_key=f"ton-automation:{ctx.run_id}:{ctx.node_id}:{ctx.iteration}:{test}",
        routine_code=routine,
        emit_event=emit_event,
    )
    impacts = {case.key: case.impact for case in plan.cases}
    keys = [case.key for case in plan.cases]
    return [
        case_item(outcome, test, impacts.get(key, Decimal(0)))
        for outcome, key in zip(outcomes, keys, strict=True)
    ]


def _financial_test(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    test = to_text(params.get("test")).strip()
    if test not in ALL_TESTS:
        raise ActionError("Escolha o teste (T1 … T10)")
    if params.get("record") and not ctx.is_test:
        cases = _record(ctx, test, params, "AUTOMATION")
        new = [case for case in cases if case["situacao"] == "Novo"]
        return {**summarize(cases), "new_items": new, "new_count": len(new), "by_unit": by_unit(cases)}
    hits = _hits(ctx, test, params)
    return {**summarize(hits), "new_items": [], "new_count": 0, "by_unit": by_unit(hits)}


register(
    NodeSpec(
        type="ton.financial_test",
        group="ton",
        label="Rodar teste financeiro",
        description="Roda um teste do Prompt Mestre (duplicidade, desvio de média, competência retroativa…) sobre a base do NG e, se pedido, registra os casos no ledger de ocorrências.",
        icon="search",
        params=(
            ParamSpec("test", "Teste", "select", required=True, default="T3", dynamic=False, options=TEST_OPTIONS),
            ParamSpec("period", "Mês (aaaa-mm; vazio = último da base)", "text", placeholder="2026-09"),
            ParamSpec("unit", "Unidade (vazio = todas)", "text"),
            ParamSpec("record", "Registrar os casos no ledger", "boolean", default=False, dynamic=False),
            ParamSpec("band_critical", "Crítico a partir de (% da receita)", "number", default=1.0, min=0, advanced=True),
            ParamSpec("band_high", "Alto a partir de (%)", "number", default=0.3, min=0, advanced=True),
            ParamSpec("band_medium", "Médio a partir de (%)", "number", default=0.1, min=0, advanced=True),
        ),
        outputs=(
            OutputSpec("items", "Casos", "array", item_fields=CASE_FIELDS),
            OutputSpec("count", "Quantidade", "number"),
            OutputSpec("total", "Impacto total", "number"),
            OutputSpec("total_formatado", "Impacto total (R$)", "string"),
            OutputSpec("new_items", "Casos novos no ledger", "array", item_fields=CASE_FIELDS),
            OutputSpec("new_count", "Quantidade de casos novos", "number"),
            OutputSpec("by_unit", "Por unidade", "array"),
        ),
        executor=_financial_test,
        keywords=("teste", "duplicidade", "desvio", "anomalia", "varredura", "ledger", "ocorrência"),
        summary=lambda params: f"Teste {params.get('test') or ''}" + (" e registra no ledger" if params.get("record") else ""),
    )
)


# -- step: sweep -------------------------------------------------------------


def _sweep(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    tests = [test for test in _list(params.get("tests")) if test in ALL_TESTS] or ALL_TESTS
    cases: list[dict[str, Any]] = []
    per_test: list[dict[str, Any]] = []
    for test in tests:
        if ctx.is_test:
            found = _hits(ctx, test, params)
            per_test.append({"teste": test, "count": len(found), "new_count": 0})
            cases.extend({**hit, "teste": test, "situacao": "Teste", "criticidade": ""} for hit in found)
            continue
        recorded = _record(ctx, test, params, "R1", emit_event=False)
        per_test.append(
            {
                "teste": test,
                "count": len(recorded),
                "new_count": sum(1 for case in recorded if case["situacao"] == "Novo"),
            }
        )
        cases.extend(recorded)
    new = [case for case in cases if case["situacao"] == "Novo"]
    if cases and not ctx.is_test:
        _emit_sweep_event(ctx, tests, cases)
    return {
        **summarize(cases),
        "new_items": new,
        "new_count": len(new),
        "by_test": per_test,
        "by_unit": by_unit(cases),
    }


def _emit_sweep_event(
    ctx: ActionContext, tests: list[str], cases: list[dict[str, Any]]
) -> None:
    """One event for the whole sweep, so a listener runs once per sweep."""
    from onyx.db.ton.email_flows import emit_flow_event__no_commit

    session, _owner = ctx.require_db()
    emit_flow_event__no_commit(
        session,
        kind=EVENT_KIND_LEDGER,
        event_key=f"sweep:{ctx.run_id}:{ctx.node_id}:{ctx.iteration}",
        payload={"teste": ", ".join(tests), "origem": "varredura R1", "cases": cases},
    )
    session.flush()


register(
    NodeSpec(
        type="ton.financial_sweep",
        group="ton",
        label="Varredura financeira (R1)",
        description="Roda vários testes do Prompt Mestre no último mês e registra os casos no ledger; repetições não duplicam. Em teste da automação, só lista sem registrar.",
        icon="shield",
        params=(
            ParamSpec("tests", "Testes", "multiselect", default=ALL_TESTS, dynamic=False, options=TEST_OPTIONS),
            ParamSpec("period", "Mês (aaaa-mm; vazio = último da base)", "text", placeholder="2026-09"),
            ParamSpec("band_critical", "Crítico a partir de (% da receita)", "number", default=1.0, min=0, advanced=True),
            ParamSpec("band_high", "Alto a partir de (%)", "number", default=0.3, min=0, advanced=True),
            ParamSpec("band_medium", "Médio a partir de (%)", "number", default=0.1, min=0, advanced=True),
        ),
        outputs=(
            OutputSpec("items", "Casos", "array", item_fields=CASE_FIELDS),
            OutputSpec("count", "Quantidade", "number"),
            OutputSpec("total", "Impacto total", "number"),
            OutputSpec("total_formatado", "Impacto total (R$)", "string"),
            OutputSpec("new_items", "Casos novos", "array", item_fields=CASE_FIELDS),
            OutputSpec("new_count", "Quantidade de casos novos", "number"),
            OutputSpec("by_test", "Por teste", "array"),
            OutputSpec("by_unit", "Por unidade", "array"),
        ),
        executor=_sweep,
        side_effect=True,
        keywords=("varredura", "r1", "rotina", "testes", "ledger", "anomalias", "diária"),
        summary=lambda params: "Testes " + ", ".join(_list(params.get("tests")) or ALL_TESTS),
    )
)


# -- trigger: cases recorded ---------------------------------------------------


def _cases_recorded(
    ctx: TriggerContext, params: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any] | None:
    tests = set(_list(params.get("tests")))
    minimum = CRITICALITY_RANK.get(to_text(params.get("min_criticality")) or "MONITORING", 0)
    only_new = params.get("only_new", True) is not False
    items = []
    for case in payload.get("cases") or []:
        if tests and case.get("teste") not in tests:
            continue
        if only_new and case.get("situacao") != "Novo":
            continue
        rank = CRITICALITY_RANK.get(CRITICALITY_LABEL.get(str(case.get("criticidade")), "MONITORING"), 0)
        if rank < minimum:
            continue
        items.append(case)
    if not items:
        return None
    return {
        **summarize(items),
        "by_unit": by_unit(items),
        "origem": payload.get("origem") or "",
        "teste": payload.get("teste") or "",
        "link": "/ton/ocorrencias",
    }


register(
    NodeSpec(
        type="trigger.ledger_cases",
        group="trigger",
        label="Casos registrados no ledger",
        description="Quando o chat, a varredura R1 ou outra automação registra casos dos testes financeiros no ledger de ocorrências.",
        icon="shield",
        is_trigger=True,
        params=(
            ParamSpec("tests", "Só estes testes (vazio = todos)", "multiselect", default=[], dynamic=False, options=TEST_OPTIONS),
            ParamSpec("min_criticality", "Criticidade mínima", "select", default="MONITORING", dynamic=False, options=CRITICALITY_OPTIONS),
            ParamSpec("only_new", "Só casos novos (ignorar repetidos)", "boolean", default=True, dynamic=False),
        ),
        outputs=(
            OutputSpec("items", "Casos", "array", item_fields=CASE_FIELDS),
            OutputSpec("count", "Quantidade", "number"),
            OutputSpec("total", "Impacto total", "number"),
            OutputSpec("total_formatado", "Impacto total (R$)", "string"),
            OutputSpec("by_unit", "Por unidade", "array"),
            OutputSpec("origem", "Origem (chat, R1, automação)", "string"),
            OutputSpec("teste", "Teste", "string"),
            OutputSpec("link", "Link do ledger", "string"),
        ),
        prepare=_cases_recorded,
        event_kinds=(EVENT_KIND_LEDGER,),
        keywords=("ledger", "ocorrência", "varredura", "teste", "r1", "duplicidade"),
    )
)
