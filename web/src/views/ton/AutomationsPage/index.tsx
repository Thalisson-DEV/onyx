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

function R3History() {
  const { canReadReports } = useTonAccess();
  const reports = useSWR<Publication[]>(
    canReadReports ? TON_REPORTS_RECENT : null,
    errorHandlingFetcher
  );
  const runs = (reports.data ?? [])
    .filter((item) => item.routine_code === "R3")
    .slice(0, 5);
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-r3-history">
      <CardHeader
        id="ton-r3-history"
        title={COPY.automations.history}
        action={{ href: "/ton/relatorios", label: COPY.automations.historyAll }}
      />
      {reports.isLoading && <LoadingBlock label={COPY.common.loading} />}
      {!reports.isLoading && runs.length === 0 && (
        <Text font="main-ui-body" color="text-03">
          {COPY.automations.historyEmpty}
        </Text>
      )}
      <ul className="flex flex-col divide-y divide-border-01">
        {runs.map((run) => (
          <li key={run.revision_id}>
            <Link
              href={run.report_url as Route}
              className="ton-row-link ton-focusable flex items-center gap-3 px-2 py-2.5 -mx-2"
            >
              <IconTile icon={SvgFileText} size="sm" tone="neutral" />
              <div className="flex flex-col min-w-0 flex-1">
                <Text font="main-ui-action" color="text-05">
                  {formatRelativeDateTime(run.output.generated_at)}
                </Text>
                <Text font="secondary-body" color="text-03">
                  {`${formatPeriod(run.output.period)} · ${run.output.scope}`}
                </Text>
              </div>
              <StatusPill tone="warning">
                {getBusinessLabel(run.status)}
              </StatusPill>
            </Link>
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
      {routines.error && (
        <TonCard className="p-5">
          <Text font="main-ui-body" color="text-03">
            {COPY.common.error}
          </Text>
        </TonCard>
      )}
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
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {waiting.map((routine) => (
              <RoutineCard key={routine.key} routine={routine} />
            ))}
          </div>
        </section>
      )}
    </PageContainer>
  );
}
