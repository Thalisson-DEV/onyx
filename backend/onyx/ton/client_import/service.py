"""Client entry point over the existing TON capture and import services."""

from io import BytesIO
from typing import BinaryIO
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onyx.auth.permissions import has_global_permission
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import client_import as repository
from onyx.db.ton import financial_domain as financial_repository
from onyx.db.ton import import_profiles, operational_import, sources
from onyx.db.ton.acl import is_ton_administrator
from onyx.db.ton.models import ImportProfileExecution, ImportRun, SourceSnapshot
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import FileStore
from onyx.ton.client_import.models import (
    ClientImportView,
    ClientSourceView,
    DiagnosticSummary,
)
from onyx.ton.financial_domain.models import BudgetInput, NormalizationRequest
from onyx.ton.financial_review.service import dataset_summary, execute_review
from onyx.ton.ng_financial.models import ProfileExecutionStatus
from onyx.ton.ng_financial.parser import NgFinancialExportParser
from onyx.ton.ng_financial.service import execute_ng_profile
from onyx.ton.operational_import.parser import identify_profile
from onyx.ton.operational_import.service import execute_operational_profile
from onyx.ton.sources.models import (
    AcquisitionType,
    Sensitivity,
    SourceCreate,
    SourceFormat,
    SourceStatus,
)
from onyx.ton.sources.service import import_file
from onyx.ton.sources.validation import MAX_UPLOAD_BYTES, validate_upload
from onyx.utils.logger import setup_logger

logger = setup_logger()

CATALOG = {
    "financial_launches": (
        "NG / Lançamentos financeiros",
        "Movimentações financeiras do NG.",
        SourceFormat.XLSX,
    ),
    "billing_invoices": (
        "Faturamento / Notas fiscais",
        "Notas fiscais e valores de faturamento.",
        SourceFormat.XLS,
    ),
    "budget": (
        "Dotação / Orçamento",
        "Planejamento e execução do orçamento.",
        SourceFormat.XLSX,
    ),
}


def _contract(key: str) -> tuple[str, str, SourceFormat]:
    contract = CATALOG.get(key)
    if contract is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Financial source not found")
    return contract


def _view(
    execution: ImportProfileExecution, snapshot: SourceSnapshot, key: str
) -> ClientImportView:
    stats = execution.statistics
    diagnostics = [
        DiagnosticSummary(code=code.removeprefix("diagnostic."), count=int(count))
        for code, count in stats.items()
        if code.startswith("diagnostic.") and isinstance(count, int) and count > 0
    ]
    return ClientImportView(
        id=execution.id,
        source_id=execution.source_id,
        status=execution.status.value,
        filename=snapshot.original_filename,
        format=snapshot.format.value,
        size_bytes=snapshot.size_bytes,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        imported=int(stats.get("detail_records_parsed", 0)),
        rejected=int(stats.get("records_rejected", 0)),
        warnings=int(stats.get("warnings", 0)),
        errors=int(stats.get("errors", 0)),
        diagnostics=sorted(diagnostics, key=lambda item: item.code),
        downstream=["financial_review", "financial_readiness", "dre"]
        if key == "financial_launches"
        else ["financial_readiness", "dre"],
        failure_reason="PROCESSING_ERROR"
        if execution.status == ProfileExecutionStatus.FAILED
        else None,
    )


def _failed_capture_view(run: ImportRun, key: str) -> ClientImportView:
    return ClientImportView(
        id=run.id,
        source_id=run.source_id,
        status="FAILED",
        filename="",
        format=CATALOG[key][2].value,
        size_bytes=0,
        started_at=run.started_at,
        finished_at=run.finished_at,
        imported=0,
        rejected=0,
        warnings=0,
        errors=1,
        diagnostics=[],
        downstream=[],
        failure_reason="INVALID_FILE"
        if run.error_code == "INVALID_INPUT"
        else "PROCESSING_ERROR",
    )


def list_client_sources(session: Session, user: User) -> list[ClientSourceView]:
    result: list[ClientSourceView] = []
    for key, (name, description, format) in CATALOG.items():
        source = repository.visible_source(session, user, key)
        history = []
        if source is not None:
            history = [
                _view(execution, snapshot, key)
                for execution, snapshot in repository.import_history(
                    session, user, source.id
                )
            ] + [
                _failed_capture_view(run, key)
                for run in repository.failed_captures(session, user, source.id)
            ]
            history.sort(key=lambda item: item.started_at, reverse=True)
            history = history[:20]
        latest = history[0] if history else None
        success = (
            repository.last_successful_at(session, user, source.id)
            if source is not None
            else None
        )
        status = (
            "UNCONFIGURED"
            if source is None or source.status != SourceStatus.ACTIVE
            else "PROCESSING"
            if latest is not None and latest.status == "RUNNING"
            else "FAILED"
            if latest is not None and latest.status == "FAILED"
            else "ATTENTION"
            if latest is not None
            and (latest.status == "PARTIAL" or latest.warnings > 0)
            else "CURRENT"
            if latest is not None
            else "UNCONFIGURED"
        )
        result.append(
            ClientSourceView(
                key=key,
                name=name,
                description=description,
                format=format.value,
                source_id=source.id if source else None,
                can_import=bool(
                    has_global_permission(user, Permission.IMPORT_TON_SOURCES)
                )
                and (
                    (
                        source is not None
                        and source.status == SourceStatus.ACTIVE
                        and repository.source_by_key_for_import(session, user, key)
                        is not None
                    )
                    or (source is None and is_ton_administrator(user))
                ),
                status=status,
                last_success_at=success,
                last_attempt_at=latest.started_at if latest else None,
                latest=latest,
                history=history,
            )
        )
    return result


