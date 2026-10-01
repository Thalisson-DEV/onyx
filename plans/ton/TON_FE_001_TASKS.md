# TON-FE-001 — Task Tracker

Este arquivo é o quadro vivo de execução do rebuild.

## Convenção
- `[x]` concluído
- `[~]` em andamento/parcial
- `[!]` bloqueado
- `[ ]` não iniciado
- `[d]` adiado deliberadamente

---

# 0. Sessão

Branch inicial:
`main`

HEAD inicial:
`8da8b16412` (test(ton): validate UX-002 browser journeys and runtime truth)

Working tree:
Somente os três documentos deste rebuild estavam untracked (`plans/ton/TON_FE_001_*.md`,
`plans/ton/TON_FRONTEND_REBUILD_ROADMAP.md`). Nenhum trabalho alheio pendente.

Referência visual encontrada em:
`plans/ton/ton_reference_visual.jpg` (os documentos citam `plans/`, o arquivo real está em `plans/ton/`).

Estratégia arquitetural escolhida:
B — route group `/ton` isolado dentro do app Next.js atual, com shell TON próprio
(`web/src/views/ton/shell/`) que substitui `TonChrome`/`TonSidebar` (Onyx SidebarLayouts).
Ver D-001.

Motivo:
O runtime de chat (AppPage + useChatController + streaming + tools + files + artifacts)
depende de providers e do RootLayout do app atual. Separar app custaria semanas e
duplicaria auth/streaming. Um layout próprio sob `/ton` troca toda a apresentação
sem tocar no runtime.

Milestone atual:
M1 — shell Vale Norte/TON + entrada do produto.

Última atualização:
2026-10-01 18:37

---

# 1. Auditoria

- [x] estrutura atual do frontend inspecionada
- [x] boundary atual TON identificado
- [x] acoplamentos com shell Onyx identificados
- [x] auth/RBAC mapeados
- [x] conversation runtime mapeado
- [x] streaming/event packets mapeados
- [x] files/Code Interpreter mapeados
- [x] artifacts mapeados
- [x] specialist runtime/context mapeado
- [x] source APIs mapeadas
- [x] DRE APIs mapeadas
- [x] readiness APIs mapeadas
- [x] routine APIs mapeadas
- [x] report APIs mapeadas
- [x] branding/i18n mapeados
- [x] client/admin boundary mapeado
- [x] estratégia do rebuild decidida

### Notas do audit
```text
Current frontend structure:
- web/src/app/ton/* : rotas finas que reexportam views. /ton redireciona para
  /ton/controladoria. /ton/dre e /ton/pendencias reexportam views de admin
  (views/admin/DrePage 1257 linhas, views/admin/FinancialReadinessPage 967 linhas).
- web/src/layouts/chromes/TonChrome.tsx + sections/sidebar/TonSidebar.tsx: usam
  RootLayout/SidebarLayouts do Onyx (sidebar cinza genérica, logo TON genérico).
- /ton/chat monta AppPage nativo dentro de AppChrome (header Onyx, seletor
  "deepseek", rodapé "TON 0.0.0-dev").
- views/ton/*: páginas de Controladoria, Fontes, Rotinas, Relatórios, Especialistas,
  Cobertura — pilhas de caixas com borda e texto (visual Markdown).
- Login cai em /app (chat Onyx genérico), não no TON. "/" redireciona para /app.

Reusable infrastructure:
- AppPage/useChatController/ChatUI: sessão, streaming, tool calls, arquivos,
  Code Interpreter, artifacts, cancelamento. Já roteia /ton/chat.
- TonToolCard/TonExecutionSummary: renderização executiva de tools ton_*.
- APIs: /api/ton/agent/{configuration,closing,routines,specialists,capabilities,
  reports,reports/groups,routines/R3/run,routines/R3/latest};
  /api/ton/data-sources; /api/ton/financial-domain/*; /api/ton/dre/*.
- useR3Execution (retry token idempotente + retomada após refresh).
- Tokens Vale Norte já existem em primitives (--vale-norte-green-*, --vale-norte-gold-*).
- labels.ts: mapeamento enum -> pt-BR.

High-risk coupling:
- AppPage é monolítico (1120 linhas); welcome/sugestões/seletor de modelo são
  internos. Exige slots opcionais, sem fork.
- useChatController decide caminho de sessão por pathname (/ton/chat).
- RootLayout.Root do Opal é exigido por partes do chat (RightPanel de documentos).
- Locale vem do cookie NEXT_LOCALE; sem cookie cai em "en".

Runtime truth (2026-10-01, conta admin autorizada):
- closing: julho/2026, Consolidado, dados sintéticos, DRE "Pendente",
  13 bloqueios (Unidade 2, Orçamento 2, Conciliação 3, Sem realizado 6).
- Especialistas: CFO Parcial; AUDITOR/CEO Operacional; seis "Aguardando fonte".
- Rotinas: R3 Agendada (1º dia útil 08:00 Brasília, próxima 03/11/2026); demais bloqueadas.
- Fontes: 3 fontes, importação manual, NG direto "Aguardando acesso e configuração".
- Relatórios: 2 grupos (Fechamento mensal 13 versões anteriores, Resumo executivo 6).

Chosen rebuild boundary:
B — /ton route group com shell TON próprio; AppPage reaproveitado com slots
(welcome, sugestões, ocultar seletor de modelo). Ver D-001/D-002.
```

