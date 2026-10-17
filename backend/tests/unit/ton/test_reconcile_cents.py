from datetime import date
from decimal import Decimal
from uuid import uuid4

from onyx.db.ton.financial_domain import _reconcile


def test_billing_third_decimal_still_matches_ng_cents() -> None:
    unit, account, run = uuid4(), uuid4(), uuid4()
    actual = {
        "id": uuid4(),
        "account_id": account,
        "unit_id": unit,
        "movement_amount": Decimal("3297457.08"),
        "calendar_period": date(2026, 9, 1),
        "emission_date": date(2026, 9, 1),
    }
    billing = {
        "id": uuid4(),
        "account_id": account,
        "unit_id": unit,
        "service_amount": Decimal("3297457.078"),
        "emission_date": date(2026, 9, 1),
    }
    items = _reconcile(
        [actual],
        [billing],
        {actual["id"]: "528"},
        {billing["id"]: "528"},
        {account},
        run,
    )
    assert [item["status"] for item in items] == ["MATCHED"]


def test_a_real_amount_difference_stays_ambiguous() -> None:
    unit, account, run = uuid4(), uuid4(), uuid4()
    actual = {
        "id": uuid4(),
        "account_id": account,
        "unit_id": unit,
        "movement_amount": Decimal("100.00"),
        "calendar_period": date(2026, 9, 1),
        "emission_date": date(2026, 9, 1),
    }
    billing = {
        "id": uuid4(),
        "account_id": account,
        "unit_id": unit,
        "service_amount": Decimal("100.02"),
        "emission_date": date(2026, 9, 1),
    }
    items = _reconcile(
        [actual],
        [billing],
        {actual["id"]: "1"},
        {billing["id"]: "1"},
        {account},
        run,
    )
    assert {item["status"] for item in items} == {"AMBIGUOUS"}
