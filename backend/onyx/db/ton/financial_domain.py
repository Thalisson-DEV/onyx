"""Tenant-scoped persistence and projections for canonical financial facts."""

import datetime
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton.acl import business_unit_visible_clause, is_ton_administrator
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.closing_treatments import rules_up_to, treatment_number
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.financial_review import get_review_run, load_finding_states
from onyx.db.ton.import_profiles import get_execution
from onyx.db.ton.models import (
    BusinessUnit,
    FinancialAccount,
    FinancialActualFact,
    FinancialAmountBasisRevision,
    FinancialBillingFact,
    FinancialBudgetFact,
    FinancialDerivedFact,
    FinancialMapping,
    FinancialMappingRevision,
    FinancialNormalizationRun,
    FinancialReconciliationDecision,
    FinancialReconciliationItem,
    ImportProfile,
    ImportProfileExecution,
    OperationalSourceRecord,
    ParsedSourceRecord,
    ReviewRun,
    SourceSnapshot,
)
from onyx.db.ton.sources import check_page, get_source
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.financial_domain import treatments
from onyx.ton.financial_domain.models import (
    AccountCreate,
    BudgetInput,
    DreInputDataset,
    FactView,
    InputPolicy,
    MappingCreate,
    MappingKind,
    MappingView,
    NormalizationRequest,
    ReadinessView,
    TreatmentEffect,
)
from onyx.ton.financial_review.catalog import DATASET_POLICY_VERSION
from onyx.ton.financial_review.dataset import (
    dataset_revision,
    excluded_rows,
    record_dispositions,
)
from onyx.ton.financial_review.models import (
    DOWNSTREAM_SAFE_DISPOSITIONS,
    ReviewDisposition,
)
from onyx.ton.financial_review.rules import ng_invoice_key
from onyx.ton.ng_financial.models import ProfileExecutionStatus
from onyx.ton.operational_import.parser import (
    BILLING_KEY,
    BUDGET_ANNUAL_KEY,
    BUDGET_TERM_KEY,
)
from onyx.utils.audit import AuditAction, AuditOutcome

BATCH_SIZE = 500
DERIVATION_VERSION = "billing-vba-emission-match-1"
AUTHORITY_POLICY_VERSION = "ng-actual-billing-diagnostic-1"
DUPLICATE_DOCUMENT_RULE = "NGF-DUP-DOC"
# UNIT mapping key for NG records whose source unit is blank. An explicit
# mapping keeps these records in one visible bucket instead of no unit.
BLANK_UNIT_KEY = "(sem unidade)"
TAX_COMPONENTS: tuple[tuple[str, str], ...] = (
    ("iss_retained", "ISS"),
    ("inss_retained", "INSS"),
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _period(value: datetime.date) -> datetime.date:
    return datetime.date(value.year, value.month, 1)


def _optional_decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _insert_batches(
    session: Session, model: type[Any], rows: list[dict[str, Any]]
) -> None:
    for start in range(0, len(rows), BATCH_SIZE):
        session.execute(
            sa.insert(cast(sa.Table, model.__table__)), rows[start : start + BATCH_SIZE]
        )


def create_account(
    session: Session, user: User, request: AccountCreate
) -> FinancialAccount:
    # Account creation is a tenant-level financial configuration action.
    if not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "Financial accounts require admin access"
        )
    existing = session.scalar(
        sa.select(FinancialAccount).where(FinancialAccount.code == request.code)
    )
    if existing is not None:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Financial account code exists")
    account = FinancialAccount(**request.model_dump())
    session.add(account)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_FINANCIAL_ACCOUNT_CREATE,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.FINANCIAL_ACCOUNT,
        resource_id=account.id,
    )
    return account


def list_accounts(
    session: Session, _user: User, limit: int, offset: int, search: str | None = None
) -> list[FinancialAccount]:
    check_page(limit, offset)
    query = sa.select(FinancialAccount)
    if search:
        query = query.where(FinancialAccount.code.ilike(f"%{search}%"))
    return list(
        session.scalars(
            query.order_by(FinancialAccount.code, FinancialAccount.id)
            .limit(limit)
            .offset(offset)
        )
    )


def _mapping_revision_number(session: Session) -> int:
    return int(
        session.scalar(sa.select(sa.func.max(FinancialMappingRevision.number))) or 0
    )


def _basis_revision_number(session: Session) -> int:
    return int(
        session.scalar(sa.select(sa.func.max(FinancialAmountBasisRevision.number))) or 0
    )


def _basis_index(session: Session, number: int) -> dict[UUID, str]:
    revisions = session.scalars(
        sa.select(FinancialAmountBasisRevision)
        .where(FinancialAmountBasisRevision.number <= number)
        .order_by(FinancialAmountBasisRevision.number.desc())
    )
    result: dict[UUID, str] = {}
    for revision in revisions:
        result.setdefault(revision.account_id, revision.basis)
    return result


def approve_amount_basis(
    session: Session, user: User, account_id: UUID, basis: str, reason: str
) -> FinancialAmountBasisRevision:
    if not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.ADMIN_ONLY, "Amount basis requires admin access")
    if basis not in ("MOVEMENT", "FINAL") or not reason.strip():
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Basis and reason are required")
    if session.get(FinancialAccount, account_id) is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Financial account not found")
    session.execute(sa.text("SELECT pg_advisory_xact_lock(4433007)"))
    revision = FinancialAmountBasisRevision(
        number=_basis_revision_number(session) + 1,
        account_id=account_id,
        basis=basis,
        reason=reason.strip(),
        created_by=user.id,
    )
    session.add(revision)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_FINANCIAL_AMOUNT_BASIS_VERSION,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.FINANCIAL_ACCOUNT,
        resource_id=account_id,
        extra={"revision": revision.number},
    )
    return revision


