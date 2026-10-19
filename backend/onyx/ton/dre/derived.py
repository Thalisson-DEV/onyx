"""DRE structures derived from the managerial one (Caixa, Econômica).

A derived structure keeps the natureza lines of its base, with the same codes
and assignments, regrouped into the blocks of the Controladoria's simplified
model, plus totals and manual-adjustment lines. When the base changes, the
derived structure follows: new naturezas land with their siblings, removed
ones leave, renamed ones take the new name. Moves the Controladoria makes in
the derived structure itself are kept.

Pure functions: the caller loads and stores the versions.
"""

from dataclasses import dataclass, field

from onyx.ton.dre.models import (
    DreLineDefinition,
    DreLineType,
    DreOperation,
)

# Sources a group takes: a base line code (natureza) wins over a base group
# code; "*" takes whatever no other group claims. A group no total reads stays
# out of the result.
REST = "*"


@dataclass(frozen=True)
class Block:
    code: str
    label: str
    kind: str  # "group" | "manual" | "total" | "result"
    sources: tuple[str, ...] = ()
    operands: tuple[str, ...] = ()


@dataclass(frozen=True)
class Template:
    key: str
    structure_key: str
    label: str
    blocks: tuple[Block, ...] = field(default_factory=tuple)


OUTSIDE = Block(
    "s9",
    "FORA DO RESULTADO (financiamento, investimento, mútuo, não gerenciais)",
    "group",
    sources=(REST,),
)
CAIXA = Template(
    key="caixa",
    structure_key="vale-norte-caixa",
    label="DRE Caixa (simplificada)",
    blocks=(
        Block("s1", "FATURAMENTO (NG, já líquido de retenções)", "group", ("g1",)),
        Block("m1", "(-) RETENÇÕES ADICIONAIS", "manual"),
        Block("t1", "= RECEITA LÍQUIDA", "total", operands=("s1", "m1")),
        Block(
            "s2",
            "(-) PAGAMENTOS OPERACIONAIS / OUTROS",
            "group",
            ("g2", "g3", "n9.02"),
        ),
        Block("t2", "= RESULTADO ANTES DE TAXAS E AJUSTES", "total", operands=("t1", "s2")),
        Block("s3", "(-) TAXAS", "group", ("n3.13", "n3.16")),
        Block("m2", "(-) PROVISÕES (AJUSTE GERENCIAL)", "manual"),
        Block("m3", "(-) TRIBUTOS NÃO PAGOS (AJUSTE GERENCIAL)", "manual"),
        Block("m4", "(+/-) AJUSTES DO IR", "manual"),
        Block(
            "r1",
            "= RESULTADO AJUSTADO (CAIXA)",
            "result",
            operands=("t2", "s3", "m2", "m3", "m4"),
        ),
        OUTSIDE,
    ),
)
ECONOMICA = Template(
    key="economica",
    structure_key="vale-norte-economica",
    label="DRE Econômica (simplificada)",
    blocks=(
        Block("s1", "FATURAMENTO (NG, já líquido de retenções)", "group", ("g1",)),
        Block("m1", "(-) RETENÇÕES ADICIONAIS", "manual"),
        Block("m4", "(+/-) AJUSTES DO IR", "manual"),
        Block("t1", "= RECEITA LÍQUIDA ECONÔMICA", "total", operands=("s1", "m1", "m4")),
        Block(
            "s2",
            "(-) CUSTOS E DESPESAS POR COMPETÊNCIA",
            "group",
            ("g2", "g3", "n9.02"),
        ),
        Block("m5", "(+/-) AJUSTES DE CUSTOS / RECEITAS", "manual"),
        Block(
            "r1",
            "= RESULTADO ECONÔMICO",
            "result",
            operands=("t1", "s2", "m5"),
        ),
        OUTSIDE,
    ),
)
TEMPLATES: dict[str, Template] = {item.key: item for item in (CAIXA, ECONOMICA)}


def _natures(lines: list[DreLineDefinition]) -> list[DreLineDefinition]:
    groups = {line.code for line in lines if line.operation == DreOperation.SUM_CHILDREN}
    return sorted(
        (
            line
            for line in lines
            if line.line_type == DreLineType.SOURCE_SUM and line.parent_code in groups
        ),
        key=lambda line: line.position,
    )


def _group_for(template: Template, nature: DreLineDefinition) -> str:
    groups = [block for block in template.blocks if block.kind == "group"]
    for block in groups:
        if nature.code in block.sources:
            return block.code
    for block in groups:
        if nature.parent_code in block.sources:
            return block.code
    return next(block.code for block in groups if REST in block.sources)


