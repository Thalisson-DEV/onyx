"""Expressions that pass data between automation steps.

A parameter value is a template: plain text with ``{{ expr }}`` parts. When
the whole value is one ``{{ expr }}`` the result keeps its type (a list, a
number); mixed with text it becomes text. This mirrors ``@expr`` and
``@{expr}`` in Power Automate.

``expr`` is parsed here (no ``eval``): literals, paths such as
``steps.buscar.outputs.items[0].valor``, arithmetic, comparisons,
``and``/``or``/``not`` and a closed list of functions. Path access is
null-safe: a missing key gives ``None``.
"""

import datetime
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

BRASILIA = ZoneInfo("America/Sao_Paulo")
ROOTS = ("trigger", "steps", "vars", "item", "loop", "run", "automation", "env")
_TEMPLATE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
# One expression only (no "}}" inside), so the result keeps its type.
_WHOLE = re.compile(r"\{\{((?:(?!\}\}).)*)\}\}", re.DOTALL)
MAX_EXPRESSION_CHARS = 2000


class ExpressionError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Token:
    kind: str  # num, str, name, op, end
    value: Any
    position: int


_TOKEN = re.compile(
    r"""
    (?P<space>\s+)
  | (?P<num>\d+(?:\.\d+)?)
  | (?P<str>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>==|!=|>=|<=|[-+*/%().,\[\]<>!])
    """,
    re.VERBOSE,
)


def _tokens(text: str) -> list[_Token]:
    if len(text) > MAX_EXPRESSION_CHARS:
        raise ExpressionError("Expressão longa demais")
    result: list[_Token] = []
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            raise ExpressionError(f"Caractere inesperado '{text[position]}'")
        kind = match.lastgroup or ""
        raw = match.group(0)
        if kind == "num":
            result.append(_Token("num", float(raw) if "." in raw else int(raw), position))
        elif kind == "str":
            body = raw[1:-1]
            result.append(_Token("str", re.sub(r"\\(.)", r"\1", body), position))
        elif kind == "name":
            result.append(_Token("name", raw, position))
        elif kind == "op":
            result.append(_Token("op", raw, position))
        position = match.end()
    result.append(_Token("end", None, len(text)))
    return result


# ---------------------------------------------------------------------------
# AST and parser
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Literal:
    value: Any


@dataclass(frozen=True)
class Path:
    root: str
    # Each part is a key (str) or an index/key expression node.
    parts: tuple[Any, ...]


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple[Any, ...]


@dataclass(frozen=True)
class Unary:
    op: str
    operand: Any


@dataclass(frozen=True)
class Binary:
    op: str
    left: Any
    right: Any


_BINARY_PRECEDENCE: dict[str, int] = {
    "or": 1,
    "and": 2,
    "==": 4,
    "!=": 4,
    ">": 4,
    ">=": 4,
    "<": 4,
    "<=": 4,
    "+": 5,
    "-": 5,
    "*": 6,
    "/": 6,
    "%": 6,
}


