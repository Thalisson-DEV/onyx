"""One-call closing overview for the TON assistant.

Each extra tool round costs the model 5–15 s, so a period/unit closing question
is answered from this single read: base, period, readiness, the persisted DRE
lines (the numbers on the DRE screen) and the open review findings.
"""

import datetime
import re
import unicodedata
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton import dre, financial_review
from onyx.db.ton.acl import business_unit_visible_clause
from onyx.db.ton.agent import financial_context, stored_result_for_scope
from onyx.db.ton.decision_loop import required_action
from onyx.db.ton.enums import OccurrenceStatus
from onyx.db.ton.models import BusinessUnit, DreResultLine
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.labels import business_label
from onyx.ton.agent.models import (
    ClosingOverview,
    OverviewBlocker,
    OverviewFinding,
    OverviewLine,
    UnitContext,
)
from onyx.ton.dre.models import DreScope
from onyx.ton.financial_review import service as review_service

OPEN_STATUSES = frozenset(
    {OccurrenceStatus.NEW, OccurrenceStatus.REOPENED, OccurrenceStatus.CONFIRMED}
)
ACTION_PLACES = {
    "DECISION_IN_PENDING": "Pendências (decisão humana)",
    "IMPORT_IN_SOURCES": "Fontes (importar o arquivo)",
    "DATA_OR_CONFIGURATION_FIX": "Fontes ou Administração (corrigir dado ou configuração)",
}
FINDINGS_SHOWN = 5
FINDINGS_SCANNED = 200


def _fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[\s\-/]+", " ", plain).strip().lower()


def _without_state(name: str) -> str:
    """'mossoro rn' -> 'mossoro'; the state suffix is how NG names cities."""
    return re.sub(r" [a-z]{2}$", "", name)


def visible_units(session: Session, user: User) -> list[UnitContext]:
    return [
        UnitContext(unit_id=unit.id, code=unit.code, name=unit.name)
        for unit in session.scalars(
            sa.select(BusinessUnit)
            .where(business_unit_visible_clause(user))
            .order_by(BusinessUnit.name)
        )
    ]


def resolve_unit(units: list[UnitContext], wanted: str) -> list[UnitContext]:
    """Units matching a name or NG code as the user wrote it.

    One element means resolved; several mean ambiguous; none means unknown.
    """
    folded = _fold(wanted)
    exact = [unit for unit in units if folded in (_fold(unit.code), _fold(unit.name))]
    if exact:
        return exact
    # "Juazeiro" names both JUAZEIRO-BA and JUAZEIRO DO NORTE: ambiguous, ask.
    return [
        unit
        for unit in units
        if folded in _fold(unit.name) or folded == _without_state(_fold(unit.name))
    ]


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _lines(session: Session, run_id: UUID) -> list[OverviewLine]:
    rows = list(
        session.scalars(
            sa.select(DreResultLine)
            .where(DreResultLine.run_id == run_id)
            .order_by(DreResultLine.position)
        )
    )
    with_budget = any(row.orcado or row.orcado_ytd for row in rows)
    return [
        OverviewLine(
            linha=row.label,
            realizado=_money(row.realizado),
            acumulado_no_ano=_money(row.realizado_ytd),
            orcado=_money(row.orcado) if with_budget else None,
        )
        for row in rows
    ]


