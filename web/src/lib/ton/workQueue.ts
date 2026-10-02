"use client";

import useSWR from "swr";
import type { Route } from "next";
import { errorHandlingFetcher } from "@/lib/fetcher";
import {
  useTonAccess,
  useTonClosing,
  useTonDataSources,
  useTonReportGroups,
} from "@/lib/ton/api";
import { COPY } from "@/lib/ton/copy";
import {
  type DecisionLog,
  type PeriodChange,
  blockerLabel,
  isDecisionBlocker,
  pendingQueueHref,
  useDecisionLog,
  useReadinessChanges,
} from "@/lib/ton/decisions";
import type {
  ClientSource,
  ClosingOutput,
  Publication,
  ReportGroup,
} from "@/lib/ton/types";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";

const QUEUE = COPY.workQueue;

export interface OverdueAction {
  reference: string;
  title: string;
  owner: string | null;
  deadline: string | null;
  criticality: string;
}

interface OverduePage {
  items: OverdueAction[];
  has_more: boolean;
}

export type WorkImpact = "blocks" | "follow";
export type WorkOrigin = keyof typeof COPY.workQueue.origins;

export interface WorkItem {
  key: string;
  impact: WorkImpact;
  origin: WorkOrigin;
  title: string;
  detail: string | null;
  /** Only when the source system recorded one; never inferred. */
  owner: string | null;
  deadline: string | null;
  href: Route;
  action: string;
}

/** The latest published closing report, newest first; executive briefs excluded. */
export function latestClosingReport(
  groups: ReportGroup[] | undefined
): Publication | null {
  return (
    (groups ?? [])
      .map((group) => group.latest)
      .filter((item) => item.report_type !== "EXECUTIVE")
      .sort((a, b) =>
        b.output.generated_at.localeCompare(a.output.generated_at)
      )[0] ?? null
  );
}

/** Decisions recorded after a report was generated. */
export function decisionsAfter(
  log: DecisionLog | undefined,
  when: string
): number {
  return (log?.entries ?? []).filter((entry) => entry.decided_at > when).length;
}

function chatHref(message: string): Route {
  const query = new URLSearchParams({
    firstMessage: message,
    [SEARCH_PARAM_NAMES.SUBMIT_ON_LOAD]: "true",
  });
  // SAFETY: /ton/chat is a static route; only its query varies.
  return `/ton/chat?${query.toString()}` as Route;
}

interface WorkInputs {
  closing: ClosingOutput;
  change: PeriodChange | undefined;
  pendingDecisions: number;
  sources: ClientSource[];
  report: Publication | null;
  log: DecisionLog | undefined;
  overdue: OverdueAction[];
}

/**
 * Everything that needs a person, ordered by what unblocks the most:
 * broken sources, recorded decisions not applied, decisions to make, data to
 * import, overdue assigned actions, then follow-ups such as a stale report.
 */
export function buildWorkQueue(input: WorkInputs): WorkItem[] {
  const { closing, change } = input;
  const scope = { period: closing.period, unit: closing.unit_id };
  const items: WorkItem[] = [];

  for (const source of input.sources) {
    if (source.status !== "FAILED" && source.status !== "ATTENTION") continue;
    items.push({
      key: `source-${source.key}`,
      impact: source.status === "FAILED" ? "blocks" : "follow",
      origin: "sources",
      title:
        source.status === "FAILED"
          ? QUEUE.sourceFailed(source.name)
          : QUEUE.sourceAttention(source.name),
      detail: source.latest?.failure_reason ?? null,
      owner: null,
      deadline: null,
      href: "/ton/fontes",
      action: QUEUE.review,
    });
  }

  if (input.pendingDecisions > 0) {
    items.push({
      key: "apply",
      impact: "blocks",
      origin: "closing",
      title: COPY.decisionLoop.control.applyTitle(input.pendingDecisions),
      detail: COPY.decisionLoop.control.applyDetail,
      owner: null,
      deadline: null,
      href: pendingQueueHref(scope),
      action: QUEUE.apply,
    });
  }

  const blockers = Object.entries(change?.blockers_after ?? {}).filter(
    ([, count]) => count > 0
  );
  for (const [blocker, count] of blockers
    .filter(([code]) => isDecisionBlocker(code))
    .sort((a, b) => b[1] - a[1])) {
    items.push({
      key: blocker,
      impact: "blocks",
      origin: "closing",
      title: COPY.decisionLoop.control.resolve(count, blockerLabel(blocker)),
      detail: null,
      owner: null,
      deadline: null,
      href: pendingQueueHref({ ...scope, blocker }),
      action: QUEUE.decide,
    });
  }
  for (const [blocker, count] of blockers.filter(
    ([code]) => !isDecisionBlocker(code)
  )) {
    items.push({
      key: blocker,
      impact: "blocks",
      origin: "closing",
      title:
        blocker === "NO_ACTUAL"
          ? COPY.decisionLoop.control.importData(count)
          : blockerLabel(blocker),
      detail: COPY.decisionLoop.control.importDetail,
      owner: null,
      deadline: null,
      href: pendingQueueHref({ ...scope, blocker }),
      action: QUEUE.open,
    });
  }

  for (const action of input.overdue) {
    items.push({
      key: `overdue-${action.reference}`,
      impact: "follow",
      origin: "actions",
      title: action.title,
      detail: QUEUE.overdue(action.reference),
      owner: action.owner,
      deadline: action.deadline,
      href: chatHref(QUEUE.overduePrompt(action.reference)),
      action: QUEUE.askTon,
    });
  }

  if (change && change.status_after === "READY") {
    items.push({
      key: "calculate",
      impact: "follow",
      origin: "closing",
      title: QUEUE.calculate,
      detail: null,
      owner: null,
      deadline: null,
      href: "/ton/dre",
      action: QUEUE.open,
    });
  }

  if (input.report) {
    const later = decisionsAfter(input.log, input.report.output.generated_at);
    const stale =
      later > 0 ||
      input.report.output.normalization_run_id !== closing.normalization_run_id;
    if (stale) {
      items.push({
        key: "report",
        impact: "follow",
        origin: "reports",
        title: QUEUE.reportStale,
        detail: COPY.decisionLoop.control.reportStale(later),
        owner: null,
        deadline: null,
        href: "/ton/automacoes",
        action: QUEUE.open,
      });
    }
  }
  return items;
}

export function useOverdueActions() {
  const { canRead } = useTonAccess();
  return useSWR<OverduePage>(
    canRead ? "/api/ton/agent/actions/overdue?limit=10" : null,
    errorHandlingFetcher
  );
}

export function useWorkQueue() {
  const closing = useTonClosing();
  const sources = useTonDataSources();
  const reports = useTonReportGroups();
  const decisions = useDecisionLog();
  const overdue = useOverdueActions();
  const changes = useReadinessChanges(
    closing.data?.normalization_run_id,
    closing.data?.structure_version_id,
    closing.data?.unit_id
  );
  const change = changes.data?.periods.find(
    (item) => item.period === closing.data?.period
  );
  const items = closing.data
    ? buildWorkQueue({
        closing: closing.data,
        change,
        pendingDecisions: changes.data?.pending_decisions ?? 0,
        sources: sources.data ?? [],
        report: latestClosingReport(reports.data),
        log: decisions.data,
        overdue: overdue.data?.items ?? [],
      })
    : [];
  return {
    items,
    isLoading: closing.isLoading || changes.isLoading,
    error: closing.error ?? changes.error,
  };
}
