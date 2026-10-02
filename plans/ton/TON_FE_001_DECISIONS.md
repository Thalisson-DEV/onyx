# TON-FE-001 — Architecture & Product Decisions

Este documento registra decisões relevantes tomadas durante o rebuild.

O agente deve atualizá-lo quando a realidade do repositório exigir uma escolha que o roadmap não determina sozinho.

Não registrar detalhes triviais.

---

# Princípios

1. Evidência do repositório vale mais que suposição do roadmap.
2. Onyx é infraestrutura; TON é o produto cliente.
3. Reaproveitar capacidades maduras antes de reimplementar.
4. A camada visual do TON pode ser substituída agressivamente.
5. Nunca falsificar estado para aproximar a tela da referência.
6. Otimizar para o caso Vale Norte, não para genericidade do Onyx.
7. Semântica financeira e fronteiras de aprovação humana são preservadas.
8. O agente tem liberdade para decidir arquitetura, desde que registre decisões materialmente relevantes.

---

# D-001 — Boundary do frontend

Status: Accepted (2026-10-01).

## Deve responder

Qual estrutura será usada para o novo frontend TON?

Opções possíveis:
- subtree isolado no app Next.js atual;
- route group/layout isolado;
- app/package frontend separado;
- outra solução melhor justificada.

## Decisão
B — route group `/ton` no app Next.js atual, com layout e shell TON próprios em
`web/src/views/ton/shell/`. O shell não usa `SidebarLayouts`/`AppChrome` do Onyx.

## Motivo
O chat nativo depende do provider tree e do `RootLayout` do app atual. Um app separado
duplicaria auth, streaming, arquivos e artifacts. Um layout próprio sob `/ton` troca
toda a apresentação com risco mínimo.

## Consequências
- `TonChrome`/`TonSidebar` são substituídos pelo shell novo.
- `/admin/*` continua com o chrome Onyx (administração técnica).
- `/app` continua existindo para administração/compatibilidade, mas não é entrada do produto.

---

# D-002 — Reuso do chat Onyx

Status: Accepted (2026-10-01).

## Deve responder

- quais APIs/runtime de conversa serão reaproveitados;
- quais componentes visuais do Onyx serão reaproveitados;
- quais serão substituídos;
- como streaming/tool events serão adaptados à apresentação TON;
- como files, Code Interpreter e artifacts continuam funcionando.

## Decisão
- Runtime: `AppPage` + `useChatController` + `ChatUI` sem fork. Sessões, streaming,
  tool calls, arquivos, Code Interpreter, artifacts e cancelamento seguem nativos.
- `AppPage` ganha slots opcionais (`welcome`, `suggestions`, `hideModelSelector`,
  `placeholder`) usados só por `/ton/chat`. `/app` não muda.
- Apresentação TON: hero "Olá, sou o TON.", sugestões da demo, seletor de modelo oculto
  para cliente (provider é configuração técnica), rodapé de versão removido.
- Tool events: `TonToolCard`/`TonExecutionSummary` existentes continuam como camada
  executiva; JSON fica em disclosure.

---

# D-003 — Modelo de especialistas

Status: Accepted (mantém a decisão do UX-002, 2026-10-01).

## Requisitos imutáveis

Especialistas canônicos:
- TON CFO
- TON COO
- TON FROTA
- TON CONTRATOS
- TON COMPLIANCE
- TON PROCUREMENT
- TON RH
- TON AUDITOR
- TON CEO

## Deve responder

- specialist é role, persona ou ambos?
- como interação direta funciona?
- como contexto de especialista é persistido?
- quem restringe tools?
- de onde vem status runtime?
- como TON continua coordenador?

## Decisão
Especialistas são papéis de orquestração no backend (`/api/ton/agent/specialists`,
`interaction: "coordinator"`), não Personas. Há uma única Persona coordenadora TON
(`/api/ton/agent/configuration`). Status vem só do runtime. A UI mostra especialistas
como contexto (rail, página secundária) e abre conversa com o coordenador com uma
pergunta focada no domínio; nenhum chat por especialista é criado.

---

# D-004 — Cliente x Admin

Status: Accepted (2026-10-01).

## Deve responder

- landing de usuário normal;
- navegação cliente;
- entry de admin;
- generic Onyx visibility;
- localização da Cobertura do Prompt Mestre;
- retorno admin → TON.

## Decisão
- Landing: login, `/` e retorno padrão vão para `/ton` (Visão Geral).
- Navegação cliente: Visão Geral, Assistente, Fechamento (DRE, Pendências), Automações,
  Relatórios, Fontes. Especialistas como seção secundária.
