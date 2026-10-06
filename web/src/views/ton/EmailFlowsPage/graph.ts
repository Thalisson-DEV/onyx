import type { Edge, Node } from "@xyflow/react";
import type { FlowDefinition, ListPath, Step } from "@/lib/ton/emailFlows";

export const NODE_WIDTH = 300;
export const NODE_HEIGHT = 84;
const GAP_Y = 64;
const GAP_X = 56;
const MERGE_SIZE = 12;

/** Where a "+" on an edge inserts a new step. */
export interface InsertTarget {
  path: ListPath;
  index: number;
}

/** Address of a step: its list and position. */
export interface StepAddress {
  path: ListPath;
  index: number;
}

export type FlowNodeData =
  | { kind: "trigger" }
  | { kind: "step"; step: Step; address: StepAddress }
  | { kind: "merge" }
  | { kind: "end" };

export interface InsertEdgeData extends Record<string, unknown> {
  target: InsertTarget;
  label?: string;
  tone?: "yes" | "no" | "loop";
}

export type FlowNode = Node<FlowNodeData & Record<string, unknown>>;
export type FlowEdge = Edge<InsertEdgeData>;

interface Graph {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

function listWidth(steps: Step[]): number {
  return steps.reduce((width, step) => Math.max(width, stepWidth(step)), NODE_WIDTH);
}

function stepWidth(step: Step): number {
  if (step.type === "condition") {
    return Math.max(NODE_WIDTH, listWidth(step.then) + GAP_X + listWidth(step.else));
  }
  if (step.type === "for_each_unit") return listWidth(step.steps) + 48;
  return NODE_WIDTH;
}

class Builder {
  nodes: FlowNode[] = [];
  edges: FlowEdge[] = [];

  edge(source: string, target: string, insert: InsertTarget, label?: string, tone?: InsertEdgeData["tone"]): void {
    this.edges.push({
      id: `e-${source}-${target}-${insert.path.join(".")}-${insert.index}`,
      source,
      target,
      type: "insert",
      data: { target: insert, label, tone },
    });
  }

  node(id: string, data: FlowNodeData, x: number, y: number, type: string, width = NODE_WIDTH): void {
    this.nodes.push({
      id,
      type,
      position: { x: x - width / 2, y },
      data: { ...data },
      draggable: false,
      connectable: false,
    });
  }

  /** Lays out a list of steps from ``entry``; returns its exit node and the
   * y below it. ``firstLabel`` labels the first edge (Sim / Não). */
  list(
    steps: Step[],
    path: ListPath,
    cx: number,
    y: number,
    entry: string,
    firstLabel?: { label: string; tone: InsertEdgeData["tone"] }
  ): { exit: string; y: number; pendingLabel?: { label: string; tone: InsertEdgeData["tone"] } } {
    let current = entry;
    let label = firstLabel;
    steps.forEach((step, index) => {
      const id = `s-${step.id}`;
      this.node(id, { kind: "step", step, address: { path, index } }, cx, y, "step");
      this.edge(current, id, { path, index }, label?.label, label?.tone);
      label = undefined;
      y += NODE_HEIGHT + GAP_Y;
      if (step.type === "condition") {
        const thenWidth = listWidth(step.then);
        const elseWidth = listWidth(step.else);
        const total = thenWidth + GAP_X + elseWidth;
        const left = cx - total / 2;
        const thenCx = left + thenWidth / 2;
        const elseCx = left + thenWidth + GAP_X + elseWidth / 2;
        const thenPath: ListPath = [...path, index, "then"];
        const elsePath: ListPath = [...path, index, "else"];
        const yes = this.list(step.then, thenPath, thenCx, y, id, { label: "Sim", tone: "yes" });
        const no = this.list(step.else, elsePath, elseCx, y, id, { label: "Não", tone: "no" });
        const mergeY = Math.max(yes.y, no.y) - GAP_Y / 2;
        const merge = `m-${step.id}`;
        this.node(merge, { kind: "merge" }, cx, mergeY, "merge", MERGE_SIZE);
        this.edge(yes.exit, merge, { path: thenPath, index: step.then.length }, yes.pendingLabel?.label, yes.pendingLabel?.tone);
        this.edge(no.exit, merge, { path: elsePath, index: step.else.length }, no.pendingLabel?.label, no.pendingLabel?.tone);
        current = merge;
        y = mergeY + MERGE_SIZE + GAP_Y;
        return;
      }
      if (step.type === "for_each_unit") {
        const innerPath: ListPath = [...path, index, "steps"];
        const inner = this.list(step.steps, innerPath, cx, y, id, { label: "cada unidade", tone: "loop" });
        const mergeY = inner.y - GAP_Y / 2;
        const merge = `m-${step.id}`;
        this.node(merge, { kind: "merge" }, cx, mergeY, "merge", MERGE_SIZE);
        this.edge(inner.exit, merge, { path: innerPath, index: step.steps.length }, inner.pendingLabel?.label, inner.pendingLabel?.tone);
        current = merge;
        y = mergeY + MERGE_SIZE + GAP_Y;
        return;
      }
      current = id;
    });
    return { exit: current, y, pendingLabel: label };
  }
}

export function buildGraph(definition: FlowDefinition): Graph {
  const builder = new Builder();
  const width = listWidth(definition.steps);
  const cx = width / 2;
  builder.node("trigger", { kind: "trigger" }, cx, 0, "trigger");
  const result = builder.list(definition.steps, [], cx, NODE_HEIGHT + GAP_Y, "trigger");
  builder.node("end", { kind: "end" }, cx, result.y, "end", 120);
  builder.edge(result.exit, "end", { path: [], index: definition.steps.length });
  return { nodes: builder.nodes, edges: builder.edges };
}
