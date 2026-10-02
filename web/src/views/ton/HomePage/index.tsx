"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import { Button, InputTypeIn, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowUp,
  SvgCalendar,
  SvgCheckCircle,
  SvgChevronRight,
  SvgClipboard,
  SvgFileText,
  SvgServer,
  SvgShield,
  SvgSparkle,
  SvgUploadCloud,
  SvgUsers,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { useUser } from "@/providers/UserProvider";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import {
  useTonClosing,
  useTonDataSources,
  useTonReportGroups,
  useTonRoutines,
  useTonSpecialists,
} from "@/lib/ton/api";
import { groupBlockers, totalBlockers } from "@/lib/ton/blockers";
import {
  COPY,
  formatPeriod,
  formatRelativeDateTime,
  formatShortDateTime,
  formatNumber,
  plural,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import { useTonActivity, type ActivityKind } from "@/lib/ton/activity";
import type { ClosingOutput } from "@/lib/ton/types";
import R3Spotlight from "@/views/ton/components/R3Spotlight";
import {
  CardHeader,
  ErrorState,
  IconTile,
  LoadingBlock,
  StatusDot,
  StatusPill,
  TonCard,
  routineTone,
  sourceTone,
  specialistTone,
  type TonTone,
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

function AskTon() {
  const router = useRouter();
  const [question, setQuestion] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    const message = question.trim();
    if (!message) return;
    const query = new URLSearchParams({
      firstMessage: message,
      [SEARCH_PARAM_NAMES.SUBMIT_ON_LOAD]: "true",
    });
    router.push(`/ton/chat?${query.toString()}` as Route);
  }

  return (
    <form onSubmit={submit} className="flex flex-col sm:flex-row gap-2 w-full">
      <div className="w-full sm:flex-1 min-w-0">
        <InputTypeIn
          aria-label={COPY.home.ask}
          placeholder={COPY.home.askPlaceholder}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
      </div>
      <Button type="submit" icon={SvgArrowUp} disabled={!question.trim()}>
        {COPY.home.ask}
      </Button>
    </form>
  );
}

function Hero({ closing }: { closing: ClosingOutput | undefined }) {
  const { user } = useUser();
  const name = firstName(user?.personalization?.name);
  return (
    <TonCard className="ton-hero-art flex flex-col gap-5 p-5 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          <h1 className="ton-title">
            <Text font="heading-h1" color="inherit">
              {name ? COPY.home.greeting(name) : COPY.home.greetingFallback}
            </Text>
          </h1>
          <Text as="p" font="main-content-body" color="text-03">
            {COPY.home.subtitle}
          </Text>
        </div>
        {closing && (
          <span
            className="ton-pill flex items-center gap-1.5"
            data-tone="brand"
          >
            <SvgCalendar size={12} />
            {`${formatPeriod(closing.period)} · ${closing.scope}`}
          </span>
        )}
      </div>
      <AskTon />
    </TonCard>
  );
}

interface StatTileProps {
  href: Route;
  icon: IconFunctionComponent;
  label: string;
  value: string;
  detail: string;
  tone: TonTone;
}

function StatTile({ href, icon, label, value, detail, tone }: StatTileProps) {
  return (
    <Link
      href={href}
      className="ton-card ton-card-interactive ton-focusable flex flex-col gap-3 p-4 min-w-0"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="ton-eyebrow">{label}</span>
        <IconTile
          icon={icon}
          size="sm"
          tone={tone === "warning" ? "warning" : "brand"}
        />
      </div>
      <div className="flex flex-col gap-1 min-w-0">
        <span className="ton-metric">
          <Text font="heading-h2" color="inherit" maxLines={2}>
            {value}
          </Text>
        </span>
        <span className="flex items-center gap-1.5 min-w-0">
          <StatusDot tone={tone} />
          <Text font="secondary-body" color="text-03" maxLines={2}>
            {detail}
          </Text>
        </span>
      </div>
    </Link>
  );
}

function ExecutiveStrip({ closing }: { closing: ClosingOutput }) {
  const sources = useTonDataSources();
  const routines = useTonRoutines();
  const total = totalBlockers(closing.blockers);
  const groups = groupBlockers(closing.blockers);
  const current =
    sources.data?.filter((source) => source.status === "CURRENT").length ?? 0;
  const configured =
    sources.data?.filter((source) => source.source_id).length ?? 0;
  const next = routines.data
    ?.filter((routine) => routine.next_run)
    .sort((a, b) => (a.next_run ?? "").localeCompare(b.next_run ?? ""))[0];
  const dreBlocked = total > 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <StatTile
        href="/ton/fechamento"
        icon={SvgClipboard}
        label={COPY.home.strip.dre}
        value={
          dreBlocked
            ? COPY.home.strip.dreBlocked
            : getBusinessLabel(closing.dre_status)
        }
        detail={
          dreBlocked
            ? COPY.home.strip.dreDetail(total)
            : getBusinessLabel(closing.dre_status)
        }
        tone={dreBlocked ? "warning" : "success"}
      />
      <StatTile
        href={pendingHref(closing)}
        icon={SvgShield}
        label={COPY.home.strip.pending}
        value={formatNumber(total)}
        detail={COPY.home.strip.pendingDetail(groups.length)}
        tone={total > 0 ? "warning" : "success"}
      />
      <StatTile
        href="/ton/fontes"
        icon={SvgServer}
        label={COPY.home.strip.sources}
        value={
          sources.data
            ? `${formatNumber(current)}/${formatNumber(configured)}`
            : "—"
        }
        detail={COPY.home.strip.sourcesDetail(current)}
        tone={current === configured && configured > 0 ? "success" : "warning"}
      />
      <StatTile
        href="/ton/automacoes"
        icon={SvgCalendar}
        label={COPY.home.strip.nextAutomation}
        value={next?.next_run ? formatShortDateTime(next.next_run) : "—"}
        detail={next ? next.name : COPY.home.strip.nextAutomationNone}
        tone={next ? "brand" : "neutral"}
      />
    </div>
  );
}

