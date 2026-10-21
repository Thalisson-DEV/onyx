"""Occurrences from the chat's financial tests, and the daily R1 sweep.

The tests (``agent_investigations``) become versioned DRAFT rules ``TON-T1`` …
``TON-T10``. A registration re-runs the test on the server and records the
chosen hits through ``record_detection__no_commit``, so a case seen again is a
repeat of the same occurrence, never a duplicate, and the ledger keeps its
history.

Criticality uses the PAD-CTRL-001 bands as parameters the person approves on
the card (or when activating R1); they are stored with each finding and in the
R1 configuration, never as a constant here.
"""

import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import agent_investigations as inv
from onyx.db.ton.agent import financial_context
from onyx.db.ton.analysis_runs import get_or_create_analysis_run__no_commit
from onyx.db.ton.enums import (
    AnalysisRunStatus,
    AnalysisSpecialist,
    AnalysisTrigger,
    EvidenceConfidenceLevel,
    FindingKind,
    MissingDataBehavior,
    OccurrenceCriticality,
    OccurrenceLedgerKind,
    PostResolutionPolicy,
    RedactionLevel,
    RuleDomain,
    RuleKind,
    RuleProvenance,
)
from onyx.db.ton.financial_review import _share_new_occurrences
from onyx.db.ton.models import AnalysisRun, BusinessUnit, Occurrence, Rule, RuleVersion
from onyx.db.ton.occurrence_records import (
    add_note__no_commit,
    assign_responsible__no_commit,
)
from onyx.db.ton.occurrences import record_detection__no_commit
from onyx.db.ton.rule_versions import compute_definition_hash

EXECUTOR_VERSION = "ton-agent-ledger-1"

# Prompt Mestre §10 wording. The numbers are the PAD-CTRL-001 suggestion that a
# person approves per registration or per R1 activation.
SUGGESTED_BANDS = (Decimal("1.0"), Decimal("0.3"), Decimal("0.1"))

TEST_RULES: dict[str, tuple[str, str, AnalysisSpecialist]] = {
    "T1": (
        "Grupo zerado",
        "Conferir se o lançamento do mês foi feito ou se a linha deixou de existir de fato.",
        AnalysisSpecialist.CFO,
    ),
    "T2": (
        "Desvio de média móvel",
        "Explicar a causa do desvio ou corrigir o lançamento; no ciclo seguinte a natureza volta à faixa.",
        AnalysisSpecialist.CFO,
    ),
    "T3": (
        "Duplicidade",
        "Confirmar com o Financeiro se houve dois pagamentos; se sim, pedir estorno e anexar o comprovante.",
        AnalysisSpecialist.AUDITOR,
    ),
    "T4": (
        "Receita NG × notas fiscais",
        "Explicar a diferença (recebimento em outro mês, retenção, nota sem lançamento) ou corrigir o NG.",
        AnalysisSpecialist.CFO,
    ),
    "T6": (
        "Sinal invertido",
        "Confirmar se é estorno legítimo ou erro de natureza; corrigir a natureza se for erro.",
        AnalysisSpecialist.CFO,
    ),
    "T8": (
        "Fornecedor × unidade",
        "Confirmar se o fornecedor atende de fato a unidade e se o rateio está certo.",
        AnalysisSpecialist.AUDITOR,
    ),
    "T9": (
        "Competência retroativa",
        "Confirmar o motivo do atraso e se a DRE deve refletir a competência original.",
        AnalysisSpecialist.AUDITOR,
    ),
    "T10": (
        "Evento não recorrente",
        "Explicar o evento e decidir se fica no resultado do mês ou recebe tratamento.",
        AnalysisSpecialist.CFO,
    ),
}


def _rule_code(test: str) -> str:
    return f"TON-{test}"


