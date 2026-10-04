"use client";

import "@/views/ton/chat/chat.css";

import { useMemo, useState } from "react";
import { Button, CopyButton, Text } from "@opal/components";
import {
  SvgAlertCircle,
  SvgCheck,
  SvgChevronDown,
  SvgChevronUp,
  SvgCpu,
  SvgFileText,
} from "@opal/icons";
import { StopReason } from "@/app/app/services/streamingModels";
import type { TurnGroup } from "@/app/app/message/messageComponents/timeline/transformers";
import { useStreamingDuration } from "@/app/app/message/messageComponents/timeline/hooks/useStreamingDuration";
import { useStreamingStartTime } from "@/app/app/stores/useChatSessionStore";
import type { ToolSnapshot } from "@/lib/tools/types";
import { useUser } from "@/providers/UserProvider";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useTonUnitNames } from "@/lib/ton/api";
import { COPY, formatClock, formatElapsed } from "@/lib/ton/copy";
import {
  buildWorkLog,
  isSpecialistActive,
  type SpecialistWork,
  type WorkLog,
  type WorkQuery,
  type WorkStatus,
  type WorkStep,
} from "@/lib/ton/work-log";
import TonMark from "@/views/ton/chat/TonMark";
import SpecialistMark from "@/views/ton/chat/SpecialistMark";
import DataPreviewView from "@/views/ton/chat/DataPreviewView";

const WORK = COPY.work;

export interface TonWorkPanelProps {
  turnGroups: TurnGroup[];
  tools: ToolSnapshot[];
  stopPacketSeen: boolean;
  stopReason?: StopReason;
  /** Answer text has started to render below the panel. */
  answering: boolean;
  processingDurationSeconds?: number;
  toolProcessingDuration?: number;
}

function useCanInspect(): boolean {
  const { user } = useUser();
  return hasPermission(
    user?.effective_permissions ?? [],
    Permission.FULL_ADMIN_PANEL_ACCESS
  );
}

function StatusDot({ status }: { status: WorkStatus }) {
  return (
    <span className="ton-wk-status" aria-hidden>
      <span className="ton-status-dot" data-status={status}>
        {status === "done" && <SvgCheck />}
        {status === "failed" && <SvgAlertCircle />}
      </span>
    </span>
  );
}

function SpecialistStack({
  specialists,
  size = 24,
}: {
  specialists: SpecialistWork[];
  size?: number;
}) {
  const active = specialists.filter(isSpecialistActive);
  if (!active.length) return null;
  return (
    <span className="ton-specialist-stack">
      {active.map((specialist) => (
        <SpecialistMark
          key={specialist.key}
          specialistKey={specialist.key}
          fallbackName={specialist.name}
          size={size}
          withTooltip
        />
      ))}
    </span>
  );
}

