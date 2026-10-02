"""Read models that close the decision loop: what was decided and what changed.

Everything here is derived from persisted, immutable decisions and normalization
runs. Nothing is estimated: a period comparison is two deterministic readiness
evaluations, and "pending" means a decision version newer than the one a base used.
"""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import financial_domain, financial_readiness
from onyx.db.ton.acl import is_ton_administrator
from onyx.db.ton.models import (
    BusinessUnit,
    DreAccountMapping,
    DreStructure,
    DreStructureVersion,
    FinancialAccount,
    FinancialAmountBasisRevision,
    FinancialCandidateDecision,
    FinancialMapping,
    FinancialMappingRevision,
    FinancialNormalizationRun,
    FinancialReconciliationDecision,
    OperationalSourceRecord,
    ParsedSourceRecord,
)
from onyx.db.ton.sources import get_source
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.financial_domain.readiness_models import (
    DecisionEntry,
    DecisionKind,
    DecisionLog,
    DecisionVersions,
    PeriodChange,
    ReadinessChanges,
)

MAPPING_KINDS: dict[str, DecisionKind] = {
    "UNIT": "UNIT_MAPPING",
    "ACCOUNT": "ACCOUNT_MAPPING",
    "BUDGET_ACCOUNT": "BUDGET_ACCOUNT_MAPPING",
    "BUDGET_UNIT": "BUDGET_UNIT_MAPPING",
    "BUDGET_PERIOD": "BUDGET_PERIOD",
}


def current_versions(session: Session) -> DecisionVersions:
    return DecisionVersions(
        mapping=int(
            session.scalar(sa.select(sa.func.max(FinancialMappingRevision.number))) or 0
        ),
        amount_basis=int(
            session.scalar(sa.select(sa.func.max(FinancialAmountBasisRevision.number)))
            or 0
        ),
        reconciliation=int(
            session.scalar(
                sa.select(sa.func.max(FinancialReconciliationDecision.number))
            )
            or 0
        ),
    )


def run_versions(run: FinancialNormalizationRun) -> DecisionVersions:
    return DecisionVersions(
        mapping=run.mapping_revision_number,
        amount_basis=run.amount_basis_revision_number,
        reconciliation=run.reconciliation_decision_number,
    )


def pending_after(session: Session, applied: DecisionVersions) -> int:
    """Decisions recorded after the versions a base was built with."""
    return (
        int(
            session.scalar(
                sa.select(sa.func.count()).where(
                    FinancialMappingRevision.number > applied.mapping
                )
            )
            or 0
        )
        + int(
            session.scalar(
                sa.select(sa.func.count()).where(
                    FinancialAmountBasisRevision.number > applied.amount_basis
                )
            )
            or 0
        )
        + int(
            session.scalar(
                sa.select(sa.func.count()).where(
                    FinancialReconciliationDecision.number > applied.reconciliation
                )
            )
            or 0
        )
    )


def _previous_run(
    session: Session, user: User, run: FinancialNormalizationRun
) -> FinancialNormalizationRun | None:
    """The newest earlier base over the same imported inputs, if visible."""
    candidates = session.scalars(
        sa.select(FinancialNormalizationRun)
        .where(
            FinancialNormalizationRun.status == "SUCCEEDED",
            FinancialNormalizationRun.id != run.id,
            FinancialNormalizationRun.started_at < run.started_at,
            FinancialNormalizationRun.review_run_id == run.review_run_id,
            FinancialNormalizationRun.dataset_revision == run.dataset_revision,
            FinancialNormalizationRun.billing_execution_id == run.billing_execution_id,
        )
        .order_by(FinancialNormalizationRun.started_at.desc())
    )
    budgets = sorted(run.budget_execution_ids)
    previous = next(
        (item for item in candidates if sorted(item.budget_execution_ids) == budgets),
        None,
    )
    if previous is None:
        return None
    try:
        financial_domain.get_run(session, user, previous.id)
    except OnyxError:
        return None
    return previous


