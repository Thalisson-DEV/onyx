## Why

Os fluxos de e-mail (`email-flows`, v1 e v2) provaram o modelo "gatilho → passos" com a
Controladoria, mas só sabem fazer uma coisa: mandar e-mail sobre inconsistências do NG. Em
2026-10-08 o Thalisson pediu o salto seguinte: um **motor de automações e workflows visuais** no
padrão de robustez do Power Automate, onde **toda automação nova do TON** é criada, configurada e
orquestrada no mesmo canvas — inclusive as rotinas autônomas do Prompt Mestre (§12, R1–R9: "o que
disparar, quando calar e a quem notificar"), os alertas das sentinelas (§11) e a entrega do pacote
executivo (§14).

Pedidos explícitos:

1. **Motor**: estado por etapa, fila, retry automático, histórico de execuções, tratamento de falhas
   (executar após falha, escopo try/catch, encerrar), arquitetura extensível de gatilhos, condições,
   ramos e ações.
2. **Dados e IA**: injetar dados estruturados e não estruturados no meio do fluxo; nós de IA que
   consomem a saída dos passos anteriores e repassam a sua para os seguintes.
3. **Canvas**: interface limpa, com a identidade visual do TON; arrastar e soltar, conexões, zoom,
   painel lateral de configuração e validação visual de erros em tempo real.
4. **Chat**: a pessoa pede a automação no chat e o TON gera o rascunho; ou cria do zero com o canvas
   vazio.
5. **Tipos de automação** (e-mail, alerta, rotina, aprovação, dados e IA, geral), para filtrar e
   validar cada uma pelo que ela precisa ter.

## What Changes

- Novo módulo `onyx/ton/automations`: definição v3 (gatilho, variáveis, árvore de nós, configurações),
  catálogo de nós em código (registro extensível), expressões entre etapas
  (`{{ steps.buscar.outputs.items }}`, `{{ vars.prazo }}`, `{{ item.unidade }}`, funções seguras),
  validador ("verificador do fluxo") com erros e avisos por nó.
- Execução durável: cada etapa vira um registro (`ton_automation_step_run`) com entradas, saídas,
  tentativa, erro e duração; execuções em fila Celery com *lease*; retomada por replay
  determinístico; retry fixo ou exponencial; *run after* (sucesso, falha, ignorado, tempo
  esgotado); escopos; ramos paralelos; para cada; repetir até; esperar; aprovação; encerrar;
  cancelar e reenviar execução.
- Gatilhos: manual (com campos de entrada), recorrência (minutos a meses, horário de Brasília),
  importação do NG, inconsistência nova/corrigida/reaparecida, conta sem classificação, DRE
  recalculada, falha de outra automação.
- Ações: e-mail (editor rico existente, modelo de estilo, blocos de dados), notificação no sino do
  TON, consulta de inconsistências e contas, dados (inserir dados, compor, JSON, filtrar,
  selecionar, ordenar, agrupar, agregar, tabela HTML, juntar), IA (prompt com saída estruturada,
  extrair, classificar, resumir), HTTP de saída, variáveis (definir, incrementar, anexar).
- Fluxos de e-mail existentes são convertidos em automações do tipo "E-mail" (sem perder versões
  novas); a tela `/ton/fluxos` passa a apontar para `/ton/automacoes`.
- Ferramenta do chat `ton_draft_automation` (substitui `ton_draft_email_flow`): rascunho de
  automação a partir do pedido, cartão no chat com "Abrir no editor".
- Telas: lista em tabela com filtro por tipo; detalhe (dados + histórico de execuções); designer em
  tela cheia; execução no canvas com o estado de cada etapa, entradas e saídas.

## Capabilities

### New Capabilities
- `automation-engine`: definição, validação, execução durável, histórico, aprovações, rascunho pelo
  chat e designer visual de automações.

### Modified Capabilities
- `email-flows`: passa a ser um tipo de automação; o motor v2 deixa de rodar.

## Impact

- Backend: `onyx/ton/automations/*`, `onyx/db/ton/automations.py`, `onyx/db/ton/models.py`,
  migração Alembic nova, `onyx/server/ton/automations.py`, tarefas Celery TON, ferramenta do chat.
- Frontend: `web/src/views/ton/AutomationsPage/*`, `web/src/lib/ton/automations.ts`, rotas
  `/ton/automacoes/**`, cartão do chat, sino.

## Dependências

- Provedor de e-mail (Resend/SMTP) e domínio verificado — já pendentes em `email-flows`.
- Provedor de LLM configurado no Onyx para os nós de IA (o padrão do ambiente).
- R1–R9 continuam dependendo das suas changes de domínio; o motor só fornece o meio.

## Estado de dado

Real: os gatilhos e consultas leem os read models reais (NG, classificação, DRE). Os testes usam
dados sintéticos rotulados.
