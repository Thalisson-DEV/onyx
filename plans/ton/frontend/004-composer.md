# TON-VIS-004 — composer

**Status: DONE.** Somente frontend. Nenhum arquivo em `backend/` mudou. Nenhuma
dependência nova.

Executado no worktree isolado `../ton-vis-004`, branch `ton/vis-004`, a partir de
`4ed516668538f5eaeae2a6ce2f540f672f302d05` (branch `main`, árvore limpa). Esse
baseline contém TON-FE-000 a FE-004, VIS-000, VIS-001, e os Planos backend 001,
002, 003a–003d, 007 e 008a.

Insumos: [`000-de-onyx-visual-audit.md`](./000-de-onyx-visual-audit.md) §5.4,
§R1–R2, §A1–A2, I1–I3 · [`001-visual-foundations.md`](./001-visual-foundations.md)
§23 · [`visual-language.md`](./visual-language.md) §4, §5, §8 ·
[`visual-implementation-roadmap.md`](./visual-implementation-roadmap.md) VIS-004 ·
[`004-ton-navigation.md`](./004-ton-navigation.md) (FE-004) · `web/AGENTS.md`.

---

## 1. Conclusão executiva

O composer deixou de ser um cartão flutuante e passou a ser um campo. A aresta
que antes era sombra agora é borda mais contraste de superfície, o raio caiu de
16px para 12px, e o controle principal do produto **ganhou tratamento de foco**,
que era o achado de acessibilidade mais grave da auditoria (A1).

Três consequências de simplificação vieram juntas:

1. Os dois espaçadores animados de 14px em `AppPage.tsx` desapareceram.
2. A compensação de padding do footer em `AppChrome.tsx` desapareceu, e com ela
   a única razão pela qual o footer lia a rota.
3. As três notas `@raunakab` que explicavam o contorno desapareceram.

O `id` duplicado de `onyx-chat-input-send-button` (A2) foi resolvido, o seletor
de modelo passou de duas posições para uma, e o overlay de vidro do composer
falso do chat compartilhado saiu.

Nada da base técnica madura mudou: o editor `contentEditable`, os rascunhos, a
fila, os atalhos de `/`, a colagem, o upload, a voz e os contratos de send/stop
estão intactos. **Nível de mudança aplicado: 3 (composição local).**

---

## 2. Arquitetura anterior do composer

| Aspecto | Antes |
|---|---|
| Aresta | `shadow-box-01`, **sem borda nenhuma** |
| Superfície | `bg-background-neutral-00` |
| Raio | `rounded-16` (16px) |
| Elevação | sombra com espalhamento de ~14px |
| Foco | **nenhum** — `outline-hidden` no editável, nada no contêiner |
| Barra | `h-11` fixo, `justify-between`, sem `min-w-0`, sem estratégia de overflow |
| Deep Research ativo | `select-light` + `selected` (fundo transparente) |
| Seletor de modelo | **dois** call sites, aparências diferentes |
| `id` de envio | **duplicado** no DOM em modo busca |
| Desabilitado (compartilhado) | overlay `backdrop-blur-xs bg-background-neutral-00/50` |

A sombra não era decorativa: era a única aresta. E por estender ~14px além da
caixa dentro de um contêiner `overflow-auto`, obrigou a três compensações de
layout em três arquivos diferentes.

---

## 3. Contrato visual final

Todo o cromo do composer vive numa regra única, em
`web/src/app/css/content-editable.css`. Os três composers a consomem, então a
linguagem não pode divergir entre eles.

```text
.ton-composer                          estático, usado pelos três
  background-color   var(--background-neutral-00)      papel `field`
  border             calc(var(--weight-line-border) * 1px) solid var(--border-01)
  border-radius      var(--radius-12)
  transition         border-color, box-shadow @ var(--duration-instant) var(--easing-standard)

.ton-composer-interactive:hover        só onde se digita
  border-color       var(--border-02)                  papel `interactive`

.ton-composer-interactive:focus-within só onde se digita
  border-color       var(--border-05)
  box-shadow         inset 0 0 0 calc(var(--weight-line-focus) * 1px) var(--background-tint-04)
```

**Por que CSS e não utilitários Tailwind.** As camadas do Tailwind v4 colocam
`utilities` acima de `base`. Uma cor de borda vinda de utilitário
(`border-border-default`) venceria qualquer regra de `:hover`/`:focus-within` em
`base`, e duas regras de mesma especificidade na camada `utilities` decidiriam
por ordem de emissão — frágil. Declarar as três células na mesma regra, com
hover antes de focus, torna a precedência determinística. É exatamente o que
`.opal-input[data-variant="primary"]` já faz para todo campo do produto, e o
composer agora segue esse mesmo padrão em vez de inventar um.

Nenhum token novo foi criado. Nenhum valor cru: cada declaração referencia um
token de VIS-001.

### 3.1 Escolhas de borda e superfície

| Estado | Papel | Token |
|---|---|---|
| repouso | `default` | `border-01` |
| hover | `interactive` | `border-02` |
| foco | aresta de foco de input | `border-05` + anel interno `background-tint-04` |

