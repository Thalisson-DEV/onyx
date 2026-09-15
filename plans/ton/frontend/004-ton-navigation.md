# TON-FE-004 — navegação TON na casca existente

**Status: DONE.** Nível 2. Somente `web/` mudou. Nenhum arquivo em `backend/`
foi tocado.

Executado em worktree isolado `../ton-frontend-004`, branch
`ton/frontend-004`, a partir de `1a9b40476abbac0594c40eb264ed3e97e3a14bb3`
(branch `main`, árvore limpa). Esse baseline contém os Planos backend 001, 002,
007, 008a, 003a e 003b (revisão Alembic `faee7eaa921e`).

Este item é arquitetura de informação, não redesenho visual. O redesenho é da
trilha `TON-VIS-*`, que começa por uma auditoria.

## Problema

A navegação autenticada era legível como aplicação de IA genérica, não como TON.

Três defeitos concretos:

1. A entrada principal chamava-se "Nova sessão". O nome descreve uma ação de
   chat, não o ponto central do produto.
2. O destino de especialistas (`/app/agents`) só era alcançável por uma aba
   chamada "Mais agentes", no fim da lista de agentes fixados. O destino lia-se
   como transbordo de uma lista, não como área do produto.
3. Especialistas, projetos e histórico eram três seções irmãs de mesmo peso. Uma
   lista de conversas sem limite ocupava o mesmo nível hierárquico das
   capacidades do produto.

## Navegação anterior

`web/src/sections/sidebar/AppSidebar.tsx`, montado por
`web/src/app/app/layout.tsx`.

```text
Header (fixo, fora do scroll)
├── Nova sessão                → /app
├── Pesquisar chats            → diálogo, sem rota
├── Craft                      → oculto por SHOW_BUILDER_PRODUCT_ENTRY
├── {recolhido} Mais agentes   → /app/agents
└── {recolhido} FoldedProjectsPopover
Body (scroll)
├── Seção "Agentes"
│   ├── agentes fixados        → /app?agentId=N
│   └── Mais agentes / Explorar agentes → /app/agents
├── Seção "Projetos"
│   ├── projetos               → /app?projectId=N
│   └── Novo projeto           → modal, quando vazio
└── Seção "Recentes"
    └── conversas              → /app?chatId=X
Footer
├── Painel de administração    → primeira rota admin permitida
└── AccountPopover
```

## Navegação final

```text
Header (fixo, fora do scroll)
├── nav[aria-label="Navegação do TON"]
│   ├── Central                → /app
│   └── Especialistas          → /app/agents
├── Pesquisar chats            → diálogo, sem rota
├── Craft                      → continua oculto
└── {recolhido} FoldedProjectsPopover
Body (scroll)
├── Seção "Especialistas fixados"   (só quando existe algum fixado)
│   └── especialistas fixados  → /app?agentId=N
├── Seção "Projetos"
│   ├── projetos               → /app?projectId=N
│   └── Novo projeto           → modal, quando vazio
├── Divider                    fronteira produto / histórico
└── nav[aria-label="Histórico de conversas"]
    └── Seção "Conversas"      → /app?chatId=X
Footer                         inalterado
```

Central e Especialistas ficam no `SidebarLayouts.Header`. O header não rola.
Nenhum histórico longo e nenhum estado recolhido empurra os dois destinos fora
de alcance.

## Mapa de rotas

Toda entrada aponta para rota que já existia. Nenhuma rota foi criada.

| Entrada | Destino | Tipo | Arquivo |
|---|---|---|---|
| Central | `/app` | rota | `web/src/app/app/page.tsx` |
| Especialistas | `/app/agents` | rota | `web/src/app/app/agents/page.tsx` |
| especialista fixado | `/app?agentId=N` | estado de consulta em `/app` | `AgentButton.tsx` |
| projeto | `/app?projectId=N` | estado de consulta em `/app` | `ProjectFolderButton.tsx` |
| conversa | `/app?chatId=X` | estado de consulta em `/app` | `ChatButton.tsx` |
| Painel de administração | `getFirstPermittedAdminRoute(...)` | rota admin | `web/src/lib/admin-routes.ts` |

