"use client";

import type { ReactNode } from "react";
import { Button, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowRight,
  SvgClipboard,
  SvgDownload,
  SvgFileText,
  SvgServer,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { getBusinessLabel, getStatusTone } from "@/lib/ton/labels";
import { COPY, formatPeriod } from "@/lib/ton/copy";
import { groupBlockers, totalBlockers } from "@/lib/ton/blockers";

interface TonToolCardProps {
  toolName: string;
  data: unknown;
}

type JsonValue = string | number | boolean | null | JsonValue[] | JsonObject;
interface JsonObject {
  [key: string]: JsonValue;
}

function isJsonValue(value: unknown): value is JsonValue {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean" ||
    (Array.isArray(value) ? value.every(isJsonValue) : record(value))
  );
}

function record(value: unknown): value is JsonObject {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.values(value).every(isJsonValue)
  );
}

const UUID = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i;

interface EvidenceRow {
  source_name?: string;
  sheet_name?: string;
  row_number?: number;
  confidence_level?: string | number;
  record_count?: number;
  status?: string;
  evidence?: string;
}

function evidenceRows(
  value: JsonObject | JsonValue[],
  depth = 0
): EvidenceRow[] {
  if (depth > 4) return [];
  if (Array.isArray(value))
    return value
      .flatMap((item) =>
        record(item) || Array.isArray(item) ? evidenceRows(item, depth + 1) : []
      )
      .slice(0, 10);
  if (!record(value)) return [];
  if (
    typeof value.row_number === "number" ||
    typeof value.sheet_name === "string" ||
    typeof value.record_count === "number"
  )
    return [
      {
        source_name:
          typeof value.source_name === "string"
            ? value.source_name
            : typeof value.source_key === "string" &&
                !UUID.test(value.source_key)
              ? value.source_key
              : undefined,
        record_count:
          typeof value.record_count === "number"
            ? value.record_count
            : undefined,
        status: typeof value.status === "string" ? value.status : undefined,
        evidence:
          typeof value.evidence === "string" ? value.evidence : undefined,
        sheet_name:
          typeof value.sheet_name === "string" ? value.sheet_name : undefined,
        row_number:
          typeof value.row_number === "number" ? value.row_number : undefined,
        confidence_level:
          typeof value.confidence_level === "string" ||
          typeof value.confidence_level === "number"
            ? value.confidence_level
            : undefined,
      },
    ];
  return ["evidence", "rows", "items", "details", "finding"]
    .flatMap((key) => {
      const child = value[key];
      return record(child) || Array.isArray(child)
        ? evidenceRows(child, depth + 1)
        : [];
    })
    .slice(0, 10);
}

type Tone = "success" | "warning" | "danger" | "neutral";

function tone(status: string | undefined): Tone {
  const value = getStatusTone(status);
  if (value === "success") return "success";
  if (value === "warning") return "warning";
  if (value === "error") return "danger";
  return "neutral";
}

function Pill({ status }: { status: string }) {
  return (
    <span className="ton-pill" data-tone={tone(status)}>
      {getBusinessLabel(status)}
    </span>
  );
}

interface CardFrameProps {
  icon: IconFunctionComponent;
  iconTone?: "brand" | "warning" | "gold";
  title: string;
  aside?: ReactNode;
  children?: ReactNode;
}

function CardFrame({
  icon: Icon,
  iconTone = "brand",
  title,
  aside,
  children,
}: CardFrameProps) {
  return (
    <div className="flex flex-col gap-3 rounded-12 border border-01 bg-background-neutral-00 p-3">
      <div className="flex items-center gap-3">
        <span
          className="ton-icon-tile flex items-center justify-center w-8 h-8 shrink-0"
          data-tone={iconTone === "brand" ? undefined : iconTone}
        >
          <Icon size={16} />
        </span>
        <span className="flex-1 min-w-0">
          <Text font="main-ui-action" color="text-05">
            {title}
          </Text>
        </span>
        {aside}
      </div>
      {children}
    </div>
  );
}

