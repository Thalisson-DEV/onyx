## Why

Na reunião de 2026-10-03 (ata D3) a Luyla pediu que o TON mande **toda semana, por e-mail, ao
Financeiro** o relatório de inconsistências que hoje a Controladoria monta à mão, e que **confira
sozinho, na extração seguinte, se o Financeiro corrigiu no NG**. O processo atual é: Controladoria
filtra → envia ao Financeiro → Financeiro corrige no NG → Controladoria reextrai tudo e confere; uma
correção retroativa obriga a refazer os meses seguintes, e um erro esquecido "volta" quando todos os
meses são recarregados.

Em 2026-10-05 o Thalisson ampliou o pedido: em vez de um relatório fixo no código, o TON deve ter
**fluxos de e-mail** no estilo do Power Automate ("aconteceu tal coisa? sim → faz isso, não → faz
aquilo"), que a própria Controladoria (Luyla, sem perfil técnico) cadastra. O TON também **propõe
fluxos prontos**, e o usuário só diz se quer cadastrar, sempre com aprovação humana. O relatório
semanal de inconsistências passa a ser o **primeiro fluxo, o padrão**.

Esta change é a primeira fatia, pedida pelo cliente, de três capacidades do roadmap: rotinas com
destinatário (`routine-framework`), verificação no ciclo seguinte (`action-verification`) e ledger com
dono (`occurrence-ledger-workflow`). O motor de fluxos é construído para ser o mesmo motor de
agendamento, execução idempotente e entrega que o `routine-framework` usará para R1–R9 (sem dois
motores).

## What Changes

- **Fluxo de e-mail** = gatilho → condição → ação no "sim" / ação no "não" (opcional). Um nível de
  sim/não no v1; sem árvore livre nem ramos criados à mão.
- **Gatilhos de um catálogo fechado**: agendamento (semanal/diário), importação do NG concluída,
  ocorrência nova/corrigida/reaparecida na revisão NG, conta nova sem classificação, DRE recalculada.
- **Condições** com filtros simples sobre os campos do evento (regra NGF, unidade, valor acima de
  R$ X, há itens, semanas em aberto ≥ N); sem condição = sempre "sim".
- **Ações**: enviar e-mail (Para, Cc, Cco, assunto, modelo; uma única mensagem por execução com todos os destinatários) ou não fazer nada. Modelos
  determinísticos em português, legíveis no celular; o conteúdo e os números vêm dos read models,
  nunca escritos pelo LLM.
- **Sugestões do TON**: o assistente gera a definição do fluxo (gatilho, condição, destinatários
  sugeridos, motivo); ela fica como "Sugerido pelo TON" com Cadastrar/Descartar e só vale depois da
  confirmação humana (mesmo padrão da pré-classificação em `/ton/classificacao`).
- **Fluxo padrão "Inconsistências da semana"**: lista as inconsistências abertas do NG com evidência
  (planilha/linha ou registro, conta, unidade, documento, valor), o que corrigir no NG e há quantas
  semanas está aberta; vem pré-cadastrado como sugestão, aguardando destinatários.
- **Verificação a cada nova extração**: cada inconsistência é marcada como corrigida no NG, ainda
  aberta ou reaparecida, por competência, a partir do evento "não detectado nesta importação" do
  carry-over.
- **Execução segura**: execuções idempotentes, histórico de envios e falhas, auditoria de toda
  alteração, prévia do e-mail e "enviar só para mim". Sem provedor de e-mail configurado (Resend ou SMTP, por variável de ambiente), a prévia e o histórico
  funcionam e o envio fica registrado como "e-mail não configurado".
- **Telas** `/ton/fluxos`: tabela simples dos fluxos; no clique, o fluxo em nós ligados (Gatilho →
  Condição → Sim/Não → Ação) com um Construtor de blocos ao lado, na identidade visual do TON.
- O TON **não corrige o NG**: só detecta, avisa e verifica.

## Capabilities

### New Capabilities
- `email-flows`: cadastro, sugestão, execução e entrega de fluxos de e-mail, com o relatório semanal
  de inconsistências do NG como fluxo padrão e a verificação de correção a cada extração.

### Modified Capabilities
<!-- nenhuma; `routine-framework` passa a depender do motor desta change -->

## Impact

- Backend: novos modelos e migração Alembic (fluxo, versão, execução, entrega), despacho de eventos a
  partir da revisão NG, da classificação de contas e da DRE, tarefa Celery Beat de agendamento,
  transporte de e-mail Resend ou SMTP por variável de ambiente, ferramenta do assistente para propor fluxo.
- Frontend: `/ton/fluxos` (tabela + detalhe).
- Usa o evento "não detectado nesta importação" de `carry-over-decisions-on-reimport`.
- `routine-framework`: R1–R9 passam a ser fluxos de origem "sistema" sobre o mesmo motor.

## Dependências

- Provedor de e-mail (Resend com domínio verificado por DNS, ou SMTP); e-mails do Financeiro e da Controladoria (Luyla, reunião de 2026-10-06). A
  verificação ganha precisão real com a extração automática do NG (`ng-direct-integration`); com
  importação manual, verifica a cada upload.

## Estado de dado

Real.
