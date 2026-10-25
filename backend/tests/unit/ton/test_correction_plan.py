import datetime
from decimal import Decimal

from onyx.ton.correction import rules
from onyx.ton.correction.catalog import GENERIC, text_for

JUL = datetime.date(2026, 7, 1)
FEB = datetime.date(2026, 2, 1)


def test_criticality_uses_the_worst_month_share() -> None:
    result = rules.criticality({JUL: (Decimal("7628503.61"), Decimal("11720000"))}, 1)
    assert result.level == "CRITICAL"
    assert result.reason.startswith("65,1% da receita faturada de 07/2026")


def test_criticality_bands() -> None:
    revenue = Decimal("10000000")
    assert rules.criticality({FEB: (Decimal("50000"), revenue)}, 1).level == "HIGH"
    assert rules.criticality({FEB: (Decimal("15000"), revenue)}, 1).level == "MEDIUM"
    assert rules.criticality({FEB: (Decimal("5000"), revenue)}, 1).level == "MONITORING"


def test_repeated_case_is_at_least_high() -> None:
    small = {
        FEB: (Decimal("700"), Decimal("10000000")),
        JUL: (Decimal("900"), Decimal("11000000")),
    }
    result = rules.criticality(small, 2)
    assert result.level == "HIGH"
    assert result.reason == "aparece em 2 meses"


def test_case_without_amount_is_monitoring() -> None:
    assert rules.criticality({}, 1).level == "MONITORING"


def test_due_dates_follow_the_regua() -> None:
    friday = datetime.date(2026, 10, 23)
    assert rules.default_due_date("CRITICAL", friday) == datetime.date(2026, 10, 30)
    assert rules.default_due_date("HIGH", friday) == datetime.date(2026, 11, 7)
    assert rules.default_due_date("MEDIUM", friday) == datetime.date(2026, 11, 22)


def test_situation() -> None:
    today = datetime.date(2026, 10, 26)
    base = dict(decision=None, owner="Financeiro", due_date=None, today=today)
    assert rules.situation(open_count=0, fixed_count=3, **base).code == "VERIFIED"
    assert rules.situation(open_count=2, fixed_count=1, **base).code == "ASSIGNED"
    assert (
        rules.situation(open_count=2, fixed_count=0, **{**base, "owner": None}).code
        == "UNASSIGNED"
    )
    overdue = rules.situation(
        open_count=1, fixed_count=0, **{**base, "due_date": datetime.date(2026, 10, 21)}
    )
    assert overdue.code == "OVERDUE"
    assert overdue.label == "Prazo vencido há 3 dias úteis"
    accepted = rules.situation(
        open_count=1, fixed_count=0, **{**base, "decision": "RISK_ACCEPTED"}
    )
    assert accepted.code == "ACCEPTED"


def test_catalog_has_plain_text_for_the_active_rules() -> None:
    for code in (
        "NGF-DUP-EXACT",
        "NGF-DUP-DOC",
        "NGF-UNIT-MISSING",
        "NGF-SRC-ROW-REJECTED",
    ):
        assert text_for(code) is not GENERIC
    assert text_for("UNKNOWN") is GENERIC
