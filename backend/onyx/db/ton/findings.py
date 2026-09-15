"""Finding and evidence writes (Plan 003c).

A finding is immutable analytical output. This module can create one and attach
evidence to it, and that is all: there is no update function, no delete
function, and no setter for a deterministic value. Immutability is enforced by
the absence of a write path rather than by a convention a later caller could
overlook.

``interpretation_status`` is the single exception, and it is owned by
:mod:`onyx.db.ton.interpretations`. Nothing here touches it after creation.

No deterministic rule executor lives here. This module records what an executor
found; the eight executor shapes Prompt Mestre §6-§8 needs belong to a later
slice.
"""

import datetime
from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    EvidenceConfidenceLevel,
    FindingKind,
    InterpretationStatus,
    RedactionLevel,
    RuleDomain,
    SourceType,
)
from onyx.db.ton.models import Finding, FindingEvidence, Occurrence, RuleVersion

# The deterministic columns an interpreter may never change. Named here so the
# rule is one list rather than scattered comments, and so a test can assert that
# no function outside this module assigns any of them (readiness §8, invariant 4).
IMMUTABLE_FINDING_COLUMNS: frozenset[str] = frozenset(
    {
        "analysis_run_id",
        "rule_version_id",
        "occurrence_id",
        "identity_key",
        "finding_kind",
        "domain",
        "business_unit_id",
        "contract_id",
        "detected_at",
        "period_start",
        "period_end",
        "expected_value",
        "actual_value",
        "deviation_value",
        "computed_impact_amount",
        "value_scale",
        "value_unit",
        "value_currency",
        "deterministic_payload",
        "nc_code",
    }
)


def create_finding__no_commit(
    db_session: Session,
    *,
    analysis_run_id: UUID,
    rule_version: RuleVersion,
    occurrence: Occurrence,
    identity_key: str,
    finding_kind: FindingKind,
    domain: RuleDomain,
    detected_at: datetime.datetime,
    interpretation_status: InterpretationStatus = InterpretationStatus.NOT_REQUIRED,
    business_unit_id: UUID | None = None,
    contract_id: UUID | None = None,
    period_start: datetime.date | None = None,
    period_end: datetime.date | None = None,
    expected_value: Decimal | None = None,
    actual_value: Decimal | None = None,
    deviation_value: Decimal | None = None,
    computed_impact_amount: Decimal | None = None,
    value_scale: int | None = None,
    value_unit: str | None = None,
    value_currency: str | None = None,
    deterministic_payload: Mapping[str, Any] | None = None,
    nc_code: str | None = None,
) -> Finding:
    """Record one immutable detection.

    ``rule_version`` is taken as an object rather than an id so the caller cannot
    accidentally pass a ``rule_id``: readiness §3 requires every finding to pin
    the version that produced it, and there is no ``rule_id`` column on
    :class:`Finding` at all.

    A ``BLIND_SPOT`` finding needs no numeric value and no evidence row, which is
    what makes Prompt Mestre §11's data gap a first-class finding. Nothing here
    requires an amount.

    Money arrives as :class:`~decimal.Decimal`. Passing a ``float`` raises,
    because a silent float conversion is exactly how a published number stops
    being reproducible.
    """
    for name, amount in (
        ("expected_value", expected_value),
        ("actual_value", actual_value),
        ("deviation_value", deviation_value),
        ("computed_impact_amount", computed_impact_amount),
    ):
        _reject_float(name, amount)

    finding = Finding(
        analysis_run_id=analysis_run_id,
        rule_version_id=rule_version.id,
        occurrence_id=occurrence.id,
        identity_key=identity_key,
        finding_kind=finding_kind,
        interpretation_status=interpretation_status,
        domain=domain,
        business_unit_id=business_unit_id,
        contract_id=contract_id,
        detected_at=detected_at,
        period_start=period_start,
        period_end=period_end,
        expected_value=expected_value,
        actual_value=actual_value,
        deviation_value=deviation_value,
        computed_impact_amount=computed_impact_amount,
        value_scale=value_scale,
        value_unit=value_unit,
        value_currency=value_currency,
        deterministic_payload=(
            dict(deterministic_payload) if deterministic_payload is not None else {}
        ),
        nc_code=nc_code,
    )
    db_session.add(finding)
    db_session.flush()
    return finding


