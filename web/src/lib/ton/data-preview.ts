import {
  COPY,
  formatDateTime,
  formatNumber,
  formatPeriod,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import { isObject, type Json, type JsonObject } from "@/lib/ton/work-log";

/**
 * A readable view of what a TON query returned: business labels, formatted
 * values, and no identifiers, hashes or engine versions. Keys without a
 * business label are left out instead of shown raw.
 */

export interface PreviewColumn {
  key: string;
  label: string;
  numeric: boolean;
}

export interface PreviewTable {
  columns: PreviewColumn[];
  rows: string[][];
  total: number;
}

export interface PreviewField {
  label: string;
  value: string;
}

export interface DataPreview {
  fields: PreviewField[];
  table: PreviewTable | null;
}

const LABELS: Record<string, string> = {
  name: "Nome",
  label: "Linha",
  title: "Título",
  status: "Situação",
  period: "Período",
  periods: "Períodos",
  checked_periods: "Períodos verificados",
  covered_periods: "Períodos com evidência",
  realizado: "Realizado",
  orcado: "Orçado",
  variance: "Variação",
  variance_percent: "Variação %",
  realizado_ytd: "Realizado no ano",
  orcado_ytd: "Orçado no ano",
  variance_ytd: "Variação no ano",
  variance_percent_ytd: "Variação % no ano",
  amount: "Valor",
  value: "Valor",
  explanation: "Explicação",
  description: "Descrição",
  criticality: "Criticidade",
  occurrence_status: "Situação da ocorrência",
  occurrence_short_code: "Ocorrência",
  short_code: "Código",
  category: "Categoria",
  blocking: "Bloqueia a publicação",
  record_count: "Registros",
  sheet_month: "Mês da planilha",
  sheet_name: "Planilha",
  row_number: "Linha da planilha",
  detected_at: "Detectado em",
  format: "Formato",
  last_success_at: "Última importação",
  last_attempt_at: "Última tentativa",
  filename: "Arquivo",
  total: "Total",
  blocker: "Pendência",
  blockers: "Pendências",
  actual_count: "Lançamentos do NG",
  billing_count: "Notas de faturamento",
  derived_count: "Lançamentos derivados",
  budget_count: "Linhas de orçamento",
  reconciliation: "Conciliação",
  dre_status: "DRE",
  scope: "Unidade/filial",
  as_of: "Data de referência",
  started_at: "Início",
  finished_at: "Fim",
  rejected: "Rejeitadas",
  warnings: "Avisos",
  errors: "Erros",
  recommendation: "Recomendação",
  recommendations: "Recomendações",
  source_name: "Fonte",
  acquisition: "Forma de aquisição",
  direct_integration: "Integração direta",
  data_context: "Contexto dos dados",
  owner: "Responsável",
  due_date: "Prazo",
  deadline: "Prazo",
  responsible: "Responsável",
  pending_decisions: "Decisões pendentes",
  findings_scope: "Escopo dos achados",
  generated_at: "Gerado em",
  verification_result: "Verificação",
};

/** Keys that hold money, rendered as R$. */
const MONEY = /^(realizado|orcado|variance|amount|value|valor)(_ytd)?$/;

/** Payload keys whose nested list is the main content. */
const LIST_KEYS = [
  "rows",
  "items",
  "findings",
  "periods",
  "entries",
  "results",
];

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HASH = /^(sha256:)?[0-9a-f]{32,}$/i;
const ISO_DATETIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;
const PERIOD = /^\d{4}-\d{2}-01$/;
const DECIMAL = /^-?\d+(\.\d+)?(E-?\d+)?$/i;
const ENUM = /^[A-Z][A-Z0-9_ ]+$/;

const currency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 2,
});

/** Backend sometimes translates a key itself ("Pronta", "Importada"). */
function labelFor(key: string): string | null {
  if (LABELS[key]) return LABELS[key];
  if (/^[A-ZÀ-Ú][a-zà-ú]/.test(key) && !key.includes("_")) return key;
  return null;
}