class _Parser:
    def __init__(self, text: str) -> None:
        self.tokens = _tokens(text)
        self.index = 0

    def peek(self) -> _Token:
        return self.tokens[self.index]

    def take(self) -> _Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def expect(self, value: str) -> None:
        token = self.take()
        if token.value != value or token.kind not in ("op", "name"):
            raise ExpressionError(f"Esperava '{value}'")

    def parse(self) -> Any:
        if self.peek().kind == "end":
            raise ExpressionError("Expressão vazia")
        node = self.expression(0)
        if self.peek().kind != "end":
            raise ExpressionError(f"Sobrou '{self.peek().value}' na expressão")
        return node

    def _binary_op(self) -> str | None:
        token = self.peek()
        if token.kind == "op" and token.value in _BINARY_PRECEDENCE:
            return str(token.value)
        if token.kind == "name" and token.value in ("and", "or"):
            return str(token.value)
        return None

    def expression(self, min_precedence: int) -> Any:
        left = self.unary()
        while True:
            op = self._binary_op()
            if op is None or _BINARY_PRECEDENCE[op] < min_precedence:
                return left
            precedence = _BINARY_PRECEDENCE[op]
            self.take()
            right = self.expression(precedence + 1)
            left = Binary(op, left, right)

    def unary(self) -> Any:
        token = self.peek()
        if (token.kind == "op" and token.value in ("-", "!")) or (
            token.kind == "name" and token.value == "not"
        ):
            self.take()
            operand = self.expression(3 if token.value != "-" else 7)
            return Unary("-" if token.value == "-" else "not", operand)
        return self.postfix(self.primary())

    def primary(self) -> Any:
        token = self.take()
        if token.kind == "num" or token.kind == "str":
            return Literal(token.value)
        if token.kind == "op" and token.value == "(":
            node = self.expression(0)
            self.expect(")")
            return node
        if token.kind == "op" and token.value == "[":
            items = []
            if not (self.peek().kind == "op" and self.peek().value == "]"):
                items.append(self.expression(0))
                while self.peek().kind == "op" and self.peek().value == ",":
                    self.take()
                    items.append(self.expression(0))
            self.expect("]")
            return Call("list", tuple(items))
        if token.kind == "name":
            name = str(token.value)
            if name in ("true", "false"):
                return Literal(name == "true")
            if name in ("null", "none"):
                return Literal(None)
            if self.peek().kind == "op" and self.peek().value == "(":
                self.take()
                args = []
                if not (self.peek().kind == "op" and self.peek().value == ")"):
                    args.append(self.expression(0))
                    while self.peek().kind == "op" and self.peek().value == ",":
                        self.take()
                        args.append(self.expression(0))
                self.expect(")")
                if name not in FUNCTIONS:
                    raise ExpressionError(f"Função desconhecida: {name}()")
                low, high = FUNCTIONS[name][0], FUNCTIONS[name][1]
                if not low <= len(args) <= high:
                    raise ExpressionError(f"{name}() recebeu {len(args)} argumento(s)")
                return Call(name, tuple(args))
            if name not in ROOTS:
                raise ExpressionError(
                    f"'{name}' não existe. Use trigger, steps, vars, item, loop, run, automation ou env"
                )
            return Path(name, ())
        raise ExpressionError(f"Não esperava '{token.value}'")

    def postfix(self, node: Any) -> Any:
        while True:
            token = self.peek()
            if token.kind == "op" and token.value == ".":
                self.take()
                key = self.take()
                if key.kind not in ("name", "num"):
                    raise ExpressionError("Esperava um nome depois do ponto")
                node = self._extend(node, str(key.value))
            elif token.kind == "op" and token.value == "[":
                self.take()
                index = self.expression(0)
                self.expect("]")
                node = self._extend(node, index.value if isinstance(index, Literal) else index)
            else:
                return node

    @staticmethod
    def _extend(node: Any, part: Any) -> Any:
        if isinstance(node, Path):
            return Path(node.root, (*node.parts, part))
        return Call("__get", (node, part if not isinstance(part, str) else Literal(part)))


_CACHE: dict[str, Any] = {}


def parse(text: str) -> Any:
    cached = _CACHE.get(text)
    if cached is not None:
        return cached
    node = _Parser(text.strip()).parse()
    if len(_CACHE) < 5000:
        _CACHE[text] = node
    return node


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


def to_number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        raw = value.strip().replace("R$", "").replace(" ", "")
        if not raw:
            return None
        if "," in raw:
            raw = raw.replace(".", "").replace(",", ".")
        try:
            number = Decimal(raw)
        except InvalidOperation:
            return None
        return int(number) if number == number.to_integral_value() and "." not in raw else float(number)
    return None


def truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() not in ("", "false", "0", "não", "nao", "no", "null")
    return bool(value)


def to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, float):
        if math.isfinite(value) and value == int(value):
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".") if math.isfinite(value) else str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def format_money(value: Any) -> str:
    number = to_number(value)
    if number is None:
        number = 0
    text = f"{abs(float(number)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if float(number) < 0 else ''}R$ {text}"


def _as_datetime(value: Any) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo else value.replace(tzinfo=BRASILIA)
    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day, tzinfo=BRASILIA)
    if isinstance(value, str) and value.strip():
        raw = value.strip()
        for pattern in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(raw, pattern).replace(tzinfo=BRASILIA)
            except ValueError:
                pass
        try:
            parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=BRASILIA)
    return None


