"""Email flows v2: run the step tree for an event or schedule window, deliver
the composed e-mails, pause at waits/approvals and resume later. Also the
default weekly flow, previews, test sends, the style template, assets, the
periodic tick and the views."""

import datetime
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from onyx.configs.app_configs import WEB_DOMAIN
from onyx.db.models import User
from onyx.db.ton import email_flows as repository
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import (
    EmailFlow,
    EmailFlowApproval,
    EmailFlowDelivery,
    EmailFlowRun,
    EmailFlowVersion,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.email_flows.api import (
    ApprovalView,
    AssetView,
    CatalogView,
    DeliveryView,
    DraftResult,
    FieldView,
    FlowCreate,
    FlowDetail,
    FlowSummary,
    FlowTable,
    FlowUpdate,
    LayoutView,
    PreviewView,
    RunView,
    StepLine,
    TriggerView,
)
from onyx.ton.email_flows.catalog import (
    CHANGE_STATES,
    EVENT_KIND_DRE,
    EVENT_KIND_NG_IMPORT,
    ITEM_STATE_LABELS,
    OPERATOR_LABELS,
    OPERATORS_BY_TYPE,
    TRIGGERS,
    TriggerKind,
)
from onyx.ton.email_flows import drafter
from onyx.ton.email_flows.composer import (
    BLOCKS,
    EmailLayout,
    RenderContext,
    compose,
    sanitize,
    system_variables,
)
from onyx.ton.email_flows.engine import Engine, Frame, SendRequest
from onyx.ton.email_flows.events import build_event
from onyx.ton.email_flows.logic import (
    BRASILIA,
    WEEKDAYS,
    batch_recipients,
    describe_clause,
    describe_trigger,
    due_window,
    next_slot,
)
from onyx.ton.email_flows.models import (
    DeliveryStatus,
    EmailAction,
    FlowOrigin,
    FlowRunStatus,
    FlowStatus,
)
from onyx.ton.email_flows.steps import (
    SYSTEM_VARIABLES,
    UNIT_RECIPIENT_TOKEN,
    UNIT_VARIABLES,
    ApprovalStep,
    ConditionStep,
    FlowDefinitionV2,
    ForEachUnitStep,
    SendEmailStep,
    WaitStep,
    activation_problems_v2,
    iter_steps,
)
from onyx.ton.email_flows.transport import (
    EmailTransport,
    InlineImage,
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
LOGO_PATH = Path(__file__).parent / "assets" / "vale-norte-logo.png"
TRIGGERS_BY_EVENT: dict[str, tuple[TriggerKind, ...]] = {
    EVENT_KIND_NG_IMPORT: (
        TriggerKind.NG_IMPORT_COMPLETED,
        TriggerKind.NG_OCCURRENCE_CHANGED,
        TriggerKind.ACCOUNT_UNCLASSIFIED,
    ),
    EVENT_KIND_DRE: (TriggerKind.DRE_RECALCULATED,),
}
BLOCKS_BY_TRIGGER: dict[TriggerKind, list[str]] = {
    TriggerKind.SCHEDULE: ["inconsistency_table", "summary", "ton_button"],
    TriggerKind.NG_IMPORT_COMPLETED: ["inconsistency_table", "summary", "ton_button"],
    TriggerKind.NG_OCCURRENCE_CHANGED: ["inconsistency_table", "summary", "ton_button"],
    TriggerKind.ACCOUNT_UNCLASSIFIED: ["account_table", "summary", "ton_button"],
    TriggerKind.DRE_RECALCULATED: ["ton_button"],
}
TON_PATH_BY_TRIGGER: dict[TriggerKind, str] = {
    TriggerKind.ACCOUNT_UNCLASSIFIED: "/ton/classificacao",
    TriggerKind.DRE_RECALCULATED: "/ton/dre",
}


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _ton_url(kind: TriggerKind) -> str:
    return f"{WEB_DOMAIN.rstrip('/')}{TON_PATH_BY_TRIGGER.get(kind, '/ton/pendencias')}"


# ---------------------------------------------------------------------------
# Defaults: weekly flow, logo, style template
# ---------------------------------------------------------------------------

DEFAULT_WEEKLY_BODY = (
    "<p>Olá,</p>"
    "<p>Estas são as inconsistências do NG que ainda precisam de correção. "
    "Elas estão agrupadas por unidade, com o que fazer em cada uma.</p>"
    '<div data-block="summary"></div>'
    '<div data-block="inconsistency_table"></div>'
    "<p>Assim que forem corrigidas no NG, o TON confere na próxima extração "
    "e elas saem desta lista.</p>"
    '<div data-block="ton_button"></div>'
)


def default_weekly_definition() -> FlowDefinitionV2:
    return FlowDefinitionV2.model_validate(
        {
            "trigger": {"kind": "SCHEDULE", "frequency": "WEEKLY", "weekday": 0, "time": "08:00"},
            "steps": [
                {
                    "type": "condition",
                    "conditions": [{"field": "itens", "operator": "GT", "value": 0}],
                    "then": [
                        {
                            "type": "send_email",
                            "subject": "Inconsistências do NG – semana {semana} ({total})",
                            "body": DEFAULT_WEEKLY_BODY,
                        }
                    ],
                    "else": [],
                }
            ],
        }
    )


def ensure_defaults(session: Session) -> None:
    """Seed once: the Vale Norte logo, the style template and the weekly
    inconsistency flow (as a TON suggestion waiting for recipients)."""
    changed = False
    logo = repository.seeded_asset(session, repository.LOGO_SEED_KEY)
    if logo is None and LOGO_PATH.exists():
        logo = repository.create_asset__no_commit(
            session,
            None,
            name="Logo Vale Norte",
            content_type="image/png",
            data=LOGO_PATH.read_bytes(),
            seed_key=repository.LOGO_SEED_KEY,
        )
        changed = True
    if repository.read_layout(session) is None:
        defaults = EmailLayout()
        repository.save_layout__no_commit(
            session,
            {
                "brand_color": defaults.brand_color,
                "logo_asset_id": str(logo.id) if logo else None,
                "footer": defaults.footer,
            },
        )
        changed = True
    if repository.seeded_flow(session, DEFAULT_SEED_KEY) is None:
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
        changed = True
    if changed:
        session.commit()


def layout_view(session: Session) -> LayoutView:
    raw = repository.read_layout(session) or {}
    defaults = EmailLayout()
    logo = raw.get("logo_asset_id")
    return LayoutView(
        brand_color=raw.get("brand_color") or defaults.brand_color,
        logo_asset_id=UUID(logo) if logo else None,
        footer=raw.get("footer") or defaults.footer,
    )


def _layout(session: Session) -> EmailLayout:
    view = layout_view(session)
    return EmailLayout(
        brand_color=view.brand_color,
        logo_asset_id=view.logo_asset_id.hex if view.logo_asset_id else None,
        footer=view.footer,
    )


def save_layout(session: Session, user: User, request: LayoutView) -> LayoutView:
    repository.require_manage(user)
    if request.logo_asset_id is not None:
        repository.get_asset(session, request.logo_asset_id)
    repository.save_layout__no_commit(session, request.model_dump(mode="json"))
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_EMAIL_FLOW_CHANGE,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        extra={"change": "layout", **request.model_dump(mode="json")},
    )
    session.commit()
    return layout_view(session)


def upload_asset(session: Session, user: User, name: str, content_type: str, data: bytes) -> AssetView:
    repository.require_manage(user)
    asset = repository.create_asset__no_commit(
        session, user, name=name or "imagem", content_type=content_type, data=data
    )
    session.commit()
    return AssetView(id=asset.id, name=asset.name, content_type=asset.content_type, size_bytes=asset.size_bytes)


def asset_bytes(session: Session, user: User, asset_id: UUID) -> tuple[bytes, str]:
    repository.require_read(user)
    asset = repository.get_asset(session, asset_id)
    return asset.data, asset.content_type


# ---------------------------------------------------------------------------
# Delivery
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


def _images(session: Session, asset_ids: list[str]) -> tuple[InlineImage, ...]:
    assets = repository.assets_by_id(session, asset_ids)
    return tuple(
        InlineImage(
            content_id=f"asset-{asset_id}",
            filename=assets[asset_id].name.replace(" ", "-")[:60]
            + {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif"}[assets[asset_id].content_type],
            content_type=assets[asset_id].content_type,
            data=assets[asset_id].data,
        )
        for asset_id in asset_ids
        if asset_id in assets
    )


def _variables(
    definition: FlowDefinitionV2,
    flow_name: str,
    request: SendRequest,
    now: datetime.datetime,
) -> dict[str, str]:
    values = system_variables(
        when=now,
        fields=request.fields,
        flow_name=flow_name,
        ton_url=_ton_url(definition.trigger.kind),
    )
    values.update({variable.name: variable.value for variable in definition.variables})
    if request.unit is not None:
        values["unidade"] = request.unit
    return values


def _recipients(step: SendEmailStep, request: SendRequest) -> EmailAction:
    def expand(addresses: list[str]) -> list[str]:
        result: list[str] = []
        for address in addresses:
            for value in request.unit_emails if address == UNIT_RECIPIENT_TOKEN else [address]:
                if value not in result:
                    result.append(value)
        return result

    return EmailAction.model_construct(
        kind="EMAIL", to=expand(step.to), cc=expand(step.cc), bcc=expand(step.bcc), subject=step.subject, template=None
    )


class _RunSender:
    """The engine's send callback for a real or test run."""

    def __init__(
        self,
        session: Session,
        *,
        run: EmailFlowRun,
        flow_name: str,
        definition: FlowDefinitionV2,
        note: str | None,
        now: datetime.datetime,
        test_recipient: str | None = None,
        only_step: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.session = session
        self.run = run
        self.flow_name = flow_name
        self.definition = definition
        self.note = note
        self.now = now
        self.test_recipient = test_recipient
        self.only_step = only_step
        self.sleep = sleep
        self.layout = _layout(session)
        self.transport = get_transport()
        self.done = repository.delivered_steps(session, run.id)
        self.sent_steps = 0

    def __call__(self, request: SendRequest) -> None:
        step = request.step
        if self.only_step is not None and step.id != self.only_step:
            return
        if self.test_recipient is not None and self.sent_steps:
            return
        if (step.id, request.unit or "") in self.done:
            return
        action = _recipients(step, request)
        if self.test_recipient is not None:
            action = action.model_copy(update={"to": [self.test_recipient], "cc": [], "bcc": []})
        if not action.to:
            logger.info("TON email flow step %s skipped: no recipients", step.id)
            return
        ctx = RenderContext(
            variables=_variables(self.definition, self.flow_name, request, self.now),
            items=request.items,
            fields=request.fields,
            ton_url=_ton_url(self.definition.trigger.kind),
            note=self.note,
        )
        email = compose(subject=step.subject, body=step.body, ctx=ctx, layout=self.layout if step.use_layout else None)
        images = _images(self.session, email.asset_ids)
        batches = batch_recipients(action, self.transport.max_recipients if self.transport else 50)
        for index, batch in enumerate(batches, start=1):
            message = OutgoingEmail(batch.to, batch.cc, batch.bcc, email.subject, email.html, email.text, images)
            status, message_id, error, attempts = _deliver(self.transport, message, self.sleep)
            repository.add_delivery__no_commit(
                self.session,
                EmailFlowDelivery(
                    run_id=self.run.id,
                    status=status.value,
                    provider=self.transport.name if self.transport else provider_name(),
                    to_addresses=batch.to,
                    cc_addresses=batch.cc,
                    bcc_addresses=batch.bcc,
                    batch_no=index,
                    batch_count=len(batches),
                    subject=email.subject[:300],
                    html_body=email.html,
                    text_body=email.text,
                    provider_message_id=message_id,
                    step_id=step.id,
                    unit=request.unit,
                    attempts=attempts,
                    error=error[:500] if error else None,
                    sent_at=_now() if status is DeliveryStatus.SENT else None,
                ),
            )
        self.session.flush()
        self.done.add((step.id, request.unit or ""))
        self.sent_steps += 1


def _final_status(session: Session, run: EmailFlowRun) -> tuple[str, str | None]:
    statuses = [DeliveryStatus(d.status) for d in repository.run_deliveries(session, run.id)]
    if not statuses:
        return FlowRunStatus.SILENT.value, "Nenhum e-mail a enviar neste caso."
    if all(s is DeliveryStatus.SENT for s in statuses):
        return FlowRunStatus.SENT.value, None
    if all(s is DeliveryStatus.NOT_CONFIGURED for s in statuses):
        return FlowRunStatus.NOT_CONFIGURED.value, "E-mail não configurado: o conteúdo ficou guardado no TON."
    if any(s is DeliveryStatus.SENT for s in statuses):
        return FlowRunStatus.PARTIAL.value, "Parte dos e-mails não foi enviada."
    return FlowRunStatus.FAILED.value, "O envio falhou depois de 3 tentativas."


def _notify_approvers(session: Session, flow: EmailFlow, approval: EmailFlowApproval) -> None:
    transport = get_transport()
    if transport is None or not approval.approvers:
        return
    link = f"{WEB_DOMAIN.rstrip('/')}/ton/fluxos?aprovacao={approval.id}"
    text = (
        f"O fluxo \"{flow.name}\" aguarda sua aprovação para continuar "
        f"({approval.item_count} itens). {approval.message or ''}\n\nAprovar ou recusar: {link}"
    )
    html = (
        '<!doctype html><html lang="pt-BR"><body style="font-family:Arial,sans-serif;color:#1f2937">'
        f"<p>O fluxo <strong>{flow.name}</strong> aguarda sua aprovação para continuar "
        f"({approval.item_count} itens).</p>"
        + (f"<p>{sanitize(approval.message)}</p>" if approval.message else "")
        + f'<p><a href="{link}">Aprovar ou recusar no TON</a></p></body></html>'
    )
    try:
        transport.send(OutgoingEmail(approval.approvers, [], [], f"Aprovação pendente: {flow.name}", html, text))
    except TransportError as error:
        logger.warning("TON approval notification failed: %s", error)


def _apply_outcome(
    session: Session,
    *,
    flow: EmailFlow,
    run: EmailFlowRun,
    outcome: Any,
    items_by_key: dict[str, Any],
) -> None:
    suspension = outcome.suspension
    run.context = {**(run.context or {}), "trace": [*(run.context or {}).get("trace", []), *outcome.trace][-60:]}
    if suspension is None:
        run.status, run.reason = _final_status(session, run)
        run.resume_at = None
        run.cursor = None
        run.finished_at = _now()
        return
    run.status = FlowRunStatus.WAITING.value
    run.cursor = {"reason": suspension.reason, "frames": [frame.dump() for frame in suspension.frames]}
    if suspension.reason == "wait":
        run.resume_at = suspension.resume_at
        local = suspension.resume_at.astimezone(BRASILIA) if suspension.resume_at else None
        run.reason = f"Esperando até {local:%d/%m/%Y %H:%M}." if local else "Esperando."
        return
    approval_step = suspension.approval
    assert approval_step is not None
    frame = suspension.frames[0] if suspension.frames else None
    count = len([key for key in (frame.item_keys if frame else []) if key in items_by_key])
    approval = repository.create_approval__no_commit(
        session,
        run=run,
        step_id=approval_step.id,
        approvers=approval_step.approvers,
        message=approval_step.message,
        item_count=count,
    )
    run.resume_at = None
    run.reason = f"Aguardando aprovação de {', '.join(approval_step.approvers) or 'alguém'}."
    _notify_approvers(session, flow, approval)


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
    only_step: str | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> EmailFlowRun | None:
    """Run the flow once for this event. ``None`` when the pair already ran.
    Test runs go only to ``test_recipient`` and walk past waits/approvals."""
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
        definition = FlowDefinitionV2.model_validate(version.definition)
        event = build_event(session, reader, definition.trigger, event_key=event_key, payload=payload, now=now)
        run.item_count = len(event.items)
        run.context = {"payload": payload, "event_key": event_key, "fields": dict(event.fields)}
        sender = _RunSender(
            session, run=run, flow_name=flow.name, definition=definition, note=event.note, now=now,
            test_recipient=test_recipient, only_step=only_step, sleep=sleep,
        )
        engine = Engine(definition, base_fields=dict(event.fields), send=sender, now=now, simulate=is_test)
        outcome = engine.run(list(event.items))
        _apply_outcome(session, flow=flow, run=run, outcome=outcome, items_by_key={i.key: i for i in event.items})
        emit_ton_audit_event(
            session,
            action=AuditAction.TON_EMAIL_FLOW_SEND,
            outcome=AuditOutcome.SUCCESS if run.status in ("SENT", "SILENT", "WAITING") else AuditOutcome.FAILURE,
            actor_user_id=reader.id if is_test else None,
            resource_kind=TonAuditResourceKind.EMAIL_FLOW,
            resource_id=flow.id,
            extra={"run_id": str(run.id), "test": is_test, "status": run.status},
        )
    except OnyxError as error:
        run.status = FlowRunStatus.FAILED.value
        run.reason = (
            "O responsável pelo fluxo não tem acesso a esses dados. Reative o fluxo com um usuário que tenha."
            if error.error_code is OnyxErrorCode.INSUFFICIENT_PERMISSIONS
            else f"Falha ao montar o e-mail: {error.detail}"
        )[:500]
        run.finished_at = _now()
    except Exception as error:
        logger.exception("TON email flow run failed flow_id=%s", flow.id)
        run.status = FlowRunStatus.FAILED.value
        run.reason = f"Falha ao executar o fluxo: {type(error).__name__}"
        run.finished_at = _now()
    return run


def resume(session: Session, run: EmailFlowRun, now: datetime.datetime) -> None:
    """Continue a paused run: re-read the data, keep the items still open."""
    flow = repository.get_flow(session, run.flow_id)
    version = session.get(EmailFlowVersion, run.version_id)
    assert version is not None
    reader = _reader(session, flow)
    if reader is None or flow.status != FlowStatus.ACTIVE.value:
        run.status = FlowRunStatus.STOPPED.value
        run.reason = "Fluxo pausado ou responsável sem acesso; a execução foi encerrada."
        run.resume_at = None
        run.finished_at = now
        return
    try:
        definition = FlowDefinitionV2.model_validate(version.definition)
        context = run.context or {}
        payload = dict(context.get("payload") or {})
        event = build_event(session, reader, definition.trigger, event_key=run.event_key, payload=payload, now=now)
        frames = [Frame.load(raw) for raw in (run.cursor or {}).get("frames", [])]
        sender = _RunSender(session, run=run, flow_name=flow.name, definition=definition, note=event.note, now=now)
        engine = Engine(definition, base_fields=dict(event.fields), send=sender, now=now)
        outcome = engine.resume(frames, list(event.items))
        _apply_outcome(session, flow=flow, run=run, outcome=outcome, items_by_key={i.key: i for i in event.items})
    except Exception as error:
        logger.exception("TON email flow resume failed run_id=%s", run.id)
        run.status = FlowRunStatus.FAILED.value
        run.reason = f"Falha ao retomar o fluxo: {type(error).__name__}"
        run.resume_at = None
        run.finished_at = now


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


def _definition(version: EmailFlowVersion) -> FlowDefinitionV2:
    return FlowDefinitionV2.model_validate(version.definition)


def dispatch_schedules(session: Session, now: datetime.datetime | None = None) -> int:
    current = now or _now()
    ran = 0
    for flow, version in repository.active_flows(session, TriggerKind.SCHEDULE.value):
        definition = _definition(version)
        assert flow.active_since is not None
        key = due_window(definition.trigger, current, flow.active_since)
        if key is None:
            continue
        reader = _reader(session, flow)
        if reader is None:
            _owner_missing_run(session, flow, version, key, current)
            session.commit()
            continue
        run = execute(session, flow=flow, version=version, reader=reader, event_key=key, payload={}, now=current)
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
                execute(session, flow=flow, version=version, reader=reader, event_key=key, payload=dict(event.payload), now=current)
        event.processed_at = current
    session.commit()
    return len(events)


def resume_due(session: Session, now: datetime.datetime | None = None) -> int:
    current = now or _now()
    runs = repository.due_waiting_runs(session, current)
    for run in runs:
        resume(session, run, current)
        session.commit()
    return len(runs)


def tick(session: Session) -> None:
    process_events(session)
    dispatch_schedules(session)
    resume_due(session)


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


def _can_decide(user: User, approval: EmailFlowApproval) -> bool:
    return (user.email or "").lower() in approval.approvers or repository.can_manage(user)


def decide(session: Session, user: User, approval_id: UUID, approve: bool, note: str | None) -> ApprovalView:
    repository.require_read(user)
    approval = repository.get_approval(session, approval_id)
    if approval.status != "PENDING":
        raise OnyxError(OnyxErrorCode.CONFLICT, "Esta aprovação já foi decidida")
    if not _can_decide(user, approval):
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, "Você não está entre as pessoas que aprovam este fluxo")
    now = _now()
    run = repository.get_run(session, approval.run_id)
    flow = repository.get_flow(session, run.flow_id)
    approval.status = "APPROVED" if approve else "REJECTED"
    approval.decided_by = user.id
    approval.decided_at = now
    approval.note = note
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_EMAIL_FLOW_CHANGE,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.EMAIL_FLOW,
        resource_id=flow.id,
        extra={"change": "approval", "approved": approve, "run_id": str(run.id), "note": note},
    )
    if approve:
        resume(session, run, now)
    else:
        run.status = FlowRunStatus.STOPPED.value
        run.reason = f"Recusado por {user.email}" + (f": {note}" if note else "")
        run.cursor = None
        run.finished_at = now
    session.commit()
    return _approval_view(approval, run, flow, user)


def _approval_view(approval: EmailFlowApproval, run: EmailFlowRun, flow: EmailFlow, user: User) -> ApprovalView:
    return ApprovalView(
        id=approval.id,
        flow_id=flow.id,
        flow_name=flow.name,
        run_id=run.id,
        step_id=approval.step_id,
        approvers=approval.approvers,
        message=approval.message,
        item_count=approval.item_count,
        status=approval.status,
        can_decide=approval.status == "PENDING" and _can_decide(user, approval),
        created_at=approval.created_at,
    )


# ---------------------------------------------------------------------------
# Plain-language views
# ---------------------------------------------------------------------------


def _clauses_text(definition: FlowDefinitionV2, step: ConditionStep) -> str:
    if not step.conditions:
        return "sempre"
    return " e ".join(describe_clause(definition.trigger, clause) for clause in step.conditions)


def _who(step: SendEmailStep) -> str:
    to = ["o e-mail da unidade" if a == UNIT_RECIPIENT_TOKEN else a for a in step.to]
    if not to:
        return "(sem destinatário)"
    head = to[0] if len(to) == 1 else f"{len(to)} pessoas"
    copies = len(step.cc) + len(step.bcc)
    return f"{head}{f' + {copies} em cópia' if copies else ''}"


def steps_text(definition: FlowDefinitionV2) -> list[StepLine]:
    lines: list[StepLine] = []

    def walk(steps: list[Any], depth: int) -> None:
        for step in steps:
            if isinstance(step, ConditionStep):
                lines.append(StepLine(depth=depth, text=f"Se {_clauses_text(definition, step)}:"))
                walk(step.then, depth + 1)
                if step.otherwise:
                    lines.append(StepLine(depth=depth, text="Senão:"))
                    walk(step.otherwise, depth + 1)
            elif isinstance(step, SendEmailStep):
                lines.append(StepLine(depth=depth, text=f"Enviar e-mail “{step.subject or 'sem assunto'}” para {_who(step)}"))
            elif isinstance(step, ForEachUnitStep):
                lines.append(StepLine(depth=depth, text="Para cada unidade:"))
                walk(step.steps, depth + 1)
            elif isinstance(step, WaitStep):
                text = (
                    f"Esperar {step.days} dia(s) {step.hours} h e conferir de novo"
                    if step.mode == "duration"
                    else f"Esperar até {WEEKDAYS[step.weekday or 0]} às {step.time} e conferir de novo"
                )
                lines.append(StepLine(depth=depth, text=text))
            elif isinstance(step, ApprovalStep):
                lines.append(StepLine(depth=depth, text=f"Pedir aprovação de {', '.join(step.approvers) or '(ninguém)'}"))

    walk(definition.steps, 0)
    return lines


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
        step_id=delivery.step_id,
        unit=delivery.unit,
        error=delivery.error,
        sent_at=delivery.sent_at,
        created_at=delivery.created_at,
    )


