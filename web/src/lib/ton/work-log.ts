import { PacketType } from "@/app/app/services/streamingModels";
import type {
  CustomToolDelta,
  CustomToolStart,
  ObjTypes,
  Packet,
} from "@/app/app/services/streamingModels";
import type {
  TransformedStep,
  TurnGroup,
} from "@/app/app/message/messageComponents/timeline/transformers";
import type { ToolSnapshot } from "@/lib/tools/types";
import { tonTool, type TonToolDescriptor } from "@/lib/ton/chat-tools";
import {
  COPY,
  formatDateTime,
  formatNumber,
  formatPeriod,
} from "@/lib/ton/copy";
import { TON_TOOL_NAMES } from "@/lib/ton/labels";
import { blockerCode, blockerLabel } from "@/lib/ton/decisions";

/**
 * The TON work log: what the assistant did to answer, derived only from the
 * stream. Every line states an observable fact (a query ran, with these
 * filters, and returned this), never model-private reasoning text.
 */

export type WorkStatus = "running" | "done" | "failed";

export type Json =
  | string
  | number
  | boolean
  | null
  | Json[]
  | { [key: string]: Json };
export type JsonObject = { [key: string]: Json };

export interface WorkQuery {
  id: string;
  /** TON tool key (`ton_*`), or null for a tool TON does not describe. */
  key: string | null;
  tool: TonToolDescriptor;
  /** Name for a tool TON does not describe. */
  fallbackName: string;
  /** Period, unit or blocker the query was about. */
  subject: string | null;
  /** One line on what came back. */
  summary: string | null;
  status: WorkStatus;
  data: Json | undefined;
  args: JsonObject | null;
  error: string | null;
}

export type ThinkPhase = "plan" | "analyze" | "compose";

export type WorkStep =
  | { kind: "think"; id: string; status: WorkStatus; phase: ThinkPhase }
  | { kind: "queries"; id: string; status: WorkStatus; items: WorkQuery[] }
  | {
      kind: "python";
      id: string;
      status: WorkStatus;
      code: string;
      output: string;
      fileIds: string[];
    }
  | { kind: "file"; id: string; status: WorkStatus; name: string | null }
  | { kind: "other"; id: string; status: WorkStatus };

export interface SpecialistStep {
  code: string;
  status: string;
  reason: string | null;
}

export interface SpecialistWork {
  key: string;
  name: string | null;
  status: string;
  reason: string | null;
  limitations: string[];
  actions: string[];
  steps: SpecialistStep[];
}

export interface DataOrigin {
  name: string;
  file: string | null;
  importedAt: string | null;
  status: string | null;
  acquisition: string | null;
}

export interface WorkSource {
  id: string;
  key: string | null;
  tool: TonToolDescriptor;
  label: string;
  subject: string | null;
  summary: string | null;
}

export interface WorkLog {
  steps: WorkStep[];
  queries: WorkQuery[];
  specialists: SpecialistWork[];
  sources: WorkSource[];
  origins: DataOrigin[];
  calculations: number;
  running: boolean;
  /** Present-continuous line for what is happening right now. */
  current: string | null;
}

export type UnitNames = (unitId: string) => string | null;

// ---------------------------------------------------------------------------
// JSON helpers
// ---------------------------------------------------------------------------

