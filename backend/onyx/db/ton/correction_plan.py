"""The correction plan: occurrences grouped into cases people can act on.

The occurrence ledger keeps one occurrence per detected item; a person acts on
"the 23 repeated launches of July", not on 23 lines. A case groups one rule's
occurrences from one source and unit. Its state comes from two places:

* the ledger, for the facts: what was detected, in which import, and whether
  the next import verified it gone (``Occurrence.verification_result``);
* this module's tables, for what people decide: owner, deadline, action,
  accepted risk, the board summary.

"Fixed" is never typed by a person. A case closes only when the ledger has
verified every item absent in a later import.
"""

import datetime
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from onyx.db.models import User
from onyx.db.ton.acl import is_ton_administrator
from onyx.db.ton.models import (
    CorrectionCase,
    CorrectionCaseEvent,
    FinancialBillingFact,
    FinancialNormalizationRun,
    Finding,
    FindingEvidence,
    Occurrence,
    OccurrenceEvent,
    ParsedSourceRecord,
    RecordUnitAssignment,
    ReviewRun,
    Rule,
    RuleVersion,
    SourceSnapshot,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.ton.correction import rules
from onyx.ton.correction.catalog import OWNER_AREAS, text_for
from onyx.ton.correction.models import (
    ActionRequest,
    BoardItem,
    BoardRequest,
    BoardSummary,
    CaseDetail,
    CaseOrigin,
    CaseRow,
    DecisionRequest,
    EvidenceRow,
    OwnerRequest,
    ReminderDraft,
    ReminderRequest,
    TimelineItem,
)

BRT = datetime.timezone(datetime.timedelta(hours=-3))
MONTHS = [
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
]
MONTH_NAMES = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]
MAX_EVIDENCE = 300


def _today() -> datetime.date:
    return datetime.datetime.now(BRT).date()


def _require_admin(user: User) -> None:
    if not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.INSUFFICIENT_PERMISSIONS,
            "O plano de correção é da Controladoria.",
        )


def _brl(value: Decimal) -> str:
    text = f"{value:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def _brl_short(value: Decimal) -> str:
    if value >= Decimal("1000000"):
        return f"R$ {value / Decimal('1000000'):.2f} mi".replace(".", ",")
    if value >= Decimal("1000"):
        return f"R$ {value / Decimal('1000'):.1f} mil".replace(".", ",")
    return _brl(value)


def _amount(payload: dict) -> Decimal | None:
    raw = (payload.get("impact") or {}).get("amount")
    if raw in (None, ""):
        return None
    try:
        return abs(Decimal(str(raw))).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _sheet_month(sheet: str | None) -> int | None:
    if not sheet:
        return None
    head = sheet.strip()[:3].lower()
    return MONTHS.index(head) + 1 if head in MONTHS else None


@dataclass
class _Member:
    occurrence: Occurrence
    rule_code: str
    rule_title: str
    payload: dict
    finding_id: UUID
    source_id: str | None
    snapshot_id: UUID | None
    first_detected_at: datetime.datetime
    impact: Decimal | None
    sheet: str | None
    month: datetime.date | None = None
    records: list[ParsedSourceRecord] = field(default_factory=list)

    @property
    def fixed(self) -> bool:
        occurrence = self.occurrence
        return (
            occurrence.verification_result == "PASSED"
            and occurrence.verification_checked_at is not None
            and occurrence.verification_checked_at >= occurrence.last_detected_at
        )


def _case_key(member: _Member) -> str:
    unit = member.occurrence.business_unit_id
    return f"{member.occurrence.rule_id}:{member.source_id or '-'}:{unit or '-'}"


