"""Proposals of change made by the TON chat, applied only by a person's click.

A proposal is validated and previewed when the chat makes it; nothing else is
written. ``apply`` runs the same repository functions the screens use, with
the permissions of the person who clicks, and records the outcome.
"""

import datetime
import io
from uuid import uuid4
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from onyx.db.models import User, UserFile
from onyx.db.ton import (
    account_classification,
    closing_treatments,
    dre,
    unit_assignment,
)
from onyx.db.ton import financial_domain as financial_repository
from onyx.db.ton.acl import is_ton_administrator
from onyx.db.ton.agent import financial_context
from onyx.db.ton.agent_overview import _fold, resolve_unit, visible_units
from onyx.db.ton.dre_line_sources import BILLING_FIELD_LABELS, adjustments_in_force
from onyx.db.ton.models import (
    AgentAction,
    ControllerRule,
    DreAdjustment,
    Occurrence,
    TonAutomation,
    DreStructure,
    FinancialAccount,
)
from onyx.db.ton.enums import AnalysisTrigger, OccurrenceCriticality
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.file_store.file_store import get_default_file_store
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.agent.action_models import (
    ActionKind,
    ActionPreview,
    ActionStatus,
    AdjustmentPayload,
    AgentActionView,
    AutomationRunPayload,
    AutomationStatusPayload,
    ClassificationConfirmPayload,
    ClassificationPayload,
    ControllerRulePayload,
    LedgerRegisterPayload,
    OccurrenceAssignPayload,
    R1SchedulePayload,
    PreviewLine,
    RecalculatePayload,
    ReviewDecisionPayload,
    ScopeInput,
    SourceImportPayload,
    StructureChangePayload,
    TreatmentPayload,
    UnitAssignmentPayload,
)
from onyx.ton.account_classification.models import (
    ClassificationChange,
    ClassificationConfirmBatch,
)
from onyx.ton.agent.structure_ops import apply_operations
from onyx.ton.automations import service as automation_service
from onyx.ton.automations.definition import AutomationStatus
from onyx.ton.financial_review import service as review_service
from onyx.ton.financial_review.models import (
    JustificationCategory,
    ReviewDecisionKind,
    ReviewDecisionRequest,
)
from onyx.ton.client_import.service import CATALOG as CLIENT_CATALOG
from onyx.ton.client_import.service import preview_client_import, upload_client_source
from onyx.ton.dre.history import VersionContent, describe_changes
from onyx.ton.dre.models import (
    DreChange,
    DreChangeKind,
    DreLineDefinition,
    DreLineSource,
    DreLineType,
    DreResultLineView,
    DreScope,
    DreVersionCreate,
    DreVersionView,
)
from onyx.ton.dre.xlsx_export import month_label
from onyx.ton.financial_domain.models import (
    TreatmentCreate,
    TreatmentEffect,
    TreatmentStatus,
)
from onyx.ton.financial_review.service import dataset_summary

EXPIRY = datetime.timedelta(hours=24)
CENT = Decimal("0.005")

PAYLOADS: dict[ActionKind, type[BaseModel]] = {
    ActionKind.DRE_STRUCTURE_CHANGE: StructureChangePayload,
    ActionKind.DRE_ADJUSTMENT: AdjustmentPayload,
    ActionKind.CLOSING_TREATMENT: TreatmentPayload,
    ActionKind.DRE_RECALCULATE: RecalculatePayload,
    ActionKind.SOURCE_IMPORT: SourceImportPayload,
    ActionKind.ACCOUNT_CLASSIFICATION: ClassificationPayload,
    ActionKind.CLASSIFICATION_CONFIRM: ClassificationConfirmPayload,
    ActionKind.REVIEW_DECISION: ReviewDecisionPayload,
    ActionKind.UNIT_ASSIGNMENT: UnitAssignmentPayload,
    ActionKind.AUTOMATION_STATUS: AutomationStatusPayload,
    ActionKind.AUTOMATION_RUN: AutomationRunPayload,
    ActionKind.CONTROLLER_RULE: ControllerRulePayload,
    ActionKind.LEDGER_REGISTER: LedgerRegisterPayload,
    ActionKind.OCCURRENCE_ASSIGN: OccurrenceAssignPayload,
    ActionKind.R1_SCHEDULE: R1SchedulePayload,
}

CHANGE_TEXT = {
    DreChangeKind.LINE_ADDED: "Linha “{line}” criada" + "{after_in}",
    DreChangeKind.LINE_REMOVED: "Linha “{line}” removida",
    DreChangeKind.LINE_RENAMED: "“{before}” renomeada para “{after}”",
    DreChangeKind.LINE_MOVED: "“{line}” saiu de “{before}” para “{after}”",
    DreChangeKind.ORDER_CHANGED: "Ordem alterada em “{line}”",
    DreChangeKind.INTO_RESULT: "“{line}” volta a entrar no resultado",
    DreChangeKind.OUT_OF_RESULT: "“{line}” sai do resultado (o valor continua visível)",
    DreChangeKind.FORMULA_CHANGED: "Cálculo de “{line}”: {before} → {after}",
    DreChangeKind.HIDDEN: "“{line}” fica oculta na DRE (continua somando)",
    DreChangeKind.SHOWN: "“{line}” volta a aparecer na DRE",
    DreChangeKind.NATURE_LINKED: "Natureza {line} ligada a “{after}”",
    DreChangeKind.NATURE_UNLINKED: "Natureza {line} desligada de “{before}”",
    DreChangeKind.NATURE_RELINKED: "Natureza {line}: “{before}” → “{after}”",
}


def _change_text(change: DreChange) -> str:
    return CHANGE_TEXT[change.kind].format(
        line=change.line,
        before=change.before or "—",
        after=change.after or "—",
        after_in=f" em “{change.after}”" if change.after else "",
    )


def _source_text(line: DreLineDefinition) -> str | None:
    if line.line_type != DreLineType.SOURCE_SUM:
        return None
    sign = " com sinal negativo" if line.negate else ""
    if line.source == DreLineSource.BILLING:
        fields = ", ".join(BILLING_FIELD_LABELS[item] for item in line.billing_fields)
        basis = "competência" if line.billing_period == "COMPETENCE" else "emissão"
        return f"“{line.label}” soma do faturamento: {fields}, pelo mês de {basis}{sign}"
    if line.source == DreLineSource.ADJUSTMENT:
        return f"“{line.label}” recebe valores informados pela Controladoria{sign}"
    return None


def _view(row: AgentAction) -> AgentActionView:
    return AgentActionView(
        id=row.id,
        kind=ActionKind(row.kind),
        title=row.title,
        status=ActionStatus(row.status),
        preview=ActionPreview.model_validate(row.preview),
        result=row.result,
        error=row.error,
        created_at=row.created_at,
        decided_at=row.decided_at,
        expires_at=row.created_at + EXPIRY,
    )


# ---------------------------------------------------------------- scope


class _Scope(BaseModel):
    normalization_run_id: UUID
    period: datetime.date
    unit_id: UUID | None
    unit_name: str | None


def _unit_id(session: Session, user: User, text: str | None) -> tuple[UUID | None, str | None]:
    if not text or text.strip().lower() in ("consolidado", "todas", "geral"):
        return None, None
    units = visible_units(session, user)
    matches = resolve_unit(units, text)
    if len(matches) != 1:
        names = ", ".join(item.name for item in (matches or units)[:12])
        raise ValueError(f"Unidade “{text}” não identificada. Opções: {names}")
    return matches[0].unit_id, matches[0].name


def _scope(session: Session, user: User, payload: ScopeInput) -> _Scope:
    context = financial_context(session, user, 1, 0)
    if not context.bases:
        raise ValueError("Não há base financeira normalizada")
    base = context.bases[0]
    if not base.periods:
        raise ValueError("A base mais recente não tem lançamentos")
    period = payload.period.replace(day=1) if payload.period else max(base.periods)
    unit_id, unit_name = _unit_id(session, user, payload.unit)
    if unit_id is None and not is_ton_administrator(user):
        raise ValueError("A DRE consolidada exige administrador; informe uma unidade")
    return _Scope(
        normalization_run_id=base.normalization_run_id,
        period=period,
        unit_id=unit_id,
        unit_name=unit_name,
    )


