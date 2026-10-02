"use client";

import type { Route } from "next";
import { Button, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowRight,
  SvgBubbleText,
  SvgCheckCircle,
  SvgFileText,
  SvgRefreshCw,
  SvgServer,
  SvgShield,
} from "@opal/icons";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useTonClosing, useTonReportGroups } from "@/lib/ton/api";
import {
  COPY,
  formatDateTime,
  formatPeriod,
  formatRelativeDateTime,
} from "@/lib/ton/copy";
import {
  type DecisionLog,
  type PeriodChange,
  appliedDecisionCount,
  blockerLabel,
  isDecisionBlocker,
  pendingQueueHref,
  sumBlockers,
  useDecisionLog,
  useReadinessChanges,
} from "@/lib/ton/decisions";
import type { ClosingOutput, Publication } from "@/lib/ton/types";
import ClosingFrame from "@/views/ton/components/ClosingFrame";
import DecisionLogList from "@/views/ton/components/DecisionLogList";
import R3Spotlight from "@/views/ton/components/R3Spotlight";
import ReadinessDelta from "@/views/ton/components/ReadinessDelta";
import {
  CardHeader,
  IconTile,
  LoadingBlock,
  StatusDot,
  StatusPill,
  TonCard,
  sourceTone,
} from "@/views/ton/components/ui";

const CONTROL = COPY.decisionLoop.control;

function askHref(): Route {
  const query = new URLSearchParams({
    firstMessage: COPY.closing.askPrompt,
    [SEARCH_PARAM_NAMES.SUBMIT_ON_LOAD]: "true",
  });
  // SAFETY: /ton/chat is a static route; only its query varies.
  return `/ton/chat?${query.toString()}` as Route;
}

interface NextAction {
  key: string;
  title: string;
  detail: string | null;
  href: Route;
  tone: "warning" | "neutral";
  icon: typeof SvgShield;
}

/** Orders what is left by who can act: apply, decide, then bring data. */
function nextActions(
  closing: ClosingOutput,
  blockers: Record<string, number>,
  pendingDecisions: number
): NextAction[] {
  const scope = {
    period: closing.period,
    normalization: null,
    unit: closing.unit_id,
  };
  const actions: NextAction[] = [];
  if (pendingDecisions > 0) {
    actions.push({
      key: "apply",
      title: CONTROL.applyTitle(pendingDecisions),
      detail: CONTROL.applyDetail,
      href: pendingQueueHref(scope),
      tone: "warning",
      icon: SvgRefreshCw,
    });
  }
  const entries = Object.entries(blockers).filter(([, count]) => count > 0);
  for (const [blocker, count] of entries
    .filter(([blocker]) => isDecisionBlocker(blocker))
    .sort((a, b) => b[1] - a[1])) {
    actions.push({
      key: blocker,
      title: CONTROL.resolve(count, blockerLabel(blocker)),
      detail: null,
      href: pendingQueueHref({ ...scope, blocker }),
      tone: "warning",
      icon: SvgShield,
    });
  }
  for (const [blocker, count] of entries.filter(
    ([blocker]) => !isDecisionBlocker(blocker)
  )) {
    actions.push({
      key: blocker,
      title:
        blocker === "NO_ACTUAL"
          ? CONTROL.importData(count)
          : CONTROL.otherData(blockerLabel(blocker)),
      detail: CONTROL.importDetail,
      href: pendingQueueHref({ ...scope, blocker }),
      tone: "neutral",
      icon: SvgServer,
    });
  }
  return actions;
}

function StatusHeader({
  closing,
  change,
}: {
  closing: ClosingOutput;
  change: PeriodChange | undefined;
}) {
  // Readiness codes from the base when available; closing labels otherwise.
  const total = change
    ? sumBlockers(change.blockers_after)
    : sumBlockers(closing.blockers);
  const period = formatPeriod(closing.period).toLowerCase();
  const blocked = change ? change.status_after !== "READY" : total > 0;
  return (
    <TonCard className="flex flex-wrap items-center gap-4 p-5">
      <IconTile
        icon={blocked ? SvgAlertTriangle : SvgCheckCircle}
        tone={blocked ? "warning" : "brand"}
        size="lg"
      />
      <div className="flex flex-col gap-1 min-w-0 flex-1">
        <Text as="h2" font="heading-h2" color="text-05">
          {blocked
            ? COPY.closing.blockedTitle(period)
            : COPY.closing.readyTitle(period)}
        </Text>
        <Text as="p" font="main-ui-body" color="text-03">
          {blocked
            ? COPY.closing.attentionCount(total)
            : COPY.closing.readyBody}
        </Text>
      </div>
      <div className="flex flex-wrap gap-2">
        {blocked ? (
          <Button
            href={pendingQueueHref({
              period: closing.period,
              unit: closing.unit_id,
            })}
            rightIcon={SvgArrowRight}
          >
            {COPY.closing.resolve}
          </Button>
        ) : (
          <Button href="/ton/dre" rightIcon={SvgArrowRight}>
            {COPY.closing.openDre}
          </Button>
        )}
        <Button href={askHref()} prominence="secondary" icon={SvgBubbleText}>
          {COPY.closing.askTon}
        </Button>
      </div>
    </TonCard>
  );
}