def _run_view(run: EmailFlowRun, version: int, deliveries: list[EmailFlowDelivery]) -> RunView:
    return RunView(
        id=run.id,
        version=version,
        event_key=run.event_key,
        status=FlowRunStatus(run.status),
        is_test=run.is_test,
        item_count=run.item_count,
        reason=run.reason,
        resume_at=run.resume_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        deliveries=[_delivery_view(item) for item in deliveries],
    )


def _summary(
    flow: EmailFlow,
    version: EmailFlowVersion,
    runs: list[tuple[EmailFlowRun, int, list[EmailFlowDelivery]]],
) -> FlowSummary:
    definition = _definition(version)
    last = next((item for item in runs if not item[0].is_test), None)
    next_run = (
        next_slot(definition.trigger, _now())
        if flow.status == FlowStatus.ACTIVE.value and definition.trigger.kind is TriggerKind.SCHEDULE
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
        steps_text=steps_text(definition),
        emails=len([s for s in iter_steps(definition.steps) if isinstance(s, SendEmailStep)]),
        suggestion_reason=flow.suggestion_reason,
        problems=activation_problems_v2(definition),
        last_run=_run_view(*last) if last else None,
        next_run_at=next_run,
        updated_at=flow.updated_at,
    )


def flow_table(session: Session, user: User) -> FlowTable:
    repository.require_read(user)
    ensure_defaults(session)
    flows = repository.list_flows(session)
    runs = repository.runs_for_flows(session, [flow.id for flow, _ in flows], per_flow=3)
    approvals = [
        _approval_view(approval, run, flow, user)
        for approval, run, flow in repository.pending_approvals(session)
    ]
    return FlowTable(
        flows=[_summary(flow, version, runs.get(flow.id, [])) for flow, version in flows],
        approvals=approvals,
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


def catalog_view(session: Session) -> CatalogView:
    ensure_defaults(session)
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
                blocks=BLOCKS_BY_TRIGGER[spec.kind],
            )
            for spec in TRIGGERS.values()
        ],
        operators=OPERATOR_LABELS,
        changes=[(state, ITEM_STATE_LABELS[state]) for state in CHANGE_STATES],
        system_variables=SYSTEM_VARIABLES,
        unit_variables=UNIT_VARIABLES,
        blocks=BLOCKS,
        assets=[
            AssetView(id=a.id, name=a.name, content_type=a.content_type, size_bytes=a.size_bytes)
            for a in repository.list_assets(session)
        ],
        layout=layout_view(session),
        provider=provider_name(),
        provider_ready=get_transport() is not None,
        sender=sender_address(),
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _require_ready(definition: FlowDefinitionV2) -> None:
    problems = activation_problems_v2(definition)
    if problems:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "; ".join(problems))


