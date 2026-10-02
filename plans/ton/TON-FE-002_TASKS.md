# TON-FE-002 — Task Tracker

## Status
- `[x]` done
- `[~]` partial/in progress
- `[!]` blocked
- `[ ]` not started
- `[d]` deferred

---

# 0. Session

Baseline HEAD:
`ea11f7be6d`

Branch:
`main` (local only, no push)

Working tree:
limpo, exceto os dois arquivos de plano TON-FE-002 (não rastreados, entrada desta tarefa)

Reference:
`plans/ton_reference_visual*`

Current milestone:
`M0 — auditoria`

---

# 1. Audit

- [x] route tree
- [x] layout tree
- [x] design tokens
- [x] component primitives
- [x] navigation
- [x] auth
- [x] chat
- [x] sources
- [x] DRE
- [x] readiness/pending
- [x] routines
- [x] reports
- [x] specialists
- [x] admin
- [x] branding
- [x] i18n removal
- [x] responsive
- [x] accessibility
- [x] client-visible Onyx remnants

### Audit decision
```text
Auditoria em Chrome real (next dev :3005 contra a API local, sessão do usuário autorizado)
e no código, 2026-10-01.

Base herdada do FE-001 é sólida: shell próprio (/ton), tokens em ton.css, primitives em
views/ton/components/ui.tsx, copy pt-BR em lib/ton/copy.ts, runtime de chat nativo com
slots de apresentação. O FE-002 amadurece em cima disso — não há razão para novo rebuild.

Gaps encontrados (por gravidade):
1. DRE: /ton/dre embute views/admin/DrePage (selects "Período/Escopo", "Opções avançadas",
   "Não pronto", cartões cinza, IDs de revisão truncados). Lê como tela admin, não como
   software financeiro. → reconstruir workspace DRE TON sobre os mesmos endpoints.
2. Assistente: popover de ações do composer lista as ferramentas técnicas (ton_*) para o
   cliente; não há barra de contexto (o que o TON está analisando); não há ações de
   continuidade após a resposta; cabeçalho "Executado em 17s · 4 etapas" do timeline Onyx
   duplica o resumo TON; "LIMITAÇÃO"/"SITUAÇÃO" em caixa alta Markdown.
3. Login: cartão genérico do Onyx, em modo escuro o logo some, link "Criar uma conta"
   exposto (deploy controlado), sem recuperação de senha (sem SMTP), sem identidade.
4. Administração: rodapé da sidebar leva direto ao admin técnico do Onyx; "Diagnóstico de
   cobertura" aparece na navegação. Não há "Administração do TON" de produto.
5. Header: sem notificações, ajuda ou busca/comandos; só demo + fontes + conta.
6. Pendências: linhas genéricas "Item de conciliação" com botão "Analisar"; precisa ser fila
   de trabalho (o que aconteceu / o que decidir / impacto) com filtros.
7. Home: R3 e fontes repetidos (spotlight + rail + strip); rail com rolagem interna dupla.
8. Fontes: cartões grandes por fonte; falta resumo de saúde no topo.
9. Automações: histórico lista 5 execuções sem agrupamento por dia; catálogo de rotinas
   bloqueadas em grade grande.
10. Relatórios: catálogo ok; "Ver versões anteriores (21)" sinaliza execuções repetidas.
11. Especialistas: na navegação primária; roadmap prefere contexto.
12. Polimento: títulos de página fixos ("TON — Vale Norte"), not-found genérico.

Sem gaps: i18n (pt fixo, D-006), branding no shell, rotas canônicas (D-007), RBAC (gates
de backend; UI espelha).

Ordem escolhida: shell/sistema → login → assistente → DRE/pendências → fontes/automações
→ relatórios/especialistas → administração → polimento/responsivo.
```

---

# 2. Design system

