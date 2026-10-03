## Why

Em 2026-10-02 a Luyla pediu que a DRE seja entregue em **Excel, não em Power BI**, porque o Excel
mantém a memória de cálculo e é fácil de personalizar; o contador da empresa pode ajudar a definir
o formato. Hoje o TON só exporta CSV (valores soltos, sem fórmulas nem origem). Uma planilha com
fórmulas vivas que apontam para a base de lançamentos é o formato que a Controladoria consegue
auditar e reaproveitar — e é o caminho natural para substituir o "Banco de Dados (Vale Norte).xlsm"
+ Power BI no processo do POP-CTR-01.

## What Changes

- Exportação `.xlsx` da DRE por período e escopo (consolidado ou unidade), mensal e acumulado.
- Aba **DRE** com fórmulas (SUMIFS/referências) sobre a aba **Base**, não valores colados.
- Aba **Base** com cada fato contribuinte: natureza, conta NG, unidade, competência, documento,
  histórico, valor, arquivo/planilha/linha de origem, disposição da revisão.
- Abas **Tratamentos e decisões** (versões usadas, autor, data, justificativa) e **Pendências**
  (bloqueios e pontos para validação, se houver).
- Cabeçalho com base de cálculo, data de importação, versão da estrutura e aviso quando a base não
  está pronta (nesse caso, a exportação sai marcada "não oficial" ou é bloqueada — ver spec).
- Totais da planilha recalculados devem bater ao centavo com o cálculo persistido.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `dre-engine`: nova exportação XLSX com memória de cálculo.

## Impact

- `backend/onyx/server/ton/dre.py` (novo endpoint), novo módulo de exportação (openpyxl),
  `web/src/views/ton/DrePage` (botão "Baixar Excel").

## Dependências

- Layout final a validar com a Luyla e o contador (ordem de linhas, colunas mensais, formatação).
  A primeira versão usa a estrutura `vale-norte-gerencial` atual.

## Estado de dado

Real (DRE jan–jun/2026). Nenhum arquivo exportado com dado real entra no Git.

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

A Luyla pediu para ver a DRE no Excel e poder montar à mão linhas extras, outro centro de custo e
cálculos próprios puxando os dados do TON (ata, pedido 1). Isso confirma a abordagem de aba Base +
fórmulas: ela pode acrescentar linhas e fórmulas próprias sobre a Base. Também pediu exportar os
lançamentos do NG em Excel, já corrigidos (pedido 3): incluir uma exportação da Base filtrada sem a
DRE. Ela vai comparar a DRE do TON com o Power BI na segunda/terça.
