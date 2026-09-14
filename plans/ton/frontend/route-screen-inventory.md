# TON — inventário de rotas e telas do frontend

## Escopo da auditoria e baseline

Este é um inventário baseado no código das rotas Next.js significativas em `web/src/app`.
Ele relaciona cada família de rota à decisão de adaptação TON. Handlers de callback e
rotas API catch-all aparecem separadamente porque são infraestrutura de runtime, não telas.

O snapshot da auditoria estava limpo antes da criação dos documentos:
`git status --short`, `git diff --stat` e `git diff --name-only` não retornaram caminhos
de aplicação. O Git exibiu um aviso de permissão para
`C:\Users\Thalisson/.config/git/ignore`; o aviso não produziu diff. Nenhuma mudança
existente foi revertida. Esta rodada permite somente arquivos Markdown em
`docs/ton/frontend/`.

A árvore contém 106 arquivos `page.tsx`. Descendentes dinâmicos são agrupados somente
quando têm a mesma decisão de produto; o anexo registra cada arquivo de página.

## Legenda de classificação

* **KEEP AS-IS**: manter rota e comportamento; verificar apenas copy ou acesso.
* **KEEP + COPY CHANGE**: manter fluxo e limite de dados, mas trocar texto de produto.
* **KEEP + BRAND CHANGE**: manter fluxo e aplicar ponto futuro da marca Vale Norte/TON,
  sem trocar o design system.
* **KEEP + SMALL UX ADAPTATION**: manter rota e fazer ajuste de usabilidade limitado.
* **ADMIN-ONLY**: manter para operadores, administradores ou integração; não expor na
  navegação comum do cliente.
* **HIDE FROM CLIENT**: manter a implementação para operador, mas retirar da experiência
  do cliente.
* **REMOVE LATER**: candidata a remoção posterior após checagem de uso e migração.
* **REQUIRES TON-SPECIFIC EXTENSION**: o host atual é adequado, mas conceitos TON
  exigem contrato de produto antes da implementação.
* **UNKNOWN / INVESTIGATE**: manter enquanto uso, dono ou necessidade são investigados.

## Public and authenticated application routes