def _load_members(session: Session, with_records: bool) -> list[_Member]:
    occurrences = list(
        session.scalars(
            sa.select(Occurrence).where(
                Occurrence.superseded_by_occurrence_id.is_(None)
            )
        )
    )
    if not occurrences:
        return []
    ids = [occurrence.id for occurrence in occurrences]
    rules_by_id = {
        rule.id: rule
        for rule in session.scalars(
            sa.select(Rule).where(Rule.id.in_({o.rule_id for o in occurrences}))
        )
    }
    titles = {
        version.id: version.title
        for version in session.scalars(
            sa.select(RuleVersion).where(
                RuleVersion.id.in_({o.current_rule_version_id for o in occurrences})
            )
        )
    }
    latest = {
        row.occurrence_id: row
        for row in session.execute(
            sa.select(
                Finding.occurrence_id,
                Finding.id,
                Finding.deterministic_payload,
                Finding.period_start,
                ReviewRun.source_id,
                ReviewRun.snapshot_id,
            )
            .outerjoin(ReviewRun, ReviewRun.analysis_run_id == Finding.analysis_run_id)
            .where(Finding.occurrence_id.in_(ids))
            .order_by(
                Finding.occurrence_id, Finding.detected_at.desc(), Finding.id.desc()
            )
            .distinct(Finding.occurrence_id)
        )
    }
    members: list[_Member] = []
    for occurrence in occurrences:
        row = latest.get(occurrence.id)
        if row is None:
            continue
        payload = row.deterministic_payload or {}
        rule = rules_by_id[occurrence.rule_id]
        member = _Member(
            occurrence=occurrence,
            rule_code=rule.code,
            rule_title=titles.get(occurrence.current_rule_version_id, rule.code),
            payload=payload,
            finding_id=row.id,
            source_id=str(row.source_id) if row.source_id else payload.get("source_id"),
            snapshot_id=row.snapshot_id,
            first_detected_at=occurrence.first_detected_at,
            impact=_amount(payload),
            sheet=(payload.get("facts") or {}).get("sheet_name"),
        )
        if row.period_start:
            member.month = row.period_start.replace(day=1)
        members.append(member)
    by_finding = {member.finding_id: member for member in members}
    record_rows = session.execute(
        sa.select(FindingEvidence.finding_id, ParsedSourceRecord)
        .join(
            ParsedSourceRecord,
            ParsedSourceRecord.id == FindingEvidence.parsed_record_id,
        )
        .where(FindingEvidence.finding_id.in_(list(by_finding)))
        .order_by(ParsedSourceRecord.source_row_number)
    ).all()
    for finding_id, record in record_rows:
        member = by_finding[finding_id]
        member.records.append(record)
        if member.month is None:
            member.month = record.emission_date.replace(day=1)
    snapshots = {
        snapshot.id: snapshot
        for snapshot in session.scalars(
            sa.select(SourceSnapshot).where(
                SourceSnapshot.id.in_({m.snapshot_id for m in members if m.snapshot_id})
            )
        )
    }
    for member in members:
        if member.month is None:
            number = _sheet_month(member.sheet)
            snapshot = snapshots.get(member.snapshot_id) if member.snapshot_id else None
            year = (
                snapshot.period_start.year
                if snapshot and snapshot.period_start
                else member.first_detected_at.year
            )
            if number:
                member.month = datetime.date(year, number, 1)
    if not with_records:
        for member in members:
            member.records = member.records[:2]
        return members
    # A duplicate's evidence is the extra copy; the proof needs the row it
    # repeats too ("kept_row_number"), from the same import.
    for member in members:
        kept = (member.payload.get("facts") or {}).get("kept_row_number")
        if not kept or not member.records:
            continue
        copy = member.records[0]
        original = session.scalar(
            sa.select(ParsedSourceRecord).where(
                ParsedSourceRecord.snapshot_id == copy.snapshot_id,
                ParsedSourceRecord.sheet_name == copy.sheet_name,
                ParsedSourceRecord.source_row_number == int(kept),
            )
        )
        if original is not None and original.id not in {r.id for r in member.records}:
            member.records = sorted(
                [original, *member.records], key=lambda record: record.source_row_number
            )
    return members


