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
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.ton.canonical import CANONICALIZATION_VERSION, compute_content_hash
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
    # Flushed before hashing so `version` is settled — it is part of the
    # canonical definition, and a server-assigned value would otherwise be absent.
    db_session.flush()

    rule_version.definition_hash = compute_definition_hash(
        rule_version, rule_code=rule.code
    )
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


# ---------------------------------------------------------------------------
# Plan 003d — the canonical definition hash.
#
# 003b created `RuleVersion.definition_hash` nullable and left it unwritten on
# purpose: the canonical serialisation was specified in readiness §12 but not
# implemented, and a hash recorded under an ad-hoc scheme would have been
# meaningless. `ton-canon-1` now exists, so this is where the column is filled.
# ---------------------------------------------------------------------------

# The business definition, and only the business definition. Two rows carrying
# the same values here describe the same rule and must hash identically, whenever
# and wherever they were stored.
RULE_VERSION_DEFINITION_FIELDS: tuple[str, ...] = (
    "rule_code",
    "version",
    "title",
    "description",
    "executor_key",
    "parameters",
    "unit",
    "currency",
    "scale",
    "rounding_mode",
    "applicability",
    "effective_from",
    "effective_to",
    "source_reference",
    "provenance",
    "missing_data_behavior",
    "evidence_requirements",
    "min_confidence_level",
    "severity_mapping",
    "nc_code",
    "identity_components",
    "post_resolution_policy",
)

# Columns deliberately outside the canonical definition, with the reason:
#
# * `id`, `rule_id` — database surrogates. `rule_code` is the business identity,
#   and Prompt Mestre §7 forbids renaming it, so it is the stable choice.
# * `status`, `approved_by`, `approved_at`, `approval_reference` — approval
#   *execution* state. Readiness does not put it in the canonical definition, and
#   including it would make one unchanged definition hash differently before and
#   after it was approved, which defeats the tamper check.
# * `created_at`, `updated_at`, `created_by` — facts about the row, not the rule.
#   These are exactly the "mutable runtime database facts" that must not make the
#   same definition hash differently merely because it was stored at another time.
# * `definition_hash` — itself.
RULE_VERSION_NON_DEFINITION_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "rule_id",
        "status",
        "approved_by",
        "approved_at",
        "approval_reference",
        "created_at",
        "updated_at",
        "created_by",
        "definition_hash",
    }
)


@dataclass(frozen=True)
class DefinitionHashBackfill:
    """Outcome of :func:`backfill_definition_hashes__no_commit`."""

    hashed: int = 0
    already_hashed: int = 0
    # Rows that could not be canonicalised, with the reason. Reported rather than
    # papered over: a fabricated hash is worse than an absent one.
    failed: list[tuple[UUID, str]] = field(default_factory=list)


def rule_version_definition_payload(
    rule_version: RuleVersion, *, rule_code: str
) -> dict[str, Any]:
    """The canonical business definition of *rule_version*.

    Exposed, like :func:`onyx.db.ton.identity.canonical_identity_payload`, so a
    test can assert the payload rather than only the digest — a digest mismatch
    cannot show *which* field moved.

    ``rule_code`` is a parameter rather than read from the relationship so this
    stays pure: no session, no lazy load, and callable on an unpersisted row.
    """
    if not rule_code or not rule_code.strip():
        raise ValueError(
            "rule_code is required: it is the stable business identity of the "
            "rule this definition belongs to."
        )

    return {
        "rule_code": rule_code.strip(),
        "version": rule_version.version,
        "title": rule_version.title,
        "description": rule_version.description,
        "executor_key": rule_version.executor_key,
        "parameters": rule_version.parameters,
        "unit": rule_version.unit,
        "currency": rule_version.currency,
        "scale": rule_version.scale,
        "rounding_mode": rule_version.rounding_mode,
        "applicability": rule_version.applicability,
        "effective_from": rule_version.effective_from,
        "effective_to": rule_version.effective_to,
        "source_reference": rule_version.source_reference,
        "provenance": rule_version.provenance,
        "missing_data_behavior": rule_version.missing_data_behavior,
        "evidence_requirements": rule_version.evidence_requirements,
        "min_confidence_level": rule_version.min_confidence_level,
        "severity_mapping": rule_version.severity_mapping,
        "nc_code": rule_version.nc_code,
        # Re-normalised rather than taken as stored: two versions declaring the
        # same dimensions in a different order declare the same definition.
        "identity_components": validate_identity_components(
            rule_version.identity_components
        ),
        "post_resolution_policy": rule_version.post_resolution_policy,
    }


