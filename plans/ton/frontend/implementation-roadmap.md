# TON — roadmap executável do frontend

## Estado e regra de execução

Este roadmap é um backlog de implementação futura. A descoberta desta rodada
não altera `web/` nem `backend/`. Execute os itens na ordem das dependências e
pare quando um item pedir contrato backend ainda não aprovado.

Regra de backend para este backlog: endpoints existentes podem ser consumidos
em implementação futura; endpoints propostos são somente contratos para
decisão. Nenhum item autoriza implementar ou alterar backend nesta fase. Os
itens TON-FE-008 e TON-FE-009 ficam bloqueados até os contratos serem aprovados.

Taxonomia canônica: nível 0 é somente texto, copy ou configuração; nível 1 é
ajuste de tema ou token; nível 2 é pequena composição de componentes ou
variante; nível 3 é nova página TON usando o design system existente; nível 4 é
mudança estrutural de frontend; nível 5 é reescrita do design system ou da
arquitetura.

Os níveis do backlog são inteiros. Nenhuma tarefa deste corte é nível 4 ou 5.
Telegram é o primeiro canal externo planejado. O canal continua fora do núcleo
TON e não será implementado nesta fase. `TON-FE-010` cobre somente a futura
administração, integração e consulta de status. O item fica bloqueado até o
contrato backend do Plano 009 existir. Nível 5 é rejeitado pela ADR-005.

## ADRs obrigatórias

### ADR-001 — Preservar a arquitetura frontend do Onyx

- **Status:** proposta obrigatória.
- **Decisão:** manter `web/src/app`, layouts, providers, SWR, stores e rotas
  existentes. A entrada autenticada continua em `/app`.
- **Motivo:** `layout.tsx`, `app/layout.tsx`, `AppChrome.tsx` e `AppSidebar.tsx`
  já resolvem auth, tema, sessão, navegação e painéis.
- **Consequência:** TON adapta composição e linguagem; não cria casca paralela.

### ADR-002 — Preservar o design system Onyx

- **Status:** proposta obrigatória.
- **Decisão:** usar Opal e `refresh-components`, tokens semânticos e layouts
  existentes. Usar `web/lib/opal/src/components/index.ts` e
  `web/lib/opal/src/layouts/index.ts` como inventário.
- **Motivo:** tokens claros/escuros e padrões mobile já existem em
  `web/lib/shared/tokens/` e no Tailwind preset.
- **Consequência:** dívida legada fica localizada; uma rota TON nova não usa
  controles ou cores fora do padrão.

### ADR-003 — Não migrar para shadcn

- **Status:** proposta obrigatória.
- **Decisão:** não introduzir shadcn nem migrar componentes para shadcn.
- **Motivo:** não há necessidade funcional e a migração aumentaria diferença,
  dependências e risco visual.
- **Consequência:** lacunas visuais são resolvidas com Opal ou refresh.

### ADR-004 — Adaptação de diferença mínima

- **Status:** proposta obrigatória.
- **Decisão:** alterar somente cópia, tokens, composição e telas necessárias ao
  fluxo TON. Preservar contratos e comportamentos úteis.
- **Motivo:** reduz regressão e mantém compatibilidade com instalações Onyx.
- **Consequência:** algumas telas legadas permanecem fora do escopo.

### ADR-005 — Não reescrever o frontend

- **Status:** proposta obrigatória.
- **Decisão:** não reescrever Next.js, providers, chat, sidebar, personas ou
  projetos.
- **Motivo:** a base cobre os fluxos principais e a reescrita seria nível 5.
- **Consequência:** dívida anterior deve ser registrada, não escondida em uma
  reforma ampla.

### ADR-006 — Nenhuma modificação backend por objetivo frontend

- **Status:** proposta obrigatória.
- **Decisão:** esta adaptação não edita `backend/`. Lacunas de ocorrências,
  relatórios e integrações viram contratos e itens bloqueáveis.
- **Motivo:** o pedido é de descoberta e planejamento frontend.
- **Consequência:** não criar tela que dependa de API apenas imaginada.

### ADR-007 — Português como idioma aceito

- **Status:** proposta obrigatória.
- **Decisão:** português pode ser o único idioma aceito para o primeiro corte.
  A interface continua usando `next-intl`.
- **Motivo:** a especificação TON aceita português e a infraestrutura já existe.
- **Consequência:** não remover chaves ou bridge; adicionar PT de forma segura.

### ADR-008 — Simplificar i18n somente depois

- **Status:** proposta obrigatória.
- **Decisão:** manter locale, mensagens e `OpalStringsBridge` durante a
  adaptação. Avaliar simplificação em decisão posterior.
- **Motivo:** `web/src/app/layout.tsx` e `web/src/i18n/request.ts` fazem parte da
  casca e remoção cria churn.
