"""Automations: orchestration around the interpreter.

* Runs are created QUEUED (trigger output frozen) and executed by the Celery
  task ``ton_automation_execute_run``, which takes a lease on the run.
* Every step is a checkpoint row; a run that waits (delay, approval, retry)
  or whose worker stopped is queued again by the tick.
* The tick (Celery Beat, every minute) consumes the event outbox, fires due
  schedules, re-queues due and orphaned runs and ends runs past their
  time limit.
"""

import datetime
import json
import os
import socket
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from onyx.configs.app_configs import WEB_DOMAIN
from onyx.db.models import User
from onyx.db.ton import automations as repository
from onyx.db.ton import email_flows as flow_repository
from onyx.db.ton.models import (
    TonAutomation,
    TonAutomationApproval,
    TonAutomationRun,
    TonAutomationStepRun,
    TonAutomationVersion,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.automations import legacy, schedule as recurrence
from onyx.ton.automations.api import (
    ApprovalView,
    AssetView,
    AutomationCreate,
    AutomationDetail,
    AutomationRef,
    AutomationSummary,
    AutomationTable,
    AutomationUpdate,
    CatalogView,
    FieldView,
    FileView,
    IssueView,
    KindView,
    NodeTypeView,
    NoticeView,
    OutputView,
    ParamView,
    PreviewRequest,
    PreviewResult,
    RetryView,
    RunDetail,
    RunSummary,
    StepView,
    TemplateView,
    ValidateResult,
    VersionView,
)
from onyx.ton.automations.conditions import OPERATOR_LABELS
from onyx.ton.automations.definition import (
    FINAL_RUN_STATUSES,
    KIND_DESCRIPTIONS,
    KIND_LABELS,
    AutomationDefinition,
    AutomationKind,
    AutomationOrigin,
    AutomationStatus,
    RunMode,
    RunStatus,
    StepStatus,
    find_node,
    iter_nodes,
)
from onyx.ton.automations.expressions import FUNCTION_HELP, ExpressionError, render
from onyx.ton.automations.interpreter import (
    ApprovalRequest,
    Interpreter,
    MemoryStore,
    RunOutcome,
    StepRecord,
    StopAtNode,
    _Frame,
)
from onyx.ton.automations.nodes.triggers import EVENT_KIND_AUTOMATION_FAILED
from onyx.ton.automations.registry import (
    GROUP_LABELS,
    ActionContext,
    NodeSpec,
    OutputSpec,
    TriggerContext,
    get_registry,
)
from onyx.ton.automations.templates import TEMPLATES
from onyx.ton.automations.validation import activation_problems, suggest_kind, validate
from onyx.ton.email_flows.composer import BLOCKS, sanitize
from onyx.ton.email_flows.models import FlowStatus
from onyx.utils.audit import AuditAction, AuditOutcome
from onyx.utils.logger import setup_logger

logger = setup_logger()

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"[:80]
HISTORY_DAYS = 28
MAX_FILE_BYTES = 5 * 1024 * 1024
FILE_TYPES = (".xlsx", ".xlsm", ".csv", ".txt", ".json", ".md", ".pdf", ".docx")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _definition(version: TonAutomationVersion) -> AutomationDefinition:
    return AutomationDefinition.model_validate(version.definition)


def _link(automation_id: UUID, run_id: UUID | None = None) -> str:
    path = f"/ton/automacoes/{automation_id}"
    return f"{path}/execucoes/{run_id}" if run_id else path


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


def _output_view(output: OutputSpec) -> OutputView:
    return OutputView(
        key=output.key,
        label=output.label,
        type=output.type,
        description=output.description,
        item_fields=[_output_view(item) for item in output.item_fields],
    )


def _node_view(spec: NodeSpec) -> NodeTypeView:
    return NodeTypeView(
        type=spec.type,
        group=spec.group,
        label=spec.label,
        description=spec.description,
        icon=spec.icon,
        params=[
            ParamView(
                key=param.key,
                label=param.label,
                kind=param.kind,
                required=param.required,
                default=param.default,
                help=param.help,
                placeholder=param.placeholder,
                options=list(param.options),
                dynamic=param.dynamic,
                min=param.min,
                max=param.max,
                item_fields=[
                    FieldView(key=f.key, label=f.label, kind=f.kind, options=list(f.options), placeholder=f.placeholder)
                    for f in param.item_fields
                ],
                show_if=(param.show_if[0], list(param.show_if[1])) if param.show_if else None,
                advanced=param.advanced,
            )
            for param in spec.params
        ],
        outputs=[_output_view(output) for output in spec.outputs],
        container=spec.container,
        is_trigger=spec.is_trigger,
        side_effect=spec.side_effect,
        ai=spec.ai,
        satisfies=list(spec.satisfies),
        dynamic_outputs=spec.dynamic_outputs,
        default_retry=RetryView(**spec.default_retry.model_dump()),
        keywords=list(spec.keywords),
    )


def _llm_ready() -> bool:
    try:
        from onyx.llm.factory import get_default_llm

        get_default_llm()
    except Exception:  # noqa: BLE001 - any failure means "not configured"
        return False
    return True


def catalog_view(session: Session, user: User) -> CatalogView:
    from onyx.ton.email_flows.transport import get_transport, sender_address

    repository.require_read(user)
    ensure_defaults(session)
    registry = get_registry()
    return CatalogView(
        nodes=[_node_view(spec) for spec in registry.values() if not spec.type.startswith("test.")],
        groups=GROUP_LABELS,
        kinds=[KindView(key=kind, label=KIND_LABELS[kind], description=KIND_DESCRIPTIONS[kind]) for kind in AutomationKind],
        templates=[
            TemplateView(key=t.key, name=t.name, description=t.description, kind=t.kind, trigger_type=t.definition["trigger"]["type"])
            for t in TEMPLATES
        ],
        functions=FUNCTION_HELP,
        operators=OPERATOR_LABELS,
        blocks=BLOCKS,
        assets=[AssetView(id=a.id, name=a.name) for a in flow_repository.list_assets(session)],
        automations=[AutomationRef(id=a.id, name=a.name) for a, _v in repository.list_automations(session)],
        provider_ready=get_transport() is not None,
        sender=sender_address(),
        llm_ready=_llm_ready(),
    )


# ---------------------------------------------------------------------------
# Defaults and the e-mail flows conversion
# ---------------------------------------------------------------------------


_STATUS_FROM_FLOW = {
    FlowStatus.SUGGESTED.value: AutomationStatus.DRAFT,
    FlowStatus.ACTIVE.value: AutomationStatus.ACTIVE,
    FlowStatus.PAUSED.value: AutomationStatus.PAUSED,
}


def migrate_email_flows(session: Session) -> int:
    """Convert every e-mail flow not converted yet. The v2 engine no longer
    runs: converted flows are paused there and their waiting runs stopped."""
    done = repository.migrated_flow_ids(session)
    now = _now()
    converted = 0
    for flow, version in flow_repository.list_flows(session):
        if flow.id in done:
            continue
        try:
            definition = legacy.convert(version.definition)
        except (ValidationError, ValueError) as error:
            logger.warning("TON automation: e-mail flow %s not converted: %s", flow.id, error)
            continue
        status = _STATUS_FROM_FLOW.get(flow.status, AutomationStatus.PAUSED)
        if status is AutomationStatus.ACTIVE and activation_problems(definition, AutomationKind.EMAIL):
            status = AutomationStatus.PAUSED
        repository.create__no_commit(
            session,
            None,
            name=flow.name,
            description="Convertida do fluxo de e-mail de mesmo nome.",
            kind=AutomationKind.EMAIL,
            definition=_clean(definition),
            origin=AutomationOrigin.TON_SUGGESTED if flow.origin == "TON_SUGGESTED" else AutomationOrigin.MIGRATED,
            status=status,
            now=now,
            suggestion_reason=flow.suggestion_reason,
            suggestion_model=flow.suggestion_model,
            seed_key=f"email-flow:{flow.seed_key}"[:64] if flow.seed_key else None,
            legacy_flow_id=flow.id,
            owner_id=flow.owner_id if status is AutomationStatus.ACTIVE else None,
            active_since=flow.active_since if status is AutomationStatus.ACTIVE else None,
        )
        if flow.status == FlowStatus.ACTIVE.value:
            flow.status = FlowStatus.PAUSED.value
            flow.updated_at = now
        flow_repository.cancel_pending_approvals__no_commit(session, flow.id, now)
        converted += 1
    if converted:
        session.commit()
    return converted


def ensure_defaults(session: Session) -> None:
    from onyx.db.ton.agent import sync_agent__system
    from onyx.ton.email_flows import service as flow_service

    flow_service.ensure_defaults(session)
    migrate_email_flows(session)
    # Chat drafting needs the automation tool on the agent provisioned earlier.
    sync_agent__system(session)


# ---------------------------------------------------------------------------
# Run store over the database
# ---------------------------------------------------------------------------


class DbRunStore:
    def __init__(self, session: Session, run: TonAutomationRun, automation: TonAutomation) -> None:
        self.session = session
        self.run = run
        self.automation = automation

    def load(self) -> dict[tuple[str, str], StepRecord]:
        return {
            (row.node_id, row.iteration): StepRecord(
                node_id=row.node_id,
                iteration=row.iteration,
                node_type=row.node_type,
                status=StepStatus(row.status),
                attempt=row.attempt,
                inputs=row.inputs,
                outputs=row.outputs,
                error=row.error,
                started_at=row.started_at,
                finished_at=row.finished_at,
                next_retry_at=row.next_retry_at,
            )
            for row in repository.step_rows(self.session, self.run.id)
        }

    def save(self, record: StepRecord) -> None:
        repository.upsert_step__no_commit(
            self.session,
            self.run.id,
            {
                "node_id": record.node_id,
                "iteration": record.iteration,
                "node_type": record.node_type,
                "status": record.status.value,
                "attempt": record.attempt,
                "inputs": record.inputs,
                "outputs": record.outputs,
                "error": record.error,
                "started_at": record.started_at,
                "finished_at": record.finished_at,
                "next_retry_at": record.next_retry_at,
            },
        )
        repository.extend_lease(self.session, self.run.id, WORKER_ID, _now())
        self.session.commit()

    def cancelled(self) -> bool:
        return repository.run_status(self.session, self.run.id) == RunStatus.CANCELLED.value

    def heartbeat(self) -> None:
        repository.extend_lease(self.session, self.run.id, WORKER_ID, _now())
        self.session.commit()

    def open_approval(self, record: StepRecord, request: ApprovalRequest) -> str:
        approval = repository.create_approval__no_commit(
            self.session,
            automation_id=self.automation.id,
            run_id=self.run.id,
            node_id=request.node_id,
            iteration=request.iteration,
            approvers=request.approvers,
            title=request.title[:300],
            details=request.details or None,
            options=request.options,
            expires_at=request.expires_at,
        )
        self.session.commit()
        _notify_approvers(self.automation, approval)
        return str(approval.id)

    def approval_result(self, approval_id: str) -> dict[str, Any] | None:
        approval = self.session.get(TonAutomationApproval, UUID(approval_id), populate_existing=True)
        if approval is None or approval.status != "DONE":
            return None
        return {
            "outcome": approval.outcome,
            "approved": approval.outcome == (approval.options[0] if approval.options else "Aprovar"),
            "responder": approval.decided_by_email,
            "comment": approval.comment or "",
            "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
        }

    def close_approval(self, approval_id: str, status: str) -> None:
        approval = self.session.get(TonAutomationApproval, UUID(approval_id))
        if approval is not None and approval.status == "PENDING":
            approval.status = status
            approval.decided_at = _now()
            self.session.commit()


def _notify_approvers(automation: TonAutomation, approval: TonAutomationApproval) -> None:
    from html import escape

    from onyx.ton.email_flows.transport import OutgoingEmail, TransportError, get_transport

    transport = get_transport()
    if transport is None or not approval.approvers:
        return
    link = f"{WEB_DOMAIN.rstrip('/')}/ton/automacoes?aprovacao={approval.id}"
    details = approval.details or ""
    text = f'A automação "{automation.name}" pede sua decisão: {approval.title}\n\n{details}\n\nResponder no TON: {link}'
    html = (
        '<!doctype html><html lang="pt-BR"><body style="font-family:Arial,sans-serif;color:#1f2937">'
        f"<p>A automação <strong>{escape(automation.name)}</strong> pede sua decisão:</p>"
        f'<p style="font-size:16px"><strong>{escape(approval.title)}</strong></p>'
        + (f'<p style="white-space:pre-line">{escape(details)}</p>' if details else "")
        + f'<p><a href="{escape(link, quote=True)}">Responder no TON</a></p></body></html>'
    )
    try:
        transport.send(OutgoingEmail(list(approval.approvers), [], [], f"Aprovação pendente: {approval.title}"[:300], html, text))
    except TransportError as error:
        logger.warning("TON automation approval e-mail failed: %s", error)


# ---------------------------------------------------------------------------
# Creating and executing runs
# ---------------------------------------------------------------------------


def _reader(session: Session, automation: TonAutomation) -> User | None:
    owner = flow_repository.get_user(session, automation.owner_id)
    if owner is None or not owner.is_active or not repository.can_read(owner):
        return None
    return owner


def _sample_payload(session: Session, trigger_type: str, user: User, inputs: dict[str, Any]) -> dict[str, Any]:
    if trigger_type == "trigger.manual":
        return {"inputs": inputs, "user_email": user.email}
    if trigger_type in ("trigger.ng_import", "trigger.ng_occurrence_changed", "trigger.account_unclassified"):
        review = flow_repository.latest_succeeded_review(session)
        if review is None:
            return {}
        return {"review_run_id": str(review.id), "source_id": str(review.source_id)}
    if trigger_type == "trigger.dre_recalculated":
        today = _now().date().replace(day=1)
        return {"competencias": [today.isoformat()], "unidades": ["consolidado"]}
    if trigger_type == "trigger.automation_failed":
        return {
            "automation_id": "exemplo",
            "automation_name": "Automação de exemplo",
            "run_id": None,
            "error": "Exemplo de erro para teste",
            "link": "/ton/automacoes",
        }
    return {}


_EMPTY_LIST_OUTPUT = {
    "items": [],
    "count": 0,
    "total": 0.0,
    "total_formatado": "R$ 0,00",
    "by_unit": [],
    "note": "Nada mudou na última importação: teste com lista vazia.",
}


def _prepare(
    session: Session,
    automation: TonAutomation,
    definition: AutomationDefinition,
    reader: User | None,
    payload: dict[str, Any],
    now: datetime.datetime,
) -> dict[str, Any] | None:
    spec = get_registry().get(definition.trigger.type)
    if spec is None or spec.prepare is None:
        return {}
    context = TriggerContext(session, reader, now, str(automation.id), automation.name)
    return spec.prepare(context, definition.trigger.params, payload)


def _failed_run(
    session: Session, automation: TonAutomation, version: TonAutomationVersion, key: str, reason: str, now: datetime.datetime
) -> None:
    run = repository.create_run__no_commit(
        session, automation=automation, version=version, trigger_key=key, mode=RunMode.LIVE,
        trigger_output={}, triggered_by=None, now=now,
    )
    if run is None:
        return
    run.status = RunStatus.FAILED.value
    run.error = reason[:1000]
    run.started_at = now
    run.finished_at = now


def start_live_run(
    session: Session,
    automation: TonAutomation,
    version: TonAutomationVersion,
    *,
    key: str,
    payload: dict[str, Any],
    now: datetime.datetime,
) -> TonAutomationRun | None:
    if repository.live_run_exists(session, automation.id, key):
        return None
    reader = _reader(session, automation)
    if reader is None:
        _failed_run(session, automation, version, key, "O responsável pela automação não está ativo ou perdeu o acesso. Reative a automação.", now)
        return None
    definition = _definition(version)
    try:
        output = _prepare(session, automation, definition, reader, payload, now)
    except OnyxError as error:
        _failed_run(session, automation, version, key, f"Falha ao ler os dados do gatilho: {error.detail}", now)
        return None
    except Exception as error:  # noqa: BLE001 - the trigger failure is recorded as a run
        logger.exception("TON automation trigger failed automation_id=%s", automation.id)
        session.rollback()
        _failed_run(session, automation, version, key, f"Falha ao ler os dados do gatilho ({type(error).__name__})", now)
        return None
    if output is None:
        return None
    return repository.create_run__no_commit(
        session, automation=automation, version=version, trigger_key=key, mode=RunMode.LIVE,
        trigger_output=_json_safe(output), triggered_by=None, now=now,
    )


def enqueue(run_ids: list[UUID], *, tenant_id: str | None = None, countdown: float | None = None) -> None:
    """Hand runs to the workers. A lost message is harmless: the tick
    queues every runnable run again."""
    if not run_ids:
        return
    try:
        from onyx.background.celery.versioned_apps.client import app as client_app
        from onyx.configs.constants import OnyxCeleryPriority, OnyxCeleryQueues, OnyxCeleryTask
        from shared_configs.contextvars import get_current_tenant_id

        tenant = tenant_id or get_current_tenant_id()
        for run_id in run_ids:
            client_app.send_task(
                OnyxCeleryTask.TON_AUTOMATION_EXECUTE_RUN,
                kwargs={"run_id": str(run_id), "tenant_id": tenant},
                queue=OnyxCeleryQueues.PRIMARY,
                priority=OnyxCeleryPriority.HIGH,
                countdown=countdown,
            )
    except Exception as error:  # noqa: BLE001 - the tick recovers queued runs
        logger.warning("TON automation enqueue failed, the tick will retry: %s", error)


def _finish(session: Session, run: TonAutomationRun, status: RunStatus, error: str | None, now: datetime.datetime) -> None:
    run.status = status.value
    run.error = error[:1000] if error else None
    run.resume_at = None
    run.waiting_on = None
    run.finished_at = now
    run.lease_until = None
    run.lease_owner = None


def _after_failure(session: Session, automation: TonAutomation, run: TonAutomationRun, definition: AutomationDefinition) -> None:
    if run.mode != RunMode.LIVE.value:
        return
    if definition.trigger.type != "trigger.automation_failed":
        flow_repository.emit_flow_event__no_commit(
            session,
            kind=EVENT_KIND_AUTOMATION_FAILED,
            event_key=str(run.id),
            payload={
                "automation_id": str(automation.id),
                "automation_name": automation.name,
                "run_id": str(run.id),
                "error": run.error,
                "link": _link(automation.id, run.id),
            },
        )
    recipients = definition.settings.notify_on_failure
    if not recipients:
        return
    from html import escape

    from onyx.ton.email_flows.transport import OutgoingEmail, TransportError, get_transport

    transport = get_transport()
    if transport is None:
        return
    link = f"{WEB_DOMAIN.rstrip('/')}{_link(automation.id, run.id)}"
    try:
        transport.send(
            OutgoingEmail(
                list(recipients), [], [],
                f"Falhou: {automation.name}"[:300],
                f'<p>A automação <strong>{escape(automation.name)}</strong> falhou.</p><p>{escape(run.error or "")}</p><p><a href="{escape(link, quote=True)}">Ver a execução</a></p>',
                f"A automação {automation.name} falhou.\n{run.error or ''}\n{link}",
            )
        )
    except TransportError as error:
        logger.warning("TON automation failure e-mail failed: %s", error)


def execute_run(session: Session, run_id: UUID, *, tenant_id: str | None = None) -> RunStatus | None:
    """Run (or continue) one run on this worker. ``None`` when another
    worker holds it or it is not runnable."""
    now = _now()
    run = repository.claim_run__no_commit(session, run_id, WORKER_ID, now)
    session.commit()
    if run is None:
        return None
    automation = repository.get_automation(session, run.automation_id)
    version = session.get(TonAutomationVersion, run.version_id)
    assert version is not None
    definition = _definition(version)
    if now > run.created_at + datetime.timedelta(hours=definition.settings.timeout_hours):
        _finish(session, run, RunStatus.TIMED_OUT, "A execução passou do tempo limite.", now)
        repository.cancel_approvals__no_commit(session, now, run_id=run.id)
        session.commit()
        return RunStatus.TIMED_OUT
    if run.mode in (RunMode.LIVE.value, RunMode.RESUBMIT.value):
        reader = _reader(session, automation)
    else:
        reader = flow_repository.get_user(session, run.triggered_by)
        reader = reader if reader is not None and reader.is_active else None
    if reader is None:
        _finish(session, run, RunStatus.FAILED, "O responsável pela automação não está ativo ou perdeu o acesso.", now)
        _after_failure(session, automation, run, definition)
        session.commit()
        return RunStatus.FAILED
    test_recipient = reader.email if run.mode == RunMode.TEST.value else None
    run_id_text, run_mode = str(run.id), run.mode
    run_info = {
        "id": str(run.id),
        "mode": run.mode,
        "started_at": (run.started_at or now).isoformat(),
        "link": f"{WEB_DOMAIN.rstrip('/')}{_link(automation.id, run.id)}",
    }
    automation_info = {"id": str(automation.id), "name": automation.name, "link": f"{WEB_DOMAIN.rstrip('/')}{_link(automation.id)}"}

    def factory(*, node: Any, iteration: str, attempt: int, scope: dict[str, Any], resolve: Any) -> ActionContext:
        return ActionContext(
            automation_id=str(automation.id),
            automation_name=automation.name,
            run_id=run_id_text,
            mode=run_mode,
            node_id=node.id,
            iteration=iteration,
            attempt=attempt,
            now=_now(),
            scope=scope,
            resolve=resolve,
            timeout_seconds=node.timeout_seconds,
            session=session,
            owner=reader,
            test_recipient=test_recipient,
        )

    interpreter = Interpreter(
        definition,
        store=DbRunStore(session, run, automation),
        trigger_outputs=run.trigger_output or {},
        run_info=run_info,
        automation_info=automation_info,
        env={"ton_url": WEB_DOMAIN.rstrip("/")},
        mode=run.mode,
        now=_now,
        context_factory=factory,
        test_recipient=test_recipient,
    )
    try:
        outcome = interpreter.run()
    except Exception as error:  # noqa: BLE001 - an engine bug fails the run, never the worker
        logger.exception("TON automation run crashed run_id=%s", run.id)
        session.rollback()
        outcome = RunOutcome(RunStatus.FAILED, error=f"Falha interna do motor ({type(error).__name__})")
    run = session.get(TonAutomationRun, run_id, populate_existing=True)
    assert run is not None
    end = _now()
    if run.status == RunStatus.CANCELLED.value:
        run.lease_until = None
        run.lease_owner = None
        session.commit()
        return RunStatus.CANCELLED
    if outcome.status is RunStatus.WAITING:
        run.status = RunStatus.WAITING.value
        run.resume_at = outcome.resume_at
        run.waiting_on = outcome.waiting_on
        run.lease_until = None
        run.lease_owner = None
        run.message = {
            "wait": "Esperando o momento de continuar",
            "approval": "Aguardando aprovação",
            "retry": "Vai tentar de novo",
        }.get(outcome.waiting_on or "", "Esperando")
        session.commit()
        if outcome.resume_at is not None and outcome.resume_at - end <= datetime.timedelta(minutes=5):
            enqueue([run.id], tenant_id=tenant_id, countdown=max(1.0, (outcome.resume_at - end).total_seconds() + 1))
        return RunStatus.WAITING
    _finish(session, run, outcome.status, outcome.error, end)
    run.message = outcome.message
    if outcome.status is RunStatus.CANCELLED:
        repository.cancel_approvals__no_commit(session, end, run_id=run.id)
    if run.mode != RunMode.TEST.value:
        repository.audit(
            session,
            None,
            AuditAction.TON_AUTOMATION_RUN,
            automation,
            {"run_id": str(run.id), "status": run.status, "mode": run.mode},
            outcome=AuditOutcome.SUCCESS if outcome.status is RunStatus.SUCCEEDED else AuditOutcome.FAILURE,
        )
    if outcome.status is RunStatus.FAILED:
        _after_failure(session, automation, run, definition)
    session.commit()
    return outcome.status


# ---------------------------------------------------------------------------
# Tick
# ---------------------------------------------------------------------------


def _event_trigger_types() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for spec in get_registry().values():
        for kind in spec.event_kinds:
            mapping.setdefault(kind, []).append(spec.type)
    return mapping


def process_events(session: Session, now: datetime.datetime) -> list[UUID]:
    created: list[UUID] = []
    by_kind = _event_trigger_types()
    for event in flow_repository.claim_pending_events(session, now):
        for automation, version in repository.active_by_trigger(session, by_kind.get(event.kind, [])):
            if automation.active_since is None or automation.active_since > event.created_at:
                continue
            run = start_live_run(
                session, automation, version, key=f"{event.kind}:{event.event_key}", payload=dict(event.payload), now=now
            )
            if run is not None:
                created.append(run.id)
        event.processed_at = now
    session.commit()
    return created


def dispatch_schedules(session: Session, now: datetime.datetime) -> list[UUID]:
    created: list[UUID] = []
    for automation, version in repository.active_by_trigger(session, ["trigger.schedule"]):
        params = _definition(version).trigger.params
        try:
            slot = recurrence.latest_slot(params, now)
            grace = recurrence.grace(params)
        except ValueError:
            continue
        if slot is None or automation.active_since is None or slot <= automation.active_since or now - slot > grace:
            continue
        run = start_live_run(
            session, automation, version, key=f"schedule:{slot.isoformat()}", payload={"scheduled_for": slot.isoformat()}, now=now
        )
        session.commit()
        if run is not None:
            created.append(run.id)
    return created


def expire_runs(session: Session, now: datetime.datetime) -> None:
    cutoffs: dict[UUID, datetime.datetime] = {}
    for automation, version in repository.list_automations(session, include_archived=True):
        hours = _definition(version).settings.timeout_hours
        cutoffs[automation.id] = now - datetime.timedelta(hours=hours)
    for run in repository.open_runs_started_before(session, cutoffs):
        _finish(session, run, RunStatus.TIMED_OUT, "A execução passou do tempo limite.", now)
        repository.cancel_approvals__no_commit(session, now, run_id=run.id)
    session.commit()


def tick(session: Session, *, tenant_id: str | None = None) -> int:
    now = _now()
    ensure_defaults(session)
    created = process_events(session, now)
    created += dispatch_schedules(session, now)
    expire_runs(session, now)
    runnable = repository.runnable_run_ids(session, now)
    stale_queued = [
        run_id
        for run_id in runnable
        if run_id not in created
    ]
    enqueue(list(dict.fromkeys(created + stale_queued)), tenant_id=tenant_id)
    return len(created)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def _duration(start: datetime.datetime | None, end: datetime.datetime | None) -> int | None:
    if start is None or end is None:
        return None
    return int((end - start).total_seconds() * 1000)


def _run_summary(run: TonAutomationRun, versions: dict[UUID, int], emails: dict[UUID, str]) -> RunSummary:
    return RunSummary(
        id=run.id,
        status=RunStatus(run.status),
        mode=RunMode(run.mode),
        trigger_key=run.trigger_key,
        version=versions.get(run.version_id),
        error=run.error,
        message=run.message,
        waiting_on=run.waiting_on,
        resume_at=run.resume_at,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=_duration(run.started_at or run.created_at, run.finished_at),
        triggered_by=emails.get(run.triggered_by) if run.triggered_by else None,
    )


def _version_numbers(session: Session, runs: list[TonAutomationRun]) -> dict[UUID, int]:
    import sqlalchemy as sa

    ids = list({run.version_id for run in runs})
    if not ids:
        return {}
    return dict(session.execute(sa.select(TonAutomationVersion.id, TonAutomationVersion.version).where(TonAutomationVersion.id.in_(ids))).all())  # type: ignore[arg-type]


def _when(definition: AutomationDefinition) -> tuple[str, str]:
    spec = get_registry().get(definition.trigger.type)
    label = spec.label if spec else definition.trigger.type
    if definition.trigger.type == "trigger.schedule":
        try:
            return label, recurrence.describe(definition.trigger.params)
        except ValueError:
            return label, label
    return label, label


def _summary(
    automation: TonAutomation,
    version: TonAutomationVersion,
    runs: list[TonAutomationRun],
    counts: dict[str, int],
    versions: dict[UUID, int],
    emails: dict[UUID, str],
) -> AutomationSummary:
    definition = _definition(version)
    label, when = _when(definition)
    last = next((run for run in runs if run.mode != RunMode.TEST.value), None)
    next_run = None
    if automation.status == AutomationStatus.ACTIVE.value and definition.trigger.type == "trigger.schedule":
        try:
            next_run = recurrence.next_slot(definition.trigger.params, _now())
        except ValueError:
            next_run = None
    return AutomationSummary(
        id=automation.id,
        name=automation.name,
        description=automation.description,
        kind=AutomationKind(automation.kind),
        status=AutomationStatus(automation.status),
        origin=AutomationOrigin(automation.origin),
        trigger_type=definition.trigger.type,
        trigger_label=label,
        when=when,
        version=automation.current_version,
        steps_count=sum(1 for _ in iter_nodes(definition.steps)),
        last_run=_run_summary(last, versions, emails) if last else None,
        next_run_at=next_run,
        runs_28d=counts,
        problems=activation_problems(definition, AutomationKind(automation.kind)),
        suggestion_reason=automation.suggestion_reason,
        updated_at=automation.updated_at,
    )


def _can_decide(user: User, approval: TonAutomationApproval) -> bool:
    return approval.status == "PENDING" and (
        (user.email or "").lower() in [a.lower() for a in approval.approvers] or repository.can_manage(user)
    )


def _approval_view(approval: TonAutomationApproval, name: str, user: User) -> ApprovalView:
    return ApprovalView(
        id=approval.id,
        automation_id=approval.automation_id,
        automation_name=name,
        run_id=approval.run_id,
        node_id=approval.node_id,
        title=approval.title,
        details=approval.details,
        options=list(approval.options),
        approvers=list(approval.approvers),
        status=approval.status,
        outcome=approval.outcome,
        comment=approval.comment,
        decided_by=approval.decided_by_email,
        decided_at=approval.decided_at,
        expires_at=approval.expires_at,
        created_at=approval.created_at,
        can_decide=_can_decide(user, approval),
    )


def table(session: Session, user: User) -> AutomationTable:
    from onyx.ton.email_flows.transport import get_transport

    repository.require_read(user)
    ensure_defaults(session)
    rows = repository.list_automations(session)
    ids = [automation.id for automation, _ in rows]
    runs = repository.runs_for(session, ids, per_automation=6)
    all_runs = [run for listed in runs.values() for run in listed]
    versions = _version_numbers(session, all_runs)
    emails = repository.user_emails(session, [run.triggered_by for run in all_runs])
    counts = repository.run_counts(session, ids, _now() - datetime.timedelta(days=HISTORY_DAYS))
    return AutomationTable(
        automations=[
            _summary(automation, version, runs.get(automation.id, []), counts.get(automation.id, {}), versions, emails)
            for automation, version in rows
        ],
        approvals=[_approval_view(approval, automation.name, user) for approval, automation in repository.pending_approvals(session)],
        can_manage=repository.can_manage(user),
        provider_ready=get_transport() is not None,
    )


def detail(session: Session, user: User, automation_id: UUID) -> AutomationDetail:
    repository.require_read(user)
    automation = repository.get_automation(session, automation_id)
    version = repository.current_version(session, automation)
    since = _now() - datetime.timedelta(days=HISTORY_DAYS)
    runs = repository.runs_for(session, [automation.id], per_automation=100, since=since).get(automation.id, [])
    counts = repository.run_counts(session, [automation.id], since).get(automation.id, {})
    history = repository.versions(session, automation.id)
    emails = repository.user_emails(
        session,
        [automation.owner_id, automation.created_by, automation.updated_by, *[run.triggered_by for run in runs], *[v.created_by for v in history]],
    )
    versions = _version_numbers(session, runs)
    definition = _definition(version)
    summary = _summary(automation, version, runs, counts, versions, emails)
    finished = [
        run for run in runs
        if run.status == RunStatus.SUCCEEDED.value and run.started_at and run.finished_at and run.mode != RunMode.TEST.value
    ]
    average = int(sum(_duration(r.started_at, r.finished_at) or 0 for r in finished) / len(finished)) if finished else None
    return AutomationDetail(
        **summary.model_dump(),
        definition=definition,
        issues=[IssueView(**issue.dump()) for issue in validate(definition)],
        owner=emails.get(automation.owner_id) if automation.owner_id else None,
        created_by=emails.get(automation.created_by) if automation.created_by else None,
        updated_by=emails.get(automation.updated_by) if automation.updated_by else None,
        created_at=automation.created_at,
        active_since=automation.active_since,
        versions=[
            VersionView(version=v.version, name=v.name, note=v.note, created_by=emails.get(v.created_by) if v.created_by else None, created_at=v.created_at)
            for v in history
        ],
        runs=[_run_summary(run, versions, emails) for run in runs],
        can_manage=repository.can_manage(user),
        average_duration_ms=average,
    )


def run_detail(session: Session, user: User, run_id: UUID) -> RunDetail:
    import sqlalchemy as sa

    repository.require_read(user)
    run = repository.get_run(session, run_id)
    automation = repository.get_automation(session, run.automation_id)
    version = session.get(TonAutomationVersion, run.version_id)
    assert version is not None
    steps = repository.step_rows(session, run.id)
    approvals = list(
        session.scalars(sa.select(TonAutomationApproval).where(TonAutomationApproval.run_id == run.id).order_by(TonAutomationApproval.created_at))
    )
    emails = repository.user_emails(session, [run.triggered_by])
    summary = _run_summary(run, {version.id: version.version}, emails)
    return RunDetail(
        **summary.model_dump(),
        automation_id=automation.id,
        automation_name=automation.name,
        definition=_definition(version),
        trigger_output=run.trigger_output or {},
        steps=[_step_view(step) for step in steps],
        approvals=[_approval_view(approval, automation.name, user) for approval in approvals],
        can_cancel=run.status in (RunStatus.QUEUED.value, RunStatus.RUNNING.value, RunStatus.WAITING.value) and repository.can_manage(user),
        can_resubmit=RunStatus(run.status) in FINAL_RUN_STATUSES and repository.can_manage(user),
    )


def _step_view(step: TonAutomationStepRun) -> StepView:
    return StepView(
        node_id=step.node_id,
        iteration=step.iteration,
        node_type=step.node_type,
        status=StepStatus(step.status),
        attempt=step.attempt,
        inputs=step.inputs,
        outputs=step.outputs,
        error=step.error,
        started_at=step.started_at,
        finished_at=step.finished_at,
        next_retry_at=step.next_retry_at,
        duration_ms=_duration(step.started_at, step.finished_at),
    )


def notices(session: Session, user: User) -> list[NoticeView]:
    repository.require_read(user)
    return [
        NoticeView(
            id=notice.id,
            automation_id=notice.automation_id,
            automation_name=name,
            run_id=notice.run_id,
            title=notice.title,
            message=notice.message,
            severity=notice.severity,
            link=notice.link,
            created_at=notice.created_at,
        )
        for notice, name in repository.recent_notices(session)
    ]


def approvals_for(session: Session, user: User) -> list[ApprovalView]:
    repository.require_read(user)
    return [_approval_view(approval, automation.name, user) for approval, automation in repository.pending_approvals(session)]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _clean(definition: AutomationDefinition) -> AutomationDefinition:
    for node in iter_nodes(definition.steps):
        if node.type == "email.send" and isinstance(node.params.get("body"), str):
            node.params["body"] = sanitize(node.params["body"])
    return definition


def _blank() -> AutomationDefinition:
    return AutomationDefinition.model_validate({"schema": 3, "trigger": {"type": "trigger.manual", "params": {}}, "steps": []})


def _require_ready(definition: AutomationDefinition, kind: AutomationKind) -> None:
    problems = activation_problems(definition, kind)
    if problems:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Corrija antes de ativar: " + "; ".join(problems[:6]))


def create(session: Session, user: User, request: AutomationCreate) -> AutomationDetail:
    repository.require_manage(user)
    kind = request.kind
    if request.template:
        template = next((t for t in TEMPLATES if t.key == request.template), None)
        if template is None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Modelo não encontrado")
        definition = AutomationDefinition.model_validate(template.definition)
        kind = template.kind
    else:
        definition = request.definition or _blank()
    automation = repository.create__no_commit(
        session,
        user,
        name=request.name.strip(),
        description=(request.description or "").strip() or None,
        kind=kind,
        definition=_clean(definition),
        origin=AutomationOrigin.USER,
        status=AutomationStatus.DRAFT,
        now=_now(),
    )
    session.commit()
    return detail(session, user, automation.id)


def update(session: Session, user: User, automation_id: UUID, request: AutomationUpdate) -> AutomationDetail:
    repository.require_manage(user)
    automation = repository.get_automation(session, automation_id)
    definition = _clean(request.definition)
    if automation.status == AutomationStatus.ACTIVE.value:
        _require_ready(definition, request.kind)
    repository.add_version__no_commit(
        session, user, automation,
        name=request.name.strip(),
        description=(request.description or "").strip() or None,
        kind=request.kind,
        definition=definition,
        now=_now(),
        note=request.note,
    )
    session.commit()
    return detail(session, user, automation.id)


def restore_version(session: Session, user: User, automation_id: UUID, version: int) -> AutomationDetail:
    repository.require_manage(user)
    automation = repository.get_automation(session, automation_id)
    old = repository.get_version(session, automation_id, version)
    definition = _definition(old)
    if automation.status == AutomationStatus.ACTIVE.value:
        _require_ready(definition, AutomationKind(automation.kind))
    repository.add_version__no_commit(
        session, user, automation, name=old.name, description=automation.description,
        kind=AutomationKind(automation.kind), definition=definition, now=_now(), note=f"Restaurada da versão {version}",
    )
    session.commit()
    return detail(session, user, automation.id)


def _cancel_open_runs(session: Session, automation_id: UUID, now: datetime.datetime) -> None:
    import sqlalchemy as sa

    session.execute(
        sa.update(TonAutomationRun)
        .where(
            TonAutomationRun.automation_id == automation_id,
            TonAutomationRun.status.in_([RunStatus.QUEUED.value, RunStatus.WAITING.value]),
        )
        .values(status=RunStatus.CANCELLED.value, finished_at=now, message="Cancelada: automação pausada", resume_at=None)
    )
    repository.cancel_approvals__no_commit(session, now, automation_id=automation_id)


def change_status(session: Session, user: User, automation_id: UUID, status: AutomationStatus) -> AutomationDetail:
    repository.require_manage(user)
    automation = repository.get_automation(session, automation_id)
    now = _now()
    if status is AutomationStatus.ACTIVE:
        _require_ready(_definition(repository.current_version(session, automation)), AutomationKind(automation.kind))
    repository.set_status__no_commit(session, user, automation, status, now)
    if status in (AutomationStatus.PAUSED, AutomationStatus.ARCHIVED):
        _cancel_open_runs(session, automation.id, now)
    session.commit()
    return detail(session, user, automation.id)


def duplicate(session: Session, user: User, automation_id: UUID) -> AutomationDetail:
    repository.require_manage(user)
    automation = repository.get_automation(session, automation_id)
    version = repository.current_version(session, automation)
    copy = repository.create__no_commit(
        session, user,
        name=f"{automation.name} (cópia)"[:120],
        description=automation.description,
        kind=AutomationKind(automation.kind),
        definition=_definition(version),
        origin=AutomationOrigin.USER,
        status=AutomationStatus.DRAFT,
        now=_now(),
    )
    session.commit()
    return detail(session, user, copy.id)


def start_manual(
    session: Session, user: User, automation_id: UUID, inputs: dict[str, Any], *, test: bool
) -> RunSummary:
    """"Executar" (real effects) or "Testar" (e-mails only to the person,
    waits skipped, approvals auto-approved). Event triggers use the latest
    NG import as sample data."""
    repository.require_manage(user)
    automation = repository.get_automation(session, automation_id)
    version = repository.current_version(session, automation)
    definition = _definition(version)
    errors = [issue for issue in validate(definition) if issue.severity == "error"]
    if errors:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Corrija antes de executar: " + "; ".join(i.message for i in errors[:5]))
    now = _now()
    payload = _sample_payload(session, definition.trigger.type, user, inputs)
    try:
        output = _prepare(session, automation, definition, user, payload, now)
    except ValueError as error:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, str(error)) from None
    if output is None:
        output = dict(_EMPTY_LIST_OUTPUT)
    mode = RunMode.TEST if test else RunMode.MANUAL
    run = repository.create_run__no_commit(
        session, automation=automation, version=version, trigger_key=f"{mode.value.lower()}:{now.isoformat()}",
        mode=mode, trigger_output=_json_safe(output), triggered_by=user.id, now=now,
    )
    assert run is not None
    repository.audit(session, user, AuditAction.TON_AUTOMATION_RUN, automation, {"run_id": str(run.id), "mode": mode.value, "change": "started"})
    session.commit()
    enqueue([run.id])
    return _run_summary(run, {version.id: version.version}, {user.id: user.email})


