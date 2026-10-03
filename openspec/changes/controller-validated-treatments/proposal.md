## Why

A DRE real jan–jun/2026 do TON depende de escolhas que só a Controladoria pode validar e que hoje
estão implícitas no código ou em decisões de teste: PARCELAMENTOS de R$ 128,9 mi no acumulado (saldo
de acordos tributários lançado inteiro em abril e maio — Prompt Mestre §6.2 "evento não recorrente",
relatório de 15/06/2026 §3.1), tratamento da NF 392 (o TON mantém uma linha e exclui a cópia; a Luyla
zera as duas e usa a nota do faturamento), receita da DRE (NG líquida de retenções × faturamento
bruto com impostos deduzidos), "Movimentos não gerenciais" fora do resultado, mútuos/Chácara como
unidades do resultado, e os 19 sem unidade como "risco aceito". A reunião de 2026-10-03 com a Luyla
é o momento de obter essas decisões; elas precisam virar regras versionadas, aplicadas
deterministicamente e visíveis na DRE — não ajustes manuais.

## What Changes

- Novo registro de **tratamentos de fechamento**: cada tratamento é uma regra versionada com escopo
  (natureza/conta, unidade, período), efeito determinístico (excluir do resultado do período,
  reclassificar para linha X, substituir valor por fonte Y), autor, data, justificativa e evidência
  da decisão (ata/mensagem da Controladoria).
- A normalização aplica os tratamentos vigentes e registra quais versões usou; a DRE mostra, por
  linha, os tratamentos aplicados e o valor antes/depois.
- Tratamentos que exigem dado externo (ex.: "só a parcela paga entra" exige cronograma de parcelas)
  ficam bloqueados até a fonte existir, com a pendência declarada.
- Decisões de teste da preparação são substituídas por decisões reais da Controladoria (novas
  versões; o histórico permanece).

## Capabilities

### New Capabilities
- `closing-treatments`: tratamentos de fechamento validados pela Controladoria, versionados e aplicados na normalização/DRE.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/financial_domain.py` (aplicação), `backend/onyx/ton/dre/engine.py`
  (proveniência), nova tabela de tratamentos, UI DRE (indicador de tratamento) e Administração do TON.

## Dependências

- Respostas da Luyla às perguntas C1–C3, D1–D3, P1–P3, R1–R3 do guia de apresentação
  (`plans/ton/APRESENTACAO_LUYLA_2026-10-02.md` §6). Sem resposta, o tratamento fica como está e
  aparece como "ponto para validação".

## Estado de dado

Real. Cada tratamento validado deve ser comparado com o "Banco de Dados (Vale Norte).xlsm" e o BI.

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

- **Parcelamentos decidido (D2):** a DRE mostra só a parcela efetivamente paga, no mês do pagamento
  (DRE "mista", não competência). Os ~R$ 90,9 mi de abril e ~R$ 38 mi de maio são parcelas futuras de
  parcelamentos cancelados e refeitos que não foram excluídas no NG; a Luyla vai limpar no NG com o
  contador. Primeiro tratamento a implementar: "PARCELAMENTOS entram pela data de pagamento; parcela
  prevista e não paga fica fora do resultado". Pergunta aberta: o NG (export ou banco) identifica
  parcela paga × prevista? Se não, o tratamento fica bloqueado e a correção acontece na limpeza do NG.
- **NF 392 (D5):** confirmada como duplicidade; o tratamento atual (manter uma linha, excluir a cópia,
  pedir correção no NG) está alinhado. Substituir as decisões de teste por uma decisão com
  justificativa da Controladoria.
- **19 sem unidade:** a Controladoria atribui pela cidade do CNPJ do fornecedor; regra candidata em
  `supplier-nature-consistency`. Até lá, ficam em "Sem unidade no NG".
- **Receita (R1), folha (F3), mútuos e fundo fixo:** adiados para a reunião de segunda (2026-10-05).
