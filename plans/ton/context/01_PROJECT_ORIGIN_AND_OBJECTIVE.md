# TON — ORIGEM, OBJETIVO E ESCOPO

## 1. O que é o TON

TON é o projeto de uma **Controladoria Digital 24/7** para a Vale Norte Construtora, com foco em contratos públicos de limpeza urbana, coleta, transporte, varrição, capina, roçada, poda, limpeza de canais e manejo de resíduos.

A visão não é “um chatbot que responde perguntas”.

É um sistema que conecta:

```text
Dados
→ validação
→ análise
→ evidência
→ decisão
→ ação
→ verificação
→ resultado financeiro
```

O objetivo central é ajudar a:

- economizar dinheiro;
- recuperar dinheiro;
- proteger margem;
- capturar receita;
- reduzir desperdício;
- antecipar riscos;
- reduzir retrabalho;
- fechar ciclos de controle.

## 2. Como o projeto começou

A necessidade nasceu do contexto da Controladoria da Vale Norte e do material fornecido por Luyla.

A primeira ideia era construir um agente autônomo que usasse as bases já existentes da empresa para encontrar inconsistências e oportunidades.

O problema crítico percebido cedo foi que os dados da empresa são distribuídos em:

- NG/Keevo;
- Excel;
- DREs;
- faturamento;
- dotações;
- contratos;
- backlog;
- banco;
- folha;
- frota;
- abastecimento;
- produção;
- documentos;
- Zeev;
- outros controles locais.

Isso criou a necessidade de uma camada de dados rastreável antes da camada de IA.

## 3. Primeira grande decisão

A arquitetura foi deliberadamente construída como:

```text
Source
→ ImportRun
→ immutable SourceSnapshot
→ Parser/Profile
→ Parsed/normalized data
→ Validation/Review
→ Evidence
→ Human decision
→ Canonical financial domain
→ DRE/readiness
→ Specialists / Agent
```

A IA não deve substituir a camada determinística.

## 4. Papel do Onyx

Onyx foi adotado como infraestrutura madura.

A decisão evoluiu para:

> **Onyx é infraestrutura. TON é o produto.**

Reutilizar:

- autenticação;
- RBAC;
- conversas;
- streaming;
- providers;
- tool calling;
- files;
- RAG;
- Code Interpreter;
- web search;
- artifacts;
- workers;
- connectors;
- infraestrutura de execução.

A interface cliente, porém, pode ser reconstruída completamente.

## 5. Visão do produto

A experiência esperada para a Vale Norte deve parecer:

```text
Vale Norte
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

O usuário não deve precisar entender:

- Onyx;
- Persona;
- Agent;
- MCP;
- OpenAPI;
- provider/modelo;
- raw tool calls;
- JSON;
- UUID;
- estrutura interna do backend.

## 6. Referência visual

A referência `ton_reference_visual` foi criada para representar a experiência prometida visualmente para Luyla.

Padrões importantes:

- Vale Norte como marca principal;
- TON como produto;
- verde institucional;
- header forte;
- sidebar operacional;
- chat central;
- fontes visíveis;
- automações visíveis;
- especialistas como parte da experiência;
- histórico;
- contexto lateral;
- empresa/controle, não playground de IA.

A referência é direção de produto, não fonte de verdade sobre integrações.

## 7. Critério de sucesso

O sucesso não é:

> “tem muitas telas”.

É:

> “Luyla consegue olhar o produto e entender o que o TON está vendo, por que está vendo, o que precisa ser decidido e o que o TON fará depois.”

