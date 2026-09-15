"""Fail-closed resource authorization for TON (Plan 003c).

This module lives in the Community tree deliberately. ``update_persona_access``
in the CE tree raises ``NotImplementedError("Onyx MIT does not support
group-based sharing")`` and group sharing is written only by the EE override.
Copying that split here would be worse than a missing feature: with the
fail-closed default below, a CE-resolved worker would write no junction rows and
every TON resource would become invisible. TON ACL writes therefore work
unconditionally, and a named test resolves the CE implementations to prove it.

**No second authorization framework.** Everything here composes the primitives
Plan 008a already established — :class:`~onyx.db.enums.Permission`,
``PermissionGrant``, ``UserGroup``, ``has_global_permission``, ``assert_global``
and ``within_managed_scope_clause``. What is new is one resource-scope predicate,
not a parallel model.

## The authorization model

=========================================== ================= ================= ========
Caller                                      Read              Write             Delete
=========================================== ================= ================= ========
global administrator                        every row         every row         yes
group holding ``READ_TON_OCCURRENCES``      shared rows       no                no
group holding ``MANAGE_TON_OCCURRENCES``    shared rows       EDITOR rows       no
anyone else                                 nothing           nothing           no
=========================================== ================= ================= ========

Four decisions make that work, all of them explicit:

**1. Zero junction rows means DENIED.** For a TON resource the junction is
*authorizing*, not restricting. No clause here has an ``is_public`` branch, and no
TON table has such a column, so the ``Persona`` short-circuit — where
``is_public`` defaults to true and bypasses the whole group ACL — is not merely
disabled, it is inexpressible.

**2. The admin bypass is ``FULL_ADMIN_PANEL_ACCESS``, not the TON token.**
Holding ``MANAGE_TON_OCCURRENCES`` is a capability, not company-wide sight: if it
bypassed the ACL, granting a group the ability to manage its own occurrences
would hand it every other unit's as well. The bypass uses
``has_global_permission`` rather than ``has_permission``, so a scoped group
manager can never trigger it.

**3. TON tokens stay out of ``SCOPED_MANAGER_PERMISSIONS``.** Readiness §10 fixes
this for ``MANAGE_TON_RULES`` and leaves the occurrence tokens open; keeping them
out is the conservative reading. Group-manager scope is a different axis from a
TON share level, and mixing them would let managing a group confer authority over
financial cases that were merely shared with it. Group membership alone is
therefore not management authority, and a group manager gains nothing
company-wide. A test asserts it for every TON token.

**4. A non-admin cannot widen a resource's groups.** ``within_managed_scope_clause``
is reused with ``non_public_clause = sa.true()`` — a TON resource is always
non-public — and with the caller's own groups as the managed set. The result: a
non-admin may act on a case only when *every* group it is shared with is one they
belong to. Reaching a case that finance also sees, and then adding a group finance
cannot see, is not expressible.
"""