def _format_date(value: Any, pattern: Any = "dd/mm/aaaa") -> str:
    moment = _as_datetime(value)
    if moment is None:
        return ""
    local = moment.astimezone(BRASILIA)
    mapping = {
        "dd/mm/aaaa hh:mm": "%d/%m/%Y %H:%M",
        "dd/mm/aaaa": "%d/%m/%Y",
        "mm/aaaa": "%m/%Y",
        "aaaa-mm-dd": "%Y-%m-%d",
        "hh:mm": "%H:%M",
    }
    return local.strftime(mapping.get(str(pattern), "%d/%m/%Y"))


def _add_days(value: Any, days: Any) -> str:
    moment = _as_datetime(value)
    number = to_number(days)
    if moment is None or number is None:
        return ""
    return (moment + datetime.timedelta(days=float(number))).isoformat()


def _sum(values: Any, field: Any = None) -> float | int:
    total = Decimal(0)
    for entry in values or []:
        raw = entry.get(field) if field is not None and isinstance(entry, Mapping) else entry
        number = to_number(raw)
        if number is not None:
            total += Decimal(str(number))
    return int(total) if total == total.to_integral_value() else float(total)


def _pluck(values: Any, field: Any) -> list[Any]:
    return [entry.get(str(field)) if isinstance(entry, Mapping) else None for entry in values or []]


def _length(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (str, list, dict, tuple)):
        return len(value)
    return 1


def _contains(container: Any, value: Any) -> bool:
    if container is None:
        return False
    if isinstance(container, str):
        return to_text(value).casefold() in container.casefold()
    if isinstance(container, Mapping):
        return to_text(value) in container
    if isinstance(container, Sequence):
        target = to_text(value).casefold()
        return any(to_text(entry).casefold() == target for entry in container)
    return False


def _split(text: Any, separator: Any = ",") -> list[str]:
    return [part.strip() for part in to_text(text).split(to_text(separator)) if part.strip()]


def _json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise ExpressionError("json(): texto não é um JSON válido") from None
    return value


def _round(value: Any, digits: Any = 0) -> float | int:
    number = to_number(value) or 0
    places = int(to_number(digits) or 0)
    result = round(float(number), places)
    return int(result) if places == 0 else result


def _divide(a: Any, b: Any) -> float | None:
    divisor = to_number(b)
    if not divisor:
        return None
    return float(to_number(a) or 0) / float(divisor)


def _if(condition: Any, then: Any, otherwise: Any = None) -> Any:
    return then if truthy(condition) else otherwise


def _coalesce(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "")), None)


def _now() -> str:
    return datetime.datetime.now(BRASILIA).isoformat()


# name -> (min args, max args, implementation)
FUNCTIONS: dict[str, tuple[int, int, Callable[..., Any]]] = {
    "length": (1, 1, _length),
    "sum": (1, 2, _sum),
    "pluck": (2, 2, _pluck),
    "join": (1, 2, lambda values, sep=", ": to_text(sep).join(to_text(v) for v in values or [])),
    "split": (1, 2, _split),
    "default": (2, 2, lambda value, fallback: fallback if value in (None, "") else value),
    "coalesce": (1, 10, _coalesce),
    "upper": (1, 1, lambda value: to_text(value).upper()),
    "lower": (1, 1, lambda value: to_text(value).lower()),
    "trim": (1, 1, lambda value: to_text(value).strip()),
    "text": (1, 1, to_text),
    "number": (1, 1, lambda value: to_number(value)),
    "format_money": (1, 1, format_money),
    "format_number": (1, 2, lambda value, digits=0: f"{float(to_number(value) or 0):,.{int(to_number(digits) or 0)}f}".replace(",", "X").replace(".", ",").replace("X", ".")),
    "format_date": (1, 2, _format_date),
    "add_days": (2, 2, _add_days),
    "now": (0, 0, _now),
    "add": (2, 2, lambda a, b: (to_number(a) or 0) + (to_number(b) or 0)),
    "sub": (2, 2, lambda a, b: (to_number(a) or 0) - (to_number(b) or 0)),
    "mul": (2, 2, lambda a, b: (to_number(a) or 0) * (to_number(b) or 0)),
    "div": (2, 2, _divide),
    "round": (1, 2, _round),
    "concat": (1, 20, lambda *values: "".join(to_text(v) for v in values)),
    "first": (1, 1, lambda values: values[0] if isinstance(values, (list, str)) and values else None),
    "last": (1, 1, lambda values: values[-1] if isinstance(values, (list, str)) and values else None),
    "json": (1, 1, _json),
    "to_json": (1, 1, lambda value: json.dumps(value, ensure_ascii=False, default=str)),
    "contains": (2, 2, _contains),
    "empty": (1, 1, lambda value: _length(value) == 0),
    "if": (2, 3, _if),
    "list": (0, 100, lambda *values: list(values)),
    "max": (1, 10, lambda *values: max((to_number(v) or 0) for v in (values[0] if len(values) == 1 and isinstance(values[0], list) else values)) if values else None),
    "min": (1, 10, lambda *values: min((to_number(v) or 0) for v in (values[0] if len(values) == 1 and isinstance(values[0], list) else values)) if values else None),
}

