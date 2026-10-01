"""Coverage registration describes capability without activating client rules."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.ton.capabilities import capability_registry
from onyx.db.ton.models import RuleVersion
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.closing_models import ClosingRequest
from tests.external_dependency_unit.ton import factories


def test_registry_covers_master_keys_without_rule_activation(
    ton_session: Session,
) -> None:
    admin = factories.make_admin(ton_session)
    items = capability_registry(ton_session, admin, ClosingRequest(request_id=uuid4()))
    expected = (
        {f"S{index}" for index in range(1, 11)}
        | {f"T{index}" for index in range(1, 31)}
        | {f"R{index}" for index in range(1, 10)}
    )
    keyed = {item.key: item for item in items}
    assert expected <= keyed.keys()
    assert len(items) == len(keyed) == 68
    assert len([item for item in items if item.family == "Fontes"]) == 10
    assert len([item for item in items if item.family == "Especialistas"]) == 9
    assert keyed["S10"].status == "OPERATIONAL"
    assert keyed["T4"].status == "PARTIAL"
    assert keyed["T3"].status == "NOT_IMPLEMENTED"
    assert keyed["CFO"].status == "BLOCKED"
    assert keyed["R3"].status == "PARTIAL"
    assert "conexão atual não validadas" in keyed["SOURCE_ZEEV"].reason
    assert all(
        item.reason
        and item.required_sources
        and item.required_configuration
        and item.owner_specialist
        and item.next_dependency
        for item in items
    )
    assert ton_session.scalar(select(func.count()).select_from(RuleVersion)) == 0
    outsider = factories.make_user(ton_session)
    with pytest.raises(OnyxError):
        capability_registry(ton_session, outsider, ClosingRequest(request_id=uuid4()))
