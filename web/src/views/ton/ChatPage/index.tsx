"use client";

import "@/views/ton/chat/chat.css";
import "@/views/ton/chat/assistant.css";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgBarChart,
  SvgBubbleText,
  SvgFileText,
  SvgServer,
  SvgSparkle,
  SvgWallet,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { useUser } from "@/providers/UserProvider";
import { getUserDisplayName } from "@/lib/users/svc";
import AppPage, { type AppPagePresentation } from "@/views/AppPage";
import { SearchFiltersProvider } from "@/lib/searchFilters/providers";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { errorHandlingFetcher } from "@/lib/fetcher";
import type { InputPrompt } from "@/app/app/interfaces";
import {
  useTonAccess,
  useTonClosing,
  useTonPersona,
  useTonSpecialistPersona,
} from "@/lib/ton/api";
import { COPY, formatPeriod, formatRelativeDateTime } from "@/lib/ton/copy";
import {
  isArtifactKind,
  markCreate,
  useArtifactStore,
  useCreateMode,
} from "@/lib/ton/artifacts";
import { LoadingBlock } from "@/views/ton/components/ui";
import TonMark from "@/views/ton/chat/TonMark";
import ArtifactPanel from "@/views/ton/chat/artifacts/ArtifactPanel";
import { ARTIFACT_ICONS } from "@/views/ton/chat/artifacts/ArtifactCard";
import { conversationTitle } from "@/views/ton/ConversationsPage";
import ChatHistory, { useTonSessions } from "@/views/ton/ChatPage/ChatHistory";
import ChatHeader from "@/views/ton/ChatPage/ChatHeader";
import CreateMenu, {
  CREATE_ITEMS,
  chooseCreate,
} from "@/views/ton/ChatPage/CreateMenu";

const CHAT = COPY.chat;
const HISTORY_KEY = "ton.chat.history-open";

const SUGGESTION_ICONS: Record<string, IconFunctionComponent> = {
  closing: SvgBarChart,
  pending: SvgAlertTriangle,
  summary: SvgFileText,
  sources: SvgServer,
  payables: SvgWallet,
};

/** TON's own "/" commands, shown in place of saved prompts. */
const COMMANDS: InputPrompt[] = CHAT.commands.map((command, index) => ({
  id: -(index + 1),
  prompt: command.prompt,
  content: command.content,
  active: true,
  is_public: false,
}));

function greeting(hour: number): string {
  if (hour < 12) return COPY.assistant.greetMorning;
  if (hour < 18) return COPY.assistant.greetAfternoon;
  return COPY.assistant.greetEvening;
}

/** The TON greets by name and says where the closing stands, in one line. */
function Welcome() {
  const { user } = useUser();
  const closing = useTonClosing();
  const [hour, setHour] = useState<number | null>(null);
  useEffect(() => setHour(new Date().getHours()), []);
  const name = getUserDisplayName(user).split(/[\s@.]/)[0] ?? "";
  const pending = Object.values(closing.data?.blockers ?? {}).reduce(
    (sum, count) => sum + count,
    0
  );
  const status = closing.data
    ? pending > 0
      ? COPY.assistant.statusPending(formatPeriod(closing.data.period), pending)
      : COPY.assistant.statusReady(formatPeriod(closing.data.period))
    : COPY.assistant.heroBody;
  return (
    <div className="tn-chat-welcome">
      <TonMark size={56} />
      <h1 className="tn-chat-welcome-title">
        {hour === null
          ? COPY.assistant.heroTitle
          : COPY.assistant.greeting(greeting(hour), name)}
      </h1>
      <p className="tn-chat-welcome-body">{status}</p>
    </div>
  );
}

interface StarterMessage {
  name: string;
  message: string;
}

