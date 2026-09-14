# TON — análise de lacunas do frontend

## Escopo e método

Esta análise é somente de descoberta. O código atual permanece intacto. A leitura
cobriu `web/AGENTS.md`, a seção **Engineering Best Practices** de
`CONTRIBUTING.md`, a especificação TON recebida e os contratos usados pelo
frontend. O backend foi lido apenas para confirmar endpoints, permissões e
ausências.

O plano usa o produto Onyx como base e a taxonomia canônica do README: nível 0,
somente texto, copy ou configuração; nível 1, ajuste de tema ou token; nível 2,
pequena composição de componentes ou variante; nível 3, nova página TON usando
o design system existente; nível 4, mudança estrutural de frontend; nível 5,
reescrita do design system ou da arquitetura. O alvo TON deve preferir níveis
0–3 e não requer nível 5.

## Evidência de base

- A composição autenticada já passa por `web/src/app/app/layout.tsx`,
  `web/src/layouts/chromes/AppChrome.tsx` e `web/src/sections/sidebar/AppSidebar.tsx`.
- Os agentes TON podem usar o contrato de personas existente em
  `web/src/lib/agents/types.ts`, `web/src/lib/agents/hooks.ts` e
  `web/src/lib/agents/svc.ts`.
- Projetos e arquivos persistentes já têm estados, upload otimista e modo
  incógnito em `web/src/lib/projects/types.ts`,
  `web/src/lib/projects/providers.tsx` e `web/src/lib/projects/svc.ts`.
- A base visual Opal, com tokens claros e escuros, está em
  `web/lib/opal/src/components/index.ts`, `web/lib/opal/src/layouts/index.ts` e
  `web/lib/shared/tokens/*.json`.
- Histórico e relatório de uso são administrativos ou EE em
  `web/src/app/ee/admin/performance/query-history/QueryHistoryTable.tsx` e
  `web/src/views/admin/WorkspaceAnalyticsPage/UsageReports.tsx`.
- Não foi encontrado modelo ou endpoint de ocorrência, achado ou caso TON.
  Os campos de “occurrence” do grafo de conhecimento em
  `backend/onyx/db/models.py` são contadores de extração e não devem ser
  reutilizados como domínio TON.

## Tabela obrigatória de lacunas