FUNCTION_HELP: dict[str, str] = {
    "length": "length(lista) — quantidade de itens",
    "sum": "sum(lista, 'campo') — soma de um campo",
    "pluck": "pluck(lista, 'campo') — só os valores de um campo",
    "join": "join(lista, ', ') — junta em texto",
    "split": "split(texto, ',') — separa em lista",
    "default": "default(valor, 'padrão') — usa o padrão se vazio",
    "coalesce": "coalesce(a, b, …) — o primeiro não vazio",
    "upper": "upper(texto) — maiúsculas",
    "lower": "lower(texto) — minúsculas",
    "trim": "trim(texto) — sem espaços nas pontas",
    "text": "text(valor) — converte em texto",
    "number": "number(texto) — converte em número",
    "format_money": "format_money(valor) — R$ 1.234,56",
    "format_number": "format_number(valor, 2) — 1.234,56",
    "format_date": "format_date(data, 'dd/mm/aaaa') — formata data",
    "add_days": "add_days(data, 3) — soma dias",
    "now": "now() — data e hora atual",
    "add": "add(a, b)",
    "sub": "sub(a, b)",
    "mul": "mul(a, b)",
    "div": "div(a, b)",
    "round": "round(valor, 2)",
    "concat": "concat(a, b, …) — junta textos",
    "first": "first(lista) — primeiro item",
    "last": "last(lista) — último item",
    "json": "json(texto) — lê JSON",
    "to_json": "to_json(valor) — escreve JSON",
    "contains": "contains(lista_ou_texto, valor)",
    "empty": "empty(valor) — vazio?",
    "if": "if(condição, se_sim, se_não)",
    "max": "max(lista) — maior valor",
    "min": "min(lista) — menor valor",
}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _get(container: Any, key: Any) -> Any:
    if container is None:
        return None
    if isinstance(container, Mapping):
        return container.get(key if isinstance(key, str) else to_text(key))
    if isinstance(container, (list, tuple)):
        index = to_number(key)
        if index is None or not isinstance(index, int):
            return None
        return container[index] if -len(container) <= index < len(container) else None
    return None


def _compare(op: str, left: Any, right: Any) -> bool:
    a_num, b_num = to_number(left), to_number(right)
    numeric = a_num is not None and b_num is not None
    if op in ("==", "!="):
        if numeric:
            equal = float(a_num) == float(b_num)  # type: ignore[arg-type]
        elif left in (None, "") or right in (None, ""):
            equal = left in (None, "") and right in (None, "")
        else:
            equal = to_text(left).strip().casefold() == to_text(right).strip().casefold()
        return equal if op == "==" else not equal
    if numeric:
        a, b = float(a_num), float(b_num)  # type: ignore[arg-type]
    else:
        a_dt, b_dt = _as_datetime(left), _as_datetime(right)
        if a_dt is not None and b_dt is not None:
            a, b = a_dt.timestamp(), b_dt.timestamp()
        else:
            return False
    return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]


