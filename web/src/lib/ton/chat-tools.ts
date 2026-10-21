import {
  SvgActivity,
  SvgAlertTriangle,
  SvgBarChart,
  SvgCalendar,
  SvgCheckCircle,
  SvgClipboard,
  SvgClock,
  SvgFileText,
  SvgHistory,
  SvgMail,
  SvgSearch,
  SvgBlocks,
  SvgServer,
  SvgWallet,
  SvgWorkflow,
} from "@opal/icons";
import type { Route } from "next";
import type { IconFunctionComponent } from "@opal/types";

/**
 * How the assistant presents each TON tool: what it is doing while the call
 * runs, what the result is called once it returns, and which product page
 * holds the same data. Business language only; tool codes never reach the UI.
 */
export interface TonToolDescriptor {
  /** Present continuous, shown while the call runs. */
  doing: string;
  /** Short noun phrase for the finished step and its source chip. */
  label: string;
  /** Page that shows the same data, for the source chip. */
  href: Route;
  icon: IconFunctionComponent;
  /** Groups sources in the footer. */
  kind: "dre" | "sources" | "findings" | "finance" | "report" | "activity";
}

export const TON_TOOLS: Record<string, TonToolDescriptor> = {
  ton_list_sources: {
    doing: "Verificando as fontes importadas",
    label: "Fontes importadas",
    href: "/ton/fontes",
    icon: SvgServer,
    kind: "sources",
  },
  ton_get_source_status: {
    doing: "Verificando a situação da fonte",
    label: "Situação da fonte",
    href: "/ton/fontes",
    icon: SvgServer,
    kind: "sources",
  },
  ton_get_financial_context: {
    doing: "Localizando as bases financeiras disponíveis",
    label: "Bases financeiras",
    href: "/ton/fontes",
    icon: SvgBlocks,
    kind: "sources",
  },
  ton_get_closing_overview: {
    doing: "Reunindo o fechamento do período",
    label: "Fechamento do período",
    href: "/ton/dre",
    icon: SvgBarChart,
    kind: "dre",
  },
  ton_list_findings: {
    doing: "Lendo os achados da revisão financeira",
    label: "Achados da revisão",
    href: "/ton/pendencias",
    icon: SvgAlertTriangle,
    kind: "findings",
  },
  ton_get_finding: {
    doing: "Abrindo a evidência do achado",
    label: "Evidência do achado",
    href: "/ton/pendencias",
    icon: SvgAlertTriangle,
    kind: "findings",
  },
  ton_get_financial_review_summary: {
    doing: "Resumindo a revisão financeira",
    label: "Revisão financeira",
    href: "/ton/pendencias",
    icon: SvgCheckCircle,
    kind: "findings",
  },
  ton_get_dre_readiness: {
    doing: "Conferindo se a DRE pode ser publicada",
    label: "Prontidão da DRE",
    href: "/ton/dre",
    icon: SvgCheckCircle,
    kind: "dre",
  },
  ton_get_dre_result: {
    doing: "Lendo o resultado oficial da DRE",
    label: "Resultado da DRE",
    href: "/ton/dre",
    icon: SvgBarChart,
    kind: "dre",
  },
  ton_get_readiness_evidence: {
    doing: "Buscando a evidência de cada pendência",
    label: "Evidência da pendência",
    href: "/ton/pendencias",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_get_dre_structure: {
    doing: "Lendo a estrutura da DRE",
    label: "Estrutura da DRE",
    href: "/ton/dre",
    icon: SvgBarChart,
    kind: "dre",
  },
  ton_propose_dre_structure_change: {
    doing: "Preparando a mudança na DRE e calculando o antes e depois",
    label: "Proposta na estrutura da DRE",
    href: "/ton/dre",
    icon: SvgBarChart,
    kind: "dre",
  },
  ton_propose_dre_adjustment: {
    doing: "Preparando o ajuste e calculando o antes e depois",
    label: "Proposta de ajuste da DRE",
    href: "/ton/dre",
    icon: SvgWallet,
    kind: "dre",
  },
  ton_propose_closing_treatment: {
    doing: "Preparando o tratamento de fechamento",
    label: "Proposta de tratamento",
    href: "/ton/tratamentos",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_propose_dre_recalculation: {
    doing: "Preparando o recálculo da DRE",
    label: "Proposta de recálculo",
    href: "/ton/dre",
    icon: SvgBarChart,
    kind: "dre",
  },
  ton_propose_source_import: {
    doing: "Lendo o arquivo anexado e comparando com a última importação",
    label: "Proposta de importação",
    href: "/ton/fontes",
    icon: SvgServer,
    kind: "sources",
  },
  ton_search_entries: {
    doing: "Buscando lançamentos",
    label: "Busca de lançamentos",
    href: "/ton/dre",
    icon: SvgSearch,
    kind: "finance",
  },
  ton_supplier_summary: {
    doing: "Somando por fornecedor",
    label: "Fornecedores",
    href: "/ton/dre",
    icon: SvgWallet,
    kind: "finance",
  },
  ton_run_financial_test: {
    doing: "Rodando o teste financeiro",
    label: "Teste financeiro",
    href: "/ton/pendencias",
    icon: SvgActivity,
    kind: "findings",
  },
  ton_compare_dre: {
    doing: "Comparando a DRE",
    label: "Comparação da DRE",
    href: "/ton/dre",
    icon: SvgBarChart,
    kind: "dre",
  },
  ton_get_dre_line_entries: {
    doing: "Abrindo os lançamentos da linha",
    label: "Lançamentos da linha",
    href: "/ton/dre",
    icon: SvgBarChart,
    kind: "dre",
  },
  ton_propose_account_classification: {
    doing: "Preparando a classificação",
    label: "Proposta de classificação",
    href: "/ton/classificacao",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_propose_classification_confirm: {
    doing: "Preparando a confirmação",
    label: "Proposta de confirmação",
    href: "/ton/classificacao",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_propose_review_decision: {
    doing: "Preparando a decisão",
    label: "Proposta de decisão",
    href: "/ton/pendencias",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_propose_unit_assignment: {
    doing: "Preparando a unidade dos lançamentos",
    label: "Proposta de unidade",
    href: "/ton/pendencias",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_propose_automation_status: {
    doing: "Preparando a mudança na automação",
    label: "Proposta na automação",
    href: "/ton/automacoes",
    icon: SvgWorkflow,
    kind: "activity",
  },
  ton_propose_automation_run: {
    doing: "Preparando a execução",
    label: "Proposta de execução",
    href: "/ton/automacoes",
    icon: SvgWorkflow,
    kind: "activity",
  },
  ton_list_classification_queue: {
    doing: "Lendo as contas para classificar",
    label: "Contas para classificar",
    href: "/ton/classificacao",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_list_unit_missing: {
    doing: "Lendo os lançamentos sem unidade",
    label: "Lançamentos sem unidade",
    href: "/ton/pendencias",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_list_automations: {
    doing: "Lendo as automações",
    label: "Automações",
    href: "/ton/automacoes",
    icon: SvgWorkflow,
    kind: "activity",
  },
  ton_propose_controller_rule: {
    doing: "Preparando a regra",
    label: "Proposta de regra",
    href: "/ton/chat",
    icon: SvgHistory,
    kind: "activity",
  },
  ton_get_controller_rules: {
    doing: "Lendo as regras da Controladoria",
    label: "Regras da Controladoria",
    href: "/ton/chat",
    icon: SvgHistory,
    kind: "activity",
  },
  ton_propose_ledger_registration: {
    doing: "Preparando o registro no ledger",
    label: "Proposta de registro no ledger",
    href: "/ton/ocorrencias",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_propose_occurrence_assignment: {
    doing: "Preparando responsável e prazo",
    label: "Proposta de responsável",
    href: "/ton/ocorrencias",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_propose_daily_sweep: {
    doing: "Preparando a varredura diária",
    label: "Proposta de varredura diária",
    href: "/ton/automacoes",
    icon: SvgCalendar,
    kind: "activity",
  },
  ton_get_daily_sweep: {
    doing: "Lendo a varredura diária",
    label: "Varredura diária",
    href: "/ton/automacoes",
    icon: SvgCalendar,
    kind: "activity",
  },
  ton_draft_automation: {
    doing: "Montando o rascunho da automação",
    label: "Rascunho de automação",
    href: "/ton/automacoes",
    icon: SvgWorkflow,
    kind: "activity",
  },
  ton_draft_email_flow: {
    doing: "Montando o rascunho do fluxo de e-mail",
    label: "Rascunho de fluxo de e-mail",
    href: "/ton/fluxos",
    icon: SvgMail,
    kind: "activity",
  },
  ton_get_recent_changes: {
    doing: "Comparando com a base anterior",
    label: "Mudanças após decisões",
    href: "/ton/fechamento",
    icon: SvgHistory,
    kind: "activity",
  },
  ton_analyze_closing: {
    doing: "Acionando os especialistas no fechamento",
    label: "Análise do fechamento",
    href: "/ton/fechamento",
    icon: SvgActivity,
    kind: "dre",
  },
  ton_get_billing_summary: {
    doing: "Cruzando o faturamento com o NG",
    label: "Faturamento",
    href: "/ton/fechamento",
    icon: SvgWallet,
    kind: "finance",
  },
  ton_get_budget_summary: {
    doing: "Comparando com o orçamento",
    label: "Orçamento",
    href: "/ton/fechamento",
    icon: SvgWallet,
    kind: "finance",
  },
  ton_get_reconciliation_summary: {
    doing: "Verificando a conciliação",
    label: "Conciliação",
    href: "/ton/fechamento",
    icon: SvgWallet,
    kind: "finance",
  },
  ton_list_occurrences: {
    doing: "Lendo as ocorrências registradas",
    label: "Ocorrências",
    href: "/ton/pendencias",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_get_occurrence: {
    doing: "Abrindo a ocorrência",
    label: "Ocorrência",
    href: "/ton/pendencias",
    icon: SvgClipboard,
    kind: "findings",
  },
  ton_list_overdue_actions: {
    doing: "Procurando ações com prazo vencido",
    label: "Ações vencidas",
    href: "/ton/pendencias",
    icon: SvgClock,
    kind: "activity",
  },
  ton_generate_closing_report: {
    doing: "Publicando o relatório de fechamento",
    label: "Relatório de fechamento",
    href: "/ton/relatorios",
    icon: SvgFileText,
    kind: "report",
  },
  ton_generate_executive_brief: {
    doing: "Publicando o resumo executivo",
    label: "Resumo executivo",
    href: "/ton/relatorios",
    icon: SvgFileText,
    kind: "report",
  },
};

export const TON_TOOL_FALLBACK: TonToolDescriptor = {
  doing: "Consultando os dados do TON",
  label: "Consulta ao TON",
  href: "/ton/fechamento",
  icon: SvgCalendar,
  kind: "activity",
};

export function tonTool(key: string | null): TonToolDescriptor {
  return (key && TON_TOOLS[key]) || TON_TOOL_FALLBACK;
}
