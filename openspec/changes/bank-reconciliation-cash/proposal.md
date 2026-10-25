## Why

O relatório de inconsistências de junho e a reunião Financeiro de 15/06/2026 colocam a conciliação
bancária e o caixa entre os maiores problemas da Vale Norte: divergência banco × NG (NG sem débito,
débito sem NG, intercompany em uma só ponta, data de lançamento × compensação), pagamentos com
documentos iguais em fornecedores distintos, fundo fixo e adiantamentos de viagem sem prestação de
contas, e a proposta de automatizar extratos e remessa CNAB (contexto 03 §4.4–§4.6). A opção F da
priorização ("Fluxo de caixa / conciliação bancária") e a pergunta "o TON faz DFC?" (hoje: não) vêm
daqui. Existe também o relatório "Fluxo de caixa jan–jun/26 contas a pagar/receber" (PDF, não lido).

## What Changes

- Fonte **extrato bancário** (OFX/CNAB/CSV por conta) e, quando disponível, contas a pagar/receber.
- Conciliação determinística banco × NG (valor, data com tolerância aprovada, documento) com os
  quatro tipos de divergência; itens ambíguos ficam para decisão humana.
- Candidatos a pagamento duplicado detectados no extrato → confirmação do gestor → registro de
  devolução/estorno com evidência (fluxo do §4.5 do relatório; o TON não decide).
- Controle de fundo fixo e adiantamentos (adiantamento × prestação; bloqueio sugerido de novo
  adiantamento com prestação aberta, como recomendação).
- DFC gerencial a partir de caixa conciliado (fase posterior desta change).

## Capabilities

### New Capabilities
- `bank-reconciliation`: extratos, conciliação banco × NG, duplicidades de pagamento, fundo fixo e DFC.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novos perfis, motor de conciliação (reaproveitando o padrão de decisão de conciliação existente),
  UI de conciliação, DRE/DFC.

## Dependências

- Extratos detalhados (ação da reunião de 15/06), acesso bancário revisado, tolerâncias aprovadas.
  Prioridade a definir pela Luyla (opção F).

## Estado de dado

Real, quando fornecido.

## Atualização de 2026-10-19 a 2026-10-23

Atas: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-19.md` §5 e `plans/ton/ATA_REUNIAO_LUYLA_2026-10-23.md`.

- Em 19/10 os extratos "Extrato Bancário Analítico" do NG (PDF, jul–set) foram lidos localmente com
  totais conferidos e confrontados com o NG (`TON_Entregas/TON - Conferencia extrato x NG - jul a set
  2026.xlsx`). Achado: a data do NG não é a data do pagamento (salário de julho no NG em 31/07, pago em
  06/08; locação Vamos de maio paga em 14/09); só ~2/3 das saídas casam no mesmo dia.
- Em 23/10 a Luyla explicou que há **dois extratos**: o emitido dentro do NG e o tirado direto no
  banco. O saldo deve bater, mas os lançamentos de cada um nem sempre são iguais. Pasta nova
  "Extratos Bancários - Bancos" com comprovantes (HTML/PDF de 22/10).
- O extrato tem pouca informação: histórico (às vezes com o fornecedor), conta destinatária, data e
  valor. Serve para achar o que foi pago e não lançado no NG, mas não é 100% conclusivo sozinho.
- **DRE de caixa = só o que foi pago** (confirmado em 23/10). A data de pagamento vem do extrato
  conciliado; o Zeev é fonte candidata (`zeev-integration`).
- Ata de 20/10 (Eric): levantar taxas de juros, encargos e custos de antecipação a partir dos extratos
  detalhados dos cartões; registrar no fluxo de caixa os pagamentos de capital de giro feitos pela
  Vale Norte (franquias/NC3).
- Pedido pendente: extrato dos últimos 6 meses direto das contas bancárias e a planilha de caixa
  (Tássio, ata de 20/10), se possível em Excel/OFX em vez de PDF.
