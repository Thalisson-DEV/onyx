# TON-VIS-001 — fundações e linguagem de superfície

**Status: DONE.** Executado em worktree isolado `../ton-vis-001`, branch
`ton/vis-001`, a partir de `70203b8630419de051e285ba35dfcbf1792c34bc` (branch
`main`, árvore limpa). Esse baseline contém TON-FE-000, FE-001, FE-002, FE-002.1,
FE-003, FE-004, TON-VIS-000 e os Planos backend 001, 002, 003a–003d, 007 e 008a.

Nível máximo aplicado: **2 (estilo)**. Nenhum arquivo em `backend/` mudou.
Nenhuma dependência nova. Nenhuma página, composer, sidebar, home, mensagem,
anexo, identidade de especialista ou voz foi redesenhada.

Insumo: [`000-de-onyx-visual-audit.md`](./000-de-onyx-visual-audit.md). Alvo:
[`visual-language.md`](./visual-language.md). Sequência:
[`visual-implementation-roadmap.md`](./visual-implementation-roadmap.md).

---

## 1. O que mudou, em uma frase

As superfícies estruturais e as bordas genéricas passaram a ser **neutras de
verdade** nos dois temas; o verde Vale Norte ficou reservado para identidade,
foco e seleção; borda, raio, elevação, estado, movimento e reduced-motion agora
têm camada de token e teste.

---

## 2. Decisão central — o neutro já existia

A auditoria pedia "escuro neutro, não escuro verde" e presumia que isso exigiria
uma rampa nova. A inspeção do código mostrou o contrário: `primitives.json` já
tem uma rampa **neutra verdadeira** (`grey-100 … grey-00`, todos com R=G=B), usada
pelo tema claro. O viés verde vinha de um único ponto: os 17 aliases `tint-*`
apontavam para `vale-norte-neutral-*`, que são carvões esverdeados.

Por isso VIS-001 **não criou árvore de token paralela**. Ele:

1. repontou os 17 aliases `tint-*` para `grey-*`;
2. repontou as superfícies e bordas estruturais escuras para `grey-*`;
3. **removeu** os 20 primitivos `vale-norte-neutral-*`, que ficaram sem nenhum
   consumidor (verificado por grep em `web/`, `mobile/` e `widget/`);
4. acrescentou **dois** passos neutros que a rampa não tinha, para fechar a
   escada escura: `grey-88` `#1f1f1f` e `grey-55` `#626262`.

`tint-*` continua sendo o **único ponto de troca** de tom de superfície. Mudou só
para onde ele aponta. As rampas de marca `vale-norte-green-*` e
`vale-norte-gold-*` não foram tocadas.

---

## 3. Valores finais

### 3.1 Escuro

| Papel | Token semântico | Alias | Primitivo | Valor | Antes |
|---|---|---|---|---|---|
| `field` | `background-neutral-00` | — | `grey-94` | `#0f0f0f` | `#0b1410` |
| `surface-raised` | `background-tint-00` | `tint-97` | `grey-88` | `#1f1f1f` | `#18231d` |
| `canvas` | `background-tint-01` | `tint-93` | `grey-80` | `#333333` | `#27332c` |
| `surface` | `background-tint-02` | `tint-88` | `grey-75` | `#404040` | `#344139` |
| `surface-hover` | `background-tint-03` | `tint-83` | `grey-70` | `#4d4d4d` | `#414f47` |
| anel interno de foco | `background-tint-04` | `tint-76` | `grey-55` | `#626262` | `#56655d` |

Bordas escuras:

| Token | Primitivo | Valor | Antes |
|---|---|---|---|
| `border-01` | `grey-60` | `#555555` | `#44524a` |
| `border-02` | `grey-50` | `#808080` | `#5b6a62` |
| `border-03` | `grey-40` | `#a4a4a4` | `#78827c` |
| `border-04` | `grey-20` | `#cccccc` | `#cbd0cd` |
| `border-05` | `grey-00` | `#ffffff` | inalterado |

Também repontados para neutro: `background-neutral-01..04`
(`grey-88`/`grey-80`/`grey-75`/`grey-70`) e `background-code-01` (`grey-88`).

### 3.2 Claro

| Papel | Token | Alias | Primitivo | Valor | Antes |
|---|---|---|---|---|---|
| `canvas` | `background-tint-01` | `tint-02` | `grey-02` | `#fafafa` | `#f8f9f8` |
| `surface` | `background-tint-02` | `tint-05` | `grey-06` | `#f0f0f0` | `#eff2f0` |
| `surface-raised` | `background-tint-00` | — | `grey-00` | `#ffffff` | inalterado |
| `surface-hover` | `background-tint-03` | `tint-10` | `grey-10` | `#e6e6e6` | `#e3e7e4` |
| `field` | `background-neutral-00` | — | `grey-00` | `#ffffff` | inalterado |
| anel interno de foco | `background-tint-04` | `tint-20` | `grey-20` | `#cccccc` | `#cbd0cd` |

O claro não foi redesenhado. Ele só perdeu o viés verde residual: os deslocamentos
são de 1 a 3 níveis de cinza e a estrutura da escada é a mesma. As **referências**
de borda claras (`grey-10/20/40/50/100`) não mudaram, então o
`Vale Norte light theme lock` de `ton-theme.test.ts` continua verde sem edição.

O canvas continua **off-white, não branco puro**, e `surface-raised` continua
branco — a hierarquia estrutural do claro permanece perceptível.

---

## 4. Contraste medido

Calculado sobre os valores finais resolvidos, com a mesma matemática de
`ton-theme.test.ts` (composição alfa + luminância relativa WCAG).

### 4.1 Escada escura — cada passo ≥ 1.15

| Par | Razão |
|---|---|
| `field` → `surface-raised` | 1.16 |
| `surface-raised` → `canvas` | 1.30 |
| `canvas` → `surface` | 1.22 |
| `surface` → `surface-hover` | 1.23 |
| `surface-hover` → anel de foco | 1.39 |
| anel de foco vs `field` | **3.14** (mínimo 3) |

Nenhuma superfície é preto puro: a mais escura é `#0f0f0f`.

### 4.2 Texto escuro sobre o canvas `#333333`

| Token | Razão | Mínimo herdado |
|---|---|---|
| `text-04` | 10.60 | 7 |
| `text-03` | 7.02 | 4.5 |
| `text-02` | 5.01 | 4.5 |
| `text-01` (disabled) | 1.89 | — |

`text-03 / text-01` = 3.71 e `text-02 / text-01` = 2.65, os dois acima do fator 2
exigido. A escada continua estritamente ordenada, então `disabled` permanece o
elo mais fraco.

