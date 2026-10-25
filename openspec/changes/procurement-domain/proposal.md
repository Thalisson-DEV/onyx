## Why

O relatório de junho cita despesas jurídicas/engenharia que saltaram de ~R$ 72,5 mil para ~R$ 473,8 mil
em jan+fev/2026 com um item de ~R$ 323,7 mil de consultoria em Itabirito sem fornecedor identificável,
pagamentos com documentos iguais em fornecedores distintos, e locações de ~R$ 5,4 mi sem relatório
consolidado (contexto 03 §3.4, §4.3, §4.5). O Prompt Mestre §8 define **T30** (preço do item > 15% da
mediana dos últimos 12 meses; compra emergencial recorrente do mesmo item = falha de processo) e o §7
**T8** (CNPJ/endereço do fornecedor incompatível com a unidade). O especialista **TON PROCUREMENT**
está "aguardando fonte".

## What Changes

- Fonte **compras** (item, quantidade, preço unitário, fornecedor com CNPJ, unidade, data, tipo —
  regular/emergencial, contrato de locação quando houver).
- Cadastro de fornecedores (CNPJ, endereço) com identidade obrigatória: lançamento sem fornecedor
  identificável vira achado de confiança (não "custo normal").
- Testes T30 e T8; fragmentação de compras; locações por veículo/competência/unidade.
- TON PROCUREMENT ativo: benchmark de preço e oportunidades de escala.

## Capabilities

### New Capabilities
- `procurement-domain`: compras, fornecedores, T30, T8, locações e TON PROCUREMENT.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novos perfis e fatos, testes, especialista PROCUREMENT.

## Dependências

- Fonte de compras/contas a pagar com fornecedor (NG? outro sistema?), relatório de locações,
  `history-2025-baseline` (mediana de 12 meses).

## Estado de dado

Real, quando fornecido.

## Atualização de 2026-10-23

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-23.md`.

- **Locações** passam a nascer dos contratos de locação do `fleet-fuel-domain` (cadastro, eventos,
  confirmação mensal, rateio por dias). Aqui fica só a consolidação para compras e a busca de
  duplicidade.
- **Cadastro de fornecedores** passa a ser compartilhado com `unit-payables-intake` e
  `fleet-fuel-domain`: CPF/CNPJ como chave, nome do dia a dia, tipo (empresa, pessoa física,
  funcionário, órgão público), dados de pagamento sempre no nome do próprio favorecido.
- Exemplo real (Itabirito, contas a pagar de setembro): "ITA CHAVES SERVICOS E COMERCIO LTDA" com CNPJ
  e "ITA FERRAMENTAS" sem CNPJ na mesma planilha; não dá para saber se é a mesma empresa.
- A fonte de compras com fornecedor passa a ser, em parte, o próprio contas a pagar das unidades
  (descrição do item, destino e placa por título), além do NG.
- Almoxarifado/estoque (a Luyla citou as empresas de construção civil do grupo) fica como módulo
  candidato em `platform-ces-foundation`; T30 ganha precisão quando houver item e quantidade por compra.
