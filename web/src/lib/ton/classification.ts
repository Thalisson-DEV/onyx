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
  pattern: PrefixPattern | null;
  suggestion: SuggestionView | null;
}

export interface BriefingView {
  summary: string;
  model_name: string | null;
  created_at: string;
}

export interface ClassificationTable {
  source_id: string;
  source_name: string;
  normalization_run_id: string | null;
  periods: string[];
  natures: NatureView[];
  groups: DreGroupView[];
  rows: ClassificationRow[];
  briefing: BriefingView | null;
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

export type Section = "needs_you" | "agrees" | "confirmed";

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
      ? `${CLASSIFICATION_API}/${sourceId}/accounts/${encodeURIComponent(code)}/entries?limit=5`
      : null,
    errorHandlingFetcher
  );
}

export function suggestionDiverges(row: ClassificationRow): boolean {
  return row.suggestion != null && !row.suggestion.agrees_with_current;
}

/** Open rows the assistant agrees with go to one batch; the rest need her. */
export function sectionOf(row: ClassificationRow): Section {
  if (row.status === "CONFIRMED") return "confirmed";
  return row.suggestion?.agrees_with_current ? "agrees" : "needs_you";
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

const brl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

/** "R$ 928.548" for a decimal string; signs are dropped, direction is in text. */
export function formatMagnitude(value: string): string {
  return brl.format(Math.abs(Number(value)));
}

export const CLASSIFICATION_COPY = {
  adminEntry: {
    title: "Classificação de contas",
    description:
      "O “Banco de Dados” da Controladoria no TON: código do NG, natureza e grupo da DRE, com o assistente sugerindo.",
    status: (open: number) =>
      open === 0
        ? "Todas as contas confirmadas"
        : `${open} ${open === 1 ? "conta aguarda" : "contas aguardam"} decisão`,
  },
  eyebrow: "Administração",
  title: "Classificação de contas",
  description:
    "Como na planilha Banco de Dados: cada código do NG recebe uma natureza, e cada natureza cai num grupo da DRE. O assistente analisa e sugere; quem decide é a Controladoria.",
  back: "Voltar para Administração",
  noAccessTitle: "Acesso restrito",
  noAccessDescription:
    "Somente administradores do TON podem revisar a classificação de contas.",
  loading: "Carregando contas…",
  exportExcel: "Baixar Excel",
  exportFailed: "Não foi possível gerar o Excel. Tente novamente.",
  tabs: {
    accounts: "Contas do NG",
    natures: "Naturezas e grupos da DRE",
  },
  assistant: {
    title: "O que o assistente encontrou",
    empty:
      "O assistente ainda não analisou as contas em aberto. Ele lê os lançamentos de cada conta, compara com as contas que a Controladoria já confirmou e diz o que acha, com a pergunta que decide cada caso.",
    analyze: "Pedir análise ao assistente",
    reanalyze: "Refazer análise",
    analyzing: (done: number, total: number) =>
      `Analisando… ${Math.min(done, total)} de ${total} contas`,
    analyzed: (when: string) => `Análise de ${when}`,
    failed:
      "O assistente não respondeu. Verifique o modelo de linguagem configurado e tente de novo.",
    done: (result: SuggestionRunResult) =>
      `${result.suggested} de ${result.requested} contas analisadas${
        result.skipped.length
          ? `; sem resposta para ${result.skipped.join(", ")}`
          : ""
      }.`,
    progress: (decided: number, total: number) =>
      `${decided} de ${total} decididas`,
    allDone: "Nenhuma conta aguarda decisão.",
    batch: (count: number) =>
      `Confirmar as ${count} em que TON e assistente concordam`,
    batchAsk: (count: number) =>
      `Confirmar ${count} ${count === 1 ? "conta" : "contas"} com a classificação atual? Cada uma fica registrada com o seu nome.`,
    batchYes: "Sim, confirmar",
    batchNo: "Cancelar",
    batchDone: (count: number) =>
      `${count} ${count === 1 ? "conta confirmada" : "contas confirmadas"}.`,
  },
  recompute: {
    text: (count: number) =>
      `${count} ${count === 1 ? "decisão ainda não entrou" : "decisões ainda não entraram"} na DRE.`,
    action: "Atualizar a base",
    running: "Atualizando a base…",
    done: "Base atualizada. Recalcule a DRE para ver os novos números.",
    openDre: "Abrir a DRE",
    failed: "Não foi possível atualizar a base. Tente de novo.",
  },
  list: {
    search: "Buscar código, descrição ou natureza",
    showConfirmed: (count: number) => `Mostrar as ${count} já confirmadas`,
    hideConfirmed: "Ocultar confirmadas",
    keyboardHint: "↑ ↓ para navegar",
    sections: {
      needs_you: {
        title: "Precisam de você",
        hint: "O assistente discorda da classificação atual ou ainda não analisou.",
      },
      agrees: {
        title: "O assistente concorda",
        hint: "Pode confirmar em lote no quadro acima.",
      },
      confirmed: {
        title: "Confirmadas",
        hint: "Já decididas pela Controladoria ou vindas da planilha dela.",
      },
    },
    empty: "Nenhuma conta nesta busca.",
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
    notAnalyzed: "—",
  },
  panel: {
    empty: "Escolha uma conta na lista para ver os detalhes e decidir.",
    entries: (count: number) =>
      `${count} ${count === 1 ? "lançamento" : "lançamentos"}`,
    units: (count: number) =>
      `${count} ${count === 1 ? "unidade" : "unidades"}`,
    question: "A pergunta que decide",
    noQuestion:
      "Peça a análise do assistente para ele formular a pergunta desta conta.",
    today: "Hoje no TON",
    suggestion: "O assistente sugere",
    agree: (nature: string) => `TON e assistente concordam: ${nature}`,
    noSuggestion: "Ainda não analisada",
    why: "Por quê",
    impactMove: (amount: string, from: string, to: string) =>
      `Se usar a sugestão, ${amount} saem de “${from}” e vão para “${to}”.`,
    impactSameGroup: (group: string) =>
      `A sugestão muda só a linha dentro de “${group}”; o total do grupo e o resultado ficam iguais.`,
    impactFromNothing: (amount: string, to: string) =>
      `Se usar a sugestão, ${amount} entram em “${to}”.`,
    pattern: (pattern: PrefixPattern) =>
      `Padrão da planilha: ${pattern.matches} de ${pattern.total} contas confirmadas com prefixo ${pattern.prefix} são ${pattern.natureza}.`,
    origin: {
      CONTROLLER_WORKBOOK: "veio da planilha da Controladoria",
      ANALOGY: "classificada pelo TON por semelhança",
      MANUAL: "decisão manual",
    } satisfies Record<ClassificationOrigin, string>,
    confidence: {
      HIGH: "confiança alta",
      MEDIUM: "confiança média",
      LOW: "confiança baixa",
    } satisfies Record<SuggestionConfidence, string>,
    decided: (who: string, when: string) => `Confirmada por ${who} em ${when}`,
    examples: "Lançamentos de exemplo (maiores valores)",
    examplesEmpty: "Sem lançamentos na base atual.",
    decide: "Sua decisão",
    keep: (nature: string) => `Manter ${nature}`,
    useSuggestion: (nature: string) => `Usar ${nature}`,
    other: "Outra natureza…",
    note: "Observação (opcional)",
    notePlaceholder: "Ex.: conferido com a planilha; é custo da unidade.",
    changeTo: (from: string | null, to: string) =>
      from ? `Mudar de ${from} para ${to}` : `Classificar como ${to}`,
    pickNature: "Escolha a natureza",
    reason: "Justificativa (obrigatória para mudar)",
    reasonFromSuggestion: (rationale: string) =>
      `Sugestão do assistente conferida: ${rationale}`,
    save: "Salvar mudança",
    cancel: "Cancelar",
    saving: "Salvando…",
    saved: "Decisão registrada.",
    failed: "Não foi possível salvar. Tente novamente.",
    ask: "Perguntar ao assistente sobre esta conta",
    askPrompt: (row: ClassificationRow) =>
      `Quero decidir a natureza da conta ${row.account_code} (${row.description}) do NG. Hoje ela está como ${row.natureza ?? "sem natureza"}${
        row.suggestion
          ? ` e a pré-classificação sugere ${row.suggestion.natureza} (${row.suggestion.rationale})`
          : ""
      }. Analise os lançamentos dessa conta e me diga o que você recomenda e por quê.`,
  },
  natures: {
    intro:
      "Como a aba AUXILIARES: cada natureza pertence a um grupo da DRE. Se aparecer um tipo de gasto que não cabe em nenhuma, crie uma natureza nova.",
    columns: {
      nature: "Natureza",
      group: "Grupo da DRE",
      accounts: "Códigos do NG",
    },
    create: "Nova natureza",
    dialogTitle: "Nova natureza",
    dialogIntro:
      "A natureza nova ganha uma linha própria na DRE, dentro do grupo escolhido. Os meses já calculados mudam só depois de recalcular a DRE.",
    name: "Nome da natureza",
    namePlaceholder: "Ex.: BENEFÍCIOS A EMPREGADOS",
    group: "Grupo da DRE",
    reason: "Por que criar (obrigatório)",
    save: "Criar natureza",
    created: (name: string) => `Natureza ${name} criada.`,
    failed:
      "Não foi possível criar. Verifique se já existe uma natureza com esse nome.",
  },
};
