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
P0 concluído; handoff da sessão 2026-10-01.

Última atualização:
2026-10-02 01:10

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
- [x] títulos significativos
- [x] sugestões iniciais
- [x] progress summary
- [x] tool trace escondida por padrão
- [x] evidence component
- [~] finding component
- [x] DRE status component
- [x] source status component
- [d] pending-decision component
- [d] routine result component
- [x] report artifact component
- [x] technical details disclosure
- [x] cancel funciona
- [x] respostas longas legíveis

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

- [x] nove especialistas canônicos preservados
- [x] status vem do runtime
- [x] shortcuts/contexto desenhados
- [x] specialist context reutiliza coordenador TON
- [x] sem nove chats fake
- [x] capacidades indisponíveis honestas
- [x] especialistas aparecem nas análises
- [x] página de especialistas é secundária

### Demonstrável
```text
/ton/especialistas: política "Consultar e recomendar"; Atuando (3): TON CFO Parcial,
TON AUDITOR e TON CEO Operacional, com objetivo, última atuação, o que já faz,
limitações atuais e "Perguntar ao TON" (abre o Assistente com pergunta focada no
domínio; a conversa continua com o coordenador). Aguardando fonte (6): COO, FROTA,
CONTRATOS, COMPLIANCE, PROCUREMENT, RH com a fonte que falta.
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

- [x] cards estilo integração
- [x] acquisition mode
- [x] freshness/status
- [x] quantidade/warnings
- [x] NG direto honestamente pendente
- [x] upload
- [x] resumo de resultado
- [x] histórico colapsado
- [x] sem estado fake de VPN/API

### Demonstrável
```text
/ton/fontes: um cartão por fonte (NG / Lançamentos financeiros, Faturamento /
Notas fiscais, Dotação / Orçamento) com modo de aquisição (Arquivo XLSX/XLS),
última atualização, registros, avisos, bloco "Integração direta" com o estado do
backend (NG: "Aguardando acesso e configuração" + explicação VPN/API/base de
leitura; demais: "Não configurada"), "Alimenta" (Revisão financeira, Prontidão
da DRE, DRE), Atualizar dados (diálogo de upload existente, só com permissão de
importação) e histórico de importações colapsado com detalhe por importação.
Validação: Chrome (histórico abre, upload abre e cancela); jest 1/1.
```

---

# 9. Automações

- [x] conceito `Automações`
- [x] R3 flagship
- [x] schedule real
- [x] next run
- [x] last run
- [x] execute-now lifecycle
- [x] completion CTA
- [x] report CTA
- [x] outras rotinas agrupadas por readiness
- [x] código R1–R9 secundário
- [x] steps técnicos escondidos

### Demonstrável
```text
/ton/automacoes: R3 "Fechamento preliminar mensal" em destaque (Agendada,
1º dia útil 08:00 Brasília com calendário Petrolina-PE, próxima 03/11/2026 08:00,
última execução, último resultado, Executar agora com feedback e retomada após
refresh, Abrir resultado), histórico de execuções R3, aviso de que rotinas não
aprovam decisões, e oito rotinas "Aguardando capacidade" com a dependência real.
Validação: Executar agora no Chrome publicou nova revisão ("Execução concluída",
listas revalidadas); jest 1/1.
```

---

# 10. Relatórios

- [x] catálogo polido
- [x] versão atual priorizada
- [x] histórico de versões colapsado
- [x] report header profissional
- [x] executive summary
- [x] findings
- [x] actions
- [x] sources/provenance
- [x] traceability colapsada
- [x] download
- [x] branding Vale Norte + TON
- [x] não parece Markdown preview

### Demonstrável
```text
/ton/relatorios: versão atual por tipo/período/escopo (Fechamento preliminar
mensal, Resumo executivo), situação, origem (rotina R3 ou Assistente), Abrir,
Baixar, "Ver versões anteriores (N)" expandindo o histórico.
Viewer /ton/controladoria/reports/{id}: documento com logo Vale Norte + TON,
título, contexto de dados, metadados (Período, Escopo, Gerado em, Situação),
resumo executivo, pendências que impedem a publicação (com Resolver), achados,
próximas ações, fontes, especialistas e rastreabilidade colapsada; Baixar relatório.
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

- [x] generic agent catalog oculto de cliente
- [x] models ocultos
- [x] MCP/OpenAPI ocultos
- [x] generic connectors ocultos
- [x] Cobertura removida da nav principal
- [x] admin preservado para autorizado
- [x] retorno admin → TON

---

# 13. Branding / localização

- [x] Vale Norte logo
- [x] TON product name
- [x] nenhum branding Onyx visível no cliente
- [x] UI cliente pt-BR
- [~] formatação BRL/data/percentual
- [x] favicon
- [x] browser title
- [x] entry/login coerente
- [x] sem `0.0.0-dev` no cliente

---

# 14. Jornada da demo

## Home
- [x] entrada natural
- [x] apresentação-ready

## Análise de fechamento
- [x] prompt
- [x] progresso claro
- [x] resposta estruturada

## Evidência
- [x] card
- [x] sem JSON

## Pendência
- [x] item
- [x] decisão humana clara

## DRE
- [x] blocked state clara
- [d] READY sintética só se claramente marcada

## R3
- [x] schedule
- [x] execute
- [x] feedback
- [x] persistência

## Relatório
- [x] open
- [x] presentation
- [x] download

## Fontes
- [x] NG manual
- [x] integração direta pendente

---

# 15. Browser QA

- [x] 1440+
- [x] ~1024
- [x] ~768
- [x] mobile básico
- [x] loading
- [x] empty
- [x] error
- [x] permission
- [x] keyboard/focus

---

# 16. Qualidade

