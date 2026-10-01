"""Shared closing execution and immutable publication on existing TON models."""

import calendar
import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.db.ton import (
    acl,
    analysis_runs,
    analysis_steps,
    dre,
    financial_domain,
    financial_review,
    reports,
    sources,
)
from onyx.db.ton.agent import financial_context
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.canonical import compute_content_hash
from onyx.db.ton.enums import (
    AnalysisRunStatus,
    AnalysisSpecialist,
    AnalysisStepBlockedReason,
    AnalysisStepCode,
    AnalysisStepStatus,
    AnalysisTrigger,
    RuleDomain,
    TonAuditResourceKind,
    TonReportType,
    TonSharePermission,
)
from onyx.db.ton.interpretations import is_interpretation_final
from onyx.db.ton.models import (
    AnalysisRun,
    BusinessUnit,
    BusinessUnit__UserGroup,
    Contract__UserGroup,
    Finding,
    ImportProfileExecution,
    Occurrence,
    ReviewRun,
    RuleVersion,
    Source__UserGroup,
    SourceSnapshot,
    TonReport__UserGroup,
    TonReportRevision__Finding,
    TonReportRevision__SourceSnapshot,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.closing_models import (
    AnalyzedClosing,
    ClosingOutput,
    ClosingRequest,
    PublishedClosing,
    SpecialistOutcome,
)
from onyx.ton.agent.labels import business_label, humanize
from onyx.ton.agent.policy import SYNTHETIC_DATA_NOTICE, uses_synthetic_demo_data
from onyx.ton.agent.registry import SPECIALISTS
from onyx.ton.client_import.service import list_client_sources
from onyx.ton.dre.models import DreScope
from onyx.ton.financial_review import service as review_service
from onyx.utils.audit import AuditAction, AuditOutcome

EXECUTOR_VERSION = "ton-closing-1"


def inspect_closing(
    session: Session, user: User, request: ClosingRequest
) -> ClosingOutput:
    acl.assert_global(user, permission=Permission.READ_TON_SOURCES)
    acl.assert_global(user, permission=Permission.READ_TON_OCCURRENCES)
    context = financial_context(session, user, 10, 0)
    base = next(
        (
            item
            for item in context.bases
            if request.normalization_run_id is None
            or item.normalization_run_id == request.normalization_run_id
        ),
        None,
    )
    if request.normalization_run_id is not None and base is None:
        # Resolve explicit IDs through the authoritative ACL before returning any detail.
        financial_domain.get_run(session, user, request.normalization_run_id)
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "Base fora da página disponível. Consulte o contexto financeiro.",
        )
    now = datetime.datetime.now(datetime.UTC)
    period = request.period or (
        max(base.periods) if base and base.periods else now.date().replace(day=1)
    )
    if period.day != 1:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "O período deve começar no primeiro dia do mês.",
        )
    version_id = request.structure_version_id or (
        context.structure_version_ids[0] if context.structure_version_ids else None
    )
    source_views = list_client_sources(session, user)
    source_summaries = [
        dict(
            key=item.key,
            name=item.name,
            source_id=str(item.source_id) if item.source_id else None,
            latest_execution_id=str(item.latest.id) if item.latest else None,
            status=business_label(item.status),
            last_success_at=item.last_success_at.isoformat()
            if item.last_success_at
            else None,
            acquisition="Importação manual",
            direct_integration="Aguardando acesso e configuração"
            if item.key == "financial_launches"
            else "Não configurada",
            review_policy="Revisão financeira NG"
            if item.key == "financial_launches"
            else "Validação pelo perfil de importação",
        )
        for item in source_views
    ]
    outcomes: list[SpecialistOutcome] = []
    findings: list[dict[str, object]] = []
    blockers: dict[str, int] = {}
    dre_status = "Não verificada"
    auditor = SpecialistOutcome(
        key="AUDITOR",
        status="Bloqueado",
        reason="Nenhuma base normalizada autorizada disponível.",
    )
    if base:
        summary = review_service.dataset_summary(
            session, user, base.source_id, base.review_run_id, None
        )
        page = review_service.list_findings(
            session,
            user,
            financial_review.FindingFilters(
                source_id=base.source_id, review_run_id=base.review_run_id
            ),
            10,
            0,
        )
        for finding in sorted(
            page, key=lambda item: (not item.blocking, item.detected_at)
        ):
            detail = review_service.get_finding(session, user, finding.id)
            evidence = review_service.list_evidence(session, user, finding.id, 3, 0)
            findings.append(
                humanize(
                    dict(
                        id=str(detail.id),
                        occurrence_id=str(detail.occurrence_id),
                        title=detail.explanation,
                        blocking=detail.blocking,
                        category=detail.category,
                        status=detail.occurrence_status.value,
                        recommendations=[
                            item.explanation for item in detail.recommendations[:3]
                        ],
                        evidence=[item.model_dump(mode="json") for item in evidence],
                    )
                )
            )
        auditor = SpecialistOutcome(
            key="AUDITOR",
            status="Operacional",
            reason="Revisão determinística e evidências consultadas; nenhuma aprovação automática.",
            facts=humanize(summary.model_dump(mode="json")),
            limitations=[
                "Achados da revisão inteira. A página contém até dez achados; não representa o total.",
                "A revisão financeira NG não se aplica ao faturamento e ao orçamento.",
            ],
            actions=[
                "Revisar as pendências com suas evidências no espaço de revisão financeira."
            ],
        )
    outcomes.append(auditor)
    cfo = SpecialistOutcome(
        key="CFO",
        status="Bloqueado",
        reason="Base normalizada ou estrutura DRE ausente.",
    )
    if base and version_id:
        try:
            scope = DreScope(
                normalization_run_id=base.normalization_run_id,
                structure_version_id=version_id,
                period=period,
                unit_id=request.unit_id,
            )
            readiness = dre.readiness(session, user, scope)
            finance = financial_domain.readiness(
                session, user, base.normalization_run_id, period, request.unit_id
            )
            blockers = {
                business_label(code): count
                for code, count in readiness.blockers.items()
            }
            dre_status = business_label(readiness.status)
            stored = [
                item.model_dump(mode="json")
                for item in base.stored_dre_results
                if item.period == period
                and item.unit_id == request.unit_id
                and item.structure_version_id == version_id
            ]
            cfo = SpecialistOutcome(
                key="CFO",
                status="Operacional" if readiness.status == "READY" else "Parcial",
                reason="Prontidão, faturamento, orçamento e conciliação consultados.",
                facts=humanize(
                    dict(
                        readiness=readiness.model_dump(mode="json"),
                        finance=finance.model_dump(mode="json"),
                        stored_results=stored,
                    )
                ),
                limitations=[
                    "Nenhuma margem, previsão ou DRE foi calculada nesta análise.",
                    "Uma base pronta exige um resultado persistido para apresentar valores de DRE.",
                ],
                actions=[
                    "Resolver os bloqueios no espaço de Prontidão financeira; aprovações exigem uma pessoa."
                ]
                if blockers
                else ["Consultar a DRE persistida para este período e escopo."],
            )
        except OnyxError as error:
            if error.error_code not in (
                OnyxErrorCode.ADMIN_ONLY,
                OnyxErrorCode.INSUFFICIENT_PERMISSIONS,
                OnyxErrorCode.NOT_FOUND,
                OnyxErrorCode.CONFLICT,
            ):
                raise
            cfo = SpecialistOutcome(
                key="CFO",
                status="Bloqueado",
                reason="Escopo financeiro indisponível ou sem autorização. Selecione uma unidade autorizada.",
            )
    outcomes.append(cfo)
    brief = {
        "RESULTADO": f"Análise preliminar do período {period:%m/%Y}. DRE: {dre_status.lower()}.",
        "PROBLEMA": "; ".join(blockers) if blockers else cfo.reason,
        "IMPACTO": "Não quantificado. Nenhum valor financeiro foi estimado.",
        "CAUSA / HIPÓTESE": "Bloqueios obtidos das regras determinísticas; causas operacionais exigem confirmação humana.",
        "AÇÃO": "Consultar as evidências e resolver as decisões pendentes em Prontidão financeira.",
    }
    outcomes.append(
        SpecialistOutcome(
            key="CEO",
            status="Operacional",
            reason="Síntese dos resultados disponíveis do AUDITOR e CFO.",
            facts=brief,
            limitations=[
                "Síntese determinística; nenhuma hipótese foi registrada como evidência."
            ],
        )
    )
    outcomes.extend(
        SpecialistOutcome(
            key=definition.key,
            status="Bloqueado",
            reason="Capacidade ainda não disponível: "
            + ", ".join(definition.required_capabilities)
            + ".",
        )
        for definition in SPECIALISTS
        if definition.key not in {"CFO", "AUDITOR", "CEO"}
    )
    for outcome in outcomes:
        outcome.name = next(
            definition.name
            for definition in SPECIALISTS
            if definition.key == outcome.key
        )
    return ClosingOutput(
        period=period,
        scope="Unidade selecionada" if request.unit_id else "Consolidado",
        normalization_run_id=base.normalization_run_id if base else None,
        structure_version_id=version_id,
        unit_id=request.unit_id,
        data_context=SYNTHETIC_DATA_NOTICE
        if uses_synthetic_demo_data()
        else "Dados das fontes autorizadas. Confira o período e a data de importação.",
        sources=source_summaries,
        specialists=outcomes,
        findings=findings,
        findings_scope="Revisão financeira inteira da base selecionada; não limitada ao mês do fechamento.",
        findings_may_have_more=len(findings) == 10,
        dre_status=dre_status,
        blockers=blockers,
        executive_brief=brief,
        generated_at=now,
    )


