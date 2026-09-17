# TON — roadmap de implementação visual (VIS-001 a VIS-010)

Sequenciamento derivado de
[`000-de-onyx-visual-audit.md`](./000-de-onyx-visual-audit.md). A linguagem alvo
está em [`visual-language.md`](./visual-language.md).

**Estado: VIS-001, VIS-004, VIS-002, VIS-005, VIS-006, VIS-003 e VIS-007 DONE. As demais não foram implementadas.**

| Fatia | Estado |
|---|---|
| VIS-001 | **DONE** — [`001-visual-foundations.md`](./001-visual-foundations.md) |
| VIS-004 | **DONE** — [`004-composer.md`](./004-composer.md) |
| VIS-002 | **DONE** — [`002-shell-navigation.md`](./002-shell-navigation.md) |
| VIS-005 | **DONE** — [`005-attachments-context.md`](./005-attachments-context.md) |
| VIS-006 | **DONE** — [`006-messages-streaming-tools.md`](./006-messages-streaming-tools.md) |
| VIS-003 | **DONE** — [`003-home-new-chat.md`](./003-home-new-chat.md) |
| VIS-007 | **DONE** — [`007-specialist-runtime-identity.md`](./007-specialist-runtime-identity.md) |
| VIS-008 … VIS-010 | não iniciadas |

---

## Regras que valem para todas as fatias

1. **A arquitetura de informação de FE-004 está congelada.** Central,
   Especialistas, Projetos, o divider e o histórico em landmark próprio
   continuam. Nenhuma fatia redesenha a navegação do produto.
2. **A sanitização de FE-003 fica intacta.** As quatro constantes de
   `web/src/lib/ton/product-surface.ts` continuam `false`.
3. **Nenhuma fatia altera `backend/`.**
4. **Nenhuma fatia troca biblioteca.** Sem Jotai, sem Vercel AI SDK, sem trocar
   router, editor, componentes ou framework.
5. **Nível 5 é proibido.** Nível 4 exige justificativa registrada.
6. `web/AGENTS.md` vale sempre: sem `dark:`, sem cor embutida do Tailwind, sem
   `<button>`/`<input>` cru, ícones só de `@opal/icons`, texto por `next-intl`,
   imports absolutos, `cn` do `@opal/utils`.
7. Toda copy nova entra em `en.json` **e** nos outros oito catálogos, ou
   `types:check` falha por paridade.
8. Toda fatia roda: `bun run types:check`, `bun run lint`, `bun run build`, os
   testes Jest relacionados, e Playwright quando houver ambiente.
9. Toda fatia que toca token atualiza `web/lib/opal/src/ton-theme.test.ts` no
   **mesmo commit**, e roda `bun run verify:tokens`.
10. Toda fatia é executada em worktree isolado, sem merge, push ou rebase.

### Ordem recomendada

```text
VIS-001 → VIS-004 → VIS-002 → VIS-005 → VIS-006 → VIS-003 → VIS-007 → VIS-008 → VIS-009 → VIS-010
```

As seis primeiras (VIS-001, VIS-004, VIS-002, VIS-005, VIS-006 e VIS-003) estão feitas. A próxima é VIS-007.

VIS-004 vem antes de VIS-002 porque trocar a aresta do composer de sombra para
borda **elimina o hack de 14px espalhado por três arquivos** e resolve a
dependência de layout do footer. VIS-003 vem depois de VIS-005 e VIS-006 porque
a transição da home precisa da geometria final de anexo e de mensagem para não
saltar.

### Gêmeos que precisam acompanhar

| Ao mudar | Também tocar |
|---|---|
| composer | `AppInputBar.tsx`, `BaseInputBar.tsx`, `SharedAppInputBar.tsx` |
| home | `AppPage.tsx`, `NRFPage.tsx`, (`BuildWelcome.tsx` se reativado) |
| ícones de marca | `icons/onyx-octagon.tsx`, `logos/onyx-logo.tsx`, **e** `loader/components.tsx:96-115` |
| `WelcomeMessage` | `/app` e `/nrf` |
| octógono / avatar | espelho `mobile/` (registrar, trilha separada) |

---

## VIS-001 — Fundações e linguagem de superfície — **DONE**

**Nível máximo: 2.** Só tokens, CSS de biblioteca e a matriz de `Interactive`.

Resultado, valores finais, contraste medido, decisões e trabalho deferido:
[`001-visual-foundations.md`](./001-visual-foundations.md).

Resumo do que entrou: escada de superfície neutra nos dois temas (canvas escuro
`#333333`, campo `#0f0f0f`, canvas claro `#fafafa`); bordas genéricas neutras;
sete papéis de borda nomeados, com `selected` em `theme-primary-04`; largura de
borda tokenizada; uma única declaração global de cor de borda, agora tema-aware
até nos pseudo-elementos; aliases de raio do Tailwind repontados para a escala TON
sem mover geometria; elevação reduzida a três níveis com sombra preta no escuro;
`selected:hover` corrigido nas cinco variantes e célula `PRESSED` adicionada, com
anel de seleção de 1px que engrossa para 2px ao pressionar; foco global
`focus-visible`; camada de token de movimento e reset global de reduced-motion com
escape hatch; escala de blur monotônica; largura de leitura semântica; resíduos
`onyx-ink-*`, `onyx-chrome-*`, `#888` e `--color-gray-200` removidos.

Duas decisões que **não** seguiram a proposta original, com a medição no
documento: espaçamento **não** foi ligado ao preset (as chaves de token são
denominadas em px e os utilitários em passos — ligar dividiria todo `p-*` por
quatro), e o papel `selected` usa `theme-primary-04` em vez de
`action-selection-04/05`, que não alcançam 3:1 sobre a sidebar escura.

### Pré-requisitos
VIS-000 aprovado. Decisão de produto sobre o **escuro neutro** (§8.2 da
auditoria), porque reabre contraste aprovado em FE-002.1. — **atendidos.**

### Escopo permitido

Arquivos:

- `web/lib/shared/tokens/primitives.json`
- `web/lib/shared/tokens/semantic-light.json`
- `web/lib/shared/tokens/semantic-dark.json`
- `web/lib/shared/tokens/size.json`
- `web/lib/shared/tokens/shadow.json`
- `web/lib/shared/tokens/typography-presets.json`
- `web/lib/opal/tailwind-preset.cjs`
- `web/lib/opal/src/core/interactive/stateful/styles.css`
- `web/lib/opal/src/ton-theme.test.ts`
- `web/src/app/globals.css`
- `web/tailwind-themes/tailwind.config.js`
- `web/lib/opal/src/icons/simple-loader.tsx` (só `motion-safe:`)
- `web/src/components/icons/icons.tsx` (só `#33C19E` → token)

