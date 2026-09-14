# TON — dependências de backend para o frontend

## Limite de escopo

Este documento não propõe editar backend agora. Ele registra o que o frontend
já consome, o que pode ser configurado e o que precisa de contrato novo. Todos
os testes de integração devem chamar o frontend em `http://localhost:3000/api/*`,
conforme `AGENTS.md`, e não o serviço backend diretamente.

## Contratos existentes

| Necessidade TON | Endpoint ou contrato atual | Fonte no frontend/backend | Uso permitido no plano |
|---|---|---|---|
| Identidade e capacidades | `GET /api/me` | `web/src/lib/swr-keys.ts`, `web/src/lib/users/svc.ts` | Identidade, nome, preferências, pins e gates. |
| Configuração de produto | `GET /api/settings`, `GET /api/enterprise-settings` | `web/src/lib/settings/hooks.ts`, `backend/onyx/server/settings/` | Nome, flags, tema/logo opcional e disponibilidade. |
| Auth | `/api/auth/*`, `/auth/*` | `web/src/lib/auth/svc.ts`, `web/src/app/auth/*` | Preservar login, SSO, senha e redirecionamento. |
| Central e especialistas | `GET /api/persona`, `GET /api/persona/:id` | `web/src/lib/agents/hooks.ts`, `svc.ts`; `backend/onyx/server/features/persona/api.py` | Listar e carregar personas autorizadas. |
| Criar/editar especialistas | `POST /api/persona`, `PATCH /api/persona/:id`, `DELETE /api/persona/:id` | `web/src/lib/agents/svc.ts`; `persona/api.py`, `persona/models.py` | Reusar permissões atuais, sem novo sistema. |
| Compartilhamento | `/api/persona/:id/share`, `/share/me`, `/transfer-ownership` | `web/src/lib/agents/svc.ts`; `persona/api.py` | Exibir somente ações presentes na permissão. |
| Pins | `/api/user/pinned-assistants` | `web/src/lib/agents/hooks.ts`, `svc.ts` | Manter update otimista e fallback. |
| Uso individual | `GET /api/user/usage` | `web/src/app/app/settings/usage/lib.ts`, `web/src/lib/swr-keys.ts` | Tratar custo e preço de modelo como superfície operacional; não converter o dado em plano, billing ou upgrade. |
| Chat e histórico | `/api/chat/*`, `GET /api/chat/get-user-chat-sessions`, `/api/chat/search` | `web/src/lib/swr-keys.ts`, `web/src/app/app/services/lib.tsx`, `useChatSessions.ts` | Central, sessões e busca já existentes. |
| Busca | `POST /api/search` e APIs de search | `web/src/lib/search/interfaces.ts`, `backend/onyx/server/features/search/api.py` | Usar apenas com vector DB e fontes autorizadas. |
| Projetos | `/api/user/projects`, `/api/user/projects/create`, `/api/user/projects/:id`, `/details`, `/instructions` | `web/src/lib/projects/svc.ts`; `backend/onyx/server/features/projects/api.py`, `models.py` | Conhecimento persistente pessoal. |
| Arquivos | `/api/user/projects/file/upload`, `/api/user/files/recent`, `/files/:projectId`, `file/statuses`, `/api/chat/file/:id` | `web/src/lib/projects/svc.ts`, `providers.tsx`; `projects/api.py` | Preservar status, ACL, incognito e upload. |
| Document sets/tags | `GET /api/manage/document-set`, `GET /api/query/valid-tags` | `web/src/lib/swr-keys.ts`, `backend/onyx/server/features/document_set/` | Fontes de especialistas; confirmar permissões antes de mostrar. |
| Hierarquia/documentos | Hierarchy APIs e IDs de documentos | `web/src/lib/hierarchy/svc.ts`; `backend/onyx/server/features/hierarchy/api.py` | Reusar apenas quando o agente já expõe esses IDs. |
| Conectores e indexação | `/api/manage/connector-status`, `/api/manage/admin/connector/indexing-status`, OAuth | `web/src/lib/connectors/connectors.tsx`, `web/src/lib/connectors/oauth.ts`, `web/src/lib/swr-keys.ts` | Resumo de fontes; gestão completa permanece admin. |
| Notificações | `/api/notifications`, `/summary`, `/dismiss` | `web/src/lib/swr-keys.ts`, `web/src/lib/notifications/api.ts`; `backend/onyx/server/features/notifications/` | Alertas transitórios, não ocorrências. |
| Relatório de uso | `/api/admin/usage-report` | `UsageReports.tsx`; `backend/ee/onyx/server/reporting/` | Referência admin/EE, não contrato TON. |
| Histórico de consultas | `/api/admin/chat-session-history` e `/:id` | `QueryHistoryTable.tsx`; `backend/ee/onyx/server/query_history/` | Referência admin/EE, não exposição normal. |
| Telegram e outros canais | Futuro contrato do Backend 009; APIs admin existentes são referência | `web/src/app/admin/bots/*`, `web/src/lib/updateSlackBotField.ts`; backend manage/oauth | Telegram é o primeiro canal externo. TON-FE-010 espera o contrato backend. |

