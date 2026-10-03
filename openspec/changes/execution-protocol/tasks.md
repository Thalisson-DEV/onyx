## 1. Orquestrador

- [ ] 1.1 Interface `StepExecutor` e registro por passo; estados PASSED / FAILED_CRITICAL / FAILED / SKIPPED_BLOCKED
- [ ] 1.2 Persistência em `AnalysisRun`/`AnalysisStep` com motivos e saídas
- [ ] 1.3 Gate de bloqueio e relatório de base reprovada (S10)

## 2. Passos

- [ ] 2.1 Passo 1: insumos ausentes por base canônica (e calendário PAD-CTRL-001 quando disponível)
- [ ] 2.2 Catálogo determinístico de pontos cegos (§11) avaliável com os dados existentes
- [ ] 2.3 Passo 6: ordenação e teto 7/12 com excedente no ledger (`published = false`)
- [ ] 2.4 Migrar R3 para o orquestrador com teste de equivalência do relatório

## 3. Assistente e UI

- [ ] 3.1 Ferramenta de análise que usa o orquestrador em modo leitura
- [ ] 3.2 Timeline de raciocínio mostra os 7 passos e o bloqueio quando houver

## 4. Validação

- [ ] 4.1 Testes: ordem, bloqueio, insumo ausente, ponto cego, teto
- [ ] 4.2 Rodar sobre jan–jun/2026 real; Chrome
- [ ] 4.3 Atualizar cobertura (S10) e `openspec/roadmap.md`
