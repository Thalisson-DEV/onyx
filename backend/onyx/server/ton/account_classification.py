"""Account classification module: NG code -> natureza, review and AI
pre-classification. TON administrators only."""

import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import account_classification as repository
from onyx.ton.account_classification.models import (
    ClassificationChange,
    ClassificationConfirm,
    ClassificationStatus,
    ClassificationTable,
    SuggestionRequest,
    SuggestionRunResult,
)
from onyx.ton.account_classification.suggester import suggest
from onyx.ton.account_classification.xlsx_export import build_workbook

router = APIRouter(
    prefix="/ton/account-classification", tags=["TON Account Classification"]
)


@router.get("")
def get_classification_table(
    source_id: UUID | None = Query(None),
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> ClassificationTable:
    return repository.classification_table(session, user, source_id)


@router.post("/{source_id}/confirm")
def confirm_classification(
    source_id: UUID,
    request: ClassificationConfirm,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    review = repository.confirm_classification(session, user, source_id, request)
    session.commit()
    return {"review_id": str(review.id)}


@router.post("/{source_id}/change")
def change_classification(
    source_id: UUID,
    request: ClassificationChange,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    review = repository.change_classification(session, user, source_id, request)
    session.commit()
    return {"review_id": str(review.id)}


@router.post("/{source_id}/suggestions")
def run_suggestions(
    source_id: UUID,
    request: SuggestionRequest,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> SuggestionRunResult:
    table = repository.classification_table(session, user, source_id)
    targets = repository.suggestion_inputs(table, session, request.account_codes)
    # End the read transaction before the slow model call.
    session.commit()
    natures = [(item.natureza, item.dre_group) for item in table.natures]
    confirmed = [
        (row.account_code, row.description, row.natureza)
        for row in table.rows
        if row.status is ClassificationStatus.CONFIRMED and row.natureza
    ]
    result = suggest(targets, natures, confirmed)
    evidence = {
        item.code: {
            "pattern": item.pattern.model_dump() if item.pattern else None,
            "history_samples": len(item.history),
            "current_natureza": item.current_natureza,
        }
        for item in targets
    }
    count = repository.record_suggestions(
        session, user, table, result.suggestions, result.model_name, evidence
    )
    session.commit()
    return SuggestionRunResult(
        requested=len(targets),
        suggested=count,
        skipped=sorted(set(result.skipped)),
        model_name=result.model_name,
    )


@router.get("/export.xlsx")
def export_classification(
    source_id: UUID | None = Query(None),
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> Response:
    table = repository.classification_table(session, user, source_id)
    now = datetime.datetime.now()
    return Response(
        content=build_workbook(table, now),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="ton-classificacao-contas-{now:%Y-%m-%d}.xlsx"'
        },
    )
