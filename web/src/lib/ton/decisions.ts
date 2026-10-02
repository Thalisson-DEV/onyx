"use client";

import useSWR from "swr";
import type { Route } from "next";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useTonAccess } from "@/lib/ton/api";
import { COPY } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";

/** One source record behind a pending item, exactly as the source states it. */
export interface EvidenceRecord {
  origin: "NG" | "BILLING";
  document: string | null;
  emission_date: string | null;
  period: string | null;
  account: string | null;
  unit: string | null;
  counterparty: string | null;
  description: string | null;
  movement_amount: string | null;
  final_amount: string | null;
  service_amount: string | null;
  net_amount: string | null;
  sheet: string | null;
  row: number | null;
}

export type DecisionKind =
  | "UNIT_MAPPING"
  | "ACCOUNT_MAPPING"
  | "BUDGET_ACCOUNT_MAPPING"
  | "BUDGET_UNIT_MAPPING"
  | "BUDGET_PERIOD"
  | "AMOUNT_BASIS"
  | "RECONCILIATION"
  | "CANDIDATE_REJECTION"
  | "DRE_ASSIGNMENT";

export interface DecisionEntry {
  kind: DecisionKind;
  subject: string;
  outcome: string;
  reason: string | null;
  decided_by: string | null;
  decided_at: string;
  version: number | null;
  /** null when the decision does not depend on recomputing the base. */
  applied: boolean | null;
}

export interface DecisionLog {
  pending_decisions: number;
  entries: DecisionEntry[];
}

export interface DecisionVersions {
  mapping: number;
  amount_basis: number;
  reconciliation: number;
}

export interface PeriodChange {
  period: string;
  status_before: "READY" | "NOT_READY" | null;
  status_after: "READY" | "NOT_READY";
  blockers_before: Record<string, number>;
  blockers_after: Record<string, number>;
}

export interface ReadinessChanges {
  run_id: string;
  run_started_at: string;
  previous_run_id: string | null;
  previous_started_at: string | null;
  applied: DecisionVersions;
  previous_applied: DecisionVersions | null;
  current: DecisionVersions;
  pending_decisions: number;
  periods: PeriodChange[];
}

export type PendingCategoryKey = keyof typeof COPY.pending.categories;

/** Readiness blocker codes that a person resolves in the pending queue. */
export const PENDING_CATEGORIES: {
  key: PendingCategoryKey;
  blocker: string;
}[] = [
  { key: "units", blocker: "UNMAPPED_UNIT" },
  { key: "accounts", blocker: "UNMAPPED_ACCOUNT" },
  { key: "budgetAccounts", blocker: "BUDGET_UNMAPPED_ACCOUNT" },
  { key: "budgetUnits", blocker: "BUDGET_UNMAPPED_UNIT" },
  { key: "amountBasis", blocker: "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED" },
  { key: "dreAssignment", blocker: "DRE_ACCOUNT_UNMAPPED" },
  { key: "drePending", blocker: "DRE_MAPPING_PENDING_APPROVAL" },
  { key: "budgetPeriods", blocker: "BUDGET_PERIOD_UNRESOLVED" },
  { key: "reconciliation", blocker: "SOURCE_RECONCILIATION_UNRESOLVED" },
  {
    key: "reconciliationAmbiguous",
    blocker: "SOURCE_RECONCILIATION_AMBIGUOUS",
  },
];

export function categoryKeyFor(blocker: string): PendingCategoryKey {
  return (
    PENDING_CATEGORIES.find((item) => item.blocker === blocker)?.key ?? "other"
  );
}

/** Business name of a readiness blocker code. */
export function blockerLabel(blocker: string): string {
  if (blocker === "NO_ACTUAL") return COPY.pending.noActual.label;
  const key = categoryKeyFor(blocker);
  return key === "other"
    ? getBusinessLabel(blocker)
    : COPY.pending.categories[key].label;
}

/** Blockers a person can settle with a decision recorded in TON. */
export function isDecisionBlocker(blocker: string): boolean {
  return categoryKeyFor(blocker) !== "other";
}