def create_mapping(session: Session, user: User, request: MappingCreate) -> MappingView:
    get_source(session, user, request.source_id, Permission.MANAGE_TON_SOURCES)
    account_kinds = {
        MappingKind.ACCOUNT,
        MappingKind.BUDGET_ACCOUNT,
        MappingKind.BILLING_ACCOUNT,
        MappingKind.BILLING_TAX_ACCOUNT,
    }
    unit_kinds = {MappingKind.UNIT, MappingKind.ENTITY, MappingKind.BUDGET_UNIT}
    valid_target = (
        (
            request.kind in account_kinds
            and request.account_id is not None
            and request.unit_id is None
            and request.calendar_period is None
        )
        or (
            request.kind in unit_kinds
            and request.unit_id is not None
            and request.account_id is None
            and request.calendar_period is None
        )
        or (
            request.kind is MappingKind.BUDGET_PERIOD
            and request.calendar_period is not None
            and request.account_id is None
            and request.unit_id is None
            and request.calendar_period.day == 1
        )
    )
    if not valid_target or (
        request.effective_from is not None
        and request.effective_to is not None
        and request.effective_to < request.effective_from
    ):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid financial mapping")
    if (
        request.account_id is not None
        and session.get(FinancialAccount, request.account_id) is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Financial account not found")
    if (
        request.unit_id is not None
        and session.scalar(
            sa.select(BusinessUnit).where(
                BusinessUnit.id == request.unit_id,
                business_unit_visible_clause(user),
            )
        )
        is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Business unit not found")
    if request.source_snapshot_id is not None:
        snapshot = session.get(SourceSnapshot, request.source_snapshot_id)
        if snapshot is None or snapshot.source_id != request.source_id:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Mapping snapshot differs")
    if request.kind is MappingKind.BUDGET_PERIOD:
        assert request.calendar_period is not None
        try:
            execution_id = UUID(request.source_key)
        except ValueError:
            raise OnyxError(
                OnyxErrorCode.INVALID_INPUT, "Budget period key must be an execution ID"
            ) from None
        execution = get_execution(session, user, request.source_id, execution_id)
        if request.effective_from is not None:
            raise OnyxError(
                OnyxErrorCode.INVALID_INPUT, "Budget period start uses calendar_period"
            )
        if request.effective_to is not None:
            if (
                request.effective_to.day != 1
                or request.effective_to < request.calendar_period
            ):
                raise OnyxError(
                    OnyxErrorCode.INVALID_INPUT,
                    "Budget period range must use whole months",
                )
            bases = set(
                session.scalars(
                    sa.select(OperationalSourceRecord.period_basis)
                    .where(OperationalSourceRecord.execution_id == execution.id)
                    .distinct()
                )
            )
            if bases != {"MONTHLY_CONTRACT"}:
                raise OnyxError(
                    OnyxErrorCode.INVALID_INPUT,
                    "Only monthly contract budgets accept a month range",
                )
            terms = set(
                session.scalars(
                    sa.select(
                        OperationalSourceRecord.typed_values[
                            "contract_term_months"
                        ].astext
                    )
                    .where(OperationalSourceRecord.execution_id == execution.id)
                    .distinct()
                )
            )
            months = (
                (request.effective_to.year - request.calendar_period.year) * 12
                + request.effective_to.month
                - request.calendar_period.month
                + 1
            )
            term = next(iter(terms)) if len(terms) == 1 else None
            if term is None or not term.isdigit() or months > int(term):
                raise OnyxError(
                    OnyxErrorCode.INVALID_INPUT,
                    "Budget range exceeds source contract term",
                )
    # One advisory lock serializes revision numbers across concurrent writers.
    session.execute(sa.text("SELECT pg_advisory_xact_lock(4433004)"))
    revision = FinancialMappingRevision(
        number=_mapping_revision_number(session) + 1,
        created_by=user.id,
        reason=request.reason,
    )
    session.add(revision)
    session.flush()
    mapping = FinancialMapping(
        revision_id=revision.id,
        **request.model_dump(mode="python", exclude={"reason"}),
    )
    session.add(mapping)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_FINANCIAL_MAPPING_VERSION,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.FINANCIAL_MAPPING,
        resource_id=mapping.id,
    )
    return MappingView.model_validate(
        {
            **request.model_dump(),
            "id": mapping.id,
            "revision_id": revision.id,
            "revision_number": revision.number,
        }
    )


def list_mappings(
    session: Session, user: User, source_id: UUID, limit: int, offset: int
) -> list[MappingView]:
    get_source(session, user, source_id)
    check_page(limit, offset)
    rows = session.execute(
        sa.select(FinancialMapping, FinancialMappingRevision.number)
        .join(
            FinancialMappingRevision,
            FinancialMappingRevision.id == FinancialMapping.revision_id,
        )
        .where(FinancialMapping.source_id == source_id)
        .order_by(FinancialMappingRevision.number.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        MappingView.model_validate(
            {
                "id": mapping.id,
                "revision_id": mapping.revision_id,
                "source_id": mapping.source_id,
                "kind": mapping.kind,
                "source_key": mapping.source_key,
                "account_id": mapping.account_id,
                "unit_id": mapping.unit_id,
                "calendar_period": mapping.calendar_period,
                "source_snapshot_id": mapping.source_snapshot_id,
                "effective_from": mapping.effective_from,
                "effective_to": mapping.effective_to,
                "revision_number": number,
            }
        )
        for mapping, number in rows
    ]


class MappingIndex:
    def __init__(self, rows: Sequence[tuple[FinancialMapping, int]]) -> None:
        self.by_key: dict[tuple[UUID, str, str], list[FinancialMapping]] = defaultdict(
            list
        )
        for mapping, _number in rows:
            self.by_key[(mapping.source_id, mapping.kind, mapping.source_key)].append(
                mapping
            )

    def find(
        self,
        source_id: UUID,
        kind: MappingKind,
        key: str | None,
        date: datetime.date | None,
    ) -> FinancialMapping | None:
        if not key:
            return None
        for item in self.by_key.get((source_id, kind.value, key), ()):
            if date is None:
                if kind is MappingKind.BUDGET_PERIOD or (
                    item.effective_from is None and item.effective_to is None
                ):
                    return item
            elif (item.effective_from is None or item.effective_from <= date) and (
                item.effective_to is None or date <= item.effective_to
            ):
                return item
        return None


def _load_mappings(session: Session, number: int) -> MappingIndex:
    rows = session.execute(
        sa.select(FinancialMapping, FinancialMappingRevision.number)
        .join(
            FinancialMappingRevision,
            FinancialMappingRevision.id == FinancialMapping.revision_id,
        )
        .where(FinancialMappingRevision.number <= number)
        .order_by(FinancialMappingRevision.number.desc())
    ).all()
    return MappingIndex([(mapping, number) for mapping, number in rows])


def _validate_inputs(
    session: Session, user: User, request: NormalizationRequest, permission: Permission
) -> tuple[ReviewRun, ImportProfileExecution, list[ImportProfileExecution]]:
    get_source(session, user, request.ng_source_id, permission)
    review = get_review_run(session, user, request.ng_source_id, request.review_run_id)
    if review.status.value != "SUCCEEDED":
        raise OnyxError(OnyxErrorCode.CONFLICT, "Review run did not succeed")
    billing = get_execution(
        session,
        user,
        request.billing_source_id,
        request.billing_execution_id,
        permission,
    )
    billing_profile = session.get(ImportProfile, billing.profile_id)
    if (
        billing_profile is None
        or billing_profile.key != BILLING_KEY
        or billing.status
        not in (
            ProfileExecutionStatus.SUCCEEDED,
            ProfileExecutionStatus.PARTIAL,
        )
    ):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid billing execution")
    if request.effective_input_policy is InputPolicy.ACTUAL_ONLY and request.budgets:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "An actual-only normalization cannot read budget workbooks",
        )
    budgets: list[ImportProfileExecution] = []
    seen: set[UUID] = set()
    for item in request.budgets:
        if item.execution_id in seen:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Duplicate budget execution")
        seen.add(item.execution_id)
        execution = get_execution(
            session, user, item.source_id, item.execution_id, permission
        )
        profile = session.get(ImportProfile, execution.profile_id)
        if (
            profile is None
            or profile.key not in (BUDGET_ANNUAL_KEY, BUDGET_TERM_KEY)
            or execution.status != ProfileExecutionStatus.SUCCEEDED
        ):
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Invalid budget execution")
        budgets.append(execution)
    return review, billing, budgets


def _reconcile(
    actuals: list[dict[str, Any]],
    billings: list[dict[str, Any]],
    actual_documents: dict[UUID, str | None],
    billing_documents: dict[UUID, str],
    revenue_accounts: set[UUID],
    run_id: UUID,
) -> list[dict[str, Any]]:
    actual_keys: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    billing_keys: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    items: list[dict[str, Any]] = []
    for actual in actuals:
        if actual["account_id"] is None:
            items.append(
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "actual_fact_id": actual["id"],
                    "billing_fact_id": None,
                    "status": "UNMAPPED",
                    "evidence_key": None,
                }
            )
            continue
        if actual["account_id"] not in revenue_accounts:
            continue
        document = actual_documents[actual["id"]]
        if (
            actual["unit_id"] is None
            or not document
            or actual["movement_amount"] is None
        ):
            items.append(
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "actual_fact_id": actual["id"],
                    "billing_fact_id": None,
                    "status": "UNMAPPED",
                    "evidence_key": None,
                }
            )
            continue
        key = (
            actual["calendar_period"],
            actual["unit_id"],
            actual["account_id"],
            ng_invoice_key(document, actual["emission_date"]),
        )
        actual_keys[key].append(actual)
    for billing in billings:
        if billing["account_id"] is None:
            items.append(
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "actual_fact_id": None,
                    "billing_fact_id": billing["id"],
                    "status": "UNMAPPED",
                    "evidence_key": None,
                }
            )
            continue
        if billing["account_id"] not in revenue_accounts:
            continue
        # An invoice with no service amount carries no revenue to reconcile.
        if billing["service_amount"] == 0:
            continue
        if billing["unit_id"] is None:
            items.append(
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "actual_fact_id": None,
                    "billing_fact_id": billing["id"],
                    "status": "UNMAPPED",
                    "evidence_key": None,
                }
            )
            continue
        # NG books revenue on the invoice emission date, so both sides match
        # on the emission month. Competence is the service month and differs.
        key = (
            _period(billing["emission_date"]),
            billing["unit_id"],
            billing["account_id"],
            ng_invoice_key(billing_documents[billing["id"]], billing["emission_date"]),
        )
        billing_keys[key].append(billing)
    for key in actual_keys.keys() | billing_keys.keys():
        ng = actual_keys.get(key, [])
        invoices = billing_keys.get(key, [])
        status = (
            "MATCHED"
            if len(ng) == 1
            and len(invoices) == 1
            and ng[0]["movement_amount"] == invoices[0]["service_amount"]
            else "AMBIGUOUS"
            if ng and invoices
            else "NG_ONLY"
            if ng
            else "BILLING_ONLY"
        )
        evidence_key = _digest(key)
        if status == "MATCHED":
            items.append(
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "actual_fact_id": ng[0]["id"],
                    "billing_fact_id": invoices[0]["id"],
                    "status": status,
                    "evidence_key": evidence_key,
                }
            )
        else:
            items.extend(
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "actual_fact_id": actual["id"],
                    "billing_fact_id": None,
                    "status": status,
                    "evidence_key": evidence_key,
                }
                for actual in ng
            )
            items.extend(
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "actual_fact_id": None,
                    "billing_fact_id": billing["id"],
                    "status": status,
                    "evidence_key": evidence_key,
                }
                for billing in invoices
            )
    return items


