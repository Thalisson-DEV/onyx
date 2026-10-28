"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { TonApiError } from "@/lib/ton/decisions";
import type { TonTone } from "@/views/ton/components/ui";

export const PAYABLES_API = "/api/ton/payables";

export type TitleKind = "REAL" | "ESTIMATE";
export type DocumentType =
  | "NF"
  | "NFSE"
  | "FATURA"
  | "RECIBO"
  | "BOLETO"
  | "CONTRATO"
  | "OUTRO";
export type DestinationKind = "VEHICLE" | "SITE" | "STOCK" | "ADMINISTRATION";
export type SupplierKind = "COMPANY" | "PERSON" | "EMPLOYEE" | "PUBLIC_BODY";
export type PixKeyType = "CPF" | "CNPJ" | "EMAIL" | "PHONE" | "RANDOM";
export type AttachmentRole = "INVOICE" | "BOLETO" | "RECEIPT" | "OTHER";
export type TitleAction =
  | "RESUBMIT"
  | "CONFER"
  | "RETURN"
  | "RELEASE"
  | "UNDO_RELEASE"
  | "BOOK"
  | "CANCEL";
export type TitleStatus =
  | "WAITING_ATTACHMENT"
  | "WAITING_SUPPLIER"
  | "RECEIVED"
  | "RETURNED"
  | "CONFERRED"
  | "RELEASED"
  | "BOOKED"
  | "PAID"
  | "ESTIMATE_OPEN"
  | "ESTIMATE_REPLACED"
  | "CANCELLED";
export type Severity = "BLOCK" | "ATTENTION" | "INFO";

export interface PayablesContext {
  is_finance: boolean;
  units: { id: string; code: string; name: string }[];
  accounts: { id: string; code: string; label: string }[];
  notice_business_days: number;
}

export interface SupplierRef {
  id: string;
  name: string;
  tax_id: string;
}

export interface Supplier {
  id: string;
  tax_id: string;
  tax_id_display: string;
  legal_name: string;
  trade_name: string | null;
  kind: SupplierKind;
  status: "ACTIVE" | "PENDING" | "REJECTED" | "INACTIVE";
  default_account_id: string | null;
  pix_key_type: PixKeyType | null;
  pix_key: string | null;
  bank_code: string | null;
  bank_agency: string | null;
  bank_account: string | null;
  review_note: string | null;
  created_at: string;
  similar: SupplierRef[];
  shared_account: SupplierRef[];
  open_titles: number;
}

export interface SupplierInput {
  tax_id: string;
  legal_name: string;
  trade_name: string | null;
  kind: SupplierKind;
  default_account_id: string | null;
  pix_key_type: PixKeyType | null;
  pix_key: string | null;
  bank_code: string | null;
  bank_agency: string | null;
  bank_account: string | null;
}

export interface TitleRow {
  id: string;
  number: number;
  kind: TitleKind;
  status: TitleStatus;
  unit_id: string;
  unit_name: string;
  supplier_id: string;
  supplier_name: string;
  supplier_tax_id: string;
  account_code: string;
  account_label: string;
  document_type: DocumentType | null;
  document_number: string | null;
  installment_number: number;
  installment_count: number;
  amount: string;
  competence: string;
  due_date: string;
  description: string;
  vehicle_plates: string[];
  attachment_count: number;
  blocking: number;
  attention: number;
  submitted_at: string;
  /** "PIX CNPJ", "Boleto" or "Transferência". */
  payment_method: string;
  top_issue: string | null;
  top_issue_severity: Severity | null;
}

export interface CheckView {
  code: string;
  severity: Severity;
  title: string;
  detail: string;
  subject: string;
  decided: boolean;
  decidable: boolean;
  decision_reason: string | null;
}

export interface AttachmentView {
  id: string;
  role: AttachmentRole;
  original_name: string;
  stored_name: string;
  content_type: string;
  size_bytes: number;
  read_kind: string | null;
  read_amount: string | null;
  read_tax_id: string | null;
  read_document_number: string | null;
  read_due_date: string | null;
  /** FILE: stated by the file itself; AI: read by a model, to confirm. */
  read_source: ReadSource | null;
  created_at: string;
}