Trabalho:

1. **Papéis de superfície nomeados** e documentados; separar neutro verdadeiro de
   verde de estado (desfazer parcialmente o alias `tint-*` de
   `primitives.json:1010-1077`).
2. **Escuro neutro** conforme §2.4 da linguagem visual, mantendo as quatro
   restrições herdadas de FE-002.1.
3. **Papéis de borda nomeados**: `subtle`, `default`, `interactive`, `selected`,
   `focus`, `error`, `attention`. Simetria claro/escuro.
4. **Uma única declaração de cor de borda padrão** em `globals.css` (hoje são
   duas, e os pseudo-elementos ficam com `#e5e7eb`).
5. **Hierarquia de raio** atribuída por classe; converter os 14 usos de
   `rounded-sm/md/lg/xl/2xl/3xl` em `web/src/**/*.tsx`.
6. **Redução de elevação**: três níveis, raio menor, papel só de elevação real.
7. **Primitivos globais de estado**: corrigir `selected:hover` (a seleção não
   pode inverter), adicionar célula `:active` para `PRESSED`, e estender a união
   de estado se necessário.
8. **Ligar `spacing` e `borderWidth`** ao preset, ou remover os tokens órfãos.
   Decisão registrada.
9. **Criar tokens de movimento** (`duration-*`, `easing-*`) e o **reset global de
   `prefers-reduced-motion`**.
10. **Corrigir a escala de `backdrop-blur`** (hoje `-02` e `-03` são iguais e
    `-01` é a maior).
11. **Tokenizar a largura de leitura**; consolidar as cinco constantes
    concorrentes em uma.
12. **Remover resíduos**: `onyx-ink-*`, `onyx-chrome-*` e suas classes;
    `#33C19E`; hex cru de `shimmer-*`; `#888` de scrollbar.
13. `motion-safe:` em `SvgSimpleLoader`.
14. Decidir KH Teka: adotar ou remover.
15. Atualizar `ton-theme.test.ts` com os papéis nomeados e as novas razões.

### Escopo proibido

Qualquer mudança de composição de página. O composer. Mensagens. Anexos.
Identidade de especialista. O loader de marca. A home. Voz. Qualquer arquivo em
`web/src/views/`, `web/src/sections/` (exceto o que a conversão de raio exigir) e
`web/src/app/app/`.

### Resultado visual esperado

A aplicação fica visivelmente menos arredondada, com menos sombra e mais borda.
O escuro fica neutro. Seleção e foco ficam explícitos e consistentes. Nenhuma
página muda de estrutura.

### Risco

**Alto por alcance.** É a fatia que toca todas as telas de uma vez. Três riscos
concretos: (1) ligar a escala de espaçamento muda todo `p-`/`gap-` do app;
(2) mudar `Interactive` afeta as sete superfícies de seleção simultaneamente;
(3) o escuro neutro reabre contraste já aprovado.

Mitigação: sequenciar em commits separados por sistema (cor → borda → raio →
elevação → estado → movimento → espaçamento), cada um com `TOK` e `VIS`.

### Validação

`bun run types:check` · `bun run lint` · `bun run build` ·
`ton-theme.test.ts` estendido · `bun run verify:tokens` · contraste medido em
todos os pares novos, claro e escuro · foco visível em toda superfície ·
reduced-motion verificado · Playwright em 375/768/1280 nos dois temas · grep
confirmando zero `dark:`, zero cor embutida e zero raio não tokenizado nos
arquivos alterados.

---

## VIS-002 — Casca e navegação (visual de FE-004) — **DONE**

**Nível máximo: 3.** Resultado, decisões e evidência de estilo computado em
[`002-shell-navigation.md`](./002-shell-navigation.md).

Entregue: aresta lógica de 1px na coluna sobre o degrau de superfície; linha de
navegação em `radius-04` com **marcador na aresta de início** no lugar do anel de
perímetro (as variantes `select-*` mantiveram o anel, que é de onde VIS-004 tira o
Deep Research); rótulo de seção de `text-02` para `text-03` e ritmo `pt-3` para
`pt-5`; faixa da marca na altura do header do chrome com o recolher centrado;
header do chrome centrado verticalmente e sem os dois `FrostedDiv`;
`AppChrome` de 742 para 226 linhas com `AppHeader.tsx` extraído literalmente.
Corrigidos A3 (menu de projeto no toque, via `Hoverable`), C1/A4
(`Open Sidebar`/`Close Sidebar` pelo contrato `OpalStrings` nos nove catálogos) e
C3 (`aria-label="share-chat-button"`). Skeletons determinísticos e carregamento por
seção. A IA de FE-004 não mudou. Playwright de aplicação **deferido** por conflito
de runtime compartilhado; validação visual feita em Chromium isolado sobre o CSS do
build. Detalhes em `002-shell-navigation.md` §13 e §15.

### Pré-requisitos
VIS-001.

### Escopo permitido

- `web/lib/opal/src/layouts/sidebar/styles.css`
- `web/lib/opal/src/layouts/sidebar/components.tsx` (só os rótulos de dobra)
- `web/lib/opal/src/components/buttons/sidebar-tab/components.tsx`
- `web/lib/opal/src/components/buttons/sidebar-tab/styles.css`
- `web/lib/opal/src/strings.tsx` + `web/src/i18n/OpalStringsBridge.tsx`
- `web/src/sections/sidebar/AppSidebar.tsx`
- `web/src/sections/sidebar/ChatButton.tsx`
- `web/src/sections/sidebar/AccountPopover.tsx`
- `web/src/lib/projects/components/ProjectFolderButton.tsx`
- `web/src/lib/projects/components/FoldedProjectsPopover.tsx`
- `web/src/layouts/chromes/AppChrome.tsx`
- `web/src/lib/app/components.tsx` (ponto de troca do logo)
- catálogos i18n

Trabalho:

1. **Aresta da sidebar**: borda de 1px no lugar do degrau tonal isolado.
2. **Rótulo de seção legível**: peso e cor conforme §8.5 da linguagem visual.
3. **Estado selecionado TON** na linha de navegação e na conversa selecionada.
4. **`"Open Sidebar"`/`"Close Sidebar"` via `OpalStrings`** — chave tipada,
   default em inglês, bridge, e as nove traduções.
5. **`ProjectFolderButton` usa `Hoverable`** — corrige o menu inacessível no
   toque.