ContentKey = tuple[UUID, str, int]


def _content_keys(
    session: Session,
    model: type[ParsedSourceRecord] | type[OperationalSourceRecord],
    record_ids: set[UUID],
) -> dict[UUID, ContentKey]:
    """Source, content fingerprint and duplicate ordinal of each record.

    The same row re-imported in a new execution gets a new id but the same key,
    so a decision taken on the earlier import still finds it.
    """
    keys: dict[UUID, ContentKey] = {}
    ordered = sorted(record_ids, key=str)
    for start in range(0, len(ordered), 1000):
        for row in session.execute(
            sa.select(
                model.id, model.source_id, model.fingerprint, model.duplicate_ordinal
            ).where(model.id.in_(ordered[start : start + 1000]))
        ):
            keys[row[0]] = (row[1], row[2], row[3])
    return keys


def _apply_reconciliation_decisions(
    session: Session,
    run: FinancialNormalizationRun,
    items: list[dict[str, Any]],
    actuals: list[dict[str, Any]],
    billings: list[dict[str, Any]],
) -> int:
    """Apply recorded decisions by record content. Returns how many carried over."""
    actual_sources = {item["id"]: item["parsed_record_id"] for item in actuals}
    billing_sources = {item["id"]: item["source_record_id"] for item in billings}
    decisions = list(
        session.scalars(
            sa.select(FinancialReconciliationDecision)
            .where(
                FinancialReconciliationDecision.number
                <= run.reconciliation_decision_number
            )
            .order_by(FinancialReconciliationDecision.number.desc())
        )
    )
    if not decisions:
        return 0
    used_actuals = {
        actual_sources[item["actual_fact_id"]]
        for item in items
        if item["actual_fact_id"] is not None
    }
    used_billings = {
        billing_sources[item["billing_fact_id"]]
        for item in items
        if item["billing_fact_id"] is not None
    }
    actual_keys = _content_keys(
        session,
        ParsedSourceRecord,
        used_actuals
        | {d.actual_source_record_id for d in decisions if d.actual_source_record_id},
    )
    billing_keys = _content_keys(
        session,
        OperationalSourceRecord,
        used_billings
        | {d.billing_source_record_id for d in decisions if d.billing_source_record_id},
    )
    by_content: dict[
        tuple[ContentKey | None, ContentKey | None], tuple[str, set[UUID | None]]
    ] = {}
    for decision in decisions:
        by_content.setdefault(
            (
                actual_keys.get(decision.actual_source_record_id)
                if decision.actual_source_record_id
                else None,
                billing_keys.get(decision.billing_source_record_id)
                if decision.billing_source_record_id
                else None,
            ),
            (
                decision.decision,
                {decision.actual_source_record_id, decision.billing_source_record_id},
            ),
        )
    carried = 0
    for item in items:
        actual_id = actual_sources.get(item["actual_fact_id"])
        billing_id = billing_sources.get(item["billing_fact_id"])
        decided = by_content.get(
            (
                actual_keys.get(actual_id) if actual_id else None,
                billing_keys.get(billing_id) if billing_id else None,
            )
        )
        if decided is None:
            continue
        item["status"] = decided[0]
        if not ({actual_id, billing_id} - {None}) <= decided[1]:
            carried += 1
    return carried


def _apply_treatment(
    rules: list[treatments.TreatmentRule],
    account_id: UUID | None,
    unit_id: UUID | None,
    period: datetime.date,
    counts: Counter[str],
) -> tuple[treatments.TreatmentRule | None, UUID | None, UUID | None]:
    """(treatment, account the fact lands on, account it came from if moved)."""
    treatment = treatments.find(rules, account_id, unit_id, period)
    if treatment is None:
        return None, account_id, None
    counts[f"treated_{treatment.effect.value.lower()}"] += 1
    if treatment.effect is TreatmentEffect.RECLASSIFY:
        return treatment, treatment.target_account_id, account_id
    return treatment, account_id, None


