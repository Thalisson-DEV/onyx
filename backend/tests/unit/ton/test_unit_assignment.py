from uuid import uuid4

from onyx.db.ton.unit_assignment import latest_assignments


def test_the_newest_assignment_of_each_record_is_in_force() -> None:
    head_office, mossoro = uuid4(), uuid4()
    rows = [
        ("rec:a#1", mossoro),  # newest first
        ("rec:b#1", head_office),
        ("rec:a#1", head_office),
    ]
    assert latest_assignments(rows) == {"rec:a#1": mossoro, "rec:b#1": head_office}


def test_an_assignment_without_a_unit_undoes_the_earlier_one() -> None:
    mossoro = uuid4()
    rows = [("rec:a#1", None), ("rec:a#1", mossoro)]
    assert latest_assignments(rows) == {}
