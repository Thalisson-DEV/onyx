"use client";

import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import { MinimalAgent } from "@/lib/agents/types";
import { Text } from "@opal/components";
import { Section } from "@/layouts/general-layouts";
import { SvgEyeClosed } from "@opal/icons";
import { useIncognito } from "@/providers/IncognitoProvider";
import { useTranslations } from "next-intl";

export interface WelcomeMessageProps {
  agent?: MinimalAgent;
  isDefaultAgent: boolean;
}

export default function WelcomeMessage({
  agent,
  isDefaultAgent,
}: WelcomeMessageProps) {
  const t = useTranslations("chat.welcome");
  const { incognitoEnabled } = useIncognito();

  let content: React.ReactNode = null;

  if (incognitoEnabled) {
    content = (
      <Section
        data-testid="incognito-intro"
        flexDirection="column"
        alignItems="center"
        gap={0.5}
        width="full"
      >
        <SvgEyeClosed size={32} className="text-text-04" />
        <Text as="h1" dir="auto" font="heading-h2" color="text-05">
          {t("incognito.title")}
        </Text>
      </Section>
    );
  } else if (isDefaultAgent) {
    content = (
      <Section
        data-testid="central-home-intro"
        flexDirection="column"
        alignItems="start"
        gap={0.5}
        width="full"
      >
        <Text as="h1" dir="auto" font="heading-h2" color="text-05">
          {t("home.title")}
        </Text>
        <Text as="p" dir="auto" font="main-content-muted" color="text-03">
          {t("home.description")}
        </Text>
      </Section>
    );
  } else if (agent) {
    content = (
      <Section
        data-testid="agent-name-display"
        flexDirection="column"
        alignItems="center"
        gap={2}
        width="full"
      >
        <AgentAvatar agent={agent} size={36} />
        <Text
          as="h1"
          dir="auto"
          font="heading-h2"
          color="text-05"
          textPosition="text-center"
        >
          {agent.name}
        </Text>
      </Section>
    );
  }

  // if we aren't using the default agent, we need to wait for the agent info to load
  // before rendering
  if (!content) return null;

  return (
    <div
      data-testid="chat-intro"
      className="flex w-full max-w-(--app-page-main-content-width) flex-col justify-center gap-3"
    >
      {content}
    </div>
  );
}
