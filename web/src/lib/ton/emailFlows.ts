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
export type ItemState = "OPEN" | "NEW" | "REAPPEARED" | "CHECK_MANUALLY" | "CORRECTED";
export type FlowOrigin = "USER" | "TON_SUGGESTED" | "SYSTEM";
export type FlowStatus = "SUGGESTED" | "ACTIVE" | "PAUSED" | "DISCARDED";
export type RunStatus =
  | "RUNNING"
  | "WAITING"
  | "SENT"
  | "SILENT"
  | "PARTIAL"
  | "FAILED"
  | "NOT_CONFIGURED"
  | "STOPPED";
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

interface StepBase {
  id: string;
  label?: string | null;
}

export interface SendEmailStep extends StepBase {
  type: "send_email";
  to: string[];
  cc: string[];
  bcc: string[];
  subject: string;
  body: string;
  use_layout: boolean;
}

export interface ConditionStep extends StepBase {
  type: "condition";
  conditions: ConditionClause[];
  then: Step[];
  else: Step[];
}

export interface UnitRecipients {
  unit: string;
  emails: string[];
}

export interface ForEachUnitStep extends StepBase {
  type: "for_each_unit";
  recipients: UnitRecipients[];
  default_emails: string[];
  steps: Step[];
}

export interface WaitStep extends StepBase {
  type: "wait";
  mode: "duration" | "until";
  days: number;
  hours: number;
  weekday: number | null;
  time: string | null;
}

export interface ApprovalStep extends StepBase {
  type: "approval";
  approvers: string[];
  message: string;
}

export type Step = SendEmailStep | ConditionStep | ForEachUnitStep | WaitStep | ApprovalStep;
export type StepType = Step["type"];

export interface FlowVariable {
  name: string;
  value: string;
}

export interface FlowDefinition {
  schema: 2;
  trigger: FlowTrigger;
  variables: FlowVariable[];
  steps: Step[];
}