from collections.abc import Mapping
from typing import TypeVar
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import ColumnElement, Select, and_, exists, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from onyx.auth.permissions import has_global_permission, has_permission
from onyx.auth.scoped_permissions import assert_global
from onyx.db.enums import Permission, PermissionAuthority
from onyx.db.models import User, User__UserGroup
from onyx.db.scoped_permissions import within_managed_scope_clause
from onyx.db.ton.enums import TonSharePermission
from onyx.db.ton.models import (
    BusinessUnit,
    BusinessUnit__UserGroup,
    Contract,
    Contract__UserGroup,
    Finding,
    FindingEvidence,
    Occurrence,
    Occurrence__UserGroup,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError

_ResourceId = TypeVar("_ResourceId")

# TON resources are always non-public. Readiness §10 correction 2 requires the
# read-side scope helper to receive an explicit non-public predicate; for TON the
# predicate is a constant because there is no column that could make a resource
# public.
TON_NON_PUBLIC_CLAUSE: ColumnElement[bool] = sa.true()

_DENIED_MESSAGE = (
    "You do not have access to this TON resource. Access requires an explicit "
    "group authorization."
)


def user_group_ids_subquery(user: User) -> Select:
    """The groups *user* belongs to.

    Membership, not management: the TON share level on the junction row decides
    what a member may do, so managing the group adds nothing here. Default groups
    are deliberately *not* excluded — unlike a manager edge, plain membership of
    "Basic" confers no scope by itself, and a TON resource shared with Basic was
    shared with the organization on purpose.
    """
    return select(User__UserGroup.user_group_id).where(
        User__UserGroup.user_id == user.id
    )


def fetch_user_group_ids(db_session: Session, user: User) -> set[int]:
    """Execute :func:`user_group_ids_subquery`."""
    return set(db_session.scalars(user_group_ids_subquery(user)).all())


def is_ton_administrator(user: User) -> bool:
    """Whether *user* may bypass the TON resource ACL.

    ``has_global_permission`` rather than ``has_permission``: a scoped group
    manager resolves ``SCOPED`` for the bundle tokens and must never be mistaken
    for an administrator here.
    """
    return has_global_permission(user, Permission.FULL_ADMIN_PANEL_ACCESS)


def holds_ton_read_capability(user: User) -> bool:
    """Whether *user* holds a token that admits them to TON occurrence reads."""
    return has_global_permission(
        user, Permission.READ_TON_OCCURRENCES
    ) or has_global_permission(user, Permission.MANAGE_TON_OCCURRENCES)


def holds_ton_manage_capability(user: User) -> bool:
    """Whether *user* holds the TON occurrence write token globally."""
    return has_global_permission(user, Permission.MANAGE_TON_OCCURRENCES)


# ---------------------------------------------------------------------------
# Read predicates
# ---------------------------------------------------------------------------


def _shared_with_user_group(
    *,
    resource_id_col: InstrumentedAttribute[_ResourceId],
    junction_resource_col: InstrumentedAttribute[_ResourceId],
    junction_group_col: InstrumentedAttribute[int],
    user: User,
) -> ColumnElement[bool]:
    """``EXISTS`` a junction row for one of *user*'s groups.

    Fail-closed by construction: with no junction rows the ``EXISTS`` is false.
    There is no ``or_`` branch for a public resource, because for TON there is no
    such thing.

    Share level is deliberately not a parameter. A VIEWER row grants read, and the
    single place that needs EDITOR — :func:`occurrence_editable_clause` — states
    it explicitly, so a caller cannot get a write predicate by accident.
    """
    return (
        select(junction_resource_col)
        .join(
            User__UserGroup,
            User__UserGroup.user_group_id == junction_group_col,
        )
        .where(
            junction_resource_col == resource_id_col,
            User__UserGroup.user_id == user.id,
        )
        .exists()
    )


def business_unit_visible_clause(user: User) -> ColumnElement[bool]:
    """A business unit is visible only when a group of *user*'s authorizes it."""
    if is_ton_administrator(user):
        return sa.true()
    return _shared_with_user_group(
        resource_id_col=BusinessUnit.id,
        junction_resource_col=BusinessUnit__UserGroup.business_unit_id,
        junction_group_col=BusinessUnit__UserGroup.user_group_id,
        user=user,
    )


def contract_visible_clause(user: User) -> ColumnElement[bool]:
    """A contract is visible only when a group of *user*'s authorizes it."""
    if is_ton_administrator(user):
        return sa.true()
    return _shared_with_user_group(
        resource_id_col=Contract.id,
        junction_resource_col=Contract__UserGroup.contract_id,
        junction_group_col=Contract__UserGroup.user_group_id,
        user=user,
    )


def occurrence_visible_clause(user: User) -> ColumnElement[bool]:
    """Whether *user* may read an occurrence.

    Three conditions, all required:

    1. a junction row for one of the caller's groups — the resource ACL;
    2. authorization for the owning business unit, when the case names one;
    3. authorization for the contract, when the case names one.

    Conditions 2 and 3 are the organizational context readiness §10 attaches to
    ``business_unit_id``. They are what makes cross-unit denial hold even if an
    occurrence junction row is created by mistake: an HR-scoped group with no
    authorization for the financial unit still cannot read its cases.
    """
    if is_ton_administrator(user):
        return sa.true()

    shared = _shared_with_user_group(
        resource_id_col=Occurrence.id,
        junction_resource_col=Occurrence__UserGroup.occurrence_id,
        junction_group_col=Occurrence__UserGroup.user_group_id,
        user=user,
    )
    unit_ok = or_(
        Occurrence.business_unit_id.is_(None),
        exists(
            select(BusinessUnit__UserGroup.business_unit_id)
            .join(
                User__UserGroup,
                User__UserGroup.user_group_id == BusinessUnit__UserGroup.user_group_id,
            )
            .where(
                BusinessUnit__UserGroup.business_unit_id == Occurrence.business_unit_id,
                User__UserGroup.user_id == user.id,
            )
        ),
    )
    contract_ok = or_(
        Occurrence.contract_id.is_(None),
        exists(
            select(Contract__UserGroup.contract_id)
            .join(
                User__UserGroup,
                User__UserGroup.user_group_id == Contract__UserGroup.user_group_id,
            )
            .where(
                Contract__UserGroup.contract_id == Occurrence.contract_id,
                User__UserGroup.user_id == user.id,
            )
        ),
    )
    return and_(shared, unit_ok, contract_ok)


def occurrence_editable_clause(user: User) -> ColumnElement[bool]:
    """Whether *user* may write an occurrence.

    Reuses ``within_managed_scope_clause`` — the read-side mirror of the GATE 2
    write gate — with ``non_public_clause = TON_NON_PUBLIC_CLAUSE`` and the
    caller's own groups as the managed set. Its guarantee is the one that matters
    here: in at least one of those groups, and in **no** group outside them. A
    case shared with a group the caller cannot reach is not editable by them, so
    editing cannot become a route to widening.

    An EDITOR row is required on top: a VIEWER share reads and nothing more.
    """
    if is_ton_administrator(user):
        return sa.true()
    if not holds_ton_manage_capability(user):
        return sa.false()

    every_group_is_the_callers = within_managed_scope_clause(
        resource_id_col=Occurrence.id,
        junction_resource_col=Occurrence__UserGroup.occurrence_id,
        junction_group_col=Occurrence__UserGroup.user_group_id,
        non_public_clause=TON_NON_PUBLIC_CLAUSE,
        managed_subq=user_group_ids_subquery(user),
    )
    has_editor_row = (
        select(Occurrence__UserGroup.occurrence_id)
        .join(
            User__UserGroup,
            User__UserGroup.user_group_id == Occurrence__UserGroup.user_group_id,
        )
        .where(
            Occurrence__UserGroup.occurrence_id == Occurrence.id,
            Occurrence__UserGroup.permission == TonSharePermission.EDITOR,
            User__UserGroup.user_id == user.id,
        )
        .exists()
    )
    return and_(every_group_is_the_callers, has_editor_row)


def finding_visible_clause(user: User) -> ColumnElement[bool]:
    """Whether *user* may read a finding.

    Derived entirely from the owning occurrence. :class:`Finding` has no junction
    of its own — two independent ACLs over one analytical case would eventually
    grant what the other denies (readiness §10).
    """
    if is_ton_administrator(user):
        return sa.true()
    return exists(
        select(Occurrence.id).where(
            Occurrence.id == Finding.occurrence_id, occurrence_visible_clause(user)
        )
    )


def finding_evidence_visible_clause(user: User) -> ColumnElement[bool]:
    """Whether *user* may read an evidence row. Derived through its finding."""
    if is_ton_administrator(user):
        return sa.true()
    return exists(
        select(Finding.id).where(
            Finding.id == FindingEvidence.finding_id, finding_visible_clause(user)
        )
    )


# ---------------------------------------------------------------------------
# Read helpers — every one applies the resource filter
# ---------------------------------------------------------------------------


def fetch_occurrences_for_user(
    db_session: Session,
    user: User,
    *,
    editable: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> list[Occurrence]:
    """Occurrences *user* may see, newest detection first.

    Ordered by ``(last_detected_at, id)``: ``last_detected_at`` alone is not a
    total order, and an unstable sort makes server-side pagination return
    duplicates.
    """
    if not holds_ton_read_capability(user) and not is_ton_administrator(user):
        return []

    clause = (
        occurrence_editable_clause(user)
        if editable
        else occurrence_visible_clause(user)
    )
    stmt = (
        select(Occurrence)
        .where(clause)
        .order_by(Occurrence.last_detected_at.desc(), Occurrence.id)
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db_session.scalars(stmt).all())


def get_occurrence_for_user(
    db_session: Session,
    user: User,
    occurrence_id: UUID,
    *,
    editable: bool = False,
) -> Occurrence:
    """One occurrence by id, or raise.

    The direct-id path applies the same predicate as the list path. A secure
    filtered list combined with an unfiltered detail fetch is the classic ACL
    failure, so both call the same clause.

    Raises the same error whether the row is absent or merely forbidden: telling a
    caller that a case exists but is not theirs already leaks the case.
    """
    if not holds_ton_read_capability(user) and not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, _DENIED_MESSAGE)

    clause = (
        occurrence_editable_clause(user)
        if editable
        else occurrence_visible_clause(user)
    )
    occurrence = db_session.scalars(
        select(Occurrence).where(Occurrence.id == occurrence_id, clause)
    ).one_or_none()
    if occurrence is None:
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, _DENIED_MESSAGE)
    return occurrence


