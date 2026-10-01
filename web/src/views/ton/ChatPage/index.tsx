"use client";

import { useEffect } from "react";
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
import { useTonAccess, useTonPersona } from "@/lib/ton/api";
import { COPY } from "@/lib/ton/copy";
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
    <div className="flex flex-col items-center gap-5 w-full pb-2 text-center">
      <SvgSparkle size={36} className="ton-gold-text" aria-hidden />
      <h1 className="ton-display flex flex-wrap justify-center gap-x-3">
        <Text font="heading-h1" color="inherit">
          {COPY.assistant.heroPrefix}
        </Text>
        <span className="ton-display-accent">
          <Text font="heading-h1" color="inherit">
            {COPY.assistant.heroName}
          </Text>
        </span>
      </h1>
      <span className="max-w-xl">
        <Text as="p" font="main-content-body" color="text-03">
          {COPY.assistant.heroBody}
        </Text>
      </span>
      <div className="ton-card flex items-start gap-3 p-4 text-start w-full max-w-2xl">
        <span className="flex items-center justify-center w-10 h-10 rounded-full shrink-0 bg-(--vale-norte-green-90) ton-gold-text">
          <SvgSparkle size={18} />
        </span>
        <div className="flex flex-col gap-1 min-w-0">
          <Text as="p" font="main-ui-body" color="text-04">
            {COPY.assistant.readyTitle}
          </Text>
          <span className="ton-brand-text">
            <Text font="main-ui-action" color="inherit">
              {COPY.assistant.readyAction}
            </Text>
          </span>
        </div>
      </div>
    </div>
  );
}

function Suggestions({ submit }: { submit: (message: string) => void }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full pt-2">
      {COPY.assistant.suggestions.map((suggestion) => (
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

const PRESENTATION: AppPagePresentation = {
  welcome: <Welcome />,
  renderSuggestions: (submit) => <Suggestions submit={submit} />,
  hideModelSelector: true,
  placeholder: COPY.assistant.placeholder,
};

export default function TonChatPage() {
  const { canRead } = useTonAccess();
  const configuration = useTonPersona();
  const router = useRouter();
  const params = useSearchParams();
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

  if (!canRead || configuration.error || personaId === null) {
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
        <SearchFiltersProvider>
          <AppPage
            firstMessage={params.get("firstMessage") ?? undefined}
            presentation={PRESENTATION}
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