def _persist_projection(
    session: Session,
    run: FinancialNormalizationRun,
    review: ReviewRun,
    billing_execution_id: UUID,
    budget_execution_ids: list[UUID],
    mapping_number: int,
) -> dict[str, int]:
    mappings = _load_mappings(session, mapping_number)
    treatment_rules = treatments.in_force(rules_up_to(session, run.treatment_number))
    states, watermark = load_finding_states(session, review, run.dataset_as_of)
    if (
        dataset_revision(review_run_id=review.id, event_watermark=watermark)
        != run.dataset_revision
    ):
        raise OnyxError(OnyxErrorCode.CONFLICT, "Reviewed dataset revision changed")
    dispositions = record_dispositions(states)
    excluded = excluded_rows(states)
    ng_records = list(
        session.scalars(
            sa.select(ParsedSourceRecord)
            .where(ParsedSourceRecord.execution_id == review.execution_id)
            .order_by(ParsedSourceRecord.id)
        )
    )
    billing_records = list(
        session.scalars(
            sa.select(OperationalSourceRecord)
            .where(
                OperationalSourceRecord.execution_id == billing_execution_id,
                OperationalSourceRecord.kind == "BILLING",
            )
            .order_by(OperationalSourceRecord.id)
        )
    )
    budget_records = list(
        session.scalars(
            sa.select(OperationalSourceRecord)
            .where(
                OperationalSourceRecord.execution_id.in_(budget_execution_ids),
                OperationalSourceRecord.kind == "BUDGET",
            )
            .order_by(OperationalSourceRecord.id)
        )
    )
    actuals: list[dict[str, Any]] = []
    billings: list[dict[str, Any]] = []
    derived: list[dict[str, Any]] = []
    budgets: list[dict[str, Any]] = []
    actual_documents: dict[UUID, str | None] = {}
    billing_documents: dict[UUID, str] = {}
    counts: Counter[str] = Counter()
    counts["excluded_source_rows"] = sum(
        item.disposition.value == "EXCLUDED_SOURCE_ERROR" for item in excluded
    )
    for record in ng_records:
        item = dispositions.get(record.id)
        disposition = item.disposition.value if item else "ACCEPTED"
        if item is not None and item.disposition not in DOWNSTREAM_SAFE_DISPOSITIONS:
            # A copy confirmed as a document-format duplicate has one known
            # treatment, removal at source, so it leaves the dataset unblocked.
            if (
                item.disposition is ReviewDisposition.CORRECTION_REQUIRED
                and item.rule_keys == (DUPLICATE_DOCUMENT_RULE,)
            ):
                counts["excluded_confirmed_duplicates"] += 1
                continue
            counts["blocked_reviewed_records"] += 1
            continue
        account_map = mappings.find(
            record.source_id,
            MappingKind.ACCOUNT,
            record.account_code,
            record.emission_date,
        )
        unit_map = mappings.find(
            record.source_id,
            MappingKind.UNIT,
            record.administrative_unit or BLANK_UNIT_KEY,
            record.emission_date,
        )
        actual_id = uuid4()
        unit_id = unit_map.unit_id if unit_map else None
        treatment, account_id, original_account_id = _apply_treatment(
            treatment_rules,
            account_map.account_id if account_map else None,
            unit_id,
            _period(record.emission_date),
            counts,
        )
        actuals.append(
            {
                "id": actual_id,
                "run_id": run.id,
                "parsed_record_id": record.id,
                "account_id": account_id,
                "unit_id": unit_id,
                "account_mapping_id": account_map.id if account_map else None,
                "unit_mapping_id": unit_map.id if unit_map else None,
                "emission_date": record.emission_date,
                "calendar_period": _period(record.emission_date),
                "source_sheet_month": record.sheet_month,
                "movement_amount": record.movement_amount,
                "final_amount": record.final_amount,
                "disposition": disposition,
                "treatment_id": treatment.id if treatment else None,
                "treatment_effect": treatment.effect.value if treatment else None,
                "original_account_id": original_account_id,
            }
        )
        actual_documents[actual_id] = record.document_number
        counts["actual_unmapped_account"] += account_map is None
        counts["actual_unmapped_unit"] += unit_map is None
    for record in billing_records:
        if record.record_date is None or record.amount is None:
            raise OnyxError(OnyxErrorCode.CONFLICT, "Billing source contract changed")
        account_map = mappings.find(
            record.source_id, MappingKind.BILLING_ACCOUNT, "GROSS", record.competence
        )
        unit_map = mappings.find(
            record.source_id, MappingKind.ENTITY, record.description, record.competence
        )
        billing_id = uuid4()
        period = _period(record.competence) if record.competence else None
        billings.append(
            {
                "id": billing_id,
                "run_id": run.id,
                "source_record_id": record.id,
                "account_id": account_map.account_id if account_map else None,
                "unit_id": unit_map.unit_id if unit_map else None,
                "account_mapping_id": account_map.id if account_map else None,
                "unit_mapping_id": unit_map.id if unit_map else None,
                "emission_date": record.record_date,
                "competence_period": period,
                "service_amount": record.amount,
                "invoice_number": record.identifier,
                "payer_text": record.description,
                "ir_retained": _optional_decimal(
                    record.numeric_values.get("ir_retained")
                ),
                "iss_retained": _optional_decimal(
                    record.numeric_values.get("iss_retained")
                ),
                "inss_retained": _optional_decimal(
                    record.numeric_values.get("inss_retained")
                ),
                "total_retained": _optional_decimal(
                    record.numeric_values.get("total_retained")
                ),
                "invoice_net_amount": _optional_decimal(
                    record.numeric_values.get("invoice_net_amount")
                ),
                "net_after_discount": _optional_decimal(
                    record.numeric_values.get("net_after_discount")
                ),
            }
        )
        billing_documents[billing_id] = record.identifier
        counts["billing_unmapped_account"] += account_map is None
        counts["billing_unmapped_unit"] += unit_map is None
        counts["billing_competence_unresolved"] += period is None
        if period is None or unit_map is None or account_map is None:
            counts["unsupported_derivation"] += 1
            continue
        derived.append(
            {
                "id": uuid4(),
                "run_id": run.id,
                "billing_fact_id": billing_id,
                "rule_key": "BILLING_GROSS",
                "rule_version": 1,
                "origin": "BILLING_DERIVED",
                "account_id": account_map.account_id,
                "unit_id": unit_map.unit_id,
                "competence_period": period,
                "amount": record.amount,
            }
        )
        if _optional_decimal(record.numeric_values.get("ir_retained")) not in (
            None,
            Decimal(0),
        ):
            counts["unresolved_ir_retention"] += 1
        for field, key in TAX_COMPONENTS:
            raw = record.numeric_values.get(field)
            if raw is None:
                continue
            value = Decimal(raw)
            if value < 0:
                counts["unsupported_derivation"] += 1
                continue
            if value == 0:
                continue
            tax_map = mappings.find(
                record.source_id,
                MappingKind.BILLING_TAX_ACCOUNT,
                key,
                record.competence,
            )
            if tax_map is None or tax_map.account_id is None:
                counts["unsupported_derivation"] += 1
                continue
            derived.append(
                {
                    "id": uuid4(),
                    "run_id": run.id,
                    "billing_fact_id": billing_id,
                    "rule_key": f"BILLING_RETAINED_{key}",
                    "rule_version": 1,
                    "origin": "BILLING_DERIVED",
                    "account_id": tax_map.account_id,
                    "unit_id": unit_map.unit_id,
                    "competence_period": period,
                    "amount": -value,
                }
            )
    for record in budget_records:
        if record.amount is None or record.period_basis is None:
            raise OnyxError(OnyxErrorCode.CONFLICT, "Budget source contract changed")
        account_map = mappings.find(
            record.source_id, MappingKind.BUDGET_ACCOUNT, record.identifier, None
        )
        unit_map = mappings.find(
            record.source_id,
            MappingKind.BUDGET_UNIT,
            record.typed_values.get("contract_label"),
            None,
        )
        period_map = mappings.find(
            record.source_id, MappingKind.BUDGET_PERIOD, str(record.execution_id), None
        )
        periods: list[datetime.date | None] = [None]
        if period_map is not None and period_map.calendar_period is not None:
            start = period_map.calendar_period
            end = period_map.effective_to or start
            if end != start and record.period_basis != "MONTHLY_CONTRACT":
                raise OnyxError(
                    OnyxErrorCode.CONFLICT,
                    "Budget range does not match source period basis",
                )
            periods = [
                datetime.date(year, month, 1)
                for year in range(start.year, end.year + 1)
                for month in range(1, 13)
                if start <= datetime.date(year, month, 1) <= end
            ]
        budgets.extend(
            (
                {
                    "id": uuid4(),
                    "run_id": run.id,
                    "source_record_id": record.id,
                    "account_id": account_map.account_id if account_map else None,
                    "unit_id": unit_map.unit_id if unit_map else None,
                    "account_mapping_id": account_map.id if account_map else None,
                    "unit_mapping_id": unit_map.id if unit_map else None,
                    "period_mapping_id": period_map.id if period_map else None,
                    "period_basis": record.period_basis,
                    "calendar_period": period,
                    "amount": record.amount,
                }
                for period in periods
            )
        )
        counts["budget_unmapped_account"] += account_map is None
        counts["budget_unmapped_unit"] += unit_map is None
        counts["budget_period_unresolved"] += period_map is None
    revenue_accounts = set(
        session.scalars(
            sa.select(FinancialAccount.id).where(
                FinancialAccount.dre_classification == "REVENUE"
            )
        )
    )
    reconciliation = _reconcile(
        actuals, billings, actual_documents, billing_documents, revenue_accounts, run.id
    )
    counts["reconciliation_decisions_carried_over"] = _apply_reconciliation_decisions(
        session, run, reconciliation, actuals, billings
    )
    _insert_batches(session, FinancialActualFact, actuals)
    _insert_batches(session, FinancialBillingFact, billings)
    _insert_batches(session, FinancialDerivedFact, derived)
    _insert_batches(session, FinancialBudgetFact, budgets)
    _insert_batches(session, FinancialReconciliationItem, reconciliation)
    counts.update(
        {
            "eligible_ng_records": len(actuals),
            "canonical_actuals": len(actuals),
            "billing_facts": len(billings),
            "derived_facts": len(derived),
            "budget_facts": len(budgets),
            "reconciliation_items": len(reconciliation),
        }
    )
    for status, count in Counter(item["status"] for item in reconciliation).items():
        counts[f"reconciliation_{status.lower()}"] = count
    return dict(counts)


