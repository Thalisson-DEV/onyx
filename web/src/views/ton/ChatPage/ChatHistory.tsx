"use client";

import { useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { Button, InputTypeIn, Text } from "@opal/components";
import { SvgPlus } from "@opal/icons";
import useChatSessions from "@/hooks/useChatSessions";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import type { ChatSession } from "@/app/app/interfaces";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import { conversationTitle } from "@/views/ton/ConversationsPage";

const HISTORY = COPY.chat.history;
const DAY = 86_400_000;

function bucket(session: ChatSession): string {
  const age = Date.now() - new Date(session.time_updated).getTime();
  if (age < DAY) return COPY.conversations.today;
  if (age < 2 * DAY) return COPY.conversations.yesterday;
  if (age < 7 * DAY) return COPY.conversations.week;
  return COPY.conversations.older;
}

export function useTonSessions(personaId: number | undefined) {
  const result = useChatSessions();
  const sessions = result.chatSessions.filter(
    (session) => personaId == null || session.persona_id === personaId
  );
  return { ...result, sessions };
}

/** The person's TON conversations beside the chat, newest first. */
export default function ChatHistory({
  personaId,
  currentId,
  newHref,
}: {
  personaId: number | undefined;
  currentId: string | null;
  newHref: Route;
}) {
  const { sessions, isLoading, hasMore, isLoadingMore, loadMore } =
    useTonSessions(personaId);
  const [query, setQuery] = useState("");
  const term = query.trim().toLowerCase();
  const shown = sessions.filter(
    (session) =>
      !term || conversationTitle(session).toLowerCase().includes(term)
  );
  const groups = new Map<string, ChatSession[]>();
  for (const session of shown) {
    const key = bucket(session);
    groups.set(key, [...(groups.get(key) ?? []), session]);
  }

  return (
    <aside className="tn-chat-history" aria-label={HISTORY.title}>
      <div className="tn-chat-history-head">
        <Text as="h2" font="main-ui-action" color="text-05">
          {HISTORY.title}
        </Text>
        <Button href={newHref} size="sm" icon={SvgPlus}>
          {HISTORY.newConversation}
        </Button>
      </div>
      <div className="px-3 pb-2">
        <InputTypeIn
          searchIcon
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={HISTORY.search}
          aria-label={HISTORY.search}
        />
      </div>
      <nav className="tn-chat-history-list" aria-label={HISTORY.title}>
        {!isLoading && shown.length === 0 && (
          <p className="tn-chat-history-empty">
            {term ? HISTORY.noMatch : HISTORY.empty}
          </p>
        )}
        {[...groups.entries()].map(([label, items]) => (
          <section key={label}>
            <h3 className="tn-chat-history-group">{label}</h3>
            <ul>
              {items.map((session) => (
                <li key={session.id}>
                  <Link
                    href={
                      `/ton/chat?${SEARCH_PARAM_NAMES.CHAT_ID}=${session.id}` as Route
                    }
                    className="tn-chat-history-item ton-focusable"
                    aria-current={session.id === currentId ? "page" : undefined}
                  >
                    <span className="tn-chat-history-title">
                      {conversationTitle(session)}
                    </span>
                    <span className="tn-chat-history-meta">
                      {formatRelativeDateTime(session.time_updated)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
        {hasMore && !term && (
          <div className="px-2 py-2">
            <Button
              size="sm"
              prominence="tertiary"
              disabled={isLoadingMore}
              onClick={() => void loadMore()}
            >
              {HISTORY.more}
            </Button>
          </div>
        )}
      </nav>
    </aside>
  );
}
