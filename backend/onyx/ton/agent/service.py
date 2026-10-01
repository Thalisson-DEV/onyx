"""Bounded TON queries and report publication through the shared chat runtime."""

from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import client_import, dre, financial_review, sources
from onyx.db.ton.acl import assert_global
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.models import ImportExecutionSummary, SourceToolStatus, ToolQuery
from onyx.ton.client_import.service import list_client_sources
from onyx.ton.dre.models import DreScope
from onyx.ton.financial_review import service as review_service
from onyx.ton.sources.models import SourceView


def query_domain(
    session: Session, user: User, operation: str, query: ToolQuery
) -> BaseModel | list[BaseModel]:
    permission = (
        Permission.READ_TON_OCCURRENCES
        if operation in ("ton_list_findings", "ton_get_finding")
        else Permission.READ_TON_SOURCES
    )
    assert_global(user, permission=permission)
    if operation in (
        "ton_analyze_closing",
        "ton_generate_closing_report",
        "ton_generate_executive_brief",
    ):
        from onyx.db.ton.closing import execute_closing, inspect_closing
        from onyx.ton.agent.closing_models import ClosingRequest, PublicationLink

        request = ClosingRequest(
            request_id=query.request_id or uuid4(),
            normalization_run_id=query.normalization_run_id,
            structure_version_id=query.structure_version_id,
            period=query.period,
            unit_id=query.unit_id,
            executive=operation == "ton_generate_executive_brief",
        )
        if operation == "ton_analyze_closing":
            return inspect_closing(session, user, request)
        result = execute_closing(session, user, request)
        return PublicationLink(
            run_id=result.run_id,
            revision_id=result.revision_id,
            status=result.status,
            period=result.output.period,
            data_context=result.output.data_context,
            executive_brief=result.output.executive_brief,
            report_url=result.report_url,
            download_url=result.download_url,
        )
    if operation in (
        "ton_get_billing_summary",
        "ton_get_budget_summary",
        "ton_get_reconciliation_summary",
    ):
        from onyx.db.ton.agent import finance_summary

        return finance_summary(session, user, query)
    if operation == "ton_list_sources":
        return [
            item.model_copy(update={"history": []})
            for item in list_client_sources(session, user)
        ]
    if operation == "ton_get_source_status":
        if query.source_id is None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Informe source_id")
        source = sources.get_source(session, user, query.source_id)
        history = client_import.import_history(session, user, source.id, query.limit)
        return SourceToolStatus(
            source=SourceView.model_validate(source),
            last_successful_import_at=client_import.last_successful_at(
                session, user, source.id
            ),
            executions=[
                ImportExecutionSummary(
                    execution_id=execution.id,
                    snapshot_id=snapshot.id,
                    status=execution.status.value,
                    finished_at=execution.finished_at,
                    imported_records=execution.statistics.get("detail_records_parsed"),
                    rejected_records=execution.statistics.get("records_rejected"),
                    warnings=execution.statistics.get("warnings"),
                    errors=execution.statistics.get("errors"),
                )
                for execution, snapshot in history
            ],
            review_run_ids=[
                run.id
                for run in financial_review.list_review_runs(
                    session, user, source.id, query.limit, 0
                )
            ],
        )
    if operation == "ton_list_findings":
        return list(
            review_service.list_findings(
                session,
                user,
                financial_review.FindingFilters(
                    source_id=query.source_id,
                    review_run_id=query.review_run_id,
                    blocking=query.blocking,
                ),
                query.limit,
                query.offset,
            )
        )
    if operation == "ton_get_finding":
        if query.finding_id is None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Informe finding_id")
        detail = review_service.get_finding(session, user, query.finding_id)
        evidence = review_service.list_evidence(
            session, user, query.finding_id, query.limit, query.offset
        )
        return [detail, *evidence]
    if operation == "ton_get_financial_review_summary":
        if query.source_id is None or query.review_run_id is None:
            raise OnyxError(
                OnyxErrorCode.INVALID_INPUT, "Informe source_id e review_run_id"
            )
        return review_service.dataset_summary(
            session, user, query.source_id, query.review_run_id, None
        )
    if operation == "ton_get_dre_readiness":
        if (
            query.normalization_run_id is None
            or query.structure_version_id is None
            or query.period is None
        ):
            raise OnyxError(
                OnyxErrorCode.INVALID_INPUT,
                "Informe normalization_run_id, structure_version_id e period",
            )
        return dre.readiness(
            session,
            user,
            DreScope(
                normalization_run_id=query.normalization_run_id,
                structure_version_id=query.structure_version_id,
                period=query.period,
                unit_id=query.unit_id,
            ),
        )
    if operation == "ton_get_dre_result":
        if query.run_id is None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Informe run_id")
        run = dre.get_calculation(session, user, query.run_id)
        if run.status != "READY":
            return run
        current = dre.readiness(session, user, run.scope)
        if current.status != "READY":
            return current
        return [
            run,
            *dre.list_result_lines(session, user, run.id, query.limit, query.offset),
        ]
    if operation == "ton_get_financial_context":
        from onyx.db.ton.agent import financial_context

        return financial_context(session, user, query.limit, query.offset)
    raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Ferramenta TON desconhecida")