- Administração: entrada discreta no rodapé da sidebar só para quem tem acesso admin.
- Cobertura do Prompt Mestre sai da navegação cliente; rota preservada como diagnóstico,
  linkada só para admin.
- Retorno admin → TON: o chrome admin já linka `/ton` (mantido).

---

# D-005 — Design system

Status: Accepted (2026-10-01).

## Deve responder

- quais primitives atuais permanecem;
- quais layouts antigos são descartados;
- onde vivem tokens/componentes TON;
- como `ton_reference_visual` influencia composição;
- quais elementos são próprios do TON.

## Decisão
- Primitives Opal permanecem (Text, Button, Tag, ícones `@opal/icons`).
- Tokens TON em `web/src/views/ton/shell/ton.css`: camada pequena de variáveis
  semânticas sobre as primitives `--vale-norte-*` já existentes. Sem cores Tailwind
  built-in.
- Composição da referência: header verde escuro, sidebar verde, workspace claro,
  right rail contextual, chat como núcleo.
- Componentes próprios em `web/src/views/ton/shell/` e `web/src/views/ton/components/`.

---

# D-006 — Branding e locale

Status: Accepted (2026-10-01).

Target:
- Vale Norte visível;
- TON como nome do produto;
- pt-BR no cliente;
- Onyx invisível na experiência cliente;
- Intl pt-BR preservado.

## Decisão
- Logo oficial salva em `web/public/ton/vale-norte-logo.png` (baixada da URL oficial,
  recortada). Variante `vale-norte-logo-reversed.png` (partes verde-escuras em branco)
  para o header escuro.
- Decisão do usuário (2026-10-01): a aplicação é somente pt-BR, sem i18n.
  - `src/i18n/request.ts` fixa o locale em `pt` (`TON_LOCALE`); a preferência
    salva do usuário é ignorada. O seletor de idioma em Configurações fica oculto
    (`SHOW_LANGUAGE_PICKER = false`).
  - Telas TON leem copy de `src/lib/ton/copy.ts` (pt-BR direto, formatação
    `Intl` pt-BR e fuso America/Sao_Paulo). Nenhuma chave nova nos catálogos.
  - A regra `i18n/no-raw-jsx-text` é desligada para `src/views/ton`, `src/lib/ton`
    e `src/app/ton`.
  - O next-intl continua como mecanismo das telas herdadas do Onyx (admin, chat
    nativo): remover a dependência tocaria 500+ arquivos sem ganho para o cliente,
    e com o locale fixo essas telas já renderizam em pt-BR.

---

# D-007 — Rotas canônicas

Status: Accepted (2026-10-01).

## Deve responder

Quais serão as rotas finais para:
- Home;
- Assistente;
- Fechamento;
- DRE;
- Pendências;
- Fontes;
- Automações;
- Relatórios;
- Admin.

Rotas antigas devem ser redirecionadas ou removidas somente após equivalente estável.

## Decisão
| Superfície | Rota |
| --- | --- |
| Visão Geral | `/ton` |
| Assistente | `/ton/chat` |
| Fechamento | `/ton/fechamento` |
| DRE | `/ton/dre` |
| Pendências | `/ton/pendencias` |
| Automações | `/ton/automacoes` (`/ton/rotinas` redireciona) |
| Relatórios | `/ton/relatorios`; viewer `/ton/controladoria/reports/{id}` (URL emitida pelo backend) |
| Fontes | `/ton/fontes` (`/ton/data-sources` redireciona) |
| Especialistas | `/ton/especialistas` (secundária) |
| Diagnóstico | `/ton/cobertura` (admin) |
| Admin | `/admin/*` |

`/ton/controladoria` redireciona para `/ton`.

---

# D-008 — Right rail

Status: Accepted (2026-10-01).

## Deve responder

O right rail da referência será:
- permanente em desktop;
- contextual;
- apenas Home/Chat;
- removido em favor de drawers;
- outra solução.

A decisão deve levar em conta densidade e responsive.

## Decisão
Contextual: só na Visão Geral e no estado inicial do Assistente, a partir de `xl`
(1280px). Blocos: Fontes (estado real), Automações (R3 real), Especialistas (status
real). Abaixo de `xl` o rail some no Assistente e desce para o fluxo na Visão Geral.
Nenhum canal (WhatsApp) ou VPN é exibido como conectado.

---

# D-009 — Dados sintéticos

Status: Accepted (2026-10-01).

## Deve responder

Como indicar ambiente/demo sintético sem poluir cada card?

Preferência:
- banner/indicator global;
- dados continuam visualmente normais;
- nenhum valor sintético tratado como resultado real.