export interface StepLine {
  depth: number;
  text: string;
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
  step_id: string | null;
  unit: string | null;
  error: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface RunView {
  id: string;
  version: number;
  event_key: string;
  status: RunStatus;
  is_test: boolean;
  item_count: number;
  reason: string | null;
  resume_at: string | null;
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
  steps_text: StepLine[];
  emails: number;
  suggestion_reason: string | null;
  problems: string[];
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

export interface ApprovalView {
  id: string;
  flow_id: string;
  flow_name: string;
  run_id: string;
  step_id: string;
  approvers: string[];
  message: string | null;
  item_count: number;
  status: string;
  can_decide: boolean;
  created_at: string;
}

export interface FlowTable {
  flows: FlowSummary[];
  approvals: ApprovalView[];
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
  blocks: string[];
}

export interface AssetView {
  id: string;
  name: string;
  content_type: string;
  size_bytes: number;
}

export interface LayoutView {
  brand_color: string;
  logo_asset_id: string | null;
  footer: string;
}

export interface CatalogView {
  triggers: TriggerView[];
  operators: Record<Operator, string>;
  changes: [ItemState, string][];
  system_variables: Record<string, string>;
  unit_variables: Record<string, string>;
  blocks: Record<string, string>;
  assets: AssetView[];
  layout: LayoutView;
  provider: string | null;
  provider_ready: boolean;
  sender: string | null;
}

export interface PreviewView {
  step_id: string | null;
  unit: string | null;
  reason: string;
  item_count: number;
  subject: string | null;
  html: string | null;
  to: string[];
  cc: string[];
  bcc: string[];
  trace: string[];
}

export interface DraftResult {
  flow_id: string;
  name: string;
  status: FlowStatus;
  created: boolean;
  when: string;
  steps_text: StepLine[];
  problems: string[];
  preview_subject: string | null;
  editor_url: string;
  can_activate: boolean;
}

export function isDraftResult(value: unknown): value is DraftResult {
  if (typeof value !== "object" || value === null) return false;
  const record: Record<string, unknown> = { ...value };
  return (
    typeof record.flow_id === "string" &&
    typeof record.name === "string" &&
    Array.isArray(record.steps_text) &&
    typeof record.editor_url === "string"
  );
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

export function useFlowTable() {
  return useSWR<FlowTable>(EMAIL_FLOWS_API, errorHandlingFetcher);
}

export function useFlowDetail(flowId: string | null) {
  return useSWR<FlowDetail>(flowId ? `${EMAIL_FLOWS_API}/${flowId}` : null, errorHandlingFetcher);
}

export function useFlowCatalog() {
  return useSWR<CatalogView>(`${EMAIL_FLOWS_API}/catalog`, errorHandlingFetcher, {
    revalidateOnFocus: false,
  });
}

async function readError(response: Response): Promise<string> {
  try {
    const body: { detail?: unknown } = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      const first: { msg?: string } = body.detail[0];
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
  step_id?: string | null;
  flow_name?: string;
}

export interface FlowDecisionBody {
  approve: boolean;
  note?: string;
}

/** Bodies the flows API accepts; actions without input send `{}`. */
export type FlowRequestBody =
  | FlowSaveBody
  | FlowPreviewBody
  | FlowDecisionBody
  | LayoutView
  | { step_id?: string | null }
  | Record<string, never>;

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
  return response.json();
}

export async function uploadAsset(file: File): Promise<AssetView> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", file.name.replace(/\.[^.]+$/, ""));
  const response = await fetch(`${EMAIL_FLOWS_API}/assets`, { method: "POST", body: form });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export function assetUrl(assetId: string): string {
  return `${EMAIL_FLOWS_API}/assets/${assetId}`;
}

// ---------------------------------------------------------------------------
// Step tree helpers
// ---------------------------------------------------------------------------

/** Address of a list of steps: [] = the main list; [2, "then"] = the Sim
 * branch of the third step; [0, "steps"] = inside "para cada unidade". */
export type ListPath = (number | "then" | "else" | "steps")[];

export function newId(): string {
  return Math.random().toString(16).slice(2, 12);
}

function childList(step: Step, branch: "then" | "else" | "steps"): Step[] {
  if (step.type === "condition") return branch === "else" ? step.else : step.then;
  if (step.type === "for_each_unit") return step.steps;
  return [];
}

export function getList(definition: FlowDefinition, path: ListPath): Step[] {
  let steps = definition.steps;
  for (let index = 0; index < path.length; index += 2) {
    const step = steps[Number(path[index])];
    const branch = path[index + 1];
    if (!step || (branch !== "then" && branch !== "else" && branch !== "steps")) return [];
    steps = childList(step, branch);
  }
  return steps;
}

function withChild(step: Step, branch: "then" | "else" | "steps", list: Step[]): Step {
  if (step.type === "condition") return branch === "else" ? { ...step, else: list } : { ...step, then: list };
  if (step.type === "for_each_unit") return { ...step, steps: list };
  return step;
}

function mapList(steps: Step[], path: ListPath, fn: (list: Step[]) => Step[]): Step[] {
  if (path.length === 0) return fn(steps);
  const [rawIndex, branch, ...rest] = path;
  const index = Number(rawIndex);
  if (branch !== "then" && branch !== "else" && branch !== "steps") return steps;
  return steps.map((step, position) =>
    position === index ? withChild(step, branch, mapList(childList(step, branch), rest, fn)) : step
  );
}

export function updateList(
  definition: FlowDefinition,
  path: ListPath,
  fn: (list: Step[]) => Step[]
): FlowDefinition {
  return { ...definition, steps: mapList(definition.steps, path, fn) };
}

export function insertStep(definition: FlowDefinition, path: ListPath, index: number, step: Step): FlowDefinition {
  return updateList(definition, path, (list) => [...list.slice(0, index), step, ...list.slice(index)]);
}

export function removeStep(definition: FlowDefinition, path: ListPath, index: number): FlowDefinition {
  return updateList(definition, path, (list) => list.filter((_, position) => position !== index));
}

export function replaceStep(definition: FlowDefinition, path: ListPath, index: number, step: Step): FlowDefinition {
  return updateList(definition, path, (list) => list.map((item, position) => (position === index ? step : item)));
}

export function moveStep(definition: FlowDefinition, path: ListPath, index: number, delta: -1 | 1): FlowDefinition {
  return updateList(definition, path, (list) => {
    const target = index + delta;
    if (target < 0 || target >= list.length) return list;
    const copy = [...list];
    const [item] = copy.splice(index, 1);
    if (item) copy.splice(target, 0, item);
    return copy;
  });
}

export function walkSteps(steps: Step[], visit: (step: Step) => void): void {
  for (const step of steps) {
    visit(step);
    if (step.type === "condition") {
      walkSteps(step.then, visit);
      walkSteps(step.else, visit);
    } else if (step.type === "for_each_unit") {
      walkSteps(step.steps, visit);
    }
  }
}

export function insideForEach(definition: FlowDefinition, path: ListPath): boolean {
  let steps = definition.steps;
  for (let index = 0; index < path.length; index += 2) {
    const step = steps[Number(path[index])];
    if (!step) return false;
    if (step.type === "for_each_unit") return true;
    const branch = path[index + 1];
    if (branch !== "then" && branch !== "else" && branch !== "steps") return false;
    steps = childList(step, branch);
  }
  return false;
}

export const DEFAULT_BODY =
  '<p>Olá,</p><p>Segue o resumo do TON.</p><div data-block="summary"></div><div data-block="ton_button"></div>';

export function blankStep(type: StepType, insideLoop: boolean): Step {
  const id = newId();
  switch (type) {
    case "send_email":
      return {
        id,
        type,
        to: insideLoop ? ["{email_unidade}"] : [],
        cc: [],
        bcc: [],
        subject: insideLoop ? "Pendências da unidade {unidade} ({total})" : "TON – {data} ({total})",
        body: DEFAULT_BODY,
        use_layout: true,
      };
    case "condition":
      return { id, type, conditions: [{ field: "itens", operator: "GT", value: 0 }], then: [], else: [] };
    case "for_each_unit":
      return { id, type, recipients: [], default_emails: [], steps: [] };
    case "wait":
      return { id, type, mode: "duration", days: 2, hours: 0, weekday: null, time: null };
    case "approval":
      return { id, type, approvers: [], message: "" };
  }
}

export function newDefinition(): FlowDefinition {
  return {
    schema: 2,
    trigger: { kind: "NG_IMPORT_COMPLETED", frequency: null, weekday: null, time: null, changes: [] },
    variables: [],
    steps: [
      {
        id: newId(),
        type: "condition",
        conditions: [{ field: "itens", operator: "GT", value: 0 }],
        then: [blankStep("send_email", false)],
        else: [],
      },
    ],
  };
}

/** "a@x.com, b@x.com; c@x.com" -> list. */
export function parseAddresses(value: string): string[] {
  return value
    .split(/[,;\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export const WEEKDAYS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"];

// ---------------------------------------------------------------------------
// Copy
// ---------------------------------------------------------------------------

export const EMAIL_FLOWS_COPY = {
  eyebrow: "Automações",
  title: "Fluxos de e-mail",
  description:
    "Quando algo acontece no TON, o fluxo segue os passos e manda os e-mails certos. Peça ao TON no chat ou monte no editor.",
  newFlow: "Novo fluxo",
  askTon: "Pedir ao TON",
  askTonPrompt:
    "Quero criar um fluxo de e-mail: quando [o que acontece], enviar um e-mail para [quem] com [o quê], no modelo padrão de estilo.",
  layoutButton: "Modelo de e-mail",
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
    steps: "Passos",
    lastRun: "Último envio",
    status: "Estado",
  },
  approvals: {
    title: "Aguardando aprovação",
    items: (count: number) => `${count} ${count === 1 ? "item" : "itens"}`,
    approve: "Aprovar",
    reject: "Recusar",
  },
  status: {
    SUGGESTED: "Rascunho do TON",
    ACTIVE: "Ativo",
    PAUSED: "Pausado",
    DISCARDED: "Descartado",
  } satisfies Record<FlowStatus, string>,
  runStatus: {
    RUNNING: "rodando",
    WAITING: "aguardando",
    SENT: "enviado",
    SILENT: "nada a enviar",
    PARTIAL: "enviado em parte",
    FAILED: "falhou",
    NOT_CONFIGURED: "não configurado",
    STOPPED: "encerrado",
  } satisfies Record<RunStatus, string>,
  deliveryStatus: {
    SENT: "enviado",
    FAILED: "falhou",
    NOT_CONFIGURED: "não configurado",
  } satisfies Record<DeliveryStatus, string>,
  register: "Ativar",
  discard: "Descartar",
  never: "—",
  test: "teste",
  back: "Fluxos",
  steps: {
    send_email: "Enviar e-mail",
    condition: "Condição",
    for_each_unit: "Para cada unidade",
    wait: "Esperar e conferir",
    approval: "Pedir aprovação",
  } satisfies Record<StepType, string>,
  stepHints: {
    send_email: "Um e-mail escrito no editor, com variáveis, blocos de dados e imagens.",
    condition: "Divide os itens: os que atendem seguem pelo Sim, os outros pelo Não.",
    for_each_unit: "Repete os passos de dentro para cada unidade, só com os itens dela.",
    wait: "Pausa o fluxo e, ao voltar, segue só com o que continua aberto.",
    approval: "Para o fluxo até alguém aprovar; se recusar, o fluxo termina.",
  } satisfies Record<StepType, string>,
  draftCard: {
    subtitle: (created: boolean) =>
      created ? "Rascunho criado pelo TON · nada é enviado antes de ativar" : "Rascunho ajustado pelo TON",
    active: "Ativo · os envios seguem os passos abaixo",
    open: "Abrir no editor",
    activate: "Ativar",
    activated: "Fluxo ativado",
  },
  layout: {
    title: "Modelo de e-mail",
    description: "Cabeçalho com a logo, cor da marca e rodapé aplicados aos e-mails dos fluxos.",
    color: "Cor da marca",
    logo: "Logo",
    noLogo: "Sem logo",
    footer: "Rodapé",
    upload: "Enviar imagem",
    save: "Salvar modelo",
    saved: "Modelo salvo.",
  },
  editor: {
    newTitle: "Novo fluxo",
    namePlaceholder: "Nome do fluxo",
    version: (version: number) => `Versão ${version}`,
    save: "Salvar",
    saving: "Salvando…",
    saved: "Salvo.",
    activate: "Ativar",
    register: "Ativar",
    pause: "Pausar",
    discard: "Descartar",
    preview: "Prévia",
    sendToMe: "Enviar só para mim",
    sending: "Enviando…",
    testSent: (status: string) => `Teste: ${status}.`,
    unsaved: "Alterações não salvas",
    when: "Quando",
    trigger: "Gatilho",
    if: "Se",
    and: "E",
    yes: "Sim",
    no: "Não",
    end: "Fim",
    eachUnit: "cada unidade",
    always: "Sempre",
    alwaysHint: "Sem condição: todos os itens seguem pelo Sim.",
    addStep: "Adicionar passo",
    removeStep: "Remover passo",
    moveUp: "Subir",
    moveDown: "Descer",
    closePanel: "Fechar",
    fitView: "Ajustar à tela",
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
    unitToken: "Use {email_unidade} para mandar a cada unidade os seus itens.",
    subject: "Assunto",
    subjectHint: "Pode usar variáveis entre chaves, como {semana} ou {total}.",
    useLayout: "Aplicar o modelo de e-mail (logo, cor, rodapé)",
    editEmail: "Escrever e-mail",
    noRecipients: "Sem destinatários ainda",
    waitDuration: "Por um tempo",
    waitUntil: "Até um dia e hora",
    days: "Dias",
    hours: "Horas",
    approvers: "Quem aprova",
    approvalMessage: "Mensagem para quem aprova",
    unitRecipients: "E-mails por unidade",
    unitRecipientsHint: "Uma linha por unidade: Unidade = e-mail1, e-mail2",
    defaultEmails: "Para unidades sem cadastro",
    variables: "Variáveis do fluxo",
    variablesHint: "Valores fixos que você usa nos e-mails, como {prazo}.",
    addVariable: "+ variável",
    variableName: "nome",
    variableValue: "valor",
    noRuns: "Ainda não rodou.",
    history: "Histórico",
    historyColumns: {
      date: "Data",
      items: "Itens",
      recipients: "Para / Cc",
      status: "Situação",
    },
    openEmail: "abrir e-mail",
    previewTitle: "Prévia do e-mail",
    previewNothing: "Nada a mostrar.",
    approvedBy: (who: string, when: string) => `Ativado por ${who} em ${when}`,
    nextRun: (when: string) => `Próxima execução: ${when}`,
    problemsTitle: "Para ativar falta:",
  },
  composer: {
    title: "E-mail",
    bold: "Negrito",
    italic: "Itálico",
    underline: "Sublinhado",
    strike: "Tachado",
    h2: "Título",
    h3: "Subtítulo",
    bullet: "Lista",
    ordered: "Lista numerada",
    alignLeft: "Alinhar à esquerda",
    alignCenter: "Centralizar",
    alignRight: "Alinhar à direita",
    color: "Cor do texto",
    link: "Link",
    linkPrompt: "Endereço do link (https://…)",
    image: "Imagem",
    variable: "Variável",
    block: "Bloco de dados",
    blockPlaceholder: (label: string) => `${label} — preenchido com os dados no envio`,
    done: "Concluir",
    refresh: "Atualizar prévia",
    previewOf: (count: number) => `Prévia com os dados de hoje · ${count} ${count === 1 ? "item" : "itens"}`,
    upload: "Enviar imagem…",
  },
};
