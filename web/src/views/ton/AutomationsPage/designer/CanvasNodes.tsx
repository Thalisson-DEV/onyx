"use client";

import { createContext, useContext, type DragEvent } from "react";
import {
  BaseEdge,
  EdgeLabelRenderer,
  Handle,
  Position,
  getSmoothStepPath,
  getStraightPath,
  type EdgeProps,
  type NodeProps,
} from "@xyflow/react";
import {
  SvgAlertCircle,
  SvgCheck,
  SvgChevronDown,
  SvgChevronUp,
  SvgClock,
  SvgLoader,
  SvgMinus,
  SvgPlus,
  SvgX,
} from "@opal/icons";
import { cn } from "@opal/utils";
import {
  DESIGNER_COPY as D,
  type Definition,
  type NodeTypeView,
  type StepStatus,
} from "@/lib/ton/automations";
import { targetKey, type InsertTarget } from "@/lib/ton/automationTree";
import { nodeIcon } from "@/views/ton/AutomationsPage/designer/icons";
import type { CanvasNode, FlowEdgeData } from "@/views/ton/AutomationsPage/designer/layout";

export interface NodeRunState {
  status: StepStatus;
  durationMs: number | null;
  iterations: number;
  failedIterations: number;
}

export interface CanvasApi {
  specs: Map<string, NodeTypeView>;
  definition: Definition;
  selectedId: string | null;
  issues: Map<string, { errors: number; warnings: number }>;
  readOnly: boolean;
  run: Map<string, NodeRunState> | null;
  dragging: boolean;
  hoverKey: string | null;
  summary: (nodeId: string) => string;
  onSelect: (id: string) => void;
  onInsertAt: (target: InsertTarget) => void;
  onDropAt: (target: InsertTarget, payload: string) => void;
  onHover: (key: string | null) => void;
  onToggleCollapse: (id: string) => void;
}

export const CanvasContext = createContext<CanvasApi | null>(null);

function useCanvas(): CanvasApi {
  const value = useContext(CanvasContext);
  if (!value) throw new Error("CanvasContext missing");
  return value;
}

export function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "";
  if (ms < 1000) return `${Math.max(0, ms)} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0).replace(".", ",")} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ${Math.round(seconds % 60)} s`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

const STATUS_ICON: Partial<Record<StepStatus, typeof SvgCheck>> = {
  SUCCEEDED: SvgCheck,
  FAILED: SvgX,
  TIMED_OUT: SvgClock,
  WAITING: SvgClock,
  RUNNING: SvgLoader,
  SKIPPED: SvgMinus,
  CANCELLED: SvgX,
};

function RunBadge({ state }: { state: NodeRunState }) {
  const Icon = STATUS_ICON[state.status] ?? SvgMinus;
  const text = state.iterations > 1 ? `${state.iterations}×` : formatDuration(state.durationMs);
  return (
    <span className="ton-auto-run-badge" data-status={state.status}>
      {text && <span>{text}</span>}
      <span className="ton-auto-run-dot">
        <Icon size={12} />
      </span>
    </span>
  );
}

function dropProps(api: CanvasApi, target: InsertTarget) {
  const key = targetKey(target);
  return {
    onDragOver: (event: DragEvent) => {
      if (!event.dataTransfer.types.includes("application/ton-node")) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
      if (api.hoverKey !== key) api.onHover(key);
    },
    onDragLeave: () => api.hoverKey === key && api.onHover(null),
    onDrop: (event: DragEvent) => {
      event.preventDefault();
      const payload = event.dataTransfer.getData("application/ton-node");
      api.onHover(null);
      if (payload) api.onDropAt(target, payload);
    },
  };
}

