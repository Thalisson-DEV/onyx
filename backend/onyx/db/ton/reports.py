"""Immutable report publication (Plan 003d).

This module closes the persistent Plan 003 chain:

    RuleVersion -> AnalysisRun -> Finding -> Occurrence -> TonReport

:class:`~onyx.db.ton.models.TonReport` is the stable logical report.
:class:`~onyx.db.ton.models.TonReportRevision` is the immutable published
snapshot. Publishing again appends revision *N+1*; it never rewrites *N*.

**There is no update path here.** Readiness §12 puts immutability in three
layers, and all three are present:

1. no function in this module updates a published revision. The only writes to an
   existing row are :func:`supersede_revision__no_commit`, which links a
   correction and touches nothing the hash covers;
2. a ``before_update`` guard on the model raises if any content column changes,
   so bypassing this module does not bypass the rule
   (see ``_reject_report_revision_content_change`` in
   :mod:`onyx.db.ton.models`);
3. :func:`verify_revision_hash` recomputes the digest from the stored payload, so
   tampering that bypassed the application entirely is still detectable.

**Reproducibility.** A revision stays reproducible after a later ``RuleVersion``
exists, an ``Occurrence`` changes state, a new ``Finding`` arrives, a source is
re-imported, an interpretation is appended and a later revision is published,
because the payload holds the values *as published* and the five join tables pin
the exact inputs by id. Nothing here resolves "latest" when reading an old
revision.

**Boundaries.** 003d provides persistence and publication primitives only. There
is no scheduler, no R1-R9 routine, no alert dispatch and no publication ceiling
(Plan 006); no agent, prompt or LLM call (Plan 005); no ingestion (Plan 004); and
no HTTP route, because the canonical planning still leaves report route names
open.
"""

import datetime
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.ton.canonical import (
    CANONICALIZATION_VERSION,
    HASH_ALGORITHM,
    canonical_document,
    compute_content_hash,
)
from onyx.db.ton.enums import TonReportType
from onyx.db.ton.interpretations import is_interpretation_final
from onyx.db.ton.models import (
    AnalysisRun,
    Finding,
    Occurrence,
    RuleVersion,
    SourceSnapshot,
    TonReport,
    TonReportRevision,
    TonReportRevision__AnalysisRun,
    TonReportRevision__Finding,
    TonReportRevision__Occurrence,
    TonReportRevision__RuleVersion,
    TonReportRevision__SourceSnapshot,
)

# Top-level keys of a canonical report payload. A fixed shape, so a consumer can
# read a revision published by any generator version.
PAYLOAD_CANONICALIZATION_KEY = "canonicalization"
PAYLOAD_REPORT_KEY = "report"
PAYLOAD_INPUTS_KEY = "inputs"
PAYLOAD_BODY_KEY = "body"

# The columns the content hash stands behind. A change to any of them would make
# the stored digest wrong, so the model guard refuses one.
IMMUTABLE_REVISION_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "report_id",
        "revision_no",
        "canonical_payload",
        "canonicalization_version",
        "hash_algorithm",
        "content_hash",
        "generator_version",
        "generated_at",
        "generated_by",
        "file_record_id",
        "created_at",
    }
)

# The two exceptions, and why they are not a hole in the rule. A revision cannot
# know its own successor at publication time — the successor does not exist yet —
# so this is forward-only linkage, written once by
# :func:`supersede_revision__no_commit`. Neither column is part of the canonical
# payload, so setting them cannot change what was published or its hash.
SUPERSESSION_COLUMNS: frozenset[str] = frozenset(
    {"superseded_by_revision_id", "correction_reason"}
)


@dataclass(frozen=True)
class PinnedInputs:
    """The exact inputs one revision was built from, read back from the joins.

    Returned as sorted id lists so a test can assert the pinning relationally
    rather than by trusting the payload it just wrote.
    """

    analysis_run_ids: tuple[UUID, ...] = ()
    occurrence_ids: tuple[UUID, ...] = ()
    finding_ids: tuple[UUID, ...] = ()
    rule_version_ids: tuple[UUID, ...] = ()
    source_snapshot_ids: tuple[UUID, ...] = ()


