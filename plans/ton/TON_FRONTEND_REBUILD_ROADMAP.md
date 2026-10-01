# TON-FE-001 — Frontend Rebuild Roadmap

## Missão

Reconstruir a experiência cliente do TON como um produto próprio da Vale Norte, usando o backend TON/Onyx existente como infraestrutura — não como restrição visual.

A referência visual obrigatória será o arquivo colocado em `plans` com nome:

`ton_reference_visual.*`

Ela é a **north star visual e de produto**, não um contrato pixel-perfect e não uma fonte de verdade sobre integrações.

Objetivo final:

> O cliente deve perceber que está usando o TON, não “Onyx customizado”.

---

## 1. Princípio central

### Onyx é infraestrutura. TON é o produto.

Arquitetura conceitual:

```text
              TON CLIENT EXPERIENCE
                       |
                       v
             TON frontend / shell
                       |
             APIs / streaming / artifacts
                       |
     +-----------------+-----------------+
     |                                   |
     v                                   v
TON domain backend                 Onyx platform
Coordinator                        Auth / RBAC
Specialists                        Conversations
Routines                           LLM providers
DRE                                Streaming
Readiness                          Tool calling
Sources                            Files / RAG
Reports                            Code Interpreter
Occurrences                        Web / Artifacts
                                   Workers / Connectors
```

O frontend novo deve reaproveitar a maturidade do Onyx sem carregar a aparência genérica do Onyx para o cliente.

Não reimplementar sem motivo:
- autenticação;
- RBAC;
- conversas;
- streaming;
- providers;
- tool calling;
- arquivos;
- RAG;
- Code Interpreter;
- artifacts;
- workers;
- connectors;
- filas;
- auditoria;
- APIs já maduras do TON.

---

## 2. Contrato de autonomia do agente

Este roadmap **não substitui a leitura do repositório**.

O código atual é a fonte de verdade de implementação.

Antes de cada fase grande, o agente deve inspecionar o código e os contratos realmente existentes.

O agente pode:
- mudar a estrutura de rotas;
- criar um boundary frontend próprio para TON;
- extrair um app separado se isso for claramente melhor e seguro;
- reaproveitar componentes Onyx úteis;
- substituir layouts inteiros;
- excluir frontend TON legado depois que a substituição estiver estável;
- adicionar endpoints read-only pequenos se faltarem para uma boa UX;
- alterar a ordem interna das tarefas;
- adiar tarefas P2 para proteger o vertical slice da demo.

O agente não pode:
- inventar dados;
- inventar integrações;
- inventar especialista operacional;
- aprovar decisão financeira;
- alterar cálculo financeiro por conveniência visual;
- criar runtime de chat paralelo sem necessidade;
- duplicar Code Interpreter/files/auth/streaming sem justificativa;
- alterar silenciosamente R1–R9 ou especialistas canônicos;
- fazer push.

Quando roadmap e repositório divergirem:
1. escolher a solução tecnicamente mais segura;
2. registrar a decisão em `TON_FE_001_DECISIONS.md`;
3. continuar.

---

## 3. Definição de sucesso

Fluxo natural:

```text
Login
  ↓
TON
  ↓
Visão Geral
  ↓
Assistente
  ↓
Fechamento
  ├─ DRE
  └─ Pendências
  ↓
Automações
  ↓
Relatórios
  ↓
Fontes
```

O cliente não precisa conhecer:
- Persona;
- Agent do Onyx;
- MCP;
- OpenAPI actions;
- Projects do Onyx;
- model admin;
- raw tool calls;
- JSON;
- UUID;
- cobertura técnica do Prompt Mestre.

Administração técnica continua disponível para quem tiver permissão, mas fora da jornada normal do produto.

---

# 4. Direção visual obrigatória

Estudar `plans/ton_reference_visual*` antes de implementar.

Preservar o espírito da referência:

### Marca
- identidade Vale Norte forte;
- TON como produto;
- verde institucional como estrutura;
- dourado/acento usado com parcimônia;
- conteúdo principal claro, premium e corporativo.

### Composição
- header do produto;
- sidebar operacional;
- workspace central;
- right rail contextual em desktop quando útil;
- chat como núcleo;
- histórico acessível;
- fontes e automações visíveis;
- especialistas inteligíveis.

### Não parecer
- admin panel;
- playground de IA;
- documentação Markdown;
- console/debug;
- Onyx renomeado.

Nunca copiar estados falsos da imagem.
Exemplo: não mostrar VPN, NG direto ou WhatsApp como conectados se o backend atual não confirmar isso.

---

# 5. Prioridades

## P0 — obrigatório para apresentação
1. novo shell TON;
2. branding Vale Norte;
3. Home / Command Center;
4. Assistente TON com apresentação própria;
5. Fechamento / DRE;
6. Pendências;
7. R3 / Automações;
8. Relatórios;
9. Fontes;
10. jornada natural sem Admin.

