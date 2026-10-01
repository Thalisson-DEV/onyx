"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { Text } from "@opal/components";
import AppPage from "@/views/AppPage";
import { SearchFiltersProvider } from "@/lib/searchFilters/providers";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useUser } from "@/providers/UserProvider";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";

export default function TonChatPage() {
  const t = useTranslations("tonNavigation");
  const { user } = useUser();
  const canRead = hasPermission(
    user?.effective_permissions ?? [],
    Permission.READ_TON_SOURCES
  );
  const configuration = useSWR<{ persona_id: number | null }>(
    canRead ? "/api/ton/agent/configuration" : null,
    errorHandlingFetcher
  );
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
      router.replace(`/ton/chat?${query.toString()}`);
    }
  }, [hasSession, personaId, initialized, params, router]);

  if (
    !canRead ||
    configuration.error ||
    configuration.data?.persona_id === null
  ) {
    return (
      <Text as="p" font="main-ui-body" color="text-03">
        {t("unavailable")}
      </Text>
    );
  }
  if (!initialized) {
    return (
      <Text as="p" font="main-ui-body" color="text-03">
        {t("loading")}
      </Text>
    );
  }
  return (
    <SearchFiltersProvider>
      <AppPage firstMessage={params.get("firstMessage") ?? undefined} />
    </SearchFiltersProvider>
  );
}