def _scope_text(scope: _Scope) -> str:
    return (
        f"{month_label(scope.period.month)}/{scope.period.year} · "
        f"{scope.unit_name or 'Consolidado'}"
    )


def _structure(session: Session, structure_id: UUID | None) -> DreStructure:
    structure = (
        session.get(DreStructure, structure_id)
        if structure_id
        else dre._primary_structure(session)
    )
    if structure is None:
        raise ValueError("Estrutura de DRE não encontrada")
    if structure.base_structure_id is not None:
        raise ValueError(
            "Esta estrutura acompanha a gerencial; mude a estrutura gerencial"
        )
    return structure


def _brl(value: Decimal) -> str:
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def _cents(value: Decimal | None) -> Decimal | None:
    return value.quantize(Decimal("0.01")) if value is not None else None


def _compare(
    before: list[DreResultLineView],
    after: list[DreResultLineView],
    lines: list[DreLineDefinition],
) -> list[PreviewLine]:
    """Lines whose month value changes, plus the top-level totals."""
    old = {item.code: item.realizado for item in before}
    new = {item.code: item.realizado for item in after}
    by_code = {line.code: line for line in lines}
    result: list[PreviewLine] = []
    for item in after or before:
        line = by_code.get(item.code)
        if line is None or line.hidden:
            continue
        previous, current = old.get(item.code), new.get(item.code)
        changed = (
            previous is None
            or current is None
            or abs(previous - current) >= CENT
        )
        top = line.parent_code is None
        if changed or top:
            result.append(
                PreviewLine(
                    label=line.label,
                    antes=_cents(previous),
                    depois=_cents(current),
                    total=line.line_type != DreLineType.SOURCE_SUM,
                )
            )
    for code, value in old.items():
        if code not in new:
            label = next((item.label for item in before if item.code == code), code)
            result.append(PreviewLine(label=label, antes=_cents(value), depois=None))
    return result[:30]


def _blocker_note(blockers: dict[str, int]) -> list[str]:
    if not blockers:
        return []
    return [
        "A base tem pendências que impedem a DRE oficial; os valores da prévia deixam de fora as naturezas sem linha aprovada."
    ]


# ------------------------------------------------------- structure change


def _structure_plan(
    session: Session, user: User, payload: StructureChangePayload
) -> tuple[DreStructure, DreVersionView, DreVersionCreate]:
    structure = _structure(session, payload.structure_id)
    current = dre.get_latest_version(session, user, structure.id)
    accounts = {
        code: account_id
        for code, account_id in session.execute(
            sa.select(FinancialAccount.code, FinancialAccount.id)
        ).tuples()
    }
    try:
        edit = apply_operations(
            current.lines, current.assignments, payload.operations, accounts
        )
    except ValueError as error:
        raise ValueError(str(error)) from error
    return (
        structure,
        current,
        DreVersionCreate(
            lines=edit.lines, assignments=edit.assignments, reason=payload.reason
        ),
    )


def _preview_structure(
    session: Session, user: User, payload: StructureChangePayload
) -> tuple[str, ActionPreview]:
    structure, current, request = _structure_plan(session, user, payload)
    natures = dre._nature_labels(session, [current])
    changes = describe_changes(
        VersionContent(current.lines, current.assignments),
        VersionContent(request.lines, request.assignments),
        natures,
    )
    summary = [_change_text(item) for item in changes]
    old_lines = {line.code: line for line in current.lines}
    for line in request.lines:
        text = _source_text(line)
        previous = old_lines.get(line.code)
        if text and (
            previous is None
            or previous.model_dump(include={"source", "billing_fields", "billing_period", "negate"})
            != line.model_dump(include={"source", "billing_fields", "billing_period", "negate"})
        ):
            summary.append(text)
    if not summary:
        raise ValueError("A mudança não altera a estrutura")
    scope = _scope(session, user, payload)
    dre_scope = DreScope(
        normalization_run_id=scope.normalization_run_id,
        structure_version_id=current.id,
        period=scope.period,
        unit_id=scope.unit_id,
    )
    before, _ = dre.preview_statement(session, user, dre_scope)
    after, blockers = dre.preview_statement(
        session, user, dre_scope, lines=request.lines, assignments=request.assignments
    )
    return (
        f"Mudar a estrutura “{structure.label}”",
        ActionPreview(
            resumo=summary,
            escopo=_scope_text(scope),
            linhas=_compare(before, after, request.lines),
            avisos=_blocker_note(blockers)
            + [
                "Ao aplicar, o TON grava uma nova versão da estrutura e recalcula a DRE consolidada do ano."
            ],
            pode_desfazer=True,
        ),
    )


def _recalculate(
    session: Session,
    user: User,
    structure_id: UUID,
    period: datetime.date,
    unit_ids: list[UUID | None],
) -> dict[str, Any]:
    context = financial_context(session, user, 1, 0)
    base = context.bases[0]
    version = dre.get_latest_version(session, user, structure_id)
    statuses: dict[str, str] = {}
    for unit_id in unit_ids:
        runs = dre.execute_year(
            session,
            user,
            DreScope(
                normalization_run_id=base.normalization_run_id,
                structure_version_id=version.id,
                period=period,
                unit_id=unit_id,
            ),
        )
        statuses[str(unit_id) if unit_id else "consolidado"] = (
            runs[-1].status if runs else "NOT_READY"
        )
    return {
        "versao_estrutura": version.number,
        "recalculado_ate": period.isoformat(),
        "situacao": statuses,
    }


def _apply_structure(
    session: Session, user: User, payload: StructureChangePayload
) -> dict[str, Any]:
    structure, current, request = _structure_plan(session, user, payload)
    saved = dre.create_version(session, user, structure.id, request)
    session.commit()
    scope = _scope(session, user, payload)
    result = _recalculate(
        session, user, structure.id, scope.period, [None] if is_ton_administrator(user) else [scope.unit_id]
    )
    return {
        **result,
        "structure_id": str(structure.id),
        "versao_anterior": current.number,
        "versao_nova": saved.number,
    }


def _undo_structure(
    session: Session, user: User, payload: StructureChangePayload, result: dict[str, Any]
) -> dict[str, Any]:
    structure_id = UUID(result["structure_id"])
    latest = dre.get_latest_version(session, user, structure_id)
    if latest.number != result["versao_nova"]:
        raise ValueError(
            "A estrutura já recebeu outra versão depois desta; desfaça pelo Histórico da estrutura"
        )
    from onyx.ton.dre.models import DreRestoreRequest

    dre.restore_version(
        session,
        user,
        structure_id,
        int(result["versao_anterior"]),
        DreRestoreRequest(reason="Desfeito pelo chat"),
    )
    session.commit()
    scope = _scope(session, user, payload)
    return _recalculate(
        session, user, structure_id, scope.period, [None] if is_ton_administrator(user) else [scope.unit_id]
    )


# ------------------------------------------------------------ adjustments