def normalize(
    session: Session,
    user: User,
    request: NormalizationRequest,
    dataset_revision_value: str,
    dataset_as_of: datetime.datetime,
) -> FinancialNormalizationRun:
    review, _billing, _budgets = _validate_inputs(
        session, user, request, Permission.IMPORT_TON_SOURCES
    )
    budget_ids = sorted((item.execution_id for item in request.budgets), key=str)
    mapping_number = _mapping_revision_number(session)
    basis_number = _basis_revision_number(session)
    reconciliation_number = int(
        session.scalar(sa.select(sa.func.max(FinancialReconciliationDecision.number)))
        or 0
    )
    treatments_number = treatment_number(session)
    input_digest = _digest(
        {
            "review_run_id": review.id,
            "dataset_revision": dataset_revision_value,
            "billing_execution_id": request.billing_execution_id,
            "budget_execution_ids": budget_ids,
            "mapping_revision_number": mapping_number,
            "amount_basis_revision_number": basis_number,
            "reconciliation_decision_number": reconciliation_number,
            "derivation_version": DERIVATION_VERSION,
            "authority_policy_version": AUTHORITY_POLICY_VERSION,
            "dataset_policy_version": DATASET_POLICY_VERSION,
            # Absent until the first treatment, so earlier digests stay valid.
            **({"treatment_number": treatments_number} if treatments_number else {}),
        }
    )
    existing = session.scalar(
        sa.select(FinancialNormalizationRun)
        .where(
            FinancialNormalizationRun.input_digest == input_digest,
            FinancialNormalizationRun.status == "SUCCEEDED",
        )
        .order_by(FinancialNormalizationRun.attempt_no.desc())
    )
    if existing is not None:
        return existing
    session.execute(sa.text("SELECT pg_advisory_xact_lock(4433005)"))
    existing = session.scalar(
        sa.select(FinancialNormalizationRun)
        .where(
            FinancialNormalizationRun.input_digest == input_digest,
            FinancialNormalizationRun.status.in_(("RUNNING", "SUCCEEDED")),
        )
        .order_by(FinancialNormalizationRun.attempt_no.desc())
    )
    if existing is not None:
        if existing.status == "SUCCEEDED":
            return existing
        raise OnyxError(OnyxErrorCode.CONFLICT, "Normalization is running")
    attempt_no = (
        int(
            session.scalar(
                sa.select(sa.func.max(FinancialNormalizationRun.attempt_no)).where(
                    FinancialNormalizationRun.input_digest == input_digest
                )
            )
            or 0
        )
        + 1
    )
    run = FinancialNormalizationRun(
        input_digest=input_digest,
        attempt_no=attempt_no,
        status="RUNNING",
        review_run_id=review.id,
        dataset_revision=dataset_revision_value,
        dataset_as_of=dataset_as_of,
        billing_execution_id=request.billing_execution_id,
        budget_execution_ids=[str(item) for item in budget_ids],
        input_policy=request.effective_input_policy.value,
        mapping_revision_number=mapping_number,
        amount_basis_revision_number=basis_number,
        reconciliation_decision_number=reconciliation_number,
        treatment_number=treatments_number,
        derivation_version=DERIVATION_VERSION,
        authority_policy_version=AUTHORITY_POLICY_VERSION,
        statistics={},
    )
    session.add(run)
    session.flush()
    previous = session.scalar(
        sa.select(FinancialNormalizationRun)
        .where(
            FinancialNormalizationRun.status == "SUCCEEDED",
            FinancialNormalizationRun.id != run.id,
        )
        .order_by(FinancialNormalizationRun.started_at.desc())
        .limit(1)
    )
    if (
        previous is None
        or previous.authority_policy_version != AUTHORITY_POLICY_VERSION
    ):
        emit_ton_audit_event(
            session,
            action=AuditAction.TON_FINANCIAL_AUTHORITY_VERSION,
            outcome=AuditOutcome.SUCCESS,
            actor_user_id=user.id,
            resource_kind=TonAuditResourceKind.FINANCIAL_NORMALIZATION_RUN,
            resource_id=run.id,
        )
    if previous is None or previous.derivation_version != DERIVATION_VERSION:
        emit_ton_audit_event(
            session,
            action=AuditAction.TON_FINANCIAL_DERIVATION_VERSION,
            outcome=AuditOutcome.SUCCESS,
            actor_user_id=user.id,
            resource_kind=TonAuditResourceKind.FINANCIAL_NORMALIZATION_RUN,
            resource_id=run.id,
        )
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_FINANCIAL_NORMALIZE_START,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.FINANCIAL_NORMALIZATION_RUN,
        resource_id=run.id,
    )
    session.commit()
    try:
        run.statistics = _persist_projection(
            session,
            run,
            review,
            request.billing_execution_id,
            budget_ids,
            mapping_number,
        )
        run.status = "SUCCEEDED"
        run.finished_at = datetime.datetime.now(datetime.UTC)
        emit_ton_audit_event(
            session,
            action=AuditAction.TON_FINANCIAL_NORMALIZE_SUCCEED,
            outcome=AuditOutcome.SUCCESS,
            actor_user_id=user.id,
            resource_kind=TonAuditResourceKind.FINANCIAL_NORMALIZATION_RUN,
            resource_id=run.id,
        )
        session.commit()
        return run
    except Exception:
        session.rollback()
        failed = session.get(FinancialNormalizationRun, run.id)
        assert failed is not None
        failed.status = "FAILED"
        failed.error_code = "NORMALIZATION_FAILED"
        failed.finished_at = datetime.datetime.now(datetime.UTC)
        emit_ton_audit_event(
            session,
            action=AuditAction.TON_FINANCIAL_NORMALIZE_FAIL,
            outcome=AuditOutcome.FAILURE,
            actor_user_id=user.id,
            resource_kind=TonAuditResourceKind.FINANCIAL_NORMALIZATION_RUN,
            resource_id=run.id,
        )
        session.commit()
        raise


