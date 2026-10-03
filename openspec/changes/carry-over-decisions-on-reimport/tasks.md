## 1. Modelo

- [x] 1.1 Definir os campos do `evidence_fingerprint` por regra NGF e persistir junto da ocorrência/achado (`ngf-ev-1` no payload do achado; `carry_over.py`)
- [x] 1.2 Adicionar base da decisão (`HUMAN` | `CARRIED_OVER`) e referência à decisão original (migração aditiva `a3c9e51d7f20`)
- [x] 1.3 Adicionar política de entradas (`ACTUAL_ONLY` | `ACTUAL_AND_APPROVED_BUDGET`; `LEGACY_ALL_AVAILABLE` no backfill) ao `FinancialNormalizationRun`

## 2. Revisão

- [x] 2.1 Reaplicar decisões na nova revisão quando identidade + fingerprint coincidem (mesma ocorrência; evidência alterada → `REOPENED`)
- [x] 2.2 Registrar evento "não detectado nesta importação" para achados decididos ausentes (evento de verificação com `not_detected_in_snapshot_id`)
- [x] 2.3 Testes determinísticos: mesmo achado, evidência alterada, achado ausente, achado novo (`test_carry_over.py`, `test_carry_over_rules.py`)
- [x] 2.4 Decisões de conciliação casadas pelo conteúdo do lançamento (fonte, fingerprint, ordinal), não pelo id

## 3. Importação e UI

- [x] 3.1 Endpoint de prévia de reimportação (`POST /ton/data-sources/{key}/imports/preview`, sem persistir)
- [x] 3.2 UI de Fontes: prévia antes de confirmar (NG); trilha mostra decisões de revisão e "decisões reaproveitadas na reimportação"
- [x] 3.3 Normalização respeita a política de entradas; importar dotação não altera a DRE

## 4. Validação

- [x] 4.1 Reimportação real do NG (com backup): prévia e revisão com 23 decisões mantidas, 1 pendente (392, correção pedida), 0 novas, 0 reabertas; política `ACTUAL_ONLY`, sem dotações. Ver nota abaixo.
- [x] 4.2 Validação no Chrome: Fontes → Atualizar dados (NG) → "Ver o que muda" com o arquivo original de 02/10: 6.307 lidos, 4 rejeitados, 23 mantidas, 1 pendente, 0 novas/reabertas/não detectadas; cancelado sem importar (nada gravado)
- [ ] 4.3 Atualizar `specs/source-ingestion` ao arquivar a change

### Nota da validação real (2026-10-03)

O arquivo local `plans/ton/DRE Jun-26/Completo - Jan-Jun 2026 - Lançamentos Financeiros.xlsx` é **outra
versão** do export (6.306 lançamentos; ~20 diferentes em abril e junho, abas "Abr ok"/"Jun ok") que a
importada em 2026-10-02 (6.307, checksum `b8eb3ebe…`). A reimportação foi feita com ele; depois, a pedido do usuário, o banco foi
restaurado do backup e migrado de novo, e a base voltou à versão original. Backup anterior: `onyx_backups/pre_carry_over_2026-10-03.dump`; arquivo
original recuperado: `onyx_backups/ng_original_2026-10-02.xlsx`.

As 2 decisões de conciliação "eventos distintos" (392) não se aplicaram, corretamente: a regra NGF-DUP-DOC
(correção pedida) agora tira a cópia da 392 da base e a nota casa sozinha (`MATCHED`); a decisão era
sobre um lado de um casamento ambíguo que deixou de existir.