def fetch_findings_for_user(
    db_session: Session, user: User, *, occurrence_id: UUID | None = None
) -> list[Finding]:
    """Findings *user* may see, optionally narrowed to one case."""
    if not holds_ton_read_capability(user) and not is_ton_administrator(user):
        return []

    stmt = select(Finding).where(finding_visible_clause(user))
    if occurrence_id is not None:
        stmt = stmt.where(Finding.occurrence_id == occurrence_id)
    return list(
        db_session.scalars(stmt.order_by(Finding.detected_at, Finding.id)).all()
    )


def get_finding_for_user(db_session: Session, user: User, finding_id: UUID) -> Finding:
    """One finding by id, or raise. Same predicate as the list path."""
    if not holds_ton_read_capability(user) and not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, _DENIED_MESSAGE)

    finding = db_session.scalars(
        select(Finding).where(Finding.id == finding_id, finding_visible_clause(user))
    ).one_or_none()
    if finding is None:
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, _DENIED_MESSAGE)
    return finding


def fetch_finding_evidence_for_user(
    db_session: Session, user: User, *, finding_id: UUID | None = None
) -> list[FindingEvidence]:
    """Evidence rows *user* may see, optionally narrowed to one finding."""
    if not holds_ton_read_capability(user) and not is_ton_administrator(user):
        return []

    stmt = select(FindingEvidence).where(finding_evidence_visible_clause(user))
    if finding_id is not None:
        stmt = stmt.where(FindingEvidence.finding_id == finding_id)
    return list(db_session.scalars(stmt.order_by(FindingEvidence.id)).all())