export interface EventView {
  id: string;
  action: string;
  from_status: TitleStatus | null;
  to_status: TitleStatus | null;
  reason: string | null;
  actor: string | null;
  created_at: string;
}

export interface RelatedTitle {
  id: string;
  number: number;
  unit_name: string;
  installment_number: number;
  installment_count: number;
  amount: string;
  due_date: string;
  status: TitleStatus;
}

export interface TitleDetail extends TitleRow {
  account_id: string;
  issue_date: string | null;
  purchase_total: string;
  destination_kind: DestinationKind;
  destination_note: string | null;
  zeev_request: string | null;
  estimate_until: string | null;
  replaces_estimate_id: string | null;
  replaced_by_id: string | null;
  ng_reference: string | null;
  created_by: string | null;
  supplier: Supplier;
  attachments: AttachmentView[];
  checks: CheckView[];
  events: EventView[];
  same_document: RelatedTitle[];
  can_edit: boolean;
  actions: TitleAction[];
  confirmations: Confirmation[];
  /** Ready text for the NG "Histórico" field. */
  ng_history: string;
}

export interface Confirmation {
  label: string;
  value: string;
  state: "OK" | "ATTENTION" | "MISMATCH" | "UNKNOWN";
}

export type ReadSource = "FILE" | "AI";

export interface DocumentRead {
  /** NOTA: a note read from a PDF or photo (DANFE key or AI). */
  kind: "XML" | "NOTA" | "BOLETO" | "PDF" | null;
  source: ReadSource | null;
  amount: string | null;
  tax_id: string | null;
  tax_id_display: string | null;
  document_type: DocumentType | null;
  document_number: string | null;
  issue_date: string | null;
  due_date: string | null;
  issuer_name: string | null;
  installments: { number: number; due_date: string; amount: string }[];
  supplier: SupplierRef | null;
  supplier_status: Supplier["status"] | null;
}

export interface BatchResult {
  done: string[];
  failed: { id: string; number: number; message: string }[];
}

export async function readDocument(file: File): Promise<DocumentRead> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${PAYABLES_API}/read-document`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) await readError(response);
  // SAFETY: the endpoint returns the DocumentReadView on 2xx.
  return (await response.json()) as DocumentRead;
}

/** POST the ids and save the file the server returns. */
export async function downloadForTitles(
  path: "/titles/payment-batch" | "/titles/attachments-zip",
  ids: string[],
  fallbackName: string
): Promise<void> {
  const response = await fetch(`${PAYABLES_API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!response.ok) await readError(response);
  const blob = await response.blob();
  const header = response.headers.get("Content-Disposition") ?? "";
  const match = /filename\*=UTF-8''([^;]+)/.exec(header);
  const name = match?.[1] ? decodeURIComponent(match[1]) : fallbackName;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

/** The order the list showed, so the detail page can go to the next title. */
const QUEUE_KEY = "ton.payables.queue";

export function rememberQueue(ids: string[]): void {
  try {
    sessionStorage.setItem(QUEUE_KEY, JSON.stringify(ids));
  } catch {
    // Private windows may refuse storage; navigation then stays per title.
  }
}

export function queueNeighbours(id: string): {
  previous: string | null;
  next: string | null;
} {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(QUEUE_KEY) ?? "[]");
    const ids = Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string")
      : [];
    const index = ids.indexOf(id);
    if (index < 0) return { previous: null, next: null };
    return {
      previous: ids[index - 1] ?? null,
      next: ids[index + 1] ?? null,
    };
  } catch {
    return { previous: null, next: null };
  }
}

export interface TitleInput {
  unit_id: string;
  kind: TitleKind;
  supplier_id: string;
  account_id: string;
  document_type: DocumentType | null;
  document_number: string | null;
  issue_date: string | null;
  competence: string;
  due_date: string;
  installment_number: number;
  installment_count: number;
  purchase_total: string;
  amount: string;
  destination_kind: DestinationKind;
  vehicle_plates: string[];
  destination_note: string | null;
  description: string;
  zeev_request: string | null;
  estimate_until: string | null;
  replaces_estimate_id: string | null;
}

