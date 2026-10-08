import type {
  CatalogView,
  Definition,
  FlowNode,
  NodeTypeView,
  OutputView,
} from "@/lib/ton/automations";
import { asText, findNode, visibleFor } from "@/lib/ton/automationTree";

export interface DynamicItem {
  label: string;
  expression: string;
  type: string;
  description?: string;
}

export interface DynamicGroup {
  key: string;
  title: string;
  icon?: string;
  group?: string;
  items: DynamicItem[];
}

export function specMap(catalog: CatalogView): Map<string, NodeTypeView> {
  return new Map(catalog.nodes.map((spec) => [spec.type, spec]));
}

function dynamicOutputs(node: FlowNode | { type: string; params: FlowNode["params"] }, spec: NodeTypeView): OutputView[] {
  const outputs = [...spec.outputs];
  const fields = node.params[spec.dynamic_outputs === "inputs" ? "inputs" : "fields"];
  if (spec.dynamic_outputs && Array.isArray(fields)) {
    const parent = spec.dynamic_outputs === "inputs" ? "inputs" : "fields";
    for (const field of fields) {
      if (field && typeof field === "object" && !Array.isArray(field) && field.name) {
        outputs.push({
          key: `${parent}.${asText(field.name)}`,
          label: asText(field.label || field.name),
          type: field.type === "number" ? "number" : field.type === "boolean" ? "boolean" : field.type === "list" ? "array" : "string",
          description: asText(field.description ?? ""),
          item_fields: [],
        });
      }
    }
  }
  return outputs;
}

function itemsOf(outputs: OutputView[], prefix: string): DynamicItem[] {
  return outputs.map((output) => ({
    label: output.label,
    expression: `${prefix}.${output.key}`,
    type: output.type,
    description: output.description,
  }));
}

/** Item fields for an expression like "{{ steps.x.outputs.items }}". */
export function itemFieldsFor(
  definition: Definition,
  expression: string,
  specs: Map<string, NodeTypeView>
): OutputView[] {
  const match = /\{\{\s*(trigger|steps\.([a-z0-9_]+))\.outputs\.([a-z0-9_]+)\s*\}\}/.exec(expression ?? "");
  if (!match) return [];
  const [, root, stepId, key] = match;
  let outputs: OutputView[] = [];
  if (root === "trigger") {
    const spec = specs.get(definition.trigger.type);
    outputs = spec ? dynamicOutputs(definition.trigger, spec) : [];
  } else if (stepId) {
    const node = findNode(definition, stepId);
    const spec = node ? specs.get(node.type) : undefined;
    if (node && spec) {
      outputs = dynamicOutputs(node, spec);
      if (node.type === "data.group") {
        return [
          { key: "key", label: "Valor do grupo", type: "string", description: "", item_fields: [] },
          { key: "count", label: "Quantidade", type: "number", description: "", item_fields: [] },
          { key: "total_formatado", label: "Soma (R$)", type: "string", description: "", item_fields: [] },
          { key: "items", label: "Itens do grupo", type: "array", description: "", item_fields: [] },
        ];
      }
      if (node.type === "data.filter" || node.type === "data.sort") {
        return itemFieldsFor(definition, asText(node.params.items), specs);
      }
    }
  }
  return outputs.find((output) => output.key === key)?.item_fields ?? [];
}

