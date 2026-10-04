"""Account classification table over the versioned NG ACCOUNT mappings.

The natureza of an NG code lives in ``ton_financial_mapping`` (latest revision
wins). This module adds the review state (origin, awaiting confirmation,
confirmed) and the AI pre-classification suggestions, which never change a
mapping on their own. Every route here is TON-administrator only.
"""

import datetime
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton.acl import is_ton_administrator
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.financial_domain import create_mapping
from onyx.db.ton.models import (
    AccountClassificationReview,
    AccountClassificationSuggestion,
    BusinessUnit,
    DreAccountMapping,
    DreStructureVersion,
    FinancialAccount,
    FinancialActualFact,
    FinancialMapping,
    FinancialMappingRevision,
    FinancialNormalizationRun,
    ParsedSourceRecord,
)
from onyx.db.ton.sources import get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.account_classification.logic import (
    ParsedSuggestion,
    SuggestionInput,
    default_status,
    infer_origin,
    prefix_pattern,
)
from onyx.ton.account_classification.models import (
    ClassificationChange,
    ClassificationConfirm,
    ClassificationOrigin,
    ClassificationRow,
    ClassificationStatus,
    ClassificationTable,
    NatureView,
    SuggestionView,
)
from onyx.ton.financial_domain.models import MappingCreate, MappingKind
from onyx.utils.audit import AuditAction, AuditOutcome

OUT_OF_RESULT = "Fora do resultado"
SUCCEEDED = "SUCCEEDED"
CENT = Decimal("0.01")


def _require_admin(user: User) -> None:
    if not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "Account classification requires admin access"
        )


def _latest_run(session: Session) -> FinancialNormalizationRun | None:
    return session.scalar(
        sa.select(FinancialNormalizationRun)
        .where(FinancialNormalizationRun.status == SUCCEEDED)
        .order_by(FinancialNormalizationRun.started_at.desc())
        .limit(1)
    )


def resolve_source_id(session: Session, source_id: UUID | None) -> UUID:
    """The NG source of the latest normalization, else any source with ACCOUNT
    mappings."""
    if source_id is not None:
        return source_id
    run = _latest_run(session)
    if run is not None:
        found = session.scalar(
            sa.select(ParsedSourceRecord.source_id)
            .join(
                FinancialActualFact,
                FinancialActualFact.parsed_record_id == ParsedSourceRecord.id,
            )
            .where(FinancialActualFact.run_id == run.id)
            .limit(1)
        )
        if found is not None:
            return found
    found = session.scalar(
        sa.select(FinancialMapping.source_id)
        .where(FinancialMapping.kind == MappingKind.ACCOUNT.value)
        .limit(1)
    )
    if found is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "No NG source with accounts")
    return found


def _dre_groups(session: Session) -> dict[UUID, str]:
    """Account -> parent DRE line label, from the newest version of each
    structure."""
    versions = session.scalars(
        sa.select(DreStructureVersion).order_by(DreStructureVersion.number.desc())
    ).all()
    newest: dict[UUID, DreStructureVersion] = {}
    for version in versions:
        newest.setdefault(version.structure_id, version)
    result: dict[UUID, str] = {}
    for version in newest.values():
        labels = {line["code"]: line for line in version.lines}
        for item in session.scalars(
            sa.select(DreAccountMapping).where(
                DreAccountMapping.version_id == version.id
            )
        ):
            line = labels.get(item.line_code)
            parent = labels.get(line.get("parent_code")) if line else None
            label = (parent or line or {}).get("label")
            if label:
                result.setdefault(item.account_id, label)
    return result


def _natures(session: Session) -> list[NatureView]:
    groups = _dre_groups(session)
    return [
        NatureView(
            account_id=account.id,
            natureza=account.label,
            dre_group=groups.get(account.id, OUT_OF_RESULT),
        )
        for account in session.scalars(
            sa.select(FinancialAccount).order_by(FinancialAccount.code)
        )
    ]


@dataclass
class _Current:
    mapping: FinancialMapping
    reason: str | None
    created_by: UUID | None
    created_at: datetime.datetime


def _current_mappings(session: Session, source_id: UUID) -> dict[str, _Current]:
    rows = session.execute(
        sa.select(
            FinancialMapping,
            FinancialMappingRevision.reason,
            FinancialMappingRevision.created_by,
            FinancialMappingRevision.created_at,
        )
        .join(
            FinancialMappingRevision,
            FinancialMappingRevision.id == FinancialMapping.revision_id,
        )
        .where(
            FinancialMapping.source_id == source_id,
            FinancialMapping.kind == MappingKind.ACCOUNT.value,
        )
        .order_by(FinancialMappingRevision.number.desc())
    ).all()
    result: dict[str, _Current] = {}
    for mapping, reason, created_by, created_at in rows:
        result.setdefault(
            mapping.source_key, _Current(mapping, reason, created_by, created_at)
        )
    return result