`useAppPosition` (`web/src/lib/position/hooks.ts`) continua a única fonte de
verdade do item ativo. Ela deriva a posição da URL, então `selected` não
depende de estado interno da sidebar.

## Terminologia

`en.json` é a fonte de verdade; `pt.json` carrega a linguagem de produto.

| Chave | Antes (en) | Depois (en) | Depois (pt) |
|---|---|---|---|
| `appSidebar.newSession.label` | New Session | Central | Central |
| `appSidebar.specialists.label` | — | Specialists | Especialistas |
| `appSidebar.agents.title` | Agents | Pinned Specialists | Especialistas fixados |
| `appSidebar.recents.title` | Recents | Conversations | Conversas |
| `appSidebar.recents.empty.text` | Try sending a message! … | Your conversations will appear here. | Suas conversas aparecerão aqui. |
| `appSidebar.productNav.ariaLabel` | — | TON navigation | Navegação do TON |
| `appSidebar.historyNav.ariaLabel` | — | Conversation history | Histórico de conversas |
| `chatSearch.newSession.label` | New Session | Central | Central |
| `appSidebar.projects.title` | Projects | Projects | Projetos |

Removidas: `appSidebar.moreAgents.label` e `appSidebar.exploreAgents.label`. As
duas nomeavam transbordo de lista. O destino agora tem nome próprio, então as
chaves antigas descreviam um conceito que deixou de existir.

`Central` fica sem tradução nos nove catálogos. É nome de produto, e o
repositório já trata `craft.label` assim. `chatSearch.newSession.label` recebeu
o mesmo valor: um destino, um nome, mesmo em duas superfícies.

A paridade de chaves é verificada em tempo de compilação por
`web/src/i18n/messages/keyParity.ts`. Os nove catálogos foram atualizados
juntos: `en`, `pt`, `es`, `fr`, `de`, `ja`, `ko`, `zh`, `ar`.

## Decisão de projeto e conhecimento

**Decisão A — expor a capacidade existente de projetos na navegação primária,
com terminologia TON.**

Motivo: projetos já é a única capacidade de conhecimento com destino real e UX
madura para o usuário. Ela tem seção na sidebar, popover no estado recolhido,
modal de criação, renomeação, exclusão, arraste de conversa para projeto e
painel de contexto. Já estava na navegação primária; a decisão é mantê-la lá.

Não foi criado um agrupamento "Conhecimento". A seção lista projetos e a sua
ação cria projeto. Chamá-la de "Conhecimento" prometeria arquivos e fontes como
destinos, e nenhum dos dois tem rota própria hoje:

- arquivos não têm rota autônoma; vivem no composer, no projeto e em
  `/app/settings`;
- document sets são administrativos (`/admin/document-sets`);
- conectores existem em `/app/settings/connectors`, mas a experiência de fontes
  pertence a `TON-FE-007`, e o roadmap não autoriza expor "Fontes" agora.

Nenhuma página nova foi criada.

## Especialistas fixados

A seção de fixados deixou de conter a aba de destino e passou a desaparecer
quando não há nada fixado. Antes, a seção vazia ainda mostrava um cabeçalho
"Agentes" com uma única aba de transbordo. Um cabeçalho sem itens não é seção.

O que foi preservado sem mudança:

- `usePinnedAgents` e `user.preferences.pinned_assistants`;
- reordenação por arraste (`DndContext` + `SortableContext` + `arrayMove`);
- a regra que fixa um agente ativo ainda não fixado ao arrastá-lo;
- a exclusão do agente unificado (`id === 0`) da lista visível;
- `isAgentTabHighlightable()` para o estado selecionado.

O ícone continua `SvgOnyxOctagon`, o mesmo glifo de agente já usado por
`AgentsNavigationPage`, pela página admin de agentes e por `CustomAgentAvatar`.
A condição que alternava para `SvgMoreHorizontal` saiu: "..." comunica
transbordo, e o item deixou de ser transbordo. A identidade de ícone dos
especialistas pertence a `TON-VIS-007`.

