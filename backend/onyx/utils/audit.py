"""Structured, SIEM-exportable audit-event subsystem (log-only).

Emits one JSON line per security-relevant action (auth, admin-config /
access-control change, credential access) on the ``onyx.audit`` logger tree.
Field names and the action taxonomy are shaped toward OCSF so the stream maps
onto OCSF event classes (Authentication / Account Change / User Access
Management / Group Management / API Activity) and drops into any SIEM. See
``docs/AUDIT_LOGGING.md`` for the schema + export path.

Invariants (from the ``credential_audit`` seed): never raise into the caller
(emission sits on hot paths), never log a secret, always tenant-tag, and dedup
hot event classes via Redis (degrade to always-emit if Redis is down).
"""

import json
import logging
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

AUDIT_SCHEMA_VERSION = "1.0"

# Root of the audit logger tree; children propagate up to the dedicated stdout
# handler configured in ``_configure_audit_logging``.
AUDIT_LOGGER_ROOT = "onyx.audit"
AUDIT_HANDLER_NAME = "onyx_audit_stdout"

# Diagnostics logger for the subsystem's own failures. Deliberately NOT under
# ``onyx.audit`` so internal warnings never land in the parsed audit stream.
_internal_logger = logging.getLogger(__name__)

_DEFAULT_DEDUP_TTL_SECONDS = 600


class OCSFEventClass(str, Enum):
    """OCSF event class carried on every event (lets consumers route by class)."""

    AUTHENTICATION = "authentication"  # OCSF class_uid 3002
    ACCOUNT_CHANGE = "account_change"  # OCSF class_uid 3001
    USER_ACCESS_MANAGEMENT = "user_access_management"  # OCSF class_uid 3005
    GROUP_MANAGEMENT = "group_management"  # OCSF class_uid 3006
    API_ACTIVITY = "api_activity"  # OCSF class_uid 6003


class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"  # authn/authz refusal, distinct from an operational error


