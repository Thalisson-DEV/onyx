/**
 * Product copy for the TON client experience. TON is Brazilian Portuguese only
 * (see plans/ton/TON_FE_001_DECISIONS.md, D-006), so screens read their text
 * from here instead of the next-intl catalogs.
 */

export function plural(count: number, one: string, other: string): string {
  return `${count.toLocaleString("pt-BR")} ${count === 1 ? one : other}`;
}

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: "America/Sao_Paulo",
});
const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});
const timeFormatter = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});
const monthFormatter = new Intl.DateTimeFormat("pt-BR", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});
const dayKey = new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/Sao_Paulo",
});

export function formatDate(value: string | Date): string {
  return dateFormatter.format(new Date(value));
}

const shortDateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});

/** "03 de nov., 08:00" */
export function formatShortDateTime(value: string | Date): string {
  return shortDateTimeFormatter.format(new Date(value));
}

export function formatDateTime(value: string | Date): string {
  return dateTimeFormatter.format(new Date(value));
}

/** "hoje, 08:14", "ontem, 22:10" or "03/11/2026, 08:00" in Brasília time. */
export function formatRelativeDateTime(value: string | Date): string {
  const date = new Date(value);
  const today = dayKey.format(new Date());
  const yesterday = dayKey.format(new Date(Date.now() - 86_400_000));
  const day = dayKey.format(date);
  if (day === today) return `hoje, ${timeFormatter.format(date)}`;
  if (day === yesterday) return `ontem, ${timeFormatter.format(date)}`;
  return dateTimeFormatter.format(date);
}