O `data-testid="AppSidebar/more-agents"` foi mantido. Ele identifica a rota, que
não mudou, e é contrato de sete especificações Playwright. Renomeá-lo geraria
churn sem ganho. Como o item deixou de ser condicional, o testid passou a estar
sempre presente, o que torna as especificações existentes mais estáveis.

## Histórico de conversas

O histórico não foi redesenhado. Nenhum comportamento foi removido.

Preservado: `useChatSessions` com `useSWRInfinite` e página de 50, o store
module-level de sessões pendentes, o scroll infinito por `IntersectionObserver`,
a seleção da conversa atual por `useAppPosition`, renomear e excluir em
`ChatButton`, o alvo de soltura `DRAG_TYPES.RECENTS` que remove a conversa do
projeto, e a persistência de scroll por `scrollKey="app-sidebar"`.

Não existe recurso de conversa fixada neste repositório. Fixar aplica-se a
agentes. Nada a preservar nesse ponto.

O que mudou é a posição relativa. O histórico ganhou:

1. um `Divider` acima, marcando onde as capacidades terminam;
2. um landmark `nav` próprio, com nome acessível.

A fronteira é estrutural e semântica, não apenas visual. Refinamento visual
profundo da casca é de `TON-VIS-002`.

## Destinos deliberadamente adiados

Nenhuma rota, nenhum item de menu, nenhum item desabilitado, nenhum "em breve".

| Domínio | Dono | Motivo |
|---|---|---|
| Ocorrências | `TON-FE-008` | Sem contrato de API e sem UX aprovada. O Plano backend 003c pode estar em execução em outro worktree; schema em andamento não autoriza superfície. |
| Relatórios | `TON-FE-009` | Depende do Plano backend 003d e do Plano 006. |
| Fontes | `TON-FE-007` | Sem inventário agregado de fontes. Conectores continuam em `/app/settings/connectors`. |
| Especialistas concretos | `TON-FE-005` | CFO, Frota, Contratos e afins pertencem ao Plano backend 005. Nenhuma persona foi criada. |
| Estado de runtime do especialista | trabalho posterior | Sem "agente online", contagem de ocorrências ou última análise na navegação. |

`web/src/ton/ton-navigation.test.tsx` prova a ausência por três vias: nenhuma
rota `page.tsx`, nenhum `href` contendo o segmento, e nenhuma menção nos nove
catálogos.

## Follow-up do Plano 008a — Groups

Correção de contrato mínima, restrita à navegação, prevista na tabela
"Frontend follow-up required" do Plano backend 008a.

`ADMIN_ROUTES.GROUPS.requiredTier` passou de `Tier.BUSINESS` para `null`.

O Plano 008a removeu o gate comercial de `/manage/admin/user-group`. O frontend
continuava espelhando o gate removido, então a entrada Groups era renderizada
desabilitada com tooltip de indisponibilidade, apesar de o backend já atender um
administrador autorizado.

Limites respeitados:

- `requiredPermission: Permission.MANAGE_USER_GROUPS` intacto. É ele que decide
  acesso;
- nenhuma outra rota administrativa mudou de tier. `API_KEYS` continua
  `Tier.BUSINESS` e `SCIM` continua `Tier.ENTERPRISE`;
- a navegação administrativa não ficou mais ampla: a entrada já era visível,
  apenas desabilitada;
- nenhuma mudança visual.

`web/src/ton/ton-product-surface.test.tsx` afirmava
`ADMIN_ROUTES.GROUPS.requiredTier === Tier.BUSINESS` para provar que o mecanismo
de tier sobreviveu à sanitização de FE-003. A afirmação foi reapontada para
`ADMIN_ROUTES.API_KEYS`, como o próprio Plano 008a prescreve. O mecanismo
continua verificado; só o exemplo mudou.