function isHidden(value: Json): boolean {
  return typeof value === "string" && (UUID.test(value) || HASH.test(value));
}

export function formatValue(key: string, value: Json): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "boolean")
    return value ? COPY.work.data.yes : COPY.work.data.no;
  if (typeof value === "number")
    return MONEY.test(key) ? currency.format(value) : formatNumber(value);
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed || isHidden(trimmed)) return null;
    if (PERIOD.test(trimmed)) return formatPeriod(trimmed);
    if (ISO_DATETIME.test(trimmed)) {
      const date = new Date(trimmed);
      return Number.isNaN(date.getTime()) ? trimmed : formatDateTime(date);
    }
    if (DECIMAL.test(trimmed)) {
      const parsed = Number(trimmed);
      if (Number.isFinite(parsed))
        return MONEY.test(key) ? currency.format(parsed) : formatNumber(parsed);
    }
    if (ENUM.test(trimmed) && trimmed.includes("_"))
      return getBusinessLabel(trimmed);
    return trimmed;
  }
  if (Array.isArray(value)) {
    const parts = value
      .map((item) =>
        typeof item === "object" && item !== null
          ? null
          : formatValue(key, item)
      )
      .filter((item): item is string => Boolean(item));
    return parts.length ? parts.join(", ") : null;
  }
  // A small count map such as {"Conciliado": 15, "NG_ONLY": 11}.
  const entries = Object.entries(value).filter(
    (entry): entry is [string, number] => typeof entry[1] === "number"
  );
  if (!entries.length) return null;
  return entries
    .map(
      ([label, count]) => `${getBusinessLabel(label)}: ${formatNumber(count)}`
    )
    .join(" · ");
}

function fieldsOf(object: JsonObject): PreviewField[] {
  return Object.entries(object).flatMap(([key, value]) => {
    const label = labelFor(key);
    if (!label) return [];
    if (Array.isArray(value) && value.some(isObject)) return [];
    const formatted = formatValue(key, value);
    return formatted ? [{ label, value: formatted }] : [];
  });
}

const MAX_ROWS = 8;

function tableOf(items: Json[]): PreviewTable | null {
  const objects = items.filter(isObject);
  if (!objects.length) return null;
  const counts = new Map<string, number>();
  for (const object of objects)
    for (const [key, value] of Object.entries(object))
      if (labelFor(key) && formatValue(key, value) !== null)
        counts.set(key, (counts.get(key) ?? 0) + 1);
  const columns = [...counts.entries()]
    .filter(([, count]) => count >= Math.max(1, objects.length / 2))
    .slice(0, 5)
    .map(([key]) => ({
      key,
      label: labelFor(key) ?? key,
      numeric: objects.some((object) => {
        const value = object[key];
        return (
          typeof value === "number" ||
          (typeof value === "string" && DECIMAL.test(value.trim()))
        );
      }),
    }));
  if (!columns.length) return null;
  const rows = objects
    .map((object) =>
      columns.map(
        (column) => formatValue(column.key, object[column.key] ?? null) ?? "—"
      )
    )
    .filter((row) => row.some((cell) => cell !== "—"));
  return { columns, rows: rows.slice(0, MAX_ROWS), total: rows.length };
}

export function buildDataPreview(data: Json | undefined): DataPreview | null {
  if (data === undefined || data === null) return null;
  if (Array.isArray(data)) {
    const table = tableOf(data);
    return table ? { fields: [], table } : null;
  }
  if (!isObject(data)) {
    const value = formatValue("", data);
    return value
      ? { fields: [{ label: COPY.work.genericQuery, value }], table: null }
      : null;
  }
  const root = isObject(data.output) ? data.output : data;
  const list = LIST_KEYS.map((key) => root[key]).find(
    (value): value is Json[] => Array.isArray(value) && value.some(isObject)
  );
  const table = list ? tableOf(list) : null;
  const fields = fieldsOf(root);
  if (!fields.length && !table) return null;
  return { fields, table };
}
