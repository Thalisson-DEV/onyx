"use client";

import type { Route } from "next";
import {
  useTonDataSources,
  useTonReportGroups,
  useTonSpecialists,
} from "@/lib/ton/api";
import { COPY, formatPeriod, plural } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";

export type ActivityKind = "report" | "import" | "importFailed" | "specialists";

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
 * publications, source imports and specialist executions. Nothing here is
 * inferred or simulated; an event exists because a record exists.
 */
export function useTonActivity() {
  const reports = useTonReportGroups();
  const sources = useTonDataSources();
  const specialists = useTonSpecialists();

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
  events.sort((a, b) => b.at.localeCompare(a.at));

  return {
    events,
    isLoading: reports.isLoading || sources.isLoading || specialists.isLoading,
    error: reports.error ?? sources.error ?? specialists.error,
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
