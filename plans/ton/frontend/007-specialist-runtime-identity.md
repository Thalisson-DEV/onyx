# TON-VIS-007 — Especialistas e Identidade de Runtime

Documento de fechamento e especificação técnica da fatia **TON-VIS-007**.
Companheiro de [`000-de-onyx-visual-audit.md`](./000-de-onyx-visual-audit.md), [`visual-language.md`](./visual-language.md) e [`visual-implementation-roadmap.md`](./visual-implementation-roadmap.md).

**Estado: DONE.**

---

## 1. Contexto e Problema Observado

Na auditoria forense inicial (`000-de-onyx-visual-audit.md`, §4.1 e §5.7), identificou-se que a geometria da marca upstream (`SvgOnyxOctagon`) era empregada indevidamente como semântica de produto para especialistas em 10 pontos de renderização.

O componente `CustomAgentAvatar` encapsulava avatares dentro de `SvgOctagonWrapper`, gerando quatro formas concorrentes para a mesma entidade:
1. Imagem enviada pelo usuário: círculo (`rounded-full`);
2. Ícone configurado: octógono de marca (`SvgOnyxOctagon`);
3. Letra inicial: octógono de marca (`SvgOnyxOctagon`);
4. Agente padrão: diamante sem moldura (`SvgOnyxLogo`).

Adicionalmente:
- A página `/app/agents` usava o título upstream "Agentes" e o octógono como ícone de cabeçalho;
- O `AgentCard` continha gradiente decorativo (`radial-00`), sombra suspensa (`hover:shadow-box-00`), altura fixa (`h-24`) e fallback de proprietário com o nome da marca upstream (`agent.owner?.email || "Onyx"`);
- O botão de novo agente expunha o identificador de teste `AgentsPage/new-agent-button` como `aria-label`;
- O fallback de inicial apenas aceitava caracteres ASCII `/^[a-zA-Z]$/`, descartando dígitos, emojis e caracteres CJK.

---

## 2. Pontos de Renderização Auditados

| Ponto de Render | Identidade Anterior | Geometria Anterior | Ação VIS-007 | Novo Tratamento |
|---|---|---|---|---|
| `CustomAgentAvatar.tsx` | `SvgOctagonWrapper` | Octógono SVG | **REPLACE** | `SpecialistAvatar` (quadrado arredondado `radius-08`) |
| `AgentAvatar.tsx` | `SvgOnyxLogo` / imagem | Diamante / círculo | **REPLACE** | `SpecialistAvatar` com `SvgManageAgent` e suporte a estado |
| `AgentCard.tsx` | `radial-00` + `shadow-box-00` | Card decorativo | **REPLACE** | Superfície neutra, borda 1px, altura por conteúdo, sem "Onyx" |
| `AgentsNavigationPage.tsx` | `SvgOnyxOctagon` | Octógono no header | **REPLACE** | `SvgManageAgent`, i18n "Especialistas", `IllustrationContent` |
| `AgentEditorPage.tsx` | `SvgOnyxOctagon` + picker | Octógono | **REPLACE** | `SvgManageAgent` no header; seletor com `CustomAgentAvatar` unificado |
| Admin `AgentsPage.tsx` | `SvgOnyxOctagon` | Octógono no header | **REPLACE** | `SvgManageAgent` no cabeçalho |
| `admin-routes.ts` (AGENTS) | `SvgOnyxOctagon` | Octógono na rota | **REPLACE** | `SvgManageAgent` como ícone de rota |
| `NoAgentModal.tsx` | `SvgOnyxOctagon` | Octógono no modal | **REPLACE** | `SvgManageAgent` no cabeçalho do modal |
| `PersonaMessagesChart.tsx` | `SvgOnyxOctagon` | Octógono no picker | **REPLACE** | `SvgManageAgent` no gatilho e nas linhas |
| `shared.tsx` (LLM modal) | `SvgOnyxOctagon` | Octógono no vazio | **REPLACE** | `SvgManageAgent` no estado vazio de acesso |
| `AppSidebar.tsx` (Specialists) | `SvgOnyxOctagon` | Octógono na aba | **REPLACE** | `SvgManageAgent` na aba Especialistas |
| `AgentButton.tsx` (Sidebar pin) | `AgentAvatar` | Octógono / círculo | **ALIGNED** | Recebe `SpecialistAvatar` unificado via `AgentAvatar` |
| `AgentViewerModal.tsx` | `agent.owner?.email ?? "Onyx"` | String de marca | **REPLACE** | Omissão neutra quando proprietário não informado |

