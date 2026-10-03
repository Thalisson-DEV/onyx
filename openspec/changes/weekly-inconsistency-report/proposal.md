## Why

Na reunião de 2026-10-03 (ata D3) a Luyla pediu que o TON mande **toda semana, por e-mail, ao
Financeiro** o relatório de inconsistências que hoje a Controladoria monta à mão, e que **confira
sozinho, na extração seguinte, se o Financeiro corrigiu no NG**. O processo atual é: Controladoria
filtra → envia ao Financeiro → Financeiro corrige no NG → Controladoria reextrai tudo e confere; uma
correção retroativa obriga a refazer os meses seguintes, e um erro esquecido "volta" quando todos os
meses são recarregados. Esta change é a primeira fatia, pedida pelo cliente, de três capacidades do
roadmap: rotinas com destinatário (`routine-framework`), verificação no ciclo seguinte
(`action-verification`) e ledger com dono (`occurrence-ledger-workflow`). O resto delas continua
nas changes originais.

## What Changes

- **Relatório semanal de inconsistências** (padrão: uma vez por semana, como a Luyla pediu): lista as
  inconsistências abertas do NG com evidência (planilha/linha ou registro do banco, conta, unidade,
  documento, valor), o que precisa ser corrigido no NG e há quantas semanas está aberta.
- **Envio por e-mail** ao Financeiro e cópia para a Controladoria; também visível no TON.
- **Administração**: regras incluídas (começa com as já existentes: duplicidade de documento,
  lançamento sem unidade, linha rejeitada), frequência (semanal por padrão, ajustável), destinatários.
- **Verificação a cada nova extração**: cada inconsistência é marcada como corrigida no NG, ainda
  aberta ou reaparecida (correção retroativa desfeita), por mês de competência.
- O TON **não corrige o NG**: só detecta, avisa e verifica.

## Capabilities

### New Capabilities
- `inconsistency-report`: relatório periódico de inconsistências do NG por e-mail, com configuração e verificação de correção.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Rotina agendada (Celery Beat), envio de e-mail (SMTP), Administração do TON, read model sobre
  ocorrências da revisão NG; usa o evento "não detectado nesta importação" de
  `carry-over-decisions-on-reimport`.

## Dependências

- SMTP do ambiente; e-mails do Financeiro (Luyla). A verificação ganha precisão real com a extração
  automática do NG (`ng-direct-integration`); com importação manual, verifica a cada upload.

## Estado de dado

Real.