## Decisão
Um indicador único no header: "Ambiente de demonstração — dados sintéticos", exibido
quando o backend declara o contexto sintético (`closing.data_context`). Cards e
tabelas não repetem o aviso. Relatórios mantêm o contexto no cabeçalho do documento,
porque circulam fora da tela.

---

# Log de decisões

Adicionar decisões novas abaixo.

## Template

```text
## D-XXX — Título

Data:
Status: Accepted / Rejected / Superseded

Contexto:

Decisão:

Alternativas consideradas:

Motivo:

Consequências:

Validação:
```

## D-010 — Inspeção com dados reais no navegador

Data: 2026-10-01
Status: Accepted

Contexto: a conta de teste do Playwright (`admin_user@example.com`) não tem permissões
TON. Conceder acesso via SQL foi negado pelo classificador de permissões.

Decisão: inspeção visual usa a sessão do usuário autorizado no Chrome (login feito com
credenciais fornecidas pelo usuário) e um `next dev` local na porta 3005 contra a mesma
API (cookies de `localhost` valem para qualquer porta). Nenhuma permissão foi alterada.

Consequências: validações de browser deste rebuild usam a base sintética real.

## D-011 — Remoção do frontend TON legado

Data: 2026-10-01
Status: Accepted

Contexto: após as superfícies novas estarem estáveis e validadas no Chrome e no
Playwright, o shell antigo e as views Controladoria/Rotinas/R3Execution ficaram sem rota.

Decisão: removidos TonChrome, sections/sidebar/TonSidebar, views/ton/ControladoriaPage
(incl. ReportPage e CapabilitiesPanel), views/ton/RoutinesPage e R3Execution. Os testes
do ciclo de execução R3 foram portados para R3Spotlight. As views admin
`/admin/dre` e `/admin/financial-readiness` permanecem como superfícies técnicas de
administração; DataSourcesPage permanece como dona do diálogo de upload reutilizado.

Consequências: nenhuma rota cliente renderiza layout legado; rotas antigas do TON
redirecionam (D-007).

## D-012 — Respostas do coordenador sem identificadores internos

Data: 2026-10-01
Status: Accepted

Contexto: o prompt do coordenador pedia identificadores "como referências de
evidência", e as respostas mostravam UUIDs — proibido pelo critério visual.

Decisão: o prompt passa a proibir UUIDs/run_id na resposta e a rastreabilidade fica
no relatório (seção colapsada). Regras financeiras, ferramentas, especialistas e
limites de aprovação não mudaram.

Aplicação local: imagem `onyxdotapp/onyx-backend:latest` reconstruída do repositório
(rollback em `:pre-fe001`), `api_server` e `background` recriados, nginx reiniciado e a
Persona TON reprovisionada por `POST /api/ton/agent/provision`. Em outro ambiente, o
mesmo passo de reprovisionamento é necessário depois do deploy do backend.

Validação: Playwright fe001 verifica que a resposta da análise não contém UUID.

## D-013 — DRE pronta na demonstração

Data: 2026-10-01
Status: Accepted

Contexto: a roadmap permite mostrar uma DRE READY sintética se houver fixture segura.
Na base atual, inclusive a unidade de demonstração `SYN-READY-UNIT`, todos os
escopos estão "Não pronto" (13 e 14 bloqueios).

Decisão: não fabricar estado pronto. A demo mostra o bloqueio honesto; a experiência
de DRE pronta (tabela hierárquica, variação, YTD, drill-down, export) continua
disponível no código existente e coberta por testes, e aparece sozinha quando uma
base ficar pronta.

## D-014 — Chat genérico /app e configurações

Data: 2026-10-01
Status: Accepted

Decisão: `/app` (chat Onyx genérico, catálogo de agentes, configurações) continua
existindo para administração e compatibilidade, mas nenhum caminho do cliente leva
até ele: login, "/", retorno do admin e menu de conta apontam para o TON. Rotas
admin continuam protegidas por permissão no backend; esconder links não é controle
de segurança.

---

# TON-FE-002 — decisões de maturidade de produto

## D-015 — Administração do TON separada da administração técnica

Data: 2026-10-01
Status: Accepted

Contexto: o rodapé da sidebar levava o administrador direto ao admin genérico do Onyx
e mostrava "Diagnóstico de cobertura" ao lado da navegação do produto.

Decisão: nova rota `/ton/administracao` dentro do shell TON, com as configurações de
produto (acesso, fontes, automações, especialistas, prontidão financeira, estrutura da
DRE, relatórios, cobertura do Prompt Mestre, assistente) e um bloco separado
"Administração técnica" que leva ao `/admin/*` do Onyx. Itens que ainda vivem no admin
técnico (usuários, prontidão, estrutura da DRE) aparecem marcados como "Técnica".
A cobertura do Prompt Mestre só é alcançada por essa página e é negada a não-admins
também na própria rota. O menu da conta mostra as duas entradas para admins.

