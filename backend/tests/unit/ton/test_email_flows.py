import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from onyx.ton.email_flows.catalog import ItemState, Operator, TemplateKey, TriggerKind
from onyx.ton.email_flows.logic import (
    BRASILIA,
    FlowEvent,
    FlowItem,
    batch_recipients,
    describe_conditions,
    describe_trigger,
    due_window,
    evaluate,
    format_money,
    next_slot,
    render_subject,
    state_of,
)
from onyx.ton.email_flows.models import (
    ConditionClause,
    DeliveryStatus,
    EmailAction,
    FlowBranch,
    FlowDefinition,
    FlowTrigger,
    activation_problems,
)
from onyx.ton.email_flows.drafter import parse as parse_draft
from onyx.ton.email_flows.events import build_event
from onyx.ton.email_flows.service import _deliver, default_weekly_definition
from onyx.ton.email_flows.steps import activation_problems_v2
from onyx.ton.email_flows.transport import (
    EmailTransport,
    OutgoingEmail,
    SendResult,
    TransportError,
)

NOW = datetime.datetime(2026, 10, 5, 11, 30, tzinfo=datetime.UTC)  # Mon 08:30 BRT


def _item(key: str, unit: str, value: float, weeks: int = 1, rule: str = "NGF-DUP-DOC") -> FlowItem:
    return FlowItem(
        key,
        {
            "regra": rule,
            "unidade": unit,
            "valor": value,
            "semanas_em_aberto": weeks,
            "competencia": 2,
            "situacao": ItemState.OPEN.value,
        },
        {
            "regra_nome": "Lançamento duplicado",
            "evidencia": "Fev ok, linha 30 · doc. 2600000000392",
            "conta": "3.1.01 Serviços",
            "correcao": "Excluir no NG o lançamento duplicado",
            "situacao": "aberta",
        },
    )


def _event(items: list[FlowItem], kind: TriggerKind = TriggerKind.SCHEDULE) -> FlowEvent:
    return FlowEvent(kind, "schedule:2026-W41", NOW, {}, items, "Última extração conferida.")


def _email(**kwargs: object) -> EmailAction:
    base: dict[str, object] = {
        "kind": "EMAIL",
        "to": ["fin@valenorte.com.br"],
        "subject": "Inconsistências {semana}",
        "template": TemplateKey.INCONSISTENCY_REPORT,
    }
    base.update(kwargs)
    return EmailAction.model_validate(base)


# --- definition validation -------------------------------------------------


def _weekly_v1() -> FlowDefinition:
    return FlowDefinition(
        trigger=FlowTrigger(kind=TriggerKind.SCHEDULE, frequency="WEEKLY", weekday=0, time="08:00"),
        conditions=[ConditionClause(field="itens", operator=Operator.GT, value=0)],
        on_yes=_email(to=[]),
    )


def test_default_weekly_flow_is_v2_and_needs_recipients() -> None:
    definition = default_weekly_definition()
    assert describe_trigger(definition.trigger) == "Toda segunda às 08:00"
    assert definition.steps[0].type == "condition"
    problems = activation_problems_v2(definition)
    assert problems == ["Inconsistências do NG – semana {semana} ({total}): informe ao menos um destinatário em Para"]



def test_condition_field_must_exist_on_trigger() -> None:
    with pytest.raises(ValidationError, match="não existe"):
        FlowDefinition(
            trigger=FlowTrigger(kind=TriggerKind.DRE_RECALCULATED),
            conditions=[ConditionClause(field="unidade", operator=Operator.EQ, value="X")],
            on_yes=EmailAction(),
        )


def test_operator_must_fit_field_type() -> None:
    with pytest.raises(ValidationError, match="Operador inválido"):
        FlowDefinition(
            trigger=FlowTrigger(kind=TriggerKind.NG_IMPORT_COMPLETED),
            conditions=[ConditionClause(field="valor", operator=Operator.IN, value="1")],
            on_yes=EmailAction(),
        )


def test_template_must_fit_trigger() -> None:
    with pytest.raises(ValidationError, match="Modelo não disponível"):
        FlowDefinition(
            trigger=FlowTrigger(kind=TriggerKind.DRE_RECALCULATED),
            on_yes=_email(template=TemplateKey.INCONSISTENCY_REPORT),
        )


def test_unknown_subject_marker_rejected() -> None:
    with pytest.raises(ValidationError, match="Marcador desconhecido"):
        _email(subject="Olá {nome}")


def test_invalid_email_rejected_and_duplicates_removed() -> None:
    with pytest.raises(ValidationError, match="E-mail inválido"):
        _email(to=["sem-arroba"])
    action = _email(to=["A@x.com", "a@x.com"], cc=["b@x.com"])
    assert action.to == ["a@x.com"]


