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
  natureza: string;
  dre_group: string;
}

export interface PrefixPattern {
  prefix: string;
  natureza: string;
  matches: number;
  total: number;
}

export interface SuggestionView {
  account_id: string;
  natureza: string;
  confidence: SuggestionConfidence;
  rationale: string;
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
  entries: number;
  total_amount: string;
  monthly: Record<string, string>;
  units: string[];
  pattern: PrefixPattern | null;
  suggestion: SuggestionView | null;
}

export interface ClassificationTable {
  source_id: string;
  source_name: string;
  normalization_run_id: string | null;
  periods: string[];
  natures: NatureView[];
  rows: ClassificationRow[];
}

export interface SuggestionRunResult {
  requested: number;
  suggested: number;
  skipped: string[];
  model_name: string | null;
}

export function useClassificationTable(enabled: boolean) {
  return useSWR<ClassificationTable>(
    enabled ? CLASSIFICATION_API : null,
    errorHandlingFetcher
  );
}

export function suggestionDiverges(row: ClassificationRow): boolean {
  return row.suggestion != null && !row.suggestion.agrees_with_current;
}

export const CLASSIFICATION_COPY = {
  adminEntry: {
    title: "Classificação de contas",
    description:
      "Natureza de cada conta do NG, pré-classificação pelo assistente e confirmação da Controladoria.",
    status: (awaiting: number) =>
      awaiting === 0
        ? "Todas as contas confirmadas"
        : `${awaiting} ${awaiting === 1 ? "conta aguarda" : "contas aguardam"} confirmação`,
  },
  eyebrow: "Administração",
  title: "Classificação de contas",
  description:
    "Cada código do NG recebe uma natureza, e a natureza define a linha da DRE. O assistente sugere uma natureza para as contas novas ou não confirmadas, mas só a Controladoria decide.",
  back: "Voltar para Administração",
  noAccessTitle: "Acesso restrito",
  noAccessDescription:
    "Somente administradores do TON podem revisar a classificação de contas.",
  source: (name: string) => `Fonte: ${name}`,
  metrics: {
    total: "Contas do NG",
    awaiting: "Aguardando confirmação",
    pending: "Sem classificação",
    divergent: "Sugestão diferente",
    awaitingDetail: "Classificadas por semelhança",
    pendingDetail: "Contas novas sem natureza",
    divergentDetail: "Assistente discorda da atual",
  },
  filters: {
    label: "Filtrar contas",
    all: "Todas",
    attention: "Precisam de atenção",
    awaiting: "Aguardando confirmação",
    pending: "Sem classificação",
    divergent: "Sugestão diferente",
    confirmed: "Confirmadas",
  },
  search: "Buscar por código, descrição ou natureza",
  suggest: "Pré-classificar com o assistente",
  suggesting: "O assistente está analisando…",
  suggestHint:
    "Analisa as contas não confirmadas usando as contas já confirmadas, o padrão do código e os históricos dos lançamentos.",
  suggestDone: (result: SuggestionRunResult) =>
    result.requested === 0
      ? "Nenhuma conta precisa de pré-classificação."
      : `${result.suggested} de ${result.requested} contas pré-classificadas${
          result.skipped.length
            ? `; sem sugestão: ${result.skipped.join(", ")}`
            : ""
        }.`,
  suggestFailed:
    "Não foi possível consultar o assistente. Verifique o modelo de linguagem configurado e tente de novo.",
  exportExcel: "Baixar Excel para conferência",
  exportFailed: "Não foi possível gerar o Excel. Tente novamente.",
  empty: "Nenhuma conta neste filtro.",
  table: {
    code: "Código",
    description: "Descrição no NG",
    nature: "Natureza no TON",
    group: "Grupo da DRE",
    status: "Situação",
    suggestion: "Sugestão do assistente",
    total: "Total no período",
    actions: "Ação",
    review: "Revisar",
  },
  status: {
    PENDING: "Sem classificação",
    AWAITING_CONFIRMATION: "Aguardando confirmação",
    CONFIRMED: "Confirmada",
  } satisfies Record<ClassificationStatus, string>,
  origin: {
    CONTROLLER_WORKBOOK: "Planilha da Controladoria",
    ANALOGY: "Semelhança (TON)",
    MANUAL: "Decisão manual",
  } satisfies Record<ClassificationOrigin, string>,
  confidence: {
    HIGH: "confiança alta",
    MEDIUM: "confiança média",
    LOW: "confiança baixa",
  } satisfies Record<SuggestionConfidence, string>,
  agrees: "Concorda com a atual",
  noSuggestion: "—",
  dialog: {
    title: (code: string) => `Conta ${code}`,
    current: "Classificação atual",
    noCurrent: "Esta conta ainda não tem natureza. Ela fica fora da DRE até ser classificada.",
    origin: "Origem",
    reason: "Motivo registrado",
    decided: (who: string | null, when: string) =>
      who ? `${who} em ${when}` : when,
    pattern: "Padrão das contas confirmadas",
    patternText: (pattern: PrefixPattern) =>
      `${pattern.matches} de ${pattern.total} contas confirmadas com prefixo ${pattern.prefix} são ${pattern.natureza}.`,
    noPattern: "Nenhuma conta confirmada com o mesmo prefixo.",
    usage: "Uso no NG",
    usageText: (entries: number, units: number) =>
      `${entries} ${entries === 1 ? "lançamento" : "lançamentos"} em ${units} ${units === 1 ? "unidade" : "unidades"}`,
    suggestion: "Sugestão do assistente",
    suggestionNote:
      "É só uma sugestão. Nada muda até alguém da Controladoria confirmar.",
    noSuggestionYet:
      "Sem sugestão ainda. Use “Pré-classificar com o assistente” na lista.",
    useSuggestion: "Usar a sugestão",
    confirmTitle: "Confirmar a natureza atual",
    confirmNote: "Observação (opcional)",
    confirm: "Confirmar natureza",
    changeTitle: "Mudar a natureza",
    changeNature: "Nova natureza",
    changeReason: "Justificativa (obrigatória)",
    changeReasonPlaceholder:
      "Ex.: conferido com a planilha da Controladoria; é custo de folha da unidade.",
    change: "Salvar nova natureza",
    changeImpact:
      "A mudança cria uma nova versão da classificação. A DRE dos meses afetados passa a usar a nova natureza no próximo recálculo.",
    saving: "Salvando…",
    failed: "Não foi possível salvar. Tente novamente.",
    close: "Fechar",
  },
};
