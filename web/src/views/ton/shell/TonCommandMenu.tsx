"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import {
  SvgArrowUpDown,
  SvgBarChart,
  SvgBubbleText,
  SvgClipboard,
  SvgFileText,
  SvgHome,
  SvgKeystroke,
  SvgServer,
  SvgSettings,
  SvgShield,
  SvgSparkle,
  SvgUsers,
  SvgWorkflow,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import CommandMenu from "@/refresh-components/commandmenu/CommandMenu";
import useChatSessions from "@/hooks/useChatSessions";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useTonAccess, useTonPersona, useTonReportGroups } from "@/lib/ton/api";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import { useUser } from "@/providers/UserProvider";

interface Command {
  key: string;
  label: string;
  icon: IconFunctionComponent;
  href: Route;
  keywords?: string;
}

function normalize(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function matches(query: string, ...values: (string | undefined)[]) {
  const needle = normalize(query.trim());
  if (!needle) return true;
  return values.some((value) => value && normalize(value).includes(needle));
}

export function askHref(message: string): Route {
  const query = new URLSearchParams({
    firstMessage: message,
    [SEARCH_PARAM_NAMES.SUBMIT_ON_LOAD]: "true",
  });
  return `/ton/chat?${query.toString()}` as Route;
}

interface TonCommandMenuProps {
  trigger: (open: () => void) => React.ReactNode;
}

/** Product search and navigation over the shared CommandMenu primitive. */
export default function TonCommandMenu({ trigger }: TonCommandMenuProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { hasAdminAccess } = useUser();
  const { canRead, canReadReports } = useTonAccess();
  const reports = useTonReportGroups();
  const persona = useTonPersona();
  const { chatSessions } = useChatSessions();

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const latestReport = reports.data
    ?.map((group) => group.latest)
    .sort((a, b) =>
      b.output.generated_at.localeCompare(a.output.generated_at)
    )[0];

  const pages = useMemo<Command[]>(() => {
    const items = COPY.command.items;
    const list: Command[] = [
      { key: "overview", label: items.overview, icon: SvgHome, href: "/ton" },
      {
        key: "assistant",
        label: items.assistant,
        icon: SvgBubbleText,
        href: "/ton/chat",
        keywords: "assistente chat perguntar",
      },
      {
        key: "closing",
        label: items.closing,
        icon: SvgBarChart,
        href: "/ton/fechamento",
        keywords: "fechamento mensal",
      },
      {
        key: "dre",
        label: items.dre,
        icon: SvgClipboard,
        href: "/ton/dre",
        keywords: "demonstrativo resultado",
      },
      {
        key: "pending",
        label: items.pending,
        icon: SvgShield,
        href: "/ton/pendencias",
        keywords: "pendencias decisoes bloqueios",
      },
      {
        key: "automations",
        label: items.automations,
        icon: SvgWorkflow,
        href: "/ton/automacoes",
        keywords: "rotinas r3 agenda fluxos email e-mail workflow alerta aprovacao",
      },
      {
        key: "reports",
        label: items.reports,
        icon: SvgFileText,
        href: "/ton/relatorios",
      },
      {
        key: "sources",
        label: items.sources,
        icon: SvgServer,
        href: "/ton/fontes",
        keywords: "ng keevo importacao arquivo",
      },
      {
        key: "specialists",
        label: items.specialists,
        icon: SvgUsers,
        href: "/ton/especialistas",
        keywords: "cfo auditor ceo",
      },
      {
        key: "conversations",
        label: items.conversations,
        icon: SvgBubbleText,
        href: "/ton/conversas",
        keywords: "historico",
      },
    ];
    if (hasAdminAccess)
      list.push({
        key: "admin",
        label: items.admin,
        icon: SvgSettings,
        href: "/ton/administracao",
        keywords: "configuracao acesso",
      });
    return list;
  }, [hasAdminAccess]);

  const go = useCallback(
    (href: Route) => {
      setOpen(false);
      router.push(href);
    },
    [router]
  );

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) setQuery("");
  }

  if (!canRead) return <>{trigger(() => undefined)}</>;

  const personaId = persona.data?.persona_id;
  const conversations = chatSessions
    .filter((session) => personaId == null || session.persona_id === personaId)
    .filter((session) => query.trim() && matches(query, session.name))
    .slice(0, 6);
  const visiblePages = pages.filter((page) =>
    matches(query, page.label, page.keywords)
  );
  const analyze = COPY.assistant.suggestions[0];
  const showAnalyze = matches(query, COPY.command.items.analyze, "analisar");
  const showLatest =
    canReadReports &&
    !!latestReport &&
    matches(query, COPY.command.items.latestReport, "relatorio");
  const question = query.trim();

  return (
    <>
      {trigger(() => setOpen(true))}
      <CommandMenu open={open} onOpenChange={handleOpenChange}>
        <CommandMenu.Content>
          <CommandMenu.Header
            placeholder={COPY.command.placeholder}
            value={query}
            onValueChange={setQuery}
            onClose={() => setOpen(false)}
          />
          <CommandMenu.List emptyMessage={COPY.command.empty}>
            {question && (
              <CommandMenu.Action
                value="ask"
                icon={SvgSparkle}
                onSelect={() => go(askHref(question))}
                defaultHighlight
              >
                {COPY.command.ask(question)}
              </CommandMenu.Action>
            )}
            {(showAnalyze || showLatest) && (
              <CommandMenu.Filter value="actions-group" isApplied>
                {COPY.command.actions}
              </CommandMenu.Filter>
            )}
            {showAnalyze && analyze && (
              <CommandMenu.Action
                value="analyze"
                icon={SvgSparkle}
                onSelect={() => go(askHref(analyze.prompt))}
                defaultHighlight={!question}
              >
                {COPY.command.items.analyze}
              </CommandMenu.Action>
            )}
            {showLatest && latestReport && (
              <CommandMenu.Action
                value="latest-report"
                icon={SvgFileText}
                onSelect={() => go(latestReport.report_url as Route)}
              >
                {COPY.command.items.latestReport}
              </CommandMenu.Action>
            )}
            {visiblePages.length > 0 && (
              <CommandMenu.Filter value="pages-group" isApplied>
                {COPY.command.pages}
              </CommandMenu.Filter>
            )}
            {visiblePages.map((page) => (
              <CommandMenu.Item
                key={page.key}
                value={`page-${page.key}`}
                icon={page.icon}
                onSelect={() => go(page.href)}
              >
                {page.label}
              </CommandMenu.Item>
            ))}
            {conversations.length > 0 && (
              <CommandMenu.Filter value="conversations-group" isApplied>
                {COPY.command.conversations}
              </CommandMenu.Filter>
            )}
            {conversations.map((session) => (
              <CommandMenu.Item
                key={session.id}
                value={`chat-${session.id}`}
                icon={SvgBubbleText}
                rightContent={formatRelativeDateTime(session.time_updated)}
                onSelect={() =>
                  go(
                    `/ton/chat?${new URLSearchParams({ [SEARCH_PARAM_NAMES.CHAT_ID]: session.id }).toString()}` as Route
                  )
                }
              >
                {session.name}
              </CommandMenu.Item>
            ))}
          </CommandMenu.List>
          <CommandMenu.Footer
            leftActions={
              <>
                <CommandMenu.FooterAction
                  icon={SvgArrowUpDown}
                  label={COPY.command.select}
                />
                <CommandMenu.FooterAction
                  icon={SvgKeystroke}
                  label={COPY.command.open}
                />
              </>
            }
          />
        </CommandMenu.Content>
      </CommandMenu>
    </>
  );
}