def readiness_changes(
    session: Session,
    user: User,
    run_id: UUID,
    version_id: UUID,
    unit_id: UUID | None,
) -> ReadinessChanges:
    run = financial_domain.get_run(session, user, run_id)
    previous = _previous_run(session, user, run)
    after = financial_readiness.overview(session, user, run.id, version_id, unit_id)
    before = (
        {
            item.scope.period: item
            for item in financial_readiness.overview(
                session, user, previous.id, version_id, unit_id
            ).periods
        }
        if previous
        else {}
    )
    applied = run_versions(run)
    return ReadinessChanges(
        run_id=run.id,
        run_started_at=run.started_at,
        previous_run_id=previous.id if previous else None,
        previous_started_at=previous.started_at if previous else None,
        applied=applied,
        previous_applied=run_versions(previous) if previous else None,
        current=current_versions(session),
        pending_decisions=pending_after(session, applied),
        periods=[
            PeriodChange(
                period=item.scope.period,
                status_before=(
                    before[item.scope.period].status
                    if item.scope.period in before
                    else None
                ),
                status_after=item.status,
                blockers_before=(
                    dict(before[item.scope.period].blockers)
                    if item.scope.period in before
                    else {}
                ),
                blockers_after=dict(item.blockers),
            )
            for item in after.periods
        ],
    )


class _SourceGate:
    """Caches source visibility so the log never leaks another tenant's keys."""

    def __init__(self, session: Session, user: User) -> None:
        self.session = session
        self.user = user
        self.admin = is_ton_administrator(user)
        self.cache: dict[UUID, bool] = {}

    def visible(self, *source_ids: UUID | None) -> bool:
        if self.admin:
            return True
        for source_id in source_ids:
            if source_id is None:
                continue
            if source_id not in self.cache:
                try:
                    get_source(self.session, self.user, source_id)
                    self.cache[source_id] = True
                except OnyxError:
                    self.cache[source_id] = False
            if not self.cache[source_id]:
                return False
        return True


def _emails(session: Session, user_ids: set[UUID]) -> dict[UUID, str]:
    from onyx.db.models import User as UserModel

    if not user_ids:
        return {}
    return {
        row.id: row.email
        for row in session.execute(
            sa.select(UserModel.id, UserModel.email).where(UserModel.id.in_(user_ids))
        )
    }


def _account_label(account: FinancialAccount | None) -> str:
    if account is None:
        return "—"
    return f"{account.code} — {account.label}" if account.label else account.code


def _unit_label(unit: BusinessUnit | None) -> str:
    if unit is None:
        return "—"
    return f"{unit.code} — {unit.name}" if unit.name else unit.code


def _assignments(session: Session, version_id: UUID) -> dict[UUID, tuple[str, str]]:
    return {
        row.account_id: (row.line_code, row.status)
        for row in session.scalars(
            sa.select(DreAccountMapping).where(
                DreAccountMapping.version_id == version_id
            )
        )
    }


def _dre_assignment_changes(
    session: Session, version: DreStructureVersion
) -> list[tuple[str | None, str]]:
    """Which account moved to which line between a version and the one before."""
    previous_id = session.scalar(
        sa.select(DreStructureVersion.id).where(
            DreStructureVersion.structure_id == version.structure_id,
            DreStructureVersion.number == version.number - 1,
        )
    )
    current = _assignments(session, version.id)
    before = _assignments(session, previous_id) if previous_id else {}
    changed = [
        account_id
        for account_id, value in current.items()
        if before.get(account_id) != value
    ]
    if not changed:
        return [(None, f"Versão {version.number} sem mudança de classificação")]
    lines = {
        str(item.get("code")): str(item.get("label", item.get("code")))
        for item in version.lines
    }
    accounts = {
        account.id: account
        for account in session.scalars(
            sa.select(FinancialAccount).where(FinancialAccount.id.in_(changed))
        )
    }
    return [
        (
            _account_label(accounts.get(account_id)),
            lines.get(current[account_id][0], current[account_id][0]),
        )
        for account_id in changed
    ]


