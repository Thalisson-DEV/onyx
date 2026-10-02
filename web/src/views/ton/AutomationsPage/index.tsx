"use client";

import Link from "next/link";
import type { Route } from "next";
import useSWR from "swr";
import { Text } from "@opal/components";
import { SvgCalendar, SvgFileText, SvgLock, SvgShield } from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import {
  TON_REPORTS_RECENT,
  useTonAccess,
  useTonRoutines,
} from "@/lib/ton/api";
import { COPY, formatPeriod, formatRelativeDateTime } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { Publication, Routine } from "@/lib/ton/types";
import R3Spotlight from "@/views/ton/components/R3Spotlight";
import {
  CardHeader,
  ErrorState,
  IconTile,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusPill,
  TonCard,
  routineTone,
} from "@/views/ton/components/ui";

function dependency(routine: Routine): string {
  return routine.reason
    .replace(/^Capacidade pendente:\s*/i, "")
    .replace(/\.$/, "");
}

const dayLabel = new Intl.DateTimeFormat("pt-BR", {
  weekday: "short",
  day: "2-digit",
  month: "2-digit",
  timeZone: "America/Sao_Paulo",
});
const dayKeyFormat = new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/Sao_Paulo",
});
const timeLabel = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});

function dayTitle(at: string): string {
  const key = dayKeyFormat.format(new Date(at));
  if (key === dayKeyFormat.format(new Date())) return COPY.automations.today;
  if (key === dayKeyFormat.format(new Date(Date.now() - 86_400_000)))
    return COPY.automations.yesterday;
  return dayLabel.format(new Date(at));
}

