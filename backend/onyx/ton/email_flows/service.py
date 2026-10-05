"""Email flows: build the event a trigger hands over, evaluate the condition,
render the e-mail and deliver it. Also the default weekly flow, previews,
test sends and the periodic tick (schedules + event outbox)."""

import datetime
import time
from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import email_flows as repository
from onyx.db.ton.account_classification import classification_table
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import EmailFlow, EmailFlowDelivery, EmailFlowRun, EmailFlowVersion
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.account_classification.models import ClassificationStatus
from onyx.ton.email_flows.catalog import (
    CHANGE_STATES,
    EVENT_KIND_DRE,
    EVENT_KIND_NG_IMPORT,
    ITEM_STATE_LABELS,
    OPERATOR_LABELS,
    OPERATORS_BY_TYPE,
    SUBJECT_MARKERS,
    TEMPLATE_LABELS,
    TRIGGERS,
    ItemState,
    Operator,
    TemplateKey,
    TriggerKind,
)
from onyx.ton.email_flows.logic import (
    BRASILIA,
    FlowEvent,
    FlowItem,
    batch_recipients,
    describe_action,
    describe_conditions,
    describe_trigger,
    due_window,
    evaluate,
    next_slot,
)
from onyx.ton.email_flows.models import (
    CatalogView,
    ConditionClause,
    DeliveryStatus,
    DeliveryView,
    EmailAction,
    FieldView,
    FlowBranch,
    FlowCreate,
    FlowDefinition,
    FlowDetail,
    FlowOrigin,
    FlowRunStatus,
    FlowStatus,
    FlowSummary,
    FlowTable,
    FlowTrigger,
    FlowUpdate,
    PreviewView,
    RunView,
    SuggestionRunResult,
    TriggerView,
    activation_problems,
)
from onyx.ton.email_flows.suggester import suggest
from onyx.ton.email_flows.templates import render
from onyx.ton.email_flows.transport import (
    EmailTransport,
    OutgoingEmail,
    TransportError,
    get_transport,
    provider_name,
    sender_address,
)
from onyx.utils.audit import AuditAction, AuditOutcome
from onyx.utils.logger import setup_logger

logger = setup_logger()

DEFAULT_SEED_KEY = "weekly-inconsistencies-v1"
SEND_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (2, 5)
# Which flow triggers one outbox event feeds.
TRIGGERS_BY_EVENT: dict[str, tuple[TriggerKind, ...]] = {
    EVENT_KIND_NG_IMPORT: (
        TriggerKind.NG_IMPORT_COMPLETED,
        TriggerKind.NG_OCCURRENCE_CHANGED,
        TriggerKind.ACCOUNT_UNCLASSIFIED,
    ),
    EVENT_KIND_DRE: (TriggerKind.DRE_RECALCULATED,),
}


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


# ---------------------------------------------------------------------------
# Default flow
# ---------------------------------------------------------------------------


def default_weekly_definition() -> FlowDefinition:
    return FlowDefinition(
        trigger=FlowTrigger(
            kind=TriggerKind.SCHEDULE, frequency="WEEKLY", weekday=0, time="08:00"
        ),
        conditions=[ConditionClause(field="itens", operator=Operator.GT, value=0)],
        on_yes=EmailAction(
            kind="EMAIL",
            subject="Inconsistências do NG – semana {semana} ({total})",
            template=TemplateKey.INCONSISTENCY_REPORT,
        ),
    )


def ensure_default_flow(session: Session) -> None:
    """Seed "Inconsistências da semana" once, as a TON suggestion waiting for
    the Financeiro addresses. It runs only after someone registers it."""
    if repository.seeded_flow(session, DEFAULT_SEED_KEY) is not None:
        return
    repository.create_flow__no_commit(
        session,
        None,
        name="Inconsistências da semana",
        definition=default_weekly_definition(),
        origin=FlowOrigin.TON_SUGGESTED,
        status=FlowStatus.SUGGESTED,
        now=_now(),
        suggestion_reason=(
            "Pedido da Luyla (03/10): toda segunda, o Financeiro recebe as "
            "inconsistências do NG ainda abertas, por unidade, com o que corrigir. "
            "Faltam os e-mails do Financeiro."
        ),
        seed_key=DEFAULT_SEED_KEY,
    )
    session.commit()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def _review_note(last_review_at: datetime.datetime | None) -> str | None:
    if last_review_at is None:
        return "Nenhuma extração do NG conferida ainda."
    local = last_review_at.astimezone(BRASILIA)
    return f"Última extração do NG conferida em {local:%d/%m/%Y às %H:%M}."


