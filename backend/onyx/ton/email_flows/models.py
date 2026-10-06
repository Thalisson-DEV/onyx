"""Enums and the version-1 definition pieces of email flows (still used to
read old definitions; v2 is in ``steps``).

A definition is validated against the closed catalogs here, so the same rules
apply to the screen, the seeded default flow and the assistant's proposals.
"""

import datetime
import re
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from onyx.ton.email_flows.catalog import (
    CHANGE_STATES,
    MAX_CONDITIONS,
    MAX_RECIPIENTS,
    OPERATORS_BY_TYPE,
    SUBJECT_MARKERS,
    TRIGGERS,
    FieldType,
    ItemState,
    Operator,
    TemplateKey,
    TriggerKind,
)

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_MARKER = re.compile(r"\{([^{}]*)\}")


class FlowOrigin(str, Enum):
    USER = "USER"
    TON_SUGGESTED = "TON_SUGGESTED"
    SYSTEM = "SYSTEM"


class FlowStatus(str, Enum):
    SUGGESTED = "SUGGESTED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISCARDED = "DISCARDED"


class FlowBranch(str, Enum):
    YES = "YES"
    NO = "NO"


class FlowRunStatus(str, Enum):
    RUNNING = "RUNNING"
    # Paused at "esperar" or "aprovação".
    WAITING = "WAITING"
    # Ended early: approval refused.
    STOPPED = "STOPPED"
    SENT = "SENT"
    SILENT = "SILENT"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    # Rendered and stored, but no e-mail provider is configured.
    NOT_CONFIGURED = "NOT_CONFIGURED"


class DeliveryStatus(str, Enum):
    SENT = "SENT"
    FAILED = "FAILED"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class FlowTrigger(BaseModel):
    kind: TriggerKind
    frequency: Literal["WEEKLY", "DAILY"] | None = None
    # 0 = Monday, as in Python's weekday().
    weekday: int | None = Field(default=None, ge=0, le=6)
    time: str | None = None
    changes: list[ItemState] = Field(default_factory=list)

    @model_validator(mode="after")
    def _params(self) -> "FlowTrigger":
        if self.kind is TriggerKind.SCHEDULE:
            if self.frequency is None or self.time is None:
                raise ValueError("O agendamento precisa de frequência e horário")
            if not _TIME.match(self.time):
                raise ValueError("Horário inválido; use HH:MM")
            if self.frequency == "WEEKLY" and self.weekday is None:
                raise ValueError("O agendamento semanal precisa do dia da semana")
            if self.frequency == "DAILY":
                self.weekday = None
        else:
            self.frequency = None
            self.weekday = None
            self.time = None
        if self.kind is TriggerKind.NG_OCCURRENCE_CHANGED:
            if not self.changes:
                raise ValueError("Escolha ao menos uma mudança: nova, corrigida ou reapareceu")
            if any(change not in CHANGE_STATES for change in self.changes):
                raise ValueError("Mudança fora do catálogo")
            self.changes = sorted(set(self.changes), key=CHANGE_STATES.index)
        else:
            self.changes = []
        return self


class ConditionClause(BaseModel):
    field: str
    operator: Operator
    value: str | float | list[str]


class EmailAction(BaseModel):
    kind: Literal["EMAIL", "NONE"] = "NONE"
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str = ""
    template: TemplateKey | None = None

    @field_validator("to", "cc", "bcc")
    @classmethod
    def _addresses(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in value:
            address = raw.strip().lower()
            if not address:
                continue
            if not _EMAIL.match(address):
                raise ValueError(f"E-mail inválido: {raw}")
            if address not in cleaned:
                cleaned.append(address)
        return cleaned

    @model_validator(mode="after")
    def _shape(self) -> "EmailAction":
        if self.kind == "NONE":
            self.to, self.cc, self.bcc = [], [], []
            self.subject, self.template = "", None
            return self
        if len(self.to) + len(self.cc) + len(self.bcc) > MAX_RECIPIENTS:
            raise ValueError(f"No máximo {MAX_RECIPIENTS} destinatários por fluxo")
        self.subject = self.subject.strip()
        if not self.subject or len(self.subject) > 200:
            raise ValueError("Assunto obrigatório, com até 200 caracteres")
        unknown = [m for m in _MARKER.findall(self.subject) if m not in SUBJECT_MARKERS]
        if unknown:
            raise ValueError(f"Marcador desconhecido no assunto: {{{unknown[0]}}}")
        if self.template is None:
            raise ValueError("Escolha o modelo do e-mail")
        return self

    def recipients(self) -> list[str]:
        return [*self.to, *self.cc, *self.bcc]


def activation_problems(definition: "FlowDefinition") -> list[str]:
    """What still blocks turning the flow on. A suggestion may be saved
    incomplete (e.g. waiting for the Financeiro addresses); an active flow
    may not."""
    problems = []
    for label, action in (("Então", definition.on_yes), ("Senão", definition.on_no)):
        if action.kind == "EMAIL" and not action.to:
            problems.append(f"{label}: informe ao menos um destinatário em Para")
    return problems


class FlowDefinition(BaseModel):
    trigger: FlowTrigger
    conditions: list[ConditionClause] = Field(default_factory=list)
    on_yes: EmailAction
    on_no: EmailAction = Field(default_factory=EmailAction)

    @model_validator(mode="after")
    def _catalog(self) -> "FlowDefinition":
        spec = TRIGGERS[self.trigger.kind]
        if len(self.conditions) > MAX_CONDITIONS:
            raise ValueError(f"No máximo {MAX_CONDITIONS} condições")
        for clause in self.conditions:
            field = spec.field(clause.field)
            if field is None:
                raise ValueError(
                    f"O campo '{clause.field}' não existe no gatilho '{spec.label}'"
                )
            if clause.operator not in OPERATORS_BY_TYPE[field.type]:
                raise ValueError(f"Operador inválido para '{field.label}'")
            clause.value = _coerce(field.type, clause.operator, clause.value, field)
        for action in (self.on_yes, self.on_no):
            if action.template is not None and action.template not in spec.templates:
                raise ValueError(f"Modelo não disponível para '{spec.label}'")
        return self


def _coerce(
    kind: FieldType, operator: Operator, value: object, field: object
) -> str | float | list[str]:
    if kind in (FieldType.NUMBER, FieldType.MONEY):
        try:
            return float(str(value).replace(",", "."))
        except ValueError:
            raise ValueError("Informe um número na condição") from None
    if operator is Operator.IN:
        items = value if isinstance(value, list) else str(value).split(",")
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        if not cleaned:
            raise ValueError("Informe ao menos um valor na condição")
        result = cleaned
    else:
        result = [str(value).strip()]
        if not result[0]:
            raise ValueError("Informe o valor da condição")
    choices = getattr(field, "choices", ())
    if choices:
        allowed = {key for key, _ in choices}
        if any(item not in allowed for item in result):
            raise ValueError("Valor fora das opções do campo")
    return result if operator is Operator.IN else result[0]
