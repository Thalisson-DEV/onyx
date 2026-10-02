"use client";

import type { ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import type { Route } from "next";
import useSWR from "swr";
import { Button, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowLeft,
  SvgArrowRight,
  SvgChevronDown,
  SvgDownload,
  SvgFileText,
} from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { groupBlockers, totalBlockers } from "@/lib/ton/blockers";
import {
  COPY,
  formatDateTime,
  formatPeriod,
  formatRelativeDateTime,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { Publication } from "@/lib/ton/types";
import { useTonAccess } from "@/lib/ton/api";
import { pendingHref } from "@/views/ton/HomePage";
import { reportTitle } from "@/views/ton/ReportsPage";
import {
  LoadingBlock,
  PageContainer,
  StatusDot,
  StatusPill,
  TonCard,
  specialistTone,
} from "@/views/ton/components/ui";

const SUMMARY_ORDER = [
  "RESULTADO",
  "PROBLEMA",
  "IMPACTO",
  "CAUSA / HIPÓTESE",
  "AÇÃO",
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3 border-t border-01 pt-6">
      <Text as="h2" font="heading-h3" color="text-05">
        {title}
      </Text>
      {children}
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="ton-eyebrow">{label}</span>
      <Text font="main-ui-action" color="text-05">
        {value}
      </Text>
    </div>
  );
}

function Document({ report }: { report: Publication }) {
  const { output } = report;
  const { isAdmin } = useTonAccess();
  const blockers = groupBlockers(output.blockers);
  const total = totalBlockers(output.blockers);
  const actions = Array.from(
    new Set(output.specialists.flatMap((item) => item.actions))
  );
  return (
    <article className="ton-card flex flex-col gap-6 p-6 sm:p-10">
      <header className="flex flex-col gap-6">
        <div className="flex items-center justify-between gap-4">
          <Image
            src="/ton/vale-norte-logo.png"
            alt="Vale Norte"
            width={1057}
            height={412}
            className="h-10 w-auto"
          />
          <span className="flex items-center gap-2">
            <span className="ton-product-badge ton-brand-text border-(--vale-norte-green-80)">
              TON
            </span>
          </span>
        </div>
        <div className="flex flex-col gap-2">
          <span className="ton-eyebrow">{COPY.reports.title}</span>
          <h1 className="ton-title">
            <Text font="heading-h1" color="inherit">
              {reportTitle(report)}
            </Text>
          </h1>
          <Text font="secondary-body" color="text-03">
            {output.data_context}
          </Text>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 rounded-12 bg-background-neutral-01 p-4">
          <Meta
            label={COPY.report.period}
            value={formatPeriod(output.period)}
          />
          <Meta label={COPY.report.scope} value={output.scope} />
          <Meta
            label={COPY.report.generated}
            value={formatRelativeDateTime(output.generated_at)}
          />
          <Meta
            label={COPY.report.status}
            value={getBusinessLabel(report.status)}
          />
        </div>
      </header>

      <Section title={COPY.report.summary}>
        <dl className="flex flex-col gap-3">
          {SUMMARY_ORDER.flatMap((key) => {
            const value = output.executive_brief[key];
            return value ? [[key, value] as const] : [];
          }).map(([key, value]) => (
            <div
              key={key}
              className="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-1 sm:gap-4"
            >
              <dt className="ton-eyebrow pt-0.5">
                {COPY.closing.summary[key] ?? key}
              </dt>
              <dd>
                <Text font="main-content-body" color="text-04">
                  {value}
                </Text>
              </dd>
            </div>
          ))}
        </dl>
      </Section>

      {total > 0 && (
        <Section title={COPY.report.blockers}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {blockers.map((group) => (
              <div
                key={group.category}
                className="flex flex-col gap-1 rounded-12 border border-01 p-3"
              >
                <span className="ton-eyebrow">
                  {COPY.blockers.categories[group.category].short}
                </span>
                <span className="ton-metric">
                  <Text font="heading-h3" color="inherit">
                    {String(group.count)}
                  </Text>
                </span>
                <Text font="secondary-body" color="text-03">
                  {group.labels
                    .map((label) => getBusinessLabel(label))
                    .join(", ")}
                </Text>
              </div>
            ))}
          </div>
          <div>
            <Button
              href={pendingHref(output)}
              prominence="secondary"
              rightIcon={SvgArrowRight}
            >
              {COPY.report.resolve}
            </Button>
          </div>
        </Section>
      )}

      <Section title={COPY.report.findings}>
        {output.findings.length === 0 && (
          <Text font="main-ui-body" color="text-03">
            {COPY.report.noFindings}
          </Text>
        )}
        <ul className="flex flex-col gap-3">
          {output.findings.map((finding) => (
            <li
              key={finding.id}
              className="flex flex-col gap-1.5 rounded-12 border border-01 p-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <SvgAlertTriangle size={14} />
                <Text font="main-ui-action" color="text-05">
                  {finding.title}
                </Text>
                <StatusPill tone={finding.blocking ? "warning" : "neutral"}>
                  {getBusinessLabel(finding.status)}
                </StatusPill>
              </div>
              {finding.recommendations.map((item) => (
                <Text key={item} font="secondary-body" color="text-04">
                  {item}
                </Text>
              ))}
              {finding.evidence.map((evidence) => (
                <Text key={evidence.id} font="secondary-body" color="text-03">
                  {COPY.report.evidence(
                    evidence.sheet_name ?? COPY.common.notAvailable,
                    evidence.row_number !== undefined
                      ? String(evidence.row_number)
                      : COPY.common.notAvailable
                  )}
                </Text>
              ))}
            </li>
          ))}
        </ul>
      </Section>

      {actions.length > 0 && (
        <Section title={COPY.report.actions}>
          <ol className="flex flex-col gap-2 list-decimal ps-5">
            {actions.map((action) => (
              <li key={action}>
                <Text font="main-ui-body" color="text-04">
                  {action}
                </Text>
              </li>
            ))}
          </ol>
        </Section>
      )}

      <Section title={COPY.report.sources}>
        <ul className="flex flex-col divide-y divide-border-01">
          {output.sources.map((source) => (
            <li
              key={source.key}
              className="grid grid-cols-1 sm:grid-cols-[1.3fr_1fr_1fr] gap-1 sm:gap-4 py-2"
            >
              <Text font="main-ui-action" color="text-05">
                {source.name}
              </Text>
              <Text font="secondary-body" color="text-04">
                {source.acquisition}
              </Text>
              <Text font="secondary-body" color="text-03">
                {COPY.closing.directIntegration(source.direct_integration)}
              </Text>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={COPY.report.specialists}>
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {output.specialists.map((item) => (
            <li key={item.key} className="flex items-start gap-2">
              <span className="pt-1.5">
                <StatusDot tone={specialistTone(item.status)} />
              </span>
              <div className="flex flex-col min-w-0">
                <Text font="secondary-action" color="text-05">
                  {`${item.name} · ${item.status}`}
                </Text>
                <Text font="secondary-body" color="text-03">
                  {item.reason}
                </Text>
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <details className="group border-t border-01 pt-5">
        <summary className="flex items-center gap-1 cursor-pointer list-none w-fit">
          <Text font="main-ui-action" color="text-04">
            {COPY.report.traceability}
          </Text>
          <SvgChevronDown
            size={14}
            className="transition-transform group-open:rotate-180"
          />
        </summary>
        <div className="flex flex-col gap-2 pt-3">
          <Text font="secondary-body" color="text-03">
            {COPY.report.traceabilityHint}
          </Text>
          <ul className="flex flex-col divide-y divide-border-01">
            {report.steps.map((step, index) => (
              <li
                key={`${step.specialist}-${step.code}-${index}`}
                className="flex flex-wrap items-center gap-2 py-2"
              >
                <span className="flex-1 min-w-0">
                  <Text font="secondary-action" color="text-05">
                    {`${step.specialist} · ${step.code}`}
                  </Text>
                </span>
                <StatusPill tone="neutral">
                  {getBusinessLabel(step.status)}
                </StatusPill>
                {step.reason && (
                  <span className="basis-full">
                    <Text font="secondary-body" color="text-03">
                      {step.reason}
                    </Text>
                  </span>
                )}
              </li>
            ))}
          </ul>
          {isAdmin && (
            <Text font="secondary-mono" color="text-03">
              {`Execução ${report.run_id.slice(0, 8)} · Revisão ${report.revision_id.slice(0, 8)}`}
            </Text>
          )}
        </div>
      </details>
    </article>
  );
}

function Versions({ revisionId }: { revisionId: string }) {
  const history = useSWR<Publication[]>(
    `/api/ton/agent/reports/${encodeURIComponent(revisionId)}/history?limit=25`,
    errorHandlingFetcher
  );
  const previous = history.data ?? [];
  if (!previous.length) return null;
  return (
    <details className="ton-card group" data-print-hide>
      <summary className="ton-focusable flex items-center justify-between gap-3 px-5 py-3 cursor-pointer list-none rounded-12">
        <Text font="secondary-action" color="text-04">
          {COPY.report.previousVersions(previous.length)}
        </Text>
        <SvgChevronDown
          size={14}
          className="transition-transform group-open:rotate-180"
        />
      </summary>
      <ul className="flex flex-col divide-y divide-border-01 px-5 pb-3">
        {previous.map((item) => (
          <li key={item.revision_id}>
            <Link
              href={item.report_url as Route}
              className="ton-row-link ton-focusable flex items-center justify-between gap-3 py-2"
            >
              <Text font="secondary-body" color="text-04">
                {formatDateTime(item.output.generated_at)}
              </Text>
              <StatusPill tone="neutral">
                {getBusinessLabel(item.status)}
              </StatusPill>
            </Link>
          </li>
        ))}
      </ul>
    </details>
  );
}

export default function ReportViewer({ revisionId }: { revisionId: string }) {
  const report = useSWR<Publication>(
    `/api/ton/agent/reports/${encodeURIComponent(revisionId)}`,
    errorHandlingFetcher
  );
  return (
    <PageContainer className="max-w-[960px]">
      <div
        className="flex flex-wrap items-center justify-between gap-3"
        data-print-hide
      >
        <Link
          href="/ton/relatorios"
          className="ton-focusable ton-brand-text flex items-center gap-1 rounded-08"
        >
          <SvgArrowLeft size={14} />
          <Text font="main-ui-action" color="inherit">
            {COPY.report.back}
          </Text>
        </Link>
        {report.data && (
          <div className="flex flex-wrap gap-2">
            <Button
              prominence="secondary"
              icon={SvgFileText}
              onClick={() => window.print()}
            >
              {COPY.report.print}
            </Button>
            <Button href={report.data.download_url} icon={SvgDownload}>
              {COPY.report.download}
            </Button>
          </div>
        )}
      </div>
      {report.isLoading && (
        <TonCard className="p-6">
          <LoadingBlock label={COPY.common.loading} lines={6} />
        </TonCard>
      )}
      {report.error && (
        <TonCard className="p-6">
          <Text font="main-ui-body" color="text-03">
            {COPY.report.notFound}
          </Text>
        </TonCard>
      )}
      {report.data && <Document report={report.data} />}
      {report.data && <Versions revisionId={revisionId} />}
    </PageContainer>
  );
}