### 4.3 Bordas escuras

| Par | Razão | Mínimo |
|---|---|---|
| `border-01` vs `canvas` | 1.69 | 1.5 |
| `border-01` vs `surface-raised` | 2.21 | 1.8 |
| `border-01` vs `field` | 2.29 | 2 |
| `border-02` vs `border-01` | 1.89 | 1.3 |
| `border-03` vs `border-02` | 1.58 | 1.3 |
| `border-04` vs pior superfície (anel de foco) | 3.80 | 3 |
| `border-05` vs `field` | 19.2 | 3 |

### 4.4 Estados escuros

| Par | Razão | Mínimo |
|---|---|---|
| `background-tint-03` vs `-02` | 1.23 | 1.15 |
| `background-tint-00` vs `-02` | 1.59 | 1.3 |
| `action-selection-01` vs `canvas` | 1.29 | 1.2 |
| `surface` vs `action-selection-01` | 1.57 | 1.4 |
| `action-selection-05` vs `action-selection-01` | 3.10 | 3 |
| `background-neutral-03` vs `-00` | 1.85 | 1.5 |

### 4.5 Papel `selected` e papel `focus`, nos dois temas

`theme-primary-04` sobre cada papel de superfície:

| Superfície | Claro | Escuro |
|---|---|---|
| `canvas` | 5.32 | 7.31 |
| `surface` | 4.87 | 6.00 |
| `surface-raised` | 5.55 | 9.54 |
| `surface-hover` | 4.55 | 4.89 |
| `field` | 5.55 | 9.54 |

`border-04` (papel `focus`) sobre os mesmos cinco papéis: 3.16–3.95 no claro e
3.80–15.2 no escuro. Todos ≥ 3.

### 4.6 Desvios registrados, não escondidos

Três medidas ficam abaixo do alvo da especificação. Nenhuma foi introduzida por
VIS-001; todas são herdadas e estão fixadas em teste com o valor medido, não com o
alvo, para que uma regressão futura seja detectada sem que o documento minta.

| Medida | Alvo | Real | Dono |
|---|---|---|---|
| `border-01` sobre canvas claro | 1.5 | 1.20 | fatia de tema claro futura |
| `border-02` vs `border-01` claro | 1.3 | 1.29 | idem |
| `status-error-05` sobre canvas escuro | 3 | 2.62 | VIS-006 (apresentação de erro) |

Reforçar as bordas claras exigiria deslocar a rampa `border-01..05` inteira
(`grey-10 → grey-20 → grey-40 → grey-50 → grey-60`), o que muda a aparência de
toda superfície com borda no tema claro. A instrução de VIS-001 é explícita:
não redesenhar o claro de forma agressiva. Fica registrado, não feito.

---

## 5. Papéis de superfície e de borda

Os papéis existem como **aliases nomeados no preset**, sobre os mesmos tokens
numéricos. Não há segunda árvore de valores, e o vínculo papel → token está
fixado em `ton-theme.test.ts` e em `ton-foundations.test.ts`.

### 5.1 Superfície

| Papel | Classe | Token |
|---|---|---|
| canvas | `bg-surface-canvas` | `--background-tint-01` |
| surface | `bg-surface` | `--background-tint-02` |
| surface-raised | `bg-surface-raised` | `--background-tint-00` |
| surface-hover | `bg-surface-hover` | `--background-tint-03` |
| field | `bg-surface-field` | `--background-neutral-00` |

### 5.2 Borda

| Papel | Classe | Token | Uso |
|---|---|---|---|
| `subtle` | `border-border-subtle` | `--border-01` | separador interno, grade |
| `default` | `border-border-default` | `--border-01` | aresta normal de componente |
| `interactive` | `border-border-interactive` | `--border-02` | aresta que responde a hover |
| `selected` | `border-border-selected` | `--theme-primary-04` | item selecionado / ativo |
| `focus` | `border-border-focus` | `--border-04` | `focus-visible` |
| `error` | `border-border-error` | `--status-error-05` | validação |
| `attention` | `border-border-attention` | `--theme-amber-05` | atenção semântica |

**Refinamento da especificação candidata.** `visual-language.md` §4.1 propunha
`action-selection-04/05` para o papel `selected`, com mínimo de 3:1. Medindo os
dois: `action-selection-04` chega a 2.28:1 sobre a sidebar escura e
`action-selection-05` a 1.98:1 — a própria tabela se contradizia. `theme-primary-04`
**inverte entre temas** (verde escuro no claro, verde claro no escuro) e é o único
verde que fica ≥ 3:1 sobre os cinco papéis de superfície nos **dois** temas.

A divisão final é coerente com a hierarquia de meios: a **lavagem** de seleção
continua vindo da rampa de estado (`action-selection-01/02`) e o **anel** de
seleção vem da identidade (`theme-primary-04`). `visual-language.md` foi corrigido
com a medição.

---

## 6. Largura de borda

`weight-line-border` (1) existia e não estava ligado. Agora:

- `weight-line-focus` (2) foi acrescentado a `size.json`;
- o preset expõe `border-line`, `border-focus` e `outline-focus`, todos como
  `calc(var(--weight-line-*) * 1px)`;
- o anel de seleção e o contorno global de foco leem os tokens, não literais.

`border` (1px) e `border-2` (2px) do Tailwind **não** foram redefinidos: as classes
tokenizadas são aditivas. Verificado em CSS gerado, não presumido.

Borda estrutural padrão: **1px**. 2px aparece só em foco e no anel de seleção
pressionado.

---

## 7. Declaração global de borda

A auditoria encontrou duas declarações concorrentes em `globals.css`, com os
pseudo-elementos presos em `var(--color-gray-200)` — o cinza do Tailwind, cego a
tema. Resolvido em **uma** declaração intencional:

```css
@layer base {
  *,
  ::after,
  ::before,
  ::backdrop,
  ::file-selector-button {
    border-color: var(--border-01);
  }
}
```

O bloco `* { @apply border-border }` foi removido. `border-border` resolvia para
`var(--border-01)`, então para elementos reais o resultado é idêntico; o ganho é
que os pseudo-elementos passaram a seguir o tema. `ton-foundations.test.ts` afirma
que existe exatamente **uma** declaração de `border-color` no arquivo e que ela é
`var(--border-01)`.

---

## 8. Raio

A escala foi mantida: `radius-02` 2px · `radius-04` 4px · `radius-08` 8px ·
`radius-12` 12px · `radius-16` 16px · `radius-20` 20px · `radius-round` 62.5rem.

### 8.1 Papéis alvo