def get_finding_evidence_for_user(
    db_session: Session, user: User, evidence_id: UUID
) -> FindingEvidence:
    """One evidence row by id, or raise. Same predicate as the list path."""
    if not holds_ton_read_capability(user) and not is_ton_administrator(user):
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, _DENIED_MESSAGE)

    evidence = db_session.scalars(
        select(FindingEvidence).where(
            FindingEvidence.id == evidence_id, finding_evidence_visible_clause(user)
        )
    ).one_or_none()
    if evidence is None:
        raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, _DENIED_MESSAGE)
    return evidence


# ---------------------------------------------------------------------------
# Write gates
# ---------------------------------------------------------------------------


def assert_can_manage_occurrence(
    db_session: Session, *, user: User, occurrence: Occurrence
) -> None:
    """GATE 2 for a write to an existing case. Raises 403 when out of scope.

    Re-reads the current group relationships **inside the transaction** with
    ``FOR UPDATE`` on the junction rows, so a concurrent reshare cannot slip
    between the check and the write, and never trusts group ids from the request.
    """
    if is_ton_administrator(user):
        return
    if not holds_ton_manage_capability(user):
        _deny(user, "manage_occurrence", occurrence_id=occurrence.id)

    current = _locked_group_ids(db_session, occurrence.id)
    if not current:
        # Fail-closed: an unshared case is reachable only by an administrator.
        _deny(user, "manage_occurrence_unshared", occurrence_id=occurrence.id)

    editor_groups = _editor_group_ids(db_session, occurrence.id, user)
    own_groups = fetch_user_group_ids(db_session, user)
    if not editor_groups or not current.issubset(own_groups):
        _deny(user, "manage_occurrence_out_of_scope", occurrence_id=occurrence.id)