- [x] global tokens consolidated
- [x] typography hierarchy
- [x] card primitives
- [x] status badges
- [x] KPI
- [x] buttons
- [x] modal/drawer
- [x] alerts
- [x] loading
- [x] empty
- [x] error
- [x] table
- [x] timeline/activity
- [x] structured evidence
- [x] artifact
- [x] source
- [x] routine
- [~] specialist

---

# 3. Navigation / shell

- [x] final information architecture
- [x] active state
- [x] back behavior
- [x] deep links
- [x] no duplicate concepts
- [x] no generic Onyx client nav
- [x] technical diagnostics moved away from client
- [x] admin escape hatch role-gated

---

# 4. Header / global status

- [x] Vale Norte + TON
- [x] environment indicator
- [x] real sync freshness
- [x] notifications
- [x] help
- [x] user menu

---

# 5. Login

- [x] branded login
- [x] no test credentials exposed
- [x] account creation behavior audited
- [~] password recovery
- [x] loading
- [x] auth error
- [x] post-login routing

---

# 6. Home

- [x] executive strip
- [x] attention queue
- [x] TON activity
- [x] R3 spotlight
- [x] source health
- [x] latest report
- [x] specialist context
- [x] reduced duplication
- [x] meaningful healthy state

---

# 7. Assistant

- [x] custom workspace
- [x] context bar
- [x] specialist focus
- [~] structured outputs
- [x] rich evidence
- [x] artifact cards
- [x] follow-up actions
- [~] meaningful history
- [x] grouped execution states
- [x] tool trace hidden
- [x] file flow
- [x] Code Interpreter preserved
- [x] cancellation
- [~] long response UX

---

# 8. Closing / DRE

- [x] closing overview
- [x] blocked DRE
- [x] blocker cards
- [x] blocker → pending filter
- [x] ready DRE
- [x] hierarchy
- [x] monthly
- [x] YTD
- [x] variance
- [x] source drilldown
- [x] export
- [x] no internal enums

---

# 9. Pending decisions

- [x] work queue
- [~] filters
- [x] category views
- [x] source context
- [x] affected records
- [x] candidate/suggestion
- [x] impact
- [x] review
- [x] justify
- [x] confirm
- [~] audit

---

# 10. Sources

- [x] integration health model
- [x] current acquisition state
- [x] freshness
- [x] warnings
- [x] NG current truth
- [x] NG direct integration pending state
- [x] guided upload
- [x] processing lifecycle
- [x] history drawer/table
- [x] no fake connectivity

---

# 11. Automations

- [x] automation home
- [x] R3 flagship
- [x] schedule from backend
- [x] next run
- [x] last run
- [x] lifecycle state
- [x] history
- [x] execute-now feedback
- [x] other routines by readiness
- [x] technical trace secondary

---

# 12. Reports

- [x] grouped catalog
- [x] latest first
- [x] revision history
- [x] branded viewer
- [x] executive summary
- [x] findings
- [x] actions
- [x] sources
- [x] traceability
- [x] print
- [x] download

---

# 13. Specialists

- [x] canonical nine
- [x] runtime status
- [x] specialist activity context
- [x] focused analysis
- [x] no fake chat
- [~] detail view
- [x] source/capability explanation
- [x] no Onyx Persona terminology in client

---

# 14. Activity / notifications

- [x] event model
- [x] header notifications
- [x] import events
- [x] automation events
- [d] DRE state events
- [x] report events
- [d] decision events
- [x] spam control

---

# 15. Search / command

- [x] product search
- [x] route-independent commands
- [x] natural commands
- [~] contextual search
- [x] reuse existing infrastructure where possible

---

# 16. Admin / configuration

- [x] TON administration boundary
- [x] technical administration boundary
- [~] branded/admin shell
- [x] user access
- [x] source configuration
- [~] automation config
- [x] specialist availability
- [x] financial readiness controls
- [~] report settings
- [d] audit
- [x] technical Onyx admin remains available
- [x] normal client cannot access technical admin