function AttentionQueue({ closing }: { closing: ClosingOutput }) {
  const groups = groupBlockers(closing.blockers).sort(
    (a, b) => b.count - a.count
  );
  return (
    <TonCard className="flex flex-col gap-4 p-5" labelledBy="ton-attention">
      <CardHeader
        id="ton-attention"
        title={COPY.home.attention.title}
        description={COPY.home.attention.subtitle(
          formatPeriod(closing.period).toLowerCase()
        )}
        action={{
          href: pendingHref(closing),
          label: COPY.home.attention.openAll,
        }}
      />
      {groups.length === 0 ? (
        <div className="flex items-center gap-2 py-2">
          <SvgCheckCircle size={16} className="ton-brand-text" />
          <Text font="main-ui-body" color="text-04">
            {COPY.home.attention.empty}
          </Text>
        </div>
      ) : (
        <ul className="flex flex-col divide-y divide-border-01">
          {groups.map((group) => {
            const category = COPY.blockers.categories[group.category];
            return (
              <li key={group.category}>
                <Link
                  href={pendingHref(closing, group.category)}
                  className="ton-row-link ton-focusable flex items-center gap-3 px-2 py-3 -mx-2"
                >
                  <IconTile icon={SvgAlertTriangle} tone="warning" />
                  <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Text font="main-ui-action" color="text-05">
                        {group.labels.length === 1
                          ? (group.labels[0] ?? category.title)
                          : category.title}
                      </Text>
                      <StatusPill tone="warning">
                        {COPY.blockers.records(group.count)}
                      </StatusPill>
                    </div>
                    <Text font="secondary-body" color="text-03">
                      {category.description}
                    </Text>
                    <span className="ton-eyebrow">{COPY.blockers.origin}</span>
                  </div>
                  <span className="ton-brand-text hidden sm:block">
                    <Text font="secondary-action" color="inherit">
                      {COPY.blockers.resolve}
                    </Text>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </TonCard>
  );
}

const ACTIVITY_ICONS: Record<ActivityKind, IconFunctionComponent> = {
  report: SvgFileText,
  import: SvgUploadCloud,
  importFailed: SvgAlertTriangle,
  specialists: SvgUsers,
};

function ActivityFeed() {
  const { events, isLoading, error } = useTonActivity();
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
        {events.slice(0, 6).map((event, index, list) => (
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
                {`${event.detail} · ${formatRelativeDateTime(event.at)}`}
              </Text>
            </div>
          </li>
        ))}
      </ol>
    </TonCard>
  );
}

function SourceHealth({ closing }: { closing: ClosingOutput | undefined }) {
  const sources = useTonDataSources();
  const configured = sources.data?.filter((source) => source.source_id) ?? [];
  const direct = closing?.sources.find(
    (source) => source.key === "financial_launches"
  );
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-source-health">
      <CardHeader
        id="ton-source-health"
        title={COPY.home.sourceHealth.title}
        action={{ href: "/ton/fontes", label: COPY.home.rail.allSources }}
      />
      {sources.isLoading && <LoadingBlock label={COPY.common.loading} />}
      {sources.error && <ErrorState compact onRetry={() => sources.mutate()} />}
      <ul className="flex flex-col divide-y divide-border-01">
        {configured.map((source) => (
          <li key={source.key} className="flex items-center gap-3 py-2">
            <StatusDot tone={sourceTone(source.status)} />
            <span className="flex-1 min-w-0">
              <Text font="secondary-action" color="text-05" maxLines={1}>
                {source.name}
              </Text>
            </span>
            <Text font="secondary-body" color="text-03">
              {source.last_success_at
                ? formatRelativeDateTime(source.last_success_at)
                : getBusinessLabel(source.status)}
            </Text>
          </li>
        ))}
        {direct && (
          <li className="flex items-center gap-3 py-2">
            <StatusDot tone="neutral" />
            <span className="flex-1 min-w-0">
              <Text font="secondary-action" color="text-05" maxLines={1}>
                {`${COPY.home.rail.directIntegration} NG/Keevo`}
              </Text>
            </span>
            <Text font="secondary-body" color="text-03">
              {direct.direct_integration}
            </Text>
          </li>
        )}
      </ul>
    </TonCard>
  );
}

/** Only the specialists the latest closing analysis actually involved. */
function InvolvedSpecialists({
  closing,
}: {
  closing: ClosingOutput | undefined;
}) {
  const involved = (closing?.specialists ?? []).filter(
    (item) => specialistTone(item.status) !== "neutral"
  );
  const waiting = (closing?.specialists ?? []).length - involved.length;
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-involved">
      <CardHeader
        id="ton-involved"
        title={COPY.home.involved.title}
        action={{
          href: "/ton/especialistas",
          label: COPY.home.rail.allSpecialists,
        }}
      />
      {!closing && <LoadingBlock label={COPY.common.loading} />}
      <ul className="flex flex-col divide-y divide-border-01">
        {involved.map((item) => (
          <li key={item.key} className="flex items-start gap-3 py-2">
            <IconTile icon={SvgSparkle} size="sm" />
            <span className="flex flex-col min-w-0 flex-1">
              <Text font="secondary-action" color="text-05">
                {item.name}
              </Text>
              <Text font="secondary-body" color="text-03" maxLines={2}>
                {item.reason}
              </Text>
            </span>
            <StatusPill tone={specialistTone(item.status)}>
              {item.status}
            </StatusPill>
          </li>
        ))}
      </ul>
      {waiting > 0 && (
        <Text as="p" font="secondary-body" color="text-03">
          {COPY.home.involved.waiting(waiting)}
        </Text>
      )}
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
            className="ton-row-link ton-focusable flex items-center gap-3 border border-01 rounded-12 p-3"
          >
            <IconTile icon={SvgFileText} />
            <div className="flex flex-col gap-1 min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Text font="main-ui-action" color="text-05">
                  {getBusinessLabel(latest.report_type ?? "MONTHLY_CLOSE")}
                </Text>
                <StatusPill tone="warning">
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

function RailSection({
  title,
  action,
  children,
}: {
  title: string;
  action: { href: Route; label: string };
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-2">
      <span className="ton-eyebrow px-1">{title}</span>
      <div className="ton-card flex flex-col p-2">
        {children}
        <div className="border-t border-01 mt-1 pt-1">
          <Link
            href={action.href}
            className="ton-row-link ton-focusable ton-brand-text flex items-center justify-between px-2 py-2"
          >
            <Text font="secondary-action" color="inherit">
              {action.label}
            </Text>
            <SvgChevronRight size={14} />
          </Link>
        </div>
      </div>
    </section>
  );
}

function RailRow({
  icon,
  title,
  detail,
  status,
  tone,
}: {
  icon: IconFunctionComponent;
  title: string;
  detail?: string;
  status?: string;
  tone: TonTone;
}) {
  return (
    <div className="flex items-center gap-3 px-2 py-2 min-w-0">
      <IconTile
        icon={icon}
        size="sm"
        tone={tone === "neutral" ? "neutral" : "brand"}
      />
      <div className="flex flex-col min-w-0 flex-1">
        <Text font="secondary-action" color="text-05" maxLines={1}>
          {title}
        </Text>
        {detail && (
          <Text font="secondary-body" color="text-03" maxLines={2}>
            {detail}
          </Text>
        )}
      </div>
      {status ? (
        <StatusPill tone={tone}>{status}</StatusPill>
      ) : (
        <StatusDot tone={tone} />
      )}
    </div>
  );
}

export function HomeRail() {
  const sources = useTonDataSources();
  const closing = useTonClosing();
  const routines = useTonRoutines();
  const specialists = useTonSpecialists();
  const direct = closing.data?.sources.find(
    (source) => source.key === "financial_launches"
  );
  const routineList = routines.data ?? [];
  const r3 = routineList.find((routine) => routine.key === "R3");
  const waiting = routineList.filter((routine) => routine.key !== "R3");
  const active = (specialists.data ?? []).filter(
    (item) => specialistTone(item.status) !== "neutral"
  );
  const awaiting = (specialists.data ?? []).filter(
    (item) => specialistTone(item.status) === "neutral"
  );

  return (
    <div className="flex flex-col gap-5">
      <RailSection
        title={COPY.home.rail.sources}
        action={{ href: "/ton/fontes", label: COPY.home.rail.allSources }}
      >
        {sources.isLoading && <LoadingBlock label={COPY.common.loading} />}
        {sources.data
          ?.filter((source) => source.source_id)
          .map((source) => (
            <RailRow
              key={source.key}
              icon={SvgServer}
              title={source.name}
              detail={
                source.last_success_at
                  ? `${COPY.home.rail.manualImport} · ${formatRelativeDateTime(source.last_success_at)}`
                  : getBusinessLabel(source.status)
              }
              tone={sourceTone(source.status)}
            />
          ))}
        {direct && (
          <RailRow
            icon={SvgShield}
            title={`${COPY.home.rail.directIntegration} NG/Keevo`}
            detail={direct.direct_integration}
            tone="neutral"
          />
        )}
      </RailSection>

      <RailSection
        title={COPY.home.rail.automations}
        action={{
          href: "/ton/automacoes",
          label: COPY.home.rail.allAutomations,
        }}
      >
        {routines.isLoading && <LoadingBlock label={COPY.common.loading} />}
        {r3 && (
          <RailRow
            icon={SvgCalendar}
            title={r3.name}
            detail={
              r3.next_run
                ? `${COPY.home.automation.nextRun}: ${formatRelativeDateTime(r3.next_run)}`
                : r3.schedule
            }
            status={r3.status}
            tone={routineTone(r3.status)}
          />
        )}
        {waiting.slice(0, 2).map((routine) => (
          <RailRow
            key={routine.key}
            icon={SvgCalendar}
            title={routine.name}
            detail={routine.reason}
            status={routine.status}
            tone={routineTone(routine.status)}
          />
        ))}
      </RailSection>

      <RailSection
        title={COPY.home.rail.specialists}
        action={{
          href: "/ton/especialistas",
          label: COPY.home.rail.allSpecialists,
        }}
      >
        {specialists.isLoading && <LoadingBlock label={COPY.common.loading} />}
        {active.map((item) => (
          <RailRow
            key={item.key}
            icon={SvgSparkle}
            title={item.name}
            detail={item.reason}
            status={item.status}
            tone={specialistTone(item.status)}
          />
        ))}
        {awaiting.length > 0 && (
          <RailRow
            icon={SvgUsers}
            title={`${plural(awaiting.length, "especialista", "especialistas")} · ${awaiting[0]?.status ?? ""}`}
            detail={awaiting
              .map((item) => item.name.replace(/^TON /, ""))
              .join(", ")}
            tone="neutral"
          />
        )}
      </RailSection>
    </div>
  );
}

export default function HomePage() {
  const closing = useTonClosing();

  return (
    <div className="flex flex-1 min-w-0">
      <div className="flex-1 min-w-0">
        <div className="w-full max-w-[1120px] mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8 flex flex-col gap-5">
          <Hero closing={closing.data} />
          {closing.isLoading && (
            <TonCard className="p-5">
              <LoadingBlock label={COPY.common.loading} />
            </TonCard>
          )}
          {closing.error && <ErrorState onRetry={() => closing.mutate()} />}
          {closing.data && (
            <>
              <ExecutiveStrip closing={closing.data} />
              <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] gap-5 items-start">
                <AttentionQueue closing={closing.data} />
                <R3Spotlight />
              </div>
            </>
          )}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
            <ActivityFeed />
            <LatestReports />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
            <SourceHealth closing={closing.data} />
            <InvolvedSpecialists closing={closing.data} />
          </div>
        </div>
      </div>
    </div>
  );
}
