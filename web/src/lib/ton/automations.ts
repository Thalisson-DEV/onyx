"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";

export const AUTOMATIONS_API = "/api/ton/automations";

// ---------------------------------------------------------------------------
// Definition (v3)
// ---------------------------------------------------------------------------

export type AutomationKind = "EMAIL" | "ALERT" | "ROUTINE" | "APPROVAL" | "DATA_AI" | "GENERAL";
export type AutomationStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "ARCHIVED";
export type AutomationOrigin = "USER" | "TON_SUGGESTED" | "SYSTEM" | "MIGRATED";
export type RunStatus = "QUEUED" | "RUNNING" | "WAITING" | "SUCCEEDED" | "FAILED" | "CANCELLED" | "TIMED_OUT";
export type RunMode = "LIVE" | "MANUAL" | "TEST" | "RESUBMIT";
export type StepStatus = "RUNNING" | "WAITING" | "SUCCEEDED" | "FAILED" | "SKIPPED" | "TIMED_OUT" | "CANCELLED";
export type RunAfter = "succeeded" | "failed" | "skipped" | "timed_out";
export type ContainerKind = "condition" | "switch" | "loop" | "until" | "scope" | "parallel";

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
export type Params = Record<string, JsonValue>;

export interface RetryPolicy {
  policy: "none" | "fixed" | "exponential";
  count: number;
  interval_seconds: number;
}

export interface Case {
  id: string;
  value: string;
  steps: FlowNode[];
}

export interface Branch {
  id: string;
  label: string;
  steps: FlowNode[];
}

export interface FlowNode {
  id: string;
  type: string;
  label?: string;
  description?: string;
  params: Params;
  run_after?: RunAfter[];
  retry?: RetryPolicy | null;
  timeout_seconds?: number | null;
  then?: FlowNode[];
  else?: FlowNode[];
  cases?: Case[];
  default?: FlowNode[];
  steps?: FlowNode[];
  branches?: Branch[];
}

export interface TriggerConfig {
  type: string;
  params: Params;
  label?: string;
}

export interface VariableDecl {
  name: string;
  type: "string" | "number" | "boolean" | "array" | "object";
  value: JsonValue;
  description?: string;
}

export interface Settings {
  notify_on_failure: string[];
  timeout_hours: number;
}

export interface Definition {
  schema: 3;
  trigger: TriggerConfig;
  variables: VariableDecl[];
  steps: FlowNode[];
  settings: Settings;
}

// ---------------------------------------------------------------------------
// Catalog
// ---------------------------------------------------------------------------

export type ParamKind =
  | "text"
  | "textarea"
  | "number"
  | "boolean"
  | "select"
  | "multiselect"
  | "emails"
  | "condition"
  | "html"
  | "json"
  | "fields"
  | "mapping"
  | "columns"
  | "keyvalue"
  | "list"
  | "time"
  | "weekdays"
  | "file"
  | "expression"
  | "automations";

export interface FieldView {
  key: string;
  label: string;
  kind: "text" | "select" | "boolean" | "expression";
  options: [string, string][];
  placeholder: string | null;
}

export interface ParamView {
  key: string;
  label: string;
  kind: ParamKind;
  required: boolean;
  default: JsonValue;
  help: string | null;
  placeholder: string | null;
  options: [string, string][];
  dynamic: boolean;
  min: number | null;
  max: number | null;
  item_fields: FieldView[];
  show_if: [string, string[]] | null;
  advanced: boolean;
}

export interface OutputView {
  key: string;
  label: string;
  type: "string" | "number" | "boolean" | "array" | "object" | "any";
  description: string;
  item_fields: OutputView[];
}

export type NodeGroup = "trigger" | "control" | "variables" | "data" | "ai" | "ton" | "email" | "approval" | "integration";

export interface NodeTypeView {
  type: string;
  group: NodeGroup;
  label: string;
  description: string;
  icon: string;
  params: ParamView[];
  outputs: OutputView[];
  container: ContainerKind | null;
  is_trigger: boolean;
  side_effect: boolean;
  ai: boolean;
  satisfies: AutomationKind[];
  dynamic_outputs: string | null;
  default_retry: RetryPolicy;
  keywords: string[];
}