def _input_rows(
    session: Session, user: User, output: ClosingOutput, *, publication: bool = True
) -> tuple[list[SourceSnapshot], list[Finding]]:
    snapshot_ids: set[UUID] = set()
    for item in output.sources:
        if item["source_id"]:
            source_id = UUID(str(item["source_id"]))
            sources.get_source(session, user, source_id)
            latest = (
                session.get(
                    ImportProfileExecution, UUID(str(item["latest_execution_id"]))
                )
                if item["latest_execution_id"]
                else None
            )
            if latest and latest.source_id == source_id:
                snapshot_ids.add(latest.snapshot_id)
    if output.normalization_run_id:
        run = financial_domain.get_run(session, user, output.normalization_run_id)
        review = session.get(ReviewRun, run.review_run_id)
        assert review is not None
        snapshot_ids.add(review.snapshot_id)
        for execution_id in [
            run.billing_execution_id,
            *[UUID(value) for value in run.budget_execution_ids],
        ]:
            execution = session.get(ImportProfileExecution, execution_id)
            assert execution is not None
            snapshot_ids.add(execution.snapshot_id)
    findings = list(
        session.scalars(
            sa.select(Finding).where(
                Finding.id.in_([UUID(str(item["id"])) for item in output.findings])
            )
        )
    )
    if publication and any(
        not is_interpretation_final(finding) for finding in findings
    ):
        raise OnyxError(
            OnyxErrorCode.CONFLICT,
            "A interpretação de um achado ainda está pendente. Conclua a revisão antes de publicar.",
        )
    return list(
        session.scalars(
            sa.select(SourceSnapshot).where(SourceSnapshot.id.in_(snapshot_ids))
        )
    ), findings


