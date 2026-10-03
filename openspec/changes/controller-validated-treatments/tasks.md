## 1. Coleta das decisões

- [x] 1.1 Registrar em `plans/ton/` a ata da reunião de 2026-10-03 com as respostas da Luyla (C1–C3, D1–D3, P1–P3, R1–R3, O1–O3, F1–F3)
- [ ] 1.2 Converter cada resposta em tratamento candidato (escopo, efeito, evidência) e confirmar por escrito com a Luyla

## 2. Modelo e aplicação

- [ ] 2.1 Tabela append-only de tratamentos com trigger de imutabilidade e auditoria
- [ ] 2.2 Aplicar tratamentos na normalização e registrar as versões usadas no `FinancialNormalizationRun`
- [ ] 2.3 Proveniência de tratamento nas linhas da DRE (antes/depois, versão, autor)
- [ ] 2.4 Estado "bloqueado por fonte" para tratamentos sem dado
- [ ] 2.5 Testes determinísticos por tipo de efeito (excluir, reclassificar, substituir, bloqueado)

## 3. UI

- [ ] 3.1 Administração do TON: lista e registro de tratamentos (com justificativa e confirmação)
- [ ] 3.2 DRE: indicador por linha tratada + composição antes/depois
- [ ] 3.3 Substituir as decisões de teste da 392 por decisão real da Controladoria (nova versão)

## 4. Validação

- [ ] 4.1 Recalcular jan–jun/2026 e comparar com o Banco de Dados/BI linha a linha; registrar diferenças remanescentes com causa
- [ ] 4.2 Validação no Chrome e atualização de `openspec/roadmap.md`