---

## 3. Contrato de Identidade Unificado (`SpecialistAvatar`)

O novo componente `SpecialistAvatar` (`web/src/refresh-components/avatars/SpecialistAvatar.tsx`) estabelece a casca geométrica única para avatares de especialistas TON:

- **Geometria externa**: quadrado arredondado com token `radius-08` (`rounded-lg` em controles ≥24px, `rounded-sm` / `radius-04` em compactos <24px);
- **Superfície**: `bg-background-tint-00`;
- **Borda base**: `border border-border-default`;
- **Escala de ícone**: 60% do tamanho do contêiner (`size * 0.6`), centralizado;
- **Acessibilidade**: ícones e iniciais marcados com `aria-hidden="true"`.

---

## 4. Cadeia de Fallback Estendida e Determinística

`CustomAgentAvatar` implementa uma cadeia estrita e determinística em 4 níveis:

1. **Imagem customizada (`src`)**: renderizada em contêiner circular (`rounded-full`) preservando o caráter fotográfico de avatar humano/institucional, com anel semântico de estado (`ring-1 ring-border-selected` / `ring-border-attention`);
2. **Ícone configurado (`iconName`)**: mapeado via `agentAvatarIconMap` para tokens semânticos TON (`stroke-theme-primary-05`, `stroke-theme-blue-05`, etc.), sem uso de verde da marca upstream (`theme-green-05`);
3. **Primeiro grafema (`name`)**: extraído via `Intl.Segmenter(undefined, { granularity: "grapheme" })`:
   - Letra latina (ex: "Alice" → "A");
   - Dígito numérico (ex: "360 Audit" → "3");
   - Emoji Unicode (ex: "⚡ Fast Engine" → "⚡");
   - Caractere CJK (ex: "会計 Audit" → "会");
4. **Vazio / ausente**: glifo institucional neutro `SvgTwoLineSmall` (`stroke-text-03`).

---

## 5. Estados de Runtime

O sistema suporta formalmente 4 estados operacionais:

- **`idle`**: repouso neutro, borda padrão `border-border-default`, sem pulso ou animação;
- **`running`**: indicador contido de execução (`span` pontual no canto inferior com `bg-theme-primary-04 motion-safe:animate-pulse`). O contêiner de identidade **não rotaciona** e **não é animado**;
- **`attention`**: borda semântica âmbar `border-border-attention` e atributo `data-attention="true"`. Não há pulso decorativo;
- **`selected`**: borda semântica primária `border-border-selected` e `aria-selected="true"`. Evidência não baseada apenas em cor.

**Garantia de Não-Deslocamento (Zero Layout Shift)**:
As dimensões do elemento raiz são fixadas em `style={{ width: size, height: size }}` em todos os estados, evitando qualquer salto geométrico.

**Rejeição de Estados Falsos em Produção**:
Nenhuma página de produção simula estados `running` ou `attention` sem dado observável do backend. A API de estados foi validada na suíte de testes e nos stories do Storybook, mantendo a produção em repouso (`idle`) ou seleção legítima (`selected`).

---

## 6. Transformação do `AgentCard`