class AuditAction(str, Enum):
    """Audited-action taxonomy. Values are an append-only schema contract
    (consumers filter on them)."""

    # Authentication
    LOGIN = "auth.login"
    LOGIN_FAILURE = "auth.login_failure"
    LOGOUT = "auth.logout"
    REGISTER = "auth.register"
    PASSWORD_FORGOT = "auth.password_forgot"
    PASSWORD_RESET = "auth.password_reset"
    EMAIL_VERIFY = "auth.email_verify"
    IMPERSONATE = "auth.impersonate"  # cloud superuser assuming another user's session

    # Account change
    USER_CREATE = "user.create"
    USER_DELETE = "user.delete"
    USER_DEACTIVATE = "user.deactivate"
    USER_REACTIVATE = "user.reactivate"

    # User access management
    USER_ROLE_CHANGE = "user.role_change"
    USER_CRAFT_ACCESS_CHANGE = "user.craft_access_change"

    # Group management
    USER_GROUP_CHANGE = "user.group_change"
    USER_GROUP_CREATE = "user_group.create"
    USER_GROUP_RENAME = "user_group.rename"
    USER_GROUP_DELETE = "user_group.delete"
    USER_GROUP_PERMISSION_CHANGE = "user_group.permission_change"
    USER_GROUP_MANAGER_CHANGE = "user_group.manager_change"

    # API activity (admin config + resource CRUD)
    CRAFT_DEFAULT_CHANGE = "settings.craft_default_change"
    SECURITY_SETTINGS_CHANGE = "settings.security_settings_change"
    CONTEXTUAL_RAG_MODEL_UPDATE = "search_settings.contextual_rag_model_update"
    LLM_PROVIDER_CREATE = "llm_provider.create"
    LLM_PROVIDER_UPDATE = "llm_provider.update"
    LLM_PROVIDER_DELETE = "llm_provider.delete"
    CONNECTOR_CREATE = "connector.create"
    CONNECTOR_UPDATE = "connector.update"
    CONNECTOR_DELETE = "connector.delete"
    CC_PAIR_CREATE = "cc_pair.create"
    CC_PAIR_UPDATE = "cc_pair.update"
    CC_PAIR_DELETE = "cc_pair.delete"
    API_KEY_CREATE = "api_key.create"
    API_KEY_REGENERATE = "api_key.regenerate"
    API_KEY_UPDATE = "api_key.update"
    API_KEY_DELETE = "api_key.delete"
    CREDENTIAL_CREATE = "credential.create"
    CREDENTIAL_UPDATE = "credential.update"
    CREDENTIAL_DELETE = "credential.delete"
    CREDENTIAL_ACCESS = "credential.access"
    # Fires only when a scoped write gate refuses an actor who already holds
    # partial authority, not on every 403.
    PERMISSION_DENIED = "permission.denied"

    # TON attributed actions (Plan 003d). These are the four events readiness §11
    # assigns to the persistent `ton_audit_event` table rather than to a domain
    # history table: the domain row records *what* changed and is transactional,
    # while these record *who* did it and are best-effort. Emitting one does not
    # replace writing the domain row -- see `onyx.db.ton.audit`.
    TON_SOURCE_CREATE = "ton_sources.source_create"
    TON_SOURCE_UPDATE = "ton_sources.source_update"
    TON_IMPORT_START = "ton_sources.import_start"
    TON_SNAPSHOT_CAPTURE = "ton_sources.snapshot_capture"
    TON_DUPLICATE_DETECT = "ton_sources.duplicate_detect"
    TON_IMPORT_SUCCEED = "ton_sources.import_succeed"
    TON_IMPORT_FAIL = "ton_sources.import_fail"
    TON_PROFILE_CREATE = "ton_sources.profile_create"
    TON_PROFILE_EXECUTE = "ton_sources.profile_execute"
    TON_PROFILE_SUCCEED = "ton_sources.profile_succeed"
    TON_PROFILE_PARTIAL = "ton_sources.profile_partial"
    TON_PROFILE_FAIL = "ton_sources.profile_fail"
    TON_REPORT_GENERATE = "ton_report.generate"
    TON_ROUTINE_SCHEDULE_UPDATE = "ton_routine.schedule_update"
    TON_RULE_VERSION_CHANGE = "ton_rule_version.change"
    TON_MANUAL_OVERRIDE = "ton_occurrence.manual_override"
    TON_HUMAN_APPROVAL = "ton_occurrence.human_approval"
    TON_REVIEW_START = "ton_review.start"
    TON_REVIEW_SUCCEED = "ton_review.succeed"
    TON_REVIEW_FAIL = "ton_review.fail"
    TON_REVIEW_VERIFY = "ton_review.verify_correction"
    TON_REVIEW_ACKNOWLEDGE = "ton_review.acknowledge"
    TON_REVIEW_REQUEST_CORRECTION = "ton_review.request_correction"
    TON_REVIEW_JUSTIFY = "ton_review.justify"
    TON_REVIEW_FALSE_POSITIVE = "ton_review.false_positive"
    TON_REVIEW_CONFIRM_CORRECTION = "ton_review.confirm_correction"
    TON_RECOMMENDATION_ACCEPT = "ton_review.recommendation_accept"
    TON_RECOMMENDATION_REJECT = "ton_review.recommendation_reject"
    TON_FINANCIAL_ACCOUNT_CREATE = "ton_financial.account_create"
    TON_FINANCIAL_MAPPING_VERSION = "ton_financial.mapping_version"
    TON_FINANCIAL_AMOUNT_BASIS_VERSION = "ton_financial.amount_basis_version"
    TON_FINANCIAL_CANDIDATE_REJECT = "ton_financial.candidate_reject"
    TON_FINANCIAL_LEGACY_CANDIDATE_IMPORT = "ton_financial.legacy_candidate_import"
    TON_FINANCIAL_RECONCILIATION_DECISION = "ton_financial.reconciliation_decision"
    TON_FINANCIAL_RECOMPUTE_REQUEST = "ton_financial.recompute_request"
    TON_FINANCIAL_NORMALIZE_START = "ton_financial.normalize_start"
    TON_FINANCIAL_NORMALIZE_SUCCEED = "ton_financial.normalize_succeed"
    TON_FINANCIAL_NORMALIZE_FAIL = "ton_financial.normalize_fail"
    TON_ACCOUNT_CLASSIFICATION_REVIEW = "ton_financial.account_classification_review"
    TON_ACCOUNT_CLASSIFICATION_SUGGEST = "ton_financial.account_classification_suggest"
    TON_CLOSING_TREATMENT = "ton_financial.closing_treatment"
    TON_EMAIL_FLOW_CHANGE = "ton_email_flow.change"
    TON_EMAIL_FLOW_SEND = "ton_email_flow.send"
    TON_EMAIL_FLOW_SUGGEST = "ton_email_flow.suggest"
    TON_AUTOMATION_CHANGE = "ton_automation.change"
    TON_AUTOMATION_RUN = "ton_automation.run"
    TON_AUTOMATION_SUGGEST = "ton_automation.suggest"
    TON_FINANCIAL_AUTHORITY_VERSION = "ton_financial.authority_version"
    TON_FINANCIAL_DERIVATION_VERSION = "ton_financial.derivation_version"
    TON_DRE_STRUCTURE_VERSION = "ton_dre.structure_version"
    TON_DRE_CALCULATE_START = "ton_dre.calculate_start"
    TON_DRE_CALCULATE_BLOCKED = "ton_dre.calculate_blocked"
    TON_DRE_CALCULATE_SUCCEED = "ton_dre.calculate_succeed"
    TON_DRE_CALCULATE_FAIL = "ton_dre.calculate_fail"
    TON_DRE_EXPORT = "ton_dre.export"


