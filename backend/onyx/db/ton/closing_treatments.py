"""Closing treatments: append-only versions decided by the Controladoria."""

import datetime
from collections import Counter
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton.acl import is_ton_administrator
from onyx.db.ton.audit import emit_ton_audit_event
from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import (
    BusinessUnit,
    ClosingTreatment,
    FinancialAccount,
    FinancialActualFact,
    FinancialNormalizationRun,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.financial_domain.models import (
    TreatmentCreate,
    TreatmentEffect,
    TreatmentOption,
    TreatmentStatus,
    TreatmentTable,
    TreatmentView,
)
from onyx.ton.financial_domain.treatments import TreatmentRule
from onyx.utils.audit import AuditAction, AuditOutcome

TREATMENT_LOCK = 4433011


def _month(value: datetime.date | None) -> datetime.date | None:
    return value.replace(day=1) if value is not None else None


def treatment_number(session: Session) -> int:
    return int(session.scalar(sa.select(sa.func.max(ClosingTreatment.number))) or 0)


def rules_up_to(session: Session, number: int) -> list[TreatmentRule]:
    return [
        TreatmentRule(
            id=row.id,
            number=row.number,
            treatment_key=row.treatment_key,
            status=TreatmentStatus(row.status),
            effect=TreatmentEffect(row.effect),
            account_id=row.account_id,
            unit_id=row.unit_id,
            period_from=row.period_from,
            period_to=row.period_to,
            target_account_id=row.target_account_id,
        )
        for row in session.scalars(
            sa.select(ClosingTreatment).where(ClosingTreatment.number <= number)
        )
    ]


def versions_in_force(session: Session, number: int) -> list[ClosingTreatment]:
    """Latest version per key up to ``number``, any status, oldest key first."""
    latest = (
        sa.select(
            ClosingTreatment.treatment_key,
            sa.func.max(ClosingTreatment.number).label("number"),
        )
        .where(ClosingTreatment.number <= number)
        .group_by(ClosingTreatment.treatment_key)
        .subquery()
    )
    return list(
        session.scalars(
            sa.select(ClosingTreatment)
            .join(latest, latest.c.number == ClosingTreatment.number)
            .order_by(ClosingTreatment.treatment_key)
        )
    )


def _validate(session: Session, request: TreatmentCreate) -> None:
    def invalid(message: str) -> OnyxError:
        return OnyxError(OnyxErrorCode.INVALID_INPUT, message)

    if request.status is not TreatmentStatus.REVOKED and request.account_id is None:
        raise invalid("Informe a natureza do tratamento")
    if (request.effect is TreatmentEffect.RECLASSIFY) != (
        request.target_account_id is not None
    ):
        raise invalid("Reclassificar exige a natureza de destino, e só ela")
    if request.target_account_id is not None and (
        request.target_account_id == request.account_id
    ):
        raise invalid("A natureza de destino deve ser diferente da de origem")
    if (request.status is TreatmentStatus.BLOCKED) != bool(
        request.required_source and request.required_source.strip()
    ):
        raise invalid("Só tratamento bloqueado informa a fonte que falta")
    if (
        request.status is TreatmentStatus.ACTIVE
        and request.effect is TreatmentEffect.REPLACE_BY_SOURCE
    ):
        raise invalid("Substituir por fonte fica bloqueado até a fonte existir")
    if (
        request.period_from is not None
        and request.period_to is not None
        and request.period_from > request.period_to
    ):
        raise invalid("O período inicial é posterior ao final")
    for account_id in (request.account_id, request.target_account_id):
        if account_id is not None and session.get(FinancialAccount, account_id) is None:
            raise OnyxError(OnyxErrorCode.NOT_FOUND, "Natureza não encontrada")
    if (
        request.unit_id is not None
        and session.get(BusinessUnit, request.unit_id) is None
    ):
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Unidade não encontrada")


def create_treatment(
    session: Session, user: User, request: TreatmentCreate
) -> ClosingTreatment:
    if not is_ton_administrator(user):
        emit_ton_audit_event(
            session,
            action=AuditAction.TON_CLOSING_TREATMENT,
            outcome=AuditOutcome.DENIED,
            actor_user_id=user.id,
            resource_kind=TonAuditResourceKind.CLOSING_TREATMENT,
            extra={"treatment_key": request.treatment_key},
        )
        session.commit()
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY,
            "Registrar tratamento exige permissão da Controladoria",
        )
    _validate(session, request)
    session.execute(sa.text(f"SELECT pg_advisory_xact_lock({TREATMENT_LOCK})"))
    previous = session.scalar(
        sa.select(ClosingTreatment)
        .where(ClosingTreatment.treatment_key == request.treatment_key)
        .order_by(ClosingTreatment.version.desc())
        .limit(1)
    )
    if previous is None and request.status is TreatmentStatus.REVOKED:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Tratamento não encontrado")
    row = ClosingTreatment(
        number=treatment_number(session) + 1,
        treatment_key=request.treatment_key,
        version=(previous.version + 1) if previous else 1,
        title=request.title.strip(),
        status=request.status.value,
        effect=request.effect.value,
        account_id=request.account_id,
        unit_id=request.unit_id,
        period_from=_month(request.period_from),
        period_to=_month(request.period_to),
        target_account_id=request.target_account_id,
        required_source=(
            request.required_source.strip()
            if request.status is TreatmentStatus.BLOCKED and request.required_source
            else None
        ),
        justification=request.justification.strip(),
        evidence=request.evidence.strip(),
        created_by=user.id,
    )
    session.add(row)
    session.flush()
    emit_ton_audit_event(
        session,
        action=AuditAction.TON_CLOSING_TREATMENT,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        resource_kind=TonAuditResourceKind.CLOSING_TREATMENT,
        resource_id=row.id,
        before_state=(
            {"version": previous.version, "status": previous.status}
            if previous
            else None
        ),
        after_state={
            "treatment_key": row.treatment_key,
            "version": row.version,
            "status": row.status,
            "effect": row.effect,
        },
    )
    return row