def test_schedule_needs_weekday_and_time() -> None:
    with pytest.raises(ValidationError, match="dia da semana"):
        FlowTrigger(kind=TriggerKind.SCHEDULE, frequency="WEEKLY", time="08:00")
    with pytest.raises(ValidationError, match="Horário inválido"):
        FlowTrigger(kind=TriggerKind.SCHEDULE, frequency="DAILY", time="8h")


def test_occurrence_changed_needs_a_change() -> None:
    with pytest.raises(ValidationError, match="ao menos uma mudança"):
        FlowTrigger(kind=TriggerKind.NG_OCCURRENCE_CHANGED)


# --- evaluation ------------------------------------------------------------


def test_item_conditions_filter_and_summary_conditions_decide() -> None:
    definition = FlowDefinition(
        trigger=FlowTrigger(kind=TriggerKind.NG_IMPORT_COMPLETED),
        conditions=[
            ConditionClause(field="unidade", operator=Operator.EQ, value="Toledo-PR"),
            ConditionClause(field="valor", operator=Operator.GT, value="1000"),
        ],
        on_yes=_email(),
    )
    result = evaluate(
        definition,
        _event(
            [_item("1", "Toledo-PR", 706726.12), _item("2", "Toledo-PR", 10), _item("3", "Cascavel", 5000)],
            TriggerKind.NG_IMPORT_COMPLETED,
        ),
    )
    assert result.branch is FlowBranch.YES
    assert [item.key for item in result.items] == ["1"]
    assert result.fields["itens"] == 1


def test_no_branch_when_nothing_open() -> None:
    result = evaluate(_weekly_v1(), _event([]))
    assert result.branch is FlowBranch.NO
    assert "quantidade de itens" in result.reason


def test_in_operator_is_case_insensitive() -> None:
    definition = FlowDefinition(
        trigger=FlowTrigger(kind=TriggerKind.SCHEDULE, frequency="DAILY", time="07:00"),
        conditions=[ConditionClause(field="regra", operator=Operator.IN, value="ngf-dup-doc, NGF-UNIT-MISSING")],
        on_yes=_email(),
    )
    result = evaluate(definition, _event([_item("1", "A", 1), _item("2", "A", 1, rule="NGF-SRC-ROW-REJECTED")]))
    assert [item.key for item in result.items] == ["1"]


# --- recipients ------------------------------------------------------------


def test_one_message_for_everyone_within_limit() -> None:
    action = _email(to=["a@x.com", "b@x.com", "c@x.com"], cc=["luyla@x.com"])
    batches = batch_recipients(action, 50)
    assert len(batches) == 1
    assert batches[0].to == ["a@x.com", "b@x.com", "c@x.com"]
    assert batches[0].cc == ["luyla@x.com"]


def test_batches_above_provider_limit_keep_to_and_split_copies() -> None:
    action = _email(to=["a@x.com"], cc=[f"c{i}@x.com" for i in range(40)], bcc=[f"b{i}@x.com" for i in range(19)])
    batches = batch_recipients(action, 50)
    assert len(batches) == 2
    assert all(batch.to == ["a@x.com"] for batch in batches)
    copied = [a for b in batches for a in b.cc + b.bcc]
    assert len(copied) == 59 and len(set(copied)) == 59
    assert all(len(b.to) + len(b.cc) + len(b.bcc) <= 50 for b in batches)


def test_batches_when_to_alone_overflows() -> None:
    action = _email(to=[f"t{i}@x.com" for i in range(60)], cc=["luyla@x.com"])
    batches = batch_recipients(action, 50)
    assert sum(len(b.to) for b in batches) == 60
    assert sum(len(b.cc) for b in batches) == 1
    assert all(len(b.to) + len(b.cc) + len(b.bcc) <= 50 for b in batches)


# --- schedule --------------------------------------------------------------


def test_weekly_window_due_once_after_slot() -> None:
    trigger = default_weekly_definition().trigger
    since = NOW - datetime.timedelta(days=30)
    assert due_window(trigger, NOW, since) == "schedule:2026-W41"
    before = datetime.datetime(2026, 10, 5, 7, 59, tzinfo=BRASILIA)
    assert due_window(trigger, before, since) is None  # last Monday is > 12h old


def test_window_before_activation_is_not_sent() -> None:
    trigger = default_weekly_definition().trigger
    assert due_window(trigger, NOW, NOW - datetime.timedelta(minutes=5)) is None


def test_next_slot_is_next_monday_brasilia() -> None:
    trigger = default_weekly_definition().trigger
    slot = next_slot(trigger, NOW)
    assert slot.astimezone(BRASILIA).isoformat() == "2026-10-12T08:00:00-03:00"


