"""Closing treatments: which version is in force, what it matches, and the
treated amount of an actual fact. Synthetic identifiers only."""

import datetime
import uuid
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError

from onyx.db.ton.financial_domain import actual_amounts
from onyx.db.ton.models import FinancialAccount, FinancialActualFact
from onyx.ton.financial_domain.models import (
    TreatmentCreate,
    TreatmentEffect,
    TreatmentStatus,
)
from onyx.ton.financial_domain.treatments import TreatmentRule, find, in_force

PARCELAMENTOS = uuid.uuid4()
DESPESAS = uuid.uuid4()
UNIT_A = uuid.uuid4()
UNIT_B = uuid.uuid4()
APRIL = datetime.date(2026, 4, 1)


def _rule(
    number: int,
    key: str = "parcelamentos",
    status: TreatmentStatus = TreatmentStatus.ACTIVE,
    effect: TreatmentEffect = TreatmentEffect.EXCLUDE,
    **scope: Any,
) -> TreatmentRule:
    values: dict[str, Any] = {
        "account_id": PARCELAMENTOS,
        "unit_id": None,
        "period_from": None,
        "period_to": None,
        "target_account_id": None,
        **scope,
    }
    return TreatmentRule(
        id=uuid.uuid4(),
        number=number,
        treatment_key=key,
        status=status,
        effect=effect,
        **values,
    )


def test_latest_version_per_key_wins_and_only_active_applies() -> None:
    first = _rule(1)
    blocked = _rule(2, status=TreatmentStatus.BLOCKED)
    other = _rule(3, key="mutuos", account_id=DESPESAS)
    assert in_force([first, blocked, other]) == [other]
    reactivated = _rule(4)
    assert in_force([first, blocked, other, reactivated]) == [reactivated, other]
    revoked = _rule(5, key="mutuos", status=TreatmentStatus.REVOKED)
    assert in_force([first, other, revoked]) == [first]


def test_scope_by_account_unit_and_period() -> None:
    rule = _rule(
        1,
        unit_id=UNIT_A,
        period_from=datetime.date(2026, 4, 1),
        period_to=datetime.date(2026, 5, 1),
    )
    assert find([rule], PARCELAMENTOS, UNIT_A, APRIL) is rule
    assert find([rule], PARCELAMENTOS, UNIT_A, datetime.date(2026, 5, 1)) is rule
    assert find([rule], PARCELAMENTOS, UNIT_A, datetime.date(2026, 6, 1)) is None
    assert find([rule], PARCELAMENTOS, UNIT_B, APRIL) is None
    assert find([rule], DESPESAS, UNIT_A, APRIL) is None
    # A fact without a mapped account never matches.
    assert find([rule], None, UNIT_A, APRIL) is None


def test_newest_decision_wins_on_overlap() -> None:
    whole = _rule(1, key="parcelamentos-todas")
    april = _rule(
        2,
        key="parcelamentos-abril",
        effect=TreatmentEffect.RECLASSIFY,
        target_account_id=DESPESAS,
        period_from=APRIL,
        period_to=APRIL,
    )
    rules = in_force([whole, april])
    assert find(rules, PARCELAMENTOS, UNIT_A, APRIL) is april
    assert find(rules, PARCELAMENTOS, UNIT_A, datetime.date(2026, 5, 1)) is whole


def _fact(**values: Any) -> FinancialActualFact:
    defaults: dict[str, Any] = {
        "account_id": PARCELAMENTOS,
        "original_account_id": None,
        "movement_amount": Decimal("-90900000.00"),
        "final_amount": Decimal("-91000000.00"),
        "treatment_effect": None,
    }
    return cast(FinancialActualFact, SimpleNamespace(**{**defaults, **values}))


def _accounts() -> dict[uuid.UUID, FinancialAccount]:
    return {
        PARCELAMENTOS: cast(
            FinancialAccount,
            SimpleNamespace(id=PARCELAMENTOS, actual_amount_basis="MOVEMENT"),
        ),
        DESPESAS: cast(
            FinancialAccount,
            SimpleNamespace(id=DESPESAS, actual_amount_basis="FINAL"),
        ),
    }


def test_excluded_fact_counts_zero_and_keeps_the_ng_value() -> None:
    basis, amount, original = actual_amounts(
        _fact(treatment_effect="EXCLUDE"), {}, _accounts()
    )
    assert (basis, amount, original) == (
        "MOVEMENT",
        Decimal(0),
        Decimal("-90900000.00"),
    )
    assert actual_amounts(_fact(), {}, _accounts())[1] == Decimal("-90900000.00")


def test_reclassified_fact_keeps_the_basis_of_its_ng_account() -> None:
    fact = _fact(
        account_id=DESPESAS,
        original_account_id=PARCELAMENTOS,
        treatment_effect="RECLASSIFY",
    )
    assert actual_amounts(fact, {}, _accounts()) == (
        "MOVEMENT",
        Decimal("-90900000.00"),
        Decimal("-90900000.00"),
    )
    # An approved basis revision for the source account still wins.
    assert actual_amounts(fact, {PARCELAMENTOS: "FINAL"}, _accounts())[1] == (
        Decimal("-91000000.00")
    )


def test_create_request_requires_justification_evidence_and_key_shape() -> None:
    valid = {
        "treatment_key": "parcelamentos-parcela-paga",
        "title": "Parcelamentos: só a parcela paga",
        "status": "BLOCKED",
        "effect": "REPLACE_BY_SOURCE",
        "account_id": str(PARCELAMENTOS),
        "required_source": "Data de pagamento das parcelas no NG",
        "justification": "Decisão D2 da reunião de 03/10/2026",
        "evidence": "plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md",
    }
    assert TreatmentCreate.model_validate(valid).status is TreatmentStatus.BLOCKED
    for field, value in (
        ("justification", ""),
        ("evidence", ""),
        ("treatment_key", "Parcelamentos Pagos"),
    ):
        with pytest.raises(ValidationError):
            TreatmentCreate.model_validate({**valid, field: value})
