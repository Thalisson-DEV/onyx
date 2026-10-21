"""Edits to a DRE structure that the chat proposes, applied on a copy."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from onyx.ton.dre.engine import calculation_order
from onyx.ton.dre.models import (
    BillingField,
    BillingPeriodBasis,
    DreAccountAssignment,
    DreLineDefinition,
    DreLineSource,
    DreLineType,
    DreOperation,
)

OperationKind = Literal[
    "add_line",
    "add_group",
    "rename_line",
    "move_line",
    "set_line_source",
    "set_formula",
    "hide_line",
    "show_line",
    "exclude_line",
    "include_line",
    "remove_line",
    "move_nature",
]


class LineOperation(BaseModel):
    """One edit. Fields not used by ``op`` are ignored."""

    model_config = ConfigDict(extra="forbid")
    op: OperationKind
    # Line the edit acts on (not used by add_line/add_group/move_nature).
    code: str | None = Field(default=None, max_length=100)
    label: str | None = Field(default=None, min_length=1, max_length=500)
    # Group the line goes under; None puts it at the top level.
    parent_code: str | None = Field(default=None, max_length=100)
    # The new or moved line comes right after this line (and its children).
    after_code: str | None = Field(default=None, max_length=100)
    source: DreLineSource | None = None
    billing_fields: list[BillingField] = Field(default_factory=list, max_length=10)
    billing_period: BillingPeriodBasis | None = None
    negate: bool | None = None
    operation: DreOperation | None = None
    operands: list[str] = Field(default_factory=list, max_length=20)
    # move_nature: natureza code (as in the NG plan) and the line that gets it.
    nature_code: str | None = Field(default=None, max_length=100)
    target_code: str | None = Field(default=None, max_length=100)


class StructureEdit(BaseModel):
    lines: list[DreLineDefinition]
    assignments: list[DreAccountAssignment]


def _is_group(line: DreLineDefinition) -> bool:
    return (
        line.line_type == DreLineType.SUBTOTAL
        and line.operation == DreOperation.SUM_CHILDREN
    )


def _new_code(codes: set[str]) -> str:
    number = 1
    while f"a{number}" in codes:
        number += 1
    return f"a{number}"


class _Draft:
    def __init__(self, lines: list[DreLineDefinition]) -> None:
        self.order = sorted(lines, key=lambda item: item.position)

    def index(self, code: str) -> int:
        for position, line in enumerate(self.order):
            if line.code == code:
                return position
        raise ValueError(f"A linha {code} não existe na estrutura")

    def get(self, code: str) -> DreLineDefinition:
        return self.order[self.index(code)]

    def put(self, line: DreLineDefinition) -> None:
        self.order[self.index(line.code)] = line

    def subtree_end(self, code: str) -> int:
        """Index right after ``code`` and all its descendants."""
        start = self.index(code)
        inside = {code}
        end = start + 1
        while end < len(self.order) and self.order[end].parent_code in inside:
            inside.add(self.order[end].code)
            end += 1
        return end

    def insertion_index(self, parent_code: str | None, after_code: str | None) -> int:
        if after_code is not None:
            after = self.get(after_code)
            if after.code != parent_code and after.parent_code != parent_code:
                raise ValueError(
                    f"A linha {after_code} não fica no mesmo grupo da linha nova"
                )
            if after.code == parent_code:
                return self.index(after_code) + 1
            return self.subtree_end(after_code)
        if parent_code is not None:
            return self.subtree_end(parent_code)
        raise ValueError("Diga depois de qual linha a linha nova entra")

    def check_parent(self, parent_code: str | None) -> None:
        if parent_code is not None and not _is_group(self.get(parent_code)):
            raise ValueError(f"A linha {parent_code} não é um grupo")

    def lines(self) -> list[DreLineDefinition]:
        return [
            line.model_copy(update={"position": position})
            for position, line in enumerate(self.order)
        ]


def _source_line(operation: LineOperation, code: str) -> DreLineDefinition:
    source = operation.source or DreLineSource.NG_ACCOUNTS
    return DreLineDefinition(
        code=code,
        label=operation.label or "",
        position=0,
        parent_code=operation.parent_code,
        line_type=DreLineType.SOURCE_SUM,
        source=source,
        billing_fields=operation.billing_fields
        if source == DreLineSource.BILLING
        else [],
        billing_period=operation.billing_period or BillingPeriodBasis.EMISSION,
        negate=bool(operation.negate),
    )


def apply_operations(
    lines: list[DreLineDefinition],
    assignments: list[DreAccountAssignment],
    operations: list[LineOperation],
    accounts_by_code: dict[str, UUID],
) -> StructureEdit:
    """The structure after ``operations``, in order. Raises ValueError with a
    message in Portuguese when an edit does not fit the structure."""
    draft = _Draft(lines)
    mapping = {item.account_id: item for item in assignments}
    for operation in operations:
        codes = {line.code for line in draft.order}
        if operation.op in ("add_line", "add_group"):
            if not operation.label:
                raise ValueError("A linha nova precisa de um nome")
            draft.check_parent(operation.parent_code)
            code = _new_code(codes)
            if operation.op == "add_line":
                line = _source_line(operation, code)
            else:
                line = DreLineDefinition(
                    code=code,
                    label=operation.label,
                    position=0,
                    parent_code=operation.parent_code,
                    line_type=DreLineType.SUBTOTAL,
                    operation=DreOperation.SUM_CHILDREN,
                )
            index = draft.insertion_index(operation.parent_code, operation.after_code)
            draft.order.insert(index, line)
            continue
        if operation.op == "move_nature":
            if not operation.nature_code or not operation.target_code:
                raise ValueError("Informe a natureza e a linha de destino")
            account_id = accounts_by_code.get(operation.nature_code)
            if account_id is None:
                raise ValueError(f"A natureza {operation.nature_code} não existe")
            target = draft.get(operation.target_code)
            if (
                target.line_type != DreLineType.SOURCE_SUM
                or target.source != DreLineSource.NG_ACCOUNTS
            ):
                raise ValueError(
                    f"A linha {target.label} não recebe naturezas do NG"
                )
            mapping[account_id] = DreAccountAssignment(
                account_id=account_id, line_code=target.code, status="APPROVED"
            )
            continue
        if operation.code is None:
            raise ValueError("Informe a linha")
        line = draft.get(operation.code)
        if operation.op == "rename_line":
            if not operation.label:
                raise ValueError("Informe o novo nome")
            draft.put(line.model_copy(update={"label": operation.label}))
        elif operation.op in ("hide_line", "show_line"):
            draft.put(line.model_copy(update={"hidden": operation.op == "hide_line"}))
        elif operation.op in ("exclude_line", "include_line"):
            if line.parent_code is None:
                raise ValueError("Só uma linha dentro de um grupo sai do resultado")
            draft.put(
                line.model_copy(update={"excluded": operation.op == "exclude_line"})
            )
        elif operation.op == "set_line_source":
            if line.line_type != DreLineType.SOURCE_SUM:
                raise ValueError(f"A linha {line.label} é um total, não uma origem")
            updated = _source_line(
                operation.model_copy(
                    update={
                        "label": operation.label or line.label,
                        "parent_code": line.parent_code,
                    }
                ),
                line.code,
            ).model_copy(update={"hidden": line.hidden, "excluded": line.excluded})
            if updated.source != DreLineSource.NG_ACCOUNTS:
                linked = [
                    key for key, item in mapping.items() if item.line_code == line.code
                ]
                if linked:
                    raise ValueError(
                        f"A linha {line.label} ainda tem {len(linked)} natureza(s) do NG; mova-as antes"
                    )
            draft.put(updated)
        elif operation.op == "set_formula":
            if line.line_type == DreLineType.SOURCE_SUM or _is_group(line):
                raise ValueError(f"A linha {line.label} não tem fórmula")
            if operation.operation is None:
                raise ValueError("Informe a operação da fórmula")
            draft.put(
                line.model_copy(
                    update={
                        "operation": operation.operation,
                        "operands": operation.operands,
                    }
                )
            )
        elif operation.op == "move_line":
            draft.check_parent(operation.parent_code)
            start = draft.index(line.code)
            end = draft.subtree_end(line.code)
            block = draft.order[start:end]
            if operation.parent_code in {item.code for item in block}:
                raise ValueError("Uma linha não pode ir para dentro dela mesma")
            del draft.order[start:end]
            block[0] = block[0].model_copy(update={"parent_code": operation.parent_code})
            index = draft.insertion_index(operation.parent_code, operation.after_code)
            draft.order[index:index] = block
        elif operation.op == "remove_line":
            if any(item.parent_code == line.code for item in draft.order):
                raise ValueError(f"O grupo {line.label} ainda tem linhas")
            if any(item.line_code == line.code for item in mapping.values()):
                raise ValueError(
                    f"A linha {line.label} ainda tem naturezas do NG; mova-as antes"
                )
            if any(line.code in item.operands for item in draft.order):
                raise ValueError(f"Um total usa a linha {line.label}")
            del draft.order[draft.index(line.code)]
    result = draft.lines()
    calculation_order(result)
    return StructureEdit(
        lines=result,
        assignments=sorted(mapping.values(), key=lambda item: str(item.account_id)),
    )