## Dependências por feature

### Central e especialistas

O contrato existente é suficiente. `PersonaUpsertRequest` em
`backend/onyx/server/features/persona/models.py` já inclui descrição, prompts,
fontes, ferramentas, labels, imagem enviada/ícone, visibilidade e permissões. Confirmar a
regra de agente padrão antes de chamar o id `0` de Central. Nenhum endpoint
novo é necessário para a primeira adaptação.

### Conhecimento e fontes

Projetos têm proprietário e arquivos associados em
`backend/onyx/server/features/projects/api.py`. A resposta de upload contém
arquivos aceitos/rejeitados e o frontend acompanha estados de processamento.
Isso oferece pontos de integração, mas não comprova a política de retenção
temporária ou persistente. Uma tela de inventário de fontes exige contrato de
agregação que não foi encontrado.

### Ocorrências

É uma lacuna de backend. Antes da UI, definir:

- entidade com tenant, título, tipo, domínio, unidade, resumo, severidade,
  status, impacto financeiro opcional, interpretação do TON, ação recomendada,
  responsável e timestamps;
- ACL por ocorrência e evidência, incluindo grupos;
- lista paginada com filtros e ordenação estável;
- detalhe, transições válidas e histórico imutável;
- vínculo de evidência a documento, arquivo, mensagem ou URL autorizada;
- ações de atribuição, comentário, resolução, descarte e auditoria;
- retenção, exportação e proteção contra dados fora da ACL.

O nome de rota fica pendente. A proposta `/api/ton/occurrences` em
`findings-ux-plan.md` é um marcador de planejamento, não uma API existente.

### Relatórios TON

Os endpoints admin/EE não atendem usuário comum. Definir contrato para lista,
criação assíncrona, detalhe e download temporário. A geração deve respeitar as
ACLs de ocorrência e evidência. Artefatos existentes com
`FileOrigin.GENERATED_REPORT` podem ser uma implementação interna, mas não
devem mudar a superfície pública sem decisão.

### Integração Telegram

Telegram está confirmado como o primeiro canal externo TON. WhatsApp vem
depois. Não foi encontrado um contrato backend TON para o canal.

TON-FE-010 fica bloqueado até o Backend 009 definir identidade, credenciais,
destino, webhook ou polling, entrega, ACL e auditoria. Web e Telegram devem
usar as mesmas capacidades de aplicação e domínio. O frontend não protege
acesso somente ao ocultar a interface.

## Flags, licença e permissão

`web/src/lib/admin-routes.ts` combina permissões, tier, cloud, assinatura,
vector DB, Craft, hooks, OpenSearch e query history. `AdminChrome` repete gates
no servidor/cliente. A UI TON deve ter uma matriz explícita de visibilidade e
não confiar só em esconder o link: rota direta também deve recusar acesso.

`useSettings` trata 404 de enterprise settings como ausência esperada em CE.
Qualquer uso de logo ou configuração EE deve manter esse comportamento e não
transformar ausência de endpoint em falha global.

## Contratos que a implementação não pode alterar neste objetivo

- `persona` e seus snapshots;
- projetos, arquivos e modo incógnito;
- chat, search e citações;
- conectores, OAuth e indexação;
- usage export e query history;
- autenticação, RBAC e capacidades.

Se uma lacuna exigir mudança, registrar contrato, owner e teste no backlog e
parar a implementação frontend até a decisão correspondente.