- **Consequência:** strings TON precisam de chaves no inglês e no português.

### ADR-009 — Logo final ainda não existe

- **Status:** proposta obrigatória.
- **Decisão:** não inventar ou commitar logo Vale Norte. Usar nome, fallback e
  tokens; preservar logo configurável do enterprise settings.
- **Motivo:** `useSettings` já suporta `logoUrl`, mas o asset final não foi
  fornecido.
- **Consequência:** a decisão visual do símbolo fica aberta sem bloquear layout.

### ADR-010 — Mobile é requisito

- **Status:** proposta obrigatória.
- **Decisão:** toda tela TON deve funcionar em breakpoints `sm` 724px e `md`
  912px, com drawer/modal quando necessário.
- **Motivo:** `AppChrome`, `AdminChrome` e `DocumentsSidebar` já suportam esse
  padrão e o produto exige uso mobile.
- **Consequência:** cada item inclui QA mobile e teclado.

### ADR-011 — Tema escuro é requisito

- **Status:** proposta obrigatória.
- **Decisão:** suportar `.dark` por tokens semânticos; não usar `dark:` nem
  cores built-in do Tailwind.
- **Motivo:** `next-themes` e os arquivos semânticos claro/escuro já estão
  disponíveis.
- **Consequência:** cada estado precisa ser verificado em claro e escuro.

### ADR-012 — Sem requisito offline

- **Status:** proposta obrigatória.
- **Decisão:** não criar cache offline, fila local ou sincronização offline.
- **Motivo:** não foi pedido e não há infraestrutura offline no frontend.
- **Consequência:** tratar falha de rede com erro e retry, sem prometer acesso
  sem conexão.

## Backlog executável