function NextActions({ actions }: { actions: NextAction[] }) {
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-next-actions">
      <CardHeader id="ton-next-actions" title={CONTROL.nextTitle} />
      {actions.length === 0 ? (
        <div className="flex flex-wrap items-center gap-3">
          <Text font="main-ui-body" color="text-04">
            {CONTROL.calculate}
          </Text>
          <Button href="/ton/dre" size="md" rightIcon={SvgArrowRight}>
            {CONTROL.calculateCta}
          </Button>
        </div>
      ) : (
        <ol className="flex flex-col divide-y divide-border-01">
          {actions.map((action, index) => (
            <li
              key={action.key}
              className="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
            >
              <span
                className="ton-step"
                data-state={index === 0 ? "current" : "next"}
              >
                {index + 1}
              </span>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <Text font="main-ui-action" color="text-05">
                  {action.title}
                </Text>
                {action.detail && (
                  <Text font="secondary-body" color="text-03">
                    {action.detail}
                  </Text>
                )}
              </div>
              <Button
                href={action.href}
                size="md"
                prominence={index === 0 ? "primary" : "secondary"}
                rightIcon={SvgArrowRight}
              >
                {CONTROL.open}
              </Button>
            </li>
          ))}
        </ol>
      )}
    </TonCard>
  );
}

function WhatChanged({
  change,
  since,
  applied,
}: {
  change: PeriodChange;
  since: string;
  applied: number;
}) {
  const moved = Object.keys({
    ...change.blockers_before,
    ...change.blockers_after,
  }).some(
    (code) =>
      (change.blockers_before[code] ?? 0) !== (change.blockers_after[code] ?? 0)
  );
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-what-changed">
      <CardHeader
        id="ton-what-changed"
        title={CONTROL.changesTitle}
        description={[
          COPY.decisionLoop.changes.since(formatDateTime(since)),
          applied > 0
            ? COPY.decisionLoop.changes.appliedDecisions(applied)
            : null,
        ]
          .filter(Boolean)
          .join(" · ")}
      />
      {moved ? (
        <ReadinessDelta
          before={change.blockers_before}
          after={change.blockers_after}
          statusBefore={change.status_before}
          statusAfter={change.status_after}
          changedOnly
        />
      ) : (
        <Text font="secondary-body" color="text-03">
          {COPY.decisionLoop.changes.noChange}
        </Text>
      )}
    </TonCard>
  );
}

function latestClosingReport(
  groups: { latest: Publication }[] | undefined
): Publication | null {
  const closing = (groups ?? [])
    .map((group) => group.latest)
    .filter((item) => item.report_type !== "EXECUTIVE")
    .sort((a, b) => b.output.generated_at.localeCompare(a.output.generated_at));
  return closing[0] ?? null;
}

function ReportFreshness({
  report,
  closing,
  log,
}: {
  report: Publication | null;
  closing: ClosingOutput;
  log: DecisionLog | undefined;
}) {
  if (!report) {
    return (
      <TonCard className="flex flex-col gap-2 p-5" labelledBy="ton-report">
        <CardHeader
          id="ton-report"
          icon={SvgFileText}
          title={CONTROL.reportTitle}
        />
        <Text font="secondary-body" color="text-03">
          {CONTROL.reportNone}
        </Text>
      </TonCard>
    );
  }
  const generated = report.output.generated_at;
  const later = (log?.entries ?? []).filter(
    (entry) => entry.decided_at > generated
  ).length;
  const current =
    report.output.normalization_run_id === closing.normalization_run_id &&
    later === 0;
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-report">
      <CardHeader
        id="ton-report"
        icon={SvgFileText}
        title={CONTROL.reportTitle}
        description={COPY.reports.generatedAt(
          formatRelativeDateTime(generated)
        )}
      />
      <div className="flex items-start gap-2">
        <span className="pt-1.5">
          <StatusDot tone={current ? "success" : "warning"} />
        </span>
        <Text font="secondary-body" color="text-04">
          {current ? CONTROL.reportCurrent : CONTROL.reportStale(later)}
        </Text>
      </div>
      <div>
        <Button
          href={report.report_url as Route}
          size="md"
          prominence="secondary"
          rightIcon={SvgArrowRight}
        >
          {CONTROL.reportOpen}
        </Button>
      </div>
    </TonCard>
  );
}

