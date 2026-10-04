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
  SvgBlocks,
  SvgServer,
  SvgWallet,
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
