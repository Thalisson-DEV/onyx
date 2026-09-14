# TON — plano UX para achados e ocorrências

## Situação atual

Não existe uma entidade TON de achado, ocorrência, caso ou evidência no
frontend. A busca por ocorrência encontrou somente campos de extração do
knowledge graph em `backend/onyx/db/models.py`, além de severidade de
notificação e audit log. Esses dados não representam um caso tratado por uma
pessoa.

Também não há rota em `web/src/app` nem serviço em `web/src/lib` para esse
domínio. Portanto, não usar chat, notificação ou contagem do grafo como
persistência implícita. A tela depende de contrato backend futuro, descrito em
`backend-dependencies.md`.

## Objetivo de produto

Permitir que uma pessoa encontre, entenda, atribua e acompanhe uma ocorrência
TON, com as fontes que sustentam o achado. O fluxo deve separar “detectar” de
“tratar”. Um resultado de busca pode originar uma ocorrência, mas não deve
criá-la sem regra explícita.

## Campos obrigatórios do domínio

O contrato e a UI futura devem preservar todos os campos pedidos pelo briefing.
Um campo desconhecido ou sem permissão deve aparecer como ausente, nunca ser
preenchido por inferência da notificação ou do knowledge graph.

| Campo TON | Uso na lista/detalhe | Estado atual |
|---|---|---|
| Título | Identificação e cabeçalho | Não existe entidade TON. |
| Tipo | Filtro e classificação do achado | Contrato futuro. |
| Domínio | Filtro e contexto operacional | Contrato futuro. |
| Severidade | Tag textual e filtro | Notificações têm severidade, mas não ocorrência. |
| Status | Estado textual e transições | Contrato futuro. |
| Unidade | Contexto da unidade afetada | Contrato futuro. |
| Data de detecção | Cabeçalho e filtro de período | Contrato futuro. |
| Impacto financeiro | Valor opcional, com moeda e precisão | Contrato futuro; não inferir de custo de uso. |
| Evidência | Documentos, arquivos, mensagens ou URLs autorizadas | Reutilizar citações somente após ACL do domínio. |
| Interpretação do TON | Resumo explicativo do achado | Contrato futuro. |
| Ação recomendada | Próximo passo e estado de execução | Contrato futuro. |
| Responsável | Pessoa/equipe atribuída | Contrato futuro. |
| Histórico/resolução | Eventos imutáveis e resultado final | Contrato futuro; não usar audit log como substituto. |

## Estrutura de informação

### Lista

Rota planejada: `/app/occurrences`.

Colunas essenciais:

- identificador curto e título;
- tipo, domínio e unidade;
- status: novo, em análise, confirmado, resolvido, descartado;
- severidade/risco, com `Tag` sem depender só de cor;
- impacto financeiro quando conhecido;
- interpretação do TON e ação recomendada;
- responsável e equipe;
- fonte principal e data da última evidência;
- atualização mais recente.

Filtros: status, severidade, responsável, origem, período e texto. O filtro
deve ser combinável e refletido na URL para permitir cópia e retorno do
navegador. Paginação deve vir do servidor.

### Detalhe

Rota planejada: `/app/occurrences/[id]`.

Ordem recomendada:

1. cabeçalho com título, estado, severidade, responsável e ações permitidas;
2. resumo do achado e data de detecção;
3. evidências e citações com `DocumentsSidebar` ou um `Card` equivalente;
4. interpretação do TON e ação recomendada;
5. impacto financeiro, unidade, domínio e tipo quando disponíveis;
6. atividade/histórico em ordem temporal;
7. campos complementares, links e notas internas;
8. modal de confirmação para descartar, resolver ou alterar responsável.

Rota planejada: `/app/occurrences/[id]/history` só é necessária se o histórico
for maior que o painel do detalhe. Começar com painel para manter a diferença
mínima.

## Componentes a reutilizar

Usar os exports de `web/lib/opal/src/components/index.ts` e
`web/lib/opal/src/layouts/index.ts`:

- `SettingsLayouts` ou `RootLayout` para a casca;
- `Content` e `ContentAction` para título, filtros e ações;
- `Table`, `Pagination`, `Tag`, `FilterButton` e inputs de seleção;
- `Card`, `Divider`, `MessageCard` e `EmptyMessageCard` para estados;
- `Modal`/`ConfirmationModalLayout` para ações irreversíveis;
- `IconLoader`/`OnyxLoader` para carregamento.

`web/src/app/ee/admin/performance/query-history/QueryHistoryTable.tsx` é uma
referência de tabela, filtros, paginação e detalhe. Ele usa um `Badge` legado;
uma tela TON deve usar `Tag` ou outro componente Opal. O
`DocumentsSidebar` e `ChatDocumentDisplay` em
`web/src/sections/document-sidebar/` são a referência para evidência citada.

## Acessibilidade e estados

- Cada ocorrência deve ter nome acessível, estado textual e ação de teclado.
- Severidade não pode ser comunicada somente pela cor.
- Filtros devem ter labels, foco visível e botão claro.
- Tabela deve oferecer detalhe acessível no mobile, sem exigir scroll horizontal
  para ações principais.
- Sem resultados: explicar filtros e oferecer limpeza.
- Sem permissão: não renderizar edição e deixar explícito que o item não é
  editável.
- Falha de rede: manter filtros e permitir retry; não apagar estado local.
- Conflito de atualização: informar que o registro mudou e recarregar a versão
  autorizada.

## Regras de permissão e privacidade

O backend deve autorizar leitura de cada ocorrência e de cada evidência. A UI
não pode assumir que acesso ao índice dá acesso ao caso. Atribuição, mudança de
estado, comentário e exportação precisam de capacidades separadas quando o
contrato exigir.

O histórico pode conter nomes, documentos e comentários. O detalhe deve
ocultar dados fora da ACL da fonte e não deve enviar o conteúdo inteiro para a
lista. Logs de auditoria são apoio técnico, não substituto do histórico de
produto.

## Dependências e ordem

1. Definir schema de ocorrência, enum de estado/severidade, ACL e paginação.
2. Definir contrato de evidência e vínculo com documentos, arquivos e chats.
3. Definir transições válidas e eventos auditáveis.
4. Implementar cliente SWR e tela de lista.
5. Implementar detalhe, histórico e ações.
6. Validar mobile, dark theme, teclado, permissões e exportação.

Nenhuma destas etapas deve alterar o backend durante o objetivo de adaptação
frontend atual. O backlog separa a decisão de contrato da futura implementação.
