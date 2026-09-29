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
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton.acl import business_unit_visible_clause, is_ton_administrator
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.financial_review import get_review_run, load_finding_states
from onyx.db.ton.import_profiles import get_execution
from onyx.db.ton.models import (
    BusinessUnit,
    FinancialAccount,
    FinancialActualFact,
    FinancialBillingFact,
    FinancialBudgetFact,
    FinancialDerivedFact,
    FinancialMapping,
    FinancialMappingRevision,
    FinancialNormalizationRun,
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
from onyx.ton.financial_domain.models import (
    AccountCreate,
    FactView,
    MappingCreate,
    MappingKind,
    MappingView,
    NormalizationRequest,
    ReadinessView,
)
from onyx.ton.financial_review.catalog import DATASET_POLICY_VERSION
from onyx.ton.financial_review.dataset import (
    dataset_revision,
    excluded_rows,
    record_dispositions,
)
from onyx.ton.financial_review.models import DOWNSTREAM_SAFE_DISPOSITIONS
from onyx.ton.ng_financial.models import ProfileExecutionStatus
from onyx.ton.operational_import.parser import (
    BILLING_KEY,
    BUDGET_ANNUAL_KEY,
    BUDGET_TERM_KEY,
)
from onyx.utils.audit import AuditAction, AuditOutcome

BATCH_SIZE = 500
DERIVATION_VERSION = "billing-vba-proven-1"
AUTHORITY_POLICY_VERSION = "ng-actual-billing-diagnostic-1"
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
    session: Session, user: User, limit: int, offset: int
) -> list[FinancialAccount]:
    if not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "Financial accounts require admin access"
        )
    check_page(limit, offset)
    return list(
        session.scalars(
            sa.select(FinancialAccount)
            .order_by(FinancialAccount.code, FinancialAccount.id)
            .limit(limit)
            .offset(offset)
        )
    )


def _mapping_revision_number(session: Session) -> int:
    return int(
        session.scalar(sa.select(sa.func.max(FinancialMappingRevision.number))) or 0
    )


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
        try:
            execution_id = UUID(request.source_key)
        except ValueError:
            raise OnyxError(
                OnyxErrorCode.INVALID_INPUT, "Budget period key must be an execution ID"
            ) from None
        get_execution(session, user, request.source_id, execution_id)
    # One advisory lock serializes revision numbers across concurrent writers.
    session.execute(sa.text("SELECT pg_advisory_xact_lock(4433004)"))
    revision = FinancialMappingRevision(
        number=_mapping_revision_number(session) + 1, created_by=user.id
    )
    session.add(revision)
    session.flush()
    mapping = FinancialMapping(
        revision_id=revision.id,
        **request.model_dump(mode="python"),
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
                if item.effective_from is None and item.effective_to is None:
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
            document.strip(),
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
        if billing["unit_id"] is None or billing["competence_period"] is None:
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
        key = (
            billing["competence_period"],
            billing["unit_id"],
            billing["account_id"],
            billing_documents[billing["id"]].strip(),
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


def _persist_projection(
    session: Session,
    run: FinancialNormalizationRun,
    review: ReviewRun,
    billing_execution_id: UUID,
    budget_execution_ids: list[UUID],
    mapping_number: int,
) -> dict[str, int]:
    mappings = _load_mappings(session, mapping_number)
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
            record.administrative_unit,
            record.emission_date,
        )
        actual_id = uuid4()
        actuals.append(
            {
                "id": actual_id,
                "run_id": run.id,
                "parsed_record_id": record.id,
                "account_id": account_map.account_id if account_map else None,
                "unit_id": unit_map.unit_id if unit_map else None,
                "account_mapping_id": account_map.id if account_map else None,
                "unit_mapping_id": unit_map.id if unit_map else None,
                "emission_date": record.emission_date,
                "calendar_period": _period(record.emission_date),
                "source_sheet_month": record.sheet_month,
                "movement_amount": record.movement_amount,
                "final_amount": record.final_amount,
                "disposition": disposition,
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
        budgets.append(
            {
                "id": uuid4(),
                "run_id": run.id,
                "source_record_id": record.id,
                "account_id": account_map.account_id if account_map else None,
                "unit_id": unit_map.unit_id if unit_map else None,
                "account_mapping_id": account_map.id if account_map else None,
                "unit_mapping_id": unit_map.id if unit_map else None,
                "period_basis": record.period_basis,
                "calendar_period": period_map.calendar_period if period_map else None,
                "amount": record.amount,
            }
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
    input_digest = _digest(
        {
            "review_run_id": review.id,
            "dataset_revision": dataset_revision_value,
            "billing_execution_id": request.billing_execution_id,
            "budget_execution_ids": budget_ids,
            "mapping_revision_number": mapping_number,
            "derivation_version": DERIVATION_VERSION,
            "authority_policy_version": AUTHORITY_POLICY_VERSION,
            "dataset_policy_version": DATASET_POLICY_VERSION,
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
        mapping_revision_number=mapping_number,
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
                    item.account_id for item in rows if item.account_id is not None
                )
            )
        )
    }
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
            basis = account.actual_amount_basis if account else None
            views.append(
                _fact_view(
                    fact_id=item.id,
                    source_record=source_record,
                    fact_type=fact_type,
                    account=account,
                    unit=unit,
                    period=item.calendar_period,
                    amount=(
                        item.movement_amount
                        if basis == "MOVEMENT"
                        else item.final_amount
                        if basis == "FINAL"
                        else None
                    ),
                    amount_basis=basis or "UNRESOLVED",
                    authority_role="AUTHORITATIVE_ACTUAL",
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
        or accounts[item.account_id].actual_amount_basis is None
        or (
            accounts[item.account_id].actual_amount_basis == "MOVEMENT"
            and item.movement_amount is None
        )
        or (
            accounts[item.account_id].actual_amount_basis == "FINAL"
            and item.final_amount is None
        )
        for item in actuals
    )
    blockers["MISSING_BUDGET"] = sum(
        (item.account_id, item.unit_id) not in budget_keys
        for item in actuals
        if item.account_id is not None and item.unit_id is not None
    )
    reconciliation_rows = session.execute(
        sa.select(FinancialReconciliationItem.status, sa.func.count())
        .where(FinancialReconciliationItem.run_id == run_id)
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