`border-05` + `background-tint-04` é o par que `001-visual-foundations.md` §23
item 2 prescreve e que `inputs/shared.css` já usa. `border-focus` (`border-04`) é
o anel genérico de `:focus-visible` para quem **não** desenha o próprio foco; o
composer desenha, então usa o par de campo, mais forte.

### 3.2 Raio

`radius-12` (0.75rem = **12px**), medido no navegador. Era `radius-16` (1rem =
16px). Nenhum alvo de toque interno encolheu: a barra continua `h-11` (44px) e os
botões Opal continuam no tamanho `lg`.

### 3.3 Elevação

`elevation-0`. Zero `box-shadow` de elevação nas três regras; a única declaração
`box-shadow` do cromo é o anel **inset** de foco, que não projeta nada fora da
caixa. Popovers e dropdowns mantêm a elevação legítima deles, intocada.

---

## 4. Remoção da sombra e do contorno de 14px

`shadow-box-01` saiu dos três composers. Nada decorativo entrou no lugar.

Hacks removidos, com o que cada um era:

| Arquivo | O que saiu |
|---|---|
| `web/src/sections/input/AppInputBar.tsx` | a nota de 8 linhas explicando que `shadow-box-01` estende ~14px, e o `cn()` que só existia para hospedá-la |
| `web/src/views/AppPage.tsx` | a nota `@raunakab` de 17 linhas; o espaçador **superior** (`isSearch ? "h-[14px]" : "h-0"`); o espaçador **inferior** (`appPosition.isChat() ? "h-[14px]" : "h-0"`) — ambos `transition-all duration-150 ease-in-out overflow-hidden` |
| `web/src/layouts/chromes/AppChrome.tsx` | a nota de 15 linhas; o ternário `appPosition.isChat() ? "pb-2" : "py-2"`; e o `useAppPosition()` do `Footer`, que existia só para alimentar esse ternário |

**Invariante exigida — sem clipping.** Verificada no navegador: a caixa do
composer é 359×90 a 375px e 720×90 a 768px e 1280px, `scrollWidth` igual a
`clientWidth` em todos os casos, e `document.scrollWidth == clientWidth` nas três
larguras. Não há mais nada para recortar, porque com `box-sizing: border-box` a
borda de 1px fica **dentro** da caixa e o anel de foco é `inset`.

Efeito colateral aceito: em conversa o intervalo entre composer e footer passou
de 14px (espaçador) + 0 (padding removido) para 8px (`py-2` incondicional), que é
o mesmo valor de todas as outras posições. O footer deixou de depender da rota.

---

## 5. Foco

O foco vive no **contêiner**, via `focus-within`, e não no editável.

`outline-hidden` **permanece** no editável dos dois composers reais. Isso desvia
do item 2 de `001-visual-foundations.md` §23, que sugeria removê-lo, e a razão é
concreta: o wrapper do editável é `overflow-hidden` porque `useContentEditable`
mede e escreve a altura dele para o autosize. A fundação global de foco de
VIS-001 é `outline: 2px solid var(--border-04)` com `outline-offset: 1px`, e um
contorno deslocado desenhado dentro de um `overflow-hidden` é recortado. Aplicá-lo
ali produziria um anel cortado dentro de outro anel. `focus-within` no contêiner
entrega o mesmo sinal, inteiro, e uma vez.

### 5.1 Evidência de estilo computado

Chromium, CSS emitido pelo build de produção, ambos os temas:

| | claro | escuro |
|---|---|---|
| canvas | `rgb(250,250,250)` | `rgb(51,51,51)` |
| superfície do composer | `rgb(255,255,255)` | `rgb(15,15,15)` |
| borda em repouso | `1px rgb(230,230,230)` | `1px rgb(85,85,85)` |
| borda em hover | `rgb(204,204,204)` | `rgb(128,128,128)` |
| borda em foco | `1px rgb(0,0,0)` | `1px rgb(255,255,255)` |
| anel de foco | `rgb(204,204,204) 0 0 0 2px inset` | `rgb(98,98,98) 0 0 0 2px inset` |
| `box-shadow` em repouso | `none` | `none` |
| raio | `12px` | `12px` |

Contraste medido (composição alfa considerada):

| Par | claro | escuro |
|---|---|---|
| borda de foco (`border-05`) vs campo | **21.00:1** | **19.17:1** |
| anel interno (`background-tint-04`) vs campo | 1.61:1 | 3.14:1 |
| borda em hover (`border-02`) vs campo | 1.61:1 | 4.85:1 |
| borda em repouso (`border-01`) vs canvas | 1.20:1 | 1.69:1 |
| superfície do composer vs canvas | 1.04:1 | 1.52:1 |

**Sem deslocamento de layout.** A largura da borda é `1px` em repouso **e** em
foco; só a cor muda, e o anel é `inset`. Caixas medidas idênticas: 359×90 → 359×90
a 375px, 720×90 → 720×90 a 768px e 1280px, mesma origem. Nenhum controle interno
é recortado, o caret continua visível e o contraste do texto não muda
(`text-04` 10.37:1 no claro, 15.43:1 no escuro).

**Hover não vence foco.** Verificado com ponteiro real sobre um composer focado:
a aresta permanece `border-05` com o anel, nas duas temáticas e nas três larguras.

### 5.2 A aresta continua distinguível do canvas

Este era o risco declarado da fatia. Números:

- **Claro.** A borda nova mede 1.20:1 contra o canvas. A sombra removida
  (`shadow-box-01`) tinha como camada mais densa `0 0 4px 1px var(--shadow-02)`,
  e `shadow-02` no claro é `#0000001a`, ou **1.26:1** contra o canvas — no pico,
  antes de decair ao longo de 12px de blur. A borda entrega praticamente o mesmo
  contraste como linha nítida de 1px ao longo de todo o perímetro, em vez de um
  gradiente difuso. A aresta não enfraqueceu; ficou mais precisa.
- **Escuro.** Ganho claro: borda a 1.69:1 contra o canvas **mais** um degrau real
  de superfície de 1.52:1 (campo mais escuro que o canvas, como um campo
  encaixado deve ler). A sombra antiga rendia 1.35:1 no pico.

O 1.20:1 do claro é o valor **herdado** da rampa `border-01`, o mesmo que
`visual-language.md` §4.1 registra e que VIS-001 documentou explicitamente como
abaixo do alvo de 1.5:1 e fora do escopo de correção, porque reforçá-lo desloca a
rampa `border-01..05` inteira e muda toda superfície com borda do tema claro. O
composer agora tem exatamente a mesma aresta que todo `.opal-input` do produto:
não está pior que o resto, e antes não tinha borda nenhuma.

---

## 6. Barra de ferramentas

A barra continua uma linha `h-11` (44px) — `h-11` foi mantido de propósito,
porque o colapso em modo busca **anima altura** e `auto` não é animável.

O que mudou é a prioridade, que era o defeito R1: `justify-between` sem `min-w-0`
significa que nenhum grupo encolhe, então em tela estreita a linha transbordava.

### 6.1 Modelo de prioridade

| Classe | Controles | Tratamento |
|---|---|---|
| **PRIMARY** | entrada de anexo; send/stop | nunca encolhem; send/stop em `shrink-0`; o anexo é o **primeiro** item, então fica visível em repouso |
| **SECONDARY** | ferramentas; Deep Research / leitura de aba | dentro do grupo rolável |
| **CONTEXTUAL** | chip de ferramenta forçada | dentro do grupo rolável; só existe nesse estado |

A classificação não criou nem removeu recurso nenhum. Ela só torna a composição
em tela estreita determinística.

### 6.2 Estratégia de overflow

```text
barra          flex justify-between items-center w-full gap-1 … h-11 … transition-all duration-fast
grupo esquerdo flex flex-row items-center min-w-0 flex-1 overflow-x-auto no-scrollbar -my-1 py-1
grupo direito  flex flex-row items-center gap-1 shrink-0
```

- `min-w-0 flex-1` permite ao grupo secundário encolher. Sem isso, o
  `min-width: auto` de item flex mantinha o grupo no tamanho de conteúdo e
  empurrava send/stop para fora.
- `overflow-x-auto` faz o excedente **rolar**, não desaparecer. Nenhum controle é
  escondido por breakpoint: não há `hidden`/`sm:hidden` no composer, e há teste
  fixando isso. Esconder ação essencial sem caminho alternativo é a falha que a
  fatia proíbe.
- `no-scrollbar` é o utilitário que já existe em `globals.css`, com `scrollbar-width: none`.
- `-my-1 py-1` se cancelam: a caixa externa não muda de altura, mas a caixa de
  recorte fica 8px mais alta que os botões de 32px, então o contorno de foco de um
  botão dentro do container de rolagem não é cortado.
- `duration-150` virou `duration-fast`, o token de VIS-001 para o mesmo 150ms.

### 6.3 Comportamento medido

Pior caso montado de propósito: anexo + ferramentas + Deep Research **ativo com
rótulo** + chip de ferramenta forçada longa + microfone + enviar.

| Largura | Página transborda | Composer transborda | Grupo secundário rola | Send alcançável | Largura do editor |
|---|---|---|---|---|---|
| **375px** | não (375/375) | não (357/357) | **sim** | sim | 333px |
| **768px** | não (768/768) | não (718/718) | não | sim | 694px |
| **1280px** | não (1280/1280) | não (718/718) | não | sim | 694px |

Idêntico nos dois temas. A 375px o grupo secundário rola internamente em vez de
transbordar a página — que é precisamente a garantia pedida.

Alvos de toque não encolheram: os botões seguem no tamanho `lg` do Opal (32px de
container), o mesmo do baseline. VIS-004 não os reduziu.

---

## 7. Deep Research

Só a apresentação mudou; `toggleDeepResearch`, `showDeepResearch` e o gate de
`hasSearchToolsAvailable` estão intactos.

```text
inativo  variant="select-light"  state="empty"     foldable
ativo    variant="select-heavy"  state="selected"  não dobra
```

**Inativo.** Fundo transparente, rótulo `text-04`, ícone `text-03`, dobrado no
ícone até o hover. Silencioso e neutro, como pedido.

**Ativo.** Institucional, por três sinais simultâneos:

| Sinal | Valor | Contraste vs campo (claro / escuro) |
|---|---|---|
| anel de seleção | `theme-primary-04`, inset, de VIS-001 | **5.55:1 / 11.09:1** |
| mudança de superfície | `action-selection-01` | 1.19:1 / 1.18:1 — contida, de propósito |
| rótulo e ícone | `action-selection-05` | 7.96:1 / 3.65:1 |
| forma | o rótulo desdobra e passa a ficar sempre visível | — |