- [x] focused frontend tests
- [x] focused backend tests se necessário
- [x] TypeScript
- [x] lint
- [x] format
- [x] build
- [x] git diff --check
- [x] demo walkthrough completo

---

# 17. Cleanup do legado

Somente após substituição estável:

- [x] shell TON antigo removido
- [x] dashboard antigo removido
- [x] chat presentation antiga removida se superseded
- [d] source UI duplicada removida
- [d] DRE duplicada removida
- [d] readiness duplicada removida
- [x] specialist UI obsoleta removida
- [x] routes antigas redirecionadas
- [x] nenhum legacy exposto ao cliente

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

### 2026-10-01 22:10
Milestone: M3 — Automações, Relatórios, Fontes.
Commit: feat(ton): rebuild automations, reports and sources surfaces.
What changed: AutomationsPage, ReportsPage (catálogo novo), ReportViewer,
SourcesPage (reusa upload/detalhe existentes), revalidação após execução R3,
rotas /ton/automacoes e /ton/fontes apontando para as views novas.
What is demonstrable: jornada completa Home → Assistente → Fechamento →
Pendências → DRE → Automações (Executar agora) → Relatórios → Fontes.
Validation: Chrome com dados reais; tsc; oxlint; jest Sources/Automations 2/2.
Known issues: views antigas ainda no repositório (sem rota); especialistas e
cobertura ainda com layout antigo; resposta do modelo cita UUIDs.
Next: Especialistas, limpeza do legado, responsivo, passada final da demo.

### 2026-10-01 22:50
Milestone: M4 — Especialistas, limpeza do legado, testes da jornada.
Commit: feat(ton): rebuild specialists and retire the legacy TON client.
What changed: SpecialistsPage nova; removidos TonChrome, TonSidebar antigo,
ControladoriaPage (+ReportPage/CapabilitiesPanel), RoutinesPage, R3Execution;
testes do ciclo R3 portados para R3Spotlight; spec Playwright fe001 (jornada
completa e análise com LLM) e TonProductPage substituem ux002/TonWorkspacePage.
What is demonstrable: jornada inteira, inclusive Especialistas.
Validation: tsc do projeto sem erros; jest R3Spotlight 5/5, PendingPage 3/3,
Sources/Automations 2/2, TonExecutionSummary 5/5; Playwright fe001 2/2 contra
http://localhost:3005 com a conta autorizada (TON_E2E_EMAIL/PASSWORD no ambiente).
Known issues: resposta do modelo cita UUIDs; responsivo < 1024 ainda não revisado.
Next: responsivo, login/favicon, histórico completo de conversas, prompt sem UUIDs.

### 2026-10-01 23:40
Milestone: M6 — respostas sem UUID, histórico completo de conversas.
Commit: fix(ton): keep internal identifiers out of assistant answers.
What changed: prompt do coordenador não pede mais identificadores como referência
(links "Abrir relatório"/"Baixar relatório"); imagem backend reconstruída
(rollback: onyxdotapp/onyx-backend:pre-fe001), api_server e background recriados,
nginx reiniciado, Persona TON reprovisionada via POST /api/ton/agent/provision.
Nova página /ton/conversas (busca, agrupamento por data, carregar mais) ligada
em "Ver todas as conversas"; histórico da sidebar limitado a 6.
Validation: Playwright fe001 2/2 com verificação de ausência de UUID na resposta.
Next: passada final, decisões e handoff.

### 2026-10-02 01:10
Milestone: Handoff — build de produção, stack restaurada, validação final.
Commits: 892a7f0d1a (admin → TON), 7b20836c04 (dark mode + D-011..D-014),
b1f250a645 (botão Nova conversa no dark).
What changed: imagem web reconstruída do repositório com a stack parada (o
primeiro build, feito com todos os containers ativos, estourou a memória do WSL
e derrubou o engine; o usuário reiniciou). Containers religados um a um:
relational_db → cache → opensearch → model servers → code-interpreter →
api_server → background → web_server → nginx (~4,3 GB de 5,8 GB).
Rollback: onyx-backend:pre-fe001 e onyx-web-server:pre-fe001.
What is demonstrable: jornada completa em http://localhost:3000 (build de produção).
Validation: Playwright fe001 2/2 contra :3000; foco por teclado visível e em ordem
lógica; modo escuro legível; sem overflow horizontal em 1024/768/390; console limpo
nas rotas TON; git diff --check limpo.
Known issues: a imagem em :3000 não inclui b1f250a645 (botão Nova conversa no modo
escuro); entra no próximo build.

---

# 19. Bloqueios atuais

```text
Nenhum bloqueio de implementação P0.
- DRE pronta não demonstrável: nenhuma base sintética está pronta (D-013). Não fabricado.
- Componentes de chat "pendência" e "resultado de rotina" adiados (P1): o chat usa o
  cartão de DRE com link para Pendências e o cartão de relatório.
- Concessão de permissão TON à conta de teste do Playwright foi negada pelo
  classificador; a validação usa a conta autorizada do usuário (D-010).
```

---

# 20. Dependências externas / reunião

```text
- NG/Keevo: acesso VPN ou API e base de leitura autorizada (Fontes mostra
  "Aguardando acesso e configuração"; dados entram por arquivo).
- Amostra real aprovada da Vale Norte para substituir a base sintética.
- Fontes de frota, contratos, produção, compras, compliance e RH para liberar
  os seis especialistas em "Aguardando fonte" e as rotinas R1, R2, R4–R9.
- Decisões humanas das 13 pendências (unidades, dotação, conciliação) e
  importação do realizado dos meses faltantes para a DRE ficar pronta.
- WhatsApp e outros canais: não integrados; não aparecem como conectados.
```
