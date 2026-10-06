import datetime

import pytest
from pydantic import ValidationError

from onyx.ton.email_flows.catalog import ItemState
from onyx.ton.email_flows.composer import (
    EmailLayout,
    RenderContext,
    compose,
    sanitize,
)
from onyx.ton.email_flows.engine import Engine, Frame, SendRequest
from onyx.ton.email_flows.logic import BRASILIA, FlowItem
from onyx.ton.email_flows.steps import (
    FlowDefinitionV2,
    activation_problems_v2,
)

NOW = datetime.datetime(2026, 10, 5, 11, 30, tzinfo=datetime.UTC)  # Mon 08:30 BRT
ASSET = "0f8fad5bd9cb469fa16570867728950e"


def _item(key: str, unit: str, value: float, rule: str = "NGF-DUP-DOC") -> FlowItem:
    return FlowItem(
        key,
        {
            "regra": rule,
            "unidade": unit,
            "valor": value,
            "semanas_em_aberto": 1,
            "competencia": 2,
            "situacao": ItemState.OPEN.value,
        },
        {"regra_nome": "Duplicidade", "evidencia": "Fev, linha 30", "conta": "1.1", "correcao": "Excluir", "situacao": "aberta"},
    )


def _email(step_id: str, to: str = "fin@x.com", **extra: object) -> dict[str, object]:
    return {
        "type": "send_email",
        "id": step_id,
        "to": [to],
        "subject": "Assunto {total}",
        "body": "<p>Olá</p>",
        **extra,
    }


def _definition(steps: list[dict[str, object]], **extra: object) -> FlowDefinitionV2:
    return FlowDefinitionV2.model_validate(
        {"trigger": {"kind": "NG_IMPORT_COMPLETED"}, "steps": steps, **extra}
    )


def _run(definition: FlowDefinitionV2, items: list[FlowItem]) -> tuple[list[SendRequest], object]:
    sent: list[SendRequest] = []
    outcome = Engine(definition, base_fields={}, send=sent.append, now=NOW).run(items)
    return sent, outcome


ITEMS = [
    _item("a", "Toledo-PR", 706726.12),
    _item("b", "Toledo-PR", 50),
    _item("c", "Cascavel", 200000),
    _item("d", "Cascavel", 10, rule="NGF-UNIT-MISSING"),
]


def test_v1_definition_is_upgraded_on_read() -> None:
    definition = FlowDefinitionV2.model_validate(
        {
            "trigger": {"kind": "SCHEDULE", "frequency": "WEEKLY", "weekday": 0, "time": "08:00"},
            "conditions": [{"field": "itens", "operator": "GT", "value": 0}],
            "on_yes": {"kind": "EMAIL", "to": ["a@x.com"], "subject": "S {semana}", "template": "INCONSISTENCY_REPORT"},
            "on_no": {"kind": "NONE"},
        }
    )
    step = definition.steps[0]
    assert step.type == "condition"
    assert step.then[0].to == ["a@x.com"]
    assert 'data-block="inconsistency_table"' in step.then[0].body


def test_condition_splits_items_between_branches() -> None:
    definition = _definition(
        [
            {
                "type": "condition",
                "id": "c1",
                "conditions": [{"field": "valor", "operator": "GT", "value": 100000}],
                "then": [_email("big", "diretoria@x.com")],
                "else": [_email("small", "financeiro@x.com")],
            }
        ]
    )
    sent, _ = _run(definition, ITEMS)
    by_step = {request.step.id: sorted(i.key for i in request.items) for request in sent}
    assert by_step == {"big": ["a", "c"], "small": ["b", "d"]}


def test_summary_condition_gates_whole_branch() -> None:
    definition = _definition(
        [
            {
                "type": "condition",
                "conditions": [{"field": "itens", "operator": "GT", "value": 10}],
                "then": [_email("yes")],
                "else": [_email("no")],
            }
        ]
    )
    sent, _ = _run(definition, ITEMS)
    assert [request.step.id for request in sent] == ["no"]
    assert len(sent[0].items) == 4


def test_for_each_unit_sends_one_email_per_unit_with_its_recipients() -> None:
    definition = _definition(
        [
            {
                "type": "for_each_unit",
                "recipients": [{"unit": "toledo-pr", "emails": ["toledo@x.com"]}],
                "default_emails": ["controladoria@x.com"],
                "steps": [_email("unit", "{email_unidade}", subject="Unidade {unidade}")],
            }
        ]
    )
    sent, _ = _run(definition, ITEMS)
    assert [(r.unit, r.unit_emails, len(r.items)) for r in sent] == [
        ("Cascavel", ["controladoria@x.com"], 2),
        ("Toledo-PR", ["toledo@x.com"], 2),
    ]


