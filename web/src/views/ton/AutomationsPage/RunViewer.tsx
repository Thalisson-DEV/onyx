"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, Modal, Text } from "@opal/components";
import { SvgArrowLeft, SvgEdit, SvgMail, SvgRefreshCw, SvgUserCheck, SvgX } from "@opal/icons";
import {
  AUTOMATIONS_API,
  MODE_LABELS,
  RUN_COPY as R,
  RUN_STATUS_LABELS,
  STEP_STATUS_LABELS,
  send,
  useAutomationCatalog,
  useRun,
  type ApprovalView,
  type JsonValue,
  type NodeTypeView,
  type RunDetail,
  type RunSummary,
  type StepStatus,
  type StepView,
} from "@/lib/ton/automations";
import { findNode } from "@/lib/ton/automationTree";
import { formatDateTime } from "@/lib/ton/copy";
import { ErrorState, LoadingBlock } from "@/views/ton/components/ui";
import ApprovalModal from "@/views/ton/AutomationsPage/ApprovalModal";
import Canvas from "@/views/ton/AutomationsPage/designer/Canvas";
import { formatDuration, type NodeRunState } from "@/views/ton/AutomationsPage/designer/CanvasNodes";
import { specMap } from "@/views/ton/AutomationsPage/designer/dynamic";
import { nodeIcon } from "@/views/ton/AutomationsPage/designer/icons";
import { nodeSummary } from "@/views/ton/AutomationsPage/designer/summary";

const PRIORITY: StepStatus[] = ["RUNNING", "WAITING", "FAILED", "TIMED_OUT", "CANCELLED", "SUCCEEDED", "SKIPPED"];

function aggregate(steps: StepView[]): Map<string, NodeRunState> {
  const map = new Map<string, NodeRunState>();
  for (const step of steps) {
    const current = map.get(step.node_id);
    if (!current) {
      map.set(step.node_id, { status: step.status, durationMs: step.duration_ms, iterations: 1, failedIterations: step.status === "FAILED" ? 1 : 0 });
      continue;
    }
    current.iterations += 1;
    if (step.status === "FAILED") current.failedIterations += 1;
    if (PRIORITY.indexOf(step.status) < PRIORITY.indexOf(current.status)) current.status = step.status;
    current.durationMs = (current.durationMs ?? 0) + (step.duration_ms ?? 0);
  }
  return map;
}

function JsonBlock({ value }: { value: JsonValue | Record<string, JsonValue> | null | undefined }) {
  const text = JSON.stringify(value ?? null, null, 2);
  return <pre className="ton-auto-json">{text.length > 60_000 ? `${text.slice(0, 60_000)}\n…` : text}</pre>;
}

function bannerTone(run: RunSummary): string {
  if (run.status === "SUCCEEDED") return "success";
  if (run.status === "FAILED" || run.status === "TIMED_OUT") return "error";
  if (run.status === "CANCELLED") return "neutral";
  return "info";
}

function bannerText(run: RunSummary): string {
  switch (run.status) {
    case "SUCCEEDED":
      return R.succeeded;
    case "FAILED":
      return `${R.failed}${run.error ? ` ${run.error}` : ""}`;
    case "TIMED_OUT":
      return R.timedOut;
    case "CANCELLED":
      return run.message ?? R.cancelled;
    case "WAITING":
      return `${run.message ?? R.waiting}${run.resume_at ? ` · ${formatDateTime(run.resume_at)}` : ""}`;
    case "QUEUED":
      return R.queued;
    default:
      return R.running;
  }
}

interface StepPanelProps {
  run: RunDetail;
  nodeId: string;
  spec: NodeTypeView | undefined;
  onClose: () => void;
  onOpenEmail: (step: StepView) => void;
  onApprove: (approval: ApprovalView) => void;
}