/** Persisted R3 publications, newest first, grouped by Brasília day. */
function R3History() {
  const { canReadReports } = useTonAccess();
  const reports = useSWR<Publication[]>(
    canReadReports ? TON_REPORTS_RECENT : null,
    errorHandlingFetcher
  );
  const runs = (reports.data ?? [])
    .filter((item) => item.routine_code === "R3")
    .sort((a, b) => b.output.generated_at.localeCompare(a.output.generated_at))
    .slice(0, 12);
  const days = new Map<string, Publication[]>();
  for (const run of runs) {
    const key = dayKeyFormat.format(new Date(run.output.generated_at));
    days.set(key, [...(days.get(key) ?? []), run]);
  }
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-r3-history">
      <CardHeader
        id="ton-r3-history"
        title={COPY.automations.history}
        description={
          runs.length ? COPY.automations.historyCount(runs.length) : undefined
        }
        action={{ href: "/ton/relatorios", label: COPY.automations.historyAll }}
      />
      {reports.isLoading && <LoadingBlock label={COPY.common.loading} />}
      {reports.error && <ErrorState compact onRetry={() => reports.mutate()} />}
      {!reports.isLoading && !reports.error && runs.length === 0 && (
        <Text font="main-ui-body" color="text-03">
          {COPY.automations.historyEmpty}
        </Text>
      )}
      <ol className="flex flex-col gap-3">
        {[...days.values()].map((dayRuns) => (
          <li key={dayRuns[0]?.revision_id} className="flex flex-col gap-1">
            <span className="ton-eyebrow">
              {dayTitle(dayRuns[0]?.output.generated_at ?? "")}
            </span>
            <ul className="flex flex-col border-s-2 border-01 ms-1">
              {dayRuns.map((run) => (
                <li key={run.revision_id}>
                  <Link
                    href={run.report_url as Route}
                    className="ton-row-link ton-focusable flex items-center gap-3 ps-3 pe-2 py-2"
                  >
                    <span className="tabular-nums w-12 shrink-0">
                      <Text font="secondary-action" color="text-05">
                        {timeLabel.format(new Date(run.output.generated_at))}
                      </Text>
                    </span>
                    <span className="flex-1 min-w-0">
                      <Text font="secondary-body" color="text-03" maxLines={1}>
                        {`${formatPeriod(run.output.period)} · ${run.output.scope}`}
                      </Text>
                    </span>
                    <StatusPill tone="warning">
                      {getBusinessLabel(run.status)}
                    </StatusPill>
                  </Link>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </TonCard>
  );
}

function WaitingRoutines({ routines }: { routines: Routine[] }) {
  return (
    <TonCard as="div" className="overflow-hidden">
      <ul className="flex flex-col divide-y divide-border-01">
        {routines.map((routine) => (
          <li
            key={routine.key}
            className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3"
          >
            <span className="ton-eyebrow w-10 shrink-0">{routine.key}</span>
            <span className="flex flex-col min-w-0 flex-1 basis-56">
              <Text as="h3" font="main-ui-action" color="text-05">
                {routine.name}
              </Text>
              <Text font="secondary-body" color="text-03">
                {`${COPY.automations.dependsOn}: ${dependency(routine)}`}
              </Text>
            </span>
            <StatusPill tone={routineTone(routine.status)}>
              {routine.status}
            </StatusPill>
          </li>
        ))}
      </ul>
    </TonCard>
  );
}

function RoutineCard({ routine }: { routine: Routine }) {
  const waiting = routineTone(routine.status) === "neutral";
  return (
    <TonCard as="article" className="flex flex-col gap-3 p-4">
      <div className="flex items-start gap-3">
        <IconTile
          icon={waiting ? SvgLock : SvgCalendar}
          tone={waiting ? "neutral" : "brand"}
        />
        <div className="flex flex-col gap-0.5 min-w-0 flex-1">
          <Text as="h3" font="main-ui-action" color="text-05">
            {routine.name}
          </Text>
          <span className="ton-eyebrow">
            {COPY.automations.code(routine.key)}
          </span>
        </div>
        <StatusPill tone={routineTone(routine.status)}>
          {routine.status}
        </StatusPill>
      </div>
      {waiting ? (
        <div className="flex flex-col gap-0.5 rounded-08 bg-background-neutral-01 px-3 py-2">
          <span className="ton-eyebrow">{COPY.automations.dependsOn}</span>
          <Text font="secondary-body" color="text-04">
            {dependency(routine)}
          </Text>
        </div>
      ) : (
        <Text font="secondary-body" color="text-03">
          {routine.schedule}
        </Text>
      )}
    </TonCard>
  );
}

export default function AutomationsPage() {
  const routines = useTonRoutines();
  const list = routines.data ?? [];
  const others = list.filter((routine) => routine.key !== "R3");
  const active = others.filter(
    (routine) => routineTone(routine.status) !== "neutral"
  );
  const waiting = others.filter(
    (routine) => routineTone(routine.status) === "neutral"
  );

  return (
    <PageContainer>
      <PageHeader
        title={COPY.automations.title}
        description={COPY.automations.description}
      />
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-5 items-start">
        <R3Spotlight showManageLink={false} />
        <R3History />
      </div>
      <div className="flex items-center gap-2 rounded-12 bg-background-neutral-02 px-4 py-3">
        <SvgShield size={16} className="shrink-0" />
        <Text font="secondary-body" color="text-04">
          {COPY.automations.guardrail}
        </Text>
      </div>
      {routines.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} />
        </TonCard>
      )}
      {routines.error && <ErrorState onRetry={() => routines.mutate()} />}
      {active.length > 0 && (
        <section className="flex flex-col gap-3">
          <Text as="h2" font="heading-h3" color="text-05">
            {COPY.automations.active}
          </Text>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {active.map((routine) => (
              <RoutineCard key={routine.key} routine={routine} />
            ))}
          </div>
        </section>
      )}
      {waiting.length > 0 && (
        <section className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <Text as="h2" font="heading-h3" color="text-05">
              {`${COPY.automations.waiting} (${waiting.length})`}
            </Text>
            <Text font="secondary-body" color="text-03">
              {COPY.automations.waitingDescription}
            </Text>
          </div>
          <WaitingRoutines routines={waiting} />
        </section>
      )}
    </PageContainer>
  );
}