6. **Header com título de contexto** e só ações genuinamente relevantes.
   Extrair `Header` de `AppChrome.tsx` (754 linhas, três componentes).
7. **Skeleton por seção** no corpo da sidebar (hoje o corpo inteiro é `null`
   enquanto qualquer das cinco fontes carrega).
8. `shuffleWidths` determinístico.
9. Decidir a fronteira produto/histórico: `Divider`, espaçamento ou hierarquia
   tipográfica. FE-004 pediu explicitamente esta decisão.
10. i18n dos toasts codificados e do `aria-label="share-chat-button"`.
11. Tokenizar ou remover a vinheta e a máscara de blur do canvas.
12. Unificar as duas cópias de `useScreenSize`.

### Escopo proibido

**Não mudar a arquitetura de informação de FE-004.** Não adicionar, remover nem
reordenar destino de produto. Não tocar `useAppPosition`. Não mexer em fold,
dnd, scroll infinito, stores nem persistência. Não usar a sidebar do CRM
ClearEyed/Twenty como referência estrutural. Não trocar `data-testid` existente.

### Resultado visual esperado

Casca mais sóbria e legível. Hierarquia clara entre capacidades de produto e
histórico. Seleção inequívoca sem pílula preenchida. Header contextual em vez de
barra SaaS sobrecarregada. Rótulos em PT-BR, incluindo o controle de dobra.

### Risco

**Alto.** `AppSidebar.tsx` é o arquivo que FE-004 acabou de estabilizar, e
`ton-navigation.test.tsx` tem 28 testes que afirmam a IA. Extrair `Header` de
`AppChrome` é refatoração num arquivo de 754 linhas com rede, `localStorage` e
tier misturados.

### Validação

`ton-navigation.test.tsx` **sem alteração de asserção** · `ton-product-surface.test.tsx` ·
`web/tests/e2e/ton/navigation.spec.ts` · as sete specs que dependem de
`"Open Sidebar"`/`"Close Sidebar"` atualizadas para as chaves novas · Playwright
375/768/1280 nos dois temas · teclado: Cmd/Ctrl+E, tab order, focus-visible ·
toque: menu de projeto alcançável.

---

## VIS-003 — Home / nova conversa — **DONE**

Implementação, decisões e gates em [`003-home-new-chat.md`](./003-home-new-chat.md).
Revisão visual aprovada em runtime nos temas claro e escuro. Decisão final:
seletor de modelos integrado à toolbar inferior direita do composer (variante limpa
`select-light` com truncamento responsivo e tooltip); botão "+" preservado com
semântica de comparação multi-modelo (sem relação com anexos); entrada da Central
determinística alinhada à esquerda sem dashboard ou métricas inventadas. Todos os
testes e gates aprovados.

**Nível máximo: 3.**

### Pré-requisitos
VIS-001 e VIS-004 (a transição depende da geometria final do composer).

### Escopo permitido

- `web/src/views/AppPage.tsx` (linhas 1 e 3 do grid)
- `web/src/app/app/components/WelcomeMessage.tsx`
- `web/src/app/app/components/AgentDescription.tsx`
- `web/src/sections/Suggestions.tsx`
- `web/src/sections/onboarding/OnboardingFlow.tsx` (só visual e i18n)
- `web/src/app/nrf/NRFPage.tsx` (gêmeo)
- catálogos i18n

Trabalho:

1. **Entrada de domínio determinística**: substituir a saudação sorteada por
   `Math.random()` por uma entrada estável, na direção de "O que você deseja
   analisar?". A copy final é decisão de produto em PT-BR.
2. **Composer como protagonista**; remover o `FrostedDiv` decorativo.
3. **Ações rápidas contidas e relevantes ao domínio**, conceitualmente na linha
   de: analisar resultado, revisar contrato, investigar divergência, analisar
   arquivo. As strings exatas não são imutáveis.
4. **Transição sem salto**: preservar o mecanismo de `gridTemplateRows`
   (`1fr auto 1fr` → `1fr auto 0fr`) e o `Fade` de 150ms. O composer **nunca
   remonta** — isso é a base e deve continuar.
5. i18n do `aria-label="onboarding-flow"`; reduzir os 500ms do onboarding.
6. `Text` novo em `WelcomeMessage` e `AgentDescription`.
7. Alinhar `NRFPage` ao comportamento do `/app`.

### Escopo proibido

**Não construir dashboard.** Não usar grade de cartões sem propósito.
**Não inventar métrica.** Se uma consciência operacional entrar, ela usa
somente: sessões de conversa, projetos, arquivos recentes, especialistas e
notificações. Não existe `findings`, `occurrences`, `analysisRun` nem `reports`
em `web/src/lib` — qualquer número de achados, ocorrências, cobertura, risco ou
SLA é **fabricado e reprova a fatia**.

Não mudar a linha 2 do grid (é de VIS-004). Não tocar `useAppPosition`.

### Resultado visual esperado

Home chat-first, silenciosa, com entrada de domínio clara e algumas ações
relevantes. Transição contínua para a conversa. Nenhuma métrica inventada.

### Risco

**Médio-alto.** `AppPage.tsx` tem 1095 linhas e governa home e conversa. O grid
já teve bug de overflow horizontal com cartões largos do onboarding — está
documentado em `AppPage.tsx:696-700` e é aviso direto para qualquer faixa nova.
`WelcomeMessage` é compartilhado com `/nrf`.

### Validação

RTL de `WelcomeMessage` determinístico (sem `Math.random()` no caminho de
render) · RTL das ações rápidas com dado real e com dado vazio · Playwright da
transição home → conversa sem salto de layout, 375/768/1280 · revisão de produto
confirmando que nenhuma métrica é inventada · `/nrf` verificado.

---

## VIS-004 — Composer — **DONE**

**Nível máximo: 3.** Resultado, decisões e evidência de estilo computado em
[`004-composer.md`](./004-composer.md).

Entregue: aresta por borda (`border-01` → `border-02` no hover → `border-05` mais
anel `background-tint-04` no foco), `radius-12`, `elevation-0`, `focus-within` no
contêiner, barra com prioridade PRIMARY/SECONDARY/CONTEXTUAL e overflow por
rolagem, Deep Research institucional sem glow, posição única do seletor de modelo,
`id` de envio único, e estado desabilitado sem vidro. Os três hacks de sombra
saíram. Playwright de aplicação ficou **deferido** por conflito de runtime
compartilhado; a validação visual foi feita em Chromium isolado sobre o CSS do
build. Detalhes em `004-composer.md` §24.

