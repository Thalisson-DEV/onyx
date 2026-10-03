## Context

`ZeevClient` já impõe a allowlist somente leitura, autenticação, retry e paginação; `ZeevCatalogService`
lista fluxos, campos e desenho de tarefas e gera candidatos por palavra-chave. BE-004B deixou explícito
o que falta (seção "Boundary to BE-004C"): escolher fluxos/recursos, provar estabilidade de IDs entre
importações, decidir backfill e validar que filtros de data (`startDateTime`, `endDateTime`,
`lastFinishedTaskDateTime`) capturam todas as mudanças de instâncias ativas e valores de formulário.

## Goals / Non-Goals

**Goals:** snapshots imutáveis e reprocessáveis; escopo explícito; sincronização incremental validada;
fatos de processo tipados por fluxo; uso em regras determinísticas.

**Non-Goals:** escrever no Zeev (nunca); baixar anexos sem rota autorizada; usar SLA do Zeev como regra
financeira (o catálogo NGF já diz "Zeev SLA rules stay outside" do motor financeiro — SLA vira
indicador de processo).

## Decisions

- **Snapshot por (fluxo, janela)**: JSONL canônico ordenado por instance ID + hash, com valores de
  formulário e tarefas; dados pessoais pseudonimizados no snapshot (ID estável, nome/e-mail fora) e
  resolução para nome só na apresentação para quem tem permissão.
- **Incremental com rede de segurança**: janela por `lastFinishedTaskDateTime` + re-leitura periódica
  das instâncias ativas por ID (para capturar edições de formulário sem tarefa concluída); a validação
  inicial compara um backfill completo de um período com a soma das janelas incrementais.
- **Perfil por fluxo e versão do fluxo** (`flowId` + `flowVersion`): mapeamento campo → fato aprovado
  por humano (tela de mapeamento a partir do catálogo); mudança de versão do fluxo exige revisão do
  mapeamento.
- **Identidade externa**: `flowId` numérico e `instanceId` numérico, UID como metadado (BE-004B).
- **Fatos de processo** genéricos (`ProcessInstanceFact`, `ProcessTaskFact`) + fatos específicos
  onde há regra consumidora (ex.: `PaymentApprovalFact` para os fluxos de liberação financeira).

## Risks / Trade-offs

- [Filtros de data não capturam edição de formulário] → re-leitura de ativas + validação de backfill.
- [Variantes de fluxo (108/148/150/130/154) duplicam pedidos] → escopo decidido pela Luyla; regra de
  deduplicação por NF/fornecedor/valor entre variantes só após confirmação.
- [Conta atual tem direito de escrita] → firewall já existe; para produção pedir credencial dedicada
  somente leitura.

## Open Questions

- As 8 perguntas do catálogo; janela histórica de backfill; quem é o dono de cada fluxo.