def _latest_by_code(
    session: Session, model: type, source_id: UUID
) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in session.scalars(
        sa.select(model)
        .where(model.source_id == source_id)  # type: ignore[attr-defined]
        .order_by(model.created_at.desc())  # type: ignore[attr-defined]
    ):
        result.setdefault(item.account_code, item)
    return result


@dataclass
class _Usage:
    description: str = ""
    entries: int = 0
    movement: Decimal = Decimal(0)
    final: Decimal = Decimal(0)
    monthly_movement: dict[str, Decimal] | None = None
    monthly_final: dict[str, Decimal] | None = None
    units: set[str] | None = None


def _usage(
    session: Session, source_id: UUID, run_id: UUID | None
) -> tuple[dict[str, _Usage], list[str]]:
    if run_id is None:
        return {}, []
    period = FinancialActualFact.calendar_period
    rows = session.execute(
        sa.select(
            ParsedSourceRecord.account_code,
            sa.func.max(ParsedSourceRecord.account_label),
            period,
            BusinessUnit.name,
            sa.func.count(),
            sa.func.coalesce(sa.func.sum(FinancialActualFact.movement_amount), 0),
            sa.func.coalesce(sa.func.sum(FinancialActualFact.final_amount), 0),
        )
        .join(
            ParsedSourceRecord,
            ParsedSourceRecord.id == FinancialActualFact.parsed_record_id,
        )
        .outerjoin(BusinessUnit, BusinessUnit.id == FinancialActualFact.unit_id)
        .where(
            FinancialActualFact.run_id == run_id,
            ParsedSourceRecord.source_id == source_id,
        )
        .group_by(ParsedSourceRecord.account_code, period, BusinessUnit.name)
    ).all()
    usage: dict[str, _Usage] = defaultdict(_Usage)
    periods: set[str] = set()
    for code, label, month, unit, count, movement, final in rows:
        key = month.strftime("%Y-%m")
        periods.add(key)
        item = usage[code]
        item.description = item.description or (label or "").strip()
        item.entries += count
        item.movement += Decimal(movement)
        item.final += Decimal(final)
        item.monthly_movement = item.monthly_movement or defaultdict(Decimal)
        item.monthly_final = item.monthly_final or defaultdict(Decimal)
        item.monthly_movement[key] += Decimal(movement)
        item.monthly_final[key] += Decimal(final)
        item.units = item.units or set()
        if unit:
            item.units.add(unit.strip())
    return usage, sorted(periods)


def _labels(session: Session, source_id: UUID, codes: set[str]) -> dict[str, str]:
    """NG description of codes without usage in the current run."""
    if not codes:
        return {}
    rows = session.execute(
        sa.select(
            ParsedSourceRecord.account_code,
            sa.func.max(ParsedSourceRecord.account_label),
        )
        .where(
            ParsedSourceRecord.source_id == source_id,
            ParsedSourceRecord.account_code.in_(codes),
        )
        .group_by(ParsedSourceRecord.account_code)
    ).all()
    return {code: (label or "").strip() for code, label in rows}


