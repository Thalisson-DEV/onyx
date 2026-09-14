# TON frontend: plano de branding e tema

## Objetivo

Aplicar a identidade TON e Vale Norte com mudança visual baixa ou moderada.
Preservar o fluxo Onyx, o contrato de dados e os limites CE/EE. Este é um plano;
não foram alterados tokens, logos ou código de aplicação.

## Estado atual

Os pontos de marca existentes são:

- `web/src/app/layout.tsx`: metadata, favicon, fontes e título do documento.
- `web/src/lib/app/components.tsx`: `Logo`, logo enterprise e texto “Powered by
  Onyx” sujeito a configuração.
- `web/src/sections/sidebar/AccountPopover.tsx`: `SvgOnyxLogo`, docs,
  changelog, settings e suporte.
- `web/src/lib/app/hooks.ts`: footer com link e slogan Onyx.
- `web/src/lib/constants.ts`: `DOCS_BASE_URL`, `APP_SLOGAN`, flags cloud e EE.
- `web/src/app/ee/admin/theme/AppearanceThemeSettings.tsx`: nome da aplicação,
  logo, estilo de logo, greeting, header/footer, login subtitle, help, banners,
  consent e `hide_onyx_branding`.
- `web/src/app/ee/admin/theme/page.tsx`: persistência via
  `/api/admin/enterprise-settings` e upload de logo.
- `web/public/`: ativos públicos, incluindo fontes, sem ativo oficial TON
  identificado nesta inspeção.

O theme admin está em `/ee/admin/theme`, mas o usuário acessa `/admin/theme`.
`web/src/proxy.ts` faz o rewrite quando o recurso EE está habilitado. O e2e
correspondente está em `web/tests/e2e/admin/theme/appearance_theme_settings.spec.ts`.

## Direção de marca

O briefing pede uma identidade institucional com estes grupos de cor:

| Papel | Direção Vale Norte | Uso previsto |
|---|---|---|
| Primária | Verde institucional profundo | Logo, ação primária e foco. |
| Apoio | Verde mais suave | Hover, seleção e superfícies de apoio. |
| Base | Neutros frios ou quentes controlados | Fundo, texto, borda e campos. |
| Acento | Dourado contido | Destaque, status informativo e assinatura. |

Os valores finais ainda não foram aprovados. Não codificar hex direto em uma
tela. Colocar valores nos primitives, criar aliases semânticos e mapear os dois
modos em `semantic-light.json` e `semantic-dark.json`.

A marca deve parecer institucional e útil. Evitar gradientes decorativos,
neon, excesso de dourado e mudança de densidade que prejudique o chat.

## Plano de identidade

1. **Aprovar ativos:** nome oficial, logo claro/escuro, favicon, avatar TON
   Central, variantes Vale Norte e licença de uso.
2. **Definir tokens:** escolher valores de verde, apoio, dourado e neutros.
   Definir estados hover, pressed, disabled, selected, focus e danger.
3. **Definir copy:** slogan, descrição do TON Central, especialistas, CTA de
   login, empty states, ajuda e footer. O destino de cada link deve ser explícito.
4. **Integrar no shell:** metadata, title, favicon, logo, sidebar, account
   popover, footer, tela compartilhada e páginas de auth.
5. **Integrar no produto:** welcome, composer, projetos, arquivos, fontes,
   agentes e settings com os mesmos tokens.
6. **Revisar operação:** admin, connectors e theme settings. Não expor Billing
   e upgrade ao usuário TON sem uma decisão comercial.
7. **Validar:** light, dark, mobile, RTL, foco e contraste antes do rollout.

## Pontos de integração recomendados

