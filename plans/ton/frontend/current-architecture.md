# TON frontend: arquitetura atual e plano de preservação

## Escopo e evidência

Este documento registra a arquitetura observada no frontend Onyx e o limite seguro
para adaptar a experiência ao TON. A inspeção foi somente de leitura em 14-09-2026.
O `git status --short` estava limpo. Nenhum arquivo de aplicação foi alterado.

Fontes principais:

- `web/src/app/layout.tsx`: metadata, locale, direção, tema e provedores globais.
- `web/src/app/app/layout.tsx`: autenticação do app, projetos, voz e shell.
- `web/src/views/AppPage.tsx`: composição de chat, busca, projeto, input e fontes.
- `web/src/layouts/chromes/AppChrome.tsx`: header, painéis e comportamento de tela.
- `web/src/sections/sidebar/AppSidebar.tsx` e `AdminSidebar.tsx`: navegação.
- `web/src/lib/admin-routes.ts`: rotas administrativas, permissões e tiers.
- `web/src/proxy.ts` e `web/next.config.js`: proteção, rewrites e redirects.
- `web/lib/shared/tokens/`: tokens semânticos, escala, tipografia e sombras.

## Resumo executivo

O frontend é um app Next.js App Router com uma casca pública, uma casca de
autenticação, uma casca autenticada para o produto e uma casca administrativa.
O chat é o centro da experiência. Agentes, projetos, arquivos, fontes e busca
entram no mesmo `AppPage` por estado e por query params.

A proposta TON deve preservar esse fluxo. O trabalho inicial é de cópia, tokens,
texto e navegação visível. Não há motivo para criar um router paralelo ou uma
segunda implementação de chat. O backend Onyx, os contratos de sessão, os
connectors e a separação CE/EE continuam sendo limites de arquitetura.

## Mapa de runtime

```text
Next root layout
  NextIntlClientProvider + OpalStringsBridge + DirectionProvider
  ThemeProvider + TooltipProvider + SWR + auth/app/gating providers
    /app layout: requireAuth + ProjectsProvider + VoiceModeProvider
      RootLayout.Root
        AppSidebar + AppChrome
          AppPage: ChatUI | SearchUI | ProjectUI
                  AppInputBar + source/document panel
    /admin layout: AdminSSChrome -> AdminChrome -> AdminSidebar
    /auth/*: AuthFlowContainer and auth forms
    /ee/*: license-aware enterprise implementation
```

`web/src/app/layout.tsx` também carrega `Hanken_Grotesk` e `DM_Mono`, resolve o
locale no servidor e configura o atributo de tema da classe. `web/src/app/app/layout.tsx`
exige autenticação antes de montar o app. `web/lib/opal/src/layouts/root` mantém
um único slot de rolagem no layout. Isso reduz o risco de alterar a hierarquia
do chat.

## Router e famílias de tela

| Família | Rotas observadas | Destino TON | Nota de preservação |
|---|---|---|---|
| Entrada | `/` -> `/app`; `/anonymous/[id]`; `/nrf/*` | Manter | `/app/page.tsx` faz o redirect; não duplicar entrada. |
| Chat | `/app`, `/app?chatId=...` | Manter e adaptar texto | `AppPage` resolve sessão, agente, projeto, fontes e input. |
| Chat compartilhado | `/app/shared/[chatId]` | Manter, revisar marca | `SharedChatDisplay` é uma leitura autenticada e reutiliza renderização de mensagens. |
| Agentes | `/app/agents`, `/app/agents/create`, `/app/agents/edit/[id]` | Manter e renomear | `AgentsNavigationPage` e `AgentEditorPage` já cobrem catálogo e edição. |
| Configurações | `/app/settings/*` | Manter, reduzir ruído SaaS | `SettingsLayouts` já tem navegação desktop e select em telas pequenas. |
| Autenticação | `/auth/login`, `signup`, `create-account`, `join`, reset/verificação | Manter e adaptar copy | Há caminhos cloud e self-host em `LoginPage` e `signup/page.tsx`. |
| Admin | `/admin/*` | Manter admin-only | `AdminChrome` exige admin; `ADMIN_ROUTES` controla visibilidade e tier. |
| Enterprise | `/ee/*` e rewrites em `/proxy.ts` | Não expor sem licença | `EEFeatureRedirect` e `ee/layout.tsx` são o limite CE/EE. |
| Craft | `/craft/*`, `/admin/craft/*` | Revisar | É uma superfície própria, flag `onyx_craft_enabled`; não presumir que pertence ao TON. |
| OAuth/callbacks | `/oauth-config`, `/federated/oauth`, `/connector/oauth`, `/mcp/oauth` | Manter interno | São integrações e retornos técnicos, não navegação do usuário final. |