function Sources({ closing }: { closing: ClosingOutput }) {
  return (
    <TonCard
      className="flex flex-col gap-3 p-5"
      labelledBy="ton-closing-sources"
    >
      <CardHeader
        id="ton-closing-sources"
        title={COPY.closing.sourcesTitle}
        action={{ href: "/ton/fontes", label: COPY.common.seeAll }}
      />
      <ul className="flex flex-col gap-2.5">
        {closing.sources.map((source) => (
          <li key={source.key} className="flex items-start gap-2.5">
            <span className="pt-1.5">
              <StatusDot
                tone={
                  source.status.toLowerCase().includes("concluída")
                    ? "success"
                    : sourceTone(source.status)
                }
              />
            </span>
            <div className="flex flex-col min-w-0">
              <Text font="main-ui-action" color="text-05">
                {source.name}
              </Text>
              <Text font="secondary-body" color="text-03">
                {[
                  source.acquisition,
                  source.last_success_at
                    ? formatRelativeDateTime(source.last_success_at)
                    : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </Text>
            </div>
          </li>
        ))}
      </ul>
    </TonCard>
  );
}

export default function ClosingPage() {
  const closing = useTonClosing();
  const reports = useTonReportGroups();
  const decisions = useDecisionLog();
  const changes = useReadinessChanges(
    closing.data?.normalization_run_id,
    closing.data?.structure_version_id,
    closing.data?.unit_id
  );
  const change = changes.data?.periods.find(
    (item) => item.period === closing.data?.period
  );
  const pendingDecisions = changes.data?.pending_decisions ?? 0;
  const appliedSincePrevious = changes.data
    ? appliedDecisionCount(changes.data)
    : 0;

  return (
    <ClosingFrame
      active="overview"
      title={COPY.closing.overviewTitle}
      description={COPY.closing.overviewDescription}
    >
      {closing.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} />
        </TonCard>
      )}
      {closing.error && (
        <TonCard className="p-5">
          <Text as="p" font="main-ui-body" color="text-03">
            {COPY.common.error}
          </Text>
        </TonCard>
      )}
      {closing.data && (
        <>
          <StatusHeader closing={closing.data} change={change} />
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-5 items-start">
            <div className="flex flex-col gap-5">
              <NextActions
                actions={nextActions(
                  closing.data,
                  change?.blockers_after ?? {},
                  pendingDecisions
                )}
              />
              {change && changes.data?.previous_started_at && (
                <WhatChanged
                  change={change}
                  since={changes.data.previous_started_at}
                  applied={appliedSincePrevious}
                />
              )}
              <TonCard
                className="flex flex-col gap-3 p-5"
                labelledBy="ton-closing-decisions"
              >
                <CardHeader
                  id="ton-closing-decisions"
                  title={CONTROL.decisionsTitle}
                  action={{
                    href: pendingQueueHref({ period: closing.data.period }),
                    label: CONTROL.seeQueue,
                  }}
                />
                <DecisionLogList
                  entries={decisions.data?.entries ?? []}
                  limit={4}
                />
              </TonCard>
            </div>
            <div className="flex flex-col gap-5">
              <ReportFreshness
                report={latestClosingReport(reports.data)}
                closing={closing.data}
                log={decisions.data}
              />
              <R3Spotlight />
              <Sources closing={closing.data} />
              {closing.data.findings.length > 0 && (
                <TonCard
                  className="flex flex-col gap-2 p-5"
                  labelledBy="ton-findings"
                >
                  <CardHeader
                    id="ton-findings"
                    title={COPY.closing.findingsTitle}
                  />
                  {closing.data.findings.slice(0, 5).map((finding) => (
                    <div key={finding.id} className="flex items-center gap-2">
                      <StatusPill
                        tone={finding.blocking ? "warning" : "neutral"}
                      >
                        {finding.blocking
                          ? CONTROL.findingBlocking
                          : CONTROL.findingInfo}
                      </StatusPill>
                      <Text font="secondary-body" color="text-04">
                        {finding.title}
                      </Text>
                    </div>
                  ))}
                </TonCard>
              )}
            </div>
          </div>
        </>
      )}
    </ClosingFrame>
  );
}