export const STATUS: Record<TitleStatus, { label: string; tone: TonTone }> = {
  WAITING_ATTACHMENT: { label: "Falta anexo", tone: "warning" },
  WAITING_SUPPLIER: { label: "Fornecedor em aprovação", tone: "warning" },
  RECEIVED: { label: "Para conferir", tone: "brand" },
  RETURNED: { label: "Devolvido à unidade", tone: "danger" },
  CONFERRED: { label: "Conferido", tone: "info" },
  RELEASED: { label: "Liberado para pagar", tone: "success" },
  BOOKED: { label: "Lançado no NG", tone: "success" },
  PAID: { label: "Pago", tone: "success" },
  ESTIMATE_OPEN: { label: "Estimativa", tone: "neutral" },
  ESTIMATE_REPLACED: { label: "Estimativa substituída", tone: "neutral" },
  CANCELLED: { label: "Cancelado", tone: "neutral" },
};

export const CLOSED_STATUSES: TitleStatus[] = [
  "BOOKED",
  "PAID",
  "CANCELLED",
  "ESTIMATE_REPLACED",
];

export interface Stage {
  key: string;
  label: string;
  statuses: TitleStatus[] | null;
}

export const STAGES: Stage[] = [
  {
    key: "abertos",
    label: "Em aberto",
    statuses: [
      "WAITING_ATTACHMENT",
      "WAITING_SUPPLIER",
      "RECEIVED",
      "RETURNED",
      "CONFERRED",
      "RELEASED",
    ],
  },
  { key: "conferir", label: "Para conferir", statuses: ["RECEIVED"] },
  {
    key: "unidade",
    label: "Com a unidade",
    statuses: ["WAITING_ATTACHMENT", "WAITING_SUPPLIER", "RETURNED"],
  },
  { key: "conferidos", label: "Conferidos", statuses: ["CONFERRED"] },
  { key: "liberados", label: "Liberados", statuses: ["RELEASED"] },
  { key: "lancados", label: "Lançados no NG", statuses: ["BOOKED", "PAID"] },
  { key: "estimativas", label: "Estimativas", statuses: ["ESTIMATE_OPEN"] },
  { key: "todos", label: "Todos", statuses: null },
];

export const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "NF", label: "NF (produto)" },
  { value: "NFSE", label: "NFS-e (serviço)" },
  { value: "FATURA", label: "Fatura" },
  { value: "RECIBO", label: "Recibo" },
  { value: "BOLETO", label: "Boleto sem nota" },
  { value: "CONTRATO", label: "Contrato" },
  { value: "OUTRO", label: "Outro" },
];

export const DOC_SHORT: Record<DocumentType, string> = {
  NF: "NF",
  NFSE: "NFS-e",
  FATURA: "Fatura",
  RECIBO: "Recibo",
  BOLETO: "Boleto",
  CONTRATO: "Contrato",
  OUTRO: "Doc.",
};

export const DESTINATIONS: { value: DestinationKind; label: string }[] = [
  { value: "VEHICLE", label: "Veículo" },
  { value: "SITE", label: "Obra ou local" },
  { value: "STOCK", label: "Estoque" },
  { value: "ADMINISTRATION", label: "Administração" },
];

export const SUPPLIER_KINDS: { value: SupplierKind; label: string }[] = [
  { value: "COMPANY", label: "Empresa" },
  { value: "PERSON", label: "Pessoa física" },
  { value: "EMPLOYEE", label: "Funcionário" },
  { value: "PUBLIC_BODY", label: "Órgão público" },
];

export const PIX_TYPES: { value: PixKeyType; label: string }[] = [
  { value: "CNPJ", label: "CNPJ" },
  { value: "CPF", label: "CPF" },
  { value: "EMAIL", label: "E-mail" },
  { value: "PHONE", label: "Telefone" },
  { value: "RANDOM", label: "Chave aleatória" },
];

export const ROLES: { value: AttachmentRole; label: string }[] = [
  { value: "INVOICE", label: "Nota fiscal" },
  { value: "BOLETO", label: "Boleto" },
  { value: "RECEIPT", label: "Recibo" },
  { value: "OTHER", label: "Outro" },
];

