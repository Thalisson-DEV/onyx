import { COPY, formatPeriod } from "@/lib/ton/copy";
import type { EvidenceRecord, PendingCategoryKey } from "@/lib/ton/decisions";
import { getBusinessLabel } from "@/lib/ton/labels";

export interface Normalization {
  id: string;
  mapping_revision_number: number;
  started_at: string;
}

export interface Structure {
  id: string;
  label: string;
  latest_version: number;
}

export interface Version {
  id: string;
  number: number;
  lines: Array<{ code: string; label: string; line_type: string }>;
}

export interface PeriodReadiness {
  status: "READY" | "NOT_READY";
  scope: { period: string };
  blockers: Record<string, number>;
}

export interface Overview {
  periods: PeriodReadiness[];
}

export interface Candidate {
  target_id: string;
  code: string;
  label: string;
  evidence: "EXACT_CODE" | "APPROVED_MAPPING";
}

export interface BlockerRow {
  source_id: string | null;
  source_key: string | null;
  account_id: string | null;
  item_id: string | null;
  record_count: number;
  periods: string[];
  status: string;
  candidate: Candidate | null;
  legacy_evidence: {
    suggested_code: string;
    suggested_label: string | null;
    reference_label: string;
    reference_digest: string;
  } | null;
  line_candidate: string | null;
  paired: boolean | null;
  evidence: string | null;
  records: EvidenceRecord[];
}

export interface BlockerPage {
  total: number;
  rows: BlockerRow[];
  covered_periods?: string[];
}

export type Triage = "evidence" | "decision" | "data";

/** What a person needs to settle an item: confirm evidence, choose, or bring data. */
export function triageOf(row: BlockerRow, category: QueueCategory): Triage {
  if (category.noActual || category.key === "other") return "data";
  if (row.candidate || row.legacy_evidence || row.line_candidate)
    return "evidence";
  return "decision";
}

export interface Target {
  id: string;
  code: string;
  label?: string;
  name?: string;
}

export interface QueueCategory {
  key: PendingCategoryKey;
  blocker: string;
  label: string;
  description: string;
  action: string;
  rowTitle: string;
  count: number;
  noActual: boolean;
}

export const RECONCILIATION_DECISIONS = [
  "SUPPLEMENTAL",
  "EXPECTED_DIFFERENCE",
  "NOT_SAME_EVENT",
  "NG_AUTHORITATIVE",
] as const;

export type ReconciliationDecision = (typeof RECONCILIATION_DECISIONS)[number];

export const MAPPING_KEYS: PendingCategoryKey[] = [
  "units",
  "accounts",
  "budgetAccounts",
  "budgetUnits",
];

/** Overview links use business categories; the queue works on blocker codes. */
export const CATEGORY_PARAM: Record<string, string> = {
  units: "UNMAPPED_UNIT",
  budget: "BUDGET_PERIOD_UNRESOLVED",
  reconciliation: "SOURCE_RECONCILIATION_UNRESOLVED",
  actuals: "NO_ACTUAL",
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function describeCategory(
  key: PendingCategoryKey,
  blocker: string,
  count: number
): QueueCategory {
  if (blocker === "NO_ACTUAL") {
    return {
      key: "other",
      blocker,
      label: COPY.pending.noActual.label,
      description: COPY.pending.noActual.description,
      action: COPY.pending.noActual.action,
      rowTitle: COPY.pending.noActual.label,
      count,
      noActual: true,
    };
  }
  const copy = COPY.pending.categories[key];
  return {
    key,
    blocker,
    label: key === "other" ? getBusinessLabel(blocker) : copy.label,
    description: copy.description,
    action: copy.action,
    rowTitle: copy.rowTitle,
    count,
    noActual: false,
  };
}

export function rowTitle(row: BlockerRow, category: QueueCategory): string {
  if (category.noActual) return category.rowTitle;
  if (row.source_key && !UUID.test(row.source_key))
    return getBusinessLabel(row.source_key);
  // Reconciliation items carry no readable key; the first sentence of the
  // evidence says what happened (for example "Somente faturamento disponível").
  const evidence = row.evidence ? getBusinessLabel(row.evidence) : "";
  const headline = evidence.split(".")[0]?.trim();
  return headline && evidence !== row.evidence ? headline : category.rowTitle;
}

/** Evidence text without the sentence already used as the row title. */
export function rowDetail(row: BlockerRow, category: QueueCategory): string {
  const evidence = row.evidence ? getBusinessLabel(row.evidence) : "";
  const title = rowTitle(row, category);
  return evidence.startsWith(title)
    ? evidence.slice(title.length).replace(/^\.\s*/, "")
    : evidence;
}

export function rowPeriods(row: BlockerRow): string | null {
  if (!row.periods.length) return null;
  return row.periods
    .map((period) => formatPeriod(period).toLowerCase())
    .join(", ");
}

export function rowSuggestion(row: BlockerRow): string {
  if (row.status === "APPROVED" && row.candidate)
    return COPY.pending.approvedCandidate(row.candidate.code);
  if (row.candidate) return COPY.pending.candidate(row.candidate.code);
  if (row.legacy_evidence)
    return COPY.pending.candidate(row.legacy_evidence.suggested_code);
  if (row.line_candidate) return COPY.pending.candidate(row.line_candidate);
  return COPY.pending.noCandidate;
}

/** The one-line identity of a source record used in the queue row. */
export function rowRecordHint(row: BlockerRow): string | null {
  const first = row.records[0];
  if (!first) return null;
  return [first.document, first.counterparty ?? first.account]
    .filter(Boolean)
    .join(" · ");
}

export function readinessUrl(
  runId: string,
  versionId: string,
  unitId?: string
): string {
  return `/api/ton/financial-domain/normalizations/${runId}/readiness?structure_version_id=${versionId}${unitId ? `&unit_id=${unitId}` : ""}`;
}