def _publication_groups(
    session: Session,
    user: User,
    snapshots: list[SourceSnapshot],
    findings: list[Finding],
    output: ClosingOutput,
) -> set[int]:
    if acl.is_ton_administrator(user):
        return set()
    groups = acl.fetch_user_group_ids(session, user)
    source_ids = {
        snapshot.source_id for snapshot in snapshots if snapshot.source_id is not None
    } | {UUID(str(item["source_id"])) for item in output.sources if item["source_id"]}
    for source_id in source_ids:
        groups &= set(
            session.scalars(
                sa.select(Source__UserGroup.user_group_id).where(
                    Source__UserGroup.source_id == source_id
                )
            )
        )
    for finding in findings:
        groups &= acl.occurrence_group_ids(session, finding.occurrence_id)
        occurrence = session.get(Occurrence, finding.occurrence_id)
        assert occurrence is not None
        if occurrence.business_unit_id:
            groups &= set(
                session.scalars(
                    sa.select(BusinessUnit__UserGroup.user_group_id).where(
                        BusinessUnit__UserGroup.business_unit_id
                        == occurrence.business_unit_id
                    )
                )
            )
        if occurrence.contract_id:
            groups &= set(
                session.scalars(
                    sa.select(Contract__UserGroup.user_group_id).where(
                        Contract__UserGroup.contract_id == occurrence.contract_id
                    )
                )
            )
    if output.unit_id:
        groups &= set(
            session.scalars(
                sa.select(BusinessUnit__UserGroup.user_group_id).where(
                    BusinessUnit__UserGroup.business_unit_id == output.unit_id
                )
            )
        )
    if not groups:
        raise OnyxError(
            OnyxErrorCode.INSUFFICIENT_PERMISSIONS,
            "Nenhum grupo autorizado pode receber todos os dados deste relatório.",
        )
    return groups