function ReportCard({ publication }: { publication: JsonObject }) {
  const output = record(publication.output) ? publication.output : null;
  const executive = publication.report_type === "EXECUTIVE";
  const period =
    output && typeof output.period === "string" ? output.period : null;
  const scope =
    output && typeof output.scope === "string" ? output.scope : null;
  return (
    <CardFrame
      icon={SvgFileText}
      iconTone="gold"
      title={
        executive ? COPY.analysis.executiveTitle : COPY.analysis.reportTitle
      }
      aside={
        typeof publication.status === "string" ? (
          <Pill status={publication.status} />
        ) : undefined
      }
    >
      {(period || scope) && (
        <Text font="secondary-body" color="text-03">
          {[period ? formatPeriod(period) : null, scope]
            .filter(Boolean)
            .join(" · ")}
        </Text>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          href={String(publication.report_url)}
          size="md"
          rightIcon={SvgArrowRight}
        >
          {COPY.analysis.openReport}
        </Button>
        {typeof publication.download_url === "string" &&
          publication.download_url.startsWith("/api/ton/agent/reports/") && (
            <Button
              href={publication.download_url}
              prominence="secondary"
              size="md"
              icon={SvgDownload}
            >
              {COPY.analysis.download}
            </Button>
          )}
      </div>
    </CardFrame>
  );
}

function DreCard({
  status,
  blockers,
}: {
  status?: string;
  blockers: Record<string, number>;
}) {
  const total = totalBlockers(blockers);
  return (
    <CardFrame
      icon={SvgClipboard}
      iconTone={total ? "warning" : "brand"}
      title={COPY.analysis.dreTitle}
      aside={status ? <Pill status={status} /> : undefined}
    >
      {total > 0 && (
        <>
          <Text font="main-ui-body" color="text-04">
            {COPY.analysis.dreBlocked(total)}
          </Text>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {groupBlockers(blockers).map((group) => (
              <div
                key={group.category}
                className="flex flex-col rounded-08 bg-background-neutral-01 px-3 py-2"
              >
                <span className="ton-eyebrow">
                  {COPY.blockers.categories[group.category].short}
                </span>
                <span className="ton-metric">
                  <Text font="heading-h3" color="inherit">
                    {String(group.count)}
                  </Text>
                </span>
              </div>
            ))}
          </div>
          <div>
            <Button href="/ton/pendencias" prominence="secondary" size="md">
              {COPY.analysis.openPending}
            </Button>
          </div>
        </>
      )}
    </CardFrame>
  );
}

function EvidenceCard({ rows }: { rows: EvidenceRow[] }) {
  return (
    <CardFrame
      icon={SvgAlertTriangle}
      iconTone="warning"
      title={COPY.analysis.evidenceTitle}
    >
      <ul className="flex flex-col divide-y divide-border-01">
        {rows.map((row, index) => (
          <li
            key={index}
            className="flex flex-col gap-1 py-2 first:pt-0 last:pb-0"
          >
            <div className="flex flex-wrap items-center gap-2">
              {row.evidence && (
                <Text font="main-ui-action" color="text-05">
                  {getBusinessLabel(row.evidence)}
                </Text>
              )}
              {row.status && <Pill status={row.status} />}
            </div>
            <Text font="secondary-body" color="text-03">
              {[
                row.record_count !== undefined
                  ? COPY.analysis.affected(row.record_count)
                  : null,
                row.source_name ? getBusinessLabel(row.source_name) : null,
                row.sheet_name !== undefined || row.row_number !== undefined
                  ? COPY.analysis.location(
                      row.sheet_name ?? COPY.common.notAvailable,
                      row.row_number !== undefined
                        ? String(row.row_number)
                        : COPY.common.notAvailable
                    )
                  : null,
                row.confidence_level !== undefined
                  ? getBusinessLabel(String(row.confidence_level))
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </Text>
          </li>
        ))}
      </ul>
      <div>
        <Button href="/ton/pendencias" prominence="secondary" size="md">
          {COPY.analysis.openPending}
        </Button>
      </div>
    </CardFrame>
  );
}

function SourcesCard({ sources }: { sources: JsonObject[] }) {
  return (
    <CardFrame icon={SvgServer} title={COPY.analysis.sourcesTitle}>
      <ul className="flex flex-col gap-1.5">
        {sources.map((source, index) => (
          <li key={index} className="flex items-center justify-between gap-2">
            <Text font="secondary-body" color="text-04">
              {typeof source.name === "string"
                ? source.name
                : COPY.common.notAvailable}
            </Text>
            {typeof source.status === "string" && (
              <Pill status={source.status} />
            )}
          </li>
        ))}
      </ul>
      <div>
        <Button href="/ton/fontes" prominence="secondary" size="md">
          {COPY.analysis.openSources}
        </Button>
      </div>
    </CardFrame>
  );
}

export function TonToolCard({ data }: TonToolCardProps) {
  const payload = record(data) && "data" in data ? data.data : data;
  const body =
    record(payload) && record(payload.output) ? payload.output : payload;
  const publication =
    record(payload) &&
    typeof payload.report_url === "string" &&
    payload.report_url.startsWith("/ton/controladoria/reports/")
      ? payload
      : null;
  if (publication) return <ReportCard publication={publication} />;

  const rows = record(body) || Array.isArray(body) ? evidenceRows(body) : [];
  const blockers: Record<string, number> =
    record(body) && record(body.blockers)
      ? Object.fromEntries(
          Object.entries(body.blockers).filter(
            (entry): entry is [string, number] => typeof entry[1] === "number"
          )
        )
      : {};
  const sources: JsonValue[] =
    Array.isArray(body) && body.every(isJsonValue)
      ? body
      : record(body) && Array.isArray(body.sources)
        ? body.sources
        : [];
  const sourceRows = sources
    .filter(record)
    .filter(
      (source) =>
        typeof source.acquisition === "string" ||
        typeof source.last_success_at === "string"
    );
  const dreStatus =
    record(body) && typeof body.dre_status === "string"
      ? body.dre_status
      : undefined;

  if (rows.length) return <EvidenceCard rows={rows} />;
  if (Object.keys(blockers).length || dreStatus)
    return <DreCard status={dreStatus} blockers={blockers} />;
  if (sourceRows.length) return <SourcesCard sources={sourceRows} />;
  return null;
}