| Classe | Raio |
|---|---|
| controle compacto | `radius-04` |
| input, botão, linha de nav | `radius-04` / `radius-08` |
| cartão, composer, popover | `radius-08` / `radius-12` |
| dialog | `radius-12`, só onde for útil |
| circular | `radius-round`, só avatar, ponto de status e pílula semântica |

### 8.2 Convergência feita — sem mover geometria

A auditoria mediu que um terço dos raios do app usa `rounded-sm/md/lg/xl/2xl/3xl`
e ignora a escala. VIS-001 resolveu isso na **fundação**, não nos call sites:
os aliases do Tailwind foram repontados para os tokens TON, e cada valor é
idêntico ao default que substitui.

| Alias | Default Tailwind v4 | Token TON | Valor |
|---|---|---|---|
| `rounded-xs` | 0.125rem | `radius-02` | 0.125rem |
| `rounded-sm` | 0.25rem | `radius-04` | 0.25rem |
| `rounded-lg` | 0.5rem | `radius-08` | 0.5rem |
| `rounded-xl` | 0.75rem | `radius-12` | 0.75rem |
| `rounded-2xl` | 1rem | `radius-16` | 1rem |

Os defaults foram lidos de `node_modules/tailwindcss/theme.css`, e o mapeamento é
verificado em teste contra esses valores. **Nenhum pixel se move**; o que muda é
que essas classes passam a resolver por token.

`rounded-md` (0.375rem) e `rounded-3xl` / `rounded-4xl` (1.5rem / 2rem) não têm
passo TON e ficaram fora da escala de propósito.

### 8.3 Deferido

A conversão dos call sites individuais **não** foi feita. Motivos, na ordem em que
importam:

1. A contagem da auditoria (14 usos) não corresponde ao repositório: a varredura
   atual encontra dezenas, a maioria em `web/src/components/` (legado, em
   remoção), `web/src/lib/credentials/`, `web/src/sections/skills/` e
   `web/src/lib/projects/`.
2. Nenhum desses arquivos está na lista de escopo de VIS-001, e vários pertencem a
   VIS-005 (anexos e projetos) e a VIS-010 (limpeza final).
3. Converter mecanicamente contraria a regra explícita de não encolher todo raio
   sem razão semântica.

Os call sites `rounded-md` e `rounded-3xl` remanescentes ficam para a fatia dona
de cada superfície.

---

## 9. Elevação

### 9.1 Reenquadramento

| Nível | Uso | Token |
|---|---|---|
`elevation-0` | em fluxo: cartão, composer, linha | **sem sombra**; borda + superfície |
`elevation-1` | popover, dropdown, tooltip | `shadow-box-00` / `shadow-box-01` |
`elevation-2` | dialog, overlay modal | `shadow-box-02` |

### 9.2 Geometria reduzida

| Token | Antes | Depois |
|---|---|---|
| `shadow-box-00` | `0 0 2px 1px shadow-01` | `0 1px 2px 0 shadow-01` |
| `shadow-box-01` | `0 2px 12px 0 shadow-02, 0 0 4px 1px shadow-02` | `0 1px 2px 0 shadow-01, 0 4px 8px -2px shadow-02` |
| `shadow-box-02` | `0 2px 24px 0 shadow-03, 0 0 12px 12px shadow-03` | `0 2px 4px -1px shadow-02, 0 8px 16px -4px shadow-03` |

Todas as camadas passaram a ter deslocamento vertical e raio limitado a 16px. Uma
camada `0 0 Npx` com spread é halo, não sombra; era isso que produzia o
"glow" nos dois temas.

### 9.3 O brilho branco do escuro

Era a causa raiz e foi corrigida na origem: no escuro, `shadow-01/02/03` apontavam
para **alfas brancos** (`alpha-grey-00-05/10/20`). Agora apontam para alfas
**pretos** (`alpha-grey-100-30/45/60`). Com o raio reduzido, uma sombra escura
finalmente lê como sombra.

### 9.4 O que não foi removido

A sombra do composer (`shadow-box-01`) **continua lá**. Ela é a única aresta do
composer e o hack de 14px em três arquivos depende dela: **VIS-004 é o dono**.
Reduzir o raio da sombra é seguro nessa direção — o espaçador de 14px passa a ser
maior do que o necessário, e nunca menor, então não há risco de reintroduzir
clipping.

---

## 10. Linguagem de estado

### 10.1 Onde cada estado vive

| Estado | Mecanismo |
|---|---|
| `DEFAULT`, `HOVER`, `SELECTED` | células da matriz de `Interactive.Stateful` |
| `PRESSED` | `:active` e `data-interaction="active"` |
| `DISABLED` | `[data-disabled]` + `aria-disabled` |
| `FOCUS_VISIBLE` | `:focus-visible` global + regras de componente |
| `ACTIVE` | igual a `SELECTED` + `data-interactive-state` |
| `LOADING`, `RUNNING`, `ERROR`, `SUCCESS`, `ATTENTION` | do componente consumidor, sobre os papéis `status-*`, `theme-amber-*` e `border-*` |

A união interna de estado (`empty | filled | selected`) **não** precisou crescer:
`PRESSED` é uma célula de interação, não um valor de estado, e o DOM já publicava
`data-interaction`.

### 10.2 Defeito 1 — a seleção invertia sob o cursor

Era real nas cinco variantes: `selected:hover` reusava exatamente a superfície do
hover não selecionado, então passar o mouse apagava a seleção. Cada variante agora
faz hover **dentro da própria família**:

| Variante | `selected` | `selected:hover` | `selected:active` |
|---|---|---|---|
| `sidebar-heavy` | `tint-00` | `tint-01` (era `tint-03`) | `tint-02` |
| `sidebar-light` | `tint-00` | `tint-01` (era `tint-03`) | `tint-02` |
| `select-heavy` | `action-selection-01` | `action-selection-02` (era `tint-02`) | `action-selection-02` |
| `select-card` | `action-selection-01` | `action-selection-02` (era `tint-02`) | `action-selection-02` |
| `select-light` | transparente | `action-selection-01` (era `tint-02`) | `action-selection-01` |
| `select-filter` | `tint-inverted-03` | `tint-inverted-04` | inalterado — já não invertia |

O passo `tint-00 → tint-01 → tint-02` clareia no escuro e escurece no claro, e nos
dois casos permanece **fora** da série de hover não selecionado (`tint-03`,
`tint-04`). O passo `action-selection-01 → 02` intensifica nos dois temas. As duas
direções são determinísticas, o que era o requisito.

### 10.3 Defeito 2 — `PRESSED` não existia