export function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: Json | undefined): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function num(value: Json | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function sum(value: Json | undefined): number {
  if (Array.isArray(value)) return value.length;
  if (!isObject(value)) return 0;
  return Object.values(value).reduce<number>(
    (total, item) => total + (typeof item === "number" ? item : 0),
    0
  );
}

export function isJson(value: unknown): value is Json {
  if (value === null) return true;
  switch (typeof value) {
    case "string":
    case "number":
    case "boolean":
      return true;
    case "object":
      return Array.isArray(value)
        ? value.every(isJson)
        : Object.values(value).every(isJson);
    default:
      return false;
  }
}

function isJsonObject(value: unknown): value is JsonObject {
  return isObject(value) && isJson(value);
}

/** The tool payload without the `{ data: ... }` envelope some deltas carry. */
export function unwrap(data: Json | undefined): Json | undefined {
  return isObject(data) && "data" in data ? data.data : data;
}

const PERIOD = /^\d{4}-\d{2}-01$/;

interface ScopeHint {
  period: string | null;
  /** null = consolidated, undefined = not stated. */
  unit: string | null | undefined;
}

function findScope(data: Json | undefined): ScopeHint {
  const candidates: Json[] = [];
  if (isObject(data)) {
    candidates.push(data);
    if (isObject(data.output)) candidates.push(data.output);
    if (isObject(data.scope)) candidates.push(data.scope);
  }
  if (Array.isArray(data) && isObject(data[0])) {
    candidates.push(data[0]);
    if (isObject(data[0].scope)) candidates.push(data[0].scope);
  }
  for (const candidate of candidates) {
    if (!isObject(candidate)) continue;
    const period = text(candidate.period);
    if (period && PERIOD.test(period)) {
      const unit =
        "unit_id" in candidate ? (text(candidate.unit_id) ?? null) : undefined;
      return { period, unit };
    }
  }
  return { period: null, unit: undefined };
}

// ---------------------------------------------------------------------------
// Query subject and summary
// ---------------------------------------------------------------------------

/** Tools whose answer depends on consolidated versus unit scope. */
const SCOPED = new Set([
  "ton_get_dre_result",
  "ton_get_dre_readiness",
  "ton_analyze_closing",
  "ton_get_billing_summary",
  "ton_get_budget_summary",
  "ton_get_reconciliation_summary",
  "ton_generate_closing_report",
  "ton_generate_executive_brief",
]);

export function querySubject(
  key: string | null,
  args: JsonObject | null,
  data: Json | undefined,
  unitNames?: UnitNames
): string | null {
  const blocker = args ? text(args.blocker) : null;
  if (blocker) return blockerLabel(blockerCode(blocker));
  const fromData = findScope(data);
  const argPeriod = args ? text(args.period) : null;
  const period =
    argPeriod && PERIOD.test(argPeriod) ? argPeriod : fromData.period;
  const argUnit = args ? text(args.unit_id) : null;
  const unit = argUnit ?? fromData.unit;
  const parts: string[] = [];
  if (period) parts.push(formatPeriod(period));
  if (key && SCOPED.has(key) && (period || unit)) {
    if (unit) parts.push(unitNames?.(unit) ?? COPY.work.subject.unit);
    else if (unit === null || period)
      parts.push(COPY.work.subject.consolidated);
  }
  return parts.length ? parts.join(" · ") : null;
}

const W = COPY.work.summary;

export function querySummary(
  key: string | null,
  body: Json | undefined
): string | null {
  if (body === undefined || body === null) return null;
  switch (key) {
    case "ton_list_sources": {
      if (!Array.isArray(body)) break;
      const attention = body.filter(
        (item) => isObject(item) && /aten/i.test(text(item.status) ?? "")
      ).length;
      return W.sources(body.length, attention);
    }
    case "ton_get_financial_context": {
      if (!isObject(body)) break;
      const bases = Array.isArray(body.bases)
        ? body.bases.filter(isObject)
        : [];
      const results = bases.reduce(
        (total, base) =>
          total +
          (Array.isArray(base.stored_dre_results)
            ? base.stored_dre_results.length
            : 0),
        0
      );
      return W.context(bases.length, results);
    }
    case "ton_list_findings": {
      const items = Array.isArray(body)
        ? body
        : isObject(body) && Array.isArray(body.items)
          ? body.items
          : null;
      if (!items) break;
      const blocking = items.filter(
        (item) => isObject(item) && item.blocking === true
      ).length;
      return W.findings(items.length, blocking);
    }
    case "ton_get_dre_result": {
      if (!Array.isArray(body)) break;
      const lines = body.filter(
        (item) => isObject(item) && text(item.label) !== null
      ).length;
      const header = body.find(
        (item) => isObject(item) && text(item.status) !== null
      );
      return W.dre(lines, isObject(header) ? text(header.status) : null);
    }
    case "ton_get_dre_readiness":
    case "ton_analyze_closing":
    case "ton_generate_closing_report":
    case "ton_generate_executive_brief": {
      if (!isObject(body)) break;
      if (text(body.report_url)) return W.published;
      const output = isObject(body.output) ? body.output : body;
      const status = text(output.dre_status) ?? text(output.status);
      const blockers = sum(output.blockers);
      const specialists = Array.isArray(output.specialists)
        ? output.specialists.filter(
            (item) => isObject(item) && !/bloque/i.test(text(item.status) ?? "")
          ).length
        : 0;
      return W.readiness(blockers, status, specialists);
    }
    case "ton_get_billing_summary": {
      if (!isObject(body)) break;
      return W.billing(
        num(body.billing_count) ?? 0,
        num(body.actual_count) ?? 0
      );
    }
    case "ton_get_budget_summary": {
      if (!isObject(body)) break;
      return W.budget(num(body.budget_count) ?? 0);
    }
    case "ton_get_reconciliation_summary": {
      if (!isObject(body) || !isObject(body.reconciliation)) break;
      const entries = Object.entries(body.reconciliation).filter(
        (entry): entry is [string, number] => typeof entry[1] === "number"
      );
      return entries
        .map(
          ([label, count]) =>
            `${formatNumber(count)} ${W.reconciliationLabel(label)}`
        )
        .join(" · ");
    }
    case "ton_get_readiness_evidence": {
      if (!isObject(body)) break;
      return W.evidence(num(body.total) ?? sum(body.rows));
    }
    case "ton_list_overdue_actions": {
      if (!isObject(body)) break;
      return W.overdue(sum(body.items));
    }
    case "ton_get_recent_changes": {
      if (!isObject(body) || !isObject(body.changes)) break;
      const periods = Array.isArray(body.changes.periods)
        ? body.changes.periods.filter(isObject)
        : [];
      const latest = periods.at(-1);
      return latest
        ? COPY.analysis.trace.changes(
            sum(latest.blockers_before),
            sum(latest.blockers_after)
          )
        : null;
    }
    default:
      break;
  }
  if (Array.isArray(body)) return W.records(body.length);
  if (isObject(body)) {
    const total = num(body.total);
    if (total !== null) return W.records(total);
    if (Array.isArray(body.items)) return W.records(body.items.length);
  }
  return null;
}

// ---------------------------------------------------------------------------
// Specialists and data origins
// ---------------------------------------------------------------------------

/** What each specialist did, from a closing analysis or report payload. */
export function specialistWork(body: Json | undefined): SpecialistWork[] {
  if (!isObject(body)) return [];
  const output = isObject(body.output) ? body.output : null;
  const outcomes =
    output && Array.isArray(output.specialists)
      ? output.specialists.filter(isObject)
      : [];
  const steps = Array.isArray(body.steps) ? body.steps.filter(isObject) : [];
  return outcomes
    .map((outcome) => {
      const key = text(outcome.key);
      if (!key) return null;
      const strings = (value: Json | undefined) =>
        Array.isArray(value)
          ? value.filter((item): item is string => typeof item === "string")
          : [];
      return {
        key,
        name: text(outcome.name),
        status: text(outcome.status) ?? "",
        reason: text(outcome.reason),
        limitations: strings(outcome.limitations),
        actions: strings(outcome.actions),
        steps: steps
          .filter((step) => step.specialist === key)
          .map((step) => ({
            code: text(step.code) ?? "",
            status: text(step.status) ?? "",
            reason: text(step.reason),
          })),
      } satisfies SpecialistWork;
    })
    .filter((item): item is SpecialistWork => item !== null);
}

export function isSpecialistActive(specialist: SpecialistWork): boolean {
  return !/bloque|aguard/i.test(specialist.status);
}

function originsFrom(key: string | null, body: Json | undefined): DataOrigin[] {
  const list: Json[] =
    key === "ton_list_sources" && Array.isArray(body)
      ? body
      : isObject(body) &&
          isObject(body.output) &&
          Array.isArray(body.output.sources)
        ? body.output.sources
        : [];
  return list.filter(isObject).flatMap((source) => {
    const name = text(source.name);
    if (!name) return [];
    const latest = isObject(source.latest) ? source.latest : null;
    return [
      {
        name,
        file: latest ? text(latest.filename) : null,
        importedAt: text(source.last_success_at),
        status: text(source.status),
        acquisition: text(source.acquisition),
      },
    ];
  });
}

// ---------------------------------------------------------------------------
// Packets → steps
// ---------------------------------------------------------------------------

type ObjOf<K extends ObjTypes["type"]> = Extract<ObjTypes, { type: K }>;

/** Packet objects of one type, narrowed without casts. */
function objects<K extends ObjTypes["type"]>(
  packets: Packet[],
  type: K
): ObjOf<K>[] {
  return packets
    .map((packet) => packet.obj)
    .filter((obj): obj is ObjOf<K> => obj.type === type);
}

function firstType(step: TransformedStep): ObjTypes["type"] | null {
  for (const packet of step.packets) {
    const type = packet.obj.type;
    if (type !== PacketType.SECTION_END && type !== PacketType.ERROR)
      return type;
  }
  return null;
}

function ended(packets: Packet[]): boolean {
  return packets.some(
    (packet) =>
      packet.obj.type === PacketType.SECTION_END ||
      packet.obj.type === PacketType.ERROR ||
      packet.obj.type === PacketType.REASONING_DONE
  );
}

function errored(packets: Packet[]): boolean {
  return packets.some((packet) => packet.obj.type === PacketType.ERROR);
}

/** The TON key from the tool id, its code, or its display name. */
function toolKey(
  start: CustomToolStart | CustomToolDelta | undefined,
  tools: ToolSnapshot[]
): string | null {
  if (!start) return null;
  const tool =
    start.tool_id != null
      ? tools.find((item) => item.id === start.tool_id)
      : undefined;
  if (tool?.name.startsWith("ton_")) return tool.name;
  if (start.tool_name.startsWith("ton_")) return start.tool_name;
  return (
    Object.entries(TON_TOOL_NAMES).find(
      ([, label]) => label === start.tool_name
    )?.[0] ?? null
  );
}

function buildQuery(
  step: TransformedStep,
  tools: ToolSnapshot[],
  stopped: boolean,
  unitNames?: UnitNames
): WorkQuery {
  const packets = step.packets;
  const start = objects(packets, "custom_tool_start")[0];
  const rawArgs: unknown = objects(packets, "custom_tool_args")[0]?.tool_args;
  const delta = objects(packets, "custom_tool_delta").at(-1);
  const key = toolKey(start ?? delta, tools);
  const args = isJsonObject(rawArgs) ? rawArgs : null;
  const raw: unknown = delta?.data;
  const data = delta?.error ? undefined : unwrap(isJson(raw) ? raw : undefined);
  const failed = Boolean(delta?.error) || errored(packets);
  const done = ended(packets) || delta !== undefined || stopped;
  return {
    id: step.key,
    key,
    tool: tonTool(key),
    fallbackName:
      start?.tool_name ?? delta?.tool_name ?? COPY.work.genericQuery,
    subject: querySubject(key, args, data, unitNames),
    summary: failed ? null : querySummary(key, data),
    status: failed ? "failed" : done ? "done" : "running",
    data,
    args,
    error: failed ? COPY.work.queryFailed : null,
  };
}

export interface BuildWorkLogOptions {
  stopped: boolean;
  /** Answer text started; the last reasoning phase writes it. */
  answering: boolean;
  unitNames?: UnitNames;
}

export function buildWorkLog(
  turnGroups: TurnGroup[],
  tools: ToolSnapshot[],
  { stopped, answering, unitNames }: BuildWorkLogOptions
): WorkLog {
  const steps: WorkStep[] = [];
  for (const group of turnGroups) {
    const queries: WorkQuery[] = [];
    for (const step of group.steps) {
      const type = firstType(step);
      const finished = ended(step.packets) || stopped;
      const status: WorkStatus = errored(step.packets)
        ? "failed"
        : finished
          ? "done"
          : "running";
      switch (type) {
        case PacketType.CUSTOM_TOOL_START:
        case PacketType.CUSTOM_TOOL_ARGS:
        case PacketType.CUSTOM_TOOL_DELTA:
          queries.push(buildQuery(step, tools, stopped, unitNames));
          break;
        case PacketType.REASONING_START:
        case PacketType.REASONING_DELTA:
          steps.push({ kind: "think", id: step.key, status, phase: "analyze" });
          break;
        case PacketType.PYTHON_TOOL_START:
        case PacketType.PYTHON_TOOL_DELTA: {
          const start = objects(step.packets, "python_tool_start")[0];
          const deltas = objects(step.packets, "python_tool_delta");
          const stderr = deltas
            .map((d) => d.stderr)
            .join("")
            .trim();
          steps.push({
            kind: "python",
            id: step.key,
            status: stderr && !deltas.some((d) => d.stdout) ? "failed" : status,
            code: start?.code ?? "",
            output: deltas
              .map((d) => d.stdout)
              .join("")
              .trimEnd(),
            fileIds: deltas.flatMap((d) => d.file_ids ?? []),
          });
          break;
        }
        case PacketType.FILE_READER_START:
        case PacketType.FILE_READER_RESULT: {
          const result = objects(step.packets, "file_reader_result")[0];
          steps.push({
            kind: "file",
            id: step.key,
            status,
            name: result?.file_name ?? null,
          });
          break;
        }
        default:
          if (type) steps.push({ kind: "other", id: step.key, status });
      }
    }
    if (queries.length) {
      const status: WorkStatus = queries.some((q) => q.status === "running")
        ? "running"
        : queries.every((q) => q.status === "failed")
          ? "failed"
          : "done";
      steps.push({
        kind: "queries",
        id: `q-${group.turnIndex}`,
        status,
        items: queries,
      });
    }
  }

  // Reasoning phases are named by where they sit, not by their private text.
  const thinks = steps.filter((step) => step.kind === "think");
  thinks.forEach((step, index) => {
    if (step.kind !== "think") return;
    const isLast = steps.at(-1) === step;
    if (isLast && (answering || steps.length === 1)) step.phase = "compose";
    else if (index === 0 && steps[0] === step) step.phase = "plan";
  });

  const queries = steps.flatMap((step) =>
    step.kind === "queries" ? step.items : []
  );

  // The latest specialist record wins: a later analysis supersedes earlier ones.
  let specialists: SpecialistWork[] = [];
  for (const query of queries) {
    const found = specialistWork(query.data);
    if (found.length) specialists = found;
  }

  const sources: WorkSource[] = [];
  const seen = new Set<string>();
  for (const query of queries) {
    if (query.status === "failed") continue;
    const id = `${query.key ?? query.fallbackName}|${query.subject ?? ""}`;
    if (seen.has(id)) continue;
    seen.add(id);
    sources.push({
      id,
      key: query.key,
      tool: query.tool,
      label: query.key ? query.tool.label : query.fallbackName,
      subject: query.subject,
      summary: query.summary,
    });
  }

  const origins = new Map<string, DataOrigin>();
  for (const query of queries) {
    for (const origin of originsFrom(query.key, query.data)) {
      const previous = origins.get(origin.name);
      origins.set(origin.name, {
        name: origin.name,
        file: origin.file ?? previous?.file ?? null,
        importedAt: origin.importedAt ?? previous?.importedAt ?? null,
        status: origin.status ?? previous?.status ?? null,
        acquisition: origin.acquisition ?? previous?.acquisition ?? null,
      });
    }
  }

  const running = !stopped && steps.some((step) => step.status === "running");
  return {
    steps,
    queries,
    specialists,
    sources,
    origins: [...origins.values()],
    calculations: steps.filter((step) => step.kind === "python").length,
    running,
    current: stopped ? null : currentActivity(steps, answering),
  };
}

function currentActivity(steps: WorkStep[], answering: boolean): string {
  if (answering) return COPY.work.doing.compose;
  const active = [...steps].reverse().find((step) => step.status === "running");
  const step = active ?? steps.at(-1);
  if (!step) return COPY.work.doing.start;
  switch (step.kind) {
    case "think":
      return active ? COPY.work.doing[step.phase] : COPY.work.doing.analyze;
    case "queries": {
      const running = step.items.filter((item) => item.status === "running");
      const first = running[0];
      if (!first) return COPY.work.doing.analyze;
      return running.length > 1
        ? COPY.work.doing.parallel(first.tool.doing, running.length - 1)
        : first.tool.doing;
    }
    case "python":
      return active ? COPY.work.doing.python : COPY.work.doing.analyze;
    case "file":
      return active ? COPY.work.doing.file : COPY.work.doing.analyze;
    default:
      return COPY.work.doing.analyze;
  }
}

/** "02/10/2026 11:35", or null for an unparseable value. */
export function safeDateTime(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : formatDateTime(date);
}