def _version_fields(test: str) -> dict[str, Any]:
    title, criterion, _ = TEST_RULES[test]
    return {
        "version": 1,
        "title": f"{test} {title}",
        "description": f"Teste {test} do Prompt Mestre rodado pelo TON sobre a base do NG. {criterion}",
        "executor_key": f"ton.agent_investigations.{test}",
        "parameters": {
            "limites": "parâmetros de cada execução, gravados no achado",
            "verificacao": criterion,
        },
        "applicability": {"source_profile": "ng_financial_export"},
        "provenance": RuleProvenance.PROMPT_MESTRE_V2,
        "source_reference": f"Prompt Mestre v2 §8 {test}",
        "missing_data_behavior": MissingDataBehavior.SKIP_WITH_NOTE,
        "evidence_requirements": {"lineage": ["parsed_source_record"]},
        "min_confidence_level": EvidenceConfidenceLevel.B,
        "severity_mapping": {
            "regua": "PAD-CTRL-001",
            "faixas": "aprovadas a cada registro ou na ativação do R1",
        },
        "identity_components": ["rule_code", "source_record_key"],
        "post_resolution_policy": PostResolutionPolicy.REOPEN_SAME_OCCURRENCE,
    }


def register_test_rules__no_commit(
    session: Session,
) -> dict[str, tuple[Rule, RuleVersion]]:
    """The DRAFT rules behind the tests; inserts what is missing."""
    session.execute(
        pg_insert(Rule)
        .values(
            [
                {
                    "id": uuid4(),
                    "code": _rule_code(test),
                    "domain": RuleDomain.FINANCIAL,
                    "kind": RuleKind.DETECTION,
                }
                for test in TEST_RULES
            ]
        )
        .on_conflict_do_nothing(index_elements=["code"])
    )
    rules = {
        rule.code: rule
        for rule in session.scalars(
            sa.select(Rule).where(Rule.code.in_([_rule_code(test) for test in TEST_RULES]))
        )
    }
    rows = []
    for test in TEST_RULES:
        rule = rules[_rule_code(test)]
        fields = _version_fields(test)
        transient = RuleVersion(rule_id=rule.id, **fields)
        rows.append(
            {
                "id": uuid4(),
                "rule_id": rule.id,
                "definition_hash": compute_definition_hash(transient, rule_code=rule.code),
                **fields,
            }
        )
    session.execute(
        pg_insert(RuleVersion)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_ton_rule_version_rule_version")
    )
    versions = {
        version.rule_id: version
        for version in session.scalars(
            sa.select(RuleVersion).where(
                RuleVersion.rule_id.in_([rule.id for rule in rules.values()]),
                RuleVersion.version == 1,
            )
        )
    }
    return {
        test: (rules[_rule_code(test)], versions[rules[_rule_code(test)].id])
        for test in TEST_RULES
    }


def suggest_criticality(
    impact: Decimal, revenue: Decimal, bands: tuple[Decimal, Decimal, Decimal]
) -> tuple[OccurrenceCriticality, Decimal | None]:
    """Band of the impact as a share of the unit's (or company's) revenue."""
    if not revenue:
        return OccurrenceCriticality.MONITORING, None
    share = impact / revenue * 100
    if share >= bands[0]:
        return OccurrenceCriticality.CRITICAL, share
    if share >= bands[1]:
        return OccurrenceCriticality.HIGH, share
    if share >= bands[2]:
        return OccurrenceCriticality.MEDIUM, share
    return OccurrenceCriticality.MONITORING, share


CRITICALITY_TEXT = {
    OccurrenceCriticality.CRITICAL: "Crítico",
    OccurrenceCriticality.HIGH: "Alto",
    OccurrenceCriticality.MEDIUM: "Médio",
    OccurrenceCriticality.MONITORING: "Monitoramento",
}


def _revenue_base(
    session: Session,
    user: User,
    cache: dict[tuple[datetime.date | None, str | None], Decimal],
    period: datetime.date | None,
    unit: str | None,
    operational: bool,
) -> tuple[Decimal, str]:
    """Revenue a case is measured against (Prompt Mestre §10: unit or company).

    Only an operational unit with revenue in the month is measured on its
    own; cost centres (Administração Central, mútuos) and units in
    implantation are measured on the consolidated."""

    def revenue(name: str | None) -> Decimal:
        key = (period, name)
        if key not in cache:
            cache[key] = inv.unit_revenue(session, user, period, name) if period else Decimal(0)
        return cache[key]

    if unit is None:
        return revenue(None), "consolidado"
    if not operational:
        return revenue(None), "consolidado (unidade não operacional)"
    own = revenue(unit)
    if not own:
        return revenue(None), "consolidado (unidade sem receita no mês)"
    return own, f"receita de {unit}"


