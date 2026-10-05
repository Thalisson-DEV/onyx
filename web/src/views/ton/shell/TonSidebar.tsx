"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { useEffect, useState, type ReactElement, type ReactNode } from "react";
import {
  Button,
  LineItemButton,
  Popover,
  PopoverMenu,
  Text,
  Tooltip,
} from "@opal/components";
import {
  SvgBarChart,
  SvgBubbleText,
  SvgChevronDown,
  SvgChevronRight,
  SvgEdit,
  SvgFileText,
  SvgHome,
  SvgMail,
  SvgMoreHorizontal,
  SvgPlus,
  SvgServer,
  SvgSettings,
  SvgTrash,
  SvgUsers,
  SvgWorkflow,
} from "@opal/icons";
import { ConfirmationModalLayout, toast } from "@opal/layouts";
import type { IconFunctionComponent } from "@opal/types";
import { cn } from "@opal/utils";
import useChatSessions from "@/hooks/useChatSessions";
import { useUser } from "@/providers/UserProvider";
import { useTonAccess, useTonPersona } from "@/lib/ton/api";
import { COPY } from "@/lib/ton/copy";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { deleteChatSession, renameChatSession } from "@/app/app/services/lib";
import type { ChatSession } from "@/app/app/interfaces";
import ButtonRenaming from "@/refresh-components/buttons/ButtonRenaming";

const UNTITLED_SESSION_NAMES = new Set(["", "new chat", "nova conversa"]);
const HISTORY_LIMIT = 20;

interface NavChild {
  href: Route;
  label: string;
  match: string[];
}

interface NavItem {
  href: Route;
  label: string;
  icon: IconFunctionComponent;
  match: string[];
  exact?: boolean;
  children?: NavChild[];
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
    href: "/ton/fluxos",
    label: COPY.nav.emailFlows,
    icon: SvgMail,
    match: ["/ton/fluxos"],
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
];

function isActive(pathname: string, match: string[], exact = false) {
  return match.some((prefix) =>
    exact ? pathname === prefix : pathname.startsWith(prefix)
  );
}

function sessionTitle(session: ChatSession): string {
  const name = session.name?.trim() ?? "";
  return UNTITLED_SESSION_NAMES.has(name.toLowerCase())
    ? COPY.shell.untitledConversation
    : name;
}

function sessionHref(sessionId: string): Route {
  const query = new URLSearchParams({
    [SEARCH_PARAM_NAMES.CHAT_ID]: sessionId,
  });
  // SAFETY: /ton/chat is a typed route; only the query string varies.
  return `/ton/chat?${query.toString()}` as Route;
}

interface RailTooltipProps {
  label: string;
  rail: boolean;
  children: ReactElement;
}

/** Names an icon-only item while the sidebar is a rail. */
function RailTooltip({ label, rail, children }: RailTooltipProps) {
  return (
    <Tooltip tooltip={label} side="right" suppressed={!rail}>
      {children}
    </Tooltip>
  );
}

interface SidebarLinkProps {
  href: Route;
  icon: IconFunctionComponent;
  label: string;
  active: boolean;
  rail: boolean;
  onNavigate: () => void;
  trailing?: ReactNode;
}

function SidebarLink({
  href,
  icon: Icon,
  label,
  active,
  rail,
  onNavigate,
  trailing,
}: SidebarLinkProps) {
  return (
    <div className="ton-nav-row relative flex items-center">
      <RailTooltip label={label} rail={rail}>
        <Link
          href={href}
          onClick={onNavigate}
          aria-current={active ? "page" : undefined}
          aria-label={rail ? label : undefined}
          className={cn(
            "ton-nav-link flex flex-1 items-center gap-3 h-9 min-w-0",
            rail ? "justify-center px-0" : "px-2.5",
            trailing && !rail && "pe-9"
          )}
        >
          <Icon size={16} className="shrink-0" />
          {!rail && (
            <Text font="main-ui-body" color="inherit" maxLines={1}>
              {label}
            </Text>
          )}
        </Link>
      </RailTooltip>
      {!rail && trailing}
    </div>
  );
}

interface NavGroupProps {
  item: NavItem;
  pathname: string;
  rail: boolean;
  onNavigate: () => void;
}

