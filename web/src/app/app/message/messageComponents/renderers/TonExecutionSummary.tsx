"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Text } from "@opal/components";
import { PacketType, StopReason } from "@/app/app/services/streamingModels";
import type { CustomToolDelta } from "@/app/app/services/streamingModels";
import type {
  TurnGroup,
  TransformedStep,
} from "@/app/app/message/messageComponents/timeline/transformers";
import type { ToolSnapshot } from "@/lib/tools/types";
import { getTonToolKey } from "@/lib/ton/chat-execution";
import { TON_TOOL_NAMES } from "@/lib/ton/labels";
import { useUser } from "@/providers/UserProvider";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import { TonToolCard } from "@/app/app/message/messageComponents/renderers/TonToolCard";

interface TonExecutionSummaryProps {
  turnGroups: TurnGroup[];
  tools: ToolSnapshot[];
  stopped: boolean;
  stopReason?: StopReason;
}

function stepData(step: TransformedStep | undefined): CustomToolDelta | null {
  if (!step) return null;
  for (const packet of [...step.packets].reverse()) {
    if (packet.obj.type === PacketType.CUSTOM_TOOL_DELTA) return packet.obj;
  }
  return null;
}

function stepStatus(step: TransformedStep, stopped: boolean): string {
  if (
    step.packets.some(
      (packet) =>
        packet.obj.type === PacketType.ERROR ||
        (packet.obj.type === PacketType.CUSTOM_TOOL_DELTA && packet.obj.error)
    )
  )
    return "FAILED";
  if (step.packets.some((packet) => packet.obj.type === PacketType.SECTION_END))
    return "COMPLETED";
  return stopped ? "SKIPPED" : "RUNNING";
}

export function TonExecutionSummary({
  turnGroups,
  tools,
  stopped,
  stopReason,
}: TonExecutionSummaryProps) {
  const t = useTranslations("tonRuntime");
  const { user } = useUser();
  const canInspect = hasPermission(
    user?.effective_permissions ?? [],
    Permission.FULL_ADMIN_PANEL_ACCESS
  );
  const [technicalOpen, setTechnicalOpen] = useState(false);
  const families = new Map<string, TransformedStep[]>();
  for (const step of turnGroups.flatMap((group) => group.steps)) {
    const key = getTonToolKey(step, tools);
    if (key) families.set(key, [...(families.get(key) ?? []), step]);
  }
  if (!families.size) return null;
  const steps = [...families.values()].flat();
  const allCompleted = steps.every(
    (step) => stepStatus(step, stopped) === "COMPLETED"
  );
  const canceled = stopReason === StopReason.USER_CANCELLED;
  return (
    <section
      className="flex flex-col gap-3 border border-01 rounded-12 p-4"
      aria-label={t("execution")}
    >
      <Text as="h3" font="main-ui-action">
        {canceled
          ? t("analysisStopped")
          : allCompleted && stopped
            ? t("analysisCompleted")
            : stopped
              ? t("analysisPartial")
              : t("analysisRunning")}
      </Text>
      <div className="flex flex-col gap-2">
        {[...families].map(([key, calls]) => (
          <div key={key} className="flex items-center justify-between gap-3">
            <Text font="main-ui-body">
              {t("family", {
                name: TON_TOOL_NAMES[key] ?? key,
                count: calls.length,
              })}
            </Text>
            <TonStatusTag
              status={
                calls.some((step) => stepStatus(step, stopped) === "FAILED")
                  ? "FAILED"
                  : calls.every(
                        (step) => stepStatus(step, stopped) === "COMPLETED"
                      )
                    ? "COMPLETED"
                    : stopped
                      ? "PARTIAL"
                      : "RUNNING"
              }
            />
          </div>
        ))}
      </div>
      {[...families]
        .filter(([key]) =>
          [
            "ton_get_finding",
            "ton_get_readiness_evidence",
            "ton_generate_closing_report",
            "ton_generate_executive_brief",
          ].includes(key)
        )
        .map(([key, calls]) => (
          <TonToolCard
            key={key}
            toolName={key}
            data={stepData(calls[calls.length - 1])?.data}
          />
        ))}
      <details>
        <summary>
          <Text font="main-ui-action">{t("viewSteps")}</Text>
        </summary>
        <div className="flex flex-col gap-3 pt-3">
          {[...families].map(([key, calls]) => (
            <details key={key}>
              <summary>
                <Text font="main-ui-body">
                  {t("family", {
                    name: TON_TOOL_NAMES[key] ?? key,
                    count: calls.length,
                  })}
                </Text>
              </summary>
              {calls.map((step) => (
                <div key={step.key} className="pt-2">
                  <TonStatusTag status={stepStatus(step, stopped)} />
                  <TonToolCard toolName={key} data={stepData(step)?.data} />
                </div>
              ))}
            </details>
          ))}
        </div>
      </details>
      {canInspect && (
        <details
          onToggle={(event) => setTechnicalOpen(event.currentTarget.open)}
        >
          <summary>
            <Text font="main-ui-action">{t("technical")}</Text>
          </summary>
          {technicalOpen && (
            <pre className="overflow-auto text-xs p-3">
              {JSON.stringify(
                steps.map((step) => step.packets),
                null,
                2
              )}
            </pre>
          )}
        </details>
      )}
    </section>
  );
}