## P1
11. especialistas integrados ao produto;
12. histórico de conversas redesenhado;
13. right rail contextual;
14. atividade recente;
15. status compactos;
16. boundary admin/cliente refinado.

## P2
17. responsive refinado;
18. configurações avançadas;
19. Cobertura do Prompt Mestre como diagnóstico;
20. catálogo amplo de automações;
21. refinamentos secundários.

---

# 6. Fase 0 — Auditoria técnica

Antes de construir, mapear:

- branch/HEAD/dirty state;
- rotas TON atuais;
- shell TON atual;
- shell Onyx atual;
- auth/RBAC;
- Persona coordenadora TON;
- criação/listagem de conversas;
- streaming;
- tool-call/event packets;
- artifacts;
- file APIs;
- Code Interpreter;
- specialist context;
- source APIs;
- DRE APIs;
- readiness APIs;
- routine APIs;
- report APIs;
- design primitives/tokens;
- branding atual;
- i18n atual;
- client/admin boundary.

Atualizar `TON_FE_001_TASKS.md` com:

```text
Current frontend structure:
Reusable infrastructure:
High-risk coupling:
Chosen rebuild boundary:
```

### Decisão permitida

O agente deve escolher a melhor estratégia após o audit:

**A.** subtree isolado no app atual  
**B.** route-group/layout TON isolado  
**C.** app frontend separado  
**D.** outra solução melhor justificada

Não escolher por “arquitetura bonita”; escolher pelo menor risco e maior velocidade para uma experiência coerente.

---

# 7. Fase 1 — Fundação visual e shell

## Branding
Usar a logo oficial Vale Norte localmente.

Fonte conhecida:
`https://www.valenorte.com/wp-content/uploads/2026/03/cropped-LOGO-VALE-NORTE.png`

Não hotlinkar.

TON permanece o nome do produto.

## Tokens
Criar/reusar camada pequena de tokens:
- verde Vale Norte escuro;
- verde estrutural;
- surface;
- border;
- muted;
- gold accent;
- success/warning/danger;
- spacing;
- radius;
- typography.

Não construir design system gigante.

## Shell
Criar shell TON próprio:
- header;
- sidebar;
- content;
- right rail opcional;
- responsive.

Não herdar sidebar genérica do Onyx na experiência do cliente.

## Navegação cliente recomendada
- Visão Geral
- Assistente
- Fechamento
- Fontes
- Automações
- Relatórios

DRE, Pendências e Especialistas podem ser subrotas/contextos.

A nomenclatura pode ser refinada após audit, mas deve permanecer simples.

## Administração
Apenas usuários autorizados veem entrada discreta:
`Administração`

Cliente normal não vê.

---

# 8. Fase 2 — Home / Command Center

Essa é a tela de abertura da demo.

## Estrutura recomendada

### Header
Saudação personalizada somente se o display name estiver disponível com segurança.

Exemplo:
`Olá, Luyla`
`Aqui está o que precisa da sua atenção hoje.`

Nunca hard-code Luyla.

### Faixa executiva
Estados reais:
- Fechamento
- DRE
- Pendências
- Fontes
- Última análise / próxima automação

### O que precisa de atenção
Top 3–5:
- título;
- explicação curta;
- quantidade;
- origem/domínio;
- CTA.

### Atividade do TON
Eventos reais:
- Auditor validou base;
- CFO analisou fechamento;
- relatório gerado;
- importação concluída.

### Automação
R3:
- agenda;
- próxima execução;
- último resultado;
- executar agora.

### Relatórios
1–2 últimos.

### Especialistas envolvidos
Mostrar como contexto de atividade/capacidade, não como configuração.

## Evitar
- RESULTADO/PROBLEMA/IMPACTO em blocos Markdown;
- trace longa;
- IDs;
- conteúdo duplicado.

---

# 9. Fase 3 — Assistente TON

## Objetivo
Criar experiência de chat própria usando o runtime maduro existente.

## Reutilizar
- conversation persistence;
- streaming;
- provider/LLM runtime;
- tools;
- files;
- Code Interpreter;
- RAG;
- web quando habilitada;
- artifacts;
- cancel;
- permissions.

## Substituir visualmente
Não usar UI genérica Onyx se ela obrigar:
- navegação Onyx;
- provider branding;
- tool trace cru;
- generic chat UX.

## Empty state
Direção:

```text
Olá, sou o TON.

Posso analisar informações financeiras,
operações, contratos e riscos conforme
as fontes disponíveis.
```

A copy deve respeitar as capacidades reais.

### Sugestões da demo
- Analisar fechamento
- Ver pendências da DRE
- Gerar resumo executivo
- Consultar fontes

