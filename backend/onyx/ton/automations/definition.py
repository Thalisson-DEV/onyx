"""Automation definition v3: trigger, declared variables, a tree of nodes and
settings. Node types come from the catalog (``registry``); the structure is
checked here, the meaning (parameters, references) in ``validation``."""

import re
from collections.abc import Iterator
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_NODES = 120
MAX_DEPTH = 8
_ID = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_VARIABLE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


class AutomationKind(str, Enum):
    EMAIL = "EMAIL"
    ALERT = "ALERT"
    ROUTINE = "ROUTINE"
    APPROVAL = "APPROVAL"
    DATA_AI = "DATA_AI"
    GENERAL = "GENERAL"


KIND_LABELS: dict[AutomationKind, str] = {
    AutomationKind.EMAIL: "E-mail",
    AutomationKind.ALERT: "Alerta",
    AutomationKind.ROUTINE: "Rotina",
    AutomationKind.APPROVAL: "Aprovação",
    AutomationKind.DATA_AI: "Dados e IA",
    AutomationKind.GENERAL: "Geral",
}
KIND_DESCRIPTIONS: dict[AutomationKind, str] = {
    AutomationKind.EMAIL: "Envia e-mails a pessoas de dentro ou de fora do TON.",
    AutomationKind.ALERT: "Avisa no sino do TON ou por e-mail quando algo acontece.",
    AutomationKind.ROUTINE: "Rotina de controladoria que roda numa agenda ou a cada evento.",
    AutomationKind.APPROVAL: "Pede a decisão de uma pessoa antes de seguir.",
    AutomationKind.DATA_AI: "Lê, transforma ou interpreta dados, com ou sem IA.",
    AutomationKind.GENERAL: "Qualquer outra automação.",
}


class AutomationStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class AutomationOrigin(str, Enum):
    USER = "USER"
    TON_SUGGESTED = "TON_SUGGESTED"
    SYSTEM = "SYSTEM"
    MIGRATED = "MIGRATED"


class RunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


FINAL_RUN_STATUSES = {
    RunStatus.SUCCEEDED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
    RunStatus.TIMED_OUT,
}


class RunMode(str, Enum):
    LIVE = "LIVE"
    MANUAL = "MANUAL"
    TEST = "TEST"
    RESUBMIT = "RESUBMIT"


class StepStatus(str, Enum):
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


FINAL_STEP_STATUSES = {
    StepStatus.SUCCEEDED,
    StepStatus.FAILED,
    StepStatus.SKIPPED,
    StepStatus.TIMED_OUT,
    StepStatus.CANCELLED,
}

RunAfter = Literal["succeeded", "failed", "skipped", "timed_out"]
RUN_AFTER_OF: dict[StepStatus, str] = {
    StepStatus.SUCCEEDED: "succeeded",
    StepStatus.FAILED: "failed",
    StepStatus.SKIPPED: "skipped",
    StepStatus.TIMED_OUT: "timed_out",
    StepStatus.CANCELLED: "failed",
}


class RetryPolicy(BaseModel):
    policy: Literal["none", "fixed", "exponential"] = "none"
    count: int = Field(default=0, ge=0, le=10)
    interval_seconds: int = Field(default=30, ge=1, le=3600)

    @model_validator(mode="after")
    def _shape(self) -> "RetryPolicy":
        if self.policy == "none":
            self.count = 0
        return self

    def delay(self, attempt: int) -> int:
        """Seconds before retry number ``attempt`` (1 = first retry)."""
        if self.policy == "exponential":
            return min(3600, self.interval_seconds * (2 ** (attempt - 1)))
        return self.interval_seconds


class Case(BaseModel):
    id: str = Field(max_length=40)
    value: str = Field(default="", max_length=200)
    steps: list["Node"] = Field(default_factory=list)


class Branch(BaseModel):
    id: str = Field(max_length=40)
    label: str = Field(default="", max_length=80)
    steps: list["Node"] = Field(default_factory=list)