---

# 17. Global states

- [x] loading
- [x] empty
- [x] success
- [x] partial
- [x] warning
- [x] error
- [x] unauthorized
- [d] degraded connection
- [x] background execution feedback

---

# 18. Responsive/accessibility

- [x] 1440+
- [x] 1280
- [x] 1024
- [x] 768
- [x] 390
- [x] no horizontal scroll
- [~] keyboard
- [x] focus
- [~] modal trap
- [~] contrast
- [x] semantic controls

---

# 19. Production polish

- [x] titles
- [x] favicon
- [x] metadata
- [d] manifest
- [x] loading/splash
- [~] error pages
- [x] not-found
- [x] auth failure
- [x] no 0.0.0-dev client text
- [x] no UUIDs
- [x] no raw JSON
- [x] no provider branding
- [x] no Onyx branding

---

# 20. UI/backend truth matrix

## DRE
API: GET /api/ton/financial-domain/normalizations/{run}/readiness?structure_version_id (periods[].status,
blockers); GET /api/ton/dre/calculations?period (READY run matching normalization+structure);
GET /calculations/{id}/statement; /series; /lines/{code}/contributors; export.csv.
UI: views/ton/DrePage/useDreWorkspace → blocked cards (groupBlockers) or statement/KPIs/drill-down.
Transformação: só agrupamento por categoria e formatação BRL/%. Nenhum valor calculado no React.
PASS: Chrome (bloqueada, 13 itens reais); jest (pronta, fixture).

## Sources
API: GET /api/ton/data-sources (status, last_success_at, latest, history);
GET /api/ton/agent/closing (sources[].direct_integration).
UI: SourcesPage HealthSummary + SourceRow; header SourcesStatus.
PASS: Chrome — 3/3 atualizadas por arquivo; NG direto "Aguardando acesso e configuração".

## R3
API: GET /api/ton/agent/routines (status, schedule, next_run); GET /routines/R3/latest;
POST /routines/R3/run; GET /api/ton/agent/reports?limit=25 (routine_code=R3) para histórico;
GET /routines/R3/schedule (admin).
UI: R3Spotlight, AutomationsPage R3History (agrupado por dia), AdminPage.
PASS: Chrome — próxima 03/11/2026 08:00, histórico real de execuções.

## Specialists
API: GET /api/ton/agent/specialists; GET /api/ton/agent/closing (specialists[]).
UI: SpecialistsPage, Home InvolvedSpecialists (só status não neutro), barra de contexto (foco).
PASS: Chrome — CFO parcial, AUDITOR e CEO operacionais, 6 aguardando fonte.

## Reports
API: GET /api/ton/agent/reports/groups; /reports/{id}; /reports/{id}/history; /download.
UI: ReportsPage, ReportViewer (impressão, versões anteriores, IDs só para admin).
PASS: Chrome — versão atual + 21 anteriores preservadas.

## Notifications
API: derivado de reports/groups, data-sources (history), specialists (last_execution).
UI: lib/ton/activity.ts → Home "Atividade do TON" e sino do header; "novo" via localStorage.
PASS: Chrome — eventos reais; badge após nova publicação.

---

# 21. Browser QA

- [x] login
- [x] Home
- [x] Assistant
- [x] Closing
- [x] DRE
- [x] Pendências
- [x] Sources
- [x] Automations
- [x] Reports
- [x] Specialists
- [x] Admin as authorized role
- [!] client role
- [x] full natural demo journey
- [x] reference visual comparison

---

# 22. Quality

- [x] focused frontend tests
- [d] focused backend tests when touched
- [x] TypeScript
- [x] lint
- [x] format
- [!] build
- [x] git diff --check

---

# 23. Progress log

Append, never rewrite:

```text
### YYYY-MM-DD HH:mm
Milestone:
Commit:
What changed:
What is demonstrable:
Validation:
Known issues:
Next:
```

---

