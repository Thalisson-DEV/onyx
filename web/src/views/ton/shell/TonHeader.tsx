"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { useState, type ReactNode } from "react";
import { LineItemButton, Popover, PopoverMenu, Text } from "@opal/components";
import {
  SvgBell,
  SvgHelpCircle,
  SvgLogOut,
  SvgMenu,
  SvgSearch,
  SvgServer,
  SvgSettings,
} from "@opal/icons";
import { Content, toast } from "@opal/layouts";
import { cn } from "@opal/utils";
import { useUser } from "@/providers/UserProvider";
import { getUserDisplayName, getUserEmail, logout } from "@/lib/users/svc";
import {
  isSyntheticContext,
  useTonAccess,
  useTonClosing,
  useTonDataSources,
} from "@/lib/ton/api";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import { getFirstPermittedAdminRoute } from "@/lib/permissions";
import { readSeenAt, useTonActivity, writeSeenAt } from "@/lib/ton/activity";
import TonCommandMenu from "@/views/ton/shell/TonCommandMenu";

function initials(name: string): string {
  const parts = name.split(/[\s._-]+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts[1]] : [name];
  return letters
    .map((part) => part?.charAt(0) ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function SourcesStatus() {
  const sources = useTonDataSources();
  if (!sources.data || sources.data.length === 0) return null;
  const configured = sources.data.filter((source) => source.source_id);
  const healthy = configured.every((source) => source.status === "CURRENT");
  const latest = configured
    .map((source) => source.last_success_at)
    .filter((value): value is string => !!value)
    .sort()
    .at(-1);
  return (
    <Link
      href="/ton/fontes"
      className="ton-header-chip ton-focusable hidden md:flex items-center gap-2.5 px-3 py-1.5"
    >
      <span className="ton-dot" data-tone={healthy ? "success" : "warning"} />
      <span className="flex flex-col leading-tight">
        <Text font="secondary-action" color="text-light-05">
          {healthy ? COPY.shell.sourcesCurrent : COPY.shell.sourcesAttention}
        </Text>
        {latest && (
          <Text font="secondary-body" color="text-light-03">
            {COPY.shell.sourcesLastImport(formatRelativeDateTime(latest))}
          </Text>
        )}
      </span>
    </Link>
  );
}

function DemoIndicator() {
  const closing = useTonClosing();
  if (!isSyntheticContext(closing.data)) return null;
  return (
    <span
      role="note"
      title={COPY.shell.demo}
      className="ton-demo-chip inline-flex items-center gap-2 px-2.5 sm:px-3 py-1"
    >
      <span className="ton-dot" data-tone="warning" />
      <span className="hidden xl:inline">
        <Text font="secondary-action" color="inherit">
          {COPY.shell.demo}
        </Text>
      </span>
      <span className="hidden sm:inline xl:hidden">
        <Text font="secondary-action" color="inherit">
          {COPY.shell.demoShort}
        </Text>
      </span>
      <span className="sm:hidden">
        <Text font="secondary-action" color="inherit">
          {COPY.shell.demoTiny}
        </Text>
      </span>
    </span>
  );
}

function AccountMenu() {
  const { user, hasAdminAccess, adminCapabilities } = useUser();
  const router = useRouter();
  const name = getUserDisplayName(user);
  const adminRoute = hasAdminAccess
    ? getFirstPermittedAdminRoute(adminCapabilities) || "/admin/language-models"
    : null;

  function handleLogout() {
    logout()
      .then((response) => {
        if (!response?.ok) {
          toast.error(COPY.shell.signOutFailed);
          return;
        }
        router.push("/auth/login");
      })
      .catch(() => toast.error(COPY.shell.signOutFailed));
  }

  return (
    <Popover>
      <Popover.Trigger asChild>
        {/* Brand chrome needs an avatar trigger that no Opal button provides. */}
        <button
          type="button"
          aria-label={COPY.shell.account}
          className="ton-avatar ton-focusable flex items-center justify-center rounded-full w-9 h-9 shrink-0"
        >
          <Text font="secondary-action" color="inherit">
            {initials(name)}
          </Text>
        </button>
      </Popover.Trigger>
      <Popover.Content align="end" width="lg">
        <PopoverMenu>
          {[
            <div key="who" className="p-2">
              <Content
                sizePreset="main-ui"
                title={name}
                description={getUserEmail(user)}
              />
            </div>,
            null,
            adminRoute && (
              <LineItemButton
                key="admin"
                sizePreset="main-ui"
                variant="section"
                rounding={2}
                icon={SvgSettings}
                title={COPY.shell.tonAdmin}
                href="/ton/administracao"
              />
            ),
            adminRoute && (
              <LineItemButton
                key="technical"
                sizePreset="main-ui"
                variant="section"
                rounding={2}
                icon={SvgServer}
                title={COPY.shell.technicalAdmin}
                href={adminRoute}
              />
            ),
            <LineItemButton
              key="logout"
              sizePreset="main-ui"
              variant="section"
              color="danger"
              rounding={2}
              icon={SvgLogOut}
              title={COPY.shell.signOut}
              onClick={handleLogout}
            />,
          ]}
        </PopoverMenu>
      </Popover.Content>
    </Popover>
  );
}

function HeaderIconButton({
  label,
  onClick,
  children,
  badge,
}: {
  label: string;
  onClick?: () => void;
  children: ReactNode;
  badge?: number;
}) {
  return (
    // Brand chrome needs an icon trigger that no Opal button provides.
    <button
      type="button"
      aria-label={badge ? `${label} (${badge})` : label}
      onClick={onClick}
      className="ton-header-icon ton-focusable relative flex items-center justify-center w-9 h-9 rounded-full shrink-0"
    >
      {children}
      {!!badge && (
        <span aria-hidden className="ton-header-badge">
          {badge > 9 ? "9+" : badge}
        </span>
      )}
    </button>
  );
}

function SearchTrigger() {
  return (
    <TonCommandMenu
      trigger={(open) => (
        <>
          <button
            type="button"
            onClick={open}
            className="ton-header-search ton-focusable hidden md:flex items-center gap-2 ps-3 pe-2 h-9 rounded-full"
          >
            <SvgSearch size={16} />
            <span className="hidden 2xl:inline">
              <Text font="secondary-body" color="inherit">
                {COPY.command.trigger}
              </Text>
            </span>
            <kbd className="ton-kbd">Ctrl K</kbd>
          </button>
          <span className="md:hidden">
            <HeaderIconButton label={COPY.command.trigger} onClick={open}>
              <SvgSearch size={18} />
            </HeaderIconButton>
          </span>
        </>
      )}
    />
  );
}

function Notifications() {
  const { user } = useUser();
  const { events, isLoading } = useTonActivity();
  const [seenAt, setSeenAt] = useState<string | null>(() =>
    readSeenAt(user?.id)
  );
  const latest = events.slice(0, 8);
  const fresh = latest.filter((event) => !seenAt || event.at > seenAt);

  function handleOpenChange(open: boolean) {
    const newest = latest[0];
    if (open || !newest) return;
    writeSeenAt(user?.id, newest.at);
    setSeenAt(newest.at);
  }

  return (
    <Popover onOpenChange={handleOpenChange}>
      <Popover.Trigger asChild>
        <span>
          <HeaderIconButton
            label={COPY.notifications.label}
            badge={fresh.length}
          >
            <SvgBell size={18} />
          </HeaderIconButton>
        </span>
      </Popover.Trigger>
      <Popover.Content align="end">
        <div className="flex flex-col gap-1 p-2 w-[min(360px,calc(100vw-2rem))]">
          <div className="flex flex-col px-2 pt-1 pb-2">
            <Text font="main-ui-action" color="text-05">
              {COPY.notifications.title}
            </Text>
            <Text font="secondary-body" color="text-03">
              {fresh.length
                ? COPY.notifications.newCount(fresh.length)
                : COPY.notifications.subtitle}
            </Text>
          </div>
          {isLoading && (
            <span className="px-2 py-2">
              <Text font="secondary-body" color="text-03">
                {COPY.common.loading}
              </Text>
            </span>
          )}
          {!isLoading && latest.length === 0 && (
            <span className="px-2 py-2">
              <Text font="secondary-body" color="text-03">
                {COPY.notifications.empty}
              </Text>
            </span>
          )}
          <ul className="flex flex-col">
            {latest.map((event) => {
              const isFresh = !seenAt || event.at > seenAt;
              const body = (
                <span className="flex items-start gap-2.5 min-w-0">
                  <span
                    aria-hidden
                    className="ton-dot mt-1.5"
                    data-tone={
                      event.attention
                        ? "danger"
                        : isFresh
                          ? "success"
                          : "neutral"
                    }
                  />
                  <span className="flex flex-col min-w-0">
                    <Text font="secondary-action" color="text-05">
                      {event.title}
                    </Text>
                    <Text font="secondary-body" color="text-03" maxLines={1}>
                      {`${event.detail} · ${formatRelativeDateTime(event.at)}`}
                    </Text>
                  </span>
                </span>
              );
              return (
                <li key={event.key}>
                  {event.href ? (
                    <Link
                      href={event.href}
                      className="ton-row-link ton-focusable flex px-2 py-2"
                    >
                      {body}
                    </Link>
                  ) : (
                    <div className="flex px-2 py-2">{body}</div>
                  )}
                </li>
              );
            })}
          </ul>
          <div className="border-t border-01 mt-1 pt-1">
            <Link
              href={"/ton" as Route}
              className="ton-row-link ton-focusable ton-brand-text flex px-2 py-2"
            >
              <Text font="secondary-action" color="inherit">
                {COPY.notifications.seeActivity}
              </Text>
            </Link>
          </div>
        </div>
      </Popover.Content>
    </Popover>
  );
}

function Help() {
  return (
    <Popover>
      <Popover.Trigger asChild>
        <span>
          <HeaderIconButton label={COPY.help.label}>
            <SvgHelpCircle size={18} />
          </HeaderIconButton>
        </span>
      </Popover.Trigger>
      <Popover.Content align="end">
        <div className="flex flex-col gap-3 p-4 w-[min(340px,calc(100vw-2rem))]">
          <Text font="main-ui-action" color="text-05">
            {COPY.help.title}
          </Text>
          <ul className="flex flex-col gap-3">
            {COPY.help.items.map((item) => (
              <li key={item.title} className="flex flex-col gap-0.5">
                <Text font="secondary-action" color="text-05">
                  {item.title}
                </Text>
                <Text font="secondary-body" color="text-03">
                  {item.body}
                </Text>
              </li>
            ))}
          </ul>
          <div className="flex items-center justify-between gap-2 border-t border-01 pt-3">
            <Text font="secondary-body" color="text-04">
              {COPY.help.shortcut}
            </Text>
            <kbd className="ton-kbd ton-kbd-light">
              {COPY.help.shortcutKeys}
            </kbd>
          </div>
          <Text font="secondary-body" color="text-03">
            {COPY.help.contact}
          </Text>
        </div>
      </Popover.Content>
    </Popover>
  );
}

interface TonHeaderProps {
  menuOpen: boolean;
  onToggleMenu: () => void;
}

export default function TonHeader({ menuOpen, onToggleMenu }: TonHeaderProps) {
  const { canRead } = useTonAccess();
  return (
    <header className="ton-header flex items-center gap-3 px-3 sm:px-5">
      <button
        type="button"
        onClick={onToggleMenu}
        aria-label={menuOpen ? COPY.shell.closeMenu : COPY.shell.openMenu}
        aria-expanded={menuOpen}
        aria-controls="ton-sidebar"
        className={cn(
          "ton-focusable lg:hidden flex items-center justify-center w-9 h-9 rounded-08"
        )}
      >
        <SvgMenu size={20} />
      </button>
      <Link
        href="/ton"
        className="ton-focusable flex items-center gap-3 sm:gap-4 min-w-0 rounded-08"
      >
        <Image
          src="/ton/vale-norte-logo-reversed.png"
          alt="Vale Norte"
          width={1057}
          height={412}
          priority
          className="h-8 sm:h-9 w-auto"
        />
        <span
          aria-hidden
          className="ton-chrome-divider hidden sm:block h-8 border-s"
        />
        <span className="ton-product-badge">TON</span>
        <span className="hidden lg:block min-w-0">
          <Text font="main-ui-body" color="text-light-03" maxLines={1}>
            {COPY.shell.tagline}
          </Text>
        </span>
      </Link>
      <div className="ms-auto flex items-center gap-1.5 sm:gap-2.5">
        {canRead && <SearchTrigger />}
        {canRead && <DemoIndicator />}
        {canRead && <SourcesStatus />}
        {canRead && <Notifications />}
        <Help />
        <AccountMenu />
      </div>
    </header>
  );
}
