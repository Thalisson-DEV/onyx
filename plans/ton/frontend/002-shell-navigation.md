# TON-VIS-002 — casca, sidebar e navegação

**Status: DONE.** Somente frontend. Nenhum arquivo em `backend/` mudou. Nenhuma
dependência nova. **A arquitetura de informação de FE-004 não mudou.**

Executado no worktree isolado `../ton-vis-002`, branch `ton/vis-002`, a partir de
`fb5a83140da62aa0e5fe34dd2db0cc78ff64f42f` (branch `main`, árvore limpa). Esse
baseline contém FE-000 a FE-004, VIS-000, VIS-001, VIS-004, e os Planos backend
001, 002, 003a–003d, 007 e 008a.

Insumos: [`000-de-onyx-visual-audit.md`](./000-de-onyx-visual-audit.md) §3.5, §5.2,
§R3, §R10, §A3, §A4, §C1, §C3, §P7 ·
[`001-visual-foundations.md`](./001-visual-foundations.md) ·
[`004-composer.md`](./004-composer.md) ·
[`visual-language.md`](./visual-language.md) §4, §5, §7, §10 ·
[`004-ton-navigation.md`](./004-ton-navigation.md) (FE-004) · `web/AGENTS.md`.

---

## 1. Conclusão executiva

A casca deixou de ser uma coluna cinza sem aresta com fileiras de cartões
contornados. O que mudou, em ordem de impacto visual:

1. **A linha de navegação selecionada não é mais um cartão.** O anel verde de
   perímetro completo saiu das variantes de sidebar e foi substituído por um
   **marcador na aresta de início** da linha. O raio da linha caiu de 8px para
   4px.
2. **A sidebar ganhou aresta.** 1px `border-01` no fim lógico da coluna. A
   superfície continua no papel `surface`; o que faltava era a fronteira.
3. **O rótulo de seção subiu de hierarquia** (`text-02` → `text-03`, 3.29:1 →
   4.59:1 no claro) e o ritmo entre seções abriu (`pt-3` → `pt-5`).
4. **A faixa da marca passou a ter a altura do header do chrome** (52px), então a
   marca e a primeira linha do canvas ficam na mesma linha, e o controle de
   recolher passou a ficar no centro óptico da marca.
5. **O header do chrome parou de flutuar.** `items-start` → `items-center`, e os
   dois `FrostedDiv` — 20px de blur mais 6px de backdrop-filter — saíram.
6. **`AppChrome` foi de 742 para 226 linhas**, com o header extraído para
   `AppHeader.tsx`, movido literalmente.

Três defeitos concretos da auditoria foram corrigidos de passagem: o menu de
projeto inalcançável no toque (A3), `"Open Sidebar"`/`"Close Sidebar"` em inglês
no produto PT-BR (C1/A4), e `aria-label="share-chat-button"` (C3). Mais dois
achados de qualidade: os skeletons pararam de sortear larguras com
`Math.random()`, e a sidebar parou de ficar vazia enquanto qualquer fonte carrega.

**Nível de mudança aplicado: 3 (composição local da casca).**

---

## 2. Mapa de componentes da sidebar

| Arquivo | Papel |
|---|---|
| `web/lib/opal/src/layouts/sidebar/components.tsx` | `Root` (coluna desktop, overlay mobile, overlay small, backdrop, spacer), `Header` (marca + recolher), `Body` (scroll + persistência), `Footer`, `Section` |
| `web/lib/opal/src/layouts/sidebar/styles.css` | todo o cromo da casca |
| `web/lib/opal/src/components/buttons/sidebar-tab/components.tsx` | a linha: overlay clicável, ícone, rótulo, `rightChildren`, tooltip quando dobrado |
| `web/lib/opal/src/components/buttons/sidebar-tab/styles.css` | o dobrar do rótulo, por CSS e `data-folded` |
| `web/lib/opal/src/core/interactive/stateful/styles.css` | a matriz variante × estado, incluindo o estado selecionado |
| `web/src/sections/sidebar/AppSidebar.tsx` | a composição TON: destinos, seções, drag/drop, paginação |
| `web/src/sections/sidebar/ChatButton.tsx` | a linha de conversa |
| `web/src/sections/sidebar/AccountPopover.tsx` | rodapé de conta |
| `web/src/lib/projects/components/ProjectFolderButton.tsx` | a linha de projeto |
| `web/src/layouts/chromes/AppChrome.tsx` | a casca: fundo, footer, refoco do composer |
| `web/src/layouts/chromes/AppHeader.tsx` | **novo** — o header, extraído |