_OCSF_CLASS_BY_ACTION: dict[AuditAction, OCSFEventClass] = {
    AuditAction.LOGIN: OCSFEventClass.AUTHENTICATION,
    AuditAction.LOGIN_FAILURE: OCSFEventClass.AUTHENTICATION,
    AuditAction.LOGOUT: OCSFEventClass.AUTHENTICATION,
    AuditAction.REGISTER: OCSFEventClass.AUTHENTICATION,
    AuditAction.PASSWORD_FORGOT: OCSFEventClass.AUTHENTICATION,
    AuditAction.PASSWORD_RESET: OCSFEventClass.AUTHENTICATION,
    AuditAction.EMAIL_VERIFY: OCSFEventClass.AUTHENTICATION,
    AuditAction.IMPERSONATE: OCSFEventClass.AUTHENTICATION,
    AuditAction.USER_CREATE: OCSFEventClass.ACCOUNT_CHANGE,
    AuditAction.USER_DELETE: OCSFEventClass.ACCOUNT_CHANGE,
    AuditAction.USER_DEACTIVATE: OCSFEventClass.ACCOUNT_CHANGE,
    AuditAction.USER_REACTIVATE: OCSFEventClass.ACCOUNT_CHANGE,
    AuditAction.USER_ROLE_CHANGE: OCSFEventClass.USER_ACCESS_MANAGEMENT,
    AuditAction.USER_CRAFT_ACCESS_CHANGE: OCSFEventClass.USER_ACCESS_MANAGEMENT,
    AuditAction.USER_GROUP_CHANGE: OCSFEventClass.GROUP_MANAGEMENT,
    AuditAction.USER_GROUP_CREATE: OCSFEventClass.GROUP_MANAGEMENT,
    AuditAction.USER_GROUP_RENAME: OCSFEventClass.GROUP_MANAGEMENT,
    AuditAction.USER_GROUP_DELETE: OCSFEventClass.GROUP_MANAGEMENT,
    AuditAction.USER_GROUP_PERMISSION_CHANGE: OCSFEventClass.GROUP_MANAGEMENT,
    AuditAction.USER_GROUP_MANAGER_CHANGE: OCSFEventClass.GROUP_MANAGEMENT,
    AuditAction.CRAFT_DEFAULT_CHANGE: OCSFEventClass.API_ACTIVITY,
    AuditAction.SECURITY_SETTINGS_CHANGE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CONTEXTUAL_RAG_MODEL_UPDATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.LLM_PROVIDER_CREATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.LLM_PROVIDER_UPDATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.LLM_PROVIDER_DELETE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CONNECTOR_CREATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CONNECTOR_UPDATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CONNECTOR_DELETE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CC_PAIR_CREATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CC_PAIR_UPDATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CC_PAIR_DELETE: OCSFEventClass.API_ACTIVITY,
    AuditAction.API_KEY_CREATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.API_KEY_REGENERATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.API_KEY_UPDATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.API_KEY_DELETE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CREDENTIAL_CREATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CREDENTIAL_UPDATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CREDENTIAL_DELETE: OCSFEventClass.API_ACTIVITY,
    AuditAction.CREDENTIAL_ACCESS: OCSFEventClass.API_ACTIVITY,
    # OCSF has no authorization-denial class, so a refused request maps onto the
    # request surface instead.
    AuditAction.PERMISSION_DENIED: OCSFEventClass.API_ACTIVITY,
    # OCSF has no business-domain class either. These are resource actions, so
    # they map onto the API activity surface like the other resource CRUD above.
    AuditAction.TON_SOURCE_CREATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_SOURCE_UPDATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_IMPORT_START: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_SNAPSHOT_CAPTURE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_DUPLICATE_DETECT: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_IMPORT_SUCCEED: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_IMPORT_FAIL: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_PROFILE_CREATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_PROFILE_EXECUTE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_PROFILE_SUCCEED: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_PROFILE_PARTIAL: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_PROFILE_FAIL: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REPORT_GENERATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_ROUTINE_SCHEDULE_UPDATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_RULE_VERSION_CHANGE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_MANUAL_OVERRIDE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_HUMAN_APPROVAL: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_START: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_SUCCEED: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_FAIL: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_VERIFY: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_ACKNOWLEDGE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_REQUEST_CORRECTION: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_JUSTIFY: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_FALSE_POSITIVE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_REVIEW_CONFIRM_CORRECTION: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_RECOMMENDATION_ACCEPT: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_RECOMMENDATION_REJECT: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_ACCOUNT_CREATE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_MAPPING_VERSION: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_AMOUNT_BASIS_VERSION: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_CANDIDATE_REJECT: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_LEGACY_CANDIDATE_IMPORT: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_RECONCILIATION_DECISION: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_RECOMPUTE_REQUEST: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_NORMALIZE_START: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_NORMALIZE_SUCCEED: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_NORMALIZE_FAIL: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_ACCOUNT_CLASSIFICATION_REVIEW: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_ACCOUNT_CLASSIFICATION_SUGGEST: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_CLOSING_TREATMENT: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_EMAIL_FLOW_CHANGE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_EMAIL_FLOW_SEND: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_EMAIL_FLOW_SUGGEST: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_AUTOMATION_CHANGE: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_AUTOMATION_RUN: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_AUTOMATION_SUGGEST: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_AUTHORITY_VERSION: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_FINANCIAL_DERIVATION_VERSION: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_DRE_STRUCTURE_VERSION: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_DRE_CALCULATE_START: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_DRE_CALCULATE_BLOCKED: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_DRE_CALCULATE_SUCCEED: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_DRE_CALCULATE_FAIL: OCSFEventClass.API_ACTIVITY,
    AuditAction.TON_DRE_EXPORT: OCSFEventClass.API_ACTIVITY,
}