export interface KindView {
  key: AutomationKind;
  label: string;
  description: string;
}

export interface TemplateView {
  key: string;
  name: string;
  description: string;
  kind: AutomationKind;
  trigger_type: string;
}

export interface CatalogView {
  nodes: NodeTypeView[];
  groups: Record<string, string>;
  kinds: KindView[];
  templates: TemplateView[];
  functions: Record<string, string>;
  operators: Record<string, string>;
  blocks: Record<string, string>;
  assets: { id: string; name: string }[];
  automations: { id: string; name: string }[];
  provider_ready: boolean;
  sender: string | null;
  llm_ready: boolean;
}

// ---------------------------------------------------------------------------
// Views
// ---------------------------------------------------------------------------

export interface Issue {
  severity: "error" | "warning";
  message: string;
  node_id: string | null;
  param: string | null;
}

export interface RunSummary {
  id: string;
  status: RunStatus;
  mode: RunMode;
  trigger_key: string;
  version: number | null;
  error: string | null;
  message: string | null;
  waiting_on: string | null;
  resume_at: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  triggered_by: string | null;
}

export interface AutomationSummary {
  id: string;
  name: string;
  description: string | null;
  kind: AutomationKind;
  status: AutomationStatus;
  origin: AutomationOrigin;
  trigger_type: string;
  trigger_label: string;
  when: string;
  version: number;
  steps_count: number;
  last_run: RunSummary | null;
  next_run_at: string | null;
  runs_28d: Partial<Record<RunStatus, number>>;
  problems: string[];
  suggestion_reason: string | null;
  updated_at: string;
}

export interface ApprovalView {
  id: string;
  automation_id: string;
  automation_name: string;
  run_id: string;
  node_id: string;
  title: string;
  details: string | null;
  options: string[];
  approvers: string[];
  status: "PENDING" | "DONE" | "EXPIRED" | "CANCELLED";
  outcome: string | null;
  comment: string | null;
  decided_by: string | null;
  decided_at: string | null;
  expires_at: string | null;
  created_at: string;
  can_decide: boolean;
}

export interface AutomationTable {
  automations: AutomationSummary[];
  approvals: ApprovalView[];
  can_manage: boolean;
  provider_ready: boolean;
}

export interface VersionView {
  version: number;
  name: string;
  note: string | null;
  created_by: string | null;
  created_at: string;
}

export interface AutomationDetail extends AutomationSummary {
  definition: Definition;
  issues: Issue[];
  owner: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  active_since: string | null;
  versions: VersionView[];
  runs: RunSummary[];
  can_manage: boolean;
  average_duration_ms: number | null;
}

export interface StepView {
  node_id: string;
  iteration: string;
  node_type: string;
  status: StepStatus;
  attempt: number;
  inputs: Record<string, JsonValue> | null;
  outputs: Record<string, JsonValue> | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  next_retry_at: string | null;
  duration_ms: number | null;
}

export interface RunDetail extends RunSummary {
  automation_id: string;
  automation_name: string;
  definition: Definition;
  trigger_output: Record<string, JsonValue>;
  steps: StepView[];
  approvals: ApprovalView[];
  can_cancel: boolean;
  can_resubmit: boolean;
}

export interface ValidateResult {
  issues: Issue[];
  problems: string[];
  structure_error: string | null;
  suggested_kind: AutomationKind | null;
}

export interface DraftResult {
  automation_id: string;
  name: string;
  kind: AutomationKind;
  status: AutomationStatus;
  created: boolean;
  summary: string;
  when: string;
  steps_text: string[];
  problems: string[];
  missing: string[];
  editor_url: string;
  definition?: Definition;
}

export interface PreviewResult {
  subject: string | null;
  html: string | null;
  reason: string;
}

export interface NoticeView {
  id: string;
  automation_id: string;
  automation_name: string;
  run_id: string | null;
  title: string;
  message: string | null;
  severity: "INFO" | "WARNING" | "CRITICAL";
  link: string | null;
  created_at: string;
}

