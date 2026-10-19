"""Differences between DRE structure versions, and going back to an old one.

Pure functions: the caller loads the versions and the natureza labels.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from onyx.ton.dre.models import (
    DreAccountAssignment,
    DreChange,
    DreChangeKind,
    DreLineDefinition,
    DreLineType,
    DreOperation,
)

TOP_LEVEL = "Linhas principais da DRE"


@dataclass(frozen=True)
class VersionContent:
    lines: list[DreLineDefinition]
    assignments: list[DreAccountAssignment]


def _is_group(line: DreLineDefinition) -> bool:
    return (
        line.line_type == DreLineType.SUBTOTAL
        and line.operation == DreOperation.SUM_CHILDREN
    )


def _summed_by_totals(lines: list[DreLineDefinition]) -> set[str]:
    """Codes some total reads directly: a group there is "in the result"."""
    return {
        code
        for line in lines
        if line.operation is not None and line.operation != DreOperation.SUM_CHILDREN
        for code in line.operands
    }


def _children_order(lines: list[DreLineDefinition]) -> dict[str | None, list[str]]:
    order: dict[str | None, list[str]] = {}
    for line in sorted(lines, key=lambda item: item.position):
        order.setdefault(line.parent_code, []).append(line.code)
    return order


def describe_changes(
    before: VersionContent,
    after: VersionContent,
    natures: Mapping[UUID, str],
) -> list[DreChange]:
    """What changed from ``before`` to ``after``, line by line."""
    old = {line.code: line for line in before.lines}
    new = {line.code: line for line in after.lines}

    def label(code: str | None) -> str:
        if code is None:
            return TOP_LEVEL
        line = new.get(code) or old.get(code)
        return line.label if line else code

    changes: list[DreChange] = []
    added = [code for code in new if code not in old]
    removed = [code for code in old if code not in new]
    for code in added:
        changes.append(
            DreChange(
                kind=DreChangeKind.LINE_ADDED,
                line=label(code),
                after=label(new[code].parent_code)
                if new[code].parent_code
                else None,
            )
        )
    for code in removed:
        changes.append(
            DreChange(
                kind=DreChangeKind.LINE_REMOVED,
                line=old[code].label,
                before=label(old[code].parent_code)
                if old[code].parent_code
                else None,
            )
        )

    summed_before = _summed_by_totals(before.lines)
    summed_after = _summed_by_totals(after.lines)
    result_moves: set[str] = set()
    for code, line in new.items():
        previous = old.get(code)
        if previous is None:
            continue
        if previous.label != line.label:
            changes.append(
                DreChange(
                    kind=DreChangeKind.LINE_RENAMED,
                    line=line.label,
                    before=previous.label,
                    after=line.label,
                )
            )
        if previous.parent_code != line.parent_code:
            changes.append(
                DreChange(
                    kind=DreChangeKind.LINE_MOVED,
                    line=line.label,
                    before=label(previous.parent_code),
                    after=label(line.parent_code),
                )
            )
        if previous.hidden != line.hidden:
            changes.append(
                DreChange(
                    kind=DreChangeKind.HIDDEN if line.hidden else DreChangeKind.SHOWN,
                    line=line.label,
                )
            )
        if previous.excluded != line.excluded:
            changes.append(
                DreChange(
                    kind=DreChangeKind.OUT_OF_RESULT
                    if line.excluded
                    else DreChangeKind.INTO_RESULT,
                    line=line.label,
                )
            )
        if _is_group(line) and _is_group(previous):
            was_in, is_in = code in summed_before, code in summed_after
            if was_in != is_in:
                result_moves.add(code)
                changes.append(
                    DreChange(
                        kind=DreChangeKind.INTO_RESULT
                        if is_in
                        else DreChangeKind.OUT_OF_RESULT,
                        line=line.label,
                    )
                )

    # A total whose formula changed for a reason not listed above.
    explained = result_moves | set(added) | set(removed)
    for code, line in new.items():
        previous = old.get(code)
        if previous is None or line.operation == DreOperation.SUM_CHILDREN:
            continue
        if line.operation is None and previous.operation is None:
            continue
        difference = set(previous.operands) ^ set(line.operands)
        if previous.operation != line.operation or difference - explained:
            changes.append(
                DreChange(
                    kind=DreChangeKind.FORMULA_CHANGED,
                    line=line.label,
                    before=" + ".join(label(item) for item in previous.operands),
                    after=" + ".join(label(item) for item in line.operands),
                )
            )

    order_before = _children_order(before.lines)
    order_after = _children_order(after.lines)
    for parent, codes in order_after.items():
        if parent is not None and parent not in old:
            continue
        common = [code for code in codes if code in old and old[code].parent_code == parent]
        previous_common = [code for code in order_before.get(parent, []) if code in common]
        if common != previous_common:
            changes.append(
                DreChange(kind=DreChangeKind.ORDER_CHANGED, line=label(parent))
            )

    def nature(account_id: UUID) -> str:
        return natures.get(account_id, str(account_id))

    links_before = {item.account_id: item.line_code for item in before.assignments}
    links_after = {item.account_id: item.line_code for item in after.assignments}
    for account_id, line_code in links_after.items():
        previous_code = links_before.get(account_id)
        if previous_code is None:
            # A new natureza line already reads as "line added".
            if line_code not in added:
                changes.append(
                    DreChange(
                        kind=DreChangeKind.NATURE_LINKED,
                        line=nature(account_id),
                        after=label(line_code),
                    )
                )
        elif previous_code != line_code:
            changes.append(
                DreChange(
                    kind=DreChangeKind.NATURE_RELINKED,
                    line=nature(account_id),
                    before=label(previous_code),
                    after=label(line_code),
                )
            )
    for account_id, line_code in links_before.items():
        if account_id not in links_after and line_code not in removed:
            changes.append(
                DreChange(
                    kind=DreChangeKind.NATURE_UNLINKED,
                    line=nature(account_id),
                    before=label(line_code),
                )
            )
    return changes


@dataclass(frozen=True)
class RestorePlan:
    content: VersionContent
    left_out: list[UUID]


def plan_restore(target: VersionContent, current: VersionContent) -> RestorePlan:
    """The structure of ``target`` with the naturezas created after it.

    Going back must not drop a natureza the Controladoria created later: it is
    kept in its line, or its line is kept in its group, when that still exists
    in the old version. Only naturezas whose group is gone are left out.
    """
    lines = {line.code: line for line in target.lines}
    linked = {item.account_id for item in target.assignments}
    assignments = list(target.assignments)
    current_lines = {line.code: line for line in current.lines}
    left_out: list[UUID] = []
    added: list[DreLineDefinition] = []
    for item in current.assignments:
        if item.account_id in linked:
            continue
        line = lines.get(item.line_code)
        if line is not None and line.line_type == DreLineType.SOURCE_SUM:
            assignments.append(item)
            continue
        source = current_lines.get(item.line_code)
        parent = lines.get(source.parent_code) if source and source.parent_code else None
        if source is None or line is not None or parent is None or not _is_group(parent):
            left_out.append(item.account_id)
            continue
        lines[source.code] = source
        added.append(source)
        assignments.append(item)

    # New lines go after their siblings; then positions are renumbered.
    keys = {code: float(line.position) for code, line in lines.items()}
    for index, line in enumerate(added, start=1):
        siblings = [
            keys[code]
            for code, other in lines.items()
            if other.parent_code == line.parent_code and other not in added
        ]
        assert line.parent_code is not None
        keys[line.code] = max([keys[line.parent_code], *siblings]) + index / 1000
    ordered = sorted(lines.values(), key=lambda line: keys[line.code])
    return RestorePlan(
        content=VersionContent(
            lines=[
                line.model_copy(update={"position": position})
                for position, line in enumerate(ordered, start=1)
            ],
            assignments=assignments,
        ),
        left_out=left_out,
    )