Não prometer Frota/Contratos se ainda aguardam fontes.

## Composer
- input grande;
- anexar;
- enviar;
- controles úteis;
- sem `deepseek` visível para cliente;
- provider é configuração técnica.

## Execução
Normal:

```text
TON está analisando...

✓ Fontes consultadas
✓ Base financeira validada
✓ DRE verificada
✓ Evidências consolidadas
```

Depois a resposta.

Detalhes:
`Ver detalhes da análise`

JSON/tool internals:
admin/dev disclosure mais profundo.

## Componentes ricos
Criar/reusar componentes para:
- evidência;
- achado;
- DRE;
- fonte;
- pendência;
- rotina;
- relatório;
- resumo executivo.

Não renderizar tudo como Markdown se existe estrutura.

## Histórico
Remover `New Chat` genérico.
Usar títulos em pt-BR, compactos e significativos.

---

# 10. Fase 4 — Especialistas

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

Ler runtime real antes de mudar comportamento.

## UX
Especialistas podem aparecer:
- sidebar;
- detalhes de análise;
- right rail;
- página secundária.

Não devem dominar a home.

## Interação
Preferência:

```text
TON CFO
   ↓
nova/focada conversa TON
   ↓
specialist context = CFO
```

TON continua coordenador.

Não criar 9 runtimes de chat falsos.

## Status
Sempre runtime-backed.

Exemplo:
`TON FROTA — Aguardando fonte`

---

# 11. Fase 5 — Fechamento

Criar conceito de produto:

`Fechamento`

Pode ter:
- Visão geral
- DRE
- Pendências

## DRE bloqueada
Explicar:
- por que não publica;
- quantos itens;
- categorias;
- ação.

Exemplo:

```text
DRE de julho ainda não pode ser publicada

13 itens exigem atenção

Unidades      2
Dotação       2
Conciliação   3
Realizado     6
```

Cada grupo abre Pendências filtradas.

## DRE pronta
Software financeiro:
- Realizado
- Orçado
- Variação
- YTD
- tabela hierárquica
- drilldown
- export
- revisão em Advanced

Nunca mostrar enum cru ou ID interno como conteúdo principal.

---

# 12. Fase 6 — Pendências

Título cliente:
`Pendências do fechamento`

Não usar `Decisões de configuração` como conceito principal.

## Lista
- problema;
- origem;
- registros afetados;
- período/unidade;
- candidate quando suportado;
- status;
- ação.

## Resolver
Drawer/modal:
- encontrado;
- decisão necessária;
- escopo afetado;
- seleção;
- justificativa;
- confirmar/cancelar.

Nunca auto-aprovar.

---

# 13. Fase 7 — Fontes

Transformar import CRUD em data/integration health.

## Card
- nome;
- modo de aquisição;
- status;
- última atualização;
- registros;
- warnings;
- estado integração automática;
- CTA.

Exemplo atual honesto:

```text
NG / Keevo

Atualizado por arquivo
Última atualização: ...

Integração direta
Aguardando acesso VPN/API
```

Não mostrar VPN/DB/API como conectados sem evidência.

Histórico deve ficar colapsado/drawer/table.

---

# 14. Fase 8 — Automações

Página:
`Automações`

## R3 flagship
- Fechamento preliminar
- status;
- cadence;
- next run;
- last run;
- result;
- Executar agora;
- report.

## Outras
Agrupar:
- Ativas
- Aguardando dados
- Ainda não disponíveis

`R3` pode aparecer como metadado secundário.

Cliente não precisa decorar R1–R9.

## Execução
Estados explícitos:
- iniciando;
- executando;
- concluída;
- concluída com pendências;
- falhou.

Persistir estado no refresh.

---

# 15. Fase 9 — Relatórios

## Catálogo
Mostrar versão atual por:
- tipo;
- período;
- escopo.

Antigas:
`Ver versões anteriores`

## Viewer
- Vale Norte + TON;
- título;
- período;
- escopo;
- data;
- resumo executivo;
- achados;
- pendências;
- ações;
- fontes;
- rastreabilidade colapsada;
- download.

Não parecer preview Markdown.

---

# 16. Fase 10 — Right rail contextual

Reintroduzir a força da referência quando útil.

Possíveis blocos:
- Fontes
- Próxima automação
- Status do fechamento
- Especialistas envolvidos
- Alertas recentes

Em telas menores, virar drawer.

Não manter rail se não ajudar a experiência.

---

# 17. Fase 11 — Cliente x Admin

## Cliente
Ocultar:
- generic Agents;
- model config;
- MCP/OpenAPI;
- generic connector config;
- Prompt Mestre coverage;
- admin técnico.

## Admin
Preservar:
- usuários;
- permissões;
- modelos;
- Persona TON;
- integrações técnicas;
- diagnostics.

