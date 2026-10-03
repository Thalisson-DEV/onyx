## 1. Modelo

- [ ] 1.1 Definir os campos do `evidence_fingerprint` por regra NGF e persistir junto da ocorrência/achado
- [ ] 1.2 Adicionar base da decisão (`HUMAN` | `CARRIED_OVER`) e referência à decisão original (migração aditiva)
- [ ] 1.3 Adicionar política de entradas (`ACTUAL_ONLY` | `ACTUAL_AND_APPROVED_BUDGET`) ao `FinancialNormalizationRun`

## 2. Revisão

- [ ] 2.1 Reaplicar decisões na nova revisão quando identidade + fingerprint coincidem
- [ ] 2.2 Registrar evento "não detectado nesta importação" para achados decididos ausentes
- [ ] 2.3 Testes determinísticos: mesmo achado, evidência alterada, achado ausente, achado novo

## 3. Importação e UI

- [ ] 3.1 Endpoint de prévia de reimportação (reaproveitadas / reabertas / novas)
- [ ] 3.2 UI de Fontes: prévia antes de confirmar; trilha distingue decisão de sistema
- [ ] 3.3 Normalização respeita a política de entradas; importar dotação não altera a DRE

## 4. Validação

- [ ] 4.1 Backup e reimportação real do NG jan–jun/2026; conferir que 392 e os 19 sem unidade não reabrem e a DRE continua READY
- [ ] 4.2 Validação no Chrome (Fontes → prévia → Pendências → trilha)
- [ ] 4.3 Atualizar `openspec/roadmap.md` e `specs/source-ingestion` (remover a limitação de reimportação ao arquivar)
