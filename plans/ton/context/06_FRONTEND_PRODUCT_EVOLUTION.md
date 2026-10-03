# TON — EVOLUÇÃO DO FRONTEND E ESTADO DO PRODUTO

## 1. Primeira fase

A primeira implementação tentou construir o TON dentro da navegação existente do Onyx.

Resultado:
funcionalidade avançou, mas a experiência parecia:

- admin;
- Markdown;
- debug;
- Onyx renomeado.

Isso foi considerado insuficiente para a apresentação a Luyla.

---

# 2. Problemas visuais que foram encontrados

Nas telas antigas havia:

- shell Onyx;
- sidebar genérica;
- generic Agents;
- Projects;
- provider/model selection;
- raw JSON;
- tool traces;
- “Processado” repetido;
- R3 mostrando 21 passos diretamente;
- especialistas parecendo CRUD;
- DRE com cara de tabela administrativa;
- relatórios parecendo Markdown;
- fontes parecendo upload CRUD;
- Cobertura do Prompt Mestre exposta demais;
- admin misturado à jornada;
- sensação de “estou usando Onyx, não TON”.

---

# 3. A virada

A decisão foi:

> reconstruir a interface cliente praticamente do zero e reutilizar o Onyx como infraestrutura.

Isso foi inspirado também pelo trabalho anterior do Sipelzinho, onde a ideia foi:
“usar a maturidade técnica existente, mas criar uma experiência própria”.

---

# 4. FE-001

A reconstrução criou:

### Branding
- Vale Norte;
- TON;
- logo local;
- favicon/title;
- sem branding Onyx no cliente;
- pt-BR.

### Shell
- header verde;
- sidebar verde;
- navegação TON;
- contexto lateral.

### Home
- status executivo;
- pendências;
- fontes;
- automação R3;
- atividade;
- relatórios;
- especialistas envolvidos.

### Assistant
- chat customizado visualmente;
- streaming existente;
- progress summary;
- rich cards;
- evidence;
- reports;
- actions.

### Closing
- visão do fechamento;
- DRE;
- blockers;
- pendências.

### Sources
- data health;
- import;
- history.

### Automations
- R3;
- schedules;
- lifecycle;
- result.

### Reports
- viewer;
- branding;
- revisions.

---

# 5. Estado do FE-001 no último handoff

Último HEAD informado:
`ea11f7be6d`

Branch:
`main`

Árvore:
limpa.

Push:
não realizado.

P0:
concluído.

Validação:
- Playwright 2/2;
- componentes;
- TypeScript;
- lint;
- build;
- Chrome;
- 1024/768/390;
- sem horizontal overflow;
- foco por teclado;
- dark mode legível.

---

# 6. O que ainda não estava perfeito

Mesmo após FE-001:

- DRE ready real não existe;
- fontes reais não estão integradas;
- alguns fluxos administrativos continuam com herança Onyx;
- admin/configuração ainda precisa refinamento;
- history/chat pode amadurecer;
- structured AI output pode evoluir;
- reports podem ficar mais executivos;
- automations podem ficar mais autônomas;
- especialistas podem ficar mais contextuais;
- a principal evolução agora deve ser macro workflow e valor diário.

---

# 7. FE-002

Objetivo:
maturidade de produto, não apenas estética.

Foco:
- design system;
- navigation;
- header/status;
- login;
- Home;
- Assistant;
- DRE;
- Pendências;
- Sources;
- Automations;
- Reports;
- Specialists;
- activity;
- notifications;
- search;
- admin separation;
- responsive/accessibility;
- production polish.

---

# 8. FE-003

Objetivo:
sair do “TON analisa” e chegar ao loop:

```text
analisa
→ explica
→ identifica
→ guia decisão
→ registra decisão
→ recalcula
→ mostra consequência
→ acompanha
→ reporta mudança
```

Prioridade:
resolução de pendências.

Também foi criada a regra de que o agente deve encontrar gaps novos por conta própria.

---

# 9. UX principle

Não fazer:
- cards decorativos;
- fake insights;
- fake KPIs;
- gradients gratuitos;
- “AI sparkle” sem função;
- animação sem significado;
- dashboard vazio;
- textão em Markdown.

Cada elemento precisa responder:
> que decisão ou ação isso ajuda o usuário a tomar?

---

# 10. Estado após FE-003 (2026-10-02)

FE-003 entregou o loop decisão → recálculo → antes/agora, decisões não aplicadas visíveis, trilha de
decisões, fila "O que precisa de você hoje", Fechamento como centro de controle, CTAs específicos no
assistente, timeline de raciocínio e Python (D-024..D-032). Detalhe: `plans/ton/TON-FE-003_GAP_REPORT.md` §12.

Pendências de produto/UX seguem como changes OpenSpec: tela do ledger (`occurrence-ledger-workflow`),
DRE em Excel (`dre-excel-export`), fichas de exceção/modo executivo (`exception-card-and-executive-mode`),
Contratos (`contract-master-registry`), Dinheiro Escondido (`hidden-money-and-roi`), Automações com
rotinas declarativas (`routine-framework`). Ver `openspec/roadmap.md`.