Descobertas de propriedade que a auditoria não registrava:

- `Interactive.Stateful` e `Interactive.Container` renderizam **o mesmo nó** do
  DOM. A variante, o estado e o raio ficam todos nele.
- `roundingToRem(n)` é `n / 4 rem`. `rounding={2}` era 8px.
- **`lib/opal/dist/` é gerado, gitignorado, e `globals.css` importa
  `@onyx-ai/opal/root.css` de lá.** Editar `lib/opal/src/**/*.css` não tem efeito
  em runtime até `bun run build` rodar dentro de `lib/opal` (o script `prepare`
  faz isso no `bun install`). Isso quase deixou passar meia mudança: o bundle de
  produção continha o anel antigo e o marcador novo ao mesmo tempo. A validação
  em navegador foi o que pegou.

---

## 3. Casca anterior

| Aspecto | Antes |
|---|---|
| Superfície da coluna | `background-tint-02`, **sem aresta** |
| Separação do canvas | apenas 1.09:1 de superfície no claro; nenhuma borda |
| Raio da linha | 8px (`rounding={2}`) |
| Linha selecionada | `background-tint-00` + **anel verde de perímetro completo** |
| Rótulo de seção | `secondary-body`, `text-02`, 3.29:1 no claro |
| Ritmo entre seções | `pt-3` |
| Faixa da marca | `pt-3`, `items-start`, altura por conteúdo |
| Recolher | alinhado ao topo, colado na marca |
| Header do chrome | `items-start`, dois `FrostedDiv` de vidro |
| `AppChrome` | 742 linhas, `Header()` ocupando 536 |
| Menu de projeto | `hidden` + `group-hover/SidebarTab:flex` — **inalcançável no toque** |
| Recolher (copy) | `"Open Sidebar"` / `"Close Sidebar"` codificado |
| Skeletons | larguras sorteadas por `Math.random()` a cada render |
| Sidebar carregando | corpo inteiro `null` até **todas** as fontes resolverem |
| Vinheta do canvas | `rgba(0, 0, 0, 0.4)` cru; máscara com `25rem` repetido |

---

## 4. Casca final

Minimal, operacional, silenciosa, precisa, corporativa — e a diferença é de
hierarquia, ritmo, geometria de linha, estado selecionado, fronteira de superfície
e composição de header. Nada decorativo entrou.

### 4.1 Superfície da sidebar

A fronteira contra o canvas é **borda de 1px mais o degrau de superfície**:

```css
.opal-sidebar-root__column,
.opal-sidebar-root__overlay {
  background: var(--background-tint-02);          /* papel `surface`, inalterado */
  border-inline-end: calc(var(--weight-line-border) * 1px) solid var(--border-01);
}
```

Sem sombra. Sem tint verde. Lógico (`border-inline-end`), então correto em RTL.

**A alternativa foi medida e rejeitada.** Pintar a coluna com a cor do canvas
(`background-tint-01`) daria o "menos painel preenchido" mais literal, mas no tema
claro deixaria uma única linha de **1.20:1** como toda a fronteira entre casca e
canvas, numa altura de viewport inteira. Mantendo `tint-02` a fronteira é a borda
**mais** o degrau de 1.09:1 (claro) / 1.22:1 (escuro) — borda sobre superfície, que
é a hierarquia declarada em `visual-language.md` §4. O papel semântico também não
se desloca: a sidebar é cromo estrutural, não conteúdo elevado.

### 4.2 Largura e densidade

**Inalteradas, deliberadamente:** `--sidebar-width-expanded: 15rem` (240px) e
`--sidebar-width-folded: 3.25rem` (52px).

Auditadas, não mantidas por inércia. 240px acomoda os rótulos PT-BR mais longos do
produto (`Pesquisar chats`, `Painel de administração`) e títulos de conversa com
truncamento em uma linha, sem tomar canvas: a 1280px sobram 1040px, e a medida de
leitura é 720px. Reduzir apertaria os rótulos PT-BR; aumentar comeria canvas sem
ganho. Nenhum número foi copiado de outro produto. Todo o resto do contrato de
largura — mobile, dobrado, drag/drop, truncamento, breakpoints — segue intacto e
está fixado em teste.

### 4.3 Área da marca

```css
.opal-sidebar-header__topbar {
  height: var(--chrome-header-height);   /* 52px, o mesmo do header do chrome */
  display: flex; align-items: center;
}
.opal-sidebar-header__topbar-inner { align-items: center; }  /* era items-start */
```

