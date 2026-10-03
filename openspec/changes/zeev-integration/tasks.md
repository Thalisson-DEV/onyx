## 1. Escopo (com a Luyla)

- [ ] 1.1 Levar as 8 perguntas de `plans/ton/integrations/zeev-source-catalog.md` e registrar as respostas
- [ ] 1.2 Configuração versionada de escopo (vigente / histórico / excluído por flow ID)
- [ ] 1.3 Pedir credencial de serviço dedicada (preferência somente leitura) para produção

## 2. Sincronização

- [ ] 2.1 Fonte "Zeev" no pipeline; snapshot canônico por (fluxo, janela) com pseudonimização
- [ ] 2.2 Checkpoint incremental por data + re-leitura de instâncias ativas
- [ ] 2.3 Backfill de um período fechado e validação backfill × incrementais
- [ ] 2.4 Tarefa Celery agendada com limites de taxa (429), retries e estados de falha

## 3. Fatos e mapeamento

- [ ] 3.1 Tela de mapeamento campo → fato por fluxo/versão a partir do catálogo (aprovação humana)
- [ ] 3.2 Fatos genéricos de instância/tarefa (tempo de ciclo, SLA, resultado)
- [ ] 3.3 `PaymentApprovalFact` para os fluxos de liberação financeira em escopo
- [ ] 3.4 Referências de documento (contrato assinado, certidões) disponíveis para cadastro mestre e compliance

## 4. Uso nas regras e no produto

- [ ] 4.1 Executor de `NGF-XS-APPROVAL-MISSING` (pagamento NG × liberação aprovada) — pode ser entregue junto da `financial-test-battery`
- [ ] 4.2 Ponto cego "processo sem rastreabilidade" no protocolo de execução
- [ ] 4.3 Indicadores de SLA/tempo de ciclo da Controladoria (sem regra financeira)
- [ ] 4.4 Fontes UI: escopo, última sincronização, falhas, validação
- [ ] 4.5 Ferramenta de leitura de processos para o assistente (sem dado pessoal sem permissão)

## 5. Validação

- [ ] 5.1 Testes com transporte local (firewall, janelas, re-leitura, pseudonimização)
- [ ] 5.2 Smoke real: zero mutações; contagens por fluxo conferidas com o Zeev
- [ ] 5.3 Atualizar cobertura (`SOURCE_ZEEV`), `specs/zeev-adapter` ao arquivar, contexto 08 e `openspec/roadmap.md`
