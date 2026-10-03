"""DRE configuration, readiness, stored results, and provenance API."""

import csv
import io
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import dre as repository
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.dre.models import (
    DreAssignmentApproval,
    DreContributorPage,
    DrePeriodPoint,
    DreReadinessView,
    DreResultLineView,
    DreRunView,
    DreScope,
    DreStatementView,
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
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[DreStructureView]:
    return repository.list_structures(session, user, limit, offset)


@router.get("/structures/{structure_id}")
def get_structure(
    structure_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
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


@router.post("/structures/{structure_id}/assignments")
def approve_assignment(
    structure_id: UUID,
    request: DreAssignmentApproval,
    user: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    session: Session = Depends(get_session),
) -> DreVersionView:
    result = repository.approve_assignment(session, user, structure_id, request)
    session.commit()
    return result


@router.get("/versions/{version_id}")
def get_version(
    version_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> DreVersionView:
    return repository.get_version(session, user, version_id)


@router.get("/structures/{structure_id}/latest-version")
def get_latest_version(
    structure_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> DreVersionView:
    return repository.get_latest_version(session, user, structure_id)


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


@router.get("/calculations")
def list_calculations(
    period: date,
    unit_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[DreRunView]:
    return repository.list_calculations(session, user, period, unit_id, limit, offset)


@router.get("/calculations/series")
def period_series(
    normalization_run_id: UUID,
    structure_version_id: UUID,
    year: int = Query(ge=1900, le=9998),
    line_code: str = Query(min_length=1),
    unit_id: UUID | None = None,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> list[DrePeriodPoint]:
    return repository.get_period_series(
        session,
        user,
        normalization_run_id,
        structure_version_id,
        year,
        unit_id,
        line_code,
    )


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


@router.get("/calculations/{run_id}/statement")
def get_statement(
    run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> DreStatementView:
    return repository.get_statement(session, user, run_id)


@router.get("/calculations/{run_id}/lines/{line_code}/contributors")
def list_contributors(
    run_id: UUID,
    line_code: str,
    fact_type: str,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> DreContributorPage:
    return repository.list_contributors(
        session, user, run_id, line_code, fact_type, limit, offset
    )


def _csv_safe(value: str) -> str:
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


@router.get("/calculations/{run_id}/export.csv")
def export_calculation(
    run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> Response:
    run = repository.get_calculation(session, user, run_id)
    if run.status != "READY":
        raise OnyxError(
            OnyxErrorCode.CONFLICT, "Only ready DRE results can be exported"
        )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["DRE", "READY"])
    writer.writerow(["period", run.scope.period.isoformat()])
    writer.writerow(
        ["unit_id", str(run.scope.unit_id) if run.scope.unit_id else "CONSOLIDATED"]
    )
    writer.writerow(["result_id", str(run.id)])
    writer.writerow(["calculated_at", run.finished_at.isoformat()])
    writer.writerow(
        ["structure_version", run.provenance.get("dre_structure_version_number", "")]
    )
    writer.writerow(["dataset_revision", run.provenance.get("dataset_revision", "")])
    writer.writerow(
        [
            "budget_executions",
            ";".join(
                str(item) for item in run.provenance.get("budget_execution_ids", [])
            ),
        ]
    )
    writer.writerow([])
    writer.writerow(
        [
            "line_code",
            "line",
            "realizado",
            "orcado",
            "variance",
            "variance_percent",
            "realizado_ytd",
            "orcado_ytd",
            "variance_ytd",
            "variance_percent_ytd",
        ]
    )
    offset = 0
    while True:
        lines = repository.list_result_lines(session, user, run_id, 100, offset)
        for line in lines:
            writer.writerow(
                [
                    _csv_safe(line.code),
                    _csv_safe(line.label),
                    line.realizado,
                    line.orcado,
                    line.variance,
                    line.variance_percent,
                    line.realizado_ytd,
                    line.orcado_ytd,
                    line.variance_ytd,
                    line.variance_percent_ytd,
                ]
            )
        offset += len(lines)
        if len(lines) < 100:
            break
    repository.audit_export(session, user, run_id)
    session.commit()
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="dre-{run.scope.period.isoformat()}-{run.id}.csv"'
        },
    )


@router.get("/calculations/{run_id}/export.xlsx")
def export_calculation_xlsx(
    run_id: UUID,
    user: User = Depends(require_permission(Permission.READ_TON_SOURCES)),
    session: Session = Depends(get_session),
) -> Response:
    run, content = repository.export_workbook(session, user, run_id)
    repository.audit_export(session, user, run_id)
    session.commit()
    period = run.scope.period
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="dre-{period.year}-01-a-{period.month:02d}.xlsx"'
        },
    )