def get_run(session: Session, user: User, run_id: UUID) -> FinancialNormalizationRun:
    run = session.get(FinancialNormalizationRun, run_id)
    if run is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Normalization run not found")
    # Read access to every input is required before any financial result is returned.
    review = session.get(ReviewRun, run.review_run_id)
    assert review is not None
    get_source(session, user, review.source_id)
    billing = session.get(ImportProfileExecution, run.billing_execution_id)
    assert billing is not None
    get_source(session, user, billing.source_id)
    for execution_id in run.budget_execution_ids:
        execution = session.get(ImportProfileExecution, UUID(execution_id))
        assert execution is not None
        get_source(session, user, execution.source_id)
    return run


def list_runs(
    session: Session, user: User, limit: int, offset: int
) -> list[FinancialNormalizationRun]:
    check_page(limit, offset)
    query = (
        sa.select(FinancialNormalizationRun)
        .where(FinancialNormalizationRun.status == "SUCCEEDED")
        .order_by(
            FinancialNormalizationRun.started_at.desc(), FinancialNormalizationRun.id
        )
    )
    if is_ton_administrator(user):
        return list(session.scalars(query.limit(limit).offset(offset)))
    result: list[FinancialNormalizationRun] = []
    position = 0
    visible = 0
    while len(result) < limit:
        candidates = list(session.scalars(query.limit(100).offset(position)))
        if not candidates:
            break
        position += len(candidates)
        for candidate in candidates:
            try:
                get_run(session, user, candidate.id)
            except OnyxError:
                continue
            if visible >= offset:
                result.append(candidate)
                if len(result) == limit:
                    break
            visible += 1
    return result


def normalization_request_for_run(
    session: Session, user: User, run_id: UUID
) -> NormalizationRequest:
    run = get_run(session, user, run_id)
    review = session.get(ReviewRun, run.review_run_id)
    billing = session.get(ImportProfileExecution, run.billing_execution_id)
    assert review is not None and billing is not None
    budgets: list[BudgetInput] = []
    for execution_id in run.budget_execution_ids:
        execution = session.get(ImportProfileExecution, UUID(execution_id))
        assert execution is not None
        budgets.append(
            BudgetInput(source_id=execution.source_id, execution_id=execution.id)
        )
    return NormalizationRequest(
        ng_source_id=review.source_id,
        review_run_id=review.id,
        billing_source_id=billing.source_id,
        billing_execution_id=billing.id,
        budgets=budgets,
        input_policy=(
            InputPolicy(run.input_policy)
            if run.input_policy in InputPolicy.__members__
            else None
        ),
    )


def list_reconciliation_items(
    session: Session,
    user: User,
    run_id: UUID,
    limit: int,
    offset: int,
    status: str | None = None,
) -> list[FinancialReconciliationItem]:
    run = get_run(session, user, run_id)
    if run.status != "SUCCEEDED":
        raise OnyxError(OnyxErrorCode.CONFLICT, "Normalization did not succeed")
    check_page(limit, offset)
    query = sa.select(FinancialReconciliationItem).where(
        FinancialReconciliationItem.run_id == run_id
    )
    if status is not None:
        query = query.where(FinancialReconciliationItem.status == status)
    return list(
        session.scalars(
            query.order_by(FinancialReconciliationItem.id).limit(limit).offset(offset)
        )
    )


def decide_reconciliation(
    session: Session,
    user: User,
    run_id: UUID,
    item_id: UUID,
    decision: str,
    reason: str,
) -> FinancialReconciliationDecision:
    run = get_run(session, user, run_id)
    if run.status != "SUCCEEDED":
        raise OnyxError(OnyxErrorCode.CONFLICT, "Normalization did not succeed")
    if (
        decision
        not in (
            "NG_AUTHORITATIVE",
            "SUPPLEMENTAL",
            "EXPECTED_DIFFERENCE",
            "NOT_SAME_EVENT",
        )
        or not reason.strip()
    ):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Decision and reason are required")
    item = session.scalar(
        sa.select(FinancialReconciliationItem).where(
            FinancialReconciliationItem.id == item_id,
            FinancialReconciliationItem.run_id == run_id,
        )
    )
    if item is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Reconciliation item not found")
    actual = (
        session.get(FinancialActualFact, item.actual_fact_id)
        if item.actual_fact_id
        else None
    )
    billing = (
        session.get(FinancialBillingFact, item.billing_fact_id)
        if item.billing_fact_id
        else None
    )
    if actual is not None:
        source_record = session.get(ParsedSourceRecord, actual.parsed_record_id)
        assert source_record is not None
        get_source(
            session, user, source_record.source_id, Permission.MANAGE_TON_SOURCES
        )
    if billing is not None:
        source_record = session.get(OperationalSourceRecord, billing.source_record_id)
        assert source_record is not None
        get_source(
            session, user, source_record.source_id, Permission.MANAGE_TON_SOURCES
        )
    if decision == "NG_AUTHORITATIVE" and (actual is None or billing is None):
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Authority requires paired evidence"
        )
    session.execute(sa.text("SELECT pg_advisory_xact_lock(4433008)"))
    number = (
        int(
            session.scalar(
                sa.select(sa.func.max(FinancialReconciliationDecision.number))
            )
            or 0
        )
        + 1
    )
    revision = FinancialReconciliationDecision(
        number=number,
        actual_source_record_id=actual.parsed_record_id if actual else None,
        billing_source_record_id=billing.source_record_id if billing else None,
        decision=decision,
        reason=reason.strip(),
        created_by=user.id,
    )
    session.add(revision)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_FINANCIAL_RECONCILIATION_DECISION,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.FINANCIAL_NORMALIZATION_RUN,
        resource_id=run_id,
        extra={"revision": revision.number},
    )
    return revision


def actual_amounts(
    fact: FinancialActualFact,
    basis_index: dict[UUID, str],
    accounts: dict[UUID, FinancialAccount],
) -> tuple[str | None, Decimal | None, Decimal | None]:
    """(basis, treated amount, source amount) of one actual fact.

    The basis follows the account the source booked, so a reclassified fact
    keeps the amount its NG account defines. An excluded fact counts as zero.
    """
    account_id = fact.original_account_id or fact.account_id
    account = accounts.get(account_id) if account_id else None
    basis = (
        basis_index.get(account.id, account.actual_amount_basis) if account else None
    )
    original = (
        fact.movement_amount
        if basis == "MOVEMENT"
        else fact.final_amount
        if basis == "FINAL"
        else None
    )
    if fact.treatment_effect == TreatmentEffect.EXCLUDE.value and original is not None:
        return basis, Decimal(0), original
    return basis, original, original