def resubmit(session: Session, user: User, run_id: UUID) -> RunSummary:
    repository.require_manage(user)
    original = repository.get_run(session, run_id)
    automation = repository.get_automation(session, original.automation_id)
    version = repository.current_version(session, automation)
    now = _now()
    run = repository.create_run__no_commit(
        session, automation=automation, version=version, trigger_key=f"resubmit:{original.id}:{now.isoformat()}",
        mode=RunMode.TEST if original.mode == RunMode.TEST.value else RunMode.RESUBMIT,
        trigger_output=original.trigger_output or {}, triggered_by=user.id, now=now, resubmitted_from=original.id,
    )
    assert run is not None
    repository.audit(session, user, AuditAction.TON_AUTOMATION_RUN, automation, {"run_id": str(run.id), "resubmitted_from": str(original.id)})
    session.commit()
    enqueue([run.id])
    return _run_summary(run, {version.id: version.version}, {user.id: user.email})


def cancel(session: Session, user: User, run_id: UUID) -> RunSummary:
    repository.require_manage(user)
    run = repository.get_run(session, run_id)
    if RunStatus(run.status) in FINAL_RUN_STATUSES:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Esta execução já terminou")
    now = _now()
    run.status = RunStatus.CANCELLED.value
    run.finished_at = now
    run.resume_at = None
    run.message = f"Cancelada por {user.email}"
    repository.cancel_approvals__no_commit(session, now, run_id=run.id)
    automation = repository.get_automation(session, run.automation_id)
    repository.audit(session, user, AuditAction.TON_AUTOMATION_RUN, automation, {"run_id": str(run.id), "change": "cancelled"})
    session.commit()
    return _run_summary(run, {}, {})


