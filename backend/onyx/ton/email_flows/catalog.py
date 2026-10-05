"""Closed catalogs of email flows: triggers, the fields each one exposes,
condition operators and e-mail templates.

A flow definition may only reference what is listed here, so the screen, the
validator and the assistant all speak the same small vocabulary. Adding a
trigger or template is a code change, reviewed like any other.
"""

from dataclasses import dataclass
from enum import Enum


class TriggerKind(str, Enum):
    SCHEDULE = "SCHEDULE"
    NG_IMPORT_COMPLETED = "NG_IMPORT_COMPLETED"
    NG_OCCURRENCE_CHANGED = "NG_OCCURRENCE_CHANGED"
    ACCOUNT_UNCLASSIFIED = "ACCOUNT_UNCLASSIFIED"
    DRE_RECALCULATED = "DRE_RECALCULATED"


class FieldType(str, Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    MONEY = "MONEY"
    CHOICE = "CHOICE"


class Operator(str, Enum):
    EQ = "EQ"
    IN = "IN"
    GT = "GT"
    GTE = "GTE"


class TemplateKey(str, Enum):
    INCONSISTENCY_REPORT = "INCONSISTENCY_REPORT"
    ACCOUNT_LIST = "ACCOUNT_LIST"
    SIMPLE_NOTICE = "SIMPLE_NOTICE"


class ItemState(str, Enum):
    """Where an NG inconsistency stands after the latest import."""

    OPEN = "OPEN"
    NEW = "NEW"
    REAPPEARED = "REAPPEARED"
    CHECK_MANUALLY = "CHECK_MANUALLY"
    CORRECTED = "CORRECTED"


ITEM_STATE_LABELS: dict[ItemState, str] = {
    ItemState.OPEN: "aberta",
    ItemState.NEW: "nova",
    ItemState.REAPPEARED: "reapareceu",
    ItemState.CHECK_MANUALLY: "conferir à mão",
    ItemState.CORRECTED: "corrigida no NG",
}

# Changes an "occurrence changed" trigger can listen to.
CHANGE_STATES = (ItemState.NEW, ItemState.CORRECTED, ItemState.REAPPEARED)

OPERATORS_BY_TYPE: dict[FieldType, tuple[Operator, ...]] = {
    FieldType.TEXT: (Operator.EQ, Operator.IN),
    FieldType.CHOICE: (Operator.EQ, Operator.IN),
    FieldType.NUMBER: (Operator.GT, Operator.GTE, Operator.EQ),
    FieldType.MONEY: (Operator.GT, Operator.GTE),
}

OPERATOR_LABELS: dict[Operator, str] = {
    Operator.EQ: "é",
    Operator.IN: "é um de",
    Operator.GT: "maior que",
    Operator.GTE: "maior ou igual a",
}


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    type: FieldType
    # Item fields filter the listed items; summary fields test the whole event.
    per_item: bool
    choices: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class TriggerSpec:
    kind: TriggerKind
    label: str
    description: str
    fields: tuple[FieldSpec, ...]
    templates: tuple[TemplateKey, ...]
    item_noun: str

    def field(self, key: str) -> FieldSpec | None:
        return next((item for item in self.fields if item.key == key), None)


ITEMS_FIELD = FieldSpec("itens", "Quantidade de itens", FieldType.NUMBER, False)
TOTAL_FIELD = FieldSpec("valor_total", "Valor total", FieldType.MONEY, False)

_STATE_CHOICES = tuple((state.value, ITEM_STATE_LABELS[state]) for state in ItemState)

INCONSISTENCY_FIELDS = (
    ITEMS_FIELD,
    TOTAL_FIELD,
    FieldSpec("regra", "Regra", FieldType.TEXT, True),
    FieldSpec("unidade", "Unidade", FieldType.TEXT, True),
    FieldSpec("valor", "Valor", FieldType.MONEY, True),
    FieldSpec("semanas_em_aberto", "Semanas em aberto", FieldType.NUMBER, True),
    FieldSpec("competencia", "Mês de competência", FieldType.NUMBER, True),
    FieldSpec("situacao", "Situação", FieldType.CHOICE, True, _STATE_CHOICES),
)

ACCOUNT_FIELDS = (
    ITEMS_FIELD,
    TOTAL_FIELD,
    FieldSpec("conta", "Código da conta", FieldType.TEXT, True),
    FieldSpec("valor", "Valor lançado", FieldType.MONEY, True),
    FieldSpec("lancamentos", "Lançamentos", FieldType.NUMBER, True),
)

DRE_FIELDS = (FieldSpec("competencia", "Mês de competência", FieldType.NUMBER, False),)

TRIGGERS: dict[TriggerKind, TriggerSpec] = {
    spec.kind: spec
    for spec in (
        TriggerSpec(
            TriggerKind.SCHEDULE,
            "Agendamento",
            "Toda semana ou todo dia, no horário de Brasília. Considera as "
            "inconsistências do NG ainda abertas.",
            INCONSISTENCY_FIELDS,
            (TemplateKey.INCONSISTENCY_REPORT, TemplateKey.SIMPLE_NOTICE),
            "inconsistência",
        ),
        TriggerSpec(
            TriggerKind.NG_IMPORT_COMPLETED,
            "Importação do NG concluída",
            "Ao terminar a revisão de uma nova extração do NG. Considera o estado "
            "de cada inconsistência após a importação.",
            INCONSISTENCY_FIELDS,
            (TemplateKey.INCONSISTENCY_REPORT, TemplateKey.SIMPLE_NOTICE),
            "inconsistência",
        ),
        TriggerSpec(
            TriggerKind.NG_OCCURRENCE_CHANGED,
            "Inconsistência nova, corrigida ou reaparecida",
            "Ao terminar uma importação, considera só as inconsistências que "
            "mudaram de situação.",
            INCONSISTENCY_FIELDS,
            (TemplateKey.INCONSISTENCY_REPORT, TemplateKey.SIMPLE_NOTICE),
            "inconsistência",
        ),
        TriggerSpec(
            TriggerKind.ACCOUNT_UNCLASSIFIED,
            "Conta sem classificação",
            "Ao terminar uma importação, considera as contas do NG que ainda não "
            "têm natureza confirmada.",
            ACCOUNT_FIELDS,
            (TemplateKey.ACCOUNT_LIST, TemplateKey.SIMPLE_NOTICE),
            "conta",
        ),
        TriggerSpec(
            TriggerKind.DRE_RECALCULATED,
            "DRE recalculada",
            "Quando a DRE de um mês é recalculada.",
            DRE_FIELDS,
            (TemplateKey.SIMPLE_NOTICE,),
            "mês",
        ),
    )
}

TEMPLATE_LABELS: dict[TemplateKey, str] = {
    TemplateKey.INCONSISTENCY_REPORT: "Relatório de inconsistências (tabela por unidade)",
    TemplateKey.ACCOUNT_LIST: "Lista de contas sem classificação",
    TemplateKey.SIMPLE_NOTICE: "Aviso curto",
}

# Markers a subject may use; anything else in braces is rejected.
SUBJECT_MARKERS: dict[str, str] = {
    "semana": "semana do ano (ex.: 41)",
    "data": "data da execução (dd/mm/aaaa)",
    "total": "quantidade de itens",
    "valor_total": "valor total em reais",
}

# What the Financeiro must do in the NG for each rule; generic otherwise.
NG_CORRECTIONS: dict[str, str] = {
    "NGF-DUP-DOC": "Excluir no NG o lançamento duplicado",
    "NGF-DUP-EXACT": "Conferir e excluir no NG o lançamento repetido",
    "NGF-UNIT-MISSING": "Informar a unidade administrativa no lançamento",
    "NGF-SRC-ROW-REJECTED": "Corrigir no NG a linha que a importação rejeitou",
    "NGF-DOC-MISSING": "Informar o número do documento no lançamento",
    "NGF-AMT-FINAL-ABSENT": "Informar o valor final do lançamento",
    "NGF-DATE-EMISSION-AFTER-SHEET": "Corrigir a data de emissão ou o mês do lançamento",
}
DEFAULT_NG_CORRECTION = "Corrigir no NG"

# Outbox event kinds the sources emit.
EVENT_KIND_NG_IMPORT = "NG_IMPORT_COMPLETED"
EVENT_KIND_DRE = "DRE_RECALCULATED"

MAX_CONDITIONS = 5
MAX_RECIPIENTS = 200