| ID | TITLE | OBJECTIVE | WHY NEEDED | CURRENT COMPONENTS/FILES INVOLVED | CHANGE LEVEL (0–5) | DEPENDENCIES | BACKEND DEPENDENCY | ACCEPTANCE CRITERIA | RISKS | TEST/QA REQUIREMENTS |
|---|---|---|---|---|---:|---|---|---|---|---|
| TON-FE-000 | Baseline e inventário congelado | Registrar rotas, componentes, tokens, flags e contratos antes de alterar UI. | Evita perda de comportamento e cria referência de comparação. | `web/src/app`, `web/src/sections/sidebar/AppSidebar.tsx`, `web/src/lib/swr-keys.ts`, `web/lib/opal/src`, docs deste diretório. | 0 | Nenhuma | Nenhuma; somente leitura. | Inventário revisado; `git diff` contém apenas docs; rotas críticas têm dono identificado. | Inventário incompleto ou confundido com escopo. | Rodar `cd web && bun run types:check` e checks de lint/formatação sem editar código; guardar evidência. |
| TON-FE-001 | Nome e copy TON | Aplicar linguagem TON por catálogos e configuração, sem logo final ou mudança de tema. | Dá identidade com diferença mínima e preserva o tema atual. | `web/src/app/layout.tsx`, `web/src/i18n/messages/en.json`, `pt.json`, `web/src/lib/constants.ts`. | 0 | TON-FE-000; ADR-001, 004, 007, 008, 009 | Usar `/api/settings` e `/api/enterprise-settings` existentes; nenhum endpoint novo. | Textos visíveis têm chave i18n; fallback sem logo funciona; auth e URLs não mudam. | Copy hard-coded ou link sem destino aprovado. | `bun run types:check`, `bun run lint`, `bun run format:check`; RTL para copy e fallback. |
| TON-FE-002 | Mapeamento de tema Vale Norte e responsividade | Mapear a paleta por tokens e validar as superfícies TON em mobile e dark. | Mobile e dark são requisitos explícitos. | `web/tailwind-themes/tailwind.config.js`, `web/lib/shared/tokens/*.json`, `AppChrome.tsx`, `AdminChrome.tsx`, `DocumentsSidebar.tsx`. | 1 | TON-FE-001; ADR-002, 010, 011 | Nenhuma nova API. | Pares de contraste passam em light/dark; breakpoints 724/912px não cortam ações; sem `dark:` ou cor built-in nas telas TON. | Overflow, foco perdido e contraste insuficiente. | RTL de foco/teclado; Playwright POM em viewport mobile e desktop; `bun run playwright <TEST_NAME>`; revisão visual. |
| TON-FE-003 | Matriz de superfícies ocultas | Esconder Billing, Craft, tier, SaaS e integrações não necessárias da navegação normal. | Link oculto sozinho não protege rota direta; flags já têm múltiplas dimensões. | `web/src/lib/admin-routes.ts`, `web/src/sections/sidebar/AdminSidebar.tsx`, `web/src/layouts/chromes/AdminChrome.tsx`, `web/src/app/admin/*`, `/ee/*`, `/craft/*`. | 2 | TON-FE-000; ADR-001, 004, 006 | Reusar `/api/settings`, capacidades e gates atuais; sem backend novo nesta fase. | Usuário comum não vê nem acessa superfícies fora da matriz; admin autorizado mantém acesso. | Quebrar admin, ignorar URL direta ou ocultar recurso necessário. | Testes de rota com usuário normal/admin; Playwright POM para gate; `bun run types:check`; testar flags ligadas/desligadas. |
| TON-FE-004 | Navegação TON na casca existente | Organizar Central, especialistas, ocorrências, relatórios e fontes na sidebar. | IA clara sem criar uma segunda navegação ou store. | `web/src/sections/sidebar/AppSidebar.tsx`, `web/src/app/app/layout.tsx`, `web/src/app/app/page.tsx`, `web/src/layouts/chromes/AppChrome.tsx`. | 2 | TON-FE-001, 003; ADR-001, 004, 005 | Central/especialistas usam personas existentes; ocorrências/relatórios só após contratos. | Central abre `/app`; especialistas abre `/app/agents`; links futuros não aparecem sem capacidade; DnD/pins/chats continuam. | Sidebar sobrecarregada, rota vazia ou estado duplicado. | RTL para navegação/pins; Playwright POM desktop/mobile; teste de teclado e retorno por browser back. |
| TON-FE-005 | Central e especialistas sobre personas | Mapear Central ao default e especialistas a personas existentes. | Evita criar sistema paralelo e preserva RBAC, fontes e ferramentas. | `web/src/lib/agents/types.ts`, `hooks.ts`, `svc.ts`, `AgentButton.tsx`, `AgentCard.tsx`, `AgentViewer.tsx`, `AgentsNavigationPage.tsx`, `/app/agents/*`. | 2 | TON-FE-004; ADR-001, 004, 005 | `/api/persona`, `/api/persona/:id`, share/pin existentes; nenhuma API nova nesta fase. | Seleção mantém `agentId`; fallback respeita precedência; ações seguem permissão; estados vazio/erro existem. | Id `0` pode não ser Central customizada; PII e share indevidos. | Testes unitários de `useActiveAgent`; RTL de card/viewer; Playwright selecionar especialista e voltar à Central. |
| TON-FE-006 | Semântica de escopo de arquivo | Exibir escopo e retenção de arquivos no composer, projeto e especialista. | O frontend tem contexto de mensagem, incognito, projeto e recentes, mas o contrato não declara a retenção de cada um. | `web/src/lib/projects/types.ts`, `providers.tsx`, `svc.ts`, `ProjectContextPanel.tsx`, `AppInputBar.tsx`, `FileCard.tsx`, `DocumentsSidebar.tsx`. | 2 | TON-FE-004, 005; ADR-004, 006, 012 | Reusar `/api/user/projects/*`, `/api/user/files/recent`, status e `/api/chat/file/:id`; contrato explícito de retenção é pré-requisito. | Após contrato aprovado, o escopo aparece sem inferir pelo `temp_id`; status e falha aparecem; remover respeita associação; citações mantêm ACL. | Vazamento, retenção errada ou rollback otimista quebrado. | RTL de upload/erro/incognito; teste integração via frontend após contrato; Playwright upload, projeto e modal mobile. |
| TON-FE-007 | Fontes e conexões | Definir tela ou seção de fontes sem duplicar conectores, projetos e citações. | Não há inventário agregado; conectores atuais são declarativos/admin. | `web/src/lib/connectors/connectors.tsx`, `web/src/app/app/settings/connectors/page.tsx`, `DocumentsSidebar.tsx`, `ProjectContextPanel.tsx`, `ConnectionProviderIcon.tsx`. | 3 | TON-FE-006; decisão de produto sobre `/app/sources` | Reusar connector status/OAuth/document sets; agregação nova requer contrato aprovado; sem backend novo nesta fase. | Decisão sobre `/app/sources` fica registrada; fontes mostram origem e ACL; credenciais nunca aparecem; estados loading/error/empty existem. | Agregação duplicada, fonte SaaS ou credencial exibida para usuário errado. | Testar ACL, loading/error/empty e ausência de segredo; visual claro/escuro e mobile; `bun run types:check`. |
| TON-FE-008 | Contrato e UI de ocorrências | Definir contrato backend e, após aprovação, lista/detalhe de achados. | Não existe entidade de ocorrência; não usar notification ou KG como substituto. | Futuras `/app/occurrences*`; Opal `Table`, `Tag`, `Content`, `Modal`; referências `QueryHistoryTable.tsx`, `DocumentsSidebar.tsx`. | 3 | TON-FE-004, 006, 007; ADR-006 | Bloqueado até schema, ACL, paginação, transições, evidências, histórico e auditoria; nenhuma implementação backend nesta fase. | O contrato aprovado lista schema, ACL e transições; antes dele, não existe tela produtiva; depois, testes mostram lista filtrável, detalhe, estados e ações respeitando ACL e mobile. | Confluir notificação com caso; PII; API inventada. | Testar contrato quando existir; RTL de tabela/filtros; Playwright POM de lista/detalhe/permissão; validar ausência de tela enquanto bloqueado. |
| TON-FE-009 | Contrato e UI de relatórios | Separar relatório TON de usage export/query history e oferecer geração/download autorizado. | APIs atuais são admin/EE e podem retornar PII. | Futuras `/app/reports*`; `UsageReports.tsx`; `QueryHistoryTable.tsx`; Opal `Table`, `Tag`, `Pagination`, `InputDatePicker`. | 3 | TON-FE-008; ADR-006, 010, 011 | Bloqueado até lista, criação assíncrona, detalhe, download temporário, retenção e ACL; nenhuma implementação backend nesta fase. | O contrato aprovado define lista, geração, detalhe, download e retenção; depois, testes cobrem estados empty/queued/generating/ready/failed/expired, polling e permissão. | Expor relatório admin, URL permanente ou dados fora da ACL. | Testes de contrato, polling/timeout e download; integração via frontend; Playwright mobile/dark; verificar auditoria. |
| TON-FE-010 | Administração e status do canal Telegram | Criar no futuro a superfície administrativa do primeiro canal externo TON. | Telegram está confirmado, mas o frontend não pode inventar transporte, credenciais, identidade, entrega ou ACL. | Rotas admin de bots/canais, por exemplo `web/src/app/admin/bots/[bot-id]/channels/*`; integrações em `web/src/lib/*`. | 3 | TON-FE-003; Backend 009 | BLOQUEADO até existir o contrato backend do canal. O backend mantém credenciais, autorização, webhook/polling, entrega e auditoria. | Após desbloqueio, admin autorizado consulta configuração e status. Nenhum link ou UI aparece antes do contrato. | Segredo exposto, autorização somente visual ou estado de entrega incorreto. | Testes de contrato e permissão; RTL de estados; Playwright admin após autorização do plano. |
| TON-FE-011 | QA integrado e aceite | Validar cópia, acessibilidade, permissões, mobile, dark e regressão Onyx. | A adaptação cruza providers, SWR, auth, chat e layouts. | Arquivos tocados pelos itens; `web/tests/e2e`, Jest/RTL e utilitários visuais. | 0 | TON-FE-001 a 010 conforme escopo; ADRs | Executar contra APIs existentes no frontend; contratos novos precisam ambiente de teste. | Type coverage e lint passam; fluxos principais Onyx e TON passam; nenhuma alteração backend não autorizada. | Teste superficial, flake e regressão em instalação CE/EE. | `cd web && bun run types:check`; `bun run lint`; `bun run format:check`; `bun run test -- ...`; `bun run playwright <TEST_NAME>`; revisão visual. |