def _latest_run(session: Session) -> FinancialNormalizationRun | None:
    return session.scalar(
        sa.select(FinancialNormalizationRun)
        .where(FinancialNormalizationRun.status == "SUCCEEDED")
        .order_by(FinancialNormalizationRun.started_at.desc())
        .limit(1)
    )


def _views(session: Session, rows: list[ClosingTreatment]) -> list[TreatmentView]:
    accounts = {
        account.id: account.label
        for account in session.scalars(sa.select(FinancialAccount))
    }
    units = {unit.id: unit.name for unit in session.scalars(sa.select(BusinessUnit))}
    authors = {row.created_by for row in rows if row.created_by}
    emails = {
        user_id: email
        for user_id, email in session.execute(sa.select(User.id, User.email))
        if user_id in authors
    }
    run = _latest_run(session)
    applied: Counter[UUID] = Counter()
    if run is not None:
        for treatment_id, count in session.execute(
            sa.select(FinancialActualFact.treatment_id, sa.func.count())
            .where(
                FinancialActualFact.run_id == run.id,
                FinancialActualFact.treatment_id.is_not(None),
            )
            .group_by(FinancialActualFact.treatment_id)
        ):
            if treatment_id is not None:
                applied[treatment_id] = count
    return [
        TreatmentView(
            id=row.id,
            number=row.number,
            treatment_key=row.treatment_key,
            version=row.version,
            title=row.title,
            status=TreatmentStatus(row.status),
            effect=TreatmentEffect(row.effect),
            account_id=row.account_id,
            account_label=accounts.get(row.account_id) if row.account_id else None,
            unit_id=row.unit_id,
            unit_name=units.get(row.unit_id) if row.unit_id else None,
            period_from=row.period_from,
            period_to=row.period_to,
            target_account_id=row.target_account_id,
            target_account_label=(
                accounts.get(row.target_account_id) if row.target_account_id else None
            ),
            required_source=row.required_source,
            justification=row.justification,
            evidence=row.evidence,
            created_by_email=emails.get(row.created_by) if row.created_by else None,
            created_at=row.created_at,
            applied_fact_count=(
                applied.get(row.id, 0)
                if run is not None and row.number <= run.treatment_number
                else None
            ),
        )
        for row in rows
    ]


def treatment_table(session: Session, user: User) -> TreatmentTable:
    """Current version of every treatment, newest decision first."""
    if not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.ADMIN_ONLY, "Tratamentos exigem acesso admin")
    number = treatment_number(session)
    rows = versions_in_force(session, number)
    rows.sort(key=lambda row: row.number, reverse=True)
    run = _latest_run(session)
    return TreatmentTable(
        treatments=_views(session, rows),
        accounts=[
            TreatmentOption(id=account.id, label=account.label)
            for account in session.scalars(
                sa.select(FinancialAccount).order_by(FinancialAccount.label)
            )
        ],
        units=[
            TreatmentOption(id=unit.id, label=unit.name)
            for unit in session.scalars(
                sa.select(BusinessUnit).order_by(BusinessUnit.name)
            )
        ],
        normalization_run_id=run.id if run else None,
        changes_since_calculation=(
            int(
                session.scalar(
                    sa.select(sa.func.count()).where(
                        ClosingTreatment.number > run.treatment_number
                    )
                )
                or 0
            )
            if run
            else 0
        ),
    )


def treatment_history(
    session: Session, user: User, treatment_key: str
) -> list[TreatmentView]:
    if not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.ADMIN_ONLY, "Tratamentos exigem acesso admin")
    rows = list(
        session.scalars(
            sa.select(ClosingTreatment)
            .where(ClosingTreatment.treatment_key == treatment_key)
            .order_by(ClosingTreatment.version.desc())
        )
    )
    if not rows:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Tratamento não encontrado")
    return _views(session, rows)
