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
import {
  brl,
  daysUntil,
  titleNumber,
  useTitles,
  type TitleRow,
} from "@/lib/ton/payables";

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

export type WorkImpact = "blocks" | "urgent" | "follow";
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
      // The import detail lists the rejected rows and links on to Pendências
      // when the import left cases to decide.
      href: `/ton/fontes?detalhe=${source.key}` as Route,
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
  // The order a controller works in: classifying accounts settles items in
  // the other lists, so it comes first; the billing comparison comes last.
  const rank = (code: string) =>
    (BLOCKER_WORK_ORDER.indexOf(code) + 1 || BLOCKER_WORK_ORDER.length + 1) * 1;
  for (const [blocker, count] of blockers
    .filter(([code]) => isDecisionBlocker(code))
    .sort((a, b) => rank(a[0]) - rank(b[0]) || b[1] - a[1])) {
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
  // Decisions that block the DRE first; follow-ups such as a source with
  // rejected rows (already a pending category) after them.
  return [
    ...items.filter((item) => item.impact === "blocks"),
    ...items.filter((item) => item.impact !== "blocks"),
  ];
}

const BLOCKER_WORK_ORDER = [
  "UNMAPPED_UNIT",
  "UNMAPPED_ACCOUNT",
  "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED",
  "DRE_ACCOUNT_UNMAPPED",
  "DRE_MAPPING_PENDING_APPROVAL",
  "REVIEW_UNRESOLVED",
  "EXCLUDED_SOURCE_ROWS",
  "SOURCE_RECONCILIATION_UNRESOLVED",
  "SOURCE_RECONCILIATION_AMBIGUOUS",
];

export function useOverdueActions() {
  const { canRead } = useTonAccess();
  return useSWR<OverduePage>(
    canRead ? "/api/ton/agent/actions/overdue?limit=10" : null,
    errorHandlingFetcher
  );
}

const OPEN_TITLES = [
  "WAITING_ATTACHMENT",
  "WAITING_SUPPLIER",
  "RECEIVED",
  "RETURNED",
  "CONFERRED",
  "RELEASED",
];

/** Payable titles that need someone today: overdue and blocked ones. */
export function payableItems(titles: TitleRow[]): WorkItem[] {
  const open = titles.filter(
    (row) => row.kind === "REAL" && OPEN_TITLES.includes(row.status)
  );
  const late = open.filter((row) => daysUntil(row.due_date) < 0);
  const today = open.filter((row) => daysUntil(row.due_date) === 0);
  const blocked = open.filter((row) => row.blocking > 0);
  const sum = (rows: TitleRow[]) =>
    brl(rows.reduce((total, row) => total + Number(row.amount), 0));
  const items: WorkItem[] = [];
  if (late.length)
    items.push({
      key: "payables-late",
      impact: "urgent",
      origin: "payables",
      title: QUEUE.payablesLate(late.length, sum(late)),
      detail: late
        .slice(0, 3)
        .map((row) => `${titleNumber(row.number)} · ${row.supplier_name}`)
        .join(" · "),
      owner: null,
      deadline: null,
      href: "/ton/contas-a-pagar" as Route,
      action: QUEUE.open,
    });
  if (today.length)
    items.push({
      key: "payables-today",
      impact: "follow",
      origin: "payables",
      title: QUEUE.payablesToday(today.length, sum(today)),
      detail: null,
      owner: null,
      deadline: null,
      href: "/ton/contas-a-pagar" as Route,
      action: QUEUE.open,
    });
  if (blocked.length)
    items.push({
      key: "payables-blocked",
      impact: "urgent",
      origin: "payables",
      title: QUEUE.payablesBlocked(blocked.length, sum(blocked)),
      detail: blocked
        .slice(0, 3)
        .map(
          (row) =>
            `${titleNumber(row.number)}${row.top_issue ? ` · ${row.top_issue}` : ""}`
        )
        .join(" · "),
      owner: null,
      deadline: null,
      href: "/ton/contas-a-pagar" as Route,
      action: QUEUE.review,
    });
  return items;
}

export function useWorkQueue() {
  const closing = useTonClosing();
  const sources = useTonDataSources();
  const reports = useTonReportGroups();
  const decisions = useDecisionLog();
  const overdue = useOverdueActions();
  const titles = useTitles();
  const changes = useReadinessChanges(
    closing.data?.normalization_run_id,
    closing.data?.structure_version_id,
    closing.data?.unit_id
  );
  const change = changes.data?.periods.find(
    (item) => item.period === closing.data?.period
  );
  const closingItems = closing.data
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
  // Payables share the day: after what blocks the DRE, before the rest.
  const rank: Record<WorkImpact, number> = { blocks: 0, urgent: 1, follow: 2 };
  const items = [...closingItems, ...payableItems(titles.data ?? [])].sort(
    (a, b) => rank[a.impact] - rank[b.impact]
  );
  return {
    items,
    isLoading: closing.isLoading || changes.isLoading,
    error: closing.error ?? changes.error,
  };
}
