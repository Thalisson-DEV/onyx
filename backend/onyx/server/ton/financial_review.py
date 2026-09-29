"""DATA-003 financial review API.

Access reuses existing tokens and ACLs: source reads and review runs follow the
source ACL, findings and decisions follow the occurrence ACL.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import financial_review as repository
from onyx.db.ton.enums import OccurrenceCriticality, OccurrenceStatus
from onyx.ton.financial_review import service
from onyx.ton.financial_review.models import (
    EvidenceView,
    FindingDetailView,
    FindingSummaryView,
    ReviewCategory,
    ReviewDecisionRequest,
    ReviewDecisionView,
    ReviewDisposition,
    ReviewedDatasetSummaryView,
    ReviewedRecordView,
    ReviewRunStatus,
    ReviewRunView,
    RuleCatalogView,
    RuleEvaluationView,
)

router = APIRouter(prefix="/ton/financial-review", tags=["TON Financial Review"])


@router.get("/rules")
def get_rule_catalog(
    _user: User = Depends(require_permission(Permission.READ_TON_ANALYSIS)),
) -> RuleCatalogView:
    return service.catalog_view()


@router.post("/sources/{source_id}/executions/{execution_id}/reviews")
def run_review(
    source_id: UUID,
    execution_id: UUID,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ReviewRunView:
    return service.execute_review(session, user, source_id, execution_id)


@router.get("/sources/{source_id}/reviews")
def list_reviews(
    source_id: UUID,
    execution_id: UUID | None = None,
    status: ReviewRunStatus | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[ReviewRunView]:
    return [
        ReviewRunView.model_validate(run)
        for run in repository.list_review_runs(
            session,
            user,
            source_id,
            limit,
            offset,
            execution_id=execution_id,
            status=status,
        )
    ]


@router.get("/sources/{source_id}/reviews/{review_run_id}")
def get_review(
    source_id: UUID,
    review_run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ReviewRunView:
    return ReviewRunView.model_validate(
        repository.get_review_run(session, user, source_id, review_run_id)
    )


@router.get("/sources/{source_id}/reviews/{review_run_id}/rule-evaluations")
def list_rule_evaluations(
    source_id: UUID,
    review_run_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[RuleEvaluationView]:
    return service.rule_evaluations(
        session, user, source_id, review_run_id, limit, offset
    )


@router.get("/sources/{source_id}/reviews/{review_run_id}/dataset")
def get_reviewed_dataset(
    source_id: UUID,
    review_run_id: UUID,
    as_of: datetime | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> ReviewedDatasetSummaryView:
    return service.dataset_summary(session, user, source_id, review_run_id, as_of)


@router.get("/sources/{source_id}/reviews/{review_run_id}/dataset/records")
def list_reviewed_records(
    source_id: UUID,
    review_run_id: UUID,
    disposition: ReviewDisposition | None = None,
    sheet_month: int | None = Query(None, ge=1, le=12),
    account_code: str | None = Query(None, max_length=100),
    administrative_unit: str | None = Query(None, max_length=500),
    unit_missing: bool | None = None,
    as_of: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[ReviewedRecordView]:
    return service.dataset_records(
        session,
        user,
        source_id,
        review_run_id,
        disposition=disposition,
        sheet_month=sheet_month,
        account_code=account_code,
        administrative_unit=administrative_unit,
        unit_missing=unit_missing,
        limit=limit,
        offset=offset,
        as_of=as_of,
    )


@router.get("/findings")
def list_findings(
    source_id: UUID | None = None,
    review_run_id: UUID | None = None,
    execution_id: UUID | None = None,
    rule_key: str | None = Query(None, max_length=100),
    category: ReviewCategory | None = None,
    criticality: OccurrenceCriticality | None = None,
    status: OccurrenceStatus | None = None,
    sheet_month: int | None = Query(None, ge=1, le=12),
    blocking: bool | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_OCCURRENCES)),
    session: Session = Depends(get_session),
) -> list[FindingSummaryView]:
    return service.list_findings(
        session,
        user,
        repository.FindingFilters(
            source_id=source_id,
            review_run_id=review_run_id,
            execution_id=execution_id,
            rule_key=rule_key,
            category=category.value if category else None,
            criticality=criticality,
            status=status,
            sheet_month=sheet_month,
            blocking=blocking,
        ),
        limit,
        offset,
    )


@router.get("/findings/{finding_id}")
def get_finding(
    finding_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_OCCURRENCES)),
    session: Session = Depends(get_session),
) -> FindingDetailView:
    return service.get_finding(session, user, finding_id)


@router.get("/findings/{finding_id}/evidence")
def list_finding_evidence(
    finding_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_OCCURRENCES)),
    session: Session = Depends(get_session),
) -> list[EvidenceView]:
    return service.list_evidence(session, user, finding_id, limit, offset)


@router.get("/occurrences/{occurrence_id}/decisions")
def list_decisions(
    occurrence_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_OCCURRENCES)),
    session: Session = Depends(get_session),
) -> list[ReviewDecisionView]:
    return service.list_decisions(session, user, occurrence_id, limit, offset)


@router.post("/occurrences/{occurrence_id}/decisions")
def record_decision(
    occurrence_id: UUID,
    request: ReviewDecisionRequest,
    user: User = Depends(require_permission(Permission.MANAGE_TON_OCCURRENCES)),
    session: Session = Depends(get_session),
) -> ReviewDecisionView:
    return service.record_decision(session, user, occurrence_id, request)
