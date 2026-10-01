/**
 * Centralized business label mapping and status presentation for TON.
 *
 * Translates backend technical enums, status codes, and blocker identifiers
 * into client-facing pt-BR terminology.
 */

export const BUSINESS_LABELS: Record<string, string> = {
  UNRESOLVED: "Sem decisão",
  "MONTHLY_CONTRACT: SOURCE HAS NO APPROVED CALENDAR START":
    "O orçamento mensal não tem data inicial aprovada.",
  "IMPORT REVIEWED NG ACTUALS FOR THIS PERIOD":
    "Importe os lançamentos financeiros revisados deste período.",
  "BILLING_ONLY; NG NO; BILLING YES; ACCOUNT MAPPED YES; UNIT MAPPED YES; DOCUMENT MATCH UNKNOWN; AMOUNT RELATION UNVERIFIED":
    "Somente faturamento disponível. Conta e unidade vinculadas. Documento e valor precisam de conferência.",
  "UNMAPPED; NG YES; BILLING NO; ACCOUNT MAPPED YES; UNIT MAPPED NO; DOCUMENT MATCH UNKNOWN; AMOUNT RELATION UNVERIFIED":
    "Lançamento financeiro sem faturamento correspondente. Conta vinculada e unidade sem vínculo. Documento e valor precisam de conferência.",
  // General status
  READY: "Pronta",
  NOT_READY: "Pendente",
  BLOCKED: "Aguardando dados",
  PARTIAL: "Parcial",
  IN_PROGRESS: "Parcial",
  "IN PROGRESS": "Parcial",
  NOT_IMPLEMENTED: "Não implementada",
  UNCONFIGURED: "Não configurada",
  MONTHLY_CLOSE: "Fechamento preliminar mensal",
  EXECUTIVE: "Resumo executivo",
  UNMAPPED: "Não vinculado",
  "SYNTHETIC UNIT": "Unidade de demonstração",
  "EXACT SOURCE FIELD FROM REVIEWED NG RECORDS":
    "Origem: lançamentos financeiros revisados",
  "EXACT SOURCE FIELD": "Origem: lançamentos financeiros revisados",
  "GROSS REVENUE": "Receita bruta",
  COST: "Custo",
  RESULT: "Resultado",
  ACCEPTED: "Revisado",
  REVIEW_REQUIRED: "Revisão necessária",
  CORRECTION_REQUIRED: "Correção necessária",
  CONFIRMED: "Confirmada",
  RESOLVED: "Resolvida",
  OPEN: "Aberta",
  CANCELLED: "Cancelada",
  NEW: "Nova",
  REOPENED: "Reaberta",
  RUNNING: "Em execução",
  QUEUED: "Na fila",
  PENDING: "Pendente",
  COMPLETED: "Concluído",
  COMPLETED_WITH_BLOCKED_DOMAINS: "Concluído com bloqueios",
  PASSED: "Concluído",
  SUCCEEDED: "Concluído",
  FAILED: "Falhou",
  SKIPPED: "Não executado",
  UNKNOWN: "Não verificado",
  ACTIVE: "Ativa",
  OPERATIONAL: "Operacional",
  AWAITING_SOURCE: "Aguardando fonte",

  // Severity
  CRITICAL: "Crítica",
  HIGH: "Alta",
  MEDIUM: "Média",
  LOW: "Baixa",

  // Ingestion / Import modes
  FILE_UPLOAD: "Envio de arquivo (XLSX/XLS)",
  MANUAL_IMPORT: "Importação manual",
  DIRECT_INTEGRATION: "Integração direta",
  WAITING_ACCESS: "Aguardando liberação de acesso",
  CURRENT: "Atualizado",
  PROCESSING: "Em processamento",
  ATTENTION: "Requer atenção",
  NO_IMPORT: "Sem importação",
  IMPORTED: "Importado",
  AVAILABLE: "Disponível",

  // Blocker & Readiness codes
  UNMAPPED_ACCOUNT: "Conta não vinculada",
  UNMAPPED_UNIT: "Unidade não vinculada",
  UNIT_UNMAPPED: "Unidade não vinculada",
  ACCOUNT_UNMAPPED: "Conta não vinculada",
  UNCLASSIFIED_ACCOUNT: "Conta sem classificação financeira",
  DRE_ACCOUNT_UNMAPPED: "Conta sem classificação na DRE",
  DRE_MAPPING_PENDING_APPROVAL: "Classificação DRE aguarda aprovação",
  BUDGET_UNMAPPED_ACCOUNT: "Conta do orçamento não vinculada",
  BUDGET_UNMAPPED_UNIT: "Unidade do orçamento não vinculada",
  BUDGET_PERIOD_UNRESOLVED: "Período do orçamento não definido",
  REVIEW_UNRESOLVED: "Revisão financeira pendente",
  EXCLUDED_SOURCE_ROWS: "Linhas excluídas por inconsistência na fonte",
  BILLING_COMPETENCE_UNRESOLVED: "Competência do faturamento não definida",
  UNSUPPORTED_DERIVATION: "Derivação financeira não suportada",
  IR_RETENTION_UNRESOLVED: "Retenção de imposto não definida",
  ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED: "Base de valor realizado não definida",
  AMOUNT_BASIS_UNRESOLVED: "Base de valor não definida",
  ACTUAL_UNIT_SCOPE_UNRESOLVED: "Escopo da unidade não definido",
  MISSING_BUDGET: "Orçamento ausente no escopo",
  SOURCE_RECONCILIATION_AMBIGUOUS: "Conciliação ambígua",
  SOURCE_RECONCILIATION_UNRESOLVED: "Conciliação sem decisão",
  RECONCILIATION_UNRESOLVED: "Conciliação pendente",
  RECONCILIATION_PENDING: "Conciliação pendente",
  NO_ACTUAL: "Sem realizado no período",
  "NO ACTUAL": "Sem realizado no período",
  FORMULA_DENOMINATOR_ZERO: "Denominador da fórmula igual a zero",
  DRE_STRUCTURE_INVALID: "Estrutura DRE inválida",
  BASE_REPROVED: "Base reprovada para publicação",
  MISSING_SOURCE: "Fonte necessária ausente",
  AWAITING_HUMAN_DECISION: "Aguardando decisão humana",
  PREREQUISITE_FAILED: "Etapa anterior pendente",
  NOT_REQUIRED: "Não necessário",

  // Reconciliation decisions
  SUPPLEMENTAL: "Lançamento complementar",
  EXPECTED_DIFFERENCE: "Diferença prevista",
  NOT_SAME_EVENT: "Eventos distintos",
  NG_AUTHORITATIVE: "Prevalência do NG/Keevo",
};