| Padrão de rota | Evidência de fonte | Classificação | Decisão e justificativa |
|---|---|---|---|
| `/` | `web/src/app/page.tsx` | KEEP AS-IS | Entrada técnica que redireciona para `/app`; não criar segunda home nesta rodada. |
| `/app` (sem query) | `web/src/app/app/page.tsx`, `web/src/app/app/layout.tsx` | KEEP + BRAND CHANGE | Casca autenticada principal e entrada natural do TON Central. Preservar `requireAuth`, sidebar, chrome responsivo, dark mode e chat. |
| `/app?chatId=...` | `web/src/app/app/page.tsx`, `web/src/lib/position/hooks.ts` | KEEP + SMALL UX ADAPTATION | A posição da sessão pode hospedar achados, ocorrências e relatórios depois. Manter URL e alterar apenas copy aprovada ou UX limitada de anexos. |
| `/app?agentId=...` | `web/src/app/app/page.tsx`, `web/src/lib/position/hooks.ts` | REQUIRES TON-SPECIFIC EXTENSION | A posição atual de Agent pode representar especialista TON. Definir contrato persona/especialista e labels antes de comportamento TON. |
| `/app?projectId=...` | `web/src/app/app/page.tsx`, `web/src/lib/position/hooks.ts` | REQUIRES TON-SPECIFIC EXTENSION | Contexto de projeto é o local atual para conhecimento de caso/workspace. Mapear para caso TON somente após contrato de conhecimento persistente. |
| `/app/agents` | `web/src/app/app/agents/page.tsx` | KEEP + COPY CHANGE | Preservar lista, navegação e permissões de especialistas. Renomear Agent apenas quando o vocabulário TON estiver confirmado. |
| `/app/agents/create` | `web/src/app/app/agents/create/page.tsx` | REQUIRES TON-SPECIFIC EXTENSION | Manter host do editor; papel, prompt, escopo de fonte e publicação exigem decisões TON. |
| `/app/agents/edit/[id]` | `web/src/app/app/agents/edit/[id]/page.tsx` | REQUIRES TON-SPECIFIC EXTENSION | Fluxo atual pode manter especialistas. IDs inválidos já redirecionam para `/app`; preservar essa proteção. |
| `/app/settings` | `web/src/app/app/settings/page.tsx` | KEEP AS-IS | Redireciona para `/app/settings/general`; manter entrada estável. |
| `/app/settings/general` | `web/src/app/app/settings/layout.tsx`, `web/src/app/app/settings/general/page.tsx` | KEEP + COPY CHANGE | Manter preferências pessoais e controles de locale/acesso. Remover upsell SaaS se alcançável nesta seção. |
| `/app/settings/chat-preferences` | `web/src/app/app/settings/chat-preferences/page.tsx` | KEEP AS-IS | Preferências neutras de chat fazem parte da casca preservada. |
| `/app/settings/accounts-access` | `web/src/app/app/settings/accounts-access/page.tsx` | KEEP + SMALL UX ADAPTATION | Manter controles de conta e acesso. Verificar que tenant/cloud não apareçam para cliente TON comum. |
| `/app/settings/connectors` | `web/src/app/app/settings/connectors/page.tsx` | ADMIN-ONLY | Tratar credenciais e acesso de conectores como configuração operacional, salvo fluxo de usuário aprovado. |
| `/app/settings/llm-gateway` | `web/src/app/app/settings/llm-gateway/page.tsx` | ADMIN-ONLY | Configuração de gateway é infraestrutura. Manter para operadores autorizados e preservar fronteiras backend. |
| `/app/settings/usage` | `web/src/app/app/settings/usage/page.tsx`, `web/src/app/app/settings/usage/UsageSettings.tsx` | KEEP AS-IS | Esta tela de settings mostra uso, custo e preço de modelos, mas não é plano, billing ou upgrade. Preservar salvo copy limitada aprovada. |
| `/app/shared/[chatId]` | `web/src/app/app/shared/[chatId]/page.tsx` | KEEP + COPY CHANGE | Chat compartilhado é útil para colaboração. Manter auth e recuperação; trocar somente linguagem Onyx. |
| `/anonymous/[id]` | `web/src/app/anonymous/[id]/page.tsx` | UNKNOWN / INVESTIGATE | Sessões anônimas públicas não estão no briefing TON. Confirmar necessidade antes de ocultar. |
| `/nrf/(main)` | `web/src/app/nrf/(main)/page.tsx`, `web/src/app/nrf/(main)/layout.tsx` | KEEP AS-IS | Entrada NRF sem auth para integração/extensão. Preservar como infraestrutura até confirmar distribuição. |
| `/nrf/side-panel` | `web/src/app/nrf/side-panel/page.tsx`, `web/src/app/nrf/layout.tsx` | KEEP AS-IS | Preservar host de side panel e modal de login; não é navegação comum do app. |

`/app` is not protected in the edge proxy. The server-side `requireAuth()` in
`web/src/app/app/layout.tsx` is the effective application guard. This distinction must
remain intact when route copy or navigation changes are made.

## Rotas de autenticação e conta

| Padrão de rota | Evidência de fonte | Classificação | Decisão e justificativa |
|---|---|---|---|
| `/auth/login` | `web/src/app/auth/login/page.tsx`, `web/src/components/auth/AuthFlowContainer.tsx` | KEEP + BRAND CHANGE | Entrada obrigatória. Manter OAuth, SSO, verificação e redirects. A integração de logo/nome em `AuthFlowContainer` é o ponto futuro aprovado da marca TON. |
| `/auth/signup` | `web/src/app/auth/signup/page.tsx` | KEEP + COPY CHANGE; HIDE FROM CLIENT (cloud branch) | Cadastro do primeiro usuário self-host pode ficar para operadores. Ocultar cadastro multi-tenant cloud, indicação e aquisição cloud. |
| `/auth/join` | `web/src/app/auth/join/page.tsx` | KEEP + COPY CHANGE | Convites de equipe continuam úteis. Remover aquisição cloud e preservar token de convite e OAuth. |
| `/auth/create-account` | `web/src/app/auth/create-account/page.tsx` | UNKNOWN / INVESTIGATE | Fluxo genérico aponta para `REGISTRATION_URL` e usa outro logo importado. Confirmar uso em deployments antes de mudar ou ocultar. |
| `/auth/forgot-password` | `web/src/app/auth/forgot-password/page.tsx` | KEEP + COPY CHANGE | Manter quando recuperação de senha estiver habilitada. Já é controlado por `NEXT_PUBLIC_FORGOT_PASSWORD_ENABLED` e modo cloud. |
| `/auth/reset-password` | `web/src/app/auth/reset-password/page.tsx` | KEEP + COPY CHANGE | Manter reset de credencial e trocar somente texto de produto. |
| `/auth/verify-email` | `web/src/app/auth/verify-email/page.tsx` | KEEP AS-IS | Verificação é requisito de auth, não marketing SaaS. Preservar redirects e estados. |
| `/auth/waiting-on-verification` | `web/src/app/auth/waiting-on-verification/page.tsx` | KEEP + COPY CHANGE | Manter espera e usar linguagem neutra de conta TON. |
| `/auth/error` | `web/src/app/auth/error/page.tsx`, `web/src/app/auth/error/layout.tsx` | KEEP + COPY CHANGE | Preservar recuperação e links de login; remover promoção específica de provider. |
| `/auth/impersonate` | `web/src/app/auth/impersonate/page.tsx`, chamada `/api/tenants/impersonate` | ADMIN-ONLY | Impersonação de tenant tem privilégio alto e nunca deve aparecer na navegação do cliente. Auditar autorização antes de qualquer uso. |
| `/auth/logout` | `web/src/app/auth/logout/route.ts` | KEEP AS-IS | Rota técnica de auth; não exige adaptação de tela. |