def _clean(definition: FlowDefinitionV2) -> FlowDefinitionV2:
    for step in iter_steps(definition.steps):
        if isinstance(step, SendEmailStep):
            step.body = sanitize(step.body)
    return definition


def create(session: Session, user: User, request: FlowCreate) -> FlowDetail:
    repository.require_manage(user)
    definition = _clean(request.definition)
    if request.activate:
        _require_ready(definition)
    flow = repository.create_flow__no_commit(
        session,
        user,
        name=request.name.strip(),
        definition=definition,
        origin=FlowOrigin.USER,
        status=FlowStatus.ACTIVE if request.activate else FlowStatus.PAUSED,
        now=_now(),
    )
    session.commit()
    return flow_detail(session, user, flow.id)


def update(session: Session, user: User, flow_id: UUID, request: FlowUpdate) -> FlowDetail:
    repository.require_manage(user)
    flow = repository.get_flow(session, flow_id)
    definition = _clean(request.definition)
    if flow.status == FlowStatus.ACTIVE.value:
        _require_ready(definition)
    repository.add_version__no_commit(session, user, flow, name=request.name.strip(), definition=definition, now=_now())
    session.commit()
    return flow_detail(session, user, flow.id)


def change_status(session: Session, user: User, flow_id: UUID, status: FlowStatus) -> FlowDetail:
    repository.require_manage(user)
    flow = repository.get_flow(session, flow_id)
    now = _now()
    if status is FlowStatus.ACTIVE:
        _require_ready(_definition(repository.current_version(session, flow)))
    repository.set_status__no_commit(session, user, flow, status, now)
    if status in (FlowStatus.PAUSED, FlowStatus.DISCARDED):
        repository.cancel_pending_approvals__no_commit(session, flow.id, now)
    session.commit()
    return flow_detail(session, user, flow.id)