**Fora deste escopo, ainda em aberto:** as demais linhas da tabela do Plano
008a. `useCanManageGroups()` continua derivando de `useTierAtLeast(Tier.BUSINESS)`,
e os seletores de grupo em `GroupsMultiSelect`, `IsPublicGroupSelector`,
`AgentCard`, `AgentRowActions`, `AgentEditorPage`, `CreateCredential` e
`languageModels/shared` continuam gated por tier. São affordances de página, não
navegação. A página Groups não consulta o tier para CRUD, então a entrada
reabilitada leva a um destino funcional. Corrigir o resto é `TON-CAP-002`.

## Permissões

Visibilidade de frontend não é segurança. Nada de autorização mudou.

- `hasAdminAccess` continua governando a entrada do painel administrativo;
- `getFirstPermittedAdminRoute(adminCapabilities)` continua escolhendo o destino;
- `requiredPermission` de todas as rotas administrativas está intacto;
- Central, Especialistas, Projetos e Conversas nunca foram gated por tier e
  continuam sem gate;
- `AppChrome` mantém `useTierAtLeast(Tier.BUSINESS)` no popover de modo;
- nenhum arquivo de `backend/` mudou, então a aplicação de rota direta segue
  sendo responsabilidade do backend.

## Mobile

`SidebarLayouts.Root` continua dono do comportamento responsivo. Nada nele
mudou.

- `sm` 724px e `md` 912px inalterados;
- overlay mobile, overlay small-screen e coluna desktop inalterados;
- backdrop `role="presentation"` que recolhe ao toque inalterado;
- botão de abrir em `AppChrome`, botão de fechar em `SidebarHeader` e o logo
  recolhido como controle de abertura inalterados;
- atalho Cmd/Ctrl+E inalterado.

O ganho mobile é de alcance. Central e Especialistas estão no header, que não
rola e que continua visível quando o corpo está oculto
(`.opal-sidebar-body__content` é escondido no estado recolhido; o header não).
Antes, com a sidebar aberta no mobile, alcançar o destino de especialistas podia
exigir rolagem sobre agentes fixados.

Verificado em Jest com `window.innerWidth = 375`: os dois destinos permanecem no
landmark de navegação, na mesma ordem.

## Tema claro e escuro

Nenhum token mudou. `git diff` em `web/lib/shared/tokens`,
`web/tailwind-themes` e `web/lib/opal/src` está vazio.

Nenhuma linha adicionada usa `dark:` nem cor built-in do Tailwind. Todo elemento
novo é primitivo existente: `SidebarTab` no variante padrão `sidebar-heavy`,
`Divider` bare e dois elementos `nav` sem classes. `nav` é semântico e não
carrega estilo.

A aba de especialistas deixou de alternar entre `sidebar-light` e
`sidebar-heavy` e passou a usar o padrão, igual às abas vizinhas do header. Isso
alinha o item aos pares em vez de introduzir cor nova.

## Acessibilidade

Melhorias, nenhuma regressão:

- dois landmarks `nav` com nome acessível separam navegação de produto e
  histórico. Antes a sidebar não tinha nenhum landmark de navegação;
- cada aba continua nomeando seu controle de sobreposição via `aria-label`
  (rótulo string) ou `aria-labelledby`, como `SidebarTab` já fazia;
- o item ativo continua exposto por `data-interactive-state="selected"` mais o
  nome acessível do link, não por cor isolada;
- `aria-expanded` das pastas de projeto inalterado;
- foco visível, ordem de tabulação e `FoldedTooltip` inalterados.

## Preservação de FE-003

Nenhuma superfície sanitizada voltou.

`SHOW_BUILDER_PRODUCT_ENTRY &&` continua literal em `AppSidebar.tsx`, incluindo
o comentário que explica a política — `ton-product-surface.test.tsx` verifica
essa string em disco. A entrada Craft, a busca de notificação de build e o
overlay de introdução continuam mortos na build TON.

Sem "Powered by Onyx", sem link para `onyx.app` ou `discord.gg`, sem "Upgrade
Plan", sem "Plans & Billing", sem banner de trial ou pagamento. As quatro
constantes de `web/src/lib/ton/product-surface.ts` continuam `false` e o módulo
não foi tocado.

`ton-navigation.test.tsx` reafirma isso na sidebar renderizada, inclusive com
`onyx_craft_enabled: true` em `useSettings`, para provar que é a política e não
a flag que retém a entrada.

