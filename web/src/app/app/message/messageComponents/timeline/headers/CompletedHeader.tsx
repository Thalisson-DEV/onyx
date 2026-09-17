"use client";

import React from "react";
import { useTranslations } from "next-intl";
import { SvgFold, SvgExpand, SvgAddLines, SvgMaximize2 } from "@opal/icons";
import { Button } from "@opal/components";
import Tag from "@/refresh-components/buttons/Tag";
import Text from "@/refresh-components/texts/Text";
import { Tooltip } from "@opal/components";
import { Section } from "@/layouts/general-layouts";
import { ContentAction } from "@opal/layouts";
import { formatDurationSeconds } from "@opal/time";
import { noProp } from "@/lib/utils";
import MemoriesModal from "@/refresh-components/modals/MemoriesModal";
import { useCreateModal } from "@opal/components";

// =============================================================================
// MemoryTagWithTooltip
// =============================================================================

interface MemoryTagWithTooltipProps {
  memoryText: string | null;
  memoryOperation: "add" | "update" | null;
  memoryId: number | null;
  memoryIndex: number | null;
}

function MemoryTagWithTooltip({
  memoryText,
  memoryOperation,
  memoryId,
  memoryIndex,
}: MemoryTagWithTooltipProps) {
  const t = useTranslations("chat.messages.timeline");
  const memoriesModal = useCreateModal();

  const operationLabel =
    memoryOperation === "add"
      ? t("memoryTag.added.label")
      : t("memoryTag.updated.label");

  const tag = <Tag icon={SvgAddLines} label={operationLabel} />;

  if (!memoryText) return tag;

  return (
    <>
      <memoriesModal.Provider>
        <MemoriesModal
          initialTargetMemoryId={memoryId}
          initialTargetIndex={memoryIndex}
          highlightOnOpen
        />
      </memoriesModal.Provider>
      {memoriesModal.isOpen ? (
        <span>{tag}</span>
      ) : (
        <Tooltip
          delayDuration={0}
          side="bottom"
          tooltip={
            <Section
              flexDirection="column"
              alignItems="start"
              padding={1}
              gap={1}
              height="auto"
            >
              <div className="p-1">
                <Text as="p" secondaryBody text03>
                  {memoryText}
                </Text>
              </div>
              <ContentAction
                icon={SvgAddLines}
                title={operationLabel}
                sizePreset="secondary"
                padding={1}
                variant="body"
                color="muted"
                rightChildren={
                  <Button
                    prominence="tertiary"
                    size="sm"
                    icon={SvgMaximize2}
                    onClick={(e) => {
                      e.stopPropagation();
                      memoriesModal.toggle(true);
                    }}
                  />
                }
              />
            </Section>
          }
        >
          <span>{tag}</span>
        </Tooltip>
      )}
    </>
  );
}

// =============================================================================
// CompletedHeader
// =============================================================================

export interface CompletedHeaderProps {
  totalSteps: number;
  collapsible: boolean;
  isExpanded: boolean;
  onToggle: () => void;
  processingDurationSeconds?: number;
  generatedImageCount?: number;
  isMemoryOnly?: boolean;
  memoryText?: string | null;
  memoryOperation?: "add" | "update" | null;
  memoryId?: number | null;
  memoryIndex?: number | null;
}

/** Header when completed - handles both collapsed and expanded states */
export const CompletedHeader = React.memo(function CompletedHeader({
  totalSteps,
  collapsible,
  isExpanded,
  onToggle,
  processingDurationSeconds = 0,
  generatedImageCount = 0,
  isMemoryOnly = false,
  memoryText = null,
  memoryOperation = null,
  memoryId = null,
  memoryIndex = null,
}: CompletedHeaderProps) {
  const t = useTranslations("chat.messages.timeline");

  if (isMemoryOnly) {
    return (
      <div className="flex w-full justify-between">
        <div className="flex items-center px-(--timeline-header-text-padding-x) py-(--timeline-header-text-padding-y)">
          <MemoryTagWithTooltip
            memoryText={memoryText}
            memoryOperation={memoryOperation}
            memoryId={memoryId}
            memoryIndex={memoryIndex}
          />
        </div>
        {collapsible && totalSteps > 0 && isExpanded && (
          <Button
            prominence="tertiary"
            size="md"
            onClick={noProp(onToggle)}
            rightIcon={isExpanded ? SvgFold : SvgExpand}
            aria-label={t("expandButton.ariaLabel")}
            aria-expanded={isExpanded}
          >
            {t("stepsButton.label", { count: totalSteps })}
          </Button>
        )}
      </div>
    );
  }

  // `pre_answer_processing_seconds` measures observable execution: the wall time
  // from request to the first answer token. It is reported as execution time, not
  // as time spent thinking.
  const durationText = processingDurationSeconds
    ? t("activity.duration.label", {
        duration: formatDurationSeconds(processingDurationSeconds),
      })
    : t("activity.unknownDuration.label");

  const imageText =
    generatedImageCount > 0
      ? t("generatedImages.label", { count: generatedImageCount })
      : null;

  const summary = (
    <div className="flex items-center gap-2 px-(--timeline-header-text-padding-x) py-(--timeline-header-text-padding-y)">
      <Text as="p" mainUiAction text03>
        {isExpanded ? durationText : (imageText ?? durationText)}
      </Text>
      {memoryOperation && !isExpanded && (
        <MemoryTagWithTooltip
          memoryText={memoryText}
          memoryOperation={memoryOperation}
          memoryId={memoryId}
          memoryIndex={memoryIndex}
        />
      )}
    </div>
  );

  const className = "flex items-center justify-between w-full";

  // Without a toggle target the row must not announce itself as a button.
  if (!collapsible || totalSteps === 0) {
    return <div className={className}>{summary}</div>;
  }

  // The row is presentational; the button is the control. One tab stop, one
  // accessible name, one `aria-expanded`. The previous `role="button"` +
  // `tabIndex` wrapper nested a control inside a control, announced the row's
  // name over the button's, and created a second tab stop that did the same
  // thing. Making the row itself clickable again would just reintroduce that as
  // a static element with a handler, so the affordance stays on the button.
  return (
    <div className={className}>
      {summary}

      <Button
        prominence="tertiary"
        size="md"
        onClick={noProp(onToggle)}
        rightIcon={isExpanded ? SvgFold : SvgExpand}
        aria-label={t("expandButton.ariaLabel")}
        aria-expanded={isExpanded}
      >
        {t("stepsButton.label", { count: totalSteps })}
      </Button>
    </div>
  );
});