## Resultado de TON-FE-000

TON-FE-000 foi concluído em `6e4b2a066459e3bd7217341b6f2fa5af4eb4bc4f`.
O inventário confirmou rotas, donos de componentes, Opal, refresh components,
tokens, flags, contratos frontend e dependências backend.

O estado inicial não tinha alteração rastreada. Os 18 documentos desta pasta
já estavam sem rastreamento. Não havia código fonte de experimento TON. O cache
ignorado do Jest contém 22 arquivos antigos com nomes TON. Eles não fazem parte
do código fonte nem do runtime.

Checks executados:

- `bun run types:check`: passou, com cobertura de tipos de 98,81%.
- `bun run lint`: passou com avisos preexistentes.
- `bun run format:check`: falhou no baseline em 1.413 arquivos existentes.
- Check de formato do novo contrato: passou.
- Contrato Jest TON: 3 testes passaram.

Nenhuma UI, rota, copy, navegação, cor, layout, tema ou comportamento mudou.
TON-FE-001 e itens posteriores não começaram.

## Resultado de TON-FE-002

**Status: DONE.**

TON-FE-002 foi executado sobre `a73cfc49115a162f0bced671e91731bfd4fa0f31`.
Esse commit contém TON-FE-001.
O commit pai contém as mudanças web do Plano 002.

A mudança ficou no nível 1.
Ela alterou somente tokens, testes e documentos frontend.
Nenhum layout, breakpoint ou componente de produção mudou.

Tokens alterados:

- novas escalas `vale-norte-green-*`, `vale-norte-gold-*` e
  `vale-norte-neutral-*`;
- aliases `tint-*` para superfícies neutras verdes;
- `theme-primary-*` para a identidade institucional;
- `action-selection-*` e `action-text-link-05` para interação;
- `theme-amber-*` e `highlight-accent` para dourado contido;
- `background-tint-00` escuro para uma superfície verde quase preta.