def analyze_closing(
    session: Session, user: User, request: ClosingRequest
) -> AnalyzedClosing:
    output = inspect_closing(session, user, request)
    snapshots, _ = _input_rows(session, user, output, publication=False)
    identity = compute_content_hash(
        dict(
            user=str(user.id),
            request=request.model_dump(mode="json"),
            output=output.model_dump(mode="json"),
        )
    )
    run, steps, status = _record_analysis(
        session, user, output, snapshots, identity, AnalysisTrigger.INTERACTIVE, None
    )
    session.commit()
    return AnalyzedClosing(
        run_id=run.id, status=business_label(status.value), output=output, steps=steps
    )


def execute_closing(
    session: Session,
    user: User,
    request: ClosingRequest,
    *,
    trigger: AnalysisTrigger = AnalysisTrigger.INTERACTIVE,
    routine_code: str | None = None,
) -> PublishedClosing:
    acl.assert_global(user, permission=Permission.MANAGE_TON_REPORTS)
    acl.assert_global(user, permission=Permission.READ_TON_REPORTS)
    # The transaction lock serializes retries before reading inputs or publishing.
    identity = compute_content_hash(
        dict(
            user=str(user.id),
            request=request.model_dump(mode="json"),
            trigger=trigger.value,
            routine=routine_code,
        )
    )
    session.execute(
        sa.text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(identity[:15], 16)}
    )
    existing = session.scalar(
        sa.select(reports.TonReport).where(
            reports.TonReport.code == "closing-" + identity
        )
    )
    if existing:
        acl.get_report_for_user(session, user, existing.id)
        revision = reports.latest_revision(session, existing.id)
        assert revision is not None
        return read_publication(session, user, revision.id)
    output = inspect_closing(session, user, request)
    snapshots, findings = _input_rows(session, user, output)
    groups = _publication_groups(session, user, snapshots, findings, output)
    run, step_details, status = _record_analysis(
        session, user, output, snapshots, identity, trigger, routine_code
    )
    title = "Resumo executivo" if request.executive else "Pendências do fechamento"
    report = reports.create_report__no_commit(
        session,
        code="closing-" + identity,
        report_type=TonReportType.EXECUTIVE
        if request.executive
        else TonReportType.MONTHLY_CLOSE,
        title=title,
        business_unit_id=output.unit_id,
        period_start=run.period_start,
        period_end=run.period_end,
        created_by=user.id,
    )
    # Creation grants only groups that can read every pinned input and scope.
    session.add_all(
        [
            TonReport__UserGroup(
                report_id=report.id,
                user_group_id=group_id,
                permission=TonSharePermission.EDITOR,
            )
            for group_id in groups
        ]
    )
    session.flush()
    acl.assert_can_manage_report(session, user=user, report=report)
    revision = reports.publish_report_revision__no_commit(
        session,
        report=report,
        body=dict(
            output=output.model_dump(mode="json"),
            run_id=str(run.id),
            status=business_label(status.value),
            steps=step_details,
            routine_code=routine_code,
        ),
        generator_version=EXECUTOR_VERSION,
        generated_at=output.generated_at,
        generated_by=user.id,
        analysis_runs=[run],
        findings=findings,
        occurrences=list(
            session.scalars(
                sa.select(Occurrence).where(
                    Occurrence.id.in_({finding.occurrence_id for finding in findings})
                )
            )
        ),
        rule_versions=list(
            session.scalars(
                sa.select(RuleVersion).where(
                    RuleVersion.id.in_(
                        {finding.rule_version_id for finding in findings}
                    )
                )
            )
        ),
        source_snapshots=snapshots,
    )
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_REPORT_GENERATE,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.REPORT_REVISION,
        resource_id=revision.id,
        extra={"run_id": str(run.id), "routine_code": routine_code},
    )
    session.commit()
    return read_publication(session, user, revision.id)


