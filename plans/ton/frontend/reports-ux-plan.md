# TON — plano UX para relatórios

## Situação atual

O checkout tem duas referências úteis, mas nenhuma é um relatório de domínio
TON:

- `web/src/views/admin/WorkspaceAnalyticsPage/UsageReports.tsx` usa
  `/api/admin/usage-report`, período, polling, paginação e download.
- `web/src/app/ee/admin/performance/query-history/QueryHistoryTable.tsx` usa
  `/api/admin/chat-session-history`, tabela, detalhe, feedback, usuário,
  persona e exportação.

O backend correspondente está em `backend/ee/onyx/server/reporting/` e
`backend/ee/onyx/server/query_history/`. Os modelos e rotas são
administrativos/EE. Eles não provam a existência de relatório TON para usuário
comum.

## Objetivo de produto

Oferecer uma visão de atividade TON, com período, status de geração, fontes de
dados, métricas de ocorrências e exportação autorizada. O usuário deve saber se
está vendo um relatório pronto, em geração ou expirado. Um relatório não deve
ser apenas uma cópia de histórico de chat.

## UX planejada

Rota inicial: `/app/reports`.

Conteúdo:

1. cabeçalho “Relatórios”, período e ação “Gerar relatório”;
2. cartões curtos para total de ocorrências, resolvidas, pendentes e fontes;
3. tabela com nome, período, tipo, status, criador, validade e download;
4. filtros por tipo, status e período;
5. estado vazio com explicação e ação de geração;
6. polling limitado enquanto o servidor gera o artefato, com timeout e retry.

Rota opcional: `/app/reports/[id]` para detalhamento de métricas, metodologia,
fontes e ocorrências incluídas. Se o relatório for somente arquivo baixável,
começar com modal ou painel para evitar uma rota sem conteúdo.

## Padrões reutilizáveis

Reutilizar a composição de `UsageReports` para geração, polling, toast,
paginação e download. Reutilizar a estrutura de `QueryHistoryTable` para
colunas, filtros e detalhe. Substituir `Badge` legado por `Tag` de Opal em
qualquer novo código.

Componentes preferidos:

- `Content`, `ContentAction`, `Card`, `Table`, `Pagination`, `Tag`;
- `InputDatePicker` e filtros Opal;
- `MessageCard` para erro e `EmptyMessageCard` para vazio;
- `Modal` ou `ConfirmationModalLayout` para confirmação de geração/exportação.

As exportações devem usar o padrão de download já validado, sem expor URLs
permanentes. O backend deve emitir autorização temporária ou sessão autenticada.

## Contrato mínimo futuro

```text
GET  /api/ton/reports?from=&to=&type=&status=&page=&page_size=
POST /api/ton/reports                    -> { report_id, status }
GET  /api/ton/reports/{id}               -> metadados e métricas autorizadas
GET  /api/ton/reports/{id}/download      -> arquivo ou URL temporária
```

Os nomes são proposta de planejamento. Não devem ser codificados antes da
decisão de backend. O payload precisa conter `id`, tipo, período, status,
created_at, created_by, expires_at, métricas e permissões. O detalhe deve
informar as fontes e a regra de inclusão.

`FileOrigin.GENERATED_REPORT`, em `backend/ee/onyx/server/reporting/`, pode
continuar identificando artefatos gerados. Isso não autoriza reutilizar o
endpoint admin nem misturar retenção de relatório de uso com relatório TON.

## Permissão, retenção e PII

- Definir quem pode gerar, ver e baixar cada tipo.
- Filtrar métricas pela mesma ACL usada em ocorrências e evidências.
- Não mostrar conteúdo de documento na lista.
- Exibir validade e remover artefato expirado de modo consistente.
- Auditar geração, download e compartilhamento.
- Bloquear download se a permissão mudou após a geração.

## Estados e mobile

Os estados mínimos são `empty`, `loading`, `queued`, `generating`, `ready`,
`failed`, `expired` e `forbidden`. O polling deve parar em pronto, falha,
expiração ou timeout. No mobile, mostrar somente colunas essenciais e mover
ações para menu ou detalhe.

O tema escuro deve usar tokens de
`web/lib/shared/tokens/semantic-dark.json`; não usar `dark:` nem cores
Tailwind built-in. Os controles devem manter foco e labels.

## Limites

- Não expor `/ee/admin/performance/*` como se fosse produto TON.
- Não remover `UsageReports` ou query history existentes.
- Não alterar modelos de uso ou histórico no escopo de adaptação frontend.
- Não chamar relatório de “ocorrência” sem vínculo de domínio explícito.