O que carrega o estado é o **anel** (≥5.5:1) e a **forma**, não a cor: a lavagem
de superfície é deliberadamente fraca. Isso satisfaz "mudança sutil de surface"
sem depender de cor sozinha.

Sem neon, sem glow, sem gradiente, sem sparkle, sem animação de "magia de IA".
Há teste fixando a ausência de `shadow-box`, `blur`, `glow`, `radial` e `sparkle`
nesse arquivo.

A troca de `select-light` para `select-heavy` no estado ativo é o que fornece a
lavagem; ambos os variants já existiam em Opal e ambos já recebiam o anel de
VIS-001, então nada foi adicionado ao design system.

---

## 8. Seletor de modelo

**Antes:** dois call sites em `AppPage.tsx` com o mesmo componente e envoltórios
diferentes — um à direita da saudação na home (`Section justifyContent="between"`),
outro num bloco `pb-1` acima do composer em conversa. Como `Fade` usa
`AnimatePresence`, na transição home → conversa os dois coexistiam por 150ms, e
nessa janela `data-testid="model-selector"` aparecia duas vezes no DOM.

**Depois:** um call site, no contexto do composer, imediatamente acima dele, em
todos os estados que oferecem escolha de modelo.

O gate novo é a **união exata** dos dois antigos, para que nenhum estado mude de
comportamento:

```ts
const modelSelectorVisible =
  !!activeAgent &&
  (appPosition.isChat() ||
    (isWelcomeFocus &&
      llmManager.hasAnyProvider &&
      !(state.phase === "idle" && state.appMode === "search")));
```

- Conversa mantém acesso incondicional, como antes (o site de conversa não
  checava `hasAnyProvider`, e continua não checando).
- A home continua esperando um provider e continua fora de modo busca.
- Página de projeto continua **sem** seletor, porque nenhum dos dois gates
  antigos cobria essa posição.
- `isWelcomeFocus` já exige fase `idle` ou `classifying`, então o termo
  `!isSearch` do gate antigo era redundante e não foi replicado.

Nada de backend, provider, disponibilidade de modelo ou permissão mudou.
`MultiModelSelector.tsx` **não foi editado**: `data-testid="model-selector"`,
`MAX_MODELS` e o popover seguem idênticos, e `chatActions.ts` continua achando o
seletor por testid.

Consequência aceita na home: sem o irmão à direita, `WelcomeMessage` (que é
`w-full` com conteúdo `items-center`) passa a ficar de fato centralizado na coluna
de leitura, em vez de levemente à esquerda. O `Section` que o envolve não foi
tocado — `justifyContent="between"` com um único filho `w-full` é visualmente
idêntico — porque a composição da home é de VIS-003.

---

## 9. `id` duplicado do botão de envio

`chatControls` é renderizado sempre e apenas **colapsado** em modo busca
(`h-0 overflow-hidden` + `inert`). A linha de busca renderizava um segundo botão
com o mesmo `id`, então em modo busca havia dois nós com
`id="onyx-chat-input-send-button"` no DOM ao mesmo tempo.

Quem é o dono legítimo: o botão de send/stop de `chatControls`. Ele está sempre
montado e é o que a aplicação e os testes endereçam —
`web/tests/e2e/chat/InputBar.ts`, `utils/chatActions.ts`, `utils/chatStream.ts`,
`chat/queued_messages.spec.ts`, `chat/share_chat.spec.ts`,
`chat/file_preview_modal.spec.ts`. Nenhum deles dirige o modo busca por esse `id`.

Resolução:

| Controle | `id` |
|---|---|
| send/stop do composer | `onyx-chat-input-send-button` (**mantido**) |
| busca inline (modo busca) | `onyx-chat-input-search-button` (**novo, distinto**) |

Nenhum `id` estável foi renomeado. `onyx-chat-input` e
`onyx-chat-input-textbox` seguem intactos, incluindo o acoplamento por string em
`AppChrome.tsx`, que refoca o editável por `getElementById`.

Testes provando unicidade: contagem de ocorrências do literal no fonte, ausência
de qualquer `id` repetido em `AppInputBar.tsx`, e verificação no navegador de que
o DOM renderizado não tem `id` duplicado.

---

## 10. Send / stop

Semântica preservada por inteiro: a cadeia de quatro ícones
(`SvgSimpleLoader` / `SvgArrowUp` / `SvgStop`), o enfileiramento quando
`chatState !== "input"`, `stopGenerating()`, `stopTTS({ manual: true })`,
`submitMessage`, e as condições de `disabled` (sem mensagem, upload em curso,
indexação em curso, classificando). Nada de rede ou cancelamento mudou.

O que foi acrescentado é acessibilidade, que a fatia exige e que não existia: o
botão era **ícone sem nome acessível**. Agora o nome acompanha a ação, espelhando
a mesma cadeia que escolhe o ícone:

| Estado | Nome acessível |
|---|---|
| enviar | `appInputBar.sendButton.ariaLabel` |
| enfileirar | `appInputBar.sendButton.queueAriaLabel` |
| parar | `appInputBar.stopButton.ariaLabel` |