`AuthFlowContainer` renderiza `logoUrl` configurado ou `SvgOnyxLogo` e lê `appName` de
settings. Manter esse ponto, sem criar logo final ou alterar paleta neste inventário.

## Onboarding (embutido, não é rota)

| Superfície | Evidência de fonte | Classificação | Decisão e justificativa |
|---|---|---|---|
| Onboarding do app | `web/src/sections/onboarding/OnboardingFlow.tsx`, `web/src/sections/onboarding/steps/{NameStep,LLMStep,FinalStep}.tsx`, `web/src/sections/onboarding/components/NonAdminStep.tsx`, `web/src/hooks/useShowOnboarding.ts` | KEEP + SMALL UX ADAPTATION | Onboarding é renderizado dentro de `/app`, sem URL própria. Preservar setup de admin e configuração de modelo, mas ocultar ou adaptar boas-vindas de tenant, convite, web-search e aquisição de imagem para o cliente TON. |

A chave de conclusão é `onyx:onboardingCompleted:<userId>`. A etapa final pode apontar
para `/admin/language-models`; esse destino deve continuar de operador, não de onboarding
do cliente.

## Admin routes

Rotas admin são mantidas para infraestrutura e operadores autorizados. Não devem ser
tratadas como telas comuns do cliente TON. `web/src/lib/admin-routes.ts` é a fonte de
navegação e marca entradas ocultas ou limitadas por tier.