def get_client_import(
    session: Session, user: User, key: str, execution_id: UUID
) -> ClientImportView:
    _contract(key)
    source = repository.visible_source(session, user, key)
    if source is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Financial source not found")
    detail = repository.import_detail(session, user, source.id, execution_id)
    if detail is None:
        failed_run = repository.failed_capture_detail(
            session, user, source.id, execution_id
        )
        if failed_run is None:
            raise OnyxError(OnyxErrorCode.NOT_FOUND, "Import not found")
        return _failed_capture_view(failed_run, key)
    return _view(*detail, key)


def _source_for_upload(session: Session, user: User, key: str) -> UUID:
    source = repository.source_by_key_for_import(session, user, key)
    if source is not None:
        return source.id
    if not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Financial source not available")
    try:
        source = sources.create_source(
            session,
            user,
            SourceCreate(
                key=key,
                display_name=CATALOG[key][0],
                description=CATALOG[key][1],
                acquisition_type=AcquisitionType.FILE_UPLOAD,
                status=SourceStatus.ACTIVE,
                sensitivity=Sensitivity.RESTRICTED,
            ),
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise OnyxError(
            OnyxErrorCode.NOT_FOUND, "Financial source not available"
        ) from None
    return source.id


def _refresh_readiness(session: Session, user: User) -> tuple[str, UUID | None]:
    ng = repository.source_by_key_for_import(session, user, "financial_launches")
    billing = repository.source_by_key_for_import(session, user, "billing_invoices")
    budget = repository.source_by_key_for_import(session, user, "budget")
    if ng is None or billing is None or budget is None:
        return "PENDING_INPUTS", None
    ng_history = repository.import_history(session, user, ng.id, 1)
    billing_history = repository.import_history(session, user, billing.id, 1)
    budget_history = repository.import_history(session, user, budget.id, 100)
    if not ng_history or not billing_history or not budget_history:
        return "PENDING_INPUTS", None
    ng_execution = ng_history[0][0]
    billing_execution = billing_history[0][0]
    if ng_execution.status not in (
        "SUCCEEDED",
        "PARTIAL",
    ) or billing_execution.status not in ("SUCCEEDED", "PARTIAL"):
        return "PENDING_INPUTS", None
    review = repository.successful_review(session, user, ng.id, ng_execution.id)
    if review is None:
        return "PENDING_INPUTS", None
    latest_budgets: dict[str, ImportProfileExecution] = {}
    for execution, snapshot in budget_history:
        latest_budgets.setdefault(snapshot.original_filename, execution)
    if not latest_budgets or any(
        execution.status != ProfileExecutionStatus.SUCCEEDED
        for execution in latest_budgets.values()
    ):
        return "PENDING_INPUTS", None
    request = NormalizationRequest(
        ng_source_id=ng.id,
        review_run_id=review.id,
        billing_source_id=billing.id,
        billing_execution_id=billing_execution.id,
        budgets=[
            BudgetInput(source_id=budget.id, execution_id=execution.id)
            for execution in latest_budgets.values()
        ],
    )
    try:
        summary = dataset_summary(session, user, ng.id, review.id)
        run = financial_repository.normalize(
            session, user, request, summary.dataset_revision, summary.as_of
        )
        return "UPDATED", run.id
    except Exception as error:
        session.rollback()
        logger.warning("TON readiness refresh failed error=%s", type(error).__name__)
        return "FAILED", None


def upload_client_source(
    session: Session,
    user: User,
    key: str,
    stream: BinaryIO,
    filename: str,
    media_type: str,
    store: FileStore,
) -> ClientImportView:
    _, _, expected_format = _contract(key)
    accessible = repository.source_by_key_for_import(session, user, key)
    if accessible is None and not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Financial source not available")
    if accessible is not None and accessible.status != SourceStatus.ACTIVE:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Financial source is not active")
    validated = validate_upload(stream, filename, media_type)
    if validated.format != expected_format:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Unsupported format for this source"
        )
    if len(validated.content) > MAX_UPLOAD_BYTES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Financial file is too large")
    try:
        profile_key = (
            NgFinancialExportParser().parse(validated.content, UUID(int=0)).profile_key
            if key == "financial_launches"
            else identify_profile(validated.content, validated.format)
        )
    except OnyxError:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "This file does not match a recognized format for this source",
        ) from None
    source_id = _source_for_upload(session, user, key)
    sources.get_source(session, user, source_id, Permission.IMPORT_TON_SOURCES)
    if key == "financial_launches":
        profile = import_profiles.create_ng_profile_v1(
            session, user, source_id, Permission.IMPORT_TON_SOURCES
        )
    else:
        profile = operational_import.create_operational_profile(
            session, user, source_id, profile_key, Permission.IMPORT_TON_SOURCES
        )
    session.commit()
    snapshot = import_file(
        session,
        user,
        source_id,
        BytesIO(validated.content),
        filename,
        media_type,
        store,
    )
    if key == "financial_launches":
        execution = execute_ng_profile(
            session, user, source_id, snapshot.id, profile.id, store
        )
        if execution.status in (
            ProfileExecutionStatus.SUCCEEDED,
            ProfileExecutionStatus.PARTIAL,
        ):
            review = execute_review(session, user, source_id, execution.id)
            summary = dataset_summary(session, user, source_id, review.id)
        else:
            summary = None
    else:
        execution = execute_operational_profile(
            session, user, source_id, snapshot.id, profile.id, store
        )
        summary = None
    stored = repository.import_detail(session, user, source_id, execution.id)
    assert stored is not None
    view = _view(*stored, key)
    if summary is not None:
        view.needs_review = summary.total_records - summary.downstream_safe_records
        view.available_for_analysis = summary.downstream_safe_records
    view.readiness_status, view.readiness_run_id = _refresh_readiness(session, user)
    return view
