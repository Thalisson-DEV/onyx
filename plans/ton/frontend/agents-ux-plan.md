# TON — plano UX para Central e especialistas

## Objetivo

Usar o sistema de personas/agentes do Onyx como a base dos especialistas TON.
“Central” é o agente padrão e “especialista” é uma persona elegível. Não criar
uma segunda entidade, um segundo store ou um segundo conjunto de endpoints.

## Mapeamento do contrato atual

| Conceito TON | Implementação atual | Contrato observado |
|---|---|---|
| Central | Assistente padrão, normalmente id `0` | `web/src/lib/agents/hooks.ts` (`useActiveAgent`) resolve sessão/URL, default, pin e fallback. |
| Especialista | `MinimalAgent`/`Agent`/`FullAgent` | `web/src/lib/agents/types.ts` contém descrição, prompts, fontes, ferramentas, imagem/ícone, labels e permissões. |
| Catálogo | Página de agentes | `web/src/views/AgentsNavigationPage.tsx` usa busca, abas, filtros, destaque e `AgentCard`. |
| Acesso rápido | Botão e pins no sidebar | `web/src/lib/agents/components/AgentButton.tsx` aponta para `/app?agentId=<id>`. |
| Detalhe | Viewer compartilhado | `web/src/lib/agents/components/AgentViewer.tsx` carrega `FullAgent`. |
| Compartilhar | Modal/serviço de compartilhamento | `web/src/lib/agents/svc.ts` e `/api/persona/:id/share`. |
| Administração | Lista e edição administrativa | `/admin/agents`, `/admin/persona` e `useAdminAgents` respeitam permissões. |

## Fluxo proposto

1. O usuário entra em `/app`. A página resolve a sessão atual e
   `useActiveAgent` seleciona Central ou o agente escolhido.
2. A sidebar mostra Central no topo e especialistas fixados na seção de
   agentes. “Ver todos” continua levando a `/app/agents`.
3. A página de especialistas oferece busca, filtro e cards. O card permite
   abrir conversa, ver detalhes e executar somente ações permitidas pelo
   objeto de permissão.
4. O detalhe mostra propósito, fontes, capacidades e compartilhamento. O botão
   de conversar mantém o parâmetro `agentId` na URL.
5. Criação e edição continuam em `/app/agents/create` e
   `/app/agents/edit/[id]`. O texto TON pode chamar a tela de “especialista”,
   mas os nomes internos `Agent` e `persona` permanecem.

## Ajustes mínimos de conteúdo

- Nome “Central” só deve ser aplicado ao agente padrão após confirmação de que
  a instalação não usa id `0` para um caso customizado. Se houver dúvida, use a
  configuração do backend e um fallback neutro.
- Trocar “agent” por “especialista” na interface TON, sem renomear tipos,
  endpoints ou dados persistidos.
- Descrever fontes como “conhecimento usado pelo especialista” e ferramentas
  como “ações permitidas”. Não prometer acesso que não esteja em `tools`,
  `document_sets`, `user_file_ids` ou `permissions`.
- Manter a imagem/ícone existente. A marca TON não precisa de avatar novo enquanto o
  logo Vale Norte não estiver definido.
- Não exibir “featured” ou “listed” como promessa de produto; são campos de
  catálogo e administração.

## Permissões e estados

O card e o viewer devem derivar ações do contrato, não de posição na UI. Os
campos relevantes são `permissions`, `user_permission`, `owner`, `users`,
`groups`, `is_public`, `is_listed` e `sharing_status` em
`web/src/lib/agents/types.ts` e nos snapshots de
`backend/onyx/server/features/persona/models.py`.

Estados necessários:

- carregando: manter `IconLoader`, `OnyxLoader` ou placeholder do Opal;
- vazio: informar que não há especialistas elegíveis e oferecer Central;
- erro: preservar resposta de erro e permitir tentar novamente;
- sem permissão: não mostrar editar, compartilhar ou apagar;
- agente excluído ou indisponível: remover seleção ativa e retornar a Central;
- pin otimista: tratar falha de `/api/user/pinned-assistants` e restaurar a
  lista anterior.

`usePinnedAgents` já atualiza pins de modo otimista. A adaptação deve preservar
essa reversão e não guardar uma cópia TON paralela.

## Fontes, arquivos e conversa

O especialista pode carregar `document_sets`, `user_file_ids`, IDs de hierarquia
e IDs de documentos. A interface deve mostrar a origem com o mesmo painel usado
na conversa (`web/src/sections/document-sidebar/DocumentsSidebar.tsx`).
Arquivos anexados a uma mensagem ficam no contexto da sessão no frontend. Só
devem ser chamados de temporários, ou de persistentes após associação explícita
a projeto ou especialista, quando o backend confirmar retenção e limpeza. A
regra planejada está em `ton-information-architecture.md`.

## Escopo fora deste plano

- Novo runtime de agentes.
- Novo mecanismo de compartilhamento ou RBAC.
- Reescrita de `AgentCard`, `AgentViewer`, `AppSidebar` ou `AppPage`.
- Edição das APIs de persona.
- Migração global de componentes legados.

Esses limites implementam as ADRs de preservação e “nenhuma modificação de
backend para o objetivo frontend”.

## Aceitação e QA futuro

- `/app/agents` lista especialistas elegíveis e possui estado vazio e erro.
- Clique no card abre `/app?agentId=<id>` e a conversa usa o mesmo agente.
- Central continua sendo o fallback quando URL, sessão ou pin não resolve.
- Editar, compartilhar e excluir só aparecem com permissão válida.
- Filtro, pin, troca de agente e refresh não criam estado duplicado.
- Desktop e mobile mantêm foco, leitura por teclado e tema escuro.
- Rodar `cd web && bun run types:check`, `bun run lint` e os testes Jest/RTL
  afetados. Criar um teste Playwright pelo padrão POM em
  `web/tests/e2e` para seleção de especialista e retorno a Central.