def create_report__no_commit(
    db_session: Session,
    *,
    code: str,
    report_type: TonReportType,
    title: str,
    business_unit_id: UUID | None = None,
    period_start: datetime.date | None = None,
    period_end: datetime.date | None = None,
    created_by: UUID | None = None,
) -> TonReport:
    """Create the stable logical identity of a report.

    Holds no payload by construction: there is no content column on
    :class:`~onyx.db.ton.models.TonReport`, so "the latest generated report" is
    not expressible as a mutable row.
    """
    if not code or not code.strip():
        raise ValueError("A report needs a stable code an owner can recognise.")
    if not title or not title.strip():
        raise ValueError("A report needs a title.")

    report = TonReport(
        code=code.strip(),
        report_type=report_type,
        title=title,
        business_unit_id=business_unit_id,
        period_start=period_start,
        period_end=period_end,
        created_by=created_by,
    )
    db_session.add(report)
    db_session.flush()
    return report


def next_revision_no(db_session: Session, report_id: UUID) -> int:
    """Next free revision number for *report_id*.

    Racy on its own; ``uq_ton_report_revision_report_revision`` is what actually
    guarantees one history, so a concurrent second publisher gets an
    ``IntegrityError`` rather than a duplicated revision number.
    """
    highest = db_session.execute(
        select(func.max(TonReportRevision.revision_no)).where(
            TonReportRevision.report_id == report_id
        )
    ).scalar()
    return 1 if highest is None else highest + 1


def latest_revision(db_session: Session, report_id: UUID) -> TonReportRevision | None:
    """The highest-numbered revision of *report_id*, or ``None``."""
    return db_session.scalars(
        select(TonReportRevision)
        .where(TonReportRevision.report_id == report_id)
        .order_by(TonReportRevision.revision_no.desc())
        .limit(1)
    ).one_or_none()


def get_revision(
    db_session: Session, *, report_id: UUID, revision_no: int
) -> TonReportRevision | None:
    """One revision by its ordinal. The read that must stay reproducible."""
    return db_session.scalars(
        select(TonReportRevision).where(
            TonReportRevision.report_id == report_id,
            TonReportRevision.revision_no == revision_no,
        )
    ).one_or_none()


def build_canonical_payload(
    *,
    report: TonReport,
    body: Mapping[str, Any],
    analysis_run_ids: Iterable[UUID] = (),
    occurrence_ids: Iterable[UUID] = (),
    finding_ids: Iterable[UUID] = (),
    rule_version_ids: Iterable[UUID] = (),
    source_snapshot_ids: Iterable[UUID] = (),
) -> dict[str, Any]:
    """The canonical document a revision publishes.

    Exposed separately from :func:`publish_report_revision__no_commit` so a test
    can assert the payload and its hash without writing a row.

    What is in it, and what is deliberately not:

    * **in** — the canonicalisation scheme, the report's identity, type and
      scope, the pinned input ids and the caller's ``body``. These are what the
      report *states*.
    * **out** — ``revision_no``, ``generated_at``, ``generated_by``,
      ``generator_version``, ``file_record_id`` and ``correction_reason``. Those
      are provenance, recorded in columns. Keeping them out is what makes the
      digest a hash of the content: republishing the same figures yields the same
      hash, so "did anything actually change?" is answerable, and a business-value
      change is the only thing that moves it.

    Input ids are sorted, so two orderings of the same inputs canonicalise
    identically.
    """
    if not isinstance(body, Mapping):
        raise ValueError("A report body must be a mapping.")

    payload = {
        PAYLOAD_CANONICALIZATION_KEY: CANONICALIZATION_VERSION,
        PAYLOAD_REPORT_KEY: {
            "code": report.code,
            "type": report.report_type,
            "business_unit_id": report.business_unit_id,
            "period_start": report.period_start,
            "period_end": report.period_end,
        },
        PAYLOAD_INPUTS_KEY: {
            "analysis_runs": _sorted_ids(analysis_run_ids),
            "occurrences": _sorted_ids(occurrence_ids),
            "findings": _sorted_ids(finding_ids),
            "rule_versions": _sorted_ids(rule_version_ids),
            "source_snapshots": _sorted_ids(source_snapshot_ids),
        },
        PAYLOAD_BODY_KEY: body,
    }
    # Reduced to JSON-native form here rather than at the storage boundary, so
    # what is hashed is byte-for-byte what is stored.
    return canonical_document(payload)