# --- state -----------------------------------------------------------------


def test_states_after_import() -> None:
    t0 = datetime.datetime(2026, 9, 1, tzinfo=datetime.UTC)
    t1 = t0 + datetime.timedelta(days=7)
    t2 = t1 + datetime.timedelta(days=7)
    assert state_of(True, t0, t1, "PASSED", t2, False, t2) is ItemState.CORRECTED
    assert state_of(True, t0, t1, "INCONCLUSIVE", t2, False, t2) is ItemState.CHECK_MANUALLY
    assert state_of(True, t0, t2, "PASSED", t1, True, t2) is ItemState.REAPPEARED
    assert state_of(True, t2, t2, None, None, False, t2) is ItemState.NEW
    assert state_of(True, t0, t2, None, None, False, t2) is ItemState.OPEN
    assert state_of(False, t0, t2, None, None, False, t2) is None


# --- rendering -------------------------------------------------------------




def test_money_and_subject_helpers() -> None:
    assert format_money(Decimal("-1234567.5")) == "-R$ 1.234.567,50"
    assert render_subject("{data} {total} {valor_total}", {"itens": 2, "valor_total": 10.0}, NOW) == "05/10/2026 2 R$ 10,00"


# --- delivery --------------------------------------------------------------


class _Flaky(EmailTransport):
    name = "fake"
    max_recipients = 50
    sender = "ton@x.com"

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def send(self, message: OutgoingEmail) -> SendResult:
        self.calls += 1
        if self.calls <= self.failures:
            raise TransportError("down")
        return SendResult("msg-1")


MESSAGE = OutgoingEmail(["a@x.com"], [], [], "s", "<p>h</p>", "t")


def test_delivery_without_provider_is_not_configured() -> None:
    status, message_id, error, attempts = _deliver(None, MESSAGE, lambda _: None)
    assert status is DeliveryStatus.NOT_CONFIGURED and attempts == 0
    assert error and "não configurado" in error


def test_delivery_retries_then_sends() -> None:
    transport = _Flaky(failures=2)
    status, message_id, _, attempts = _deliver(transport, MESSAGE, lambda _: None)
    assert (status, message_id, attempts) == (DeliveryStatus.SENT, "msg-1", 3)


def test_delivery_fails_after_three_attempts() -> None:
    status, _, error, attempts = _deliver(_Flaky(failures=5), MESSAGE, lambda _: None)
    assert (status, attempts, error) == (DeliveryStatus.FAILED, 3, "down")


# --- suggestions -----------------------------------------------------------




def test_dre_event_groups_months_and_units_in_one_note() -> None:
    event = build_event(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        FlowTrigger(kind=TriggerKind.DRE_RECALCULATED),
        event_key="DRE_RECALCULATED:x",
        payload={
            "competencias": ["2026-09-01", "2026-01-01", "2026-05-01"],
            "unidades": ["consolidado", "u1", "u2"],
        },
        now=NOW,
    )
    assert event.fields == {"competencia": 9}
    assert event.note == "Meses recalculados: 01/2026 a 09/2026 (consolidado + 2 unidades)."


def test_chat_draft_is_validated_and_forgives_near_misses() -> None:
    text = """Aqui está: {"name": "Duplicidades grandes", "summary": "Avisa a diretoria",
      "missing": "e-mail da diretoria",
      "definition": {"trigger": {"kind": "NG_OCCURRENCE_CHANGED", "params": {"changes": "NEW, REAPPEARED"}},
        "steps": {"type": "condition",
          "conditions": {"field": "valor", "operator": "GT", "value": 100000},
          "then": [{"type": "send_email", "to": "", "subject": "Duplicidades ({total})",
                    "body": "<p>Olá</p><div data-block='inconsistency_table'></div>"}]}}}"""
    name, summary, missing, definition = parse_draft(text)
    assert name == "Duplicidades grandes"
    assert missing == ["e-mail da diretoria"]
    assert definition.trigger.changes == [ItemState.NEW, ItemState.REAPPEARED]
    email = definition.steps[0].then[0]
    assert email.to == [] and "inconsistency_table" in email.body


def test_chat_draft_rejects_unknown_fields() -> None:
    from onyx.ton.email_flows.drafter import DraftError

    text = """{"name": "X", "definition": {"trigger": {"kind": "DRE_RECALCULATED"},
      "steps": [{"type": "condition", "conditions": [{"field": "unidade", "operator": "EQ", "value": "A"}]}]}}"""
    with pytest.raises(DraftError, match="não existe"):
        parse_draft(text)
