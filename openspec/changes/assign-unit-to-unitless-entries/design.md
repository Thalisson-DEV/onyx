## Contexto

O lançamento do NG vira fato realizado na normalização. A unidade do fato vem de um mapeamento por
texto da coluna "unidade administrativa"; o texto vazio é mapeado para "SEM-UNIDADE". Não há como
mapear um lançamento específico, porque todos os vazios têm o mesmo texto.

O id do registro (`ParsedSourceRecord.id`) muda a cada importação. A revisão já tem uma identidade
estável por conteúdo: `record_keys(records, frozenset())` produz `review_key = rec:<sha256 do conteúdo>#<ordinal>`,
sem aba nem linha. É a mesma usada para reaproveitar decisões na reimportação.

## Decisões

1. **Chave**: `review_key` com nada excluído. O conteúdo inclui a unidade vazia, então quando o NG
   passar a trazer a unidade a chave muda e a atribuição para de valer. Isso é desejado: a fonte
   corrigida vence.
2. **Tabela só de acréscimo** `ton_record_unit_assignment` (source_id, record_key, unit_id nulo = desfeita,
   reason, occurrence_id, created_by, created_at). A atribuição vigente é a linha mais recente por
   (source_id, record_key).
3. **Normalização**: só quando o lançamento não tem unidade no NG (texto vazio). Calcula as chaves do
   export uma vez (`load_review_inputs` + `record_keys`) e só se houver atribuições para a fonte.
   Conta `actual_unit_assigned` nas estatísticas.
4. **Decisão do caso**: atribuir grava as linhas e registra `JUSTIFY_EXCEPTION`
   (`BUSINESS_EXCEPTION`, motivo "Unidade atribuída pela Controladoria: X") em cada ocorrência,
   na mesma transação. O caso sai da fila; o carry-over existente leva a decisão para a próxima
   revisão e a atribuição continua valendo pela chave.
5. **Permissão**: `MANAGE_TON_OCCURRENCES`, a mesma das decisões de revisão; a unidade precisa ser
   visível ao usuário e ativa.

## Fora de escopo

- Atribuir unidade a lançamento que já tem unidade no NG (isso é reclassificação, não lacuna).
- Escrever de volta no NG.
