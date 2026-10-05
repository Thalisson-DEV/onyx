## Context

- A revisão NG (`onyx/db/ton/financial_review.py`) persiste ocorrências por importação e, desde o
  carry-over, grava para cada caso anterior não redetectado um evento de verificação
  (`not_detected_in_snapshot_id`, PASSED/INCONCLUSIVE) sem mudar o status.
- O R3 tem agenda própria em `KVStore` (`ton:routines:R3:schedule:v1`) com lock consultivo e chave
  de publicação idempotente; `registry.ROUTINES` lista R1–R9 só como texto.
- O Onyx já tem envio de e-mail (`onyx.auth.email_utils.send_email`, SMTP ou SendGrid, ligado por
  `EMAIL_CONFIGURED`).
- A pré-classificação de contas já estabeleceu o padrão "o assistente sugere, o humano confirma".
- `routine-framework` (design) prevê `RoutineDefinition` versionada + `RoutineRun` + entrega
  in-app/e-mail. Esta change constrói esse núcleo uma vez.

## Goals / Non-Goals

**Goals:** cadastro de fluxo por usuário de negócio sem código; catálogo fechado de gatilhos,
condições e ações; sugestões do TON com aprovação; relatório semanal de inconsistências como fluxo
padrão; verificação corrigida/aberta/reaparecida por importação; execução idempotente, auditada e
testável (prévia, "só para mim"); núcleo reutilizável pelo `routine-framework`.

**Non-Goals:** árvore livre ou vários níveis de condição; arrastar nós ou criar ramos no canvas; ações
que escrevem no NG ou em sistemas externos além de enviar e-mail; texto de e-mail redigido por LLM;
canais além de e-mail e in-app (Telegram/WhatsApp ficam no plano 009).

## Decisions

### Modelo

- **`ton_flow`**: nome, origem (`USER` | `TON_SUGGESTED` | `SYSTEM`), estado (`SUGGESTED` | `ACTIVE`
  | `PAUSED` | `DISCARDED`), versão vigente, motivo da sugestão, quem cadastrou/confirmou.
- **`ton_flow_version`** imutável: gatilho, condição, ação "sim", ação "não" (JSON validado por
  Pydantic). Toda edição cria versão nova; a execução aponta para a versão que rodou.
- **`ton_flow_run`**: versão, evento do gatilho, ramo (`YES` | `NO`), estado, erro e
  unicidade (fluxo, chave do evento), fora os testes: editar o fluxo no meio da semana não reenvia a
  mesma janela. Chave do evento: janela do agendamento
  (`2026-W41`) ou id do evento de origem (review run, DRE, conta).
- **`ton_flow_delivery`**: uma linha por mensagem enviada (ou lote): execução, canal, provedor,
  para/cc/cco, lote i de n, id da mensagem no provedor, assunto, corpo renderizado (snapshot do que
  foi enviado), estado (`SENT` | `FAILED` | `NOT_CONFIGURED` | `TEST`), tentativas, erro.

Migração `e5b8c2d4f1a7`, depois de `d7a1e4c9b2f6` (`controller-validated-treatments`).

### Catálogos (código, não banco)

- **Gatilho** = tipo + parâmetros + campos do evento que expõe. v1:
  `schedule.weekly(dia, hora)`, `schedule.daily(hora)` (America/Sao_Paulo);
  `ng_import.completed`; `ng_occurrence.changed(tipo ∈ nova|corrigida|reaparecida)`;
  `account.unclassified`; `dre.recalculated`.
- **Condição** = lista de cláusulas ligadas por "e" (`campo`, `operador`, `valor`); cada gatilho
  declara seus campos e tipos, e a tela só oferece operadores válidos (`é`, `é um de`, `≥`, `>`).
  Lista vazia = sempre "sim".
- **Ação** = `none` | `send_email(para, cc, cco, assunto, modelo)`. Modelos do catálogo:
  `inconsistency_report` (tabela por unidade), `occurrence_alert`, `simple_notice`. Assunto aceita só
  marcadores do catálogo (`{semana}`, `{total}`, `{unidade}`).
- Catálogo fechado em código mantém a definição validável, testável e segura para o assistente
  preencher; ampliar o catálogo é uma mudança de código pequena e revisada.

### Execução

- **Eventos**: as transações de origem chamam `emit_flow_event__no_commit(tipo, chave, campos)` que
  grava num outbox; uma tarefa Celery consome, avalia os fluxos ativos daquele gatilho e cria runs.
  O evento só existe se a transação de origem fizer commit.
- **Agendamento**: uma tarefa Beat a cada 2 min (`ton_email_flows_tick`, que também consome o outbox) calcula, por fluxo agendado ativo, a janela devida
  e cria o run idempotente (atraso ou retry nunca enviam duas vezes).
- **Avaliação**: carrega o read model do gatilho, avalia a condição, escolhe o ramo, renderiza o
  modelo, grava a entrega. Ramo sem ação = execução "silenciosa" registrada com motivo (mesma regra
  de silêncio do `routine-framework`).
- **Transporte** (`onyx/ton/flows/transport.py`): interface `EmailTransport.send(message)` com duas
  implementações escolhidas por `TON_EMAIL_PROVIDER=resend|smtp`. `resend`: API HTTP
  (`POST https://api.resend.com/emails`) via `httpx`, `RESEND_API_KEY`, sem SDK novo. `smtp`:
  reaproveita `SMTP_SERVER`/`EMAIL_FROM` de `app_configs` e o envio de `email_utils`. Remetente em
  `TON_EMAIL_FROM` (cai para `EMAIL_FROM`). Sem provedor configurado a entrega fica
  `NOT_CONFIGURED` com o corpo guardado e visível no TON; nada quebra. Falha = `FAILED` com erro,
  até 3 tentativas.