Os dois botões só-ícone da linha de busca também ganharam nome:
`appInputBar.clearButton.ariaLabel` e `appInputBar.searchButton.ariaLabel`.

---

## 11. Composer desabilitado

`SharedAppInputBar` é um composer falso na página pública de conversa
compartilhada. O overlay `absolute inset-0 rounded-16 backdrop-blur-xs
bg-background-neutral-00/50` **saiu**.

Ele existia para empurrar o composer falso para trás do CTA, mas fazia isso
obscurecendo conteúdo decorativamente, enquanto a superfície embaixo continuava
lendo como habilitada. No lugar, o composer falso é envolvido em `Disabled`, o
primitivo de desabilitado do próprio repositório — o mesmo que `AppInputBar` já
usa. Ele aplica `cursor-not-allowed`, `select-none`, opacidade de desabilitado e,
o que importa mais, **`aria-disabled`**. O estado passou a ser declarado em vez de
sugerido por vidro, o conteúdo continua legível, e o CTA continua lendo como
primeiro plano sem precisar de blur.

`AppInputBar` mantém o `Disabled disabled={disabled} allowClick` que já tinha, e
com ele a razão que o produto já dava: `allowClick` existe para que o tooltip de
"aguardando processamento de arquivo" continue alcançável com o controle
desabilitado. Nenhuma explicação de negócio nova foi inventada.

---

## 12. Apresentação do contentEditable

Mudanças de apresentação, nenhuma de comportamento:

- `p-[2px]` virou `p-0.5` (2px idênticos, um valor arbitrário a menos). A regra
  de placeholder usa `padding: inherit`, então o alinhamento não mudou.
- `min-h-[44px]` virou `min-h-11` e `min-h-[40px]` virou `min-h-10` no gêmeo
  Craft. Mesmos pixels, sem valor arbitrário.
- Relação com a barra: a barra agora tem `gap-1` e prioridade explícita.

**Nenhum interno comportamental do editor mudou**, e portanto não houve nada a
reportar sob a regra de "PARAR e documentar". Preservados: `useContentEditable`,
autosize 44↔200px, min/max de altura, undo/redo, IME
(`onCompositionStart`/`onCompositionEnd`), tiles de colagem, achatamento de
copy/cut, `firstStrongTextDir` para RTL, o modelo de teclado e o modelo de
rascunho.

---

## 13. Placeholder

Intacto e deliberadamente não tocado além do necessário. Continua sendo
`data-placeholder` + `data-empty` com `::before` lendo
`attr(data-placeholder)`, e continua derivando de `activePlaceholder`, que cascateia
fila → gravando → falando → busca → padrão.

Esse é exatamente o contrato de que VIS-003 precisa para trocar a copy da home
depois: o mesmo composer serve home vazia e conversa, e a copy entra por prop de
estado, não por markup. Há teste fixando que o mecanismo continua sendo o atributo.

Nenhuma copy de home/nova conversa de VIS-003 foi implementada.

---

## 14. Rascunhos

`useDraft` não foi tocado. Preservados: a chave `onyx:draft:chat:<id>` via
`draftKey`, o debounce, o seeding único por sessão com `draftSeededRef`, o
`skipNextDraftSaveRef` que impede a gravação de sobrescrever o que acabou de ser
semeado, a limpeza ao trocar de sessão, e o `clearChatDraft()` imediato no
enfileiramento. Há teste fixando a presença desses pontos.

O contrato "digitar → navegar → voltar" é coberto pelas specs Playwright de
composer existentes, que não foram alteradas.

---

## 15. Fila

Nada mudou: ordenação, máquina de estados, `MAX_QUEUED_MESSAGES`, o efeito de
auto-envio com o gate `latestMessageRenderComplete`, a navegação por ArrowUp via
`handleInputNavKeys` e `useQueuedMessageNavigation`, o descarte, e o
`QueuedMessageBar` acima do composer. A geometria nova não exigiu adaptação de
apresentação da fila.

---

## 16. Comandos de `/`

O popover de atalhos de prompt não foi redesenhado. `handleContentEditableInput`
continua abrindo por `/`, `handleKeyDownForPromptShortcuts` continua tratando
Enter, Tab, Shift+Tab, ArrowUp e ArrowDown, e `Popover.Anchor` continua ancorado
no wrapper do editável. A elevação do popover continua sendo a de VIS-001.

---

## 17. Anexos

VIS-005 **não** foi implementada. Preservados: a máquina de estados de upload,
`FileCard`, a colagem de arquivos por `getPastedFilesIfNoText`, o dropzone com
`noClick`/`noPaste`, os ids temporários e o polling.

A faixa de anexos continua medindo a altura do conteúdo em JS com
`PADDING = 8` espelhando `p-1`, e continua dentro da caixa do composer — que
agora tem borda, o que não afeta a medição porque `box-sizing` é `border-box`.
`dropzonePaste.test.tsx` passa sem alteração.

Chips e cartões de anexo não foram redesenhados.

---

## 18. Voz

VIS-008 **não** foi implementada. Nada de conversa falada foi removido, nada de
ditado do navegador foi adicionado, e TTS, STT, contratos de microfone e
`Waveform` estão intactos. `MicrophoneButton` e os dois overlays de `Waveform`
continuam montados nas mesmas posições absolutas.

