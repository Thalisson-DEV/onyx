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

/** A calendar date ("2026-01-10") as the source wrote it, without timezone shifts. */
export function formatDay(value: string): string {
  const [year, month, day] = value.slice(0, 10).split("-");
  return year && month && day ? `${day}/${month}/${year}` : value;
}

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

/** "42 s", "2 min 4 s" or "3 min". */
export function formatElapsed(seconds: number): string {
  const total = Math.max(1, Math.round(seconds));
  if (total < 60) return `${total} s`;
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
}

/** Live timer: "0:42", "2:04". */
export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
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

const amountFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const monthNameFormatter = new Intl.DateTimeFormat("pt-BR", {
  month: "long",
  timeZone: "UTC",
});

/** "1.279.626,41" for statement cells: the column header carries "R$". */
export function formatAmount(value: string | null | undefined): string {
  return value == null ? "—" : amountFormatter.format(Number(value));
}

/** "Setembro", or "Setembro de 2026" with the year, for "2026-09-01". */
export function formatMonthName(period: string, withYear = false): string {
  const label = (withYear ? monthFormatter : monthNameFormatter).format(
    new Date(`${period}T12:00:00Z`)
  );
  return label.charAt(0).toUpperCase() + label.slice(1);
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
    history: "Recentes",
    team: "Equipe",
    collapseSidebar: "Recolher menu",
    expandSidebar: "Expandir menu",
    sidebarShortcut: "Ctrl B",
    showSection: (label: string) => `Mostrar ${label}`,
    hideSection: (label: string) => `Ocultar ${label}`,
    conversationActions: (title: string) => `Ações da conversa ${title}`,
    renameConversation: "Renomear",
    renameFailed: "Não foi possível renomear a conversa.",
    deleteConversation: "Excluir",
    deleteConversationTitle: "Excluir conversa?",
    deleteConversationDescription: (title: string) =>
      `"${title}" e todas as mensagens dela serão removidas. Esta ação não pode ser desfeita.`,
    deleteConversationConfirm: "Excluir conversa",
    deleteFailed: "Não foi possível excluir a conversa.",
    conversationDeleted: "Conversa excluída.",
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
    sourcesCurrent: "Fontes importadas",
    sourcesMissing: (imported: number, total: number) =>
      `${formatNumber(imported)}/${formatNumber(total)} fontes importadas`,
    sourcesAttention: "Fontes com linhas rejeitadas",
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
    dreManagerial: "DRE Gerencial",
    dreCash: "DRE Caixa",
    dreEconomic: "DRE Econômica",
    pending: "Pendências",
    automations: "Automações",
    emailFlows: "Fluxos de e-mail",
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
          ? "1 fonte da DRE importada"
          : `${formatNumber(count)} fontes da DRE importadas`,
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
    closingUntil: "Fechamento até",
    headline: (scope: string, first: string, last: string) =>
      first === last
        ? `${scope} · ${formatPeriod(last)}`
        : `${scope} · ${formatShortMonth(first).replace(".", "")} a ${formatShortMonth(last).replace(".", "")} de ${last.slice(0, 4)}`,
    summaryMonth: (line: string, month: string) => `${line} · ${month}`,
    scope: "Unidade/filial",
    consolidated: "Consolidado",
    advanced: "Base de dados",
    model: "Modelo da DRE",
    createSimplified: "Criar DRE Caixa e Econômica",
    creatingSimplified: "Criando…",
    createSimplifiedFailed: "Não foi possível criar as DREs simplificadas.",
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
    recalculate: "Calcular DRE do ano",
    recalculating: "Calculando…",
    recalculatingMonth: (done: number, total: number) =>
      `Calculando ${done + 1} de ${total} meses…`,
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
    excel: "Baixar Excel",
    excelLoading: "Gerando Excel…",
    excelHint: (scope: string) =>
      scope === "Consolidado"
        ? "Planilha de janeiro até o mês escolhido: o consolidado e, abaixo, cada unidade/filial, com os lançamentos de cada linha."
        : `Planilha de janeiro até o mês escolhido só de ${scope}, com os lançamentos de cada linha.`,
    excelFailed:
      "Não foi possível gerar o Excel. Tente novamente em instantes.",
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
      excluded: "fora do resultado",
    },
    year: {
      lineHeader: "Linha · R$",
      ytdHeader: (first: string, last: string) =>
        first === last
          ? `Acumulado ${formatShortMonth(last).replace(".", "")}`
          : `Acumulado ${formatShortMonth(first).replace(".", "")}–${formatShortMonth(last).replace(".", "")}`,
      shownTotal: (periods: string[]) =>
        `Soma ${periods.map((period) => formatShortMonth(period).replace(".", "")).join(", ")}`,
      ytdUntil: (period: string) =>
        `Acumulado até ${formatShortMonth(period).replace(".", "")}`,
      drillCell: (line: string, month: string) =>
        `Ver lançamentos de ${line} em ${month}`,
      monthsLabel: "Meses exibidos",
      allMonths: "Mostrar todos",
      notCalculated: "Mês pronto, ainda não calculado: use Calcular DRE do ano",
      blocked: "Mês bloqueado por pendências",
      viewLabel: "Visualização",
      columns: "Lado a lado",
      stacked: "Mês a mês",
      expandAll: "Abrir todos os meses",
      collapseAll: "Fechar todos os meses",
      loadFailed: "Não foi possível carregar os meses do ano.",
    },
    editStructure: "Editar estrutura",
    units: {
      title: "Escolher unidades",
      consolidated: "Consolidado — todas as unidades",
      pick: "Uma ou mais unidades",
      operational: (count: number) => `Operacionais ativas (${count})`,
      operationalHint:
        "Segue o cadastro em Administração → Classificação de contas → Unidades: tipo Operacional e ativa.",
      reset: "Limpar seleção e voltar ao consolidado",
      clear: "Limpar",
      apply: "Ver DRE",
      oneHint: "Uma unidade: DRE dela, com os lançamentos.",
      sumHint: (count: number) =>
        `${count} unidades: a DRE soma as ${count}, mês a mês.`,
      many: (count: number) => `${count} unidades`,
      summed: "Soma das unidades",
      partial: "Soma parcial",
      calculating: (done: number, total: number) =>
        `Calculando unidade ${done + 1} de ${total}…`,
      absent: (names: string) =>
        `Sem resultado no ano para: ${names}. Elas ficam fora da soma até a base delas estar pronta.`,
      drillHint:
        "Para ver os lançamentos de uma linha, escolha uma unidade só. O Excel traz a soma e cada unidade, com os lançamentos.",
      excelHint:
        "Planilha com a soma das unidades escolhidas e, abaixo, cada unidade, com os lançamentos de cada linha.",
    },
    structureSaved: (number: number) =>
      `Estrutura salva (versão ${number}). Clique em Calcular DRE do ano para ver os números nela.`,
    editor: {
      eyebrow: (number: number) => `Estrutura da DRE · versão ${number}`,
      title: "Editar a estrutura da DRE",
      description:
        "Renomeie, reordene e crie grupos; mova naturezas entre grupos e decida o que entra no resultado. Salvar cria uma nova versão; as anteriores ficam guardadas.",
      close: "Fechar",
      columns: {
        order: "Ordem",
        line: "Linha",
        group: "Grupo",
        result: "Resultado",
        shown: "Na DRE",
        remove: "Remover",
      },
      kinds: { group: "Grupo", nature: "Natureza", total: "Total" },
      inResult: "Entra no resultado",
      outOfResult: "Fora do resultado",
      shown: "Mostrar",
      hidden: "Oculto",
      hiddenButSummed: "Oculto, mas soma no resultado",
      natureInGroup: "Soma no grupo",
      natureOutOfGroup: "Fora do resultado",
      natureOutHint:
        "Continua aparecendo com o valor, mas o grupo e o resultado não a somam.",
      tabs: { structure: "Estrutura", history: "Histórico" },
      history: {
        loading: "Carregando o histórico…",
        failed: "Não foi possível carregar o histórico.",
        empty: "Ainda não há versões anteriores.",
        current: "Versão em uso",
        version: (number: number) => `Versão ${number}`,
        by: (author: string | null, date: string) =>
          author ? `${author} · ${date}` : date,
        noReason: "Sem motivo informado",
        noChanges: "Sem mudança na estrutura (só a versão inicial ou um recálculo).",
        restore: "Voltar para esta versão",
        preview: (number: number) => `Voltar para a versão ${number}`,
        previewIntro: "Ao confirmar, o TON cria uma nova versão com estas mudanças:",
        previewNone:
          "Nada a voltar: a estrutura em uso já é igual a esta versão (naturezas criadas depois dela são mantidas).",
        leftOut: (natures: string) =>
          `Ficam sem linha (o grupo delas não existe nesta versão): ${natures}. Elas voltarão para a Classificação.`,
        reason: "Motivo da volta (opcional)",
        confirm: "Confirmar a volta",
        confirming: "Voltando…",
        cancel: "Cancelar",
        restoreFailed: "Não foi possível voltar para esta versão.",
        changes: {
          LINE_ADDED: (line: string, _before: string | null, after: string | null) =>
            after ? `Linha “${line}” criada em “${after}”` : `Linha “${line}” criada`,
          LINE_REMOVED: (line: string, before: string | null) =>
            before ? `Linha “${line}” removida de “${before}”` : `Linha “${line}” removida`,
          LINE_RENAMED: (_line: string, before: string | null, after: string | null) =>
            `“${before}” renomeada para “${after}”`,
          LINE_MOVED: (line: string, before: string | null, after: string | null) =>
            `“${line}” saiu de “${before}” para “${after}”`,
          ORDER_CHANGED: (line: string) => `Ordem alterada em “${line}”`,
          INTO_RESULT: (line: string) => `“${line}” voltou a entrar no resultado`,
          OUT_OF_RESULT: (line: string) => `“${line}” saiu do resultado`,
          FORMULA_CHANGED: (line: string, before: string | null, after: string | null) =>
            `Cálculo de “${line}”: ${before || "—"} → ${after || "—"}`,
          HIDDEN: (line: string) => `“${line}” oculta na DRE`,
          SHOWN: (line: string) => `“${line}” voltou a aparecer na DRE`,
          NATURE_LINKED: (line: string, _before: string | null, after: string | null) =>
            `Natureza ${line} ligada a “${after}”`,
          NATURE_UNLINKED: (line: string, before: string | null) =>
            `Natureza ${line} desligada de “${before}”`,
          NATURE_RELINKED: (line: string, before: string | null, after: string | null) =>
            `Natureza ${line}: “${before}” → “${after}”`,
        } as Record<
          string,
          (line: string, before: string | null, after: string | null) => string
        >,
      },
      newGroup: "Novo grupo",
      addGroup: "Novo grupo",
      rename: (line: string) => `Nome de ${line}`,
      moveUp: (line: string) => `Subir ${line}`,
      moveDown: (line: string) => `Descer ${line}`,
      moveTo: (line: string) => `Grupo de ${line}`,
      remove: (line: string) => `Remover ${line}`,
      problems: {
        emptyName: "Toda linha precisa de nome.",
        emptyGroup: (group: string) =>
          `“${group}” está vazio: mova ao menos uma natureza para ele ou remova o grupo.`,
        emptyTotal: (total: string) =>
          `“${total}” ficou sem nenhuma linha somada.`,
      },
      reason: "Motivo da mudança (opcional)",
      reasonPlaceholder: "Ex.: pedido da Miriam na reunião de 19/10",
      defaultReason: "Estrutura ajustada pela Controladoria",
      cancel: "Cancelar",
      save: "Salvar nova versão",
      saving: "Salvando…",
      afterSave:
        "Os números atuais continuam na versão anterior até você calcular a DRE do ano de novo.",
      failed: "Não foi possível salvar a estrutura. Tente novamente.",
      failedWithDetail: (detail: string) =>
        `Não foi possível salvar a estrutura: ${detail}`,
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
      treated: "Tratado",
      treatedDetail: (
        amount: string,
        title: string,
        version: number | null | undefined,
        movedFrom: string | null | undefined
      ) =>
        `No NG: ${amount}${movedFrom ? ` em ${movedFrom}` : ""} · ${title}${
          version ? ` (v${version})` : ""
        }`,
      sourceOnce: (source: string, file: string) =>
        `Origem: ${source} · ${file}`,
      columns: {
        date: "Data",
        unit: "Unidade",
        account: "Conta NG",
        document: "Documento",
        history: "Histórico",
        amount: "Valor",
        origin: "Planilha · linha",
      },
      row: (sheet: string, row: number) => `${sheet} · ${formatNumber(row)}`,
      entries: "Lançamentos",
      sorted: "Ordenados por data",
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
    periodStatus: (period: string, count: number) =>
      `${period} · ${count === 1 ? "1 item pendente" : `${formatNumber(count)} itens pendentes`}`,
    ready: "Pronta para publicação",
    notReady: "Não pronta",
    categoriesLabel: "Tipos de pendência",
    search: "Buscar por documento, conta ou histórico",
    retry: "Tentar de novo",
    allRules: "Todos",
    casesAndEntries: (cases: number, entries: number) =>
      `${plural(cases, "caso", "casos")} · ${plural(entries, "lançamento afetado", "lançamentos afetados")}`,
    entries: (count: number) =>
      count === 1 ? "1 lançamento" : `${formatNumber(count)} lançamentos`,
    classificationGuide: {
      accounts:
        "Contas novas do NG se classificam na tela de Classificação de contas: lá você escolhe a natureza de cada uma, com a sugestão do assistente, e confirma várias de uma vez.",
      amountBasis:
        "Esta pendência some sozinha quando as contas novas recebem uma natureza na Classificação de contas.",
      dreAssignment:
        "A linha da DRE vem da natureza escolhida na Classificação de contas.",
      drePending:
        "A linha da DRE vem da natureza escolhida na Classificação de contas.",
    } as Record<string, string>,
    classificationCta: "Abrir Classificação de contas",
    unmappedGuide: (count: number) =>
      `${count === 1 ? "1 item" : `${formatNumber(count)} itens`} desta lista só ${count === 1 ? "existe" : "existem"} porque a conta ainda não tem natureza. Classifique as contas primeiro: ${count === 1 ? "ele some" : "eles somem"} sozinho${count === 1 ? "" : "s"}.`,
    compare: {
      field: "Campo",
      ng: "NG",
      billing: "Faturamento",
      document: "Documento",
      emission: "Emissão",
      competence: "Competência",
      who: "Unidade / tomador",
      account: "Conta",
      amount: "Valor",
      net: "Valor líquido",
      description: "Histórico / descrição",
      where: "Aba · linha",
      ngTotal: "Valor no NG",
      billingTotal: "Valor no faturamento",
      difference: "Diferença",
      rounding: (value: string) => `R$ ${value} — só arredondamento`,
    },
    duplicate: {
      field: "Campo",
      kept: "Primeira linha",
      repeated: "Linha repetida",
      stays: "fica na DRE",
      inQuestion: "em análise",
      where: "Aba · linha",
      document: "Documento",
      date: "Emissão",
      account: "Conta",
      unit: "Unidade",
      amount: "Valor",
      history: "Histórico",
      note: "As duas linhas têm o mesmo valor: manter uma ou outra não muda a DRE. O que importa é se são o mesmo lançamento ou dois lançamentos diferentes.",
    },
    ruleDecisions: {
      "NGF-DUP-DOC": {
        REQUEST_SOURCE_CORRECTION: {
          title: "É o mesmo lançamento: fica só a primeira linha",
          help: "A linha repetida sai da DRE. Corrija no NG para não voltar na próxima importação.",
        },
        JUSTIFY_EXCEPTION: {
          title: "São lançamentos diferentes: ficam os dois",
          help: "Por exemplo duas parcelas no mesmo dia. As duas linhas entram na DRE.",
        },
        MARK_FALSE_POSITIVE: {
          title: "Não é duplicidade",
          help: "O alerta não procede. As duas linhas entram na DRE.",
        },
      },
      "NGF-DUP-EXACT": {
        REQUEST_SOURCE_CORRECTION: {
          title: "É o mesmo lançamento: fica só a primeira linha",
          help: "As repetições saem da DRE. Corrija no NG para não voltar na próxima importação.",
        },
        JUSTIFY_EXCEPTION: {
          title: "São lançamentos diferentes: ficam todos",
          help: "Por exemplo duas parcelas iguais no mesmo dia. Confira no extrato bancário.",
        },
        MARK_FALSE_POSITIVE: {
          title: "Não é duplicidade",
          help: "O alerta não procede. Todas as linhas entram na DRE.",
        },
      },
      "NGF-UNIT-MISSING": {
        JUSTIFY_EXCEPTION: {
          title: "Aceitar sem unidade",
          help: "O lançamento entra na DRE no grupo \u201cSem unidade no NG\u201d. Escreva no motivo qual é a unidade certa, para corrigir no NG.",
        },
        REQUEST_SOURCE_CORRECTION: {
          title: "Tirar da DRE até lançar a unidade no NG",
          help: "O lançamento fica fora da DRE até o arquivo corrigido ser importado.",
        },
        MARK_FALSE_POSITIVE: {
          title: "Não precisa de unidade",
          help: "O lançamento entra na DRE normalmente.",
        },
      },
      "NGF-SRC-ROW-REJECTED": {
        JUSTIFY_EXCEPTION: {
          title: "Pode ficar de fora",
          help: "A linha quebrada no export do NG não entra na DRE e fica registrado o motivo.",
        },
        REQUEST_SOURCE_CORRECTION: {
          title: "Corrigir o arquivo e importar de novo",
          help: "A linha continua pendente até o arquivo corrigido ser importado.",
        },
        MARK_FALSE_POSITIVE: {
          title: "Não é um problema",
          help: "A linha não tinha valor a considerar.",
        },
      },
    } as Record<
      string,
      Record<string, { title: string; help: string } | undefined> | undefined
    >,
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
    decide: "Decidir",
    selectAll: "Selecionar todos desta página",
    selectRow: (item: string) => `Selecionar ${item}`,
    selected: (count: number) =>
      count === 1 ? "1 selecionado" : `${formatNumber(count)} selecionados`,
    decideSelected: "Decidir selecionados",
    clearSelection: "Limpar seleção",
    columns: {
      item: "Item",
      period: "Mês",
      amount: "Valor",
    },
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
      review: {
        label: "Revisão financeira",
        description:
          "Lançamentos do NG que a revisão do TON segurou: duplicidade, unidade ausente e outros.",
        action: "Decida o que fazer com cada caso.",
        rowTitle: "Caso da revisão",
      },
      excludedRows: {
        label: "Linhas rejeitadas na importação",
        description:
          "Linhas do arquivo do NG que não puderam ser lidas, por exemplo com colunas deslocadas.",
        action: "Decida se a linha pode ficar de fora ou se o arquivo precisa ser corrigido.",
        rowTitle: "Linha rejeitada",
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
      action: "Importe em Fontes os lançamentos revisados do NG desses meses.",
      cta: "Abrir Fontes",
    },
    reviewDecisions: {
      JUSTIFY_EXCEPTION: "Aceitar como está",
      MARK_FALSE_POSITIVE: "Não é um problema",
      REQUEST_SOURCE_CORRECTION: "Tirar da DRE até corrigir no NG",
    } as Record<string, string>,
    reviewDecisionHelp: {
      JUSTIFY_EXCEPTION:
        "O caso é conhecido. O lançamento entra na DRE e fica registrado o motivo.",
      MARK_FALSE_POSITIVE:
        "O alerta não procede. O lançamento entra na DRE normalmente.",
      REQUEST_SOURCE_CORRECTION:
        "O lançamento está errado no NG. Em duplicidade, só o primeiro registro fica na DRE até o arquivo corrigido ser importado.",
    } as Record<string, string>,
    justification: {
      label: "Motivo da aceitação",
      BUSINESS_EXCEPTION: "Regra da Controladoria",
      LEGITIMATE_REPETITION: "Repetição legítima",
      EXPORT_ARTIFACT: "Defeito do export do NG",
      IMMATERIAL: "Valor sem relevância",
      OTHER: "Outro",
    } as Record<string, string>,
    quickReasons: {
      review: [
        "Conforme decisão da Controladoria",
        "Lançamento conferido no NG",
        "Será corrigido no NG pelo Financeiro",
      ],
      excludedRows: [
        "Quebra de linha no export do NG",
        "Linha sem valor relevante",
      ],
      reconciliation: [
        "Mesma nota com número diferente no NG",
        "Unidade diferente entre NG e faturamento",
        "Nota de outro período",
      ],
      reconciliationAmbiguous: ["Mesma nota conferida no NG e no faturamento"],
    } as Record<string, string[] | undefined>,
    decisions: {
      SUPPLEMENTAL: "As duas valem e se completam",
      EXPECTED_DIFFERENCE: "É a mesma nota, com diferença explicada",
      NOT_SAME_EVENT: "São notas diferentes",
      NG_AUTHORITATIVE: "É a mesma nota: vale o NG",
    },
    dialog: {
      title: "Decisão necessária",
      found: "O que aconteceu",
      suggestion: "Sugestão do TON",
      scope: "Quantos registros são afetados",
      decision: "O que fazer?",
      moreOptions: "Mais opções",
      batchTitle: (count: number) =>
        `${formatNumber(count)} itens selecionados`,
      batchBody:
        "A mesma decisão e o mesmo motivo valem para todos. Cada item fica registrado separadamente no histórico.",
      impactMany: (count: number) =>
        `Vale para ${formatNumber(count)} itens`,
      impactRecompute: "a base é recalculada em seguida",
      impactPair: "Vale para os dois lados desta nota (NG e faturamento)",
      impactRecordOnly: "fica registrada para o próximo recálculo",
      confirmMany: (count: number) =>
        `Confirmar para ${formatNumber(count)} itens`,
      errorWithDetail: (detail: string) =>
        `Não foi possível registrar a decisão: ${detail}`,
      reason: "Justificativa",
      reasonPlaceholder: "Motivo ou referência do documento",
      quickReasons: "Textos prontos",
      reasonOptional: "Motivo (opcional)",
      noteOptional: "Observação (opcional)",
      assignUnit: "Atribuir a unidade certa",
      assignUnitHelp:
        "O lançamento passa a contar na DRE da unidade escolhida. Vale até o NG trazer a unidade e continua valendo se o arquivo for importado de novo.",
      assignUnitPick: "Escolha a unidade",
      recordedMany: (count: number, outcome: string) =>
        `${formatNumber(count)} decisões registradas: ${outcome}`,
      defaultReason: (decision: string) =>
        `${decision} (decisão da Controladoria)`,
      defaultMappingReason: "Aprovado pela Controladoria",
      applyToAll: (count: number, rule: string) =>
        `Aplicar a mesma decisão aos ${formatNumber(count)} casos de “${rule}”`,
      applyToList: (count: number) =>
        `Aplicar a mesma decisão aos ${formatNumber(count)} itens desta lista`,
      applyToAllHint:
        "Cada caso fica registrado separadamente, com a mesma justificativa. A prontidão é recalculada uma vez no final.",
      recordingMany: (done: number, total: number) =>
        `Registrando ${formatNumber(done)} de ${formatNumber(total)} decisões…`,
      authorization: "Quem autorizou",
      authorizationPlaceholder: "Ex.: Controladoria, reunião de 16/10",
      authorizationDefault: "Controladoria",
      facts: {
        document: "Documento",
        unit: "Unidade",
        date: "Emissão",
        amount: "Valor",
        where: "Onde está",
        account: "Conta",
        history: "Histórico",
      },
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
      error:
        "Não foi possível registrar a decisão. Confira a evidência e tente novamente.",
      noPermission:
        "Somente usuários autorizados podem registrar esta decisão. Você pode consultar a evidência.",
      confirmTitle: "Confirme antes de registrar",
    },
  },
  workQueue: {
    title: "O que precisa de você hoje",
    subtitle: (period: string) =>
      `Fechamento de ${period}, fontes, relatórios e ações atribuídas`,
    empty:
      "Nada aguarda uma pessoa agora. O TON avisa quando algo novo precisar de decisão.",
    impact: {
      blocks: "Bloqueia a DRE",
      follow: "Acompanhar",
    },
    origins: {
      closing: "Fechamento",
      sources: "Fontes",
      reports: "Relatórios",
      actions: "Ações atribuídas",
    },
    owner: (owner: string) => `Responsável: ${owner}`,
    deadline: (date: string) => `Prazo: ${date}`,
    sourceFailed: (name: string) => `Importação falhou — ${name}`,
    sourceAttention: (name: string) =>
      `Linhas rejeitadas na importação — ${name}`,
    overdue: (reference: string) => `Ocorrência ${reference} com prazo vencido`,
    overduePrompt: (reference: string) =>
      `Mostre a ocorrência ${reference}: o que foi detectado, o responsável, o prazo e o critério de verificação.`,
    calculate: "A DRE está sem bloqueios. Calcule o resultado do período.",
    reportStale: "Relatório de fechamento desatualizado",
    review: "Revisar",
    apply: "Aplicar",
    decide: "Decidir",
    open: "Abrir",
    askTon: "Ver com o TON",
    more: (count: number) => `+ ${plural(count, "item", "itens")}`,
  },
  decisionLoop: {
    evidenceTitle: "Registros de origem",
    evidenceSample: (shown: number, total: number) =>
      `Mostrando ${formatNumber(shown)} de ${plural(total, "registro", "registros")}`,
    noEvidence:
      "A origem não traz registros individuais para este item. Ele é avaliado pelo período inteiro.",
    origin: {
      NG: "NG / Lançamentos financeiros",
      BILLING: "Faturamento",
    },
    fields: {
      document: "Documento",
      invoice: "Nota fiscal",
      emission: "Emissão",
      competence: "Competência",
      account: "Conta",
      unit: "Unidade de origem",
      counterparty: "Tomador",
      history: "Histórico",
      movement: "Movimento",
      final: "Saldo final",
      service: "Valor do serviço",
      net: "Líquido da nota",
    },
    location: (sheet: string, row: number) => `Aba ${sheet}, linha ${row}`,
    reconciliationGap:
      "Não há registro correspondente do outro lado. Compare documento, data e valor antes de classificar.",
    preview: {
      title: "O que muda se você confirmar",
      unit: (source: string, target: string) =>
        `“${source}” passa a ser lido como a unidade ${target}.`,
      account: (source: string, target: string) =>
        `“${source}” passa a ser lido como a conta ${target}.`,
      amountBasis: (basis: string) =>
        `O realizado desta conta passa a usar ${basis.toLowerCase()}.`,
      dre: (line: string) =>
        `A conta entra na linha “${line}” da DRE. A estrutura ganha uma nova versão.`,
      budgetPeriod: (start: string, end: string | null) =>
        end
          ? `A linha de orçamento passa a valer de ${start} a ${end}.`
          : `A linha de orçamento passa a valer a partir de ${start}.`,
      reconciliation: (decision: string) =>
        `O item passa a ser classificado como “${decision}”.`,
      review: (decision: string) => `O caso passa a ser “${decision}”.`,
      scope: (records: string, periods: string | null) =>
        periods ? `Afeta ${records} em ${periods}` : `Afeta ${records}`,
      recompute:
        "Ao confirmar, o TON registra a decisão com seu nome e recalcula a prontidão para mostrar o antes e o depois.",
      recordOnly:
        "Ao confirmar, a decisão é registrada com seu nome. O recálculo da prontidão depende de uma pessoa com permissão de importação.",
      nothingAutomatic: "Nenhum valor é aprovado automaticamente.",
    },
    working: {
      recording: "Registrando a decisão…",
      recomputing: "Recalculando a prontidão…",
    },
    result: {
      title: "Decisão registrada",
      meta: (version: number | null, who: string | null, when: string) =>
        [version != null ? `Versão ${version}` : null, who, when]
          .filter(Boolean)
          .join(" · "),
      recomputed: "Prontidão recalculada com a decisão",
      notRecomputed:
        "Aguardando recálculo. A prontidão só muda depois que uma pessoa com permissão de importação recalcular a base.",
      before: "Antes",
      now: "Agora",
      total: "Total de pendências",
      unchanged:
        "A prontidão não mudou com esta decisão. Os itens restantes dependem de outras decisões ou dados.",
      nowReady: (period: string) =>
        `A DRE de ${period} não tem mais bloqueios. O cálculo continua sendo uma ação explícita.`,
      stillBlocked: (period: string, count: number) =>
        `A DRE de ${period} ainda tem ${plural(count, "pendência", "pendências")}.`,
      next: "Próxima pendência",
      openDre: "Abrir DRE",
      done: "Concluir",
      rejected:
        "Sugestão rejeitada e registrada. Ela não será proposta de novo.",
    },
    status: {
      READY: "Pronta",
      NOT_READY: "Não pronta",
    },
    pendingBanner: (count: number) =>
      count === 1
        ? "1 decisão registrada ainda não foi aplicada à base do fechamento."
        : `${formatNumber(count)} decisões registradas ainda não foram aplicadas à base do fechamento.`,
    applyNow: "Recalcular agora",
    applying: "Recalculando…",
    applyNeedsPermission:
      "Uma pessoa com permissão de importação precisa recalcular a prontidão.",
    log: {
      title: "Decisões recentes",
      many: (count: number, kind: string) => `${kind} · ${formatNumber(count)} itens`,
      empty: "Nenhuma decisão registrada até agora.",
      applied: "Aplicada",
      pending: "Aguardando recálculo",
      by: (who: string) => `por ${who}`,
      version: (version: number) => `versão ${version}`,
      kinds: {
        UNIT_MAPPING: "Unidade vinculada",
        ACCOUNT_MAPPING: "Conta vinculada",
        BUDGET_ACCOUNT_MAPPING: "Conta da dotação vinculada",
        BUDGET_UNIT_MAPPING: "Unidade da dotação vinculada",
        BUDGET_PERIOD: "Período da dotação definido",
        AMOUNT_BASIS: "Base do realizado definida",
        RECONCILIATION: "Conciliação classificada",
        CANDIDATE_REJECTION: "Sugestão rejeitada",
        DRE_ASSIGNMENT: "Classificação da DRE",
        REVIEW_DECISION: "Pendência decidida",
        REVIEW_CARRIED_OVER: "Decisões reaproveitadas na reimportação",
        CLOSING_TREATMENT: "Tratamento de fechamento",
      },
      outcomes: {
        MOVEMENT: "Movimento",
        FINAL: "Saldo final",
        SUPPLEMENTAL: "Lançamento complementar",
        EXPECTED_DIFFERENCE: "Diferença esperada",
        NOT_SAME_EVENT: "Eventos distintos",
        NG_AUTHORITATIVE: "Prevalece o NG/Keevo",
        EXACT_CODE: "Código idêntico rejeitado",
        LEGACY_REFERENCE: "Referência anterior rejeitada",
        JUSTIFY_EXCEPTION: "Exceção justificada",
        MARK_FALSE_POSITIVE: "Falso positivo",
        REQUEST_SOURCE_CORRECTION: "Correção pedida na origem",
        CONFIRM_SOURCE_CORRECTION: "Correção confirmada",
        ACKNOWLEDGE: "Ciente",
        ACCEPT_RECOMMENDATION: "Sugestão aceita",
        REJECT_RECOMMENDATION: "Sugestão rejeitada",
      } as Record<string, string>,
    },
    triage: {
      evidence: "Sugestão com evidência",
      decision: "Precisa da sua decisão",
      data: "Depende de dados",
    },
    evidenceReady: {
      title: "Pronta para avançar",
      body: (basis: string) =>
        `Há evidência determinística (${basis}). Confira os registros e confirme ou rejeite a sugestão.`,
      EXACT_CODE: "o código de origem é idêntico ao do cadastro",
      APPROVED_MAPPING: "o mesmo valor já foi aprovado antes",
      LEGACY: "referência da planilha anterior da Controladoria",
    },
    explain: {
      title: "Entenda",
      changesNumbers: "Muda números da DRE",
      keepsNumbers: "Não muda números da DRE",
      categories: {
        units: {
          question:
            "O NG usa um nome de unidade que o TON ainda não conhece. Indique a qual unidade da DRE ele corresponde.",
          effect:
            "Os lançamentos passam a contar no resultado dessa unidade, inclusive nas próximas importações com o mesmo nome.",
          changes: true,
        },
        accounts: {
          question:
            "A conta do NG ainda não está ligada a uma conta do plano do TON.",
          effect:
            "Os valores passam a entrar na DRE pela conta escolhida, inclusive nas próximas importações.",
          changes: true,
        },
        budgetAccounts: {
          question:
            "A conta da planilha de dotação ainda não está ligada a uma conta do plano do TON.",
          effect:
            "O orçado dessa linha passa a ser comparado na conta escolhida.",
          changes: true,
        },
        budgetUnits: {
          question:
            "A unidade da planilha de dotação ainda não está ligada a uma unidade da DRE.",
          effect: "O orçado dessa linha passa a contar na unidade escolhida.",
          changes: true,
        },
        amountBasis: {
          question:
            "O NG traz dois valores por lançamento: o movimento e o saldo final. O TON precisa saber qual deles representa o realizado desta conta.",
          effect: "O realizado desta conta passa a usar o valor escolhido.",
          changes: true,
        },
        dreAssignment: {
          question: "A conta ainda não tem lugar na estrutura da DRE.",
          effect: "Os valores da conta passam a aparecer na linha escolhida.",
          changes: true,
        },
        drePending: {
          question:
            "A linha da DRE desta conta foi proposta e falta aprovação.",
          effect: "Os valores da conta passam a aparecer na linha aprovada.",
          changes: true,
        },
        budgetPeriods: {
          question:
            "A planilha de dotação não diz a partir de quando o orçamento vale. O TON não deduz o calendário pelo nome do arquivo nem pelo valor.",
          effect: "O orçado passa a ser distribuído nos meses informados.",
          changes: true,
        },
        reconciliation: {
          question:
            "O TON compara cada receita do NG com as notas do faturamento. Este registro não encontrou par do outro lado.",
          effect:
            "O realizado da DRE vem só do NG. A decisão registra por que a diferença existe e libera o item.",
          changes: false,
        },
        reconciliationAmbiguous: {
          question:
            "Este registro tem mais de um par possível do outro lado, e o TON não escolhe sozinho.",
          effect:
            "O realizado da DRE vem só do NG. A decisão registra qual relação vale e libera o item.",
          changes: false,
        },
        review: {
          question:
            "A revisão do TON encontrou algo nestes lançamentos e os segurou fora da DRE até alguém decidir.",
          effect:
            "Aceitar libera os lançamentos para a DRE; corrigir no NG mantém fora até a reimportação.",
          changes: true,
        },
        excludedRows: {
          question:
            "Esta linha do arquivo do NG não pôde ser lida, então o mês fica incompleto.",
          effect:
            "Aceitar libera o mês sem esta linha; corrigir no NG pede um arquivo novo.",
          changes: true,
        },
      } as Record<
        string,
        { question: string; effect: string; changes: boolean } | undefined
      >,
      options: {
        SUPPLEMENTAL:
          "Os dois registros são válidos e um completa o outro, por exemplo quando a contrapartida está em outro documento ou mês.",
        EXPECTED_DIFFERENCE:
          "É a mesma nota, mas não bate por um motivo conhecido: número diferente no NG, retenção, prazo ou arredondamento.",
        NOT_SAME_EVENT:
          "Mesmo número, mas são fatos diferentes (por exemplo uma nota de 2020). Não devem ser comparadas.",
        NG_AUTHORITATIVE:
          "A nota existe nos dois lados e o valor que vale é o do NG.",
      },
      askTon: "Perguntar ao TON sobre este item",
      askTonShort: "Perguntar ao TON",
      askPrompt: (category: string, item: string, periods: string | null) =>
        `Explique em linguagem simples a pendência "${category}: ${item}"${periods ? ` (${periods})` : ""} do fechamento: o que aconteceu, quais evidências devo conferir e o que cada opção muda. Não decida por mim.`,
    },
    missing: {
      title: "Faltam lançamentos do NG de alguns meses",
      why: (period: string) =>
        `A DRE de ${period} é acumulada no ano: soma janeiro até ${period}. Cada mês sem lançamentos revisados do NG impede a publicação.`,
      have: "A base atual tem",
      missing: "Faltam",
      notDecision:
        "Isto não se resolve com uma decisão: é preciso importar os dados.",
      steps: [
        (range: string) =>
          `Exporte do NG os lançamentos de ${range} em um único arquivo.`,
        (_range: string) =>
          "Importe o arquivo em Fontes, em NG / Lançamentos financeiros. A nova importação substitui a anterior, então o arquivo precisa trazer também os meses que já estão na base.",
        (_range: string) =>
          "O TON revisa os lançamentos e recalcula a prontidão sozinho. Depois volte aqui para ver o que mudou.",
      ],
      range: (from: string, to: string) => `${from} a ${to}`,
      cta: "Importar lançamentos do NG",
    },
    uploadGuidance: {
      ng: "A importação do NG substitui a anterior. O arquivo deve cobrir de janeiro até o mês do fechamento.",
      ngRange: (range: string) =>
        `Para o fechamento, o arquivo deve cobrir ${range}. A importação do NG substitui a anterior.`,
    },
    control: {
      nextTitle: "Próximas ações",
      nextEmpty:
        "Nenhuma ação pendente para este período. A DRE pode ser calculada.",
      applyTitle: (count: number) =>
        count === 1
          ? "Aplicar 1 decisão registrada"
          : `Aplicar ${formatNumber(count)} decisões registradas`,
      applyDetail:
        "Decisões já registradas que ainda não entraram na base do fechamento.",
      resolve: (count: number, label: string) =>
        `${label}: ${plural(count, "item", "itens")} para decidir`,
      importData: (count: number) =>
        `Importar realizado de ${plural(count, "mês", "meses")}`,
      importDetail: "Depende de dados do NG, não de decisão.",
      otherData: (label: string) => label,
      open: "Abrir",
      calculate: "A DRE não tem bloqueios. Calcule para publicar o resultado.",
      calculateCta: "Abrir DRE",
      decisionsTitle: "Decisões recentes",
      seeQueue: "Ver fila",
      reportTitle: "Relatório do fechamento",
      reportNone: "Nenhum relatório de fechamento publicado ainda.",
      reportCurrent: "Gerado sobre a base atual.",
      reportStale: (count: number) =>
        count > 0
          ? `Gerado antes de ${plural(count, "decisão registrada", "decisões registradas")}. Gere novamente para refletir a base atual.`
          : "Gerado sobre uma base anterior. Gere novamente para refletir a base atual.",
      reportOpen: "Abrir relatório",
      changesTitle: "O que mudou desde a análise anterior",
      findingBlocking: "Bloqueia",
      findingInfo: "Informativo",
      findingWhere: (sheet: string, row?: number | null) =>
        row
          ? `Planilha ${sheet} · linha ${formatNumber(row)}`
          : `Planilha ${sheet}`,
    },
    changes: {
      title: "O que mudou na última atualização",
      since: (when: string) => `Comparado com a base anterior, de ${when}`,
      appliedDecisions: (count: number) =>
        `${plural(count, "decisão aplicada", "decisões aplicadas")} nesta atualização`,
      first:
        "Esta é a primeira base com estes dados importados. Ainda não há comparação.",
      noChange: "Nenhuma pendência mudou em relação à base anterior.",
      resolved: (count: number) =>
        plural(count, "pendência resolvida", "pendências resolvidas"),
      added: (count: number) =>
        plural(count, "nova pendência", "novas pendências"),
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
    closingUntil: "Fechamento até",
    headline: (scope: string, first: string, last: string) =>
      first === last
        ? `${scope} · ${formatPeriod(last)}`
        : `${scope} · ${formatShortMonth(first).replace(".", "")} a ${formatShortMonth(last).replace(".", "")} de ${last.slice(0, 4)}`,
    summaryMonth: (line: string, month: string) => `${line} · ${month}`,
    scope: "Unidade/filial",
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
    pasteOpen: "Colar planilha",
    paste: {
      title: "Colar planilha",
      description:
        "Copie as linhas no Excel (com ou sem os títulos) e cole em qualquer célula. Corrija aqui mesmo, confira e importe.",
      close: "Fechar",
      row: "Linha",
      titleOf: (column: string) => `Título da coluna ${column}`,
      cell: (column: string, row: number) => `Coluna ${column}, linha ${row}`,
      removeRow: (row: number) => `Remover a linha ${row}`,
      addRows: "Mais 10 linhas",
      filled: (rows: string) => `${rows} linhas preenchidas`,
      cancel: "Cancelar",
      check: "Conferir",
      checking: "Conferindo…",
      import: (rows: string) => `Importar ${rows} linhas`,
      importing: "Importando…",
      summary: (records: string, errors: number) =>
        errors
          ? `${records} linhas prontas · ${errors} com problema (em destaque na grade)`
          : `${records} linhas prontas para importar`,
      problemAt: (row: number | null, column: string | null, label: string) =>
        `${row ? `Linha ${row}` : "Tabela"}${column ? ` · coluna ${column}` : ""}: ${label}`,
      notRecognized:
        "Não encontrei as colunas obrigatórias: Mês (ou Data de pagamento), Unidade e Valor pago.",
      failed: "Não foi possível conferir a tabela.",
      evidence:
        "A tabela importada fica guardada como arquivo da fonte, com data e autor, como um upload.",
    },
    preview: {
      check: "Ver o que muda",
      confirm: "Confirmar importação",
      title: "O que muda com este arquivo",
      billingRecords: (imported: number, rejected: number) =>
        `${formatNumber(imported)} notas lidas · ${formatNumber(rejected)} rejeitadas`,
      previousImport: (count: number) =>
        `Na importação anterior: ${formatNumber(count)} notas.`,
      billingOnly:
        "O faturamento não muda os lançamentos da DRE. Ele serve para conferir as notas com o NG na conciliação.",
      records: (imported: number, rejected: number) =>
        `${formatNumber(imported)} lançamentos lidos · ${formatNumber(rejected)} rejeitados`,
      carriedOver: "Decisões mantidas (mesma evidência)",
      evidenceChanged: "Voltam para decisão (evidência mudou)",
      reopened: "Reaparecem depois de corrigidas",
      newFindings: "Pendências novas",
      stillOpen: "Continuam pendentes",
      notDetected: "Não aparecem mais neste arquivo",
      firstImport: (count: number) =>
        `Primeira importação desta fonte: ${plural(count, "caso", "casos")} para revisar em Pendências. Um caso pode envolver mais de um lançamento.`,
      toDecide: (count: number) =>
        count === 1
          ? "1 caso vai precisar de decisão depois da importação."
          : `${formatNumber(count)} casos vão precisar de decisão depois da importação.`,
      nothingToDecide: "Nenhuma decisão nova será necessária.",
    },
    history: "Histórico de importações",
    hideHistory: "Ocultar histórico",
    detail: {
      imported: "Importados",
      rejected: "Rejeitados",
      toDecide: "Lançamentos aguardando decisão",
      actionableTitle: "Linhas com problema",
      problems: {
        show: "Ver linhas",
        hide: "Ocultar",
        loading: "Lendo as linhas no arquivo importado…",
        failed: "Não foi possível ler as linhas. Tente de novo.",
        cellsUnavailable:
          "O arquivo importado não pôde ser lido de novo; abaixo só a aba e a linha.",
        columns: {
          place: "Aba e linha",
          column: "Coluna",
          content: "O que está na linha (a coluna com problema em destaque)",
        },
        place: (sheet: string, row: number) => `${sheet} · linha ${row}`,
        emptyCell: (column: string) => `Coluna ${column}: vazia`,
        truncated: (shown: string, total: string) =>
          `Mostrando ${shown} de ${total} linhas.`,
      },
      informational: (count: number) =>
        `${plural(count, "observação da leitura", "observações da leitura")} que não exigem ação`,
      nextNg:
        "Os lançamentos que aguardam decisão ficam fora da DRE até alguém decidir em Pendências.",
      nextOther: "A conferência com o NG foi atualizada. Veja em Pendências.",
      openPending: "Resolver pendências",
      openDre: "Abrir DRE",
    },
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
    rejectedShort: "Rejeitados",
    showDetails: (name: string) => `Mostrar detalhes de ${name}`,
    hideDetails: (name: string) => `Ocultar detalhes de ${name}`,
    health: {
      healthy: "Fontes da DRE importadas",
      missing: (count: number) =>
        count === 1
          ? "Falta importar 1 fonte da DRE"
          : `Faltam importar ${formatNumber(count)} fontes da DRE`,
      withRejections: (count: number) =>
        count === 1
          ? "1 com linhas rejeitadas"
          : `${formatNumber(count)} com linhas rejeitadas`,
      empty: "Nenhuma fonte importada ainda",
      attention: (count: number) =>
        count === 1
          ? "1 fonte teve linhas rejeitadas"
          : `${formatNumber(count)} fontes tiveram linhas rejeitadas`,
      body: "Estado real de cada importação. O TON só analisa o que foi importado; o que falta integrar aparece como pendente.",
      configured: "Fontes da DRE",
      current: "importadas (orçamento é opcional)",
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
  chatFile: {
    open: "Abrir",
    download: "Baixar",
    generated: "Gerado pelo TON",
    kinds: {
      pdf: "PDF",
      xlsx: "Planilha Excel",
      xls: "Planilha Excel",
      csv: "Planilha CSV",
      docx: "Documento Word",
      pptx: "Apresentação",
      txt: "Texto",
      json: "Dados JSON",
      zip: "Arquivo compactado",
      png: "Imagem",
      jpg: "Imagem",
      jpeg: "Imagem",
      svg: "Imagem",
    } as Record<string, string>,
    fallbackKind: "Arquivo",
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
    trace: {
      sources: (count: number) =>
        plural(count, "fonte consultada", "fontes consultadas"),
      records: (count: number) =>
        plural(count, "registro retornado", "registros retornados"),
      items: (count: number) =>
        plural(count, "item encontrado", "itens encontrados"),
      context: (bases: number, structures: number) =>
        `${plural(bases, "base normalizada", "bases normalizadas")} e ${plural(structures, "estrutura de DRE", "estruturas de DRE")} disponíveis`,
      blockers: (count: number, status: string | null) =>
        count > 0
          ? `${plural(count, "pendência impede", "pendências impedem")} a DRE${status ? ` · ${status}` : ""}`
          : `DRE sem pendências${status ? ` · ${status}` : ""}`,
      changes: (before: number, after: number) =>
        `Pendências: ${formatNumber(before)} na base anterior → ${formatNumber(after)} agora`,
    },
    resolveAction: "Resolver",
    importAction: "Importar",
    changesTitle: "O que mudou",
    changesTotals: (before: number, after: number) =>
      `Pendências da DRE: ${formatNumber(before)} antes → ${formatNumber(after)} agora`,
    changesDecisions: (recorded: number, pending: number) =>
      pending > 0
        ? `${plural(recorded, "decisão recente", "decisões recentes")}; ${plural(pending, "aguarda", "aguardam")} recálculo`
        : `${plural(recorded, "decisão recente", "decisões recentes")}, todas aplicadas`,
    openChanges: "Ver no Fechamento",
    dreTitle: "Situação da DRE",
    dreClear: "Nada impede a publicação neste período.",
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
  work: {
    genericQuery: "Consulta",
    queryFailed: "Esta consulta não respondeu. O TON seguiu com o que tinha.",
    subject: { consolidated: "Consolidado", unit: "Unidade" },
    doing: {
      start: "Lendo sua pergunta",
      plan: "Entendendo a pergunta e planejando",
      analyze: "Analisando o que encontrou",
      compose: "Escrevendo a resposta",
      python: "Fazendo um cálculo de apoio",
      file: "Lendo o arquivo anexado",
      parallel: (first: string, more: number) =>
        `${first} e mais ${plural(more, "consulta", "consultas")}`,
    },
    phase: {
      plan: "Entendeu a pergunta e planejou as consultas",
      analyze: "Analisou o que encontrou",
      compose: "Organizou a resposta",
    },
    summary: {
      sources: (total: number, attention: number) =>
        attention > 0
          ? `${plural(total, "fonte", "fontes")} · ${plural(attention, "requer", "requerem")} atenção`
          : plural(total, "fonte", "fontes"),
      context: (bases: number, results: number) =>
        `${plural(bases, "base financeira", "bases financeiras")} · ${plural(results, "DRE calculada", "DREs calculadas")}`,
      findings: (total: number, blocking: number) =>
        blocking > 0
          ? `${plural(total, "achado", "achados")} · ${plural(blocking, "bloqueia", "bloqueiam")} a publicação`
          : plural(total, "achado", "achados"),
      dre: (lines: number, status: string | null) =>
        status
          ? `${plural(lines, "linha da DRE", "linhas da DRE")} · ${status}`
          : plural(lines, "linha da DRE", "linhas da DRE"),
      readiness: (
        blockers: number,
        status: string | null,
        specialists: number
      ) =>
        [
          status ? `DRE ${status.toLowerCase()}` : null,
          blockers > 0
            ? plural(blockers, "pendência", "pendências")
            : "sem pendências",
          specialists > 0
            ? plural(specialists, "especialista atuou", "especialistas atuaram")
            : null,
        ]
          .filter(Boolean)
          .join(" · "),
      billing: (billing: number, actual: number) =>
        `${plural(billing, "nota de faturamento", "notas de faturamento")} · ${plural(actual, "lançamento do NG", "lançamentos do NG")}`,
      budget: (count: number) =>
        count > 0
          ? plural(count, "linha de orçamento", "linhas de orçamento")
          : "Nenhum orçamento importado",
      reconciliationLabel: (label: string) =>
        ({
          Conciliado: "conciliados",
          NG_ONLY: "só no NG",
          BILLING_ONLY: "só no faturamento",
          UNMAPPED: "sem vínculo",
        })[label] ?? label.toLowerCase().replaceAll("_", " "),
      evidence: (count: number) =>
        count > 0
          ? plural(count, "linha de evidência", "linhas de evidência")
          : "Nenhuma linha de evidência no período",
      overdue: (count: number) =>
        count > 0
          ? plural(count, "ação vencida", "ações vencidas")
          : "Nenhuma ação vencida",
      published: "Publicado",
      records: (count: number) => plural(count, "item", "itens"),
    },
    header: {
      empty: "Lendo sua pergunta…",
      worked: (duration: string) => `Trabalhou por ${duration}`,
      workedShort: "Análise concluída",
      stopped: "Análise interrompida",
      queries: (count: number) => plural(count, "consulta", "consultas"),
      specialists: (count: number) =>
        plural(count, "especialista", "especialistas"),
      calculations: (count: number) => plural(count, "cálculo", "cálculos"),
      show: "Ver como chegou nisso",
      hide: "Ocultar etapas",
    },
    parallel: (count: number) => `${count} consultas ao mesmo tempo`,
    readData: "Ver o que foi lido",
    hideData: "Ocultar",
    copyRaw: "Copiar dados brutos",
    copyRawTooltip: "Copia a resposta técnica da consulta (administrador)",
    python: {
      title: "Fez um cálculo de apoio",
      running: "Calculando…",
      note: "Cálculo exploratório sobre os números consultados. Não é um valor oficial.",
      showOutput: "Ver resultado",
      showCode: "Ver código",
      files: (count: number) =>
        plural(count, "arquivo gerado", "arquivos gerados"),
      language: "Python",
      output: "Resultado",
      lines: (count: number) => plural(count, "linha", "linhas"),
      copy: "Copiar",
    },
    file: {
      title: (name: string) => `Leu o arquivo ${name}`,
      fallback: "Leu um arquivo anexado",
    },
    other: "Etapa de apoio",
    failed: "Não concluída",
    stoppedNotice:
      "Você interrompeu a análise. O que o TON já consultou continua acima.",
    specialists: {
      title: "Especialistas nesta análise",
      subtitle: "Quem atuou e o que fez em cada etapa do protocolo.",
      waiting: (count: number) =>
        `${plural(count, "especialista aguarda", "especialistas aguardam")} fonte de dados`,
      protocol: (done: number, total: number) =>
        `${formatNumber(done)} de ${formatNumber(total)} etapas concluídas`,
      skippedTitle: "Não executado",
      actions: "Recomenda",
      limitations: "Limites",
      inline: (count: number) =>
        plural(count, "especialista atuou", "especialistas atuaram"),
    },
    details: {
      label: "Detalhes desta resposta",
      sources: "Fontes",
      specialists: "Especialistas",
      results: "Resultados",
    },
    sources: {
      title: "Fontes desta resposta",
      consulted: "Dados consultados",
      origins: "De onde vêm os dados",
      imported: (date: string) => `importado em ${date}`,
      open: (label: string) => `Abrir ${label}`,
      count: (count: number) => plural(count, "fonte", "fontes"),
    },
    data: {
      empty: "A consulta não trouxe dados.",
      showing: (shown: number, total: number) =>
        `Mostrando ${formatNumber(shown)} de ${formatNumber(total)}`,
      yes: "Sim",
      no: "Não",
    },
  },
  assistant: {
    heroTitle: "O que você quer analisar?",
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
    decision: (kind: string, subject: string) => `${kind} — ${subject}`,
    readinessChanged: (before: number, after: number) =>
      `Prontidão recalculada: ${formatNumber(before)} → ${plural(after, "pendência", "pendências")}`,
    dreReady: (period: string) => `A DRE de ${period} ficou sem bloqueios`,
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
      emailFlows: "Fluxos de e-mail",
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
    audit: {
      title: "Trilha de decisões financeiras",
      description: (pending: number) =>
        pending > 0
          ? `Quem decidiu, quando, por quê e em qual versão. ${plural(pending, "decisão aguarda", "decisões aguardam")} recálculo.`
          : "Quem decidiu, quando, por quê e em qual versão. Todas as decisões estão aplicadas.",
    },
    eyebrow: "Configuração",
    title: "Administração do TON",
    description:
      "Fontes, automações e controles do produto para a Vale Norte.",
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
        `${formatNumber(current)} de ${formatNumber(total)} fontes da DRE importadas`,
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
    models: {
      title: "Provedor de IA",
      description:
        "Qual serviço de IA o assistente do TON usa, as chaves de acesso e o modelo padrão.",
      eyebrow: "Administração",
      pageDescription:
        "Conecte um provedor (OpenAI, Anthropic, Google, Azure e outros), escolha os modelos disponíveis e o modelo padrão do assistente.",
      status: (count: number, model: string | null) =>
        count === 0
          ? "Nenhum provedor configurado"
          : model
            ? `Padrão: ${model}`
            : plural(count, "provedor configurado", "provedores configurados"),
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
    brand: "Vale Norte",
    product: "TON",
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
  notFound: {
    eyebrow: "Página não encontrada",
    title: "Este endereço não existe no TON",
    body: "O link pode estar incompleto ou a página mudou de lugar. Volte para a Visão Geral ou use Ctrl + K para buscar.",
    back: "Ir para a Visão Geral",
  },
} as const;