- **Destinatários agrupados**: a ação tem "Para", "Cc" e "Cco" (opcional); cada execução gera UMA
  mensagem com todos juntos, não uma por pessoa (economiza a cota do Resend). O histórico tem uma
  linha por mensagem com a lista de destinatários. Se a soma passar do limite do provedor (Resend:
  50 por mensagem; SMTP: `TON_EMAIL_MAX_RECIPIENTS`, padrão 50), a mensagem é dividida em lotes
  (Cc/Cco repartidos, "Para" repetido em cada lote) e cada lote vira uma linha com "lote i de n".
- **Teste**: "Ver prévia" renderiza com os dados de agora sem criar run; "Enviar só para mim" cria
  entrega `TEST` para o e-mail do usuário e não consome a janela do agendamento.

### Read model de inconsistências

- Derivado das tabelas existentes (ocorrências da revisão NG + findings por snapshot + eventos de
  verificação), sem tabela nova, por competência:
  - **aberta**: status em aberto e detectada na última importação que cobre a competência;
  - **corrigida no NG**: verificação PASSED "não detectada nesta importação" para uma importação que
    cobre a competência;
  - **reapareceu**: detectada de novo depois de uma verificação PASSED.
  INCONCLUSIVE fica aberta, com nota "conferir à mão". Nunca afirma correção para competência que a
  importação não cobriu.
- Semanas em aberto = semanas desde a primeira detecção.
- A cada revisão NG concluída é emitido `ng_import.completed` (totais) e um
  `ng_occurrence.changed` por transição, o que alimenta fluxos de alerta e o fluxo semanal.

### Sugestões do TON

- Ferramenta do assistente `propose_email_flow` devolve uma definição que passa pelo mesmo validador
  da tela; vira `ton_flow` com origem `TON_SUGGESTED`, estado `SUGGESTED` e motivo. Só
  "Cadastrar" (humano, com permissão) a ativa; "Descartar" guarda quem e quando. O LLM nunca escreve
  conteúdo de e-mail, só escolhe itens dos catálogos.
- O fluxo "Inconsistências da semana" é semeado como sugestão (segunda-feira 08:00 de Brasília, modelo
  `inconsistency_report`, condição "há itens abertos > 0", "não" = sem ação) aguardando os
  destinatários do Financeiro.

### Permissões e auditoria

- Ver: `READ_TON_REPORTS`. Cadastrar, editar, pausar, confirmar/descartar sugestão:
  `MANAGE_TON_REPORTS` (concedida à Controladoria). Sem permissão nova.
- Toda criação, versão, ativação, pausa, descarte e envio de teste gera evento de auditoria TON.

### Reaproveitamento pelo `routine-framework`

- `RoutineDefinition` vira um fluxo de origem `SYSTEM` cuja ação é "executar rotina e publicar"; o
  framework herda agenda, eventos, idempotência, silêncio, entrega e histórico. Gatilho D+n útil
  entra no catálogo de gatilhos daquela change. O R3 continua no `KVStore` até ser migrado lá.

## UI

Referência visual do Thalisson (2026-10-05, `exemplo-fluxo.png`): visualização de fluxo em nós
ligados por setas, com um "Construtor" de blocos ao lado. Mantém a identidade visual do TON; só o
tipo de visualização vem da referência.

- `/ton/fluxos`: tabela simples, uma linha por fluxo (Fluxo · Quando · Se · Então · Senão · Último
  envio · Estado). Sugestões do TON aparecem na mesma tabela com "Sugerido pelo TON" e
  Cadastrar/Descartar na linha.
- `/ton/fluxos/{id}`: **canvas do fluxo** (fundo pontilhado) com nós fixos de cima para baixo:
  `Gatilho` → `Condição` → duas saídas rotuladas **Sim** e **Não** → nó de ação em cada saída. Cada
  nó mostra o tipo (cabeçalho com ícone) e um resumo em frase ("Toda segunda às 08:00", "Itens
  abertos > 0", "E-mail para Financeiro (3) · Cc Luyla"). Ação vazia = nó tracejado "Não fazer nada".
- **Construtor** à direita: seções Gatilho / Condição / Ação com os itens do catálogo em blocos.
  Selecionar um nó no canvas abre os campos dele no Construtor; clicar num bloco do catálogo troca o
  tipo do nó selecionado. A estrutura é fixa (sem arrastar nós nem criar ramos novos no v1), o que
  mantém a definição válida para a Luyla e para o assistente.
- Barra do topo: estado/versão, Ver prévia (abre o e-mail renderizado), Enviar só para mim, Salvar.
  Abaixo do canvas: histórico de execuções em tabela.

## Risks / Trade-offs

- [Catálogo fechado limita a Luyla] → cobre os casos pedidos; novos gatilhos são mudança pequena.
- [Ruído por e-mail] → um nível de sim/não, silêncio registrado, alertas por evento com debounce.
- [Reaparecida depende de redetectar a mesma ocorrência] → usa fingerprint/base_key do carry-over;
  casos ambíguos ficam "conferir à mão".
- [Provedor ausente ou domínio não verificado] → tudo funciona exceto o envio, explicitamente
  marcado.

## Open Questions

- Destinatários do Financeiro e da Controladoria e formato do relatório atual (Luyla, 2026-10-06).
- Provedor e remetente: o Resend exige domínio remetente verificado por DNS (Vale Norte/TI Celso, ou
  domínio do Thalisson) — pendência externa.
