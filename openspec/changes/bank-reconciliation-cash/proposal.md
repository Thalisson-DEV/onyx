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
