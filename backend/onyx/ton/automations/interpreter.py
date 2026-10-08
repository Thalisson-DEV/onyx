"""Durable interpreter of automation definitions.

Every node execution is a ``StepRecord`` saved through a ``RunStore`` (one
row per node and loop iteration). A run is executed by walking the tree from
the top each time: steps already finished are *replayed* from their record
(outputs, variable changes, the branch a condition took, the list a loop
iterated), so a run can stop at any point — a wait, an approval, a retry
delay, a worker crash — and continue later with the same result.

Side-effect steps (e-mail, HTTP, notices) run at most once: a record found
``RUNNING`` on replay means a worker stopped in the middle, and the step is
failed as interrupted instead of being repeated.
"""

import datetime
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from onyx.ton.automations.conditions import evaluate_group, parse_group
from onyx.ton.automations.definition import (
    FINAL_STEP_STATUSES,
    RUN_AFTER_OF,
    AutomationDefinition,
    Node,
    RetryPolicy,
    RunStatus,
    StepStatus,
)
from onyx.ton.automations.expressions import (
    ExpressionError,
    render,
    to_number,
    to_text,
)
from onyx.ton.automations.registry import (
    ActionContext,
    ActionError,
    NodeSpec,
    get_registry,
)

MAX_LOOP_ITEMS = 500
MAX_UNTIL_ITERATIONS = 100
INLINE_RETRY_SECONDS = 5
MAX_OUTPUT_BYTES = 4_000_000
MAX_INPUT_PREVIEW_CHARS = 4000


@dataclass
class StepRecord:
    node_id: str
    iteration: str
    node_type: str
    status: StepStatus
    attempt: int = 0
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    # Retry time, wait end or approval deadline.
    next_retry_at: datetime.datetime | None = None


@dataclass(frozen=True)
class ApprovalRequest:
    node_id: str
    iteration: str
    approvers: list[str]
    title: str
    details: str
    options: list[str]
    expires_at: datetime.datetime | None


class RunStore(Protocol):
    def load(self) -> dict[tuple[str, str], StepRecord]: ...

    def save(self, record: StepRecord) -> None: ...

    def cancelled(self) -> bool: ...

    def heartbeat(self) -> None: ...

    def open_approval(self, record: StepRecord, request: ApprovalRequest) -> str: ...

    def approval_result(self, approval_id: str) -> dict[str, Any] | None: ...

    def close_approval(self, approval_id: str, status: str) -> None: ...


@dataclass
class RunOutcome:
    status: RunStatus
    resume_at: datetime.datetime | None = None
    error: str | None = None
    waiting_on: str | None = None
    message: str | None = None


@dataclass
class _Frame:
    iteration: str = ""
    item: Any = None
    loops: dict[str, Any] = field(default_factory=dict)

    def child(self, loop_id: str, index: int, item: Any, count: int) -> "_Frame":
        return _Frame(
            iteration=f"{self.iteration}/{loop_id}[{index}]",
            item=item,
            loops={**self.loops, loop_id: {"item": item, "index": index, "count": count}},
        )


class _Suspend(Exception):
    def __init__(self, resume_at: datetime.datetime | None, waiting_on: str) -> None:
        self.resume_at = resume_at
        self.waiting_on = waiting_on


class _Terminate(Exception):
    def __init__(self, status: str, message: str) -> None:
        self.status = status
        self.message = message


class _Cancelled(Exception):
    pass


class StopAtNode(Exception):
    """Dry run reached ``stop_at``."""


def _placeholder(spec: NodeSpec) -> dict[str, Any]:
    """Outputs of an AI or external step during a dry run."""
    values: dict[str, Any] = {}
    for output in spec.outputs:
        if output.type == "string":
            values[output.key] = f"[{output.label}: preenchido na execução]"
        elif output.type == "number":
            values[output.key] = 0
        elif output.type == "boolean":
            values[output.key] = True
        elif output.type == "array":
            values[output.key] = []
        else:
            values[output.key] = {}
    return {**values, "simulado": True}