# Guard: every action must map to a class, so a new action can't ship untagged.
_unmapped = set(AuditAction) - set(_OCSF_CLASS_BY_ACTION)
if _unmapped:
    raise RuntimeError(
        f"AuditAction members missing an OCSF class mapping: "
        f"{sorted(a.value for a in _unmapped)}"
    )


def ocsf_class_for(action: AuditAction) -> OCSFEventClass | None:
    """The OCSF class an action is tagged with.

    A public accessor over the mapping above, so a second audit sink (the
    persistent `ton_audit_event` table) records the same class as the stdout
    stream instead of reading a private module attribute or keeping its own copy
    that could drift.
    """
    return _OCSF_CLASS_BY_ACTION.get(action)


@dataclass(frozen=True)
class AuditActor:
    """Who performed the action; all fields optional. Never a secret —
    ``api_key_id`` is the key's id, never its value."""

    user_id: str | None = None
    email: str | None = None
    api_key_id: str | None = None
    auth_type: str | None = None  # e.g. "password", "oauth", "saml", "api_key"

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "api_key_id": self.api_key_id,
            "auth_type": self.auth_type,
        }


def actor_from_user(
    user: Any | None, *, auth_type: str | None = None
) -> AuditActor | None:
    """Build an ``AuditActor`` from a fastapi-users ``User`` (best-effort).

    Returns ``None`` when there's no user. Typed ``Any`` so this module stays
    free of an import dependency on the ORM/User model. Never raises."""
    if user is None:
        return None
    try:
        return AuditActor(
            user_id=str(user.id),
            email=getattr(user, "email", None),  # ods: ignore[getattr]
            auth_type=auth_type,
        )
    except Exception:
        # Don't raise into the caller, but surface the failure for diagnosis
        # (distinguishes an internal error from a genuinely absent user).
        _internal_logger.warning("actor_from_user failed to build actor", exc_info=True)
        return None


# Best-effort context gathering: each degrades to ``None`` rather than raising,
# so emission works off the request path (e.g. a connector thread) too.