### Pré-requisitos
VIS-001.

### Escopo permitido

- `web/src/sections/input/AppInputBar.tsx` (apresentação e layout)
- `web/src/sections/input/BaseInputBar.tsx` (gêmeo Craft)
- `web/src/sections/input/SharedAppInputBar.tsx` (gêmeo compartilhado)
- `web/src/app/css/content-editable.css`
- `web/src/views/AppPage.tsx` (só os espaçadores de sombra e a posição do seletor de modelo)
- `web/src/layouts/chromes/AppChrome.tsx` (só o padding do footer)
- `web/src/sections/model-selector/MultiModelSelector.tsx`

Trabalho:

1. **Aresta por borda, não por sombra.** `border-01`/`border-02` de 1px,
   `radius-12`, sem `shadow-box-01`.
2. **Remover o contorno de 14px**: os dois espaçadores animados em
   `AppPage.tsx:986-991` e `:1041-1046`, e a compensação `pb-2`/`py-2` em
   `AppChrome.tsx:647`. Apagar as três notas `@raunakab` que os explicam.
3. **Tratamento de foco.** É o achado de a11y mais grave: hoje não existe. Usar
   borda de foco + anel interno, o padrão que `ton-theme.test.ts:211-233` já
   prescreve (`border-05` + `background-tint-04`).
4. **Barra de ferramentas integrada** com prioridade de overflow em telas
   estreitas. Hoje é `h-11` fixo, sem wrap e sem scroll.
5. **Deep Research**: inativo neutro e silencioso; ativo com contorno
   institucional e mudança sutil de superfície. Sem neon, sem glow, sem "magia
   de IA".
6. **Corrigir o `id` duplicado** de `onyx-chat-input-send-button` (existe em
   `:783` e `:1045`, ambos no DOM em modo busca).
7. Posição única e contida do seletor de modelo (hoje aparece em dois lugares
   com aparências diferentes).
8. Estado desabilitado sóbrio em `SharedAppInputBar`; remover o overlay
   `backdrop-blur-xs`.

### Escopo proibido

**Não substituir o editor.** `useContentEditable.ts` (~870 linhas) implementa
autosize 44↔200px, pilha própria de undo/redo com coalescing, IME completo,
tiles de colagem, RTL por `firstStrongTextDir`, e achatamento de copy/cut.
Trocar por Lexical, TipTap, ProseMirror ou Slate seria nível 5 injustificado.

Não mudar: `useDraft`, o tratamento de Enter/Shift+Enter, a navegação da fila, o
popover de `/`, os tiles, a mecânica de upload, nem os ids `onyx-chat-input` e
`onyx-chat-input-textbox` (acoplados por string em `AppChrome.tsx:702`/`:716` e
em `web/tests/e2e/chat/InputBar.ts`).

### Resultado visual esperado

Composer largo mas contido: minimal, definido por borda, raio menor, barra
integrada, foco claro, controles secundários silenciosos. Três hacks de sombra
desaparecem.

### Risco

**Médio.** O risco real é remover a sombra e a borda não estabelecer aresta
suficiente, deixando o composer indistinto do canvas. Segundo risco: os
espaçadores existem por um motivo real, e removê-los sem remover a sombra
reintroduz o clipping.

### Validação

`A11Y` **obrigatório**: foco visível por teclado, nos dois temas, medido ·
Playwright de teclado (Enter, Shift+Enter, `/`, ArrowUp na fila) · Playwright
375px confirmando que nenhum controle fica inacessível · RTL de envio, parada,
fila e rascunho · verificar que `dropzonePaste.test.tsx` continua passando ·
confirmar id único no DOM em modo busca e em chat.

---

## VIS-005 — Anexos e contexto — **DONE**

**Nível máximo: 3.** Resultado, decisões, contraste medido e trabalho deferido em
[`005-attachments-context.md`](./005-attachments-context.md).

Entregue: uma função `fileCategory(name, mime)` compartilhada com oito
categorias, precedência MIME exato → extensão → família MIME → `OTHER`, semeada
por `IMAGE_EXTENSIONS` e por `SPREADSHEET_MIME_TYPES`, consumida pelas quatro
superfícies que duplicavam o mapeamento de ícone; uma geometria de anexo
convergida sobre `AttachmentItemButton` (`radius-12`, borda de 1px,
`elevation-0`), com o chip Craft em `radius-04` para ficar dentro da curva do
composer; um modelo de estado único (`attachmentState`) cobrindo
`UPLOADING`/`PROCESSING`/`READY`/`FAILED`/`DELETING` e insensível à caixa do
status; **arquivo com falha permanece visível**, com aresta `border-error`,
superfície `status-error-00`, glifo de alerta e remoção explícita; o descritor de
transporte passou a filtrar a falha, para que ela apareça ao usuário e nunca vá
para o servidor; overlay de arrastar em todo o viewport do chat lendo o
`isDragActive` que já existia; estados vazios em `IllustrationContent`; alvo de
remoção de 16px para 24px.

Duas decisões que **não** seguiram a proposta original, com a medição no
documento: **categoria não usa cor** — glifo mais rótulo textual, deixando cor
inteira para estado (§5 do documento) — e o raio do cartão-linha ficou em
`radius-12`, não `radius-08`, porque é o valor nativo de `AttachmentItemButton` e
mudá-lo seria nível 4 (§6.1). `svc.ts` **não** foi alterado: as mensagens que a
auditoria apontou nunca chegam à tela, e os toasts que chegam já passam por
next-intl (§12.1). Arraste inválido **não** foi implementado: o dropzone do chat
não declara `accept`, então `isDragReject` é sempre falso e o componente não tem
como saber (§9.1).

Playwright de aplicação ficou **deferido** pelo mesmo conflito de runtime
compartilhado de VIS-002 e VIS-004; a validação visual foi feita em Chromium
isolado sobre o CSS do build, com a página gerada pelo `FileCard` real. Detalhes
em `005-attachments-context.md` §17.

### Pré-requisitos
VIS-001, VIS-004. — **atendidos.**

### Escopo permitido

- `web/src/sections/cards/FileCard.tsx`
- `web/src/sections/input/InputChipStrip.tsx`
- `web/src/refresh-components/popovers/FilePickerPopover.tsx`
- `web/src/sections/modals/UserFilesModal.tsx`
- `web/src/lib/projects/components/ProjectContextPanel.tsx`
- `web/src/views/AppPage.tsx` (só o overlay do `Dropzone`)
- `web/src/lib/utils.ts` (nova função de categoria)
- `web/src/lib/projects/svc.ts` (só i18n das mensagens de erro)
- catálogos i18n