def _fact_view(
    *,
    fact_id: UUID,
    source_record: ParsedSourceRecord | OperationalSourceRecord,
    fact_type: str,
    account: FinancialAccount | None,
    unit: BusinessUnit | None,
    period: datetime.date | None,
    amount: Decimal | None,
    amount_basis: str,
    authority_role: str,
    treated: FinancialActualFact | None = None,
    original_amount: Decimal | None = None,
) -> FactView:
    return FactView(
        id=fact_id,
        source_record_id=source_record.id,
        source_id=source_record.source_id,
        source_snapshot_id=source_record.snapshot_id,
        source_execution_id=source_record.execution_id,
        fact_type=fact_type,
        account_id=account.id if account else None,
        account_classification=account.dre_classification if account else None,
        unit_id=unit.id if unit else None,
        unit_code=unit.code if unit else None,
        unit_kind=unit.kind.value if unit else None,
        period=period,
        amount=amount,
        amount_basis=amount_basis,
        authority_role=authority_role,
        treatment_id=treated.treatment_id if treated else None,
        treatment_effect=treated.treatment_effect if treated else None,
        original_amount=original_amount if treated else None,
        original_account_id=treated.original_account_id if treated else None,
    )


def list_facts(
    session: Session,
    user: User,
    run_id: UUID,
    fact_type: str,
    limit: int,
    offset: int,
    period: datetime.date | None = None,
    unit_id: UUID | None = None,
) -> list[FactView]:
    run = get_run(session, user, run_id)
    if run.status != "SUCCEEDED":
        raise OnyxError(OnyxErrorCode.CONFLICT, "Normalization did not succeed")
    check_page(limit, offset)
    return _fact_views(session, run, fact_type, period, unit_id, limit, offset)


def _fact_views(
    session: Session,
    run: FinancialNormalizationRun,
    fact_type: str,
    period: datetime.date | None,
    unit_id: UUID | None,
    limit: int | None,
    offset: int,
) -> list[FactView]:
    """Facts of an authorized, succeeded run; no limit loads the whole scope."""
    run_id = run.id
    model_by_type: dict[str, type[Any]] = {
        "ACTUAL": FinancialActualFact,
        "BILLING": FinancialBillingFact,
        "DERIVED": FinancialDerivedFact,
        "BUDGET": FinancialBudgetFact,
    }
    model = model_by_type.get(fact_type)
    if model is None:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Unknown financial fact type")
    query = sa.select(model).where(model.run_id == run_id)
    if period is not None:
        if period.day != 1:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Period must start on day one")
        period_column = (
            model.calendar_period
            if fact_type in ("ACTUAL", "BUDGET")
            else model.competence_period
        )
        query = query.where(period_column == period)
    if unit_id is not None:
        query = query.where(model.unit_id == unit_id)
    rows = list(session.scalars(query.order_by(model.id).limit(limit).offset(offset)))
    derived_billing = {}
    if fact_type == "DERIVED" and rows:
        derived_billing = {
            item.id: item.source_record_id
            for item in session.scalars(
                sa.select(FinancialBillingFact).where(
                    FinancialBillingFact.id.in_(item.billing_fact_id for item in rows)
                )
            )
        }
    accounts = {
        account.id: account
        for account in session.scalars(
            sa.select(FinancialAccount).where(
                FinancialAccount.id.in_(
                    {
                        account_id
                        for item in rows
                        for account_id in (
                            item.account_id,
                            getattr(item, "original_account_id", None),
                        )
                        if account_id is not None
                    }
                )
            )
        )
    }
    basis_index = _basis_index(session, run.amount_basis_revision_number)
    units = {
        unit.id: unit
        for unit in session.scalars(
            sa.select(BusinessUnit).where(
                BusinessUnit.id.in_(
                    item.unit_id for item in rows if item.unit_id is not None
                )
            )
        )
    }
    source_ids = (
        [item.parsed_record_id for item in rows]
        if fact_type == "ACTUAL"
        else [derived_billing[item.billing_fact_id] for item in rows]
        if fact_type == "DERIVED"
        else [item.source_record_id for item in rows]
    )
    source_model = (
        ParsedSourceRecord if fact_type == "ACTUAL" else OperationalSourceRecord
    )
    source_records: dict[UUID, ParsedSourceRecord | OperationalSourceRecord] = {
        record.id: record
        for record in session.scalars(
            sa.select(source_model).where(source_model.id.in_(source_ids))
        )
    }
    views: list[FactView] = []
    for item in rows:
        source_id = (
            item.parsed_record_id
            if fact_type == "ACTUAL"
            else derived_billing[item.billing_fact_id]
            if fact_type == "DERIVED"
            else item.source_record_id
        )
        source_record = source_records[source_id]
        account = accounts.get(item.account_id)
        unit = units.get(item.unit_id)
        if fact_type == "ACTUAL":
            basis, amount, original = actual_amounts(item, basis_index, accounts)
            views.append(
                _fact_view(
                    fact_id=item.id,
                    source_record=source_record,
                    fact_type=fact_type,
                    account=account,
                    unit=unit,
                    period=item.calendar_period,
                    amount=amount,
                    amount_basis=basis or "UNRESOLVED",
                    authority_role="AUTHORITATIVE_ACTUAL",
                    treated=item if item.treatment_id else None,
                    original_amount=original,
                )
            )
        elif fact_type == "BILLING":
            views.append(
                _fact_view(
                    fact_id=item.id,
                    source_record=source_record,
                    fact_type=fact_type,
                    account=account,
                    unit=unit,
                    period=item.competence_period,
                    amount=item.service_amount,
                    amount_basis="SOURCE_SERVICE_VALUE",
                    authority_role="SOURCE_EVIDENCE",
                )
            )
        elif fact_type == "DERIVED":
            views.append(
                _fact_view(
                    fact_id=item.id,
                    source_record=source_record,
                    fact_type=fact_type,
                    account=account,
                    unit=unit,
                    period=item.competence_period,
                    amount=item.amount,
                    amount_basis=item.rule_key,
                    authority_role="SUPPLEMENTAL_NOT_ADDITIVE",
                )
            )
        else:
            views.append(
                _fact_view(
                    fact_id=item.id,
                    source_record=source_record,
                    fact_type=fact_type,
                    account=account,
                    unit=unit,
                    period=item.calendar_period,
                    amount=item.amount,
                    amount_basis=item.period_basis,
                    authority_role="BUDGET",
                )
            )
    return views


