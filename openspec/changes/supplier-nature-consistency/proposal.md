## Why

Na reunião de 2026-10-03 (ata, pedido 5) a Luyla deu o exemplo: quando o financeiro lança combustível
com a natureza "despesas extras", a empresa **perde o crédito de PIS/COFINS**; hoje o contador revisa
item por item, o que demora (o PIS/COFINS de julho só chegou no fim de setembro). Ela quer que o TON
use o **CNPJ do fornecedor** para ver, por exemplo, que é um posto de combustível e que a natureza
está errada, e também compare o valor com o histórico do mesmo fornecedor na unidade. As sugestões
de correção passam por aprovação humana (ata D4). É também o T8 do PAD-CTRL-001 (fornecedor × unidade)
e a mesma informação usada para atribuir unidade aos lançamentos sem unidade (cidade do CNPJ).

## What Changes

- **Cadastro de fornecedores** a partir do NG (CNPJ, razão social, cidade/UF) e, quando aprovado,
  atividade econômica (CNAE) de fonte oficial.
- **Regra natureza × atividade do fornecedor** definida pela Controladoria (ex.: CNAE de comércio de
  combustível → natureza COMBUSTÍVEL); lançamento divergente vira sugestão "natureza provável X —
  crédito de PIS/COFINS possivelmente perdido" com evidência.
- **Valor atípico por fornecedor/unidade** contra o histórico (só com histórico suficiente).
- **Sugestão de unidade** para lançamentos sem unidade pela cidade do CNPJ, como a Controladoria faz
  hoje à mão, sempre como sugestão.
- Cada sugestão é **aprovada ou rejeitada** por uma pessoa; a aprovação vira reclassificação no TON
  e item no relatório semanal para correção no NG. Aprovações recorrentes podem virar regra
  (decisão da Controladoria), nunca aprendizado automático silencioso.

## Capabilities

### New Capabilities
- `supplier-nature-consistency`: fornecedores, regra natureza × atividade, valor atípico e sugestão de unidade, com aprovação humana.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Parser/consulta do NG (campos de fornecedor), novo cadastro de fornecedores, regras, fila de
  aprovação, relatório semanal, quantificação do crédito perdido (com a planilha de PIS/COFINS).

## Dependências

- **CNPJ do fornecedor no NG** — o export atual não traz; vem com a integração por VPN
  (`ng-direct-integration`). Tabela atividade → natureza aprovada pela Controladoria. Fonte oficial
  de CNAE (consulta pública de CNPJ) a aprovar.

## Estado de dado

Real, após a integração com o NG.
