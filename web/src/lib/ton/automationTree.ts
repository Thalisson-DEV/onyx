import type {
  Branch,
  Case,
  Definition,
  FlowNode,
  JsonValue,
  NodeTypeView,
  Params,
} from "@/lib/ton/automations";

/** A child list: the main list (parentId null) or a slot of a container. */
export type Slot = "steps" | "then" | "else" | "default" | `case:${string}` | `branch:${string}`;

export interface ListRef {
  parentId: string | null;
  slot: Slot;
}

export interface InsertTarget extends ListRef {
  index: number;
}

export const ROOT: ListRef = { parentId: null, slot: "steps" };

export function sameRef(a: ListRef, b: ListRef): boolean {
  return a.parentId === b.parentId && a.slot === b.slot;
}

export function targetKey(target: InsertTarget): string {
  return `${target.parentId ?? "root"}:${target.slot}:${target.index}`;
}

/** Child lists of a node, in display order. */
export function childLists(node: FlowNode): [Slot, FlowNode[]][] {
  const lists: [Slot, FlowNode[]][] = [];
  if (node.then) lists.push(["then", node.then]);
  if (node.else) lists.push(["else", node.else]);
  for (const item of node.cases ?? []) lists.push([`case:${item.id}`, item.steps]);
  if (node.default) lists.push(["default", node.default]);
  if (node.steps) lists.push(["steps", node.steps]);
  for (const branch of node.branches ?? []) lists.push([`branch:${branch.id}`, branch.steps]);
  return lists;
}

function listOf(node: FlowNode, slot: Slot): FlowNode[] | undefined {
  return childLists(node).find(([key]) => key === slot)?.[1];
}

function withList(node: FlowNode, slot: Slot, list: FlowNode[]): FlowNode {
  if (slot === "then" || slot === "else" || slot === "default" || slot === "steps") return { ...node, [slot]: list };
  if (slot.startsWith("case:")) {
    const id = slot.slice(5);
    return { ...node, cases: (node.cases ?? []).map((item: Case) => (item.id === id ? { ...item, steps: list } : item)) };
  }
  const id = slot.slice(7);
  return { ...node, branches: (node.branches ?? []).map((item: Branch) => (item.id === id ? { ...item, steps: list } : item)) };
}

export function* walk(nodes: FlowNode[]): Generator<FlowNode> {
  for (const node of nodes) {
    yield node;
    for (const [, list] of childLists(node)) yield* walk(list);
  }
}

export function allIds(definition: Definition): Set<string> {
  const ids = new Set<string>(["trigger"]);
  for (const node of walk(definition.steps)) ids.add(node.id);
  return ids;
}

export function findNode(definition: Definition, id: string): FlowNode | undefined {
  for (const node of walk(definition.steps)) if (node.id === id) return node;
  return undefined;
}

export interface Located {
  node: FlowNode;
  ref: ListRef;
  index: number;
}

export function locate(definition: Definition, id: string): Located | undefined {
  function search(nodes: FlowNode[], ref: ListRef): Located | undefined {
    for (let index = 0; index < nodes.length; index += 1) {
      const node = nodes[index]!;
      if (node.id === id) return { node, ref, index };
      for (const [slot, list] of childLists(node)) {
        const found = search(list, { parentId: node.id, slot });
        if (found) return found;
      }
    }
    return undefined;
  }
  return search(definition.steps, ROOT);
}

export function getList(definition: Definition, ref: ListRef): FlowNode[] | undefined {
  if (ref.parentId === null) return definition.steps;
  const parent = findNode(definition, ref.parentId);
  return parent ? listOf(parent, ref.slot) : undefined;
}

function mapNodes(nodes: FlowNode[], fn: (node: FlowNode) => FlowNode): FlowNode[] {
  return nodes.map((node) => {
    let next = fn(node);
    for (const [slot, list] of childLists(next)) next = withList(next, slot, mapNodes(list, fn));
    return next;
  });
}

export function updateNode(definition: Definition, id: string, fn: (node: FlowNode) => FlowNode): Definition {
  return { ...definition, steps: mapNodes(definition.steps, (node) => (node.id === id ? fn(node) : node)) };
}

function updateList(definition: Definition, ref: ListRef, fn: (list: FlowNode[]) => FlowNode[]): Definition {
  if (ref.parentId === null) return { ...definition, steps: fn(definition.steps) };
  return updateNode(definition, ref.parentId, (node) => withList(node, ref.slot, fn(listOf(node, ref.slot) ?? [])));
}

export function insertNode(definition: Definition, target: InsertTarget, node: FlowNode): Definition {
  return updateList(definition, target, (list) => [...list.slice(0, target.index), node, ...list.slice(target.index)]);
}

export function removeNode(definition: Definition, id: string): Definition {
  const found = locate(definition, id);
  if (!found) return definition;
  return updateList(definition, found.ref, (list) => list.filter((node) => node.id !== id));
}

export function contains(node: FlowNode, id: string): boolean {
  for (const inner of walk([node])) if (inner.id === id) return true;
  return false;
}

