# Auditoria de superfícies SaaS e upstream

## Resumo da decisão

O frontend contém uma apresentação SaaS cloud completa: cadastro e indicação cloud,
planos, checkout e portal Stripe, lembretes de pagamento, bloqueios por tier, links de
upgrade, recuperação de assinatura e links Onyx/comunidade. TON não deve mostrar isso
como produto comum do cliente.

Mantenha a infraestrutura e os controles de operador que fazem a instalação funcionar.
Oculte a apresentação SaaS do cliente. Use gates e settings existentes, sem reescrever
billing ou APIs de tenant nesta rodada frontend.

## Matriz de superfícies

| Superfície | Evidência | Comportamento atual | Decisão TON |
|---|---|---|---|
| Cadastro cloud | `web/src/app/auth/signup/page.tsx` | Ramifica em `multiTenant`, mostra “Cloud Signup”, indicação e OAuth cloud. | HIDE FROM CLIENT no ramo cloud. Manter fluxo limitado de primeiro usuário self-host para operador, se necessário. |
| Entrada por convite | `web/src/app/auth/join/page.tsx` | Fluxo de convite inclui OAuth cloud e apresentação de indicação. | KEEP + COPY CHANGE. Manter convites e remover copy de aquisição. |
| Entrada de billing | `web/src/app/admin/billing/page.tsx` | Modos cloud/self-host, checkout/portal Stripe, ativação de licença e telas de plano/checkout. | HIDE FROM CLIENT. Manter licença privada somente se o deployment exigir. |
| Planos Business/Enterprise | `web/src/app/admin/billing/PlansView.tsx` | Mostra preços, planos Business/Enterprise, “self-hosting optional” e URL de vendas. | HIDE FROM CLIENT. Não expor comparação de planos ou conversão comercial. |
| Checkout Stripe | `web/src/app/admin/billing/CheckoutView.tsx` | Compra mensal/anual e trial de um mês. | HIDE FROM CLIENT. Não manter caminho de compra frontend para cliente TON comum. |
| Detalhes de assinatura | `web/src/app/admin/billing/BillingDetailsView.tsx` | Trial, expiração, status de assinatura e ações de plano. | HIDE FROM CLIENT. Se mantido, restringir a papel admin privado. |
| Ativação de licença | `web/src/app/admin/billing/LicenseActivationCard.tsx` | Ajuda de ativação aponta para `https://docs.onyx.app/admins/billing/overview`. | HIDE FROM CLIENT; trocar domínio de docs de operador se suporte de licença continuar. |
| Informações de billing | `web/src/app/ee/admin/billing/page.tsx`, `BillingInformationPage.tsx` | Portal de cliente Stripe para billing EE. | HIDE FROM CLIENT; manter atrás de gates EE/operator atuais apenas se necessário. |
| Uso individual e custo de modelo | `web/src/app/app/settings/usage/page.tsx`, `web/src/app/app/settings/usage/lib.ts`, `web/src/lib/swr-keys.ts` | Mostra uso, custo e preços de modelo por `/api/user/usage`; não é plano, billing ou upgrade. | KEEP AS-IS. Preservar esta visão operacional; não transformá-la em copy de plano, billing ou upgrade. |
| Navegação de upgrade | `web/src/lib/admin-sidebar-utils.ts` | Adiciona `upgradePlan` em `/admin/billing` quando `!flags.hasSubscription`. | HIDE FROM CLIENT. Remover da sidebar comum; não remover API de billing. |
| Lembrete de pagamento | `web/src/layouts/chromes/AdminChrome.tsx` | Banner aponta para `/admin/billing`. | HIDE FROM CLIENT. Não mostrar lembrete no shell cliente TON. |
| Restrição de acesso | `web/src/components/errorPages/AccessRestrictedPage.tsx`, `web/src/components/GatedContentWrapper.tsx` | Expiração de assinatura/licença oferece ressubscrição, suporte ou billing. | HIDE FROM CLIENT para recuperação SaaS. Manter erro neutro de operador se licença for necessária. |
| Bloqueios de tier e upsell | `web/src/lib/admin-routes.ts`, `web/src/lib/admin-sidebar-utils.ts`, `web/src/views/SettingsPage.tsx`, `web/src/views/admin/ServiceAccountsPage/index.tsx` | Itens Business/Enterprise aparecem desabilitados ou mostram trial/compra/API key. | HIDE FROM CLIENT. Manter autorização e gates; remover compra de settings visível. |
| Settings de índice cloud/self-host | `web/src/views/admin/IndexSettingsPage/index.tsx` | Abas cloud-managed e self-hosted incluem linguagem de preço. | ADMIN-ONLY + COPY CHANGE. Manter controles de infra; remover framing SaaS e links de preço. |
| Hooks de billing | `web/src/hooks/useBillingInformation.ts`, `useCloudSubscription.ts`, `useLicense.ts` | Selecionam endpoints de billing cloud/self-host e estado de licença/assinatura. | KEEP AS-IS para infraestrutura. Não inferir acesso de cliente pela copy; coordenar política backend futura. |
| Rodapé do app | `web/src/lib/app/hooks.ts`, `web/src/lib/constants.ts` | Renderiza `[Onyx version](https://www.onyx.app/) - Open Source AI Platform`. | HIDE FROM CLIENT ou substituir por identidade TON aprovada. `APP_SLOGAN` e URL upstream são pontos explícitos. |
| Ajuda/docs da conta | `web/src/sections/sidebar/AccountPopover.tsx` | Links para `https://docs.onyx.app` e changelog. | KEEP somente se docs forem operacionais; caso contrário, trocar por suporte/docs Vale Norte. |
| Prompt de suporte padrão | `web/src/providers/AppProvider.tsx` | Sugere `https://discord.gg/4NA5SbzrWb` para suporte. | HIDE FROM CLIENT ou trocar por canal Vale Norte aprovado. Manter caminho configurado se operador precisar. |
| URL de registro | `web/src/lib/constants.ts`, `web/src/app/auth/create-account/page.tsx` | Usa `http://127.0.0.1:3001` por padrão, salvo URL interna. | UNKNOWN / INVESTIGATE. Confirmar uso no deployment antes de mudar ou expor. |
| Branding auth Onyx | `web/src/components/auth/AuthFlowContainer.tsx` | Usa `logoUrl` ou `SvgOnyxLogo` configurado e `appName` de settings. | KEEP + BRAND CHANGE. É ponto de integração de marca; logo final não está no escopo. |

