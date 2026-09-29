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
from onyx.ton.financial_domain.models import (
    AccountCreate,
    AccountView,
    FactView,
    MappingCreate,
    MappingView,
    NormalizationRequest,
    NormalizationView,
    ReadinessView,
    ReconciliationItemView,
)
from onyx.ton.financial_review.service import dataset_summary

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
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> list[AccountView]:
    return [
        AccountView.model_validate(item)
        for item in repository.list_accounts(session, user, limit, offset)
    ]


@router.post("/mappings")
def create_mapping(
    request: MappingCreate,
    user: User = Depends(require_permission(Permission.MANAGE_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> MappingView:
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