`sidebar-heavy` e `sidebar-light` não tinham célula `:active`: pressionar era
idêntico a passar o mouse. Agora, não selecionado: hover `tint-03` → pressed
`tint-04`. Selecionado: hover `tint-01` → pressed `tint-02`.

### 10.4 O anel de seleção

`SELECTED` ganhou um anel de 1px, e `PRESSED` engrossa para 2px:

```css
box-shadow: inset 0 0 0 calc(var(--weight-line-border) * 1px)
  var(--theme-primary-04);
```

Três propriedades importam:

- **não é cor sozinha.** A espessura do anel distingue pressionado de hover sem
  depender de matiz, e o atributo `data-interactive-state` continua publicando o
  estado para leitor de tela e para teste.
- **não move geometria.** `box-shadow: inset` desenha dentro da caixa. O mesmo
  recurso já desenha a aresta de foco dos inputs (`inputs/shared.css`) e a borda
  do header em edição (`layouts/content/styles.css`), então é técnica de casa, não
  invenção.
- **disabled fica mais fraco.** Selecionado e desabilitado troca o verde por
  `border-01`: mantém a forma, perde a ênfase.

Auditado antes de aplicar: nenhum nó `.interactive` carrega utilitário de sombra,
então o anel não sobrescreve elevação de ninguém. `.opal-card[data-shadow]` e
`.opal-tabs-trigger` têm sombra própria e **não** passam por `Interactive`.

### 10.5 Alcance

Uma mudança central corrige as sete superfícies de seleção que a auditoria listou:
conversa selecionada, navegação ativa, especialista ativo, projeto selecionado,
Deep Research ativo, anexo ativo, e fonte ou ferramenta ativa. Esse era o
benefício e também o risco declarado da fatia.

---

## 11. Foco

Fundação global em `globals.css`:

```css
@layer base {
  :focus-visible {
    outline: calc(var(--weight-line-focus) * 1px) solid var(--border-04);
    outline-offset: 1px;
  }
}
```

Três consequências deliberadas:

1. Qualquer elemento focável que não desenhava foco passa a ter um contorno
   acessível — `border-04` fica ≥ 3:1 sobre os cinco papéis de superfície nos dois
   temas (§4.5).
2. Componentes que já têm tratamento próprio continuam ganhando: as regras deles
   ficam na camada `utilities`, que vence `base`. O foco inset de `SidebarTab`
   (`outline-offset-[-2px]`) não mudou.
3. **O composer não foi tocado.** Ele usa `outline-hidden`, um utilitário, então
   continua sem foco. Isso é intencional: A1 é o achado de a11y mais grave da
   auditoria e **VIS-004 é o dono** dele. VIS-001 entrega a linguagem que VIS-004
   vai aplicar.

---

## 12. Movimento

### 12.1 Tokens

Camada nova: `web/lib/shared/tokens/motion.json`.

| Token | Valor |
|---|---|
| `duration-instant` | 120ms |
| `duration-fast` | 150ms |
| `duration-base` | 200ms |
| `duration-slow` | 280ms |
| `easing-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` |
| `easing-out` | `cubic-bezier(0, 0, 0.2, 1)` |
| `easing-in` | `cubic-bezier(0.4, 0, 1, 1)` |

Expostos como `duration-instant|fast|base|slow` e `ease-standard|out|in`.

**Os valores não foram importados de referência nenhuma.** As três curvas são
exatamente `--ease-in-out`, `--ease-out` e `--ease-in` do Tailwind v4, lidas de
`node_modules/tailwindcss/theme.css` — as mesmas que o app já usa como palavra
reservada. `duration-fast` (150ms) é o `--default-transition-duration` do Tailwind
e a duração de `.interactive`. `duration-base` (200ms) é a dobra da sidebar. A
faixa 120–280ms é a faixa que a auditoria mediu, e o teste a fixa.

Nenhuma animação existente foi migrada: **VIS-009 é o dono** do passe final.

### 12.2 Reduced motion