def _revenue_by_month(session: Session) -> dict[datetime.date, Decimal]:
    run_id = session.scalar(
        sa.select(FinancialNormalizationRun.id)
        .where(FinancialNormalizationRun.status == "SUCCEEDED")
        .order_by(FinancialNormalizationRun.started_at.desc())
        .limit(1)
    )
    if run_id is None:
        return {}
    month = sa.func.date_trunc(
        "month",
        sa.func.coalesce(
            FinancialBillingFact.competence_period, FinancialBillingFact.emission_date
        ),
    )
    return {
        row[0].date() if isinstance(row[0], datetime.datetime) else row[0]: Decimal(
            row[1] or 0
        )
        for row in session.execute(
            sa.select(month, sa.func.sum(FinancialBillingFact.service_amount))
            .where(FinancialBillingFact.run_id == run_id)
            .group_by(month)
        )
    }


def _ensure_cases(
    session: Session, members: list[_Member]
) -> dict[str, CorrectionCase]:
    keys = {_case_key(member): member.occurrence.rule_id for member in members}
    if keys:
        session.execute(
            pg_insert(CorrectionCase)
            .values(
                [{"case_key": key, "rule_id": rule_id} for key, rule_id in keys.items()]
            )
            .on_conflict_do_nothing(index_elements=["case_key"])
        )
        session.commit()
    return {
        case.case_key: case
        for case in session.scalars(
            sa.select(CorrectionCase).where(CorrectionCase.case_key.in_(list(keys)))
        )
    }


def _months_text(months: list[datetime.date]) -> str:
    if not months:
        return ""
    if len(months) == 1:
        return f"em {MONTH_NAMES[months[0].month - 1]}/{months[0].year}"
    first, last = months[0], months[-1]
    span = f"{MONTHS[first.month - 1]}–{MONTHS[last.month - 1]}/{last.year}"
    return f"em {len(months)} meses ({span})"


def _clean_history(text: str | None) -> str:
    if not text:
        return ""
    # NG histories start with the history code: "000030 - RECEBIMENTO …".
    text = re.sub(r"\s+", " ", re.sub(r"^\d+\s*-\s*", "", text.strip()))
    letters = [char for char in text if char.isalpha()]
    # Mostly upper case reads as shouting; sentence case reads as a sentence.
    if letters and sum(char.isupper() for char in letters) / len(letters) > 0.7:
        text = text[:1].upper() + text[1:].lower()
    return text


