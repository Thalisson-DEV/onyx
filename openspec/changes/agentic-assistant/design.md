## Proposta de ação

Uma ferramenta de escrita nunca escreve. Ela chama `propose_action(kind, payload)`:

1. valida o payload com o mesmo modelo Pydantic da rota da tela (ex.: `TreatmentCreate`,
   `DreVersionCreate`);
2. confere a permissão da pessoa (mesmas checagens do repositório, sem aplicar);
3. calcula a prévia: o que muda e, para mudanças de DRE, as linhas afetadas antes × depois do
   período e unidade da conversa (cálculo em memória, sem gravar `DreCalculationRun`);
4. grava `TonAgentAction` (id, chat_session_id, message_id, user_id, kind, payload, preview,
   status `PROPOSED | APPLIED | CANCELLED | EXPIRED | UNDONE | FAILED`, applied_at, result_ref,
   undo_ref) e devolve ao modelo o id e um resumo da prévia.

O cartão chama `POST /ton/agent/actions/{id}/apply`. O servidor relê a proposta, valida de novo
contra o estado atual (se a base mudou, refaz a prévia e pede nova confirmação), executa o serviço
existente na sessão da pessoa e grava o resultado. `cancel` e `undo` seguem o mesmo padrão.

Cada `kind` é um registro em `ACTION_HANDLERS` com `validate`, `preview`, `apply` e, quando o
serviço é versionado, `undo`:

| kind | serviço existente | desfazer |
|---|---|---|
| `dre_structure_change` | nova versão da estrutura | restaurar versão anterior |
| `closing_treatment` | `closing_treatments.create_treatment` | nova versão com status inativo |
| `dre_manual_adjustment` | novo (abaixo) | nova versão zerada |
| `account_classification` | `account_classification` change/confirm-batch | classificação anterior |
| `occurrence_decision` | `financial_review` decisions | — (decisão é histórico) |
| `unit_assignment` | `unit_assignment` | atribuição anterior |
| `reconciliation_decision` | decisão do item de conciliação | — |
| `source_import` | importação + perfil | limpeza da execução (`runs/{id}/cleanup`) |
| `dre_recalculate` | `/ton/dre/calculations` (mês ou ano) | — |
| `automation_activate` / `automation_run` | automações | pausar |
| `controller_rule` | novo (regras lembradas) | arquivar |

Depois de aplicar, o frontend envia à conversa uma mensagem do sistema curta ("Ação aplicada:
…") para o agente continuar com o estado novo, por exemplo recalcular e mostrar a DRE.

## Origens de linha da DRE

Hoje `SOURCE_SUM` só soma contas do NG atribuídas à linha. Uma linha passa a ter `source` opcional:

- `ng_accounts` (padrão, comportamento atual);
- `billing_gross`: soma de `amount` (valor do serviço) dos registros de faturamento do mês e da
  unidade, por emissão ou competência conforme a configuração da linha;
- `billing_tax`: soma de campos de imposto escolhidos da nota (ISS da nota; outros quando o
  arquivo trouxer);
- `pis_cofins`: fatos da fonte de PIS/COFINS, quando existir;
- `manual_adjustment`: valores de `TonDreAdjustment` (estrutura, linha, mês, unidade, valor,
  justificativa, versão, autor).

O drill-down de cada origem mostra as notas, as linhas da planilha ou o ajuste com autor e
justificativa. O Excel da DRE recebe as novas linhas sem mudança de formato.

## Chat por especialista

Cada `SpecialistDefinition` ganha `prompt`, `starter_messages` e `allowed_tools` incluindo ações.
`provision_agent` passa a criar uma persona por especialista ativo (nome "TON CFO" etc.), com o
`sync_agent__system` mantendo ferramentas e prompt atualizados. A rota
`/ton/especialistas/[key]` abre a conversa com a persona do especialista. A lista de conversas
mostra o ícone do especialista.

O prompt do especialista recusa pedidos fora do domínio e indica quem atende ("Isso é com o
AUDITOR"), com link para a conversa dele.

## Contexto fixado e regras lembradas

O seletor de período e unidade grava no `chat_session` um contexto TON. O backend injeta no prompt
"Contexto da conversa: período X, unidade Y" e as regras da Controladoria ativas
(`TonControllerRule`: texto, autor, versão, ativa).

## Limites

- Uma proposta expira em 24 h ou quando a base muda.
- O agente cria no máximo 5 propostas por resposta.
- Ações em lote (classificação, decisões) mostram o total e as 20 primeiras linhas; o restante fica
  em "Ver todas".
- Toda ação usa as permissões de quem clica, não de quem pediu.