def publish_report_revision__no_commit(
    db_session: Session,
    *,
    report: TonReport,
    body: Mapping[str, Any],
    generator_version: str,
    generated_at: datetime.datetime,
    generated_by: UUID | None = None,
    analysis_runs: Iterable[AnalysisRun] = (),
    occurrences: Iterable[Occurrence] = (),
    findings: Iterable[Finding] = (),
    rule_versions: Iterable[RuleVersion] = (),
    source_snapshots: Iterable[SourceSnapshot] = (),
    file_record_id: str | None = None,
    corrects: TonReportRevision | None = None,
    correction_reason: str | None = None,
) -> TonReportRevision:
    """Publish the next immutable revision of *report*.

    Every finding must have a **final** interpretation.
    :func:`onyx.db.ton.interpretations.is_interpretation_final` is the predicate —
    reused, not reimplemented — so only ``COMPLETED`` and ``NOT_REQUIRED`` are
    eligible. A ``PENDING``, ``RUNNING`` or ``FAILED`` interpretation means the
    narrative behind a number is unsettled, and publishing it would put a figure
    in front of a board that the system itself has not finished assessing.

    Pass ``corrects`` to publish a correction: the new revision is created first,
    then the superseded one is linked to it with ``correction_reason``. Revision
    *N* keeps its payload and its hash.

    The write is transactional. A failure here must fail the publication, which is
    why nothing in this function is best-effort — that distinction belongs to
    :mod:`onyx.db.ton.audit`, and reversing the two would either lose domain
    history or let an audit outage block a business operation.
    """
    if not generator_version or not generator_version.strip():
        raise ValueError(
            "generator_version is required: a published snapshot must record the "
            "code identity that produced it."
        )
    if generated_at.tzinfo is None:
        raise ValueError(
            "generated_at must be timezone-aware. A naive publication time cannot "
            "be normalised to UTC without guessing."
        )
    if corrects is not None and not (correction_reason or "").strip():
        raise ValueError(
            "A correction must record why. Publishing a different figure without "
            "a reason is the audit gap revisions exist to close."
        )
    if corrects is None and correction_reason is not None:
        raise ValueError(
            "correction_reason applies to the revision being superseded. Pass "
            "corrects together with it."
        )

    finding_rows = list(findings)
    _assert_findings_are_final(finding_rows)

    analysis_run_ids = [row.id for row in analysis_runs]
    occurrence_ids = [row.id for row in occurrences]
    finding_ids = [row.id for row in finding_rows]
    rule_version_ids = [row.id for row in rule_versions]
    source_snapshot_ids = [row.id for row in source_snapshots]

    payload = build_canonical_payload(
        report=report,
        body=body,
        analysis_run_ids=analysis_run_ids,
        occurrence_ids=occurrence_ids,
        finding_ids=finding_ids,
        rule_version_ids=rule_version_ids,
        source_snapshot_ids=source_snapshot_ids,
    )

    revision = TonReportRevision(
        report_id=report.id,
        revision_no=next_revision_no(db_session, report.id),
        canonical_payload=payload,
        canonicalization_version=CANONICALIZATION_VERSION,
        hash_algorithm=HASH_ALGORITHM,
        content_hash=compute_content_hash(payload),
        generator_version=generator_version.strip(),
        generated_at=generated_at,
        generated_by=generated_by,
        file_record_id=file_record_id,
    )
    db_session.add(revision)
    db_session.flush()

    _pin_inputs(
        db_session,
        revision=revision,
        analysis_run_ids=analysis_run_ids,
        occurrence_ids=occurrence_ids,
        finding_ids=finding_ids,
        rule_version_ids=rule_version_ids,
        source_snapshot_ids=source_snapshot_ids,
    )

    if corrects is not None:
        supersede_revision__no_commit(
            db_session,
            superseded=corrects,
            replacement=revision,
            correction_reason=correction_reason or "",
        )

    return revision


