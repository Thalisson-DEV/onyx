import uuid
from decimal import Decimal

from onyx.ton.dre.engine import evaluate_lines
from onyx.ton.dre.history import VersionContent, describe_changes, plan_restore
from onyx.ton.dre.models import (
    DreAccountAssignment,
    DreChangeKind,
    DreLineDefinition,
    DreLineType,
    DreOperation,
)
from onyx.ton.dre.xlsx_export import hidden_codes

FOLHA = uuid.uuid4()
PARCELAMENTOS = uuid.uuid4()
NOVA = uuid.uuid4()
NATURES = {FOLHA: "FOLHA", PARCELAMENTOS: "PARCELAMENTOS", NOVA: "CONSULTORIA"}


def _group(code: str, label: str, position: int, hidden: bool = False) -> DreLineDefinition:
    return DreLineDefinition(
        code=code,
        label=label,
        position=position,
        line_type=DreLineType.SUBTOTAL,
        operation=DreOperation.SUM_CHILDREN,
        hidden=hidden,
    )


def _nature(code: str, label: str, position: int, parent: str) -> DreLineDefinition:
    return DreLineDefinition(
        code=code,
        label=label,
        position=position,
        parent_code=parent,
        line_type=DreLineType.SOURCE_SUM,
    )


def _total(operands: list[str], position: int = 9) -> DreLineDefinition:
    return DreLineDefinition(
        code="r",
        label="Resultado",
        position=position,
        line_type=DreLineType.RESULT,
        operation=DreOperation.SUM_LINES,
        operands=operands,
    )


def _link(account: uuid.UUID, line: str) -> DreAccountAssignment:
    return DreAccountAssignment(account_id=account, line_code=line, status="APPROVED")


BASE = VersionContent(
    lines=[
        _group("g1", "Despesas", 1),
        _nature("n1", "Folha", 2, "g1"),
        _group("g2", "Parcelamentos", 3),
        _nature("n2", "Parcelamentos", 4, "g2"),
        _total(["g1", "g2"]),
    ],
    assignments=[_link(FOLHA, "n1"), _link(PARCELAMENTOS, "n2")],
)


def _kinds(before: VersionContent, after: VersionContent) -> set[DreChangeKind]:
    return {change.kind for change in describe_changes(before, after, NATURES)}


def test_out_of_result_and_hidden_are_named_without_a_formula_change() -> None:
    after = VersionContent(
        lines=[
            BASE.lines[0],
            BASE.lines[1],
            _group("g2", "Parcelamentos", 3, hidden=True),
            BASE.lines[3],
            _total(["g1"]),
        ],
        assignments=BASE.assignments,
    )
    assert _kinds(BASE, after) == {DreChangeKind.OUT_OF_RESULT, DreChangeKind.HIDDEN}


def test_rename_move_and_order() -> None:
    after = VersionContent(
        lines=[
            _group("g2", "Parcelamentos", 1),
            _nature("n2", "Parcelamentos", 2, "g2"),
            _nature("n1", "Folha de pagamento", 3, "g2"),
            _group("g1", "Despesas", 4),
            _total(["g1", "g2"]),
        ],
        assignments=BASE.assignments,
    )
    kinds = _kinds(BASE, after)
    assert DreChangeKind.LINE_RENAMED in kinds
    assert DreChangeKind.LINE_MOVED in kinds
    assert DreChangeKind.ORDER_CHANGED in kinds


def test_new_natureza_reads_as_one_added_line() -> None:
    after = VersionContent(
        lines=[*BASE.lines, _nature("n3", "Consultoria", 5, "g1")],
        assignments=[*BASE.assignments, _link(NOVA, "n3")],
    )
    changes = describe_changes(BASE, after, NATURES)
    assert [change.kind for change in changes] == [DreChangeKind.LINE_ADDED]
    assert changes[0].after == "Despesas"


def test_restore_keeps_a_natureza_created_later() -> None:
    later = VersionContent(
        lines=[
            BASE.lines[0],
            BASE.lines[1],
            _nature("n3", "Consultoria", 2, "g1"),
            _group("g2", "Parcelamentos", 3, hidden=True),
            BASE.lines[3],
            _total(["g1"]),
        ],
        assignments=[*BASE.assignments, _link(NOVA, "n3")],
    )
    plan = plan_restore(BASE, later)
    codes = [line.code for line in plan.content.lines]
    assert plan.left_out == []
    assert codes.index("n3") == codes.index("n1") + 1
    assert {item.account_id for item in plan.content.assignments} == {
        FOLHA,
        PARCELAMENTOS,
        NOVA,
    }
    assert next(line for line in plan.content.lines if line.code == "r").operands == [
        "g1",
        "g2",
    ]
    assert not any(line.hidden for line in plan.content.lines)


def test_restore_leaves_out_a_natureza_whose_group_is_gone() -> None:
    later = VersionContent(
        lines=[*BASE.lines, _group("g3", "Mútuo", 6), _nature("n3", "Mútuo", 7, "g3")],
        assignments=[*BASE.assignments, _link(NOVA, "n3")],
    )
    assert plan_restore(BASE, later).left_out == [NOVA]


def test_hidden_group_hides_its_children() -> None:
    lines = [*BASE.lines[:2], _group("g2", "P", 3, hidden=True), BASE.lines[3]]
    assert hidden_codes(lines) == {"g2", "n2"}


def test_excluded_nature_keeps_its_value_but_leaves_the_group() -> None:
    lines = [
        _group("g1", "Custos operacionais", 1),
        _nature("n1", "Folha", 2, "g1"),
        _nature("n2", "Parcelamentos", 3, "g1").model_copy(update={"excluded": True}),
        _total(["g1"]),
    ]
    values = evaluate_lines(lines, {"n1": Decimal(-100), "n2": Decimal(-5000)})
    assert values["n2"] == Decimal(-5000)
    assert values["g1"] == Decimal(-100)
    assert values["r"] == Decimal(-100)
    before = VersionContent(
        lines=[line.model_copy(update={"excluded": False}) for line in lines],
        assignments=[],
    )
    after = VersionContent(lines=lines, assignments=[])
    changes = describe_changes(before, after, NATURES)
    assert [(change.kind, change.line) for change in changes] == [
        (DreChangeKind.OUT_OF_RESULT, "Parcelamentos")
    ]
    assert [(change.kind, change.line) for change in describe_changes(after, before, NATURES)] == [
        (DreChangeKind.INTO_RESULT, "Parcelamentos")
    ]