/** Everything a parameter of ``nodeId`` may read (``"trigger"`` = nothing). */
export function dynamicGroups(
  definition: Definition,
  nodeId: string,
  catalog: CatalogView,
  options: { itemSource?: string } = {}
): DynamicGroup[] {
  if (nodeId === "trigger") return [];
  const specs = specMap(catalog);
  const groups: DynamicGroup[] = [];
  const visible = visibleFor(definition, nodeId);
  if (options.itemSource !== undefined) {
    const fields = itemFieldsFor(definition, options.itemSource, specs);
    groups.push({
      key: "item",
      title: "Item da lista",
      icon: "list",
      group: "control",
      items: [{ label: "Item inteiro", expression: "item", type: "object" }, ...itemsOf(fields, "item")],
    });
  }
  for (const loopId of [...visible.loops].reverse()) {
    const loop = findNode(definition, loopId);
    if (!loop) continue;
    const fields = itemFieldsFor(definition, asText(loop.params.items), specs);
    groups.push({
      key: `loop:${loopId}`,
      title: `Item atual · ${loop.label || "Para cada"}`,
      icon: "repeat",
      group: "control",
      items: [
        { label: "Item inteiro", expression: "item", type: "object" },
        ...itemsOf(fields, "item"),
        { label: "Posição (0, 1, 2…)", expression: `loop.${loopId}.index`, type: "number" },
      ],
    });
  }
  const trigger = specs.get(definition.trigger.type);
  if (trigger) {
    groups.push({
      key: "trigger",
      title: `Quando começa · ${trigger.label}`,
      icon: trigger.icon,
      group: "trigger",
      items: itemsOf(dynamicOutputs(definition.trigger, trigger), "trigger.outputs"),
    });
  }
  for (const stepId of visible.steps) {
    const node = findNode(definition, stepId);
    const spec = node ? specs.get(node.type) : undefined;
    if (!node || !spec) continue;
    const outputs = dynamicOutputs(node, spec);
    const items = itemsOf(outputs, `steps.${node.id}.outputs`);
    items.push({ label: "Deu certo ou falhou", expression: `steps.${node.id}.status`, type: "string" }, { label: "Mensagem de erro", expression: `steps.${node.id}.error`, type: "string" });
    groups.push({ key: node.id, title: node.label || spec.label, icon: spec.icon, group: spec.group, items });
  }
  if (definition.variables.length) {
    groups.push({
      key: "vars",
      title: "Valores guardados",
      icon: "variable",
      group: "variables",
      items: definition.variables.map((variable) => ({
        label: variable.description || prettyName(variable.name),
        expression: `vars.${variable.name}`,
        type: variable.type,
        description: variable.description,
      })),
    });
  }
  groups.push({
    key: "run",
    title: "Sobre esta execução",
    icon: "play",
    group: "trigger",
    items: [
      { label: "Link da execução", expression: "run.link", type: "string" },
      { label: "Nome da automação", expression: "automation.name", type: "string" },
      { label: "Agora", expression: "now()", type: "string" },
    ],
  });
  return groups.filter((group) => group.items.length);
}

/** Friendly name of a token, e.g. "Buscar inconsistências › Quantidade". */
export function describeExpression(expression: string, definition: Definition, catalog: CatalogView): string {
  const text = expression.trim();
  const specs = specMap(catalog);
  const step = /^steps\.([a-z0-9_]+)\.outputs\.([a-z0-9_.]+)$/.exec(text);
  if (step) {
    const node = findNode(definition, step[1]!);
    const spec = node ? specs.get(node.type) : undefined;
    const output = spec && node ? dynamicOutputs(node, spec).find((item) => item.key === step[2]) : undefined;
    return `${node?.label || spec?.label || step[1]} › ${output?.label ?? step[2]}`;
  }
  const trigger = /^trigger\.outputs\.([a-z0-9_.]+)$/.exec(text);
  if (trigger) {
    const spec = specs.get(definition.trigger.type);
    const output = spec ? dynamicOutputs(definition.trigger, spec).find((item) => item.key === trigger[1]) : undefined;
    return `Início › ${output?.label ?? trigger[1]}`;
  }
  const variable = /^vars\.([a-z0-9_]+)$/.exec(text);
  if (variable) {
    const declared = definition.variables.find((item) => item.name === variable[1]);
    return declared?.description || prettyName(variable[1]!);
  }
  const item = /^item(?:\.([a-z0-9_.]+))?$/.exec(text);
  if (item) return item[1] ? `Item › ${prettyName(item[1])}` : "Item da lista";
  if (text === "run.link") return "Link da execução";
  if (text === "automation.name") return "Nome da automação";
  if (text === "now()") return "Agora";
  const status = /^steps\.([a-z0-9_]+)\.(status|error)$/.exec(text);
  if (status) {
    const node = findNode(definition, status[1]!);
    return `${node?.label || specs.get(node?.type ?? "")?.label || status[1]} › ${status[2] === "status" ? "Deu certo ou falhou" : "Mensagem de erro"}`;
  }
  return `ƒ ${text.length > 40 ? `${text.slice(0, 38)}…` : text}`;
}

/** "total_de_linhas" → "Total de linhas". */
export function prettyName(name: string): string {
  const text = name.replace(/_/g, " ").trim();
  return text ? text[0]!.toUpperCase() + text.slice(1) : name;
}

export interface Segment {
  text: string;
  expression?: string;
}

export function segments(value: string): Segment[] {
  const parts: Segment[] = [];
  const pattern = /\{\{([\s\S]*?)\}\}/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(value)) !== null) {
    if (match.index > last) parts.push({ text: value.slice(last, match.index) });
    parts.push({ text: match[0], expression: match[1]!.trim() });
    last = match.index + match[0].length;
  }
  if (last < value.length) parts.push({ text: value.slice(last) });
  return parts;
}