| Família de rota | Evidência de fonte | Classificação | Decisão e justificativa |
|---|---|---|---|
| `/admin/language-models`, `/admin/web-search`, `/admin/image-generation`, `/admin/voice`, `/admin/code-interpreter`, `/admin/chat-preferences` | `web/src/lib/admin-routes.ts` e páginas correspondentes em `web/src/app/admin` | ADMIN-ONLY | Manter infraestrutura de modelo, ferramentas e chat para operadores. Ocultar da navegação comum. |
| `/admin/agents`, `/admin/mcp-actions`, `/admin/openapi-actions` | Páginas correspondentes em `web/src/app/admin` | ADMIN-ONLY; REQUIRES TON-SPECIFIC EXTENSION para governança | Manter configuração de ações e agentes. Definir separadamente dono, permissões e política de fontes dos especialistas TON. |
| `/admin/add-connector`, `/admin/connectors/[connector]`, `/admin/connector/[ccPairId]`, `/admin/federated/[id]`, callbacks OAuth de conectores | `web/src/app/admin/add-connector/page.tsx`, `web/src/app/admin/connectors/[connector]/page.tsx`, `AddConnectorPage.tsx`, `web/src/app/admin/connector/[ccPairId]/page.tsx`, `web/src/app/admin/federated/[id]/page.tsx` | ADMIN-ONLY | Conectores e federação são infraestrutura de fontes. Manter setup e callbacks; não expor credenciais na casca do cliente. |
| `/admin/indexing/status` | `web/src/app/admin/indexing/status/page.tsx`, `web/src/lib/admin-routes.ts` | ADMIN-ONLY | Manter indexação e saúde das fontes para operadores. |
| `/admin/documents/sets`, `/admin/documents/sets/new`, `/admin/documents/sets/[documentSetId]` | Páginas em `web/src/app/admin/documents/sets` | ADMIN-ONLY; REQUIRES TON-SPECIFIC EXTENSION | Document sets são primitiva de conhecimento durável. Preservar e mapear termos de fonte/relatório após contrato TON. |
| `/admin/documents/explorer`, `/admin/documents/feedback`, `/admin/document-processing`, `/admin/index-settings` | Páginas/componentes em `web/src/app/admin/documents` e páginas admin correspondentes | ADMIN-ONLY | Manter inspeção, feedback, processamento e indexação operacional. `index-settings` tem copy cloud/managed para revisar no audit SaaS. |
| `/admin/users`, `/admin/groups`, `/admin/groups/create`, `/admin/groups/[id]`, `/admin/groups2/*`, `/admin/scim` | Páginas correspondentes em `web/src/app/admin` | ADMIN-ONLY | Preservar administração de usuários, grupos e provisionamento. Rotas limitadas por tier não devem virar upsell. |
| `/admin/service-accounts`, `/admin/bots`, `/admin/bots/new`, `/admin/bots/[bot-id]`, `/admin/bots/[bot-id]/channels/*`, `/admin/discord-bot`, `/admin/discord-bot/[guild-id]`, `/admin/hooks` | Páginas correspondentes em `web/src/app/admin` | ADMIN-ONLY | Manter integrações e automação. Telegram é integração futura, não motivo para expor telas ao cliente. |
| `/admin/security`, `/admin/sso-providers`, `/admin/craft/access`, `/admin/craft/apps`, `/admin/craft/preferences` | Páginas correspondentes em `web/src/app/admin` | ADMIN-ONLY | Segurança, SSO e extensões de plataforma pertencem a operadores. |
| `/admin/index-settings`, `/admin/tracing`, `/admin/export-logs`, `/admin/systeminfo`, `/admin/document-processing` | Páginas correspondentes em `web/src/app/admin` | ADMIN-ONLY | Preservar diagnóstico e infraestrutura self-host. Remover promoção self-host de notices visíveis ao cliente. |
| `/admin/performance/usage`, `/admin/performance/analytics`, `/admin/performance/query-history`, `/admin/performance/custom-analytics` | `web/src/app/ee/admin/performance/*`, `web/src/lib/admin-routes.ts` | ADMIN-ONLY | Manter analytics operacional e histórico atrás de gates de licença/feature. |
| `/admin/standard-answer`, `/admin/standard-answer/new`, `/admin/standard-answer/[id]` | `web/src/app/ee/admin/standard-answer/*` | ADMIN-ONLY; UNKNOWN / INVESTIGATE | Navegação está oculta, mas deployments podem usar o recurso. Preservar até confirmar uso e relevância TON. |
| `/admin/theme` | `web/src/app/ee/admin/theme/page.tsx`, `web/src/lib/admin-routes.ts` | ADMIN-ONLY | Manter administração de tema se necessária. Paleta e design system ficam fora desta fase. |
| `/admin/oauth-test` | `web/src/app/admin/oauth-test/page.tsx`, metadata de rota oculta | REMOVE LATER | Superfície de teste interna. Confirmar runbook antes de remover em mudança separada. |
| `/admin/billing` | `web/src/app/admin/billing/page.tsx`, `web/src/layouts/chromes/AdminChrome.tsx`, `web/src/lib/admin-sidebar-utils.ts` | HIDE FROM CLIENT | Ocultar planos, checkout/portal Stripe, trials, assinaturas, lembretes e upgrade do cliente TON. Manter somente se operador precisar de caminho privado de licença. |

`web/src/lib/admin-sidebar-utils.ts` adiciona o item `upgradePlan` para
`/admin/billing` quando não há assinatura. `AdminChrome.tsx` também renderiza um banner
de lembrete de pagamento. Ambos são alvos explícitos de remoção da superfície cliente,
não motivos para remover a infraestrutura admin.

## Rotas Enterprise

