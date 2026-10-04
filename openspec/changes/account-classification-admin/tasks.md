## 1. Imediato

- [ ] 1.1 Enviar à Luyla pelo WhatsApp a lista dos 29 códigos com a classificação e o motivo de cada um
- [x] 1.2 Marcar os 29 como "aguardando confirmação" (origem da classificação): a migração
  `b8e1d5c3a7f4` grava a revisão `AWAITING_CONFIRMATION`/`ANALOGY` de cada um

## 2. Backend

- [x] 2.1 Read model da tabela (código, descrição, natureza, grupo DRE, origem, autor, data):
  `GET /api/ton/account-classification`, com lançamentos, total e valor por mês da última normalização
- [x] 2.2 Edição com justificativa como nova versão de mapeamento (`/change`); confirmação sem mudar
  a natureza (`/confirm`); ambas append-only em `ton_account_classification_review`, com auditoria
- [ ] 2.3 Exportação Excel e importação como propostas a confirmar: exportação feita
  (`/export.xlsx`, colunas amarelas Confere?/Natureza correta/Observação); importação pendente
- [ ] 2.4 Detecção de conta nova na importação → classificação pendente: a tabela já lista como
  "Sem classificação" todo código da última normalização sem mapeamento; falta o item no relatório semanal
- [ ] 2.5 Regras de pré-classificação versionadas (prefixo, termo da descrição) que só sugerem
- [x] 2.6 Pré-classificação pelo assistente (decisão do Thalisson em 2026-10-04): o modelo padrão
  recebe as contas confirmadas, o padrão do prefixo e os históricos e devolve natureza, confiança e
  justificativa; a sugestão é gravada em `ton_account_classification_suggestion` e nunca muda a
  classificação sozinha. O padrão do prefixo (contas confirmadas com o mesmo prefixo) é calculado de
  forma determinística e mostrado ao lado

## 3. UI

- [x] 3.1 Tela `/ton/classificacao` (entrada na Administração) com filtros (precisam de atenção,
  aguardando, sem classificação, sugestão diferente, confirmadas), busca e diálogo de revisão
- [ ] 3.2 Tela de regras de pré-classificação

## 4. Validação

- [ ] 4.1 Testes de versão, importação como proposta, conta nova e regra: unitários da origem,
  do padrão do prefixo, do prompt, da leitura da resposta do modelo e do Excel em
  `backend/tests/unit/ton/test_account_classification.py`
- [ ] 4.2 Conferir com a Luyla usando a planilha atual
- [ ] 4.3 Atualizar `openspec/roadmap.md`
