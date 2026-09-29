"""DATA-004C/D synthetic source-to-canonical persistence."""

import datetime
from io import BytesIO
from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import financial_domain, operational_import, sources
from onyx.db.ton.enums import BusinessUnitKind
from onyx.db.ton.models import (
    BusinessUnit,
    FinancialActualFact,
    FinancialBillingFact,
    FinancialBudgetFact,
    FinancialDerivedFact,
    FinancialMapping,
    FinancialNormalizationRun,
    OperationalSourceRecord,
    ParsedSourceRecord,
    TonAuditEvent,
)
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.financial_domain.models import (
    AccountCreate,
    BudgetInput,
    MappingCreate,
    MappingKind,
    NormalizationRequest,
)
from onyx.ton.financial_review.service import dataset_summary
from onyx.ton.operational_import.parser import BILLING_KEY, BUDGET_ANNUAL_KEY
from onyx.ton.operational_import.service import execute_operational_profile
from onyx.ton.sources.models import SourceCreate, SourceFormat
from onyx.ton.sources.service import import_file
from onyx.ton.sources.validation import MEDIA_TYPES
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.test_financial_review import (
    Pipeline,
    book,
    launch,
)
from tests.unit.ton.test_operational_import_parser import (
    billing_book,
    budget_book,
    invoice,
)


@pytest.fixture
def admin(ton_session: Session) -> User:
    user = factories.make_user(ton_session)
    group = factories.make_group(ton_session)
    factories.grant_permissions(
        ton_session, group=group, permissions=[Permission.FULL_ADMIN_PANEL_ACCESS]
    )
    factories.add_member(ton_session, group=group, user=user)
    ton_session.commit()
    return user


@pytest.fixture
def store() -> Mock:
    blobs: dict[str, bytes] = {}
    result = Mock(spec=FileStore)

    def save(content: BytesIO, *, file_id: str, **_kwargs: object) -> str:
        blobs[file_id] = content.read()
        return file_id

    result.save_file.side_effect = save
    result.read_file.side_effect = lambda key: BytesIO(blobs[key])
    result.delete_file.side_effect = lambda key, **_kwargs: blobs.pop(key, None)
    return result


def _operational_execution(
    session: Session,
    user: User,
    store: FileStore,
    *,
    key: str,
    content: bytes,
    format: SourceFormat,
    profile_key: str,
) -> tuple[UUID, UUID]:
    source = sources.create_source(
        session,
        user,
        SourceCreate(
            key=key,
            display_name="Synthetic source",
            acquisition_type="FILE_UPLOAD",
            status="ACTIVE",
        ),
    )
    session.commit()
    snapshot = import_file(
        session,
        user,
        source.id,
        BytesIO(content),
        f"synthetic.{format.value.lower()}",
        MEDIA_TYPES[format],
        store,
    )
    profile = operational_import.create_operational_profile(
        session, user, source.id, profile_key
    )
    session.commit()
    execution = execute_operational_profile(
        session, user, source.id, snapshot.id, profile.id, store
    )
    return source.id, execution.id


def _map(
    session: Session,
    user: User,
    source_id: UUID,
    kind: MappingKind,
    key: str,
    *,
    account_id: UUID | None = None,
    unit_id: UUID | None = None,
    calendar_period: datetime.date | None = None,
) -> None:
    financial_domain.create_mapping(
        session,
        user,
        MappingCreate(
            source_id=source_id,
            kind=kind,
            source_key=key,
            account_id=account_id,
            unit_id=unit_id,
            calendar_period=calendar_period,
        ),
    )
    session.commit()


