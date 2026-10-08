import type { Edge, Node } from "@xyflow/react";
import type { Definition, FlowNode } from "@/lib/ton/automations";
import { childLists, countNodes, type InsertTarget, type ListRef, type Slot } from "@/lib/ton/automationTree";

export const CARD_W = 320;
export const CARD_H = 68;
const GAP = 76;
const PAD = 32;
const COL_GAP = 64;
const LABEL_H = 26;
const LABEL_GAP = 32;
const SLOT_H = 48;
const COLLAPSED_EXTRA = 26;
const FRAME_TOP = 0;
const BRANCH_CONTAINERS = new Set(["control.condition", "control.switch", "control.parallel"]);
const FRAME_CONTAINERS = new Set(["control.foreach", "control.until", "control.scope"]);

export type CanvasNodeData =
  | { kind: "trigger" }
  | { kind: "step"; node: FlowNode; ref: ListRef; index: number; collapsed: boolean; childCount: number }
  | { kind: "frame"; nodeId: string; width: number; height: number; tone: "branch" | "loop" }
  | { kind: "label"; text: string; tone: "yes" | "no" | "case" | "default" | "branch"; nodeId: string; slot: Slot }
  | { kind: "slot"; target: InsertTarget; inner: boolean }
  | { kind: "point" }
  | { kind: "end"; target: InsertTarget };

export interface FlowEdgeData extends Record<string, unknown> {
  target?: InsertTarget;
  bend?: boolean;
}

export type CanvasNode = Node<CanvasNodeData & Record<string, unknown>>;
export type CanvasEdge = Edge<FlowEdgeData>;

export interface Layout {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  /** Insert targets with their canvas point (for dropping dragged nodes). */
  targets: { target: InsertTarget; x: number; y: number }[];
}

interface Box {
  w: number;
  h: number;
}

export interface LabelFor {
  yes: string;
  no: string;
  otherwise: string;
}

function isBranch(node: FlowNode): boolean {
  return BRANCH_CONTAINERS.has(node.type);
}

function isFrame(node: FlowNode): boolean {
  return FRAME_CONTAINERS.has(node.type);
}

export function columnsOf(node: FlowNode, labels: LabelFor): { slot: Slot; list: FlowNode[]; text: string; tone: "yes" | "no" | "case" | "default" | "branch" }[] {
  if (node.type === "control.condition") {
    return [
      { slot: "then", list: node.then ?? [], text: labels.yes, tone: "yes" },
      { slot: "else", list: node.else ?? [], text: labels.no, tone: "no" },
    ];
  }
  if (node.type === "control.switch") {
    return [
      ...(node.cases ?? []).map((item) => ({ slot: `case:${item.id}` as Slot, list: item.steps, text: item.value || "…", tone: "case" as const })),
      { slot: "default", list: node.default ?? [], text: labels.otherwise, tone: "default" },
    ];
  }
  return (node.branches ?? []).map((branch) => ({ slot: `branch:${branch.id}` as Slot, list: branch.steps, text: branch.label || "Ramo", tone: "branch" }));
}

class Builder {
  nodes: CanvasNode[] = [];
  edges: CanvasEdge[] = [];
  targets: Layout["targets"] = [];
  /** Offset of the node being placed (its own plus its ancestors'). */
  private shift = { x: 0, y: 0 };
  constructor(
    private collapsed: Set<string>,
    private labels: LabelFor,
    private offsets: Record<string, { x: number; y: number }>
  ) {}

  add(node: CanvasNode): void {
    this.nodes.push({ ...node, position: { x: node.position.x + this.shift.x, y: node.position.y + this.shift.y } });
  }

  measureList(list: FlowNode[]): Box {
    if (!list.length) return { w: CARD_W, h: SLOT_H };
    let w = CARD_W;
    let h = 0;
    list.forEach((node, index) => {
      const box = this.measure(node);
      w = Math.max(w, box.w);
      h += box.h + (index ? GAP : 0);
    });
    return { w, h };
  }

