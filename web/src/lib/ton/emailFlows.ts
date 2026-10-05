"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";

export const EMAIL_FLOWS_API = "/api/ton/email-flows";

export type TriggerKind =
  | "SCHEDULE"
  | "NG_IMPORT_COMPLETED"
  | "NG_OCCURRENCE_CHANGED"
  | "ACCOUNT_UNCLASSIFIED"
  | "DRE_RECALCULATED";
export type FieldType = "TEXT" | "NUMBER" | "MONEY" | "CHOICE";
export type Operator = "EQ" | "IN" | "GT" | "GTE";
export type TemplateKey = "INCONSISTENCY_REPORT" | "ACCOUNT_LIST" | "SIMPLE_NOTICE";
export type ItemState =
  | "OPEN"
  | "NEW"
  | "REAPPEARED"
  | "CHECK_MANUALLY"
  | "CORRECTED";
export type FlowOrigin = "USER" | "TON_SUGGESTED" | "SYSTEM";
export type FlowStatus = "SUGGESTED" | "ACTIVE" | "PAUSED" | "DISCARDED";
export type FlowBranch = "YES" | "NO";
export type RunStatus =
  | "RUNNING"
  | "SENT"
  | "SILENT"
  | "PARTIAL"
  | "FAILED"
  | "NOT_CONFIGURED";
export type DeliveryStatus = "SENT" | "FAILED" | "NOT_CONFIGURED";

export interface FlowTrigger {
  kind: TriggerKind;
  frequency: "WEEKLY" | "DAILY" | null;
  weekday: number | null;
  time: string | null;
  changes: ItemState[];
}

export interface ConditionClause {
  field: string;
  operator: Operator;
  value: string | number | string[];
}

export interface EmailAction {
  kind: "EMAIL" | "NONE";
  to: string[];
  cc: string[];
  bcc: string[];
  subject: string;
  template: TemplateKey | null;
}

export interface FlowDefinition {
  trigger: FlowTrigger;
  conditions: ConditionClause[];
  on_yes: EmailAction;
  on_no: EmailAction;
}

export interface DeliveryView {
  id: string;
  status: DeliveryStatus;
  provider: string | null;
  to: string[];
  cc: string[];
  bcc: string[];
  batch_no: number;
  batch_count: number;
  subject: string;
  error: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface RunView {
  id: string;
  version: number;
  event_key: string;
  branch: FlowBranch | null;
  status: RunStatus;
  is_test: boolean;
  item_count: number;
  reason: string | null;
  started_at: string;
  finished_at: string | null;
  deliveries: DeliveryView[];
}

export interface FlowSummary {
  id: string;
  name: string;
  origin: FlowOrigin;
  status: FlowStatus;
  version: number;
  definition: FlowDefinition;
  when: string;
  condition: string;
  on_yes: string;
  on_no: string;
  suggestion_reason: string | null;
  last_run: RunView | null;
  next_run_at: string | null;
  updated_at: string;
}

export interface FlowDetail extends FlowSummary {
  runs: RunView[];
  created_by: string | null;
  approved_by: string | null;
  approved_at: string | null;
}

export interface FlowTable {
  flows: FlowSummary[];
  can_manage: boolean;
  provider_ready: boolean;
}

export interface FieldView {
  key: string;
  label: string;
  type: FieldType;
  per_item: boolean;
  operators: Operator[];
  choices: [string, string][];
}

export interface TriggerView {
  kind: TriggerKind;
  label: string;
  description: string;
  fields: FieldView[];
  templates: TemplateKey[];
}

export interface CatalogView {
  triggers: TriggerView[];
  templates: Record<TemplateKey, string>;
  operators: Record<Operator, string>;
  subject_markers: Record<string, string>;
  changes: [ItemState, string][];
  provider: string | null;
  provider_ready: boolean;
  sender: string | null;
}

export interface PreviewView {
  branch: FlowBranch;
  reason: string;
  item_count: number;
  subject: string | null;
  html: string | null;
  to: string[];
  cc: string[];
  bcc: string[];
  batches: number;
}

export interface SuggestionRunResult {
  created: number;
  skipped: string[];
  model_name: string | null;
}

export function useFlowTable() {
  return useSWR<FlowTable>(EMAIL_FLOWS_API, errorHandlingFetcher);
}

export function useFlowDetail(flowId: string | null) {
  return useSWR<FlowDetail>(
    flowId ? `${EMAIL_FLOWS_API}/${flowId}` : null,
    errorHandlingFetcher
  );
}

export function useFlowCatalog() {
  return useSWR<CatalogView>(`${EMAIL_FLOWS_API}/catalog`, errorHandlingFetcher, {
    revalidateOnFocus: false,
  });
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      const first = body.detail[0] as { msg?: string };
      return (first.msg ?? "").replace(/^Value error, /, "");
    }
  } catch {
    // fall through
  }
  return `HTTP ${response.status}`;
}

export interface FlowSaveBody {
  name: string;
  definition: FlowDefinition;
  activate?: boolean;
}

export interface FlowPreviewBody {
  flow_id?: string;
  definition?: FlowDefinition;
  branch?: FlowBranch;
}

/** Bodies the flows API accepts; actions without input send `{}`. */
export type FlowRequestBody = FlowSaveBody | FlowPreviewBody | Record<string, never>;

export async function sendJson<T>(
  url: string,
  body: FlowRequestBody,
  method: "POST" | "PUT" = "POST"
): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as T;
}

export function emptyAction(): EmailAction {
  return { kind: "NONE", to: [], cc: [], bcc: [], subject: "", template: null };
}

export function emailAction(template: TemplateKey): EmailAction {
  return {
    kind: "EMAIL",
    to: [],
    cc: [],
    bcc: [],
    subject: "TON – {data} ({total})",
    template,
  };
}