def test_complete_synthetic_scope_is_dre_ready(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    day = datetime.date(2026, 1, 10)
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(
        book([launch("1.1 - Synthetic account", day, document="101", movement=100.25)])
    )
    review = pipeline.review(execution_id)
    reviewed = dataset_summary(ton_session, admin, pipeline.source_id, review.id)
    billing_source_id, billing_execution_id = _operational_execution(
        ton_session,
        admin,
        store,
        key="billing_invoices",
        content=billing_book([invoice(gross=100.25)]),
        format=SourceFormat.XLS,
        profile_key=BILLING_KEY,
    )
    budget_source_id, budget_execution_id = _operational_execution(
        ton_session,
        admin,
        store,
        key="budget",
        content=budget_book(),
        format=SourceFormat.XLSX,
        profile_key=BUDGET_ANNUAL_KEY,
    )
    account = financial_domain.create_account(
        ton_session,
        admin,
        AccountCreate(
            code="SYN-READY",
            label="Synthetic revenue",
            dre_classification="REVENUE",
            actual_amount_basis="MOVEMENT",
        ),
    )
    unit = BusinessUnit(
        code="SYN-READY-UNIT",
        name="Synthetic unit",
        kind=BusinessUnitKind.OPERATIONAL,
    )
    ton_session.add(unit)
    ton_session.commit()
    ng_record = ton_session.scalar(
        select(ParsedSourceRecord).where(
            ParsedSourceRecord.execution_id == execution_id
        )
    )
    billing_record = ton_session.scalar(
        select(OperationalSourceRecord).where(
            OperationalSourceRecord.execution_id == billing_execution_id
        )
    )
    budget_records = list(
        ton_session.scalars(
            select(OperationalSourceRecord).where(
                OperationalSourceRecord.execution_id == budget_execution_id
            )
        )
    )
    assert ng_record is not None and billing_record is not None
    assert ng_record.administrative_unit is not None
    assert billing_record.description is not None
    _map(
        ton_session,
        admin,
        pipeline.source_id,
        MappingKind.ACCOUNT,
        ng_record.account_code,
        account_id=account.id,
    )
    _map(
        ton_session,
        admin,
        pipeline.source_id,
        MappingKind.UNIT,
        ng_record.administrative_unit,
        unit_id=unit.id,
    )
    _map(
        ton_session,
        admin,
        billing_source_id,
        MappingKind.BILLING_ACCOUNT,
        "GROSS",
        account_id=account.id,
    )
    _map(
        ton_session,
        admin,
        billing_source_id,
        MappingKind.ENTITY,
        billing_record.description,
        unit_id=unit.id,
    )
    for record in budget_records:
        _map(
            ton_session,
            admin,
            budget_source_id,
            MappingKind.BUDGET_ACCOUNT,
            record.identifier,
            account_id=account.id,
        )
    assert budget_records
    contract_label = budget_records[0].typed_values["contract_label"]
    assert contract_label is not None
    _map(
        ton_session,
        admin,
        budget_source_id,
        MappingKind.BUDGET_UNIT,
        contract_label,
        unit_id=unit.id,
    )
    _map(
        ton_session,
        admin,
        budget_source_id,
        MappingKind.BUDGET_PERIOD,
        str(budget_execution_id),
        calendar_period=datetime.date(2026, 1, 1),
    )
    run = financial_domain.normalize(
        ton_session,
        admin,
        NormalizationRequest(
            ng_source_id=pipeline.source_id,
            review_run_id=review.id,
            billing_source_id=billing_source_id,
            billing_execution_id=billing_execution_id,
            budgets=[
                BudgetInput(
                    source_id=budget_source_id, execution_id=budget_execution_id
                )
            ],
        ),
        reviewed.dataset_revision,
        reviewed.as_of,
    )
    result = financial_domain.readiness(
        ton_session, admin, run.id, datetime.date(2026, 1, 1), unit.id
    )
    assert result.ready
    assert result.blockers == {}
    assert result.actual_budget_aligned_count == 1
    actual_page = financial_domain.list_facts(
        ton_session,
        admin,
        run.id,
        "ACTUAL",
        10,
        0,
        datetime.date(2026, 1, 1),
        unit.id,
    )
    assert actual_page[0].amount == 100.25
    assert actual_page[0].amount_basis == "MOVEMENT"
    assert actual_page[0].account_classification == "REVENUE"
    assert actual_page[0].unit_code == unit.code
    assert actual_page[0].source_execution_id == execution_id


def test_canonical_lineage_mapping_reconciliation_and_revisions(
    ton_session: Session,
    admin: User,
    store: FileStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    day = datetime.date(2026, 1, 10)
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(
        book(
            [
                launch("1.1 - Synthetic account", day, document="101", movement=100.25),
                launch(None, day, unit=None, document="102", movement=20),
                launch(None, day, document="103", interest="invalid"),
            ]
        )
    )
    review = pipeline.review(execution_id)
    reviewed = dataset_summary(ton_session, admin, pipeline.source_id, review.id)
    assert reviewed.downstream_safe_records == 1
    assert reviewed.excluded_source_rows == 1
    billing_source_id, billing_execution_id = _operational_execution(
        ton_session,
        admin,
        store,
        key="billing_invoices",
        content=billing_book([invoice(gross=100.25, retained=2)]),
        format=SourceFormat.XLS,
        profile_key=BILLING_KEY,
    )
    budget_source_id, budget_execution_id = _operational_execution(
        ton_session,
        admin,
        store,
        key="budget",
        content=budget_book(),
        format=SourceFormat.XLSX,
        profile_key=BUDGET_ANNUAL_KEY,
    )
    account = financial_domain.create_account(
        ton_session,
        admin,
        AccountCreate(
            code="SYN-REV", label="Synthetic revenue", dre_classification="REVENUE"
        ),
    )
    tax_account = financial_domain.create_account(
        ton_session,
        admin,
        AccountCreate(code="SYN-TAX", label="Synthetic retention"),
    )
    unit = BusinessUnit(
        code="SYN-UNIT", name="Synthetic unit", kind=BusinessUnitKind.OPERATIONAL
    )
    ton_session.add(unit)
    ton_session.commit()
    ng_record = ton_session.scalar(
        select(ParsedSourceRecord)
        .where(ParsedSourceRecord.execution_id == execution_id)
        .order_by(ParsedSourceRecord.source_row_number)
    )
    billing_record = ton_session.scalar(
        select(OperationalSourceRecord).where(
            OperationalSourceRecord.execution_id == billing_execution_id
        )
    )
    budget_record = ton_session.scalar(
        select(OperationalSourceRecord).where(
            OperationalSourceRecord.execution_id == budget_execution_id
        )
    )
    assert (
        ng_record is not None
        and billing_record is not None
        and budget_record is not None
    )
    _map(
        ton_session,
        admin,
        pipeline.source_id,
        MappingKind.ACCOUNT,
        ng_record.account_code,
        account_id=account.id,
    )
    assert ng_record.administrative_unit is not None
    _map(
        ton_session,
        admin,
        pipeline.source_id,
        MappingKind.UNIT,
        ng_record.administrative_unit,
        unit_id=unit.id,
    )
    _map(
        ton_session,
        admin,
        billing_source_id,
        MappingKind.BILLING_ACCOUNT,
        "GROSS",
        account_id=account.id,
    )
    assert billing_record.description is not None
    _map(
        ton_session,
        admin,
        billing_source_id,
        MappingKind.ENTITY,
        billing_record.description,
        unit_id=unit.id,
    )
    _map(
        ton_session,
        admin,
        billing_source_id,
        MappingKind.BILLING_TAX_ACCOUNT,
        "ISS",
        account_id=tax_account.id,
    )
    _map(
        ton_session,
        admin,
        budget_source_id,
        MappingKind.BUDGET_ACCOUNT,
        budget_record.identifier,
        account_id=account.id,
    )
    contract_label = budget_record.typed_values["contract_label"]
    assert contract_label is not None
    _map(
        ton_session,
        admin,
        budget_source_id,
        MappingKind.BUDGET_UNIT,
        contract_label,
        unit_id=unit.id,
    )
    request = NormalizationRequest(
        ng_source_id=pipeline.source_id,
        review_run_id=review.id,
        billing_source_id=billing_source_id,
        billing_execution_id=billing_execution_id,
        budgets=[
            BudgetInput(source_id=budget_source_id, execution_id=budget_execution_id)
        ],
    )
    first = financial_domain.normalize(
        ton_session, admin, request, reviewed.dataset_revision, reviewed.as_of
    )
    assert first.status == "SUCCEEDED"
    assert first.statistics["canonical_actuals"] == 1
    assert first.statistics["blocked_reviewed_records"] == 1
    assert first.statistics["excluded_source_rows"] == 1
    assert first.statistics["billing_facts"] == 1
    assert first.statistics["derived_facts"] == 2
    assert first.statistics["budget_facts"] == 2
    assert first.statistics["budget_period_unresolved"] == 2
    assert first.statistics["reconciliation_matched"] == 1
    audit_events = list(
        ton_session.scalars(
            select(TonAuditEvent).where(TonAuditEvent.action.like("ton_financial.%"))
        )
    )
    assert audit_events
    assert all(
        event.before_state is None and event.after_state is None and event.extra == {}
        for event in audit_events
    )
    matched = financial_domain.list_reconciliation_items(
        ton_session, admin, first.id, 10, 0, "MATCHED"
    )
    assert len(matched) == 1
    assert matched[0].actual_fact_id is not None
    assert matched[0].billing_fact_id is not None
    assert (
        financial_domain.normalize(
            ton_session, admin, request, reviewed.dataset_revision, reviewed.as_of
        ).id
        == first.id
    )
    actual = ton_session.scalar(
        select(FinancialActualFact).where(FinancialActualFact.run_id == first.id)
    )
    billing = ton_session.scalar(
        select(FinancialBillingFact).where(FinancialBillingFact.run_id == first.id)
    )
    assert actual is not None and billing is not None
    assert actual.parsed_record_id == ng_record.id
    assert billing.source_record_id == billing_record.id
    assert billing.invoice_number == billing_record.identifier
    assert billing.payer_text == billing_record.description
    assert billing.iss_retained == 2
    assert billing.total_retained == 2
    assert actual.account_id == billing.account_id == account.id
    assert actual.unit_id == billing.unit_id == unit.id
    assert sorted(
        item.amount
        for item in ton_session.scalars(
            select(FinancialDerivedFact).where(FinancialDerivedFact.run_id == first.id)
        )
    ) == [-2, 100.25]
    readiness = financial_domain.readiness(
        ton_session, admin, first.id, datetime.date(2026, 1, 1), unit.id
    )
    assert not readiness.ready
    assert readiness.blockers["BUDGET_PERIOD_UNRESOLVED"] == 2
    assert readiness.blockers["ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED"] == 1
    outsider = factories.make_user(ton_session)
    ton_session.commit()
    with pytest.raises(OnyxError):
        financial_domain.get_run(ton_session, outsider, first.id)
    _map(
        ton_session,
        admin,
        budget_source_id,
        MappingKind.BUDGET_PERIOD,
        str(budget_execution_id),
        calendar_period=datetime.date(2026, 1, 1),
    )
    second = financial_domain.normalize(
        ton_session, admin, request, reviewed.dataset_revision, reviewed.as_of
    )
    assert second.id != first.id
    assert second.statistics.get("budget_period_unresolved", 0) == 0
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(FinancialBudgetFact)
            .where(
                FinancialBudgetFact.run_id == first.id,
                FinancialBudgetFact.calendar_period.is_not(None),
            )
        )
        == 0
    )
    assert (
        financial_domain.readiness(
            ton_session, admin, second.id, datetime.date(2026, 1, 1), unit.id
        ).actual_budget_aligned_count
        == 1
    )
    assert (
        ton_session.scalar(select(func.count()).select_from(FinancialNormalizationRun))
        == 2
    )
    assert readiness.actual_count == 1
    assert readiness.derived_count == 2
    _map(
        ton_session,
        admin,
        budget_source_id,
        MappingKind.BUDGET_ACCOUNT,
        budget_record.identifier,
        account_id=tax_account.id,
    )
    insert_batches = financial_domain._insert_batches

    def fail_after_actual_batch(
        session: Session, model: type[Any], rows: list[dict[str, Any]]
    ) -> None:
        insert_batches(session, model, rows)
        if model is FinancialActualFact:
            raise RuntimeError("synthetic batch failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(financial_domain, "_insert_batches", fail_after_actual_batch)
        with pytest.raises(RuntimeError, match="synthetic batch failure"):
            financial_domain.normalize(
                ton_session, admin, request, reviewed.dataset_revision, reviewed.as_of
            )
    failed = ton_session.scalar(
        select(FinancialNormalizationRun).where(
            FinancialNormalizationRun.status == "FAILED"
        )
    )
    assert failed is not None
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(FinancialActualFact)
            .where(FinancialActualFact.run_id == failed.id)
        )
        == 0
    )
    assert (
        ton_session.scalar(
            select(func.count())
            .select_from(FinancialBillingFact)
            .where(FinancialBillingFact.run_id == failed.id)
        )
        == 0
    )