| Família de rota | Evidência de fonte | Classificação | Decisão e justificativa |
|---|---|---|---|
| `/ee/admin/billing` | `web/src/app/ee/admin/billing/page.tsx`, `BillingInformationPage.tsx` | HIDE FROM CLIENT | Portal Stripe privado. Manter somente para licença/operação autorizada, se necessário. |
| `/ee/admin/groups*` | Páginas em `web/src/app/ee/admin/groups` | ADMIN-ONLY | Preservar administração de grupos enterprise atrás dos gates EE existentes. |
| `/ee/admin/performance/*` | Páginas em `web/src/app/ee/admin/performance` | ADMIN-ONLY | Preservar uso, analytics, histórico e analytics customizado para operadores. |
| `/ee/admin/export-logs` | `web/src/app/ee/admin/export-logs/page.tsx` | ADMIN-ONLY | Preservar exportação de logs atrás do gate EE existente. |
| `/ee/admin/standard-answer*` | Páginas em `web/src/app/ee/admin/standard-answer` | ADMIN-ONLY; UNKNOWN / INVESTIGATE | Manter nos gates atuais até confirmar uso de produto. |
| `/ee/admin/theme` | `web/src/app/ee/admin/theme/page.tsx` | ADMIN-ONLY | Preservar settings de operador; sem mudança de tema agora. |
| `/ee/agents/stats/[id]` | `web/src/app/ee/agents/stats/[id]/page.tsx` | ADMIN-ONLY | Manter métricas de especialistas privadas para operadores. |

`web/src/proxy.ts` faz rewrite das rotas EE listadas somente quando os recursos enterprise
pagos estão habilitados. O layout EE verifica flag de build e licença/settings em runtime.
Manter esses gates; remover apenas apresentação de plano e compra para o cliente.

## Rotas Craft

| Família de rota | Evidência de fonte | Classificação | Decisão e justificativa |
|---|---|---|---|
| `/craft`, `/craft/v1` | `web/src/app/craft/page.tsx`, `web/src/app/craft/v1/page.tsx`, layouts em `web/src/app/craft` | UNKNOWN / INVESTIGATE | Craft é uma superfície builder distinta. Manter redirect e host enquanto dono e relevância TON são confirmados. |
| `/craft/v1/apps`, `/craft/v1/apps/admin`, `/craft/v1/apps/manage` | Páginas/layouts em `web/src/app/craft/v1/apps` | ADMIN-ONLY | Gestão de apps e OAuth são operações, salvo fluxo de cliente aprovado. |
| `/craft/v1/skills`, `/craft/v1/skills/new`, `/craft/v1/skills/edit/[id]` | Páginas em `web/src/app/craft/v1/skills` | REQUIRES TON-SPECIFIC EXTENSION | Pode hospedar skills de especialistas TON, mas ciclo e permissões exigem decisão. |
| `/craft/v1/tasks`, `/craft/v1/tasks/new`, `/craft/v1/tasks/[id]`, `/craft/v1/tasks/[id]/edit` | Páginas em `web/src/app/craft/v1/tasks` | UNKNOWN / INVESTIGATE | Preservar enquanto se verifica relação com achados, ocorrências ou relatórios. |
| `/craft/v1/apps/oauth/callback` | `web/src/app/craft/v1/apps/oauth/callback/page.tsx` | KEEP AS-IS | Retorno OAuth técnico, sem navegação do cliente. |

## Callbacks técnicos e handlers de rota

| Padrão de rota | Evidência de fonte | Classificação | Decisão e justificativa |
|---|---|---|---|
| `/api/[...path]` | `web/src/app/api/[...path]/route.ts` | KEEP AS-IS | Limite de proxy frontend. Chamadas ao backend devem continuar por esta rota frontend. |
| `/mcp/[[...path]]`, `/api/chat/mcp/oauth/callback`, `/mcp/oauth/callback` | Handlers/páginas correspondentes em `web/src/app` | KEEP AS-IS | Infraestrutura de protocolo e OAuth; sem mudança no inventário de telas. |
| `/auth/oauth/callback`, `/auth/oidc/callback`, `/auth/saml/callback` | Handlers correspondentes em `web/src/app/auth` | KEEP AS-IS | Callbacks de protocolo auth; preservar redirect e state exatos. |
| `/oauth-config/callback`, `/federated/oauth/callback` | Handlers/páginas correspondentes em `web/src/app` | KEEP AS-IS | Infraestrutura de conector/federação, não telas comuns. |
| `/admin/connectors/[connector]/auth/callback`, `/admin/connectors/[connector]/oauth/callback`, `/admin/connectors/[connector]/oauth/finalize` | `web/src/app/admin/connectors/[connector]/auth/callback/route.ts` e páginas callback correspondentes em `web/src/app/admin/connectors/[connector]` | KEEP AS-IS | Callbacks de provider e finalização OAuth são necessários ao setup de conectores; manter privados e operacionais. |

## Gates para próxima etapa

1. Confirmar uso e redirects de `/anonymous/[id]`, `/auth/create-account` e Craft antes
   de ocultar qualquer superfície.