export function pendingQueueHref(options: {
  blocker?: string;
  period?: string | null;
  normalization?: string | null;
  unit?: string | null;
}): Route {
  const query = new URLSearchParams();
  if (options.period) query.set("period", options.period);
  if (options.normalization) query.set("normalization", options.normalization);
  if (options.unit) query.set("unit", options.unit);
  if (options.blocker) query.set("blocker", options.blocker);
  const text = query.toString();
  // SAFETY: /ton/pendencias is a static route; only its query varies.
  return (text ? `/ton/pendencias?${text}` : "/ton/pendencias") as Route;
}

export interface BlockerDelta {
  blocker: string;
  before: number;
  after: number;
}

/** Side-by-side counts of two backend readiness results; no inference. */
export function blockerDeltas(
  before: Record<string, number>,
  after: Record<string, number>
): BlockerDelta[] {
  const codes = new Set([...Object.keys(before), ...Object.keys(after)]);
  return [...codes]
    .map((blocker) => ({
      blocker,
      before: before[blocker] ?? 0,
      after: after[blocker] ?? 0,
    }))
    .filter((item) => item.before > 0 || item.after > 0)
    .sort(
      (a, b) =>
        Number(b.before !== b.after) - Number(a.before !== a.after) ||
        b.after - a.after
    );
}

export function sumBlockers(blockers: Record<string, number>): number {
  return Object.values(blockers).reduce((sum, count) => sum + count, 0);
}

/** How many recorded decisions a recompute folded into the base. */
export function appliedDecisionCount(changes: ReadinessChanges): number {
  const before = changes.previous_applied;
  if (!before) return 0;
  return (
    changes.applied.mapping -
    before.mapping +
    (changes.applied.amount_basis - before.amount_basis) +
    (changes.applied.reconciliation - before.reconciliation)
  );
}

export const TON_DECISIONS_KEY = "/api/ton/financial-domain/decisions?limit=20";

export function useDecisionLog() {
  const { canRead } = useTonAccess();
  return useSWR<DecisionLog>(
    canRead ? TON_DECISIONS_KEY : null,
    errorHandlingFetcher
  );
}

export function readinessChangesKey(
  runId: string | null | undefined,
  versionId: string | null | undefined,
  unitId?: string | null
): string | null {
  if (!runId || !versionId) return null;
  return `/api/ton/financial-domain/normalizations/${runId}/readiness/changes?structure_version_id=${versionId}${unitId ? `&unit_id=${unitId}` : ""}`;
}

export function useReadinessChanges(
  runId: string | null | undefined,
  versionId: string | null | undefined,
  unitId?: string | null
) {
  const { canRead } = useTonAccess();
  return useSWR<ReadinessChanges>(
    canRead ? readinessChangesKey(runId, versionId, unitId) : null,
    errorHandlingFetcher
  );
}

export async function postTonJson<T>(
  path: string,
  body: Record<string, string | null>
): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(String(response.status));
  // SAFETY: TON endpoints return the declared Pydantic view on 2xx.
  return (await response.json()) as T;
}

/** Business labels the assistant tools return, mapped back to readiness codes. */
const AGENT_BLOCKER_LABELS: Record<string, string> = {
  "Unidade não vinculada": "UNMAPPED_UNIT",
  "Conta não vinculada": "UNMAPPED_ACCOUNT",
  "Conta do orçamento não vinculada": "BUDGET_UNMAPPED_ACCOUNT",
  "Unidade do orçamento não vinculada": "BUDGET_UNMAPPED_UNIT",
  "Base de valor realizado não definida": "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED",
  "Conta sem classificação na DRE": "DRE_ACCOUNT_UNMAPPED",
  "Classificação DRE aguarda aprovação": "DRE_MAPPING_PENDING_APPROVAL",
  "Período do orçamento não definido": "BUDGET_PERIOD_UNRESOLVED",
  "Conciliação sem decisão": "SOURCE_RECONCILIATION_UNRESOLVED",
  "Conciliação ambígua": "SOURCE_RECONCILIATION_AMBIGUOUS",
  "Períodos sem realizado no escopo": "NO_ACTUAL",
};

export function blockerCode(labelOrCode: string): string {
  return AGENT_BLOCKER_LABELS[labelOrCode] ?? labelOrCode;
}
