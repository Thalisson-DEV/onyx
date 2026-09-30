"""Minimal DRE configuration, readiness, and calculation API."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import dre as repository
from onyx.ton.dre.models import (
    DreReadinessView,
    DreResultLineView,
    DreRunView,
    DreScope,
    DreStructureCreate,
    DreStructureView,
    DreVersionCreate,
    DreVersionView,
)

router = APIRouter(prefix="/ton/dre", tags=["TON DRE"])


@router.post("/structures")
def create_structure(
    request: DreStructureCreate,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> DreVersionView:
    result = repository.create_structure(session, user, request)
    session.commit()
    return result


@router.get("/structures")
def list_structures(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> list[DreStructureView]:
    return repository.list_structures(session, user, limit, offset)


@router.get("/structures/{structure_id}")
def get_structure(
    structure_id: UUID,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> DreStructureView:
    return repository.get_structure(session, user, structure_id)


@router.post("/structures/{structure_id}/versions")
def create_version(
    structure_id: UUID,
    request: DreVersionCreate,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> DreVersionView:
    result = repository.create_version(session, user, structure_id, request)
    session.commit()
    return result


@router.get("/versions/{version_id}")
def get_version(
    version_id: UUID,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> DreVersionView:
    return repository.get_version(session, user, version_id)


@router.post("/readiness")
def readiness(
    scope: DreScope,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> DreReadinessView:
    return repository.readiness(session, user, scope)


@router.post("/calculations")
def calculate(
    scope: DreScope,
    user: User = Depends(require_permission(Permission.IMPORT_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> DreRunView:
    try:
        return repository.execute(session, user, scope)
    except Exception:
        session.rollback()
        try:
            repository.audit_failed_calculation(
                session, user, scope.structure_version_id
            )
            session.commit()
        except Exception:
            session.rollback()
        raise


@router.get("/calculations/{run_id}")
def get_calculation(
    run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> DreRunView:
    return repository.get_calculation(session, user, run_id)


@router.get("/calculations/{run_id}/lines")
def list_result_lines(
    run_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[DreResultLineView]:
    return repository.list_result_lines(session, user, run_id, limit, offset)
