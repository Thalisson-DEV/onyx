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

## Atualização de 2026-10-16 a 2026-10-23

Atas da Controladoria de 16/10 e 20/10 (Drive) e `plans/ton/ATA_REUNIAO_LUYLA_2026-10-23.md`.

- A planilha chegou: `Cópia de PIS COFINS - Apuracao.xlsx` na pasta compartilhada (21/10). Ler o
  layout e criar o perfil a partir dela.
- Em 23/10 a Luyla repetiu que a apuração é **crucial para fechar a DRE**. O sistema que o Eric
  desenvolve também faz essa apuração: conferir na reunião com ele se ele pode ser a fonte.
- Regras da Controladoria (atas de 16/10 e 20/10):
  - apresentar **PIS e COFINS efetivos** e seus créditos/diferenças conforme cada relatório;
  - na DRE econômica, apresentar os tributos **sem deduzir as retenções** do faturamento;
  - usar a **alíquota efetiva do mês anterior** nos cálculos tributários;
  - os fornecedores Posto Buca, Zona Norte, Qualiservice e Conqservice geram crédito de PIS/COFINS,
    mas o que se comprou pode não corresponder à natureza usada (combustível, fardamento, saco de
    cal): revisar (liga com `supplier-nature-consistency`).
- O assistente hoje sugere PIS 1% e COFINS 4,6% fixos sobre o bruto (macro da NF); com a apuração
  importada, o percentual efetivo do mês substitui o fixo.
