"""Flow definition v2: a trigger, flow variables and a tree of steps.

Steps: condition (Sim/Não, item clauses split the items), send_email (HTML
written in the editor), for_each_unit (repeat per unit), wait (pause and
re-check) and approval (pause until a person decides). Version-1 definitions
(one condition, Sim/Não e-mail) are converted on read, so stored rows never
need a data migration.
"""

import re
from typing import Annotated, Any, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from onyx.ton.email_flows.catalog import (
    MAX_CONDITIONS,
    MAX_RECIPIENTS,
    OPERATORS_BY_TYPE,
    TRIGGERS,
    TemplateKey,
    TriggerKind,
)
from onyx.ton.email_flows.models import (
    ConditionClause,
    EmailAction,
    FlowTrigger,
    _coerce,
)

MAX_DEPTH = 5
MAX_STEPS = 40
MAX_BODY_CHARS = 60_000
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_VARIABLE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_MARKER = re.compile(r"\{([a-z][a-z0-9_]*)\}")
# Recipient tokens resolved at run time inside "para cada unidade".
UNIT_RECIPIENT_TOKEN = "{email_unidade}"

# System variables every trigger offers; {unidade} only inside for_each_unit.
SYSTEM_VARIABLES: dict[str, str] = {
    "semana": "Semana do ano (ex.: 41)",
    "data": "Data da execução (dd/mm/aaaa)",
    "total": "Quantidade de itens",
    "valor_total": "Valor total dos itens",
    "nome_fluxo": "Nome do fluxo",
    "link_ton": "Link para o TON",
}
UNIT_VARIABLES: dict[str, str] = {"unidade": "Nome da unidade"}


def _new_id() -> str:
    return uuid4().hex[:10]


def _addresses(value: list[str], *, allow_unit_token: bool) -> list[str]:
    cleaned: list[str] = []
    for raw in value:
        address = raw.strip()
        if not address:
            continue
        if allow_unit_token and address == UNIT_RECIPIENT_TOKEN:
            pass
        else:
            address = address.lower()
            if not _EMAIL.match(address):
                raise ValueError(f"E-mail inválido: {raw}")
        if address not in cleaned:
            cleaned.append(address)
    return cleaned


class FlowVariable(BaseModel):
    name: str
    value: str = Field(max_length=500)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip().lower()
        if not _VARIABLE_NAME.match(value):
            raise ValueError(
                "Nome de variável: letras minúsculas, números e _ (ex.: prazo_correcao)"
            )
        if value in SYSTEM_VARIABLES or value in UNIT_VARIABLES:
            raise ValueError(f"'{value}' já é uma variável do sistema")
        return value


class _Step(BaseModel):
    id: str = Field(default_factory=_new_id, max_length=40)
    label: str | None = Field(default=None, max_length=120)


class SendEmailStep(_Step):
    type: Literal["send_email"] = "send_email"
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str = Field(default="", max_length=200)
    body: str = Field(default="", max_length=MAX_BODY_CHARS)
    use_layout: bool = True

    @field_validator("to", "cc", "bcc")
    @classmethod
    def _recipients(cls, value: list[str]) -> list[str]:
        return _addresses(value, allow_unit_token=True)

    @model_validator(mode="after")
    def _limits(self) -> "SendEmailStep":
        if len(self.to) + len(self.cc) + len(self.bcc) > MAX_RECIPIENTS:
            raise ValueError(f"No máximo {MAX_RECIPIENTS} destinatários por e-mail")
        self.subject = self.subject.strip()
        return self

    def recipients(self) -> list[str]:
        return [*self.to, *self.cc, *self.bcc]


class ConditionStep(_Step):
    type: Literal["condition"] = "condition"
    conditions: list[ConditionClause] = Field(default_factory=list)
    then: list["Step"] = Field(default_factory=list)
    otherwise: list["Step"] = Field(default_factory=list, alias="else")

    model_config = {"populate_by_name": True}


class UnitRecipients(BaseModel):
    unit: str = Field(min_length=1, max_length=120)
    emails: list[str] = Field(default_factory=list)

    @field_validator("emails")
    @classmethod
    def _emails(cls, value: list[str]) -> list[str]:
        return _addresses(value, allow_unit_token=False)