class Node(BaseModel):
    id: str
    type: str = Field(max_length=48)
    label: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=500)
    params: dict[str, Any] = Field(default_factory=dict)
    run_after: list[RunAfter] = Field(default_factory=lambda: list[RunAfter](["succeeded"]))
    retry: RetryPolicy | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=86_400)
    # Containers. Which ones a node may have depends on its catalog entry.
    then: list["Node"] | None = None
    otherwise: list["Node"] | None = Field(default=None, alias="else")
    cases: list[Case] | None = None
    default: list["Node"] | None = None
    steps: list["Node"] | None = None
    branches: list[Branch] | None = None

    model_config = {"populate_by_name": True}

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        if not _ID.match(value):
            raise ValueError(
                f"Id de passo inválido '{value}': use letras minúsculas, números e _"
            )
        return value

    @field_validator("run_after")
    @classmethod
    def _run_after(cls, value: list[str]) -> list[str]:
        unique = list(dict.fromkeys(value))
        if not unique:
            raise ValueError("Escolha ao menos uma situação em 'Executar após'")
        return unique

    def children(self) -> Iterator[tuple[str, list["Node"]]]:
        """(slot, nodes) for every child list, e.g. ("then", [...])."""
        if self.then is not None:
            yield "then", self.then
        if self.otherwise is not None:
            yield "else", self.otherwise
        for case in self.cases or []:
            yield f"case:{case.id}", case.steps
        if self.default is not None:
            yield "default", self.default
        if self.steps is not None:
            yield "steps", self.steps
        for branch in self.branches or []:
            yield f"branch:{branch.id}", branch.steps


Case.model_rebuild()
Branch.model_rebuild()
Node.model_rebuild()


class TriggerConfig(BaseModel):
    type: str = Field(max_length=48)
    params: dict[str, Any] = Field(default_factory=dict)
    label: str = Field(default="", max_length=120)


class VariableDecl(BaseModel):
    name: str
    type: Literal["string", "number", "boolean", "array", "object"] = "string"
    value: Any = None
    description: str = Field(default="", max_length=300)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip().lower()
        if not _VARIABLE.match(value):
            raise ValueError(
                "Nome de variável: letras minúsculas, números e _ (ex.: prazo_correcao)"
            )
        return value


class Settings(BaseModel):
    # People told by e-mail when a live run fails.
    notify_on_failure: list[str] = Field(default_factory=list)
    timeout_hours: int = Field(default=168, ge=1, le=720)


class AutomationDefinition(BaseModel):
    schema_version: Literal[3] = Field(default=3, alias="schema")
    trigger: TriggerConfig
    variables: list[VariableDecl] = Field(default_factory=list)
    steps: list[Node] = Field(default_factory=list)
    settings: Settings = Field(default_factory=Settings)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _structure(self) -> "AutomationDefinition":
        names = [variable.name for variable in self.variables]
        if len(names) != len(set(names)):
            raise ValueError("Há variáveis com o mesmo nome")
        ids: set[str] = set()
        count = 0

        def walk(nodes: list[Node], depth: int) -> None:
            nonlocal count
            if depth > MAX_DEPTH:
                raise ValueError(f"No máximo {MAX_DEPTH} níveis de passos")
            for node in nodes:
                count += 1
                if node.id in ids or node.id == "trigger":
                    raise ValueError(f"Há dois passos com o id '{node.id}'")
                ids.add(node.id)
                for _slot, children in node.children():
                    walk(children, depth + 1)

        walk(self.steps, 1)
        if count > MAX_NODES:
            raise ValueError(f"No máximo {MAX_NODES} passos por automação")
        return self

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


def iter_nodes(nodes: list[Node]) -> Iterator[Node]:
    for node in nodes:
        yield node
        for _slot, children in node.children():
            yield from iter_nodes(children)


def find_node(nodes: list[Node], node_id: str) -> Node | None:
    return next((node for node in iter_nodes(nodes) if node.id == node_id), None)


def unique_id(base: str, taken: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", base.lower()).strip("_")[:34] or "passo"
    if not slug[0].isalpha():
        slug = f"p_{slug}"[:34]
    candidate = slug
    index = 2
    while candidate in taken:
        candidate = f"{slug}_{index}"
        index += 1
    return candidate