def _safe_get_tenant_id() -> str | None:
    try:
        from shared_configs.contextvars import get_current_tenant_id

        return get_current_tenant_id()
    except Exception:
        return None


def _safe_get_request_id() -> str | None:
    try:
        from shared_configs.contextvars import ONYX_REQUEST_ID_CONTEXTVAR

        return ONYX_REQUEST_ID_CONTEXTVAR.get()
    except Exception:
        return None


def _safe_get_endpoint() -> str | None:
    try:
        from shared_configs.contextvars import CURRENT_ENDPOINT_CONTEXTVAR

        return CURRENT_ENDPOINT_CONTEXTVAR.get()
    except Exception:
        return None


def _safe_get_client_ip() -> str | None:
    try:
        from onyx.utils.client_ip import current_client_ip

        return current_client_ip()
    except Exception:
        return None


def should_emit(dedup_key: str, ttl_seconds: int, tenant_id: str | None) -> bool:
    """Redis ``SETNX``-with-``EX`` dedup. ``True`` if the window wasn't already
    claimed; degrades to always-emit (``True``) if Redis is unavailable."""
    try:
        from onyx.redis.redis_pool import get_redis_client

        client = get_redis_client(tenant_id=tenant_id)
        # nx=True returns truthy only when the key didn't exist (window is free).
        result = client.set(f"audit:{dedup_key}", "1", ex=ttl_seconds, nx=True)
        return bool(result)
    except Exception:
        return True


def emit_audit_event(
    action: AuditAction,
    outcome: AuditOutcome,
    *,
    actor: AuditActor | None = None,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    dedup_key: str | None = None,
    dedup_ttl_seconds: int = _DEFAULT_DEDUP_TTL_SECONDS,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit one structured audit line. Never raises.

    Tenant / request / endpoint / client-IP context is gathered automatically.
    Pass ``dedup_key`` for high-volume actions to suppress duplicates within
    ``dedup_ttl_seconds`` (omit it for low-volume config/access changes). Never
    put secrets in ``extra``.
    """
    try:
        tenant_id = _safe_get_tenant_id()

        if dedup_key is not None and not should_emit(
            dedup_key, dedup_ttl_seconds, tenant_id
        ):
            return

        ocsf_class = _OCSF_CLASS_BY_ACTION.get(action)

        payload: dict[str, Any] = {
            "audit_schema_version": AUDIT_SCHEMA_VERSION,
            "ts": time.time(),
            "action": action.value,
            "ocsf_class": ocsf_class.value if ocsf_class else None,
            "outcome": outcome.value,
            "tenant_id": tenant_id,
            "actor": actor.to_dict() if actor else None,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id is not None else None,
            "request_id": _safe_get_request_id(),
            "endpoint": _safe_get_endpoint(),
            "source_ip": _safe_get_client_ip(),
            "extra": extra or None,
        }

        # JSON as the message body so it parses identically under plain/json
        # LOG_FORMAT; default=str keeps a stray value from raising.
        _logger_for(ocsf_class).info(json.dumps(payload, default=str))
    except Exception:
        # Audit must never break the caller.
        return


def _configure_audit_logging() -> None:
    """Own an INFO stdout handler on ``onyx.audit`` so events reach stdout
    regardless of host-process logging. Relying on root propagation dropped
    every event under uvicorn (root unconfigured -> WARNING ``lastResort``).
    ``propagate=False`` keeps output identical across processes and avoids
    double-logging where root is configured (celery). Idempotent.
    """
    audit_root = logging.getLogger(AUDIT_LOGGER_ROOT)
    if any(h.name == AUDIT_HANDLER_NAME for h in audit_root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.name = AUDIT_HANDLER_NAME
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    audit_root.addHandler(handler)
    audit_root.setLevel(logging.INFO)
    audit_root.propagate = False


# IMPORT-TIME SIDE EFFECT (deliberate): configure the audit handler on import
# so the subsystem is self-contained in every process that imports it. A
# startup-hook entrypoint would reintroduce the bug this fixes -- a process
# emitting events without having called it drops them silently. Idempotent and
# inert until an event is actually emitted.
_configure_audit_logging()


def _logger_for(ocsf_class: OCSFEventClass | None) -> logging.Logger:
    name = (
        AUDIT_LOGGER_ROOT
        if ocsf_class is None
        else f"{AUDIT_LOGGER_ROOT}.{ocsf_class.value}"
    )
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
