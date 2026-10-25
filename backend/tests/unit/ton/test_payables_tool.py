"""The payables tool answers from the titles the person can see."""

import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from onyx.db.models import User
from onyx.tools.tool_implementations.ton.ton_tool import TonPayablesTool

TODAY = datetime.date.today()


def _row(number: int, status: str, due_in: int, blocking: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        number=number,
        kind="REAL",
        status=status,
        unit_name="TOLEDO-PR",
        supplier_name="Oeste Mangueiras",
        supplier_tax_id="82603929000170",
        account_code="3.02",
        account_label="MANUTENÇÃO",
        document_type="NF",
        document_number=str(19000 + number),
        vehicle_plates=["RKJ7A39"],
        amount=Decimal("100.00"),
        due_date=TODAY + datetime.timedelta(days=due_in),
        payment_method="PIX CNPJ",
        attachment_count=1,
        blocking=blocking,
        attention=0,
        top_issue="Documento já enviado" if blocking else None,
    )


def _compute(rows: list[SimpleNamespace], **kwargs: object) -> dict:
    tool = TonPayablesTool.__new__(TonPayablesTool)
    user = User(id=uuid4(), is_active=True)
    with patch("onyx.db.ton.payables.list_titles", return_value=rows) as listing:
        result = tool.compute(Mock(), user, kwargs)
    # The listing always runs as the person: their units, their visibility.
    assert listing.call_args.args[1] is user
    return result


def test_views_count_late_blocked_and_ready_titles() -> None:
    rows = [
        _row(1, "RELEASED", -2),
        _row(2, "CONFERRED", 1, blocking=1),
        _row(3, "RECEIVED", 10),
        _row(4, "PAID", -5),
    ]
    result = _compute(rows)
    summary = result["resumo"]
    assert summary["abertos"]["titulos"] == 3
    assert summary["vencidos"]["titulos"] == 1
    assert summary["vencem_7_dias"]["titulos"] == 1
    assert summary["impedimento"]["titulos"] == 1
    assert summary["prontos"]["titulos"] == 1
    assert [item["numero"] for item in result["titulos"]] == [
        "CP-000001",
        "CP-000002",
        "CP-000003",
    ]


def test_view_filters_the_list_and_rejects_unknown_views() -> None:
    rows = [_row(1, "RELEASED", -2), _row(2, "CONFERRED", 1, blocking=1)]
    blocked = _compute(rows, view="impedimento")
    assert [item["numero"] for item in blocked["titulos"]] == ["CP-000002"]
    assert blocked["titulos"][0]["ton_apontou"] == "Documento já enviado"
    with pytest.raises(ValueError):
        _compute(rows, view="qualquer")


def test_unknown_title_number_is_reported() -> None:
    with pytest.raises(ValueError):
        _compute([_row(1, "RELEASED", 0)], title_number="CP-000099")