Trabalho:

1. **Identidade semântica de arquivo.** Uma função `fileCategory(name, mime)`
   compartilhada: planilha, documento, imagem, apresentação, áudio, vídeo,
   arquivo compactado, outro. Semear com `IMAGE_EXTENSIONS`
   (`web/src/lib/utils.ts:127-186`) e `SPREADSHEET_MIME_TYPES`
   (`PreviewModal/variants/xlsxVariant.tsx:11-23`). Consumir nos **quatro**
   lugares que hoje duplicam o mapeamento de ícone. Cores são semânticas TON.
   **Nenhum trabalho de backend.**
2. **Uma geometria de anexo.** Hoje são três: cartão-linha (`FileCard`), tile de
   imagem (`ImageFileCard`) e pílula (`InputChipStrip`, Craft).
3. **Estado de erro visível.** Hoje o poller **remove** arquivos `failed` de
   `currentMessageFiles`, então o composer nunca mostra falha. Manter o arquivo
   visível com estado de erro e remoção explícita.
4. **Overlay de arrastar em toda a área do chat.** O `Dropzone` em
   `AppPage.tsx:778-786` **já envolve o viewport inteiro** e só desestrutura
   `getRootProps`. Basta ler `isDragActive` e renderizar um overlay dentro do
   root `relative` existente: borda tracejada TON + véu neutro + instrução
   PT-BR "Solte os arquivos aqui".
5. Estados vazios em `IllustrationContent`.
6. i18n dos erros de `svc.ts:11-13`.
7. Remoção sem sombra.

### Escopo proibido

**Não tocar a infraestrutura de upload.** `web/src/lib/projects/providers.tsx` e
`svc.ts:34-65` implementam `temp_<uuid>`, insert otimista em três listas,
reconciliação por `temp_id`, precheck de tamanho, rollback e polling de 3s. É
madura e deve ser preservada.

**Não mudar o prefixo `temp_`** — `AgentEditorPage.tsx:1160-1240` é um segundo
consumidor.

**Manter `noClick` e `noPaste`** em todo dropzone de composer.
`web/src/sections/input/__tests__/dropzonePaste.test.tsx` afirma isso em nível de
fonte, e remover `noPaste` duplica anexos porque o `handlePaste` do composer já
faz upload.

Nenhuma biblioteca de upload nova.

### Resultado visual esperado

Anexos com identidade semântica, compactos, com estado claro de upload, erro e
remoção. Soltar arquivo em qualquer ponto do chat tem retorno visual.

### Risco

**Médio.** Manter arquivo com falha visível muda o contrato de
`currentMessageFiles` e o gate de envio (`hasUploadingFiles`/`hasIndexingFiles`).
Segundo risco: mexer no `Dropzone` e quebrar a asserção de `noPaste`.

### Validação

`dropzonePaste.test.tsx` passando **sem alteração** · RTL de upload, oversize,
rejeição, falha e remoção · RTL da função de categoria por extensão e por MIME ·
Playwright de arrastar/soltar em desktop e do picker no mobile · `VIS` das oito
categorias nos dois temas.

---

## VIS-006 — Mensagens, streaming e atividade de ferramenta — **DONE**

**Nível máximo: 3.**

### Pré-requisitos
VIS-001.

### Escopo permitido

- `web/src/sections/chat/ChatUI.tsx`
- `web/src/app/app/message/HumanMessage.tsx`
- `web/src/app/app/message/messageComponents/AgentMessage.tsx`
- `web/src/app/app/message/messageComponents/MessageToolbar.tsx`
- `web/src/app/app/message/messageComponents/renderers/**`
- `web/src/app/app/message/messageComponents/timeline/**`
- `web/src/app/app/message/messageComponents/markdownUtils.tsx`
- `web/src/app/app/message/CodeBlock.tsx`
- `web/src/app/app/message/custom-code-styles.css`
- `web/src/app/app/message/Resubmit.tsx`
- `web/src/app/app/message/BlinkingBar.tsx`
- `web/src/refresh-components/texts/ShimmerText.tsx`
- `web/src/refresh-components/buttons/source-tag/**`
- catálogos i18n

Trabalho:

1. **Hierarquia conversacional mínima.** Reduzir a bolha do usuário: alinhamento
   + superfície sutil + raio menor, sem cauda assimétrica. A mensagem do
   assistente já não tem bolha e fica como está.
2. **Escada de heading real no markdown.** `.prose-onyx` hoje define
   `--tw-prose-headings` **igual** a `--tw-prose-body`. Diferenciar por cor,
   peso e espaçamento. Renomear para `prose-ton`.
3. **Um pipeline de tema para markdown.** `markdownUtils.tsx:239` usa
   `prose dark:prose-invert` — o modificador proibido. Unificar em `prose-ton`.
4. **Tema de sintaxe por token.** Substituir as ~130 linhas de Atom One hex
   (`custom-code-styles.css:51-215`) e os cinzas de scrollbar com glow
   (`:223-303`).
5. **Erro tokenizado.** `Resubmit.tsx` usa `text-red-700`, `text-neutral-700
   dark:text-neutral-300`, `bg-neutral-100 dark:bg-neutral-800` e seis cores
   cruas no `<pre>`. Trocar por `status-error-*` com ícone e texto.
6. **Atividade operacional em vez de raciocínio.** Substituir `"Thinking..."`,
   `"Reading"`, `"Searching the web"` por rótulos operacionais PT-BR:
   "Consultando fontes…", "Validando competência…", "Analisando contrato…",
   "Comparando dados…", "Executando regra…", "Preparando resposta…". Cada
   rótulo precisa corresponder a um pacote real.
7. **Não expor chain-of-thought.** `ReasoningRenderer.tsx:85` concatena
   `REASONING_DELTA` verbatim e `:182-190` oferece modal "Full text" com
   download `.txt`. Substituir por atividade observável. Distinguir atividade
   real de "pensando" decorativo.
8. **Ferramenta com estado legível**: nome da operação, executando/concluído/
   falhou com ícone por estado, evidência ou fonte usada, e detalhe técnico
   recolhido. JSON bruto só onde for apropriado para admin.
9. Substituir os três pontos feitos à mão (`CustomToolRenderer.tsx:162-183`) e o
   `SvgSparkle` (`CodingAgentRenderer.tsx:146`).
10. Substituir a varredura contínua do shimmer por indicador contido.
11. `MessageToolbar` revelado em hover/foco com `Hoverable`; remover as classes
    inertes de `:260`.
