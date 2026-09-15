"""Persistent best-effort TON audit (Plan 003d).

Readiness §11 divides audit into two layers with two different guarantees, and
the division is the whole design:

============================== ============================================
Layer                          Guarantee
============================== ============================================
**domain history** —           **transactional**. Part of the business
``OccurrenceEvent``,           transaction. It **must raise** on failure, and
``OccurrenceAssignment``,      the business operation fails with it.
``OccurrenceNote``,
``FindingInterpretation``,
``RuleVersion``,
``TonReportRevision``
**``TonAuditEvent``** —        **best-effort**. It **never raises** into the
actor attribution                 caller. A failed audit write does not undo a
                               valid published revision.
============================== ============================================

A lost lifecycle transition is data loss, so it fails loudly. A lost audit line
must not break a user's action. Reversing either direction is a defect: making
audit transactional turns an audit outage into an outage of the product, and
making domain history best-effort silently loses evidence.

**Why a SAVEPOINT.** In PostgreSQL a failed statement aborts the whole
transaction, so a naive ``try/except`` around ``session.add`` would swallow the
exception and then leave the caller unable to commit anything — the business
operation would still be destroyed, just less visibly.
:func:`emit_ton_audit_event` therefore writes inside ``begin_nested()``. The
rollback is scoped to the savepoint, and the caller's transaction survives intact.

**A reference, not a copy.** Readiness §11's anti-duplication rule: when the fact
is already an immutable domain row, this stores ``resource_kind``,
``resource_id`` and ``domain_event_id`` and stops. The domain table stays the
source of truth. :data:`SENSITIVE_KEY_FRAGMENTS` additionally strips anything
that looks like a secret or like raw evidence out of the metadata before writing.

**Additive.** ``onyx.utils.audit.emit_audit_event`` is untouched and keeps writing
its stdout line for SIEM export. This module is a second sink, not a replacement,
and 003d performs no global logging refactor.
"""

import datetime
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.ton.enums import TonAuditResourceKind
from onyx.db.ton.models import TonAuditEvent
from onyx.utils.audit import (
    AUDIT_SCHEMA_VERSION,
    AuditAction,
    AuditActor,
    AuditOutcome,
    ocsf_class_for,
)
from onyx.utils.logger import setup_logger

logger = setup_logger()

# Key fragments that must never reach a stored audit payload. Two categories,
# both refused rather than truncated:
#
# * secrets — an audit row is widely readable by design, so a credential in it is
#   a credential published;
# * raw business evidence — the point of an audit event is to *reference* the
#   authoritative row, and copying a canonical payload or an evidence excerpt in
#   here would create a second, unversioned copy of published material that no
#   immutability rule protects.
SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "secret",
    "password",
    "token",
    "api_key",
    "apikey",
    "credential",
    "private_key",
    "authorization_header",
    "canonical_payload",
    "raw_",
    "evidence_content",
    "excerpt",
    "transcript",
    "prompt",
    "hashed_password",
)

# A redacted value is left behind rather than the key silently vanishing, so a
# reader can tell the difference between "not recorded" and "refused".
REDACTED = "[redacted]"

# Long free text in an audit row is either a copy of domain content or an
# accident. Truncated with a marker so the row stays a reference.
MAX_VALUE_LENGTH = 512