---

# 2. Foundation / Shell

- [x] logo oficial Vale Norte local
- [x] branding Onyx removido da experiência cliente
- [x] tokens TON definidos/reusados
- [x] shell TON novo
- [x] header
- [x] sidebar
- [x] right rail strategy
- [x] responsive shell
- [x] navegação cliente simples
- [x] admin role-gated
- [x] nenhuma navegação genérica Onyx no cliente

### Demonstrável
```text
Shell TON próprio em todas as rotas /ton: header verde Vale Norte (logo oficial,
badge TON, tagline, indicador único de demonstração, status real das fontes,
menu de conta), sidebar verde (Nova conversa, Visão Geral, Assistente,
Fechamento > DRE/Pendências, Automações, Relatórios, Fontes, Especialistas,
histórico do coordenador TON), rodapé admin-only (Diagnóstico de cobertura,
Administração). Login e "/" entram em /ton.
```

### Validação
```text
2026-10-01: Chrome 1488px com a conta admin autorizada e dados reais.
tsc sem erros nos arquivos TON; oxfmt; oxlint sem erros; jest TON 222/222
(readiness passa isolado; timeout sob carga no lote completo).
```

---

# 3. Home / Command Center

- [x] landing forte
- [x] faixa executiva
- [x] top attention queue
- [x] atividade recente do TON
- [x] R3 spotlight
- [x] últimos relatórios
- [x] status de fontes
- [x] especialistas envolvidos
- [x] sem visual Markdown
- [x] sem informação duplicada

### Demonstrável
```text
/ton: saudação com nome do perfil, período "Julho de 2026 · Consolidado",
pergunta direta ao TON (abre o Assistente e envia), faixa executiva (DRE
bloqueada 13 itens, Pendências 13 em 4 categorias, Fontes 3/3, próxima automação
03/11 08:00), fila "O que precisa de atenção" com links filtrados, R3 com
Executar agora, atividade real (relatórios, importações, especialistas),
últimos relatórios, right rail com fontes, automações e especialistas reais.
```

### Validação
```text
Chrome 1488px, dados reais. Nenhum UUID, enum ou JSON visível.
```

---

# 4. Assistente TON

- [x] conversation persistence reaproveitada
- [x] streaming reaproveitado
- [x] files reaproveitados
- [x] Code Interpreter preservado
- [x] artifacts preservados
- [x] apresentação de chat própria do TON
- [x] provider/modelo não exposto no cliente
- [x] nova conversa
- [x] histórico pt-BR
- [~] títulos significativos
- [x] sugestões iniciais
- [x] progress summary
- [x] tool trace escondida por padrão
- [x] evidence component
- [ ] finding component
- [x] DRE status component
- [x] source status component
- [ ] pending-decision component
- [ ] routine result component
- [x] report artifact component
- [x] technical details disclosure
- [ ] cancel funciona
- [~] respostas longas legíveis

### Demonstrável
```text
/ton/chat: hero "Olá, sou o TON." com cartão "Tudo pronto", composer sem
seletor de modelo, quatro sugestões da demo, rail de fontes/automações/
especialistas. Conversa real: checklist de fases acima da resposta (Fontes
consultadas, Base financeira validada, DRE verificada, Evidências consolidadas,
Relatório publicado), resposta do coordenador, cartões de evidência e de
relatório abaixo; detalhes por ferramenta e JSON (admin) em disclosure.
```

### Validação
```text
Prompt da demo executado no Chrome com o runtime real (streaming, 13 tool
calls, relatório publicado). jest TonExecutionSummary 5/5.
Pendente: a resposta do modelo ainda cita UUIDs de evidência (prompt da Persona).
```