O único cuidado tomado foi de alcançabilidade: o microfone está no grupo direito
com `shrink-0`, então continua visível a 375px.

---

## 19. Mensagens

VIS-006 **não** foi implementada. Bolha do usuário, mensagem do assistente,
raciocínio, renderizadores de ferramenta, Markdown, citações e apresentação de
atividade de streaming não foram tocados.

---

## 20. Home e casca

VIS-003 **não** foi implementada: `WelcomeMessage` não foi substituído, não há
ações rápidas TON, não há "O que você deseja analisar?", não há métricas de
dashboard e a composição de conversa vazia não foi redesenhada. A única mudança
na linha da saudação é a saída do seletor de modelo, que é o item 8 desta fatia.

VIS-002 **não** foi implementada. `AppChrome` mudou **só** no padding do footer,
que era compensação direta da sombra do composer. Navegação FE-004, seções da
sidebar, nav ativa, layout de histórico e layout de projeto intactos. Nenhum
componente de casca foi extraído ou reestruturado.

---

## 21. Tokens

Nenhum token novo. Nenhum sistema de token novo. Consumidos, todos de VIS-001:
`background-neutral-00`, `border-01`, `border-02`, `border-05`,
`background-tint-04`, `radius-12`, `weight-line-border`, `weight-line-focus`,
`duration-instant`, `duration-fast`, `easing-standard`, e indiretamente
`theme-primary-04`, `action-selection-01` e `action-selection-05` pela matriz de
`Interactive`.

Nenhum primitivo semântico faltou. A paleta escura neutra não foi reaberta.

Sem cor Tailwind bruta, sem hex novo, sem modificador `dark:`, e os dois valores
arbitrários que estavam no caminho (`p-[2px]`, `min-h-[44px]`, `min-h-[40px]`)
foram trocados por utilitários equivalentes. Há teste fixando ausência de hex e de
`dark:` nos quatro arquivos de composer.

---

## 22. i18n

Cinco chaves novas, em `chat.input.appInputBar`, todas nomes acessíveis:

```text
clearButton.ariaLabel
searchButton.ariaLabel
sendButton.ariaLabel
sendButton.queueAriaLabel
stopButton.ariaLabel
```

Adicionadas aos **nove** catálogos (`en`, `pt`, `es`, `fr`, `de`, `ar`, `ja`,
`ko`, `zh`), reaproveitando por locale o vocabulário que `baseInputBar` já usava
para "parar a geração" e "colocar na fila", para que os dois composers falem
igual. Nenhuma tem argumento ICU. Paridade de chaves e forma ICU verificadas por
`src/i18n/__tests__/catalog.test.ts` e por `types:check`.

Nenhuma string de UI foi codificada. O único literal do diretório continua sendo o
nome de modelo de placeholder em `SharedAppInputBar`, que já tinha `oxlint-disable`
e pertence à limpeza de marca upstream de VIS-007/VIS-010.

---

## 23. Testes

### 23.1 Mapeamento anterior

Antes de mexer: **nenhum** teste Jest renderizava `AppInputBar`, `BaseInputBar`,
`SharedAppInputBar` ou `MultiModelSelector`, e não havia teste unitário de
rascunho nem de modo pesquisa. O composer precisa da árvore inteira de providers
(session store, query controller, LLM manager, voz, projetos, agentes), então
renderizá-lo em jsdom não é viável.

Cobertura existente: `__tests__/dropzonePaste.test.tsx` (colagem vs dropzone, mais
asserção no fonte dos call sites), `__tests__/inputBarKeys.test.ts` (precedência
de `handleInputNavKeys`), e as specs Playwright em `web/tests/e2e/chat`
(`input_bar_behaviors`, `queued_messages`, `input_focus_retention`,
`share_chat`, `file_preview_modal`, `welcome_page`, `tools_popover`,
`llm_ordering`, `llm_runtime_selection`).

### 23.2 O que foi acrescentado

`web/src/sections/input/__tests__/composerVisualContract.test.ts` — 46 testes.
Segue o padrão que o próprio repositório usa para superfícies que não renderizam
em jsdom: asserção sobre a regra CSS compilada e sobre os invariantes de fonte.
Nenhum outro teste foi alterado.

