"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LineItemButton, Popover, PopoverMenu, Text } from "@opal/components";
import { SvgLogOut, SvgMenu, SvgSettings, SvgSliders } from "@opal/icons";
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
            <LineItemButton
              key="preferences"
              sizePreset="main-ui"
              variant="section"
              rounding={2}
              icon={SvgSliders}
              title={COPY.shell.preferences}
              href="/app/settings"
            />,
            adminRoute && (
              <LineItemButton
                key="admin"
                sizePreset="main-ui"
                variant="section"
                rounding={2}
                icon={SvgSettings}
                title={COPY.shell.admin}
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
      <div className="ms-auto flex items-center gap-2 sm:gap-3">
        {canRead && <DemoIndicator />}
        {canRead && <SourcesStatus />}
        <AccountMenu />
      </div>
    </header>
  );
}