def supersede_revision__no_commit(
    db_session: Session,
    *,
    superseded: TonReportRevision,
    replacement: TonReportRevision,
    correction_reason: str,
) -> TonReportRevision:
    """Link *superseded* to the revision that corrects it.

    The only write to an existing revision anywhere in TON, and the narrowest one
    possible: two columns, neither covered by the content hash, set once. What
    *superseded* published is untouched, which is the point — a correction records
    that a figure changed without erasing the figure that was published.
    """
    if superseded.id == replacement.id:
        raise ValueError("A revision cannot supersede itself.")
    if superseded.report_id != replacement.report_id:
        raise ValueError(
            "A correction must belong to the same report as the revision it supersedes."
        )
    if replacement.revision_no <= superseded.revision_no:
        raise ValueError(
            "A correction must be a later revision. Revision history is ordered "
            "and append-only."
        )
    if superseded.superseded_by_revision_id is not None:
        raise ValueError(
            "That revision is already superseded. Correct the current revision "
            "instead of rewriting the supersession chain."
        )
    if not correction_reason.strip():
        raise ValueError("A correction must record why.")

    superseded.superseded_by_revision_id = replacement.id
    superseded.correction_reason = correction_reason.strip()
    db_session.flush()
    return superseded


def recompute_content_hash(revision: TonReportRevision) -> str:
    """The digest the stored payload should have.

    Reads ``canonical_payload`` back and re-canonicalises it. PostgreSQL reorders
    JSONB keys, so this only agrees with the recorded hash because the
    canonicalisation sorts keys itself.
    """
    return compute_content_hash(revision.canonical_payload)


def verify_revision_hash(revision: TonReportRevision) -> bool:
    """Whether *revision* still matches its recorded digest.

    Readiness §12's third immutability layer: an UPDATE that bypassed both this
    module and the model guard — a hand-written SQL statement, a restored backup —
    still shows up here.

    ``False`` for a revision published under a different canonicalisation scheme
    or hash algorithm, because this process cannot re-derive it. That is why both
    are stored as data rather than assumed.
    """
    if revision.canonicalization_version != CANONICALIZATION_VERSION:
        return False
    if revision.hash_algorithm != HASH_ALGORITHM:
        return False
    return revision.content_hash == recompute_content_hash(revision)


def pinned_inputs(db_session: Session, revision_id: UUID) -> PinnedInputs:
    """Read the pinned inputs of a revision back out of the join tables."""
    return PinnedInputs(
        analysis_run_ids=_link_ids(
            db_session,
            TonReportRevision__AnalysisRun.analysis_run_id,
            TonReportRevision__AnalysisRun.report_revision_id,
            revision_id,
        ),
        occurrence_ids=_link_ids(
            db_session,
            TonReportRevision__Occurrence.occurrence_id,
            TonReportRevision__Occurrence.report_revision_id,
            revision_id,
        ),
        finding_ids=_link_ids(
            db_session,
            TonReportRevision__Finding.finding_id,
            TonReportRevision__Finding.report_revision_id,
            revision_id,
        ),
        rule_version_ids=_link_ids(
            db_session,
            TonReportRevision__RuleVersion.rule_version_id,
            TonReportRevision__RuleVersion.report_revision_id,
            revision_id,
        ),
        source_snapshot_ids=_link_ids(
            db_session,
            TonReportRevision__SourceSnapshot.source_snapshot_id,
            TonReportRevision__SourceSnapshot.report_revision_id,
            revision_id,
        ),
    )


def revisions_using_finding(
    db_session: Session, finding_id: UUID
) -> list[TonReportRevision]:
    """Which published revisions included a given detection.

    The question readiness §12 requires to stay relationally answerable, and the
    reason the pinned inputs are join tables rather than a JSON list.
    """
    return _revisions_joined_on(
        db_session,
        TonReportRevision__Finding.report_revision_id,
        TonReportRevision__Finding.finding_id,
        finding_id,
    )


def revisions_using_occurrence(
    db_session: Session, occurrence_id: UUID
) -> list[TonReportRevision]:
    """Which published revisions reported a given business case."""
    return _revisions_joined_on(
        db_session,
        TonReportRevision__Occurrence.report_revision_id,
        TonReportRevision__Occurrence.occurrence_id,
        occurrence_id,
    )