def test_exact_reconciliation_keeps_unmatched_and_ambiguous() -> None:
    run_id = uuid4()
    unit_id = uuid4()
    account_id = uuid4()
    month = datetime.date(2026, 2, 1)

    def actual(document: str, amount: int) -> dict[str, Any]:
        return {
            "id": uuid4(),
            "calendar_period": month,
            "unit_id": unit_id,
            "account_id": account_id,
            "movement_amount": amount,
            "document": document,
        }

    def billing(document: str, amount: int) -> dict[str, Any]:
        return {
            "id": uuid4(),
            "competence_period": month,
            "unit_id": unit_id,
            "account_id": account_id,
            "service_amount": amount,
            "document": document,
        }

    actuals = [actual("A", 10), actual("B", 20), actual("D", 40)]
    billings = [billing("A", 10), billing("C", 30), billing("D", 15), billing("D", 25)]
    rows = financial_domain._reconcile(
        actuals,
        billings,
        {item["id"]: item["document"] for item in actuals},
        {item["id"]: item["document"] for item in billings},
        {account_id},
        run_id,
    )
    statuses = [item["status"] for item in rows]
    assert statuses.count("MATCHED") == 1
    assert statuses.count("NG_ONLY") == 1
    assert statuses.count("BILLING_ONLY") == 1
    assert statuses.count("AMBIGUOUS") == 3
    assert all(item["run_id"] == run_id for item in rows)


def test_mapping_versions_use_exact_keys_and_effective_dates() -> None:
    source_id = uuid4()
    older = FinancialMapping(
        id=uuid4(),
        source_id=source_id,
        kind=MappingKind.ACCOUNT.value,
        source_key="SYN-01",
        account_id=uuid4(),
        effective_from=None,
        effective_to=None,
    )
    newer = FinancialMapping(
        id=uuid4(),
        source_id=source_id,
        kind=MappingKind.ACCOUNT.value,
        source_key="SYN-01",
        account_id=uuid4(),
        effective_from=datetime.date(2026, 1, 1),
        effective_to=None,
    )
    index = financial_domain.MappingIndex([(newer, 2), (older, 1)])
    assert (
        index.find(source_id, MappingKind.ACCOUNT, "SYN-01", datetime.date(2025, 1, 1))
        is older
    )
    assert (
        index.find(source_id, MappingKind.ACCOUNT, "SYN-01", datetime.date(2026, 1, 1))
        is newer
    )
    assert (
        index.find(source_id, MappingKind.ACCOUNT, "SYN-0", datetime.date(2026, 1, 1))
        is None
    )
