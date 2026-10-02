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

- [ ] global tokens consolidated
- [ ] typography hierarchy
- [ ] card primitives
- [ ] status badges
- [ ] KPI
- [ ] buttons
- [ ] modal/drawer
- [ ] alerts
- [ ] loading
- [ ] empty
- [ ] error
- [ ] table
- [ ] timeline/activity
- [ ] structured evidence
- [ ] artifact
- [ ] source
- [ ] routine
- [ ] specialist

---

# 3. Navigation / shell

- [ ] final information architecture
- [ ] active state
- [ ] back behavior
- [ ] deep links
- [ ] no duplicate concepts
- [ ] no generic Onyx client nav
- [ ] technical diagnostics moved away from client
- [ ] admin escape hatch role-gated

---

# 4. Header / global status

- [ ] Vale Norte + TON
- [ ] environment indicator
- [ ] real sync freshness
- [ ] notifications
- [ ] help
- [ ] user menu

---

# 5. Login

- [ ] branded login
- [ ] no test credentials exposed
- [ ] account creation behavior audited
- [ ] password recovery
- [ ] loading
- [ ] auth error
- [ ] post-login routing

---

# 6. Home

- [ ] executive strip
- [ ] attention queue
- [ ] TON activity
- [ ] R3 spotlight
- [ ] source health
- [ ] latest report
- [ ] specialist context
- [ ] reduced duplication
- [ ] meaningful healthy state

---

# 7. Assistant

- [ ] custom workspace
- [ ] context bar
- [ ] specialist focus
- [ ] structured outputs
- [ ] rich evidence
- [ ] artifact cards
- [ ] follow-up actions
- [ ] meaningful history
- [ ] grouped execution states
- [ ] tool trace hidden
- [ ] file flow
- [ ] Code Interpreter preserved
- [ ] cancellation
- [ ] long response UX

---

# 8. Closing / DRE

- [ ] closing overview
- [ ] blocked DRE
- [ ] blocker cards
- [ ] blocker → pending filter
- [ ] ready DRE
- [ ] hierarchy
- [ ] monthly
- [ ] YTD
- [ ] variance
- [ ] source drilldown
- [ ] export
- [ ] no internal enums

---

# 9. Pending decisions

- [ ] work queue
- [ ] filters
- [ ] category views
- [ ] source context
- [ ] affected records
- [ ] candidate/suggestion
- [ ] impact
- [ ] review
- [ ] justify
- [ ] confirm
- [ ] audit

---

# 10. Sources

- [ ] integration health model
- [ ] current acquisition state
- [ ] freshness
- [ ] warnings
- [ ] NG current truth
- [ ] NG direct integration pending state
- [ ] guided upload
- [ ] processing lifecycle
- [ ] history drawer/table
- [ ] no fake connectivity

---

# 11. Automations

- [ ] automation home
- [ ] R3 flagship
- [ ] schedule from backend
- [ ] next run
- [ ] last run
- [ ] lifecycle state
- [ ] history
- [ ] execute-now feedback
- [ ] other routines by readiness
- [ ] technical trace secondary

---

# 12. Reports

- [ ] grouped catalog
- [ ] latest first
- [ ] revision history
- [ ] branded viewer
- [ ] executive summary
- [ ] findings
- [ ] actions
- [ ] sources
- [ ] traceability
- [ ] print
- [ ] download

---

# 13. Specialists

- [ ] canonical nine
- [ ] runtime status
- [ ] specialist activity context
- [ ] focused analysis
- [ ] no fake chat
- [ ] detail view
- [ ] source/capability explanation
- [ ] no Onyx Persona terminology in client

---

# 14. Activity / notifications

- [ ] event model
- [ ] header notifications
- [ ] import events
- [ ] automation events
- [ ] DRE state events
- [ ] report events
- [ ] decision events
- [ ] spam control

---

# 15. Search / command

- [ ] product search
- [ ] route-independent commands
- [ ] natural commands
- [ ] contextual search
- [ ] reuse existing infrastructure where possible

---

# 16. Admin / configuration

- [ ] TON administration boundary
- [ ] technical administration boundary
- [ ] branded/admin shell
- [ ] user access
- [ ] source configuration
- [ ] automation config
- [ ] specialist availability
- [ ] financial readiness controls
- [ ] report settings
- [ ] audit
- [ ] technical Onyx admin remains available
- [ ] normal client cannot access technical admin

---

# 17. Global states

- [ ] loading
- [ ] empty
- [ ] success
- [ ] partial
- [ ] warning
- [ ] error
- [ ] unauthorized
- [ ] degraded connection
- [ ] background execution feedback

---

# 18. Responsive/accessibility

- [ ] 1440+
- [ ] 1280
- [ ] 1024
- [ ] 768
- [ ] 390
- [ ] no horizontal scroll
- [ ] keyboard
- [ ] focus
- [ ] modal trap
- [ ] contrast
- [ ] semantic controls

---

# 19. Production polish

- [ ] titles
- [ ] favicon
- [ ] metadata
- [ ] manifest
- [ ] loading/splash
- [ ] error pages
- [ ] not-found
- [ ] auth failure
- [ ] no 0.0.0-dev client text
- [ ] no UUIDs
- [ ] no raw JSON
- [ ] no provider branding
- [ ] no Onyx branding

---

# 20. UI/backend truth matrix

## DRE
API:
UI:
PASS:

## Sources
API:
UI:
PASS:

## R3
API:
UI:
PASS:

## Specialists
API:
UI:
PASS:

## Reports
API:
UI:
PASS:

## Notifications
API:
UI:
PASS:

---

# 21. Browser QA

- [ ] login
- [ ] Home
- [ ] Assistant
- [ ] Closing
- [ ] DRE
- [ ] Pendências
- [ ] Sources
- [ ] Automations
- [ ] Reports
- [ ] Specialists
- [ ] Admin as authorized role
- [ ] client role
- [ ] full natural demo journey
- [ ] reference visual comparison

---

# 22. Quality

- [ ] focused frontend tests
- [ ] focused backend tests when touched
- [ ] TypeScript
- [ ] lint
- [ ] format
- [ ] build
- [ ] git diff --check

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
None recorded yet.
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
TBD
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
