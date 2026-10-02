"use client";

import { Text } from "@opal/components";
import {
  SvgAlertCircle,
  SvgCheckCircle,
  SvgCircle,
  SvgMinusCircle,
} from "@opal/icons";
import { COPY, formatPeriod } from "@/lib/ton/copy";
import { TON_TOOL_NAMES } from "@/lib/ton/labels";

type Json = string | number | boolean | null | Json[] | { [key: string]: Json };
type JsonObject = { [key: string]: Json };

const TRACE = COPY.analysis.trace;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: Json | undefined): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function count(value: Json | undefined): number {
  if (Array.isArray(value)) return value.length;
  if (isObject(value))
    return Object.values(value).reduce<number>(
      (sum, item) => sum + (typeof item === "number" ? item : 0),
      0
    );
  return 0;
}

/** The TON tool key from the name the stream carries (code or display name). */
export function tonToolKey(name: string): string | null {
  if (name.startsWith("ton_")) return name;
  return (
    Object.entries(TON_TOOL_NAMES).find(([, label]) => label === name)?.[0] ??
    null
  );
}

function StepIcon({ status }: { status: string }) {
  const value = status.toLowerCase();
  if (/conclu|passed|aprovad/.test(value))
    return <SvgCheckCircle size={14} className="ton-brand-text shrink-0" />;
  if (/bloque|falh|failed/.test(value))
    return (
      <SvgAlertCircle size={14} className="text-status-warning-05 shrink-0" />
    );
  if (/não executad|skipped/.test(value))
    return <SvgMinusCircle size={14} className="text-text-03 shrink-0" />;
  return <SvgCircle size={14} className="text-text-03 shrink-0" />;
}

/** What each specialist did in a closing analysis, from the recorded steps. */
function SpecialistTrace({ body }: { body: JsonObject }) {
  const output = isObject(body.output) ? body.output : null;
  const steps = Array.isArray(body.steps) ? body.steps.filter(isObject) : [];
  const specialists =
    output && Array.isArray(output.specialists)
      ? output.specialists.filter(isObject)
      : [];
  const keys = [
    ...new Set(steps.map((step) => text(step.specialist)).filter(Boolean)),
  ] as string[];
  if (!keys.length) return null;
  return (
    <ol className="flex flex-col gap-3">
      {keys.map((key) => {
        const outcome = specialists.find((item) => item.key === key);
        const own = steps.filter((step) => step.specialist === key);
        const status = text(outcome?.status);
        const reason = text(outcome?.reason);
        return (
          <li key={key} className="flex flex-col gap-1">
            <div className="flex flex-wrap items-baseline gap-x-2">
              <Text font="secondary-action" color="text-05">
                {text(outcome?.name) ?? key}
              </Text>
              {status && (
                <Text font="secondary-body" color="text-03">
                  {status}
                </Text>
              )}
            </div>
            {reason && (
              <Text font="secondary-body" color="text-04">
                {reason}
              </Text>
            )}
            <ul className="flex flex-col gap-0.5 ps-1">
              {own.map((step, index) => (
                <li key={index} className="flex items-start gap-1.5">
                  <span className="pt-0.5">
                    <StepIcon status={text(step.status) ?? ""} />
                  </span>
                  <Text font="secondary-body" color="text-04">
                    {[text(step.code), text(step.reason)]
                      .filter(Boolean)
                      .join(" — ")}
                  </Text>
                </li>
              ))}
            </ul>
          </li>
        );
      })}
    </ol>
  );
}

/** One line saying what a TON query returned, in business terms. */
export function tonResultSummary(key: string, body: Json): string | null {
  if (key === "ton_list_sources" && Array.isArray(body))
    return TRACE.sources(body.length);
  if (!isObject(body)) {
    return Array.isArray(body) ? TRACE.records(body.length) : null;
  }
  if (key === "ton_get_financial_context")
    return TRACE.context(
      Array.isArray(body.bases) ? body.bases.length : 0,
      Array.isArray(body.structure_version_ids)
        ? body.structure_version_ids.length
        : 0
    );
  if (key === "ton_get_recent_changes" && isObject(body.changes)) {
    const periods = Array.isArray(body.changes.periods)
      ? body.changes.periods.filter(isObject)
      : [];
    const latest = periods.at(-1);
    return latest
      ? TRACE.changes(
          count(latest.blockers_before),
          count(latest.blockers_after)
        )
      : null;
  }
  if (typeof body.total === "number") return TRACE.items(body.total);
  if (isObject(body.blockers))
    return TRACE.blockers(count(body.blockers), text(body.status));
  const output = isObject(body.output) ? body.output : null;
  if (output && isObject(output.blockers)) {
    const period = text(output.period);
    const line = TRACE.blockers(
      count(output.blockers),
      text(output.dre_status)
    );
    // A model may query more than one period; each step names its own.
    return period ? `${formatPeriod(period)}: ${line}` : line;
  }
  return null;
}

/**
 * The body of a TON tool step in the reasoning timeline: what the step
 * checked, never the raw payload (that stays behind the admin disclosure).
 */
export default function TonStepDetail({
  toolName,
  data,
}: {
  toolName: string;
  data: unknown;
}) {
  const key = tonToolKey(toolName);
  if (!key) return null;
  const payload = isObject(data) && "data" in data ? data.data : data;
  if (payload === undefined) return null;
  const body = payload as Json;
  const specialists =
    isObject(body) &&
    (key === "ton_analyze_closing" ||
      key === "ton_generate_closing_report" ||
      key === "ton_generate_executive_brief") ? (
      <SpecialistTrace body={body} />
    ) : null;
  const summary = tonResultSummary(key, body);
  if (!specialists && !summary) return null;
  return (
    <div className="flex flex-col gap-2 ps-(--timeline-common-text-padding)">
      {summary && (
        <Text font="secondary-body" color="text-04">
          {summary}
        </Text>
      )}
      {specialists}
    </div>
  );
}
