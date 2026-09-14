# TON — arquitetura de informação e navegação

## Princípios

1. `/app` continua sendo a casca autenticada. TON muda a linguagem e a
   composição, não cria outra aplicação.
2. O usuário deve distinguir quatro contextos: conversar, consultar
   especialistas, tratar ocorrências e consultar relatórios.
3. Fontes e conhecimento persistente ficam próximos do contexto que os usa.
   Anexos ficam no composer e na resposta atual; chamar esse escopo de
   “temporário” somente após o contrato do servidor confirmar retenção e limpeza.
4. Rotas administrativas continuam separadas. Billing, Craft, tier, tracing e
   outras superfícies SaaS não entram na navegação TON de usuário normal.
5. A mesma árvore funciona em desktop, mobile e tema escuro. No mobile, painéis
   laterais viram modal ou drawer.

## Árvore proposta

```text
TON
├── Central                         /app
│   ├── Nova conversa               /app
│   ├── Resposta e fontes           /app (painel DocumentsSidebar)
│   └── Histórico                   /app (AppSidebar / chat sessions)
├── Especialistas                   /app/agents
│   ├── Ver especialista             /app/agents (AgentViewer)
│   ├── Criar especialista           /app/agents/create
│   └── Editar especialista          /app/agents/edit/[id]
├── Ocorrências                     /app/occurrences (rota futura)
│   ├── Lista e filtros              /app/occurrences
│   ├── Detalhe e evidências         /app/occurrences/[id]
│   └── Histórico                    /app/occurrences/[id]/history
├── Relatórios                      /app/reports (rota futura)
│   ├── Lista e períodos             /app/reports
│   └── Relatório                    /app/reports/[id]
├── Fontes                          /app/sources (rota futura ou settings)
│   ├── Fontes disponíveis           /app/sources
│   └── Arquivo pessoal/projetos     /app/settings ou contexto do projeto
├── Configurações                   /app/settings
│   ├── Geral, conversa, acesso      abas já existentes
│   ├── Conectores                   /app/settings/connectors
│   └── Conta                        abas já existentes
└── Administração                   /admin/* (admin only)
    ├── Conectores e indexação
    ├── Personas/agentes
    ├── Usuários e permissões
    └── Uso, histórico e integrações
```

As rotas de ocorrências, relatórios e fontes são destinos de planejamento.
Elas não existem no checkout atual e não devem ser simuladas como existentes.
O backlog em `implementation-roadmap.md` cria contratos antes de criar telas.

## Navegação global

`web/src/sections/sidebar/AppSidebar.tsx` já tem cabeçalho, agentes, projetos,
chats recentes e rodapé de conta/admin. A adaptação deve manter esse componente
como dono da navegação autenticada. A proposta é:

- “Central” aponta para `/app` e usa o agente padrão, sem criar um roteador
  paralelo.
- “Especialistas” aponta para `/app/agents`. A conversa de um especialista
  continua em `/app?agentId=<id>`, como em
  `web/src/lib/agents/components/AgentButton.tsx`.
- “Ocorrências” e “Relatórios” só aparecem quando os contratos TON e a
  permissão correspondente existirem. Um link não deve apontar para uma tela
  vazia.
- “Fontes” pode começar como seção em Settings e em
  `ProjectContextPanel`. Uma rota própria só é necessária se houver inventário
  de fontes além de conectores e arquivos pessoais.
- O acesso ao admin permanece no rodapé. `AdminSidebar` continua separado e
  usa `ADMIN_ROUTES` em `web/src/lib/admin-routes.ts`.

## Classificação de superfícies