class ForEachUnitStep(_Step):
    type: Literal["for_each_unit"] = "for_each_unit"
    recipients: list[UnitRecipients] = Field(default_factory=list)
    default_emails: list[str] = Field(default_factory=list)
    steps: list["Step"] = Field(default_factory=list)

    @field_validator("default_emails")
    @classmethod
    def _defaults(cls, value: list[str]) -> list[str]:
        return _addresses(value, allow_unit_token=False)

    def emails_for(self, unit: str) -> list[str]:
        key = unit.strip().casefold()
        for entry in self.recipients:
            if entry.unit.strip().casefold() == key:
                return entry.emails
        return self.default_emails


class WaitStep(_Step):
    type: Literal["wait"] = "wait"
    mode: Literal["duration", "until"] = "duration"
    days: int = Field(default=0, ge=0, le=60)
    hours: int = Field(default=0, ge=0, le=23)
    weekday: int | None = Field(default=None, ge=0, le=6)
    time: str | None = None

    @model_validator(mode="after")
    def _shape(self) -> "WaitStep":
        if self.mode == "duration" and self.days == 0 and self.hours == 0:
            raise ValueError("Espera: informe dias ou horas")
        if self.mode == "until":
            if self.weekday is None or self.time is None or not _TIME.match(self.time):
                raise ValueError("Espera até: informe o dia da semana e o horário (HH:MM)")
        return self


class ApprovalStep(_Step):
    type: Literal["approval"] = "approval"
    approvers: list[str] = Field(default_factory=list)
    message: str = Field(default="", max_length=1000)

    @field_validator("approvers")
    @classmethod
    def _approvers(cls, value: list[str]) -> list[str]:
        return _addresses(value, allow_unit_token=False)


Step = Annotated[
    Union[SendEmailStep, ConditionStep, ForEachUnitStep, WaitStep, ApprovalStep],
    Field(discriminator="type"),
]
ConditionStep.model_rebuild()
ForEachUnitStep.model_rebuild()


def _legacy_body(template: TemplateKey | None) -> str:
    block = {
        TemplateKey.INCONSISTENCY_REPORT: "inconsistency_table",
        TemplateKey.ACCOUNT_LIST: "account_table",
    }.get(template or TemplateKey.SIMPLE_NOTICE, "summary")
    return (
        "<p>Olá,</p>"
        f'<div data-block="{block}"></div>'
        '<p><span data-variable="link_ton"></span></p>'
    )


def _from_action(action: EmailAction) -> list["Step"]:
    if action.kind != "EMAIL":
        return []
    return [
        SendEmailStep(
            to=action.to,
            cc=action.cc,
            bcc=action.bcc,
            subject=action.subject.strip(),
            body=_legacy_body(action.template),
        )
    ]


def convert_v1(raw: dict[str, Any]) -> dict[str, Any]:
    """Turn a version-1 definition (trigger, conditions, on_yes, on_no) into
    the v2 shape: one condition step whose branches hold the e-mails."""
    trigger = raw.get("trigger") or {}
    on_yes = EmailAction.model_validate(raw.get("on_yes") or {})
    on_no = EmailAction.model_validate(raw.get("on_no") or {})
    then = _from_action(on_yes)
    otherwise = _from_action(on_no)
    conditions = raw.get("conditions") or []
    steps: list[Any]
    if conditions or otherwise:
        steps = [
            ConditionStep(
                conditions=[ConditionClause.model_validate(c) for c in conditions],
                then=then,
                otherwise=otherwise,
            )
        ]
    else:
        steps = then
    return {
        "schema": 2,
        "trigger": trigger,
        "variables": [],
        "steps": [step.model_dump(mode="json", by_alias=True) for step in steps],
    }