12. Corrigir o `role="button"` envolvendo `Button` em `CompletedHeader.tsx:202-218`.
13. Usar `CopyButton` do Opal em `CodeBlock.tsx:45-68`.
14. Largura de leitura tokenizada; remover `MSG_MAX_W` codificado.
15. Grade de tabela explícita e densa.
16. `useFormatter` no `RateLimitBanner`.
17. Normalizar reticências e caixa nas strings de timeline.

### Escopo proibido

**Não expor raciocínio oculto.** Não tocar o pipeline de pacotes,
`usePacketProcessor`, `useTypewriter`, `useSmoothStreaming`, nem o contrato de
`children([...])` dos renderizadores. Não quebrar a sincronização de voz do
`MessageTextRenderer` (ver VIS-008). Não remover `revealedCharCount`,
`isAudioSyncActive` nem `isAwaitingAutoPlaybackStart` do contexto.

### Resultado visual esperado

Transcript minimal e legível, com hierarquia por tipografia. Streaming que
comunica operação real, não introspecção. Ferramenta com estado claro e detalhe
sob demanda. Erros sóbrios e acessíveis.

### Risco

**Alto.** A remoção do raciocínio pode esvaziar o timeline se o substituto não
existir. O tema de sintaxe afeta legibilidade de código nos dois temas. Os
rótulos operacionais só são honestos se corresponderem a pacotes reais — um
rótulo sem processo é decoração, e reprova.

### Validação

RTL de cada renderizador de timeline · RTL confirmando que nenhum
`REASONING_DELTA` bruto chega à tela · `A11Y` de contraste de código nos dois
temas · `A11Y` do toolbar revelado (alcançável por teclado) · Playwright de
streaming, ferramenta executando/concluída/falha, e erro · revisão de produto
aprovando cada rótulo operacional contra um pacote real · grep confirmando zero
`dark:` e zero cor embutida nos arquivos alterados.

---

## VIS-007 — Especialistas e identidade de runtime — **DONE**

**Nível máximo: 4.** Justificativa: cria um componente TON novo de identidade,
substituindo a moldura de marca upstream. Não é reescrita de arquitetura.

### Pré-requisitos
VIS-001. Decisão de produto sobre a forma de identidade. ADR-009 continua
bloqueando o ativo de logo.

### Escopo permitido

- `web/src/refresh-components/avatars/CustomAgentAvatar.tsx`
- `web/src/refresh-components/avatars/AgentAvatar.tsx`
- `web/src/sections/agents/AgentCard.tsx`
- `web/src/views/AgentsNavigationPage.tsx`
- `web/src/views/AgentEditorPage.tsx` (só o seletor de identidade)
- `web/src/views/admin/AgentsPage.tsx`
- `web/src/lib/agents/components/NoAgentModal.tsx`
- `web/src/sections/modals/languageModels/shared.tsx`
- `web/src/views/admin/WorkspaceAnalyticsPage/PersonaMessagesChart.tsx`
- `web/src/lib/admin-routes.ts` (só ícone e i18n)
- `web/src/sections/Suggestions.tsx` e `web/src/lib/agents/components/AgentViewerModal.tsx` (geometria de starter)
- `web/lib/opal/src/icons/` (glifo TON novo)
- `web/src/app/css/card.css` e `web/src/app/globals.css` (remover `radial-00`)

Trabalho:

1. **Sistema unificado de identidade de especialista.** Uma forma para todos os
   estados e fallbacks. Substitui `SvgOctagonWrapper`, que hoje usa o octógono
   Onyx como moldura de **todo** avatar (`CustomAgentAvatar.tsx:76-85`).
2. **Eliminar as quatro formas concorrentes**: imagem → círculo; ícone →
   octógono; letra → octógono; agente padrão → diamante sem moldura.
3. **Paleta de acento TON** no lugar de `agentAvatarIconMap`, cuja moldura é
   sempre `stroke-text-04` (anel cinza em volta de glifo colorido) e cujas
   quatro entradas "green" usam `theme-green-05` = **verde Onyx**.
4. **Estados de runtime**: `idle`, `running`, `attention`, `selected`.
5. **Cartão de especialista sóbrio**: sair do `Card` depreciado, remover
   `radial-00` (gradiente) e `hover:shadow-box-00`, adicionar estado
   selecionado, altura por conteúdo.
6. Fallback de inicial que aceite dígito, emoji e CJK
   (hoje só `/^[a-zA-Z]$/`).
7. Substituir `title={agent.owner?.email || "Onyx"}` (`AgentCard.tsx:144`).
8. Estado vazio de `/app/agents` em `IllustrationContent`.
9. i18n de `NEW_AGENT_BUTTON_ARIA_LABEL` e de `admin-routes.ts:207-208`.
10. Uma geometria de starter message (hoje são três).
11. Trocar os oito outros pontos de render do octógono.

### Escopo proibido

**Não criar personas.** TON Central, CFO, Frota, Contratos, Auditor e RH
pertencem ao Plano backend 005 e a `TON-FE-005`. Esta fatia entrega o **sistema**
de identidade, não as identidades.

Não inventar logo (ADR-009). Não mudar `usePinnedAgents`, a reordenação por
arraste, `isAgentTabHighlightable`, nem a exclusão do agente unificado.

### Resultado visual esperado

Toda superfície de especialista usa uma identidade TON coerente. O octógono
Onyx desaparece do produto. Cartões sóbrios com estado selecionado.

### Risco

**Alto.** Dez pontos de render, mais o espelho `mobile/`.

**Armadilha registrada:** `loader/components.tsx:96-115` **duplica** a geometria
do octógono e do logo por decisão comentada. Trocar os ícones sem trocar essas
constantes **dessincroniza o `OnyxLoader` em silêncio**. VIS-007 e VIS-009 devem
coordenar, ou VIS-007 unifica a fonte de geometria.

### Validação

RTL da cadeia de fallback completa (imagem, ícone, letra latina, dígito, emoji,
CJK, vazio) · RTL dos quatro estados de runtime · grep confirmando zero
`SvgOnyxOctagon` em `web/src/` · grep confirmando que `loader/components.tsx` não
ficou desincronizado · `A11Y` de contraste dos acentos · Playwright de
`/app/agents`, cartão, editor e sidebar nos dois temas, 375/1280 · `VIS` de
`radial-00` removido.

---

## VIS-008 — Voz apenas por ditado

**Nível máximo: 3.**

### Pré-requisitos
VIS-004. Confirmação de produto de que conversa falada sai do produto.