A marca e a primeira linha de conteúdo do canvas passam a assentar na mesma linha
horizontal, o que é o que faz a casca parecer intencional em vez de duas colunas
começando em alturas diferentes. O controle de recolher fica no centro óptico da
marca, lendo como utilidade da casca e não como parte do logotipo.

**Nenhum logotipo foi inventado.** `renderSidebarLogo` e o ativo que ele escolhe
não foram tocados; a ADR-009 segue bloqueando o ativo TON real, e VIS-002 não
precisou dele. Sem gradiente, sem tagline.

### 4.4 Contrato da linha de navegação

```text
raio        4px (`rounding={1}`), com o overlay de foco em `rounded-04`
repouso     transparente, ícone `text-02`, rótulo `text-03`
hover       `background-tint-03`
selecionado marcador na aresta de início + `background-tint-00` + rótulo `text-04`
pressionado o marcador engrossa e vai de ponta a ponta
desabilitado o marcador mantém a forma e cai para `border-02`
```

O marcador:

```css
.interactive:is([variant="sidebar-heavy"], [variant="sidebar-light"])[state="selected"]::before {
  content: "";
  position: absolute;
  inset-block: calc(var(--weight-line-focus) * 1px);
  inset-inline-start: 0;
  width: calc(var(--weight-line-focus) * 1px);
  border-radius: var(--radius-round);
  background-color: var(--theme-primary-04);
  pointer-events: none;
}
```

`::before` e não `box-shadow` inset porque o deslocamento precisa ser **lógico**:
o offset de um box-shadow é físico e cairia no lado errado em RTL.
`Interactive.Container` recorta o overflow, então o marcador é limitado pela caixa
arredondada da própria linha; `inset-block` de 2px o mantém fora das curvas.

`position: relative` foi adicionado **apenas à linha selecionada**, não a
`.interactive` em geral, para não trocar o bloco de contenção de todo botão do
app. O overlay e o slot de ações da linha já são caixas de sangria completa, então
reancorá-los do wrapper para esse nó não os move — verificado no navegador.

**Três sinais carregam o estado**, e nenhum deles é cor sozinha: posição (uma
forma na aresta), superfície (o degrau silencioso da matriz) e texto (o rótulo
sobe para `text-04`). Nada depende do rótulo estar visível, então a coluna dobrada
mantém indicação de seleção completa.

**As variantes `select-*` não foram tocadas.** O anel de perímetro continua nelas,
que é de onde o controle de Deep Research de VIS-004 tira o estado ativo. Só a
família de sidebar saiu, e há teste fixando exatamente isso.

### 4.5 Conversa selecionada

`ChatButton` renderiza um `SidebarTab` e passa `selected`, então herda o contrato
acima por construção — não tem tratamento próprio, e há teste garantindo que não
adquira um. O contorno verde arredondado do screenshot deu lugar ao marcador de
aresta. Títulos longos continuam truncando em uma linha (`titleMaxLines={1}` mais
o espaçador de truncamento que reserva espaço para o menu).

### 4.6 Navegação de produto versus histórico

A separação é espaçamento, tipografia, divisor e ritmo — nesta ordem, e sem
container novo:

- **Ritmo:** `pt-5` antes do header de cada seção (era `pt-3`).
- **Tipografia:** rótulo de seção em `text-03`; rótulo de linha em `text-03`;
  rótulo de linha selecionada em `text-04`. O rótulo de seção deixou de ser mais
  silencioso que as linhas que governa.
- **Divisor:** o `Divider` que FE-004 já colocava entre Projetos e Conversas
  segue, agora com ritmo suficiente dos dois lados para ler como fronteira.
- **Semântica:** dois landmarks `nav` distintos, de FE-004, intactos.
- **Posição:** Central, Especialistas e Pesquisar chats seguem fixados no
  `Header`, fora da área que rola; Conversas fica no `Body`, que rola. Essa é a
  diferença de camada mais forte que existe e ela já era assim.

Nenhum nível de navegação foi acrescentado. Nenhuma caixa de cartão separa seções
— há teste para as duas coisas.

### 4.7 Central e Especialistas

Primeiros na coluna, no landmark de produto, na variante `sidebar-heavy` (rótulo
`text-03`, ícone `text-02`, selecionado `text-04`). **Pesquisar chats** fica logo
abaixo e lê como utilidade em vez de destino por um motivo estrutural, não
cosmético: não tem `href`, abre um command menu. Ordem, rotas e rótulos
inalterados.

