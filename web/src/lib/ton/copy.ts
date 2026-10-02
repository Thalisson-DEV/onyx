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

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 2,
});
const percentFormatter = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 1,
});
const shortMonthFormatter = new Intl.DateTimeFormat("pt-BR", {
  month: "short",
  timeZone: "UTC",
});

/** Decimal strings from the API; null stays "—", never zero. */
export function formatCurrency(value: string | null | undefined): string {
  return value == null ? "—" : currencyFormatter.format(Number(value));
}

export function formatPercent(value: string | null | undefined): string {
  return value == null ? "—" : `${percentFormatter.format(Number(value))}%`;
}

/** "jul." for an ISO period such as "2026-07-01". */
export function formatShortMonth(period: string): string {
  return shortMonthFormatter.format(new Date(`${period}T12:00:00Z`));
}

export const COPY = {
  shell: {
    tagline: "Inteligência Operacional e Controladoria com IA",
    navigationLabel: "Navegação do TON",
    openMenu: "Abrir menu",
    closeMenu: "Fechar menu",
    newConversation: "Nova conversa",
    history: "Histórico",
    team: "Equipe do TON",
    allConversations: "Ver todas as conversas",
    noConversations: "Suas conversas com o TON aparecem aqui.",
    untitledConversation: "Análise sem título",
    admin: "Administração",
    tonAdmin: "Administração do TON",
    technicalAdmin: "Administração técnica",
    diagnostics: "Diagnóstico de cobertura",
    demo: "Ambiente de demonstração — dados sintéticos",
    demoShort: "Demonstração",
    demoTiny: "Demo",
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
    sourceHealth: {
      title: "Saúde das fontes",
    },
    involved: {
      title: "Especialistas no fechamento",
      waiting: (count: number) =>
        count === 1
          ? "1 especialista aguarda fonte de dados."
          : `${formatNumber(count)} especialistas aguardam fonte de dados.`,
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
  closing: {
    eyebrow: "Fechamento",
    tabs: {
      overview: "Visão geral",
      dre: "DRE",
      pending: "Pendências",
    },
    overviewTitle: "Fechamento do período",
    overviewDescription:
      "Situação do fechamento, o que impede a publicação da DRE e quem está atuando.",
    blockedTitle: (period: string) =>
      `DRE de ${period} ainda não pode ser publicada`,
    readyTitle: (period: string) => `DRE de ${period} pronta para revisão`,
    attentionCount: (count: number) =>
      count === 1
        ? "1 item exige atenção"
        : `${formatNumber(count)} itens exigem atenção`,
    blockedBody:
      "A base financeira foi importada e revisada, mas decisões humanas e dados faltantes impedem um resultado oficial. Nenhum valor foi estimado.",
    readyBody:
      "Nenhum bloqueio de prontidão no escopo. Revise o resultado calculado antes de publicar.",
    resolve: "Resolver pendências",
    askTon: "Perguntar ao TON",
    askPrompt:
      "Explique por que a DRE do período atual ainda não pode ser publicada e qual pendência devo resolver primeiro.",
    openDre: "Abrir DRE",
    summaryTitle: "Leitura do TON",
    summary: {
      RESULTADO: "Situação",
      PROBLEMA: "Bloqueios",
      IMPACTO: "Impacto",
      "CAUSA / HIPÓTESE": "Causa",
      AÇÃO: "Próxima ação",
    } as Record<string, string>,
    specialistsTitle: "Especialistas envolvidos",
    sourcesTitle: "Fontes da análise",
    findingsTitle: "Achados da revisão financeira",
    noFindings: "A revisão financeira não retornou achados abertos.",
    directIntegration: (status: string) => `Integração direta: ${status}`,
  },
  dre: {
    title: "DRE",
    description:
      "Demonstrativo de resultado versionado por período e escopo. Valores só aparecem quando a base está pronta.",
    period: "Período",
    scope: "Escopo",
    consolidated: "Consolidado",
    advanced: "Base e estrutura",
    normalization: "Base normalizada",
    structure: "Estrutura da DRE",
    months: "Meses do exercício",
    monthReady: "Pronta",
    monthBlocked: "Bloqueada",
    blockedTitle: (period: string) =>
      `DRE de ${period} ainda não pode ser publicada`,
    blockedCount: (count: number) =>
      count === 1
        ? "1 item exige atenção"
        : `${formatNumber(count)} itens exigem atenção`,
    blockedBody:
      "A base foi importada, mas decisões humanas ou dados faltantes impedem um resultado oficial. Nenhum valor é estimado enquanto houver bloqueio.",
    resolve: "Resolver",
    resolveAll: "Resolver pendências",
    recalculate: "Recalcular DRE",
    recalculating: "Recalculando…",
    recalcBlocked:
      "Recálculo concluído: a DRE continua bloqueada pelos itens abaixo.",
    recalcReady: "Recálculo concluído: a DRE está pronta.",
    recalcFailed: "Não foi possível recalcular. Tente novamente.",
    ask: "Perguntar ao TON",
    askPrompt: (period: string) =>
      `O que impede a publicação da DRE de ${period} e qual a evidência de cada bloqueio?`,
    readyNoResult:
      "A base está pronta, mas ainda não há cálculo oficial para este período.",
    official: "Resultado oficial",
    calculatedAt: (date: string) => `Calculado em ${date}`,
    export: "Exportar CSV",
    exportFailed: "Não foi possível exportar. Tente novamente.",
    kpi: {
      actual: "Realizado",
      budget: "Orçado",
      variance: "Variação",
      variancePercent: "Variação %",
      ytd: "Acumulado no ano",
    },
    table: {
      line: "Linha",
      month: "Mês",
      ytd: "Acumulado",
      actual: "Realizado",
      budget: "Orçado",
      variance: "Var.",
      variancePercent: "Var. %",
      expand: (line: string) => `Expandir ${line}`,
      collapse: (line: string) => `Recolher ${line}`,
      drill: (line: string) => `Ver composição de ${line}`,
    },
    trend: "Evolução no ano",
    trendEmpty: "Sem outros meses calculados neste ano.",
    drawer: {
      title: "Composição da linha",
      close: "Fechar",
      actual: "Realizado",
      budget: "Orçado",
      facts: (count: number) => plural(count, "lançamento", "lançamentos"),
      empty: "Nenhum lançamento compõe esta linha no período.",
      source: (source: string, file: string) => `${source} · ${file}`,
      location: (sheet: string, row: number) =>
        `Planilha ${sheet} · linha ${formatNumber(row)}`,
      review: "Revisão",
      previous: "Anterior",
      next: "Próxima",
      page: (start: number, end: number, total: number) =>
        `${formatNumber(start)}–${formatNumber(end)} de ${formatNumber(total)}`,
    },
    version: "Versão do cálculo",
    versionStructure: (number: number) => `Estrutura v${number}`,
    noConfiguration:
      "A DRE ainda não tem base normalizada ou estrutura configurada.",
    noPeriods: "Nenhum período disponível para este escopo.",
    noAccess: "Sua conta não tem acesso à DRE.",
  },
  pending: {
    title: "Pendências do fechamento",
    description:
      "Itens que precisam de decisão humana ou de dados antes da publicação da DRE. Nada é aprovado automaticamente.",
    recompute: "Recalcular prontidão",
    periodStatus: (period: string, count: number) =>
      `${period} · ${count === 1 ? "1 item pendente" : `${formatNumber(count)} itens pendentes`}`,
    ready: "Pronta para publicação",
    notReady: "Não pronta",
    categoriesLabel: "Tipos de pendência",
    search: "Buscar pelo valor de origem",
    empty: "Nenhum item nesta categoria.",
    noBase: "Ainda não há base normalizada ou estrutura de DRE para analisar.",
    loadError:
      "Não foi possível carregar as pendências. Tente novamente em instantes.",
    affected: (count: number) =>
      plural(count, "registro afetado", "registros afetados"),
    candidate: (code: string) => `Sugestão do TON: ${code}`,
    approvedCandidate: (code: string) => `Decisão registrada: ${code}`,
    noCandidate: "Sem sugestão determinística",
    analyze: "Ver evidência",
    decide: "Revisar e decidir",
    steps: {
      label: "Etapas da decisão",
      review: "Revisar",
      decide: "Decidir e justificar",
      confirm: "Confirmar",
      done: "Registrada",
    },
    previous: "Anterior",
    next: "Próxima",
    pageRange: (start: number, end: number, total: number) =>
      `${start}–${end} de ${total}`,
    advanced: "Opções avançadas",
    advancedBase: "Base normalizada",
    advancedStructure: "Estrutura da DRE",
    advancedUnit: "Unidade",
    categories: {
      units: {
        label: "Unidades",
        description: "Unidades de origem sem vínculo com uma unidade da DRE.",
        action: "Escolha a unidade da DRE que corresponde ao valor de origem.",
        rowTitle: "Unidade de origem",
      },
      accounts: {
        label: "Contas",
        description: "Contas de origem sem vínculo com uma conta canônica.",
        action: "Escolha ou crie a conta canônica correspondente.",
        rowTitle: "Conta de origem",
      },
      budgetAccounts: {
        label: "Contas da dotação",
        description: "Contas do orçamento sem vínculo com uma conta canônica.",
        action: "Escolha a conta canônica da linha de orçamento.",
        rowTitle: "Conta do orçamento",
      },
      budgetUnits: {
        label: "Unidades da dotação",
        description: "Unidades do orçamento sem vínculo com a DRE.",
        action: "Escolha a unidade da DRE da linha de orçamento.",
        rowTitle: "Unidade do orçamento",
      },
      amountBasis: {
        label: "Base do realizado",
        description: "Contas sem definição de movimento ou saldo final.",
        action:
          "Defina se o valor realizado representa movimento ou saldo final.",
        rowTitle: "Conta",
      },
      dreAssignment: {
        label: "Classificação DRE",
        description: "Contas sem linha da DRE.",
        action: "Escolha a linha da DRE em que a conta entra.",
        rowTitle: "Conta",
      },
      drePending: {
        label: "Aprovação DRE pendente",
        description: "Classificações da DRE aguardando aprovação.",
        action: "Confirme a linha da DRE proposta para a conta.",
        rowTitle: "Conta",
      },
      budgetPeriods: {
        label: "Períodos da dotação",
        description: "Linhas do orçamento sem período inicial aprovado.",
        action:
          "Defina o primeiro e, se houver, o último mês da linha de orçamento.",
        rowTitle: "Linha de orçamento",
      },
      reconciliation: {
        label: "Conciliação",
        description:
          "Diferenças entre NG e faturamento aguardando decisão humana.",
        action: "Classifique a diferença entre os lançamentos.",
        rowTitle: "Item de conciliação",
      },
      reconciliationAmbiguous: {
        label: "Correspondências ambíguas",
        description: "Lançamentos com mais de uma correspondência possível.",
        action: "Classifique a correspondência entre os lançamentos.",
        rowTitle: "Correspondência",
      },
      other: {
        label: "Outros",
        description: "Itens que exigem dados adicionais.",
        action: "Este item não é resolvido por decisão nesta tela.",
        rowTitle: "Item",
      },
    },
    noActual: {
      label: "Realizado ausente",
      description: "Meses do escopo sem lançamentos realizados revisados.",
      action:
        "Importe o realizado revisado desses meses em Fontes. Depois, recalcule a prontidão.",
      cta: "Abrir Fontes",
    },
    decisions: {
      SUPPLEMENTAL: "Lançamento complementar",
      EXPECTED_DIFFERENCE: "Diferença esperada",
      NOT_SAME_EVENT: "Eventos distintos",
      NG_AUTHORITATIVE: "Prevalece o NG/Keevo",
    },
    dialog: {
      title: "Decisão necessária",
      found: "O que aconteceu",
      suggestion: "Sugestão do TON",
      scope: "Quantos registros são afetados",
      decision: "O que precisa ser decidido",
      impact: "O que muda se você confirmar",
      reason: "Justificativa",
      reasonPlaceholder: "Motivo ou referência do documento",
      consequence: (count: number) =>
        `Esta decisão pode afetar ${plural(count, "registro", "registros")} após o recálculo. Ela não cria um resultado oficial de DRE.`,
      searchTarget: "Buscar destino",
      accountCode: "Código da conta",
      accountLabel: "Nome da conta",
      createAccount: "Criar conta canônica",
      movement: "Movimento",
      finalAmount: "Saldo final",
      startMonth: "Primeiro mês",
      endMonth: "Último mês (opcional)",
      review: "Revisar decisão",
      confirm: "Confirmar decisão",
      back: "Voltar",
      reject: "Rejeitar sugestão",
      close: "Fechar",
      saved:
        "Decisão registrada. Recalcule a prontidão para aplicá-la ao fechamento.",
      error:
        "Não foi possível registrar a decisão. Confira a evidência e tente novamente.",
      noPermission:
        "Somente usuários autorizados podem registrar esta decisão. Você pode consultar a evidência.",
      confirmTitle: "Confirme antes de registrar",
    },
  },
  automations: {
    title: "Automações",
    description:
      "Rotinas que o TON executa no calendário ou sob demanda. Nenhuma rotina aprova decisões financeiras.",
    flagship: "Rotina principal",
    active: "Ativas",
    waiting: "Aguardando capacidade",
    waitingDescription:
      "Estas rotinas dependem de fontes ou regras que ainda não estão disponíveis. Elas não executam até a dependência ser liberada.",
    dependsOn: "Depende de",
    schedule: "Agenda",
    notScheduled: "Sem agenda",
    history: "Histórico de execuções",
    historyEmpty: "Nenhuma execução publicada ainda.",
    historyAll: "Ver no catálogo de relatórios",
    historyCount: (count: number) =>
      `${plural(count, "execução recente", "execuções recentes")} da rotina R3`,
    today: "Hoje",
    yesterday: "Ontem",
    code: (code: string) => `Rotina ${code}`,
    guardrail:
      "As rotinas publicam relatórios internos. Decisões e aprovações continuam exigindo uma pessoa.",
  },
  reports: {
    title: "Relatórios",
    description:
      "Versão atual de cada relatório publicado pelo TON. Versões anteriores ficam preservadas para auditoria.",
    current: "Versão atual",
    previousVersions: "Ver versões anteriores",
    hideVersions: "Ocultar versões anteriores",
    versionsCount: (count: number) =>
      plural(count, "versão anterior", "versões anteriores"),
    open: "Abrir",
    download: "Baixar",
    empty: "Nenhum relatório publicado ainda.",
    generatedAt: (date: string) => `Gerado em ${date}`,
    byRoutine: (code: string) => `Publicado pela rotina ${code}`,
    byAssistant: "Publicado pelo Assistente",
  },
  report: {
    back: "Relatórios",
    download: "Baixar relatório",
    print: "Imprimir",
    previousVersions: (count: number) =>
      `${plural(count, "versão anterior preservada", "versões anteriores preservadas")} para auditoria`,
    period: "Período",
    scope: "Escopo",
    generated: "Gerado em",
    status: "Situação",
    summary: "Resumo executivo",
    blockers: "Pendências que impedem a publicação",
    findings: "Achados",
    noFindings: "Nenhum achado aberto na revisão financeira.",
    actions: "Próximas ações",
    sources: "Fontes consultadas",
    specialists: "Especialistas",
    traceability: "Rastreabilidade",
    traceabilityHint:
      "Etapas executadas e referências internas para auditoria.",
    resolve: "Resolver pendências",
    notFound: "Relatório não encontrado ou sem acesso.",
    evidence: (sheet: string, row: string) =>
      `Planilha ${sheet} · linha ${row}`,
  },
  sources: {
    title: "Fontes",
    description:
      "De onde vêm os dados que o TON analisa, quando foram atualizados e o que ainda falta integrar.",
    acquisition: "Modo de aquisição",
    fileFormat: (format: string) => `Arquivo ${format}`,
    lastUpdate: "Última atualização",
    records: "Registros",
    warnings: "Avisos",
    never: "Nunca importado",
    update: "Atualizar dados",
    history: "Histórico de importações",
    hideHistory: "Ocultar histórico",
    directTitle: "Integração direta",
    directPending: "Aguardando acesso VPN/API",
    directNotConfigured: "Não configurada",
    directExplainNg:
      "A conexão direta com o NG/Keevo depende de acesso VPN ou API e de uma base de leitura autorizada. Até lá, os dados entram por arquivo exportado.",
    directExplainOther:
      "Sem integração automática configurada. Os dados entram por arquivo.",
    pendingAccess: "Pendente de acesso",
    listTitle: "Fontes",
    updatedShort: "Atualização",
    showDetails: (name: string) => `Mostrar detalhes de ${name}`,
    hideDetails: (name: string) => `Ocultar detalhes de ${name}`,
    health: {
      healthy: "Fontes configuradas estão atualizadas",
      attention: (count: number) =>
        count === 1
          ? "1 fonte exige atenção"
          : `${formatNumber(count)} fontes exigem atenção`,
      body: "Estado real de cada importação. O TON só analisa o que foi importado; o que falta integrar aparece como pendente.",
      configured: "Fontes atualizadas",
      current: "configuradas com importação válida",
      manual: "Arquivo exportado",
      manualDetail: "Importação manual (XLSX/XLS)",
      ngDirect: "Integração direta NG",
      ngDirectDetail: "Sem conexão direta",
      pathLabel: "Caminho da integração com o NG/Keevo",
      nowTitle: "Hoje: arquivo exportado do NG",
      nowBadge: "Em uso",
      nowBody:
        "Os lançamentos entram por planilha exportada, validada e revisada antes de alimentar a DRE.",
      nextTitle: "Próximo: conexão direta (VPN/API ou base de leitura)",
      nextBadge: "Aguardando acesso",
    },
    usedBy: "Alimenta",
    downstream: {
      financial_review: "Revisão financeira",
      financial_readiness: "Prontidão da DRE",
      dre: "DRE",
    } as Record<string, string>,
    importedRows: (imported: number, rejected: number) =>
      rejected
        ? `${plural(imported, "registro importado", "registros importados")} · ${plural(rejected, "rejeitado", "rejeitados")}`
        : plural(imported, "registro importado", "registros importados"),
  },
  conversations: {
    title: "Conversas",
    description: "Todas as suas conversas com o TON.",
    search: "Buscar conversa",
    noMatch: "Nenhuma conversa encontrada.",
    loadMore: "Carregar mais",
    today: "Hoje",
    yesterday: "Ontem",
    week: "Últimos 7 dias",
    older: "Anteriores",
  },
  specialists: {
    title: "Especialistas",
    description:
      "O TON coordena especialistas por domínio. Cada especialista atua só quando suas fontes e regras estão disponíveis; a conversa é sempre com o TON.",
    working: "Atuando",
    waiting: "Aguardando fonte",
    waitingDescription:
      "Estes especialistas ficam inativos até a fonte de dados ou as regras do domínio estarem disponíveis.",
    can: "O que já faz",
    limits: "Limitações atuais",
    needs: "Precisa de",
    lastRun: (date: string) => `Última atuação: ${date}`,
    neverRan: "Ainda não atuou",
    ask: "Perguntar ao TON",
    askPrompt: (name: string, objective: string) =>
      `Com foco no ${name} (${objective.replace(/\.$/, "")}), o que precisa da minha atenção agora?`,
    policy: "Consultar e recomendar. Decisões e aprovações exigem uma pessoa.",
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
    followUps: {
      label: "Continuar em",
      pending: "Ver pendências",
      dre: "Abrir DRE",
      sources: "Ver fontes",
      reports: "Ver relatórios",
    },
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
    context: {
      coordinator: "TON · coordenador",
      label: "Contexto",
      focus: "Foco",
    },
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
  activity: {
    importFailed: (source: string) => `Importação falhou — ${source}`,
  },
  notifications: {
    label: "Notificações",
    title: "Notificações",
    subtitle: "O que aconteceu no TON recentemente.",
    empty: "Nenhum evento registrado ainda.",
    newCount: (count: number) =>
      count === 1 ? "1 novidade" : `${formatNumber(count)} novidades`,
    markSeen: "Marcar como vistas",
    seeActivity: "Ver visão geral",
    isNew: "Novo",
  },
  help: {
    label: "Ajuda",
    title: "Como o TON trabalha",
    items: [
      {
        title: "Dados com origem",
        body: "Toda análise usa as fontes importadas. O TON não estima valores ausentes.",
      },
      {
        title: "Decisão humana",
        body: "Pendências e aprovações sempre exigem uma pessoa. Nada é aprovado automaticamente.",
      },
      {
        title: "Ambiente de demonstração",
        body: "Quando o selo de demonstração aparece no topo, os dados são sintéticos e não representam resultados reais.",
      },
    ],
    shortcut: "Busca e comandos",
    shortcutKeys: "Ctrl + K",
    contact:
      "Dúvidas de acesso ou de dados: fale com o administrador do TON na Vale Norte.",
  },
  command: {
    trigger: "Buscar ou ir para…",
    placeholder: "Buscar páginas, ações ou conversas…",
    empty: "Nada encontrado. Pressione Enter para perguntar ao TON.",
    pages: "Ir para",
    actions: "Ações",
    conversations: "Conversas",
    ask: (text: string) => `Perguntar ao TON: “${text}”`,
    select: "Selecionar",
    open: "Abrir",
    items: {
      overview: "Visão Geral",
      assistant: "Nova conversa com o TON",
      closing: "Fechamento do período",
      dre: "Abrir DRE",
      pending: "Ver pendências",
      automations: "Automações",
      reports: "Relatórios",
      latestReport: "Mostrar último relatório",
      sources: "Abrir fontes",
      specialists: "Especialistas",
      analyze: "Analisar fechamento",
      conversations: "Todas as conversas",
      admin: "Administração do TON",
    },
  },
  admin: {
    eyebrow: "Configuração",
    title: "Administração do TON",
    description:
      "Acesso, fontes, automações e controles do produto para a Vale Norte. Configurações de infraestrutura ficam na administração técnica.",
    productSection: "Produto",
    technicalBadge: "Técnica",
    technicalHint: "Abre na administração técnica",
    noAccessTitle: "Área restrita a administradores",
    noAccessDescription:
      "A configuração do TON é feita por administradores autorizados da Vale Norte.",
    access: {
      title: "Acesso de usuários",
      description:
        "Quem usa o TON, grupos e permissões de leitura, importação e relatórios.",
    },
    sources: {
      title: "Fontes de dados",
      description:
        "Importações, modo de aquisição e estado da integração direta com o NG/Keevo.",
      status: (current: number, total: number) =>
        `${formatNumber(current)} de ${formatNumber(total)} fontes atualizadas`,
    },
    automations: {
      title: "Automações",
      description:
        "Agenda da rotina de fechamento preliminar (R3) e rotinas aguardando capacidade.",
      enabled: (next: string) => `R3 agendada · próxima execução ${next}`,
      disabled: "R3 sem agenda ativa",
    },
    specialists: {
      title: "Especialistas",
      description:
        "Disponibilidade dos nove especialistas e as fontes de que cada um depende.",
      status: (active: number, total: number) =>
        `${formatNumber(active)} de ${formatNumber(total)} atuando`,
    },
    readiness: {
      title: "Controles de prontidão financeira",
      description:
        "Vínculos de contas e unidades, semântica de valores e recálculo da prontidão.",
    },
    dre: {
      title: "Estrutura da DRE",
      description: "Versões da estrutura de linhas e cálculos da DRE.",
    },
    reports: {
      title: "Relatórios e publicação",
      description:
        "Relatórios publicados pelo TON e versões preservadas para auditoria.",
      status: (types: number, versions: number) =>
        `${plural(types, "tipo de relatório", "tipos de relatório")} · ${plural(versions, "versão", "versões")}`,
    },
    coverage: {
      title: "Cobertura do Prompt Mestre",
      description:
        "Diagnóstico das capacidades do TON: operacionais, parciais, bloqueadas e não implementadas.",
    },
    assistant: {
      title: "Assistente TON",
      description:
        "Coordenador único que conversa com os usuários e aciona os especialistas.",
      ready: "Configurado",
      missing: "Não provisionado",
    },
    technical: {
      title: "Administração técnica",
      description:
        "Modelos e provedores, agentes nativos, MCP/OpenAPI, conectores genéricos e diagnóstico de infraestrutura. Restrita a administradores técnicos.",
      open: "Abrir administração técnica",
    },
    back: "Administração do TON",
  },
  coverage: {
    eyebrow: "Diagnóstico",
    title: "Cobertura do Prompt Mestre",
    description:
      "Estado de cada capacidade prevista para o TON. Uso interno de administração; não aparece para clientes.",
    count: (count: number) => plural(count, "capacidade", "capacidades"),
    needs: (sources: string, owner: string) =>
      `Fontes: ${sources} · Responsável: ${owner}`,
    next: "Próxima dependência",
  },
  auth: {
    points: [
      "Fechamento e DRE com evidência de origem",
      "Rotinas automáticas no calendário da Vale Norte",
      "Decisões e aprovações sempre humanas",
    ],
    headline: "Inteligência operacional e controladoria",
    headlineAccent: "com IA",
    footer: "Vale Norte Construtora · uso interno",
    restrictedTitle: "Acesso restrito",
    restrictedBody:
      "O TON é de uso interno da Vale Norte. Contas são criadas pelo administrador do TON; peça acesso a ele.",
    forgotPassword: "Esqueceu a senha?",
    forgotPasswordHelp:
      "Fale com o administrador do TON para redefinir o acesso.",
  },
} as const;