`Cobertura do Prompt Mestre` deve virar diagnóstico/admin, não item principal da demo.

---

# 18. Fase 12 — Branding e pt-BR

Se ainda não estiver concluído:

- logo Vale Norte local;
- TON como produto;
- sem branding Onyx visível no cliente;
- UI normal pt-BR;
- Intl pt-BR mantido;
- favicon;
- title;
- metadata;
- login/entry;
- remover `0.0.0-dev` da UI cliente.

Não renomear package/module Onyx só por branding.

---

# 19. Regras de demo data

Synthetic data:
- permitido;
- sempre claramente identificado;
- não repetir warning gigante em todos os cards.

Preferência:
banner único:
`Ambiente de demonstração — dados sintéticos`

Nunca apresentar como resultado real Vale Norte.

---

# 20. Jornada obrigatória da demo

## 1. Home
Abrir TON.

## 2. Assistente
Perguntar:
`Analise o fechamento financeiro atual e me diga o que precisa da minha atenção.`

Mostrar progresso simples + resposta estruturada.

## 3. Evidência
Perguntar:
`Mostre a evidência da principal pendência.`

Card de evidência.

## 4. Pendências
Abrir uma pendência.
Mostrar decisão humana.

## 5. DRE
Mostrar bloqueio honesto.
Se houver fixture READY segura, pode mostrar separadamente e marcada como sintética.

## 6. Automação
Mostrar R3:
- primeiro dia útil;
- 08:00 Brasília;
- próxima execução;
- executar agora.

## 7. Relatório
Abrir resultado gerado.

## 8. Fontes
Mostrar NG manual + integração direta pendente.

Isso deve conduzir naturalmente para a conversa com Luyla sobre VPN/API/read-only DB.

---

# 21. Protocolo de execução do agente

Este roadmap é longo.

O agente não deve produzir um diff monolítico e sumir.

## Início
Atualizar `TON_FE_001_TASKS.md` com:
- baseline;
- audit;
- arquitetura escolhida;
- milestone atual.

## Depois de cada milestone estável
1. atualizar tasks;
2. registrar o que mudou;
3. registrar o que já é demonstrável;
4. registrar validação;
5. commit local coerente;
6. continuar automaticamente para a próxima tarefa P0.

Não pedir confirmação após cada fase.

## Só parar para perguntar se:
- migração destrutiva;
- credencial/acesso externo;
- duas alternativas têm consequências grandes e o repo não resolve;
- surgem mudanças de outro usuário/agente;
- requisito exigiria fake.

Bloqueou uma tarefa?
Marcar `[!]`, explicar e seguir para outra independente.

---

# 22. Validação

Durante:
- focused frontend tests;
- backend tests só se backend mudou;
- typecheck;
- lint;
- format;
- browser real.

Milestone visual só passa após abrir em Chrome.

Compilar != aceitar visualmente.

Final:
- testes relevantes;
- build;
- `git diff --check`;
- demo end-to-end.

---

# 23. Critério visual

NÃO aceitar página que:
- pareça mais Onyx do que TON;
- pareça Markdown;
- seja só whitespace + texto;
- mostre JSON;
- mostre tool trace como conteúdo principal;
- mostre UUID;
- exija explicar Onyx;
- não tenha ação principal;
- duplique informação;
- faça claim falso;
- use copy dev/debug.

Aceitar quando:
- hierarquia é entendida em segundos;
- status e ação são claros;
- cliente entende sem explicação técnica;
- pertence visualmente ao mesmo produto da referência;
- continua honesta sobre capacidade real.

---

# 24. Performance / manutenção

Preferir:
- API existente;
- server aggregation se evita N chamadas;
- cache/query layer existente;
- typed view models;
- componentes compartilhados do TON.

Evitar:
- regra de domínio reconstruída no frontend;
- fetch duplicado por página;
- provider gigante;
- library de animação desnecessária.

---

# 25. Migração do frontend legado

Não apagar tudo primeiro.

Sequência:
1. construir novo shell;
2. migrar superfícies canônicas;
3. validar equivalência;
4. remover legado após estabilidade.

Pode manter rota interna temporária para comparação.

Nunca expor `legacy` para cliente.

---

# 26. Entrega P0

Ao terminar P0, deve existir:

- shell Vale Norte/TON coerente;
- Home forte;
- chat TON próprio;
- Fechamento/DRE;
- Pendências;
- Automações/R3;
- Relatórios;
- Fontes;
- client/admin boundary;
- jornada de demo natural.

A estrutura exata de arquivos fica a cargo do agente após auditoria.

---

# 27. Princípio final

Não otimizar para preservar frontend antigo.

Otimizar para preservar capacidades corretas de backend e entregar a experiência que foi prometida visualmente para a Vale Norte.

Substituir grandes partes do frontend TON atual é permitido e esperado.
