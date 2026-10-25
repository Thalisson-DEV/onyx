## 1. Coleta das decisões

- [x] 1.1 Registrar em `plans/ton/` a ata da reunião de 2026-10-03 com as respostas da Luyla (C1–C3, D1–D3, P1–P3, R1–R3, O1–O3, F1–F3)
- [ ] 1.2 Converter cada resposta em tratamento candidato (escopo, efeito, evidência) e confirmar por escrito com a Luyla

## 2. Modelo e aplicação

- [x] 2.1 Tabela append-only de tratamentos com trigger de imutabilidade e auditoria — `ton_closing_treatment` (migração `d7a1e4c9b2f6`), versão por chave, auditoria `ton_financial.closing_treatment` (inclusive recusa por permissão)
- [x] 2.2 Aplicar tratamentos na normalização e registrar as versões usadas no `FinancialNormalizationRun` — `treatment_number` no run e no digest (só quando há tratamento), fato com `treatment_id`/`treatment_effect`/`original_account_id`; decisões pendentes de recálculo contam tratamentos
- [x] 2.3 Proveniência de tratamento nas linhas da DRE (antes/depois, versão, autor) — composição da linha e aba Base do Excel (colunas "Valor no NG" e "Tratamento da Controladoria"); Premissas do Excel vêm dos tratamentos em vigor
- [x] 2.4 Estado "bloqueado por fonte" para tratamentos sem dado — `BLOCKED` com `required_source`; "substituir por fonte" não pode ficar ativo
- [x] 2.5 Testes determinísticos por tipo de efeito (excluir, reclassificar, substituir, bloqueado) — `tests/unit/ton/test_closing_treatments.py`, Excel em `test_dre_xlsx_export.py`

## 3. UI

- [x] 3.1 Administração do TON: lista e registro de tratamentos (com justificativa e confirmação) — `/ton/tratamentos`: tabela, detalhe no clique (justificativa, evidência, histórico), nova versão, revogar, "Atualizar a base"
- [x] 3.2 DRE: indicador por linha tratada + composição antes/depois — marca "Tratado" e "No NG: R$ X · tratamento (vN)" na composição da linha
- [ ] 3.3 Substituir as decisões de teste da 392 por decisão real da Controladoria (nova versão)

## 4. Validação

Validado em 2026-10-05 numa cópia do banco real (`ton_treatments_check`, descartada depois): tratamento
bloqueado de parcelamentos não altera a DRE (abril −90.892.064,91 antes e depois); exclusão de teste
abr–mai em PARCELAMENTOS marca 15 lançamentos, a linha de abril vai a 0 com o valor do NG na
composição, e o Excel passa na conferência com o cálculo persistido.

- [ ] 4.1 Recalcular jan–jun/2026 e comparar com o Banco de Dados/BI linha a linha; registrar diferenças remanescentes com causa
- [ ] 4.2 Validação no Chrome e atualização de `openspec/roadmap.md`

## 5. Acrescentado em 2026-10-23

- [ ] 5.1 Converter os itens das atas da Controladoria de 16/10 e 20/10 (Vale Norte) em tratamentos candidatos e confirmar cada um por escrito
- [ ] 5.2 Ordem de grupos da DRE da ata de 16/10 nas estruturas Caixa e Econômica
- [ ] 5.3 Excluir a contingência de 1% (estrutura e padrão do assistente)
- [ ] 5.4 Apostilamento rateado no faturamento e exibido separado
- [ ] 5.5 Rubrica "aterro" de Mossoró; "Despesas extraordinárias" (acordo de R$ 288 mil em 8x); Fan Card → combustível; centro de custo Consultoria
- [ ] 5.6 Folha: FGTS rescisório, provisão FGTS 40%, rescisões deduzidas das provisões, descontos de funcionários classificados, férias do mês sem duplicar provisão
- [ ] 5.7 Estorno de despesa fora do faturamento; regra para estorno de férias em duplicidade
- [ ] 5.8 Coluna de status "não paga" no modelo e no perfil de parcelamentos pagos; novos credores sem mudar o layout
- [ ] 5.9 Esclarecer com a Luyla: "estrutura igual à de Ferrari" e se Franquias/NC3 entram no TON
