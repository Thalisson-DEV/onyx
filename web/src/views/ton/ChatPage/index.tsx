"use client";

import { useEffect } from "react";
import useSWR from "swr";
import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgBarChart,
  SvgChevronRight,
  SvgFileText,
  SvgServer,
  SvgSparkle,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { cn } from "@opal/utils";
import AppPage, { type AppPagePresentation } from "@/views/AppPage";
import { SearchFiltersProvider } from "@/lib/searchFilters/providers";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { errorHandlingFetcher } from "@/lib/fetcher";
import {
  useTonAccess,
  useTonClosing,
  useTonPersona,
  useTonSpecialistPersona,
  useTonSpecialists,
} from "@/lib/ton/api";
import { COPY, formatPeriod } from "@/lib/ton/copy";
import { IconTile, LoadingBlock } from "@/views/ton/components/ui";
import { HomeRail } from "@/views/ton/HomePage";

const SUGGESTION_ICONS: Record<string, IconFunctionComponent> = {
  closing: SvgBarChart,
  pending: SvgAlertTriangle,
  summary: SvgFileText,
  sources: SvgServer,
};

function Welcome() {
  return (
    <div className="flex flex-col items-center gap-2 w-full pb-2 text-center">
      <h1 className="ton-title">
        <Text font="heading-h1" color="inherit">
          {COPY.assistant.heroTitle}
        </Text>
      </h1>
      <span className="max-w-xl">
        <Text as="p" font="main-content-body" color="text-03">
          {COPY.assistant.heroBody}
        </Text>
      </span>
    </div>
  );
}

interface StarterMessage {
  name: string;
  message: string;
}

interface SuggestionsProps {
  submit: (message: string) => void;
  /** Persona of a specialist conversation, whose own first questions show. */
  specialistPersonaId?: number | null;
}

function Suggestions({ submit, specialistPersonaId }: SuggestionsProps) {
  const persona = useSWR<{ starter_messages: StarterMessage[] | null }>(
    specialistPersonaId ? `/api/persona/${specialistPersonaId}` : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
  const starters = persona.data?.starter_messages ?? [];
  const items = specialistPersonaId
    ? starters.map((starter, index) => ({
        key: `starter-${index}`,
        label: starter.name,
        prompt: starter.message,
      }))
    : COPY.assistant.suggestions;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full pt-2">
      {items.map((suggestion) => (
        // A whole-card target; no Opal button renders a card surface.
        <button
          key={suggestion.key}
          type="button"
          onClick={() => submit(suggestion.prompt)}
          className="ton-card ton-card-interactive ton-focusable flex items-center gap-3 p-3 text-start"
        >
          <IconTile
            icon={SUGGESTION_ICONS[suggestion.key] ?? SvgSparkle}
            size="md"
            tone="neutral"
          />
          <span className="flex-1 min-w-0">
            <Text font="main-ui-action" color="text-05">
              {suggestion.label}
            </Text>
          </span>
          <SvgChevronRight size={14} className="shrink-0 opacity-60" />
        </button>
      ))}
    </div>
  );
}

/** What the TON is analyzing: the closing period/scope the backend reports. */
function ContextBar({ focus }: { focus: string | null }) {
  const closing = useTonClosing();
  const specialists = useTonSpecialists();
  const specialist = focus
    ? specialists.data?.find((item) => item.key === focus)
    : undefined;
  return (
    <div className="ton-context-bar flex flex-wrap items-center gap-x-4 gap-y-1 px-4 sm:px-6 py-2">
      <span className="flex items-center gap-2">
        <span aria-hidden className="ton-dot" data-tone="success" />
        <Text font="secondary-action" color="text-05">
          {specialist ? specialist.name : COPY.assistant.context.coordinator}
        </Text>
      </span>
      {closing.data && (
        <Text font="secondary-body" color="text-03">
          {`${COPY.assistant.context.label}: ${COPY.nav.closing} · ${formatPeriod(closing.data.period)} · ${closing.data.scope}`}
        </Text>
      )}
      {specialist && (
        <Text font="secondary-body" color="text-03">
          {specialist.objective}
        </Text>
      )}
    </div>
  );
}

function presentation(specialistPersonaId: number | null): AppPagePresentation {
  return {
    welcome: <Welcome />,
    renderSuggestions: (submit) => (
      <Suggestions submit={submit} specialistPersonaId={specialistPersonaId} />
    ),
    hideModelSelector: true,
    hideToolPicker: true,
    placeholder: COPY.assistant.placeholder,
  };
}

export default function TonChatPage() {
  const { canEnter } = useTonAccess();
  const router = useRouter();
  const params = useSearchParams();
  const focus = params.get("foco");
  const coordinator = useTonPersona();
  const specialist = useTonSpecialistPersona(focus);
  // A specialist conversation runs on the specialist's own persona.
  const configuration = focus ? specialist : coordinator;
  const hasSession = params.has(SEARCH_PARAM_NAMES.CHAT_ID);
  const personaId = configuration.data?.persona_id;
  const initialized =
    hasSession ||
    (personaId != null &&
      params.get(SEARCH_PARAM_NAMES.AGENT_ID) === String(personaId));

  useEffect(() => {
    if (!hasSession && personaId != null && !initialized) {
      const query = new URLSearchParams(params);
      query.set(SEARCH_PARAM_NAMES.AGENT_ID, String(personaId));
      router.replace(`/ton/chat?${query.toString()}` as Route);
    }
  }, [hasSession, personaId, initialized, params, router]);

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
  return (
    <div className="flex flex-1 min-h-0 min-w-0">
      <div
        className={cn(
          "flex flex-1 flex-col min-h-0 min-w-0",
          !hasSession && "ton-hero-art"
        )}
      >
        <ContextBar focus={focus} />
        <SearchFiltersProvider>
          <AppPage
            firstMessage={params.get("firstMessage") ?? undefined}
            presentation={presentation(focus ? (personaId ?? null) : null)}
          />
        </SearchFiltersProvider>
      </div>
      {!hasSession && (
        <aside
          aria-label={COPY.home.rail.sources}
          className="ton-rail hidden xl:block w-[300px] shrink-0 overflow-y-auto p-5"
        >
          <HomeRail />
        </aside>
      )}
    </div>
  );
}