Antes existiam quatro blocos escopados e nenhum reset global, então
`animate-pulse`, `animate-waveform`, `animate-fade-in-up` e todo `duration-150`
continuavam rodando para quem pediu menos movimento (achado A9). Agora:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }

  [data-motion="essential"],
  [data-motion="essential"] * {
    animation-duration: var(--motion-essential-duration, 1s) !important;
    animation-iteration-count: var(--motion-essential-iterations, infinite) !important;
  }
}
```

Duas escolhas explicam o resto:

- **0.01ms, não 0s.** `transitionend` e `animationend` continuam disparando, então
  o `Presence` do Radix ainda desmonta e nada fica preso na tela.
- **escape hatch.** `data-motion="essential"` mantém indicador de progresso
  operacional rodando. Nenhum componente usa o atributo hoje; é vocabulário para
  as fatias seguintes, e está documentado e testado.

`SvgSimpleLoader` recebeu `motion-safe:animate-spin`, alinhando o spinner mais
usado do admin ao que `IconLoader` e `OnyxLoader` já fazem (achado A10).
`OnyxLoader` **não** foi tocado: o loader de marca é de VIS-007 / VIS-009.

---

## 13. Blur

Escala degenerada corrigida:

| Token | Antes | Depois |
|---|---|---|
| `backdrop-blur-01` | 2px | 2px |
| `backdrop-blur-02` | 1px | 4px |
| `backdrop-blur-03` | 1px | 8px |

Consumo real, verificado: só `backdrop-blur-03` é usado em produção — overlay de
modal (`modal/styles.css`), backdrop da sidebar mobile, `CommandMenu`, `Spinner`,
`MCPPageContent` e `OpenApiPageContent`. `-01` e `-02` não têm consumidor.

Como `-03` é o único em uso e sempre em backdrop de overlay real, ele passou de
1px (perceptualmente nada) para 8px, que é blur de backdrop de verdade. Blur
continua sendo para backdrop, não para vidro decorativo.

---

## 14. Espaçamento — **não** foi remapeado

Decisão: **não ligar `spacing` ao preset.** A razão é aritmética, não estética.

Os tokens são **denominados em px**: `spacing-block-4` = `0.25rem`,
`spacing-block-16` = `1rem`. Os utilitários do Tailwind são **denominados em
passos**: `p-4` = `calc(var(--spacing) * 4)` = `1rem`. Ligar as chaves faria `p-4`
resolver para `0.25rem` — **um quarto** do valor atual — em todo `p-*`, `px-*`,
`py-*`, `m-*`, `gap-*` e `space-*` do aplicativo.

Isso viola diretamente a regra de segurança da fatia, então não foi feito.
Confirmado em CSS gerado que `p-4` continua `calc(var(--spacing) * 4)` e
`gap-2` continua `calc(var(--spacing) * 2)`. `ton-foundations.test.ts` afirma que
o preset não tem chave `spacing`, `padding`, `margin` nem `gap`.

**Correção à auditoria:** os 25 passos `spacing-block-*` / `spacing-inline-*`
**não são órfãos**. O formato `js/nativewind-theme` do Style Dictionary os
converte no `theme.extend.spacing` do mobile
(`style-dictionary.config.mjs`, formato `js/nativewind-theme`). Removê-los
quebraria o mobile. Ficam, e a documentação registra que são vivos lá e
deliberadamente não ligados na web.

Caminho futuro, para a fatia que quiser resolver: renomear as chaves para a
denominação de passo (`spacing-1 … spacing-40`) e só então ligar, ou expor aliases
semânticos e migrar componente a componente. Nenhuma migração em massa aqui.

---

## 15. Largura de leitura

Havia cinco constantes concorrentes. VIS-001 introduziu **um** nome semântico
ligado à fonte que o app já usa para layout:

```js
width:    { reading: "var(--app-page-main-content-width)" }
maxWidth: { reading: "var(--app-page-main-content-width)" }
```

`--app-page-main-content-width` já vale 45rem / 720px em `opal/src/styles/sizes.css`,
que é exatamente a largura com que a página de conversa já se desenha. Adotar
`max-w-reading` **não move nada**.

Migrar os call sites ficou para quem é dono deles: `MSG_MAX_W` (720px literal em
`ChatUI.tsx`) é de VIS-006, a máscara de 800px do canvas é de VIS-002, e
`max-w-200` do chat compartilhado é de VIS-004. `width.message-default` (740px)
**não** foi removido: ele tem um consumidor real
(`components/tools/ExpandableContentWrapper.tsx`), contrariando a auditoria.

---

## 16. Tipografia e KH Teka

`heading-h1` era o único preset com px cru. Agora referencia métrica:
`height-font-display` (3rem = 48px) e `height-line-display` (4rem = 64px), ambos
novos em `size.json`. O valor resolvido é idêntico — 48px/64px — nos três formatos
gerados (web, NativeWind, RN).

**KH Teka: não adotar, remoção deferida.** A fonte está carregada e tokenizada e
nenhum preset a referencia. Decisão de produto: ela **não entra** no sistema de
tipo TON, porque a instrução é não introduzir nem aplicar fonte de display nova.

A remoção física não foi feita por escopo, não por dúvida: o `@font-face` está em
`web/lib/opal/src/styles/typography.css`, o token em `tokens/typography.json` e os
dois `.otf` em `web/public/fonts/` — nenhum desses arquivos está no escopo de
VIS-001. Os únicos consumidores são três `style` inline em superfícies Craft
suprimidas (`BuildWelcome.tsx`, `IntroContent.tsx`, `WelcomePageMock.tsx`).
**Deferido para VIS-010** (QA final De-Onyx), junto com a remoção dos ativos.

O resto da tipografia não foi tocado. A escada de heading do markdown
(`--tw-prose-headings` igual a `--tw-prose-body`) é o ganho grande apontado pela
auditoria e é **de VIS-006**.

---

## 17. Resíduo upstream

| Resíduo | Situação |
|---|---|
| `onyx-ink-100/95/90` | **removido** de `primitives.json` e do preset |
| `onyx-chrome-20/10/00` | **removido** de `primitives.json` e do preset |
| `shimmer-base` / `-highlight` hex cru | **tokenizado**: `{grey-40}`/`{grey-100}` no claro, `{grey-55}`/`{grey-00}` no escuro |
| `--color-gray-200` em pseudo-elementos | **removido** (§7) |
| `#888` de scrollbar | **tokenizado**: `var(--scrollbar-thumb)` / `var(--scrollbar-track)` |
| sombras escuras como brilho branco | **corrigido** (§9.3) |
| `vale-norte-neutral-*` esverdeado no canvas | **removido**; `tint-*` aponta para `grey-*` |
| `#33C19E` | **drift da auditoria — ver abaixo** |

Antes de remover as duas rampas `onyx-*`, grep confirmou zero consumidores em
`web/`. As ocorrências restantes no repositório são independentes: `widget/` tem a
sua própria cópia literal em `widget/src/styles/colors.ts` (não consome estes
tokens) e `backend/ee/.../usage_report_pdf.py` tem um comentário.

### 17.1 `#33C19E` — a auditoria errou o local e a natureza

O plano manda substituir `#33C19E` em `web/src/components/icons/icons.tsx` por um
token TON. **Esse arquivo não tem hex nenhum.** Grep no repositório inteiro
encontra a cor em dois lugares:

- `web/lib/opal/src/logos/bifrost.tsx` — `className={cn(className, "text-[#33C19E]!")}`
- `web/src/components/icons/icons.test.tsx:66` — a asserção que cobre o de cima

`SvgBifrost` é o **logo de um fornecedor terceiro**, um dos 93 logos de
fornecedor que a própria auditoria contou em `web/lib/opal/src/logos/` (§10.4).
`#33C19E` é a cor de marca do Bifrost, não menta do Onyx. Trocá-la pelo verde
Vale Norte descaracterizaria a marca de terceiro — exatamente o oposto do que a
auditoria decidiu para os ícones de conector, que classificou como
KEEP: "identidade de terceiro, não Onyx" (§5.5, `SourceTag` `IconStack`).

Somado a isso, `web/lib/opal/src/logos/` não está na lista de escopo de VIS-001.

**Resolução: nenhuma mudança, drift registrado.** Se produto quiser padronizar a
apresentação de logos de fornecedor, isso é uma decisão de marca para VIS-010, não
uma correção de token de fundação.

---

## 18. Testes

### 18.1 `web/lib/opal/src/ton-theme.test.ts` — estendido

Atualizado no **mesmo commit** que os tokens. Nenhuma asserção antiga foi
enfraquecida; a escada escura, o texto escuro, o foco escuro e o lock do tema
claro passam sem edição, porque as referências de primitivo do claro não mudaram.

Grupos novos:

- **`TON neutral surface foundation`** — toda superfície estrutural e toda borda
  genérica é neutra de verdade (R=G=B) nos dois temas; as referências neutras do
  escuro estão fixadas nome a nome; o canvas escuro é `#333333` e o campo
  `#0f0f0f`; o canvas claro é `#fafafa` e não branco puro; os 17 aliases `tint-*`
  apontam para `grey-*`; nenhum primitivo `onyx-ink-*`/`onyx-chrome-*` sobrou;
  nenhum token semântico de cor carrega valor cru.
