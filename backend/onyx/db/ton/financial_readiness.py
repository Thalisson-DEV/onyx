"""Paged, tenant-scoped financial readiness evidence."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import dre, financial_domain
from onyx.db.ton.acl import business_unit_visible_clause, is_ton_administrator
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import (
    BusinessUnit,
    DreAccountMapping,
    FinancialAccount,
    FinancialActualFact,
    FinancialAmountBasisRevision,
    FinancialBillingFact,
    FinancialBudgetFact,
    FinancialCandidateDecision,
    FinancialLegacyCandidate,
    FinancialMapping,
    FinancialMappingRevision,
    FinancialReconciliationItem,
    OperationalSourceRecord,
    ParsedSourceRecord,
)
from onyx.db.ton.sources import check_page, get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.dre.models import DreScope
from onyx.ton.financial_domain.readiness_models import (
    BlockerPage,
    BlockerRow,
    CandidateRejection,
    CandidateView,
    LegacyCandidateImport,
    LegacyEvidenceView,
    ReadinessOverview,
)
from onyx.utils.audit import AuditAction, AuditOutcome

SUMMARY_BLOCKERS = frozenset(
    {
        "UNCLASSIFIED_ACCOUNT",
        "BUDGET_UNMAPPED_ACCOUNT",
        "BUDGET_UNMAPPED_UNIT",
        "REVIEW_UNRESOLVED",
        "EXCLUDED_SOURCE_ROWS",
        "BILLING_COMPETENCE_UNRESOLVED",
        "UNSUPPORTED_DERIVATION",
        "IR_RETENTION_UNRESOLVED",
        "MISSING_BUDGET",
        "NO_ACTUAL",
        "ACTUAL_UNIT_SCOPE_UNRESOLVED",
        "FORMULA_DENOMINATOR_ZERO",
        "DRE_STRUCTURE_INVALID",
    }
)
BLOCKER_GUIDANCE = {
    "REVIEW_UNRESOLVED": "Complete the reviewed NG record decisions",
    "EXCLUDED_SOURCE_ROWS": "Inspect excluded NG parse and review rows",
    "BILLING_COMPETENCE_UNRESOLVED": "Resolve billing source competence evidence",
    "UNSUPPORTED_DERIVATION": "Review the billing derivation rule and source fields",
    "IR_RETENTION_UNRESOLVED": "Resolve retained tax source evidence",
    "MISSING_BUDGET": "Review budget account, unit, period, and source coverage",
    "NO_ACTUAL": "Import reviewed NG actuals for this period",
    "ACTUAL_UNIT_SCOPE_UNRESOLVED": "Approve source unit mappings before unit scoped calculation",
    "FORMULA_DENOMINATOR_ZERO": "Review the DRE formula and denominator inputs",
    "DRE_STRUCTURE_INVALID": "Create a corrected DRE structure version",
    "UNCLASSIFIED_ACCOUNT": "Review canonical account classification",
}


def overview(
    session: Session, user: User, run_id: UUID, version_id: UUID, unit_id: UUID | None
) -> ReadinessOverview:
    financial_domain.get_run(session, user, run_id)
    periods = list(
        session.scalars(
            sa.select(FinancialActualFact.calendar_period)
            .where(FinancialActualFact.run_id == run_id)
            .distinct()
            .order_by(FinancialActualFact.calendar_period)
        )
    )
    return ReadinessOverview(
        normalization_run_id=run_id,
        structure_version_id=version_id,
        periods=[
            dre.readiness(
                session,
                user,
                DreScope(
                    normalization_run_id=run_id,
                    structure_version_id=version_id,
                    period=period,
                    unit_id=unit_id,
                ),
            )
            for period in periods
        ],
    )


def list_units(
    session: Session, user: User, limit: int, offset: int, search: str | None
) -> list[BusinessUnit]:
    check_page(limit, offset)
    query = sa.select(BusinessUnit).where(business_unit_visible_clause(user))
    if search:
        query = query.where(BusinessUnit.code.ilike(f"%{search}%"))
    return list(
        session.scalars(query.order_by(BusinessUnit.code).limit(limit).offset(offset))
    )


def _candidate(
    session: Session, user: User, source_id: UUID, kind: str, source_key: str
) -> CandidateView | None:
    # Only an exact code or an earlier explicit approval is evidence.
    mapping = session.execute(
        sa.select(FinancialMapping)
        .join(
            FinancialMappingRevision,
            FinancialMappingRevision.id == FinancialMapping.revision_id,
        )
        .where(
            FinancialMapping.source_id == source_id,
            FinancialMapping.kind == kind,
            FinancialMapping.source_key == source_key,
        )
        .order_by(FinancialMappingRevision.number.desc())
        .limit(1)
    ).scalar_one_or_none()
    if kind == "UNIT":
        query = sa.select(BusinessUnit).where(business_unit_visible_clause(user))
        if mapping is not None and mapping.unit_id is not None:
            query = query.where(BusinessUnit.id == mapping.unit_id)
        else:
            query = query.where(
                sa.func.lower(sa.func.trim(BusinessUnit.code))
                == source_key.strip().lower()
            )
        target = session.scalar(query.limit(1))
        if target is None:
            return None
        candidate = CandidateView(
            target_id=target.id,
            code=target.code,
            label=target.name,
            evidence="APPROVED_MAPPING" if mapping is not None else "EXACT_CODE",
        )
    else:
        query = sa.select(FinancialAccount)
        if mapping is not None and mapping.account_id is not None:
            query = query.where(FinancialAccount.id == mapping.account_id)
        else:
            query = query.where(
                sa.func.lower(sa.func.trim(FinancialAccount.code))
                == source_key.strip().lower()
            )
        target = session.scalar(query.limit(1))
        if target is None:
            return None
        candidate = CandidateView(
            target_id=target.id,
            code=target.code,
            label=target.label,
            evidence="APPROVED_MAPPING" if mapping is not None else "EXACT_CODE",
        )
    rejected = session.scalar(
        sa.select(FinancialCandidateDecision.id)
        .where(
            FinancialCandidateDecision.source_id == source_id,
            FinancialCandidateDecision.kind == kind,
            FinancialCandidateDecision.source_key == source_key,
            FinancialCandidateDecision.target_id == candidate.target_id,
            FinancialCandidateDecision.evidence == candidate.evidence,
        )
        .limit(1)
    )
    return None if rejected else candidate


def _page_candidates(
    session: Session,
    user: User,
    kind: str,
    keys: list[tuple[UUID, str]],
) -> dict[tuple[UUID, str], CandidateView]:
    if not keys:
        return {}
    source_ids = {source_id for source_id, _key in keys}
    source_keys = {key for _source_id, key in keys}
    mapping_rows = session.execute(
        sa.select(FinancialMapping, FinancialMappingRevision.number)
        .join(
            FinancialMappingRevision,
            FinancialMappingRevision.id == FinancialMapping.revision_id,
        )
        .where(
            FinancialMapping.source_id.in_(source_ids),
            FinancialMapping.kind == kind,
            FinancialMapping.source_key.in_(source_keys),
        )
        .order_by(FinancialMappingRevision.number.desc())
    ).all()
    mappings: dict[tuple[UUID, str], FinancialMapping] = {}
    for mapping, _number in mapping_rows:
        mappings.setdefault((mapping.source_id, mapping.source_key), mapping)
    normalized = {key.strip().lower() for key in source_keys}
    if kind == "UNIT":
        targets = list(
            session.scalars(
                sa.select(BusinessUnit).where(
                    business_unit_visible_clause(user),
                    sa.or_(
                        sa.func.lower(sa.func.trim(BusinessUnit.code)).in_(normalized),
                        BusinessUnit.id.in_(
                            {
                                item.unit_id
                                for item in mappings.values()
                                if item.unit_id is not None
                            }
                        ),
                    ),
                )
            )
        )
        by_id = {item.id: item for item in targets}
        by_code: dict[str, list[BusinessUnit]] = {}
        for target in targets:
            by_code.setdefault(target.code.strip().lower(), []).append(target)
    else:
        accounts = list(
            session.scalars(
                sa.select(FinancialAccount).where(
                    sa.or_(
                        sa.func.lower(sa.func.trim(FinancialAccount.code)).in_(
                            normalized
                        ),
                        FinancialAccount.id.in_(
                            {
                                item.account_id
                                for item in mappings.values()
                                if item.account_id is not None
                            }
                        ),
                    )
                )
            )
        )
        by_id = {item.id: item for item in accounts}
        by_code = {}
        for target in accounts:
            by_code.setdefault(target.code.strip().lower(), []).append(target)
    rejected_rows = session.scalars(
        sa.select(FinancialCandidateDecision).where(
            FinancialCandidateDecision.source_id.in_(source_ids),
            FinancialCandidateDecision.kind == kind,
            FinancialCandidateDecision.source_key.in_(source_keys),
        )
    )
    rejected = {
        (item.source_id, item.source_key, item.target_id, item.evidence)
        for item in rejected_rows
    }
    result: dict[tuple[UUID, str], CandidateView] = {}
    for source_id, key in keys:
        mapping = mappings.get((source_id, key))
        target = (
            by_id.get(mapping.unit_id if kind == "UNIT" else mapping.account_id)
            if mapping
            else None
        )
        evidence = "APPROVED_MAPPING" if target else "EXACT_CODE"
        if target is None:
            matches = by_code.get(key.strip().lower(), [])
            if len(matches) != 1:
                continue
            target = matches[0]
        if (source_id, key, target.id, evidence) in rejected:
            continue
        result[(source_id, key)] = CandidateView(
            target_id=target.id,
            code=target.code,
            label=target.name if isinstance(target, BusinessUnit) else target.label,
            evidence=evidence,
        )
    return result


def import_legacy_candidates(
    session: Session, user: User, request: LegacyCandidateImport
) -> int:
    from onyx.db.enums import Permission

    get_source(session, user, request.source_id, Permission.MANAGE_TON_SOURCES)
    key = (
        ParsedSourceRecord.administrative_unit
        if request.kind == "UNIT"
        else ParsedSourceRecord.account_code
    )
    requested_keys = {row.source_key for row in request.rows}
    if len(requested_keys) != len(request.rows):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Duplicate candidate source key")
    if any(
        row.source_key.strip().casefold() != row.suggested_code.strip().casefold()
        for row in request.rows
    ):
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Legacy candidate requires exact code"
        )
    existing_keys = set(
        session.scalars(
            sa.select(key)
            .where(
                ParsedSourceRecord.source_id == request.source_id,
                key.in_(requested_keys),
            )
            .distinct()
        )
    )
    if requested_keys != existing_keys:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Candidate source value not found")
    session.execute(sa.text("SELECT pg_advisory_xact_lock(4433009)"))
    existing = {
        (source_key, suggested_code)
        for source_key, suggested_code in session.execute(
            sa.select(
                FinancialLegacyCandidate.source_key,
                FinancialLegacyCandidate.suggested_code,
            ).where(
                FinancialLegacyCandidate.source_id == request.source_id,
                FinancialLegacyCandidate.kind == request.kind,
                FinancialLegacyCandidate.reference_digest == request.reference_digest,
                FinancialLegacyCandidate.source_key.in_(requested_keys),
            )
        ).all()
    }
    existing_by_key = dict(existing)
    if any(
        row.source_key in existing_by_key
        and existing_by_key[row.source_key] != row.suggested_code
        for row in request.rows
    ):
        raise OnyxError(OnyxErrorCode.CONFLICT, "Legacy candidate evidence conflicts")
    count = 0
    for row in request.rows:
        if (row.source_key, row.suggested_code) in existing:
            continue
        existing.add((row.source_key, row.suggested_code))
        session.add(
            FinancialLegacyCandidate(
                source_id=request.source_id,
                kind=request.kind,
                source_key=row.source_key,
                suggested_code=row.suggested_code,
                suggested_label=row.suggested_label,
                reference_digest=request.reference_digest,
                reference_label=request.reference_label,
                created_by=user.id,
            )
        )
        count += 1
    if count:
        session.flush()
        emit_ton_audit_event(
            session,
            action=AuditAction.TON_FINANCIAL_LEGACY_CANDIDATE_IMPORT,
            outcome=AuditOutcome.SUCCESS,
            actor_user_id=user.id,
            resource_kind=TonAuditResourceKind.FINANCIAL_MAPPING,
            resource_id=request.source_id,
        )
    return count


def list_blockers(  # noqa: C901 - each blocker uses a separate bounded query
    session: Session,
    user: User,
    run_id: UUID,
    version_id: UUID,
    blocker: str,
    limit: int,
    offset: int,
    search: str | None,
    unit_id: UUID | None = None,
) -> BlockerPage:
    run = financial_domain.get_run(session, user, run_id)
    version = dre.get_version(session, user, version_id)
    check_page(limit, offset)
    if not is_ton_administrator(user):
        if (
            unit_id is None
            or session.scalar(
                sa.select(BusinessUnit.id).where(
                    BusinessUnit.id == unit_id, business_unit_visible_clause(user)
                )
            )
            is None
        ):
            raise OnyxError(OnyxErrorCode.NOT_FOUND, "Business unit not found")
    rows: list[BlockerRow] = []
    if blocker in ("UNMAPPED_UNIT", "UNMAPPED_ACCOUNT"):
        is_unit = blocker == "UNMAPPED_UNIT"
        key = (
            ParsedSourceRecord.administrative_unit
            if is_unit
            else ParsedSourceRecord.account_code
        )
        condition = (
            FinancialActualFact.unit_id.is_(None)
            if is_unit
            else FinancialActualFact.account_id.is_(None)
        )
        query = (
            sa.select(
                ParsedSourceRecord.source_id,
                key,
                sa.func.count().label("affected"),
                sa.func.array_agg(
                    sa.distinct(FinancialActualFact.calendar_period)
                ).label("periods"),
            )
            .join(
                FinancialActualFact,
                FinancialActualFact.parsed_record_id == ParsedSourceRecord.id,
            )
            .where(FinancialActualFact.run_id == run_id, condition, key.is_not(None))
            .group_by(ParsedSourceRecord.source_id, key)
        )
        if unit_id is not None:
            query = query.where(FinancialActualFact.unit_id == unit_id)
        if search:
            query = query.where(key.ilike(f"%{search}%"))
        grouped = query.subquery()
        total = int(
            session.scalar(sa.select(sa.func.count()).select_from(grouped)) or 0
        )
        page = session.execute(
            sa.select(grouped)
            .order_by(grouped.c.affected.desc(), grouped.c.source_id)
            .limit(limit)
            .offset(offset)
        ).all()
        candidates = _page_candidates(
            session,
            user,
            "UNIT" if is_unit else "ACCOUNT",
            [
                (source_id, source_key)
                for source_id, source_key, _count, _periods in page
            ],
        )
        legacy_rows = session.scalars(
            sa.select(FinancialLegacyCandidate).where(
                FinancialLegacyCandidate.source_id.in_(
                    {source_id for source_id, _key, _count, _periods in page}
                ),
                FinancialLegacyCandidate.kind == ("UNIT" if is_unit else "ACCOUNT"),
                FinancialLegacyCandidate.source_key.in_(
                    {source_key for _source_id, source_key, _count, _periods in page}
                ),
            )
        )
        rejected_legacy = {
            (item.source_id, item.source_key, item.reference_digest)
            for item in session.scalars(
                sa.select(FinancialCandidateDecision).where(
                    FinancialCandidateDecision.source_id.in_(
                        {source_id for source_id, _key, _count, _periods in page}
                    ),
                    FinancialCandidateDecision.kind
                    == ("UNIT" if is_unit else "ACCOUNT"),
                    FinancialCandidateDecision.evidence == "LEGACY_REFERENCE",
                    FinancialCandidateDecision.source_key.in_(
                        {
                            source_key
                            for _source_id, source_key, _count, _periods in page
                        }
                    ),
                )
            )
        }
        legacy = {
            (item.source_id, item.source_key): LegacyEvidenceView(
                suggested_code=item.suggested_code,
                suggested_label=item.suggested_label,
                reference_label=item.reference_label,
                reference_digest=item.reference_digest,
            )
            for item in legacy_rows
            if (item.source_id, item.source_key, item.reference_digest)
            not in rejected_legacy
        }
        for source_id, source_key, count, periods in page:
            candidate = candidates.get((source_id, source_key))
            evidence = legacy.get((source_id, source_key))
            rows.append(
                BlockerRow(
                    source_id=source_id,
                    source_key=source_key,
                    record_count=int(count),
                    periods=sorted(periods),
                    status=(
                        "APPROVED"
                        if candidate and candidate.evidence == "APPROVED_MAPPING"
                        else "CANDIDATE"
                        if candidate or evidence
                        else "UNMAPPED"
                    ),
                    candidate=candidate,
                    legacy_evidence=evidence,
                    evidence="Exact source field from reviewed NG records",
                )
            )
    elif blocker == "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED":
        # An approved basis revision resolves the account on a new normalization.
        ranked_basis = (
            sa.select(
                FinancialAmountBasisRevision.account_id,
                FinancialAmountBasisRevision.basis,
                sa.func.row_number()
                .over(
                    partition_by=FinancialAmountBasisRevision.account_id,
                    order_by=FinancialAmountBasisRevision.number.desc(),
                )
                .label("rank"),
            )
            .where(
                FinancialAmountBasisRevision.number <= run.amount_basis_revision_number
            )
            .subquery()
        )
        approved_basis = (
            sa.select(ranked_basis.c.account_id, ranked_basis.c.basis)
            .where(ranked_basis.c.rank == 1)
            .subquery()
        )
        basis = sa.func.coalesce(
            approved_basis.c.basis, FinancialAccount.actual_amount_basis
        )
        query = (
            sa.select(
                FinancialAccount.id,
                FinancialAccount.code,
                sa.func.count().label("affected"),
                sa.func.array_agg(sa.distinct(FinancialActualFact.calendar_period)),
                sa.func.count(FinancialActualFact.movement_amount).label(
                    "movement_present"
                ),
                sa.func.count(FinancialActualFact.final_amount).label("final_present"),
                basis.label("selected_basis"),
            )
            .select_from(FinancialActualFact)
            .outerjoin(
                FinancialAccount,
                FinancialActualFact.account_id == FinancialAccount.id,
            )
            .outerjoin(
                approved_basis,
                approved_basis.c.account_id == FinancialAccount.id,
            )
            .where(
                FinancialActualFact.run_id == run_id,
                sa.or_(
                    FinancialActualFact.account_id.is_(None),
                    basis.is_(None),
                    sa.and_(
                        basis == "MOVEMENT",
                        FinancialActualFact.movement_amount.is_(None),
                    ),
                    sa.and_(
                        basis == "FINAL", FinancialActualFact.final_amount.is_(None)
                    ),
                ),
            )
            .group_by(
                FinancialAccount.id, FinancialAccount.code, approved_basis.c.basis
            )
        )
        if unit_id is not None:
            query = query.where(FinancialActualFact.unit_id == unit_id)
        if search:
            query = query.where(FinancialAccount.code.ilike(f"%{search}%"))
        grouped = query.subquery()
        total = int(
            session.scalar(sa.select(sa.func.count()).select_from(grouped)) or 0
        )
        page = session.execute(
            sa.select(grouped)
            .order_by(grouped.c.affected.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        rows = [
            BlockerRow(
                account_id=account_id,
                source_key=code or "UNMAPPED_ACCOUNT",
                record_count=int(count),
                periods=sorted(periods),
                status="UNRESOLVED",
                evidence=(
                    "Approve an account mapping before choosing an amount basis"
                    if account_id is None
                    else f"MOVEMENT present {movement_present}/{count}; "
                    f"FINAL present {final_present}/{count}; "
                    f"approved basis {selected_basis or 'none'}"
                ),
            )
            for account_id, code, count, periods, movement_present, final_present, selected_basis in page
        ]
    elif blocker in ("DRE_ACCOUNT_UNMAPPED", "DRE_MAPPING_PENDING_APPROVAL"):
        approved = blocker == "DRE_MAPPING_PENDING_APPROVAL"
        line_codes = {
            line.code for line in version.lines if line.line_type == "SOURCE_SUM"
        }
        actual_scope = sa.select(
            FinancialActualFact.account_id.label("account_id"),
            FinancialActualFact.calendar_period.label("period"),
        ).where(FinancialActualFact.run_id == run_id)
        budget_scope = sa.select(
            FinancialBudgetFact.account_id.label("account_id"),
            FinancialBudgetFact.calendar_period.label("period"),
        ).where(FinancialBudgetFact.run_id == run_id)
        if unit_id is not None:
            actual_scope = actual_scope.where(FinancialActualFact.unit_id == unit_id)
            budget_scope = budget_scope.where(FinancialBudgetFact.unit_id == unit_id)
        facts = sa.union_all(actual_scope, budget_scope).subquery()
        query = (
            sa.select(
                FinancialAccount.id,
                FinancialAccount.code,
                FinancialAccount.dre_classification,
                DreAccountMapping.line_code,
                sa.func.count().label("affected"),
                sa.func.array_agg(sa.distinct(facts.c.period)),
            )
            .join(
                facts,
                facts.c.account_id == FinancialAccount.id,
            )
            .outerjoin(
                DreAccountMapping,
                (DreAccountMapping.account_id == FinancialAccount.id)
                & (DreAccountMapping.version_id == version_id),
            )
            .group_by(
                FinancialAccount.id,
                FinancialAccount.code,
                DreAccountMapping.line_code,
            )
        )
        query = query.where(
            DreAccountMapping.status == "PENDING_APPROVAL"
            if approved
            else DreAccountMapping.id.is_(None)
        )
        if search:
            query = query.where(FinancialAccount.code.ilike(f"%{search}%"))
        grouped = query.subquery()
        total = int(
            session.scalar(sa.select(sa.func.count()).select_from(grouped)) or 0
        )
        page = session.execute(
            sa.select(grouped)
            .order_by(grouped.c.affected.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        rows = [
            BlockerRow(
                account_id=account_id,
                source_key=code,
                record_count=int(count),
                periods=sorted(period for period in periods if period is not None),
                status=(
                    "CANDIDATE"
                    if approved or classification in line_codes
                    else "UNMAPPED"
                ),
                line_candidate=(
                    current_line
                    if approved
                    else classification
                    if classification in line_codes
                    else None
                ),
                evidence=(
                    "Pending DRE assignment in this structure version"
                    if approved
                    else "Exact canonical classification code"
                    if classification in line_codes
                    else "No exact DRE line candidate"
                ),
            )
            for account_id, code, classification, current_line, count, periods in page
        ]
    elif blocker in ("BUDGET_UNMAPPED_ACCOUNT", "BUDGET_UNMAPPED_UNIT"):
        is_unit = blocker == "BUDGET_UNMAPPED_UNIT"
        key = (
            OperationalSourceRecord.typed_values["contract_label"].astext
            if is_unit
            else OperationalSourceRecord.identifier
        )
        condition = (
            FinancialBudgetFact.unit_id.is_(None)
            if is_unit
            else FinancialBudgetFact.account_id.is_(None)
        )
        query = (
            sa.select(
                OperationalSourceRecord.source_id,
                key.label("source_key"),
                sa.func.count().label("affected"),
                sa.func.array_agg(
                    sa.distinct(FinancialBudgetFact.calendar_period)
                ).label("periods"),
            )
            .join(
                FinancialBudgetFact,
                FinancialBudgetFact.source_record_id == OperationalSourceRecord.id,
            )
            .where(FinancialBudgetFact.run_id == run_id, condition, key.is_not(None))
            .group_by(OperationalSourceRecord.source_id, key)
        )
        if unit_id is not None:
            query = query.where(FinancialBudgetFact.unit_id == unit_id)
        if search:
            query = query.where(key.ilike(f"%{search}%"))
        grouped = query.subquery()
        total = int(
            session.scalar(sa.select(sa.func.count()).select_from(grouped)) or 0
        )
        page = session.execute(
            sa.select(grouped)
            .order_by(grouped.c.affected.desc(), grouped.c.source_id)
            .limit(limit)
            .offset(offset)
        ).all()
        rows = [
            BlockerRow(
                source_id=source_id,
                source_key=source_key,
                record_count=int(count),
                periods=sorted(period for period in periods if period is not None),
                status="UNMAPPED",
                evidence="Exact budget source field; select an approved canonical target",
            )
            for source_id, source_key, count, periods in page
        ]
    elif blocker == "BUDGET_PERIOD_UNRESOLVED":
        query = (
            sa.select(
                OperationalSourceRecord.source_id,
                OperationalSourceRecord.execution_id,
                FinancialBudgetFact.period_basis,
                sa.func.count().label("affected"),
            )
            .join(
                FinancialBudgetFact,
                FinancialBudgetFact.source_record_id == OperationalSourceRecord.id,
            )
            .where(
                FinancialBudgetFact.run_id == run_id,
                FinancialBudgetFact.calendar_period.is_(None),
            )
            .group_by(
                OperationalSourceRecord.source_id,
                OperationalSourceRecord.execution_id,
                FinancialBudgetFact.period_basis,
            )
        )
        if unit_id is not None:
            query = query.where(FinancialBudgetFact.unit_id == unit_id)
        grouped = query.subquery()
        total = int(
            session.scalar(sa.select(sa.func.count()).select_from(grouped)) or 0
        )
        page = session.execute(
            sa.select(grouped)
            .order_by(grouped.c.affected.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        rows = [
            BlockerRow(
                source_id=source_id,
                source_key=str(execution_id),
                record_count=int(count),
                status="UNRESOLVED",
                evidence=f"{basis}: source has no approved calendar start",
            )
            for source_id, execution_id, basis, count in page
        ]
    elif blocker in (
        "SOURCE_RECONCILIATION_UNRESOLVED",
        "SOURCE_RECONCILIATION_AMBIGUOUS",
    ):
        statuses = (
            ("AMBIGUOUS",)
            if blocker.endswith("AMBIGUOUS")
            else ("UNMAPPED", "BILLING_ONLY")
        )
        query = (
            sa.select(
                FinancialReconciliationItem,
                FinancialActualFact,
                FinancialBillingFact,
                ParsedSourceRecord.document_number,
            )
            .outerjoin(
                FinancialActualFact,
                FinancialActualFact.id == FinancialReconciliationItem.actual_fact_id,
            )
            .outerjoin(
                FinancialBillingFact,
                FinancialBillingFact.id == FinancialReconciliationItem.billing_fact_id,
            )
            .outerjoin(
                ParsedSourceRecord,
                ParsedSourceRecord.id == FinancialActualFact.parsed_record_id,
            )
            .where(
                FinancialReconciliationItem.run_id == run_id,
                FinancialReconciliationItem.status.in_(statuses),
            )
        )
        if unit_id is not None:
            query = query.where(
                sa.or_(
                    FinancialActualFact.unit_id == unit_id,
                    FinancialBillingFact.unit_id == unit_id,
                )
            )
        total = int(
            session.scalar(sa.select(sa.func.count()).select_from(query.subquery()))
            or 0
        )
        page = session.execute(
            query.order_by(FinancialReconciliationItem.id).limit(limit).offset(offset)
        ).all()
        rows = [
            BlockerRow(
                item_id=item.id,
                record_count=1,
                paired=bool(actual and billing),
                periods=[actual.calendar_period]
                if actual
                else [billing.competence_period]
                if billing and billing.competence_period
                else [],
                status="UNRESOLVED",
                evidence=(
                    f"{item.status}; NG {'yes' if actual else 'no'}; "
                    f"billing {'yes' if billing else 'no'}; "
                    f"account mapped {'yes' if (actual or billing) and (actual or billing).account_id else 'no'}; "
                    f"unit mapped {'yes' if (actual or billing) and (actual or billing).unit_id else 'no'}; "
                    f"document match {'yes' if document and billing and document.strip() == billing.invoice_number.strip() else 'unknown'}; "
                    "amount relation unverified"
                ),
            )
            for item, actual, billing, document in page
        ]
    elif blocker in SUMMARY_BLOCKERS:
        periods = overview(session, user, run_id, version_id, unit_id).periods
        matching = [item for item in periods if item.blockers.get(blocker, 0)]
        total = len(matching)
        rows = [
            BlockerRow(
                source_key=blocker,
                record_count=item.blockers[blocker],
                periods=[item.scope.period],
                status="UNRESOLVED",
                evidence=BLOCKER_GUIDANCE.get(
                    blocker, "Review source configuration for this period"
                ),
            )
            for item in matching[offset : offset + limit]
        ]
    else:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Unknown blocker type")
    return BlockerPage(
        blocker=blocker, total=total, limit=limit, offset=offset, rows=rows
    )


def reject_candidate(session: Session, user: User, request: CandidateRejection) -> UUID:
    from onyx.db.enums import Permission

    get_source(session, user, request.source_id, Permission.MANAGE_TON_SOURCES)
    source_key = (
        ParsedSourceRecord.administrative_unit
        if request.kind == "UNIT"
        else ParsedSourceRecord.account_code
    )
    if (
        session.scalar(
            sa.select(ParsedSourceRecord.id)
            .where(
                ParsedSourceRecord.source_id == request.source_id,
                source_key == request.source_key,
            )
            .limit(1)
        )
        is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Source value not found")
    session.execute(sa.text("SELECT pg_advisory_xact_lock(4433009)"))
    if request.evidence == "EXACT_CODE":
        candidate = _candidate(
            session, user, request.source_id, request.kind, request.source_key
        )
        if (
            candidate is None
            or candidate.target_id != request.target_id
            or candidate.evidence != "EXACT_CODE"
            or request.reference_digest is not None
        ):
            raise OnyxError(OnyxErrorCode.CONFLICT, "Candidate evidence changed")
    else:
        if request.target_id is not None or request.reference_digest is None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Legacy reference is required")
        evidence = session.scalar(
            sa.select(FinancialLegacyCandidate.id)
            .where(
                FinancialLegacyCandidate.source_id == request.source_id,
                FinancialLegacyCandidate.kind == request.kind,
                FinancialLegacyCandidate.source_key == request.source_key,
                FinancialLegacyCandidate.reference_digest == request.reference_digest,
            )
            .limit(1)
        )
        if evidence is None:
            raise OnyxError(OnyxErrorCode.CONFLICT, "Candidate evidence changed")
        if (
            session.scalar(
                sa.select(FinancialCandidateDecision.id)
                .where(
                    FinancialCandidateDecision.source_id == request.source_id,
                    FinancialCandidateDecision.kind == request.kind,
                    FinancialCandidateDecision.source_key == request.source_key,
                    FinancialCandidateDecision.evidence == "LEGACY_REFERENCE",
                    FinancialCandidateDecision.reference_digest
                    == request.reference_digest,
                )
                .limit(1)
            )
            is not None
        ):
            raise OnyxError(OnyxErrorCode.CONFLICT, "Candidate already rejected")
    rejected = FinancialCandidateDecision(
        source_id=request.source_id,
        kind=request.kind,
        source_key=request.source_key,
        target_id=request.target_id,
        evidence=request.evidence,
        reference_digest=request.reference_digest,
        reason=request.reason.strip(),
        created_by=user.id,
    )
    session.add(rejected)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_FINANCIAL_CANDIDATE_REJECT,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.FINANCIAL_MAPPING,
        resource_id=rejected.id,
    )
    return rejected.id
