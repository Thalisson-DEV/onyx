"""Automation engine: expressions, conditions, the durable interpreter
(replay, retries, run after, containers, waits, approvals) and the checker.
Synthetic data only."""

import datetime
from typing import Any

import pytest

from onyx.ton.automations.conditions import evaluate_group, parse_group
from onyx.ton.automations.definition import (
    AutomationDefinition,
    AutomationKind,
    RunStatus,
    StepStatus,
)
from onyx.ton.automations.expressions import ExpressionError, evaluate, render
from onyx.ton.automations.interpreter import Interpreter, MemoryStore
from onyx.ton.automations.registry import ActionError, NodeSpec, REGISTRY, register
from onyx.ton.automations.registry import get_registry
from onyx.ton.automations.schedule import latest_slot, next_slot
from onyx.ton.automations.validation import activation_problems, validate

NOW = datetime.datetime(2026, 10, 8, 12, 0, tzinfo=datetime.UTC)
ITEMS = [
    {"unidade": "Toledo-PR", "valor": 150000.0, "regra": "NGF-DUP-DOC"},
    {"unidade": "Toledo-PR", "valor": 200.0, "regra": "NGF-UNIT-MISSING"},
    {"unidade": "Cascavel-PR", "valor": 50.5, "regra": "NGF-DUP-DOC"},
]
CALLS: dict[str, int] = {}


