"use client";

import { Button, Text } from "@opal/components";
import { PacketType, StopReason } from "@/app/app/services/streamingModels";
import type { CustomToolDelta } from "@/app/app/services/streamingModels";
import type {
  TurnGroup,
  TransformedStep,
} from "@/app/app/message/messageComponents/timeline/transformers";
import type { ToolSnapshot } from "@/lib/tools/types";
import { getTonToolKey } from "@/lib/ton/chat-execution";
import { COPY } from "@/lib/ton/copy";
import { TonToolCard } from "@/app/app/message/messageComponents/renderers/TonToolCard";

interface TonExecutionSummaryProps {
  turnGroups: TurnGroup[];
  tools: ToolSnapshot[];
  stopped: boolean;
  stopReason?: StopReason;
}

type Area = "sources" | "dre" | "evidence" | "report";

const AREAS: Record<Area, string[]> = {
  sources: ["ton_list_sources", "ton_get_source_status"],
  dre: [
    "ton_get_dre_readiness",
    "ton_get_dre_result",
    "ton_get_recent_changes",
    "ton_analyze_closing",
  ],
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
  "ton_analyze_closing",
  "ton_get_dre_readiness",
  "ton_get_recent_changes",
  "ton_get_finding",
  "ton_get_readiness_evidence",
  "ton_generate_closing_report",
  "ton_generate_executive_brief",
];

function stepData(step: TransformedStep | undefined): CustomToolDelta | null {
  if (!step) return null;
  for (const packet of [...step.packets].reverse()) {
    if (packet.obj.type === PacketType.CUSTOM_TOOL_DELTA) return packet.obj;
  }
  return null;
}

/**
 * What a TON answer leaves behind, below the text: result cards and links to
 * the product areas the analysis touched. The step-by-step work (reasoning,
 * queries, specialists, Python) lives in the reasoning timeline above.
 */
export function TonExecutionSummary({
  turnGroups,
  tools,
  stopped,
  stopReason,
}: TonExecutionSummaryProps) {
  const families = new Map<string, TransformedStep[]>();
  for (const step of turnGroups.flatMap((group) => group.steps)) {
    const key = getTonToolKey(step, tools);
    if (key) families.set(key, [...(families.get(key) ?? []), step]);
  }
  if (!families.size) return null;
  if (!stopped || stopReason === StopReason.USER_CANCELLED) return null;

  const cards = [...families].filter(([key]) => CARD_TOOLS.includes(key));
  const ran = new Set(
    [...families.keys()].flatMap((key) =>
      (Object.keys(AREAS) as Area[]).filter((area) => AREAS[area].includes(key))
    )
  );
  // Follow-ups only navigate to the product surfaces the analysis touched;
  // nothing is executed or approved from here.
  const labels = COPY.analysis.followUps;
  const followUps: { href: string; label: string }[] = [];
  if (ran.has("dre") || ran.has("evidence"))
    followUps.push({ href: "/ton/pendencias", label: labels.pending });
  if (ran.has("dre")) followUps.push({ href: "/ton/dre", label: labels.dre });
  if (ran.has("sources"))
    followUps.push({ href: "/ton/fontes", label: labels.sources });
  if (ran.has("report"))
    followUps.push({ href: "/ton/relatorios", label: labels.reports });
  if (!cards.length && !followUps.length) return null;
  return (
    <div className="flex flex-col gap-2">
      {cards.map(([key, calls]) => (
        <TonToolCard
          key={key}
          toolName={key}
          data={stepData(calls[calls.length - 1])?.data}
        />
      ))}
      {followUps.length > 0 && (
        <nav
          aria-label={COPY.analysis.followUps.label}
          className="flex flex-wrap items-center gap-2 pt-1"
        >
          <Text font="secondary-body" color="text-03">
            {COPY.analysis.followUps.label}
          </Text>
          {followUps.map((item) => (
            <Button
              key={item.href}
              href={item.href}
              size="sm"
              prominence="secondary"
            >
              {item.label}
            </Button>
          ))}
        </nav>
      )}
    </div>
  );
}