### 4.8 Rótulos de seção

`Text font="secondary-body" color="text-03"`. Só a cor mudou. Tamanho e peso
ficaram, então não viraram títulos. Sem caixa alta, sem letter-spacing.

| | claro | escuro |
|---|---|---|
| antes (`text-02`) | 3.29:1 | 4.40:1 |
| depois (`text-03`) | **4.59:1** | **6.03:1** |

O alinhamento horizontal **não** mudou: `px-0.5` foi mantido porque, medido, põe as
letras a 18px da aresta da coluna, que é exatamente onde começa o ícone de uma
linha. Só a folga vertical fechou (`py-1.5` → `py-1`), de modo que o rótulo fica
mais perto das linhas que titula do que da seção acima.

### 4.9 Projetos

Comportamento inteiro preservado: criar, renomear, excluir, arrastar conversa para
dentro, projetos dobrados, popover, painel de contexto. As linhas de projeto usam a
mesma linguagem de linha TON via `SidebarTab`. Nenhum grupo "Conhecimento" foi
criado.

### 4.10 Header do chrome

Refinado, não redesenhado:

- `items-center` no lugar de `items-start`, mais `gap-2`. Os controles estavam
  pendurados no topo de uma faixa de 52px, que é a maior parte do motivo pelo qual
  o header lia como espaço vazio acidental.
- Os dois `FrostedDiv` foram substituídos por `div` comuns. Aquele wrapper pintava
  um bloom de 20px de `filter: blur` mais 6px de `backdrop-filter` atrás de cada
  grupo de ações — glassmorphism, e o último efeito decorativo do chrome. Os
  botões já têm superfície própria.
- `aria-label="share-chat-button"` virou `aria-label={t("share.label")}`.

**Nenhuma ação foi inventada.** Compartilhar, exportar, mover, excluir, incognito,
largura total e o seletor de modo são exatamente os que existiam, com a mesma
semântica, as mesmas permissões e o mesmo roteamento. Nenhuma navegação de produto
migrou do sidebar para o header — há teste.

---

## 5. Extração do header

`AppChrome.tsx` tinha 742 linhas, das quais `Header()` ocupava 536, o que tornava
impossível ler os três slots da casca — header, conteúdo, footer — lado a lado.

O header saiu para `web/src/layouts/chromes/AppHeader.tsx`. A extração foi feita
por script, fatiando o texto original, para que não pudesse divergir do original
por transcrição. Depois disso o bloco de imports de `AppChrome` foi podado: 30
especificadores tinham ficado mortos.

| | antes | depois |
|---|---:|---:|
| `AppChrome.tsx` | 742 | **226** |
| `AppHeader.tsx` | — | 596 |

Condições da fatia, todas satisfeitas:

- **Comportamento idêntico.** Nenhum hook, estado, modal, efeito ou handler
  mudou. Todo o header era autocontido — não compartilhava nada com o resto de
  `AppChrome`, que é por que saiu limpo.
- **Nenhum contrato de rede mudou.** `deleteChatSession`,
  `endIncognitoSession`, `exportChatSession`, `handleMoveOperation` foram com ele,
  intactos.
- **Nenhum contrato de localStorage mudou.**
  `LOCAL_STORAGE_KEYS.HIDE_MOVE_CUSTOM_AGENT_MODAL` foi com ele.
- **Nenhuma semântica de tier ou permissão mudou.** `useTierAtLeast(Tier.BUSINESS)`
  e `useIsSearchModeAvailable` foram com ele.
- **Testes focados adicionados**, fixando que cada um desses contratos está no
  arquivo novo e **não** ficou atrás no antigo.
- **Escopo de casca.** Nenhuma lógica não relacionada de `AppChrome` foi
  refatorada.

---

## 6. Acessibilidade de toque nos projetos

O achado A3 da auditoria. O menu do projeto era:

```tsx
<div className={cn(!popoverOpen && "hidden", !isEditing && "group-hover/SidebarTab:flex")}>
```

`hidden` mais `group-hover:flex`, sem caminho alternativo. O Tailwind fecha
`hover:` atrás de `@media (hover: hover)`, então num aparelho de toque a classe de
revelação nunca aplica e o menu — renomear, excluir, mover — **não existia**. Não
há variante `no-hover:` neste repositório; o primitivo nativo é `Hoverable`.