def decide(session: Session, user: User, approval_id: UUID, outcome: str, comment: str | None) -> ApprovalView:
    repository.require_read(user)
    approval = repository.get_approval(session, approval_id)
    if approval.status != "PENDING":
        raise OnyxError(OnyxErrorCode.CONFLICT, "Esta aprovação já foi respondida")
    if not _can_decide(user, approval):
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, "Você não está entre as pessoas que aprovam")
    if outcome not in approval.options:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Resposta fora das opções")
    now = _now()
    approval.status = "DONE"
    approval.outcome = outcome
    approval.comment = comment
    approval.decided_by = user.id
    approval.decided_by_email = user.email
    approval.decided_at = now
    run = repository.get_run(session, approval.run_id)
    automation = repository.get_automation(session, approval.automation_id)
    if run.status == RunStatus.WAITING.value:
        run.status = RunStatus.QUEUED.value
        run.resume_at = None
    repository.audit(session, user, AuditAction.TON_AUTOMATION_CHANGE, automation, {"change": "approval", "outcome": outcome, "run_id": str(run.id), "comment": comment})
    session.commit()
    enqueue([run.id])
    return _approval_view(approval, automation.name, user)


def check(session: Session, user: User, raw: dict[str, Any], kind: AutomationKind) -> ValidateResult:
    repository.require_read(user)
    try:
        definition = AutomationDefinition.model_validate(raw)
    except ValidationError as error:
        first = error.errors()[0]
        message = str(first.get("msg", "inválido")).removeprefix("Value error, ")
        location = ".".join(str(part) for part in first.get("loc", ()))
        # Rule errors (ids, variables, limits) already say where; field errors need the path.
        return ValidateResult(issues=[], problems=[], structure_error=f"{location}: {message}" if location else message)
    return ValidateResult(
        issues=[IssueView(**issue.dump()) for issue in validate(definition)],
        problems=activation_problems(definition, kind),
        suggested_kind=suggest_kind(definition),
    )