def assert_can_delete_occurrence(
    db_session: Session, *, user: User, occurrence: Occurrence
) -> None:
    """Deletion is the strictest gate: global authority **and** resource scope.

    ``assert_global`` first, as readiness §10 correction 5 requires — never an
    ``allow_scope`` shortcut on a delete path. That alone excludes a scoped group
    manager, who resolves ``NONE`` for every TON token.

    An administrator stops there. Anyone else must additionally pass the resource
    write gate, because deleting a case destroys its findings, events, impacts,
    assignments and notes: a group granted the capability must not be able to
    destroy a case it could not even read.
    """
    assert_global(user, permission=Permission.MANAGE_TON_OCCURRENCES)
    if is_ton_administrator(user):
        return
    assert_can_manage_occurrence(db_session, user=user, occurrence=occurrence)


def set_occurrence_groups__no_commit(
    db_session: Session,
    *,
    user: User,
    occurrence: Occurrence,
    group_permissions: Mapping[int, TonSharePermission],
) -> list[Occurrence__UserGroup]:
    """Replace the group authorizations of *occurrence*.

    Lives in the Community tree and works unconditionally. There is no versioned
    dispatch and no EE override, so a CE-resolved worker writes the same rows as
    an EE-resolved one.

    A non-administrator may neither reach outside their own groups nor add a group
    they do not belong to. Both halves matter: the first stops them touching a case
    finance also sees, the second stops them publishing a case to a group that was
    never authorized for it.
    """
    requested = dict(group_permissions)
    assert_can_manage_occurrence(db_session, user=user, occurrence=occurrence)

    if not is_ton_administrator(user):
        own_groups = fetch_user_group_ids(db_session, user)
        widened = set(requested) - own_groups
        if widened:
            _deny(
                user,
                "widen_occurrence_groups",
                occurrence_id=occurrence.id,
                extra_group_ids=sorted(widened),
            )
        if not requested:
            # A non-administrator removing the last authorization would orphan
            # the case behind the fail-closed default and lose their own access.
            _deny(user, "orphan_occurrence", occurrence_id=occurrence.id)

    return _replace_group_rows(db_session, occurrence=occurrence, requested=requested)