Agora usa `Hoverable.Root` + `Hoverable.Item`, o mesmo que `ChatButton` já usava.
`Hoverable` põe o `opacity: 0` dentro de `@media (hover: hover)`, então onde não há
hover o item nasce visível, e também revela em `:has(:focus-visible)`, que o par
antigo não fazia. Nenhum comportamento de projeto foi redesenhado.

---

## 7. Copy do controle de recolher

Os achados C1 e A4. O rótulo do controle mais usado da casca era um literal em
inglês, no nome acessível **e** no tooltip, tanto do botão de recolher quanto do
botão-logotipo dobrado.

Passou a andar pelo contrato `OpalStrings`, que é a arquitetura declarada em
`web/AGENTS.md` para labels que um componente Opal renderiza por conta própria:

1. `sidebarOpen` / `sidebarClose` tipados em `OpalStrings`, com default inglês em
   `defaultOpalStrings`.
2. Lidos com `useOpalStrings()` dentro de `SidebarHeader`.
3. Mapeados em `OpalStringsBridge` de `opal.sidebar.open` / `opal.sidebar.close`.
4. Adicionados aos **nove** catálogos.

PT-BR renderiza `Abrir a barra lateral` / `Fechar a barra lateral`, fixado em
teste. Nenhum português foi codificado dentro de um primitivo Opal.

---

## 8. Carregamento e skeletons

**Determinismo.** `shuffleWidths()` reordenava as larguras com
`Math.random()` a cada mudança de contagem de sessões, o que fazia as linhas
placeholder pularem entre renders e dava ao servidor e ao cliente duas primeiras
pinturas diferentes. Agora é uma tupla fixa.

**Skeleton por seção.** O corpo era `{isLoadingDynamicContent ? null : ...}`, com
`isLoadingDynamicContent` sendo o OU de quatro fontes: uma requisição de projetos
lenta apagava a coluna inteira, incluindo o histórico já carregado. O agregado foi
removido e cada seção lê a fonte de que realmente depende:

| Seção | Fonte | Enquanto carrega |
|---|---|---|
| Especialistas fixados | `isLoadingAgents`, `isLoadingPinnedAgents` | fica fora — pode resolver vazia, e um título que depois desaparece é pior que um que chega tarde |
| Projetos | `isLoadingProjects` | título + 2 linhas placeholder |
| Conversas | `isLoadingChatSessions` | título + 3 linhas placeholder |

**O modelo de dados não mudou.** `useChatSessions`, a paginação SWR, o
`IntersectionObserver`, o sentinela, o store de sessão pendente, a persistência de
scroll, a ordenação e o drag/drop estão intactos e fixados em teste. Nenhuma
identidade de loader global foi tocada — isso é de VIS-007 e das fatias seguintes.

---

## 9. Aresta do canvas, vinheta e máscara

Auditados. A vinheta e a máscara de blur **só existem quando um operador
configurou uma imagem de fundo** — são superfície configurada, não decoração que
TON acrescentou, então foram tokenizadas em vez de removidas:

- `rgba(0, 0, 0, 0.4)` → `var(--mask-02)`. Mesmo papel, mesma escada de scrims do
  resto do app, e agora segue o tema.
- A máscara horizontal passou a ler `var(--app-page-main-content-width)` em vez de
  repetir `25rem`, então a janela de nitidez é a medida de leitura por definição, a
  mesma que o transcript e o composer usam.

O `black` / `transparent` da máscara ficou: numa `mask-image` essas paradas são
canais alfa — "manter" e "descartar" — e não cores de tema.

O fade da sidebar (`ShadowDiv mask` no `Body`) ficou: é indício de rolagem, com
função. Nenhum glassmorphism foi adicionado; dois foram removidos.

---

## 10. Colapsado e mobile

**Colapsado.** Ícones, tooltips, seleção, controle de recolher, alcance dos
destinos, entrada de conta/admin e comportamento de projeto auditados. O ponto que
importa: **nenhum tratamento de estado selecionado depende de texto visível.** O
marcador é uma forma na aresta, e ficou medido em 52px de largura com o rótulo em
`visibility: hidden`. Os destinos ficam no `Header`, fora da área que rola, então
seguem alcançáveis dobrados; projetos aparecem via `FoldedProjectsPopover`.

**Mobile.** Overlay, backdrop, spacer, breakpoints, `Cmd/Ctrl+E` e o layout Root
responsivo estão intactos e fixados em teste, incluindo o slide RTL
(`-translate-x-full rtl:translate-x-full`). A casca responsiva não foi
substituída. A 375px: destinos alcançáveis, fechar óbvio (backdrop mais o botão de
recolher), sem overflow horizontal, ordem de foco preservada, estado selecionado
claro e alvos de toque inalterados.