def preview(session: Session, user: User, request: PreviewRequest) -> PreviewResult:
    """Render an e-mail step with today's data: the flow runs as a dry run
    (no e-mail, HTTP, notice or AI call) up to that step."""
    from onyx.ton.automations.nodes.email import preview_html

    repository.require_read(user)
    definition = _clean(request.definition)
    now = _now()
    automation = repository.get_automation(session, request.automation_id) if request.automation_id else None
    name = request.name or (automation.name if automation else "Automação")
    payload = _sample_payload(session, definition.trigger.type, user, {})
    fake = TonAutomation(id=automation.id if automation else UUID(int=0), name=name)
    try:
        output = _prepare(session, fake, definition, user, payload, now)
    except ValueError:
        output = {}
    if output is None:
        output = dict(_EMPTY_LIST_OUTPUT)
    captured: dict[str, Any] = {}

    def on_stop(node: Any, spec: NodeSpec, context: ActionContext, inputs: dict[str, Any]) -> None:
        if node.type == "email.send":
            raw = {**inputs, "body": node.params.get("body", "")}
            captured.update(preview_html(context, raw))
        else:
            captured["inputs"] = inputs

    def factory(*, node: Any, iteration: str, attempt: int, scope: dict[str, Any], resolve: Any) -> ActionContext:
        return ActionContext(
            automation_id=str(fake.id), automation_name=name, run_id="", mode="TEST", node_id=node.id,
            iteration=iteration, attempt=attempt, now=now, scope=scope, resolve=resolve, session=session, owner=user,
            test_recipient=user.email,
        )

    interpreter = Interpreter(
        definition,
        store=MemoryStore(),
        trigger_outputs=_json_safe(output),
        run_info={"id": "previa", "mode": "TEST"},
        automation_info={"id": str(fake.id), "name": name},
        env={"ton_url": WEB_DOMAIN.rstrip("/")},
        mode="TEST",
        context_factory=factory,
        test_recipient=user.email,
        dry_run=True,
        stop_at=request.node_id,
        on_stop=on_stop,
    )
    try:
        outcome = interpreter.run()
    except StopAtNode:
        session.rollback()
        return PreviewResult(
            subject=captured.get("subject"),
            html=captured.get("html"),
            reason="Prévia com os dados de hoje. Passos de IA e envios externos aparecem como exemplo.",
            outputs_sample={key: value for key, value in captured.items() if key not in ("html",)},
        )
    target = find_node(definition.steps, request.node_id)
    spec = get_registry().get(target.type) if target else None
    if target is not None and spec is not None and target.type == "email.send":
        # Not reached today: render it anyway with what the run produced.
        scope = interpreter.scope(_Frame())
        inputs: dict[str, Any] = {}
        for param in spec.params:
            raw = target.params.get(param.key, param.default)
            try:
                inputs[param.key] = render(raw, scope) if param.resolve else raw
            except ExpressionError:
                inputs[param.key] = None
        context = factory(node=target, iteration="", attempt=1, scope=scope, resolve=lambda value, extra=None: render(value, {**scope, **(extra or {})}))
        try:
            email = preview_html(context, inputs)
        except Exception:  # noqa: BLE001 - a preview never fails the editor
            email = {}
        session.rollback()
        prefix = (
            f"A simulação parou antes ({outcome.error}). " if outcome.status is RunStatus.FAILED else "Com os dados de hoje este e-mail não seria enviado. "
        )
        return PreviewResult(subject=email.get("subject"), html=email.get("html"), reason=f"{prefix}Prévia com os dados disponíveis.")
    session.rollback()
    if outcome.status is RunStatus.FAILED:
        return PreviewResult(subject=None, html=None, reason=f"A simulação parou antes deste passo: {outcome.error}")
    return PreviewResult(subject=None, html=None, reason="Com os dados de hoje, a execução não chega a este passo.")


def upload_file(session: Session, user: User, name: str, content_type: str, data: bytes) -> FileView:
    repository.require_manage(user)
    if len(data) > MAX_FILE_BYTES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Arquivo maior que 5 MB")
    if not name.lower().endswith(FILE_TYPES):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Tipo de arquivo não aceito (Excel, CSV, JSON, TXT, PDF ou Word)")
    stored = repository.create_file__no_commit(session, user, name=name, content_type=content_type or "application/octet-stream", data=data)
    session.commit()
    return FileView(id=stored.id, name=stored.name, size_bytes=stored.size_bytes)


def step_html(session: Session, user: User, run_id: UUID, node_id: str, iteration: str) -> str:
    repository.require_read(user)
    step = repository.get_step(session, run_id, node_id, iteration)
    if step is None or not isinstance((step.outputs or {}).get("html"), str):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Este passo não tem e-mail")
    return str(step.outputs["html"]).replace('src="cid:asset-', 'src="/api/ton/email-flows/assets/')  # type: ignore[index]
