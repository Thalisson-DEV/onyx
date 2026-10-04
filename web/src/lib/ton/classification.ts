"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";

export const CLASSIFICATION_API = "/api/ton/account-classification";

export type ClassificationStatus =
  | "PENDING"
  | "AWAITING_CONFIRMATION"
  | "CONFIRMED";
export type ClassificationOrigin = "CONTROLLER_WORKBOOK" | "ANALOGY" | "MANUAL";
export type SuggestionConfidence = "HIGH" | "MEDIUM" | "LOW";

export interface NatureView {
  account_id: string;
  code: string;
  natureza: string;
  dre_group: string;
  dre_group_code: string | null;
  accounts: number;
}

export interface DreGroupView {
  code: string;
  label: string;
}

export interface SuggestionView {
  account_id: string;
  natureza: string;
  confidence: SuggestionConfidence;
  rationale: string;
  question: string | null;
  model_name: string | null;
  created_at: string;
  agrees_with_current: boolean;
}

export interface ClassificationRow {
  account_code: string;
  description: string;
  account_id: string | null;
  natureza: string | null;
  dre_group: string | null;
  status: ClassificationStatus;
  origin: ClassificationOrigin | null;
  reason: string | null;
  decided_by: string | null;
  decided_at: string | null;
  decided_by_person: boolean;
  entries: number;
  total_amount: string;
  monthly: Record<string, string>;
  units: string[];
  suggestion: SuggestionView | null;
}

export interface ClassificationTable {
  source_id: string;
  source_name: string;
  normalization_run_id: string | null;
  periods: string[];
  natures: NatureView[];
  groups: DreGroupView[];
  rows: ClassificationRow[];
  changes_since_calculation: number;
}

export interface EntryView {
  date: string;
  unit: string | null;
  document: string | null;
  history: string;
  amount: string | null;
}

export interface SuggestionRunResult {
  requested: number;
  suggested: number;
  skipped: string[];
  model_name: string | null;
  briefing: boolean;
}

export function useClassificationTable(enabled: boolean) {
  return useSWR<ClassificationTable>(
    enabled ? CLASSIFICATION_API : null,
    errorHandlingFetcher
  );
}

export function useAccountEntries(
  sourceId: string | null,
  code: string | null
) {
  return useSWR<EntryView[]>(
    sourceId && code
      ? `${CLASSIFICATION_API}/${sourceId}/accounts/${encodeURIComponent(code)}/entries?limit=3`
      : null,
    errorHandlingFetcher
  );
}

export function isOpen(row: ClassificationRow): boolean {
  return row.status !== "CONFIRMED";
}

export function agrees(row: ClassificationRow): boolean {
  return row.suggestion?.agrees_with_current ?? false;
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as T;
}

/** "MOVIMENTOS NÃO GERENCIAIS" -> "Movimentos não gerenciais" for short labels. */
export function sentenceCase(value: string): string {
  const lower = value.toLocaleLowerCase("pt-BR");
  return lower.charAt(0).toLocaleUpperCase("pt-BR") + lower.slice(1);
}

export const CLASSIFICATION_COPY = {
  adminEntry: {
    title: "Classificação de contas",
    description:
      "Código do NG → natureza → grupo da DRE, como na planilha Banco de Dados.",
    status: (open: number) =>
      open === 0
        ? "Todas as contas confirmadas"
        : `${open} ${open === 1 ? "conta aguarda" : "contas aguardam"} decisão`,
  },
  eyebrow: "Administração",
  title: "Classificação de contas",
  description:
    "Cada código do NG tem uma natureza, e cada natureza cai num grupo da DRE.",
  back: "Voltar para Administração",
  noAccessTitle: "Acesso restrito",
  noAccessDescription:
    "Somente administradores do TON podem revisar a classificação de contas.",
  loading: "Carregando contas…",
  exportExcel: "Baixar Excel",
  exportFailed: "Não foi possível gerar o Excel. Tente novamente.",
  tabs: {
    accounts: "Contas do NG",
    natures: "Naturezas",
  },
  filters: {
    label: "Mostrar",
    open: (count: number) => `Aguardam decisão (${count})`,
    confirmed: (count: number) => `Confirmadas (${count})`,
    all: (count: number) => `Todas (${count})`,
  },
  search: "Buscar código, descrição ou natureza",
  suggest: "Pedir sugestões ao assistente",
  suggesting: (done: number, total: number) =>
    `Analisando ${Math.min(done, total)} de ${total}…`,
  suggestDone: (result: { suggested: number; requested: number }) =>
    `Assistente analisou ${result.suggested} de ${result.requested} contas.`,
  suggestFailed:
    "O assistente não respondeu. Verifique o modelo de linguagem e tente de novo.",
  batch: (count: number) => `Confirmar as ${count} em que o assistente concorda`,
  batchAsk: (count: number) => `Confirmar ${count} contas?`,
  batchYes: "Confirmar",
  batchNo: "Cancelar",
  batchDone: (count: number) => `${count} contas confirmadas.`,
  recompute: {
    text: (count: number) =>
      `${count} ${count === 1 ? "decisão ainda não está" : "decisões ainda não estão"} na DRE.`,
    action: "Atualizar a base",
    running: "Atualizando…",
    done: "Base atualizada; recalcule a DRE.",
    failed: "Não foi possível atualizar a base.",
  },
  columns: {
    code: "Código",
    description: "Descrição no NG",
    nature: "Natureza",
    assistant: "Assistente",
    total: "Jan–jun",
  },
  noNature: "Sem natureza",
  newNatureOption: "+ Nova natureza…",
  agrees: "Concorda",
  suggests: (nature: string) => `Sugere ${nature}`,
  use: "Usar",
  notAnalyzed: "—",
  empty: "Nenhuma conta neste filtro.",
  detail: {
    noAnalysis: "O assistente ainda não analisou esta conta.",
    confirm: (nature: string) => `Confirmar ${nature}`,
    ask: "Perguntar ao assistente",
    askPrompt: (row: ClassificationRow) =>
      `Quero decidir a natureza da conta ${row.account_code} (${row.description}) do NG. Hoje ela está como ${row.natureza ?? "sem natureza"}${
        row.suggestion ? ` e a sugestão é ${row.suggestion.natureza}` : ""
      }. Analise os lançamentos dessa conta e me diga o que recomenda e por quê.`,
    decided: (who: string, when: string) => `Confirmada por ${who} em ${when}.`,
  },
  change: {
    title: (from: string | null, to: string) =>
      from ? `Mudar de ${from} para ${to}` : `Classificar como ${to}`,
    reason: "Justificativa",
    reasonFromSuggestion: (rationale: string) =>
      `Sugestão do assistente conferida: ${rationale}`,
    save: "Salvar",
    cancel: "Cancelar",
  },
  saving: "Salvando…",
  failed: "Não foi possível salvar. Tente novamente.",
  natures: {
    intro: "Como a aba AUXILIARES: cada natureza pertence a um grupo da DRE.",
    columns: {
      nature: "Natureza",
      group: "Grupo da DRE",
      accounts: "Códigos do NG",
    },
    create: "Nova natureza",
    dialogTitle: "Nova natureza",
    dialogIntro:
      "A natureza nova ganha uma linha própria na DRE, dentro do grupo escolhido.",
    name: "Nome",
    namePlaceholder: "Ex.: BENEFÍCIOS A EMPREGADOS",
    group: "Grupo da DRE",
    reason: "Por que criar",
    save: "Criar natureza",
    created: (name: string) => `Natureza ${name} criada.`,
    failed:
      "Não foi possível criar. Verifique se já existe uma natureza com esse nome.",
  },
};
