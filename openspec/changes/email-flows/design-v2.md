## v2 — fluxos avançados (decisão de 2026-10-05, noite)

Depois de usar a v1 o Thalisson pediu algo próximo do Power Automate: o canvas como a tela inteira,
com zoom e arraste; fluxos com mais de um nível; e-mail escrito como num cliente de e-mail, com
estilo, variáveis e imagens (logo); e o TON criando fluxos **a partir do chat** ("quero que quando
tal coisa aconteça seja enviado um e-mail para tal pessoa, seguindo o modelo padrão de estilo"),
entregando um rascunho para a Luyla revisar. Escolhas dele: os quatro tipos de passo abaixo, editor
de texto livre estilizado, e rascunho entregue como cartão no chat com prévia, "Abrir no editor" e
"Ativar". A v1 continua válida para o que não muda (gatilhos, read model, transporte, histórico,
idempotência, permissões).

### Definição v2

```
{ "schema": 2, "trigger": <igual à v1>, "variables": [{"name": "prazo", "value": "sexta-feira"}],
  "steps": [<passo>, ...] }
```

Passos (cada um com `id` estável):

- `condition` — `conditions` (cláusulas do catálogo), `then: [...]`, `else: [...]`. Cláusulas de
  item **dividem** os itens: os que atendem seguem pelo Sim, os demais pelo Não ("se for duplicidade
  acima de R$ 100 mil → diretoria; senão → Financeiro"). Cláusulas de resumo (quantidade, total)
  decidem o ramo inteiro. Um ramo sem itens não roda.
- `send_email` — Para/Cc/Cco, assunto e corpo em HTML escrito no editor, com o modelo padrão de
  estilo aplicado (ou não). Pode haver vários, em qualquer ponto.
- `for_each_unit` — repete os passos internos para cada unidade com itens; dentro dele os itens são
  só os da unidade e existem as variáveis `{unidade}` e `{email_unidade}` (destinatários por
  unidade definidos no passo, com um padrão para unidades sem cadastro).
- `wait` — espera um tempo (dias/horas) ou até um dia da semana e hora (Brasília) e, ao retomar,
  **confere de novo**: recarrega os dados e mantém só os itens que continuam abertos.
- `approval` — pede aprovação a pessoas do TON; o fluxo para até alguém aprovar (segue) ou recusar
  (termina, com motivo). As pessoas recebem um e-mail com o link para aprovar no TON.

Limites: profundidade 5, 40 passos, sem `for_each_unit` dentro de outro, `wait`/`approval` fora de
`for_each_unit` (retomada simples). Definições v1 são convertidas na leitura para v2 (condição com
Sim/Não), sem migração de dados.

### Execução retomável

`ton_email_flow_run` ganha `WAITING` (espera ou aprovação), `resume_at` e `cursor` (caminho do
próximo passo + chaves dos itens em curso). O tick retoma execuções vencidas; aprovação retoma na
hora da decisão. Cada envio é idempotente por (execução, passo, unidade, lote), então retomar ou
repetir nunca reenvia. Tabela nova `ton_email_flow_approval` (pessoas, situação, quem decidiu,
quando, observação).

### E-mail

- **Editor** (TipTap no navegador): texto livre com negrito, itálico, sublinhado, títulos, cores,
  alinhamento, listas, links; **chips de variável** (do gatilho — `{semana}`, `{data}`, `{total}`,
  `{valor_total}`, `{unidade}`, `{nome_fluxo}`, `{link_ton}` — e as definidas no fluxo); **blocos**
  que o servidor preenche com os dados (tabela de inconsistências por unidade, lista de contas,
  resumo em números, botão "Abrir no TON"); **imagens** da biblioteca de assets (logo).
- **Modelo padrão de estilo**: cabeçalho com a logo, cor da marca, rodapé. Um por ambiente,
  editável em "Modelo de e-mail"; o assistente e os fluxos novos usam por padrão.
- **Servidor**: o HTML do editor é saneado por lista de permissões (tags, atributos e estilos
  conhecidos); variáveis viram texto escapado; blocos viram HTML com estilos inline; imagens vão
  como anexos inline (CID) para não depender de URL pública. Os números continuam vindo só dos read
  models.
- **Assets**: `ton_email_asset` (nome, tipo, bytes; PNG/JPEG/GIF até 1 MB). A logo da Vale Norte é
  semeada.

### Rascunho pelo chat

Ferramenta do TON `ton_draft_email_flow(pedido, fluxo_id?)`: um LLM recebe o pedido em português,
o catálogo, o esquema v2 e o modelo padrão, e devolve a definição completa (passos + texto do
e-mail). Ela passa pelo mesmo validador do editor e é salva como **rascunho** ("Sugerido pelo TON",
criado pela pessoa do chat). Com `fluxo_id`, ajusta o rascunho existente ("muda o destinatário
para…"). O chat mostra um cartão com os passos em frases, o que falta (ex.: e-mail do Financeiro),
a prévia do e-mail e os botões "Abrir no editor" e "Ativar". O texto do e-mail pode ser redigido
pelo LLM **no rascunho**; nada é enviado sem ativação humana, e números/itens vêm só das variáveis
e blocos. (Isso substitui a regra da v1 "o LLM nunca escreve o e-mail", restrita agora aos números.)

### Tela

`/ton/fluxos/{id}` em tela cheia: o canvas ocupa a página (React Flow: arrastar, zoom, mini-mapa,
"ajustar à tela"), com layout automático de cima para baixo; "+" entre os passos insere um passo;
clicar num passo abre o painel só dele; o e-mail abre o editor grande com prévia ao lado. A lista
`/ton/fluxos` continua uma tabela, com uma linha "Aguardando aprovação" quando houver.