def revisions_using_rule_version(
    db_session: Session, rule_version_id: UUID
) -> list[TonReportRevision]:
    """Which published revisions were built under a given rule version."""
    return _revisions_joined_on(
        db_session,
        TonReportRevision__RuleVersion.report_revision_id,
        TonReportRevision__RuleVersion.rule_version_id,
        rule_version_id,
    )


def revisions_using_source_snapshot(
    db_session: Session, source_snapshot_id: UUID
) -> list[TonReportRevision]:
    """Which published revisions rest on a given extraction receipt."""
    return _revisions_joined_on(
        db_session,
        TonReportRevision__SourceSnapshot.report_revision_id,
        TonReportRevision__SourceSnapshot.source_snapshot_id,
        source_snapshot_id,
    )


def revisions_using_analysis_run(
    db_session: Session, analysis_run_id: UUID
) -> list[TonReportRevision]:
    """Which published revisions came out of a given analysis run."""
    return _revisions_joined_on(
        db_session,
        TonReportRevision__AnalysisRun.report_revision_id,
        TonReportRevision__AnalysisRun.analysis_run_id,
        analysis_run_id,
    )


def _sorted_ids(ids: Iterable[UUID]) -> list[str]:
    return sorted({str(value) for value in ids})


def _assert_findings_are_final(findings: list[Finding]) -> None:
    unsettled = [
        finding for finding in findings if not is_interpretation_final(finding)
    ]
    if not unsettled:
        return
    detail = ", ".join(
        f"{finding.id} ({finding.interpretation_status.value})" for finding in unsettled
    )
    raise ValueError(
        "A report revision cannot include a finding whose interpretation is not "
        "final. Only COMPLETED and NOT_REQUIRED are eligible; these are not: "
        f"{detail}."
    )


def _pin_inputs(
    db_session: Session,
    *,
    revision: TonReportRevision,
    analysis_run_ids: list[UUID],
    occurrence_ids: list[UUID],
    finding_ids: list[UUID],
    rule_version_ids: list[UUID],
    source_snapshot_ids: list[UUID],
) -> None:
    # Deduplicated and ordered: the composite primary keys would refuse a repeated
    # input, and a caller passing the same finding twice means one inclusion, not
    # an error.
    rows: list[Any] = []
    rows.extend(
        TonReportRevision__AnalysisRun(
            report_revision_id=revision.id, analysis_run_id=value
        )
        for value in sorted(set(analysis_run_ids))
    )
    rows.extend(
        TonReportRevision__Occurrence(
            report_revision_id=revision.id, occurrence_id=value
        )
        for value in sorted(set(occurrence_ids))
    )
    rows.extend(
        TonReportRevision__Finding(report_revision_id=revision.id, finding_id=value)
        for value in sorted(set(finding_ids))
    )
    rows.extend(
        TonReportRevision__RuleVersion(
            report_revision_id=revision.id, rule_version_id=value
        )
        for value in sorted(set(rule_version_ids))
    )
    rows.extend(
        TonReportRevision__SourceSnapshot(
            report_revision_id=revision.id, source_snapshot_id=value
        )
        for value in sorted(set(source_snapshot_ids))
    )
    db_session.add_all(rows)
    db_session.flush()


def _link_ids(
    db_session: Session,
    resource_column: Any,
    revision_column: Any,
    revision_id: UUID,
) -> tuple[UUID, ...]:
    values = db_session.scalars(
        select(resource_column)
        .where(revision_column == revision_id)
        .order_by(resource_column)
    ).all()
    return tuple(values)


def _revisions_joined_on(
    db_session: Session,
    revision_column: Any,
    resource_column: Any,
    resource_id: UUID,
) -> list[TonReportRevision]:
    # A subquery rather than a join, so the junction class does not have to be
    # threaded through as a separate argument for each of the five link tables.
    return list(
        db_session.scalars(
            select(TonReportRevision)
            .where(
                TonReportRevision.id.in_(
                    select(revision_column).where(resource_column == resource_id)
                )
            )
            .order_by(TonReportRevision.revision_no, TonReportRevision.id)
        ).all()
    )