class FlowDefinitionV2(BaseModel):
    schema_version: Literal[2] = Field(default=2, alias="schema")
    trigger: FlowTrigger
    variables: list[FlowVariable] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def _upgrade(cls, raw: Any) -> Any:
        if isinstance(raw, dict) and "steps" not in raw and "on_yes" in raw:
            return convert_v1(raw)
        return raw

    @model_validator(mode="after")
    def _validate_tree(self) -> "FlowDefinitionV2":
        spec = TRIGGERS[self.trigger.kind]
        names = [variable.name for variable in self.variables]
        if len(names) != len(set(names)):
            raise ValueError("Há variáveis com o mesmo nome")
        count = 0
        ids: set[str] = set()

        def walk(steps: list[Any], depth: int, in_loop: bool) -> None:
            nonlocal count
            if depth > MAX_DEPTH:
                raise ValueError(f"No máximo {MAX_DEPTH} níveis de passos")
            for step in steps:
                count += 1
                if step.id in ids:
                    step.id = _new_id()
                ids.add(step.id)
                if isinstance(step, ConditionStep):
                    if len(step.conditions) > MAX_CONDITIONS:
                        raise ValueError(f"No máximo {MAX_CONDITIONS} condições por passo")
                    for clause in step.conditions:
                        field = spec.field(clause.field)
                        if field is None:
                            raise ValueError(
                                f"O campo '{clause.field}' não existe no gatilho '{spec.label}'"
                            )
                        if clause.operator not in OPERATORS_BY_TYPE[field.type]:
                            raise ValueError(f"Operador inválido para '{field.label}'")
                        clause.value = _coerce(field.type, clause.operator, clause.value, field)
                    walk(step.then, depth + 1, in_loop)
                    walk(step.otherwise, depth + 1, in_loop)
                elif isinstance(step, ForEachUnitStep):
                    if in_loop:
                        raise ValueError("'Para cada unidade' não pode ficar dentro de outro")
                    if spec.kind is TriggerKind.ACCOUNT_UNCLASSIFIED or spec.kind is TriggerKind.DRE_RECALCULATED:
                        raise ValueError("'Para cada unidade' só vale para inconsistências do NG")
                    walk(step.steps, depth + 1, True)
                elif isinstance(step, (WaitStep, ApprovalStep)):
                    if in_loop:
                        raise ValueError(
                            "Esperar e aprovação ficam fora de 'Para cada unidade'"
                        )
                elif isinstance(step, SendEmailStep):
                    allowed = {*SYSTEM_VARIABLES, *names, *(UNIT_VARIABLES if in_loop else {})}
                    unknown = [m for m in _MARKER.findall(step.subject) if m not in allowed]
                    if unknown:
                        raise ValueError(f"Variável desconhecida no assunto: {{{unknown[0]}}}")
                    if not in_loop and UNIT_RECIPIENT_TOKEN in step.recipients():
                        raise ValueError(
                            "{email_unidade} só pode ser usado dentro de 'Para cada unidade'"
                        )

        walk(self.steps, 1, False)
        if count > MAX_STEPS:
            raise ValueError(f"No máximo {MAX_STEPS} passos por fluxo")
        return self

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


def iter_steps(steps: list[Any]) -> Any:
    for step in steps:
        yield step
        if isinstance(step, ConditionStep):
            yield from iter_steps(step.then)
            yield from iter_steps(step.otherwise)
        elif isinstance(step, ForEachUnitStep):
            yield from iter_steps(step.steps)


def activation_problems_v2(definition: FlowDefinitionV2) -> list[str]:
    """What still blocks turning the flow on (a draft may be incomplete)."""
    problems: list[str] = []
    emails = [s for s in iter_steps(definition.steps) if isinstance(s, SendEmailStep)]
    if not emails:
        problems.append("O fluxo não envia nenhum e-mail")
    for step in emails:
        name = step.label or step.subject or "e-mail"
        if not step.to:
            problems.append(f"{name}: informe ao menos um destinatário em Para")
        if not step.subject:
            problems.append(f"{name}: informe o assunto")
        if not step.body.strip():
            problems.append(f"{name}: o texto do e-mail está vazio")
    for step in iter_steps(definition.steps):
        if isinstance(step, ApprovalStep) and not step.approvers:
            problems.append("Aprovação: informe quem aprova")
        if isinstance(step, ForEachUnitStep) and not (step.recipients or step.default_emails):
            uses_token = any(
                isinstance(inner, SendEmailStep) and UNIT_RECIPIENT_TOKEN in inner.recipients()
                for inner in iter_steps(step.steps)
            )
            if uses_token:
                problems.append("Para cada unidade: cadastre os e-mails por unidade ou um padrão")
    return problems
