"use client";

import { useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { Button, InputTypeIn, Text } from "@opal/components";
import { SvgBubbleText, SvgPlus } from "@opal/icons";
import useChatSessions from "@/hooks/useChatSessions";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useTonPersona } from "@/lib/ton/api";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import type { ChatSession } from "@/app/app/interfaces";
import {
  LoadingBlock,
  PageContainer,
  PageHeader,
  TonCard,
} from "@/views/ton/components/ui";

const UNTITLED = new Set(["", "new chat", "nova conversa"]);
const DAY = 86_400_000;

export function conversationTitle(session: ChatSession): string {
  const name = session.name?.trim() ?? "";
  return UNTITLED.has(name.toLowerCase())
    ? COPY.shell.untitledConversation
    : name;
}

function bucket(session: ChatSession): string {
  const age = Date.now() - new Date(session.time_updated).getTime();
  if (age < DAY) return COPY.conversations.today;
  if (age < 2 * DAY) return COPY.conversations.yesterday;
  if (age < 7 * DAY) return COPY.conversations.week;
  return COPY.conversations.older;
}

export default function ConversationsPage() {
  const persona = useTonPersona();
  const { chatSessions, isLoading, hasMore, isLoadingMore, loadMore } =
    useChatSessions();
  const [query, setQuery] = useState("");
  const personaId = persona.data?.persona_id;
  const term = query.trim().toLowerCase();
  const sessions = chatSessions
    .filter((session) => personaId == null || session.persona_id === personaId)
    .filter(
      (session) =>
        !term || conversationTitle(session).toLowerCase().includes(term)
    );
  const groups = new Map<string, ChatSession[]>();
  for (const session of sessions) {
    const key = bucket(session);
    groups.set(key, [...(groups.get(key) ?? []), session]);
  }

  return (
    <PageContainer className="max-w-[880px]">
      <PageHeader
        title={COPY.conversations.title}
        description={COPY.conversations.description}
        actions={
          <Button href="/ton/chat" icon={SvgPlus}>
            {COPY.shell.newConversation}
          </Button>
        }
      />
      <InputTypeIn
        searchIcon
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={COPY.conversations.search}
        aria-label={COPY.conversations.search}
      />
      {isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} />
        </TonCard>
      )}
      {!isLoading && sessions.length === 0 && (
        <TonCard className="p-5">
          <Text font="main-ui-body" color="text-03">
            {term ? COPY.conversations.noMatch : COPY.shell.noConversations}
          </Text>
        </TonCard>
      )}
      {[...groups].map(([label, items]) => (
        <section key={label} className="flex flex-col gap-2">
          <span className="ton-eyebrow">{label}</span>
          <TonCard as="div" className="flex flex-col p-1.5">
            {items.map((session) => (
              <Link
                key={session.id}
                href={
                  `/ton/chat?${new URLSearchParams({ [SEARCH_PARAM_NAMES.CHAT_ID]: session.id }).toString()}` as Route
                }
                className="ton-row-link ton-focusable flex items-center gap-3 px-3 py-2.5"
              >
                <SvgBubbleText size={16} className="shrink-0 opacity-60" />
                <span className="flex-1 min-w-0">
                  <Text font="main-ui-body" color="text-05" maxLines={1}>
                    {conversationTitle(session)}
                  </Text>
                </span>
                <Text font="secondary-body" color="text-03">
                  {formatRelativeDateTime(session.time_updated)}
                </Text>
              </Link>
            ))}
          </TonCard>
        </section>
      ))}
      {hasMore && (
        <div>
          <Button
            prominence="secondary"
            disabled={isLoadingMore}
            onClick={loadMore}
          >
            {COPY.conversations.loadMore}
          </Button>
        </div>
      )}
    </PageContainer>
  );
}