- **`TON border role foundation`** — os sete papéis resolvem nos dois temas;
  `selected` e `focus` ≥ 3:1 sobre os cinco papéis de superfície; `subtle` visível
  sobre o canvas; `interactive` separado de `default`; `error` distinto de
  `attention`.
- **`TON identity colour discipline`** — `theme-primary-*`, `action-selection-*` e
  `action-text-link-05` só referenciam `vale-norte-green|gold`; nenhum deles
  resolve para o mesmo valor de `theme-green-05`; `theme-green-05` continua sendo
  `green-*` upstream; `disabled` continua o texto mais fraco nos dois temas.

30 testes, todos passando.

### 18.2 `web/lib/opal/src/ton-foundations.test.ts` — novo

Invariantes estáticas para o que contraste não mede: pesos de linha tokenizados e
ligados; `border`/`border-2` do Tailwind intactos; **uma** declaração de
`border-color`, tema-aware e cobrindo pseudo-elementos; nenhum cinza cego a tema
sobrando; vocabulário de movimento presente, dentro da faixa medida e estritamente
crescente; reset global de reduced-motion com escape hatch; `motion-safe` no
spinner; escala de raio preservada e aliases mapeados **contra os defaults reais do
Tailwind**; três níveis de sombra com raio limitado; blur monotônico e sem passos
repetidos; papéis de superfície e de borda nomeados; nenhuma classe `onyx-*` no
preset; **nenhuma chave de espaçamento no preset**; largura de leitura ligada;
`selected:hover` nunca cai na superfície de hover não selecionado; variantes de
sidebar com célula `:active`; seleção com anel. Mais higiene do escopo alterado:
zero `dark:`, zero cor bruta da paleta Tailwind, zero hex cru.

28 testes, todos passando.

### 18.3 Regressão

| Suíte | Resultado |
|---|---|
| `ton-theme.test.ts` | 30 passam |
| `ton-foundations.test.ts` | 28 passam |
| `ton-navigation.test.tsx` | passa **sem alteração de asserção** |
| `ton-product-surface.test.tsx` | passa |
| `ton-privacy.test.tsx` | passa |
| `ton-web-only.contract.test.tsx` | passa |
| Jest completo | **153 suítes, 1382 testes, todos passam** |

A primeira execução completa (`maxWorkers: 50%`) reprovou 7 suítes / 39 testes
com `Unable to find an element…` e um `<body><div /></body>` vazio — nenhuma delas
de superfície TON. Diagnóstico, não suposição: as 7 passam com as mudanças
guardadas (54/54), passam com as mudanças restauradas (54/54), e a execução
completa com `--maxWorkers=2` passa inteira. É contenção de recurso do ambiente,
não regressão. Jest, além disso, mocka CSS e não roda Tailwind, então as mudanças
de CSS e de preset não podem alcançar aquelas suítes.

### 18.4 Portões

| Portão | Resultado |
|---|---|
| `bun run build:tokens` | ok |
| `bun run verify:tokens` | **skip limpo** — ver abaixo |
| `bun lib/opal/scripts/bundle-css.mjs` | ok, `dist/root.css` regenerado |
| `bun run types:check` | sem erros; cobertura 98.81% |
| `bun run lint` | exit 0; só warnings pré-existentes, nenhum em arquivo alterado |
| `oxfmt --check` nos arquivos alterados | limpo |

**Sobre `verify:tokens`:** ele compara com
`origin/main:web/lib/opal/src/styles/colors.css`, que **não existe mais** naquele
ref. O script trata isso como o estado pós-migração esperado e sai com 0
("parity check skipped"). Ou seja, o portão está **inerte** desde que a migração
Opal → shared entrou. Isso é comportamento projetado, não falha, mas vale
registrar: ele **não** protegeu nenhuma das mudanças desta fatia. Quem protege é
`ton-theme.test.ts`.

`bun run format:check` reprova em todos os 1404 arquivos de `src/`, inclusive em
arquivos que esta fatia não tocou. Causa: `core.autocrlf=true` neste checkout
Windows, então a árvore de trabalho tem CRLF e o oxfmt espera LF. Falha de
ambiente, pré-existente, confirmada em arquivo commitado e intocado. O conteúdo
**commitado** é LF e está formatado: `oxfmt --check` passa nos sete arquivos de
código alterados.

---

## 19. Validação de runtime

**RUNTIME VALIDATION EXECUTADA — em runtime isolado, por medição.**
**A revisão de captura de tela da aplicação continua deferida.**

### 19.1 O que foi possível, e por quê

Não existe stack Onyx no ar: `http://localhost:3000` e `http://localhost:8080`
não respondem e `docker ps` não lista contêiner nenhum. Subir a stack foi
recusado pelas mesmas razões que VIS-000 registrou, todas ainda válidas: altera
estado Docker compartilhado, `onyx-web_server-1` roda imagem pronta sem bind
mount (serviria o código do baseline e daria falso positivo), e um segundo
frontend contra o mesmo PostgreSQL faria o global-setup do Playwright registrar
usuários no banco compartilhado.

Existe, porém, um runtime **seguro e isolado** que serve exatamente esta camada:
o **Storybook** do próprio repositório. Ele importa `src/app/globals.css`, logo
carrega os tokens reais, o build real do Tailwind e a classe `.dark` real, e não
depende de backend, banco, Docker nem usuário. Foi iniciado em porta dedicada
(6017) e conduzido por Playwright com o Chromium já instalado.

### 19.2 O que foi medido, não observado

O relatório lê **estilo computado de um navegador vivo**, não pixels
interpretados. Todos os valores abaixo vêm daí.

Tokens resolvidos por tema, em `getComputedStyle(document.documentElement)`:

| Token | Claro | Escuro |
|---|---|---|
| `--background-tint-01` (canvas) | `#fafafa` | `#333333` |
| `--background-tint-02` (surface) | `#f0f0f0` | `#404040` |
| `--background-tint-00` (raised) | `#ffffff` | `#1f1f1f` |
| `--background-tint-03` (hover) | `#e6e6e6` | `#4d4d4d` |
| `--background-tint-04` (anel interno) | `#cccccc` | `#626262` |
| `--background-neutral-00` (field) | `#ffffff` | `#0f0f0f` |
| `--border-01` | `#e6e6e6` | `#555555` |
| `--border-04` | `#808080` | `#cccccc` |
| `--theme-primary-04` | `#227653` | `#a9cdbd` |