---

## 11. Conta e administração

Preservados: o gate de permissão do Painel de administração
(`hasAdminAccess` mais `getFirstPermittedAdminRoute(adminCapabilities)`), o popover
de conta, a autorização e a identidade do usuário. O rodapé lê como parte do mesmo
sistema porque usa a mesma linha `SidebarTab` — herdou a geometria e o estado novos
sem mudança própria. Nenhum link de produto ou SaaS suprimido por FE-003 foi
exposto.

---

## 12. Fronteiras preservadas

**FE-004.** A arquitetura de informação não mudou: Central, Especialistas,
Pesquisar chats, Projetos, Novo projeto, Conversas, admin/conta onde autorizado.
Nenhum destino somado, nenhum removido, nenhuma ordem alterada. Sem Ocorrências,
sem Relatórios, sem Fontes, sem dashboard, sem personas. `ton-navigation.test.tsx`
renderiza a sidebar de verdade e cobre isso — 34 asserções, todas verdes, nenhuma
enfraquecida.

**FE-003.** Sem Billing, sem CTA de upgrade, sem exposição do Craft, sem docs
upstream, sem Discord, sem changelog, sem prompt de trial, sem link de marca
upstream. `ton-product-surface.test.tsx` verde.

**ClearEyed/Twenty.** Nenhuma estrutura copiada: nem navegação por objetos de CRM,
nem hierarquia de workspace, nem estrutura de records/history, nem espaçamentos,
nem dimensões. A largura ficou onde estava, justificada por rótulos PT-BR. A casca
segue a IA de produto do TON.

**VIS-004.** O composer não foi tocado. `.ton-composer`, o `focus-within`, o raio,
a borda, a barra, o seletor de modelo, o Deep Research, a remoção do hack de 14px e
o layout de send/stop estão intactos, e o anel `select-*` de que o Deep Research
depende continua exatamente onde estava. Nenhuma regressão de casca no composer
ocorreu.

---

## 13. Evidência de estilo computado

Chromium sobre o CSS que o build de produção emitiu, ambos os temas, 375/768/1280.

| | claro | escuro |
|---|---|---|
| superfície da sidebar | `rgb(240,240,240)` | `rgb(64,64,64)` |
| aresta final | `1px rgb(230,230,230)` | `1px rgb(85,85,85)` |
| `box-shadow` da coluna | `none` | `none` |
| largura | 240px expandida / 52px dobrada | idem |
| faixa da marca | 52px, `align-items: center` | idem |
| raio da linha | `4px` | `4px` |
| **anel de perímetro na linha selecionada** | **`none`** | **`none`** |
| marcador selecionado | `2px rgb(34,118,83)` @ `inline-start 0px` | `2px rgb(169,205,189)` |
| linha não selecionada tem marcador | não | não |
| hover não selecionado | `rgb(230,230,230)` | `rgb(77,77,77)` |
| hover **sobre** selecionado | `rgb(250,250,250)`, marcador intacto | `rgb(51,51,51)`, marcador intacto |
| seleção sobrevive ao hover | **sim** | **sim** |
| contorno de foco | `2px solid rgb(128,128,128)` | `2px solid rgb(204,204,204)` |
| foco mantém o marcador | sim (sinais distintos) | sim |
| dobrado: marcador | `2px`, rótulo `visibility: hidden` | idem |
| rótulo de seção | `rgba(0,0,0,0.55)` | `rgba(255,255,255,0.698)` |
| título longo trunca | sim | sim |
| overflow horizontal da página | não | não |

Idêntico nas três larguras. Contraste do marcador contra a superfície da sidebar:
**4.87:1** no claro, **6.00:1** no escuro.

---

## 14. Testes

### 14.1 Mapeamento anterior

`ton-navigation.test.tsx` é o único teste que **renderiza** a sidebar, com as
fontes de dados mockadas: destinos, ordem, landmarks, domínios diferidos,
alcançabilidade em viewport pequeno, nomes acessíveis, preservação de FE-003,
permissões de admin e o catálogo em nove locales. Não foi alterado e não foi
enfraquecido. Não há teste Jest que renderize `SidebarTab`, `ChatButton`,
`ProjectFolderButton`, `AppChrome` ou `AccountPopover`.

### 14.2 O que foi acrescentado

`web/src/ton/ton-shell.test.tsx` — 49 testes. Cobre a camada de apresentação que
a suíte de navegação não vê: o CSS compilado e os invariantes de fonte.