def emit_ton_audit_event(
    db_session: Session,
    *,
    action: AuditAction,
    outcome: AuditOutcome,
    actor: AuditActor | None = None,
    actor_user_id: UUID | None = None,
    resource_kind: TonAuditResourceKind | None = None,
    resource_id: UUID | None = None,
    domain_event_id: UUID | None = None,
    authorization_reference: str | None = None,
    before_state: Mapping[str, Any] | None = None,
    after_state: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
    occurred_at: datetime.datetime | None = None,
) -> TonAuditEvent | None:
    """Record one attributed TON action. **Never raises.**

    Returns the row on success and ``None`` when persistence failed, so a caller
    that wants to know can check — but a caller that ignores the result is correct
    too, which is the point.

    The write happens in a SAVEPOINT. On failure the savepoint is rolled back, the
    failure is logged for an operator, and the caller's transaction is left exactly
    as it was. A business operation therefore completes whether or not its audit
    row survived.

    ``actor`` accepts the existing :class:`~onyx.utils.audit.AuditActor`, so a
    call site that already built one for the stdout stream reuses it.
    ``actor_user_id`` is separate because the stored column is a real foreign key
    and ``AuditActor.user_id`` is a string.
    """
    try:
        with db_session.begin_nested():
            event = TonAuditEvent(
                audit_schema_version=AUDIT_SCHEMA_VERSION,
                occurred_at=occurred_at or datetime.datetime.now(datetime.UTC),
                action=action.value,
                outcome=outcome.value,
                ocsf_class=_ocsf_class_value(action),
                tenant_id=_safe_tenant_id(),
                actor_user_id=actor_user_id or _actor_uuid(actor),
                actor_email=actor.email if actor else None,
                actor_api_key_id=actor.api_key_id if actor else None,
                actor_auth_type=actor.auth_type if actor else None,
                resource_kind=resource_kind,
                resource_id=resource_id,
                domain_event_id=domain_event_id,
                authorization_reference=authorization_reference,
                before_state=sanitize_audit_metadata(before_state),
                after_state=sanitize_audit_metadata(after_state),
                extra=sanitize_audit_metadata(extra) or {},
            )
            db_session.add(event)
            db_session.flush()
        return event
    except Exception:
        # Deliberately broad. Anything at all — a constraint, a dead connection, a
        # serialisation failure — must stay inside this function. The operator
        # still learns about it through the log; the caller does not.
        logger.warning(
            "TON audit event could not be persisted; the business operation "
            "continues. action=%s resource_kind=%s resource_id=%s",
            action.value,
            resource_kind.value if resource_kind else None,
            resource_id,
            exc_info=True,
        )
        return None


def sanitize_audit_metadata(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Strip secrets and raw evidence out of audit metadata.

    Recursive, because a nested mapping hides a key just as well as a top-level
    one. Returns ``None`` for ``None`` so an absent before/after stays absent
    rather than becoming an empty object.
    """
    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        raise ValueError("Audit metadata must be a mapping.")
    return {
        str(key): _sanitize_value(str(key), value) for key, value in payload.items()
    }


def fetch_audit_events(
    db_session: Session,
    *,
    resource_kind: TonAuditResourceKind | None = None,
    resource_id: UUID | None = None,
    action: AuditAction | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[TonAuditEvent]:
    """Audit rows, newest first, optionally narrowed to one resource or action.

    Unfiltered by authorization on purpose: this is the data-access layer, and
    audit rows may carry PII, so a caller exposing them must apply the TON
    resource ACL from :mod:`onyx.db.ton.acl` for the resource in question. 003d
    creates no route, so there is no unprotected surface here.

    Ordered by ``(occurred_at, id)``: the timestamp alone is not a total order,
    and an unstable sort makes pagination return duplicates.
    """
    stmt = select(TonAuditEvent)
    if resource_kind is not None:
        stmt = stmt.where(TonAuditEvent.resource_kind == resource_kind)
    if resource_id is not None:
        stmt = stmt.where(TonAuditEvent.resource_id == resource_id)
    if action is not None:
        stmt = stmt.where(TonAuditEvent.action == action.value)
    stmt = stmt.order_by(TonAuditEvent.occurred_at.desc(), TonAuditEvent.id).offset(
        offset
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db_session.scalars(stmt).all())


def _ocsf_class_value(action: AuditAction) -> str | None:
    ocsf_class = ocsf_class_for(action)
    return ocsf_class.value if ocsf_class else None


def _actor_uuid(actor: AuditActor | None) -> UUID | None:
    if actor is None or actor.user_id is None:
        return None
    try:
        return UUID(actor.user_id)
    except ValueError:
        # An API-key or service actor may carry a non-UUID identity. The textual
        # columns still record it; the foreign key simply stays empty.
        return None


def _safe_tenant_id() -> str | None:
    try:
        from shared_configs.contextvars import get_current_tenant_id

        return get_current_tenant_id()
    except Exception:
        return None


def _sanitize_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(inner_key): _sanitize_value(str(inner_key), inner_value)
            for inner_key, inner_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(key, item) for item in value]
    if isinstance(value, str) and len(value) > MAX_VALUE_LENGTH:
        return value[:MAX_VALUE_LENGTH] + "[truncated]"
    if isinstance(value, (UUID, datetime.datetime, datetime.date)):
        return str(value)
    return value