## Capacidades preservadas

Nada útil foi removido. Continuam presentes e sem alteração de contrato:
agentes e personas, projetos, arquivos, conectores, busca, chat, seleção de
modelo, ferramentas, MCP e OpenAPI, administração, autenticação, SSO,
segurança, indexação e histórico.

Uma única entrada de navegação foi eliminada, e por duplicação: a aba de
transbordo no fim da lista de fixados, agora substituída pelo destino no header.
A sidebar ficou com menos itens, não mais.

## Testes e verificações

Especificação nomeada: `web/src/ton/ton-navigation.test.tsx`. A sidebar é
renderizada de verdade; só os hooks de dados e os componentes de linha de outras
fatias são stubs. 28 testes.

| Grupo | O que prova |
|---|---|
| destinos TON | Central existe e aponta `/app`; Especialistas existe e aponta `/app/agents`; os dois no mesmo landmark, nessa ordem; Especialistas alcançável sem nada fixado; fixados são atalho, não destino; Projetos continua visível |
| realidade de rota | todo `href` renderizado resolve para um `page.tsx` existente; Central e Especialistas resolvem por entrada direta |
| domínios adiados | sem rota para ocorrências, relatórios e fontes; sem `href` e sem rótulo, desabilitado ou não; sem menção nos nove catálogos |
| histórico | usável, em landmark próprio, com as linhas e os `href` certos; nenhuma conversa dentro da navegação de produto; Central fora do landmark de histórico; estado vazio próprio |
| alcance | os destinos ficam no header, o histórico no corpo com scroll; os dois destinos permanecem a 375px; nomes acessíveis presentes |
| preservação FE-003 | sem entrada de builder mesmo com a flag ligada; sem copy de commerce ou upstream; sem endereço upstream em nenhum link |
| permissões | sem entrada admin para usuário sem acesso; toda rota admin mantém `requiredPermission` |
| Groups após 008a | `requiredTier` nulo e item não desabilitado em tier community; permissão preservada e item ausente sem ela; nenhuma outra entrada tier-gated foi ampliada |
| catálogo | destinos nomeados nos nove locales; chaves de transbordo retiradas; vocabulário PT-BR fixado |

Playwright: `web/tests/e2e/ton/navigation.spec.ts` com
`web/tests/e2e/pages/TonNavigationPage.ts`. Cobre a matriz tema × viewport
(claro e escuro, 375 e 1280), navegação por clique, entrada direta por URL, 404
dos domínios adiados e fechamento do drawer mobile.

### Checks executados

| Check | Resultado |
|---|---|
| `bun run types:check` | passou; cobertura de tipos 98,81% (233.398 de 236.210 identificadores, 1.245 arquivos), idêntica ao baseline |
| `bun run lint` | passou; 905 avisos, 0 erros, idêntico ao baseline de FE-003; nenhum aviso novo nos arquivos alterados |
| `oxfmt --check` nos 7 arquivos TS alterados e novos | limpo na forma LF, que é a forma committada (`core.autocrlf=true`) |
| `bun run build` | compilou em 79s; a lista de rotas confirma `/app` e `/app/agents` e não contém ocorrências, relatórios ou fontes |
| Jest `src/ton/` | 3 suítes, 44 testes, todos passaram |
| Jest suíte completa | 152 suítes, 1.334 testes; 9 suítes e 61 testes falharam |
| Jest suíte completa no baseline (`git stash`) | 151 suítes, 1.306 testes; 9 suítes e 62 testes falharam |

### Falhas preexistentes, não relacionadas

As mesmas nove suítes falham com e sem FE-004:

`src/app/admin/billing/page`, `src/app/craft/v1/tasks/components/ScheduleTaskForm`,
`src/views/SkillsPage`, `src/views/SkillEditorPage`, `src/lib/auth/components`,
`src/sections/modals/skills/ImportSkillsFromGitHubModal`,
`src/views/admin/ExternalAppsPage/index`,
`src/sections/modals/languageModels/CustomModal`,
`src/app/craft/v1/apps/admin/ConfigureProviderModal`.