def evaluate_node(node: Any, scope: Mapping[str, Any]) -> Any:
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Path):
        value = scope.get(node.root)
        for part in node.parts:
            key = part if isinstance(part, (str, int, float)) else evaluate_node(part, scope)
            value = _get(value, key)
        return value
    if isinstance(node, Call):
        if node.name == "__get":
            target = evaluate_node(node.args[0], scope)
            return _get(target, evaluate_node(node.args[1], scope))
        args = [evaluate_node(arg, scope) for arg in node.args]
        try:
            return FUNCTIONS[node.name][2](*args)
        except ExpressionError:
            raise
        except (TypeError, ValueError, ArithmeticError) as error:
            raise ExpressionError(f"{node.name}(): {error}") from None
    if isinstance(node, Unary):
        value = evaluate_node(node.operand, scope)
        if node.op == "-":
            return -(to_number(value) or 0)
        return not truthy(value)
    if isinstance(node, Binary):
        if node.op == "and":
            return truthy(evaluate_node(node.left, scope)) and truthy(evaluate_node(node.right, scope))
        if node.op == "or":
            return truthy(evaluate_node(node.left, scope)) or truthy(evaluate_node(node.right, scope))
        left = evaluate_node(node.left, scope)
        right = evaluate_node(node.right, scope)
        if node.op in ("==", "!=", "<", "<=", ">", ">="):
            return _compare(node.op, left, right)
        if node.op == "+" and (isinstance(left, str) or isinstance(right, str)) and (
            to_number(left) is None or to_number(right) is None
        ):
            return to_text(left) + to_text(right)
        a, b = to_number(left) or 0, to_number(right) or 0
        if node.op == "+":
            return a + b
        if node.op == "-":
            return a - b
        if node.op == "*":
            return a * b
        if node.op == "/":
            return None if b == 0 else a / b
        if node.op == "%":
            return None if b == 0 else a % b
    raise ExpressionError("Expressão inválida")


def evaluate(text: str, scope: Mapping[str, Any]) -> Any:
    return evaluate_node(parse(text), scope)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def is_template(value: Any) -> bool:
    return isinstance(value, str) and "{{" in value


def render(value: Any, scope: Mapping[str, Any]) -> Any:
    """Resolve a template. Non-strings pass through; lists and dicts are
    resolved recursively."""
    if isinstance(value, list):
        return [render(entry, scope) for entry in value]
    if isinstance(value, dict):
        return {key: render(entry, scope) for key, entry in value.items()}
    if not isinstance(value, str) or "{{" not in value:
        return value
    whole = _WHOLE.fullmatch(value.strip())
    if whole is not None:
        return evaluate(whole.group(1), scope)
    return _TEMPLATE.sub(lambda match: to_text(evaluate(match.group(1), scope)), value)


def render_text(value: Any, scope: Mapping[str, Any]) -> str:
    return to_text(render(value, scope))


# ---------------------------------------------------------------------------
# Static analysis (used by the checker)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reference:
    root: str
    name: str | None  # step id, variable name or loop id
    rest: tuple[str, ...]


def _references(node: Any, found: list[Reference]) -> None:
    if isinstance(node, Path):
        parts = [part for part in node.parts]
        name = parts[0] if parts and isinstance(parts[0], str) else None
        rest = tuple(part for part in parts[1:] if isinstance(part, str))
        found.append(Reference(node.root, name, rest))
        for part in parts:
            if not isinstance(part, (str, int, float)):
                _references(part, found)
    elif isinstance(node, Call):
        for arg in node.args:
            _references(arg, found)
    elif isinstance(node, Unary):
        _references(node.operand, found)
    elif isinstance(node, Binary):
        _references(node.left, found)
        _references(node.right, found)


def template_references(value: Any) -> list[Reference]:
    """Every path a template reads. Raises ExpressionError on a parse error."""
    found: list[Reference] = []
    if isinstance(value, list):
        for entry in value:
            found.extend(template_references(entry))
        return found
    if isinstance(value, dict):
        for entry in value.values():
            found.extend(template_references(entry))
        return found
    if not isinstance(value, str) or "{{" not in value:
        return found
    if value.count("{{") != value.count("}}"):
        raise ExpressionError("Chaves {{ }} sem fechamento")
    for match in _TEMPLATE.finditer(value):
        _references(parse(match.group(1)), found)
    return found