export const SUPPLIER_STATUS: Record<
  Supplier["status"],
  { label: string; tone: TonTone }
> = {
  ACTIVE: { label: "Aprovado", tone: "success" },
  PENDING: { label: "Em aprovação", tone: "warning" },
  REJECTED: { label: "Recusado", tone: "danger" },
  INACTIVE: { label: "Inativo", tone: "neutral" },
};

export const EVENT_LABEL: Record<string, string> = {
  SUBMITTED: "Enviado pela unidade",
  EDITED: "Alterado",
  ATTACHED: "Anexo incluído",
  DETACHED: "Anexo removido",
  RESUBMITTED: "Reenviado pela unidade",
  SUPPLIER_REVIEWED: "Fornecedor revisado",
  CONFER: "Conferido",
  RETURN: "Devolvido à unidade",
  RELEASE: "Liberado para pagar",
  UNDO_RELEASE: "Liberação desfeita",
  BOOK: "Lançado no NG",
  CANCEL: "Cancelado",
  REPLACED: "Substituída pela conta real",
  REOPENED: "Estimativa reaberta",
  CHECK_DECIDED: "Conferência dispensada",
};

export const ACTION_LABEL: Record<TitleAction, string> = {
  RESUBMIT: "Reenviar ao financeiro",
  CONFER: "Marcar como conferido",
  RETURN: "Devolver à unidade",
  RELEASE: "Liberar para pagar",
  UNDO_RELEASE: "Desfazer liberação",
  BOOK: "Registrar lançamento no NG",
  CANCEL: "Cancelar título",
};

export const ACTION_DONE: Record<TitleAction, string> = {
  RESUBMIT: "Título reenviado ao financeiro.",
  CONFER: "Título conferido.",
  RETURN: "Título devolvido à unidade.",
  RELEASE: "Título liberado para pagamento.",
  UNDO_RELEASE: "Liberação desfeita.",
  BOOK: "Lançamento no NG registrado.",
  CANCEL: "Título cancelado.",
};

/** A PIX key as people read it: CPF and CNPJ keys get their mask. */
export function pixText(type: PixKeyType | null, key: string): string {
  return type === "CPF" || type === "CNPJ" ? maskTaxId(key) : key;
}

const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

export function brl(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? BRL.format(number) : "—";
}

/** "1.582,80", "1582.80" or "R$ 1.582,80" as a number; null when unreadable. */
export function parseMoney(text: string): number | null {
  const cleaned = text.replace(/R\$|\s/g, "");
  if (!cleaned) return null;
  const normalized = cleaned.includes(",")
    ? cleaned.replace(/\./g, "").replace(",", ".")
    : cleaned;
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) return null;
  const value = Number(normalized);
  return Number.isFinite(value) && value > 0 ? value : null;
}

export function moneyInput(value: number): string {
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** ISO date (yyyy-mm-dd) as dd/mm/aaaa, without time-zone drift. */
export function brDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [year, month, day] = iso.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

export function brDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const MONTHS = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];

export function monthLabel(iso: string): string {
  const [year, month] = iso.split("-");
  return `${MONTHS[Number(month) - 1]} de ${year}`;
}

export function shortMonth(iso: string): string {
  const [year, month] = iso.split("-");
  return `${MONTHS[Number(month) - 1]?.slice(0, 3)}/${year?.slice(2)}`;
}

/** First days of the months around today, newest first, for the competência. */
export function competenceOptions(today = new Date()): string[] {
  const options: string[] = [];
  for (let offset = 1; offset >= -14; offset--) {
    const date = new Date(today.getFullYear(), today.getMonth() + offset, 1);
    options.push(
      `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-01`
    );
  }
  return options;
}

export function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function titleNumber(number: number): string {
  return `CP-${String(number).padStart(6, "0")}`;
}

export function documentText(row: {
  document_type: DocumentType | null;
  document_number: string | null;
}): string {
  if (!row.document_number) return "Sem documento";
  return `${row.document_type ? DOC_SHORT[row.document_type] : "Doc."} ${row.document_number}`;
}