# 24. Blockers

```text
- Validação com papel cliente (sem admin) não feita: a conta de teste do Playwright não tem
  permissões TON e conceder via SQL foi negado no FE-001 (D-010). Telas escondem admin por
  hasAdminAccess e as rotas/APIs continuam protegidas no backend.
- Build de produção da imagem web não refeito nesta sessão (memória do WSL; ver memória
  docker-sequential-startup). Validação feita em next dev :3005 contra a API local.
- DRE pronta não demonstrável na base local (D-013); coberta por testes.
```

---

# 25. External dependencies

Record only real external dependencies:

- NG/Keevo VPN/API/read-only DB
- approved real data
- fleet sources
- contract sources
- procurement
- compliance
- RH
- Zeev official integration details

```text
- NG/Keevo: acesso VPN/API ou base de leitura (Fontes mostra o caminho como pendente).
- Amostra real aprovada da Vale Norte.
- Fontes de frota, contratos, produção, compras, compliance e RH (especialistas e R1, R2, R4–R9).
- SMTP para recuperação de senha self-service.
- Decisão de autenticação sobre cadastro direto em /auth/signup (D-019).
```

### 2026-10-01 22:30
Milestone: M1–M3 parcial — shell/admin, login, assistente (parte 1).
Commits: 67dd9a755c (auditoria), 36441395a3 (shell, busca Ctrl+K, notificações,
Administração do TON), 020d3a7b3d (login controlado Vale Norte), commit atual
(assistente sem seletor de ferramentas técnicas e sem timeline duplicada).
Validation: Chrome real (:3005) — header, notificações, Ctrl+K, admin, login com
erro inline; tsc limpo; jest TON + mensagens 430/430; jest auth 9/9.
Known issues: limite de uso atingido — interrompido aqui.
Next: barra de contexto e ações de continuidade no Assistente; workspace DRE
nativo (substituir views/admin/DrePage embutida); Pendências como fila de
trabalho; Fontes (resumo de saúde); Automações (histórico por dia); Relatórios;
Especialistas; Home sem duplicação; responsivo 1024/768/390; títulos por página.

### 2026-10-02 03:00
Milestone: M3–M8 — assistente, DRE, pendências, fontes, automações, home, relatórios, polimento.
Commits: 6ac8f5aa32 (contexto e continuidade no assistente), 0485bbfa63 + 22a32ea5df (workspace
DRE), fdc4f82c44 (pendências como fila guiada), 39afa9ce5e (fontes/saúde), 0c72b54c6e
(automações), 3d14f0986e (home sem duplicação), 2932d4009c (relatório imprimível + versões),
6f4163d2af (títulos + not-found), b2b7071c3a (header em 390px), 2c61b990fa (cartões após a
resposta), eb66f1dffe (lint/format).
What is demonstrable: Home → pergunta → Assistente (barra de contexto, progresso por fases,
evidência, relatório, "Continuar em") → Pendências (fila guiada, etapas da decisão) → DRE
(bloqueio por categoria com links para a fila) → Automações (R3, histórico por dia) →
Relatório (impressão, versões) → Fontes (saúde e caminho NG).
Validation: Chrome real :3005 em todas as telas; 390/768/1024 sem rolagem horizontal (iframes
de mesma origem); tsc limpo; oxlint sem erros nos diretórios tocados; oxfmt; jest 462/462
(--maxWorkers=4; com 20 workers dois suites estouram timeout no transform frio).
Known issues: resposta do modelo às vezes começa com preâmbulo ("Antes de qualquer número…")
e cabeçalhos em caixa alta — conteúdo do LLM/prompt, não da UI; "Fontes atualizadas" no
header considera só fontes configuradas.
Next (P1): filtros por período/resolvidas em Pendências; detalhe por especialista; trilha de
auditoria de decisões (precisa de endpoint de leitura); manifest/PWA; validação com papel
cliente; build de produção.