function QueryRow({
  query,
  specialists,
  canInspect,
  index,
}: {
  query: WorkQuery;
  specialists: SpecialistWork[];
  canInspect: boolean;
  index: number;
}) {
  const [open, setOpen] = useState(false);
  const Icon = query.tool.icon;
  const title = query.key ? query.tool.label : query.fallbackName;
  const running = query.status === "running";
  const ownSpecialists =
    query.key === "ton_analyze_closing" ||
    query.key === "ton_generate_closing_report" ||
    query.key === "ton_generate_executive_brief"
      ? specialists
      : [];
  const hasData = query.status === "done" && query.data !== undefined;
  return (
    <li
      className="ton-query"
      data-status={query.status}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="ton-query-row">
        <span className="ton-query-icon" aria-hidden>
          <Icon />
        </span>
        <span className="flex flex-1 min-w-0 flex-col">
          <span className="flex flex-wrap items-baseline gap-x-1.5">
            <Text font="secondary-action" color="text-05">
              {running ? `${query.tool.doing}…` : title}
            </Text>
            {query.subject && (
              <Text font="secondary-body" color="text-03">
                {query.subject}
              </Text>
            )}
          </span>
          {(query.summary || query.error) && (
            <Text font="secondary-body" color="text-03">
              {query.error ?? query.summary ?? ""}
            </Text>
          )}
        </span>
        {ownSpecialists.length > 0 && (
          <SpecialistStack specialists={ownSpecialists} />
        )}
        {hasData && (
          <span className="ton-query-action" data-open={open || undefined}>
            <Button
              prominence="tertiary"
              size="sm"
              rightIcon={open ? SvgChevronUp : SvgChevronDown}
              aria-expanded={open}
              onClick={() => setOpen((value) => !value)}
            >
              {open ? WORK.hideData : WORK.readData}
            </Button>
          </span>
        )}
      </div>
      {open && hasData && (
        <div className="ton-query-detail flex flex-col gap-2">
          <DataPreviewView data={query.data} />
          {canInspect && (
            <div>
              <CopyButton
                size="sm"
                tooltip={WORK.copyRawTooltip}
                getCopyText={() =>
                  JSON.stringify(
                    { args: query.args, data: query.data },
                    null,
                    2
                  )
                }
              >
                {WORK.copyRaw}
              </CopyButton>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function PythonStep({
  step,
  canInspect,
}: {
  step: Extract<WorkStep, { kind: "python" }>;
  canInspect: boolean;
}) {
  const [view, setView] = useState<"none" | "output" | "code">("none");
  const toggle = (next: "output" | "code") =>
    setView((current) => (current === next ? "none" : next));
  return (
    <>
      <div className="ton-wk-row">
        <span className="ton-query-icon" aria-hidden>
          <SvgCpu />
        </span>
        <span className="flex flex-1 min-w-0 flex-col">
          <Text font="secondary-action" color="text-05">
            {step.status === "running"
              ? WORK.python.running
              : WORK.python.title}
          </Text>
          <Text font="secondary-body" color="text-03">
            {step.fileIds.length > 0
              ? `${WORK.python.note} ${WORK.python.files(step.fileIds.length)}.`
              : WORK.python.note}
          </Text>
        </span>
        {step.output && (
          <Button
            prominence="tertiary"
            size="sm"
            rightIcon={view === "output" ? SvgChevronUp : SvgChevronDown}
            aria-expanded={view === "output"}
            onClick={() => toggle("output")}
          >
            {WORK.python.showOutput}
          </Button>
        )}
        {canInspect && step.code && (
          <Button
            prominence="tertiary"
            size="sm"
            aria-expanded={view === "code"}
            onClick={() => toggle("code")}
          >
            {WORK.python.showCode}
          </Button>
        )}
      </div>
      {view !== "none" && (
        <div className="ton-query-detail">
          <pre className="ton-code">
            {view === "output" ? step.output : step.code}
          </pre>
        </div>
      )}
    </>
  );
}

function StepView({
  step,
  log,
  canInspect,
}: {
  step: WorkStep;
  log: WorkLog;
  canInspect: boolean;
}) {
  switch (step.kind) {
    case "think":
      return (
        <li className="ton-wk-step">
          <StatusDot status={step.status} />
          <Text font="secondary-body" color="text-04">
            {step.status === "running"
              ? `${WORK.doing[step.phase]}…`
              : WORK.phase[step.phase]}
          </Text>
        </li>
      );
    case "queries":
      return (
        <li className="ton-wk-step">
          <StatusDot status={step.status} />
          {step.items.length > 1 && (
            <Text font="secondary-body" color="text-04">
              {WORK.parallel(step.items.length)}
            </Text>
          )}
          <ul className="ton-query-list">
            {step.items.map((query, index) => (
              <QueryRow
                key={query.id}
                query={query}
                specialists={log.specialists}
                canInspect={canInspect}
                index={index}
              />
            ))}
          </ul>
        </li>
      );
    case "python":
      return (
        <li className="ton-wk-step">
          <StatusDot status={step.status} />
          <PythonStep step={step} canInspect={canInspect} />
        </li>
      );
    case "file":
      return (
        <li className="ton-wk-step">
          <StatusDot status={step.status} />
          <div className="ton-wk-row">
            <span className="ton-query-icon" aria-hidden>
              <SvgFileText />
            </span>
            <Text font="secondary-body" color="text-04">
              {step.name ? WORK.file.title(step.name) : WORK.file.fallback}
            </Text>
          </div>
        </li>
      );
    default:
      return (
        <li className="ton-wk-step">
          <StatusDot status={step.status} />
          <Text font="secondary-body" color="text-03">
            {step.status === "failed" ? WORK.failed : WORK.other}
          </Text>
        </li>
      );
  }
}

function statsLine(log: WorkLog): string {
  const active = log.specialists.filter(isSpecialistActive).length;
  return [
    log.queries.length ? WORK.header.queries(log.queries.length) : null,
    active ? WORK.header.specialists(active) : null,
    log.calculations ? WORK.header.calculations(log.calculations) : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

/**
 * How TON reached the answer, above the answer text. While TON works the
 * steps stream in live with what each query is doing; once the answer starts
 * the panel folds into one line and stays one click away.
 */
export default function TonWorkPanel({
  turnGroups,
  tools,
  stopPacketSeen,
  stopReason,
  answering,
  processingDurationSeconds,
  toolProcessingDuration,
}: TonWorkPanelProps) {
  const unitNames = useTonUnitNames();
  const canInspect = useCanInspect();
  const log = useMemo(
    () =>
      buildWorkLog(turnGroups, tools, {
        stopped: stopPacketSeen,
        answering,
        unitNames,
      }),
    [turnGroups, tools, stopPacketSeen, answering, unitNames]
  );
  const [toggled, setToggled] = useState<boolean | null>(null);
  const streamingStart = useStreamingStartTime();
  const busy = !stopPacketSeen;
  const working = busy && !answering;
  const elapsed = useStreamingDuration(
    working,
    streamingStart,
    toolProcessingDuration
  );
  const userStopped = stopReason === StopReason.USER_CANCELLED;
  const hasSteps = log.steps.length > 0;
  // Live while TON works; folded once the answer is on screen.
  const expanded = toggled ?? (working && hasSteps);
  const duration = toolProcessingDuration ?? processingDurationSeconds;
  const stats = statsLine(log);

  if (!hasSteps && !busy) return null;

  return (
    <section className="ton-work" aria-live="polite" aria-busy={busy}>
      <div className="ton-work-header">
        <TonMark working={busy} />
        <div className="flex flex-1 min-w-0 flex-col">
          {busy ? (
            <span key={log.current ?? "start"} className="ton-work-live">
              <Text font="main-ui-action" color="text-04" maxLines={1}>
                {hasSteps
                  ? `${log.current ?? WORK.doing.analyze}…`
                  : WORK.header.empty}
              </Text>
            </span>
          ) : (
            <span className="flex flex-wrap items-baseline gap-x-2">
              <Text font="main-ui-action" color="text-04">
                {userStopped
                  ? WORK.header.stopped
                  : duration
                    ? WORK.header.worked(formatElapsed(duration))
                    : WORK.header.workedShort}
              </Text>
              {stats && (
                <Text font="secondary-body" color="text-03">
                  {stats}
                </Text>
              )}
            </span>
          )}
        </div>
        {!expanded && !busy && log.specialists.length > 0 && (
          <SpecialistStack specialists={log.specialists} />
        )}
        {working && elapsed > 0 && (
          <span className="ton-work-timer">
            <Text font="secondary-body" color="text-03">
              {formatClock(elapsed)}
            </Text>
          </span>
        )}
        {hasSteps && (
          <Button
            prominence="tertiary"
            size="sm"
            rightIcon={expanded ? SvgChevronUp : SvgChevronDown}
            aria-expanded={expanded}
            onClick={() => setToggled(!expanded)}
          >
            {expanded ? WORK.header.hide : WORK.header.show}
          </Button>
        )}
      </div>
      {busy && <div className="ton-work-progress" aria-hidden />}
      {expanded && (
        <ol className="ton-work-steps">
          {log.steps.map((step) => (
            <StepView
              key={step.id}
              step={step}
              log={log}
              canInspect={canInspect}
            />
          ))}
        </ol>
      )}
    </section>
  );
}
