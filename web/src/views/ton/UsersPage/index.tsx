"use client";

import { useState, type ReactNode } from "react";
import { Button, InputTypeIn, Modal, Text } from "@opal/components";
import { SvgLock, SvgUserPlus } from "@opal/icons";
import { cn } from "@opal/utils";
import { useUser } from "@/providers/UserProvider";
import { COPY } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import { TonApiError } from "@/lib/ton/decisions";
import {
  TEAM_API,
  TEAM_COPY,
  memberName,
  sendTeamJson,
  useTeam,
  useTeamUnits,
  type TeamAccessLink,
  type TeamMember,
  type TeamProfile,
  type TeamUnit,
} from "@/lib/ton/team";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusPill,
} from "@/views/ton/components/ui";

const T = TEAM_COPY;
const PROFILES: TeamProfile[] = ["ADMIN", "MANAGER"];

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="ton-eyebrow">{label}</span>
      {children}
    </div>
  );
}

function unitName(unit: TeamUnit | undefined, id: string): string {
  return getBusinessLabel(unit?.name ?? unit?.code ?? id);
}

function errorText(error: unknown): string {
  return error instanceof TonApiError && error.detail
    ? error.detail
    : T.actionFailed;
}

/** Create a person, or change the profile and units of one. */
function MemberDialog({
  member,
  units,
  onClose,
  onCreated,
  onSaved,
}: {
  /** null: a new person. */
  member: TeamMember | null;
  units: TeamUnit[];
  onClose: () => void;
  onCreated: (link: TeamAccessLink) => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(member?.name ?? "");
  const [email, setEmail] = useState(member?.email ?? "");
  const [profile, setProfile] = useState<TeamProfile>(
    member?.profile ?? "MANAGER"
  );
  const [unitIds, setUnitIds] = useState<string[]>(member?.unit_ids ?? []);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const operational = units
    .filter((unit) => unit.kind === "OPERATIONAL")
    .map((unit) => unit.id);
  const needsUnits = profile === "MANAGER" && unitIds.length === 0;
  const ready =
    !needsUnits && (member !== null || /^\S+@\S+\.\S+$/.test(email.trim()));

  async function save() {
    setBusy(true);
    setFailure(null);
    const access = {
      profile,
      unit_ids: profile === "MANAGER" ? unitIds : [],
    };
    try {
      if (member) {
        await sendTeamJson("PUT", `${TEAM_API}/${member.id}`, access);
        onSaved();
      } else {
        onCreated(
          await sendTeamJson<TeamAccessLink>("POST", TEAM_API, {
            ...access,
            email: email.trim(),
            name: name.trim() || null,
          })
        );
      }
    } catch (error) {
      setFailure(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Modal.Content width="md">
        <Modal.Header
          title={
            member
              ? T.dialog.editTitle(memberName(member))
              : T.dialog.createTitle
          }
          description={member ? undefined : T.dialog.intro}
          onClose={() => !busy && onClose()}
        />
        <Modal.Body>
          <div className="w-full flex flex-col gap-4">
            {!member && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label={T.dialog.name}>
                  <InputTypeIn
                    value={name}
                    placeholder={T.dialog.namePlaceholder}
                    maxLength={200}
                    aria-label={T.dialog.name}
                    onChange={(event) => setName(event.target.value)}
                  />
                </Field>
                <Field label={T.dialog.email}>
                  <InputTypeIn
                    value={email}
                    type="email"
                    placeholder={T.dialog.emailPlaceholder}
                    maxLength={320}
                    aria-label={T.dialog.email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </Field>
              </div>
            )}
            <Field label={T.dialog.profile}>
              <div className="flex flex-col gap-2" role="radiogroup">
                {PROFILES.map((item) => (
                  <label
                    key={item}
                    aria-label={T.profile[item]}
                    className={cn(
                      "ton-picker-row items-start gap-3 rounded-08 border border-01 p-3",
                      profile === item && "is-current"
                    )}
                  >
                    <input
                      type="radio"
                      name="ton-team-profile"
                      className="mt-1"
                      checked={profile === item}
                      onChange={() => setProfile(item)}
                    />
                    <span className="flex flex-col gap-0.5">
                      <Text font="main-ui-action" color="text-05">
                        {T.profile[item]}
                      </Text>
                      <Text font="secondary-body" color="text-03">
                        {T.profileHint[item]}
                      </Text>
                    </span>
                  </label>
                ))}
              </div>
            </Field>
            {profile === "MANAGER" && (
              <Field label={T.dialog.units}>
                <div className="flex flex-col gap-1">
                  <span className="flex gap-2">
                    {operational.length > 1 && (
                      <button
                        type="button"
                        className="ton-focusable ton-link-button"
                        onClick={() => setUnitIds(operational)}
                      >
                        {T.dialog.operational(operational.length)}
                      </button>
                    )}
                    {unitIds.length > 0 && (
                      <button
                        type="button"
                        className="ton-focusable ton-link-button"
                        onClick={() => setUnitIds([])}
                      >
                        {T.dialog.clear}
                      </button>
                    )}
                  </span>
                  <ul className="ton-picker-list max-h-60 overflow-auto rounded-08 border border-01">
                    {units.map((unit) => {
                      const checked = unitIds.includes(unit.id);
                      return (
                        <li key={unit.id}>
                          <label className="ton-picker-row">
                            <input
                              type="checkbox"
                              className="ton-checkbox"
                              checked={checked}
                              onChange={() =>
                                setUnitIds((old) =>
                                  checked
                                    ? old.filter((id) => id !== unit.id)
                                    : [...old, unit.id]
                                )
                              }
                            />
                            <Text font="main-ui-body" color="text-05">
                              {unitName(unit, unit.id)}
                            </Text>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                  {needsUnits && (
                    <Text font="secondary-body" color="text-03">
                      {T.dialog.unitsNeeded}
                    </Text>
                  )}
                </div>
              </Field>
            )}
            {failure && (
              <Text as="p" font="secondary-body" color="text-05">
                {failure}
              </Text>
            )}
            <div className="flex justify-end gap-2">
              <Button prominence="tertiary" disabled={busy} onClick={onClose}>
                {T.dialog.cancel}
              </Button>
              <Button disabled={!ready || busy} onClick={() => void save()}>
                {busy
                  ? T.dialog.saving
                  : member
                    ? T.dialog.save
                    : T.dialog.createSave}
              </Button>
            </div>
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      prominence="secondary"
      onClick={() => {
        void navigator.clipboard?.writeText(text).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 2000);
        });
      }}
    >
      {copied ? T.linkDialog.copied : label}
    </Button>
  );
}

/** The first-access link, ready to paste into WhatsApp or e-mail. */
function LinkDialog({
  access,
  onClose,
}: {
  access: TeamAccessLink;
  onClose: () => void;
}) {
  const who = memberName(access.member);
  // Opened only after a click, in the browser; the guard keeps the server
  // render safe.
  const origin = typeof window === "undefined" ? "" : window.location.origin;
  const link = access.link.startsWith("/")
    ? `${origin}${access.link}`
    : access.link;
  const firstName = access.member.name?.trim().split(/\s+/)[0] ?? "";
  const expires = new Date(access.expires_at).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
  return (
    <Modal open onOpenChange={(open) => !open && onClose()}>
      <Modal.Content width="md">
        <Modal.Header
          title={T.linkDialog.title(who)}
          description={T.linkDialog.intro}
          onClose={onClose}
        />
        <Modal.Body>
          <div className="w-full flex flex-col gap-3">
            <code className="ton-team-link">{link}</code>
            <Text font="secondary-body" color="text-03">
              {T.linkDialog.expires(expires)}
            </Text>
            <div className="flex flex-wrap justify-end gap-2">
              <CopyButton
                text={T.linkDialog.message(firstName, link)}
                label={T.linkDialog.copyMessage}
              />
              <CopyButton text={link} label={T.linkDialog.copyLink} />
              <Button onClick={onClose}>{T.linkDialog.close}</Button>
            </div>
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

function ConfirmDialog({
  text,
  busy,
  onConfirm,
  onClose,
}: {
  text: string;
  busy: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal open onOpenChange={(open) => !open && !busy && onClose()}>
      <Modal.Content width="sm">
        <Modal.Header title={T.actions.deactivate} onClose={onClose} />
        <Modal.Body>
          <div className="w-full flex flex-col gap-4">
            <Text as="p" font="main-ui-body" color="text-05">
              {text}
            </Text>
            <div className="flex justify-end gap-2">
              <Button prominence="tertiary" disabled={busy} onClick={onClose}>
                {T.cancel}
              </Button>
              <Button disabled={busy} onClick={onConfirm}>
                {T.confirm}
              </Button>
            </div>
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}

function StatusCell({ member }: { member: TeamMember }) {
  if (!member.active)
    return <StatusPill tone="neutral">{T.status.inactive}</StatusPill>;
  if (member.pending_first_access)
    return <StatusPill tone="warning">{T.status.pending}</StatusPill>;
  return <StatusPill tone="success">{T.status.active}</StatusPill>;
}

export default function UsersPage() {
  const { isAdmin } = useUser();
  const team = useTeam(isAdmin);
  const units = useTeamUnits(isAdmin);
  const [editing, setEditing] = useState<TeamMember | "new" | null>(null);
  const [link, setLink] = useState<TeamAccessLink | null>(null);
  const [deactivating, setDeactivating] = useState<TeamMember | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  if (!isAdmin) {
    return (
      <PageContainer>
        <EmptyState
          icon={SvgLock}
          title={T.noAccessTitle}
          description={T.noAccessDescription}
        />
      </PageContainer>
    );
  }

  const unitList = units.data ?? [];
  const byId = new Map(unitList.map((unit) => [unit.id, unit]));

  /** One request; the list reloads after it. null: it failed (shown). */
  async function run<T>(request: () => Promise<T>): Promise<T | null> {
    setBusy(true);
    setFailure(null);
    try {
      const result = await request();
      await team.mutate();
      return result;
    } catch (error) {
      setFailure(errorText(error));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function issueLink(member: TeamMember) {
    const access = await run(() =>
      sendTeamJson<TeamAccessLink>(
        "POST",
        `${TEAM_API}/${member.id}/access-link`,
        {}
      )
    );
    if (access) setLink(access);
  }

  async function setActive(member: TeamMember, active: boolean) {
    const saved = await run(() =>
      sendTeamJson<TeamMember>("PUT", `${TEAM_API}/${member.id}/active`, {
        active,
      })
    );
    if (saved && !active) setDeactivating(null);
  }

  function unitsText(member: TeamMember): string {
    if (member.profile === "ADMIN") return T.allUnits;
    if (member.unit_ids.length === 0) return "—";
    if (member.unit_ids.length > 2) return T.unitsCount(member.unit_ids.length);
    return member.unit_ids.map((id) => unitName(byId.get(id), id)).join(", ");
  }

  return (
    <PageContainer>
      <BackLink href="/ton/administracao" label={COPY.admin.back} />
      <PageHeader
        eyebrow={T.eyebrow}
        title={T.title}
        description={T.description}
        actions={
          <Button icon={SvgUserPlus} onClick={() => setEditing("new")}>
            {T.create}
          </Button>
        }
      />
      {failure && (
        <Text as="p" font="secondary-body" color="text-05">
          {failure}
        </Text>
      )}
      {team.isLoading && <LoadingBlock label={COPY.common.loading} lines={5} />}
      {team.error && (
        <ErrorState message={T.failedLoad} onRetry={() => team.mutate()} />
      )}
      {team.data && team.data.length === 0 && (
        <Text as="p" font="secondary-body" color="text-03">
          {T.empty}
        </Text>
      )}
      {team.data && team.data.length > 0 && (
        <div className="ton-card overflow-x-auto">
          <table className="ton-ledger w-full border-collapse">
            <thead>
              <tr>
                <th scope="col">{T.columns.person}</th>
                <th scope="col">{T.columns.profile}</th>
                <th scope="col">{T.columns.units}</th>
                <th scope="col">{T.columns.status}</th>
                <th scope="col" className="ton-ledger-end">
                  {T.columns.actions}
                </th>
              </tr>
            </thead>
            <tbody>
              {team.data.map((member) => (
                <tr key={member.id}>
                  <td>
                    <span className="flex flex-col">
                      <span>
                        {memberName(member)}
                        {member.is_you && (
                          <span className="ton-ledger-muted">{` (${T.you})`}</span>
                        )}
                      </span>
                      {member.name && (
                        <span className="ton-ledger-muted">{member.email}</span>
                      )}
                    </span>
                  </td>
                  <td>
                    {member.profile
                      ? T.profile[member.profile]
                      : T.profile.none}
                  </td>
                  <td
                    title={
                      member.profile === "MANAGER"
                        ? member.unit_ids
                            .map((id) => unitName(byId.get(id), id))
                            .join(", ")
                        : undefined
                    }
                  >
                    {unitsText(member)}
                  </td>
                  <td>
                    <StatusCell member={member} />
                  </td>
                  <td className="ton-ledger-end">
                    <span className="inline-flex flex-wrap justify-end gap-3">
                      {member.active && !member.is_you && (
                        <button
                          type="button"
                          className="ton-focusable ton-link-button"
                          disabled={busy}
                          onClick={() => setEditing(member)}
                        >
                          {T.actions.edit}
                        </button>
                      )}
                      {member.active && !member.is_you && (
                        <button
                          type="button"
                          className="ton-focusable ton-link-button"
                          disabled={busy}
                          onClick={() => void issueLink(member)}
                        >
                          {T.actions.link}
                        </button>
                      )}
                      {!member.is_you &&
                        (member.active ? (
                          <button
                            type="button"
                            className="ton-focusable ton-link-button"
                            disabled={busy}
                            onClick={() => setDeactivating(member)}
                          >
                            {T.actions.deactivate}
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="ton-focusable ton-link-button"
                            disabled={busy}
                            onClick={() => void setActive(member, true)}
                          >
                            {T.actions.reactivate}
                          </button>
                        ))}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {editing && (
        <MemberDialog
          member={editing === "new" ? null : editing}
          units={unitList}
          onClose={() => setEditing(null)}
          onCreated={(access) => {
            setEditing(null);
            setLink(access);
            void team.mutate();
          }}
          onSaved={() => {
            setEditing(null);
            void team.mutate();
          }}
        />
      )}
      {link && <LinkDialog access={link} onClose={() => setLink(null)} />}
      {deactivating && (
        <ConfirmDialog
          text={T.confirmDeactivate(memberName(deactivating))}
          busy={busy}
          onClose={() => setDeactivating(null)}
          onConfirm={() => void setActive(deactivating, false)}
        />
      )}
    </PageContainer>
  );
}
