## Why

As três dotações reais contêm muito mais que o orçado: composições de custo por serviço, curva ABC,
BDI, encargos sociais, reserva técnica de mão de obra, salários da categoria, dimensionamento de mão
de obra e frota (operacional e administrativa), ferramental, preços de referência, custo-hora de cada
veículo, cronograma e, em Mossoró, o quadro DP-01/DP-02 e a síntese de custos. O parser atual lê só a
aba `DOTAÇÃO` (colunas A–D, 45 fatos). Essa é a fonte do bloco **econômico-operacional** do cadastro
mestre (§4) e da **margem contratual prevista** (§4.1: Mossoró 16,89% = orçamento contratante
R$ 4.525.843,89/mês × orçamento Vale Norte R$ 3.761.365,15/mês), e o custo unitário de referência
preferido do §9. Sem ela não existem T24 (frota licitada × real), T25 (produtividade), T27 (quadro ×
dotação) nem T28 (reserva técnica).

## What Changes

- Perfis de leitura **por estrutura de workbook** (as três têm layouts diferentes: Mossoró com abas por
  serviço "1.1 COLETA"…; Juazeiro-BA com abas numeradas e "SINTESE DOS CUSTOS"; Itabirito com "PPU",
  "Composições") que extraem: síntese de custos e preço por serviço, curva ABC, BDI, encargos %,
  reserva técnica %, piso/salários da categoria, dimensionamento de MO por cargo, frota por tipo,
  custo-hora por veículo, quantitativos e unidade de medida por serviço, orçamento do contratante.
- Extração revisável: cada valor extraído com aba/célula de origem; a Controladoria confirma a versão
  extraída antes de ela alimentar o cadastro mestre.
- Cálculo da margem contratual prevista a partir de orçamento do contratante × orçamento Vale Norte.
- Diagnóstico quando uma aba esperada não existe ou muda de layout (nunca adivinhar célula).

## Capabilities

### New Capabilities
- `dotacao-composition`: leitura completa das dotações e alimentação do bloco econômico-operacional.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/ton/operational_import/parser.py` (novos perfis), novo modelo de composição de
  dotação ligado ao contrato, revisão/confirmação na UI de Contratos.

## Dependências

- `contract-master-registry`. Confirmação da Luyla/João Hebert (mantenedor das dotações) sobre quais
  abas são oficiais. Identidade de dotação declarada (change `stabilize-real-data-runtime`).

## Estado de dado

Real (três workbooks em `plans/ton/DRE Jun-26/`, fora do Git).