def closing_overview(
    session: Session,
    user: User,
    period: datetime.date | None,
    unit_id: UUID | None,
    unit: str | None,
) -> ClosingOverview:
    if period is not None and period.day != 1:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "O período deve começar no primeiro dia do mês.",
        )
    context = financial_context(session, user, 1, 0)
    units = context.units
    unresolved: str | None = None
    candidates: list[str] = []
    if unit_id is None and unit:
        matches = resolve_unit(units, unit)
        if len(matches) == 1:
            unit_id = matches[0].unit_id
        else:
            unresolved = unit
            candidates = [item.name for item in (matches or units)]
    if unit_id is not None and all(item.unit_id != unit_id for item in units):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Unidade indisponível")
    unit_name = next((item.name for item in units if item.unit_id == unit_id), None)
    base = context.bases[0] if context.bases else None
    latest = max(base.periods) if base and base.periods else None
    chosen = period or latest or datetime.date.today().replace(day=1)
    overview = ClosingOverview(
        periodo=chosen,
        ultimo_periodo_disponivel=latest,
        periodos_disponiveis=sorted(base.periods) if base else [],
        escopo=unit_name or "Consolidado (todas as unidades)",
        unidade_solicitada_nao_encontrada=unresolved,
        unidades_candidatas=candidates,
        fonte=base.source_name if base else None,
        situacao_dre="Não verificada",
        bloqueios=[],
        dre_calculada=False,
        linhas_dre=[],
        achados_abertos_na_revisao=0,
        achados_que_impedem_dre=0,
        principais_achados=[],
        registros_na_base=None,
        registros_excluidos=None,
        onde_conferir={
            "DRE": "/ton/dre",
            "Pendências": "/ton/pendencias",
            "Fechamento": "/ton/fechamento",
        },
        limitacoes=[],
    )
    if unresolved is not None:
        overview.limitacoes.append(
            "Unidade não identificada com segurança; pergunte qual destas o usuário quis."
        )
        return overview
    if base is None or not context.structure_version_ids:
        overview.limitacoes.append(
            "Não há base financeira normalizada ou estrutura de DRE autorizada."
        )
        return overview
    if base.periods and chosen not in base.periods:
        overview.limitacoes.append(
            "O período pedido não tem lançamentos na base mais recente."
        )
    scope = DreScope(
        normalization_run_id=base.normalization_run_id,
        structure_version_id=context.structure_version_ids[0],
        period=chosen,
        unit_id=unit_id,
    )
    overview.normalization_run_id = scope.normalization_run_id
    overview.structure_version_id = scope.structure_version_id
    overview.unit_id = unit_id
    try:
        readiness = dre.readiness(session, user, scope)
    except OnyxError as error:
        if error.error_code not in (
            OnyxErrorCode.ADMIN_ONLY,
            OnyxErrorCode.INSUFFICIENT_PERMISSIONS,
            OnyxErrorCode.NOT_FOUND,
        ):
            raise
        overview.limitacoes.append(
            "Sem autorização para este escopo; selecione uma unidade autorizada."
        )
        return overview
    overview.situacao_dre = business_label(readiness.status)
    overview.bloqueios = [
        OverviewBlocker(
            bloqueio=business_label(code),
            quantidade=count,
            onde_resolver=ACTION_PLACES[required_action(code)],
        )
        for code, count in sorted(readiness.blockers.items(), key=lambda kv: -kv[1])
    ]
    stored = stored_result_for_scope(session, user, scope)
    if stored is not None and stored.status == "READY" and readiness.status == "READY":
        overview.dre_calculada = True
        overview.run_id = stored.run_id
        overview.linhas_dre = _lines(session, stored.run_id)
    elif stored is not None and stored.status == "READY":
        overview.limitacoes.append(
            "Há DRE calculada, mas a base tem bloqueios agora; os valores não são apresentados até resolvê-los."
        )
    else:
        overview.limitacoes.append(
            "Não há DRE calculada para este período e escopo; não há valores de DRE."
        )
    _add_findings(session, user, base.source_id, base.review_run_id, overview)
    return overview


def _add_findings(
    session: Session,
    user: User,
    source_id: UUID,
    review_run_id: UUID,
    overview: ClosingOverview,
) -> None:
    summary = review_service.dataset_summary(session, user, source_id, review_run_id)
    overview.registros_na_base = summary.total_records
    overview.registros_excluidos = summary.excluded_source_rows
    filters = financial_review.FindingFilters(
        source_id=source_id, review_run_id=review_run_id
    )
    open_findings = []
    for offset in range(0, FINDINGS_SCANNED, 25):
        page = review_service.list_findings(session, user, filters, 25, offset)
        open_findings.extend(
            item for item in page if item.occurrence_status in OPEN_STATUSES
        )
        if len(page) < 25:
            break
    else:
        overview.limitacoes.append(
            f"Contagem de achados limitada aos {FINDINGS_SCANNED} primeiros."
        )
    open_findings.sort(key=lambda item: (not item.blocking, -item.record_count))
    overview.achados_abertos_na_revisao = len(open_findings)
    overview.achados_que_impedem_dre = sum(item.blocking for item in open_findings)
    overview.principais_achados = [
        OverviewFinding(
            titulo=item.explanation,
            impede_dre=item.blocking,
            situacao=business_label(item.occurrence_status.value),
            registros=item.record_count,
        )
        for item in open_findings[:FINDINGS_SHOWN]
    ]
    overview.limitacoes.append(
        "Achados cobrem a revisão inteira da base, não só o mês pedido."
    )