function StepPanel({ run, nodeId, spec, onClose, onOpenEmail, onApprove }: StepPanelProps) {
  const steps = run.steps.filter((step) => step.node_id === nodeId);
  const [index, setIndex] = useState(Math.max(0, steps.length - 1));
  const step = steps[Math.min(index, steps.length - 1)];
  const Icon = nodeIcon(spec?.icon);
  const node = nodeId === "trigger" ? null : findNode(run.definition, nodeId);
  const approval = run.approvals.find((item) => item.node_id === nodeId && item.status === "PENDING");
  return (
    <aside className="ton-auto-panel" data-group={nodeId === "trigger" ? "trigger" : spec?.group}>
      <header className="ton-auto-panel-head">
        <span className="ton-auto-node-icon">
          <Icon size={18} />
        </span>
        <div className="flex min-w-0 flex-1 flex-col">
          <Text font="main-ui-action" color="text-05">
            {node?.label || spec?.label || nodeId}
          </Text>
          <Text font="secondary-body" color="text-03">
            {step ? `${STEP_STATUS_LABELS[step.status]}${step.duration_ms !== null ? ` · ${formatDuration(step.duration_ms)}` : ""}${step.attempt > 1 ? ` · ${R.attempts(step.attempt)}` : ""}` : nodeId === "trigger" ? RUN_STATUS_LABELS.SUCCEEDED : R.notRun}
          </Text>
        </div>
        <Button size="sm" prominence="tertiary" icon={SvgX} aria-label={R.cancel} onClick={onClose} />
      </header>
      <div className="ton-auto-panel-body">
        {steps.length > 1 && (
          <div className="ton-auto-iterations" role="group" aria-label={R.iteration}>
            <Text font="secondary-action" color="text-04">
              {R.iteration}
            </Text>
            <div className="ton-auto-weekdays">
              {steps.map((item, position) => (
                <button key={item.iteration} type="button" className="ton-auto-weekday ton-focusable" data-active={position === index || undefined} data-status={item.status} onClick={() => setIndex(position)}>
                  {position + 1}
                </button>
              ))}
            </div>
          </div>
        )}
        {approval && (
          <Button icon={SvgUserCheck} onClick={() => onApprove(approval)}>
            {R.answer}
          </Button>
        )}
        {nodeId === "trigger" ? (
          <>
            <Text font="secondary-action" color="text-04">
              {R.triggerOutput}
            </Text>
            <JsonBlock value={run.trigger_output} />
          </>
        ) : !step ? (
          <Text font="secondary-body" color="text-03">
            {R.notRun}
          </Text>
        ) : (
          <>
            {step.error && (
              <div className="ton-auto-banner" data-tone="error">
                <Text font="secondary-body" color="text-05">
                  {step.error}
                </Text>
              </div>
            )}
            {node?.type === "email.send" && step.outputs && typeof step.outputs.html === "string" && (
              <Button prominence="secondary" icon={SvgMail} onClick={() => onOpenEmail(step)}>
                {R.openEmail}
              </Button>
            )}
            <Text font="secondary-action" color="text-04">
              {R.inputs}
            </Text>
            <JsonBlock value={step.inputs} />
            <Text font="secondary-action" color="text-04">
              {R.outputs}
            </Text>
            <JsonBlock value={step.outputs ? Object.fromEntries(Object.entries(step.outputs).filter(([key]) => key !== "html")) : null} />
          </>
        )}
      </div>
    </aside>
  );
}