| Ponto | Arquivo | Decisão segura |
|---|---|---|
| Documento e fonte | `web/src/app/layout.tsx` | Aplicar metadata e fonte aprovadas. Preservar locale e providers. |
| Logo | `web/src/lib/app/components.tsx` | Encapsular variante TON no `Logo`; manter fallback técnico. |
| Navegação | `web/src/sections/sidebar/AppSidebar.tsx` | Trocar labels e ícone. Preservar DnD, recents e links. |
| Conta | `web/src/sections/sidebar/AccountPopover.tsx` | Trocar marca e links somente com destinos aprovados. |
| Footer | `web/src/lib/app/hooks.ts`, `AppChrome.tsx` | Remover ou adaptar a assinatura Onyx por política. |
| Auth | `web/src/lib/auth/*`, `web/src/app/auth/*` | Manter provedores e alterar apenas copy/ativos. |
| Tema EE | `web/src/app/ee/admin/theme/*` | Usar controls existentes; preservar licença e validação. |
| Tokens | `web/lib/shared/tokens/*` | Alterar semântica, não classes de tela. |
| Opal CSS | `web/lib/opal/src/_reference.css`, `root.css` | Reexportar tokens atuais sem fork. |

## Superfícies a manter, adaptar, ocultar ou revisar

| Superfície | Classificação | Evidência e plano |
|---|---|---|
| TON Central | KEEP + RENAME/BRAND | Agente padrão ID `0` e editor em `web/src/lib/agents`. Usar dados aprovados. |
| Especialistas | KEEP + RENAME | `AgentsNavigationPage` e `AgentButton`; preservar permissões e pin. |
| Chat/composer/histórico | KEEP + BRAND | `AppPage`, `ChatUI`, `AppInputBar`, store de sessão e sidebar. |
| Projetos e arquivos | KEEP + CLARIFY | Provider e picker atuais separam upload, recentes e projeto. Melhorar copy. |
| Knowledge/connectors | KEEP + ADMIN-ONLY | Provider e rotas admin existentes. Não criar integração fictícia. |
| Settings/auth/onboarding | KEEP + ADAPT | Reusar `SettingsLayouts`, `AuthLayouts` e `OnboardingFlow`. |
| Craft | REVIEW | Flag `onyx_craft_enabled` e rotas `/craft/*`. Confirmar pertinência TON. |
| Billing/upgrade/plans | HIDE FROM TON CLIENT | Rotas em `web/src/app/admin/billing`, `PlansView` e `admin-routes`. |
| “Powered by Onyx”/docs Onyx | REVIEW/HIDE | `Logo`, `AccountPopover`, footer e `DOCS_BASE_URL`; trocar somente com link TON. |
| EE analytics/query history | KEEP UNDER EE | Preserve `ee/layout.tsx`, proxy e `paidTierGated`. |
| Telegram | FUTURE, CONFIRMED | Primeiro canal externo; não adicionar navegação sem o contrato backend. |

## i18n e copy

`web/src/i18n/config.ts` mantém `en`, `es`, `pt`, `fr`, `de`, `ja`, `zh`, `ko`
e `ar`, com RTL em árabe. `web/src/i18n/request.ts` carrega inglês como base
com overlay da língua alvo. `OpalStringsBridge` mantém strings Opal alinhadas
com os catálogos.

Decisão inicial: conservar a infraestrutura e priorizar PT-BR se produto aprovar.
Não remover locales no rebrand. A remoção exigiria mudanças de catálogo,
cookie `NEXT_LOCALE`, bridge e testes de paridade. Toda nova copy TON entra em
`web/src/i18n/messages/en.json` e nos demais catálogos conforme a política
existente. Usar ICU para interpolação e não escrever texto literal nas telas.

## Orçamento e gates

- Nível 0: somente texto, copy ou configuração.
- Nível 1: ajuste de tema ou token.
- Nível 2: pequena composição de componentes ou variante.
- Nível 3: nova página TON usando o design system existente.
- Nível 4: mudança estrutural de frontend.
- Nível 5: reescrita do design system ou da arquitetura.

A primeira entrega fica nos níveis 0–3. Níveis 4–5 precisam de decisão de
produto, contrato, owner e plano de teste. Nível 5 é incompatível com este
objetivo. Flags devem ficar nos entry points,
ter estados on/off testados e ser removidas quando o rollout terminar.

## QA da marca

Validar as telas shell, auth, welcome, chat, composer, fontes, arquivos,
projetos, agents, settings, shared chat e admin theme. Para cada tela, testar:

- logo claro e escuro;
- contraste de texto, ação, borda e foco;
- estados hover, pressed, selected, disabled, loading, empty e error;
- viewport desktop e mobile;
- teclado, leitores de tela e nomes de ícones;
- locale PT-BR, fallback em inglês e RTL árabe;
- CE, EE e feature flags ligadas/desligadas;
- links de suporte, docs, versão e logout.

Use Jest/RTL para mapeamentos e cópia condicional. Use Playwright Page Objects
para fluxos visíveis. Use screenshots somente para shell, chat, sidebar,
settings e auth, em light e dark. Ferramentas e regras estão em
`web/package.json`, `web/tests/README.md` e `web/tests/e2e/README.md`.

## Decisões e riscos

- O ativo oficial TON não está no repositório; a aprovação é um bloqueio para
  branding final, mas não para inventário ou plano.
- O theme admin é EE. Não tratá-lo como substituto para tokens CE.
- A remoção de Onyx em URLs, APIs ou licença pode quebrar suporte e contratos;
  ocultar apenas a superfície do cliente quando houver destino novo.
- Rebranding de connectors não altera identificadores de source, APIs ou
  permissões.
- Dourado deve permanecer acento, não substituir estados de sucesso/erro.

## Mapeamento aplicado por TON-FE-002

TON-FE-002 aplicou a paleta na arquitetura de tokens compartilhados.
Nenhum componente React recebeu cor direta.

### Paleta Vale Norte

| Grupo | Valores principais | Papel |
|---|---|---|
| Verde | `#0c3b2b`, `#145c42`, `#227653`, `#2f795a` | Ação, foco e identidade. |
| Verde suave | `#69b493`, `#a9cdbd`, `#c3ded2`, `#e1efe8` | Links escuros, hover e selected. |
| Neutro verde | `#08110d` até `#f8f9f8` | Superfícies `background-tint-*`. |
| Dourado | `#876625`, `#a98032`, `#c29c50`, `#f7f0dc` | Acento e tema amber. |

Os aliases `tint-*` agora usam neutros Vale Norte.
O mapeamento preserva texto, borda e superfície como papéis separados.

### Mapeamento light

- `theme-primary-*` usa verde institucional profundo.
- `action-selection-*` usa a escala verde Vale Norte.
- `action-text-link-05` usa `vale-norte-green-80`.
- `theme-amber-*` usa a escala dourada.
- `highlight-accent` usa dourado com 30% de opacidade.

### Mapeamento dark

- `theme-primary-*` usa verdes claros com texto invertido escuro.
- `action-selection-*` usa verdes profundos com texto branco.
- `action-text-link-05` usa verde suave sobre superfície escura.
- `background-tint-00` usa `#08110d`, sem preto puro na superfície principal.
- `theme-amber-*` usa dourado sem brilho neon.

### Decisões de contraste

O teste de tokens mede os pares usados pelos controles Opal.
Texto normal exige contraste 4,5:1.
Foco e limites interativos exigem contraste 3:1.

Os menores resultados medidos foram:

- 4,66:1 para dourado em superfície dourada clara;
- 5,25:1 para ação verde escura com texto branco;
- 7,09:1 para link verde no tema escuro;
- 3,45:1 para foco verde contra a superfície escura principal.

Success, warning, danger e info mantêm as cores semânticas anteriores.
Disabled continua usando os tokens neutros do sistema.

### Validação visual e responsiva

Playwright validou `375x812`, `768x1024` e `1280x720`.
Cada largura passou nos temas light e dark.

O teste cobriu chat, composer, sidebar, agents, settings e popover.
Não houve overflow horizontal.
O foco voltou ao composer após fechar a sidebar mobile.
As variáveis CSS geradas corresponderam aos tokens rastreados.

As capturas ficaram em `web/output/screenshots/` para revisão local.
Esses arquivos são artefatos ignorados e não entram no repositório.

### Refinamentos adiados

- Revisar sombras do composer e de cards em uma tarefa visual futura.
- Revisar vignette e fundos configuráveis de `AppChrome` depois.
- Preservar elevação de dialogs, menus e popovers.
- Revisar ilustrações com fundo próprio quando houver ativo final.

O logo final ainda não existe.
O fallback configurável continua sem alteração.
Links upstream e superfícies SaaS continuam fora deste item.
