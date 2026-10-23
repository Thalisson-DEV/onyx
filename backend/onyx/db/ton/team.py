"""People of the TON and what each one sees, managed by a TON administrator.

Two profiles, in the Controladoria's words:

* **Administrador** — the seeded Admin group: every unit and every screen,
  including this one. Admin *is* that membership (``set_user_admin_access``).
* **Gestor de unidade** — read-only, limited to the chosen units. Each manager
  gets one group of their own, named ``MANAGER_GROUP_PREFIX + email``, holding
  the source read token and a VIEWER authorization on each chosen unit, and no
  share of any source: the DRE of a visible unit is read through
  ``financial_domain.unit_reader``, while sources, reviews, automations and
  every other company-wide screen stay closed to them.

Nobody sets another person's password. A new person gets a first-access link:
a password-reset token of the standard ``/auth/reset-password`` route, valid for
``ACCESS_LINK_DAYS`` and void once a password is chosen (the token carries a
fingerprint of the current password hash).
"""

import datetime
import secrets
from uuid import UUID

import sqlalchemy as sa
from email_validator import EmailNotValidError, validate_email
from fastapi_users.jwt import generate_jwt
from fastapi_users.password import PasswordHelper
from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from onyx.configs.app_configs import USER_AUTH_SECRET
from onyx.configs.constants import ANONYMOUS_USER_EMAIL
from onyx.db.enums import AccountType, GrantSource, Permission
from onyx.db.models import PermissionGrant, User, User__UserGroup, UserGroup
from onyx.db.permissions import recompute_user_permissions__no_commit
from onyx.db.ton.acl import is_ton_administrator
from onyx.db.ton.enums import TonSharePermission
from onyx.db.ton.models import (
    BusinessUnit,
    BusinessUnit__UserGroup,
    Source__UserGroup,
)
from onyx.db.users import (
    assign_user_to_default_groups__no_commit,
    get_user_by_email,
    set_user_admin_access,
    user_is_admin,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.utils.audit import (
    AuditAction,
    AuditOutcome,
    actor_from_user,
    emit_audit_event,
)

MANAGER_GROUP_PREFIX = "TON · Gestor · "
ACCESS_LINK_DAYS = 7
# Same audience the fastapi-users reset route checks.
RESET_AUDIENCE = "fastapi-users:reset"
MANAGER_PERMISSIONS = (Permission.READ_TON_SOURCES,)
ADMIN = "ADMIN"
MANAGER = "MANAGER"


class TeamMemberView(BaseModel):
    id: UUID
    email: str
    name: str | None
    # ADMIN, MANAGER, or None for an account with no TON access yet.
    profile: str | None
    unit_ids: list[UUID]
    active: bool
    # No password chosen yet: the person has not used the first-access link.
    pending_first_access: bool
    is_you: bool


class TeamMemberCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str | None = Field(default=None, max_length=200)
    profile: str = Field(pattern=f"^({ADMIN}|{MANAGER})$")
    unit_ids: list[UUID] = Field(default_factory=list, max_length=500)


class TeamMemberUpdate(BaseModel):
    profile: str = Field(pattern=f"^({ADMIN}|{MANAGER})$")
    unit_ids: list[UUID] = Field(default_factory=list, max_length=500)


class TeamAccessLink(BaseModel):
    member: TeamMemberView
    link: str
    expires_at: datetime.datetime


def _require_admin(user: User) -> None:
    if not is_ton_administrator(user):
        raise OnyxError(
            OnyxErrorCode.ADMIN_ONLY, "Somente administradores gerenciam usuários"
        )


def _manager_group(session: Session, member: User) -> UserGroup | None:
    return session.scalar(
        sa.select(UserGroup)
        .join(User__UserGroup, User__UserGroup.user_group_id == UserGroup.id)
        .where(
            User__UserGroup.user_id == member.id,
            UserGroup.name.startswith(MANAGER_GROUP_PREFIX),
        )
    )


def _unit_ids(session: Session, group: UserGroup | None) -> list[UUID]:
    if group is None:
        return []
    return list(
        session.scalars(
            sa.select(BusinessUnit__UserGroup.business_unit_id).where(
                BusinessUnit__UserGroup.user_group_id == group.id
            )
        )
    )


def _pending(member: User) -> bool:
    # Still the placeholder: the person has not used the first-access link.
    return bool(member.hashed_password.startswith(PENDING_MARK))


def _view(session: Session, member: User, actor: User) -> TeamMemberView:
    group = _manager_group(session, member)
    profile = ADMIN if user_is_admin(member) else MANAGER if group else None
    return TeamMemberView(
        id=member.id,
        email=member.email,
        name=member.personal_name,
        profile=profile,
        unit_ids=[] if profile == ADMIN else _unit_ids(session, group),
        active=member.is_active,
        pending_first_access=_pending(member),
        is_you=member.id == actor.id,
    )


def list_members(session: Session, actor: User) -> list[TeamMemberView]:
    _require_admin(actor)
    members = (
        session.scalars(
            sa.select(User)
            .where(
                User.account_type == AccountType.STANDARD,
                User.email != ANONYMOUS_USER_EMAIL,
            )
            .order_by(User.is_active.desc(), sa.func.lower(User.email))
        )
        .unique()
        .all()
    )
    return [_view(session, member, actor) for member in members]


def _member(session: Session, user_id: UUID) -> User:
    member = session.get(User, user_id)
    if member is None or member.account_type != AccountType.STANDARD:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Usuário não encontrado")
    return member


def _check_units(session: Session, unit_ids: list[UUID]) -> list[UUID]:
    wanted = list(dict.fromkeys(unit_ids))
    found = set(
        session.scalars(sa.select(BusinessUnit.id).where(BusinessUnit.id.in_(wanted)))
    )
    if len(found) != len(wanted):
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Unidade não encontrada")
    if not wanted:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Escolha ao menos uma unidade para o gestor"
        )
    return wanted