def readiness(
    session: Session,
    user: User,
    run_id: UUID,
    period: datetime.date,
    unit_id: UUID | None,
) -> ReadinessView:
    run = get_run(session, user, run_id)
    if run.status != "SUCCEEDED":
        raise OnyxError(OnyxErrorCode.CONFLICT, "Normalization did not succeed")
    if period.day != 1:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Period must start on day one")
    actual_query = sa.select(FinancialActualFact).where(
        FinancialActualFact.run_id == run_id,
        FinancialActualFact.calendar_period == period,
    )
    billing_query = sa.select(FinancialBillingFact).where(
        FinancialBillingFact.run_id == run_id,
        FinancialBillingFact.competence_period == period,
    )
    derived_query = sa.select(FinancialDerivedFact).where(
        FinancialDerivedFact.run_id == run_id,
        FinancialDerivedFact.competence_period == period,
    )
    budget_query = sa.select(FinancialBudgetFact).where(
        FinancialBudgetFact.run_id == run_id,
        FinancialBudgetFact.calendar_period == period,
    )
    if unit_id is not None:
        actual_query = actual_query.where(FinancialActualFact.unit_id == unit_id)
        billing_query = billing_query.where(FinancialBillingFact.unit_id == unit_id)
        derived_query = derived_query.where(FinancialDerivedFact.unit_id == unit_id)
        budget_query = budget_query.where(FinancialBudgetFact.unit_id == unit_id)
    actuals = list(session.scalars(actual_query))
    billings = list(session.scalars(billing_query))
    derived = list(session.scalars(derived_query))
    budgets = list(session.scalars(budget_query))
    budget_keys = {
        (item.account_id, item.unit_id)
        for item in budgets
        if item.account_id is not None and item.unit_id is not None
    }
    account_ids = {
        item.account_id
        for item in [*actuals, *budgets, *derived]
        if item.account_id is not None
    }
    accounts = {
        account.id: account
        for account in session.scalars(
            sa.select(FinancialAccount).where(FinancialAccount.id.in_(account_ids))
        )
    }
    basis_index = _basis_index(session, run.amount_basis_revision_number)
    aligned = sum(
        (item.account_id, item.unit_id) in budget_keys
        for item in actuals
        if item.account_id is not None and item.unit_id is not None
    )
    blockers: Counter[str] = Counter()
    blockers["UNMAPPED_ACCOUNT"] = sum(item.account_id is None for item in actuals)
    blockers["UNMAPPED_UNIT"] = sum(item.unit_id is None for item in actuals)
    blockers["UNCLASSIFIED_ACCOUNT"] = sum(
        account.dre_classification is None for account in accounts.values()
    )
    blockers["BUDGET_UNMAPPED_ACCOUNT"] = run.statistics.get(
        "budget_unmapped_account", 0
    )
    blockers["BUDGET_UNMAPPED_UNIT"] = run.statistics.get("budget_unmapped_unit", 0)
    blockers["BUDGET_PERIOD_UNRESOLVED"] = run.statistics.get(
        "budget_period_unresolved", 0
    )
    blockers["REVIEW_UNRESOLVED"] = run.statistics.get("blocked_reviewed_records", 0)
    blockers["EXCLUDED_SOURCE_ROWS"] = run.statistics.get("excluded_source_rows", 0)
    blockers["BILLING_COMPETENCE_UNRESOLVED"] = run.statistics.get(
        "billing_competence_unresolved", 0
    )
    blockers["UNSUPPORTED_DERIVATION"] = run.statistics.get("unsupported_derivation", 0)
    blockers["IR_RETENTION_UNRESOLVED"] = run.statistics.get(
        "unresolved_ir_retention", 0
    )
    blockers["ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED"] = sum(
        item.account_id is None
        or basis_index.get(
            item.account_id, accounts[item.account_id].actual_amount_basis
        )
        is None
        or (
            basis_index.get(
                item.account_id, accounts[item.account_id].actual_amount_basis
            )
            == "MOVEMENT"
            and item.movement_amount is None
        )
        or (
            basis_index.get(
                item.account_id, accounts[item.account_id].actual_amount_basis
            )
            == "FINAL"
            and item.final_amount is None
        )
        for item in actuals
    )
    # Budget coverage is only evaluated when the run has budget inputs. A run
    # without budgets is an Actual-only scope, not a gap in every record.
    if run.budget_execution_ids:
        blockers["MISSING_BUDGET"] = sum(
            (item.account_id, item.unit_id) not in budget_keys
            for item in actuals
            if item.account_id is not None and item.unit_id is not None
        )
    # Reconciliation items count in the period of the facts they concern. Both
    # sides use the emission month, the same key the reconciliation uses.
    next_period = (period + datetime.timedelta(days=32)).replace(day=1)
    in_scope_actuals = sa.select(FinancialActualFact.id).where(
        FinancialActualFact.run_id == run_id,
        FinancialActualFact.calendar_period == period,
    )
    in_scope_billings = sa.select(FinancialBillingFact.id).where(
        FinancialBillingFact.run_id == run_id,
        FinancialBillingFact.emission_date >= period,
        FinancialBillingFact.emission_date < next_period,
    )
    if unit_id is not None:
        in_scope_actuals = in_scope_actuals.where(
            FinancialActualFact.unit_id == unit_id
        )
        in_scope_billings = in_scope_billings.where(
            FinancialBillingFact.unit_id == unit_id
        )
    reconciliation_rows = session.execute(
        sa.select(FinancialReconciliationItem.status, sa.func.count())
        .where(
            FinancialReconciliationItem.run_id == run_id,
            sa.or_(
                FinancialReconciliationItem.actual_fact_id.in_(in_scope_actuals),
                FinancialReconciliationItem.billing_fact_id.in_(in_scope_billings),
            ),
        )
        .group_by(FinancialReconciliationItem.status)
    ).all()
    reconciliation = {status: int(count) for status, count in reconciliation_rows}
    blockers["SOURCE_RECONCILIATION_AMBIGUOUS"] = reconciliation.get("AMBIGUOUS", 0)
    blockers["SOURCE_RECONCILIATION_UNRESOLVED"] = reconciliation.get(
        "BILLING_ONLY", 0
    ) + reconciliation.get("UNMAPPED", 0)
    if not actuals:
        blockers["NO_ACTUAL"] = 1
    return ReadinessView(
        run_id=run_id,
        period=period,
        unit_id=unit_id,
        ready=not any(blockers.values()),
        blockers={key: value for key, value in blockers.items() if value},
        actual_count=len(actuals),
        billing_count=len(billings),
        derived_count=len(derived),
        budget_count=len(budgets),
        actual_budget_aligned_count=aligned,
        reconciliation=reconciliation,
        authority_policy_version=run.authority_policy_version,
        dataset_revision=run.dataset_revision,
        mapping_revision_number=run.mapping_revision_number,
        derivation_version=run.derivation_version,
    )


_DATASET_CACHE = "ton_dre_input_datasets"


@event.listens_for(Session, "after_flush")
@event.listens_for(Session, "after_commit")
@event.listens_for(Session, "after_rollback")
def _forget_datasets(session: Session, *_: object) -> None:
    session.info.pop(_DATASET_CACHE, None)


def load_dre_input_dataset(
    session: Session,
    user: User,
    run_id: UUID,
    period: datetime.date,
    unit_id: UUID | None,
) -> DreInputDataset:
    """Read one canonical period through the existing fact and readiness services.

    A year-to-date DRE reads every earlier month, and readiness overviews do
    that for each month of the year, so datasets are cached until the session
    writes or ends its transaction (accounts and mappings can change then).
    """
    cache: dict[tuple[UUID, UUID, datetime.date, UUID | None], DreInputDataset] = (
        session.info.setdefault(_DATASET_CACHE, {})
    )
    key = (user.id, run_id, period, unit_id)
    cached = cache.get(key)
    if cached is not None:
        return cached
    view = readiness(session, user, run_id, period, unit_id)
    run = get_run(session, user, run_id)
    dataset = DreInputDataset(
        readiness=view,
        actuals=_fact_views(session, run, "ACTUAL", period, unit_id, None, 0),
        budgets=_fact_views(session, run, "BUDGET", period, unit_id, None, 0),
    )
    cache[key] = dataset
    return dataset