export function StepNode({ id, data }: NodeProps<CanvasNode>) {
  const api = useCanvas();
  const isTrigger = data.kind === "trigger";
  const node = data.kind === "step" ? data.node : null;
  const type = isTrigger ? api.definition.trigger.type : node?.type ?? "";
  const spec = api.specs.get(type);
  const Icon = nodeIcon(spec?.icon);
  const title = isTrigger ? spec?.label ?? D.addTrigger : node?.label || spec?.label || type;
  const subtitle = api.summary(id);
  const issues = api.issues.get(id);
  const run = api.run?.get(id);
  const collapsed = data.kind === "step" && data.collapsed;
  const hasChildren = data.kind === "step" && !!spec?.container;
  return (
    <div
      className="ton-auto-node"
      data-group={isTrigger ? "trigger" : spec?.group ?? "control"}
      data-selected={api.selectedId === id || undefined}
      data-error={issues?.errors ? true : undefined}
      data-run={run?.status}
      data-unknown={!spec || undefined}
      onClick={() => api.onSelect(id)}
      role="button"
      tabIndex={0}
      aria-label={title}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") api.onSelect(id);
      }}
    >
      <Handle type="target" position={Position.Top} className="ton-auto-handle" isConnectable={false} />
      <span className="ton-auto-node-icon">
        <Icon size={18} />
      </span>
      <span className="ton-auto-node-text">
        <span className="ton-auto-node-title">{title}</span>
        {subtitle && <span className="ton-auto-node-sub">{subtitle}</span>}
        {collapsed && data.kind === "step" && <span className="ton-auto-node-sub ton-auto-node-count">{D.actions(data.childCount)}</span>}
      </span>
      <span className="ton-auto-node-badges">
        {spec?.ai && <span className="ton-auto-tag">{D.aiBadge}</span>}
        {issues && (issues.errors > 0 || issues.warnings > 0) && !run && (
          <span className="ton-auto-issue" data-severity={issues.errors ? "error" : "warning"} title={issues.errors ? D.errors(issues.errors) : D.warnings(issues.warnings)}>
            <SvgAlertCircle size={14} />
            {issues.errors || issues.warnings}
          </span>
        )}
        {hasChildren && (
          <span
            className="ton-auto-collapse"
            role="button"
            tabIndex={0}
            aria-label={collapsed ? D.expand : D.collapse}
            onClick={(event) => {
              event.stopPropagation();
              api.onToggleCollapse(id);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.stopPropagation();
                api.onToggleCollapse(id);
              }
            }}
          >
            {collapsed ? <SvgChevronDown size={14} /> : <SvgChevronUp size={14} />}
          </span>
        )}
      </span>
      {run && <RunBadge state={run} />}
      <Handle type="source" position={Position.Bottom} className="ton-auto-handle" isConnectable={false} />
    </div>
  );
}

export function FrameNode({ data }: NodeProps<CanvasNode>) {
  const api = useCanvas();
  if (data.kind !== "frame") return null;
  return <div className="ton-auto-frame" data-tone={data.tone} data-selected={api.selectedId === data.nodeId || undefined} style={{ width: data.width, height: data.height }} />;
}

export function LabelNode({ data }: NodeProps<CanvasNode>) {
  if (data.kind !== "label") return null;
  return (
    <div className="ton-auto-label" data-tone={data.tone}>
      <Handle type="target" position={Position.Top} className="ton-auto-handle" isConnectable={false} />
      <span>{data.text}</span>
      <Handle type="source" position={Position.Bottom} className="ton-auto-handle" isConnectable={false} />
    </div>
  );
}