def _set_manager_access__no_commit(
    session: Session, actor: User, member: User, unit_ids: list[UUID]
) -> None:
    """The member's own read-only group: the source read token and the chosen
    units."""
    group = _manager_group(session, member)
    if group is None:
        group = UserGroup(
            name=f"{MANAGER_GROUP_PREFIX}{member.email}",
            is_up_to_date=True,
            time_last_modified_by_user=datetime.datetime.now(datetime.timezone.utc),
        )
        session.add(group)
        session.flush()
        session.add(User__UserGroup(user_id=member.id, user_group_id=group.id))
    # The whole group is rewritten, so a change in what a manager may see also
    # reaches the managers registered before it.
    for model, column in (
        (PermissionGrant, PermissionGrant.group_id),
        (Source__UserGroup, Source__UserGroup.user_group_id),
        (BusinessUnit__UserGroup, BusinessUnit__UserGroup.user_group_id),
    ):
        session.execute(sa.delete(model).where(column == group.id))
    session.add_all(
        PermissionGrant(
            group_id=group.id,
            permission=permission,
            grant_source=GrantSource.SYSTEM,
            granted_by=actor.id,
        )
        for permission in MANAGER_PERMISSIONS
    )
    session.add_all(
        BusinessUnit__UserGroup(
            business_unit_id=unit_id,
            user_group_id=group.id,
            permission=TonSharePermission.VIEWER,
        )
        for unit_id in unit_ids
    )
    session.flush()
    recompute_user_permissions__no_commit(member.id, session)


def _drop_manager_access__no_commit(session: Session, member: User) -> None:
    group = _manager_group(session, member)
    if group is None:
        return
    for model, column in (
        (BusinessUnit__UserGroup, BusinessUnit__UserGroup.user_group_id),
        (Source__UserGroup, Source__UserGroup.user_group_id),
        (User__UserGroup, User__UserGroup.user_group_id),
        (PermissionGrant, PermissionGrant.group_id),
    ):
        session.execute(sa.delete(model).where(column == group.id))
    session.delete(group)
    session.flush()
    recompute_user_permissions__no_commit(member.id, session)


# Messages of the shared user services, as the Controladoria reads them; the
# originals are in English and name the platform underneath.
ADMIN_MESSAGES = {
    "You can't remove yourself from the admin group. Ask another admin to do it.": "Você não pode tirar o seu próprio acesso de administrador; peça a outro administrador.",
    "You can't remove the last admin. Grant another user admin access first.": "Não é possível tirar o último administrador; dê acesso de administrador a outra pessoa antes.",
}


def _set_admin(session: Session, actor: User, member: User, is_admin: bool) -> None:
    try:
        set_user_admin_access(session, actor, member, is_admin)
    except OnyxError as error:
        raise OnyxError(
            error.error_code,
            ADMIN_MESSAGES.get(
                error.detail, "Não foi possível alterar o acesso de administrador"
            ),
        ) from error


def _apply_profile(
    session: Session, actor: User, member: User, profile: str, unit_ids: list[UUID]
) -> None:
    if profile == ADMIN:
        _drop_manager_access__no_commit(session, member)
        session.commit()
        _set_admin(session, actor, member, True)
        return
    units = _check_units(session, unit_ids)
    if user_is_admin(member):
        # Raises before anything changes when it would remove the last admin
        # or the actor themselves.
        _set_admin(session, actor, member, False)
    _set_manager_access__no_commit(session, actor, member, units)
    session.commit()


# Placeholder password of a person who has not chosen one: an argon2 hash of a
# random secret nobody knows. Its parameters differ from the ones real
# passwords get, which is how the screen tells "aguardando primeiro acesso";
# it stays a valid hash, so a login attempt simply fails.
PENDING_HASHER = Argon2Hasher(time_cost=1, memory_cost=16384, parallelism=1)
PENDING_MARK = "$argon2id$v=19$m=16384,t=1,p=1$"


def _placeholder_password() -> str:
    return PENDING_HASHER.hash(secrets.token_urlsafe(32))