def _user_names(session: Session, ids: set[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    return dict(
        session.execute(sa.select(User.id, User.email).where(User.id.in_(ids))).all()
    )


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT)


def _code_key(code: str) -> tuple:
    return tuple(int(part) if part.isdigit() else part for part in code.split("."))


def classification_table(
    session: Session, user: User, source_id: UUID | None
) -> ClassificationTable:
    _require_admin(user)
    source = get_source(session, user, resolve_source_id(session, source_id))
    run = _latest_run(session)
    natures = _natures(session)
    nature_by_id = {item.account_id: item for item in natures}
    bases = dict(
        session.execute(
            sa.select(FinancialAccount.id, FinancialAccount.actual_amount_basis)
        ).all()
    )
    current = _current_mappings(session, source.id)
    reviews = _latest_by_code(session, AccountClassificationReview, source.id)
    suggestions = _latest_by_code(session, AccountClassificationSuggestion, source.id)
    usage, periods = _usage(session, source.id, run.id if run else None)
    codes = set(current) | set(usage)
    labels = _labels(session, source.id, codes - set(usage))

    states: dict[str, tuple[ClassificationStatus, ClassificationOrigin | None]] = {}
    for code in codes:
        mapping = current.get(code)
        review = reviews.get(code)
        if mapping is None:
            states[code] = (ClassificationStatus.PENDING, None)
        elif isinstance(review, AccountClassificationReview):
            states[code] = (
                ClassificationStatus(review.status),
                ClassificationOrigin(review.origin),
            )
        else:
            origin = infer_origin(mapping.reason)
            states[code] = (default_status(origin), origin)
    confirmed = [
        (code, nature_by_id[current[code].mapping.account_id].natureza)
        for code, (status, _origin) in states.items()
        if status is ClassificationStatus.CONFIRMED
        and current[code].mapping.account_id in nature_by_id
    ]
    names = _user_names(
        session,
        {
            item
            for item in [
                *(entry.created_by for entry in current.values()),
                *(
                    entry.created_by
                    for entry in reviews.values()
                    if isinstance(entry, AccountClassificationReview)
                ),
            ]
            if item is not None
        },
    )

    rows: list[ClassificationRow] = []
    for code in sorted(codes, key=_code_key):
        mapping = current.get(code)
        review = reviews.get(code)
        status, origin = states[code]
        nature = (
            nature_by_id.get(mapping.mapping.account_id)
            if mapping and mapping.mapping.account_id
            else None
        )
        uses = usage.get(code) or _Usage(description=labels.get(code, ""))
        final_basis = nature is not None and bases.get(nature.account_id) == "FINAL"
        monthly = (uses.monthly_final if final_basis else uses.monthly_movement) or {}
        # Only a confirmation speaks for the row; while awaiting, the mapping's
        # own reason explains why the code got its natureza.
        decided = (
            review
            if isinstance(review, AccountClassificationReview)
            and review.status == ClassificationStatus.CONFIRMED.value
            and (mapping is None or review.created_at >= mapping.created_at)
            else None
        )
        if decided is not None:
            reason, author, when = decided.note, decided.created_by, decided.created_at
        elif mapping is not None:
            reason, author, when = (
                mapping.reason,
                mapping.created_by,
                mapping.created_at,
            )
        else:
            reason, author, when = None, None, None
        suggestion = suggestions.get(code)
        suggestion_view = None
        if isinstance(suggestion, AccountClassificationSuggestion):
            suggested = nature_by_id.get(suggestion.account_id)
            if suggested is not None:
                suggestion_view = SuggestionView(
                    account_id=suggestion.account_id,
                    natureza=suggested.natureza,
                    confidence=suggestion.confidence,
                    rationale=suggestion.rationale,
                    model_name=suggestion.model_name,
                    created_at=suggestion.created_at,
                    agrees_with_current=nature is not None
                    and nature.account_id == suggestion.account_id,
                )
        rows.append(
            ClassificationRow(
                account_code=code,
                description=uses.description,
                account_id=nature.account_id if nature else None,
                natureza=nature.natureza if nature else None,
                dre_group=nature.dre_group if nature else None,
                status=status,
                origin=origin,
                reason=reason,
                decided_by=names.get(author) if author else None,
                decided_at=when,
                entries=uses.entries,
                total_amount=_cents(uses.final if final_basis else uses.movement),
                monthly={key: _cents(monthly.get(key, Decimal(0))) for key in periods},
                units=sorted(uses.units or ()),
                pattern=prefix_pattern(code, confirmed),
                suggestion=suggestion_view,
            )
        )
    return ClassificationTable(
        source_id=source.id,
        source_name=source.display_name,
        normalization_run_id=run.id if run else None,
        periods=periods,
        natures=natures,
        rows=rows,
    )


def _review(
    session: Session,
    user: User,
    source_id: UUID,
    code: str,
    mapping_id: UUID | None,
    status: ClassificationStatus,
    origin: ClassificationOrigin,
    note: str,
) -> AccountClassificationReview:
    review = AccountClassificationReview(
        source_id=source_id,
        account_code=code,
        mapping_id=mapping_id,
        status=status.value,
        origin=origin.value,
        note=note,
        created_by=user.id,
    )
    session.add(review)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_ACCOUNT_CLASSIFICATION_REVIEW,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.ACCOUNT_CLASSIFICATION,
        resource_id=review.id,
        extra={"account_code": code, "status": status.value},
    )
    return review


