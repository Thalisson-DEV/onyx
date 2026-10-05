"""Closing treatments decided by the Controladoria.

TON users reach the routes; the repository allows TON administrators only and
audits refused attempts.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import closing_treatments as repository
from onyx.ton.financial_domain.models import (
    TreatmentCreate,
    TreatmentTable,
    TreatmentView,
)

router = APIRouter(prefix="/ton/closing-treatments", tags=["TON Closing Treatments"])


@router.get("")
def get_treatment_table(
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> TreatmentTable:
    return repository.treatment_table(session, user)


@router.get("/{treatment_key}/history")
def treatment_history(
    treatment_key: str,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[TreatmentView]:
    return repository.treatment_history(session, user, treatment_key)


@router.post("")
def create_treatment(
    request: TreatmentCreate,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> TreatmentView:
    row = repository.create_treatment(session, user, request)
    session.commit()
    return repository.treatment_history(session, user, row.treatment_key)[0]