/** "julho de 2026" for an ISO period such as "2026-07-01". */
export function formatPeriod(period: string): string {
  const label = monthFormatter.format(new Date(`${period}T12:00:00Z`));
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function formatNumber(value: number): string {
  return value.toLocaleString("pt-BR");
}

export const COPY = {
  shell: {
    tagline: "Inteligência Operacional e Controladoria com IA",
    navigationLabel: "Navegação do TON",
    openMenu: "Abrir menu",
    closeMenu: "Fechar menu",
    newConversation: "Nova conversa",
    history: "Histórico",
    allConversations: "Ver todas as conversas",
    noConversations: "Suas conversas com o TON aparecem aqui.",
    untitledConversation: "Análise sem título",
    admin: "Administração",
    diagnostics: "Diagnóstico de cobertura",
    demo: "Ambiente de demonstração — dados sintéticos",
    demoShort: "Demonstração",
    sourcesCurrent: "Fontes atualizadas",
    sourcesAttention: "Fontes exigem atenção",
    sourcesLastImport: (date: string) => `Última importação: ${date}`,
    account: "Conta",
    preferences: "Preferências",
    signOut: "Sair",
    signOutFailed: "Não foi possível sair. Tente novamente.",
    noAccessTitle: "O TON não está disponível para esta conta",
    noAccessDescription:
      "Peça a um administrador acesso às fontes e análises do TON.",
  },
  nav: {
    overview: "Visão Geral",
    assistant: "Assistente",
    closing: "Fechamento",
    dre: "DRE",
    pending: "Pendências",
    automations: "Automações",
    reports: "Relatórios",
    sources: "Fontes",
    specialists: "Especialistas",
  },
  common: {
    loading: "Carregando…",
    error:
      "Não foi possível carregar esta informação. Tente novamente em instantes.",
    retry: "Tentar novamente",
    seeAll: "Ver todos",
    open: "Abrir",
    notAvailable: "Não disponível",
    cancel: "Cancelar",
    close: "Fechar",
  },
  blockers: {
    categories: {
      units: {
        short: "Unidades",
        title: "Unidade não vinculada",
        description:
          "Lançamentos cuja unidade não está vinculada a uma unidade da DRE.",
      },
      budget: {
        short: "Dotação",
        title: "Período do orçamento não definido",
        description: "Linhas do orçamento sem período inicial aprovado.",
      },
      reconciliation: {
        short: "Conciliação",
        title: "Conciliação sem decisão",
        description:
          "Diferenças entre NG e faturamento aguardando decisão humana.",
      },
      actuals: {
        short: "Realizado",
        title: "Períodos sem realizado",
        description: "Meses do escopo sem realizado revisado importado.",
      },
      other: {
        short: "Outros",
        title: "Outros bloqueios",
        description: "Itens que impedem a publicação da DRE.",
      },
    },
    records: (count: number) => plural(count, "registro", "registros"),
    origin: "Fechamento · DRE",
    resolve: "Resolver",
  },
  home: {
    greeting: (name: string) => `Olá, ${name}`,
    greetingFallback: "Olá",
    subtitle: "Aqui está o que precisa da sua atenção hoje.",
    askPlaceholder:
      "Pergunte ao TON sobre o fechamento, as fontes ou os relatórios…",
    ask: "Perguntar ao TON",
    strip: {
      closing: "Fechamento",
      closingPending: "Com pendências",
      closingReady: "Pronto para publicar",
      dre: "Fechamento · DRE",
      dreBlocked: "Bloqueada",
      dreReady: "Pronta",
      dreDetail: (count: number) =>
        count === 1
          ? "1 item impede a publicação"
          : `${formatNumber(count)} itens impedem a publicação`,
      pending: "Pendências",
      pendingDetail: (count: number) =>
        `em ${plural(count, "categoria", "categorias")}`,
      sources: "Fontes",
      sourcesDetail: (count: number) =>
        count === 1
          ? "1 fonte atualizada por arquivo"
          : `${formatNumber(count)} fontes atualizadas por arquivo`,
      nextAutomation: "Próxima automação",
      nextAutomationNone: "Nenhuma automação agendada",
    },
    attention: {
      title: "O que precisa de atenção",
      subtitle: (period: string) =>
        `Itens que impedem a publicação do fechamento de ${period}.`,
      empty: "Nada bloqueia o fechamento agora.",
      openAll: "Abrir pendências",
    },
    activity: {
      title: "Atividade do TON",
      reportPublished: (report: string) => `${report} publicado`,
      sourceImported: (source: string) => `Importação concluída — ${source}`,
      specialistRan: (names: string[]) =>
        names.length > 1
          ? `${names.slice(0, -1).join(", ")} e ${names.at(-1)} analisaram o fechamento`
          : `${names[0] ?? "TON"} analisou o fechamento`,
      empty: "Nenhuma atividade recente.",
    },
    automation: {
      title: "Automação",
      nextRun: "Próxima execução",
      lastRun: "Última execução",
      lastResult: "Último resultado",
      notRunYet: "Ainda não executada",
      runNow: "Executar agora",
      running: "Executando…",
      runFailed:
        "A execução falhou. Tente novamente para retomar a mesma solicitação.",
      completed: "Execução concluída",
      openResult: "Abrir resultado",
      manageAutomations: "Ver automações",
    },
    reports: {
      title: "Últimos relatórios",
      previousVersions: (count: number) =>
        count === 0
          ? "Versão atual"
          : plural(count, "versão anterior", "versões anteriores"),
      empty: "Nenhum relatório publicado ainda.",
    },
    rail: {
      sources: "Fontes",
      allSources: "Ver todas as fontes",
      manualImport: "Atualizado por arquivo",
      directIntegration: "Integração direta",
      automations: "Automações",
      allAutomations: "Ver todas as automações",
      specialists: "Especialistas",
      allSpecialists: "Ver especialistas",
    },
  },
  analysis: {
    running: "TON está analisando…",
    completed: "Análise concluída",
    partial: "Análise parcial",
    stopped: "Análise interrompida",
    details: "Ver detalhes da análise",
    technical: "Dados técnicos (JSON)",
    phases: {
      sources: "Fontes consultadas",
      base: "Base financeira validada",
      dre: "DRE verificada",
      evidence: "Evidências consolidadas",
      report: "Relatório publicado",
    },
    stepStatus: {
      COMPLETED: "Concluída",
      RUNNING: "Em execução",
      FAILED: "Falhou",
      SKIPPED: "Não executada",
    },
    calls: (count: number) => plural(count, "consulta", "consultas"),
    evidenceTitle: "Evidência",
    affected: (count: number) =>
      `${plural(count, "registro afetado", "registros afetados")}`,
    location: (sheet: string, row: string) =>
      `Planilha ${sheet} · linha ${row}`,
    openPending: "Abrir pendências",
    dreTitle: "Situação da DRE",
    dreBlocked: (count: number) =>
      count === 1
        ? "1 item impede a publicação"
        : `${formatNumber(count)} itens impedem a publicação`,
    sourcesTitle: "Fontes consultadas",
    openSources: "Ver fontes",
    reportTitle: "Relatório de fechamento",
    executiveTitle: "Resumo executivo",
    openReport: "Abrir relatório",
    download: "Baixar",
  },
  assistant: {
    heroPrefix: "Olá, sou o",
    heroName: "TON.",
    heroBody:
      "Posso analisar o fechamento financeiro, as fontes, as pendências e os relatórios disponíveis.",
    readyTitle:
      "Tudo pronto! Pergunte sobre o fechamento, a DRE, as pendências ou as fontes importadas.",
    readyAction: "Como posso ajudar?",
    placeholder: "Pergunte algo ao TON…",
    unavailable:
      "O assistente TON está indisponível. Verifique o acesso e a configuração do TON.",
    loading: "Abrindo o assistente TON…",
    suggestions: [
      {
        key: "closing",
        label: "Analisar fechamento",
        prompt:
          "Analise o fechamento financeiro atual e me diga o que precisa da minha atenção.",
      },
      {
        key: "pending",
        label: "Ver pendências da DRE",
        prompt:
          "Quais pendências impedem a publicação da DRE e qual evidência sustenta cada uma?",
      },
      {
        key: "summary",
        label: "Gerar resumo executivo",
        prompt:
          "Gere um resumo executivo do fechamento atual com achados, pendências e próximos passos.",
      },
      {
        key: "sources",
        label: "Consultar fontes",
        prompt:
          "Quais fontes estão disponíveis, quando foram atualizadas e o que ainda falta integrar?",
      },
    ],
  },
} as const;