`body` no escuro resolve para `rgb(51, 51, 51)`. **O canvas escuro é carvão
neutro, não carvão verde** — verificado em runtime, não deduzido.

Declaração global de borda, em elemento **e** em pseudo-elemento:

| Leitura | Claro | Escuro |
|---|---|---|
| `div` `borderColor` | `rgb(230, 230, 230)` | `rgb(85, 85, 85)` |
| `div::before` `borderColor` | `rgb(230, 230, 230)` | `rgb(85, 85, 85)` |

O pseudo-elemento **segue o tema**. O `#e5e7eb` (`rgb(229, 231, 235)`) que a
auditoria encontrou não aparece em nenhum dos dois temas.

### 19.3 Estado selecionado, hover e pressionado

Medido em `SidebarTab` real (`Interactive.Stateful`, variante `sidebar-heavy`),
com hover e `mouse.down()` de verdade:

| Leitura | Claro | Escuro |
|---|---|---|
| selecionado, em repouso | `#ffffff` + anel `rgb(34,118,83)` 1px inset | `#1f1f1f` + anel `rgb(169,205,189)` 1px inset |
| selecionado, hover | `#fafafa` + anel 1px | `#333333` + anel 1px |
| selecionado, pressionado | `#f0f0f0` + anel **2px** | `#404040` + anel **2px** |
| não selecionado, hover | `#e6e6e6`, sem anel | `#4d4d4d`, sem anel |
| não selecionado, pressionado | `#cccccc`, sem anel | `#626262`, sem anel |

Os dois defeitos auditados estão fechados, e o sondador afirmou isso
explicitamente: `selectionSurvivesHover: true` (o fundo do selecionado sob o
cursor **não** é o fundo do hover não selecionado) e
`pressedDiffersFromHover: true`, nos dois temas.

### 19.4 Foco

Medido com navegação real por `Tab` em `<button>` real, com `:focus-visible`
confirmado pelo próprio navegador (`node.matches(":focus-visible") === true`):

| Tema | Contorno |
|---|---|
| claro | `2px solid rgb(128, 128, 128)`, offset `1px` |
| escuro | `2px solid rgb(204, 204, 204)`, offset `1px` |

São exatamente `border-04` de cada tema, na largura de `weight-line-focus`.

### 19.5 Desabilitado

`data-disabled="true"` e `aria-disabled="true"` presentes, `opacity: 0.5`,
`cursor: not-allowed`, e nenhum anel de seleção — nos dois temas. Desabilitado
continua o estado mais fraco e não depende só de cor.

### 19.6 Elevação, blur, raio, espaçamento e largura de leitura

| Leitura | Claro | Escuro |
|---|---|---|
| `shadow-box-00` | `rgba(0,0,0,0.05) 0 1px 2px 0` | `rgba(0,0,0,0.3) 0 1px 2px 0` |
| `shadow-box-01` | `…0.05 0 1px 2px`, `…0.1 0 4px 8px -2px` | `…0.3 0 1px 2px`, `…0.45 0 4px 8px -2px` |
| `shadow-box-02` | `…0.1 0 2px 4px -1px`, `…0.2 0 8px 16px -4px` | `…0.45 0 2px 4px -1px`, `…0.6 0 8px 16px -4px` |

**As sombras escuras são preto, não branco.** O brilho branco acabou, medido em
runtime.

| Utilitário | Valor resolvido |
|---|---|
| `backdrop-blur-01` / `-02` / `-03` | `blur(2px)` / `blur(4px)` / `blur(8px)` |
| `rounded-sm` | `4px` |
| `rounded-04` | `4px` |
| `p-4` | `16px` |
| `border-line` | `1px` |
| `max-w-reading` | `720px` |

`rounded-sm` e `rounded-04` resolvem para o **mesmo** `4px`: o realias de raio é
neutro em geometria. `p-4` continua `16px`: a semântica numérica de espaçamento
do Tailwind **não** mudou. As duas afirmações centrais de segurança da fatia
estão verificadas em navegador, não presumidas.

### 19.7 Reduced motion

Com `prefers-reduced-motion: reduce` real no contexto do navegador:

| Leitura | Valor |
|---|---|
| decorativo, `transition-duration` | `1e-05s` |
| decorativo, `animation-duration` | `1e-05s` |
| decorativo, `animation-iteration-count` | `1` |
| `[data-motion="essential"]`, `animation-duration` | `1s` |
| `[data-motion="essential"]`, `animation-iteration-count` | `infinite` |

O movimento decorativo colapsa e o indicador operacional continua rodando,
exatamente como projetado.

### 19.8 Limites honestos desta validação

1. **Nenhuma captura de tela da aplicação foi produzida.** Um primeiro passe de
   48 capturas foi descartado: as imagens saíram com o spinner de carregamento do
   Storybook, ou seja, não mostravam a história renderizada. Elas **não** foram
   usadas como evidência e o diretório de sondagem foi apagado. Nenhuma
   observação visual foi inventada a partir delas.
2. O que foi validado é a **fundação**: tokens, superfície, borda, foco, estado,
   elevação, blur, raio, espaçamento e movimento, em componentes Opal reais.
   Isso é exatamente o que VIS-001 mudou.
3. O que **não** foi validado é a **composição da aplicação**: canvas de
   conversa, slab da sidebar dentro da casca, e diálogo/popover no contexto de
   página. Storybook renderiza o primitivo, não a tela.
4. As medidas de estado, foco, elevação e movimento foram lidas a 1280px. A
   varredura `375 / 768 / 1280` de composição de página continua pendente.

**Pendente, com critério de aceite:** quando existir ambiente que sirva este
branch, revisar `375 / 768 / 1280` × claro / escuro olhando canvas da aplicação,
superfície da sidebar, canvas de conversa e diálogo/popover em contexto. Tudo o
que é token-level já está medido acima.

Toda medida de contraste da §4 vem de cálculo sobre os valores finais resolvidos,
com a matemática de `ton-theme.test.ts`, e está afirmada em teste. Toda afirmação
sobre CSS gerado vem de ler o CSS de produção do `next build` ou de compilar um
stylesheet de sondagem pelo PostCSS + Tailwind v4 reais; as duas sondagens foram
apagadas.

---

## 20. Escopo — o que não foi tocado