/** Brazilian plate without hyphen or space; null when it is not one. */
export function normalizePlate(text: string): string | null {
  const candidate = text.toUpperCase().replace(/[^A-Z0-9]/g, "");
  return /^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/.test(candidate) ? candidate : null;
}

export function formatPlate(value: string): string {
  return `${value.slice(0, 3)}-${value.slice(3)}`;
}

/** Digits of a CPF or CNPJ, formatted while the person types. */
export function maskTaxId(text: string): string {
  const digits = text.replace(/\D/g, "").slice(0, 14);
  if (digits.length <= 11) {
    return digits
      .replace(/^(\d{3})(\d)/, "$1.$2")
      .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/\.(\d{3})(\d{1,2})$/, ".$1-$2");
  }
  return digits
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
}

function checkDigitsOk(digits: string): boolean {
  if (/^(\d)\1+$/.test(digits)) return false;
  const numbers = digits.split("").map(Number);
  const at = (index: number) => numbers[index] ?? 0;
  if (digits.length === 11) {
    for (const size of [9, 10]) {
      let total = 0;
      for (let index = 0; index < size; index++)
        total += at(index) * (size + 1 - index);
      if (((total * 10) % 11) % 10 !== numbers[size]) return false;
    }
    return true;
  }
  if (digits.length === 14) {
    const base = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    for (const size of [12, 13]) {
      const weights = size === 12 ? base : [6, ...base];
      let total = 0;
      for (let index = 0; index < size; index++)
        total += at(index) * (weights[index] ?? 0);
      const rest = total % 11;
      if ((rest < 2 ? 0 : 11 - rest) !== numbers[size]) return false;
    }
    return true;
  }
  return false;
}

export function validTaxId(text: string): boolean {
  return checkDigitsOk(text.replace(/\D/g, ""));
}

/** The attachment role a file name suggests. */
export function guessRole(name: string): AttachmentRole {
  const lower = name.toLowerCase();
  if (lower.includes("boleto") || lower.includes("bol_")) return "BOLETO";
  if (lower.includes("recibo") || lower.includes("comprovante")) return "RECEIPT";
  return "INVOICE";
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
}

export function daysUntil(iso: string): number {
  const [year = 0, month = 1, day = 1] = iso.split("-").map(Number);
  const due = new Date(year, month - 1, day);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((due.getTime() - today.getTime()) / 86_400_000);
}

export function usePayablesContext() {
  return useSWR<PayablesContext>(`${PAYABLES_API}/context`, errorHandlingFetcher);
}

export function useTitles() {
  return useSWR<TitleRow[]>(
    `${PAYABLES_API}/titles?limit=2000`,
    errorHandlingFetcher
  );
}

export function useTitle(id: string | null) {
  return useSWR<TitleDetail>(
    id ? `${PAYABLES_API}/titles/${id}` : null,
    errorHandlingFetcher
  );
}

export function useSuppliers() {
  return useSWR<Supplier[]>(`${PAYABLES_API}/suppliers`, errorHandlingFetcher);
}

async function readError(response: Response): Promise<never> {
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

export async function payablesJson<T>(
  method: "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  const response = await fetch(`${PAYABLES_API}${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) await readError(response);
  // SAFETY: TON endpoints return the declared Pydantic view on 2xx.
  return (await response.json()) as T;
}

export async function uploadAttachment(
  titleId: string,
  file: File,
  role: AttachmentRole
): Promise<TitleDetail> {
  const form = new FormData();
  form.append("role", role);
  form.append("file", file);
  const response = await fetch(
    `${PAYABLES_API}/titles/${titleId}/attachments`,
    { method: "POST", body: form }
  );
  if (!response.ok) await readError(response);
  // SAFETY: the endpoint returns the TitleDetail view on 2xx.
  return (await response.json()) as TitleDetail;
}

export function attachmentUrl(titleId: string, attachmentId: string): string {
  return `${PAYABLES_API}/titles/${titleId}/attachments/${attachmentId}?inline=true`;
}

export function errorText(error: unknown, fallback: string): string {
  return error instanceof TonApiError && error.detail ? error.detail : fallback;
}