### Escopo permitido

- `web/src/sections/input/AppInputBar.tsx` (props de voz e pontos de render)
- `web/src/sections/input/MicrophoneButton.tsx`
- `web/src/components/voice/Waveform.tsx`
- `web/src/app/app/message/messageComponents/MessageToolbar.tsx` (remover `TTSButton`)
- `web/src/views/SettingsPage.tsx` (cartão de voz)
- `web/src/views/admin/VoicePage/**` (ocultar metade TTS)
- `web/src/app/globals.css` (remover `@keyframes waveform`)
- catálogos i18n

Trabalho:

1. **Desligar o laço conversacional**: `autoSend={false}` e `autoListen={false}`
   em `AppInputBar.tsx:744-745`. **Isto sozinho remove a conversa e mantém o
   ditado.**
2. Remover `TTSButton` do toolbar.
3. Remover a waveform `"speaking"` e o `@keyframes waveform` de 0.8s.
4. Manter a waveform `"recording"` (120 barras por RMS real + timer), sóbria, e
   levar `"Mute"`/`"Unmute microphone"` para i18n.
5. Remover os três controles de voz de `SettingsPage.tsx:1630-1681`, incluindo o
   `<input type="range">` cru.
6. Ocultar a metade TTS do admin de voz.
7. Reescrever as strings que mencionam Onyx (`speakingPlaceholder`,
   `voiceSetupButton.tooltip`).
8. Remover as chaves i18n órfãs nos **nove** catálogos.
9. **Fronteira de composer** que substitui a experiência de voz: microfone →
   texto no composer → revisão → envio normal.

### Escopo proibido — acoplamentos que quebram

Estes são achados verificados, não precauções genéricas:

1. **Não remover `stopTTS` do contexto.** Ele é chamado por quatro interações
   não relacionadas a voz: o wrapper de submit (`AppInputBar.tsx:293`), o dreno
   da fila (`:408`) e os dois ramos do botão enviar/parar (`:804`, `:807`). O
   ícone e o `disabled` do botão dependem de `isVoicePlaybackControllable`
   (`:209`). **Manter como no-op.**
2. **Não remover `revealedCharCount`, `isAudioSyncActive` nem
   `isAwaitingAutoPlaybackStart` de `VoiceModeContextType`.**
   `MessageTextRenderer` os usa em seis pontos (`:145-149`, `:181-233`,
   `:428-447`) e a compilação quebra. O portão correto é
   `shouldUseAutoPlaybackSync`, cujo primeiro conjunto é `autoPlayback`
   (`VoiceModeProvider.tsx:149-150`). Com `autoPlayback` falso, todos os ramos
   retornam `fullContent`. **Portar pelo gate, não amputar.**
3. **Não remover `VoiceModeProvider`.** Está montado em
   `app/app/layout.tsx:30` e `app/nrf/layout.tsx:17`, e `useVoiceMode()` lança
   fora dele.
4. **Cuidar do `isDisabled` do microfone.** Inclui `isTTSPlaying ||
   isTTSLoading || isAwaitingAutoPlaybackStart`
   (`MicrophoneButton.tsx:307-312`). Se algum travar em `true` e a UI de parar
   tiver sido removida, o microfone fica desabilitado sem saída. Remover esses
   três termos ou garantir que fiquem falsos.
5. **Não implementar `SpeechRecognition` nesta fatia.** O ditado atual usa
   `getUserMedia` + `AudioContext` + `ScriptProcessorNode` streamando PCM16 por
   WebSocket para `/api/voice/transcribe/stream`, e depende de `stt_enabled`. Um
   caminho de navegador substituiria `VoiceRecorderSession` inteira e **perderia
   o RMS que alimenta a waveform**.

Precedente útil: `MultiModelPanel.tsx:309` já passa `disableTTS` e
`AgentMessage.tsx:233` já curto-circuita nele — o caminho sem voz já é
exercitado.

### Contrato futuro de ditado

Requisitos, para quando `SpeechRecognition` for avaliado: detecção de capacidade
graciosa; esconder o microfone se não houver suporte; consciência de contexto
seguro; transcrição intermediária; transcrição final inserida no composer;
inserção consciente do cursor onde praticável; sem perda de foco; parar ao
enviar; watchdog de inatividade (já existe, 10s); pt-BR primeiro; considerações
de Safari e iOS.

### Resultado visual esperado

Nenhuma superfície de conversa falada. Um microfone que produz texto revisável.
Waveform de gravação sóbria e informativa.

### Risco

**Médio-alto.** Os cinco acoplamentos acima são caminhos reais de quebra, e dois
deles quebram a compilação ou o streaming, não só o visual.

### Validação

`bun run types:check` **é o portão principal** (a compilação detecta a amputação
indevida) · RTL do streaming com `autoPlayback` falso, confirmando
`fullContent` · RTL de envio, fila e parada com `stopTTS` como no-op · RTL do
microfone nunca travando desabilitado · `web/tests/e2e/admin/voice/stt-only.spec.ts`
como âncora · teste de paridade de catálogo após remover as chaves órfãs ·
Playwright de ditado ponta a ponta.

---

## VIS-009 — Movimento e microinterações

**Nível máximo: 4.** Justificativa: substitui o loader de marca por um
primitivo TON novo. Não é reescrita.

### Pré-requisitos
VIS-001 (tokens de movimento) e VIS-007 (identidade, por causa da geometria
duplicada).

### Escopo permitido

- `web/lib/opal/src/components/loader/styles.css`
- `web/lib/opal/src/components/loader/components.tsx`
- `web/lib/opal/src/layouts/page-loader/components.tsx`
- `web/lib/opal/src/icons/simple-loader.tsx`
- os oito skeletons (`web/src/refresh-components/skeletons/**`,
  `web/src/sections/actions/skeleton/**`, `LLMStep.tsx`,
  `ConnectorRowSkeleton.tsx`, `UsageReports.tsx`, `ModelPickerButton.tsx`)
- `web/src/app/globals.css` (keyframes)
- `web/tailwind-themes/tailwind.config.js` (keyframes/animation)
- `web/src/app/app/message/messageComponents/timeline/**` (durações)

Trabalho:

1. **Substituir o `OnyxLoader`.** É a impressão digital mais reconhecível: 2000ms
   girando 360° com crossfade entre o contorno do octógono e os quatro diamantes
   do logo Onyx, duas vezes por ciclo. Se um ativo TON existir, avaliar movimento
   contido com ele. **Não inventar logo.**