O `AgentCard` (`web/src/sections/agents/AgentCard.tsx`) foi limpo da linguagem visual legada:
- Remoção de `className="radial-00 hover:shadow-box-00"`;
- Eliminação do gradiente radial de fundo (`radial-00`);
- Eliminação da sombra suspensa no hover (`hover:shadow-box-00`);
- Altura do cabeçalho conduzida por conteúdo (remoção da classe restritiva `h-24`);
- Remoção do fallback `"Onyx"`: quando `agent.owner?.email` não existe, o metadado secundário é omitido de forma limpa;
- Preservação total de comportamentos: fixação/desafixação (`usePinnedAgents`), edição, compartilhamento, estatísticas e início de conversa.

---

## 7. Decisões de Terminologia e i18n

Em conformidade com a arquitetura de informação de FE-004 e as normas do projeto:
- Terminologia de produto atualizada de "Agentes" para "Especialistas" em português (`pt.json`) e "Specialists" em inglês (`en.json`);
- Atualização simultânea com paridade total em todos os 9 catálogos (`en`, `pt`, `es`, `fr`, `de`, `ar`, `ja`, `ko`, `zh`);
- `NEW_AGENT_BUTTON_ARIA_LABEL`: substituído por `aria-label={t("navigation.newAgent.ariaLabel")}` ("Novo especialista" / "New specialist"), mantendo `data-testid="AgentsPage/new-agent-button"` para compatibilidade de testes;
- Estado vazio da página de navegação atualizado para usar `IllustrationContent` sem ilustrações gigantes ou alegações de marketing de IA.

---

## 8. Segurança de Marca e Bloqueios (ADR-009)

- **Sem invenção de logotipo**: nenhum logotipo corporativo da Vale Norte ou TON foi criado. O ícone `SvgManageAgent` de `@opal/icons` foi adotado como glifo semântico operacional genérico de especialista;
- **Sem criação de personas**: nenhuma persona concreta (CFO, Frota, Contratos, Auditor, RH) foi introduzida no código. As personas reais pertencem ao backend Plan 005 / TON-FE-005;
- **Acoplamento do Loader**: auditou-se `web/lib/opal/src/components/loader/components.tsx`. A identidade de especialistas foi estritamente isolada do caminho de SVG do `OnyxLoader`, sem desincronização silenciosa;
- **Ocorrências remanescentes de `SvgOnyxLogo`**: restritas às superfícies de autenticação, provedores em modais de configuração admin e componentes centrais bloqueados por ADR-009, devidamente catalogadas.

---

## 9. Validação e Gates de Qualidade

1. **Testes Unitários e de Integração VIS-007**:
   - `web/src/ton/ton-specialist-identity.test.tsx` com 28 testes passando (100% de sucesso);
   - `src/i18n/__tests__/catalog.test.ts` com 9 testes e 145.392 asserções ICU validadas;
2. **Testes de Regressão das Fatias Anteriores**:
   - `ton-shell.test.tsx`: 49 testes aprovados;
   - `ton-navigation.test.tsx`: 28 testes aprovados;
   - `homeVisualContract.test.tsx`: aprovado;
   - `ton-product-surface.test.tsx`: aprovado;
   - `composerVisualContract.test.ts`: aprovado;
   - `attachmentVisualContract.test.ts`: aprovado;
   - `ton-theme.test.ts`: aprovado;
   - `ton-foundations.test.ts`: aprovado;
   - `messageVisualContract.test.ts`: aprovado;
   - `ReasoningRenderer.test.tsx`: aprovado;
3. **Verificação de Tipos (`bun run types:check`)**:
   - 0 erros de tipo; cobertura de tipos de 98.81% em 1249 arquivos;
4. **Linter (`bun run lint`)**:
   - 0 erros;
5. **Formatação (`oxfmt`)**:
   - Todos os arquivos alterados formatados e verificados;
6. **Git diff check (`git diff --check`)**:
   - 0 erros de whitespace;
7. **Compilação de Produção (`bun run build`)**:
   - Next.js 16.3.3 compilou com sucesso todas as páginas estáticas e dinâmicas.
