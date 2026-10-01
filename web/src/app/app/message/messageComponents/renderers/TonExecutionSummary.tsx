"use client";

import { useState } from "react";
import { Text } from "@opal/components";
import {
  SvgAlertCircle,
  SvgCheckCircle,
  SvgChevronDown,
  SvgCircle,
  SvgSimpleLoader,
} from "@opal/icons";
import { PacketType, StopReason } from "@/app/app/services/streamingModels";
import type { CustomToolDelta } from "@/app/app/services/streamingModels";
import type {
  TurnGroup,
  TransformedStep,
} from "@/app/app/message/messageComponents/timeline/transformers";
import type { ToolSnapshot } from "@/lib/tools/types";
import { getTonToolKey } from "@/lib/ton/chat-execution";
import { TON_TOOL_NAMES } from "@/lib/ton/labels";
import { COPY } from "@/lib/ton/copy";
import { useUser } from "@/providers/UserProvider";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { TonToolCard } from "@/app/app/message/messageComponents/renderers/TonToolCard";

interface TonExecutionSummaryProps {
  turnGroups: TurnGroup[];
  tools: ToolSnapshot[];
  stopped: boolean;
  stopReason?: StopReason;
  /** "progress" goes above the answer; "artifacts" (rich cards) below it. */
  part?: "progress" | "artifacts";
}

type StepStatus = "COMPLETED" | "RUNNING" | "FAILED" | "SKIPPED";
type Phase = keyof typeof COPY.analysis.phases;

const PHASES: Record<Phase, string[]> = {
  sources: ["ton_list_sources", "ton_get_source_status"],
  base: [
    "ton_get_financial_context",
    "ton_get_financial_review_summary",
    "ton_get_billing_summary",
    "ton_get_budget_summary",
    "ton_get_reconciliation_summary",
    "ton_analyze_closing",
  ],
  dre: ["ton_get_dre_readiness", "ton_get_dre_result"],
  evidence: [
    "ton_list_findings",
    "ton_get_finding",
    "ton_get_readiness_evidence",
    "ton_list_occurrences",
    "ton_get_occurrence",
    "ton_list_overdue_actions",
  ],
  report: ["ton_generate_closing_report", "ton_generate_executive_brief"],
};

/** Tools whose last result is shown as a rich card in the answer. */
const CARD_TOOLS = [
  "ton_get_finding",
  "ton_get_readiness_evidence",
  "ton_generate_closing_report",
  "ton_generate_executive_brief",
];

function phaseOf(toolKey: string): Phase {
  for (const [phase, keys] of Object.entries(PHASES)) {
    if (keys.includes(toolKey)) return phase as Phase;
  }
  return "base";
}

function stepData(step: TransformedStep | undefined): CustomToolDelta | null {
  if (!step) return null;
  for (const packet of [...step.packets].reverse()) {
    if (packet.obj.type === PacketType.CUSTOM_TOOL_DELTA) return packet.obj;
  }
  return null;
}

function stepStatus(step: TransformedStep, stopped: boolean): StepStatus {
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

function combined(statuses: StepStatus[]): StepStatus {
  if (statuses.includes("FAILED")) return "FAILED";
  if (statuses.includes("RUNNING")) return "RUNNING";
  if (statuses.every((status) => status === "COMPLETED")) return "COMPLETED";
  return "SKIPPED";
}

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === "COMPLETED")
    return <SvgCheckCircle size={16} className="ton-brand-text shrink-0" />;
  if (status === "RUNNING")
    return <SvgSimpleLoader size={16} className="shrink-0" />;
  if (status === "FAILED")
    return (
      <SvgAlertCircle size={16} className="text-status-error-05 shrink-0" />
    );
  return <SvgCircle size={16} className="text-text-02 shrink-0" />;
}

export function TonExecutionSummary({
  turnGroups,
  tools,
  stopped,
  stopReason,
  part = "progress",
}: TonExecutionSummaryProps) {
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

  if (part === "artifacts") {
    const cards = [...families].filter(([key]) => CARD_TOOLS.includes(key));
    if (!stopped || !cards.length) return null;
    return (
      <div className="flex flex-col gap-2">
        {cards.map(([key, calls]) => (
          <TonToolCard
            key={key}
            toolName={key}
            data={stepData(calls[calls.length - 1])?.data}
          />
        ))}
      </div>
    );
  }

  const phases = (Object.keys(PHASES) as Phase[])
    .map((phase) => {
      const statuses = [...families]
        .filter(([key]) => phaseOf(key) === phase)
        .flatMap(([, calls]) => calls.map((step) => stepStatus(step, stopped)));
      return statuses.length ? { phase, status: combined(statuses) } : null;
    })
    .filter((item): item is { phase: Phase; status: StepStatus } => !!item);

  const steps = [...families.values()].flat();
  const allCompleted = steps.every(
    (step) => stepStatus(step, stopped) === "COMPLETED"
  );
  const canceled = stopReason === StopReason.USER_CANCELLED;
  const heading = canceled
    ? COPY.analysis.stopped
    : allCompleted && stopped
      ? COPY.analysis.completed
      : stopped
        ? COPY.analysis.partial
        : COPY.analysis.running;

  return (
    <section
      className="ton-card flex flex-col gap-3 p-4"
      aria-label={heading}
      aria-busy={!stopped}
    >
      <div className="flex items-center gap-2">
        {!stopped && <SvgSimpleLoader size={16} />}
        <Text as="h3" font="main-ui-action" color="text-05">
          {heading}
        </Text>
      </div>
      <ul className="flex flex-wrap gap-x-5 gap-y-2">
        {phases.map(({ phase, status }) => (
          <li key={phase} className="flex items-center gap-1.5">
            <StatusIcon status={status} />
            <Text
              font="secondary-body"
              color={status === "COMPLETED" ? "text-04" : "text-03"}
            >
              {COPY.analysis.phases[phase]}
            </Text>
          </li>
        ))}
      </ul>

      <details className="group">
        <summary className="flex items-center gap-1 cursor-pointer list-none ton-brand-text w-fit">
          <Text font="secondary-action" color="inherit">
            {COPY.analysis.details}
          </Text>
          <SvgChevronDown
            size={14}
            className="transition-transform group-open:rotate-180"
          />
        </summary>
        <ul className="flex flex-col gap-1.5 pt-3">
          {[...families].map(([key, calls]) => {
            const status = combined(
              calls.map((step) => stepStatus(step, stopped))
            );
            return (
              <li key={key} className="flex items-center gap-2">
                <StatusIcon status={status} />
                <span className="flex-1 min-w-0">
                  <Text font="secondary-body" color="text-04">
                    {TON_TOOL_NAMES[key] ?? key}
                  </Text>
                </span>
                <Text font="secondary-body" color="text-03">
                  {`${COPY.analysis.calls(calls.length)} · ${COPY.analysis.stepStatus[status]}`}
                </Text>
              </li>
            );
          })}
        </ul>
        {canInspect && (
          <details
            className="pt-3"
            onToggle={(event) => setTechnicalOpen(event.currentTarget.open)}
          >
            <summary className="cursor-pointer w-fit">
              <Text font="secondary-action" color="text-03">
                {COPY.analysis.technical}
              </Text>
            </summary>
            {technicalOpen && (
              <pre className="overflow-auto text-xs p-3 max-h-96">
                {JSON.stringify(
                  steps.map((step) => step.packets),
                  null,
                  2
                )}
              </pre>
            )}
          </details>
        )}
      </details>
    </section>
  );
}