def test_wait_suspends_and_resume_keeps_only_items_still_open() -> None:
    definition = _definition(
        [
            _email("first"),
            {"type": "wait", "id": "w", "mode": "until", "weekday": 4, "time": "17:00"},
            _email("reminder"),
        ]
    )
    sent, outcome = _run(definition, ITEMS)
    assert [r.step.id for r in sent] == ["first"]
    suspension = outcome.suspension
    assert suspension.reason == "wait"
    assert suspension.resume_at.astimezone(BRASILIA).isoformat() == "2026-10-09T17:00:00-03:00"
    frames = [Frame.load(frame.dump()) for frame in suspension.frames]
    resumed: list[SendRequest] = []
    outcome = Engine(definition, base_fields={}, send=resumed.append, now=NOW).resume(frames, ITEMS[:2])
    assert outcome.suspension is None
    assert [(r.step.id, [i.key for i in r.items]) for r in resumed] == [("reminder", ["a", "b"])]


def test_approval_inside_sim_branch_resumes_sim_then_nao_then_rest() -> None:
    definition = _definition(
        [
            {
                "type": "condition",
                "conditions": [{"field": "valor", "operator": "GT", "value": 100000}],
                "then": [
                    {"type": "approval", "approvers": ["luyla@x.com"]},
                    _email("after-approval"),
                ],
                "else": [_email("small")],
            },
            _email("closing"),
        ]
    )
    sent, outcome = _run(definition, ITEMS)
    assert sent == []
    assert outcome.suspension.reason == "approval"
    resumed: list[SendRequest] = []
    Engine(definition, base_fields={}, send=resumed.append, now=NOW).resume(outcome.suspension.frames, ITEMS)
    assert [(r.step.id, len(r.items)) for r in resumed] == [
        ("after-approval", 2),
        ("small", 2),
        ("closing", 4),
    ]


def test_tree_rules() -> None:
    with pytest.raises(ValidationError, match="só pode ser usado dentro"):
        _definition([_email("x", "{email_unidade}")])
    with pytest.raises(ValidationError, match="fora de 'Para cada unidade'"):
        _definition([{"type": "for_each_unit", "steps": [{"type": "wait", "days": 1}]}])
    with pytest.raises(ValidationError, match="Variável desconhecida"):
        _definition([_email("x", subject="Oi {nome}")])
    ok = _definition([_email("x", subject="Prazo {prazo}")], variables=[{"name": "prazo", "value": "sexta"}])
    assert ok.variables[0].name == "prazo"


def test_activation_problems_for_drafts() -> None:
    draft = _definition([{"type": "send_email", "subject": "", "body": ""}])
    problems = activation_problems_v2(draft)
    assert any("destinatário" in p for p in problems)
    assert any("assunto" in p for p in problems)


def test_sanitize_keeps_editor_markup_and_drops_the_rest() -> None:
    clean = sanitize(
        '<p style="text-align: center; position: fixed">Oi <strong>x</strong></p>'
        '<script>alert(1)</script><a href="javascript:x">l</a>'
        f'<img data-asset-id="{ASSET}" onerror="x"><img src="http://evil">'
        '<span data-variable="unidade">{unidade}</span><div data-block="summary"></div>'
        '<div data-block="unknown">t</div><iframe src="x"></iframe>'
    )
    assert "script" not in clean and "javascript" not in clean and "onerror" not in clean
    assert "position" not in clean and 'style="text-align: center"' in clean
    assert "evil" not in clean and "iframe" not in clean
    assert f'data-asset-id="{ASSET}"' in clean
    assert 'data-variable="unidade"' in clean and 'data-block="summary"' in clean


def test_compose_fills_variables_blocks_and_inline_images() -> None:
    body = (
        '<h2>Olá</h2><p>Unidade: <span data-variable="unidade">x</span> '
        '<span data-variable="prazo">x</span></p>'
        '<div data-block="inconsistency_table"></div><div data-block="summary"></div>'
        f'<img data-asset-id="{ASSET}" width="120"><p>&lt;b&gt;</p>'
    )
    ctx = RenderContext(
        variables={"unidade": "Toledo <PR>", "prazo": "sexta", "total": "2"},
        items=ITEMS[:2],
        fields={"itens": 2, "valor_total": 706776.12},
        ton_url="https://ton.example/ton/pendencias",
        note="Última extração conferida.",
    )
    email = compose(subject="Pendências {unidade} ({total})", body=body, ctx=ctx, layout=EmailLayout(logo_asset_id=ASSET))
    assert email.subject == "Pendências Toledo <PR> (2)"
    assert "Toledo &lt;PR&gt;" in email.html and "sexta" in email.html
    assert "Toledo-PR · 2" in email.html and "R$ 706.726,12" in email.html
    assert f"cid:asset-{ASSET}" in email.html
    assert email.asset_ids == [ASSET]
    assert "&lt;b&gt;" in email.html
    assert "Última extração conferida." in email.text