O redirect `/chat` -> `/app` e redirects de rotas legadas estão em
`web/next.config.js`. Não remover aliases durante a fase de cópia.

## Shell, nav e sidebar

`AppSidebar` apresenta nova sessão, busca de chats, Craft condicional, agentes,
projetos, recents e menu de conta. Ela usa DnD para agentes/projetos e lista
infinita de conversas. O agente padrão de ID `0` não aparece como item normal,
mas participa da resolução do chat em `web/src/lib/agents/hooks.ts`.

`AppChrome` decide header, modo chat/busca, compartilhar, mover, exportar,
deletar, incognito, background e painel de fontes. `AdminSidebar` usa a lista
declarativa de `web/src/lib/admin-routes.ts`; entradas podem estar ocultas,
desabilitadas ou limitadas por licença.

Para TON Central, a opção de menor risco é continuar usando o agente padrão e
alterar nome, avatar, descrição e mensagens iniciais via dados/configuração.
Especialistas podem continuar como agentes existentes. Não criar uma navegação
paralela até existir uma decisão de conteúdo e permissão.

## Chat, composer e histórico

`AppPage` organiza três áreas: conteúdo superior, `AppInputBar` no meio e
 sugestões, busca ou sessões do projeto abaixo. `ChatUI` renderiza a árvore de
mensagens e `ChatScrollContainer` controla a leitura. O estado de sessão vive
em `web/src/app/app/stores/useChatSessionStore.ts`, com mapa por sessão,
mensagens, streaming, erro, node selecionado, fila de até cinco mensagens,
abort controllers e arquivos da mensagem.

`AppInputBar` integra `BaseInputBar`, contenteditable, upload, arquivos recentes,
tools, fontes, deep research, multi-model, voz, fila e drag-and-drop. A ação de
anexar usa `FilePickerPopover` e `UserFilesModal`. A visualização de citações e
arquivos do usuário usa `DocumentsSidebar` em painel desktop e modal em mobile.

O histórico aparece como recents na sidebar, busca em `ChatSearchCommandMenu` e
`ProjectChatSessionList` para sessões de projeto. Isso permite um rótulo TON
sem mudar o modelo de sessão. A rota compartilhada permanece somente leitura.

## Projetos, arquivos, conhecimento e conectores

`ProjectsProvider` em `web/src/lib/projects/providers.tsx` carrega projetos,
arquivos recentes, arquivos da mensagem e arquivos do projeto via SWR. Ele faz
upload, link, unlink e delete com atualização otimista. `ProjectFile` distingue
`uploading`, `processing`, `completed`, `skipped`, `failed`, `canceled` e
`deleting` em `web/src/lib/projects/types.ts`.

O picker oferece “Upload files”, um atalho para arquivos recentes e uma modal
“All Recent Files”. O upload usa input HTML oculto e `accept="*/*"`. Um arquivo
recente pode ser selecionado para uma mensagem ou visualizado. Exclusão falha
quando há associação com projeto ou agente e mostra os nomes associados.

O contexto do projeto está em `ProjectContextPanel`: instruções, arquivo,
drag-and-drop, status e contagem de tokens. A UI TON deve distinguir o arquivo
anexado à mensagem do arquivo persistente de projeto, mas o frontend atual não
declara sozinho a política de retenção. A classificação abaixo é a regra
planejada, condicionada ao contrato do servidor:

- Escopo de mensagem: arquivo selecionado ou enviado no contexto de uma
  mensagem; o estado fica em `currentMessageFiles`/sessão. Chamar de
  “temporário” somente após confirmação de retenção e limpeza pelo servidor.
- Escopo persistente: arquivo em projeto ou biblioteca reutilizável, quando o
  servidor declarar essa política; possui status, associações, visualização e
  exclusão controlada.

Knowledge de agente está em `web/src/sections/knowledge/agent-knowledge/*`.
`SourceHierarchyBrowser` oferece busca, breadcrumb, hierarquia, seleção de
documentos/pastas e ordenação. `useAvailableSources` em
`web/src/lib/connectors/hooks.ts` combina fontes indexadas e federadas. Erros
podem parecer uma lista vazia, portanto a UI TON precisa manter estado de erro
distinto de vazio.