| # | Exigência | Como é provado |
|---:|---|---|
| 1 | aresta por borda | `.ton-composer` tem `border: calc(var(--weight-line-border)…) solid var(--border-01)` sobre `background-neutral-00` |
| 2 | `shadow-box-01` não é mais a aresta | ausente nos três composers; `shadow-box-*` ausente do CSS |
| 3 | raio aprovado | `border-radius: var(--radius-12)`; medido 12px no navegador |
| 4 | `focus-within` cria foco visível | `border-05` + anel inset `background-tint-04` |
| 5 | foco não muda dimensão | a regra de foco declara **exatamente** `border-color` e `box-shadow`, nada mais; caixas idênticas medidas no navegador |
| 6 | espaçadores removidos | `h-[14px]` ausente de `AppPage.tsx` |
| 7 | compensação do footer removida | ternário `isChat() ? "pb-2"` ausente; `py-2` presente; nenhum dos três arquivos menciona o hack |
| 8 | envio inalterado | `submitMessage`, `stopGenerating()`, `enqueueCurrentMessage`, `MAX_QUEUED_MESSAGES` presentes |
| 9 | parada inalterada | `stopGenerating()` e `stopTTS({ manual: true })` presentes |
| 10 | Enter inalterado | `event.key === "Enter"` presente |
| 11 | Shift+Enter inalterado | `!event.shiftKey` e `!event.nativeEvent.isComposing` presentes |
| 12 | `/` inalterado | `handleKeyDownForPromptShortcuts` presente |
| 13 | rascunho inalterado | `useDraft` e `clearChatDraft` presentes |
| 14 | fila inalterada | `handleInputNavKeys`, `enqueueCurrentMessage`, `MAX_QUEUED_MESSAGES` presentes |
| 15 | colagem/dropzone verdes | `dropzonePaste.test.tsx` roda sem alteração |
| 16 | seletor de modelo funcional | um único call site; `data-testid` e `MAX_MODELS` intactos |
| 17 | Deep Research funcional | `toggleDeepResearch` e `showDeepResearch` presentes |
| 18 | ativo distinto sem glow | par `select-heavy`/`select-light`; ausência de `shadow-box`, `blur`, `glow`, `radial`, `sparkle` |
| 19 | `id` duplicado eliminado | literal aparece 1×; nenhum `id` repetido no arquivo; DOM sem duplicata no navegador |
| 20 | desabilitado sem blur | `backdrop-blur` e `bg-…/50` ausentes; `Disabled` presente |
| 21 | 375px mantém o essencial | grupo secundário rolável; `shrink-0` no grupo primário; nenhum `*:hidden`; medido no navegador |
| 22 | sem transbordo horizontal | `scrollWidth == clientWidth` na página e no composer, 375/768/1280, dois temas |

Extras fixados: ausência de hex e de `dark:` nos quatro arquivos; nenhuma
biblioteca de editor em `package.json`; preservação de `useContentEditable`, IME,
copy/cut, RTL, `PADDING = 8`, `FileCard`, `MicrophoneButton`, `Waveform`; e o
mecanismo de placeholder por atributo, que VIS-003 vai precisar.

### 23.3 Resultado

| Gate | Resultado |
|---|---|
| `bun run types:check` | **PASSA** — sem erros; cobertura de tipos 98.81% (233388/236200) em 1245 arquivos |
| `bun run lint` (oxlint) | **PASSA** — saída 0; só avisos `anti-slop` pré-existentes, nenhum em linha desta fatia |
| `bun run build` | **PASSA** — compilado em 55s; `.ton-composer*` presente no bundle CSS de produção |
| `bun run jest` (`--ci --maxWorkers=2`) | **PASSA** — 154/154 suites, 1428/1428 testes |
| suites TON | **PASSAM** — `ton-navigation`, `ton-product-surface`, `ton-privacy`, `ton-web-only.contract`, `ton-foundations`, `ton-theme` |
| composer/input + i18n + Craft | **PASSAM** — 15 suites, 180 testes |
| formatação dos arquivos alterados | **limpa** — `oxfmt` não muda nenhum dos 6 arquivos (a menos de EOL) |

---

## 24. Validação de runtime

**Validação visual: FEITA, em runtime isolado.** Chromium via `@playwright/test`
(já instalado; nenhuma dependência adicionada), carregando o **CSS que o build de
produção emitiu** numa página estática cuja árvore espelha a estrutura real do
composer. Sem servidor, sem container, sem banco. Mediu, nos dois temas e em
375/768/1280: borda em repouso, hover com ponteiro real, foco por `focus()`,
hover-sobre-focado, `box-shadow`, raio, superfície, caixas antes e depois do foco,
transbordo de página e de composer, rolagem do grupo secundário, alcançabilidade
de send, largura do editor, casamento da regra de placeholder e duplicidade de
`id`. Os números estão em §5.1 e §6.3. Isso valida a cascata compilada e a
geometria; **não** valida o comportamento do app React, que é das specs Playwright.

**PLAYWRIGHT DEFERIDO — CONFLITO DE RUNTIME COMPARTILHADO.**

Motivo exato: há um stack Docker compartilhado no ar há 10 horas
(`onyx-nginx-1`, `onyx-web_server-1`, `onyx-api_server-1`,
`onyx-code-interpreter-1`, `onyx-relational_db-1`), e `localhost:3000` responde
200 servido por `onyx-web_server-1`, que é o build do worktree original — o
**baseline**, sem as mudanças de VIS-004. Validar contra ele mediria o composer
antigo. Servir esta branch e apontá-la ao mesmo backend colocaria as suítes e2e
deste repositório contra um banco Postgres compartilhado e persistente, e o
`global setup` do Playwright **registra usuários de teste** — exatamente o que
está proibido, junto com migrar o banco compartilhado e mexer em containers de
outros projetos. Não havia caminho para um runtime de aplicação isolado sem
subir um stack paralelo.

Consequência: os comportamentos que precisam do app vivo — Enter, Shift+Enter,
`/`, teclado da fila, send/stop de ponta a ponta, alternância de modo pesquisa,
persistência de rascunho ao navegar — **não foram observados em navegador nesta
fatia**. Estão cobertos por specs existentes e intocadas, e por asserções de
fonte de que o código que elas dirigem continua presente. Nenhuma observação de
navegador foi inventada.

