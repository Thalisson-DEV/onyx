"use client";

import { OnSubmitProps } from "@/hooks/useChatController";
import { useActiveAgent } from "@/lib/agents/hooks";
import type { ProjectFile } from "@/lib/projects/providers";
import { Button, Text } from "@opal/components";
import { SvgArrowUpRight } from "@opal/icons";
import { useTranslations } from "next-intl";

export interface SuggestionsProps {
  onSubmit: (props: OnSubmitProps) => void;
  isDefaultAgent?: boolean;
  currentMessageFiles?: ProjectFile[];
}

export default function Suggestions({
  onSubmit,
  isDefaultAgent = false,
  currentMessageFiles = [],
}: SuggestionsProps) {
  const t = useTranslations("chat.welcome.quickActions");
  const activeAgent = useActiveAgent();

  const suggestions = isDefaultAgent
    ? [
        { label: t("analyzeFile.label"), message: t("analyzeFile.prompt") },
        {
          label: t("reviewContract.label"),
          message: t("reviewContract.prompt"),
        },
        {
          label: t("investigateDifference.label"),
          message: t("investigateDifference.prompt"),
        },
        {
          label: t("analyzeResult.label"),
          message: t("analyzeResult.prompt"),
        },
      ]
    : (activeAgent?.starter_messages ?? []).map(({ message }) => ({
        label: message,
        message,
      }));

  if (suggestions.length === 0) return null;

  const handleSuggestionClick = (suggestion: string) => {
    onSubmit({
      message: suggestion,
      currentMessageFiles,
      deepResearch: false,
    });
  };

  if (!isDefaultAgent) {
    return (
      <div
        data-testid="home-quick-actions"
        className="grid w-full max-w-(--app-page-main-content-width) grid-cols-1 gap-1 p-1 sm:grid-cols-2"
      >
        {suggestions.map(({ label, message }, index) => (
          <Button
            key={`${index}-${label}`}
            prominence="secondary"
            size="md"
            width="full"
            onClick={() => handleSuggestionClick(message)}
          >
            {label}
          </Button>
        ))}
      </div>
    );
  }

  return (
    <div
      data-testid="home-quick-actions"
      className="flex w-full max-w-(--app-page-main-content-width) flex-col items-start gap-1"
    >
      <Text as="p" font="secondary-body" color="text-02">
        {t("contextLabel")}
      </Text>
      <div className="flex max-w-full flex-wrap items-center gap-x-1 gap-y-0.5">
        {suggestions.map(({ label, message }, index) => (
          <Button
            key={`${index}-${label}`}
            icon={SvgArrowUpRight}
            prominence="tertiary"
            size="sm"
            onClick={() => handleSuggestionClick(message)}
          >
            {label}
          </Button>
        ))}
      </div>
    </div>
  );
}
