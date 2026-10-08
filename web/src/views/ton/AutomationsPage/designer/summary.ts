import type { CatalogView, Definition, FlowNode, NodeTypeView, Params } from "@/lib/ton/automations";
import { asList, asText } from "@/lib/ton/automationTree";
import { describeExpression, prettyName, segments } from "@/views/ton/AutomationsPage/designer/dynamic";

const WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

export function describeSchedule(params: Params): string {
  const frequency = asText(params.frequency) || "week";
  const interval = Number(params.interval) || 1;
  const time = asText(params.time) || "08:00";
  if (frequency === "minute") return `A cada ${interval} min`;
  if (frequency === "hour") return interval === 1 ? "A cada hora" : `A cada ${interval} horas`;
  if (frequency === "day") return interval === 1 ? `Todo dia às ${time}` : `A cada ${interval} dias às ${time}`;
  if (frequency === "month") return `Dia ${asText(params.day_of_month) || "1"} de cada mês às ${time}`;
  const days = asList(params.weekdays).map(Number).sort();
  const names = days.join(",") === "0,1,2,3,4" ? "dia útil" : days.map((day) => WEEKDAYS[day] ?? "").join(", ");
  return `Toda ${names || "seg"} às ${time}`;
}

function friendly(value: string, definition: Definition, catalog: CatalogView): string {
  return segments(value)
    .map((part) => (part.expression !== undefined ? describeExpression(part.expression, definition, catalog) : part.text))
    .join("")
    .trim();
}

function cut(text: string, size = 46): string {
  return text.length > size ? `${text.slice(0, size - 1)}…` : text;
}

/** One line under the node title: what the step does with its parameters. */
export function nodeSummary(node: FlowNode | null, spec: NodeTypeView | undefined, definition: Definition, catalog: CatalogView): string {
  if (!spec) return node?.type ?? "";
  const params = node ? node.params : definition.trigger.params;
  const custom = node && node.label && node.label !== spec.label;
  switch (spec.type) {
    case "trigger.schedule":
      return describeSchedule(params);
    case "trigger.manual": {
      const count = Array.isArray(params.inputs) ? params.inputs.length : 0;
      return count ? `Pede ${count} informação(ões)` : "Botão Executar ou chat";
    }
    case "email.send": {
      const to = asList(params.to);
      if (!to.length) return "Sem destinatário";
      const first = friendly(to[0]!, definition, catalog);
      return cut(`Para: ${first}${to.length > 1 ? ` +${to.length - 1}` : ""}`);
    }
    case "control.condition": {
      const rules = params.condition && typeof params.condition === "object" && !Array.isArray(params.condition) && Array.isArray(params.condition.rules) ? params.condition.rules.length : 0;
      return rules ? `${rules} regra(s)` : "Sem regras";
    }
    case "control.foreach":
    case "data.filter":
    case "data.sort":
    case "data.group":
    case "data.table":
      return custom ? spec.label : cut(friendly(asText(params.items), definition, catalog) || spec.label);
    case "control.wait":
      return cut(spec.label);
    case "ton.notify":
    case "approval.request":
      return cut(friendly(asText(params.title), definition, catalog) || spec.label);
    case "http.request":
      return cut(`${asText(params.method) || "POST"} ${asText(params.url).replace(/^https:\/\//, "")}`);
    case "variable.set":
    case "variable.increment":
    case "variable.append":
      return asText(params.name) ? prettyName(asText(params.name)) : spec.label;
    case "ai.prompt":
      return cut(asText(params.instructions) || spec.label);
    default:
      return custom ? spec.label : "";
  }
}