Alternativas: reconstruir todas as telas admin dentro do TON (custo alto, risco de
regressão em RBAC) — rejeitada; o roadmap pede separação, não reescrita.

Consequências: cliente comum não vê nenhuma entrada de administração. Esconder links
continua não sendo controle de segurança; as rotas `/admin/*` e as APIs seguem
protegidas no backend.

## D-016 — Eventos e notificações derivados de estado persistido

Data: 2026-10-01
Status: Accepted

Decisão: `lib/ton/activity.ts` monta o feed só a partir de registros existentes —
publicações de relatório, importações (concluídas e falhas) e execuções de
especialistas. A Visão Geral e o sino do header usam o mesmo feed. "Novo" é marcado
por usuário via `localStorage` (conveniência local; sem storage o feed continua
funcionando). Nenhum evento é simulado e não há backend de notificações novo.

## D-017 — Busca e comandos

Data: 2026-10-01
Status: Accepted

Decisão: `Ctrl+K` abre `TonCommandMenu`, construído sobre o `CommandMenu` já usado
pelo Onyx (teclado, foco, highlight). Comandos: páginas do produto, "Analisar
fechamento", "Mostrar último relatório", conversas do coordenador TON e "Perguntar ao
TON: …" com o texto digitado, que abre o Assistente com a pergunta.

## D-018 — Tokens TON em :root

Data: 2026-10-01
Status: Accepted

Contexto: popovers e diálogos são portados para fora de `.ton-shell`, onde as
variáveis `--ton-*` não existiam (links verdes saíam pretos dentro do popover).

Decisão: as variáveis ficam em `:root` (e o ajuste escuro em `.dark`). Só nomes
`--ton-*` são definidos; telas não-TON não os usam.

## D-019 — Login controlado e identidade Vale Norte

Data: 2026-10-01
Status: Accepted

Contexto: modelo de autenticação local = senha (basic), sem SSO, sem SMTP
(`NEXT_PUBLIC_FORGOT_PASSWORD_ENABLED` desligado), deploy interno da Vale Norte.

Decisão:
- `AuthFlowContainer` vira layout TON em duas colunas (painel verde Vale Norte com
  logo oficial invertido + formulário neutro). Vale para login, cadastro, convite e
  redefinição de senha.
- O login não oferece "Criar uma conta"; mostra "Acesso restrito" (contas criadas
  pelo administrador do TON). As rotas `/auth/signup` e `/auth/join` continuam para o
  primeiro usuário e convites — a semântica de autenticação não mudou.
- Sem SMTP não há recuperação self-service; o login diz para falar com o
  administrador. Com a flag ligada, o link "Esqueceu a senha" do Onyx volta.
- Falha de login fica visível no formulário (alerta inline), além do toast.

Dívida: o backend basic auth ainda aceita cadastro direto em `/auth/signup`. Fechar
isso é decisão de autenticação (ex.: domínio permitido ou convite obrigatório) e
fica para o responsável pelo deploy.

## D-020 — Workspace DRE nativo do TON

Data: 2026-10-01
Status: Accepted

Contexto: `/ton/dre` embutia `views/admin/DrePage` (selects administrativos, revisões com
prefixo de UUID, cartões genéricos).

Decisão: `views/ton/DrePage` passa a ter workspace próprio. `useDreWorkspace` usa os
mesmos endpoints e a mesma regra de seleção da view admin (última normalização e
estrutura; só um cálculo READY que casa com ambas é oficial). A UI:
- bloqueada: título "DRE de <mês> ainda não pode ser publicada", total, cartões por
  categoria (Unidades, Dotação, Conciliação, Realizado) com contagem, explicação e
  "Resolver" que abre a fila já filtrada pelo código do bloqueio (ou categoria);
  "Recalcular DRE" com retorno explícito do resultado; "Perguntar ao TON".
- pronta: KPIs do mês com acumulado, tabela hierárquica com grupos Mês/Acumulado,
  variação e %, colapso de níveis, drill-down em painel lateral (lançamentos com
  conta, unidade, data, arquivo, planilha/linha e revisão), evolução no ano e
  exportação CSV. Versão mostrada por número da estrutura e data — sem IDs.
- base/estrutura só aparecem para admin, recolhidas.
A view admin continua em `/admin/dre`. Nenhum valor é calculado no React.

Validação: Chrome (estado bloqueado real, 13 itens); jest cobre o estado pronto com
fixture (D-013: a base local não tem período pronto).
