"use client";

import type { ReactNode } from "react";
import { Button, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgArrowRight,
  SvgClipboard,
  SvgDownload,
  SvgFileText,
  SvgRefreshCw,
  SvgServer,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { getBusinessLabel, getStatusTone } from "@/lib/ton/labels";
import type { Json } from "@/lib/ton/work-log";
import { COPY, formatPeriod } from "@/lib/ton/copy";
import { totalBlockers } from "@/lib/ton/blockers";
import { isDraftResult } from "@/lib/ton/emailFlows";
import FlowDraftCard from "@/views/ton/EmailFlowsPage/FlowDraftCard";
import AutomationDraftCard, { isAutomationDraft } from "@/views/ton/AutomationsPage/AutomationDraftCard";
import {
  blockerCode,
  blockerLabel,
  isDecisionBlocker,
  pendingQueueHref,
} from "@/lib/ton/decisions";

interface TonToolCardProps {
  toolName: string;
  data: unknown;
  /** Period and scope the card is about ("Junho de 2026 · Consolidado"). */
  subtitle?: string | null;
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
  subtitle?: string | null;
  aside?: ReactNode;
  children?: ReactNode;
}

function CardFrame({
  icon: Icon,
  iconTone = "brand",
  title,
  subtitle,
  aside,
  children,
}: CardFrameProps) {
  return (
    <div className="ton-result-card flex flex-col gap-3 p-3">
      <div className="flex items-center gap-3">
        <span
          className="ton-icon-tile flex items-center justify-center w-8 h-8 shrink-0"
          data-tone={iconTone === "brand" ? undefined : iconTone}
        >
          <Icon size={16} />
        </span>
        <span className="flex flex-1 min-w-0 flex-col">
          <Text font="main-ui-action" color="text-05">
            {title}
          </Text>
          {subtitle && (
            <Text font="secondary-body" color="text-03">
              {subtitle}
            </Text>
          )}
        </span>
        {aside}
      </div>
      {children}
    </div>
  );
}

function ReportCard({
  publication,
  executiveTool,
}: {
  publication: JsonObject;
  executiveTool: boolean;
}) {
  const output = record(publication.output) ? publication.output : null;
  // The publication link omits the report type; the tool that made it says.
  const executive = executiveTool || publication.report_type === "EXECUTIVE";
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
  period,
  subtitle,
}: {
  status?: string;
  blockers: Record<string, number>;
  period: string | null;
  subtitle?: string | null;
}) {
  const total = totalBlockers(blockers);
  // One action per blocker: decisions open the queue on that category, data
  // gaps open the import guide. Nothing is resolved from the conversation.
  const actions = Object.entries(blockers)
    .filter(([, count]) => count > 0)
    .map(([label, count]) => ({ code: blockerCode(label), count }))
    .sort(
      (a, b) =>
        Number(isDecisionBlocker(b.code)) - Number(isDecisionBlocker(a.code)) ||
        b.count - a.count
    );
  return (
    <CardFrame
      icon={SvgClipboard}
      iconTone={total ? "warning" : "brand"}
      title={COPY.analysis.dreTitle}
      subtitle={subtitle}
      aside={status ? <Pill status={status} /> : undefined}
    >
      {total === 0 && (
        <Text font="main-ui-body" color="text-04">
          {COPY.analysis.dreClear}
        </Text>
      )}
      {total > 0 && (
        <>
          <Text font="main-ui-body" color="text-04">
            {COPY.analysis.dreBlocked(total)}
          </Text>
          <ul className="flex flex-col divide-y divide-border-01">
            {actions.map((action) => (
              <li
                key={action.code}
                className="flex flex-wrap items-center gap-2 py-2 first:pt-0 last:pb-0"
              >
                <span className="flex-1 min-w-0">
                  <Text font="secondary-action" color="text-05">
                    {`${blockerLabel(action.code)} · ${action.count}`}
                  </Text>
                </span>
                <Button
                  href={pendingQueueHref({ blocker: action.code, period })}
                  prominence="secondary"
                  size="sm"
                  rightIcon={SvgArrowRight}
                >
                  {isDecisionBlocker(action.code)
                    ? COPY.analysis.resolveAction
                    : COPY.analysis.importAction}
                </Button>
              </li>
            ))}
          </ul>
        </>
      )}
    </CardFrame>
  );
}

