"use client";

import { Button, Text } from "@opal/components";
import { StopReason } from "@/app/app/services/streamingModels";
import type {
  TurnGroup,
  TransformedStep,
} from "@/app/app/message/messageComponents/timeline/transformers";
import type { ToolSnapshot } from "@/lib/tools/types";
import { getTonToolKey } from "@/lib/ton/chat-execution";
import { COPY } from "@/lib/ton/copy";
import {
  TonToolCard,
  cardNeedsAttention,
} from "@/app/app/message/messageComponents/renderers/TonToolCard";
import { buildWorkLog } from "@/lib/ton/work-log";
import { useTonUnitNames } from "@/lib/ton/api";
import AnswerDetails from "@/views/ton/chat/AnswerDetails";

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

/** Tools whose result is shown as a rich card in the answer. */
const CARD_TOOLS = [
  "ton_analyze_closing",
  "ton_get_dre_readiness",
  "ton_get_recent_changes",
  "ton_draft_email_flow",
  "ton_draft_automation",
  "ton_get_finding",
  "ton_get_readiness_evidence",
  "ton_generate_closing_report",
  "ton_generate_executive_brief",
];

/** Readiness-style tools share one card per period and scope. */
const DRE_CARD_TOOLS = new Set([
  "ton_analyze_closing",
  "ton_get_dre_readiness",
]);

/**
 * What a TON answer leaves behind, below the text. Cards that ask for an
 * action stay visible; sources, specialists and the other result cards fold
 * behind a details bar. Follow-ups link to the areas the analysis touched.
 */
export function TonExecutionSummary({
  turnGroups,
  tools,
  stopped,
  stopReason,
}: TonExecutionSummaryProps) {
  const unitNames = useTonUnitNames();
  const families = new Map<string, TransformedStep[]>();
  for (const step of turnGroups.flatMap((group) => group.steps)) {
    const key = getTonToolKey(step, tools);
    if (key) families.set(key, [...(families.get(key) ?? []), step]);
  }
  if (!families.size) return null;
  if (!stopped || stopReason === StopReason.USER_CANCELLED) return null;

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
  const log = buildWorkLog(turnGroups, tools, {
    stopped: true,
    answering: false,
    unitNames,
  });
  // One card per kind and subject; a later call supersedes an earlier one.
  const cardsById = new Map<string, (typeof log.queries)[number]>();
  for (const query of log.queries) {
    if (
      !query.key ||
      !CARD_TOOLS.includes(query.key) ||
      query.status !== "done"
    )
      continue;
    const kind = DRE_CARD_TOOLS.has(query.key) ? "dre" : query.key;
    cardsById.set(`${kind}|${query.subject ?? ""}`, query);
  }
  const cards = [...cardsById.entries()].map(([id, query]) => ({
    id,
    attention: cardNeedsAttention(query.data),
    node: (
      <TonToolCard
        key={id}
        toolName={query.key ?? ""}
        data={query.data}
        subtitle={query.subject}
      />
    ),
  }));
  const prominent = cards.filter((card) => card.attention);
  const folded = cards.filter((card) => !card.attention);
  return (
    <div className="flex flex-col gap-3 px-3">
      {prominent.map((card) => card.node)}
      <AnswerDetails
        sources={log.sources}
        origins={log.origins}
        specialists={log.specialists}
        results={folded.map((card) => card.node)}
      />
      {followUps.length > 0 && (
        <nav
          aria-label={COPY.analysis.followUps.label}
          className="flex flex-wrap items-center gap-2"
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
