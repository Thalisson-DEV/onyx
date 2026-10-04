"""Account classification table over the versioned NG ACCOUNT mappings.

The natureza of an NG code lives in ``ton_financial_mapping`` (latest revision
wins). This module adds the review state (origin, awaiting confirmation,
confirmed) and the AI pre-classification suggestions, which never change a
mapping on their own. Every route here is TON-administrator only.
"""

import datetime
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import dre as dre_repository
from onyx.db.ton.acl import is_ton_administrator
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.financial_domain import create_account, create_mapping
from onyx.db.ton.models import (
    AccountClassificationBriefing,
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
    BriefingView,
    ClassificationChange,
    ClassificationConfirm,
    ClassificationConfirmBatch,
    ClassificationOrigin,
    ClassificationRow,
    ClassificationStatus,
    ClassificationTable,
    DreGroupView,
    EntryView,
    NatureCreate,
    NatureView,
    SuggestionView,
)
from onyx.ton.dre.models import (
    DreAccountAssignment,
    DreLineDefinition,
    DreLineType,
    DreVersionCreate,
)
from onyx.ton.financial_domain.models import AccountCreate, MappingCreate, MappingKind
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


@dataclass
class _DreLayout:
    """Where each natureza sits in the managerial DRE (newest version)."""

    version: DreStructureVersion | None
    account_group: dict[UUID, tuple[str, str]]
    groups: list[DreGroupView]


def _newest_version(session: Session) -> DreStructureVersion | None:
    """Newest version of the structure with the most account assignments."""
    versions = session.scalars(
        sa.select(DreStructureVersion).order_by(DreStructureVersion.number.desc())
    ).all()
    newest: dict[UUID, DreStructureVersion] = {}
    for version in versions:
        newest.setdefault(version.structure_id, version)
    if not newest:
        return None
    sizes = dict(
        session.execute(
            sa.select(DreAccountMapping.version_id, sa.func.count())
            .where(
                DreAccountMapping.version_id.in_([item.id for item in newest.values()])
            )
            .group_by(DreAccountMapping.version_id)
        ).all()
    )
    return max(newest.values(), key=lambda item: sizes.get(item.id, 0))


def _dre_layout(session: Session) -> _DreLayout:
    version = _newest_version(session)
    if version is None:
        return _DreLayout(None, {}, [])
    lines = {line["code"]: line for line in version.lines}
    groups = [
        DreGroupView(code=line["code"], label=line["label"])
        for line in sorted(version.lines, key=lambda item: item["position"])
        if line["line_type"] == DreLineType.SUBTOTAL.value
        and any(
            child.get("parent_code") == line["code"]
            and child["line_type"] == DreLineType.SOURCE_SUM.value
            for child in version.lines
        )
    ]
    account_group: dict[UUID, tuple[str, str]] = {}
    for item in session.scalars(
        sa.select(DreAccountMapping).where(DreAccountMapping.version_id == version.id)
    ):
        line = lines.get(item.line_code)
        parent = lines.get(line.get("parent_code")) if line else None
        target = parent or line
        if target:
            account_group[item.account_id] = (target["code"], target["label"])
    return _DreLayout(version, account_group, groups)


def _natures(
    session: Session, layout: _DreLayout, usage: dict[UUID, int]
) -> list[NatureView]:
    result = []
    for account in session.scalars(
        sa.select(FinancialAccount).order_by(FinancialAccount.code)
    ):
        group = layout.account_group.get(account.id)
        result.append(
            NatureView(
                account_id=account.id,
                code=account.code,
                natureza=account.label,
                dre_group=group[1] if group else OUT_OF_RESULT,
                dre_group_code=group[0] if group else None,
                accounts=usage.get(account.id, 0),
            )
        )
    return result


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
    current = _current_mappings(session, source.id)
    layout = _dre_layout(session)
    natures = _natures(
        session,
        layout,
        Counter(
            entry.mapping.account_id
            for entry in current.values()
            if entry.mapping.account_id is not None
        ),
    )
    nature_by_id = {item.account_id: item for item in natures}
    bases = dict(
        session.execute(
            sa.select(FinancialAccount.id, FinancialAccount.actual_amount_basis)
        ).all()
    )
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
                    question=suggestion.question,
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
                decided_by_person=decided is not None
                and decided.created_by is not None,
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
        groups=layout.groups,
        rows=rows,
        briefing=_latest_briefing(session, source.id),
        changes_since_calculation=_changes_since(session, source.id, run),
    )


def _latest_briefing(session: Session, source_id: UUID) -> BriefingView | None:
    item = session.scalar(
        sa.select(AccountClassificationBriefing)
        .where(AccountClassificationBriefing.source_id == source_id)
        .order_by(AccountClassificationBriefing.created_at.desc())
        .limit(1)
    )
    if item is None:
        return None
    return BriefingView(
        summary=item.summary, model_name=item.model_name, created_at=item.created_at
    )