O modo predominante é timeout de 5s em modais e formulários. Nenhuma toca
sidebar, navegação, rota ou i18n. A diferença de 62 para 61 testes falhos é
variação de flake nesses mesmos arquivos.

`bun run format:check` falha no repositório inteiro por fim de linha CRLF no
checkout Windows. É preexistente desde TON-FE-000 e não é resultado deste item.

### PLAYWRIGHT DEFERRED — SHARED RUNTIME CONFLICT

Os testes Playwright estão escritos, tipados, formatados e sem aviso de lint,
mas não foram executados ao vivo. Isso é bloqueio de ambiente, não resultado.

Uma stack está no ar e `http://localhost:3000` responde 200. Ela não pode
validar FE-004:

```text
docker inspect onyx-web_server-1
  image   = onyxdotapp/onyx-web-server:latest
  mounts  = (nenhum)
  created = 2026-09-15T02:12:25Z
```

O contêiner roda imagem pronta, sem bind mount do repositório, e foi criado
antes desta mudança. Ele serve o código anterior a FE-004. Executar Playwright
contra ele afirmaria a sidebar antiga e produziria um falso positivo.

As alternativas foram recusadas por segurança de execução concorrente:

1. reconstruir ou reiniciar `onyx-web_server-1` altera estado Docker
   compartilhado e pode ser o contêiner usado pelo Plano backend 003c;
2. subir um segundo frontend contra o mesmo PostgreSQL faria o global-setup do
   Playwright registrar usuários no banco compartilhado, enquanto o Plano 003c
   pode estar operando nele.

A verificação estática, de tipos, de unidade, de componente e de build cobriu o
contrato. Executar `bun run playwright navigation` quando existir um ambiente
que sirva este branch.

## Handoff para TON-VIS-000

A auditoria visual herda esta estrutura. Nada abaixo foi resolvido aqui.

**Hierarquia final:** Central e Especialistas fixados no header; especialistas
fixados, projetos e — após um divider — conversas no corpo com scroll; admin e
conta no footer.

**Onde a casca mora:**

- `web/src/sections/sidebar/AppSidebar.tsx` — dono da navegação autenticada;
- `web/src/app/app/layout.tsx` — monta a sidebar ao lado de `AppChrome`;
- `web/src/layouts/chromes/AppChrome.tsx` — header, conteúdo, painel direito e
  botão de abrir no mobile;
- `web/lib/opal/src/layouts/sidebar/components.tsx` — `Root`, `Header`, `Body`,
  `Footer`, `Section`, fold, overlay, backdrop e persistência de scroll;
- `web/lib/opal/src/layouts/sidebar/styles.css` — todo o visual da casca;
- `web/lib/opal/src/components/buttons/sidebar-tab/components.tsx` — a aba;
- `web/lib/opal/src/layouts/root/components.tsx` — `SidebarStateProvider`.

**Estado ativo e selecionado:** `useAppPosition` deriva a posição da URL.
`SidebarTab` traduz `selected` em `Interactive.Stateful state="selected"`, que
publica `data-interactive-state`. O fold é publicado como atributo `data-folded`
no root, de propósito, para que recolher não re-renderize abas.

**Breakpoints:** `sm` 724px, `md` 912px, `lg` em
`web/tailwind-themes/tailwind.config.js`. Três ramos de layout: overlay mobile,
overlay small-screen com spacer, coluna desktop.

**Dívida visual conhecida, para VIS-000 auditar:**

1. `SvgOnyxOctagon` é o glifo de agente em oito superfícies, incluindo o destino
   Especialistas, `AgentsNavigationPage`, a página admin de agentes e o fallback
   de `CustomAgentAvatar`. É um octógono de marca upstream servindo de semântica
   de agente. Identidade de especialista é `TON-VIS-007`.
2. `SidebarHeader` codifica `"Open Sidebar"` e `"Close Sidebar"` em inglês, sem
   i18n. Opal não tem next-intl; o caminho correto é o contrato `OpalStrings`.
   Sete especificações Playwright dependem desses rótulos.
