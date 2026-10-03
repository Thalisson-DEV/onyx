"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { useState, type ReactNode } from "react";
import {
  LineItemButton,
  Popover,
  PopoverMenu,
  Text,
  Tooltip,
} from "@opal/components";
import {
  SvgBell,
  SvgHelpCircle,
  SvgLogOut,
  SvgMenu,
  SvgSearch,
  SvgServer,
  SvgSettings,
  SvgSidebar,
} from "@opal/icons";
import { Content, toast } from "@opal/layouts";
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
    <Tooltip
      tooltip={
        latest
          ? COPY.shell.sourcesLastImport(formatRelativeDateTime(latest))
          : undefined
      }
      side="bottom"
    >
      <Link
        href="/ton/fontes"
        className="ton-header-chip ton-focusable hidden md:flex items-center gap-2 px-2.5 h-8"
      >
        <span className="ton-dot" data-tone={healthy ? "success" : "warning"} />
        <Text font="secondary-action" color="inherit" maxLines={1}>
          {healthy ? COPY.shell.sourcesCurrent : COPY.shell.sourcesAttention}
        </Text>
      </Link>
    </Tooltip>
  );
}

function DemoIndicator() {
  const closing = useTonClosing();
  if (!isSyntheticContext(closing.data)) return null;
  return (
    <span
      role="note"
      title={COPY.shell.demo}
      className="ton-demo-chip inline-flex items-center gap-2 px-2.5 h-8"
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
          className="ton-avatar ton-focusable flex items-center justify-center rounded-full w-8 h-8 shrink-0"
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

interface HeaderIconButtonProps {
  label: string;
  onClick?: () => void;
  children: ReactNode;
  badge?: number;
  expanded?: boolean;
  controls?: string;
}

function HeaderIconButton({
  label,
  onClick,
  children,
  badge,
  expanded,
  controls,
}: HeaderIconButtonProps) {
  return (
    // Brand chrome needs an icon trigger that no Opal button provides.
    <button
      type="button"
      aria-label={badge ? `${label} (${badge})` : label}
      aria-expanded={expanded}
      aria-controls={controls}
      onClick={onClick}
      className="ton-header-icon ton-focusable relative flex items-center justify-center w-8 h-8 shrink-0"
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
            className="ton-header-search ton-focusable hidden md:flex items-center gap-2 ps-2.5 pe-1.5 h-8 lg:w-56 xl:w-64"
          >
            <SvgSearch size={14} className="shrink-0" />
            <span className="hidden lg:inline flex-1 min-w-0 text-start">
              <Text font="secondary-body" color="inherit" maxLines={1}>
                {COPY.command.trigger}
              </Text>
            </span>
            <kbd className="ton-kbd ms-auto">Ctrl K</kbd>
          </button>
          <span className="hidden sm:block md:hidden">
            <HeaderIconButton label={COPY.command.trigger} onClick={open}>
              <SvgSearch size={16} />
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
            <SvgBell size={16} />
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
            <SvgHelpCircle size={16} />
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
          <div className="flex flex-col gap-2 border-t border-01 pt-3">
            <div className="flex items-center justify-between gap-2">
              <Text font="secondary-body" color="text-04">
                {COPY.help.shortcut}
              </Text>
              <kbd className="ton-kbd ton-kbd-light">
                {COPY.help.shortcutKeys}
              </kbd>
            </div>
            <div className="flex items-center justify-between gap-2">
              <Text font="secondary-body" color="text-04">
                {COPY.shell.collapseSidebar}
              </Text>
              <kbd className="ton-kbd ton-kbd-light">
                {COPY.shell.sidebarShortcut}
              </kbd>
            </div>
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
  /** Sidebar is docked (desktop): the toggle switches the icon rail. */
  docked: boolean;
  menuOpen: boolean;
  rail: boolean;
  onToggleNavigation: () => void;
}

export default function TonHeader({
  docked,
  menuOpen,
  rail,
  onToggleNavigation,
}: TonHeaderProps) {
  const { canRead } = useTonAccess();
  const toggleLabel = docked
    ? rail
      ? COPY.shell.expandSidebar
      : COPY.shell.collapseSidebar
    : menuOpen
      ? COPY.shell.closeMenu
      : COPY.shell.openMenu;

  return (
    <header className="ton-header flex items-center gap-2 ps-3 pe-3 sm:pe-4">
      <Tooltip
        tooltip={`${toggleLabel} · ${COPY.shell.sidebarShortcut}`}
        side="bottom"
        align="start"
        suppressed={!docked}
      >
        <span className="flex">
          <HeaderIconButton
            label={toggleLabel}
            onClick={onToggleNavigation}
            expanded={docked ? !rail : menuOpen}
            controls="ton-sidebar"
          >
            {docked ? <SvgSidebar size={16} /> : <SvgMenu size={18} />}
          </HeaderIconButton>
        </span>
      </Tooltip>
      <Link
        href="/ton"
        className="ton-focusable flex items-center gap-3 min-w-0 ps-1 pe-2 rounded-08"
      >
        <Image
          src="/ton/vale-norte-logo-reversed.png"
          alt="Vale Norte"
          width={1057}
          height={412}
          priority
          className="h-7 w-auto"
        />
        <span aria-hidden className="ton-chrome-divider h-5 border-s" />
        <span className="ton-product-name">TON</span>
        <span className="ton-tagline hidden xl:block min-w-0">
          <Text font="secondary-body" color="inherit" maxLines={1}>
            {COPY.shell.tagline}
          </Text>
        </span>
      </Link>
      <div className="ms-auto flex items-center gap-1 sm:gap-1.5">
        {canRead && <SearchTrigger />}
        {canRead && <DemoIndicator />}
        {canRead && <SourcesStatus />}
        {canRead && (
          <span
            aria-hidden
            className="ton-chrome-divider hidden md:block h-5 border-s mx-1"
          />
        )}
        {canRead && <Notifications />}
        <span className="hidden sm:block">
          <Help />
        </span>
        <span className="ps-1">
          <AccountMenu />
        </span>
      </div>
    </header>
  );
}