/**
 * Returns user-facing pt-BR label for any status or code.
 */
export function getBusinessLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return (
    BUSINESS_LABELS[code] ??
    BUSINESS_LABELS[code.toUpperCase()] ??
    code
      .replace(/\bSynthetic unit\b/gi, BUSINESS_LABELS["SYNTHETIC UNIT"] ?? "")
      .replaceAll("_", " ")
  );
}

export type StatusTone = "success" | "warning" | "error" | "neutral" | "info";

/**
 * Map status or severity to a semantic tone for badge or tag styling.
 */
export function getStatusTone(status: string | null | undefined): StatusTone {
  if (!status) return "neutral";
  const upper = status.toUpperCase();

  switch (upper) {
    case "READY":
    case "PRONTA":
    case "SUCCEEDED":
    case "COMPLETED":
    case "CONCLUÍDO":
    case "PASSED":
    case "CURRENT":
    case "ATUALIZADO":
    case "OPERATIONAL":
    case "OPERACIONAL":
    case "CONFIRMED":
    case "RESOLVED":
      return "success";

    case "NOT_READY":
    case "PENDENTE":
    case "PENDING":
    case "PARTIAL":
    case "PARCIAL":
    case "REVIEW_REQUIRED":
    case "CORRECTION_REQUIRED":
    case "REVISÃO NECESSÁRIA":
    case "ATTENTION":
    case "MEDIUM":
    case "MÉDIA":
      return "warning";

    case "BLOCKED":
    case "BLOQUEADO":
    case "FAILED":
    case "FALHOU":
    case "CRITICAL":
    case "CRÍTICA":
    case "HIGH":
    case "ALTA":
      return "error";

    case "RUNNING":
    case "EM EXECUÇÃO":
    case "PROCESSING":
    case "EM PROCESSAMENTO":
    case "QUEUED":
    case "WAITING_ACCESS":
    case "AGUARDANDO FONTE":
    case "AWAITING_SOURCE":
    case "INFO":
      return "info";

    default:
      return "neutral";
  }
}