class PlannedCase(BaseModel):
    key: str
    title: str
    unit: str | None
    unit_id: UUID | None
    period: datetime.date | None
    impact: Decimal
    revenue: Decimal
    share: Decimal | None
    criticality: OccurrenceCriticality
    payload: dict[str, Any]


class LedgerPlan(BaseModel):
    test: str
    parameters: dict[str, Any]
    cases: list[PlannedCase]
    missing_keys: list[str] = Field(default_factory=list)


def plan_cases(
    session: Session,
    user: User,
    test: str,
    params: dict[str, Any],
    keys: list[str] | None,
    bands: tuple[Decimal, Decimal, Decimal],
    criticality: OccurrenceCriticality | None = None,
) -> LedgerPlan:
    if test not in TEST_RULES:
        raise inv.InvestigationError("Teste sem registro no ledger; use T1, T2, T3, T4, T6, T8, T9 ou T10")
    result = inv.run_test(session, user, {**params, "test": test})
    items: list[dict[str, Any]] = [item for item in result["_todos"] if "_ledger" in item]
    by_key = {item["_ledger"]["chave"]: item for item in items}
    chosen = [by_key[key] for key in keys if key in by_key] if keys else items
    missing = [key for key in keys or [] if key not in by_key]
    unit_rows = list(session.scalars(sa.select(BusinessUnit)))
    units = {unit.name: unit.id for unit in unit_rows}
    operational = {unit.name for unit in unit_rows if unit.kind.value == "OPERATIONAL"}
    revenues: dict[tuple[datetime.date | None, str | None], Decimal] = {}
    cases: list[PlannedCase] = []
    for item in chosen:
        ledger = item["_ledger"]
        period = ledger["periodo"]
        unit = ledger["unidade"]
        revenue, base_label = _revenue_base(
            session,
            user,
            revenues,
            period,
            unit if unit in units else None,
            unit in operational,
        )
        suggested, share = suggest_criticality(ledger["valor"], revenue, bands)
        public = inv.public(item)
        cases.append(
            PlannedCase(
                key=ledger["chave"],
                title=ledger["titulo"],
                unit=unit,
                unit_id=units.get(unit or ""),
                period=period,
                impact=ledger["valor"],
                revenue=revenue,
                share=share,
                criticality=criticality or suggested,
                payload={
                    "teste": test,
                    "achado": public,
                    "parametros_do_teste": result.get("parametros_do_teste"),
                    "receita_base": str(revenue),
                    "base_da_receita": base_label,
                    "impacto_percentual": str(share) if share is not None else None,
                    "regua_pad_ctrl": [str(item) for item in bands],
                },
            )
        )
    return LedgerPlan(test=test, parameters=params, cases=cases, missing_keys=missing)