Os tokens de status não mudaram.
Os tokens de radius, espaçamento, tipografia e sombra não mudaram.

Verificação executada:

- build dos tokens compartilhados: passou;
- build Opal: passou com avisos de chunks circulares existentes;
- teste de contrato do tema: 3 testes passaram;
- testes TON, privacidade e fallback: 12 testes passaram;
- `bun run types:check`: passou com cobertura de 98,81%;
- `bun run lint`: passou com avisos existentes;
- Playwright POM: 6 casos passaram;
- revisão visual: light e dark em mobile e desktop passaram.

Playwright usou larguras de 375, 768 e 1280 pixels.
O teste abriu chat, sidebar mobile, agents, settings e popover.
Ele verificou foco, variáveis CSS e overflow horizontal.

O setup Playwright padrão falhou antes dos testes.
O endpoint de grupos exigiu o plano Business e retornou 402.
Uma configuração temporária removeu somente esse setup.
Ela não ficou no repositório.

O ambiente também registrou um aviso preexistente de controle do popover.
A conta de teste recebeu 403 em chamadas administrativas da tela agents.
Esses eventos não alteraram o resultado visual validado.

O logo final continua bloqueado por falta do ativo oficial.
Sombras, vignette e fundos configuráveis ficam para refinamento futuro.
TON-FE-003 e itens posteriores não começaram.
Nenhum arquivo em `backend/` mudou.

### Refinamento de contraste no tema escuro

**Status: DONE.** Nível 1. Somente tokens, testes e este documento mudaram.

O tema escuro tinha camadas semânticas muito próximas em luminância.
O conteúdo normal parecia desabilitado.
O refinamento separou as camadas e manteve a paleta, o Opal e a arquitetura.

Escada de superfícies escuras, do mais profundo ao mais claro:

| Token | Papel | Antes | Depois |
|---|---|---|---|
| `background-neutral-00` | campo do composer e dos inputs | `#000000` | `#0b1410` |
| `background-tint-00` | card, superfície recolhida, item selecionado | `#08110d` | `#18231d` |
| `background-tint-01` | fundo da aplicação | `#131c17` | `#27332c` |
| `background-tint-02` | sidebar e hover geral | `#1d2822` | `#344139` |
| `background-tint-03` | superfície elevada e hover de navegação | `#29352e` | `#414f47` |
| `background-tint-04` | anel de foco interno dos inputs | `#35423b` | `#56655d` |

Cada passo agora tem ao menos 1,15 de contraste.
Nenhuma superfície usa preto puro.
`background-neutral-01` a `-04` seguem a mesma escala verde-neutra.

Texto escuro: `text-04` foi para 90%, `text-03` para 70% e `text-02` para 55%.
`text-05` e `text-01` não mudaram, então desabilitado continua o mais fraco.

Bordas escuras trocaram cinza por verde-neutro.
`border-01` subiu de 1,04 para 1,60 contra o fundo da aplicação.
`border-04` e `border-05` mantêm o foco acima de 3:1.

Estados: `action-selection-05` virou `vale-norte-green-50` e `-04` virou
`vale-norte-green-45`. `action-selection-01` virou `vale-norte-green-92`.
A linha selecionada passou de 1,13 para 1,24 contra o fundo.
O hover sobre a linha selecionada passou de 1,01 para 1,52.

`background-code-01` perdeu o hex fixo cinza e usa `vale-norte-neutral-97`.

Novos primitivos: `vale-norte-neutral-99/97/93/88/83/82/76/74`,
`vale-norte-green-92`, `vale-norte-green-45` e os aliases `tint-97/93/88/83/76`.
O tema claro não referencia nenhum deles.

Verificação executada:

- build dos tokens compartilhados: passou;
- build Opal: passou com os avisos de chunks circulares existentes;
- contrato do tema e hierarquia escura: 10 testes passaram;
- `bun run types:check`: passou com cobertura de 98,81%;
- `bun run lint`: passou com avisos existentes;
- `oxfmt` nos arquivos TS alterados: passou;
- Playwright em 375, 768 e 1280 pixels no escuro: 3 casos passaram.

O Playwright validou chat, composer, sidebar, cards, agents, settings e popover.
Ele mediu a escada de superfícies no DOM real, não apenas nas variáveis.

O setup padrão do Playwright continua falhando antes dos testes.
O endpoint de grupos exige o plano Business e retorna 402.
Uma configuração temporária removeu somente esse setup e não ficou no repositório.

O `web_server` local roda uma imagem pronta sem montagem do repositório.
Ele não serve o CSS reconstruído.
A validação injetou o `tokens.css` gerado na aplicação em execução.

