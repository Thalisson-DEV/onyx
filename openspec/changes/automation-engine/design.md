## Contexto

O motor v2 de `email-flows` (`onyx/ton/email_flows/engine.py`) é um interpretador em memória: uma
execução guarda só um cursor (`frames`) e as entregas. Ele não registra o estado de cada passo, não
tem retry por passo nem *run after*, e cada tipo de passo é um `isinstance` no interpretador. O
pedido de 2026-10-08 exige um motor genérico. Este desenho reaproveita do v2: o outbox de eventos
(`ton_email_flow_event`), o read model de inconsistências, o compositor e o transporte de e-mail,
os assets e o modelo de estilo, as permissões (`READ_TON_REPORTS` / `MANAGE_TON_REPORTS`) e a
auditoria TON.

## Referência: Power Automate

| Power Automate | TON |
|---|---|
| Fluxo automatizado / instantâneo / agendado | Gatilho de evento / manual / recorrência |
| Ação, conector | Nó do catálogo (`email.send`, `ton.inconsistencies`, `ai.prompt`…) |
| Conteúdo dinâmico, `outputs('X')`, `triggerBody()` | `{{ steps.x.outputs.campo }}`, `{{ trigger.outputs.campo }}` |
| `variables('v')`, Inicializar/Definir/Incrementar/Acrescentar | `vars` declaradas no fluxo + `variable.set/increment/append` |
| `items('Apply_to_each')` | `{{ item }}` e `{{ loop.<id>.index }}` |
| Condição, Switch, Aplicar a cada, Fazer até, Escopo, Encerrar, Ramo paralelo | `control.condition/switch/foreach/until/scope/terminate/parallel` |
| Configurar execução após (sucesso/falha/ignorado/tempo limite) | `run_after` por nó, relativo ao nó anterior |
| Política de repetição (fixa/exponencial) | `retry` por nó; padrão do catálogo |
| Aprovações | `approval.request` (saída com resultado, quem, comentário) |
| AI Builder "Executar prompt" | `ai.prompt` (texto ou campos estruturados), `ai.extract`, `ai.classify`, `ai.summarize` |
| Histórico de 28 dias, reenviar, cancelar | Execuções com etapas, reenviar, cancelar |
| Verificador do fluxo | `validate()`: erros e avisos por nó, também no navegador |
| Copilot cria o fluxo | `ton_draft_automation` no chat e "Pedir ao TON" no designer |

## Definição v3

```
{ "schema": 3,
  "trigger": {"type": "trigger.schedule", "params": {...}},
  "variables": [{"name": "prazo", "type": "string", "value": "sexta-feira"}],
  "steps": [<nó>, ...],
  "settings": {"notify_on_failure": ["..."], "timeout_hours": 168} }

<nó> = {"id": "buscar", "type": "ton.inconsistencies", "label": "Buscar inconsistências",
        "params": {...}, "run_after": ["succeeded"], "retry": {"policy": "exponential",
        "count": 3, "interval_seconds": 30}, "timeout_seconds": null,
        // contêineres
        "then": [], "else": [], "cases": [{"id", "value", "steps"}], "default": [],
        "steps": [], "branches": [{"id", "label", "steps"}]}
```

- `id` é estável e legível (referências não quebram ao renomear o rótulo).
- Valores de parâmetro aceitam modelos `{{ expr }}`. Um valor que é só `{{ expr }}` mantém o tipo
  (lista, número); misturado com texto vira texto — como `@expr` e `@{expr}` do Power Automate.
- Expressões: caminhos (`steps.x.outputs.items[0].valor`), literais e uma lista fechada de funções
  (`length`, `sum`, `join`, `default`, `upper`, `lower`, `format_money`, `format_date`, `add`,
  `sub`, `mul`, `div`, `round`, `concat`, `first`, `last`, `json`, `contains`, `not`, `if`,
  `coalesce`, `now`, `add_days`). Parser próprio, sem `eval`.
- Condições: grupos `and`/`or` aninhados com regras `{left, operator, right}`; operadores
  `eq, ne, gt, gte, lt, lte, contains, not_contains, starts_with, ends_with, empty, not_empty, in`.
- Limites: 120 nós, profundidade 8, 500 itens por "para cada", 100 iterações por "repetir até".

## Tipos de automação

`EMAIL`, `ALERT`, `ROUTINE`, `APPROVAL`, `DATA_AI`, `GENERAL`. O tipo é escolhido pela pessoa (ou
sugerido pelos nós) e entra na validação de ativação: `EMAIL` precisa de `email.send`; `ALERT` de
`ton.notify` ou `email.send`; `APPROVAL` de `approval.request`; `ROUTINE` de gatilho de recorrência
ou evento; `DATA_AI` de um nó de dados ou IA.

## Execução durável

- `ton_automation_run`: estado (`QUEUED, RUNNING, WAITING, SUCCEEDED, FAILED, CANCELLED,
  TIMED_OUT`), `trigger_key` idempotente por automação, saída do gatilho congelada, `lease_until`,
  `resume_at`, modo (`LIVE, MANUAL, TEST, RESUBMIT`).
- `ton_automation_step_run`: um por (execução, nó, iteração); entradas resolvidas, saídas, estado
  (`RUNNING, WAITING, SUCCEEDED, FAILED, SKIPPED, TIMED_OUT, CANCELLED`), tentativas, próximo retry,
  erro, início e fim. É o *checkpoint*: cada passo é gravado e comitado.
- A tarefa `ton_automation_execute_run` toma a execução por *lease* (UPDATE atômico); o
  interpretador percorre a árvore e **reaproveita** cada passo já concluído (replay determinístico:
  decisões de condição, switch e listas do "para cada" ficam gravadas). Um passo em espera
  (esperar, aprovação, retry com atraso) suspende a execução com `resume_at`; o *tick* devolve à
  fila quando vence.
- Efeitos externos (e-mail, HTTP, notificação) rodam no máximo uma vez: se um worker cai no meio de
  um, o replay encontra o passo `RUNNING` e o marca como falha "interrompido", sem reenviar.
- O *tick* (Celery Beat, 1 min): consome o outbox de eventos, dispara recorrências, devolve à fila
  execuções vencidas e execuções com *lease* expirado (worker caiu), encerra execuções acima do
  tempo limite.
- Teste: e-mails só para quem testa, esperas puladas, aprovações aprovadas pela própria pessoa.

## Segurança e não negociáveis

- IA interpreta, resume e extrai; o validador avisa quando uma condição usa saída de IA sem
  aprovação humana antes de uma ação externa. Números de e-mail vêm de dados, não do LLM.
- Nada roda sem ativação humana; rascunhos do chat são sempre `DRAFT`.
- HTTP: só `https`, bloqueio de endereços privados/loopback, tempo limite, corpo limitado.
- Execuções leem dados com a visibilidade do dono da automação.