def decision_log(session: Session, user: User, limit: int) -> DecisionLog:  # noqa: C901
    gate = _SourceGate(session, user)
    latest = session.scalar(
        sa.select(FinancialNormalizationRun)
        .where(FinancialNormalizationRun.status == "SUCCEEDED")
        .order_by(FinancialNormalizationRun.started_at.desc())
        .limit(1)
    )
    applied = run_versions(latest) if latest else None
    entries: list[DecisionEntry] = []
    authors: list[UUID | None] = []

    for mapping, revision, account, unit in session.execute(
        sa.select(
            FinancialMapping, FinancialMappingRevision, FinancialAccount, BusinessUnit
        )
        .join(
            FinancialMappingRevision,
            FinancialMappingRevision.id == FinancialMapping.revision_id,
        )
        .outerjoin(FinancialAccount, FinancialAccount.id == FinancialMapping.account_id)
        .outerjoin(BusinessUnit, BusinessUnit.id == FinancialMapping.unit_id)
        .order_by(FinancialMappingRevision.number.desc())
        .limit(limit)
    ):
        kind = MAPPING_KINDS.get(mapping.kind)
        if kind is None or not gate.visible(mapping.source_id):
            continue
        if mapping.kind == "BUDGET_PERIOD":
            start = mapping.calendar_period
            end = mapping.effective_to
            outcome = (
                f"{start:%m/%Y} a {end:%m/%Y}"
                if start and end
                else f"a partir de {start:%m/%Y}"
                if start
                else "—"
            )
            subject = "Período da dotação"
        elif mapping.kind in ("UNIT", "BUDGET_UNIT"):
            outcome = _unit_label(unit)
            subject = mapping.source_key
        else:
            outcome = _account_label(account)
            subject = mapping.source_key
        entries.append(
            DecisionEntry(
                kind=kind,
                subject=subject,
                outcome=outcome,
                reason=revision.reason,
                decided_by=None,
                decided_at=revision.created_at,
                version=revision.number,
                applied=(revision.number <= applied.mapping) if applied else None,
            )
        )
        authors.append(revision.created_by)

    for basis, account in session.execute(
        sa.select(FinancialAmountBasisRevision, FinancialAccount)
        .join(
            FinancialAccount,
            FinancialAccount.id == FinancialAmountBasisRevision.account_id,
        )
        .order_by(FinancialAmountBasisRevision.number.desc())
        .limit(limit)
    ):
        entries.append(
            DecisionEntry(
                kind="AMOUNT_BASIS",
                subject=_account_label(account),
                outcome=basis.basis,
                reason=basis.reason,
                decided_by=None,
                decided_at=basis.created_at,
                version=basis.number,
                applied=(basis.number <= applied.amount_basis) if applied else None,
            )
        )
        authors.append(basis.created_by)

    for decision, ng, billing in session.execute(
        sa.select(
            FinancialReconciliationDecision, ParsedSourceRecord, OperationalSourceRecord
        )
        .outerjoin(
            ParsedSourceRecord,
            ParsedSourceRecord.id
            == FinancialReconciliationDecision.actual_source_record_id,
        )
        .outerjoin(
            OperationalSourceRecord,
            OperationalSourceRecord.id
            == FinancialReconciliationDecision.billing_source_record_id,
        )
        .order_by(FinancialReconciliationDecision.number.desc())
        .limit(limit)
    ):
        if not gate.visible(
            ng.source_id if ng else None, billing.source_id if billing else None
        ):
            continue
        documents = [
            value
            for value in (
                ng.document_number if ng else None,
                billing.identifier if billing else None,
            )
            if value
        ]
        entries.append(
            DecisionEntry(
                kind="RECONCILIATION",
                subject=" · ".join(dict.fromkeys(documents)) or "Conciliação",
                outcome=decision.decision,
                reason=decision.reason,
                decided_by=None,
                decided_at=decision.created_at,
                version=decision.number,
                applied=(
                    (decision.number <= applied.reconciliation) if applied else None
                ),
            )
        )
        authors.append(decision.created_by)

    for rejection in session.scalars(
        sa.select(FinancialCandidateDecision)
        .order_by(FinancialCandidateDecision.created_at.desc())
        .limit(limit)
    ):
        if not gate.visible(rejection.source_id):
            continue
        entries.append(
            DecisionEntry(
                kind="CANDIDATE_REJECTION",
                subject=rejection.source_key,
                outcome=rejection.evidence,
                reason=rejection.reason,
                decided_by=None,
                decided_at=rejection.created_at,
                version=None,
                applied=None,
            )
        )
        authors.append(rejection.created_by)

    for version, structure in session.execute(
        sa.select(DreStructureVersion, DreStructure)
        .join(DreStructure, DreStructure.id == DreStructureVersion.structure_id)
        .where(DreStructureVersion.number > 1)
        .order_by(DreStructureVersion.created_at.desc())
        .limit(limit)
    ):
        for subject, outcome in _dre_assignment_changes(session, version):
            entries.append(
                DecisionEntry(
                    kind="DRE_ASSIGNMENT",
                    subject=subject or structure.label,
                    outcome=outcome,
                    reason=version.reason,
                    decided_by=None,
                    decided_at=version.created_at,
                    version=version.number,
                    applied=None,
                )
            )
            authors.append(version.created_by)

    emails = _emails(session, {author for author in authors if author})
    for entry, author in zip(entries, authors, strict=True):
        entry.decided_by = emails.get(author) if author else None
    entries.sort(key=lambda item: item.decided_at, reverse=True)
    return DecisionLog(
        pending_decisions=pending_after(session, applied) if applied else 0,
        entries=entries[:limit],
    )