def _compact(value: Any, limit: int = MAX_INPUT_PREVIEW_CHARS) -> Any:
    """A display copy of resolved inputs: long text and lists are cut."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "…"
    if isinstance(value, list):
        head = [_compact(entry, limit // 4) for entry in value[:20]]
        return head + ([f"… +{len(value) - 20} itens"] if len(value) > 20 else [])
    if isinstance(value, dict):
        return {key: _compact(entry, limit // 2) for key, entry in list(value.items())[:60]}
    return value


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def coerce_variable(kind: str, value: Any) -> Any:
    if kind == "number":
        return to_number(value) or 0
    if kind == "boolean":
        return value if isinstance(value, bool) else to_text(value).strip().casefold() in ("true", "sim", "1")
    if kind == "array":
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value.strip().startswith("["):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                return [value]
        return [] if value in (None, "") else [value]
    if kind == "object":
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip().startswith("{"):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}
    return "" if value is None else value if isinstance(value, str) else to_text(value)


class Interpreter:
    def __init__(
        self,
        definition: AutomationDefinition,
        *,
        store: RunStore,
        trigger_outputs: dict[str, Any],
        run_info: dict[str, Any],
        automation_info: dict[str, Any],
        env: dict[str, Any] | None = None,
        mode: str = "LIVE",
        now: Callable[[], datetime.datetime] = lambda: datetime.datetime.now(datetime.UTC),
        sleep: Callable[[float], None] = time.sleep,
        context_factory: Callable[..., ActionContext] | None = None,
        test_recipient: str | None = None,
        dry_run: bool = False,
        stop_at: str | None = None,
        on_stop: Callable[[Node, NodeSpec, ActionContext, dict[str, Any]], None] | None = None,
    ) -> None:
        self.definition = definition
        self.store = store
        self.registry = get_registry()
        self.mode = mode
        self.now = now
        self.sleep = sleep
        self.context_factory = context_factory
        self.test_recipient = test_recipient
        # Dry run (designer previews): external effects and AI calls are
        # replaced by placeholders; ``stop_at`` hands that node to ``on_stop``.
        self.dry_run = dry_run
        self.stop_at = stop_at
        self.on_stop = on_stop
        self.records = store.load()
        self.trigger = {"outputs": trigger_outputs, "type": definition.trigger.type}
        self.steps: dict[str, Any] = {}
        self.vars: dict[str, Any] = {
            variable.name: coerce_variable(variable.type, render(variable.value, {"env": env or {}, "run": run_info, "automation": automation_info, "trigger": self.trigger}))
            for variable in definition.variables
        }
        self.var_types = {variable.name: variable.type for variable in definition.variables}
        self.run_info = run_info
        self.automation_info = automation_info
        self.env = env or {}
        self.first_error: str | None = None
        self.executed = 0

    # -- public ------------------------------------------------------------

    def run(self) -> RunOutcome:
        try:
            outcome = self._run_list(self.definition.steps, _Frame())
        except _Suspend as suspended:
            return RunOutcome(RunStatus.WAITING, suspended.resume_at, None, suspended.waiting_on)
        except _Terminate as terminated:
            status = {
                "succeeded": RunStatus.SUCCEEDED,
                "failed": RunStatus.FAILED,
                "cancelled": RunStatus.CANCELLED,
            }.get(terminated.status, RunStatus.FAILED)
            return RunOutcome(
                status,
                error=terminated.message if status is RunStatus.FAILED else None,
                message=terminated.message or None,
            )
        except _Cancelled:
            return RunOutcome(RunStatus.CANCELLED, message="Execução cancelada")
        if outcome in (StepStatus.FAILED, StepStatus.TIMED_OUT):
            return RunOutcome(RunStatus.FAILED, error=self.first_error or "Um passo falhou")
        return RunOutcome(RunStatus.SUCCEEDED)

    # -- scope -------------------------------------------------------------

    def scope(self, frame: _Frame, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        values = {
            "trigger": self.trigger,
            "steps": self.steps,
            "vars": self.vars,
            "item": frame.item,
            "loop": frame.loops,
            "run": self.run_info,
            "automation": self.automation_info,
            "env": self.env,
        }
        if extra:
            values.update(extra)
        return values

    # -- lists ---------------------------------------------------------------

    def _run_list(self, nodes: list[Node], frame: _Frame) -> StepStatus:
        previous = StepStatus.SUCCEEDED
        outcome = StepStatus.SUCCEEDED
        for node in nodes:
            status = self._run_node(node, frame, previous)
            previous = status
            if status in (StepStatus.FAILED, StepStatus.TIMED_OUT, StepStatus.CANCELLED):
                outcome = StepStatus.FAILED if status is StepStatus.CANCELLED else status
            elif status is StepStatus.SUCCEEDED:
                outcome = StepStatus.SUCCEEDED
        return outcome

    def _publish(self, node: Node, record: StepRecord) -> None:
        self.steps[node.id] = {
            "status": RUN_AFTER_OF.get(record.status, "failed"),
            "outputs": record.outputs or {},
            "error": record.error,
        }
        spec = self.registry.get(node.type)
        if (
            spec is not None
            and spec.group == "variables"
            and record.status is StepStatus.SUCCEEDED
            and record.outputs is not None
            and "name" in (record.inputs or {})
        ):
            self.vars[str((record.inputs or {})["name"])] = record.outputs.get("value")

    def _save(self, record: StepRecord) -> None:
        self.records[(record.node_id, record.iteration)] = record
        self.store.save(record)

    def _fail(self, node: Node, record: StepRecord, message: str, status: StepStatus = StepStatus.FAILED) -> StepStatus:
        record.status = status
        record.error = message[:2000]
        record.finished_at = self.now()
        record.next_retry_at = None
        self._save(record)
        self._publish(node, record)
        if self.first_error is None:
            self.first_error = f"{node.label or node.id}: {message}"[:1000]
        return status

    def _succeed(self, node: Node, record: StepRecord, outputs: dict[str, Any]) -> StepStatus:
        safe = _json_safe(outputs)
        if len(json.dumps(safe, ensure_ascii=False)) > MAX_OUTPUT_BYTES:
            return self._fail(node, record, "A saída deste passo é grande demais (limite 4 MB)")
        record.status = StepStatus.SUCCEEDED
        record.outputs = safe
        record.error = None
        record.finished_at = self.now()
        record.next_retry_at = None
        self._save(record)
        self._publish(node, record)
        return StepStatus.SUCCEEDED

    # -- nodes ---------------------------------------------------------------

    def _run_node(self, node: Node, frame: _Frame, previous: StepStatus) -> StepStatus:
        key = (node.id, frame.iteration)
        record = self.records.get(key)
        spec = self.registry.get(node.type)
        if spec is None:
            record = record or StepRecord(node.id, frame.iteration, node.type, StepStatus.RUNNING, started_at=self.now())
            return self._fail(node, record, f"Tipo de passo desconhecido: {node.type}")
        if RUN_AFTER_OF.get(previous, "failed") not in node.run_after:
            if record is None or record.status is not StepStatus.SKIPPED:
                record = StepRecord(
                    node.id, frame.iteration, node.type, StepStatus.SKIPPED,
                    started_at=self.now(), finished_at=self.now(),
                )
                self._save(record)
            self._publish(node, record)
            return StepStatus.SKIPPED
        if spec.container is not None:
            return self._run_container(node, spec, frame, record)
        if record is not None and record.status in FINAL_STEP_STATUSES:
            self._publish(node, record)
            if node.type == "control.terminate" and record.status is StepStatus.SUCCEEDED:
                raise _Terminate(str((record.inputs or {}).get("status") or "succeeded"), str((record.inputs or {}).get("message") or ""))
            return record.status
        if self.store.cancelled():
            raise _Cancelled()
        self.store.heartbeat()
        if node.type == "control.wait":
            return self._wait(node, spec, frame, record)
        if node.type == "approval.request":
            return self._approval(node, spec, frame, record)
        if node.type == "control.terminate":
            return self._terminate(node, spec, frame, record)
        return self._action(node, spec, frame, record)

    def _resolve_params(self, node: Node, spec: NodeSpec, frame: _Frame) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        scope = self.scope(frame)
        for param in spec.params:
            raw = node.params.get(param.key, param.default)
            try:
                resolved[param.key] = render(raw, scope) if param.resolve else raw
            except ExpressionError as error:
                raise ExpressionError(f"{param.label}: {error}") from None
        return resolved

    def _context(self, node: Node, frame: _Frame, attempt: int) -> ActionContext:
        def resolve(value: Any, extra: Mapping[str, Any] | None = None) -> Any:
            return render(value, self.scope(frame, extra))

        if self.context_factory is not None:
            return self.context_factory(
                node=node,
                iteration=frame.iteration,
                attempt=attempt,
                scope=self.scope(frame),
                resolve=resolve,
            )
        return ActionContext(
            automation_id=str(self.automation_info.get("id", "")),
            automation_name=str(self.automation_info.get("name", "")),
            run_id=str(self.run_info.get("id", "")),
            mode=self.mode,
            node_id=node.id,
            iteration=frame.iteration,
            attempt=attempt,
            now=self.now(),
            scope=self.scope(frame),
            resolve=resolve,
            timeout_seconds=node.timeout_seconds,
            test_recipient=self.test_recipient,
        )

    def _action(self, node: Node, spec: NodeSpec, frame: _Frame, record: StepRecord | None) -> StepStatus:
        retry: RetryPolicy = node.retry or spec.default_retry
        if record is not None and record.status is StepStatus.RUNNING:
            if spec.side_effect:
                return self._fail(
                    node, record,
                    "Interrompido no meio do envio. Para não duplicar, o passo não foi repetido; confira e reenvie a execução se precisar.",
                )
            record.error = "Interrompido; repetido automaticamente"
        if record is not None and record.status is StepStatus.WAITING:
            due = record.next_retry_at
            if due is not None and self.now() < due:
                raise _Suspend(due, "retry")
        attempt = record.attempt if record else 0
        record = record or StepRecord(node.id, frame.iteration, node.type, StepStatus.RUNNING, started_at=self.now())
        while True:
            attempt += 1
            record.attempt = attempt
            record.status = StepStatus.RUNNING
            record.next_retry_at = None
            try:
                inputs = self._resolve_params(node, spec, frame)
            except ExpressionError as error:
                return self._fail(node, record, str(error))
            record.inputs = _json_safe(_compact(inputs))
            if spec.side_effect:
                # Checkpoint before the effect: a crash now is detected on replay.
                self._save(record)
            if node.id == self.stop_at and self.on_stop is not None:
                self.on_stop(node, spec, self._context(node, frame, attempt), inputs)
                raise StopAtNode()
            if spec.executor is None:
                return self._fail(node, record, f"O passo {spec.label} não pode ser executado")
            self.executed += 1
            if self.dry_run and (spec.side_effect or spec.ai):
                return self._succeed(node, record, _placeholder(spec))
            try:
                outputs = spec.executor(self._context(node, frame, attempt), inputs)
                if spec.ai:
                    outputs = {**outputs, "gerado_por_ia": True}
                if spec.group == "variables":
                    outputs = {**outputs, "value": coerce_variable(self.var_types.get(str(inputs.get("name")), "string"), outputs.get("value"))}
                return self._succeed(node, record, outputs)
            except ActionError as error:
                message, retryable = error.message, error.retryable
            except ExpressionError as error:
                message, retryable = str(error), False
            except Exception as error:  # noqa: BLE001 - any executor failure is a step failure
                message, retryable = f"Falha inesperada ({type(error).__name__}): {error}"[:500], spec.side_effect is False
            retries_done = attempt - 1
            if retryable and retries_done < retry.count:
                delay = retry.delay(attempt)
                record.error = message[:2000]
                if delay <= INLINE_RETRY_SECONDS:
                    self._save(record)
                    self.sleep(delay)
                    continue
                record.status = StepStatus.WAITING
                record.next_retry_at = self.now() + datetime.timedelta(seconds=delay)
                self._save(record)
                raise _Suspend(record.next_retry_at, "retry")
            return self._fail(node, record, message)

    def _wait(self, node: Node, spec: NodeSpec, frame: _Frame, record: StepRecord | None) -> StepStatus:
        from onyx.ton.automations.nodes.control import wait_until

        if record is not None and record.status is StepStatus.WAITING:
            if record.next_retry_at is None or self.now() >= record.next_retry_at:
                return self._succeed(node, record, {**(record.outputs or {}), "waited": True})
            raise _Suspend(record.next_retry_at, "wait")
        record = StepRecord(node.id, frame.iteration, node.type, StepStatus.RUNNING, attempt=1, started_at=self.now())
        try:
            inputs = self._resolve_params(node, spec, frame)
            resume_at = wait_until(inputs, self.now())
        except (ExpressionError, ValueError) as error:
            return self._fail(node, record, str(error))
        record.inputs = _json_safe(_compact(inputs))
        if self.mode == "TEST":
            return self._succeed(node, record, {"resume_at": resume_at.isoformat(), "waited": False, "skipped_in_test": True})
        record.status = StepStatus.WAITING
        record.outputs = {"resume_at": resume_at.isoformat()}
        record.next_retry_at = resume_at
        self._save(record)
        raise _Suspend(resume_at, "wait")

    def _approval(self, node: Node, spec: NodeSpec, frame: _Frame, record: StepRecord | None) -> StepStatus:
        if record is not None and record.status is StepStatus.WAITING:
            approval_id = str((record.outputs or {}).get("approval_id") or "")
            result = self.store.approval_result(approval_id) if approval_id else None
            if result is not None:
                return self._succeed(node, record, {**result, "approval_id": approval_id})
            if record.next_retry_at is not None and self.now() >= record.next_retry_at:
                self.store.close_approval(approval_id, "EXPIRED")
                record.outputs = {"approval_id": approval_id, "outcome": "Expirada", "approved": False}
                return self._fail(node, record, "Ninguém respondeu à aprovação no prazo", StepStatus.TIMED_OUT)
            raise _Suspend(record.next_retry_at, "approval")
        record = StepRecord(node.id, frame.iteration, node.type, StepStatus.RUNNING, attempt=1, started_at=self.now())
        try:
            inputs = self._resolve_params(node, spec, frame)
        except ExpressionError as error:
            return self._fail(node, record, str(error))
        record.inputs = _json_safe(_compact(inputs))
        options = [to_text(option).strip() for option in (inputs.get("options") or []) if to_text(option).strip()]
        if inputs.get("kind", "approve_reject") == "approve_reject" or not options:
            options = ["Aprovar", "Recusar"]
        approvers = [to_text(a).strip().lower() for a in _flatten(inputs.get("approvers")) if to_text(a).strip()]
        if not approvers and self.mode != "TEST":
            return self._fail(node, record, "Informe quem aprova")
        if self.mode == "TEST":
            return self._succeed(
                node, record,
                {
                    "outcome": options[0],
                    "approved": True,
                    "responder": self.test_recipient or "teste",
                    "comment": "Aprovado automaticamente no teste",
                    "decided_at": self.now().isoformat(),
                },
            )
        hours = to_number(inputs.get("expires_after_hours")) or 0
        expires_at = self.now() + datetime.timedelta(hours=float(hours)) if hours > 0 else None
        record.status = StepStatus.WAITING
        record.next_retry_at = expires_at
        self._save(record)
        approval_id = self.store.open_approval(
            record,
            ApprovalRequest(
                node_id=node.id,
                iteration=frame.iteration,
                approvers=approvers,
                title=to_text(inputs.get("title")) or (node.label or "Aprovação"),
                details=to_text(inputs.get("details")),
                options=options,
                expires_at=expires_at,
            ),
        )
        record.outputs = {"approval_id": approval_id}
        self._save(record)
        raise _Suspend(expires_at, "approval")

    def _terminate(self, node: Node, spec: NodeSpec, frame: _Frame, record: StepRecord | None) -> StepStatus:
        record = record or StepRecord(node.id, frame.iteration, node.type, StepStatus.RUNNING, attempt=1, started_at=self.now())
        try:
            inputs = self._resolve_params(node, spec, frame)
        except ExpressionError as error:
            return self._fail(node, record, str(error))
        record.inputs = _json_safe(_compact(inputs))
        self._succeed(node, record, {})
        raise _Terminate(str(inputs.get("status") or "succeeded"), to_text(inputs.get("message")))

    # -- containers ------------------------------------------------------------

    def _decision(self, node: Node, frame: _Frame, record: StepRecord | None, decide: Callable[[], dict[str, Any]]) -> tuple[StepRecord, dict[str, Any]] | StepStatus:
        """Evaluate a container's decision once and keep it for replays."""
        if record is not None and record.outputs is not None and "decision" in record.outputs:
            return record, record.outputs["decision"]
        record = StepRecord(node.id, frame.iteration, node.type, StepStatus.RUNNING, attempt=1, started_at=self.now())
        try:
            decision = decide()
        except (ExpressionError, ValueError) as error:
            return self._fail(node, record, str(error))
        record.outputs = {"decision": _json_safe(decision)}
        self._save(record)
        return record, record.outputs["decision"]

    def _finish_container(self, node: Node, record: StepRecord, outcome: StepStatus, outputs: dict[str, Any]) -> StepStatus:
        status = StepStatus.SUCCEEDED if outcome in (StepStatus.SUCCEEDED, StepStatus.SKIPPED) else outcome
        changed = record.status is not status or (record.outputs or {}).get("result") != outputs
        record.status = status
        record.outputs = {**(record.outputs or {}), "result": _json_safe(outputs)}
        if record.finished_at is None or changed:
            record.finished_at = self.now()
        if status is not StepStatus.SUCCEEDED:
            record.error = record.error or "Um passo dentro deste bloco falhou"
        if changed:
            self._save(record)
        self.steps[node.id] = {"status": RUN_AFTER_OF[status], "outputs": outputs, "error": record.error}
        return status

    def _run_container(self, node: Node, spec: NodeSpec, frame: _Frame, record: StepRecord | None) -> StepStatus:
        if record is None and self.store.cancelled():
            raise _Cancelled()
        scope = self.scope(frame)
        if spec.container == "condition":
            group = parse_group(node.params.get("condition"))
            got = self._decision(node, frame, record, lambda: {"result": evaluate_group(group, scope)})
            if isinstance(got, StepStatus):
                return got
            record, decision = got
            chosen = node.then if decision["result"] else node.otherwise
            outcome = self._run_list(chosen or [], frame)
            return self._finish_container(node, record, outcome, {"result": bool(decision["result"])})
        if spec.container == "switch":
            def choose() -> dict[str, Any]:
                value = to_text(render(node.params.get("on", ""), scope)).strip().casefold()
                for case in node.cases or []:
                    if to_text(render(case.value, scope)).strip().casefold() == value:
                        return {"case": case.id, "value": value}
                return {"case": None, "value": value}

            got = self._decision(node, frame, record, choose)
            if isinstance(got, StepStatus):
                return got
            record, decision = got
            case = next((c for c in node.cases or [] if c.id == decision["case"]), None)
            outcome = self._run_list(case.steps if case else (node.default or []), frame)
            return self._finish_container(node, record, outcome, {"case": decision["case"], "value": decision["value"]})
        if spec.container == "loop":
            def items() -> dict[str, Any]:
                value = render(node.params.get("items", ""), scope)
                if value is None or value == "":
                    listed: list[Any] = []
                elif isinstance(value, list):
                    listed = value
                elif isinstance(value, dict):
                    listed = [value]
                else:
                    raise ValueError("'Para cada' precisa de uma lista (ex.: {{ steps.x.outputs.items }})")
                if len(listed) > MAX_LOOP_ITEMS:
                    raise ValueError(f"'Para cada' aceita até {MAX_LOOP_ITEMS} itens; recebeu {len(listed)}")
                return {"items": listed}

            got = self._decision(node, frame, record, items)
            if isinstance(got, StepStatus):
                return got
            record, decision = got
            listed = decision["items"]
            outcome = StepStatus.SUCCEEDED
            failures = 0
            suspended: _Suspend | None = None
            for index, item in enumerate(listed):
                try:
                    status = self._run_list(node.steps or [], frame.child(node.id, index, item, len(listed)))
                except _Suspend as pause:
                    suspended = pause
                    break
                if status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                    outcome = StepStatus.FAILED
                    failures += 1
            if suspended is not None:
                raise suspended
            return self._finish_container(node, record, outcome, {"count": len(listed), "failed": failures})
        if spec.container == "until":
            got = self._decision(node, frame, record, lambda: {"started": True})
            if isinstance(got, StepStatus):
                return got
            record, _decision = got
            group = parse_group(node.params.get("condition"))
            limit = int(min(MAX_UNTIL_ITERATIONS, max(1, to_number(node.params.get("max_iterations")) or 20)))
            outcome = StepStatus.SUCCEEDED
            iterations = 0
            reached = False
            for index in range(limit):
                child = frame.child(node.id, index, frame.item, limit)
                outcome = self._run_list(node.steps or [], child)
                iterations = index + 1
                if outcome in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                    break
                try:
                    if evaluate_group(group, self.scope(child)):
                        reached = True
                        break
                except ExpressionError as error:
                    record.error = str(error)
                    outcome = StepStatus.FAILED
                    break
            return self._finish_container(node, record, outcome, {"iterations": iterations, "condition_met": reached})
        if spec.container == "scope":
            got = self._decision(node, frame, record, lambda: {"started": True})
            if isinstance(got, StepStatus):
                return got
            record, _decision = got
            outcome = self._run_list(node.steps or [], frame)
            return self._finish_container(node, record, outcome, {})
        if spec.container == "parallel":
            got = self._decision(node, frame, record, lambda: {"started": True})
            if isinstance(got, StepStatus):
                return got
            record, _decision = got
            outcome = StepStatus.SUCCEEDED
            pauses: list[_Suspend] = []
            for branch in node.branches or []:
                try:
                    status = self._run_list(branch.steps, frame)
                except _Suspend as pause:
                    pauses.append(pause)
                    continue
                if status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                    outcome = StepStatus.FAILED
            if pauses:
                times = [p.resume_at for p in pauses if p.resume_at is not None]
                raise _Suspend(min(times) if len(times) == len(pauses) else None, pauses[0].waiting_on)
            return self._finish_container(node, record, outcome, {})
        record = record or StepRecord(node.id, frame.iteration, node.type, StepStatus.RUNNING, started_at=self.now())
        return self._fail(node, record, f"Bloco desconhecido: {spec.container}")