def create_member(
    session: Session, actor: User, request: TeamMemberCreate
) -> TeamAccessLink:
    _require_admin(actor)
    try:
        email = validate_email(request.email, check_deliverability=False).normalized
    except EmailNotValidError as error:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "E-mail inválido") from error
    email = email.lower()
    if request.profile == MANAGER:
        _check_units(session, request.unit_ids)
    existing = get_user_by_email(email, session)
    if existing is not None and existing.account_type == AccountType.STANDARD:
        raise OnyxError(
            OnyxErrorCode.CONFLICT,
            "Já existe um usuário com este e-mail; altere o acesso dele na lista",
        )
    # Imported here: onyx.auth.users pulls in the whole auth stack, and the
    # sources module imports this one.
    from onyx.auth.users import enforce_seat_limit_locked

    try:
        enforce_seat_limit_locked(session, seats_needed=1)
    except OnyxError as error:
        raise OnyxError(
            error.error_code,
            "O limite de usuários da licença do TON foi atingido; desative alguém ou fale com o suporte",
        ) from error
    if existing is None:
        member = User(
            email=email,
            hashed_password=_placeholder_password(),
            is_active=True,
            is_verified=True,
            is_superuser=False,
            account_type=AccountType.STANDARD,
            personal_name=request.name or None,
        )
        session.add(member)
    else:
        # A placeholder row (an e-mail seen in a connector) becomes a login.
        member = existing
        member.hashed_password = _placeholder_password()
        member.account_type = AccountType.STANDARD
        member.is_active = True
        member.is_verified = True
        if request.name:
            member.personal_name = request.name
    session.flush()
    assign_user_to_default_groups__no_commit(session, member)
    session.commit()
    _apply_profile(session, actor, member, request.profile, request.unit_ids)
    emit_audit_event(
        AuditAction.USER_CREATE,
        AuditOutcome.SUCCESS,
        actor=actor_from_user(actor),
        resource_type="user",
        resource_id=str(member.id),
        extra={"target_email": member.email, "ton_profile": request.profile},
    )
    session.refresh(member)
    return _link(session, actor, member)


def update_member(
    session: Session, actor: User, user_id: UUID, request: TeamMemberUpdate
) -> TeamMemberView:
    _require_admin(actor)
    member = _member(session, user_id)
    before = _view(session, member, actor)
    _apply_profile(session, actor, member, request.profile, request.unit_ids)
    session.refresh(member)
    after = _view(session, member, actor)
    emit_audit_event(
        AuditAction.USER_ROLE_CHANGE,
        AuditOutcome.SUCCESS,
        actor=actor_from_user(actor),
        resource_type="user",
        resource_id=str(member.id),
        extra={
            "target_email": member.email,
            "previous_ton_profile": before.profile,
            "ton_profile": after.profile,
            "unit_count": len(after.unit_ids),
        },
    )
    return after


def set_member_active(
    session: Session, actor: User, user_id: UUID, active: bool
) -> TeamMemberView:
    _require_admin(actor)
    member = _member(session, user_id)
    if member.id == actor.id:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Você não pode desativar a si mesmo"
        )
    if member.is_active != active:
        if not active and user_is_admin(member):
            others = session.scalar(
                sa.select(sa.func.count())
                .select_from(User)
                .where(
                    User.is_active.is_(True),
                    User.id != member.id,
                    User.account_type == AccountType.STANDARD,
                    User.effective_permissions.contains(
                        [Permission.FULL_ADMIN_PANEL_ACCESS.value]
                    ),
                )
            )
            if not others:
                raise OnyxError(
                    OnyxErrorCode.INVALID_INPUT,
                    "Não é possível desativar o último administrador",
                )
        member.is_active = active
        session.commit()
        emit_audit_event(
            AuditAction.USER_REACTIVATE if active else AuditAction.USER_DEACTIVATE,
            AuditOutcome.SUCCESS,
            actor=actor_from_user(actor),
            resource_type="user",
            resource_id=str(member.id),
            extra={"target_email": member.email},
        )
    return _view(session, member, actor)


def _link(session: Session, actor: User, member: User) -> TeamAccessLink:
    if not member.is_active:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT, "Reative o usuário antes de gerar o link"
        )
    lifetime = ACCESS_LINK_DAYS * 24 * 3600
    token = generate_jwt(
        {
            "sub": str(member.id),
            "password_fgpt": PasswordHelper().hash(member.hashed_password),
            "aud": RESET_AUDIENCE,
        },
        USER_AUTH_SECRET,
        lifetime,
    )
    return TeamAccessLink(
        member=_view(session, member, actor),
        # A path: the screen prefixes the address the administrator is on,
        # so the link never depends on how the deployment names itself.
        link=f"/auth/primeiro-acesso?token={token}",
        expires_at=datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(seconds=lifetime),
    )


def access_link(session: Session, actor: User, user_id: UUID) -> TeamAccessLink:
    """A new first-access (or forgotten-password) link. The earlier ones keep
    working until a password is chosen, which voids them all."""
    _require_admin(actor)
    member = _member(session, user_id)
    result = _link(session, actor, member)
    emit_audit_event(
        AuditAction.PASSWORD_FORGOT,
        AuditOutcome.SUCCESS,
        actor=actor_from_user(actor),
        resource_type="user",
        resource_id=str(member.id),
        extra={"target_email": member.email, "issued_by_admin": True},
    )
    return result