| Superfície atual | Classe TON | Ação de descoberta |
|---|---|---|
| `/app`, chat, search e shared chat | Principal | Preservar. Ajustar texto, agente padrão e estados. |
| `/app/agents/*` | Principal | Preservar. Mapear personas para especialistas. |
| `/app/settings/*` | Principal | Manter apenas abas úteis; esconder sem apagar contratos. |
| `/app/occurrences/*` | Lacuna | Definir entidade, RBAC e API antes da UI. |
| `/app/reports/*` | Lacuna | Separar relatório TON de uso administrativo/EE. |
| `/app/sources/*` | Decisão | Começar com conectores, arquivos e fontes citadas; evitar inventário duplicado. |
| `/admin/*` | Admin | Preservar permissão e gate. Reclassificar links visíveis. |
| `/craft/*`, `/nrf/*`, `/mcp/*` | Oculta ou integração | Não colocar na navegação normal sem requisito TON explícito. |
| `/ee/admin/*` | Admin/EE | Não expor como recurso TON por padrão. |
| `/auth/*` e `/anonymous/*` | Entrada pública | Preservar segurança e ajustar somente linguagem/destino. |

## Persistência e contexto

| Tipo | Exemplos no checkout | Regra TON |
|---|---|---|
| Escopo de conversa (a confirmar) | Anexo no composer, arquivo de uma mensagem, sessão incógnita | Deve ficar ligado à sessão/mensagem; só recebe o rótulo “temporário” quando o servidor confirmar retenção e limpeza. |
| Persistente pessoal (quando declarado pelo servidor) | Arquivo recente, `ProjectFile`, projeto e instruções | Deve mostrar proprietário, escopo, estado de processamento e ação de remoção. A presença em “recentes” não prova retenção. |
| Persistente de especialista | `user_file_ids`, document sets, hierarchy/document IDs | Deve seguir as permissões do agente/persona e indicar quem pode usar a fonte. |
| Fonte indexada | Citações e documentos de conectores | Deve respeitar ACL do documento; a UI mostra apenas metadados permitidos. |
| Resultado derivado | Ocorrência, evidência, relatório | Requer entidade e retenção próprias; não deve ser salvo como chat ou notificação por acidente. |

`web/src/lib/projects/providers.tsx` já diferencia upload otimista, projeto,
arquivo recente e sessão incógnita. Essa distinção é o ponto de integração. A
UI não deve inferir permanência apenas porque um arquivo aparece na resposta.

## Padrões de tela

- **Listas:** `Content`, `ContentAction`, `Table`, `Pagination`, `Tag` e
  `FilterButton` de `@opal/components`.
- **Detalhes:** `SettingsLayouts`, `Card`, `Divider`, `Modal` ou
  `ConfirmationModalLayout`.
- **Chat e fontes:** `RootLayout` e `DocumentsSidebar`; no mobile, usar o
  modal já usado por `DocumentsSidebar`.
- **Navegação:** `SidebarLayouts` e `SidebarTab`; não introduzir uma sidebar
  paralela.
- **Estados:** `IconLoader`/`OnyxLoader`, `EmptyMessageCard` e `MessageCard`; cada carregamento
  SWR deve ter estados de erro e vazio.

Os componentes são exportados por `web/lib/opal/src/components/index.ts` e os
layouts por `web/lib/opal/src/layouts/index.ts`. Qualquer exceção precisa ser
registrada como dívida localizada, não como motivo para migrar todo o legado.

## Mobile, acessibilidade e tema

`web/tailwind-themes/tailwind.config.js` define `sm` em 724px e `md` em 912px.
`AppChrome`, `AdminChrome` e `DocumentsSidebar` já têm toggles, overlay ou
modal para telas estreitas. A nova IA deve obedecer a estes comportamentos:

- sidebar fechada por padrão no mobile, com botão de abertura acessível;
- tabela de ocorrências e relatórios com colunas essenciais, ações em menu e
  alternativa de detalhe;
- nenhum conteúdo importante somente por hover;
- tokens sem classes `dark:` ou cores Tailwind built-in;
- foco visível, nome acessível e alvo de toque adequado.

O tema é controlado por `next-themes` em `web/src/app/layout.tsx`. Os tokens
semânticos claros e escuros estão em `web/lib/shared/tokens/semantic-light.json`
e `semantic-dark.json`. Não há requisito offline no escopo.

## Decisões de arquitetura

As ADRs completas estão em `implementation-roadmap.md`. Em resumo, elas
preservam a casca `/app`, Opal, adaptação de diferença mínima, sem migração
shadcn e sem reescrita. O objetivo frontend não altera backend. Português é o
idioma aceito; a infraestrutura i18n fica intacta para decisão posterior.