def _flaky(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    CALLS["flaky"] = CALLS.get("flaky", 0) + 1
    if CALLS["flaky"] < int(params.get("succeed_on") or 1):
        raise ActionError("serviço fora", retryable=True)
    return {"ok": True, "calls": CALLS["flaky"]}


def _effect(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    CALLS["effect"] = CALLS.get("effect", 0) + 1
    return {"sent": params.get("text")}


def _boom(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    raise ActionError("falhou de propósito")


get_registry()
if "test.flaky" not in REGISTRY:
    from onyx.ton.automations.registry import ParamSpec

    register(NodeSpec("test.flaky", "integration", "Instável", "", "x", params=(ParamSpec("succeed_on", "n", "number"),), executor=_flaky))
    register(NodeSpec("test.effect", "integration", "Efeito", "", "x", params=(ParamSpec("text", "t"),), executor=_effect, side_effect=True))
    register(NodeSpec("test.boom", "integration", "Falha", "", "x", executor=_boom))


def _definition(steps: list[dict[str, Any]], variables: list[dict[str, Any]] | None = None) -> AutomationDefinition:
    return AutomationDefinition.model_validate(
        {"schema": 3, "trigger": {"type": "trigger.manual", "params": {}}, "variables": variables or [], "steps": steps}
    )


def _run(definition: AutomationDefinition, store: MemoryStore | None = None, *, now: datetime.datetime = NOW, mode: str = "LIVE", trigger: dict[str, Any] | None = None) -> tuple[Any, MemoryStore, Interpreter]:
    store = store or MemoryStore()
    interpreter = Interpreter(
        definition,
        store=store,
        trigger_outputs=trigger if trigger is not None else {"items": ITEMS, "count": len(ITEMS)},
        run_info={"id": "r1"},
        automation_info={"id": "a1", "name": "Teste"},
        mode=mode,
        now=lambda: now,
        sleep=lambda _seconds: None,
        test_recipient="eu@exemplo.com.br",
    )
    return interpreter.run(), store, interpreter


# -- expressions ---------------------------------------------------------------


def test_expressions_keep_type_and_interpolate() -> None:
    scope = {"steps": {"buscar": {"outputs": {"items": ITEMS, "count": 3}}}, "vars": {"prazo": "sexta"}}
    assert render("{{ steps.buscar.outputs.items }}", scope) == ITEMS
    assert render("Total {{ steps.buscar.outputs.count }} até {{ vars.prazo }}", scope) == "Total 3 até sexta"
    assert evaluate("sum(steps.buscar.outputs.items, 'valor')", scope) == 150250.5
    assert evaluate("format_money(sum(steps.buscar.outputs.items, 'valor'))", scope) == "R$ 150.250,50"
    assert evaluate("steps.buscar.outputs.items[0].unidade", scope) == "Toledo-PR"
    assert evaluate("steps.nada.outputs.x", scope) is None
    assert evaluate("steps.buscar.outputs.count > 2 and vars.prazo == 'SEXTA'", scope) is True
    assert evaluate("if(length(steps.buscar.outputs.items) > 5, 'muitos', 'poucos')", scope) == "poucos"
    assert evaluate("2 + 3 * 4", {}) == 14
    assert evaluate("not (1 > 2)", {}) is True


def test_expressions_reject_unknown_names_and_functions() -> None:
    with pytest.raises(ExpressionError):
        evaluate("os.system('x')", {})
    with pytest.raises(ExpressionError):
        evaluate("__import__('os')", {})
    with pytest.raises(ExpressionError):
        evaluate("eval(1)", {})


def test_condition_group_nested() -> None:
    group = parse_group(
        {
            "op": "and",
            "rules": [
                {"left": "{{ item.valor }}", "operator": "gt", "right": "100"},
                {"op": "or", "rules": [
                    {"left": "{{ item.unidade }}", "operator": "eq", "right": "toledo-pr"},
                    {"left": "{{ item.regra }}", "operator": "in", "right": "NGF-X, NGF-Y"},
                ]},
            ],
        }
    )
    assert [evaluate_group(group, {"item": item}) for item in ITEMS] == [True, True, False]


# -- interpreter -------------------------------------------------------------------


def test_filter_condition_foreach_and_variables() -> None:
    definition = _definition(
        [
            {"id": "grandes", "type": "data.filter", "params": {
                "items": "{{ trigger.outputs.items }}",
                "condition": {"op": "and", "rules": [{"left": "{{ item.valor }}", "operator": "gte", "right": "100"}]},
            }},
            {"id": "tem", "type": "control.condition", "params": {
                "condition": {"op": "and", "rules": [{"left": "{{ steps.grandes.outputs.count }}", "operator": "gt", "right": "0"}]},
            }, "then": [
                {"id": "cada", "type": "control.foreach", "params": {"items": "{{ steps.grandes.outputs.items }}"}, "steps": [
                    {"id": "conta", "type": "variable.increment", "params": {"name": "n", "by": 1}},
                    {"id": "junta", "type": "variable.append", "params": {"name": "nomes", "value": "{{ item.unidade }}"}},
                ]},
            ], "else": [
                {"id": "nada", "type": "data.compose", "params": {"value": "nada"}},
            ]},
            {"id": "fim", "type": "data.compose", "params": {"value": "{{ vars.n }} itens: {{ join(vars.nomes, '; ') }}"}},
        ],
        variables=[{"name": "n", "type": "number", "value": 0}, {"name": "nomes", "type": "array", "value": []}],
    )
    outcome, store, interpreter = _run(definition)
    assert outcome.status is RunStatus.SUCCEEDED
    assert interpreter.steps["fim"]["outputs"]["value"] == "2 itens: Toledo-PR; Toledo-PR"
    assert ("nada", "") not in store.records
    assert store.records[("conta", "/cada[1]")].outputs == {"value": 2}


def test_retry_suspends_and_resumes_without_repeating_finished_steps() -> None:
    CALLS.clear()
    definition = _definition(
        [
            {"id": "efeito", "type": "test.effect", "params": {"text": "a"}},
            {"id": "instavel", "type": "test.flaky", "params": {"succeed_on": 3},
             "retry": {"policy": "fixed", "count": 3, "interval_seconds": 60}},
        ]
    )
    outcome, store, _ = _run(definition)
    assert outcome.status is RunStatus.WAITING and outcome.waiting_on == "retry"
    assert store.records[("instavel", "")].status is StepStatus.WAITING
    later = NOW + datetime.timedelta(minutes=2)
    outcome, store, _ = _run(definition, store, now=later)
    assert outcome.status is RunStatus.WAITING
    outcome, store, _ = _run(definition, store, now=later + datetime.timedelta(minutes=2))
    assert outcome.status is RunStatus.SUCCEEDED
    assert CALLS == {"effect": 1, "flaky": 3}
    assert store.records[("instavel", "")].attempt == 3


def test_interrupted_side_effect_is_not_repeated() -> None:
    CALLS.clear()
    definition = _definition([{"id": "efeito", "type": "test.effect", "params": {"text": "a"}}])
    store = MemoryStore()
    from onyx.ton.automations.interpreter import StepRecord

    store.records[("efeito", "")] = StepRecord("efeito", "", "test.effect", StepStatus.RUNNING, attempt=1)
    outcome, store, _ = _run(definition, store)
    assert outcome.status is RunStatus.FAILED
    assert "Interrompido" in (store.records[("efeito", "")].error or "")
    assert CALLS == {}


def test_run_after_try_catch_scope() -> None:
    definition = _definition(
        [
            {"id": "tentar", "type": "control.scope", "steps": [
                {"id": "quebra", "type": "test.boom"},
                {"id": "pulado", "type": "data.compose", "params": {"value": "x"}},
            ]},
            {"id": "tratar", "type": "data.compose", "run_after": ["failed", "timed_out"],
             "params": {"value": "erro: {{ steps.quebra.error }}"}},
            {"id": "depois", "type": "data.compose", "params": {"value": "ok"}},
        ]
    )
    outcome, store, interpreter = _run(definition)
    assert outcome.status is RunStatus.SUCCEEDED
    assert store.records[("pulado", "")].status is StepStatus.SKIPPED
    assert store.records[("tentar", "")].status is StepStatus.FAILED
    assert interpreter.steps["tratar"]["outputs"]["value"] == "erro: falhou de propósito"


def test_unhandled_failure_fails_the_run() -> None:
    definition = _definition([{"id": "quebra", "type": "test.boom"}, {"id": "x", "type": "data.compose", "params": {"value": "1"}}])
    outcome, store, _ = _run(definition)
    assert outcome.status is RunStatus.FAILED
    assert "falhou de propósito" in (outcome.error or "")
    assert store.records[("x", "")].status is StepStatus.SKIPPED


def test_wait_and_approval_suspend_then_resume() -> None:
    definition = _definition(
        [
            {"id": "espera", "type": "control.wait", "params": {"mode": "duration", "hours": 2}},
            {"id": "aprova", "type": "approval.request", "params": {"approvers": ["chefe@exemplo.com.br"], "title": "Pode?"}},
            {"id": "decide", "type": "control.switch", "params": {"on": "{{ steps.aprova.outputs.outcome }}"},
             "cases": [{"id": "sim", "value": "Aprovar", "steps": [{"id": "segue", "type": "data.compose", "params": {"value": "foi"}}]}],
             "default": [{"id": "para", "type": "control.terminate", "params": {"status": "cancelled", "message": "recusado"}}]},
        ]
    )
    outcome, store, _ = _run(definition)
    assert outcome.status is RunStatus.WAITING and outcome.waiting_on == "wait"
    outcome, store, _ = _run(definition, store, now=NOW + datetime.timedelta(hours=3))
    assert outcome.status is RunStatus.WAITING and outcome.waiting_on == "approval"
    approval_id = next(iter(store.approvals))
    outcome, store, _ = _run(definition, store, now=NOW + datetime.timedelta(hours=4))
    assert outcome.status is RunStatus.WAITING
    store.approvals[approval_id]["result"] = {"outcome": "Recusar", "approved": False, "responder": "chefe@exemplo.com.br"}
    outcome, store, _ = _run(definition, store, now=NOW + datetime.timedelta(hours=5))
    assert outcome.status is RunStatus.CANCELLED
    assert outcome.message == "recusado"


def test_test_mode_skips_waits_and_auto_approves() -> None:
    definition = _definition(
        [
            {"id": "espera", "type": "control.wait", "params": {"mode": "duration", "days": 1}},
            {"id": "aprova", "type": "approval.request", "params": {"approvers": [], "title": "Pode?"}},
        ]
    )
    outcome, store, _ = _run(definition, mode="TEST")
    assert outcome.status is RunStatus.SUCCEEDED
    assert store.records[("aprova", "")].outputs["approved"] is True


def test_parallel_branches_continue_when_one_waits() -> None:
    definition = _definition(
        [
            {"id": "ramos", "type": "control.parallel", "branches": [
                {"id": "a", "steps": [{"id": "espera", "type": "control.wait", "params": {"mode": "duration", "minutes": 30}}]},
                {"id": "b", "steps": [{"id": "faz", "type": "data.compose", "params": {"value": "b"}}]},
            ]},
        ]
    )
    outcome, store, _ = _run(definition)
    assert outcome.status is RunStatus.WAITING
    assert store.records[("faz", "")].status is StepStatus.SUCCEEDED
    outcome, store, _ = _run(definition, store, now=NOW + datetime.timedelta(hours=1))
    assert outcome.status is RunStatus.SUCCEEDED


def test_until_loop_stops_on_condition() -> None:
    definition = _definition(
        [
            {"id": "repete", "type": "control.until", "params": {
                "condition": {"op": "and", "rules": [{"left": "{{ vars.n }}", "operator": "gte", "right": "3"}]},
                "max_iterations": 10,
            }, "steps": [{"id": "soma", "type": "variable.increment", "params": {"name": "n"}}]},
        ],
        variables=[{"name": "n", "type": "number", "value": 0}],
    )
    outcome, store, interpreter = _run(definition)
    assert outcome.status is RunStatus.SUCCEEDED
    assert interpreter.vars["n"] == 3
    assert store.records[("repete", "")].outputs["result"] == {"iterations": 3, "condition_met": True}


def test_data_input_table_group_and_table() -> None:
    definition = _definition(
        [
            {"id": "dados", "type": "data.input", "params": {"source": "table", "content": "unidade;valor\nA;10\nB;5,5\nA;1"}},
            {"id": "grupos", "type": "data.group", "params": {"items": "{{ steps.dados.outputs.rows }}", "by": "unidade", "sum_field": "valor"}},
            {"id": "tabela", "type": "data.table", "params": {"items": "{{ steps.grupos.outputs.groups }}",
             "columns": [{"header": "Unidade", "value": "{{ item.key }}"}, {"header": "Total", "value": "{{ item.total_formatado }}"}]}},
        ]
    )
    outcome, _store, interpreter = _run(definition)
    assert outcome.status is RunStatus.SUCCEEDED
    groups = interpreter.steps["grupos"]["outputs"]["groups"]
    assert [(g["key"], g["total"]) for g in groups] == [("A", 11), ("B", 5.5)]
    assert "R$ 5,50" in interpreter.steps["tabela"]["outputs"]["html"]


def test_expression_error_fails_step_without_retry() -> None:
    definition = _definition([{"id": "x", "type": "data.compose", "params": {"value": "{{ length( }}"}}])
    outcome, store, _ = _run(definition)
    assert outcome.status is RunStatus.FAILED
    assert store.records[("x", "")].attempt == 1


# -- checker ---------------------------------------------------------------------


def test_checker_finds_bad_references() -> None:
    definition = _definition(
        [
            {"id": "antes", "type": "data.compose", "params": {"value": "{{ steps.depois.outputs.value }}"}},
            {"id": "cada", "type": "control.foreach", "params": {"items": "{{ trigger.outputs.items }}"}, "steps": [
                {"id": "dentro", "type": "data.compose", "params": {"value": "{{ item.unidade }}"}},
            ]},
            {"id": "depois", "type": "data.compose", "params": {"value": "{{ steps.dentro.outputs.value }} {{ vars.nao }} {{ item.x }}"}},
            {"id": "mail", "type": "email.send", "params": {"to": ["não-é-email"], "subject": "", "body": "<p>oi</p>"}},
        ]
    )
    messages = [(issue.node_id, issue.message) for issue in validate(definition) if issue.severity == "error"]
    joined = " | ".join(f"{n}: {m}" for n, m in messages)
    assert "antes: O passo 'depois' não roda antes" in joined
    assert "depois: O passo 'dentro' não roda antes" in joined
    assert "A variável 'nao' não foi declarada" in joined
    assert "{{ item }} só existe dentro" in joined
    assert "E-mail inválido" in joined
    assert "Preencha 'Assunto'" in joined
    assert ("dentro", "{{ item }} só existe dentro de 'Para cada' (ou nas regras de 'Filtrar lista')") not in messages


def test_kind_gates_activation() -> None:
    definition = _definition([{"id": "x", "type": "data.compose", "params": {"value": "1"}}])
    assert "A automação de e-mail não envia nenhum e-mail" in activation_problems(definition, AutomationKind.EMAIL)
    assert activation_problems(definition, AutomationKind.GENERAL) == []


def test_structure_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError):
        _definition([{"id": "a", "type": "data.compose"}, {"id": "a", "type": "data.compose"}])


def test_layout_keeps_only_known_nodes_and_clamps() -> None:
    definition = AutomationDefinition.model_validate(
        {
            "schema": 3,
            "trigger": {"type": "trigger.manual", "params": {}},
            "steps": [{"id": "a", "type": "data.compose"}],
            "layout": {"a": {"x": 40, "y": "12.5"}, "trigger": {"x": 99999999}, "gone": {"x": 1, "y": 1}, "bad": 3},
        }
    )
    assert definition.layout == {"a": {"x": 40.0, "y": 12.5}, "trigger": {"x": 20000.0, "y": 0.0}}
    assert definition.dump()["layout"]["a"] == {"x": 40.0, "y": 12.5}


# -- schedule ------------------------------------------------------------------------


def test_schedule_slots_in_brasilia() -> None:
    params = {"frequency": "week", "weekdays": [0], "time": "08:00"}
    monday_10_local = datetime.datetime(2026, 10, 5, 13, 0, tzinfo=datetime.UTC)
    slot = latest_slot(params, monday_10_local)
    assert slot is not None and slot.isoformat().startswith("2026-10-05T08:00:00-03:00")
    upcoming = next_slot(params, monday_10_local)
    assert upcoming is not None and upcoming.isoformat().startswith("2026-10-12T08:00")
    every15 = {"frequency": "minute", "interval": 15}
    assert latest_slot(every15, datetime.datetime(2026, 10, 5, 13, 7, tzinfo=datetime.UTC)).minute == 0  # type: ignore[union-attr]


# -- e-mail flows conversion and composer ------------------------------------------


def test_legacy_split_condition_and_units_convert_and_run() -> None:
    from onyx.ton.automations import legacy

    v2 = {
        "schema": 2,
        "trigger": {"kind": "NG_IMPORT_COMPLETED"},
        "steps": [
            {
                "type": "condition",
                "conditions": [{"field": "valor", "operator": "GTE", "value": 1000}],
                "then": [{"type": "send_email", "to": ["diretoria@exemplo.com.br"], "subject": "Altas {total}", "body": "<p>x</p>"}],
                "else": [
                    {
                        "type": "for_each_unit",
                        "recipients": [{"unit": "Toledo-PR", "emails": ["toledo@exemplo.com.br"]}],
                        "default_emails": ["geral@exemplo.com.br"],
                        "steps": [{"type": "send_email", "to": ["{email_unidade}"], "subject": "Unidade {unidade}", "body": '<p><span data-variable="unidade"></span></p>'}],
                    }
                ],
            }
        ],
    }
    converted = legacy.convert(v2)
    assert [i.message for i in validate(converted) if i.severity == "error"] == []
    sent: list[dict[str, Any]] = []
    spec = REGISTRY["email.send"]
    original = spec.executor

    def capture(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
        sent.append({"to": params["to"], "subject": params["subject"], "items": len(params["items"])})
        return {"delivery": "SENT"}

    object.__setattr__(spec, "executor", capture)
    try:
        outcome, _store, _ = _run(converted, trigger={"items": ITEMS, "count": 3})
    finally:
        object.__setattr__(spec, "executor", original)
    assert outcome.status is RunStatus.SUCCEEDED
    assert sent[0] == {"to": ["diretoria@exemplo.com.br"], "subject": "Altas {total}", "items": 1}
    assert {(tuple(s["to"]) if isinstance(s["to"], list) else (s["to"],), s["subject"], s["items"]) for s in sent[1:]} == {
        (("geral@exemplo.com.br",), "Unidade Cascavel-PR", 1),
        (("toledo@exemplo.com.br",), "Unidade Toledo-PR", 1),
    }


def test_composer_resolves_dynamic_chips_and_sourced_blocks() -> None:
    from onyx.ton.automations.nodes.common import as_flow_item
    from onyx.ton.email_flows.composer import RenderContext, compose

    scope = {"steps": {"resumo": {"outputs": {"text": "Tudo <certo>"}}}}
    items = [as_flow_item({"unidade": "A", "valor": 10}), as_flow_item({"unidade": "B", "valor": 5})]
    ctx = RenderContext(
        variables={},
        items=[],
        fields={},
        ton_url="https://ton.exemplo",
        resolve=lambda expression: str(evaluate(expression, scope)),
        items_for=lambda source: (items, {"itens": 2, "valor_total": 15.0}) if source else ([], {}),
    )
    email = compose(
        subject="Assunto",
        body='<p><span data-expr="steps.resumo.outputs.text"></span></p><div data-block="summary" data-source="steps.x.outputs.items"></div><div data-block="items_table" data-source="steps.x.outputs.items"></div>',
        ctx=ctx,
        layout=None,
    )
    assert "Tudo &lt;certo&gt;" in email.html
    assert "R$ 15,00" in email.html
    assert "<td" in email.html and ">B<" in email.html