function ChangesCard({ body }: { body: JsonObject }) {
  const changes = record(body.changes) ? body.changes : null;
  const decisions = record(body.decisions) ? body.decisions : null;
  const periods =
    changes && Array.isArray(changes.periods)
      ? changes.periods.filter(record)
      : [];
  const latest = periods.at(-1);
  const sum = (value: JsonValue | undefined) =>
    record(value)
      ? Object.values(value).reduce<number>(
          (total, item) => total + (typeof item === "number" ? item : 0),
          0
        )
      : 0;
  const hasPrevious =
    changes && typeof changes.previous_started_at === "string";
  const pending =
    changes && typeof changes.pending_decisions === "number"
      ? changes.pending_decisions
      : 0;
  const recorded =
    decisions && Array.isArray(decisions.entries)
      ? decisions.entries.length
      : 0;
  return (
    <CardFrame icon={SvgRefreshCw} title={COPY.analysis.changesTitle}>
      {latest && hasPrevious ? (
        <Text font="main-ui-body" color="text-04">
          {COPY.analysis.changesTotals(
            sum(latest.blockers_before),
            sum(latest.blockers_after)
          )}
        </Text>
      ) : (
        <Text font="main-ui-body" color="text-04">
          {COPY.decisionLoop.changes.first}
        </Text>
      )}
      <Text font="secondary-body" color="text-03">
        {COPY.analysis.changesDecisions(recorded, pending)}
      </Text>
      <div className="flex flex-wrap gap-2">
        <Button
          href="/ton/fechamento"
          prominence="secondary"
          size="md"
          rightIcon={SvgArrowRight}
        >
          {COPY.analysis.openChanges}
        </Button>
        {pending > 0 && (
          <Button href="/ton/pendencias" size="md" rightIcon={SvgArrowRight}>
            {COPY.decisionLoop.applyNow}
          </Button>
        )}
      </div>
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

export function TonToolCard({ toolName, data, subtitle }: TonToolCardProps) {
  const payload = record(data) && "data" in data ? data.data : data;
  const body =
    record(payload) && record(payload.output) ? payload.output : payload;
  const publication =
    record(payload) &&
    typeof payload.report_url === "string" &&
    payload.report_url.startsWith("/ton/controladoria/reports/")
      ? payload
      : null;
  if (record(payload) && payload.kind === "automation_draft" && isAutomationDraft(payload))
    return <AutomationDraftCard draft={payload} />;
  if (record(payload) && payload.kind === "flow_draft" && isDraftResult(payload))
    return <FlowDraftCard draft={payload} />;
  if (publication)
    return (
      <ReportCard
        publication={publication}
        executiveTool={toolName === "ton_generate_executive_brief"}
      />
    );
  if (record(payload) && record(payload.changes) && record(payload.decisions))
    return <ChangesCard body={payload} />;

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
  const period =
    record(body) && typeof body.period === "string" ? body.period : null;
  if (Object.keys(blockers).length || dreStatus)
    return (
      <DreCard
        status={dreStatus}
        blockers={blockers}
        period={period}
        subtitle={subtitle}
      />
    );
  if (sourceRows.length) return <SourcesCard sources={sourceRows} />;
  return null;
}

/**
 * Cards that ask for an action stay open below the answer: a published
 * report, records to check, or a DRE with items that block publication. The
 * rest wait behind the "Resultados" disclosure.
 */
export function cardNeedsAttention(data: Json | undefined): boolean {
  const payload = record(data) && "data" in data ? data.data : data;
  if (!record(payload)) return false;
  if (payload.kind === "flow_draft" || payload.kind === "automation_draft") return true;
  if (
    typeof payload.report_url === "string" &&
    payload.report_url.startsWith("/ton/controladoria/reports/")
  )
    return true;
  const body = record(payload.output) ? payload.output : payload;
  if (evidenceRows(body).length > 0) return true;
  if (!record(body.blockers)) return false;
  const blockers = Object.fromEntries(
    Object.entries(body.blockers).filter(
      (entry): entry is [string, number] => typeof entry[1] === "number"
    )
  );
  return totalBlockers(blockers) > 0;
}