## O que manter

* Auth, SSO, segurança, setup de conectores, indexação, configuração de modelos,
  diagnóstico e demais infraestruturas de operador permanecem atrás das permissões.
* `NEXT_PUBLIC_CLOUD_ENABLED`, `SERVER_SIDE_ONLY__CLOUD_ENABLED`, rewrites EE e hooks
  de licença/assinatura continuam limites de runtime. Não são motivo para apagar APIs
  ou alterar comportamento backend nesta rodada frontend.
* Links de documentação do provider em setup de conector ou modelo podem ser operacionais.
  Revisar cada link pela intenção, sem remover toda URL externa.

## O que ocultar ou substituir

Ocultar da experiência comum do cliente TON:

* cadastro multi-tenant cloud, coleta de indicação, aquisição OAuth cloud e marketing de
  onboarding cloud;
* cards de plano, preço/trial, checkout Stripe, gestão de assinatura, links de venda,
  portais de billing, lembretes de pagamento e navegação `upgradePlan`;
* tooltips de bloqueio por tier e prompts de compra de API key/service account;
* ofertas de ressubscrição após expiração e marketing upstream self-host/open-source;
* footer, ajuda, changelog, Discord, docs e contato para domínios Onyx ou comunidade,
  salvo quando forem docs temporários de operador explicitamente necessários.

A distinção é visibilidade para cliente, não exclusão de código. Rota privada de billing
ou licença pode ser útil para operadores do deployment. Mantê-la fora da `AdminSidebar`
para usuários TON comuns e confirmar a política de papel antes de mudar rotas.

## Riscos e próximos passos

1. Rota billing oculta não pode quebrar gate EE ou licença self-host. Testar contas de
   operador e comum separadamente.
2. Ramos cloud são selecionados por settings e ambiente. Testar configurações cloud e
   self-host antes de remover copy ou navegação.
3. Buscar chaves SaaS equivalentes em todos os catálogos. Remover string inglesa sem
   decisão de chave deixa tradução obsoleta.
4. Trocar links upstream somente após existirem destinos Vale Norte de suporte/docs;
   caso contrário, usar copy neutra em vez de link morto.

## Disposição final — TON-FE-003

**Status: DONE.** Executado sobre `d49ea04e09eb726ad7cea330c038dbd1e3685546`.
Nível 0–2. Nenhum arquivo em `backend/` mudou.

A política de superfície vive em `web/src/lib/ton/product-surface.ts`. São quatro
constantes: `SHOW_UPSTREAM_ATTRIBUTION`, `SHOW_UPSTREAM_LINKS`,
`SHOW_COMMERCE_SURFACES` e `SHOW_BUILDER_PRODUCT_ENTRY`. Todas são `false`.

Elas são constantes, não variáveis de ambiente. Um `process.env` sem prefixo
`NEXT_PUBLIC_` resolve para `undefined` no bundle do cliente, então a política
divergiria entre servidor e cliente. Virar uma constante restaura a superfície
upstream correspondente.

### Matriz de disposição

Legenda de visibilidade: **N** = usuário TON comum, **A** = administrador.

