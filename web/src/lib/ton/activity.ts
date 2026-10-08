"use client";

import type { Route } from "next";
import {
  useTonClosing,
  useTonDataSources,
  useTonReportGroups,
  useTonSpecialists,
} from "@/lib/ton/api";
import { COPY, formatPeriod, plural } from "@/lib/ton/copy";
import {
  pendingQueueHref,
  sumBlockers,
  useDecisionLog,
  useReadinessChanges,
} from "@/lib/ton/decisions";
import { getBusinessLabel } from "@/lib/ton/labels";
import { useAutomationNotices } from "@/lib/ton/automations";

export type ActivityKind =
  | "report"
  | "import"
  | "importFailed"
  | "specialists"
  | "decision"
  | "readiness"
  | "automation";

export interface ActivityEvent {
  key: string;
  kind: ActivityKind;
  at: string;
  title: string;
  detail: string;
  href?: Route;
  /** Events that ask for a human action; the bell highlights them. */
  attention: boolean;
}

/**
 * The TON event feed, derived only from persisted backend state: report
 * publications, source imports, specialist executions, recorded decisions and
 * recomputed bases. Nothing here is inferred or simulated; an event exists
 * because a record exists.
 */
export function useTonActivity(enabled = true) {
  const reports = useTonReportGroups();
  const sources = useTonDataSources();
  const specialists = useTonSpecialists(enabled);
  const decisions = useDecisionLog();
  const closing = useTonClosing(undefined, enabled);
  const notices = useAutomationNotices(enabled);
  const changes = useReadinessChanges(
    closing.data?.normalization_run_id,
    closing.data?.structure_version_id,
    closing.data?.unit_id
  );

  const events: ActivityEvent[] = [];
  for (const group of reports.data ?? []) {
    const { latest } = group;
    events.push({
      key: `report-${latest.revision_id}`,
      kind: "report",
      at: latest.output.generated_at,
      title: COPY.home.activity.reportPublished(
        getBusinessLabel(latest.report_type ?? "MONTHLY_CLOSE")
      ),
      detail: `${getBusinessLabel(latest.status)} · ${formatPeriod(latest.output.period)}`,
      href: latest.report_url as Route,
      attention: false,
    });
  }
  for (const source of sources.data ?? []) {
    for (const run of source.history.length
      ? source.history
      : source.latest
        ? [source.latest]
        : []) {
      if (!run.finished_at) continue;
      if (run.status === "SUCCEEDED") {
        events.push({
          key: `import-${run.id}`,
          kind: "import",
          at: run.finished_at,
          title: COPY.home.activity.sourceImported(source.name),
          detail: `${plural(run.imported, "registro", "registros")} · ${run.filename}`,
          href: "/ton/fontes",
          attention: false,
        });
      } else if (run.status === "FAILED") {
        events.push({
          key: `import-${run.id}`,
          kind: "importFailed",
          at: run.finished_at,
          title: COPY.activity.importFailed(source.name),
          detail: run.filename,
          href: "/ton/fontes",
          attention: true,
        });
      }
    }
  }
  const byTime = new Map<string, string[]>();
  for (const item of specialists.data ?? []) {
    if (!item.last_execution) continue;
    byTime.set(item.last_execution, [
      ...(byTime.get(item.last_execution) ?? []),
      item.name,
    ]);
  }
  for (const [at, names] of byTime) {
    events.push({
      key: `specialists-${at}`,
      kind: "specialists",
      at,
      title: COPY.home.activity.specialistRan(names),
      detail: COPY.nav.closing,
      href: "/ton/fechamento",
      attention: false,
    });
  }
  for (const entry of decisions.data?.entries ?? []) {
    events.push({
      key: `decision-${entry.kind}-${entry.version ?? entry.decided_at}-${entry.subject}`,
      kind: "decision",
      at: entry.decided_at,
      title: COPY.activity.decision(
        COPY.decisionLoop.log.kinds[entry.kind],
        getBusinessLabel(entry.subject)
      ),
      detail: [
        entry.decided_by,
        entry.applied === false ? COPY.decisionLoop.log.pending : null,
      ]
        .filter(Boolean)
        .join(" · "),
      href: pendingQueueHref({ period: closing.data?.period }),
      attention: entry.applied === false,
    });
  }
  const change = changes.data?.periods.find(
    (item) => item.period === closing.data?.period
  );
  if (changes.data?.previous_run_id && change) {
    const before = sumBlockers(change.blockers_before);
    const after = sumBlockers(change.blockers_after);
    const nowReady =
      change.status_before !== "READY" && change.status_after === "READY";
    if (before !== after || nowReady) {
      events.push({
        key: `readiness-${changes.data.run_id}`,
        kind: "readiness",
        at: changes.data.run_started_at,
        title: nowReady
          ? COPY.activity.dreReady(formatPeriod(change.period).toLowerCase())
          : COPY.activity.readinessChanged(before, after),
        detail: formatPeriod(change.period),
        href: nowReady ? "/ton/dre" : "/ton/fechamento",
        attention: nowReady,
      });
    }
  }
  for (const notice of notices.data ?? []) {
    events.push({
      key: `automation-${notice.id}`,
      kind: "automation",
      at: notice.created_at,
      title: notice.title,
      detail: notice.message ? `${notice.automation_name} · ${notice.message}` : notice.automation_name,
      href: (notice.link ?? `/ton/automacoes/${notice.automation_id}`) as Route,
      attention: notice.severity !== "INFO",
    });
  }
  events.sort((a, b) => b.at.localeCompare(a.at));

  return {
    events,
    isLoading:
      reports.isLoading ||
      sources.isLoading ||
      specialists.isLoading ||
      decisions.isLoading,
    error:
      reports.error ?? sources.error ?? specialists.error ?? decisions.error,
  };
}

const SEEN_KEY = "ton:activity:seen";

export function readSeenAt(userId: string | undefined): string | null {
  if (!userId) return null;
  try {
    return localStorage.getItem(`${SEEN_KEY}:${userId}`);
  } catch {
    return null;
  }
}

export function writeSeenAt(userId: string | undefined, at: string) {
  if (!userId) return;
  try {
    localStorage.setItem(`${SEEN_KEY}:${userId}`, at);
  } catch {
    // Per-viewer convenience only; the feed works without it.
  }
}