export function newDefinition(): FlowDefinition {
  return {
    trigger: {
      kind: "NG_IMPORT_COMPLETED",
      frequency: null,
      weekday: null,
      time: null,
      changes: [],
    },
    conditions: [{ field: "itens", operator: "GT", value: 0 }],
    on_yes: emailAction("INCONSISTENCY_REPORT"),
    on_no: emptyAction(),
  };
}

/** "a@x.com, b@x.com; c@x.com" -> list. */
export function parseAddresses(value: string): string[] {
  return value
    .split(/[,;\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export const WEEKDAYS = [
  "segunda",
  "terça",
  "quarta",
  "quinta",
  "sexta",
  "sábado",
  "domingo",
];

export const EMAIL_FLOWS_COPY = {
  eyebrow: "Automações",
  title: "Fluxos de e-mail",
  description:
    "Quando algo acontece no TON, o fluxo confere a condição e manda o e-mail certo. Sugestões do TON só valem depois que alguém cadastra.",
  adminEntry: {
    title: "Fluxos de e-mail",
    description: "Aconteceu tal coisa? Sim → manda este e-mail. Não → faz aquilo.",
  },
  newFlow: "Novo fluxo",
  suggest: "Pedir sugestões ao TON",
  suggesting: "Pensando…",
  suggested: (count: number) =>
    count === 0
      ? "O TON não encontrou fluxos novos para sugerir."
      : `${count} ${count === 1 ? "sugestão nova" : "sugestões novas"} na tabela.`,
  noAccessTitle: "Acesso restrito",
  noAccess: "Ver fluxos exige a permissão de leitura de relatórios do TON.",
  loading: "Carregando fluxos",
  error: "Não foi possível carregar os fluxos.",
  empty: "Nenhum fluxo ainda.",
  providerMissing:
    "O envio de e-mail ainda não está configurado neste ambiente. Os fluxos rodam, a prévia funciona e cada e-mail fica guardado no histórico como “não configurado”.",
  columns: {
    flow: "Fluxo",
    when: "Quando",
    condition: "Se",
    yes: "Então",
    no: "Senão",
    lastRun: "Último envio",
    status: "Estado",
  },
  status: {
    SUGGESTED: "Sugerido pelo TON",
    ACTIVE: "Ativo",
    PAUSED: "Pausado",
    DISCARDED: "Descartado",
  } satisfies Record<FlowStatus, string>,
  runStatus: {
    RUNNING: "rodando",
    SENT: "enviado",
    SILENT: "nada a enviar",
    PARTIAL: "enviado em parte",
    FAILED: "falhou",
    NOT_CONFIGURED: "não configurado",
  } satisfies Record<RunStatus, string>,
  deliveryStatus: {
    SENT: "enviado",
    FAILED: "falhou",
    NOT_CONFIGURED: "não configurado",
  } satisfies Record<DeliveryStatus, string>,
  register: "Cadastrar",
  discard: "Descartar",
  never: "—",
  test: "teste",
  back: "Fluxos",
  editor: {
    newTitle: "Novo fluxo",
    namePlaceholder: "Nome do fluxo",
    version: (version: number) => `Versão ${version}`,
    save: "Salvar",
    saving: "Salvando…",
    saved: "Salvo.",
    activate: "Ativar",
    register: "Cadastrar",
    pause: "Pausar",
    discard: "Descartar",
    preview: "Ver prévia",
    sendToMe: "Enviar só para mim",
    sending: "Enviando…",
    testSent: (status: string) => `Teste: ${status}.`,
    unsaved: "Alterações não salvas",
    suggestedBy: "Sugerido pelo TON",
    builder: "Construtor",
    builderHint: "Clique num bloco do fluxo para editar. Um bloco do catálogo troca o tipo do bloco selecionado.",
    trigger: "Gatilho",
    condition: "Condição",
    action: "Ação",
    yes: "Sim",
    no: "Não",
    always: "Sempre",
    nothing: "Não fazer nada",
    sendEmail: "Enviar e-mail",
    addCondition: "+ condição",
    remove: "Remover",
    frequency: "Frequência",
    weekly: "Toda semana",
    daily: "Todo dia",
    weekday: "Dia",
    time: "Horário (Brasília)",
    changes: "Mudanças",
    field: "Campo",
    operator: "Operador",
    value: "Valor",
    to: "Para",
    cc: "Cc",
    bcc: "Cco (opcional)",
    addressesHint: "Separe os e-mails por vírgula. Sai um único e-mail com todos juntos.",
    subject: "Assunto",
    markers: (markers: string) => `Marcadores: ${markers}`,
    template: "Modelo",
    history: "Histórico",
    noRuns: "Ainda não rodou.",
    historyColumns: {
      date: "Data",
      branch: "Ramo",
      items: "Itens",
      recipients: "Para / Cc / Cco",
      batch: "Lote",
      status: "Situação",
    },
    openEmail: "abrir e-mail",
    previewTitle: "Prévia do e-mail",
    previewBranch: (branch: string, reason: string, items: number) =>
      `Ramo ${branch} · ${reason} · ${items} ${items === 1 ? "item" : "itens"}`,
    previewNothing: "Neste caso o fluxo não envia nada.",
    previewRecipients: (to: number, cc: number, bcc: number, batches: number) =>
      `${to} em Para, ${cc} em Cc, ${bcc} em Cco · ${batches} ${batches === 1 ? "mensagem" : "mensagens"}`,
    closePreview: "Fechar prévia",
    approvedBy: (who: string, when: string) => `Cadastrado por ${who} em ${when}`,
    nextRun: (when: string) => `Próxima execução: ${when}`,
  },
};
