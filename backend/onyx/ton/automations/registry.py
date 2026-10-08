"""The node catalog: every trigger and step an automation may use.

A node type is a ``NodeSpec`` (labels, parameters, outputs, container kind,
retry default) plus, for actions, an executor. The designer renders its forms
and the dynamic-content picker from these specs, the checker validates
against them and the interpreter runs them. Adding a node = one
``register()`` call in ``nodes/``.
"""

import datetime
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from onyx.ton.automations.definition import AutomationKind, RetryPolicy

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from onyx.db.models import User

ParamKind = Literal[
    "text",
    "textarea",
    "number",
    "boolean",
    "select",
    "multiselect",
    "emails",
    "condition",
    "html",
    "json",
    "fields",
    "mapping",
    "columns",
    "keyvalue",
    "list",
    "time",
    "weekdays",
    "file",
    "expression",
    "automations",
]
Container = Literal["condition", "switch", "loop", "until", "scope", "parallel"]
Group = Literal[
    "trigger",
    "control",
    "variables",
    "data",
    "ai",
    "ton",
    "email",
    "approval",
    "integration",
]

GROUP_LABELS: dict[str, str] = {
    "trigger": "Gatilhos",
    "control": "Controle",
    "variables": "Variáveis",
    "data": "Dados",
    "ai": "Inteligência artificial",
    "ton": "TON",
    "email": "E-mail",
    "approval": "Aprovações",
    "integration": "Integrações",
}


@dataclass(frozen=True)
class FieldSpec:
    """A column of a list-valued parameter (fields, mapping, columns)."""

    key: str
    label: str
    kind: Literal["text", "select", "boolean", "expression"] = "text"
    options: tuple[tuple[str, str], ...] = ()
    placeholder: str | None = None


@dataclass(frozen=True)
class ParamSpec:
    key: str
    label: str
    kind: ParamKind = "text"
    required: bool = False
    default: Any = None
    help: str | None = None
    placeholder: str | None = None
    options: tuple[tuple[str, str], ...] = ()
    # False: the executor resolves it itself (per item, conditions).
    resolve: bool = True
    # Accepts {{ }} expressions (dynamic content).
    dynamic: bool = True
    min: float | None = None
    max: float | None = None
    item_fields: tuple[FieldSpec, ...] = ()
    # Show only when another parameter has one of these values.
    show_if: tuple[str, tuple[str, ...]] | None = None
    advanced: bool = False


@dataclass(frozen=True)
class OutputSpec:
    key: str
    label: str
    type: Literal["string", "number", "boolean", "array", "object", "any"] = "string"
    description: str = ""
    # For arrays of objects: the fields of each item ({{ item.campo }}).
    item_fields: tuple["OutputSpec", ...] = ()


class ActionError(Exception):
    """A step failure. ``retryable`` failures follow the retry policy."""

    def __init__(self, message: str, *, retryable: bool = False, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.code = code


@dataclass
class ActionContext:
    """What an executor may use. ``session``/``owner`` are None in pure
    tests; DB-backed nodes raise ActionError when they are missing."""

    automation_id: str
    automation_name: str
    run_id: str
    mode: str
    node_id: str
    iteration: str
    attempt: int
    now: datetime.datetime
    scope: Mapping[str, Any]
    resolve: Callable[[Any, Mapping[str, Any] | None], Any]
    timeout_seconds: int | None = None
    session: "Session | None" = None
    owner: "User | None" = None
    test_recipient: str | None = None
    services: Any = None

    @property
    def is_test(self) -> bool:
        return self.mode == "TEST"

    def require_db(self) -> tuple["Session", "User"]:
        if self.session is None or self.owner is None:
            raise ActionError("Este passo precisa do banco do TON e de um responsável ativo")
        return self.session, self.owner


Executor = Callable[[ActionContext, dict[str, Any]], dict[str, Any]]


@dataclass
class TriggerContext:
    session: "Session | None"
    owner: "User | None"
    now: datetime.datetime
    automation_id: str
    automation_name: str


TriggerPrepare = Callable[[TriggerContext, dict[str, Any], dict[str, Any]], dict[str, Any] | None]


@dataclass(frozen=True)
class NodeSpec:
    type: str
    group: Group
    label: str
    description: str
    icon: str
    params: tuple[ParamSpec, ...] = ()
    outputs: tuple[OutputSpec, ...] = ()
    container: Container | None = None
    is_trigger: bool = False
    # External effect (e-mail, HTTP, notice): runs at most once per step.
    side_effect: bool = False
    default_retry: RetryPolicy = field(default_factory=RetryPolicy)
    # Automation types this node satisfies at activation.
    satisfies: tuple[AutomationKind, ...] = ()
    executor: Executor | None = None
    # Triggers: build the frozen trigger output from an event payload.
    prepare: TriggerPrepare | None = None
    # Outbox event kinds a trigger listens to.
    event_kinds: tuple[str, ...] = ()
    # Outputs that depend on parameters ("fields" = params.fields,
    # "inputs" = params.inputs of the manual trigger).
    dynamic_outputs: str | None = None
    # AI nodes: their outputs are labeled as AI-generated.
    ai: bool = False
    keywords: tuple[str, ...] = ()
    # Short sentence in the add-action panel and the node card.
    summary: Callable[[dict[str, Any]], str] | None = None

    def param(self, key: str) -> ParamSpec | None:
        return next((item for item in self.params if item.key == key), None)


REGISTRY: dict[str, NodeSpec] = {}


def register(spec: NodeSpec) -> NodeSpec:
    if spec.type in REGISTRY:
        raise ValueError(f"duplicate node type {spec.type}")
    REGISTRY[spec.type] = spec
    return spec


def get_registry() -> dict[str, NodeSpec]:
    # Importing the package registers every node module once.
    import onyx.ton.automations.nodes  # noqa: F401

    return REGISTRY


def get_spec(node_type: str) -> NodeSpec | None:
    return get_registry().get(node_type)
