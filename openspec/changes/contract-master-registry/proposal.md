## Why

O Prompt Mestre §4 chama o cadastro mestre do contrato de **"o cérebro"**: antes de qualquer análise
financeira de um contrato o TON precisa da sua estrutura econômica; se ela não existir, construí-la é a
primeira tarefa e a análise fica bloqueada, declaradamente. O indicador-mãe da diretoria é margem
contratual prevista × margem real (Mossoró 02/2023: prevista 16,89%). Hoje `ton_contract` tem só
código, unidade, contratante, objeto, vigência e status (o suficiente para S7 e T19); não há valores,
reajustes, aditivos, serviços, dimensionamento, governança, nem vínculo contrato ↔ unidade usado pela
DRE. "Por contrato, ainda não: falta o cadastro de contratos" (FAQ 16 da apresentação).

## What Changes

- Cadastro mestre versionado com os cinco blocos do §4: **Identificação**, **Econômico** (valor
  global, mensal atual/original, índice e data-base de reajuste, reajustes, repactuações, aditivos,
  apostilamentos, saldo, % executado), **Operacional** (serviços com quantitativo e unidade de medida,
  frequência, equipes, dimensionamento de MO e frota, produtividade de referência),
  **Econômico-operacional** (da dotação: custo unitário, BDI, curva ABC, encargos, reserva técnica,
  piso, CCT, margem prevista) e **Governança** (critérios de medição e faturamento, prazo de
  pagamento, penalidades, glosas, SLAs, garantias, seguros, obrigações, fiscal e gestor).
- Eventos contratuais append-only (aditivo, apostilamento, reajuste, repactuação, prorrogação) com
  documento de origem (nível A) — o valor vigente é derivado dos eventos.
- Completude por bloco e **bloqueio declarado**: análise contratual de um contrato sem bloco mínimo
  completo retorna "bloqueada — cadastro mestre incompleto: <campos>".
- Vínculo contrato ↔ unidade administrativa do NG ↔ tomador do faturamento (de/para aprovado).
- Tela **Contratos** (lista, ficha do contrato, completude, documentos, eventos).

## Capabilities

### New Capabilities
- `contract-master`: cadastro mestre do contrato, eventos contratuais, completude e vínculos.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/models.py` (`Contract` + novas tabelas), migrations, novos endpoints, nova
  superfície `web/src/views/ton/ContractsPage`, especialista CONTRATOS passa a ter ferramentas.

## Dependências

- Contratos, editais, aditivos e apostilamentos (PDF) — Luyla/jurídico. Dotações (change
  `dotacao-composition-import`) para o bloco econômico-operacional. Backlog para conferência.

## Estado de dado

Real, carregado por importação/UI com evidência — **nunca** por seed/migration com dados do cliente.

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

Contratos **não são prioridade agora** (D1). A fonte existe: uma planilha Excel de controle de
contratos com links para o contrato e os termos aditivos; a Luyla vai mostrar e explicar na segunda.
Começar pela importação dessa planilha como fonte do bloco Identificação/Econômico.
