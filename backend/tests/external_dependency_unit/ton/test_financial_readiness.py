"""Synthetic DATA-006 readiness decisions and immutable revisions."""

import datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import dre, financial_domain, financial_readiness
from onyx.db.ton.enums import BusinessUnitKind
from onyx.db.ton.models import (
    BusinessUnit,
    DreCalculationRun,
    FinancialBudgetFact,
    FinancialLegacyCandidate,
    FinancialMapping,
    FinancialReconciliationItem,
    ParsedSourceRecord,
    TonAuditEvent,
)
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.dre.models import DreLineDefinition, DreLineType, DreStructureCreate
from onyx.ton.financial_domain.models import AccountCreate, MappingCreate, MappingKind
from onyx.ton.financial_domain.readiness_models import (
    CandidateRejection,
    LegacyCandidateImport,
    LegacyCandidateImportRow,
)
from tests.external_dependency_unit.ton import factories
from tests.external_dependency_unit.ton.test_financial_domain import (
    build_complete_synthetic_scope,
)
from tests.external_dependency_unit.ton.test_financial_review import (
    Pipeline,
    book,
    launch,
)

pytest_plugins = ("tests.external_dependency_unit.ton.test_financial_domain",)


def test_basis_budget_and_reconciliation_recompute_keep_old_run(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    first_id, account_id, _unit_id = build_complete_synthetic_scope(
        ton_session, admin, store
    )
    first = financial_domain.get_run(ton_session, admin, first_id)
    version = dre.create_structure(
        ton_session,
        admin,
        DreStructureCreate(
            key="synthetic-readiness",
            label="Synthetic readiness",
            lines=[
                DreLineDefinition(
                    code="service",
                    label="Service",
                    position=1,
                    line_type=DreLineType.SOURCE_SUM,
                )
            ],
        ),
    )
    before = financial_readiness.overview(
        ton_session, admin, first_id, version.id, None
    )
    assert len(before.periods) == 1
    assert before.periods[0].blockers["DRE_ACCOUNT_UNMAPPED"] > 0
    drill = financial_readiness.list_blockers(
        ton_session, admin, first_id, version.id, "DRE_ACCOUNT_UNMAPPED", 1, 0, None
    )
    assert drill.total == 1
    assert drill.rows[0].account_id == account_id
    assert ton_session.scalar(select(DreCalculationRun.id)) is None
    old_actual = financial_domain.list_facts(
        ton_session, admin, first_id, "ACTUAL", 10, 0
    )
    assert old_actual[0].amount_basis == "MOVEMENT"
    budget_record = ton_session.scalar(
        select(FinancialBudgetFact).where(FinancialBudgetFact.run_id == first_id)
    )
    assert budget_record is not None
    source_record = budget_record.source_record_id
    budget_source = ton_session.execute(
        text(
            "SELECT source_id, execution_id FROM ton_operational_source_record WHERE id = :id"
        ),
        {"id": source_record},
    ).one()
    financial_domain.approve_amount_basis(
        ton_session, admin, account_id, "FINAL", "Finance approved final amount"
    )
    financial_domain.create_mapping(
        ton_session,
        admin,
        MappingCreate(
            source_id=budget_source.source_id,
            kind=MappingKind.BUDGET_PERIOD,
            source_key=str(budget_source.execution_id),
            calendar_period=datetime.date(2026, 1, 1),
            effective_to=datetime.date(2026, 12, 1),
            reason="Approved contract start and monthly term",
        ),
    )
    reconciliation = ton_session.scalar(
        select(FinancialReconciliationItem).where(
            FinancialReconciliationItem.run_id == first_id,
        )
    )
    assert reconciliation is not None
    financial_domain.decide_reconciliation(
        ton_session,
        admin,
        first_id,
        reconciliation.id,
        "SUPPLEMENTAL",
        "Finance reviewed source evidence",
    )
    ton_session.commit()
    second = financial_domain.normalize(
        ton_session,
        admin,
        financial_domain.normalization_request_for_run(ton_session, admin, first_id),
        first.dataset_revision,
        first.dataset_as_of,
    )
    assert second.id != first_id
    assert second.amount_basis_revision_number > first.amount_basis_revision_number
    assert second.mapping_revision_number > first.mapping_revision_number
    assert second.reconciliation_decision_number > first.reconciliation_decision_number
    assert (
        financial_domain.list_facts(ton_session, admin, first_id, "ACTUAL", 10, 0)[
            0
        ].amount_basis
        == "MOVEMENT"
    )
    assert (
        financial_domain.list_facts(ton_session, admin, second.id, "ACTUAL", 10, 0)[
            0
        ].amount_basis
        == "FINAL"
    )
    assert (
        ton_session.scalar(
            select(FinancialBudgetFact).where(
                FinancialBudgetFact.run_id == first_id,
                FinancialBudgetFact.calendar_period == datetime.date(2026, 12, 1),
            )
        )
        is None
    )
    assert (
        ton_session.scalar(
            select(FinancialBudgetFact).where(
                FinancialBudgetFact.run_id == second.id,
                FinancialBudgetFact.calendar_period == datetime.date(2026, 12, 1),
            )
        )
        is not None
    )
    assert (
        ton_session.scalar(
            select(FinancialReconciliationItem).where(
                FinancialReconciliationItem.run_id == first_id,
                FinancialReconciliationItem.status == "SUPPLEMENTAL",
            )
        )
        is None
    )
    assert (
        ton_session.scalar(
            select(FinancialReconciliationItem).where(
                FinancialReconciliationItem.run_id == second.id,
                FinancialReconciliationItem.status == "SUPPLEMENTAL",
            )
        )
        is not None
    )
    assert (
        ton_session.scalar(
            select(TonAuditEvent).where(
                TonAuditEvent.action == "ton_financial.amount_basis_version"
            )
        )
        is not None
    )


def test_exact_unit_candidate_can_be_rejected_without_approval(
    ton_session: Session, admin: User, store: FileStore
) -> None:
    pipeline = Pipeline(ton_session, admin, store)
    execution_id = pipeline.parse(
        book([launch("1.1 - Synthetic account", datetime.date(2026, 1, 10))])
    )
    record = ton_session.scalar(
        select(ParsedSourceRecord).where(
            ParsedSourceRecord.execution_id == execution_id
        )
    )
    assert record is not None
    assert record.administrative_unit is not None
    unit = BusinessUnit(
        code=record.administrative_unit,
        name="Synthetic unit",
        kind=BusinessUnitKind.OPERATIONAL,
    )
    ton_session.add(unit)
    ton_session.commit()
    imported = financial_readiness.import_legacy_candidates(
        ton_session,
        admin,
        LegacyCandidateImport(
            source_id=record.source_id,
            kind="UNIT",
            reference_label="Synthetic exact-code table",
            reference_digest="a" * 64,
            rows=[
                LegacyCandidateImportRow(
                    source_key=record.administrative_unit,
                    suggested_code=record.administrative_unit,
                )
            ],
        ),
    )
    assert imported == 1
    assert ton_session.scalar(select(FinancialLegacyCandidate.id)) is not None
    candidate = financial_readiness._candidate(
        ton_session, admin, record.source_id, "UNIT", record.administrative_unit
    )
    assert candidate is not None
    assert candidate.evidence == "EXACT_CODE"
    read_only = factories.make_user(ton_session)
    with pytest.raises(OnyxError):
        financial_readiness.reject_candidate(
            ton_session,
            read_only,
            CandidateRejection(
                source_id=record.source_id,
                kind="UNIT",
                source_key=record.administrative_unit,
                target_id=candidate.target_id,
                evidence=candidate.evidence,
                reason="Not the same unit",
            ),
        )
    financial_readiness.reject_candidate(
        ton_session,
        admin,
        CandidateRejection(
            source_id=record.source_id,
            kind="UNIT",
            source_key=record.administrative_unit,
            target_id=candidate.target_id,
            evidence=candidate.evidence,
            reason="Not the same unit",
        ),
    )
    ton_session.commit()
    assert (
        financial_readiness._candidate(
            ton_session,
            admin,
            record.source_id,
            "UNIT",
            record.administrative_unit,
        )
        is None
    )
    financial_readiness.reject_candidate(
        ton_session,
        admin,
        CandidateRejection(
            source_id=record.source_id,
            kind="UNIT",
            source_key=record.administrative_unit,
            evidence="LEGACY_REFERENCE",
            reference_digest="a" * 64,
            reason="Legacy table does not identify this unit",
        ),
    )
    ton_session.commit()
    account = financial_domain.create_account(
        ton_session,
        admin,
        AccountCreate(code=record.account_code, label="Synthetic account"),
    )
    account_candidate = financial_readiness._candidate(
        ton_session, admin, record.source_id, "ACCOUNT", record.account_code
    )
    assert account_candidate is not None
    assert account_candidate.target_id == account.id
    approved = financial_domain.create_mapping(
        ton_session,
        admin,
        MappingCreate(
            source_id=record.source_id,
            kind=MappingKind.ACCOUNT,
            source_key=record.account_code,
            account_id=account.id,
            reason="Finance reviewed exact source code",
        ),
    )
    assert approved.revision_number > 0
    unit_mapping = financial_domain.create_mapping(
        ton_session,
        admin,
        MappingCreate(
            source_id=record.source_id,
            kind=MappingKind.UNIT,
            source_key=record.administrative_unit,
            unit_id=unit.id,
            reason="Finance confirmed the source unit despite rejected evidence",
        ),
    )
    assert unit_mapping.revision_number > approved.revision_number
    assert unit_mapping.unit_id == unit.id
    replacement = BusinessUnit(
        code="REPLACEMENT",
        name="Synthetic replacement unit",
        kind=BusinessUnitKind.OPERATIONAL,
    )
    ton_session.add(replacement)
    ton_session.flush()
    superseding = financial_domain.create_mapping(
        ton_session,
        admin,
        MappingCreate(
            source_id=record.source_id,
            kind=MappingKind.UNIT,
            source_key=record.administrative_unit,
            unit_id=replacement.id,
            reason="Finance corrected the canonical unit",
        ),
    )
    assert superseding.revision_number > unit_mapping.revision_number
    assert superseding.unit_id == replacement.id
    assert ton_session.get(FinancialMapping, unit_mapping.id) is not None