export function SlotNode({ data }: NodeProps<CanvasNode>) {
  const api = useCanvas();
  if (data.kind !== "slot") return null;
  const key = targetKey(data.target);
  const small = data.inner && data.target.index > 0;
  if (api.readOnly) {
    return (
      <div className={cn("ton-auto-slot", small && "ton-auto-slot-round")} data-readonly>
        <Handle type="target" position={Position.Top} className="ton-auto-handle" isConnectable={false} />
        <Handle type="source" position={Position.Bottom} className="ton-auto-handle" isConnectable={false} />
      </div>
    );
  }
  return (
    <div
      className={cn("ton-auto-slot", small && "ton-auto-slot-round")}
      data-dragging={api.dragging || undefined}
      data-hover={api.hoverKey === key || undefined}
      role="button"
      tabIndex={0}
      aria-label={D.addAction}
      onClick={() => api.onInsertAt(data.target)}
      onKeyDown={(event) => event.key === "Enter" && api.onInsertAt(data.target)}
      {...dropProps(api, data.target)}
    >
      <Handle type="target" position={Position.Top} className="ton-auto-handle" isConnectable={false} />
      <SvgPlus size={small ? 14 : 16} />
      {!small && <span>{api.dragging ? D.dropHere : D.addAction}</span>}
      <Handle type="source" position={Position.Bottom} className="ton-auto-handle" isConnectable={false} />
    </div>
  );
}

export function PointNode() {
  return (
    <div className="ton-auto-point">
      <Handle type="target" position={Position.Top} className="ton-auto-handle" isConnectable={false} />
      <Handle type="source" position={Position.Bottom} className="ton-auto-handle" isConnectable={false} />
    </div>
  );
}

export function EndNode({ data }: NodeProps<CanvasNode>) {
  const api = useCanvas();
  if (data.kind !== "end" || api.readOnly) {
    return (
      <div className="ton-auto-point">
        <Handle type="target" position={Position.Top} className="ton-auto-handle" isConnectable={false} />
      </div>
    );
  }
  const key = targetKey(data.target);
  return (
    <div
      className="ton-auto-end"
      data-dragging={api.dragging || undefined}
      data-hover={api.hoverKey === key || undefined}
      role="button"
      tabIndex={0}
      onClick={() => api.onInsertAt(data.target)}
      onKeyDown={(event) => event.key === "Enter" && api.onInsertAt(data.target)}
      {...dropProps(api, data.target)}
    >
      <Handle type="target" position={Position.Top} className="ton-auto-handle" isConnectable={false} />
      <SvgPlus size={14} />
      <span>{api.dragging ? D.dropHere : D.addAction}</span>
    </div>
  );
}

export function FlowEdge({ sourceX, sourceY, targetX, targetY, data }: EdgeProps & { data?: FlowEdgeData }) {
  const api = useCanvas();
  const bend = data?.bend || Math.abs(sourceX - targetX) > 1;
  const [path, labelX, labelY] = bend
    ? getSmoothStepPath({ sourceX, sourceY, targetX, targetY, borderRadius: 14, offset: 18, sourcePosition: Position.Bottom, targetPosition: Position.Top })
    : getStraightPath({ sourceX, sourceY, targetX, targetY });
  const target = data?.target;
  const key = target ? targetKey(target) : null;
  const plusX = bend ? sourceX : labelX;
  const plusY = bend ? sourceY + 22 : labelY;
  return (
    <>
      <BaseEdge path={path} className="ton-auto-edge" markerEnd="url(#ton-auto-arrow)" />
      {target && !api.readOnly && (
        <EdgeLabelRenderer>
          <div
            className="ton-auto-insert nodrag nopan"
            data-dragging={api.dragging || undefined}
            data-hover={api.hoverKey === key || undefined}
            style={{ transform: `translate(-50%, -50%) translate(${plusX}px, ${plusY}px)` }}
            role="button"
            tabIndex={0}
            aria-label={D.addHere}
            title={D.addHere}
            onClick={() => api.onInsertAt(target)}
            onKeyDown={(event) => event.key === "Enter" && api.onInsertAt(target)}
            {...dropProps(api, target)}
          >
            <SvgPlus size={12} />
            {api.dragging && <span>{D.dropHere}</span>}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const NODE_TYPES = {
  step: StepNode,
  frame: FrameNode,
  label: LabelNode,
  slot: SlotNode,
  point: PointNode,
  end: EndNode,
};

export const EDGE_TYPES = { flow: FlowEdge };
