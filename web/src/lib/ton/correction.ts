"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { TonApiError } from "@/lib/ton/decisions";
import type { TonTone } from "@/views/ton/components/ui";

export const CORRECTION_API = "/api/ton/correction";

export type Criticality = "CRITICAL" | "HIGH" | "MEDIUM" | "MONITORING";
export type CaseSituation =
  | "UNASSIGNED"
  | "ASSIGNED"
  | "OVERDUE"
  | "VERIFIED"
  | "ACCEPTED";

export interface CaseOrigin {
  system: string;
  file_name: string | null;
  imported_at: string | null;
  sheets: string[];
}

export interface CaseRow {
  id: string;
  number: number;
  rule_code: string;
  title: string;
  summary: string;
  owner_area: string | null;
  owner_name: string | null;
  suggested_area: string;
  due_date: string | null;
  situation: CaseSituation;
  situation_label: string;
  criticality: Criticality;
  criticality_label: string;
  criticality_reason: string;
  impact_open: string;
  impact_total: string;
  has_amount: boolean;
  member_count: number;
  open_count: number;
  fixed_count: number;
  months: string[];
  recurring: boolean;
  origin: CaseOrigin;
  first_detected_at: string;
  last_detected_at: string;
  verified_at: string | null;
  closing_note: string | null;
  in_board_summary: boolean;
}

export interface EvidenceRow {
  occurrence_code: string;
  status: "OPEN" | "FIXED";
  sheet: string | null;
  row: number | null;
  column: string | null;
  emission: string | null;
  unit: string | null;
  document: string | null;
  history: string | null;
  account: string | null;
  amount: string | null;
  group: string | null;
}

export interface TimelineItem {
  at: string;
  kind: "DETECTED" | "SEEN_AGAIN" | "VERIFIED" | "PEOPLE";
  label: string;
  detail: string | null;
  actor: string | null;
}

export interface CaseDetail extends CaseRow {
  found: string;
  matters: string;
  cause: string;
  action: string;
  action_is_default: boolean;
  verify: string;
  impact_basis: string;
  rule_title: string;
  decision_reason: string | null;
  evidence: EvidenceRow[];
  evidence_total: number;
  timeline: TimelineItem[];
  owner_areas: string[];
}

export interface ReminderDraft {
  owner: string;
  subject: string;
  body: string;
  can_send: boolean;
  why_not: string | null;
}

export interface BoardItem {
  case_id: string;
  number: number;
  criticality: Criticality;
  result: string;
  problem: string;
  impact: string;
  cause: string;
  action: string;
  verified: boolean;
}

export interface BoardSummary {
  open_amount: string;
  verified_amount: string;
  recurring: number;
  unassigned: number;
  overdue: number;
  items: BoardItem[];
}

export const CRITICALITY_TONE: Record<Criticality, TonTone> = {
  CRITICAL: "danger",
  HIGH: "warning",
  MEDIUM: "brand",
  MONITORING: "neutral",
};

export const SITUATION_TONE: Record<CaseSituation, TonTone> = {
  UNASSIGNED: "warning",
  ASSIGNED: "brand",
  OVERDUE: "danger",
  VERIFIED: "success",
  ACCEPTED: "neutral",
};

export const OWNER_AREAS = [
  "Financeiro",
  "Contabilidade",
  "Controladoria",
  "Unidades",
  "DP",
];

export function caseNumber(number: number): string {
  return `PC-${String(number).padStart(4, "0")}`;
}

export function isOpen(row: CaseRow): boolean {
  return row.situation !== "VERIFIED" && row.situation !== "ACCEPTED";
}

export function useCases() {
  return useSWR<CaseRow[]>(`${CORRECTION_API}/cases`, errorHandlingFetcher);
}

export function useCase(id: string) {
  return useSWR<CaseDetail>(`${CORRECTION_API}/cases/${id}`, errorHandlingFetcher);
}

export function useBoard() {
  return useSWR<BoardSummary>(`${CORRECTION_API}/board`, errorHandlingFetcher);
}

export async function correctionJson<T>(
  method: "POST" | "PUT",
  path: string,
  body: unknown
): Promise<T> {
  const response = await fetch(`${CORRECTION_API}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? payload.detail
        : null;
    throw new TonApiError(
      response.status,
      typeof detail === "string" ? detail : null
    );
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  // SAFETY: TON endpoints return the declared Pydantic view (or null) on 2xx.
  return (text ? JSON.parse(text) : undefined) as T;
}

/** The order the list showed, for previous/next on the case page. */
const QUEUE_KEY = "ton.correction.queue";

export function rememberCases(ids: string[]): void {
  try {
    sessionStorage.setItem(QUEUE_KEY, JSON.stringify(ids));
  } catch {
    // Storage can be refused; navigation then stays per case.
  }
}

export function caseNeighbours(id: string): {
  previous: string | null;
  next: string | null;
} {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(QUEUE_KEY) ?? "[]");
    const ids = Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string")
      : [];
    const index = ids.indexOf(id);
    return index < 0
      ? { previous: null, next: null }
      : { previous: ids[index - 1] ?? null, next: ids[index + 1] ?? null };
  } catch {
    return { previous: null, next: null };
  }
}