| Fronteira | Confirmação |
|---|---|
| `backend/` | nenhum arquivo alterado |
| Dependências | nenhuma adicionada; `bun.lock` sem mudança de conteúdo |
| IA de FE-004 | intacta; `ton-navigation.test.tsx` passa sem alteração de asserção |
| Sanitização de FE-003 | intacta; `ton-product-surface.test.tsx` passa |
| VIS-002 sidebar / casca | nenhum arquivo de sidebar, `AppChrome` ou `AppSidebar` alterado |
| VIS-003 home | `AppPage`, `WelcomeMessage`, `NRFPage`, `Suggestions` intactos |
| VIS-004 composer | `AppInputBar`, `BaseInputBar`, `SharedAppInputBar` intactos; sombra e hack de 14px preservados |
| VIS-005 anexos | `FileCard`, `InputChipStrip`, `Dropzone` intactos |
| VIS-006 mensagens | `custom-code-styles.css`, `Resubmit`, `ReasoningRenderer`, `ShimmerText` intactos |
| VIS-007 identidade | `SvgOnyxOctagon`, `CustomAgentAvatar`, `AgentCard`, `radial-00` intactos |
| VIS-008 voz | nenhum arquivo de voz alterado |
| VIS-009 movimento | só a camada de token e o reset; nenhuma animação migrada |
| `dark:` | zero nos arquivos alterados, afirmado em teste |
| Cor bruta do Tailwind | zero nos arquivos alterados, afirmado em teste |

Mudanças de primitivo compartilhado alcançam a sidebar, a home, o composer e as
mensagens **por token**. Isso é intencional e é o objetivo da fatia; nenhuma
composição mudou.

---

## 21. Arquivos

Fonte de token:

- `web/lib/shared/tokens/primitives.json`
- `web/lib/shared/tokens/semantic-light.json`
- `web/lib/shared/tokens/semantic-dark.json`
- `web/lib/shared/tokens/size.json`
- `web/lib/shared/tokens/shadow.json`
- `web/lib/shared/tokens/typography-presets.json`
- `web/lib/shared/tokens/motion.json` *(novo)*

Ligação e estilo:

- `web/lib/opal/tailwind-preset.cjs`
- `web/lib/opal/src/core/interactive/stateful/styles.css`
- `web/lib/opal/src/icons/simple-loader.tsx`
- `web/src/app/globals.css`
- `web/tailwind-themes/tailwind.config.js`

Teste:

- `web/lib/opal/src/ton-theme.test.ts`
- `web/lib/opal/src/ton-foundations.test.ts` *(novo)*

Documentação:

- `plans/ton/frontend/001-visual-foundations.md` *(novo)*
- `plans/ton/frontend/visual-language.md`
- `plans/ton/frontend/visual-implementation-roadmap.md`

`web/lib/shared/dist/` e `web/lib/opal/dist/` foram regenerados pelo comando
canônico e continuam gitignored; nada gerado foi commitado nem editado à mão.

---

## 22. Deferido, com dono

| Item | Dono |
|---|---|
| Foco do composer, aresta por borda, remoção do hack de 14px, raio 12px | VIS-004 |
| Aresta da sidebar, contraste do rótulo de seção, máscara e vinheta do canvas | VIS-002 |
| Escada de heading do markdown, tema de sintaxe, erro tokenizado, `MSG_MAX_W` | VIS-006 |
| Geometria única de anexo, `rounded-xl` de projetos e skills | VIS-005 |
| `radial-00`, octógono, `agentAvatarIconMap` com `theme-green-05` | VIS-007 |
| Migração das animações para os tokens de duração | VIS-009 |
| Remoção física de KH Teka (`@font-face`, token, dois `.otf`) | VIS-010 |
| Decisão de marca sobre logos de fornecedor (`#33C19E` do Bifrost) | VIS-010 |
| Reforço das bordas do tema claro para 1.5:1 | fatia de tema claro futura |
| Renomear as chaves de espaçamento para denominação de passo e então ligar | fatia futura, se houver |

---

## 23. Pré-requisitos exatos para VIS-004

VIS-004 é a próxima fatia da ordem recomendada. Tudo de que ela precisa está
pronto:

1. **Aresta por borda.** `border-border-default` / `border-border-interactive`
   existem, com largura tokenizada (`border-line`). O composer pode trocar
   `shadow-box-01` por borda de 1px sem literal nenhum.
2. **Foco.** O padrão está definido e medido: borda `border-05` mais anel interno
   `background-tint-04`, o mesmo que `inputs/shared.css` já usa, com
   `background-tint-04` a 3.14:1 do campo no escuro. `outline-focus` e
   `border-focus` estão disponíveis. O composer precisa **remover**
   `outline-hidden` do editável e adicionar `focus-within` no contêiner — a regra
   global não alcança um `outline-style: none` vindo de utilitário.
3. **Raio.** `rounded-12` já é tokenizado. `rounded-16 → rounded-12` no composer
   é uma troca de classe.
4. **Sombra.** `shadow-box-01` continua existindo, com raio menor. Ao removê-la do
   composer, remover **junto** os dois espaçadores animados
   (`AppPage.tsx:986-991` e `:1041-1046`) e a compensação `pb-2`/`py-2`
   (`AppChrome.tsx:647`), mais as três notas que os explicam.
5. **Largura de leitura.** `max-w-reading` já resolve para os 720px que o composer
   e o transcript usam.
6. **Movimento.** `duration-instant` para a borda de foco, `duration-fast` para a
   barra de ferramentas.
7. **Deep Research ativo.** Usar `border-border-selected` com mudança sutil de
   superfície. Sem glow: `shadow-box-*` é elevação, e o teste de elevação limita o
   raio.

Nada em VIS-004 depende de token novo.

---

## 24. Conflitos prováveis de integração

| Onde | Por quê |
|---|---|
| `web/lib/shared/tokens/*.json` | qualquer fatia que edite token toca os mesmos arquivos; o conflito é textual e fácil, mas `ton-theme.test.ts` precisa ser reconciliado junto |
| `web/lib/opal/src/ton-theme.test.ts` | VIS-001 acrescentou ~260 linhas; outra fatia que estenda o mesmo arquivo conflita no fim dos blocos |
| `web/src/app/globals.css` | VIS-002 vai mexer na máscara e na vinheta e VIS-007 vai remover `radial-00`, no mesmo arquivo |
| `web/lib/opal/tailwind-preset.cjs` | qualquer fatia que exponha token novo edita as mesmas chaves |
| `stateful/styles.css` | VIS-002 vai ajustar a apresentação da linha de navegação sobre as mesmas células |
| `web/tailwind-themes/tailwind.config.js` | VIS-006 provavelmente remove larguras mortas ao migrar `MSG_MAX_W` |

Risco maior, e não é textual: **a matriz de `Interactive` é compartilhada.** Uma
fatia que ajuste seleção localmente em cima do anel novo produz sinal duplicado.
A ordem recomendada continua sendo a defesa: VIS-004 antes de VIS-002.
