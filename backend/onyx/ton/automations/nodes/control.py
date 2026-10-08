"""Control nodes. Their behavior lives in the interpreter; here are the
catalog entries and the wait-time calculation."""

import datetime
from typing import Any

from onyx.ton.automations.expressions import BRASILIA, _as_datetime, to_number
from onyx.ton.automations.registry import NodeSpec, OutputSpec, ParamSpec, register
from onyx.ton.automations.schedule import WEEKDAY_NAMES

_WEEKDAYS = tuple((str(index), name.capitalize()) for index, name in enumerate(WEEKDAY_NAMES))
MAX_WAIT = datetime.timedelta(days=90)


def wait_until(params: dict[str, Any], now: datetime.datetime) -> datetime.datetime:
    mode = params.get("mode") or "duration"
    if mode == "duration":
        delta = datetime.timedelta(
            days=float(to_number(params.get("days")) or 0),
            hours=float(to_number(params.get("hours")) or 0),
            minutes=float(to_number(params.get("minutes")) or 0),
        )
        if delta <= datetime.timedelta(0):
            raise ValueError("Esperar: informe dias, horas ou minutos")
        if delta > MAX_WAIT:
            raise ValueError("Esperar: no máximo 90 dias")
        return now + delta
    if mode == "datetime":
        moment = _as_datetime(params.get("until"))
        if moment is None:
            raise ValueError("Esperar até: data e hora inválidas")
        if moment - now > MAX_WAIT:
            raise ValueError("Esperar: no máximo 90 dias")
        return max(moment, now)
    weekday = int(to_number(params.get("weekday")) or 0)
    raw = str(params.get("time") or "08:00")
    hour, minute = (int(part) for part in raw.split(":", 1))
    local = now.astimezone(BRASILIA)
    for offset in range(0, 8):
        day = local.date() + datetime.timedelta(days=offset)
        if day.weekday() != weekday:
            continue
        slot = datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=BRASILIA)
        if slot > local:
            return slot
    raise ValueError("Esperar até: dia inválido")


def _wait_summary(params: dict[str, Any]) -> str:
    mode = params.get("mode") or "duration"
    if mode == "duration":
        parts = [
            f"{params.get(key)} {label}"
            for key, label in (("days", "dia(s)"), ("hours", "hora(s)"), ("minutes", "minuto(s)"))
            if to_number(params.get(key))
        ]
        return f"Esperar {' e '.join(parts) or '…'}"
    if mode == "datetime":
        return "Esperar até a data informada"
    day = int(to_number(params.get("weekday")) or 0)
    return f"Esperar até {WEEKDAY_NAMES[day]} às {params.get('time') or '08:00'}"


register(
    NodeSpec(
        type="control.condition",
        group="control",
        label="Condição",
        description="Se as regras forem verdadeiras, segue pelo Sim; senão, pelo Não.",
        icon="branch",
        container="condition",
        params=(ParamSpec("condition", "Regras", "condition", required=True, default={"op": "and", "rules": []}, resolve=False),),
        outputs=(OutputSpec("result", "Resultado (verdadeiro/falso)", "boolean"),),
        keywords=("se", "if", "então", "senão", "decisão"),
    )
)
register(
    NodeSpec(
        type="control.switch",
        group="control",
        label="Escolher caso",
        description="Compara um valor com vários casos e segue pelo caso igual; senão, pelo Padrão.",
        icon="switch",
        container="switch",
        params=(ParamSpec("on", "Valor comparado", "expression", required=True, resolve=False, placeholder="Use ⚡ para escolher o valor"),),
        outputs=(OutputSpec("case", "Caso escolhido", "string"), OutputSpec("value", "Valor comparado", "string")),
        keywords=("switch", "caso", "opções"),
    )
)
register(
    NodeSpec(
        type="control.foreach",
        group="control",
        label="Para cada",
        description="Repete os passos internos para cada item de uma lista. Dentro, use {{ item }}.",
        icon="repeat",
        container="loop",
        params=(ParamSpec("items", "Lista", "expression", required=True, resolve=False, placeholder="Use ⚡ para escolher a lista"),),
        outputs=(OutputSpec("count", "Itens percorridos", "number"), OutputSpec("failed", "Itens com falha", "number")),
        keywords=("loop", "apply to each", "repetir", "cada", "lista"),
    )
)
register(
    NodeSpec(
        type="control.until",
        group="control",
        label="Repetir até",
        description="Repete os passos internos até as regras serem verdadeiras (ou o limite de vezes).",
        icon="refresh",
        container="until",
        params=(
            ParamSpec("condition", "Parar quando", "condition", required=True, default={"op": "and", "rules": []}, resolve=False),
            ParamSpec("max_iterations", "No máximo (vezes)", "number", default=20, dynamic=False, min=1, max=100),
        ),
        outputs=(OutputSpec("iterations", "Vezes executadas", "number"), OutputSpec("condition_met", "Condição atingida", "boolean")),
        keywords=("do until", "enquanto", "loop"),
    )
)
register(
    NodeSpec(
        type="control.scope",
        group="control",
        label="Escopo",
        description="Agrupa passos. Falha se algum passo dentro falhar: use com 'Executar após falha' para tratar erros (tentar/tratar).",
        icon="box",
        container="scope",
        keywords=("try", "catch", "tentar", "tratar", "grupo"),
    )
)
register(
    NodeSpec(
        type="control.parallel",
        group="control",
        label="Ramos paralelos",
        description="Ramos independentes: a falha ou a espera de um não impede os outros.",
        icon="columns",
        container="parallel",
        keywords=("paralelo", "ramos", "simultâneo"),
    )
)
register(
    NodeSpec(
        type="control.wait",
        group="control",
        label="Esperar",
        description="Pausa a execução por um tempo ou até um momento. A execução é retomada sozinha.",
        icon="clock",
        params=(
            ParamSpec("mode", "Esperar", "select", default="duration", dynamic=False, options=(("duration", "Por um tempo"), ("weekday", "Até um dia da semana"), ("datetime", "Até uma data e hora"))),
            ParamSpec("days", "Dias", "number", default=0, min=0, max=90, show_if=("mode", ("duration",))),
            ParamSpec("hours", "Horas", "number", default=0, min=0, max=23, show_if=("mode", ("duration",))),
            ParamSpec("minutes", "Minutos", "number", default=0, min=0, max=59, show_if=("mode", ("duration",))),
            ParamSpec("weekday", "Dia", "select", default="4", options=_WEEKDAYS, show_if=("mode", ("weekday",))),
            ParamSpec("time", "Horário (Brasília)", "time", default="17:00", dynamic=False, show_if=("mode", ("weekday",))),
            ParamSpec("until", "Data e hora", "text", placeholder="31/10/2026 17:00", show_if=("mode", ("datetime",))),
        ),
        outputs=(OutputSpec("resume_at", "Retomou em", "string"),),
        keywords=("delay", "aguardar", "pausa"),
        summary=_wait_summary,
    )
)
register(
    NodeSpec(
        type="control.terminate",
        group="control",
        label="Encerrar",
        description="Termina a execução aqui, com sucesso, falha ou cancelada.",
        icon="stop",
        params=(
            ParamSpec("status", "Situação final", "select", default="succeeded", dynamic=False, options=(("succeeded", "Sucesso"), ("failed", "Falha"), ("cancelled", "Cancelada"))),
            ParamSpec("message", "Mensagem", "text", placeholder="Por que terminou aqui"),
        ),
        keywords=("terminate", "parar", "fim"),
    )
)
