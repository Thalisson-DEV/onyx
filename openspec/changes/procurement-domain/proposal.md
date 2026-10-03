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