2. **Unificar a geometria.** `loader/components.tsx:96-115` duplica os paths por
   decisão comentada. Passar a importar, ou documentar o acoplamento de forma que
   não dessincronize em silêncio.
3. **Um primitivo de skeleton.** Hoje são oito, com três tokens de fundo
   (`tint-04`, `tint-02`, `neutral-01`), três raios (08/12/16), **um** com
   `role="status"` e **um** com `motion-safe:`.
4. **Convergir os indicadores de carga** em um conjunto pequeno e proposital,
   conceitualmente: indicador de atividade, execução de especialista,
   carregamento de fonte, progresso de análise, skeleton. **Os nomes não são
   fixados aqui.**
5. `motion-safe:` em `SvgSimpleLoader`.
6. Reduzir os efeitos de 500ms e os de 300ms do timeline.
7. Implementar as microinterações da §11.6 da linguagem visual.
8. Remover keyframes órfãos (`waveform`, se VIS-008 já saiu).

### Escopo proibido

Não inventar logo. Não introduzir movimento decorativo contínuo, faísca, bounce
grande ou escala dramática. Não animar propriedade de layout onde `transform`
resolve.

### Resultado visual esperado

Movimento breve, funcional e de baixa amplitude. Nenhuma marca upstream animada.
Carregamento coerente em toda a aplicação. Reduced-motion respeitado.

### Risco

**Médio-alto.** O loader é usado em `PageLoader` e em toda tela de carregamento;
um substituto ruim degrada a percepção de desempenho. A geometria duplicada é
armadilha real.

### Validação

`A11Y` de reduced-motion em **todo** loader e skeleton · `role="status"` e nome
acessível em todos · grep confirmando zero geometria Onyx em
`loader/components.tsx` · Playwright de estados de carregamento nos dois temas ·
`VIS` de percepção de desempenho.

---

## VIS-010 — QA final De-Onyx

**Nível máximo: 2.**

### Pré-requisitos
VIS-001 a VIS-009.

### Escopo permitido

Correções pontuais nas superfícies auditadas, exclusão de código morto,
padronização de estado vazio, e o relatório final.

Trabalho:

1. **A pergunta central, superfície por superfície:** um usuário familiarizado
   com Onyx identificaria esta tela sem o logo TON? Registrar sim/não e por quê.
2. **Excluir código morto**: `web/src/app/app/message/thinkingBox/ThinkingBox.css`
   (371 linhas, zero importadores, com `box-shadow`, `text-shadow`,
   `perspective: 1000px`, `.dark` e hex cru).
3. Excluir `radial-00` se VIS-007 já migrou o único consumidor.
4. Excluir `UPSTREAM_SUPPORT_APPENDIX` (`AppProvider.tsx:41-42`, com convite
   `discord.gg`), que já não renderiza.
5. Varredura final: nenhum `dark:` fora de `createLogoIcon`; nenhuma cor
   embutida do Tailwind; nenhum raio não tokenizado; nenhum hex cru em `web/src`
   fora dos utilitários de debug; nenhuma string de UI em inglês visível numa
   operação PT-BR.
6. Padronizar os estados vazios restantes em `IllustrationContent` com copy de
   domínio.
7. Matriz completa: claro × escuro × 375/768/1280 em shell, home, conversa,
   composer, anexos, mensagens, ferramentas, especialistas, settings, admin
   visível ao cliente, auth e erro.
8. `A11Y` completo: contraste, teclado, `focus-visible`, landmarks, nomes
   acessíveis, reduced motion, alvo de toque, estado sem cor.
9. Confirmar que a IA de FE-004 e a sanitização de FE-003 sobreviveram.
10. Registrar o que continua bloqueado (logo, personas, domínios adiados).

### Escopo proibido

Nenhuma mudança nova de linguagem visual. Nenhuma feature. Nenhum backend.

### Resultado visual esperado

Um produto que não lê como Onyx rebrandado, construído sobre a base madura do
Onyx.

### Risco

**Baixo.** O risco é declarar concluído sem cobrir a matriz.

### Validação

Suíte Jest completa comparada ao baseline · toda spec Playwright existente ·
matriz de tema × viewport completa · auditoria a11y · grep de cada padrão
proibido · confirmação de que `git diff` não contém `backend/`.

---

## Rastreamento de bloqueios

| Bloqueio | Impede | Dono |
|---|---|---|
| **Ativo de logo Vale Norte / TON não existe** (ADR-009) | conclusão de VIS-002, VIS-007 e VIS-009 | produto |
| Decisão sobre **escuro neutro vs escuro verde** | início de VIS-001 | produto e design |
| Decisão sobre **ligar a escala de espaçamento** | escopo de VIS-001 | engenharia |
| Decisão sobre **KH Teka**: adotar ou remover | escopo de VIS-001 | design |
| Copy final da **entrada de domínio da home** | VIS-003 | produto |
| Aprovação dos **rótulos de atividade operacional** | VIS-006 | produto |
| **Personas concretas** de especialista | `TON-FE-005` / Plano backend 005 | produto e backend |
| Contratos de **ocorrências e relatórios** | `TON-FE-008` / `TON-FE-009` | Plano backend 003c/003d/006 |
| **Ambiente de runtime** que sirva o branch | validação `VIS` de todas as fatias | infraestrutura |

## Fatos que qualquer executor precisa saber antes de começar

1. Um terço dos raios do app ignora a escala de token.
2. Os tokens de espaçamento existem e **não estão ligados**; editá-los não faz
   nada.
3. Não existe token de movimento nem reset global de `prefers-reduced-motion`.
4. `ton-theme.test.ts` **fixa o tema claro em valores exatos** e vai falhar em
   qualquer ajuste até ser atualizado no mesmo commit.
5. A sombra do composer **é a única aresta dele**, e gerou um hack em três
   arquivos.
6. Trocar `Interactive` afeta **sete** superfícies de seleção ao mesmo tempo.
7. O octógono Onyx é a **moldura de todo avatar** de especialista.
8. Trocar os ícones de marca sem tocar `loader/components.tsx:96-115`
   dessincroniza o loader em silêncio.
9. Remover chaves do contexto de voz **quebra a compilação** do renderizador de
   streaming.
10. Remover `noPaste` de um dropzone de composer **duplica anexos**, e há teste
    de fonte que afirma isso.
11. Não existe `findings`, `occurrences`, `analysisRun` nem `reports` no
    frontend. Qualquer métrica de domínio na home seria inventada.
12. `WelcomeMessage` é compartilhado entre `/app` e `/nrf`; o composer tem três
    implementações.
