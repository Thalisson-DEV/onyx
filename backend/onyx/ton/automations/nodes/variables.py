"""Variable steps. The variable is declared in the automation (name, type,
initial value); these steps change it. The interpreter applies the returned
``value`` and replays it on resume."""

from typing import Any

from onyx.ton.automations.expressions import to_number, to_text
from onyx.ton.automations.registry import (
    ActionContext,
    ActionError,
    NodeSpec,
    OutputSpec,
    ParamSpec,
    register,
)

_NAME = ParamSpec("name", "Variável", "select", required=True, dynamic=False, help="Declare a variável no painel Variáveis.")


def _current(ctx: ActionContext, name: str) -> Any:
    variables = ctx.scope.get("vars") or {}
    if name not in variables:
        raise ActionError(f"A variável '{name}' não foi declarada")
    return variables[name]


def _set(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    name = str(params.get("name") or "")
    _current(ctx, name)
    return {"value": params.get("value")}


def _increment(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    name = str(params.get("name") or "")
    current = to_number(_current(ctx, name)) or 0
    step = to_number(params.get("by"))
    return {"value": current + (1 if step is None else step)}


def _append(ctx: ActionContext, params: dict[str, Any]) -> dict[str, Any]:
    name = str(params.get("name") or "")
    current = _current(ctx, name)
    value = params.get("value")
    if isinstance(current, list):
        return {"value": [*current, *(value if isinstance(value, list) and params.get("spread") else [value])]}
    return {"value": f"{to_text(current)}{to_text(value)}"}


_OUT = (OutputSpec("value", "Novo valor", "any"),)

register(
    NodeSpec(
        type="variable.set",
        group="variables",
        label="Definir variável",
        description="Troca o valor de uma variável.",
        icon="variable",
        params=(_NAME, ParamSpec("value", "Valor", "textarea")),
        outputs=_OUT,
        executor=_set,
        keywords=("set", "atribuir", "valor"),
    )
)
register(
    NodeSpec(
        type="variable.increment",
        group="variables",
        label="Incrementar variável",
        description="Soma um número a uma variável numérica (use negativo para diminuir).",
        icon="plus",
        params=(_NAME, ParamSpec("by", "Somar", "number", default=1)),
        outputs=_OUT,
        executor=_increment,
        keywords=("contador", "somar", "increment"),
    )
)
register(
    NodeSpec(
        type="variable.append",
        group="variables",
        label="Acrescentar à variável",
        description="Acrescenta um item a uma lista ou um texto ao fim de um texto.",
        icon="list",
        params=(
            _NAME,
            ParamSpec("value", "Valor", "textarea"),
            ParamSpec("spread", "Se o valor for uma lista, acrescentar cada item", "boolean", default=False, dynamic=False),
        ),
        outputs=_OUT,
        executor=_append,
        keywords=("append", "lista", "juntar"),
    )
)
