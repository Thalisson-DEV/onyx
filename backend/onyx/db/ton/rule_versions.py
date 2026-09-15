"""Rule and rule-version operations (Plan 003b).

Only what the versioning contract needs to be executable and testable: create a
rule, append a version, record an approval, activate an approved version and
select the version in force on a date.

No deterministic executor is implemented here. ``executor_key`` names one; the
eight executor shapes the Prompt Mestre needs are a later slice, and nothing in
003b runs a business rule.

**Nothing in this module seeds anything.** No S-rule, no T-rule, no threshold, no
NC mapping and no Vale Norte value appears in this file or in the migration.
"""

import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.ton.enums import (
    EvidenceConfidenceLevel,
    MissingDataBehavior,
    PostResolutionPolicy,
    RuleDomain,
    RuleKind,
    RuleProvenance,
    RuleVersionStatus,
)
from onyx.db.ton.identity import validate_identity_components
from onyx.db.ton.models import Rule, RuleVersion

# Statuses whose findings may be published. `TEST_ONLY` is deliberately outside
# it: a test version must stay runnable without ever reaching a business
# audience (readiness §3).
PUBLISHABLE_STATUSES: frozenset[RuleVersionStatus] = frozenset(
    {RuleVersionStatus.ACTIVE}
)


def create_rule__no_commit(
    db_session: Session,
    *,
    code: str,
    domain: RuleDomain,
    kind: RuleKind,
    created_by: UUID | None = None,
) -> Rule:
    """Create the stable identity of a rule.

    Carries no threshold, no status and no effective date by construction — those
    columns do not exist on :class:`Rule`.
    """
    rule = Rule(code=code, domain=domain, kind=kind, created_by=created_by)
    db_session.add(rule)
    db_session.flush()
    return rule


def next_version_number(db_session: Session, rule_id: UUID) -> int:
    """Next free version number for *rule_id*.

    Racy on its own; ``uq_ton_rule_version_rule_version`` is what actually
    guarantees a single history, so a concurrent second writer gets an
    ``IntegrityError`` instead of a duplicated version.
    """
    highest = db_session.execute(
        select(func.max(RuleVersion.version)).where(RuleVersion.rule_id == rule_id)
    ).scalar()
    return 1 if highest is None else highest + 1


def create_rule_version__no_commit(
    db_session: Session,
    *,
    rule: Rule,
    title: str,
    executor_key: str,
    provenance: RuleProvenance,
    missing_data_behavior: MissingDataBehavior,
    min_confidence_level: EvidenceConfidenceLevel,
    post_resolution_policy: PostResolutionPolicy,
    identity_components: Sequence[str],
    version: int | None = None,
    description: str | None = None,
    parameters: dict[str, object] | None = None,
    applicability: dict[str, object] | None = None,
    evidence_requirements: dict[str, object] | None = None,
    severity_mapping: dict[str, object] | None = None,
    unit: str | None = None,
    currency: str | None = None,
    scale: int | None = None,
    rounding_mode: str | None = None,
    effective_from: datetime.date | None = None,
    effective_to: datetime.date | None = None,
    source_reference: str | None = None,
    nc_code: str | None = None,
    status: RuleVersionStatus = RuleVersionStatus.DRAFT,
    created_by: UUID | None = None,
) -> RuleVersion:
    """Append a version to *rule*.

    Refuses to create an ``ACTIVE`` version directly. The database refuses it too
    (``ck_ton_rule_version_active_requires_approval``); this guard exists so the
    caller gets a domain message naming the missing approval rather than a
    constraint violation. Activation goes through
    :func:`activate_rule_version__no_commit`.
    """
    if status is RuleVersionStatus.ACTIVE:
        raise ValueError(
            "A rule version cannot be created ACTIVE. Record an approval with "
            "approve_rule_version__no_commit, then activate it — activating a "
            "threshold has company-wide effect and must carry its approval."
        )

    normalised_components = validate_identity_components(identity_components)

    rule_version = RuleVersion(
        rule_id=rule.id,
        version=version
        if version is not None
        else next_version_number(db_session, rule.id),
        title=title,
        description=description,
        executor_key=executor_key,
        parameters=parameters if parameters is not None else {},
        unit=unit,
        currency=currency,
        scale=scale,
        rounding_mode=rounding_mode,
        applicability=applicability if applicability is not None else {},
        effective_from=effective_from,
        effective_to=effective_to,
        status=status,
        source_reference=source_reference,
        provenance=provenance,
        missing_data_behavior=missing_data_behavior,
        evidence_requirements=(
            evidence_requirements if evidence_requirements is not None else {}
        ),
        min_confidence_level=min_confidence_level,
        severity_mapping=severity_mapping if severity_mapping is not None else {},
        nc_code=nc_code,
        identity_components=normalised_components,
        post_resolution_policy=post_resolution_policy,
        created_by=created_by,
    )
    db_session.add(rule_version)
    db_session.flush()
    return rule_version