def _changes_since(
    session: Session, source_id: UUID, run: FinancialNormalizationRun | None
) -> int:
    """Account mapping versions the latest normalization does not include yet."""
    if run is None:
        return 0
    return int(
        session.scalar(
            sa.select(sa.func.count())
            .select_from(FinancialMapping)
            .join(
                FinancialMappingRevision,
                FinancialMappingRevision.id == FinancialMapping.revision_id,
            )
            .where(
                FinancialMapping.source_id == source_id,
                FinancialMapping.kind == MappingKind.ACCOUNT.value,
                FinancialMappingRevision.number > run.mapping_revision_number,
            )
        )
        or 0
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
                question=item.question,
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


def record_briefing(
    session: Session,
    user: User,
    source_id: UUID,
    summary: str,
    model_name: str | None,
    codes: list[str],
) -> None:
    session.add(
        AccountClassificationBriefing(
            source_id=source_id,
            summary=summary,
            model_name=model_name,
            account_codes=codes,
            created_by=user.id,
        )
    )
    session.flush()


def confirm_batch(
    session: Session, user: User, source_id: UUID, request: ClassificationConfirmBatch
) -> int:
    """Confirm several codes at once with one note (e.g. every code where the
    current natureza and the assistant agree)."""
    note = (request.note or "").strip() or (
        "Confirmada em lote: classificação atual e assistente concordam"
    )
    count = 0
    for code in dict.fromkeys(request.account_codes):
        confirm_classification(
            session,
            user,
            source_id,
            ClassificationConfirm(account_code=code, note=note),
        )
        count += 1
    return count


def list_entries(
    session: Session, user: User, source_id: UUID, code: str, limit: int
) -> list[EntryView]:
    """Largest entries of a code in the latest normalization."""
    _require_admin(user)
    get_source(session, user, source_id)
    run = _latest_run(session)
    if run is None:
        return []
    rows = session.execute(
        sa.select(
            ParsedSourceRecord.emission_date,
            ParsedSourceRecord.administrative_unit,
            ParsedSourceRecord.document_number,
            ParsedSourceRecord.history,
            FinancialActualFact.movement_amount,
        )
        .join(
            FinancialActualFact,
            FinancialActualFact.parsed_record_id == ParsedSourceRecord.id,
        )
        .where(
            FinancialActualFact.run_id == run.id,
            ParsedSourceRecord.source_id == source_id,
            ParsedSourceRecord.account_code == code,
        )
        .order_by(
            sa.func.abs(sa.func.coalesce(FinancialActualFact.movement_amount, 0)).desc()
        )
        .limit(limit)
    ).all()
    return [
        EntryView(
            date=date,
            unit=_unit_name(unit),
            document=document,
            history=" ".join((history or "").split()),
            amount=_cents(amount) if amount is not None else None,
        )
        for date, unit, document, history, amount in rows
    ]


def _unit_name(value: str | None) -> str | None:
    """NG units come as '000009 - MOSSORÓ-RN '."""
    if not value:
        return None
    return value.split(" - ", 1)[-1].strip()


def create_nature(session: Session, user: User, request: NatureCreate) -> NatureView:
    """New natureza under a DRE group: a canonical account plus a new DRE
    structure version with its own line, like a row added to AUXILIARES."""
    _require_admin(user)
    name = " ".join(request.natureza.split()).upper()
    if session.scalar(
        sa.select(FinancialAccount.id).where(
            sa.func.upper(FinancialAccount.label) == name
        )
    ):
        raise OnyxError(OnyxErrorCode.CONFLICT, "Natureza already exists")
    layout = _dre_layout(session)
    group = next(
        (item for item in layout.groups if item.code == request.dre_group_code), None
    )
    if layout.version is None or group is None:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Unknown DRE group")
    lines = [DreLineDefinition.model_validate(item) for item in layout.version.lines]
    siblings = [
        line
        for line in lines
        if line.parent_code == group.code and line.line_type == DreLineType.SOURCE_SUM
    ]
    prefix = group.code.lstrip("g")
    number = 1 + max(
        (
            int(line.code.rsplit(".", 1)[-1])
            for line in siblings
            if line.code.rsplit(".", 1)[-1].isdigit()
        ),
        default=0,
    )
    line_code = f"n{prefix}.{number:02d}"
    account_code = f"{prefix}.{number:02d}"
    while session.scalar(
        sa.select(FinancialAccount.id).where(FinancialAccount.code == account_code)
    ):
        number += 1
        line_code, account_code = f"n{prefix}.{number:02d}", f"{prefix}.{number:02d}"
    template = (
        session.scalar(
            sa.select(DreAccountMapping.account_id)
            .where(
                DreAccountMapping.version_id == layout.version.id,
                DreAccountMapping.line_code == siblings[-1].code,
            )
            .limit(1)
        )
        if siblings
        else None
    )
    sibling_account = session.get(FinancialAccount, template) if template else None
    account = create_account(
        session,
        user,
        AccountCreate(
            code=account_code,
            label=name,
            dre_classification=(
                sibling_account.dre_classification if sibling_account else "EXPENSE"
            ),
            actual_amount_basis=(
                sibling_account.actual_amount_basis if sibling_account else "MOVEMENT"
            ),
        ),
    )
    anchor = max(
        (line.position for line in siblings),
        default=next(line.position for line in lines if line.code == group.code),
    )
    shifted = [
        line.model_copy(update={"position": line.position + 1})
        if line.position > anchor
        else line
        for line in lines
    ]
    shifted.append(
        DreLineDefinition(
            code=line_code,
            label=name.capitalize(),
            position=anchor + 1,
            parent_code=group.code,
            line_type=DreLineType.SOURCE_SUM,
        )
    )
    current = dre_repository.get_latest_version(
        session, user, layout.version.structure_id
    )
    assignments = [*current.assignments]
    assignments.append(
        DreAccountAssignment(
            account_id=account.id, line_code=line_code, status="APPROVED"
        )
    )
    dre_repository.create_version(
        session,
        user,
        layout.version.structure_id,
        DreVersionCreate(
            lines=sorted(shifted, key=lambda line: line.position),
            assignments=assignments,
            reason=f"Nova natureza {name}: {request.reason.strip()}"[:500],
        ),
    )
    return NatureView(
        account_id=account.id,
        code=account.code,
        natureza=account.label,
        dre_group=group.label,
        dre_group_code=group.code,
        accounts=0,
    )