O tema claro não mudou.
Os valores claros resolvidos continuam idênticos e estão fixados em teste.
Nenhum componente, layout, tipografia, espaçamento ou raio mudou.
Nenhum arquivo em `backend/` mudou.

## Resultado de TON-FE-003

**Status: DONE.**

TON-FE-003 foi executado sobre `d49ea04e09eb726ad7cea330c038dbd1e3685546`.
Esse commit contém TON-FE-001, TON-FE-002 e o refinamento do tema escuro.
As mudanças web do Plano 002 estão em `ea903d2965`.

A mudança ficou entre os níveis 0 e 2.
Ela alterou copy, catálogos, visibilidade de navegação e uma composição.
Nenhum token, breakpoint, layout de chat ou arquitetura de navegação mudou.
Nenhum arquivo em `backend/` mudou.
A matriz de disposição completa está em `saas-surface-audit.md`.

### Política de superfície

O novo módulo `web/src/lib/ton/product-surface.ts` centraliza a decisão.
São quatro constantes, todas `false`: `SHOW_UPSTREAM_ATTRIBUTION`,
`SHOW_UPSTREAM_LINKS`, `SHOW_COMMERCE_SURFACES` e `SHOW_BUILDER_PRODUCT_ENTRY`.

São constantes e não variáveis de ambiente.
Um `process.env` sem prefixo `NEXT_PUBLIC_` resolve para `undefined` no bundle
do cliente, o que faria a política divergir entre servidor e cliente.

### Superfícies removidas ou ocultas

- atribuição "Powered by Onyx" sob o logo da sidebar;
- rodapé `Onyx <versão> - Open Source AI Platform`;
- link Help & FAQ e link de changelog para `docs.onyx.app`;
- apêndice de suporte do toast com `discord.gg`;
- wordmark upstream nas páginas de erro;
- link de documentação upstream no erro de configuração;
- link da comunidade Discord no erro e no acesso restrito;
- banner de lembrete de pagamento e fim de trial;
- item de navegação `Upgrade Plan`;
- entrada `Plans & Billing` na sidebar admin;
- botão `Upgrade Plan` nos tokens de acesso;
- entrada Craft e sua intro na sidebar do app.

### Superfícies renomeadas ou com copy trocada

- rodapé: `product.footer.text` com `appName` e `settings.version`;
- versão no menu da conta: `product.version.label`;
- subtítulo do login: tagline TON em vez de "open source AI platform";
- tooltip de tier: `capabilityUnavailable`, sem plano nem link de billing;
- tokens de acesso: `apiKeys.unavailable.description`;
- onboarding: `nameStep.title`, `llmStep.description` e
  `finalStep.webSearch.description` sem referência a Onyx ou self-hosted;
- páginas de erro: descrições sem nome de produto upstream.

O logo final continua bloqueado por falta do ativo oficial.
As páginas de erro passaram a usar o `Logo` configurável já existente.

### Onboarding depois da mudança

O onboarding não foi redesenhado e nenhum passo foi removido.

A auditoria confirmou que `OnboardingFlow` já separa os dois casos.
O ramo `isAdmin` hospeda Welcome, Name, LlmSetup e Complete.
O usuário comum só alcança `NonAdminStep`, que pede o nome de exibição.

Ou seja, "Connect your LLM models" nunca aparecia para o usuário comum.
O requisito de não guiar o usuário comum por setup de plataforma já estava
satisfeito pela estrutura. Só a copy foi neutralizada.

`useShowOnboarding` continua decidindo por provider configurado, sessões de
chat e a chave `onyx:onboardingCompleted:<userId>`. Nada disso mudou.

### Billing, tier e Craft

Billing saiu da apresentação, não do código.
A entrada de rota `BILLING` continua em `admin-routes.ts`, com a mesma
permissão, então `matchAdminRoute` e o deep link do operador seguem válidos.
`useBillingInformation`, `useLicense` e `useCloudSubscription` não mudaram.

O mecanismo de tier foi preservado por necessidade.
`requiredTier`, `tierAtLeast` e `useTierAtLeast` decidem capacidade em runtime
em `SettingsPage`, `AgentEditorPage`, `ChatPreferencesPage`, `GroupsPage`,
`SSOProvidersPage` e `AgentRowActions`. Só o texto de upsell mudou.

Os badges `Business Plan` e `Enterprise Plan` em `lib/tier-badge.ts` foram
preservados. Eles são admin-only e explicam por que um controle está
desabilitado. Renomeá-los depende do vocabulário do Plano 008.

Craft saiu da navegação do usuário comum.
As rotas `/craft/*`, as páginas admin de Craft e o flag `onyx_craft_available`
não mudaram. Nenhuma execução em segundo plano foi tocada.

### Verificação executada

