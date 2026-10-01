"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { Text } from "@opal/components";
import {
  SvgBarChart,
  SvgBookOpen,
  SvgBubbleText,
  SvgChevronRight,
  SvgClipboard,
  SvgFileText,
  SvgHome,
  SvgPlus,
  SvgServer,
  SvgSettings,
  SvgUsers,
  SvgWorkflow,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { cn } from "@opal/utils";
import useChatSessions from "@/hooks/useChatSessions";
import { useUser } from "@/providers/UserProvider";
import { getFirstPermittedAdminRoute } from "@/lib/permissions";
import { useTonAccess, useTonPersona } from "@/lib/ton/api";
import { COPY } from "@/lib/ton/copy";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";

const UNTITLED_SESSION_NAMES = new Set(["", "new chat", "nova conversa"]);
const HISTORY_LIMIT = 6;

interface NavItem {
  href: Route;
  label: string;
  icon: IconFunctionComponent;
  match: string[];
  exact?: boolean;
  children?: { href: Route; label: string; match: string[] }[];
}

const NAV: NavItem[] = [
  {
    href: "/ton",
    label: COPY.nav.overview,
    icon: SvgHome,
    match: ["/ton", "/ton/controladoria"],
    exact: true,
  },
  {
    href: "/ton/chat",
    label: COPY.nav.assistant,
    icon: SvgBubbleText,
    match: ["/ton/chat"],
  },
  {
    href: "/ton/fechamento",
    label: COPY.nav.closing,
    icon: SvgBarChart,
    match: ["/ton/fechamento"],
    children: [
      { href: "/ton/dre", label: COPY.nav.dre, match: ["/ton/dre"] },
      {
        href: "/ton/pendencias",
        label: COPY.nav.pending,
        match: ["/ton/pendencias"],
      },
    ],
  },
  {
    href: "/ton/automacoes",
    label: COPY.nav.automations,
    icon: SvgWorkflow,
    match: ["/ton/automacoes", "/ton/rotinas"],
  },
  {
    href: "/ton/relatorios",
    label: COPY.nav.reports,
    icon: SvgFileText,
    match: ["/ton/relatorios", "/ton/controladoria/reports"],
  },
  {
    href: "/ton/fontes",
    label: COPY.nav.sources,
    icon: SvgServer,
    match: ["/ton/fontes", "/ton/data-sources"],
  },
  {
    href: "/ton/especialistas",
    label: COPY.nav.specialists,
    icon: SvgUsers,
    match: ["/ton/especialistas"],
  },
];

function isActive(pathname: string, match: string[], exact = false) {
  return match.some((prefix) =>
    exact ? pathname === prefix : pathname.startsWith(prefix)
  );
}

interface SidebarLinkProps {
  href: Route;
  icon?: IconFunctionComponent;
  label: string;
  active: boolean;
  onNavigate: () => void;
}

function SidebarLink({
  href,
  icon: Icon,
  label,
  active,
  onNavigate,
}: SidebarLinkProps) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className="ton-nav-link flex items-center gap-3 px-3 py-2"
    >
      {Icon && <Icon size={18} className="shrink-0" />}
      <Text font="main-ui-body" color="inherit" maxLines={1}>
        {label}
      </Text>
    </Link>
  );
}

function ConversationHistory({ onNavigate }: { onNavigate: () => void }) {
  const persona = useTonPersona();
  const { chatSessions, currentChatSessionId } = useChatSessions();
  const personaId = persona.data?.persona_id;
  const sessions = chatSessions
    .filter((session) => personaId == null || session.persona_id === personaId)
    .slice(0, HISTORY_LIMIT);

  return (
    <section className="flex flex-col gap-1">
      <span className="ton-sidebar-section-label px-3 pb-1">
        {COPY.shell.history}
      </span>
      {sessions.length === 0 && (
        <span className="px-3 py-1">
          <Text font="secondary-body" color="text-light-03">
            {COPY.shell.noConversations}
          </Text>
        </span>
      )}
      {sessions.map((session) => {
        const name = session.name?.trim() ?? "";
        const title = UNTITLED_SESSION_NAMES.has(name.toLowerCase())
          ? COPY.shell.untitledConversation
          : name;
        const query = new URLSearchParams({
          [SEARCH_PARAM_NAMES.CHAT_ID]: session.id,
        });
        return (
          <Link
            key={session.id}
            href={`/ton/chat?${query.toString()}` as Route}
            onClick={onNavigate}
            aria-current={
              session.id === currentChatSessionId ? "page" : undefined
            }
            className="ton-nav-link flex items-center gap-3 px-3 py-1.5"
          >
            <SvgBubbleText size={14} className="shrink-0 opacity-70" />
            <Text font="secondary-body" color="inherit" maxLines={1}>
              {title}
            </Text>
          </Link>
        );
      })}
      <Link
        href="/ton/conversas"
        onClick={onNavigate}
        className="ton-nav-link ton-nav-sublink flex items-center justify-between gap-2 px-3 py-1.5"
      >
        <Text font="secondary-action" color="inherit">
          {COPY.shell.allConversations}
        </Text>
        <SvgChevronRight size={14} />
      </Link>
    </section>
  );
}