| EXISTING CAPABILITY | TON REQUIREMENT | CURRENT FIT | MINIMUM NECESSARY CHANGE | COMPONENTS/ROUTES AFFECTED | BACKEND DEPENDENCY | RISK | ESTIMATED EFFORT |
|---|---|---|---|---|---|---|---|
| Chat principal com modo de busca e conversa | TON Central como entrada única | Parcial: `/app` já é o destino e `AppPage` já compõe chat, fontes e arquivos | Definir copy TON e agente padrão por configuração; manter estados e ordem atuais até haver evidência de gap | `web/src/app/app/page.tsx`, `web/src/views/AppPage.tsx`, `web/src/layouts/chromes/AppChrome.tsx` | `/api/me`, `/api/settings`, `/api/persona`, chat/search APIs | Mudança de copy pode quebrar expectativas de usuários Onyx | Nível 0 |
| Navegação lateral de agentes, projetos e chats | Central, especialistas, ocorrências, relatórios e fontes | Parcial: sidebar já tem agentes, projetos, chats e administração | Reordenar rótulos e adicionar destinos TON somente quando houver contrato | `web/src/sections/sidebar/AppSidebar.tsx`, `web/src/app/app/layout.tsx` | Persona e projetos existentes; APIs novas para ocorrências/relatórios TON | DnD, pins e histórico estão acoplados ao sidebar | Nível 2 |
| Personas/agentes com listagem, viewer, criação, edição e compartilhamento | Especialistas TON | Forte: uma persona já cobre nome, descrição, fontes, prompts, ferramentas e permissões | Mapear Central para agente padrão e especialistas para personas; ajustar textos e filtros | `web/src/views/AgentsNavigationPage.tsx`, `web/src/sections/agents/AgentCard.tsx`, `web/src/lib/agents/components/AgentViewer.tsx`, `/app/agents/*` | `/api/persona`, `/api/persona/:id`, `/api/persona/:id/share`, permissões persona | “Agent” no frontend e “persona” no backend pode induzir novo sistema | Nível 2 |
| Upload, arquivos recentes, projetos, instruções e modo incógnito | Separar conhecimento temporário de conhecimento persistente | Parcial forte: estados e APIs já existem; sem semântica TON explícita | Rotular escopos, preservar associação a projeto e indicar retenção/privacidade | `web/src/lib/projects/types.ts`, `web/src/lib/projects/providers.tsx`, `web/src/lib/projects/svc.ts`, `web/src/lib/projects/components/ProjectContextPanel.tsx`, `web/src/sections/input/AppInputBar.tsx` | `/api/user/projects/*`, `/api/user/files/recent`, `/api/chat/file/:id` | Arquivo pessoal pode aparecer em projeto ou agente; modo incógnito não deve entrar em recentes | Nível 2 |
| Citações e painel de documentos | Mostrar fontes usadas na resposta | Forte: painel desktop e modal mobile já existem | Trocar linguagem e metadados permitidos; preservar o identificador interno | `web/src/sections/document-sidebar/DocumentsSidebar.tsx`, `web/src/sections/document-sidebar/ChatDocumentDisplay.tsx` | Chat/document APIs e permissões de documento | Citações de arquivo anexado podem expor conteúdo fora do contexto se o escopo não for confirmado | Nível 0 |
| Configuração declarativa de conectores e status de indexação | Tela de fontes/conexões TON | Parcial: conectores, OAuth e status administrativo já existem | Expor somente resumo permitido ao usuário TON e manter gestão completa no admin | `web/src/lib/connectors/connectors.tsx`, `web/src/app/app/settings/connectors/page.tsx`, `web/src/app/admin/indexing/status/page.tsx` | Connector/CCPair, OAuth e indexação existentes | Mostrar conectores SaaS ou credenciais no lugar errado | Nível 3 |
| Histórico de consultas e relatórios de uso | Relatórios TON de atividade, achados e exportação | Fraco para domínio TON: o que existe é EE/admin e orientado a uso | Reusar tabela/paginação/download somente como padrão visual; definir contrato TON | `web/src/app/ee/admin/performance/query-history/QueryHistoryTable.tsx`, `web/src/views/admin/WorkspaceAnalyticsPage/UsageReports.tsx` | `/api/admin/chat-session-history`, `/api/admin/usage-report`; API TON nova provável | Gate EE/admin e PII impedem uso direto em área normal | Nível 3 |
| Notificações e severidade | Sinalizar pendências ou risco | Fraco: há dismiss de notificações, sem entidade de ocorrência | Definir estado de ocorrência separado de notificação transitória | `web/src/lib/notifications/api.ts`, futuras telas TON | Modelo/API de ocorrência com RBAC, histórico e auditoria | Misturar alerta operacional com caso de negócio | Nível 3 |
| Rotas administrativas e flags de produto | Ocultar billing, Craft, tier, SaaS e integrações não necessárias | Parcial: `ADMIN_ROUTES` já filtra por flags, tier e permissão | Criar matriz de visibilidade TON e testar usuário normal/admin em cada entrada | `web/src/lib/admin-routes.ts`, `web/src/sections/sidebar/AdminSidebar.tsx`, `web/src/layouts/chromes/AdminChrome.tsx` | `/api/settings`, capacidades administrativas e tiers | Link direto pode revelar tela mesmo se sidebar ocultar | Nível 2 |
| Tema, marca, logo e tipografia | Vale Norte sem logo final, claro/escuro e mobile | Forte para tema; parcial para marca: logo é configurável, mas asset TON não existe | Usar tokens sem criar logo; definir fallback e nome de marca | `web/src/app/layout.tsx`, `web/src/lib/settings/hooks.ts`, `web/lib/shared/tokens/*.json`, `web/src/app/globals.css` | `/api/settings`, `/api/enterprise-settings/logo` opcional | Upload/cache de logo e contraste podem divergir entre temas | Nível 1 |
| i18n com next-intl | Português como interface de aceite | Forte infra, divergente em legado | Adicionar copy TON aos catálogos; não remover infra agora | `web/src/app/layout.tsx`, `web/src/i18n/request.ts`, `web/src/i18n/messages/*.json`, `web/src/views/SettingsPage.tsx` | Nenhuma nova API | Strings hard-coded e remoção prematura geram churn e regressão | Nível 0 |
| Auth e onboarding | Entrada sem ruído de SaaS e orientação TON | Parcial: login e onboarding Opal existem, mas têm fluxo multi-tenant e setup de LLM | Ajustar copy e destino pós-login; manter SSO/senha e onboarding até decisão de produto | `web/src/app/auth/login/LoginPage.tsx`, `web/src/sections/onboarding/OnboardingFlow.tsx`, `web/src/app/app/layout.tsx` | `/api/me`, auth metadata, settings e `requireAuth` | Remover passos pode impedir primeiro usuário ou configuração LLM | Nível 0 |
| Responsividade e tema escuro | Uso em mobile e dark obrigatório | Forte na base: breakpoints, overlay e `.dark` já existem | Auditar cada nova tela com modal/painel mobile e tokens sem `dark:` | `web/tailwind-themes/tailwind.config.js`, `AppChrome.tsx`, `AdminChrome.tsx`, `DocumentsSidebar.tsx` | Nenhuma nova API | Layout de tabela e ações pode perder acessibilidade em telas pequenas | Nível 2 |
| Design system Opal | Preservar componentes, tokens e padrões existentes | Forte, com legado misto | Usar Opal/refresh em qualquer rota tocada; não migrar todo `src/components` | `web/lib/opal/src/components/index.ts`, `web/lib/opal/src/layouts/index.ts`, rotas TON | Nenhuma | Misturar legado, built-in colors ou ícones proibidos cria dívida visual | Nível 0 |
| Telegram e outras integrações | Telegram é o primeiro canal externo; WhatsApp vem depois | Parcial: integrações e canais existem sobretudo no admin | Planejar administração e status sem criar fluxo paralelo | `web/src/app/admin/bots/[bot-id]/channels/*`, `web/src/lib/updateSlackBotField.ts` e rotas admin relacionadas | Backend 009: canal, identidade, credenciais, entrega, ACL e auditoria | Começar antes do contrato aumenta risco e exposição | Nível 3, bloqueado pelo backend |

## Conclusão

TON pode ser uma adaptação incremental. Agentes, chat, arquivos, fontes,
tema, i18n e responsividade já têm uma base útil. Ocorrências e relatórios
TON são lacunas de produto e contrato. A implementação deve parar na fronteira
frontend/backend definida em `backend-dependencies.md`.

Telegram exige contrato backend para credenciais, entrega, ACL e auditoria.
TON-FE-010 continua bloqueado. Não há nível 5 aceito.