def _flatten(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[Any] = []
        for entry in value:
            result.extend(_flatten(entry))
        return result
    if isinstance(value, str):
        return [part for part in value.replace(";", ",").split(",")]
    return [value]


class MemoryStore:
    """RunStore kept in memory: tests and dry runs."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str], StepRecord] = {}
        self.approvals: dict[str, dict[str, Any]] = {}
        self.is_cancelled = False
        self.saves = 0

    def load(self) -> dict[tuple[str, str], StepRecord]:
        return {key: StepRecord(**vars(record)) for key, record in self.records.items()}

    def save(self, record: StepRecord) -> None:
        self.saves += 1
        self.records[(record.node_id, record.iteration)] = StepRecord(**vars(record))

    def cancelled(self) -> bool:
        return self.is_cancelled

    def heartbeat(self) -> None:
        return None

    def open_approval(self, record: StepRecord, request: ApprovalRequest) -> str:
        approval_id = f"ap{len(self.approvals) + 1}"
        self.approvals[approval_id] = {"request": request, "result": None, "status": "PENDING"}
        return approval_id

    def approval_result(self, approval_id: str) -> dict[str, Any] | None:
        entry = self.approvals.get(approval_id)
        return entry["result"] if entry else None

    def close_approval(self, approval_id: str, status: str) -> None:
        if approval_id in self.approvals:
            self.approvals[approval_id]["status"] = status