  measure(node: FlowNode): Box {
    if (this.collapsed.has(node.id) && childLists(node).length) return { w: CARD_W, h: CARD_H + COLLAPSED_EXTRA };
    if (isFrame(node)) {
      const inner = this.measureList(node.steps ?? []);
      return { w: Math.max(CARD_W, inner.w) + PAD * 2, h: FRAME_TOP + CARD_H + GAP + inner.h + GAP / 2 + PAD };
    }
    if (isBranch(node)) {
      const columns = columnsOf(node, this.labels).map((column) => this.measureList(column.list));
      const width = columns.reduce((sum, box) => sum + box.w, 0) + COL_GAP * Math.max(0, columns.length - 1);
      const height = Math.max(SLOT_H, ...columns.map((box) => box.h));
      return { w: Math.max(CARD_W, width) + PAD * 2, h: CARD_H + GAP + LABEL_H + LABEL_GAP + height + GAP };
    }
    return { w: CARD_W, h: CARD_H };
  }

  edge(source: string, target: string, data: FlowEdgeData = {}): void {
    this.edges.push({ id: `e:${source}->${target}`, source, target, type: "flow", data, selectable: false, focusable: false });
  }

  point(id: string, x: number, y: number): void {
    this.add({ id, type: "point", position: { x: x - 1, y: y - 1 }, data: { kind: "point" }, draggable: false, selectable: false, width: 2, height: 2 });
  }

  addTarget(target: InsertTarget, x: number, y: number): void {
    this.targets.push({ target, x: x + this.shift.x, y: y + this.shift.y });
  }

  /** Place a list centered on cx from y. Returns the id of its last exit. */
  placeList(list: FlowNode[], ref: ListRef, cx: number, y: number, source: string, inner: boolean): { exit: string; bottom: number } {
    if (!list.length) {
      const id = `slot:${ref.parentId ?? "root"}:${ref.slot}`;
      const target = { ...ref, index: 0 };
      this.add({ id, type: "slot", position: { x: cx - CARD_W / 2, y }, data: { kind: "slot", target, inner }, draggable: false, selectable: false, width: CARD_W, height: SLOT_H });
      this.edge(source, id);
      this.addTarget(target, cx, y + SLOT_H / 2);
      return { exit: id, bottom: y + SLOT_H };
    }
    let previous = source;
    let top = y;
    list.forEach((node, index) => {
      const placed = this.place(node, ref, index, cx, top);
      const target = { ...ref, index };
      this.edge(previous, placed.entry, { target });
      this.addTarget(target, cx, top - GAP / 2);
      previous = placed.exit;
      top = placed.bottom + GAP;
    });
    return { exit: previous, bottom: top - GAP };
  }

  place(node: FlowNode, ref: ListRef, index: number, cx: number, y: number): { entry: string; exit: string; bottom: number } {
    const parent = this.shift;
    const own = this.offsets[node.id];
    if (own) this.shift = { x: parent.x + own.x, y: parent.y + own.y };
    try {
      return this.placeShifted(node, ref, index, cx, y);
    } finally {
      this.shift = parent;
    }
  }