def set_business_unit_groups__no_commit(
    db_session: Session,
    *,
    user: User,
    business_unit: BusinessUnit,
    group_permissions: Mapping[int, TonSharePermission],
) -> list[BusinessUnit__UserGroup]:
    """Replace the group authorizations of a business unit.

    Global-only. A unit's authorization list decides who can see every case in
    that unit, so widening it is an organizational act rather than a
    case-level one.
    """
    assert_global(user, permission=Permission.MANAGE_TON_BUSINESS_UNITS)

    for existing in db_session.scalars(
        select(BusinessUnit__UserGroup)
        .where(BusinessUnit__UserGroup.business_unit_id == business_unit.id)
        .with_for_update()
    ).all():
        db_session.delete(existing)
    db_session.flush()

    rows = [
        BusinessUnit__UserGroup(
            business_unit_id=business_unit.id,
            user_group_id=group_id,
            permission=permission,
        )
        for group_id, permission in group_permissions.items()
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


def set_contract_groups__no_commit(
    db_session: Session,
    *,
    user: User,
    contract: Contract,
    group_permissions: Mapping[int, TonSharePermission],
) -> list[Contract__UserGroup]:
    """Replace the group authorizations of a contract. Global-only, as for units."""
    assert_global(user, permission=Permission.MANAGE_TON_BUSINESS_UNITS)

    for existing in db_session.scalars(
        select(Contract__UserGroup)
        .where(Contract__UserGroup.contract_id == contract.id)
        .with_for_update()
    ).all():
        db_session.delete(existing)
    db_session.flush()

    rows = [
        Contract__UserGroup(
            contract_id=contract.id, user_group_id=group_id, permission=permission
        )
        for group_id, permission in group_permissions.items()
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


def occurrence_group_ids(db_session: Session, occurrence_id: UUID) -> set[int]:
    """The groups currently authorized for a case. Introspection, not a gate."""
    return set(
        db_session.scalars(
            select(Occurrence__UserGroup.user_group_id).where(
                Occurrence__UserGroup.occurrence_id == occurrence_id
            )
        ).all()
    )


def user_share_permission(
    db_session: Session, *, user: User, occurrence_id: UUID
) -> TonSharePermission | None:
    """The best share level *user* holds on a case, or ``None``.

    Serves the per-row authorization a UI needs to hide an edit affordance. It is
    a hint only — the write gate still refuses a direct call.
    """
    levels = set(
        db_session.scalars(
            select(Occurrence__UserGroup.permission)
            .join(
                User__UserGroup,
                User__UserGroup.user_group_id == Occurrence__UserGroup.user_group_id,
            )
            .where(
                Occurrence__UserGroup.occurrence_id == occurrence_id,
                User__UserGroup.user_id == user.id,
            )
        ).all()
    )
    if TonSharePermission.EDITOR in levels:
        return TonSharePermission.EDITOR
    if TonSharePermission.VIEWER in levels:
        return TonSharePermission.VIEWER
    return None


def _replace_group_rows(
    db_session: Session,
    *,
    occurrence: Occurrence,
    requested: Mapping[int, TonSharePermission],
) -> list[Occurrence__UserGroup]:
    for existing in db_session.scalars(
        select(Occurrence__UserGroup)
        .where(Occurrence__UserGroup.occurrence_id == occurrence.id)
        .with_for_update()
    ).all():
        db_session.delete(existing)
    db_session.flush()

    rows = [
        Occurrence__UserGroup(
            occurrence_id=occurrence.id,
            user_group_id=group_id,
            permission=permission,
        )
        for group_id, permission in requested.items()
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


def _locked_group_ids(db_session: Session, occurrence_id: UUID) -> set[int]:
    """Current authorizations, read ``FOR UPDATE`` inside the transaction."""
    return set(
        db_session.scalars(
            select(Occurrence__UserGroup.user_group_id)
            .where(Occurrence__UserGroup.occurrence_id == occurrence_id)
            .with_for_update()
        ).all()
    )


def _editor_group_ids(db_session: Session, occurrence_id: UUID, user: User) -> set[int]:
    return set(
        db_session.scalars(
            select(Occurrence__UserGroup.user_group_id)
            .join(
                User__UserGroup,
                User__UserGroup.user_group_id == Occurrence__UserGroup.user_group_id,
            )
            .where(
                Occurrence__UserGroup.occurrence_id == occurrence_id,
                Occurrence__UserGroup.permission == TonSharePermission.EDITOR,
                User__UserGroup.user_id == user.id,
            )
        ).all()
    )


def _deny(
    user: User,
    gate: str,
    *,
    occurrence_id: UUID | None = None,
    extra_group_ids: list[int] | None = None,
) -> None:
    """Raise the standard denial.

    Emits nothing to a persistent audit table: 003c creates none, and the existing
    stdout audit stream is unchanged. 003d owns persistent generic audit.
    """
    del user, gate, occurrence_id, extra_group_ids  # kept for call-site clarity
    raise OnyxError(OnyxErrorCode.INSUFFICIENT_PERMISSIONS, _DENIED_MESSAGE)


def ton_permission_authority(user: User, permission: Permission) -> PermissionAuthority:
    """The authority *user* holds for a TON token.

    Exposed so a test can assert that no TON token ever resolves ``SCOPED``:
    group-manager scope is a different axis from a TON share level, and letting
    them overlap is how a group manager would gain authority they were never
    granted.
    """
    return has_permission(user, permission)