def read_publication(
    session: Session, user: User, revision_id: UUID
) -> PublishedClosing:
    revision = acl.get_report_revision_for_user(session, user, revision_id)
    acl.assert_global(user, permission=Permission.READ_TON_SOURCES)
    acl.assert_global(user, permission=Permission.READ_TON_OCCURRENCES)
    report = acl.get_report_for_user(session, user, revision.report_id)
    if (
        report.business_unit_id is not None
        and session.scalar(
            sa.select(BusinessUnit.id).where(
                BusinessUnit.id == report.business_unit_id,
                acl.business_unit_visible_clause(user),
            )
        )
        is None
    ):
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, "Escopo indisponível.")
    snapshots = session.scalars(
        sa.select(SourceSnapshot)
        .join(
            TonReportRevision__SourceSnapshot,
            TonReportRevision__SourceSnapshot.source_snapshot_id == SourceSnapshot.id,
        )
        .where(TonReportRevision__SourceSnapshot.report_revision_id == revision.id)
    )
    for snapshot in snapshots:
        if snapshot.source_id is not None:
            sources.get_source(session, user, snapshot.source_id)
    finding_ids = session.scalars(
        sa.select(TonReportRevision__Finding.finding_id).where(
            TonReportRevision__Finding.report_revision_id == revision.id
        )
    )
    for finding_id in finding_ids:
        review_service.get_finding(session, user, finding_id)
    if not reports.verify_revision_hash(revision):
        raise OnyxError(
            OnyxErrorCode.CONFLICT,
            "O relatório não passou na verificação de integridade.",
        )
    body = revision.canonical_payload["body"]
    if revision.generator_version != EXECUTOR_VERSION:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "Formato de relatório não suportado nesta tela.",
        )
    return PublishedClosing(
        run_id=body["run_id"],
        report_id=revision.report_id,
        revision_id=revision.id,
        status=body["status"],
        output=ClosingOutput.model_validate(body["output"]),
        steps=body["steps"],
        routine_code=body.get("routine_code"),
        report_url=f"/ton/controladoria/reports/{revision.id}",
        download_url=f"/api/ton/agent/reports/{revision.id}/download",
    )