  placeShifted(node: FlowNode, ref: ListRef, index: number, cx: number, y: number): { entry: string; exit: string; bottom: number } {
    const box = this.measure(node);
    const lists = childLists(node);
    const collapsed = this.collapsed.has(node.id) && lists.length > 0;
    const card: CanvasNode = {
      id: node.id,
      type: "step",
      position: { x: cx - CARD_W / 2, y },
      data: { kind: "step", node, ref, index, collapsed, childCount: lists.reduce((sum, [, list]) => sum + countNodes(list), 0) },
      width: CARD_W,
      height: collapsed ? CARD_H + COLLAPSED_EXTRA : CARD_H,
      zIndex: 2,
    };
    if (collapsed || (!isFrame(node) && !isBranch(node))) {
      this.add(card);
      return { entry: node.id, exit: node.id, bottom: y + box.h };
    }
    const left = cx - box.w / 2;
    this.add({
      id: `frame:${node.id}`,
      type: "frame",
      position: { x: left, y: y + CARD_H / 2 },
      data: { kind: "frame", nodeId: node.id, width: box.w, height: box.h - CARD_H / 2, tone: isBranch(node) ? "branch" : "loop" },
      draggable: false,
      selectable: false,
      width: box.w,
      height: box.h - CARD_H / 2,
      zIndex: 0,
    });
    this.add(card);
    const exitId = `exit:${node.id}`;
    this.point(exitId, cx, y + box.h);
    if (isFrame(node)) {
      const innerRef: ListRef = { parentId: node.id, slot: "steps" };
      const placed = this.placeList(node.steps ?? [], innerRef, cx, y + CARD_H + GAP, node.id, true);
      if ((node.steps ?? []).length) {
        const endId = `slot:${node.id}:end`;
        const target = { ...innerRef, index: (node.steps ?? []).length };
        const endY = placed.bottom + GAP / 2 - 14;
        this.add({ id: endId, type: "slot", position: { x: cx - 14, y: endY }, data: { kind: "slot", target, inner: true }, draggable: false, selectable: false, width: 28, height: 28 });
        this.edge(placed.exit, endId);
        this.addTarget(target, cx, endY + 14);
      }
      return { entry: node.id, exit: exitId, bottom: y + box.h };
    }
    const columns = columnsOf(node, this.labels);
    const boxes = columns.map((column) => this.measureList(column.list));
    const total = boxes.reduce((sum, b) => sum + b.w, 0) + COL_GAP * Math.max(0, columns.length - 1);
    let x = cx - total / 2;
    const labelY = y + CARD_H + GAP;
    const mergeY = y + box.h - GAP / 2;
    const mergeId = `merge:${node.id}`;
    this.point(mergeId, cx, mergeY);
    columns.forEach((column, position) => {
      const columnBox = boxes[position]!;
      const colCx = x + columnBox.w / 2;
      const labelId = `label:${node.id}:${column.slot}`;
      this.add({
        id: labelId,
        type: "label",
        position: { x: colCx - 60, y: labelY },
        data: { kind: "label", text: column.text, tone: column.tone, nodeId: node.id, slot: column.slot },
        draggable: false,
        selectable: false,
        width: 120,
        height: LABEL_H,
        zIndex: 2,
      });
      this.edge(node.id, labelId, { bend: true });
      const listRef: ListRef = { parentId: node.id, slot: column.slot };
      const placed = this.placeList(column.list, listRef, colCx, labelY + LABEL_H + LABEL_GAP, labelId, true);
      const endTarget = { ...listRef, index: column.list.length };
      if (column.list.length) {
        this.edge(placed.exit, mergeId, { target: endTarget, bend: true });
        this.addTarget(endTarget, colCx, placed.bottom + GAP / 2);
      } else {
        this.edge(placed.exit, mergeId, { bend: true });
      }
      x += columnBox.w + COL_GAP;
    });
    this.edge(mergeId, exitId);
    return { entry: node.id, exit: exitId, bottom: y + box.h };
  }
}

export function buildLayout(definition: Definition, collapsed: Set<string>, labels: LabelFor): Layout {
  const offsets = definition.layout ?? {};
  const builder = new Builder(collapsed, labels, offsets);
  const cx = 0;
  const moved = offsets.trigger ?? { x: 0, y: 0 };
  builder.nodes.push({
    id: "trigger",
    type: "step",
    position: { x: cx - CARD_W / 2 + moved.x, y: moved.y },
    data: { kind: "trigger" },
    width: CARD_W,
    height: CARD_H,
    zIndex: 2,
  });
  const placed = builder.placeList(definition.steps, { parentId: null, slot: "steps" }, cx, CARD_H + GAP, "trigger", false);
  if (definition.steps.length) {
    const target: InsertTarget = { parentId: null, slot: "steps", index: definition.steps.length };
    const endY = placed.bottom + GAP;
    builder.nodes.push({ id: "end", type: "end", position: { x: cx - 100, y: endY }, data: { kind: "end", target }, draggable: false, selectable: false, width: 200, height: 44 });
    builder.edge(placed.exit, "end", { target });
    builder.addTarget(target, cx, placed.bottom + GAP / 2);
  }
  return { nodes: builder.nodes, edges: builder.edges, targets: builder.targets };
}
