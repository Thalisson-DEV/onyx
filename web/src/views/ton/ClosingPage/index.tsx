"use client";

import Link from "next/link";
import type { Route } from "next";
import { Button, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowRight,
  SvgBubbleText,
  SvgCheckCircle,
  SvgServer,
  SvgSparkle,
} from "@opal/icons";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useTonClosing } from "@/lib/ton/api";
import { groupBlockers, totalBlockers } from "@/lib/ton/blockers";
import { COPY, formatPeriod, formatRelativeDateTime } from "@/lib/ton/copy";
import type { ClosingOutput } from "@/lib/ton/types";
import ClosingFrame from "@/views/ton/components/ClosingFrame";
import R3Spotlight from "@/views/ton/components/R3Spotlight";
import { pendingHref } from "@/views/ton/HomePage";
import {
  CardHeader,
  IconTile,
  LoadingBlock,
  StatusDot,
  StatusPill,
  TonCard,
  sourceTone,
  specialistTone,
} from "@/views/ton/components/ui";

const SUMMARY_ORDER = ["RESULTADO", "IMPACTO", "CAUSA / HIPÓTESE", "AÇÃO"];

function askHref(): Route {
  const query = new URLSearchParams({
    firstMessage: COPY.closing.askPrompt,
    [SEARCH_PARAM_NAMES.SUBMIT_ON_LOAD]: "true",
  });
  return `/ton/chat?${query.toString()}` as Route;
}

function StatusHero({ closing }: { closing: ClosingOutput }) {
  const total = totalBlockers(closing.blockers);
  const groups = groupBlockers(closing.blockers);
  const period = formatPeriod(closing.period).toLowerCase();
  const blocked = total > 0;
  return (
    <TonCard className="flex flex-col gap-5 p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <IconTile
          icon={blocked ? SvgAlertTriangle : SvgCheckCircle}
          tone={blocked ? "warning" : "brand"}
          size="lg"
        />
        <div className="flex flex-col gap-1.5 min-w-0">
          <Text as="h2" font="heading-h2" color="text-05">
            {blocked
              ? COPY.closing.blockedTitle(period)
              : COPY.closing.readyTitle(period)}
          </Text>
          {blocked && (
            <span className="ton-gold-text">
              <Text font="main-ui-action" color="inherit">
                {COPY.closing.attentionCount(total)}
              </Text>
            </span>
          )}
          <Text as="p" font="main-ui-body" color="text-03">
            {blocked ? COPY.closing.blockedBody : COPY.closing.readyBody}
          </Text>
        </div>
      </div>
      {blocked && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {groups.map((group) => (
            <Link
              key={group.category}
              href={pendingHref(closing, group.category)}
              className="ton-focusable ton-card-interactive flex flex-col gap-1 rounded-12 border border-01 bg-background-neutral-01 p-4"
            >
              <span className="ton-eyebrow">
                {COPY.blockers.categories[group.category].short}
              </span>
              <span className="ton-metric">
                <Text font="heading-h2" color="inherit">
                  {String(group.count)}
                </Text>
              </span>
              <Text font="secondary-body" color="text-03" maxLines={2}>
                {COPY.blockers.categories[group.category].description}
              </Text>
            </Link>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {blocked ? (
          <Button href={pendingHref(closing)} rightIcon={SvgArrowRight}>
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

function TonReading({ closing }: { closing: ClosingOutput }) {
  const entries = SUMMARY_ORDER.flatMap((key) => {
    const value = closing.executive_brief[key];
    return value ? [[key, value] as const] : [];
  });
  return (
    <TonCard className="flex flex-col gap-4 p-5" labelledBy="ton-reading">
      <CardHeader
        id="ton-reading"
        icon={SvgSparkle}
        title={COPY.closing.summaryTitle}
      />
      <dl className="flex flex-col gap-3">
        {entries.map(([key, value]) => (
          <div
            key={key}
            className="grid grid-cols-1 sm:grid-cols-[120px_1fr] gap-1 sm:gap-4"
          >
            <dt className="ton-eyebrow pt-0.5">
              {COPY.closing.summary[key] ?? key}
            </dt>
            <dd>
              <Text font="main-ui-body" color="text-04">
                {value}
              </Text>
            </dd>
          </div>
        ))}
      </dl>
      <div className="border-t border-01 pt-3 flex flex-col gap-2">
        <span className="ton-eyebrow">{COPY.closing.findingsTitle}</span>
        <Text font="secondary-body" color="text-03">
          {closing.findings_scope}
        </Text>
        {closing.findings.length === 0 ? (
          <Text font="secondary-body" color="text-03">
            {COPY.closing.noFindings}
          </Text>
        ) : (
          closing.findings.slice(0, 5).map((finding) => (
            <div key={finding.id} className="flex items-center gap-2">
              <StatusDot tone={finding.blocking ? "warning" : "neutral"} />
              <Text font="secondary-body" color="text-04">
                {finding.title}
              </Text>
            </div>
          ))
        )}
      </div>
    </TonCard>
  );
}

function Specialists({ closing }: { closing: ClosingOutput }) {
  const involved = closing.specialists.filter(
    (item) => specialistTone(item.status) !== "neutral"
  );
  const waiting = closing.specialists.length - involved.length;
  return (
    <TonCard className="flex flex-col gap-3 p-5" labelledBy="ton-specialists">
      <CardHeader
        id="ton-specialists"
        title={COPY.closing.specialistsTitle}
        action={{ href: "/ton/especialistas", label: COPY.common.seeAll }}
      />
      <ul className="flex flex-col gap-3">
        {involved.map((item) => (
          <li key={item.key} className="flex items-start gap-3">
            <IconTile icon={SvgSparkle} size="sm" />
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Text font="main-ui-action" color="text-05">
                  {item.name}
                </Text>
                <StatusPill tone={specialistTone(item.status)}>
                  {item.status}
                </StatusPill>
              </div>
              <Text font="secondary-body" color="text-03">
                {item.reason}
              </Text>
            </div>
          </li>
        ))}
      </ul>
      {waiting > 0 && (
        <Text font="secondary-body" color="text-03">
          {`+ ${waiting} especialistas aguardando fontes`}
        </Text>
      )}
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
      <ul className="flex flex-col gap-3">
        {closing.sources.map((source) => (
          <li key={source.key} className="flex items-start gap-3">
            <IconTile icon={SvgServer} size="sm" tone="neutral" />
            <div className="flex flex-col gap-0.5 min-w-0">
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
              <Text font="secondary-body" color="text-03">
                {COPY.closing.directIntegration(source.direct_integration)}
              </Text>
            </div>
            <span className="ms-auto pt-1">
              <StatusDot
                tone={
                  source.status.toLowerCase().includes("concluída")
                    ? "success"
                    : sourceTone(source.status)
                }
              />
            </span>
          </li>
        ))}
      </ul>
    </TonCard>
  );
}

export default function ClosingPage() {
  const closing = useTonClosing();
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
          <StatusHero closing={closing.data} />
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] gap-5 items-start">
            <div className="flex flex-col gap-5">
              <TonReading closing={closing.data} />
              <R3Spotlight />
            </div>
            <div className="flex flex-col gap-5">
              <Specialists closing={closing.data} />
              <Sources closing={closing.data} />
            </div>
          </div>
        </>
      )}
    </ClosingFrame>
  );
}