def build(template: Template, base: list[DreLineDefinition]) -> list[DreLineDefinition]:
    """The first version of a derived structure from the base lines."""
    placed: dict[str, list[DreLineDefinition]] = {}
    for nature in _natures(base):
        placed.setdefault(_group_for(template, nature), []).append(nature)
    return _assemble(template, placed)


def _assemble(
    template: Template, placed: dict[str, list[DreLineDefinition]]
) -> list[DreLineDefinition]:
    lines: list[DreLineDefinition] = []
    for block in template.blocks:
        children = placed.get(block.code, [])
        if block.kind == "group" and not children:
            continue
        if block.kind == "group":
            lines.append(
                DreLineDefinition(
                    code=block.code,
                    label=block.label,
                    position=len(lines) + 1,
                    line_type=DreLineType.SUBTOTAL,
                    operation=DreOperation.SUM_CHILDREN,
                )
            )
            for child in children:
                lines.append(
                    child.model_copy(
                        update={"position": len(lines) + 1, "parent_code": block.code}
                    )
                )
        elif block.kind == "manual":
            lines.append(
                DreLineDefinition(
                    code=block.code,
                    label=block.label,
                    position=len(lines) + 1,
                    line_type=DreLineType.SOURCE_SUM,
                )
            )
        else:
            present = {line.code for line in lines}
            lines.append(
                DreLineDefinition(
                    code=block.code,
                    label=block.label,
                    position=len(lines) + 1,
                    line_type=DreLineType.RESULT
                    if block.kind == "result"
                    else DreLineType.SUBTOTAL,
                    operation=DreOperation.SUM_LINES,
                    operands=[code for code in block.operands if code in present]
                    or [lines[-1].code],
                )
            )
    return lines


def sync(
    template: Template,
    derived: list[DreLineDefinition],
    base: list[DreLineDefinition],
) -> list[DreLineDefinition] | None:
    """The derived lines updated to the base, or None when nothing changed."""
    base_natures = {line.code: line for line in _natures(base)}
    current = {line.code: line for line in derived}
    derived_natures = {line.code: line for line in _natures(derived)}
    lines: list[DreLineDefinition] = []
    for line in sorted(derived, key=lambda item: item.position):
        if line.code in derived_natures and line.code not in base_natures:
            continue
        source = base_natures.get(line.code)
        if source is not None and source.label != line.label:
            line = line.model_copy(update={"label": source.label})
        lines.append(line)
    groups = {
        line.code for line in lines if line.operation == DreOperation.SUM_CHILDREN
    }
    added: list[tuple[str, DreLineDefinition]] = []
    for code, nature in base_natures.items():
        if code in current:
            continue
        # With its base siblings, where the Controladoria keeps them; else
        # where the template puts it.
        siblings = [
            current[other].parent_code
            for other, item in base_natures.items()
            if item.parent_code == nature.parent_code
            and other in current
            and current[other].parent_code in groups
        ]
        target = (
            max(set(siblings), key=siblings.count)
            if siblings
            else _group_for(template, nature)
        )
        added.append((target, nature))
    # A group emptied by removals goes; a new one the template has comes in.
    emptied = {
        code
        for code in groups
        if not any(line.parent_code == code for line in lines)
        and not any(target == code for target, _ in added)
    }
    if not added and not emptied and lines == sorted(
        derived, key=lambda item: item.position
    ):
        return None
    lines = [line for line in lines if line.code not in emptied]
    missing_groups = {target for target, _ in added} - {line.code for line in lines}
    for code in missing_groups:
        block = next(item for item in template.blocks if item.code == code)
        lines.append(
            DreLineDefinition(
                code=block.code,
                label=block.label,
                position=len(lines) + 1,
                line_type=DreLineType.SUBTOTAL,
                operation=DreOperation.SUM_CHILDREN,
            )
        )
    for target, nature in added:
        index = max(
            (i for i, line in enumerate(lines) if line.code == target or line.parent_code == target),
        )
        lines.insert(index + 1, nature.model_copy(update={"parent_code": target}))
    # Totals must not read a group that left.
    present = {line.code for line in lines}
    lines = [
        line.model_copy(
            update={"operands": [code for code in line.operands if code in present]}
        )
        if line.operation == DreOperation.SUM_LINES
        else line
        for line in lines
    ]
    return [
        line.model_copy(update={"position": position})
        for position, line in enumerate(lines, start=1)
    ]