def confirm_classification(
    session: Session, user: User, source_id: UUID, request: ClassificationConfirm
) -> AccountClassificationReview:
    """The Controladoria agrees with the current natureza of a code."""
    _require_admin(user)
    get_source(session, user, source_id, Permission.MANAGE_TON_SOURCES)
    current = _current_mappings(session, source_id).get(request.account_code)
    if current is None:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Code has no classification to confirm"
        )
    latest = _latest_by_code(session, AccountClassificationReview, source_id).get(
        request.account_code
    )
    origin = (
        ClassificationOrigin(latest.origin)
        if isinstance(latest, AccountClassificationReview)
        else infer_origin(current.reason)
    )
    note = (request.note or "").strip() or "Classificação confirmada pela Controladoria"
    return _review(
        session,
        user,
        source_id,
        request.account_code,
        current.mapping.id,
        ClassificationStatus.CONFIRMED,
        origin,
        note,
    )


def change_classification(
    session: Session, user: User, source_id: UUID, request: ClassificationChange
) -> AccountClassificationReview:
    """New natureza for a code: a new mapping version plus a confirmed review."""
    _require_admin(user)
    reason = request.reason.strip()
    mapping = create_mapping(
        session,
        user,
        MappingCreate(
            source_id=source_id,
            kind=MappingKind.ACCOUNT,
            source_key=request.account_code,
            account_id=request.account_id,
            reason=reason,
        ),
    )
    return _review(
        session,
        user,
        source_id,
        request.account_code,
        mapping.id,
        ClassificationStatus.CONFIRMED,
        ClassificationOrigin.MANUAL,
        reason,
    )


def suggestion_inputs(
    table: ClassificationTable, session: Session, codes: list[str]
) -> list[SuggestionInput]:
    """Rows to pre-classify: the requested codes, else all not yet confirmed."""
    wanted = set(codes)
    rows = [
        row
        for row in table.rows
        if (row.account_code in wanted)
        or (not wanted and row.status is not ClassificationStatus.CONFIRMED)
    ]
    history = _history_samples(
        session,
        table.source_id,
        table.normalization_run_id,
        [r.account_code for r in rows],
    )
    return [
        SuggestionInput(
            code=row.account_code,
            description=row.description,
            current_natureza=(
                row.natureza
                if row.status is not ClassificationStatus.CONFIRMED
                else None
            ),
            entries=row.entries,
            total_amount=f"{row.total_amount:.2f}",
            units=row.units,
            history=history.get(row.account_code, []),
            pattern=row.pattern,
        )
        for row in rows
    ]


def _history_samples(
    session: Session, source_id: UUID, run_id: UUID | None, codes: list[str]
) -> dict[str, list[str]]:
    """Distinct histories of the largest entries of each code."""
    if not codes or run_id is None:
        return {}
    ranked = (
        sa.select(
            ParsedSourceRecord.account_code,
            ParsedSourceRecord.history,
            sa.func.row_number()
            .over(
                partition_by=ParsedSourceRecord.account_code,
                order_by=sa.func.abs(
                    sa.func.coalesce(FinancialActualFact.movement_amount, 0)
                ).desc(),
            )
            .label("position"),
        )
        .join(
            FinancialActualFact,
            FinancialActualFact.parsed_record_id == ParsedSourceRecord.id,
        )
        .where(
            FinancialActualFact.run_id == run_id,
            ParsedSourceRecord.source_id == source_id,
            ParsedSourceRecord.account_code.in_(codes),
        )
        .subquery()
    )
    result: dict[str, list[str]] = defaultdict(list)
    for code, history in session.execute(
        sa.select(ranked.c.account_code, ranked.c.history)
        .where(ranked.c.position <= 12)
        .order_by(ranked.c.account_code, ranked.c.position)
    ):
        text = " ".join((history or "").split())
        if text and text not in result[code]:
            result[code].append(text)
    return result


def record_suggestions(
    session: Session,
    user: User,
    table: ClassificationTable,
    parsed: list[ParsedSuggestion],
    model_name: str | None,
    evidence: dict[str, dict],
) -> int:
    by_name = {item.natureza: item.account_id for item in table.natures}
    count = 0
    for item in parsed:
        account_id = by_name.get(item.natureza)
        if account_id is None:
            continue
        session.add(
            AccountClassificationSuggestion(
                source_id=table.source_id,
                account_code=item.code,
                account_id=account_id,
                method="AI",
                confidence=item.confidence.value,
                rationale=item.rationale,
                model_name=model_name,
                evidence=evidence.get(item.code, {}),
                created_by=user.id,
            )
        )
        count += 1
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_ACCOUNT_CLASSIFICATION_SUGGEST,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.SOURCE,
        resource_id=table.source_id,
        extra={"suggested": count, "model": model_name},
    )
    return count