export interface FileView {
  id: string;
  name: string;
  size_bytes: number;
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

export function useAutomationTable() {
  return useSWR<AutomationTable>(AUTOMATIONS_API, errorHandlingFetcher);
}

export function useAutomation(id: string | null) {
  return useSWR<AutomationDetail>(id ? `${AUTOMATIONS_API}/${id}` : null, errorHandlingFetcher);
}

export function useAutomationCatalog() {
  return useSWR<CatalogView>(`${AUTOMATIONS_API}/catalog`, errorHandlingFetcher, { revalidateOnFocus: false });
}

const OPEN_RUN: RunStatus[] = ["QUEUED", "RUNNING", "WAITING"];

export function isOpenRun(status: RunStatus): boolean {
  return OPEN_RUN.includes(status);
}

export function useRun(id: string | null) {
  return useSWR<RunDetail>(id ? `${AUTOMATIONS_API}/runs/${id}` : null, errorHandlingFetcher, {
    refreshInterval: (data) => (!data || isOpenRun(data.status) ? 1500 : 0),
    revalidateOnMount: true,
    dedupingInterval: 500,
  });
}

export function useAutomationNotices(enabled = true) {
  return useSWR<NoticeView[]>(enabled ? `${AUTOMATIONS_API}/notices` : null, errorHandlingFetcher, {
    refreshInterval: 60_000,
  });
}

async function readError(response: Response): Promise<string> {
  try {
    const body: { detail?: unknown } = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      const first: { msg?: string; loc?: unknown[] } = body.detail[0];
      return (first.msg ?? "").replace(/^Value error, /, "");
    }
  } catch {
    // fall through
  }
  return `HTTP ${response.status}`;
}

export interface SaveBody {
  name: string;
  description: string | null;
  kind: AutomationKind;
  definition: Definition;
  note?: string | null;
}

export type RequestBody =
  | SaveBody
  | { name: string; description?: string | null; kind?: AutomationKind; template?: string | null; definition?: Definition | null }
  | { status: AutomationStatus }
  | { inputs: Record<string, JsonValue> }
  | { definition: Definition; kind: AutomationKind }
  | { definition: Definition; node_id: string; automation_id?: string | null; name?: string | null }
  | { request: string; automation_id?: string | null; definition?: Definition | null }
  | { outcome: string; comment?: string | null }
  | Record<string, never>;