function NavGroup({ item, pathname, rail, onNavigate }: NavGroupProps) {
  const children = item.children ?? [];
  const childActive = children.some((child) => isActive(pathname, child.match));
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (childActive) setExpanded(true);
  }, [childActive]);

  return (
    <div className="flex flex-col">
      <SidebarLink
        href={item.href}
        icon={item.icon}
        label={item.label}
        active={
          isActive(pathname, item.match, item.exact) || (rail && childActive)
        }
        rail={rail}
        onNavigate={onNavigate}
        trailing={
          // Brand chrome needs a disclosure control that no Opal button provides.
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            aria-label={
              expanded
                ? COPY.shell.hideSection(item.label)
                : COPY.shell.showSection(item.label)
            }
            className="ton-nav-disclosure ton-focusable absolute end-1 flex items-center justify-center w-7 h-7"
          >
            {expanded ? (
              <SvgChevronDown size={14} />
            ) : (
              <SvgChevronRight size={14} />
            )}
          </button>
        }
      />
      {!rail && expanded && (
        <div className="ton-nav-children flex flex-col gap-px ms-[1.125rem] ps-2.5 my-0.5">
          {children.map((child) => {
            const active = isActive(pathname, child.match);
            return (
              <Link
                key={child.href}
                href={child.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className="ton-nav-link ton-nav-sublink flex items-center h-8 px-2.5"
              >
                <Text font="secondary-body" color="inherit" maxLines={1}>
                  {child.label}
                </Text>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface HistoryRowProps {
  session: ChatSession;
  current: boolean;
  onNavigate: () => void;
  onRename: (session: ChatSession, name: string) => Promise<void>;
  onDelete: (session: ChatSession) => void;
}

function HistoryRow({
  session,
  current,
  onNavigate,
  onRename,
  onDelete,
}: HistoryRowProps) {
  const [renaming, setRenaming] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const title = sessionTitle(session);

  if (renaming) {
    return (
      <div className="ton-history-rename flex items-center h-8 px-2.5">
        <ButtonRenaming
          initialName={session.name}
          onRename={(name) => onRename(session, name)}
          onClose={() => setRenaming(false)}
          className="font-secondary-body"
        />
      </div>
    );
  }

  return (
    <div
      className="ton-history-row relative flex items-center"
      data-menu-open={menuOpen || undefined}
    >
      <Link
        href={sessionHref(session.id)}
        onClick={onNavigate}
        aria-current={current ? "page" : undefined}
        title={title}
        className="ton-nav-link ton-nav-sublink flex flex-1 items-center h-8 ps-2.5 pe-8 min-w-0"
      >
        <Text font="secondary-body" color="inherit" maxLines={1}>
          {title}
        </Text>
      </Link>
      <Popover open={menuOpen} onOpenChange={setMenuOpen}>
        <Popover.Trigger asChild>
          {/* Brand chrome needs an icon trigger that no Opal button provides. */}
          <button
            type="button"
            aria-label={COPY.shell.conversationActions(title)}
            className="ton-row-action ton-focusable absolute end-1 flex items-center justify-center w-6 h-6"
          >
            <SvgMoreHorizontal size={14} />
          </button>
        </Popover.Trigger>
        <Popover.Content side="right" align="start" width="md">
          <PopoverMenu>
            {[
              <LineItemButton
                key="rename"
                sizePreset="main-ui"
                variant="section"
                rounding={2}
                icon={SvgEdit}
                title={COPY.shell.renameConversation}
                onClick={() => {
                  setMenuOpen(false);
                  setRenaming(true);
                }}
              />,
              null,
              <LineItemButton
                key="delete"
                sizePreset="main-ui"
                variant="section"
                color="danger"
                rounding={2}
                icon={SvgTrash}
                title={COPY.shell.deleteConversation}
                onClick={() => {
                  setMenuOpen(false);
                  onDelete(session);
                }}
              />,
            ]}
          </PopoverMenu>
        </Popover.Content>
      </Popover>
    </div>
  );
}

function ConversationHistory({ onNavigate }: { onNavigate: () => void }) {
  const router = useRouter();
  const persona = useTonPersona();
  const {
    chatSessions,
    currentChatSessionId,
    refreshChatSessions,
    removeSession,
  } = useChatSessions();
  const [pendingDelete, setPendingDelete] = useState<ChatSession | null>(null);
  const personaId = persona.data?.persona_id;
  const sessions = chatSessions
    .filter((session) => personaId == null || session.persona_id === personaId)
    .slice(0, HISTORY_LIMIT);

  async function handleRename(session: ChatSession, name: string) {
    const response = await renameChatSession(session.id, name);
    if (!response.ok) {
      toast.error(COPY.shell.renameFailed);
      return;
    }
    await refreshChatSessions();
  }

  async function handleDelete(session: ChatSession) {
    setPendingDelete(null);
    const response = await deleteChatSession(session.id);
    if (!response.ok) {
      toast.error(COPY.shell.deleteFailed);
      return;
    }
    removeSession(session.id);
    toast.success(COPY.shell.conversationDeleted);
    if (session.id === currentChatSessionId) router.push("/ton/chat");
    await refreshChatSessions();
  }

  return (
    <section className="flex flex-col gap-px">
      <span className="ton-sidebar-section-label px-2.5 pb-1">
        {COPY.shell.history}
      </span>
      {sessions.length === 0 && (
        <span className="ton-sidebar-hint px-2.5 py-1">
          <Text font="secondary-body" color="inherit">
            {COPY.shell.noConversations}
          </Text>
        </span>
      )}
      {sessions.map((session) => (
        <HistoryRow
          key={session.id}
          session={session}
          current={session.id === currentChatSessionId}
          onNavigate={onNavigate}
          onRename={handleRename}
          onDelete={setPendingDelete}
        />
      ))}
      {sessions.length > 0 && (
        <Link
          href="/ton/conversas"
          onClick={onNavigate}
          className="ton-nav-link ton-nav-sublink ton-nav-more flex items-center gap-1 h-8 px-2.5"
        >
          <Text font="secondary-action" color="inherit">
            {COPY.shell.allConversations}
          </Text>
          <SvgChevronRight size={12} />
        </Link>
      )}

      {pendingDelete && (
        <ConfirmationModalLayout
          icon={SvgTrash}
          title={COPY.shell.deleteConversationTitle}
          description={COPY.shell.deleteConversationDescription(
            sessionTitle(pendingDelete)
          )}
          onClose={() => setPendingDelete(null)}
          submit={
            <Button
              variant="danger"
              onClick={() => void handleDelete(pendingDelete)}
            >
              {COPY.shell.deleteConversationConfirm}
            </Button>
          }
        />
      )}
    </section>
  );
}

interface TonSidebarProps {
  /** Drawer state below the `lg` breakpoint. */
  open: boolean;
  /** Icon rail on desktop. The mobile drawer always shows labels. */
  rail: boolean;
  onClose: () => void;
}

export default function TonSidebar({ open, rail, onClose }: TonSidebarProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { hasAdminAccess } = useUser();
  const { canRead } = useTonAccess();
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
        data-rail={rail || undefined}
        data-open={open || undefined}
        className={cn(
          "ton-sidebar flex flex-col shrink-0 min-h-0",
          "fixed top-(--ton-header-height) bottom-0 start-0 z-40",
          "lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full rtl:translate-x-full"
        )}
      >
        <div
          className={cn(
            "flex flex-col gap-4 pt-3 pb-2",
            rail ? "px-2.5" : "px-3"
          )}
        >
          <RailTooltip label={COPY.shell.newConversation} rail={rail}>
            <Link
              href="/ton/chat"
              onClick={onClose}
              aria-label={rail ? COPY.shell.newConversation : undefined}
              aria-current={
                pathname.startsWith("/ton/chat") && !inSession
                  ? "page"
                  : undefined
              }
              className={cn(
                "ton-new-conversation ton-focusable flex items-center gap-2.5 h-9",
                rail ? "justify-center" : "px-2.5"
              )}
            >
              <SvgPlus size={16} className="shrink-0" />
              {!rail && (
                <Text font="main-ui-action" color="inherit" maxLines={1}>
                  {COPY.shell.newConversation}
                </Text>
              )}
            </Link>
          </RailTooltip>

          <nav
            aria-label={COPY.shell.navigationLabel}
            className="flex flex-col gap-px"
          >
            {NAV.map((item) =>
              item.children ? (
                <NavGroup
                  key={item.href}
                  item={item}
                  pathname={pathname}
                  rail={rail}
                  onNavigate={onClose}
                />
              ) : (
                <SidebarLink
                  key={item.href}
                  href={item.href}
                  icon={item.icon}
                  label={item.label}
                  active={isActive(pathname, item.match, item.exact)}
                  rail={rail}
                  onNavigate={onClose}
                />
              )
            )}
          </nav>

          {canRead && (
            <section className="flex flex-col gap-px">
              {rail ? (
                <hr className="ton-chrome-divider mx-1 mb-2" />
              ) : (
                <span className="ton-sidebar-section-label px-2.5 pb-1">
                  {COPY.shell.team}
                </span>
              )}
              <SidebarLink
                href="/ton/especialistas"
                icon={SvgUsers}
                label={COPY.nav.specialists}
                active={pathname.startsWith("/ton/especialistas")}
                rail={rail}
                onNavigate={onClose}
              />
            </section>
          )}
        </div>

        <div className="ton-sidebar-scroll flex flex-col flex-1 min-h-0 overflow-y-auto px-3 pt-2 pb-3">
          {canRead && !rail && <ConversationHistory onNavigate={onClose} />}
        </div>

        {hasAdminAccess && (
          <div
            className={cn(
              "flex flex-col py-2 border-t ton-chrome-divider",
              rail ? "px-2.5" : "px-3"
            )}
          >
            <SidebarLink
              href="/ton/administracao"
              icon={SvgSettings}
              label={COPY.shell.tonAdmin}
              active={
                pathname.startsWith("/ton/administracao") ||
                pathname.startsWith("/ton/cobertura")
              }
              rail={rail}
              onNavigate={onClose}
            />
          </div>
        )}
      </aside>
    </>
  );
}
