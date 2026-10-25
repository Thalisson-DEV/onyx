"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import { Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgCheckCircle,
  SvgChevronRight,
  SvgFileText,
  SvgRefreshCw,
  SvgShield,
  SvgUploadCloud,
  SvgUsers,
  SvgWorkflow,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { useUser } from "@/providers/UserProvider";

import {
  useTonClosing,
  useTonDataSources,
  useTonReportGroups,
  useTonRoutines,
} from "@/lib/ton/api";
import { totalBlockers } from "@/lib/ton/blockers";
import {
  COPY,
  formatPeriod,
  formatRelativeDateTime,
  formatShortDateTime,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import { useTonActivity, type ActivityKind } from "@/lib/ton/activity";
import type { ClosingOutput } from "@/lib/ton/types";
import WorkQueue from "@/views/ton/components/WorkQueue";
import { PageFrame, PageHead, Tag } from "@/views/ton/components/kit";
import { useAskTonPage } from "@/views/ton/ask/AskTon";
import { useWorkQueue } from "@/lib/ton/workQueue";
import { summarizeSources } from "@/lib/ton/sources";
import {
  CardHeader,
  ErrorState,
  IconTile,
  LoadingBlock,
  StatusPill,
  TonCard,
  runTone,
} from "@/views/ton/components/ui";

function firstName(name: string | undefined): string | null {
  const value = name?.trim();
  if (!value) return null;
  return value.split(/\s+/)[0] ?? null;
}

export function pendingHref(output: ClosingOutput, category?: string): Route {
  const query = new URLSearchParams({ period: output.period });
  if (output.normalization_run_id)
    query.set("normalization", output.normalization_run_id);
  if (output.unit_id) query.set("unit", output.unit_id);
  if (category) query.set("categoria", category);
  return `/ton/pendencias?${query.toString()}` as Route;
}

const ACTIVITY_ICONS: Record<ActivityKind, IconFunctionComponent> = {
  report: SvgFileText,
  import: SvgUploadCloud,
  importFailed: SvgAlertTriangle,
  specialists: SvgUsers,
  decision: SvgShield,
  readiness: SvgRefreshCw,
  automation: SvgWorkflow,
};

function ActivityFeed() {
  const { events, isLoading, error } = useTonActivity();
  // The same action repeated in a row reads as one line with its count.
  const grouped: { event: (typeof events)[number]; count: number }[] = [];
  for (const event of events) {
    const last = grouped[grouped.length - 1];
    if (last && last.event.title === event.title) last.count += 1;
    else grouped.push({ event, count: 1 });
  }
  return (
    <TonCard className="flex flex-col gap-4 p-5" labelledBy="ton-activity">
      <CardHeader id="ton-activity" title={COPY.home.activity.title} />
      {isLoading && <LoadingBlock label={COPY.common.loading} />}
      {error && <ErrorState compact />}
      {!isLoading && !error && events.length === 0 && (
        <Text as="p" font="main-ui-body" color="text-03">
          {COPY.home.activity.empty}
        </Text>
      )}
      <ol className="flex flex-col">
        {grouped.slice(0, 6).map(({ event, count }, index, list) => (
          <li key={event.key} className="flex gap-3">
            <div className="flex flex-col items-center">
              <IconTile
                icon={ACTIVITY_ICONS[event.kind]}
                size="sm"
                tone={event.attention ? "warning" : "neutral"}
              />
              {index < list.length - 1 && (
                <span aria-hidden className="w-px flex-1 bg-border-01 my-1" />
              )}
            </div>
            <div className="flex flex-col gap-0.5 pb-4 min-w-0">
              {event.href ? (
                <Link
                  href={event.href}
                  className="ton-focusable hover:underline rounded-04"
                >
                  <Text font="main-ui-action" color="text-05">
                    {event.title}
                  </Text>
                </Link>
              ) : (
                <Text font="main-ui-action" color="text-05">
                  {event.title}
                </Text>
              )}
              <Text font="secondary-body" color="text-03" maxLines={1}>
                {count > 1
                  ? COPY.home.activity.repeated(
                      count,
                      formatRelativeDateTime(event.at)
                    )
                  : `${event.detail} · ${formatRelativeDateTime(event.at)}`}
              </Text>
            </div>
          </li>
        ))}
      </ol>
    </TonCard>
  );
}

function LatestReports() {
  const reports = useTonReportGroups();
  return (
    <TonCard className="flex flex-col gap-4 p-5" labelledBy="ton-reports">
      <CardHeader
        id="ton-reports"
        title={COPY.home.reports.title}
        action={{ href: "/ton/relatorios", label: COPY.common.seeAll }}
      />
      {reports.isLoading && <LoadingBlock label={COPY.common.loading} />}
      {reports.data?.length === 0 && (
        <Text as="p" font="main-ui-body" color="text-03">
          {COPY.home.reports.empty}
        </Text>
      )}
      <div className="flex flex-col gap-2">
        {reports.data?.slice(0, 2).map(({ latest, previous_count }) => (
          <Link
            key={latest.revision_id}
            href={latest.report_url as Route}
            className="ton-row-link ton-focusable flex items-center gap-3 border border-01 p-3"
          >
            <div className="flex flex-col gap-1 min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Text font="main-ui-action" color="text-05">
                  {getBusinessLabel(latest.report_type ?? "MONTHLY_CLOSE")}
                </Text>
                <StatusPill tone={runTone(latest.status)}>
                  {getBusinessLabel(latest.status)}
                </StatusPill>
              </div>
              <Text font="secondary-body" color="text-03">
                {`${formatPeriod(latest.output.period)} · ${latest.output.scope} · ${formatRelativeDateTime(latest.output.generated_at)}`}
              </Text>
              <Text font="secondary-body" color="text-03">
                {COPY.home.reports.previousVersions(previous_count)}
              </Text>
            </div>
            <SvgChevronRight size={16} className="shrink-0" />
          </Link>
        ))}
      </div>
    </TonCard>
  );
}

/** A unit manager has only the DRE of their units: home is that DRE. */
function ManagerRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/ton/dre" as Route);
  }, [router]);
  return null;
}