/** Move a node (with its children) to a slot. A move into itself is ignored. */
export function moveNode(definition: Definition, id: string, target: InsertTarget): Definition {
  const found = locate(definition, id);
  if (!found) return definition;
  if (target.parentId !== null && contains(found.node, target.parentId)) return definition;
  let index = target.index;
  if (sameRef(found.ref, target)) {
    if (index === found.index || index === found.index + 1) return definition;
    if (index > found.index) index -= 1;
  }
  return insertNode(removeNode(definition, id), { ...target, index }, found.node);
}

export function slug(text: string): string {
  const base = text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 34);
  if (!base) return "passo";
  return /^[a-z]/.test(base) ? base : `p_${base}`.slice(0, 34);
}

export function uniqueId(base: string, taken: Set<string>): string {
  const root = slug(base);
  let candidate = root;
  let index = 2;
  while (taken.has(candidate)) {
    candidate = `${root}_${index}`;
    index += 1;
  }
  taken.add(candidate);
  return candidate;
}

function defaults(spec: NodeTypeView): Params {
  const params: Params = {};
  for (const param of spec.params) {
    if (param.default !== null && param.default !== undefined) params[param.key] = structuredClone(param.default);
  }
  return params;
}

export function newNode(spec: NodeTypeView, taken: Set<string>): FlowNode {
  const node: FlowNode = { id: uniqueId(spec.label, taken), type: spec.type, label: spec.label, params: defaults(spec) };
  switch (spec.container) {
    case "condition":
      return { ...node, then: [], else: [] };
    case "switch":
      return { ...node, cases: [{ id: uniqueId("caso", taken), value: "", steps: [] }], default: [] };
    case "loop":
    case "until":
    case "scope":
      return { ...node, steps: [] };
    case "parallel":
      return {
        ...node,
        branches: [
          { id: uniqueId("ramo", taken), label: "Ramo 1", steps: [] },
          { id: uniqueId("ramo", taken), label: "Ramo 2", steps: [] },
        ],
      };
    default:
      return node;
  }
}

/** Deep copy with fresh ids (references inside keep pointing to the originals). */
export function cloneWithIds(node: FlowNode, taken: Set<string>): FlowNode {
  const copy: FlowNode = { ...structuredClone(node), id: uniqueId(node.id, taken) };
  if (copy.label) copy.label = `${copy.label} (cópia)`;
  for (const [slot, list] of childLists(copy)) {
    const fresh = list.map((child) => cloneWithIds(child, taken));
    Object.assign(copy, withList(copy, slot, fresh));
  }
  if (copy.cases) copy.cases = copy.cases.map((item) => ({ ...item, id: uniqueId(item.id, taken) }));
  if (copy.branches) copy.branches = copy.branches.map((item) => ({ ...item, id: uniqueId(item.id, taken) }));
  return copy;
}

export function duplicateNode(definition: Definition, id: string): { definition: Definition; id: string | null } {
  const found = locate(definition, id);
  if (!found) return { definition, id: null };
  const copy = cloneWithIds(found.node, allIds(definition));
  return { definition: insertNode(definition, { ...found.ref, index: found.index + 1 }, copy), id: copy.id };
}

export function countNodes(nodes: FlowNode[]): number {
  let count = 0;
  for (const _node of walk(nodes)) count += 1;
  return count;
}

export interface Visible {
  /** Step ids whose outputs this node may read, in run order. */
  steps: string[];
  /** Enclosing "Para cada" ids, innermost last. */
  loops: string[];
}

/** What a node may reference: same rule as the server checker. */
export function visibleFor(definition: Definition, nodeId: string): Visible {
  let result: Visible = { steps: [], loops: [] };
  const containers = new Set(["control.condition", "control.switch", "control.scope", "control.parallel"]);

  function run(nodes: FlowNode[], visible: string[], loops: string[]): { produced: string[]; found: boolean } {
    const produced: string[] = [];
    for (const node of nodes) {
      const here = [...visible, ...produced];
      if (node.id === nodeId) {
        result = { steps: here, loops };
        return { produced, found: true };
      }
      produced.push(node.id);
      const lists = childLists(node);
      if (!lists.length) continue;
      const isLoop = node.type === "control.foreach";
      const innerLoops = isLoop ? [...loops, node.id] : loops;
      for (const [, list] of lists) {
        const inner = run(list, here, innerLoops);
        if (inner.found) return { produced, found: true };
        if (containers.has(node.type)) produced.push(...inner.produced);
      }
    }
    return { produced, found: false };
  }

  run(definition.steps, [], []);
  return result;
}

export function blankDefinition(): Definition {
  return {
    schema: 3,
    trigger: { type: "trigger.manual", params: {} },
    variables: [],
    steps: [],
    settings: { notify_on_failure: [], timeout_hours: 168 },
  };
}

export function normalizeDefinition(raw: Definition): Definition {
  return {
    ...raw,
    variables: raw.variables ?? [],
    settings: raw.settings ?? { notify_on_failure: [], timeout_hours: 168 },
  };
}

export function asText(value: JsonValue | undefined): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

export function asList(value: JsonValue | undefined): string[] {
  if (Array.isArray(value)) return value.map((item) => asText(item));
  if (typeof value === "string" && value.trim()) return [value];
  return [];
}