| Superfície | Papel atual | Decisão final | N | A | Capacidade preservada? | Dependência Plano 008? | Cobertura de teste |
|---|---|---|---|---|---|---|---|
| Atribuição "Powered by Onyx" (`lib/app/components.tsx`) | Tagline upstream sob o logo da sidebar | REPLACE CLIENT COPY — não renderiza | oculto | oculto | Sim: env toggle e `hide_onyx_branding` intactos | Não | RTL `ton-product-surface`; Playwright `product-surface`, `appearance_theme_settings` |
| Rodapé do app (`lib/app/hooks.ts`, `constants.ts`) | `[Onyx x.y.z](onyx.app) - Open Source AI Platform` | REPLACE CLIENT COPY — `product.footer.text` com `appName` e `settings.version` | TON | TON | Sim: `custom_lower_disclaimer_content` tem precedência | Não | RTL; Playwright `expectProductFooter` |
| `APP_SLOGAN` | Constante do slogan upstream | REMOVE — sem outro consumidor | n/a | n/a | n/a | Não | RTL (ausência em `constants.ts`) |
| Versão no menu da conta (`AccountPopover.tsx`) | `[Onyx x.y.z](docs.onyx.app/changelog)` + `SvgOnyxLogo` | REPLACE CLIENT COPY — `product.version.label`, sem link nem logo upstream | TON | TON | Sim: versão vem de `/api/settings` | Não | RTL; Playwright `expectNoUpstreamLinks` |
| Help & FAQ no menu da conta | Link para `docs.onyx.app` | HIDE FROM NORMAL USER — `SHOW_UPSTREAM_LINKS` | oculto | oculto | Sim: `custom_help_link_url` continua renderizando | Não | RTL; Playwright |
| Apêndice de suporte no toast (`AppProvider.tsx`) | String inglesa fixa com `discord.gg` | HIDE FROM NORMAL USER | oculto | oculto | Sim: `NEXT_PUBLIC_INCLUDE_ERROR_POPUP_SUPPORT_LINK` intacto | Não | RTL |
| Wordmark upstream em erro (`ErrorPageLayout.tsx`) | `OnyxLogoTypeIcon` do legado `src/components/` | REPLACE CLIENT COPY — usa `Logo` configurável | TON | TON | Sim: respeita `logoUrl` e `application_name` | Não | RTL |
| Docs upstream em erro de config (`ErrorPage.tsx`) | Link `docs.onyx.app` com UTM | HIDE FROM NORMAL USER — variante `adminHintInternal` | oculto | oculto | Sim: `DOCS_BASE_URL` intacto | Não | RTL |
| Comunidade Discord em erro/acesso restrito | `needHelp.text` com `<discordLink>` | HIDE FROM NORMAL USER — variante `needHelpInternal` | oculto | oculto | Sim | Não | RTL |
| Banner de lembrete de pagamento (`AdminChrome.tsx`) | Banner de fim de trial → `/admin/billing` | REMOVE CLIENT-FACING SURFACE | oculto | oculto | Sim: `application_status` e `ApplicationStatus` intactos | Sim — política de trial é do servidor | RTL; Playwright `expectNoCommerceNavigation` |
| Navegação `upgradePlan` (`admin-sidebar-utils.ts`) | Item de sidebar quando `!hasSubscription` | REMOVE CLIENT-FACING ROUTE da navegação | oculto | oculto | Sim: `hasSubscription` continua alimentando gates | Sim — gating de tier | RTL `buildItems`; Playwright |
| Entrada `Plans & Billing` (`admin-routes.ts` `BILLING`) | Item de sidebar quando `hasSubscription` | HIDE FROM NAV — rota, permissão e `matchAdminRoute` preservados | oculto | oculto na nav; rota direta permanece | Sim: rota e página intactas | Sim — autorização de rota direta | RTL `visibleWhen`; Playwright |
| Tooltip de upsell por tier (`AdminSidebar.tsx`) | "Enterprise version of Onyx" com link para billing | REPLACE CLIENT COPY — `capabilityUnavailable.tooltip`, sem plano nem link | n/a | copy neutra | Sim: `requiredTier` e `tierAtLeast` intactos | Sim — enforcement de tier | RTL (tooltip e itens desabilitados) |
| Upsell de token de acesso (`SettingsPage.tsx`) | "Upgrade Plan" → `/admin/billing` | REPLACE CLIENT COPY — `apiKeys.unavailable.description`, sem botão | copy neutra | copy neutra | Sim: `useTierAtLeast` intacto | Sim | RTL; Playwright em `/app/settings/general` |
| Subtítulo do login (`auth.login.welcomeSubtitle`) | "Your open source AI platform for work" | REPLACE CLIENT COPY — tagline TON | TON | TON | Sim: `custom_login_subtitle` tem precedência | Não | RTL |
| Copy de onboarding (`nameStep`, `llmStep`, `finalStep`) | "What should Onyx call you?", "self-hosted models", "Enable Onyx to search" | REPLACE CLIENT COPY — neutra | copy neutra | copy neutra | Sim: nenhum passo removido | Não | RTL |
| Onboarding de provider LLM (`OnboardingFlow.tsx`) | Passos Name/LLM/Final | KEEP ADMIN-ONLY — já era: o ramo `isAdmin` hospeda os passos; o comum só vê `NonAdminStep` | só nome de exibição | setup completo | Sim: nada removido | Não | RTL (contrato do ramo `isAdmin`) |
| Entrada Craft na sidebar do app (`AppSidebar.tsx`) | `SidebarTab` + intro animada sob `onyx_craft_enabled` | HIDE FROM NORMAL USER | oculto | oculto | Sim: rotas `/craft/*`, páginas admin e `onyx_craft_available` intactos | Sim — autorização de rota direta `/craft/*` | RTL; Playwright `expectNoBuilderProductEntry` |
| Craft no painel admin (`CRAFT_ACCESS`, `CRAFT_APPS`, `CRAFT_PREFERENCES`) | Configuração de acesso, apps e preferências | KEEP ADMIN-ONLY — sem mudança | oculto | visível quando `onyx_craft_available` | Sim | Não | RTL (`visibleWhen` continua `true`) |
| Copy cloud/self-hosted e link de preço em `IndexSettingsPage` | Abas de provider e link de preço do provider | KEEP ADMIN-ONLY — sem mudança | oculto | visível | Sim | Não | Fora do escopo desta rodada |
| Badges "Business Plan"/"Enterprise Plan" (`lib/tier-badge.ts`) | Marca o limite de capacidade em duas telas admin | KEEP ADMIN-ONLY — preservado deliberadamente | oculto | visível | Sim | Sim — o vocabulário de tier depende do Plano 008 | RTL (mecanismo de tier preservado) |
| Recuperação de licença/assinatura (`AccessRestrictedPage.tsx`) | Ressubscrição, seat limit e ativação de licença | KEEP para operador; copy neutralizada | só quando o servidor bloqueia | visível | Sim: `useLicense`, `/api/tenants/*` intactos | Sim — o bloqueio é do servidor | RTL (`SHOW_UPSTREAM_LINKS` presente) |
| Hooks de billing/licença (`useBillingInformation`, `useLicense`) | Estado de assinatura e licença | KEEP AS-IS | n/a | n/a | Sim | Sim | Nenhuma mudança |
| Cadastro cloud (`auth/signup`), tenant, impersonate | Ramo multi-tenant | DEFER — já desligado por `NEXT_PUBLIC_CLOUD_ENABLED=false` | oculto | oculto | Sim | Sim — política de tenant | Nenhuma mudança de código |
| Uso e custo de modelo (`/app/settings/usage`) | Visão operacional de uso | KEEP AS-IS | visível | visível | Sim | Não | Nenhuma mudança |