- `bun run types:check`: passou, cobertura de tipos 98,81%;
- `bun run lint`: 905 avisos e 0 erros, idêntico ao baseline medido com
  `git stash`; nenhum aviso novo;
- `bun run build`: compilou e passou o TypeScript de produção;
- `oxfmt --check` nos dois arquivos novos: passou;
- `oxfmt` nos arquivos alterados: nenhuma diferença de conteúdo — as falhas de
  `format:check` no repositório são de fim de linha CRLF no checkout Windows,
  preexistentes desde TON-FE-000;
- Jest: 70 testes passaram em 10 suítes — `ton-product-surface` (12 novos),
  `ton-privacy`, `lib/app`, `lib/settings`, `i18n` incluindo o teste de
  paridade de catálogo, `onboardingReducer` e `ton-theme`.

### Contrato de superfície testado

`web/src/ton/ton-product-surface.test.tsx` cobre os dois papéis.

Usuário comum: nome do produto sem atribuição upstream; rodapé sem
`APP_SLOGAN` e sem `onyx.app`; copy de rodapé, versão e login sem menção a
open source; onboarding de provider restrito ao ramo admin; nenhum link
upstream no menu da conta nem nas páginas de erro; `buildItems` sem
`upgradePlan` e sem `plansAndBilling` nos estados pago e não pago;
`BILLING.visibleWhen` falso mesmo com assinatura ativa; sem entrada de builder.

Administrador: `buildItems` mantém language models, users, groups, agents,
connectors, add connector, document sets, index settings, security, SSO, MCP e
OpenAPI actions, chat preferences e web search; a rota `BILLING` continua
existindo com `FULL_ADMIN_PANEL_ACCESS`; Craft admin continua visível quando
disponível; itens desabilitados por tier continuam desabilitados com
`requiredTier` preservado.

`web/tests/e2e/ton/product-surface.spec.ts` e
`web/tests/e2e/pages/TonProductSurfacePage.ts` cobrem o mesmo contrato em
claro e escuro, em 375 e 1280 pixels, e verificam que o admin ainda alcança
language models, users, agents, security, conectores e document sets.

### Validação visual e limites do ambiente

Nenhum serviço Onyx estava em execução nesta rodada.
`http://localhost:3000` não respondeu e `backend/log` não existe.
Os contêineres presentes são de outros projetos e estão parados.

Portanto os testes Playwright de FE-003 não foram executados ao vivo.
Eles estão escritos, tipados e sem aviso de lint, mas não têm evidência de
execução. Isso é um bloqueio de ambiente, não um resultado.

A ausência de regressão visual foi verificada de forma estática:
`git diff` em `web/lib/shared/tokens`, `web/tailwind-themes` e
`web/lib/opal/src` está vazio; nenhuma linha adicionada usa `dark:` nem cor
built-in do Tailwind. O sistema visual aprovado em TON-FE-002 não foi tocado.

As duas mudanças com efeito de layout são pequenas e locais: o `Logo` deixa de
renderizar uma linha de texto secundária, e `ErrorPageLayout` troca o wordmark
upstream pelo `Logo` configurável.

### Teste upstream reconciliado

`appearance_theme_settings.spec.ts` afirmava que o toggle "Hide Onyx Branding"
removia a tagline. Com a atribuição fora do produto, a tagline nunca renderiza.
O teste passou a afirmar a ausência nos dois estados do toggle, e o helper
`expectPoweredByOnyxVisible` foi removido. O toggle e a settings continuam
funcionando.

### Avisos

1. Os testes Playwright de FE-003 precisam ser executados quando o ambiente
   subir. O setup padrão do Playwright ainda falha por causa do endpoint de
   grupos que exige plano Business e retorna 402, conforme registrado em
   TON-FE-002.
2. `web/src/components/errorPages/ErrorPageLayout.tsx` deixou de importar do
   legado `web/src/components/icons/icons.tsx`, o que aproxima o arquivo do
   padrão de `web/AGENTS.md`.
3. As dependências do Backend Plano 008 estão registradas em
   `saas-surface-audit.md`. Nenhuma delas foi implementada aqui.

TON-FE-004 foi executado depois. Itens posteriores não começaram.

## Resultado de TON-FE-004

**Status: DONE.** O registro completo está em
[`004-ton-navigation.md`](./004-ton-navigation.md).

Executado em worktree isolado `../ton-frontend-004`, branch `ton/frontend-004`,
sobre `1a9b40476abbac0594c40eb264ed3e97e3a14bb3`. Esse baseline contém os Planos
backend 001, 002, 007, 008a, 003a e 003b (revisão `faee7eaa921e`).

A mudança ficou no nível 2. Ela alterou rótulos, agrupamento, ordenação, um
separador e dois landmarks. Nenhum token, breakpoint, store, rota ou mecânica de
sidebar mudou. Nenhum arquivo em `backend/` mudou.