def _sample_payload(session: Session, kind: TriggerKind) -> tuple[str, dict[str, object]]:
    review = repository.latest_succeeded_review(session)
    if kind in (TriggerKind.SCHEDULE, TriggerKind.DRE_RECALCULATED) or review is None:
        return "preview", {}
    return f"preview:{review.id}", {"review_run_id": str(review.id), "source_id": str(review.source_id)}


def preview(
    session: Session,
    user: User,
    *,
    flow_id: UUID | None,
    definition: FlowDefinitionV2 | None,
    step_id: str | None,
    flow_name: str | None,
) -> PreviewView:
    """Render one e-mail step with today's data, without sending. Event
    triggers use the latest NG import as the sample event."""
    repository.require_read(user)
    flow = repository.get_flow(session, flow_id) if flow_id else None
    if definition is None:
        if flow is None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Informe o fluxo")
        definition = _definition(repository.current_version(session, flow))
    definition = _clean(definition)
    now = _now()
    key, payload = _sample_payload(session, definition.trigger.kind)
    event = build_event(session, user, definition.trigger, event_key=key, payload=payload, now=now)
    captured: list[SendRequest] = []

    def capture(request: SendRequest) -> None:
        if not captured and (step_id is None or request.step.id == step_id):
            captured.append(request)

    engine = Engine(definition, base_fields=dict(event.fields), send=capture, now=now, simulate=True)
    outcome = engine.run(list(event.items))
    if not captured:
        target = next(
            (s for s in iter_steps(definition.steps) if isinstance(s, SendEmailStep) and (step_id is None or s.id == step_id)),
            None,
        )
        if target is None:
            return PreviewView(step_id=step_id, unit=None, reason="O fluxo não tem e-mail para mostrar.", item_count=0,
                               subject=None, html=None, to=[], cc=[], bcc=[], trace=outcome.trace)
        # Hoje nenhum item chega a este e-mail: mostre-o vazio mesmo assim.
        captured.append(SendRequest(target, [], {"itens": 0, "valor_total": 0.0}, None, []))
        reason = "Com os dados de hoje nenhum item chega a este e-mail; prévia sem itens."
    else:
        reason = f"Prévia com os dados de hoje ({len(captured[0].items)} itens)."
    request = captured[0]
    ctx = RenderContext(
        variables=_variables(definition, flow_name or (flow.name if flow else "Fluxo"), request, now),
        items=request.items,
        fields=request.fields,
        ton_url=_ton_url(definition.trigger.kind),
        note=event.note,
        image_mode="url",
    )
    layout = _layout(session) if request.step.use_layout else None
    email = compose(subject=request.step.subject, body=request.step.body, ctx=ctx, layout=layout)
    action = _recipients(request.step, request)
    return PreviewView(
        step_id=request.step.id,
        unit=request.unit,
        reason=reason,
        item_count=len(request.items),
        subject=email.subject,
        html=email.html,
        to=action.to,
        cc=action.cc,
        bcc=action.bcc,
        trace=outcome.trace,
    )


