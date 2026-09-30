"""Minimal DATA-004C/D APIs. Source ACLs guard every input and output."""

import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import financial_domain as repository
from onyx.db.ton import financial_readiness
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.financial_domain.models import (
    AccountCreate,
    AccountView,
    AmountBasisApproval,
    AmountBasisRevisionView,
    FactView,
    MappingCreate,
    MappingView,
    NormalizationRequest,
    NormalizationView,
    ReadinessView,
    ReconciliationItemView,
    UnitView,
)
from onyx.ton.financial_domain.readiness_models import (
    BlockerPage,
    CandidateRejection,
    LegacyCandidateImport,
    ReadinessOverview,
    ReconciliationApproval,
)
from onyx.ton.financial_review.service import dataset_summary
from onyx.utils.audit import AuditAction, AuditOutcome

router = APIRouter(prefix="/ton/financial-domain", tags=["TON Financial Domain"])


@router.post("/accounts")
def create_account(
    request: AccountCreate,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> AccountView:
    account = repository.create_account(session, user, request)
    result = AccountView.model_validate(account)
    session.commit()
    return result


@router.get("/accounts")
def list_accounts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=100),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[AccountView]:
    return [
        AccountView.model_validate(item)
        for item in repository.list_accounts(session, user, limit, offset, search)
    ]


@router.get("/units")
def list_financial_units(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=100),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[UnitView]:
    return [
        UnitView.model_validate(unit)
        for unit in financial_readiness.list_units(session, user, limit, offset, search)
    ]