def approve_rule_version__no_commit(
    db_session: Session,
    *,
    rule_version: RuleVersion,
    approved_by: UUID,
    approval_reference: str,
    approved_at: datetime.datetime | None = None,
) -> RuleVersion:
    """Record the human approval of *rule_version*. Does not activate it.

    Approval and activation are separate acts: an approved version may still wait
    for its effective date.
    """
    rule_version.approved_by = approved_by
    rule_version.approval_reference = approval_reference
    rule_version.approved_at = approved_at or datetime.datetime.now(datetime.UTC)
    db_session.flush()
    return rule_version


def activate_rule_version__no_commit(
    db_session: Session, *, rule_version: RuleVersion
) -> RuleVersion:
    """Move an approved version to ``ACTIVE``.

    Raises when the approval record is incomplete. The same rule is a database
    CHECK constraint, so this cannot be bypassed by another writer.
    """
    if rule_version.approved_by is None or rule_version.approved_at is None:
        raise ValueError(
            "An ACTIVE rule version requires both approved_by and approved_at. "
            "No unapproved threshold may reach production."
        )
    rule_version.status = RuleVersionStatus.ACTIVE
    db_session.flush()
    return rule_version


def is_publishable(rule_version: RuleVersion) -> bool:
    """Whether findings from *rule_version* may reach a business audience.

    ``TEST_ONLY`` returns ``False``: 003c consumes this to keep a test version
    from producing a publishable occurrence.
    """
    return rule_version.status in PUBLISHABLE_STATUSES


def is_in_force_on(rule_version: RuleVersion, on_date: datetime.date) -> bool:
    """Whether *rule_version* is the configuration in force on *on_date*.

    Requires ``ACTIVE`` and an explicit ``effective_from``. A version with no
    ``effective_from`` is not in force anywhere — an undated version would
    otherwise apply retroactively to every historical period.
    """
    if rule_version.status is not RuleVersionStatus.ACTIVE:
        return False
    if rule_version.effective_from is None:
        return False
    if on_date < rule_version.effective_from:
        return False
    if rule_version.effective_to is not None and on_date > rule_version.effective_to:
        return False
    return True


def select_effective_rule_version(
    versions: Sequence[RuleVersion], on_date: datetime.date
) -> RuleVersion | None:
    """The single version in force on *on_date*, or ``None``.

    Raises when two versions overlap. Picking the highest version number would
    hide a misconfiguration that silently changes which threshold a published
    number was measured against.
    """
    in_force = [version for version in versions if is_in_force_on(version, on_date)]
    if not in_force:
        return None
    if len(in_force) > 1:
        overlapping = ", ".join(
            str(version.version)
            for version in sorted(in_force, key=lambda candidate: candidate.version)
        )
        raise ValueError(
            f"Rule versions {overlapping} are all in force on {on_date.isoformat()}. "
            "Effective ranges of ACTIVE versions must not overlap."
        )
    return in_force[0]


def get_effective_rule_version(
    db_session: Session, *, rule_code: str, on_date: datetime.date
) -> RuleVersion | None:
    """Database counterpart of :func:`select_effective_rule_version`.

    Loads every version of the rule and applies the same pure selection, so the
    two paths cannot disagree.
    """
    versions = (
        db_session.execute(select(RuleVersion).join(Rule).where(Rule.code == rule_code))
        .scalars()
        .all()
    )
    return select_effective_rule_version(list(versions), on_date)