def send_test(session: Session, user: User, flow_id: UUID, step_id: str | None) -> RunView:
    """Send one e-mail step only to the requesting user (a test run never
    consumes a schedule window or an event, and skips waits/approvals)."""
    repository.require_manage(user)
    flow = repository.get_flow(session, flow_id)
    version = repository.current_version(session, flow)
    key, payload = _sample_payload(session, _definition(version).trigger.kind)
    run = execute(
        session, flow=flow, version=version, reader=user, event_key=key, payload=payload,
        now=_now(), test_recipient=user.email, only_step=step_id,
    )
    assert run is not None
    session.commit()
    detail = repository.runs_for_flows(session, [flow.id], per_flow=30).get(flow.id, [])
    match = next(item for item in detail if item[0].id == run.id)
    return _run_view(*match)


def delivery_html(session: Session, user: User, delivery_id: UUID) -> str:
    repository.require_read(user)
    # Sent with inline images (cid:); in the browser they come from the API.
    html = repository.get_delivery(session, delivery_id).html_body
    return html.replace('src="cid:asset-', 'src="/api/ton/email-flows/assets/')



# ---------------------------------------------------------------------------
# Drafts from the chat
# ---------------------------------------------------------------------------


def draft_flow(session: Session, user: User, request: str, flow_id: UUID | None = None) -> DraftResult:
    """Create (or adjust) a flow draft from a chat request. The draft is a
    TON suggestion owned by the person who asked; nothing runs until it is
    activated."""
    repository.require_manage(user)
    existing = repository.get_flow(session, flow_id) if flow_id else None
    if existing is not None and existing.status == FlowStatus.DISCARDED.value:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Esse rascunho foi descartado")
    current = repository.current_version(session, existing).definition if existing else None
    try:
        outcome = drafter.draft(request, current=current, current_name=existing.name if existing else None)
    except drafter.DraftError as error:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, f"Não consegui montar o fluxo: {error}") from None
    definition = _clean(outcome.definition)
    now = _now()
    reason = outcome.summary or f"Pedido no chat: {request[:300]}"
    blocking = activation_problems_v2(definition)
    if existing is None:
        flow = repository.create_flow__no_commit(
            session,
            user,
            name=outcome.name,
            definition=definition,
            origin=FlowOrigin.TON_SUGGESTED,
            status=FlowStatus.SUGGESTED,
            now=now,
            suggestion_reason=reason,
            suggestion_model=outcome.model_name,
        )
    else:
        flow = existing
        if flow.status == FlowStatus.ACTIVE.value and blocking:
            raise OnyxError(
                OnyxErrorCode.INVALID_INPUT,
                "O ajuste deixaria o fluxo ativo incompleto: " + "; ".join(blocking),
            )
        repository.add_version__no_commit(session, user, flow, name=outcome.name, definition=definition, now=now)
        if flow.status == FlowStatus.SUGGESTED.value:
            flow.suggestion_reason = reason
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_EMAIL_FLOW_SUGGEST,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.EMAIL_FLOW,
        resource_id=flow.id,
        extra={"source": "chat", "created": existing is None, "model": outcome.model_name},
    )
    session.commit()
    first_email = next((s for s in iter_steps(definition.steps) if isinstance(s, SendEmailStep)), None)
    return DraftResult(
        flow_id=flow.id,
        name=flow.name,
        status=FlowStatus(flow.status),
        created=existing is None,
        when=describe_trigger(definition.trigger),
        steps_text=steps_text(definition),
        problems=blocking + [item for item in outcome.missing if item not in blocking],
        preview_subject=first_email.subject if first_email else None,
        editor_url=f"/ton/fluxos/{flow.id}",
        can_activate=not blocking,
    )