---

# 5. Especialistas

- [ ] nove especialistas canônicos preservados
- [ ] status vem do runtime
- [ ] shortcuts/contexto desenhados
- [ ] specialist context reutiliza coordenador TON
- [ ] sem nove chats fake
- [ ] capacidades indisponíveis honestas
- [ ] especialistas aparecem nas análises
- [ ] página de especialistas é secundária

### Demonstrável
```text
TBD
```

---

# 6. Fechamento / DRE

- [x] conceito de Fechamento estabelecido
- [x] experiência DRE bloqueada
- [~] experiência DRE pronta
- [x] agrupamento de bloqueios
- [x] blocker → pendência filtrada
- [~] métricas financeiras
- [~] tabela DRE hierárquica
- [~] drill-down
- [~] revision metadata em advanced
- [~] export
- [x] sem enums internos

### Demonstrável
```text
/ton/fechamento: "DRE de julho de 2026 ainda não pode ser publicada", "13 itens
exigem atenção", grade Unidades 2 / Dotação 2 / Conciliação 3 / Realizado 6 (cada
uma abre Pendências filtradas), Resolver pendências, Perguntar ao TON (envia o
prompt ao Assistente), Leitura do TON (Situação, Impacto, Causa, Próxima ação),
achados, R3, especialistas envolvidos e fontes da análise.
/ton/dre: a view DRE existente (estado bloqueado agrupado; estado pronto com
Realizado/Orçado/Variação/YTD, tabela hierárquica, drill-down, export CSV e
revisão em Opções avançadas) embutida no frame do Fechamento.
READY sintética: a unidade de demonstração tem 14 bloqueios na base atual; não há
DRE pronta para exibir, e nada foi fabricado. Estado pronto validado só por testes.
```

---

# 7. Pendências

- [x] work queue clara
- [x] filtros úteis
- [x] origem/contexto
- [x] quantidade afetada
- [x] candidate/sugestão
- [x] modal/drawer de decisão
- [x] justificativa
- [x] consequência da decisão
- [x] sem auto-approval
- [x] sem IDs crus

### Demonstrável
```text
/ton/pendencias: status do período (Não pronta · Julho de 2026 · 13 itens),
tipos de pendência com contagem (Unidades, Períodos da dotação, Conciliação,
Realizado ausente), fila com título de negócio (nunca UUID), registros afetados,
período, evidência humanizada, Analisar → diálogo "Decisão necessária" (o que o
TON encontrou, escopo afetado, sua decisão, justificativa, consequência) com
revisão e confirmação em duas etapas. Conciliação sem decisão pré-selecionada.
Realizado ausente leva a Fontes. Base/estrutura em Opções avançadas.
Validação: Chrome com dados reais (diálogo aberto e fechado, nada registrado);
jest PendingPage 3/3.
```

---

# 8. Fontes

- [ ] cards estilo integração
- [ ] acquisition mode
- [ ] freshness/status
- [ ] quantidade/warnings
- [ ] NG direto honestamente pendente
- [ ] upload
- [ ] resumo de resultado
- [ ] histórico colapsado
- [ ] sem estado fake de VPN/API

### Demonstrável
```text
TBD
```

---

# 9. Automações

- [ ] conceito `Automações`
- [ ] R3 flagship
- [ ] schedule real
- [ ] next run
- [ ] last run
- [ ] execute-now lifecycle
- [ ] completion CTA
- [ ] report CTA
- [ ] outras rotinas agrupadas por readiness
- [ ] código R1–R9 secundário
- [ ] steps técnicos escondidos

### Demonstrável
```text
TBD
```

---

# 10. Relatórios

- [ ] catálogo polido
- [ ] versão atual priorizada
- [ ] histórico de versões colapsado
- [ ] report header profissional
- [ ] executive summary
- [ ] findings
- [ ] actions
- [ ] sources/provenance
- [ ] traceability colapsada
- [ ] download
- [ ] branding Vale Norte + TON
- [ ] não parece Markdown preview

### Demonstrável
```text
TBD
```

---

# 11. Right rail

- [x] estratégia desktop decidida
- [x] fontes
- [x] automação
- [x] status fechamento
- [x] especialistas/alertas quando úteis
- [x] responsive collapse
- [x] nenhum claim falso

---

# 12. Cliente x Admin