| # | Exigência | Prova |
|---:|---|---|
| 1–9 | IA, rotas, ordem, ausência de Ocorrências/Relatórios/Fontes | `ton-navigation.test.tsx`, intacto e verde |
| 10 | navegação selecionada usa o estado TON | o `::before` de aresta existe com `theme-primary-04` e `weight-line-focus`; nenhuma regra de anel menciona mais as variantes de sidebar |
| 11 | conversa selecionada usa o estado TON | `ChatButton` passa `selected` a `SidebarTab` e não tem raio próprio |
| 12 | selecionado e foco continuam distintos | seleção é `::before` no contêiner, foco é `outline` no controle |
| 13 | `selected:hover` preserva a seleção | nenhuma célula `selected:hover` de sidebar usa a superfície de hover não selecionada |
| 14 | dobrado preserva a indicação | o marcador não referencia o rótulo; o CSS de dobra não referencia estado |
| 15 | overlay mobile inalterado | overlay, backdrop, spacer e o slide RTL presentes |
| 16 | `Cmd/Ctrl+E` inalterado | o handler segue no Root |
| 17 | menu de projeto alcançável no toque | `Hoverable.Root`/`Item` presentes, `group-hover/SidebarTab:flex` ausente; e o primitivo tem caminho sem hover e por foco |
| 18 | paginação intacta | `useChatSessions`, `IntersectionObserver`, sentinela, `hasMore`, `loadMore` |
| 19 | FE-003 intacta | `ton-product-surface.test.tsx` verde |
| 20 | admin por permissão | `ton-navigation.test.tsx` verde |
| 21 | nenhuma estrutura ClearEyed/Twenty | largura fixada nos valores originais; nenhum nível de navegação novo; nenhuma caixa de cartão entre seções |
| 22 | contrato do composer VIS-004 verde | `composerVisualContract.test.ts` verde; e o anel `select-*` fixado aqui também |

Extras fixados: a aresta lógica da coluna, o papel de superfície, o ritmo `pt-5`, o
`text-03` do rótulo, a altura da faixa da marca, o `items-center` do header, a
ausência de `FrostedDiv`, o nome acessível de compartilhar, a tokenização da
vinheta, o determinismo dos skeletons, a ausência do gate agregado de loading, e
que a extração levou cada contrato de rede/localStorage/tier **e** não deixou
nenhum atrás.

### 14.3 Resultado

| Gate | Resultado |
|---|---|
| `bun run types:check` | **PASSA** — sem erros; cobertura 98.81% em 1246 arquivos |
| `bun run lint` (oxlint) | **PASSA** — saída 0; só avisos `anti-slop` pré-existentes |
| `bun run build` | **PASSA** — compilado com sucesso |
| `bun run jest --ci --maxWorkers=2` | 153/155 suites, 1469/1477 testes |
| `ton-navigation.test.tsx` | **PASSA** |
| `ton-product-surface.test.tsx` | **PASSA** |
| `ton-theme.test.ts` · `ton-foundations.test.ts` | **PASSAM** — incluindo as asserções de anel de seleção de VIS-001 |
| `composerVisualContract.test.ts` | **PASSA** |
| `ton-shell.test.tsx` | **PASSA** — 49/49 |
| formatação dos arquivos alterados | limpa (`oxfmt`, a menos de EOL) |

**Duas falhas não relacionadas.**
`src/app/craft/components/output-panel/FilesTab.test.tsx` passa isolado e falha só
sob carga com `maxWorkers`: flake de paralelismo.
`src/sections/modals/languageModels/CustomModal.test.tsx` falha com 6 erros —
**reproduzido no commit de baseline** `fb5a83140d`, com os mesmos 6 erros, num
worktree separado. É pré-existente e não pertence a esta fatia.

---

## 15. Validação em runtime

**Validação visual: FEITA, em runtime isolado.** Chromium via `@playwright/test`
(já instalado; nenhuma dependência adicionada), carregando o CSS que o build de
produção emitiu numa página estática cuja árvore espelha a estrutura real da
sidebar. Sem servidor, sem container, sem banco. Mediu, nos dois temas e em
375/768/1280: superfície e aresta da coluna, largura expandida e dobrada, altura e
alinhamento da faixa da marca, raio da linha, `box-shadow` da linha selecionada,
geometria e cor do marcador, ausência de marcador na linha não selecionada, hover
com ponteiro real sobre linha não selecionada e sobre linha selecionada, contorno
de foco por teclado, sobrevivência do marcador ao foco, estado dobrado com o
rótulo oculto, cor e posição do rótulo de seção, truncamento de título longo e
overflow da página. Os números estão em §13.