def build_event(
    session: Session,
    reader: User,
    trigger: FlowTrigger,
    *,
    event_key: str,
    payload: dict[str, object],
    now: datetime.datetime,
) -> FlowEvent:
    """What the trigger hands the flow, read with ``reader``'s visibility."""
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
            items = [i for i in items if i.fields.get("mudou") in wanted]
            items = [
                FlowItem(
                    i.key,
                    i.fields,
                    {**i.columns, "situacao": ITEM_STATE_LABELS[ItemState(i.fields["mudou"])]},
                )
                for i in items
            ]
        return FlowEvent(kind, event_key, now, {}, items, _review_note(snapshot.last_review_at))
    if kind is TriggerKind.ACCOUNT_UNCLASSIFIED:
        source_id = payload.get("source_id")
        table = classification_table(
            session, reader, UUID(str(source_id)) if source_id else None
        )
        items = [
            FlowItem(
                row.account_code,
                {
                    "conta": row.account_code,
                    "valor": float(row.total_amount),
                    "lancamentos": row.entries,
                },
                {"descricao": row.description},
            )
            for row in table.rows
            if row.status is not ClassificationStatus.CONFIRMED
        ]
        return FlowEvent(kind, event_key, now, {}, items)
    months = sorted(str(item) for item in payload.get("competencias") or [])  # type: ignore[union-attr]
    units = list(payload.get("unidades") or [])  # type: ignore[call-overload]
    latest = datetime.date.fromisoformat(months[-1]) if months else None
    note = None
    if months:
        first = datetime.date.fromisoformat(months[0])
        span = (
            f"{first:%m/%Y}"
            if first == latest
            else f"{first:%m/%Y} a {latest:%m/%Y}"
        )
        others = len([unit for unit in units if unit != "consolidado"])
        scope = " + ".join(
            part
            for part in (
                "consolidado" if "consolidado" in units else "",
                f"{others} {'unidade' if others == 1 else 'unidades'}" if others else "",
            )
            if part
        )
        note = f"Meses recalculados: {span} ({scope})."
    return FlowEvent(
        kind, event_key, now, {"competencia": latest.month if latest else None}, (), note
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _deliver(
    transport: EmailTransport | None,
    message: OutgoingEmail,
    sleep: Callable[[float], None],
) -> tuple[DeliveryStatus, str | None, str | None, int]:
    if transport is None:
        return (
            DeliveryStatus.NOT_CONFIGURED,
            None,
            "E-mail não configurado no ambiente: o conteúdo ficou guardado no TON.",
            0,
        )
    error = None
    for attempt in range(1, SEND_ATTEMPTS + 1):
        try:
            result = transport.send(message)
            return DeliveryStatus.SENT, result.provider_message_id, None, attempt
        except TransportError as failure:
            error = str(failure)
            logger.warning("TON email flow delivery attempt %s failed: %s", attempt, error)
            if attempt < SEND_ATTEMPTS:
                sleep(RETRY_DELAYS_SECONDS[attempt - 1])
    return DeliveryStatus.FAILED, None, error, SEND_ATTEMPTS


def _action_for(
    definition: FlowDefinition, branch: FlowBranch, prefer_email: bool
) -> tuple[FlowBranch, EmailAction]:
    action = definition.on_yes if branch is FlowBranch.YES else definition.on_no
    if prefer_email and action.kind == "NONE":
        for other, candidate in ((FlowBranch.YES, definition.on_yes), (FlowBranch.NO, definition.on_no)):
            if candidate.kind == "EMAIL":
                return other, candidate
    return branch, action


def execute(
    session: Session,
    *,
    flow: EmailFlow,
    version: EmailFlowVersion,
    reader: User,
    event_key: str,
    payload: dict[str, object],
    now: datetime.datetime,
    test_recipient: str | None = None,
    branch_override: FlowBranch | None = None,
    transport: EmailTransport | None = None,
    use_configured_transport: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> EmailFlowRun | None:
    """Run the flow once for this event. Returns ``None`` when the (flow,
    event) pair already ran. The caller commits."""
    is_test = test_recipient is not None
    run = repository.start_run__no_commit(
        session,
        flow=flow,
        version=version,
        event_key=f"test:{uuid4()}" if is_test else event_key,
        is_test=is_test,
        triggered_by=reader.id if is_test else None,
        now=now,
    )
    if run is None:
        return None
    try:
        definition = FlowDefinition.model_validate(version.definition)
        event = build_event(
            session, reader, definition.trigger, event_key=event_key, payload=payload, now=now
        )
        evaluation = evaluate(definition, event)
        run.item_count = len(evaluation.items)
        run.context = {
            "fields": evaluation.fields,
            "event_key": event_key,
            "evaluated_branch": evaluation.branch.value,
        }
        branch, action = (
            _action_for(definition, branch_override or evaluation.branch, True)
            if is_test
            else _action_for(definition, evaluation.branch, False)
        )
        run.branch = branch.value
        run.reason = evaluation.reason[:500]
        if action.kind == "NONE":
            run.status = FlowRunStatus.SILENT.value
            run.reason = f"{evaluation.reason}. Nada a enviar neste caso."[:500]
            run.finished_at = _now()
            return run
        if is_test:
            assert test_recipient is not None
            action = action.model_copy(update={"to": [test_recipient], "cc": [], "bcc": []})
        assert action.template is not None
        email = render(action.template, action.subject, evaluation.items, evaluation.fields, event, now)
        sender = transport or (get_transport() if use_configured_transport else None)
        batches = batch_recipients(action, sender.max_recipients if sender else 50)
        statuses = []
        for index, batch in enumerate(batches, start=1):
            message = OutgoingEmail(batch.to, batch.cc, batch.bcc, email.subject, email.html, email.text)
            status, message_id, error, attempts = _deliver(sender, message, sleep)
            statuses.append(status)
            repository.add_delivery__no_commit(
                session,
                EmailFlowDelivery(
                    run_id=run.id,
                    status=status.value,
                    provider=sender.name if sender else provider_name(),
                    to_addresses=batch.to,
                    cc_addresses=batch.cc,
                    bcc_addresses=batch.bcc,
                    batch_no=index,
                    batch_count=len(batches),
                    subject=email.subject[:300],
                    html_body=email.html,
                    text_body=email.text,
                    provider_message_id=message_id,
                    attempts=attempts,
                    error=error[:500] if error else None,
                    sent_at=_now() if status is DeliveryStatus.SENT else None,
                ),
            )
        if all(s is DeliveryStatus.SENT for s in statuses):
            run.status = FlowRunStatus.SENT.value
        elif any(s is DeliveryStatus.SENT for s in statuses):
            run.status = FlowRunStatus.PARTIAL.value
        elif all(s is DeliveryStatus.NOT_CONFIGURED for s in statuses):
            run.status = FlowRunStatus.NOT_CONFIGURED.value
            run.reason = "E-mail não configurado: o conteúdo ficou guardado no TON."
        else:
            run.status = FlowRunStatus.FAILED.value
            run.reason = "O envio falhou depois de 3 tentativas."
        emit_ton_audit_event(
            session,
            action=AuditAction.TON_EMAIL_FLOW_SEND,
            outcome=AuditOutcome.SUCCESS
            if run.status == FlowRunStatus.SENT.value
            else AuditOutcome.FAILURE,
            actor_user_id=reader.id if is_test else None,
            resource_kind=TonAuditResourceKind.EMAIL_FLOW,
            resource_id=flow.id,
            extra={
                "run_id": str(run.id),
                "test": is_test,
                "messages": len(batches),
                "recipients": len(action.recipients()),
                "status": run.status,
            },
        )
    except OnyxError as error:
        run.status = FlowRunStatus.FAILED.value
        run.reason = (
            "O responsável pelo fluxo não tem acesso a esses dados. Reative o fluxo com "
            "um usuário que tenha."
            if error.error_code is OnyxErrorCode.INSUFFICIENT_PERMISSIONS
            else f"Falha ao montar o e-mail: {error.detail}"
        )[:500]
    except Exception as error:
        logger.exception("TON email flow run failed flow_id=%s", flow.id)
        run.status = FlowRunStatus.FAILED.value
        run.reason = f"Falha ao executar o fluxo: {type(error).__name__}"
    run.finished_at = _now()
    return run


def _reader(session: Session, flow: EmailFlow) -> User | None:
    owner = repository.get_user(session, flow.owner_id)
    if owner is None or not owner.is_active or not repository.can_read(owner):
        return None
    return owner


def _owner_missing_run(
    session: Session, flow: EmailFlow, version: EmailFlowVersion, event_key: str, now: datetime.datetime
) -> None:
    run = repository.start_run__no_commit(
        session, flow=flow, version=version, event_key=event_key, is_test=False, triggered_by=None, now=now
    )
    if run is None:
        return
    run.status = FlowRunStatus.FAILED.value
    run.reason = "O responsável pelo fluxo não está ativo ou perdeu o acesso. Reative o fluxo."
    run.finished_at = now


def dispatch_schedules(session: Session, now: datetime.datetime | None = None) -> int:
    current = now or _now()
    ran = 0
    for flow, version in repository.active_flows(session, TriggerKind.SCHEDULE.value):
        definition = FlowDefinition.model_validate(version.definition)
        assert flow.active_since is not None
        key = due_window(definition.trigger, current, flow.active_since)
        if key is None:
            continue
        reader = _reader(session, flow)
        if reader is None:
            _owner_missing_run(session, flow, version, key, current)
            session.commit()
            continue
        run = execute(
            session, flow=flow, version=version, reader=reader, event_key=key, payload={}, now=current
        )
        session.commit()
        ran += run is not None
    return ran


def process_events(session: Session, now: datetime.datetime | None = None) -> int:
    current = now or _now()
    events = repository.claim_pending_events(session, current)
    for event in events:
        for trigger_kind in TRIGGERS_BY_EVENT.get(event.kind, ()):
            for flow, version in repository.active_flows(session, trigger_kind.value):
                if flow.active_since is None or flow.active_since > event.created_at:
                    continue
                key = f"{event.kind}:{event.event_key}"
                reader = _reader(session, flow)
                if reader is None:
                    _owner_missing_run(session, flow, version, key, current)
                    continue
                execute(
                    session,
                    flow=flow,
                    version=version,
                    reader=reader,
                    event_key=key,
                    payload=dict(event.payload),
                    now=current,
                )
        event.processed_at = current
    session.commit()
    return len(events)


def tick(session: Session) -> None:
    process_events(session)
    dispatch_schedules(session)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def _delivery_view(delivery: EmailFlowDelivery) -> DeliveryView:
    return DeliveryView(
        id=delivery.id,
        status=DeliveryStatus(delivery.status),
        provider=delivery.provider,
        to=delivery.to_addresses,
        cc=delivery.cc_addresses,
        bcc=delivery.bcc_addresses,
        batch_no=delivery.batch_no,
        batch_count=delivery.batch_count,
        subject=delivery.subject,
        error=delivery.error,
        sent_at=delivery.sent_at,
        created_at=delivery.created_at,
    )


def _run_view(run: EmailFlowRun, version: int, deliveries: list[EmailFlowDelivery]) -> RunView:
    return RunView(
        id=run.id,
        version=version,
        event_key=run.event_key,
        branch=FlowBranch(run.branch) if run.branch else None,
        status=FlowRunStatus(run.status),
        is_test=run.is_test,
        item_count=run.item_count,
        reason=run.reason,
        started_at=run.started_at,
        finished_at=run.finished_at,
        deliveries=[_delivery_view(item) for item in deliveries],
    )


def _summary(
    flow: EmailFlow,
    version: EmailFlowVersion,
    runs: list[tuple[EmailFlowRun, int, list[EmailFlowDelivery]]],
) -> FlowSummary:
    definition = FlowDefinition.model_validate(version.definition)
    last = next((item for item in runs if not item[0].is_test), None)
    next_run = (
        next_slot(definition.trigger, _now())
        if flow.status == FlowStatus.ACTIVE.value
        and definition.trigger.kind is TriggerKind.SCHEDULE
        else None
    )
    return FlowSummary(
        id=flow.id,
        name=flow.name,
        origin=FlowOrigin(flow.origin),
        status=FlowStatus(flow.status),
        version=flow.current_version,
        definition=definition,
        when=describe_trigger(definition.trigger),
        condition=describe_conditions(definition),
        on_yes=describe_action(definition.on_yes),
        on_no=describe_action(definition.on_no),
        suggestion_reason=flow.suggestion_reason,
        last_run=_run_view(*last) if last else None,
        next_run_at=next_run,
        updated_at=flow.updated_at,
    )


def flow_table(session: Session, user: User) -> FlowTable:
    repository.require_read(user)
    ensure_default_flow(session)
    flows = repository.list_flows(session)
    runs = repository.runs_for_flows(session, [flow.id for flow, _ in flows], per_flow=3)
    return FlowTable(
        flows=[_summary(flow, version, runs.get(flow.id, [])) for flow, version in flows],
        can_manage=repository.can_manage(user),
        provider_ready=get_transport() is not None,
    )


def flow_detail(session: Session, user: User, flow_id: UUID) -> FlowDetail:
    repository.require_read(user)
    flow = repository.get_flow(session, flow_id)
    version = repository.current_version(session, flow)
    runs = repository.runs_for_flows(session, [flow.id], per_flow=30).get(flow.id, [])
    emails = repository.user_emails(session, [flow.created_by, flow.approved_by])
    summary = _summary(flow, version, runs)
    return FlowDetail(
        **summary.model_dump(),
        runs=[_run_view(*item) for item in runs],
        created_by=emails.get(flow.created_by) if flow.created_by else None,
        approved_by=emails.get(flow.approved_by) if flow.approved_by else None,
        approved_at=flow.approved_at,
    )


def catalog_view() -> CatalogView:
    return CatalogView(
        triggers=[
            TriggerView(
                kind=spec.kind,
                label=spec.label,
                description=spec.description,
                fields=[
                    FieldView(
                        key=field.key,
                        label=field.label,
                        type=field.type,
                        per_item=field.per_item,
                        operators=list(OPERATORS_BY_TYPE[field.type]),
                        choices=list(field.choices),
                    )
                    for field in spec.fields
                ],
                templates=list(spec.templates),
            )
            for spec in TRIGGERS.values()
        ],
        templates=TEMPLATE_LABELS,
        operators=OPERATOR_LABELS,
        subject_markers=SUBJECT_MARKERS,
        changes=[(state, ITEM_STATE_LABELS[state]) for state in CHANGE_STATES],
        provider=provider_name(),
        provider_ready=get_transport() is not None,
        sender=sender_address(),
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _require_ready(definition: FlowDefinition) -> None:
    problems = activation_problems(definition)
    if problems:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "; ".join(problems))


def create(session: Session, user: User, request: FlowCreate) -> FlowDetail:
    repository.require_manage(user)
    if request.activate:
        _require_ready(request.definition)
    flow = repository.create_flow__no_commit(
        session,
        user,
        name=request.name.strip(),
        definition=request.definition,
        origin=FlowOrigin.USER,
        status=FlowStatus.ACTIVE if request.activate else FlowStatus.PAUSED,
        now=_now(),
    )
    session.commit()
    return flow_detail(session, user, flow.id)


def update(session: Session, user: User, flow_id: UUID, request: FlowUpdate) -> FlowDetail:
    repository.require_manage(user)
    flow = repository.get_flow(session, flow_id)
    if flow.status == FlowStatus.ACTIVE.value:
        _require_ready(request.definition)
    repository.add_version__no_commit(
        session, user, flow, name=request.name.strip(), definition=request.definition, now=_now()
    )
    session.commit()
    return flow_detail(session, user, flow.id)


def change_status(
    session: Session, user: User, flow_id: UUID, status: FlowStatus
) -> FlowDetail:
    repository.require_manage(user)
    flow = repository.get_flow(session, flow_id)
    if status is FlowStatus.ACTIVE:
        _require_ready(
            FlowDefinition.model_validate(repository.current_version(session, flow).definition)
        )
    repository.set_status__no_commit(session, user, flow, status, _now())
    session.commit()
    return flow_detail(session, user, flow.id)


def _definition_for(
    session: Session, flow_id: UUID | None, definition: FlowDefinition | None
) -> tuple[EmailFlow | None, FlowDefinition]:
    flow = repository.get_flow(session, flow_id) if flow_id else None
    if definition is None:
        if flow is None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Informe o fluxo")
        definition = FlowDefinition.model_validate(
            repository.current_version(session, flow).definition
        )
    return flow, definition


def _sample_payload(session: Session, kind: TriggerKind) -> tuple[str, dict[str, object]]:
    review = repository.latest_succeeded_review(session)
    if kind is TriggerKind.SCHEDULE or review is None:
        return "preview", {}
    return f"preview:{review.id}", {
        "review_run_id": str(review.id),
        "source_id": str(review.source_id),
    }


def preview(
    session: Session,
    user: User,
    *,
    flow_id: UUID | None,
    definition: FlowDefinition | None,
    branch: FlowBranch | None,
) -> PreviewView:
    """Render what the flow would send now, without sending or recording.
    Event triggers use the latest NG import as the sample event."""
    repository.require_read(user)
    _, definition = _definition_for(session, flow_id, definition)
    now = _now()
    key, payload = _sample_payload(session, definition.trigger.kind)
    event = build_event(session, user, definition.trigger, event_key=key, payload=payload, now=now)
    evaluation = evaluate(definition, event)
    chosen, action = _action_for(definition, branch or evaluation.branch, True)
    if action.kind == "NONE" or action.template is None:
        return PreviewView(
            branch=chosen,
            reason=evaluation.reason,
            item_count=len(evaluation.items),
            subject=None,
            html=None,
            to=[],
            cc=[],
            bcc=[],
            batches=0,
        )
    email = render(action.template, action.subject, evaluation.items, evaluation.fields, event, now)
    transport = get_transport()
    batches = batch_recipients(action, transport.max_recipients if transport else 50)
    return PreviewView(
        branch=chosen,
        reason=evaluation.reason,
        item_count=len(evaluation.items),
        subject=email.subject,
        html=email.html,
        to=action.to,
        cc=action.cc,
        bcc=action.bcc,
        batches=len(batches) if action.to else 0,
    )


def send_test(
    session: Session, user: User, flow_id: UUID, branch: FlowBranch | None
) -> RunView:
    """Send the e-mail only to the requesting user. Recorded as a test run:
    it never consumes a schedule window or an event."""
    repository.require_manage(user)
    flow = repository.get_flow(session, flow_id)
    version = repository.current_version(session, flow)
    definition = FlowDefinition.model_validate(version.definition)
    key, payload = _sample_payload(session, definition.trigger.kind)
    run = execute(
        session,
        flow=flow,
        version=version,
        reader=user,
        event_key=key,
        payload=payload,
        now=_now(),
        test_recipient=user.email,
        branch_override=branch,
    )
    assert run is not None
    session.commit()
    detail = repository.runs_for_flows(session, [flow.id], per_flow=30).get(flow.id, [])
    match = next(item for item in detail if item[0].id == run.id)
    return _run_view(*match)


def delivery_html(session: Session, user: User, delivery_id: UUID) -> str:
    repository.require_read(user)
    return repository.get_delivery(session, delivery_id).html_body


def request_suggestions(session: Session, user: User) -> SuggestionRunResult:
    """Ask the assistant for up to three new flows. Each one is stored as a
    suggestion and does nothing until a person registers it."""
    repository.require_manage(user)
    now = _now()
    flows = repository.list_flows(session)
    known: list[str] = []
    for _, version in flows:
        definition = FlowDefinition.model_validate(version.definition)
        for address in [*definition.on_yes.recipients(), *definition.on_no.recipients()]:
            if address not in known:
                known.append(address)
    items = repository.inconsistencies(session, user, now=now).items
    outcome = suggest(items, [flow.name for flow, _ in flows], known)
    for proposal in outcome.suggestions:
        repository.create_flow__no_commit(
            session,
            user,
            name=proposal.name,
            definition=proposal.definition,
            origin=FlowOrigin.TON_SUGGESTED,
            status=FlowStatus.SUGGESTED,
            now=now,
            suggestion_reason=proposal.reason,
            suggestion_model=outcome.model_name,
        )
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_EMAIL_FLOW_SUGGEST,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        extra={
            "created": len(outcome.suggestions),
            "rejected": outcome.rejected[:10],
            "model": outcome.model_name,
        },
    )
    session.commit()
    return SuggestionRunResult(
        created=len(outcome.suggestions),
        skipped=outcome.rejected,
        model_name=outcome.model_name,
    )