def register_plan__no_commit(
    session: Session,
    user: User,
    plan: LedgerPlan,
    *,
    trigger: AnalysisTrigger,
    idempotency_key: str,
    routine_code: str,
    responsible: str | None = None,
    deadline: datetime.date | None = None,
    note: str | None = None,
    emit_event: bool = True,
) -> list[dict[str, Any]]:
    """Record every planned case; returns what happened to each.

    ``emit_event`` False lets a caller that records several tests (the sweep)
    hand automations one event for the whole run."""
    if not plan.cases:
        return []
    registered = register_test_rules__no_commit(session)
    rule, rule_version = registered[plan.test]
    periods = [case.period for case in plan.cases if case.period] or [
        datetime.date.today().replace(day=1)
    ]
    analysis_run, _ = get_or_create_analysis_run__no_commit(
        session,
        idempotency_key=idempotency_key,
        trigger=trigger,
        specialist=TEST_RULES[plan.test][2],
        domain=RuleDomain.FINANCIAL,
        period_start=min(periods),
        period_end=max(periods),
        executor_version=EXECUTOR_VERSION,
        triggered_by_user_id=user.id,
        routine_code=routine_code,
    )
    analysis_run.status = AnalysisRunStatus.RUNNING
    now = datetime.datetime.now(datetime.timezone.utc)
    analysis_run.started_at = analysis_run.started_at or now
    outcomes: list[dict[str, Any]] = []
    new_ids: set[UUID] = set()
    for case in plan.cases:
        detection = record_detection__no_commit(
            session,
            analysis_run_id=analysis_run.id,
            rule=rule,
            rule_version=rule_version,
            identity_values={"source_record_key": case.key},
            finding_kind=FindingKind.DETECTION,
            title=case.title,
            owning_domain=RuleDomain.FINANCIAL,
            ledger_kind=OccurrenceLedgerKind.EXCEPTION,
            criticality=case.criticality,
            detected_at=now,
            business_unit_id=case.unit_id,
            verification_criterion=TEST_RULES[plan.test][1],
            deterministic_payload=case.payload,
            computed_impact_amount=case.impact,
            value_currency="BRL",
            period_start=case.period,
            period_end=case.period,
        )
        occurrence = detection.occurrence
        if detection.outcome.value in ("NEW", "SUPERSEDED"):
            new_ids.add(occurrence.id)
        if responsible:
            assign_responsible__no_commit(
                session,
                occurrence=occurrence,
                responsible_label=responsible,
                assigned_by_user_id=user.id,
                deadline=deadline,
            )
        if note:
            add_note__no_commit(
                session,
                occurrence=occurrence,
                body=note,
                redaction_level=RedactionLevel.NONE,
                author_user_id=user.id,
            )
        outcomes.append(
            {
                "ocorrencia": str(occurrence.id),
                "codigo": occurrence.short_code,
                "titulo": case.title,
                "unidade": case.unit,
                "situacao": detection.outcome.value,
                "criticidade": CRITICALITY_TEXT[case.criticality],
            }
        )
    context = financial_context(session, user, 1, 0)
    if context.bases:
        _share_new_occurrences(session, context.bases[0].source_id, new_ids)
    analysis_run.status = AnalysisRunStatus.COMPLETED
    analysis_run.finished_at = now
    if emit_event:
        _emit_cases_event(session, plan, outcomes, analysis_run.id, routine_code)
    session.flush()
    return outcomes


ORIGIN_TEXT = {"TON-CHAT": "chat", "R1": "varredura R1", "AUTOMATION": "automação"}


def _emit_cases_event(
    session: Session,
    plan: "LedgerPlan",
    outcomes: list[dict[str, Any]],
    analysis_run_id: UUID,
    routine_code: str,
) -> None:
    """Hands the recorded cases to automations (trigger "Casos registrados")."""
    from onyx.db.ton.email_flows import emit_flow_event__no_commit
    from onyx.ton.automations.nodes.ledger import EVENT_KIND_LEDGER, case_item

    cases = [
        case_item(outcome, plan.test, case.impact)
        for outcome, case in zip(outcomes, plan.cases, strict=True)
    ]
    emit_flow_event__no_commit(
        session,
        kind=EVENT_KIND_LEDGER,
        event_key=str(analysis_run_id),
        payload={
            "teste": plan.test,
            "origem": ORIGIN_TEXT.get(routine_code, routine_code),
            "cases": cases,
        },
    )


def assign__no_commit(
    session: Session,
    user: User,
    occurrence_ids: list[UUID],
    responsible: str | None,
    deadline: datetime.date | None,
    note: str | None,
) -> int:
    rows = list(session.scalars(sa.select(Occurrence).where(Occurrence.id.in_(occurrence_ids))))
    for occurrence in rows:
        if responsible:
            assign_responsible__no_commit(
                session,
                occurrence=occurrence,
                responsible_label=responsible,
                assigned_by_user_id=user.id,
                deadline=deadline,
            )
        if note:
            add_note__no_commit(
                session,
                occurrence=occurrence,
                body=note,
                redaction_level=RedactionLevel.NONE,
                author_user_id=user.id,
            )
    return len(rows)


# --------------------------------------------------------------------- R1

R1_SEED_KEY = "ton-r1-financial-sweep"
R1_NAME = "Varredura financeira diária (R1)"


def r1_automation(session: Session) -> Any:
    """The automation that runs R1, created from the chat; None before that."""
    from onyx.db.ton import automations as automation_repository

    return automation_repository.seeded(session, R1_SEED_KEY)