def compute_definition_hash(rule_version: RuleVersion, *, rule_code: str) -> str:
    """Tamper evidence over the canonical definition of *rule_version*.

    Scheme-prefixed, as :func:`onyx.db.ton.identity.compute_identity_key` is, and
    unlike ``TonReportRevision.content_hash``: a revision stores its
    ``canonicalization_version`` in its own column, whereas ``definition_hash`` has
    no companion column, so the scheme travels inside the value. A future scheme
    change is then visible instead of producing a silently incomparable digest.

    Raises ``ValueError`` if the definition cannot be canonicalised — most often a
    float that reached ``parameters`` through JSONB. That is deliberate: a
    threshold stored as an IEEE-754 double is not exactly reproducible, and
    hashing it anyway would record tamper evidence that cannot be re-derived.
    """
    payload = rule_version_definition_payload(rule_version, rule_code=rule_code)
    return f"{CANONICALIZATION_VERSION}:{compute_content_hash(payload)}"


def set_definition_hash__no_commit(
    db_session: Session, *, rule_version: RuleVersion
) -> str:
    """Compute and store the definition hash of *rule_version*.

    Reads the rule code through the relationship, so unlike
    :func:`compute_definition_hash` this one needs a session.
    """
    digest = compute_definition_hash(rule_version, rule_code=rule_version.rule.code)
    rule_version.definition_hash = digest
    db_session.flush()
    return digest


def definition_hash_matches(rule_version: RuleVersion, *, rule_code: str) -> bool:
    """Whether the stored hash still matches the stored definition.

    ``False`` for an unhashed row: absence of evidence is not evidence of
    integrity, and answering ``True`` would let a NULL pass a tamper check.
    """
    if rule_version.definition_hash is None:
        return False
    return rule_version.definition_hash == compute_definition_hash(
        rule_version, rule_code=rule_code
    )


def backfill_definition_hashes__no_commit(
    db_session: Session,
) -> DefinitionHashBackfill:
    """Fill ``definition_hash`` on rows that have none, under ``ton-canon-1``.

    The production migration seeds zero rule versions, so on a real deployment
    this finds nothing. It exists for a development or disposable database that
    holds legitimate rows created before 003d.

    Three properties matter, and each is the reason the column stays nullable:

    * **Nothing is deleted or recreated.** Only ``definition_hash`` is written.
    * **A row already carrying a hash is left alone**, so re-running cannot
      overwrite recorded tamper evidence.
    * **A row that cannot be canonicalised is reported, not fabricated.** Making
      the column NOT NULL would force a value for such a row, and inventing one
      would defeat the purpose of the column. Readiness requires no NOT NULL here,
      so the safe shape is a nullable column plus this reported backfill.
    """
    result = DefinitionHashBackfill(failed=[])
    hashed = 0
    already_hashed = 0

    rows = db_session.scalars(
        select(RuleVersion).order_by(RuleVersion.rule_id, RuleVersion.version)
    ).all()
    for rule_version in rows:
        if rule_version.definition_hash is not None:
            already_hashed += 1
            continue
        try:
            rule_version.definition_hash = compute_definition_hash(
                rule_version, rule_code=rule_version.rule.code
            )
        except ValueError as error:
            result.failed.append((rule_version.id, str(error)))
            continue
        hashed += 1

    db_session.flush()
    return DefinitionHashBackfill(
        hashed=hashed, already_hashed=already_hashed, failed=result.failed
    )