def list_publications(
    session: Session, user: User, limit: int = 10
) -> list[PublishedClosing]:
    acl.assert_global(user, permission=Permission.READ_TON_REPORTS)
    revisions = session.scalars(
        sa.select(reports.TonReportRevision)
        .where(
            acl.report_revision_visible_clause(user),
            reports.TonReportRevision.generator_version == EXECUTOR_VERSION,
        )
        .order_by(
            reports.TonReportRevision.generated_at.desc(), reports.TonReportRevision.id
        )
        .limit(limit)
    )
    return [read_publication(session, user, revision.id) for revision in revisions]


def _record_analysis(
    session: Session,
    user: User,
    output: ClosingOutput,
    snapshots: list[SourceSnapshot],
    identity: str,
    trigger: AnalysisTrigger,
    routine_code: str | None,
) -> tuple[AnalysisRun, list[dict[str, str | None]], AnalysisRunStatus]:
    run, _ = analysis_runs.get_or_create_analysis_run__no_commit(
        session,
        idempotency_key=identity,
        trigger=trigger,
        specialist=AnalysisSpecialist.CEO,
        domain=RuleDomain.FINANCIAL,
        period_start=output.period,
        period_end=output.period.replace(
            day=calendar.monthrange(output.period.year, output.period.month)[1]
        ),
        executor_version=EXECUTOR_VERSION,
        business_unit_id=output.unit_id,
        triggered_by_user_id=user.id,
        routine_code=routine_code,
    )
    for snapshot in snapshots:
        analysis_runs.attach_source_snapshot__no_commit(
            session, analysis_run=run, source_snapshot=snapshot
        )
    step_details: list[dict[str, str | None]] = []
    for domain, specialist in [
        (RuleDomain.FINANCIAL, "CFO"),
        (RuleDomain.AUDIT, "AUDITOR"),
        (RuleDomain.QUALITY, "CEO"),
    ]:
        outcome = next(item for item in output.specialists if item.key == specialist)
        steps = {
            code: analysis_steps.create_analysis_step__no_commit(
                session,
                analysis_run=run,
                step_code=code,
                domain=domain,
                business_unit_id=output.unit_id,
            )
            for code in analysis_steps.STEP_ORDER
        }
        for code, step in steps.items():
            reason: str | None = None
            if step.status == AnalysisStepStatus.BLOCKED:
                reason = (
                    business_label(step.blocked_reason.value)
                    if step.blocked_reason
                    else outcome.reason
                )
            elif code == AnalysisStepCode.BASE_VALIDATION and (
                outcome.status == "Bloqueado"
                or (specialist == "CFO" and output.dre_status != "Pronta")
            ):
                analysis_steps.fail_step__no_commit(
                    session,
                    step=step,
                    blocked_reason=AnalysisStepBlockedReason.AWAITING_HUMAN_DECISION
                    if outcome.status != "Bloqueado"
                    else AnalysisStepBlockedReason.MISSING_SOURCE,
                )
                reason = outcome.reason + " Publicação financeira bloqueada."
            elif code == AnalysisStepCode.QUANTIFICATION:
                analysis_steps.skip_step__no_commit(session, step=step)
                reason = "Impacto não quantificado; a rotina não calcula uma nova DRE."
            elif (
                specialist in ("AUDITOR", "CEO")
                and code == AnalysisStepCode.CHAIN_RECONCILIATION
            ):
                analysis_steps.skip_step__no_commit(session, step=step)
                reason = "Conciliação pertence ao CFO; este especialista usa os resultados disponíveis."
            else:
                analysis_steps.pass_step__no_commit(session, step=step)
            step_details.append(
                dict(
                    specialist=specialist,
                    code=business_label(code.value),
                    status=business_label(step.status.value),
                    reason=reason,
                )
            )
    status = analysis_runs.finalize_analysis_run__no_commit(session, analysis_run=run)
    return run, step_details, status