export type TagColor = "green" | "purple" | "blue" | "gray" | "amber" | "red";

export function getStatusColor(status: string | null | undefined): TagColor {
  const tone = getStatusTone(status);
  switch (tone) {
    case "success":
      return "green";
    case "warning":
      return "amber";
    case "error":
      return "red";
    case "info":
      return "blue";
    default:
      return "gray";
  }
}

/**
 * Business blocker categories for the Pendências work queue.
 */
export interface BlockerCategoryGroup {
  id: string;
  label: string;
  description: string;
  actionVerb: string;
  blockerKeys: string[];
}

export const BLOCKER_GROUPS: BlockerCategoryGroup[] = [
  {
    id: "financial-classification",
    label: "Classificação financeira",
    description:
      "Contas de origem aguardando enquadramento contábil ou estrutura da DRE",
    actionVerb: "Classificar",
    blockerKeys: [
      "UNMAPPED_ACCOUNT",
      "DRE_ACCOUNT_UNMAPPED",
      "DRE_MAPPING_PENDING_APPROVAL",
      "UNCLASSIFIED_ACCOUNT",
      "BUDGET_UNMAPPED_ACCOUNT",
    ],
  },
  {
    id: "units",
    label: "Unidade",
    description: "Obras e centros de custo não associados às unidades do grupo",
    actionVerb: "Vincular unidade",
    blockerKeys: [
      "UNMAPPED_UNIT",
      "UNIT_UNMAPPED",
      "BUDGET_UNMAPPED_UNIT",
      "ACTUAL_UNIT_SCOPE_UNRESOLVED",
    ],
  },
  {
    id: "budget",
    label: "Dotação e orçamento",
    description: "Valores ou períodos de orçamento aguardando sincronização",
    actionVerb: "Definir período",
    blockerKeys: ["BUDGET_PERIOD_UNRESOLVED", "MISSING_BUDGET"],
  },
  {
    id: "reconciliation",
    label: "Conciliação",
    description: "Divergências entre lançamentos bancários, NG e notas fiscais",
    actionVerb: "Resolver conciliação",
    blockerKeys: [
      "SOURCE_RECONCILIATION_UNRESOLVED",
      "SOURCE_RECONCILIATION_AMBIGUOUS",
      "RECONCILIATION_UNRESOLVED",
      "RECONCILIATION_PENDING",
    ],
  },
  {
    id: "calculation-basis",
    label: "Base de cálculo",
    description: "Semântica de realizado, competência fiscal e retenções",
    actionVerb: "Definir base",
    blockerKeys: [
      "ACTUAL_AMOUNT_SEMANTICS_UNRESOLVED",
      "AMOUNT_BASIS_UNRESOLVED",
      "BILLING_COMPETENCE_UNRESOLVED",
      "IR_RETENTION_UNRESOLVED",
      "NO_ACTUAL",
      "NO ACTUAL",
    ],
  },
];

export const TON_TOOL_NAMES: Record<string, string> = {
  ton_list_sources: "Fontes financeiras",
  ton_get_source_status: "Estado da fonte",
  ton_list_findings: "Pendências financeiras",
  ton_get_finding: "Evidência da pendência",
  ton_get_financial_review_summary: "Resumo da revisão financeira",
  ton_get_dre_readiness: "Prontidão da DRE",
  ton_get_dre_result: "Resultado da DRE",
  ton_get_financial_context: "Contexto financeiro",
  ton_analyze_closing: "Análise do fechamento",
  ton_generate_closing_report: "Relatório de fechamento",
  ton_generate_executive_brief: "Resumo executivo",
  ton_get_billing_summary: "Resumo do faturamento",
  ton_get_budget_summary: "Resumo do orçamento",
  ton_get_reconciliation_summary: "Resumo da conciliação",
  ton_list_occurrences: "Ocorrências",
  ton_get_occurrence: "Detalhe da ocorrência",
  ton_list_overdue_actions: "Ações vencidas",
  ton_get_readiness_evidence: "Evidência da prontidão",
};
