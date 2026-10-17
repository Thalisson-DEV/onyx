## 1. Modelo

- [x] 1.1 Tabela só de acréscimo `ton_record_unit_assignment` (migração aditiva)
- [x] 1.2 Repositório: atribuição vigente por (fonte, chave do registro); atribuir a partir de uma ocorrência NGF-UNIT-MISSING com decisão na mesma transação

## 2. Normalização e API

- [x] 2.1 Normalização usa a unidade atribuída só para lançamento sem unidade no NG; estatística `actual_unit_assigned`
- [x] 2.2 `POST /ton/financial-review/occurrences/{id}/unit-assignment` (MANAGE_TON_OCCURRENCES; unidade ativa e visível)
- [ ] 2.3 Testes: atribuição vigente (versões, desfazer) ✔ em `test_unit_assignment.py`; falta teste automatizado da normalização (validado à mão: vazio usa atribuída, unidade do NG vence)

## 3. UI

- [x] 3.1 Pendências: opção "Atribuir unidade" no caso sem unidade, com seletor de unidades ativas, um caso ou vários
- [x] 3.2 Resultado e histórico mostram a unidade atribuída

## 4. Validação

- [x] 4.1 Dados reais (local): atribuir unidade a casos sem unidade, recalcular e conferir a DRE da unidade e do "Sem unidade no NG"
- [x] 4.2 Reimportar o mesmo export e conferir que as atribuições continuam valendo

## Notas da implementação (2026-10-17)

- Além das Pendências, a aba Classificação → Unidades lista todos os lançamentos sem unidade (pendentes e já aceitos), com atribuição em lote, desfazer ("Sem unidade") e "Recalcular a base".
- Caso já aceito: a atribuição muda só a unidade; a decisão anterior fica. Caso pendente: é decidido junto (exceção justificada, "Unidade atribuída pela Controladoria: X").
- O total de atribuições da fonte entra no digest da normalização, senão o recálculo reaproveitava a base antiga.
- 4.2 validado comparando as chaves nos dois imports do Jan–Set existentes no banco local (o registro 499 é encontrado nos dois).
