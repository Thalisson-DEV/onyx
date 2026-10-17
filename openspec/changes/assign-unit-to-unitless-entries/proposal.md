## Why

Na reunião de 2026-10-17 a Controladoria encontrou 29 lançamentos do NG sem unidade administrativa
(ex.: adesivos comprados por João na Boboussa para a reforma da sala da Vale Norte matriz, em janeiro).
Ela sabe a unidade certa, mas o TON só deixava "aceitar com justificativa" ou "tirar da DRE até corrigir
no NG". Aceitando, o lançamento cai no grupo "Sem unidade no NG" e some da DRE da unidade a que
pertence; tirando, some da DRE inteira. Os dois distorcem a DRE por unidade, que é a forma como a
diretoria e os gestores olham o resultado. Juazeiro e Petrolina começaram em abril e vão gerar mais
casos ("compra aqui, mas leva para Mossoró").

## What Changes

- A Controladoria passa a **atribuir a unidade** a um lançamento sem unidade, direto na pendência
  "Lançamento sem unidade administrativa" (um caso ou vários de uma vez).
- A atribuição fica guardada pela **identidade do lançamento** (a mesma chave de conteúdo do
  carry-over: conta, data, documento, histórico, valores e ordinal, sem aba nem linha). Reimportar o NG
  reaproveita a atribuição; se o Financeiro corrigir a unidade no NG, a chave muda e a atribuição deixa
  de valer sozinha, porque o NG passou a dizer a unidade.
- A normalização usa a unidade atribuída quando o lançamento não tem unidade no NG. A atribuição nunca
  sobrepõe uma unidade que veio do NG.
- Atribuir também registra a decisão do caso na revisão ("Unidade atribuída pela Controladoria: X"),
  então a pendência sai da fila e o histórico mostra quem atribuiu, quando e por quê.
- A atribuição é versionada e só acrescenta: trocar ou desfazer cria uma nova linha; nada é apagado.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `financial-readiness`: unidade atribuída pela Controladoria entra na normalização.
- `ng-financial-review`: nova decisão "atribuir unidade" no caso NGF-UNIT-MISSING.

## Impact

- Nova tabela `ton_record_unit_assignment` (migração aditiva).
- `backend/onyx/db/ton/unit_assignment.py` (novo), `backend/onyx/db/ton/financial_domain.py`
  (normalização), `backend/onyx/server/ton/financial_review.py` (endpoint).
- Pendências (diálogo de decisão) no frontend.

## Dependências

Nenhuma externa. A correção definitiva continua sendo lançar a unidade no NG; o TON só evita que a DRE
por unidade fique errada enquanto isso.

## Estado de dado

Real: 29 casos no export jan–set/2026 (homolog de 2026-10-17).