export async function send<T>(url: string, body: RequestBody, method: "POST" | "PUT" = "POST"): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function uploadFile(file: File): Promise<FileView> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${AUTOMATIONS_API}/files`, { method: "POST", body: form });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

// ---------------------------------------------------------------------------
// Copy
// ---------------------------------------------------------------------------

export const KIND_LABELS: Record<AutomationKind, string> = {
  EMAIL: "E-mail",
  ALERT: "Alerta",
  ROUTINE: "Rotina",
  APPROVAL: "Aprovação",
  DATA_AI: "Dados e IA",
  GENERAL: "Geral",
};

export const STATUS_LABELS: Record<AutomationStatus, string> = {
  DRAFT: "Rascunho",
  ACTIVE: "Ativa",
  PAUSED: "Pausada",
  ARCHIVED: "Arquivada",
};

export const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  QUEUED: "Na fila",
  RUNNING: "Executando",
  WAITING: "Aguardando",
  SUCCEEDED: "Sucesso",
  FAILED: "Falhou",
  CANCELLED: "Cancelada",
  TIMED_OUT: "Tempo esgotado",
};

export const STEP_STATUS_LABELS: Record<StepStatus, string> = {
  RUNNING: "Executando",
  WAITING: "Aguardando",
  SUCCEEDED: "Sucesso",
  FAILED: "Falhou",
  SKIPPED: "Ignorado",
  TIMED_OUT: "Tempo esgotado",
  CANCELLED: "Cancelado",
};

export const MODE_LABELS: Record<RunMode, string> = {
  LIVE: "Automática",
  MANUAL: "Manual",
  TEST: "Teste",
  RESUBMIT: "Reenvio",
};

export const RUN_AFTER_LABELS: Record<RunAfter, string> = {
  succeeded: "deu certo",
  failed: "falhou",
  skipped: "foi ignorado",
  timed_out: "esgotou o tempo",
};

export const COPY = {
  title: "Automações",
  description: "Tudo o que o TON faz sozinho: gatilho, passos e o histórico de cada execução.",
  newAutomation: "Nova automação",
  blank: "Em branco",
  blankHint: "Começar com o canvas vazio",
  fromTemplate: "A partir de um modelo",
  askTon: "Pedir ao TON",
  askTonHint: "Descreva a automação e o TON monta o rascunho",
  routines: "Rotinas do TON",
  all: "Todas",
  empty: "Nenhuma automação ainda.",
  emptyHint: "Crie do zero, a partir de um modelo ou peça ao TON no chat.",
  columns: {
    name: "Automação",
    kind: "Tipo",
    trigger: "Quando roda",
    status: "Situação",
    lastRun: "Última execução",
    runs: "28 dias",
  },
  never: "Nunca rodou",
  next: (when: string) => `Próxima: ${when}`,
  nextRun: "Próxima execução",
  approvalsTitle: "Aguardando sua decisão",
  approve: "Responder",
  comment: "Comentário (opcional)",
  steps: (count: number) => (count === 1 ? "1 passo" : `${count} passos`),
  problems: (count: number) => (count === 1 ? "1 pendência" : `${count} pendências`),
  name: "Nome",
  namePlaceholder: "Ex.: Relatório semanal ao Financeiro",
  create: "Criar",
  cancel: "Cancelar",
  draftPlaceholder:
    "Ex.: Toda segunda às 8h, envie ao financeiro@valenorte.com.br as inconsistências abertas do NG, separadas por unidade. Se alguma passar de R$ 100 mil, avise também a diretoria.",
  drafting: "O TON está montando o rascunho…",
  draftCreate: "Gerar rascunho",
  details: "Detalhes",
  edit: "Editar",
  run: "Executar",
  test: "Testar",
  activate: "Ativar",
  pause: "Pausar",
  archive: "Arquivar",
  restore: "Restaurar",
  duplicate: "Duplicar",
  history: "Histórico de 28 dias",
  allRuns: "Todas as execuções",
  noRuns: "Nenhuma execução nos últimos 28 dias.",
  start: "Início",
  duration: "Duração",
  mode: "Origem",
  owner: "Responsável",
  createdAt: "Criada",
  updatedAt: "Modificada",
  version: "Versão",
  versions: "Versões",
  averageDuration: "Duração média",
  successRate: "Execuções com sucesso",
  pending: "Antes de ativar",
  type: "Tipo",
  trigger: "Gatilho",
  status: "Situação",
  inputsTitle: "Executar automação",
  testTitle: "Testar automação",
  testHint: "No teste os e-mails vão só para você, as esperas são puladas e as aprovações são aprovadas automaticamente.",
  runHint: "A execução é real: e-mails, avisos e chamadas acontecem de verdade.",
  started: "Execução iniciada",
};

export const DESIGNER_COPY = {
  back: "Voltar",
  save: "Salvar",
  saving: "Salvando…",
  saved: "Salvo",
  unsaved: "Alterações não salvas",
  undo: "Desfazer",
  redo: "Refazer",
  checker: "Verificador",
  checkerOk: "Nenhum problema encontrado",
  errors: (count: number) => (count === 1 ? "1 erro" : `${count} erros`),
  warnings: (count: number) => (count === 1 ? "1 aviso" : `${count} avisos`),
  test: "Testar",
  ask: "Pedir ao TON",
  variables: "Variáveis",
  settings: "Configurações",
  addAction: "Adicionar ação",
  addTrigger: "Escolher o gatilho",
  search: "Buscar ação ou conector",
  noResults: "Nada encontrado",
  dropHere: "Solte aqui",
  addHere: "Adicionar aqui",
  emptyCanvas: "Escolha o gatilho e adicione os passos.",
  parameters: "Parâmetros",
  configuration: "Configurações",
  outputs: "Saídas",
  label: "Nome do passo",
  notes: "Anotação",
  runAfter: "Executar depois que o passo anterior",
  runAfterHint: "Use 'falhou' para tratar erros (tentar e tratar).",
  retry: "Tentar de novo quando falhar",
  retryPolicy: { none: "Não", fixed: "Intervalo fixo", exponential: "Intervalo crescente" } as const,
  retryCount: "Tentativas extras",
  retryInterval: "Intervalo (segundos)",
  timeout: "Tempo limite (segundos)",
  timeoutHint: "Vazio = padrão do passo.",
  duplicate: "Duplicar",
  remove: "Excluir",
  moveUp: "Subir",
  moveDown: "Descer",
  collapse: "Recolher",
  expand: "Expandir",
  actions: (count: number) => (count === 1 ? "1 ação" : `${count} ações`),
  yes: "Sim",
  no: "Não",
  otherwise: "Padrão",
  addCase: "Adicionar caso",
  addBranch: "Adicionar ramo",
  caseValue: "Valor",
  branchLabel: "Ramo",
  dynamic: "Conteúdo dinâmico",
  expression: "Expressão",
  functions: "Funções",
  insert: "Inserir",
  noOutputs: "Nenhum passo anterior tem saídas.",
  trigger: "Gatilho",
  currentItem: "Item atual",
  addRule: "Adicionar regra",
  addGroup: "Adicionar grupo",
  and: "e",
  or: "ou",
  removeRule: "Remover regra",
  addRow: "Adicionar",
  previewEmail: "Ver prévia",
  previewTitle: "Prévia do e-mail",
  upload: "Enviar arquivo",
  uploading: "Enviando…",
  variableName: "Nome",
  variableType: "Tipo",
  variableValue: "Valor inicial",
  addVariable: "Adicionar variável",
  variableTypes: { string: "Texto", number: "Número", boolean: "Sim/Não", array: "Lista", object: "Objeto" } as const,
  notifyOnFailure: "Avisar por e-mail quando uma execução falhar",
  timeoutHours: "Tempo máximo de uma execução (horas)",
  kind: "Tipo da automação",
  description: "Descrição",
  askPlaceholder: "Ex.: Depois de enviar o e-mail, espere 2 dias e, se ainda houver inconsistências, avise a diretoria.",
  askSubmit: "Aplicar",
  asking: "O TON está ajustando a automação…",
  askApplied: "Rascunho aplicado no canvas. Revise e salve.",
  required: "Obrigatório",
  advanced: "Avançado",
  closePanel: "Fechar painel",
  fit: "Ajustar à tela",
  zoomIn: "Aproximar",
  zoomOut: "Afastar",
  minimap: "Mapa",
  aiBadge: "IA",
  effectBadge: "Envia para fora",
  saveFirst: "Salve antes de testar",
  leaveConfirm: "Há alterações não salvas.",
  more: "Mais ações",
  edit: "Editar mensagem",
  done: "Concluir",
  providerMissing: "E-mail ainda não configurado no ambiente: o conteúdo fica guardado no TON até o provedor ser configurado.",
  llmMissing: "Nenhum modelo de IA configurado: este passo vai falhar até um provedor ser configurado.",
};

export const RUN_COPY = {
  succeeded: "A execução terminou com sucesso.",
  failed: "A execução falhou.",
  running: "Executando…",
  waiting: "Aguardando",
  queued: "Na fila de execução",
  cancelled: "A execução foi cancelada.",
  timedOut: "A execução passou do tempo limite.",
  resubmit: "Reenviar",
  cancel: "Cancelar",
  edit: "Editar",
  inputs: "Entradas",
  outputs: "Saídas",
  error: "Erro",
  attempts: (count: number) => `${count} tentativas`,
  notRun: "Este passo não rodou nesta execução.",
  iteration: "Repetição",
  openEmail: "Abrir e-mail enviado",
  triggerOutput: "Dados do gatilho",
  answer: "Responder aprovação",
};
