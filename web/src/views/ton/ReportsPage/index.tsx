"use client";

import { useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import useSWR from "swr";
import { Button, Text } from "@opal/components";
import {
  SvgArrowRight,
  SvgChevronDown,
  SvgDownload,
  SvgFileText,
} from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useTonReportGroups } from "@/lib/ton/api";
import { COPY, formatPeriod, formatRelativeDateTime } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { Publication, ReportGroup } from "@/lib/ton/types";
import {
  IconTile,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusPill,
  TonCard,
} from "@/views/ton/components/ui";

export function reportTitle(publication: Publication): string {
  return getBusinessLabel(publication.report_type ?? "MONTHLY_CLOSE");
}

function origin(publication: Publication): string {
  return publication.routine_code
    ? COPY.reports.byRoutine(publication.routine_code)
    : COPY.reports.byAssistant;
}

function History({ revisionId }: { revisionId: string }) {
  const history = useSWR<Publication[]>(
    `/api/ton/agent/reports/${encodeURIComponent(revisionId)}/history?limit=25`,
    errorHandlingFetcher
  );
  if (history.isLoading) return <LoadingBlock label={COPY.common.loading} />;
  const previous = (history.data ?? []).filter(
    (item) => item.revision_id !== revisionId
  );
  return (
    <ul className="flex flex-col divide-y divide-border-01 rounded-12 border border-01">
      {previous.map((item) => (
        <li key={item.revision_id}>
          <Link
            href={item.report_url as Route}
            className="ton-row-link ton-focusable flex flex-wrap items-center gap-3 px-3 py-2.5"
          >
            <span className="flex-1 min-w-0">
              <Text font="secondary-action" color="text-05">
                {formatRelativeDateTime(item.output.generated_at)}
              </Text>
            </span>
            <Text font="secondary-body" color="text-03">
              {origin(item)}
            </Text>
            <StatusPill tone="neutral">
              {getBusinessLabel(item.status)}
            </StatusPill>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function ReportCard({ group }: { group: ReportGroup }) {
  const [open, setOpen] = useState(false);
  const { latest, previous_count } = group;
  return (
    <TonCard as="article" className="flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-start gap-4">
        <IconTile icon={SvgFileText} tone="gold" size="lg" />
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Text as="h2" font="heading-h3" color="text-05">
              {reportTitle(latest)}
            </Text>
            <StatusPill tone="brand">{COPY.reports.current}</StatusPill>
          </div>
          <Text font="main-ui-body" color="text-04">
            {`${formatPeriod(latest.output.period)} · ${latest.output.scope}`}
          </Text>
          <Text font="secondary-body" color="text-03">
            {`${COPY.reports.generatedAt(formatRelativeDateTime(latest.output.generated_at))} · ${origin(latest)}`}
          </Text>
        </div>
        <StatusPill tone="warning">
          {getBusinessLabel(latest.status)}
        </StatusPill>
      </div>
      <Text as="p" font="main-ui-body" color="text-04">
        {latest.output.executive_brief.RESULTADO ?? latest.output.data_context}
      </Text>
      <div className="flex flex-wrap items-center gap-2">
        <Button href={latest.report_url} rightIcon={SvgArrowRight}>
          {COPY.reports.open}
        </Button>
        <Button
          href={latest.download_url}
          prominence="secondary"
          icon={SvgDownload}
        >
          {COPY.reports.download}
        </Button>
        {previous_count > 0 && (
          <Button
            prominence="tertiary"
            rightIcon={SvgChevronDown}
            onClick={() => setOpen((value) => !value)}
          >
            {open
              ? COPY.reports.hideVersions
              : `${COPY.reports.previousVersions} (${previous_count})`}
          </Button>
        )}
      </div>
      {open && <History revisionId={latest.revision_id} />}
    </TonCard>
  );
}

export default function ReportsPage() {
  const reports = useTonReportGroups();
  return (
    <PageContainer>
      <PageHeader
        title={COPY.reports.title}
        description={COPY.reports.description}
      />
      {reports.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} />
        </TonCard>
      )}
      {reports.error && (
        <TonCard className="p-5">
          <Text font="main-ui-body" color="text-03">
            {COPY.common.error}
          </Text>
        </TonCard>
      )}
      {reports.data?.length === 0 && (
        <TonCard className="p-5">
          <Text font="main-ui-body" color="text-03">
            {COPY.reports.empty}
          </Text>
        </TonCard>
      )}
      <div className="flex flex-col gap-4">
        {reports.data?.map((group) => (
          <ReportCard key={group.latest.revision_id} group={group} />
        ))}
      </div>
    </PageContainer>
  );
}
