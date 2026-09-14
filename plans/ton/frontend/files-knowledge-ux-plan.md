# TON — plano UX de arquivos e conhecimento

## Constatação

O frontend existente tem as primitivas necessárias para arquivos e conhecimento, mas não
explica a distinção mais importante: “usar este arquivo somente nesta conversa” versus
“tornar este arquivo conhecimento persistente que TON poderá usar depois”. A posição
sugere o escopo, mas a UI não o nomeia.

Não use `temp_id` como sinal semântico. Em `web/src/lib/projects/types.ts` e
`web/src/lib/projects/providers.tsx`, `temp_<uuid>` é um ID otimista de upload usado
enquanto o servidor retorna o ID real do arquivo. Ele não define política de conhecimento
temporário.

## Modelo atual e caminhos de origem

| Conceito atual | Evidência de fonte | Escopo/comportamento atual | Implicação UX |
|---|---|---|---|
| Anexo de mensagem | `web/src/sections/input/AppInputBar.tsx`, `web/src/refresh-components/popovers/FilePickerPopover.tsx`, `web/src/sections/cards/FileCard.tsx` | Usuário seleciona/envia arquivos para uma mensagem. `currentMessageFiles` é verificado antes do envio. | Parece escopo de conversa, mas UI não informa se o objeto ficará disponível depois. |
| Arquivo recente do usuário | `web/src/sections/modals/UserFilesModal.tsx`, `web/src/lib/projects/providers.tsx` | Arquivos recentes vêm de `/api/user/files/recent`; uploads fora de incognito podem continuar selecionáveis e ser ligados a projeto. | Endpoint expõe arquivos reutilizáveis, mas frontend não prova retenção ou escopo de knowledge. Rotular persistência só após contrato do servidor. |
| Arquivo de projeto | `web/src/lib/projects/components/ProjectContextPanel.tsx` e componentes de projeto | Arquivos são ligados/desligados por `/api/user/projects/{id}/files/{fileId}` e podem ser enviados no contexto do projeto. | Primitiva durável de workspace mais forte. Adequada para conhecimento de caso/investigação TON após acordo de termos. |
| Knowledge de agente | `web/src/sections/knowledge/AgentKnowledgePane.tsx`, `web/src/sections/knowledge/agent-knowledge/KnowledgeAddView.tsx`, `web/src/sections/knowledge/agent-knowledge/KnowledgeMainContent.tsx` | Seleciona document sets, fontes conectadas, arquivos do usuário e registros para um Agent. | Superfície de knowledge durável de especialista. Manter como host de configuração; adicionar copy explícita depois. |
| Fontes conectadas | `web/src/sections/knowledge/AgentKnowledgePane.tsx`, `web/src/sections/knowledge/agent-knowledge/KnowledgeAddView.tsx` | Usa pares de conectores e document sets existentes. | Preservar fronteiras de conector/indexação; não criar novo file store TON no frontend. |
| Sessão incógnita | `web/src/providers/IncognitoProvider.tsx`, `web/src/app/app/page.tsx` | `incognitoSessionId` aleatório é enviado com uploads; teardown chama `/api/chat/end-incognito-session/{sessionId}` via `sendBeacon`. Limpeza do servidor é explícita. | É a única semântica claramente efêmera. Manter modo e aviso curto de que arquivos não permanecem após teardown. |
| Exibição de chat/fonte | `web/src/sections/document-sidebar/DocumentsSidebar.tsx`, `web/src/app/app/interfaces.ts` | Fontes citadas e descritores de arquivo aparecem após mensagem. `ChatFileType` inclui `USER_KNOWLEDGE`. | Labels atuais distinguem fontes de anexos, mas não intenção de persistência. |

## Existing API and state boundaries

`web/src/lib/projects/svc.ts` já separa as seguintes operações:

* upload: `/api/user/projects/file/upload`, with optional `project_id`, `temp_id_map`,
  and incognito session ID;
* recent files: `/api/user/files/recent`;
* project files: `/api/user/projects/files/{projectId}`;
* project instructions/details and project CRUD;
* link/unlink: `/api/user/projects/{id}/files/{fileId}`;
* delete: `/api/user/projects/file/{fileId}`;
* status: `/api/user/projects/file/statuses`;
* session files: `/api/user/projects/session/{chatSessionId}/files`;
* token counts and chat/project movement endpoints.

`web/src/lib/projects/providers.tsx` (`ProjectsProvider`) possui arquivos de projeto,
recentes, mensagem atual, estado otimista de upload, rejeição/toast e `incognitoSessionId`.
O provider mapeia ID de cliente a ID real do servidor, mas não tem modo explícito de
persistência. `IncognitoProvider` possui o ciclo de vida efêmero mais forte.

Portanto, o frontend não deve prometer “temporário” ou “persistente” apenas pelo ID atual.
O contrato do servidor deve definir retenção, escopo de consulta, exclusão e vínculo a
projeto/agente.

## Minimal UX direction

Reutilizar picker e superfícies de knowledge existentes. Não adicionar sistema novo de
gestão de arquivos. Adicionar escolha explícita de escopo quando o arquivo entrar:

| Intenção do usuário | Label PT-BR sugerido | Host existente | Comportamento exigido |
|---|---|---|---|
| Analisar somente na conversa atual | **Somente esta conversa** | `FilePickerPopover.tsx` / `AppInputBar.tsx` | Anexar à mensagem/sessão atual. Mostrar “não será usado em outras conversas” somente se backend garantir o escopo. |
| Reter como knowledge TON | **Adicionar ao conhecimento** | `UserFilesModal.tsx`, `ProjectContextPanel.tsx` ou `AgentKnowledgePane.tsx`, conforme destino | Persistir arquivo e mostrar destino: pessoal, projeto/caso ou especialista. Exigir destino explícito se houver mais de um. |
| Não reter após sessão incógnita | **Sessão privada (não reter)** | Pill atual em `AppChrome` e `IncognitoProvider.tsx` | Manter teardown e exibir aviso de retenção antes do upload. |

Evitar chamar IDs otimistas de “arquivos temporários”. Para progresso, usar
“enviando/processando”; reservar “temporário” para escopo de retenção imposto pelo servidor.

## Fluxos planejados

### A. Análise somente na conversa

1. Usuário seleciona arquivo em `AppInputBar`.
2. Picker mostra “Somente esta conversa” como padrão somente se backend suportar escopo
   real de sessão/mensagem; caso contrário, manter comportamento atual e marcar contrato pendente.
3. `currentMessageFiles` continua sendo a origem do anexo da mensagem.
4. UI mostra estados de upload, processamento e falha já representados por
   `ProjectFileStatus` (`UPLOADING`, `PROCESSING`, `COMPLETED`, `FAILED` e outros).
5. No teardown da conversa, somente arquivos desse escopo podem entrar na limpeza.

### B. Knowledge TON persistente

1. Usuário escolhe “Adicionar ao conhecimento”.
2. UI pede o destino existente: pessoal, projeto/caso ou especialista. Não selecionar destino
   de forma silenciosa.
3. Reutilizar `ProjectContextPanel` para arquivos de projeto/caso e `AgentKnowledgePane`
   para fontes de especialista.
4. Mostrar status durável e oferecer ações existentes de excluir/desligar.
5. Conversas futuras consultam o arquivo somente conforme o escopo escolhido no servidor.

### C. Incognito

1. Manter modo incógnito e pill existentes.
2. Antes do upload, informar que arquivos são anexados à sessão privada e removidos no
   teardown, sujeito à confirmação do backend.
3. Preservar limpeza `pagehide`/`sendBeacon` e testar sessão de browser interrompida.

## Fronteira backend e perguntas abertas

Este é um plano UX frontend, não implementação backend. Antes de codificar labels ou
controles, donos do backend devem responder:

* Um upload sem projeto persiste hoje como arquivo de usuário reutilizável? Provider atual
  mostra o arquivo em recentes, mas UI não declara regra de retenção.
* Retenção somente na conversa usa ID de sessão, mensagem ou novo escopo de arquivo? Qual
  a garantia de limpeza em teardown normal e interrompido?
* “Knowledge persistente” significa consulta pessoal, de projeto, de agente ou todas? Como
  permissões e exclusão são propagadas?
* Um arquivo persistente existente pode ser anexado a uma conversa sem mudar seu escopo?
* Como mobile e side panel NRF mostram a mesma escolha de escopo?

Não adicionar flag somente frontend que alegue persistência. Usar resposta de API com
escopo e status explícitos e renderizar o contrato nos componentes compartilhados.

## Guardrails de implementação

* Manter limite frontend `/api/...`. Não introduzir URL direta do backend.
* Preferir componentes/layouts Opal exigidos por `web/AGENTS.md`: `Button`, input,
  modal/popover, `Text`, ícones e classes de tokens semânticos.
* Manter strings nos catálogos next-intl; usar chaves para labels PT-BR e copy explicativa.
  Não remover infraestrutura i18n (ver `i18n-decision.md`).
* Não adicionar componente shadcn, paleta nova ou file system separado.
* Preservar foco de teclado, labels de leitor de tela, layout responsivo e dark mode.

## Plano de verificação

Após o contrato do servidor existir, validar o menor conjunto de fluxos:

* Playwright: anexar arquivo somente à conversa, recarregar/continuar e verificar que não
  é oferecido como knowledge durável.
* Playwright: persistir em projeto e especialista, verificar painel correspondente e
  desligar/excluir.
* Playwright: upload incógnito seguido de teardown; verificar status e copy de limpeza sem
  depender de `temp_<uuid>`.
* Integração: endpoints de upload/status/exclusão/vínculo pela rota API frontend e checks
  de permissão para escopos de usuário/projeto/agente.
* TypeScript e catálogos: `cd web && bun run types:check`, testes de paridade/ICU e suite
  `web/tests/e2e` relevante.

A recomendação é uma pequena extensão de copy e escopo em componentes existentes, bloqueada
somente por contrato explícito de retenção backend. Não exige mudança de rota ou novo storage TON.
