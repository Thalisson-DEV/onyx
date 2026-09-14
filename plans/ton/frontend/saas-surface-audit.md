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