- [ ] generic agent catalog oculto de cliente
- [ ] models ocultos
- [ ] MCP/OpenAPI ocultos
- [ ] generic connectors ocultos
- [x] Cobertura removida da nav principal
- [x] admin preservado para autorizado
- [ ] retorno admin → TON

---

# 13. Branding / localização

- [x] Vale Norte logo
- [x] TON product name
- [~] nenhum branding Onyx visível no cliente
- [x] UI cliente pt-BR
- [~] formatação BRL/data/percentual
- [ ] favicon
- [x] browser title
- [~] entry/login coerente
- [x] sem `0.0.0-dev` no cliente

---

# 14. Jornada da demo

## Home
- [x] entrada natural
- [ ] apresentação-ready

## Análise de fechamento
- [x] prompt
- [x] progresso claro
- [x] resposta estruturada

## Evidência
- [ ] card
- [ ] sem JSON

## Pendência
- [x] item
- [x] decisão humana clara

## DRE
- [x] blocked state clara
- [~] READY sintética só se claramente marcada

## R3
- [ ] schedule
- [ ] execute
- [ ] feedback
- [ ] persistência

## Relatório
- [ ] open
- [ ] presentation
- [ ] download

## Fontes
- [ ] NG manual
- [ ] integração direta pendente

---

# 15. Browser QA

- [ ] 1440+
- [ ] ~1024
- [ ] ~768
- [ ] mobile básico
- [ ] loading
- [ ] empty
- [ ] error
- [ ] permission
- [ ] keyboard/focus

---

# 16. Qualidade

- [ ] focused frontend tests
- [ ] focused backend tests se necessário
- [ ] TypeScript
- [ ] lint
- [ ] format
- [ ] build
- [ ] git diff --check
- [ ] demo walkthrough completo

---

# 17. Cleanup do legado

Somente após substituição estável:

- [ ] shell TON antigo removido
- [ ] dashboard antigo removido
- [ ] chat presentation antiga removida se superseded
- [ ] source UI duplicada removida
- [ ] DRE duplicada removida
- [ ] readiness duplicada removida
- [ ] specialist UI obsoleta removida
- [ ] routes antigas redirecionadas
- [ ] nenhum legacy exposto ao cliente

---

# 18. Progress log

Nunca apagar entradas anteriores.

## Template

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

### 2026-10-01 20:40
Milestone: M1 — shell Vale Norte/TON, Visão Geral, Assistente.
Commit: ver `git log` (feat(ton): rebuild client shell, overview and assistant).
What changed:
- Shell TON próprio (views/ton/shell) substitui TonChrome/TonSidebar.
- /ton é a Visão Geral nova; login, "/" e redirect admin entram em /ton.
- Rotas /ton/fontes, /ton/automacoes, /ton/fechamento; antigas redirecionam.
- AppPage ganhou slots de apresentação; /ton/chat usa hero, sugestões e rail TON.
- Execução no chat: checklist de fases acima, cartões ricos abaixo da resposta.
- Locale fixo pt; seletor de idioma oculto; copy TON em lib/ton/copy.ts.
What is demonstrable: Home → Assistente → análise de fechamento com evidência e relatório.
Validation: Chrome com conta admin real; tsc; oxlint; jest TON.
Known issues: resposta do modelo cita UUIDs; Fechamento ainda redireciona para DRE;
DRE/Pendências/Fontes/Automações/Relatórios ainda com layout antigo dentro do shell.
Next: Fechamento + Pendências (work queue e decisão humana).

### 2026-10-01 21:30
Milestone: M2 — Fechamento, DRE no frame, Pendências.
Commit: feat(ton): add closing overview and pending-decision work queue.
What changed: ClosingFrame (abas Visão geral/DRE/Pendências), ClosingPage,
PendingPage (lógica de decisão portada da view admin, mesmos endpoints),
DrePage com modo embedded, label da unidade de demonstração.
What is demonstrable: Home → Fechamento → Pendências filtradas → decisão humana.
Validation: Chrome com dados reais; tsc; oxlint; jest PendingPage 3/3.
Known issues: estado DRE pronto não demonstrável na base atual (sem fixture READY).
Next: Automações, Relatórios, Fontes.

---

# 19. Bloqueios atuais

```text
Nenhum registrado ainda.
```

---

# 20. Dependências externas / reunião

Registrar apenas dependências reais, por exemplo:
- VPN NG/Keevo
- API/read-only DB
- amostra real aprovada
- Zeev oficial
- decisões de autoridade de fonte

```text
TBD
```
