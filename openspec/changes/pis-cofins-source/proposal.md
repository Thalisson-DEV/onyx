## Why

A linha "Impostos s/ faturamento" da DRE do TON está zerada, mas a apuração de PIS/COFINS da
Contabilidade (posição 07/08/2026) mostra R$ 3.862.987,69 a recolher em jan–jun/2026, sobre receita
base de R$ 65,91 mi — contra R$ 59,03 mi de receita líquida na DRE do TON. Pelo POP-CTR-01 o PIS/COFINS
chega da Contabilidade até o dia 05 e entra na DRE gerencial. O Prompt Mestre §3.2 lista PIS e COFINS
no grupo IMPOSTOS S/FATURAMENTO. Sem essa fonte a DRE do TON fica sistematicamente diferente da DRE
da Controladoria.

## What Changes

- Nova fonte "Apuração PIS/COFINS (Contabilidade)" com perfil determinístico de leitura por
  competência: receita base, PIS e COFINS a recolher (e créditos, se o arquivo trouxer).
- Fatos canônicos de imposto por competência mapeados para a linha "Impostos s/ faturamento" por
  decisão versionada (não por suposição).
- Conferência: receita base da apuração × receita da DRE por competência, com a diferença exposta
  como item de conciliação (hipótese de retenções/competência, nunca afirmação).
- Rateio por unidade **somente** se a apuração vier por filial/unidade ou se a Controladoria aprovar
  uma regra de rateio; caso contrário, o imposto fica no consolidado com a ressalva.

## Capabilities

### New Capabilities
- `pis-cofins-source`: importação e uso da apuração de PIS/COFINS na DRE.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novo perfil em `backend/onyx/ton/operational_import`, domínio financeiro (novo tipo de fato),
  estrutura de DRE (atribuição da linha), Fontes UI.

## Dependências

- Pergunta R3 (em que linha entra) e formato estruturado: pedir à Contabilidade a apuração em XLSX/CSV.
  Parsing de PDF só se não houver alternativa, com validação de totais.

## Estado de dado

Real (apuração 2026). O PDF atual fica em `plans/ton/DRE Jun-26/` (fora do Git).

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

- A fonte certa é a **planilha Excel de cálculo de PIS/COFINS** da Luyla (com as fórmulas), não o PDF
  do contador; ela vai enviar o link.
- O contador demora (julho chegou no fim de setembro); a DRE de jul/ago depende desse percentual.
- Pedido futuro: o TON calcular o PIS/COFINS automaticamente a partir do NG e da planilha de regras.
  Fica como fase posterior desta change, depois de a importação estar validada.