export default function RunViewer({ automationId, runId }: { automationId: string; runId: string }) {
  const router = useRouter();
  const run = useRun(runId);
  const catalog = useAutomationCatalog();
  const [selected, setSelected] = useState<string | null>(null);
  const [email, setEmail] = useState<StepView | null>(null);
  const [approval, setApproval] = useState<ApprovalView | null>(null);
  const [busy, setBusy] = useState(false);
  const specs = useMemo(() => (catalog.data ? specMap(catalog.data) : new Map<string, NodeTypeView>()), [catalog.data]);
  const states = useMemo(() => {
    const map = aggregate(run.data?.steps ?? []);
    if (run.data) map.set("trigger", { status: "SUCCEEDED", durationMs: null, iterations: 1, failedIterations: 0 });
    return map;
  }, [run.data]);

  if (run.error || catalog.error) return <ErrorState onRetry={() => void run.mutate()} />;
  if (!run.data || !catalog.data) return <LoadingBlock label="…" />;
  const data = run.data;
  const catalogData = catalog.data;

  async function act(action: "resubmit" | "cancel") {
    setBusy(true);
    try {
      const result = await send<RunSummary>(`${AUTOMATIONS_API}/runs/${runId}/${action}`, {});
      if (action === "resubmit") router.push(`/ton/automacoes/${automationId}/execucoes/${result.id}` as Route);
      else await run.mutate();
    } finally {
      setBusy(false);
    }
  }

  const summary = (id: string) =>
    id === "trigger"
      ? nodeSummary(null, specs.get(data.definition.trigger.type), data.definition, catalogData)
      : nodeSummary(findNode(data.definition, id) ?? null, specs.get(findNode(data.definition, id)?.type ?? ""), data.definition, catalogData);

  return (
    <div className="ton-auto-designer">
      <header className="ton-auto-topbar">
        <Button size="sm" prominence="tertiary" icon={SvgArrowLeft} href={`/ton/automacoes/${automationId}`}>
          {data.automation_name}
        </Button>
        <Text font="secondary-body" color="text-03">
          {`${formatDateTime(data.created_at)} · ${MODE_LABELS[data.mode]}${data.version ? ` · v${data.version}` : ""}${data.duration_ms !== null ? ` · ${formatDuration(data.duration_ms)}` : ""}`}
        </Text>
        <span className="flex-1" />
        {data.can_cancel && (
          <Button size="sm" prominence="tertiary" icon={SvgX} disabled={busy} onClick={() => void act("cancel")}>
            {R.cancel}
          </Button>
        )}
        {data.can_resubmit && (
          <Button size="sm" prominence="secondary" icon={SvgRefreshCw} disabled={busy} onClick={() => void act("resubmit")}>
            {R.resubmit}
          </Button>
        )}
        <Button size="sm" prominence="tertiary" icon={SvgEdit} href={`/ton/automacoes/${automationId}/editar`}>
          {R.edit}
        </Button>
      </header>
      <div className="ton-auto-banner" data-tone={bannerTone(data)}>
        <Text font="secondary-action" color="text-05">
          {bannerText(data)}
        </Text>
        {data.approvals
          .filter((item) => item.status === "PENDING")
          .map((item) => (
            <Button key={item.id} size="sm" prominence="secondary" icon={SvgUserCheck} onClick={() => setApproval(item)}>
              {`${R.answer}: ${item.title}`}
            </Button>
          ))}
      </div>
      <div className="ton-auto-workspace">
        <Canvas
          definition={data.definition}
          specs={specs}
          selectedId={selected}
          issues={new Map()}
          readOnly
          run={states}
          summary={summary}
          onSelect={setSelected}
          onInsertAt={() => undefined}
          onDropNew={() => undefined}
          onMove={() => undefined}
        />
        {selected && (
          <StepPanel
            key={selected}
            run={data}
            nodeId={selected}
            spec={specs.get(selected === "trigger" ? data.definition.trigger.type : findNode(data.definition, selected)?.type ?? "")}
            onClose={() => setSelected(null)}
            onOpenEmail={setEmail}
            onApprove={setApproval}
          />
        )}
      </div>
      <Modal open={email !== null} onOpenChange={(value) => !value && setEmail(null)}>
        <Modal.Content width="lg" height="lg">
          <Modal.Header icon={SvgMail} title={email?.outputs && typeof email.outputs.subject === "string" ? email.outputs.subject : R.openEmail} onClose={() => setEmail(null)} />
          <Modal.Body>
            {email && (
              <iframe
                title={R.openEmail}
                src={`${AUTOMATIONS_API}/runs/${runId}/steps/${email.node_id}/email?iteration=${encodeURIComponent(email.iteration)}`}
                sandbox="allow-same-origin"
                className="ton-flow-preview"
              />
            )}
          </Modal.Body>
        </Modal.Content>
      </Modal>
      <ApprovalModal approval={approval} onClose={() => setApproval(null)} onDecided={() => void run.mutate()} />
    </div>
  );
}