### Superfícies deliberadamente preservadas

Auth, SSO, senha, redirects e o comportamento seguro de redirect do Plano 002.
RBAC, permissões, capacidades e `tierAtLeast`. Usuários, grupos, SCIM.
Personas/agentes, projetos, arquivos, conectores, federação, indexação,
document sets, configuração de modelos e gateway, MCP e OpenAPI actions, bots,
hooks, segurança, tracing, export de logs, analytics, query history, tema admin.
Toda a infraestrutura de licença e billing continua no código.

### Dependências registradas para o Backend Plano 008

1. **Autorização de rota direta.** `/admin/billing`, `/ee/admin/billing` e
   `/craft/*` saíram da navegação, não do roteamento. O servidor precisa negar
   acesso direto quando o papel não autorizar.
2. **Enforcement de tier.** `requiredTier`, `tierAtLeast` e `hasSubscription`
   continuam decidindo capacidade em runtime. Só o Plano 008 pode dizer o que
   pode ser removido ou substituído no servidor.
3. **Política de trial e lembrete de pagamento.** `ApplicationStatus.PAYMENT_REMINDER`
   continua sendo emitido pelo servidor; o frontend apenas não o apresenta.
4. **Bloqueio por licença/assento.** `GATED_ACCESS` e `SEAT_LIMIT_EXCEEDED`
   continuam vindo do servidor e ainda renderizam a página de acesso restrito.
5. **Vocabulário de plano no servidor.** `Tier.COMMUNITY/BUSINESS/ENTERPRISE`
   é contrato de API. Renomear é decisão do Plano 008.
6. **Onboarding cloud e tenant.** Ramos multi-tenant seguem controlados por
   `NEXT_PUBLIC_CLOUD_ENABLED` e por settings do servidor.