def add_finding_evidence__no_commit(
    db_session: Session,
    *,
    finding: Finding,
    source_type: SourceType,
    confidence_level: EvidenceConfidenceLevel,
    redaction_level: RedactionLevel,
    source_snapshot_id: UUID | None = None,
    record_key: str | None = None,
    locator: Mapping[str, Any] | None = None,
    file_record_id: str | None = None,
    document_id: str | None = None,
    chat_message_id: int | None = None,
    extracted_value: str | None = None,
    value_scale: int | None = None,
    value_unit: str | None = None,
    value_currency: str | None = None,
    is_non_standard_source: bool = False,
) -> FindingEvidence:
    """Attach one source pointer to *finding*.

    ``confidence_level`` and ``redaction_level`` are required arguments with no
    default. Prompt Mestre §3.4 makes a number without its A/B/C/D level a
    defect, and §12.1 forbids imputing conduct to a named person, so neither may
    be inferred from context.

    ``extracted_value`` is a decimal **string**. It records what the source said
    at the source's own scale; converting it to a float here would lose the exact
    value the 003d report hash depends on.

    ``locator`` stays source-agnostic: ``page``, ``sheet``, ``row``, ``column``,
    ``cell``, ``chunk_id``, ``char_span``, ``line``. No NG/Keevo key belongs in
    it, and no source-specific column exists to hold one.
    """
    if isinstance(extracted_value, float):
        raise TypeError(
            "extracted_value is a decimal string, not a float. A float "
            "round-trip would change the value the source actually stated."
        )

    evidence = FindingEvidence(
        finding_id=finding.id,
        source_snapshot_id=source_snapshot_id,
        source_type=source_type,
        confidence_level=confidence_level,
        record_key=record_key,
        locator=dict(locator) if locator is not None else {},
        file_record_id=file_record_id,
        document_id=document_id,
        chat_message_id=chat_message_id,
        extracted_value=extracted_value,
        value_scale=value_scale,
        value_unit=value_unit,
        value_currency=value_currency,
        is_non_standard_source=is_non_standard_source,
        redaction_level=redaction_level,
    )
    db_session.add(evidence)
    db_session.flush()
    return evidence


def fetch_findings_for_occurrence(
    db_session: Session, occurrence_id: UUID
) -> list[Finding]:
    """Every detection recorded against one case, oldest first.

    Unfiltered on purpose: this is the internal read. Every caller that serves a
    user must go through :mod:`onyx.db.ton.acl`, which derives access from the
    owning occurrence.
    """
    return list(
        db_session.scalars(
            select(Finding)
            .where(Finding.occurrence_id == occurrence_id)
            .order_by(Finding.detected_at, Finding.id)
        ).all()
    )


def highest_evidence_confidence(
    evidence: list[FindingEvidence],
) -> EvidenceConfidenceLevel | None:
    """The best confidence level present, or ``None`` for no evidence.

    Reads the maximum rather than combining levels. Prompt Mestre §3.4 forbids
    promotion by repetition, so five D rows stay D: there is deliberately no
    arithmetic here that could turn quantity into quality.
    """
    if not evidence:
        return None
    order = list(EvidenceConfidenceLevel)
    return min((item.confidence_level for item in evidence), key=order.index)


def _reject_float(name: str, value: object | None) -> None:
    if isinstance(value, float):
        raise TypeError(
            f"{name} must be a Decimal, not a float. Prompt Mestre §6 exists "
            "because arithmetic in this data is already wrong by cents; an "
            "IEEE-754 round-trip would make a published number irreproducible."
        )