function Task({
  icon: Icon,
  title,
  detail,
  onClick,
  href,
  tone,
}: {
  icon: IconFunctionComponent;
  title: string;
  detail?: string;
  onClick?: () => void;
  href?: Route;
  tone?: "muted";
}) {
  const body = (
    <>
      <span className="tn-chat-task-icon" data-tone={tone} aria-hidden>
        <Icon size={14} />
      </span>
      <span className="flex min-w-0 flex-col">
        <span className="tn-chat-task-title">{title}</span>
        {detail && <span className="tn-chat-task-detail">{detail}</span>}
      </span>
    </>
  );
  if (href)
    return (
      <Link href={href} className="tn-chat-task ton-focusable">
        {body}
      </Link>
    );
  return (
    // A whole-row target; no Opal button renders a two-line task row.
    <button
      type="button"
      className="tn-chat-task ton-focusable"
      onClick={onClick}
    >
      {body}
    </button>
  );
}

function Panels({
  submit,
  specialistPersonaId,
  coordinatorId,
}: {
  submit: (message: string) => void;
  specialistPersonaId: number | null;
  coordinatorId: number | undefined;
}) {
  const persona = useSWR<{ starter_messages: StarterMessage[] | null }>(
    specialistPersonaId ? `/api/persona/${specialistPersonaId}` : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
  const { sessions } = useTonSessions(coordinatorId);
  const starters = specialistPersonaId
    ? (persona.data?.starter_messages ?? []).map((starter, index) => ({
        key: `starter-${index}`,
        label: starter.name,
        prompt: starter.message,
      }))
    : COPY.assistant.suggestions;
  const recent = sessions.slice(0, 4);
  return (
    <div className="tn-chat-panels">
      <section className="tn-chat-panel" aria-labelledby="tn-start">
        <h2 id="tn-start">{CHAT.panels.start}</h2>
        {starters.map((item) => (
          <Task
            key={item.key}
            icon={SUGGESTION_ICONS[item.key] ?? SvgSparkle}
            title={item.label}
            onClick={() => submit(item.prompt)}
          />
        ))}
      </section>
      <section className="tn-chat-panel" aria-labelledby="tn-resume">
        <h2 id="tn-resume">{CHAT.panels.resume}</h2>
        {recent.length === 0 && (
          <Text font="secondary-body" color="text-03">
            {CHAT.panels.noRecent}
          </Text>
        )}
        {recent.map((session) => (
          <Task
            key={session.id}
            icon={SvgBubbleText}
            tone="muted"
            title={conversationTitle(session)}
            detail={formatRelativeDateTime(session.time_updated)}
            href={
              `/ton/chat?${SEARCH_PARAM_NAMES.CHAT_ID}=${session.id}` as Route
            }
          />
        ))}
      </section>
      <section className="tn-chat-panel" aria-labelledby="tn-create">
        <h2 id="tn-create">{CHAT.panels.create}</h2>
        {CREATE_ITEMS.map((item) => (
          <Task
            key={item.key}
            icon={ARTIFACT_ICONS[item.key]}
            title={item.label}
            detail={item.description}
            onClick={() => chooseCreate(item.key)}
          />
        ))}
      </section>
    </div>
  );
}

function readHistoryOpen(): boolean {
  try {
    return window.localStorage.getItem(HISTORY_KEY) !== "0";
  } catch {
    return true;
  }
}

export default function TonChatPage() {
  const { canEnter } = useTonAccess();
  const router = useRouter();
  const params = useSearchParams();
  const focus = params.get("foco");
  const chatId = params.get(SEARCH_PARAM_NAMES.CHAT_ID);
  const coordinator = useTonPersona();
  const specialist = useTonSpecialistPersona(focus);
  // A specialist conversation runs on the specialist's own persona.
  const configuration = focus ? specialist : coordinator;
  const hasSession = chatId !== null;
  const personaId = configuration.data?.persona_id;
  const coordinatorId = coordinator.data?.persona_id ?? undefined;
  const initialized =
    hasSession ||
    (personaId != null &&
      params.get(SEARCH_PARAM_NAMES.AGENT_ID) === String(personaId));
  const { sessions } = useTonSessions(undefined);
  const [historyOpen, setHistoryOpen] = useState(true);
  const resetArtifacts = useArtifactStore((state) => state.reset);
  const artifactExpanded = useArtifactStore((state) => state.expanded);
  const createKind = useCreateMode((state) => state.kind);
  const setCreateKind = useCreateMode((state) => state.setKind);

  useEffect(() => setHistoryOpen(readHistoryOpen()), []);
  // Artifacts and the "Criar" mark belong to one conversation.
  // A link from the library opens one artifact of the conversation.
  // "?criar=painel" arrives with the result already marked.
  const wantedArtifact = params.get("artefato");
  const createParam = params.get("criar");
  useEffect(() => {
    resetArtifacts(wantedArtifact);
    setCreateKind(isArtifactKind(createParam) ? createParam : null);
  }, [chatId, wantedArtifact, createParam, resetArtifacts, setCreateKind]);

  useEffect(() => {
    if (!hasSession && personaId != null && !initialized) {
      const query = new URLSearchParams(params);
      query.set(SEARCH_PARAM_NAMES.AGENT_ID, String(personaId));
      router.replace(`/ton/chat?${query.toString()}` as Route);
    }
  }, [hasSession, personaId, initialized, params, router]);

  const presentation = useMemo<AppPagePresentation>(
    () => ({
      welcome: <Welcome />,
      renderSuggestions: (submit) => (
        <Panels
          submit={submit}
          specialistPersonaId={focus ? (personaId ?? null) : null}
          coordinatorId={coordinatorId}
        />
      ),
      hideModelSelector: true,
      hideToolPicker: true,
      placeholder:
        CREATE_ITEMS.find((item) => item.key === createKind)?.placeholder ??
        COPY.assistant.placeholder,
      promptShortcuts: COMMANDS,
      composerControls: <CreateMenu />,
      prepareMessage: (message) => {
        const { kind, setKind } = useCreateMode.getState();
        if (!kind) return message;
        setKind(null);
        return markCreate(kind, message);
      },
    }),
    [focus, personaId, coordinatorId, createKind]
  );

  if (!canEnter || configuration.error || personaId === null) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <Text as="p" font="main-ui-body" color="text-03">
          {COPY.assistant.unavailable}
        </Text>
      </div>
    );
  }
  if (!initialized) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <LoadingBlock label={COPY.assistant.loading} />
      </div>
    );
  }
  const session = sessions.find((item) => item.id === chatId);
  const title = session ? conversationTitle(session) : CHAT.header.untitled;
  const toggleHistory = () => {
    const next = !historyOpen;
    setHistoryOpen(next);
    try {
      window.localStorage.setItem(HISTORY_KEY, next ? "1" : "0");
    } catch {
      // Only a convenience; the default (open) is fine.
    }
  };
  return (
    <div
      className="tn-chat"
      data-artifact-expanded={artifactExpanded || undefined}
    >
      {historyOpen && (
        <ChatHistory
          personaId={coordinatorId}
          currentId={chatId}
          newHref={(focus ? `/ton/chat?foco=${focus}` : "/ton/chat") as Route}
        />
      )}
      <div className="tn-chat-main">
        <ChatHeader
          title={title}
          focus={focus}
          historyOpen={historyOpen}
          onToggleHistory={toggleHistory}
        />
        <div className="tn-chat-runtime" data-new={!hasSession || undefined}>
          <SearchFiltersProvider>
            <AppPage
              firstMessage={params.get("firstMessage") ?? undefined}
              presentation={presentation}
            />
          </SearchFiltersProvider>
          <p className="tn-chat-promise">{CHAT.composer.promise}</p>
        </div>
      </div>
      <ArtifactPanel />
    </div>
  );
}