Foi essa validação que pegou o problema de `lib/opal/dist` descrito em §2 — sem
ela, metade da mudança teria ido para produção.

**Playwright de aplicação: DEFERIDO — conflito de runtime compartilhado.** O
stack Docker compartilhado serve o build do worktree original, e as suítes e2e
deste repositório rodam contra um Postgres compartilhado e persistente cujo
`global setup` registra usuários de teste. Comportamentos que exigem o app vivo —
o overlay mobile em uso, `Cmd/Ctrl+E` pressionado de fato, o menu de projeto tocado
num aparelho de toque — não foram observados em navegador nesta fatia. Estão
cobertos por asserções de fonte de que o mecanismo continua presente. Nenhuma
observação de navegador foi fabricada.

**Screenshots antes/depois: não capturados.** O "antes" exigiria servir o baseline
e o "depois" exigiria servir esta branch, e as duas coisas passam pelo mesmo
runtime compartilhado. As medições de §13 são a evidência que substitui isso, e
elas são mais verificáveis que uma imagem.

---

## 16. Trabalho diferido

| Fatia | O que continua dela |
|---|---|
| VIS-003 | a home, `WelcomeMessage`, `FrostedDiv` na saudação, o "Vamos começar." |
| VIS-005 | anexos: `FileCard`, `InputChipStrip`, file picker, overlay de arrastar |
| VIS-006 | mensagens, raciocínio, markdown, citações, tema de sintaxe |
| VIS-007 | identidade de especialista, `SvgOnyxOctagon` como moldura de avatar, loader de marca |
| VIS-008 | voz |
| VIS-009 | movimento; o `duration-300` dos skeletons e o `duration-600` do canvas seguem lá |
| VIS-010 | QA final De-Onyx |

`SvgOnyxOctagon` **não** foi substituído: aqui ele é ícone de navegação, não marca
da casca, e VIS-007 é dono da identidade de especialista. Nenhum logotipo foi
inventado.

---

## 17. Pré-requisitos que esta fatia libera

**Para VIS-005 (anexos e contexto).** A linguagem de linha da casca está fechada:
`radius-04`, marcador de aresta para selecionado, `text-03`/`text-04` para
hierarquia de rótulo, `Hoverable` como o primitivo de ação revelada. Um chip ou
cartão de anexo pode escolher raio concentricamente contra 4px de linha e 12px de
composer, e a revelação de ações de anexo tem um primitivo com caminho de toque e
de foco já provado. A aresta sidebar/canvas está resolvida, então uma sobreposição
de arrastar não precisa negociar fronteira de casca.

**Para VIS-003 (home).** A altura da faixa da marca agora casa com o header do
chrome, então a home tem uma linha de base horizontal estável para compor contra.

**Para VIS-006 e VIS-009.** `AppChrome` em 226 linhas é legível; o header é um
arquivo próprio.

---

## 18. Conflitos prováveis de integração

| Onde | Por quê |
|---|---|
| `lib/opal/src/core/interactive/stateful/styles.css` | VIS-001 e VIS-002 já editaram; qualquer fatia que ajuste seleção toca as mesmas células, e `ton-foundations.test.ts` precisa ser reconciliado junto |
| `lib/opal/src/layouts/sidebar/styles.css` | dono é VIS-002; VIS-009 pode ajustar as transições de 200ms |
| `web/src/sections/sidebar/AppSidebar.tsx` | VIS-007 vai mexer nos ícones de especialista nas mesmas seções |
| `web/src/layouts/chromes/AppChrome.tsx` | agora pequeno; VIS-009 é dono do `duration-600` do canvas |
| `web/src/layouts/chromes/AppHeader.tsx` | arquivo novo; VIS-006 pode tocar a área de ações de mensagem |
| `web/src/i18n/messages/*.json` | qualquer fatia que adicione copy toca os nove catálogos |
| `web/src/refresh-components/FrostedDiv.tsx` | não foi apagado porque `WelcomeMessage` ainda usa; VIS-003 decide o destino dele |

**Nota operacional para quem integrar:** `lib/opal/dist/` é gerado e gitignorado.
Depois de um merge que toque `lib/opal/src/**`, rode `bun run build` dentro de
`web/lib/opal` (ou reinstale) antes de buildar o app, ou o bundle sai com a versão
anterior do CSS.