export default function HomePage() {
  const { isAdmin } = useUser();
  return isAdmin ? <AdminHome /> : <ManagerRedirect />;
}

function greetingWord(hour: number): string {
  if (hour < 12) return COPY.assistant.greetMorning;
  if (hour < 18) return COPY.assistant.greetAfternoon;
  return COPY.assistant.greetEvening;
}

/** The state of the closing, the sources and the next run in one line. */
function DayStatus({ closing }: { closing: ClosingOutput }) {
  const sources = useTonDataSources();
  const routines = useTonRoutines();
  const total = totalBlockers(closing.blockers);
  const summary = summarizeSources(sources.data ?? []);
  const next = routines.data
    ?.filter((routine) => routine.next_run)
    .sort((a, b) => (a.next_run ?? "").localeCompare(b.next_run ?? ""))[0];
  return (
    <div className="tn-statusline" data-tone={total > 0 ? "warn" : "ok"}>
      {total > 0 ? (
        <SvgAlertTriangle size={16} />
      ) : (
        <SvgCheckCircle size={16} />
      )}
      <Link href={pendingHref(closing)} className="tn-link ton-focusable">
        {total > 0 ? COPY.home.day.pending(total) : COPY.home.day.noPending}
      </Link>
      <span className="tn-statusline-meta">·</span>
      <Link href="/ton/fontes" className="tn-link ton-focusable">
        {COPY.home.day.sources(
          summary.imported.length,
          summary.required.length
        )}
      </Link>
      {next?.next_run && (
        <>
          <span className="tn-statusline-meta">·</span>
          <Link href="/ton/automacoes" className="tn-link ton-focusable">
            {COPY.home.day.nextRun(
              next.name,
              formatShortDateTime(next.next_run)
            )}
          </Link>
        </>
      )}
    </div>
  );
}

function AdminHome() {
  const closing = useTonClosing();
  const queue = useWorkQueue();
  const { user } = useUser();
  const [hour, setHour] = useState<number | null>(null);
  useEffect(() => setHour(new Date().getHours()), []);
  const name = firstName(user?.personalization?.name);
  const data = closing.data;
  const total = data ? totalBlockers(data.blockers) : 0;

  useAskTonPage(
    data
      ? {
          screen: COPY.home.title,
          chips: [COPY.nav.overview, formatPeriod(data.period), data.scope],
          details: [
            `Fechamento ${data.period} · ${data.scope} · DRE ${data.dre_status} · ${total} pendências`,
            ...queue.items.map(
              (item) =>
                `A fazer: ${item.title}${item.detail ? ` (${item.detail})` : ""}`
            ),
          ],
          opener: COPY.home.askOpener(queue.items.length),
          suggestions: COPY.home.askSuggestions,
        }
      : null
  );

  return (
    <PageFrame>
      <PageHead
        title={
          hour === null
            ? COPY.home.title
            : COPY.assistant.greeting(greetingWord(hour), name ?? "")
        }
        description={COPY.home.subtitle}
        status={
          data ? (
            <Tag tone={total > 0 ? "warn" : "ok"}>
              {`${formatPeriod(data.period)} · ${total > 0 ? COPY.home.day.notReady : COPY.home.day.ready}`}
            </Tag>
          ) : undefined
        }
      />
      {closing.isLoading && <LoadingBlock label={COPY.common.loading} />}
      {closing.error && <ErrorState onRetry={() => closing.mutate()} />}
      {data && <DayStatus closing={data} />}
      {data && (
        <WorkQueue
          id="ton-today"
          title={COPY.workQueue.title}
          description={COPY.workQueue.subtitle(
            formatPeriod(data.period).toLowerCase()
          )}
          items={queue.items}
          isLoading={queue.isLoading}
          limit={8}
          action={{
            href: pendingHref(data),
            label: COPY.home.attention.openAll,
          }}
        />
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <ActivityFeed />
        <LatestReports />
      </div>
    </PageFrame>
  );
}
