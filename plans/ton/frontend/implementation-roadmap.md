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