@router.post("/mappings")
def create_mapping(
    request: MappingCreate,
    user: User = Depends(require_permission(Permission.MANAGE_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> MappingView:
    if not request.reason or not request.reason.strip():
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Approval reason is required")
    result = repository.create_mapping(session, user, request)
    session.commit()
    return result


@router.get("/sources/{source_id}/mappings")
def list_mappings(
    source_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[MappingView]:
    return repository.list_mappings(session, user, source_id, limit, offset)


@router.post("/normalizations")
def normalize(
    request: NormalizationRequest,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> NormalizationView:
    summary = dataset_summary(
        session, user, request.ng_source_id, request.review_run_id
    )
    run = repository.normalize(
        session, user, request, summary.dataset_revision, summary.as_of
    )
    return NormalizationView.model_validate(run)


@router.get("/normalizations")
def list_normalizations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[NormalizationView]:
    return [
        NormalizationView.model_validate(run)
        for run in repository.list_runs(session, user, limit, offset)
    ]


@router.get("/normalizations/{run_id}")
def get_normalization(
    run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> NormalizationView:
    return NormalizationView.model_validate(repository.get_run(session, user, run_id))


@router.get("/normalizations/{run_id}/facts/{fact_type}")
def list_facts(
    run_id: UUID,
    fact_type: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[FactView]:
    return repository.list_facts(session, user, run_id, fact_type, limit, offset)


@router.get("/normalizations/{run_id}/coverage")
def get_mapping_coverage(
    run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    run = repository.get_run(session, user, run_id)
    stats = run.statistics
    return {
        "actual_total": stats.get("canonical_actuals", 0),
        "actual_account_mapped": stats.get("canonical_actuals", 0)
        - stats.get("actual_unmapped_account", 0),
        "actual_unit_mapped": stats.get("canonical_actuals", 0)
        - stats.get("actual_unmapped_unit", 0),
        "billing_total": stats.get("billing_facts", 0),
        "billing_account_mapped": stats.get("billing_facts", 0)
        - stats.get("billing_unmapped_account", 0),
        "billing_unit_mapped": stats.get("billing_facts", 0)
        - stats.get("billing_unmapped_unit", 0),
        "budget_total": stats.get("budget_facts", 0),
        "budget_account_mapped": stats.get("budget_facts", 0)
        - stats.get("budget_unmapped_account", 0),
        "budget_unit_mapped": stats.get("budget_facts", 0)
        - stats.get("budget_unmapped_unit", 0),
    }


@router.get("/normalizations/{run_id}/reconciliation")
def get_reconciliation_summary(
    run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    run = repository.get_run(session, user, run_id)
    return {
        key.removeprefix("reconciliation_").upper(): value
        for key, value in run.statistics.items()
        if key.startswith("reconciliation_") and key != "reconciliation_items"
    }


@router.get("/normalizations/{run_id}/reconciliation/items")
def list_reconciliation_items(
    run_id: UUID,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[ReconciliationItemView]:
    return [
        ReconciliationItemView.model_validate(item)
        for item in repository.list_reconciliation_items(
            session, user, run_id, limit, offset, status
        )
    ]


@router.get("/normalizations/{run_id}/dre-input/facts/{fact_type}")
def list_dre_input_facts(
    run_id: UUID,
    fact_type: str,
    period: datetime.date,
    unit_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[FactView]:
    return repository.list_facts(
        session, user, run_id, fact_type, limit, offset, period, unit_id
    )


@router.get("/normalizations/{run_id}/dre-input")
def get_dre_input(
    run_id: UUID,
    period: datetime.date,
    unit_id: UUID | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ReadinessView:
    return repository.readiness(session, user, run_id, period, unit_id)


@router.get("/normalizations/{run_id}/readiness")
def financial_readiness_overview(
    run_id: UUID,
    structure_version_id: UUID,
    unit_id: UUID | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ReadinessOverview:
    return financial_readiness.overview(
        session, user, run_id, structure_version_id, unit_id
    )


@router.get("/normalizations/{run_id}/readiness/blockers/{blocker}")
def financial_readiness_blockers(
    run_id: UUID,
    blocker: str,
    structure_version_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=100),
    unit_id: UUID | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> BlockerPage:
    return financial_readiness.list_blockers(
        session,
        user,
        run_id,
        structure_version_id,
        blocker,
        limit,
        offset,
        search,
        unit_id,
    )


@router.post("/candidates/rejections")
def reject_mapping_candidate(
    request: CandidateRejection,
    user: User = Depends(require_permission(Permission.MANAGE_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> dict[str, UUID]:
    decision_id = financial_readiness.reject_candidate(session, user, request)
    session.commit()
    return {"id": decision_id}


@router.post("/candidates/legacy-import")
def import_legacy_candidates(
    request: LegacyCandidateImport,
    user: User = Depends(require_permission(Permission.MANAGE_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    count = financial_readiness.import_legacy_candidates(session, user, request)
    session.commit()
    return {"imported": count}


@router.post("/accounts/{account_id}/amount-basis")
def approve_amount_basis(
    account_id: UUID,
    request: AmountBasisApproval,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> AmountBasisRevisionView:
    revision = repository.approve_amount_basis(
        session, user, account_id, request.basis, request.reason
    )
    result = AmountBasisRevisionView.model_validate(revision)
    session.commit()
    return result


@router.post("/normalizations/{run_id}/reconciliation/items/{item_id}/decision")
def decide_reconciliation(
    run_id: UUID,
    item_id: UUID,
    request: ReconciliationApproval,
    user: User = Depends(require_permission(Permission.MANAGE_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    revision = repository.decide_reconciliation(
        session, user, run_id, item_id, request.decision, request.reason
    )
    number = revision.number
    session.commit()
    return {"revision_number": number}


@router.post("/normalizations/recompute")
def recompute_financial_readiness(
    request: NormalizationRequest,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> NormalizationView:
    summary = dataset_summary(
        session, user, request.ng_source_id, request.review_run_id
    )
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_FINANCIAL_RECOMPUTE_REQUEST,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.REVIEW_RUN,
        resource_id=request.review_run_id,
    )
    session.commit()
    run = repository.normalize(
        session, user, request, summary.dataset_revision, summary.as_of
    )
    return NormalizationView.model_validate(run)


@router.post("/normalizations/{run_id}/recompute")
def recompute_from_run(
    run_id: UUID,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> NormalizationView:
    request = repository.normalization_request_for_run(session, user, run_id)
    return recompute_financial_readiness(request, user, session)