def _adjustment_rows(
    session: Session, user: User, payload: AdjustmentPayload
) -> tuple[DreStructure, DreLineDefinition, list[DreAdjustment]]:
    structure = _structure(session, payload.structure_id)
    version = dre.get_latest_version(session, user, structure.id)
    line = next((item for item in version.lines if item.code == payload.line_code), None)
    if line is None:
        raise ValueError(f"A linha {payload.line_code} não existe na estrutura")
    if line.source != DreLineSource.ADJUSTMENT:
        raise ValueError(
            f"A linha “{line.label}” não recebe ajustes; proponha antes uma linha de ajuste da Controladoria"
        )
    rows: list[DreAdjustment] = []
    for value in payload.values:
        unit_id, _ = _unit_id(session, user, value.unit)
        if unit_id is None and not is_ton_administrator(user):
            raise ValueError("Ajuste no consolidado exige administrador")
        rows.append(
            DreAdjustment(
                structure_id=structure.id,
                line_code=line.code,
                period=value.period.replace(day=1),
                unit_id=unit_id,
                amount=value.amount,
                justification=payload.justification,
                created_by=user.id,
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
        )
    return structure, line, rows


def _preview_adjustment(
    session: Session, user: User, payload: AdjustmentPayload
) -> tuple[str, ActionPreview]:
    structure, line, rows = _adjustment_rows(session, user, payload)
    periods = sorted({row.period for row in rows})
    scope = _scope(
        session,
        user,
        payload.model_copy(update={"period": payload.period or periods[-1]}),
    )
    version = dre.get_latest_version(session, user, structure.id)
    dre_scope = DreScope(
        normalization_run_id=scope.normalization_run_id,
        structure_version_id=version.id,
        period=scope.period,
        unit_id=scope.unit_id,
    )
    before, _ = dre.preview_statement(session, user, dre_scope)
    after, blockers = dre.preview_statement(
        session, user, dre_scope, extra_adjustments=rows
    )
    units = {item.unit_id: item.name for item in visible_units(session, user)}
    sign = " (entra com sinal negativo)" if line.negate else ""
    summary = [
        f"{month_label(row.period.month)}/{row.period.year} · "
        f"{units.get(row.unit_id, 'Consolidado') if row.unit_id else 'Consolidado'}: "
        f"{_brl(row.amount)}{sign}"
        for row in rows
    ]
    return (
        f"Ajuste em “{line.label}”",
        ActionPreview(
            resumo=summary + [f"Justificativa: {payload.justification}"],
            escopo=_scope_text(scope),
            linhas=_compare(before, after, version.lines),
            avisos=_blocker_note(blockers)
            + ["Cada valor substitui o ajuste anterior do mesmo mês e unidade."],
            pode_desfazer=True,
        ),
    )


def _in_force_amounts(
    session: Session, rows: list[DreAdjustment]
) -> list[dict[str, Any]]:
    previous: list[dict[str, Any]] = []
    for row in rows:
        current = next(
            (
                item
                for item in adjustments_in_force(
                    session, row.structure_id, row.period.year, row.unit_id
                )
                if item.line_code == row.line_code
                and item.period == row.period
                and item.unit_id == row.unit_id
            ),
            None,
        )
        previous.append(
            {
                "structure_id": str(row.structure_id),
                "line_code": row.line_code,
                "period": row.period.isoformat(),
                "unit_id": str(row.unit_id) if row.unit_id else None,
                "amount": str(current.amount if current else Decimal(0)),
            }
        )
    return previous


def _apply_adjustment(
    session: Session, user: User, payload: AdjustmentPayload
) -> dict[str, Any]:
    structure, _line, rows = _adjustment_rows(session, user, payload)
    previous = _in_force_amounts(session, rows)
    session.add_all(rows)
    session.commit()
    result = _recalculate(
        session,
        user,
        structure.id,
        max(row.period for row in rows),
        _recalc_units(user, [row.unit_id for row in rows]),
    )
    return {**result, "anteriores": previous}


def _recalc_units(user: User, unit_ids: list[UUID | None]) -> list[UUID | None]:
    units: list[UUID | None] = [None] if is_ton_administrator(user) else []
    for unit_id in unit_ids:
        if unit_id is not None and unit_id not in units:
            units.append(unit_id)
    return units


def _undo_adjustment(
    session: Session, user: User, payload: AdjustmentPayload, result: dict[str, Any]
) -> dict[str, Any]:
    rows = [
        DreAdjustment(
            structure_id=UUID(item["structure_id"]),
            line_code=item["line_code"],
            period=datetime.date.fromisoformat(item["period"]),
            unit_id=UUID(item["unit_id"]) if item["unit_id"] else None,
            amount=Decimal(item["amount"]),
            justification=f"Desfeito pelo chat: {payload.justification}"[:2000],
            created_by=user.id,
        )
        for item in result["anteriores"]
    ]
    session.add_all(rows)
    session.commit()
    return _recalculate(
        session,
        user,
        rows[0].structure_id,
        max(row.period for row in rows),
        _recalc_units(user, [row.unit_id for row in rows]),
    )


# ------------------------------------------------------------- treatments


def _treatment_request(
    session: Session, user: User, payload: TreatmentPayload
) -> TreatmentCreate:
    def account(code: str) -> UUID:
        found = session.scalar(
            sa.select(FinancialAccount.id).where(FinancialAccount.code == code)
        )
        if found is None:
            raise ValueError(f"A natureza {code} não existe")
        return found

    unit_id, _ = _unit_id(session, user, payload.treatment_unit)
    return TreatmentCreate(
        treatment_key=payload.treatment_key,
        title=payload.title,
        status=payload.status,
        effect=payload.effect,
        account_id=account(payload.nature_code),
        unit_id=unit_id,
        period_from=payload.period_from,
        period_to=payload.period_to,
        target_account_id=account(payload.target_nature_code)
        if payload.target_nature_code
        else None,
        required_source=payload.required_source,
        justification=payload.justification,
        evidence=payload.evidence,
    )


EFFECT_TEXT = {
    TreatmentEffect.EXCLUDE: "tira os lançamentos da DRE",
    TreatmentEffect.RECLASSIFY: "move os lançamentos para outra natureza",
    TreatmentEffect.REPLACE_BY_SOURCE: "substitui os lançamentos por outra fonte",
}


def _preview_treatment(
    session: Session, user: User, payload: TreatmentPayload
) -> tuple[str, ActionPreview]:
    if not is_ton_administrator(user):
        raise ValueError("Tratamentos de fechamento exigem administrador")
    request = _treatment_request(session, user, payload)
    if request.effect is TreatmentEffect.RECLASSIFY and request.target_account_id is None:
        raise ValueError("Reclassificar exige a natureza de destino")
    history = []
    try:
        history = closing_treatments.treatment_history(session, user, request.treatment_key)
    except OnyxError:
        history = []
    period = (
        f"de {request.period_from:%m/%Y} a {request.period_to:%m/%Y}"
        if request.period_from and request.period_to
        else "em todos os meses"
    )
    summary = [
        f"Natureza {payload.nature_code}: {EFFECT_TEXT[request.effect]}"
        + (f" ({payload.target_nature_code})" if payload.target_nature_code else "")
        + f", {period}"
        + (f", unidade {payload.treatment_unit}" if payload.treatment_unit else ""),
        f"Justificativa: {request.justification}",
        f"Evidência: {request.evidence}",
    ]
    if history:
        summary.insert(0, f"Nova versão do tratamento “{history[0].title}” (versão {history[0].version + 1})")
    avisos = ["Ao aplicar, o TON registra o tratamento, atualiza a base e recalcula a DRE consolidada. Pode levar alguns minutos."]
    if request.status is TreatmentStatus.BLOCKED:
        avisos = ["O tratamento fica aguardando a fonte e não muda valores agora."]
    return (
        f"Tratamento: {request.title}",
        ActionPreview(resumo=summary, avisos=avisos, pode_desfazer=True),
    )


def _refresh_base(session: Session, user: User) -> UUID:
    context = financial_context(session, user, 1, 0)
    base = context.bases[0]
    request = financial_repository.normalization_request_for_run(
        session, user, base.normalization_run_id
    )
    summary = dataset_summary(session, user, request.ng_source_id, request.review_run_id)
    session.commit()
    run = financial_repository.normalize(
        session, user, request, summary.dataset_revision, summary.as_of
    )
    return run.id


def _apply_treatment(
    session: Session, user: User, payload: TreatmentPayload
) -> dict[str, Any]:
    request = _treatment_request(session, user, payload)
    try:
        previous = closing_treatments.treatment_history(session, user, request.treatment_key)
    except OnyxError:
        previous = []
    row = closing_treatments.create_treatment(session, user, request)
    session.commit()
    result: dict[str, Any] = {
        "treatment_key": row.treatment_key,
        "versao": row.version,
        "anterior": previous[0].model_dump(mode="json") if previous else None,
    }
    if request.status is TreatmentStatus.ACTIVE:
        _refresh_base(session, user)
        structure = _structure(session, None)
        scope = _scope(session, user, payload)
        result.update(_recalculate(session, user, structure.id, scope.period, [None]))
    return result


def _undo_treatment(
    session: Session, user: User, payload: TreatmentPayload, result: dict[str, Any]
) -> dict[str, Any]:
    previous = result.get("anterior")
    request = _treatment_request(session, user, payload)
    if previous:
        request = TreatmentCreate(
            treatment_key=previous["treatment_key"],
            title=previous["title"],
            status=previous["status"],
            effect=previous["effect"],
            account_id=previous["account_id"],
            unit_id=previous["unit_id"],
            period_from=previous["period_from"],
            period_to=previous["period_to"],
            target_account_id=previous.get("target_account_id"),
            required_source=previous.get("required_source"),
            justification=f"Desfeito pelo chat: {previous['justification']}"[:2000],
            evidence=previous["evidence"],
        )
    else:
        request = request.model_copy(
            update={
                "status": TreatmentStatus.REVOKED,
                "justification": f"Desfeito pelo chat: {request.justification}"[:2000],
            }
        )
    closing_treatments.create_treatment(session, user, request)
    session.commit()
    _refresh_base(session, user)
    structure = _structure(session, None)
    scope = _scope(session, user, payload)
    return _recalculate(session, user, structure.id, scope.period, [None])


# ------------------------------------------------------------ recalculate


def _recalc_targets(
    session: Session, user: User, payload: RecalculatePayload
) -> tuple[list[UUID | None], list[str]]:
    targets: list[UUID | None] = [None] if is_ton_administrator(user) else []
    names: list[str] = ["Consolidado"] if targets else []
    if any(item.strip().lower() == "todas" for item in payload.units):
        for unit in visible_units(session, user):
            targets.append(unit.unit_id)
            names.append(unit.name)
        return targets, names
    for text in payload.units:
        unit_id, name = _unit_id(session, user, text)
        if unit_id is not None and unit_id not in targets:
            targets.append(unit_id)
            names.append(name or text)
    if not targets:
        raise ValueError("Informe ao menos uma unidade")
    return targets, names


def _preview_recalculate(
    session: Session, user: User, payload: RecalculatePayload
) -> tuple[str, ActionPreview]:
    structure = _structure(session, payload.structure_id)
    scope = _scope(session, user, payload)
    _, names = _recalc_targets(session, user, payload)
    return (
        f"Recalcular a DRE até {month_label(scope.period.month)}/{scope.period.year}",
        ActionPreview(
            resumo=[
                f"Estrutura “{structure.label}”, janeiro a {month_label(scope.period.month).lower()}",
                "Escopos: " + ", ".join(names),
            ],
            avisos=["Cada unidade leva alguns segundos."] if len(names) > 3 else [],
        ),
    )


def _apply_recalculate(
    session: Session, user: User, payload: RecalculatePayload
) -> dict[str, Any]:
    structure = _structure(session, payload.structure_id)
    scope = _scope(session, user, payload)
    targets, _ = _recalc_targets(session, user, payload)
    return _recalculate(session, user, structure.id, scope.period, targets)


# ---------------------------------------------------------------- imports


SOURCE_NAMES = {key: value[0] for key, value in CLIENT_CATALOG.items()}


def _attachment(
    session: Session, user: User, file_id: UUID
) -> tuple[bytes, str, str]:
    """Original bytes, name and media type of a file attached to the chat."""
    store = get_default_file_store()
    user_file = session.get(UserFile, file_id)
    if user_file is not None:
        if user_file.user_id != user.id:
            raise ValueError("Arquivo indisponível")
        record = store.read_file_record(user_file.file_id)
        content = store.read_file(user_file.file_id, mode="b").read()
        return content, user_file.name, record.file_type
    try:
        record = store.read_file_record(str(file_id))
    except Exception as error:
        raise ValueError("Arquivo anexado não encontrado") from error
    content = store.read_file(str(file_id), mode="b").read()
    return content, record.display_name or "arquivo", record.file_type


SPREADSHEET_SUFFIXES = (".xls", ".xlsx", ".xlsm", ".csv")


def attached_spreadsheets(
    session: Session, user: User, file_ids: list[UUID]
) -> list[tuple[UUID, str]]:
    """Spreadsheets among the files attached to a conversation, by name."""
    found: list[tuple[UUID, str]] = []
    for file_id in file_ids:
        try:
            _, name, _ = _attachment_header(session, user, file_id)
        except ValueError:
            continue
        if name.lower().endswith(SPREADSHEET_SUFFIXES):
            found.append((file_id, name))
    return found


def _attachment_header(
    session: Session, user: User, file_id: UUID
) -> tuple[UUID, str, str]:
    store = get_default_file_store()
    user_file = session.get(UserFile, file_id)
    if user_file is not None:
        if user_file.user_id != user.id:
            raise ValueError("Arquivo indisponível")
        return file_id, user_file.name, user_file.file_type
    try:
        record = store.read_file_record(str(file_id))
    except Exception as error:
        raise ValueError("Arquivo anexado não encontrado") from error
    return file_id, record.display_name or "arquivo", record.file_type


def _preview_import(
    session: Session, user: User, payload: SourceImportPayload
) -> tuple[str, ActionPreview]:
    if payload.file_id is None:
        raise ValueError("Informe o arquivo anexado")
    content, filename, media_type = _attachment(session, user, payload.file_id)
    try:
        view = preview_client_import(
            session, user, payload.source_key, io.BytesIO(content), filename, media_type
        )
    except OnyxError as error:
        raise ValueError(
            f"O arquivo “{filename}” não serve para {SOURCE_NAMES[payload.source_key]}: {error.detail}"
        ) from error
    summary = [
        f"Arquivo “{filename}” como nova importação de {SOURCE_NAMES[payload.source_key]}",
        f"{view.imported} linhas lidas, {view.rejected} rejeitadas",
    ]
    if view.has_previous_review:
        summary.append(
            f"Decisões mantidas: {view.carried_over} · voltam para decisão: "
            f"{view.evidence_changed + view.reopened} · casos novos: {view.new} · "
            f"deixam de aparecer: {view.not_detected}"
        )
    avisos = ["Ao aplicar, o TON importa o arquivo, atualiza a base e recalcula a DRE consolidada."]
    if view.rejected:
        avisos.append("Linhas rejeitadas ficam fora; confira em Fontes depois de importar.")
    return (
        f"Importar “{filename}”",
        ActionPreview(resumo=summary, avisos=avisos),
    )


def _apply_import(
    session: Session, user: User, payload: SourceImportPayload
) -> dict[str, Any]:
    assert payload.file_id is not None
    content, filename, media_type = _attachment(session, user, payload.file_id)
    view = upload_client_source(
        session,
        user,
        payload.source_key,
        io.BytesIO(content),
        filename,
        media_type,
        get_default_file_store(),
    )
    session.commit()
    result: dict[str, Any] = {
        "importacao": str(view.id),
        "situacao_importacao": view.status,
        "linhas": view.imported,
        "rejeitadas": view.rejected,
        "base": view.readiness_status,
    }
    if view.readiness_status == "UPDATED" and is_ton_administrator(user):
        structure = _structure(session, None)
        scope = _scope(session, user, payload)
        result.update(_recalculate(session, user, structure.id, scope.period, [None]))
    return result


# ---------------------------------------------------------- classification


def _natures(session: Session, user: User) -> tuple[UUID, dict[str, Any]]:
    table = account_classification.classification_table(session, user, None)
    return table.source_id, {"table": table}


def _nature_for(table: Any, text: str) -> Any:
    folded = _fold(text)
    exact = [
        item
        for item in table.natures
        if item.code == text or _fold(item.natureza) == folded
    ]
    if len(exact) == 1:
        return exact[0]
    partial = [item for item in table.natures if folded in _fold(item.natureza)]
    if len(partial) == 1:
        return partial[0]
    options = ", ".join(f"{item.code} {item.natureza}" for item in (partial or table.natures)[:20])
    raise ValueError(f"Natureza “{text}” não identificada. Opções: {options}")


def _classification_plan(
    session: Session, user: User, payload: ClassificationPayload
) -> tuple[UUID, list[tuple[str, Any, Any]]]:
    source_id, context = _natures(session, user)
    table = context["table"]
    rows = {row.account_code: row for row in table.rows}
    plan = []
    for item in payload.items:
        row = rows.get(item.account_code)
        if row is None:
            raise ValueError(f"A conta {item.account_code} não está na base do NG")
        plan.append((item.account_code, row, _nature_for(table, item.natureza)))
    return source_id, plan


def _preview_classification(
    session: Session, user: User, payload: ClassificationPayload
) -> tuple[str, ActionPreview]:
    _, plan = _classification_plan(session, user, payload)
    summary = [
        f"{code} {row.description}: {row.natureza or 'sem natureza'} → {nature.code} {nature.natureza} "
        f"({row.entries} lançamentos, {_brl(row.total_amount)})"
        for code, row, nature in plan
    ]
    return (
        f"Classificar {len(plan)} conta(s) do NG",
        ActionPreview(
            resumo=summary[:40] + ([f"… e mais {len(summary) - 40}"] if len(summary) > 40 else []),
            avisos=["A DRE muda depois de atualizar a base; ao aplicar, o TON atualiza e recalcula o consolidado."],
            pode_desfazer=True,
        ),
    )


def _apply_classification(
    session: Session, user: User, payload: ClassificationPayload
) -> dict[str, Any]:
    source_id, plan = _classification_plan(session, user, payload)
    previous = [
        {"account_code": code, "natureza": row.account_id and str(row.account_id)}
        for code, row, _ in plan
    ]
    for code, _row, nature in plan:
        account_classification.change_classification(
            session,
            user,
            source_id,
            ClassificationChange(
                account_code=code, account_id=nature.account_id, reason=payload.reason
            ),
        )
    session.commit()
    _refresh_base(session, user)
    structure = _structure(session, None)
    scope = _scope(session, user, payload)
    return {
        "classificadas": len(plan),
        "anteriores": previous,
        **_recalculate(session, user, structure.id, scope.period, [None]),
    }


def _undo_classification(
    session: Session, user: User, payload: ClassificationPayload, result: dict[str, Any]
) -> dict[str, Any]:
    source_id, _ = _natures(session, user)
    restored = 0
    for item in result["anteriores"]:
        if not item["natureza"]:
            continue
        account_classification.change_classification(
            session,
            user,
            source_id,
            ClassificationChange(
                account_code=item["account_code"],
                account_id=UUID(item["natureza"]),
                reason="Desfeito pelo chat",
            ),
        )
        restored += 1
    session.commit()
    _refresh_base(session, user)
    structure = _structure(session, None)
    scope = _scope(session, user, payload)
    return {"restauradas": restored, **_recalculate(session, user, structure.id, scope.period, [None])}


def _preview_confirm(
    session: Session, user: User, payload: ClassificationConfirmPayload
) -> tuple[str, ActionPreview]:
    _, context = _natures(session, user)
    rows = {row.account_code: row for row in context["table"].rows}
    summary = []
    for code in payload.account_codes:
        row = rows.get(code)
        if row is None:
            raise ValueError(f"A conta {code} não está na base do NG")
        if row.suggestion is None and row.natureza is None:
            raise ValueError(f"A conta {code} não tem natureza sugerida para confirmar")
        summary.append(f"{code} {row.description} → {row.natureza or 'sugestão do assistente'}")
    return (
        f"Confirmar a natureza de {len(summary)} conta(s)",
        ActionPreview(resumo=summary[:40], avisos=["Confirma as sugestões como estão; para trocar, peça a classificação."]),
    )


def _apply_confirm(
    session: Session, user: User, payload: ClassificationConfirmPayload
) -> dict[str, Any]:
    source_id, _ = _natures(session, user)
    count = account_classification.confirm_batch(
        session,
        user,
        source_id,
        ClassificationConfirmBatch(account_codes=payload.account_codes, note=payload.note),
    )
    session.commit()
    return {"confirmadas": count}


# ------------------------------------------------------- review decisions


DECISION_TEXT = {
    "ACKNOWLEDGE": "ciente, sem mudar a base",
    "REQUEST_SOURCE_CORRECTION": "pedir correção na fonte",
    "JUSTIFY_EXCEPTION": "justificar como exceção",
    "MARK_FALSE_POSITIVE": "marcar como falso positivo",
    "CONFIRM_SOURCE_CORRECTION": "confirmar que a fonte foi corrigida",
}


def _occurrences(session: Session, ids: list[UUID]) -> list[Occurrence]:
    rows = list(session.scalars(sa.select(Occurrence).where(Occurrence.id.in_(ids))))
    if len(rows) != len(set(ids)):
        raise ValueError("Alguma pendência não foi encontrada; consulte a lista de novo")
    return rows


def _preview_decision(
    session: Session, user: User, payload: ReviewDecisionPayload
) -> tuple[str, ActionPreview]:
    rows = _occurrences(session, payload.occurrence_ids)
    return (
        f"Decidir {len(rows)} pendência(s): {DECISION_TEXT[payload.decision]}",
        ActionPreview(
            resumo=[f"{row.short_code or ''} {row.title}".strip() for row in rows[:30]]
            + [f"Motivo: {payload.reason}"],
            avisos=["A decisão fica no histórico da pendência com seu nome; mudanças na base valem na próxima atualização."],
        ),
    )


def _apply_decision(
    session: Session, user: User, payload: ReviewDecisionPayload
) -> dict[str, Any]:
    decided = 0
    failed: list[str] = []
    for occurrence_id in payload.occurrence_ids:
        try:
            review_service.record_decision(
                session,
                user,
                occurrence_id,
                ReviewDecisionRequest(
                    kind=ReviewDecisionKind(payload.decision),
                    reason=payload.reason,
                    justification_category=JustificationCategory(payload.justification_category)
                    if payload.justification_category
                    else None,
                ),
            )
            decided += 1
        except OnyxError as error:
            session.rollback()
            failed.append(f"{occurrence_id}: {error.detail}")
    return {"decididas": decided, "falhas": failed[:10]}


# -------------------------------------------------------- unit assignment


def _unit_plan(
    session: Session, user: User, payload: UnitAssignmentPayload
) -> list[tuple[Occurrence, UUID | None, str]]:
    rows = {row.id: row for row in _occurrences(session, [item.occurrence_id for item in payload.items])}
    plan = []
    for item in payload.items:
        unit_id, name = _unit_id(session, user, item.unit)
        plan.append((rows[item.occurrence_id], unit_id, name or "sem unidade"))
    return plan


def _preview_units(
    session: Session, user: User, payload: UnitAssignmentPayload
) -> tuple[str, ActionPreview]:
    plan = _unit_plan(session, user, payload)
    return (
        f"Atribuir unidade a {len(plan)} lançamento(s) sem unidade",
        ActionPreview(
            resumo=[f"{row.title} → {name}" for row, _, name in plan[:30]],
            avisos=["Vale na próxima atualização da base; ao aplicar, o TON atualiza e recalcula o consolidado."],
            pode_desfazer=True,
        ),
    )


def _apply_units(
    session: Session, user: User, payload: UnitAssignmentPayload
) -> dict[str, Any]:
    plan = _unit_plan(session, user, payload)
    for row, unit_id, _ in plan:
        unit_assignment.assign_unit__no_commit(session, user, row.id, unit_id, payload.reason)
    session.commit()
    _refresh_base(session, user)
    structure = _structure(session, None)
    scope = _scope(session, user, payload)
    return {
        "atribuidas": len(plan),
        "ocorrencias": [str(row.id) for row, _, _ in plan],
        **_recalculate(session, user, structure.id, scope.period, [None]),
    }


def _undo_units(
    session: Session, user: User, payload: UnitAssignmentPayload, result: dict[str, Any]
) -> dict[str, Any]:
    for occurrence_id in result["ocorrencias"]:
        unit_assignment.assign_unit__no_commit(
            session, user, UUID(occurrence_id), None, "Desfeito pelo chat"
        )
    session.commit()
    _refresh_base(session, user)
    structure = _structure(session, None)
    scope = _scope(session, user, payload)
    return _recalculate(session, user, structure.id, scope.period, [None])


# ------------------------------------------------------------ automations


def _automation(session: Session, text: str) -> TonAutomation:
    try:
        found = session.get(TonAutomation, UUID(text))
        if found is not None:
            return found
    except ValueError:
        pass
    folded = _fold(text)
    rows = [
        row
        for row in session.scalars(sa.select(TonAutomation).where(TonAutomation.status != "ARCHIVED"))
        if folded in _fold(row.name)
    ]
    if len(rows) != 1:
        names = ", ".join(row.name for row in rows[:10]) or "nenhuma"
        raise ValueError(f"Automação “{text}” não identificada. Encontradas: {names}")
    return rows[0]


STATUS_TEXT = {"ACTIVE": "ativa", "PAUSED": "pausada", "DRAFT": "rascunho"}


def _preview_automation_status(
    session: Session, user: User, payload: AutomationStatusPayload
) -> tuple[str, ActionPreview]:
    row = _automation(session, payload.automation)
    if row.status == payload.status:
        raise ValueError(f"A automação já está {STATUS_TEXT.get(row.status, row.status)}")
    return (
        f"{'Ativar' if payload.status == 'ACTIVE' else 'Pausar'} “{row.name}”",
        ActionPreview(
            resumo=[f"Situação: {STATUS_TEXT.get(row.status, row.status)} → {STATUS_TEXT[payload.status]}"],
            avisos=["Uma automação ativa age sozinha nos gatilhos dela (e-mails, alertas)."]
            if payload.status == "ACTIVE"
            else [],
            pode_desfazer=True,
        ),
    )


def _apply_automation_status(
    session: Session, user: User, payload: AutomationStatusPayload
) -> dict[str, Any]:
    row = _automation(session, payload.automation)
    previous = row.status
    automation_service.change_status(session, user, row.id, AutomationStatus(payload.status))
    return {"automacao": str(row.id), "anterior": previous}


def _undo_automation_status(
    session: Session, user: User, payload: AutomationStatusPayload, result: dict[str, Any]
) -> dict[str, Any]:
    target = AutomationStatus(result["anterior"])
    if target is AutomationStatus.DRAFT:
        target = AutomationStatus.PAUSED
    automation_service.change_status(session, user, UUID(result["automacao"]), target)
    return {"situacao": target.value}


def _preview_automation_run(
    session: Session, user: User, payload: AutomationRunPayload
) -> tuple[str, ActionPreview]:
    row = _automation(session, payload.automation)
    return (
        f"{'Testar' if payload.test else 'Executar'} “{row.name}” agora",
        ActionPreview(
            resumo=[
                "Teste: e-mails vão só para você, esperas são puladas e aprovações aprovadas."
                if payload.test
                else "Execução real: os passos agem de verdade (e-mails aos destinatários configurados)."
            ],
        ),
    )


def _apply_automation_run(
    session: Session, user: User, payload: AutomationRunPayload
) -> dict[str, Any]:
    row = _automation(session, payload.automation)
    summary = automation_service.start_manual(session, user, row.id, {}, test=payload.test)
    return {
        "execucao": str(summary.id),
        "situacao": str(summary.status),
        "link": f"/ton/automacoes/{row.id}",
    }

# ------------------------------------------------------- controller rules


def rules_in_force(session: Session) -> list[ControllerRule]:
    """Latest version of every rule, active ones only, by topic."""
    rows = session.scalars(
        sa.select(ControllerRule).order_by(
            ControllerRule.rule_key, ControllerRule.version.desc()
        )
    )
    latest: dict[str, ControllerRule] = {}
    for row in rows:
        latest.setdefault(row.rule_key, row)
    return sorted(
        (row for row in latest.values() if row.active),
        key=lambda row: (row.topic, row.created_at),
    )


def rules_for_chat(session: Session) -> list[dict[str, Any]]:
    return [
        {
            "chave": row.rule_key,
            "tema": row.topic,
            "regra": row.text,
            "versao": row.version,
            "desde": row.created_at.date().isoformat(),
        }
        for row in rules_in_force(session)
    ]


def _rule_key(topic: str, session: Session) -> str:
    base = "-".join(_fold(topic).split())[:60] or "regra"
    taken = set(session.scalars(sa.select(ControllerRule.rule_key).distinct()))
    key, number = base, 2
    while key in taken:
        key, number = f"{base}-{number}", number + 1
    return key


def _current_rule(session: Session, key: str) -> ControllerRule | None:
    return session.scalar(
        sa.select(ControllerRule)
        .where(ControllerRule.rule_key == key)
        .order_by(ControllerRule.version.desc())
        .limit(1)
    )


def _preview_rule(
    session: Session, user: User, payload: ControllerRulePayload
) -> tuple[str, ActionPreview]:
    if not is_ton_administrator(user):
        raise ValueError("Regras da Controladoria exigem administrador")
    current = _current_rule(session, payload.rule_key) if payload.rule_key else None
    if payload.rule_key and current is None:
        raise ValueError(f"A regra {payload.rule_key} não existe")
    if payload.archive:
        if current is None:
            raise ValueError("Informe a regra a esquecer")
        return (
            f"Esquecer a regra “{current.topic}”",
            ActionPreview(resumo=[f"Deixa de valer: {current.text}"], pode_desfazer=True),
        )
    summary = [f"{payload.topic}: {payload.text}"]
    if current is not None:
        summary.insert(0, f"Substitui: {current.text}")
    return (
        f"Lembrar a regra “{payload.topic}”",
        ActionPreview(
            resumo=summary,
            avisos=[
                "Todas as conversas do TON passam a considerar esta regra. Ela não muda valores sozinha."
            ],
            pode_desfazer=True,
        ),
    )


def _apply_rule(
    session: Session, user: User, payload: ControllerRulePayload
) -> dict[str, Any]:
    current = _current_rule(session, payload.rule_key) if payload.rule_key else None
    key = current.rule_key if current else _rule_key(payload.topic, session)
    keep = current is not None and payload.archive
    row = ControllerRule(
        rule_key=key,
        version=(current.version + 1) if current else 1,
        topic=current.topic if keep and current else payload.topic,
        text=current.text if keep and current else payload.text,
        active=not payload.archive,
        created_by=user.id,
    )
    session.add(row)
    session.commit()
    return {"chave": key, "versao": row.version}


def _undo_rule(
    session: Session, user: User, payload: ControllerRulePayload, result: dict[str, Any]
) -> dict[str, Any]:
    key = result["chave"]
    current = _current_rule(session, key)
    if current is None:
        raise ValueError("Regra não encontrada")
    previous = session.scalar(
        sa.select(ControllerRule).where(
            ControllerRule.rule_key == key,
            ControllerRule.version == int(result["versao"]) - 1,
        )
    )
    source = previous or current
    row = ControllerRule(
        rule_key=key,
        version=current.version + 1,
        topic=source.topic,
        text=source.text,
        active=previous.active if previous else False,
        created_by=user.id,
    )
    session.add(row)
    session.commit()
    return {"versao": row.version}

# ----------------------------------------------------------------- ledger


def _bands(values: list[float]) -> tuple[Decimal, Decimal, Decimal]:
    first, second, third = (Decimal(str(value)) for value in values)
    if not first > second > third > 0:
        raise ValueError("As faixas da régua devem ser decrescentes e positivas (ex.: 1; 0,3; 0,1)")
    return first, second, third


def _ledger_plan(session: Session, user: User, payload: LedgerRegisterPayload) -> Any:
    from onyx.db.ton import agent_ledger

    plan = agent_ledger.plan_cases(
        session,
        user,
        payload.test,
        dict(payload.test_parameters),
        payload.keys or None,
        _bands(payload.bands),
        OccurrenceCriticality(payload.criticality) if payload.criticality else None,
    )
    if not plan.cases:
        raise ValueError("O teste não encontrou esses casos agora; rode o teste de novo")
    return plan


def _preview_ledger(
    session: Session, user: User, payload: LedgerRegisterPayload
) -> tuple[str, ActionPreview]:
    from onyx.db.ton import agent_ledger

    plan = _ledger_plan(session, user, payload)
    lines = []
    for case in plan.cases[:30]:
        share = (
            f" · {case.share:.2f}%".replace(".", ",") + f" ({case.payload['base_da_receita']})"
            if case.share is not None
            else " · sem receita no mês para medir"
        )
        lines.append(
            f"{case.title} · {_brl(case.impact)}{share} · {agent_ledger.CRITICALITY_TEXT[case.criticality]}"
        )
    if len(plan.cases) > 30:
        lines.append(f"… e mais {len(plan.cases) - 30}")
    bands = "; ".join(f"{value:g}%".replace(".", ",") for value in payload.bands)
    avisos = [
        f"Criticidade pela régua PAD-CTRL-001 sobre a receita da unidade no mês ({bands}); ao aplicar você aprova estas faixas para estes casos.",
        "Casos já registrados contam como repetição da mesma ocorrência, sem duplicar.",
    ]
    if payload.responsible:
        prazo = f" até {payload.deadline:%d/%m/%Y}" if payload.deadline else ""
        avisos.append(f"Responsável: {payload.responsible}{prazo}.")
    if plan.missing_keys:
        avisos.append(f"{len(plan.missing_keys)} caso(s) pedidos não aparecem mais no teste e ficam de fora.")
    return (
        f"Registrar {len(plan.cases)} ocorrência(s) do {payload.test} no ledger",
        ActionPreview(resumo=lines, avisos=avisos),
    )


def _apply_ledger(
    session: Session, user: User, payload: LedgerRegisterPayload
) -> dict[str, Any]:
    from onyx.db.ton import agent_ledger

    plan = _ledger_plan(session, user, payload)
    outcomes = agent_ledger.register_plan__no_commit(
        session,
        user,
        plan,
        trigger=AnalysisTrigger.INTERACTIVE,
        idempotency_key=f"ton-chat:{uuid4()}",
        routine_code="TON-CHAT",
        responsible=payload.responsible,
        deadline=payload.deadline,
        note=payload.note,
    )
    session.commit()
    return {"ocorrencias": outcomes[:50], "total": len(outcomes), "link": "/ton/ocorrencias"}


def _preview_assign(
    session: Session, user: User, payload: OccurrenceAssignPayload
) -> tuple[str, ActionPreview]:
    if not (payload.responsible or payload.note):
        raise ValueError("Informe o responsável, o prazo ou a nota")
    rows = _occurrences(session, payload.occurrence_ids)
    summary = [f"{row.short_code or ''} {row.title}".strip() for row in rows[:30]]
    if payload.responsible:
        prazo = f" até {payload.deadline:%d/%m/%Y}" if payload.deadline else " (sem prazo)"
        summary.append(f"Responsável: {payload.responsible}{prazo}")
    if payload.note:
        summary.append(f"Nota: {payload.note}")
    return (
        f"Atribuir {len(rows)} ocorrência(s)",
        ActionPreview(
            resumo=summary,
            avisos=["A atribuição anterior fica no histórico; ações vencidas aparecem para o R9."],
        ),
    )


def _apply_assign(
    session: Session, user: User, payload: OccurrenceAssignPayload
) -> dict[str, Any]:
    from onyx.db.ton import agent_ledger

    count = agent_ledger.assign__no_commit(
        session, user, payload.occurrence_ids, payload.responsible, payload.deadline, payload.note
    )
    session.commit()
    return {"atribuidas": count}


TEST_NAMES = {
    "T1": "grupo zerado",
    "T2": "desvio de média",
    "T3": "duplicidade",
    "T4": "receita NG × notas",
    "T6": "sinal invertido",
    "T8": "fornecedor × unidade",
    "T9": "competência retroativa",
    "T10": "não recorrente",
}


def _sweep_time(hour: int) -> str:
    return f"{hour:02d}:00"


def _preview_r1(
    session: Session, user: User, payload: R1SchedulePayload
) -> tuple[str, ActionPreview]:
    from onyx.db.ton import agent_ledger

    if not is_ton_administrator(user):
        raise ValueError("A varredura diária exige administrador")
    _bands(payload.bands)
    current = agent_ledger.r1_automation(session)
    active = current is not None and current.status == "ACTIVE"
    if not payload.enabled:
        if not active:
            raise ValueError("A varredura diária já está desligada")
        return (
            "Pausar a varredura diária (R1)",
            ActionPreview(
                resumo=["A automação “Varredura financeira diária (R1)” fica pausada; nada é apagado."],
                pode_desfazer=True,
            ),
        )
    bands = "; ".join(f"{value:g}%".replace(".", ",") for value in payload.bands)
    return (
        "Ligar a varredura diária (R1)" if not active else "Ajustar a varredura diária (R1)",
        ActionPreview(
            resumo=[
                f"Automação “Varredura financeira diária (R1)”: todo dia às {_sweep_time(payload.hour)} (Brasília) roda "
                + ", ".join(f"{test} ({TEST_NAMES[test]})" for test in payload.tests),
                "Sobre o último mês da base; cada caso vira ocorrência no ledger (repetições não duplicam).",
                f"Criticidade pela régua PAD-CTRL-001: {bands} da receita da unidade.",
                "Quando houver caso novo, avisa no sino do TON. Você pode acrescentar e-mail ou outros passos em Automações.",
                "O gatilho “Casos registrados no ledger” fica disponível para outras automações.",
            ],
            avisos=[
                "Ao aplicar você aprova os testes e as faixas acima como regra da varredura; a automação usa as suas permissões."
            ],
            pode_desfazer=True,
        ),
    )


def _apply_r1(session: Session, user: User, payload: R1SchedulePayload) -> dict[str, Any]:
    from onyx.db.ton import agent_ledger
    from onyx.db.ton import automations as automation_repository
    from onyx.ton.automations.definition import (
        AutomationDefinition,
        AutomationKind,
        AutomationOrigin,
    )
    from onyx.ton.automations.templates import sweep_definition

    current = agent_ledger.r1_automation(session)
    previous_status = current.status if current is not None else None
    if not payload.enabled:
        if current is not None:
            automation_service.change_status(session, user, current.id, AutomationStatus.PAUSED)
        return {"anterior": previous_status, "automacao": str(current.id) if current else None}
    definition = AutomationDefinition.model_validate(
        sweep_definition(
            list(payload.tests),
            _sweep_time(payload.hour),
            (payload.bands[0], payload.bands[1], payload.bands[2]),
        )
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    if current is None:
        current = automation_repository.create__no_commit(
            session,
            user,
            name=agent_ledger.R1_NAME,
            description="Testes financeiros do Prompt Mestre todo dia, casos no ledger e aviso quando há casos novos.",
            kind=AutomationKind.ALERT,
            definition=definition,
            origin=AutomationOrigin.USER,
            status=AutomationStatus.DRAFT,
            now=now,
            seed_key=agent_ledger.R1_SEED_KEY,
        )
        session.commit()
    else:
        automation_repository.add_version__no_commit(
            session,
            user,
            current,
            name=current.name,
            description=current.description,
            kind=AutomationKind.ALERT,
            definition=definition,
            now=now,
            note="Ajustada pelo chat",
        )
        session.commit()
    if current.status != "ACTIVE":
        automation_service.change_status(session, user, current.id, AutomationStatus.ACTIVE)
    return {
        "anterior": previous_status,
        "automacao": str(current.id),
        "link": f"/ton/automacoes/{current.id}",
    }


def _undo_r1(
    session: Session, user: User, payload: R1SchedulePayload, result: dict[str, Any]
) -> dict[str, Any]:
    if not result.get("automacao"):
        return {"restaurado": False}
    target = result.get("anterior")
    status = (
        AutomationStatus.ACTIVE
        if target == "ACTIVE"
        else AutomationStatus.PAUSED
    )
    automation_service.change_status(session, user, UUID(result["automacao"]), status)
    return {"situacao": status.value}



PREVIEWS = {
    ActionKind.DRE_STRUCTURE_CHANGE: _preview_structure,
    ActionKind.DRE_ADJUSTMENT: _preview_adjustment,
    ActionKind.CLOSING_TREATMENT: _preview_treatment,
    ActionKind.DRE_RECALCULATE: _preview_recalculate,
    ActionKind.SOURCE_IMPORT: _preview_import,
    ActionKind.ACCOUNT_CLASSIFICATION: _preview_classification,
    ActionKind.CLASSIFICATION_CONFIRM: _preview_confirm,
    ActionKind.REVIEW_DECISION: _preview_decision,
    ActionKind.UNIT_ASSIGNMENT: _preview_units,
    ActionKind.AUTOMATION_STATUS: _preview_automation_status,
    ActionKind.AUTOMATION_RUN: _preview_automation_run,
    ActionKind.CONTROLLER_RULE: _preview_rule,
    ActionKind.LEDGER_REGISTER: _preview_ledger,
    ActionKind.OCCURRENCE_ASSIGN: _preview_assign,
    ActionKind.R1_SCHEDULE: _preview_r1,
}
APPLIERS = {
    ActionKind.DRE_STRUCTURE_CHANGE: _apply_structure,
    ActionKind.DRE_ADJUSTMENT: _apply_adjustment,
    ActionKind.CLOSING_TREATMENT: _apply_treatment,
    ActionKind.DRE_RECALCULATE: _apply_recalculate,
    ActionKind.SOURCE_IMPORT: _apply_import,
    ActionKind.ACCOUNT_CLASSIFICATION: _apply_classification,
    ActionKind.CLASSIFICATION_CONFIRM: _apply_confirm,
    ActionKind.REVIEW_DECISION: _apply_decision,
    ActionKind.UNIT_ASSIGNMENT: _apply_units,
    ActionKind.AUTOMATION_STATUS: _apply_automation_status,
    ActionKind.AUTOMATION_RUN: _apply_automation_run,
    ActionKind.CONTROLLER_RULE: _apply_rule,
    ActionKind.LEDGER_REGISTER: _apply_ledger,
    ActionKind.OCCURRENCE_ASSIGN: _apply_assign,
    ActionKind.R1_SCHEDULE: _apply_r1,
}
UNDOERS = {
    ActionKind.DRE_STRUCTURE_CHANGE: _undo_structure,
    ActionKind.DRE_ADJUSTMENT: _undo_adjustment,
    ActionKind.CLOSING_TREATMENT: _undo_treatment,
    ActionKind.ACCOUNT_CLASSIFICATION: _undo_classification,
    ActionKind.UNIT_ASSIGNMENT: _undo_units,
    ActionKind.AUTOMATION_STATUS: _undo_automation_status,
    ActionKind.CONTROLLER_RULE: _undo_rule,
    ActionKind.R1_SCHEDULE: _undo_r1,
}


# ---------------------------------------------------------------- public


def propose(
    session: Session,
    user: User,
    kind: ActionKind,
    raw_payload: dict[str, Any],
    chat_session_id: UUID | None,
) -> AgentActionView:
    """Validate and preview one change; raises ValueError in Portuguese."""
    try:
        payload = PAYLOADS[kind].model_validate(raw_payload)
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(item) for item in first["loc"])
        raise ValueError(f"Pedido incompleto ({where}): {first['msg']}") from error
    title, preview = PREVIEWS[kind](session, user, payload)  # type: ignore[operator]
    row = AgentAction(
        chat_session_id=chat_session_id,
        kind=kind.value,
        title=title[:300],
        payload=payload.model_dump(mode="json"),
        preview=preview.model_dump(mode="json"),
        status=ActionStatus.PROPOSED.value,
        proposed_by=user.id,
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    view = _view(row)
    session.commit()
    return view


def _get(session: Session, user: User, action_id: UUID) -> AgentAction:
    row = session.get(AgentAction, action_id, with_for_update=True)
    if row is None or (
        row.proposed_by != user.id and not is_ton_administrator(user)
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Ação não encontrada")
    return row


def _decide(
    session: Session,
    user: User,
    row: AgentAction,
    status: ActionStatus,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> AgentActionView:
    row.status = status.value
    row.decided_by = user.id
    row.decided_at = datetime.datetime.now(datetime.timezone.utc)
    if result is not None:
        row.result = result
    row.error = error
    session.commit()
    return _view(row)


def apply(session: Session, user: User, action_id: UUID) -> AgentActionView:
    row = _get(session, user, action_id)
    if row.status != ActionStatus.PROPOSED:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Esta ação já foi decidida")
    now = datetime.datetime.now(datetime.timezone.utc)
    if row.created_at + EXPIRY < now:
        return _decide(session, user, row, ActionStatus.EXPIRED)
    kind = ActionKind(row.kind)
    payload = PAYLOADS[kind].model_validate(row.payload)
    action_row_id = row.id
    try:
        result = APPLIERS[kind](session, user, payload)  # type: ignore[operator]
    except (ValueError, OnyxError) as error:
        session.rollback()
        message = error.detail if isinstance(error, OnyxError) else str(error)
        row = _get(session, user, action_row_id)
        return _decide(session, user, row, ActionStatus.FAILED, error=message[:1000])
    row = _get(session, user, action_row_id)
    return _decide(session, user, row, ActionStatus.APPLIED, result=result)


def cancel(session: Session, user: User, action_id: UUID) -> AgentActionView:
    row = _get(session, user, action_id)
    if row.status != ActionStatus.PROPOSED:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Esta ação já foi decidida")
    return _decide(session, user, row, ActionStatus.CANCELLED)


def undo(session: Session, user: User, action_id: UUID) -> AgentActionView:
    row = _get(session, user, action_id)
    kind = ActionKind(row.kind)
    if row.status != ActionStatus.APPLIED or kind not in UNDOERS or not row.result:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Esta ação não pode ser desfeita")
    payload = PAYLOADS[kind].model_validate(row.payload)
    result = dict(row.result)
    action_row_id = row.id
    try:
        undone = UNDOERS[kind](session, user, payload, result)  # type: ignore[operator]
    except ValueError as error:
        session.rollback()
        raise OnyxError(OnyxErrorCode.CONFLICT, str(error)) from error
    row = _get(session, user, action_row_id)
    return _decide(
        session, user, row, ActionStatus.UNDONE, result={**result, "desfeito": undone}
    )


def list_for_session(
    session: Session, user: User, chat_session_id: UUID
) -> list[AgentActionView]:
    rows = session.scalars(
        sa.select(AgentAction)
        .where(
            AgentAction.chat_session_id == chat_session_id,
            AgentAction.proposed_by == user.id,
        )
        .order_by(AgentAction.created_at)
    )
    return [_view(row) for row in rows]


def get(session: Session, user: User, action_id: UUID) -> AgentActionView:
    row = session.get(AgentAction, action_id)
    if row is None or (
        row.proposed_by != user.id and not is_ton_administrator(user)
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Ação não encontrada")
    return _view(row)


def structure_for_chat(
    session: Session, user: User, structure_id: UUID | None
) -> dict[str, Any]:
    """The structure as the chat needs it to propose edits: codes, groups,
    where each line reads its values and the naturezas linked to it."""
    try:
        structure = _structure(session, structure_id)
    except ValueError as error:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, str(error)) from error
    version = dre.get_latest_version(session, user, structure.id)
    accounts = {
        account.id: account
        for account in session.scalars(
            sa.select(FinancialAccount).where(
                FinancialAccount.id.in_([item.account_id for item in version.assignments])
            )
        )
    }
    natures: dict[str, list[str]] = {}
    for item in version.assignments:
        account = accounts.get(item.account_id)
        if account is not None:
            natures.setdefault(item.line_code, []).append(f"{account.code} {account.label}")
    lines = []
    for line in sorted(version.lines, key=lambda item: item.position):
        kind = (
            "grupo"
            if line.line_type == DreLineType.SUBTOTAL and line.operation == "SUM_CHILDREN"
            else "linha"
            if line.line_type == DreLineType.SOURCE_SUM
            else "total"
        )
        entry: dict[str, Any] = {
            "codigo": line.code,
            "nome": line.label,
            "tipo": kind,
            "grupo": line.parent_code,
        }
        if kind == "linha":
            entry["origem"] = _source_text(line) or "naturezas do NG"
            linked = natures.get(line.code, [])
            entry["naturezas"] = linked[:15]
            if len(linked) > 15:
                entry["naturezas_a_mais"] = len(linked) - 15
        elif kind == "total":
            entry["formula"] = f"{line.operation} {', '.join(line.operands)}"
        if line.hidden:
            entry["oculta"] = True
        if line.excluded:
            entry["fora_do_resultado"] = True
        lines.append(entry)
    return {
        "estrutura": structure.label,
        "structure_id": str(structure.id),
        "versao": version.number,
        "linhas": lines,
        "campos_de_faturamento": {
            field.value: label for field, label in BILLING_FIELD_LABELS.items()
        },
        "observacao": "Custos e deduções entram com valor negativo; linhas de imposto ou retenção do faturamento usam negate=true.",
        "regras_da_controladoria": rules_for_chat(session),
    }
