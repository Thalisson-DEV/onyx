## Why

Mão de obra é ~38% da composição de custo (Mossoró, §4.1); encargos de jan+fev/2026 ficaram em ~62%
da folha (relatório de junho, como hipótese a investigar — não constante); Mossoró tem 207 garis + 23
feristas + 26 afastados = 256 posições (DP-01) e reserva técnica contratada de 10,04%. O §8 define T27
(quadro × dotação > 5% em cargo da curva A), T28 (afastados + feristas acima da reserva técnica
contratada), T29 (horas extras > 8% da folha por 2 meses) e o §7 T12 (rescisão sem multa de 40% do
FGTS). O POP-CTR-01 diz que folha/FGTS chegam por relatório separado até o dia 05 — e há a decisão
pendente "folha pelo NG ou pela folha (FG)". O especialista **TON RH** está "aguardando fonte".

## What Changes

- Fontes **folha analítica** (matrícula, cargo, salário, verbas, encargos, HE, rescisões),
  **quadro DP-01/DP-02** (situação Normal/Férias/Afastado, admissão, departamento) e **ponto**
  (quando disponível).
- Testes T12, T27, T28, T29.
- Proteção de dados pessoais: mascaramento por padrão, acesso por papel RH/Controladoria, nenhum dado
  pessoal no assistente sem permissão, retenção definida (LGPD).
- Decisão versionada sobre a fonte oficial de folha na DRE (NG × relatório de folha) para não contar
  duas vezes.
- TON RH ativo: quadro × dotação, simulação de dimensionamento.

## Capabilities

### New Capabilities
- `hr-domain`: folha, quadro e ponto; T12, T27–T29; proteção de dados; TON RH.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novos perfis, fatos de pessoal com ACL e mascaramento, testes, especialista RH.

## Dependências

- Relatórios de folha/FGTS/DP (Departamento Pessoal), decisão F3 da Luyla (folha pelo NG ou
  separada), papéis de acesso a dado pessoal (decision-log, decisão aberta nº 4), dotação confirmada.

## Estado de dado

Real, com mascaramento.

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

A Luyla citou hora extra como indicador a monitorar e vai passar outros indicadores de folha a partir
do NG na próxima semana. Há "algum banco de dados" de RH que ela pode passar para começar.

## Atualização de 2026-10-23 (atas da Controladoria de 16/10 e 20/10 + reunião de 23/10)

- **Fontes recebidas:** pasta "Custos Fixos - Adm Central/Folha matriz" com a "Listagem de Folha de
  Pagamento - Analítica" (setembro e outra maior) e a da DELTA (outra empresa do grupo).
- **Especialista de folha** (ata 20/10, não urgente): fazer corretamente a dedução provisão × efetivo
  da folha e das rescisões, para não duplicar na DRE.
- **Monitoramento de horas extras** (ata 20/10): comparar mês a mês por unidade, investigar aumentos
  considerando sazonalidade e eventos locais (festas, romarias, padroeira — ex.: Nossa Senhora das
  Dores), pedir justificativa ao gestor. Liga com o especialista de calendário anual
  (`agentic-assistant` 5.3) e com T29.
- **Perguntas ao DP (ata 20/10):** eventos 0550/0551 (insuficiência de saldo: o saldo da folha não pode
  ficar negativo; desconta no mês seguinte); pensão alimentícia vem no título "Alimentar"; se os
  descontos da folha também estão no contas a pagar do NG (DP não sabe — ver com o Eric); mensalidade
  sindical no relatório a pagar (pendente); folha de férias de setembro de todas as unidades
  (pendente); gratificações de função de Mossoró autorizadas pelo diretor operacional.
- **Consignado × FGTS** (ata 16/10): investigar se os descontos do Crédito do Trabalhador estão
  refletidos na folha e no eSocial.
- **Contas a pagar das unidades:** Mossoró lança folha líquida, INSS, FGTS e IRRF no contas a pagar da
  unidade; proposta de tirar e trazer só do DP/NG (pergunta no documento de padrão).
- **Futuro (plataforma, `platform-ces-foundation`):** no CES o DP tem descontos e terá ponto, sanções
  disciplinares e folha; a Vale Norte paga sistema de ponto (levantamento da Luyla).