---

## 25. Fronteiras de escopo

| Fatia | Confirmação |
|---|---|
| VIS-002 | nenhum arquivo de sidebar; `AppChrome` só no padding do footer; navegação FE-004 intacta |
| VIS-003 | `WelcomeMessage`, `NRFPage`, `Suggestions`, `OnboardingFlow` intactos; nenhuma copy de home |
| VIS-005 | `FileCard`, `InputChipStrip`, dropzone, polling e ids temporários intactos |
| VIS-006 | mensagens, raciocínio, markdown, citações, streaming intactos |
| VIS-007 a VIS-010 | nada de identidade, voz, movimento ou QA final |
| FE-005 a FE-011 | nada |
| `backend/` | **nenhum arquivo alterado** |
| dependências | **nenhuma adicionada** |
| Plano 004 backend | não iniciado |

Nenhuma condição de PARADA foi atingida. Em particular, a que era o risco central
— "remover a sombra não preserva aresta visível com os papéis de VIS-001" — foi
medida e não se materializou (§5.2).

---

## 26. Desvios registrados

1. **`outline-hidden` fica no editável.** `001-visual-foundations.md` §23 item 2
   sugeria removê-lo. Não foi removido, porque o wrapper do editável é
   `overflow-hidden` para o autosize e recortaria o `outline-offset: 1px` da
   fundação global, produzindo um anel cortado dentro do anel do contêiner. O
   `focus-within` do contêiner entrega o sinal inteiro. Detalhe em §5.
2. **Cromo em CSS, não em utilitários Tailwind.** A ordem de camadas do Tailwind
   v4 impede que `base` sobreponha uma cor de borda vinda de `utilities`.
   Justificativa em §3, com o precedente `.opal-input`.
3. **`h-11` mantido na barra** em vez de `min-h-11`, porque o colapso em modo
   busca anima altura. §6.
4. **Nome de modelo `GPT-4o` mantido** em `SharedAppInputBar`. É marca upstream
   num placeholder decorativo, não estado desabilitado nem seleção real de
   modelo; pertence a VIS-007/VIS-010. §22.
5. **`format:check` falha no baseline** por motivo de ambiente, não de código:
   `core.autocrlf=true` deixa a árvore de trabalho em CRLF e `oxfmt` emite LF.
   Verificado com arquivo não tocado. Os 6 arquivos desta fatia são limpos a menos
   de EOL. §23.3.
6. **`Disabled` de `@opal/core` usado em código de app.** `web/AGENTS.md`
   desencoraja primitivos de `@opal/core` em `src/`. A alternativa era reescrever
   à mão `opacity`/`cursor`/`aria-disabled` no call site, que é pior; e
   `AppInputBar` já importava `Disabled`. §11.

---

## 27. Pré-requisitos que esta fatia libera

**Para VIS-002 (casca e navegação).** A dependência de layout entre composer e
footer acabou: `Footer` não lê mais `useAppPosition`, e o padding é
incondicional. Não há mais espaçador reagindo a `isChat()`/`isSearch` na linha 2
do grid. VIS-002 pode ajustar a casca sem reconciliar compensação de sombra. E o
composer já não usa sombra, então a hierarquia de elevação que VIS-002 vai aplicar
à sidebar e aos popovers não conflita com ele.

**Para VIS-005 (anexos e contexto).** A geometria final do composer está fixada:
`radius-12`, borda de 1px por dentro da caixa, `elevation-0`. A faixa de anexos
continua com a medição de altura em JS intacta, e o raio dos chips pode ser
escolhido concentricamente a 12px. O contrato de foco do contêiner já existe, então
uma sobreposição de arraste de VIS-005 pode se apoiar nele em vez de inventar
estado.

**Para VIS-003 (home).** Contrato de placeholder preservado como atributo de
estado, e o seletor de modelo saiu da linha da saudação, deixando essa linha
livre para VIS-003 recompor.

**Para VIS-008 (voz).** Controles de voz seguem montados e alcançáveis, com
comportamento inalterado.

---

## 28. Conflitos prováveis de integração

| Onde | Por quê |
|---|---|
| `web/src/views/AppPage.tsx` | arquivo central; VIS-003 vai recompor a linha 1 e VIS-002 pode tocar o grid. O bloco do composer e o gate `modelSelectorVisible` são de VIS-004 |
| `web/src/app/css/content-editable.css` | VIS-005 vai mexer nas regras de tile no mesmo arquivo; o bloco `.ton-composer*` está no topo, separado |
| `web/src/layouts/chromes/AppChrome.tsx` | VIS-002 é dona do arquivo; VIS-004 alterou só o `Footer`, e removeu um hook dele |
| `web/src/i18n/messages/*.json` | qualquer fatia que adicione copy toca os nove catálogos; conflito textual, resolução trivial |
| `web/src/sections/input/AppInputBar.tsx` | VIS-005 (anexos) e VIS-008 (voz) vão editar o mesmo arquivo; VIS-004 mexeu no cromo, na barra e nos `id`, não nas regiões de anexo ou de voz |