### Arquitetura de informação final

```text
Header (fixo)   Central → /app · Especialistas → /app/agents · Pesquisar chats
Body (scroll)   Especialistas fixados · Projetos · ─divider─ · Conversas
Footer          Painel de administração · conta
```

Central é a entrada principal existente com terminologia TON. Especialistas
deixou de ser o transbordo da lista de fixados e passou a ser destino próprio,
fixado ao lado de Central fora da área com scroll. Conversas ganhou um `Divider`
e um landmark `nav` próprio, separando histórico de navegação de produto.

`appSidebar.moreAgents` e `appSidebar.exploreAgents` saíram;
`appSidebar.specialists`, `productNav.ariaLabel` e `historyNav.ariaLabel`
entraram. `newSession.label` e `chatSearch.newSession.label` valem `Central` nos
nove catálogos, como nome de produto, à maneira de `craft.label`.

### Decisão de projeto e conhecimento

**A** — expor a capacidade existente de projetos na navegação primária, com
terminologia TON. Projetos é a única capacidade de conhecimento com destino real
e UX madura hoje. Nenhum agrupamento "Conhecimento" foi criado, porque arquivos e
document sets não têm rota de usuário própria e Fontes pertence a TON-FE-007.

### Adiado, sem link morto

Ocorrências (TON-FE-008), Relatórios (TON-FE-009), Fontes (TON-FE-007),
especialistas concretos (TON-FE-005) e estado de runtime do especialista. Sem
rota, sem item desabilitado, sem "em breve". O Plano backend 003c em execução
concorrente não autoriza expor Ocorrências, e FE-004 não depende dele.

### Follow-up do Plano 008a

`ADMIN_ROUTES.GROUPS.requiredTier` passou de `Tier.BUSINESS` para `null`, a
única linha da tabela do Plano 008a que é navegação. `MANAGE_USER_GROUPS`
continua decidindo acesso. `API_KEYS` e `SCIM` mantêm seus tiers. A afirmação de
tier em `ton-product-surface.test.tsx` foi reapontada para `API_KEYS`, como o
Plano 008a prescreve. `useCanManageGroups` e os seletores de grupo continuam
gated: são affordances de página, não navegação, e ficam para TON-CAP-002.

### Verificação executada

- `bun run types:check`: passou, cobertura de tipos 98,81%, idêntica ao baseline;
- `bun run lint`: 905 avisos e 0 erros, idêntico ao baseline de FE-003;
- `oxfmt --check` nos sete arquivos TS alterados e novos: limpo na forma LF;
- `bun run build`: compilou; a lista de rotas não contém ocorrências,
  relatórios nem fontes;
- Jest `src/ton/`: 3 suítes, 44 testes, todos passaram, sendo 28 novos em
  `ton-navigation.test.tsx`, que renderiza a sidebar de verdade;
- Jest completo: 9 suítes falham, as mesmas 9 que falham no baseline medido com
  `git stash`. Nenhuma toca sidebar, navegação, rota ou i18n.

**PLAYWRIGHT DEFERRED — SHARED RUNTIME CONFLICT.**
`web/tests/e2e/ton/navigation.spec.ts` e `TonNavigationPage.ts` estão escritos,
tipados e formatados, mas não rodaram ao vivo. O contêiner `onyx-web_server-1`
roda a imagem pronta `onyxdotapp/onyx-web-server:latest` sem bind mount e foi
criado antes desta mudança, então serve o código anterior a FE-004. Reconstruí-lo
alteraria estado Docker compartilhado, e um segundo frontend faria o global-setup
registrar usuários no banco compartilhado com o Plano 003c. Rodar
`bun run playwright navigation` quando existir ambiente que sirva este branch.

### Handoff para TON-VIS-000

`004-ton-navigation.md` registra a hierarquia final, os donos de componente da
casca, a implementação de estado ativo, os breakpoints e sete itens de dívida
visual — entre eles `SvgOnyxOctagon` como glifo de agente em oito superfícies e
os rótulos `"Open Sidebar"`/`"Close Sidebar"` sem i18n em Opal. Nenhum deles foi
resolvido aqui.

TON-FE-005 e os itens `TON-VIS-*` não começaram.

## Sequência recomendada

```text
TON-FE-000
    ├── TON-FE-001 ── TON-FE-002
    ├── TON-FE-003 ── TON-FE-004 ── TON-FE-005 ── TON-FE-006
    │                                         └── TON-FE-007
    │                                         └── TON-FE-008 ── TON-FE-009
    └── TON-FE-010 (bloqueado pelo Backend 009)

TON-FE-001..010 ── TON-FE-011
```

Os itens 008 e 009 são explicitamente bloqueáveis por backend. Isso não é uma
falha do plano: é a fronteira necessária para não inventar entidades ou
endpoints.