interface TonSidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function TonSidebar({ open, onClose }: TonSidebarProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { hasAdminAccess, adminCapabilities } = useUser();
  const { canRead } = useTonAccess();
  const adminRoute = hasAdminAccess
    ? getFirstPermittedAdminRoute(adminCapabilities) || "/admin/language-models"
    : null;
  const inSession =
    pathname.startsWith("/ton/chat") &&
    searchParams.has(SEARCH_PARAM_NAMES.CHAT_ID);

  return (
    <>
      {open && (
        <div
          aria-hidden
          onClick={onClose}
          className="ton-scrim fixed inset-0 top-(--ton-header-height) z-30 lg:hidden"
        />
      )}
      <aside
        id="ton-sidebar"
        className={cn(
          "ton-sidebar flex flex-col shrink-0 min-h-0",
          "fixed top-(--ton-header-height) bottom-0 start-0 z-40 transition-transform duration-200",
          "lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full rtl:translate-x-full"
        )}
      >
        <div className="flex flex-col gap-5 p-4 flex-1 min-h-0 overflow-y-auto">
          <Link
            href="/ton/chat"
            onClick={onClose}
            aria-current={
              pathname.startsWith("/ton/chat") && !inSession
                ? "page"
                : undefined
            }
            className="ton-new-conversation ton-focusable flex items-center gap-3 px-4 py-3"
          >
            <SvgPlus size={18} />
            <Text font="main-ui-action" color="inherit">
              {COPY.shell.newConversation}
            </Text>
          </Link>

          <nav
            aria-label={COPY.shell.navigationLabel}
            className="flex flex-col gap-0.5"
          >
            {NAV.map((item) => (
              <div key={item.href} className="flex flex-col">
                <SidebarLink
                  href={item.href}
                  icon={item.icon}
                  label={item.label}
                  active={isActive(pathname, item.match, item.exact)}
                  onNavigate={onClose}
                />
                {item.children && (
                  <div className="flex flex-col ms-[1.6rem] ps-3 border-s ton-chrome-divider">
                    {item.children.map((child) => {
                      const active = isActive(pathname, child.match);
                      return (
                        <Link
                          key={child.href}
                          href={child.href}
                          onClick={onClose}
                          aria-current={active ? "page" : undefined}
                          className="ton-nav-link ton-nav-sublink flex items-center gap-2 px-3 py-1.5"
                        >
                          <SvgClipboard size={14} className="shrink-0" />
                          <Text
                            font="secondary-body"
                            color="inherit"
                            maxLines={1}
                          >
                            {child.label}
                          </Text>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </nav>

          {canRead && (
            <>
              <hr className="ton-chrome-divider" />
              <ConversationHistory onNavigate={onClose} />
            </>
          )}
        </div>

        {adminRoute && (
          <div className="flex flex-col gap-0.5 p-3 border-t ton-chrome-divider">
            <SidebarLink
              href="/ton/cobertura"
              icon={SvgBookOpen}
              label={COPY.shell.diagnostics}
              active={pathname.startsWith("/ton/cobertura")}
              onNavigate={onClose}
            />
            <SidebarLink
              href={adminRoute as Route}
              icon={SvgSettings}
              label={COPY.shell.admin}
              active={false}
              onNavigate={onClose}
            />
          </div>
        )}
      </aside>
    </>
  );
}
