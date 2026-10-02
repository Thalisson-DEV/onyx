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


def query_domain(  # noqa: C901 - one flat dispatch per TON tool
    session: Session, user: User, operation: str, query: ToolQuery
) -> BaseModel | list[BaseModel]:
    permission = (
        Permission.READ_TON_OCCURRENCES
        if operation
        in (
            "ton_list_findings",
            "ton_get_finding",
            "ton_list_occurrences",
            "ton_get_occurrence",
            "ton_list_overdue_actions",
        )
        else Permission.READ_TON_SOURCES
    )
    assert_global(user, permission=permission)
    if operation in (
        "ton_get_readiness_evidence",
        "ton_list_occurrences",
        "ton_get_occurrence",
        "ton_list_overdue_actions",
    ):
        return _supporting_evidence(session, user, operation, query)
    if operation in (
        "ton_analyze_closing",
        "ton_generate_closing_report",
        "ton_generate_executive_brief",
    ):
        from onyx.db.ton.closing import analyze_closing, execute_closing
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
            return analyze_closing(session, user, request)
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
    if operation == "ton_get_recent_changes":
        return _recent_changes(session, user, query)
    raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Ferramenta TON desconhecida")


def _recent_changes(session: Session, user: User, query: ToolQuery) -> BaseModel:
    from onyx.db.ton.agent import financial_context
    from onyx.db.ton.decision_loop import (
        decision_log,
        readiness_changes,
        required_action,
    )
    from onyx.ton.financial_domain.readiness_models import (
        RecentChanges,
        RequiredAction,
    )

    run_id = query.normalization_run_id
    version_id = query.structure_version_id
    if run_id is None or version_id is None:
        context = financial_context(session, user, 1, 0)
        if not context.bases or not context.structure_version_ids:
            raise OnyxError(
                OnyxErrorCode.INVALID_INPUT,
                "Não há base normalizada ou estrutura de DRE autorizada.",
            )
        run_id = run_id or context.bases[0].normalization_run_id
        version_id = version_id or context.structure_version_ids[0]
    changes = readiness_changes(session, user, run_id, version_id, query.unit_id)
    latest = changes.periods[-1] if changes.periods else None
    return RecentChanges(
        changes=changes,
        decisions=decision_log(session, user, query.limit),
        required_actions=[
            RequiredAction(blocker=code, count=count, action=required_action(code))
            for code, count in (latest.blockers_after if latest else {}).items()
        ],
    )


def _supporting_evidence(
    session: Session, user: User, operation: str, query: ToolQuery
) -> BaseModel:
    if operation != "ton_get_readiness_evidence":
        from onyx.db.ton.agent_occurrences import query_occurrences

        return query_occurrences(session, user, operation, query)
    from onyx.db.ton import financial_readiness
    from onyx.ton.agent.labels import business_label

    if query.normalization_run_id is None or query.structure_version_id is None:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Informe a base e a estrutura DRE."
        )
    supported = financial_readiness.SUMMARY_BLOCKERS | {
        "UNMAPPED_UNIT",
        "UNMAPPED_ACCOUNT",
        "AMOUNT_BASIS_UNRESOLVED",
        "DRE_ACCOUNT_UNMAPPED",
        "DRE_MAPPING_PENDING_APPROVAL",
        "BUDGET_PERIOD_UNRESOLVED",
        "SOURCE_RECONCILIATION_UNRESOLVED",
        "SOURCE_RECONCILIATION_AMBIGUOUS",
    }
    blocker = next(
        (code for code in supported if query.blocker in (code, business_label(code))),
        None,
    )
    if blocker is None:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Informe um bloqueio obtido da prontidão."
        )
    return financial_readiness.list_blockers(
        session,
        user,
        query.normalization_run_id,
        query.structure_version_id,
        blocker,
        query.limit,
        query.offset,
        None,
        query.unit_id,
    )