Conectores administrativos estão em `/admin/add-connector`,
`/admin/connectors/[connector]`, `/admin/connector/[ccPairId]` e status de
indexação. A página de settings mostra conectores indexados e federados, mas
essa página de usuário não substitui o controle admin.

## Auth, onboarding e limites CE/EE

`LoginPage` e `signup/page.tsx` alternam cloud/self-host, SSO, password,
CAPTCHA e reset com flags de ambiente. `useIsMultiTenant` consulta metadados de
auth. `OnboardingFlow` usa localStorage por usuário para concluir etapas de
admin, nome e provider LLM, além de uma etapa para não-admin. A onboarding atual
é embutida no `AppPage`; sua ordem e estado devem ser preservados.

O `proxy.ts` protege `/admin`, `/agents` e `/connector`. Rotas EE são reescritas
para `/ee` quando habilitadas. `ce.tsx` implementa `paidTierGated`; os tiers são
Community, Business e Enterprise em `web/src/lib/tiers.ts`. `ProductGatingWrapper`
controla acesso e limites de assentos. `web/src/app/ee/LICENSE` registra o
limite de produto licenciado.

### Superfícies SaaS a classificar

| Superfície | Estado preservador TON |
|---|---|
| Billing, upgrade, checkout, portal e lembretes | Ocultar da experiência TON se não houver cobrança TON. Manter código admin somente se a instalação precisar dele. |
| “Powered by Onyx”, docs/changelog e slogan Onyx | Adaptar somente em pontos de marca aprovados; não trocar links técnicos sem destino TON. |
| Enterprise theme, analytics, query history, export logs | Manter sob EE/flag; não expor como capacidade CE. |
| Craft | Revisar com produto TON; flag existente permite desligar a entrada. |
| Connectors, knowledge, indexing e bots | Manter como infraestrutura; mudar apenas labels/copy e permissões decididas. |

## Feature flags e configuração

Há três camadas. Flags de build/env estão em `web/src/lib/constants.ts`, flags
de PostHog em `web/src/lib/analytics/hooks.ts` e settings/backend em
`web/src/lib/settings/types.ts`. Exemplos observados: `NEXT_PUBLIC_CLOUD_ENABLED`,
`NEXT_PUBLIC_FORGOT_PASSWORD_ENABLED`, `onyx_craft_enabled`,
`onyx_craft_available`, `ee_features_enabled`, vector DB, billing e recursos
de analytics.

Qualquer flag TON nova deve controlar a entrada de UI, ter estado ligado e
desligado testado e ter vida curta. A regra de contribuição limita mudanças
reais a incrementos pequenos, preferencialmente até 500 linhas, com flags em
entry points. Não introduzir flag para apenas esconder uma cor. Registrar dono,
default, estado de remoção e impacto CE/EE antes de criar uma flag.

## Matriz TON de gaps e mudança mínima

| Gap TON | Evidência atual | Tratamento preservador | Dono provável |
|---|---|---|---|
| TON Central e especialistas | Agentes e agente padrão em `web/src/lib/agents` | Cópia e dados de agente; manter rotas e RBAC | Produto/conteúdo |
| Identidade Vale Norte | Tokens e theme admin existem; logo TON não existe | Criar tokens semânticos e ponto de logo; não substituir Opal | Design/frontend |
| SaaS visível | Billing, upgrade e Powered by Onyx existem | Classificar por rollout e ocultar nos entry points aprovados | Produto/EE |
| Dark theme | `next-themes` e `semantic-dark.json` existem | Completar mapeamento sem `dark:` ad hoc; testar contraste | Design/frontend |
| Arquivo temporário vs persistente | `currentMessageFiles`, projetos e UserFilesModal | Explicitar copy e estados; não mudar contrato nesta fase | Produto/frontend |
| Mobile | Sidebar overlay, modal de fontes, settings dropdown | Auditar fluxos e corrigir apenas gaps confirmados | Frontend/QA |
| Localização | 9 locales + Opal bridge | Manter infraestrutura; priorizar PT-BR se aprovado | Conteúdo/localização |
| Telegram | Nenhuma tela Telegram observada; connector OAuth existe | Primeiro canal externo; sem stub visual até o Backend 009 | Backend integra; frontend apresenta |

## Orçamento de mudança

Use esta escala antes de qualquer implementação:

| Nível | Significado | Exemplos TON |
|---|---|---|
| 0 | Copy, texto ou configuração | Nome de agente, labels, descrições e links aprovados. |
| 1 | Ajuste de tema ou token | Paleta Vale Norte, logo, favicon e metadata. |
| 2 | Composição ou variante pequena | Ordem de nav, ocultação por flag, modal ou breakpoint corrigido. |
| 3 | Nova página TON com sistema existente | Futura tela de ocorrência ou relatório. |
| 4 | Mudança estrutural de frontend | Fluxo novo que cruza várias cascas e contratos. |
| 5 | Reescrita do design system ou da arquitetura | Substituição da arquitetura visual ou de frontend. |

A fase atual deve ficar nos níveis 0–3. Níveis 4–5 exigem decisão explícita,
contrato e plano próprio.

## Roadmap e backlog de descoberta

1. **F0 — baseline:** fixar inventário, status limpo, owners e flags existentes.
2. **F1 — identidade:** aprovar logo, Vale Norte, nome TON Central e tom de voz.
3. **F2 — tokens/dark:** mapear light/dark semânticos e validar contraste.
4. **F3 — shell:** adaptar metadata, favicon, logo, sidebar, footer e links.
5. **F4 — chat:** adaptar welcome, composer, histórico, fontes e estados vazios.
6. **F5 — agentes/projetos:** nomes de especialistas, projetos e arquivos.
7. **F6 — onboarding/auth:** copy, destino pós-login e etapa admin/non-admin.
8. **F7 — admin/connectors:** separar operação TON de superfícies SaaS.
9. **F8 — mobile:** executar matriz de viewport e corrigir falhas confirmadas.
10. **F9 — i18n:** manter todos os catálogos; publicar PT-BR quando aprovado.
11. **F10 — QA:** Jest, Playwright, a11y e visual light/dark.
12. **F11 — rollout:** flag temporária, métricas e remoção de dívida aprovada.

Backlog mínimo: `TON-ARCH-01` manter rotas e aliases; `TON-BRAND-01` aprovar
ativos; `TON-THEME-01` mapear tokens; `TON-DARK-01` revisar dark; `TON-SHELL-01`
revisar nav/footer; `TON-CHAT-01` copy do composer e welcome; `TON-FILES-01`
clarear temporário/persistente; `TON-ADMIN-01` ocultar SaaS; `TON-MOBILE-01`
matriz mobile; `TON-I18N-01` catálogo PT-BR; `TON-QA-01` cobertura automatizada.

## Decisões registradas

- **D1:** usar App Router e `AppPage` atuais; não criar app paralelo.
- **D2:** Opal é a autoridade visual. `refresh-components` é segunda camada.
- **D3:** manter i18n e bridge Opal; remoção seria mudança ampla sem benefício
  inicial.
- **D4:** tema usa tokens semânticos. Código de tela não recebe `dark:` novo.
- **D5:** CE/EE e tiers continuam limites de acesso.
- **D6:** Telegram é o primeiro canal externo futuro e não deve ser simulado na UI atual.
- **D7:** SaaS não deve aparecer ao usuário TON sem decisão de produto.

## Testes e tooling

O tooling existente está em `web/package.json`: Bun, Oxlint, Oxfmt,
`types:check`, Jest/RTL, Playwright e Storybook. `web/tests/README.md` exige
testes co-localizados, queries por role/label e comportamento observável.
`web/tests/e2e/README.md` exige Page Objects em `web/tests/e2e/pages` e locators
acessíveis. `playwright.config.ts` cobre admin/exclusive/lite; o projeto lite
é útil para verificar ausência de vector DB.

Adicionar testes somente quando uma decisão TON tiver implementação. Cobrir os
dois estados de cada flag, login, `/app`, agentes, projetos, upload, source
panel, settings, admin gate e mobile. Adicionar visual light/dark para shell,
chat, composer e sidebar. Usar a11y para nomes, foco, contraste e navegação de
teclado. Não usar snapshots amplos para mascarar mudanças.

## Complemento obrigatório: change levels e futuros domínios TON

Para manter consistência com o briefing, use esta taxonomia canônica em novos
backlogs. Ela substitui qualquer shorthand anterior deste documento:

| Level | Definição canônica | Exemplo |
|---|---|---|
| 0 | Copy, texto ou configuração | Labels de agente, metadata e links aprovados. |
| 1 | Ajuste de tema ou token | Vale Norte light/dark e logo quando o ativo existir. |
| 2 | Composição ou variante pequena | Item de navegação, modal ou variante de componente. |
| 3 | Nova página TON usando o sistema existente | Futura tela de ocorrência ou relatório. |
| 4 | Mudança estrutural de frontend | Fluxo que cruza cascas, estado e contratos atuais. |
| 5 | Reescrita do design system ou da arquitetura | Substituição da arquitetura visual ou de frontend. |

O backlog inicial deve preferir Levels 0–3. Levels 4–5 exigem justificativa,
owner, dependências e aprovação explícita. Não usar `REMOVE` para uma capacidade
útil só porque ela não estava no briefing; classificar como KEEP, KEEP BUT
RENAME, KEEP BUT HIDE FROM NORMAL USERS, ADAPT, REMOVE FROM CLIENT EXPERIENCE
ou REVIEW LATER.

### Contratos futuros que não existem hoje

Occurrences/findings e reports ainda não têm rota ou entidade TON dedicada.
Para findings, reutilizar no futuro `web/src/layouts/table-layouts.tsx`,
`web/src/app/admin/documents/feedback/DocumentFeedbackTable.tsx`,
`web/src/app/ee/admin/performance/query-history/QueryHistoryTable.tsx`,
`Tag`, `Status` e `Modal`. A página só deve nascer após um contrato para título,
tipo, domínio, severidade, unidade, datas, impacto, evidência, interpretação,
ação, responsável e histórico. Persistência, filtros, histórico e ACL são
dependências de backend documentadas, não tarefas deste objetivo.

Para reports, usar `web/src/views/admin/WorkspaceAnalyticsPage/UsageReports.tsx`
como referência administrativa e decidir entre arquivo persistente, histórico
de execução ou ambos. Geração, armazenamento, status e permissões exigem
backend. NG/Keevo, planilhas e contratos devem entrar pelos fluxos de sources,
connectors e arquivos existentes. Telegram não tem tela atual; uma futura visão
de canal pode ficar junto de `web/src/app/admin/bots/*`, com credenciais,
webhook, entrega e status providos pelo backend.

### Formato de gap analysis para execução futura

| Existing capability | TON requirement | Current fit | Minimum necessary change | Components/routes affected | Backend dependency | Risk | Estimated effort |
|---|---|---|---|---|---|---|---|
| Agent/persona catalog and default agent | TON Central and specialists | Alto | Rename/copy/avatar data; preserve agent UX | `web/src/lib/agents/*`, `AgentsNavigationPage`, `AppSidebar` | Existing persona ACL only | Low | S |
| Tables, tags, status and timeline renderers | Persistent occurrences/findings | Parcial | New Level 3 page after data contract | `table-layouts.tsx`, feedback/query-history tables, `Tag`, `Status`, `Modal` | Occurrence entity, filters, history and ACL | Medium | M |
| Usage report and persistent project files | Generated reports | Parcial | Decide artifact vs run history, then compose existing UI | `UsageReports.tsx`, `ProjectFile`, `UserFilesModal` | Generation, storage, status and permissions | Medium | M |
| Connector/source hierarchy and file picker | NG/Keevo, spreadsheets and contracts | Alto for presentation | Rename source labels; keep source identifiers and error states | `useAvailableSources`, `SourceHierarchyBrowser`, file/project UI | Existing connector/file contracts | Medium | S–M |
| Admin bot/integration routes | Telegram channel | Baixo; no Telegram screen observed | Add status/settings only after channel contract | `web/src/app/admin/bots/*`, admin integrations | Credentials, webhook, delivery and channel ACL | High | L |
| Opal tokens and theme providers | Vale Norte light/dark identity | Alto structurally | Update semantic token mapping and approved assets | `web/lib/shared/tokens/*`, Opal preset, root layout | None for client theme | Medium | S–M |

## Decisões obrigatórias confirmadas

- Não migrar para shadcn/ui e não instalar essa biblioteca.
- Não reescrever o frontend nem substituir a arquitetura Opal/refresh.
- O objetivo frontend não altera backend, APIs, banco, workers ou autenticação.
- Produto somente em português pode ser aceito no futuro; i18n pode ser
  simplificado depois, mas não deve ser removido nesta fase.
- Não há logo TON/Vale Norte final disponível. Não criar placeholder oficial.
- Mobile e dark theme continuam requisitos obrigatórios.
- Não há requisito offline. Não adicionar PWA, IndexedDB ou service worker.
