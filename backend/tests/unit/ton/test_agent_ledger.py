import datetime
from decimal import Decimal

import pytest

from onyx.db.ton.agent_ledger import SUGGESTED_BANDS, suggest_criticality
from onyx.db.ton.enums import OccurrenceCriticality
from onyx.ton.automations.nodes.ledger import _cases_recorded
from onyx.ton.automations.registry import TriggerContext
from onyx.ton.automations.templates import sweep_definition
from onyx.ton.automations.definition import AutomationDefinition


@pytest.mark.parametrize(
    "impact, revenue, expected",
    [
        (Decimal(10_000), Decimal(1_000_000), OccurrenceCriticality.CRITICAL),
        (Decimal(3_000), Decimal(1_000_000), OccurrenceCriticality.HIGH),
        (Decimal(1_000), Decimal(1_000_000), OccurrenceCriticality.MEDIUM),
        (Decimal(999), Decimal(1_000_000), OccurrenceCriticality.MONITORING),
        (Decimal(50_000), Decimal(0), OccurrenceCriticality.MONITORING),
    ],
)
def test_pad_ctrl_bands(impact: Decimal, revenue: Decimal, expected: OccurrenceCriticality) -> None:
    criticality, share = suggest_criticality(impact, revenue, SUGGESTED_BANDS)
    assert criticality is expected
    assert (share is None) == (revenue == 0)


def _context() -> TriggerContext:
    return TriggerContext(
        session=None,
        owner=None,
        now=datetime.datetime(2026, 10, 21, tzinfo=datetime.timezone.utc),
        automation_id="a",
        automation_name="Ouvinte",
    )


CASES = [
    {"teste": "T3", "criticidade": "Crítico", "situacao": "Novo", "valor": 10.0, "unidade": "A"},
    {"teste": "T3", "criticidade": "Médio", "situacao": "Novo", "valor": 5.0, "unidade": "A"},
    {"teste": "T9", "criticidade": "Alto", "situacao": "Repetido", "valor": 7.0, "unidade": "B"},
]


def test_trigger_keeps_new_cases_at_or_above_the_criticality() -> None:
    output = _cases_recorded(
        _context(),
        {"min_criticality": "HIGH", "only_new": True, "tests": []},
        {"cases": CASES, "origem": "varredura R1", "teste": "T3, T9"},
    )
    assert output is not None
    assert output["count"] == 1
    assert output["items"][0]["criticidade"] == "Crítico"
    assert output["origem"] == "varredura R1"


def test_trigger_filters_by_test_and_includes_repeats_when_asked() -> None:
    output = _cases_recorded(
        _context(),
        {"min_criticality": "MONITORING", "only_new": False, "tests": ["T9"]},
        {"cases": CASES},
    )
    assert output is not None and output["count"] == 1


def test_trigger_does_not_run_without_matching_cases() -> None:
    assert (
        _cases_recorded(
            _context(),
            {"min_criticality": "CRITICAL", "only_new": True, "tests": ["T9"]},
            {"cases": CASES},
        )
        is None
    )


def test_sweep_template_is_a_valid_definition() -> None:
    from onyx.ton.automations.validation import validate

    definition = AutomationDefinition.model_validate(sweep_definition(["T3"], "06:00"))
    assert definition.trigger.params["time"] == "06:00"
    assert not [issue for issue in validate(definition) if issue.severity == "error"]