2. Confirmar qual papel de operador acessa `/admin/billing` e `/ee/admin/billing` se a
   licença continuar necessária no deployment.
3. Definir vocabulário TON Central, especialista, achado, ocorrência, relatório e fonte
   antes de trocar labels ou semântica de Agent/Project.
4. Manter guards de rota, rewrites EE, callbacks auth e roteamento frontend-backend
   inalterados durante a auditoria de copy e navegação.


## Anexo: cobertura explícita das páginas

A tabela abaixo foi gerada diretamente da árvore atual e cobre todas as 106 ocorrências de page.tsx em web/src/app. Rotas com segmentos dinâmicos permanecem como padrões. Handlers route.ts continuam no inventário técnico acima.

| Rota | Arquivo | Classificação | Justificativa curta |
|---|---|---|---|
| `/` | `web/src/app/page.tsx` | KEEP AS-IS | Entrada técnica; redirect para /app. |
| `/admin/add-connector` | `web/src/app/admin/add-connector/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/agents` | `web/src/app/admin/agents/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/billing` | `web/src/app/admin/billing/page.tsx` | HIDE FROM CLIENT | Billing, planos e Stripe não entram na UX normal. |
| `/admin/bots` | `web/src/app/admin/bots/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/bots/new` | `web/src/app/admin/bots/new/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/bots/[bot-id]` | `web/src/app/admin/bots/[bot-id]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/bots/[bot-id]/channels/new` | `web/src/app/admin/bots/[bot-id]/channels/new/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/bots/[bot-id]/channels/[id]` | `web/src/app/admin/bots/[bot-id]/channels/[id]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/chat-preferences` | `web/src/app/admin/chat-preferences/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/code-interpreter` | `web/src/app/admin/code-interpreter/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/connector/[ccPairId]` | `web/src/app/admin/connector/[ccPairId]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/connectors/[connector]` | `web/src/app/admin/connectors/[connector]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/connectors/[connector]/oauth/callback` | `web/src/app/admin/connectors/[connector]/oauth/callback/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/connectors/[connector]/oauth/finalize` | `web/src/app/admin/connectors/[connector]/oauth/finalize/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/craft/access` | `web/src/app/admin/craft/access/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/craft/apps` | `web/src/app/admin/craft/apps/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/craft/preferences` | `web/src/app/admin/craft/preferences/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/discord-bot` | `web/src/app/admin/discord-bot/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/discord-bot/[guild-id]` | `web/src/app/admin/discord-bot/[guild-id]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/document-processing` | `web/src/app/admin/document-processing/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/documents/explorer` | `web/src/app/admin/documents/explorer/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/documents/feedback` | `web/src/app/admin/documents/feedback/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/documents/sets` | `web/src/app/admin/documents/sets/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/documents/sets/new` | `web/src/app/admin/documents/sets/new/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/documents/sets/[documentSetId]` | `web/src/app/admin/documents/sets/[documentSetId]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/federated/[id]` | `web/src/app/admin/federated/[id]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/groups` | `web/src/app/admin/groups/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/groups/create` | `web/src/app/admin/groups/create/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/groups/[id]` | `web/src/app/admin/groups/[id]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/groups2` | `web/src/app/admin/groups2/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/groups2/create` | `web/src/app/admin/groups2/create/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/groups2/[id]` | `web/src/app/admin/groups2/[id]/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/hooks` | `web/src/app/admin/hooks/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/image-generation` | `web/src/app/admin/image-generation/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/index-settings` | `web/src/app/admin/index-settings/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/indexing/status` | `web/src/app/admin/indexing/status/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/language-models` | `web/src/app/admin/language-models/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/mcp-actions` | `web/src/app/admin/mcp-actions/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/oauth-test` | `web/src/app/admin/oauth-test/page.tsx` | REMOVE LATER | Superfície técnica; confirmar uso antes de remover. |
| `/admin/openapi-actions` | `web/src/app/admin/openapi-actions/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/scim` | `web/src/app/admin/scim/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/security` | `web/src/app/admin/security/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/service-accounts` | `web/src/app/admin/service-accounts/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/sso-providers` | `web/src/app/admin/sso-providers/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/systeminfo` | `web/src/app/admin/systeminfo/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/tracing` | `web/src/app/admin/tracing/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/users` | `web/src/app/admin/users/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/voice` | `web/src/app/admin/voice/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/admin/web-search` | `web/src/app/admin/web-search/page.tsx` | ADMIN-ONLY | Operação, segurança ou integração restrita a operadores. |
| `/anonymous/[id]` | `web/src/app/anonymous/[id]/page.tsx` | UNKNOWN / INVESTIGATE | Acesso público não está definido no briefing TON. |
| `/app` | `web/src/app/app/page.tsx` | KEEP + BRAND CHANGE | Casca autenticada e entrada natural do TON Central; preservar auth, shell, chat e tema. |
| `/app/agents` | `web/src/app/app/agents/page.tsx` | KEEP + COPY CHANGE | Catálogo de agentes reutilizável para especialistas. |
| `/app/agents/create` | `web/src/app/app/agents/create/page.tsx` | REQUIRES TON-SPECIFIC EXTENSION | Host de especialista existente; contrato TON pendente. |
| `/app/agents/edit/[id]` | `web/src/app/app/agents/edit/[id]/page.tsx` | REQUIRES TON-SPECIFIC EXTENSION | Host de especialista existente; contrato TON pendente. |
| `/app/settings` | `web/src/app/app/settings/page.tsx` | KEEP AS-IS | Entrada técnica; redirect para settings geral. |
| `/app/settings/accounts-access` | `web/src/app/app/settings/accounts-access/page.tsx` | KEEP + SMALL UX ADAPTATION | Manter acesso; remover linguagem cloud quando aplicável. |
| `/app/settings/chat-preferences` | `web/src/app/app/settings/chat-preferences/page.tsx` | KEEP AS-IS | Preferências de conversa são neutras. |
| `/app/settings/connectors` | `web/src/app/app/settings/connectors/page.tsx` | ADMIN-ONLY | Credenciais e gateway são configuração operacional. |
| `/app/settings/general` | `web/src/app/app/settings/general/page.tsx` | KEEP + COPY CHANGE | Preferências preservadas; revisar linguagem SaaS. |
| `/app/settings/llm-gateway` | `web/src/app/app/settings/llm-gateway/page.tsx` | ADMIN-ONLY | Credenciais e gateway são configuração operacional. |
| `/app/settings/usage` | `web/src/app/app/settings/usage/page.tsx` | KEEP AS-IS | Uso, custo e preço de modelo são superfície operacional, não plano, billing ou upgrade. |
| `/app/shared/[chatId]` | `web/src/app/app/shared/[chatId]/page.tsx` | KEEP + COPY CHANGE | Compartilhamento preservado com marca aprovada. |
| `/auth/create-account` | `web/src/app/auth/create-account/page.tsx` | UNKNOWN / INVESTIGATE | Confirmar se este registro externo é usado no deployment. |
| `/auth/error` | `web/src/app/auth/error/page.tsx` | KEEP + COPY CHANGE | Fluxo de autenticação preservado com copy TON. |
| `/auth/forgot-password` | `web/src/app/auth/forgot-password/page.tsx` | KEEP + COPY CHANGE | Fluxo de autenticação preservado com copy TON. |
| `/auth/impersonate` | `web/src/app/auth/impersonate/page.tsx` | ADMIN-ONLY | Impersonação tem privilégio elevado. |
| `/auth/join` | `web/src/app/auth/join/page.tsx` | KEEP + COPY CHANGE | Convite permanece útil; remover aquisição SaaS. |
| `/auth/login` | `web/src/app/auth/login/page.tsx` | KEEP + BRAND CHANGE | Auth obrigatório; aplicar ponto de marca sem alterar segurança. |
| `/auth/reset-password` | `web/src/app/auth/reset-password/page.tsx` | KEEP + COPY CHANGE | Fluxo de autenticação preservado com copy TON. |
| `/auth/signup` | `web/src/app/auth/signup/page.tsx` | KEEP + COPY CHANGE | Manter apenas o fluxo permitido; ocultar aquisição cloud. |
| `/auth/verify-email` | `web/src/app/auth/verify-email/page.tsx` | KEEP AS-IS | Verificação é requisito de autenticação. |
| `/auth/waiting-on-verification` | `web/src/app/auth/waiting-on-verification/page.tsx` | KEEP + COPY CHANGE | Fluxo de autenticação preservado com copy TON. |
| `/craft` | `web/src/app/craft/page.tsx` | UNKNOWN / INVESTIGATE | Builder separado; confirmar pertinência ao TON. |
| `/craft/v1` | `web/src/app/craft/v1/page.tsx` | UNKNOWN / INVESTIGATE | Builder separado; confirmar pertinência ao TON. |
| `/craft/v1/apps` | `web/src/app/craft/v1/apps/page.tsx` | ADMIN-ONLY | Apps externos exigem decisão de acesso. |
| `/craft/v1/apps/admin` | `web/src/app/craft/v1/apps/admin/page.tsx` | ADMIN-ONLY | Gestão de apps e OAuth é operacional. |
| `/craft/v1/apps/manage` | `web/src/app/craft/v1/apps/manage/page.tsx` | ADMIN-ONLY | Gestão de apps e OAuth é operacional. |
| `/craft/v1/apps/oauth/callback` | `web/src/app/craft/v1/apps/oauth/callback/page.tsx` | KEEP AS-IS | Callback técnico sem navegação de cliente. |
| `/craft/v1/skills` | `web/src/app/craft/v1/skills/page.tsx` | REQUIRES TON-SPECIFIC EXTENSION | Pode hospedar skills; ciclo e permissões pendentes. |
| `/craft/v1/skills/edit/[id]` | `web/src/app/craft/v1/skills/edit/[id]/page.tsx` | REQUIRES TON-SPECIFIC EXTENSION | Pode hospedar skills; ciclo e permissões pendentes. |
| `/craft/v1/skills/new` | `web/src/app/craft/v1/skills/new/page.tsx` | REQUIRES TON-SPECIFIC EXTENSION | Pode hospedar skills; ciclo e permissões pendentes. |
| `/craft/v1/tasks` | `web/src/app/craft/v1/tasks/page.tsx` | UNKNOWN / INVESTIGATE | Relação com ocorrências e relatórios ainda não definida. |
| `/craft/v1/tasks/new` | `web/src/app/craft/v1/tasks/new/page.tsx` | UNKNOWN / INVESTIGATE | Relação com ocorrências e relatórios ainda não definida. |
| `/craft/v1/tasks/[id]` | `web/src/app/craft/v1/tasks/[id]/page.tsx` | UNKNOWN / INVESTIGATE | Relação com ocorrências e relatórios ainda não definida. |
| `/craft/v1/tasks/[id]/edit` | `web/src/app/craft/v1/tasks/[id]/edit/page.tsx` | UNKNOWN / INVESTIGATE | Relação com ocorrências e relatórios ainda não definida. |
| `/ee/admin/billing` | `web/src/app/ee/admin/billing/page.tsx` | HIDE FROM CLIENT | Billing, planos e Stripe não entram na UX normal. |
| `/ee/admin/export-logs` | `web/src/app/ee/admin/export-logs/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/groups` | `web/src/app/ee/admin/groups/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/groups/create` | `web/src/app/ee/admin/groups/create/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/groups/[id]` | `web/src/app/ee/admin/groups/[id]/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/performance/analytics` | `web/src/app/ee/admin/performance/analytics/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/performance/custom-analytics` | `web/src/app/ee/admin/performance/custom-analytics/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/performance/query-history` | `web/src/app/ee/admin/performance/query-history/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/performance/query-history/[id]` | `web/src/app/ee/admin/performance/query-history/[id]/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/performance/usage` | `web/src/app/ee/admin/performance/usage/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/standard-answer` | `web/src/app/ee/admin/standard-answer/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/standard-answer/new` | `web/src/app/ee/admin/standard-answer/new/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/standard-answer/[id]` | `web/src/app/ee/admin/standard-answer/[id]/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/admin/theme` | `web/src/app/ee/admin/theme/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/ee/agents/stats/[id]` | `web/src/app/ee/agents/stats/[id]/page.tsx` | ADMIN-ONLY | Superfície EE atrás de licença e permissão. |
| `/federated/oauth/callback` | `web/src/app/federated/oauth/callback/page.tsx` | KEEP AS-IS | Host ou callback técnico fora da navegação normal. |
| `/mcp/oauth/callback` | `web/src/app/mcp/oauth/callback/page.tsx` | KEEP AS-IS | Host ou callback técnico fora da navegação normal. |
| `/nrf` | `web/src/app/nrf/(main)/page.tsx` | KEEP AS-IS | Host ou callback técnico fora da navegação normal. |
| `/nrf/side-panel` | `web/src/app/nrf/side-panel/page.tsx` | KEEP AS-IS | Host ou callback técnico fora da navegação normal. |
| `/oauth-config/callback` | `web/src/app/oauth-config/callback/page.tsx` | KEEP AS-IS | Host ou callback técnico fora da navegação normal. |