3. O corpo da sidebar não tem skeleton por seção. Enquanto
   `isLoadingDynamicContent` é verdadeiro, o corpo inteiro renderiza `null`,
   então especialistas fixados, projetos e conversas aparecem de uma vez.
4. `SidebarTabSkeleton` só é usado no scroll infinito de conversas.
5. O logo final Vale Norte não existe (ADR-009). `renderSidebarLogo` usa o
   `Logo` configurável com fallback textual.
6. `AppChrome` é grande e acumula header, popover de modo, painel direito e
   popover de mover conversa.
7. O `Divider` desta fatia é a fronteira mínima possível com primitivo
   existente. VIS-002 decide se a fronteira deve ser espaçamento, superfície ou
   hierarquia tipográfica.

## Fora de escopo, confirmado

- Nenhum arquivo em `backend/` mudou. Nenhum toque em `backend/onyx/db/ton/`,
  `backend/alembic/`, `Finding`, `Occurrence`, `Rule` ou `AnalysisRun`.
- Nenhuma dependência do Plano backend 003c. Os testes de FE-004 passam sem ele.
- Nenhum trabalho de FE-005: nenhuma persona criada, nenhum mapeamento de CFO,
  Frota ou Contratos, nenhuma troca de supervisor, nenhum card de runtime.
- Nenhuma implementação `TON-VIS-*`: nenhuma mudança de raio, borda, sombra,
  espaçamento global, composer, anexos, mensagens, loaders, microinteração,
  ditado ou nova home.
- A sidebar CRM ClearEyed/Twenty não foi usada como referência estrutural. Não
  há troca de workspace, mini-nav de CRM nem hierarquia centrada em CRM.
- O worktree original não foi tocado. Nenhum merge, nenhum push, nenhuma troca
  de branch fora deste worktree.

## Trilha visual futura, documentada e não implementada

`TON-VIS-000` De-Onyx Visual Forensics / Audit ·
`TON-VIS-001` Foundations & Surface Language ·
`TON-VIS-002` TON Shell / Sidebar ·
`TON-VIS-003` Home / New Chat ·
`TON-VIS-004` Composer ·
`TON-VIS-005` Attachments & Context ·
`TON-VIS-006` Messages / Streaming / Tool Activity ·
`TON-VIS-007` Agents / Runtime Identity ·
`TON-VIS-008` Dictation-only Voice ·
`TON-VIS-009` Motion / Microinteractions ·
`TON-VIS-010` Final De-Onyx Visual QA.

VIS-000 audita antes de qualquer implementação visual.

## Arquivos

**Alterados**

- `web/src/sections/sidebar/AppSidebar.tsx`
- `web/src/lib/admin-routes.ts`
- `web/src/i18n/messages/{en,pt,es,fr,de,ja,ko,zh,ar}.json`
- `web/src/ton/ton-product-surface.test.tsx`
- `web/tests/e2e/auth/password_managements.spec.ts`

**Novos**

- `web/src/ton/ton-navigation.test.tsx`
- `web/tests/e2e/ton/navigation.spec.ts`
- `web/tests/e2e/pages/TonNavigationPage.ts`
- `plans/ton/frontend/004-ton-navigation.md`

## Critérios de conclusão

- [x] Central abre `/app`.
- [x] Especialistas abre `/app/agents` e é destino próprio, não transbordo.
- [x] A capacidade de conhecimento exposta é a que existe hoje: projetos.
- [x] Histórico preservado e separado da navegação de produto.
- [x] Nenhum destino morto, desabilitado ou "em breve".
- [x] Nenhuma rota criada; nenhuma página nova.
- [x] Ocorrências e relatórios ausentes da navegação e das rotas.
- [x] Mecânica da sidebar preservada: fold, mobile, arraste, scroll, stores.
- [x] Sanitização de FE-003 intacta.
- [x] Permissões intactas; nenhuma alteração de autorização.
- [x] Tokens de tema intactos; sem `dark:` e sem cor built-in.
- [x] Sem dependência do Plano backend 003c.
- [x] Sem trabalho de FE-005 e sem implementação `TON-VIS-*`.