def _short(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _origin(session: Session, members: list[_Member]) -> CaseOrigin:
    latest = max(members, key=lambda m: m.occurrence.last_detected_at)
    snapshot = (
        session.get(SourceSnapshot, latest.snapshot_id) if latest.snapshot_id else None
    )
    sheets = sorted(
        {m.sheet for m in members if m.sheet},
        key=lambda name: _sheet_month(name) or 99,
    )
    system = (
        "NG · lançamentos financeiros"
        if latest.rule_code.startswith("NGF-")
        else "TON · testes financeiros"
    )
    return CaseOrigin(
        system=system,
        file_name=snapshot.original_filename if snapshot else None,
        imported_at=snapshot.created_at if snapshot else None,
        sheets=sheets,
    )


def _closing_note(session: Session, members: list[_Member]) -> str | None:
    parts = []
    accepted = sum(1 for m in members if m.occurrence.status == "RISK_ACCEPTED")
    confirmed = sum(1 for m in members if m.occurrence.status == "CONFIRMED")
    if accepted:
        parts.append(f"{accepted} aceito(s) para o fechamento em Pendências")
    if confirmed:
        parts.append(f"{confirmed} confirmado(s) pela Controladoria")
    if members[0].rule_code == "NGF-UNIT-MISSING":
        # The latest assignment per entry is in force; one without a unit undoes it.
        latest = (
            sa.select(RecordUnitAssignment.occurrence_id, RecordUnitAssignment.unit_id)
            .where(
                RecordUnitAssignment.occurrence_id.in_(
                    [m.occurrence.id for m in members]
                )
            )
            .order_by(
                RecordUnitAssignment.source_id,
                RecordUnitAssignment.record_key,
                RecordUnitAssignment.created_at.desc(),
            )
            .distinct(RecordUnitAssignment.source_id, RecordUnitAssignment.record_key)
            .subquery()
        )
        assigned = (
            session.scalar(
                sa.select(sa.func.count(sa.distinct(latest.c.occurrence_id))).where(
                    latest.c.unit_id.is_not(None)
                )
            )
            or 0
        )
        if assigned:
            parts.append(f"{assigned} já atribuído(s) a uma unidade no TON")
    return "; ".join(parts) if parts else None


def _row(
    session: Session,
    case: CorrectionCase,
    members: list[_Member],
    revenue: dict[datetime.date, Decimal],
    today: datetime.date,
) -> CaseRow:
    code = members[0].rule_code
    text = text_for(code)
    open_members = [m for m in members if not m.fixed]
    fixed_members = [m for m in members if m.fixed]
    basis = open_members or members
    monthly: dict[datetime.date, Decimal] = defaultdict(Decimal)
    for member in basis:
        if member.month and member.impact:
            monthly[member.month] += member.impact
    months = sorted({m.month for m in basis if m.month})
    level = rules.criticality(
        {
            month: (amount, revenue.get(month, Decimal(0)))
            for month, amount in monthly.items()
        },
        len(months),
    )
    count = len(members)
    noun = text.singular if count == 1 else text.plural
    title = f"{count} {noun} {_months_text(months)}".strip()
    biggest = max(
        (record for m in basis for record in m.records),
        key=lambda record: abs(record.final_amount or 0),
        default=None,
    )
    if biggest is not None and biggest.final_amount:
        summary = f"maior: {_short(_clean_history(biggest.history))} · {_brl(abs(biggest.final_amount))}"
    else:
        rows = sorted(
            {
                str((m.payload.get("facts") or {}).get("row_number"))
                for m in basis
                if (m.payload.get("facts") or {}).get("row_number")
            },
            key=int,
        )
        summary = (
            f"linhas {', '.join(rows[:6])}{'…' if len(rows) > 6 else ''}"
            if rows
            else members[0].rule_title
        )
    situation = rules.situation(
        open_count=len(open_members),
        fixed_count=len(fixed_members),
        decision=case.decision,
        owner=case.owner_area,
        due_date=case.due_date,
        today=today,
    )
    verified_at = (
        max(
            m.occurrence.verification_checked_at
            for m in fixed_members
            if m.occurrence.verification_checked_at
        )
        if fixed_members and not open_members
        else None
    )
    return CaseRow(
        id=case.id,
        number=case.number,
        rule_code=code,
        title=title[:1].upper() + title[1:],
        summary=summary,
        owner_area=case.owner_area,
        owner_name=case.owner_name,
        suggested_area=text.owner_area,
        due_date=case.due_date,
        situation=situation.code,
        situation_label=situation.label,
        criticality=level.level,
        criticality_label=rules.CRITICALITY_LABEL[level.level],
        criticality_reason=level.reason,
        impact_open=sum((m.impact or Decimal(0) for m in open_members), Decimal(0)),
        impact_total=sum((m.impact or Decimal(0) for m in members), Decimal(0)),
        has_amount=any(m.impact for m in members),
        member_count=count,
        open_count=len(open_members),
        fixed_count=len(fixed_members),
        months=[f"{MONTHS[m.month - 1]}/{str(m.year)[2:]}" for m in months],
        recurring=len(months) >= 2,
        origin=_origin(session, members),
        first_detected_at=min(m.occurrence.first_detected_at for m in members),
        last_detected_at=max(m.occurrence.last_detected_at for m in members),
        verified_at=verified_at,
        closing_note=_closing_note(session, members),
        in_board_summary=case.in_board_summary,
    )


def _grouped(
    session: Session, with_records: bool
) -> tuple[list[tuple[CorrectionCase, list[_Member]]], dict[datetime.date, Decimal]]:
    members = _load_members(session, with_records)
    cases = _ensure_cases(session, members)
    groups: dict[str, list[_Member]] = defaultdict(list)
    for member in members:
        groups[_case_key(member)].append(member)
    return [(cases[key], items) for key, items in groups.items()], _revenue_by_month(
        session
    )


def list_cases(session: Session, user: User) -> list[CaseRow]:
    _require_admin(user)
    today = _today()
    groups, revenue = _grouped(session, with_records=False)
    rows = [_row(session, case, items, revenue, today) for case, items in groups]
    rows.sort(
        key=lambda row: (
            row.situation == "VERIFIED",
            row.situation == "ACCEPTED",
            rules.CRITICALITY_ORDER[row.criticality],
            -row.impact_open,
        )
    )
    return rows


def _case_members(
    session: Session, case_id: UUID
) -> tuple[CorrectionCase, list[_Member], dict[datetime.date, Decimal]]:
    case = session.get(CorrectionCase, case_id)
    if case is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Caso não encontrado.")
    groups, revenue = _grouped(session, with_records=True)
    for candidate, items in groups:
        if candidate.id == case.id:
            return case, items, revenue
    raise OnyxError(
        OnyxErrorCode.NOT_FOUND, "Este caso não tem mais ocorrências no ledger."
    )


def _evidence(members: list[_Member]) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []
    for member in sorted(
        members,
        key=lambda m: (
            m.fixed,
            -(m.impact or Decimal(0)),
            m.month or datetime.date.min,
        ),
    ):
        facts = member.payload.get("facts") or {}
        status = "FIXED" if member.fixed else "OPEN"
        code = member.occurrence.short_code
        if member.records:
            rows.extend(
                EvidenceRow(
                    occurrence_code=code,
                    status=status,
                    sheet=record.sheet_name,
                    row=record.source_row_number,
                    column=None,
                    emission=record.emission_date,
                    unit=record.administrative_unit,
                    document=record.document_number,
                    history=_clean_history(record.history),
                    account=f"{record.account_code} {record.account_label}".strip(),
                    amount=record.final_amount.quantize(Decimal("0.01"))
                    if record.final_amount is not None
                    else None,
                    group=code if len(member.records) > 1 else None,
                )
                for record in member.records
            )
        else:
            rows.append(
                EvidenceRow(
                    occurrence_code=code,
                    status=status,
                    sheet=member.sheet,
                    row=facts.get("row_number"),
                    column=facts.get("column"),
                    emission=None,
                    unit=None,
                    document=facts.get("document_number"),
                    history=None,
                    account=None,
                    amount=member.impact,
                    group=None,
                )
            )
    return rows


def _timeline(
    session: Session, case: CorrectionCase, members: list[_Member]
) -> list[TimelineItem]:
    items: list[TimelineItem] = []
    ids = [m.occurrence.id for m in members]
    detections = session.execute(
        sa.select(
            ReviewRun.snapshot_id,
            SourceSnapshot.original_filename,
            SourceSnapshot.created_at,
            sa.func.count(sa.distinct(Finding.occurrence_id)),
        )
        .join(ReviewRun, ReviewRun.analysis_run_id == Finding.analysis_run_id)
        .join(SourceSnapshot, SourceSnapshot.id == ReviewRun.snapshot_id)
        .where(Finding.occurrence_id.in_(ids))
        .group_by(
            ReviewRun.snapshot_id,
            SourceSnapshot.original_filename,
            SourceSnapshot.created_at,
        )
        .order_by(SourceSnapshot.created_at)
    ).all()
    for index, (_, name, at, count) in enumerate(detections):
        items.append(
            TimelineItem(
                at=at,
                kind="DETECTED" if index == 0 else "SEEN_AGAIN",
                label="Detectado" if index == 0 else "Visto de novo",
                detail=f'arquivo "{name}" · {count} {"item" if count == 1 else "itens"}',
                actor=None,
            )
        )
    verified = session.execute(
        sa.select(OccurrenceEvent.context, OccurrenceEvent.occurred_at)
        .where(
            OccurrenceEvent.occurrence_id.in_(ids),
            OccurrenceEvent.context["verification_result"].astext == "PASSED",
        )
        .order_by(OccurrenceEvent.occurred_at)
    ).all()
    by_snapshot: dict[str, tuple[datetime.datetime, int]] = {}
    for context, at in verified:
        key = str(context.get("not_detected_in_snapshot_id"))
        first, count = by_snapshot.get(key, (at, 0))
        by_snapshot[key] = (min(first, at), count + 1)
    for key, (at, count) in by_snapshot.items():
        snapshot = (
            session.get(SourceSnapshot, UUID(key)) if key not in ("None", "") else None
        )
        items.append(
            TimelineItem(
                at=at,
                kind="VERIFIED",
                label="Verificado pelo TON: não está mais na origem",
                detail=(
                    f'arquivo "{snapshot.original_filename}" · {count} {"item corrigido" if count == 1 else "itens corrigidos"}'
                    if snapshot
                    else f"{count} itens corrigidos"
                ),
                actor=None,
            )
        )
    people = {
        user.id: user.personal_name or user.email
        for user in session.scalars(
            sa.select(User).where(
                User.id.in_(
                    sa.select(CorrectionCaseEvent.actor_id).where(
                        CorrectionCaseEvent.case_id == case.id
                    )
                )
            )
        ).unique()
    }
    labels = {
        "OWNER": "Responsável definido",
        "ACTION": "Ação alterada",
        "ACCEPT_RISK": "Risco aceito",
        "REOPEN": "Reaberto",
        "BOARD_IN": "Incluído no resumo da diretoria",
        "BOARD_OUT": "Retirado do resumo da diretoria",
    }
    items.extend(
        TimelineItem(
            at=event.created_at,
            kind="PEOPLE",
            label=labels.get(event.action, event.action),
            detail=event.detail,
            actor=people.get(event.actor_id) if event.actor_id else None,
        )
        for event in session.scalars(
            sa.select(CorrectionCaseEvent).where(CorrectionCaseEvent.case_id == case.id)
        )
    )
    return sorted(items, key=lambda item: item.at)


def get_case(session: Session, user: User, case_id: UUID) -> CaseDetail:
    _require_admin(user)
    case, members, revenue = _case_members(session, case_id)
    row = _row(session, case, members, revenue, _today())
    text = text_for(row.rule_code)
    evidence = _evidence(members)
    return CaseDetail(
        **row.model_dump(),
        found=text.found,
        matters=text.matters,
        cause=text.cause,
        action=case.action_text or text.action,
        action_is_default=case.action_text is None,
        verify=text.verify,
        impact_basis=text.impact_basis,
        rule_title=members[0].rule_title,
        decision_reason=case.decision_reason,
        evidence=evidence[:MAX_EVIDENCE],
        evidence_total=len(evidence),
        timeline=_timeline(session, case, members),
        owner_areas=list(OWNER_AREAS),
    )


def _event(
    session: Session, case: CorrectionCase, user: User, action: str, detail: str | None
) -> None:
    session.add(
        CorrectionCaseEvent(
            case_id=case.id, action=action, detail=detail, actor_id=user.id
        )
    )


def set_owner(session: Session, user: User, request: OwnerRequest) -> list[CaseRow]:
    _require_admin(user)
    today = _today()
    rows = {row.id: row for row in list_cases(session, user)}
    for case_id in request.ids:
        case = session.get(CorrectionCase, case_id)
        row = rows.get(case_id)
        if case is None or row is None:
            continue
        case.owner_area = request.owner_area.strip()
        case.owner_name = (request.owner_name or "").strip() or None
        case.due_date = request.due_date or rules.default_due_date(
            row.criticality, today
        )
        who = " · ".join(part for part in (case.owner_area, case.owner_name) if part)
        _event(session, case, user, "OWNER", f"{who}, prazo {case.due_date:%d/%m/%Y}")
    session.commit()
    return [row for row in list_cases(session, user) if row.id in set(request.ids)]


def set_action(
    session: Session, user: User, case_id: UUID, request: ActionRequest
) -> CaseDetail:
    _require_admin(user)
    case = session.get(CorrectionCase, case_id)
    if case is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Caso não encontrado.")
    case.action_text = (request.action_text or "").strip() or None
    _event(session, case, user, "ACTION", case.action_text or "Ação sugerida pelo TON")
    session.commit()
    return get_case(session, user, case_id)


def decide(
    session: Session, user: User, case_id: UUID, request: DecisionRequest
) -> CaseDetail:
    _require_admin(user)
    case = session.get(CorrectionCase, case_id)
    if case is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Caso não encontrado.")
    if request.decision == "ACCEPT_RISK":
        case.decision = "RISK_ACCEPTED"
        case.decision_reason = request.reason.strip()
        _event(session, case, user, "ACCEPT_RISK", case.decision_reason)
    else:
        case.decision = None
        case.decision_reason = None
        _event(session, case, user, "REOPEN", request.reason.strip())
    session.commit()
    return get_case(session, user, case_id)


def set_board(session: Session, user: User, request: BoardRequest) -> None:
    _require_admin(user)
    for case_id in request.ids:
        case = session.get(CorrectionCase, case_id)
        if case is None or case.in_board_summary == request.include:
            continue
        case.in_board_summary = request.include
        _event(
            session, case, user, "BOARD_IN" if request.include else "BOARD_OUT", None
        )
    session.commit()


def reminder(
    session: Session, user: User, request: ReminderRequest
) -> list[ReminderDraft]:
    """One message per owner, listing their cases; nothing is sent yet."""
    _require_admin(user)
    wanted = set(request.ids)
    by_owner: dict[str, list[CaseRow]] = defaultdict(list)
    for row in list_cases(session, user):
        if row.id in wanted and row.situation not in ("VERIFIED", "ACCEPTED"):
            owner = " · ".join(
                p for p in (row.owner_area or row.suggested_area, row.owner_name) if p
            )
            by_owner[owner].append(row)
    drafts = []
    for owner, rows in by_owner.items():
        lines = [
            f"- PC-{row.number:04d} · {row.title} · {_brl(row.impact_open)} · "
            f"{row.criticality_label} · prazo {row.due_date:%d/%m/%Y}"
            if row.due_date
            else f"- PC-{row.number:04d} · {row.title} · {_brl(row.impact_open)} · {row.criticality_label} · prazo a definir"
            for row in rows
        ]
        body = (
            f"Olá,\n\nO TON encontrou {len(rows)} {'caso' if len(rows) == 1 else 'casos'} para corrigir na origem:\n\n"
            + "\n".join(lines)
            + "\n\nCada caso tem a lista dos lançamentos, a regra que o encontrou e o que fazer. "
            "Depois da correção, a próxima importação confere e fecha o caso sozinha.\n\nControladoria · TON"
        )
        drafts.append(
            ReminderDraft(
                owner=owner,
                subject=f"TON · {len(rows)} {'caso' if len(rows) == 1 else 'casos'} para corrigir na origem",
                body=body,
                can_send=False,
                why_not="O envio por e-mail começa quando o domínio de envio estiver configurado. Copie a mensagem por enquanto.",
            )
        )
    return drafts


def _month_span(months: list[str]) -> str:
    """ "jan/26, fev/26" or, for more than two, "jan/26 a set/26 (8 meses)"."""
    if len(months) <= 2:
        return " e ".join(months)
    return f"{months[0]} a {months[-1]} ({len(months)} meses)"


def _board_item(row: CaseRow) -> BoardItem:
    text = text_for(row.rule_code)
    if row.situation == "VERIFIED":
        result = f"Corrigido na origem e verificado pelo TON ({_brl_short(row.impact_total)})."
        action = "Concluída: a importação seguinte não tem mais o problema."
    else:
        where = f" em {_month_span(row.months)}" if row.months else ""
        result = (
            f"{_brl_short(row.impact_open)}{where} ainda errados na origem."
            if row.has_amount
            else f"Dados{where} fora da base até a correção."
        )
        owner = " · ".join(p for p in (row.owner_area, row.owner_name) if p)
        who = f"Responsável: {owner}" if owner else "Responsável a definir"
        deadline = f"prazo {row.due_date:%d/%m}" if row.due_date else "prazo a definir"
        action = f"{text.action} {who}, {deadline}."
    return BoardItem(
        case_id=row.id,
        number=row.number,
        criticality=row.criticality,
        result=result,
        problem=f"{row.title}; {row.summary}.",
        impact=f"{row.criticality_label}: {row.criticality_reason}.",
        cause=text.cause,
        action=action,
        verified=row.situation == "VERIFIED",
    )


def board(session: Session, user: User) -> BoardSummary:
    rows = list_cases(session, user)
    month_start = _today().replace(day=1)
    chosen = [row for row in rows if row.in_board_summary] or [
        row
        for row in rows
        if row.criticality in ("CRITICAL", "HIGH") and row.situation != "ACCEPTED"
    ][:5]
    return BoardSummary(
        open_amount=sum(
            (
                r.impact_open
                for r in rows
                if r.situation not in ("VERIFIED", "ACCEPTED")
            ),
            Decimal(0),
        ),
        verified_amount=sum(
            (
                r.impact_total
                for r in rows
                if r.situation == "VERIFIED"
                and r.verified_at
                and r.verified_at.astimezone(BRT).date() >= month_start
            ),
            Decimal(0),
        ),
        recurring=sum(1 for r in rows if r.recurring and r.situation != "VERIFIED"),
        unassigned=sum(1 for r in rows if r.situation == "UNASSIGNED"),
        overdue=sum(1 for r in rows if r.situation == "OVERDUE"),
        items=[_board_item(row) for row in chosen],
    )


def board_xlsx(session: Session, user: User) -> bytes:
    import xlsxwriter

    summary = board(session, user)
    rows = list_cases(session, user)
    output = io.BytesIO()
    book = xlsxwriter.Workbook(output, {"in_memory": True})
    title = book.add_format({"bold": True, "font_size": 14, "font_color": "#145C42"})
    header = book.add_format(
        {
            "bold": True,
            "bg_color": "#145C42",
            "font_color": "#FFFFFF",
            "text_wrap": True,
            "valign": "top",
        }
    )
    wrap = book.add_format({"text_wrap": True, "valign": "top"})
    money = book.add_format({"num_format": "#,##0.00", "valign": "top"})
    sheet = book.add_worksheet("Resumo")
    sheet.write(0, 0, "TON · O que precisa ser corrigido", title)
    sheet.write(
        1,
        0,
        f"Em aberto: {_brl(summary.open_amount)} · corrigido e verificado no mês: {_brl(summary.verified_amount)}",
    )
    for index, (name, width) in enumerate(
        (
            ("Caso", 10),
            ("Resultado", 40),
            ("Problema", 50),
            ("Impacto", 36),
            ("Causa", 36),
            ("Ação", 50),
        )
    ):
        sheet.write(3, index, name, header)
        sheet.set_column(index, index, width)
    for offset, item in enumerate(summary.items, start=4):
        for index, value in enumerate(
            (
                f"PC-{item.number:04d}",
                item.result,
                item.problem,
                item.impact,
                item.cause,
                item.action,
            )
        ):
            sheet.write(offset, index, value, wrap)
    cases = book.add_worksheet("Todos os casos")
    columns = (
        ("Caso", 10),
        ("Situação", 22),
        ("Criticidade", 14),
        ("Caso", 50),
        ("Em aberto (R$)", 16),
        ("Total (R$)", 16),
        ("Meses", 24),
        ("Responsável", 26),
        ("Prazo", 12),
        ("Origem", 44),
    )
    for index, (name, width) in enumerate(columns):
        cases.write(0, index, name, header)
        cases.set_column(index, index, width)
    for offset, row in enumerate(rows, start=1):
        cases.write(offset, 0, f"PC-{row.number:04d}", wrap)
        cases.write(offset, 1, row.situation_label, wrap)
        cases.write(offset, 2, row.criticality_label, wrap)
        cases.write(offset, 3, row.title, wrap)
        cases.write_number(offset, 4, float(row.impact_open), money)
        cases.write_number(offset, 5, float(row.impact_total), money)
        cases.write(offset, 6, ", ".join(row.months), wrap)
        cases.write(
            offset,
            7,
            " · ".join(p for p in (row.owner_area, row.owner_name) if p) or "—",
            wrap,
        )
        cases.write(
            offset, 8, row.due_date.strftime("%d/%m/%Y") if row.due_date else "—", wrap
        )
        cases.write(
            offset,
            9,
            f"{row.origin.system} · {row.origin.file_name or ''} · {', '.join(row.origin.sheets)}",
            wrap,
        )
    book.close()
    return output.getvalue()
