# TON-VIS-000 — auditoria forense visual e De-Onyx

**Status: DONE.** Auditoria somente de leitura. Nenhum arquivo de produção
mudou. Nenhum arquivo em `backend/` mudou.

Executado em worktree isolado `../ton-vis-000`, branch `ton/vis-000`, a partir
de `3de088cbd7896399022c7e49aef6dd8ba12bcb35` (branch `main`, árvore limpa).
Esse baseline contém TON-FE-000, FE-001, FE-002, FE-002.1, FE-003 e FE-004, e os
Planos backend 001, 002, 003a, 003b, 003c, 007 e 008a.

Este documento é o insumo único de `TON-VIS-001`. A linguagem visual alvo está
em [`visual-language.md`](./visual-language.md). O sequenciamento está em
[`visual-implementation-roadmap.md`](./visual-implementation-roadmap.md).

---

## 1. Conclusão executiva

A pergunta central era: *um usuário familiarizado com Onyx reconheceria este
produto sem o logo TON?*

**Sim, reconheceria imediatamente.** Mas não pelo motivo esperado.

O rebrand de FE-002 e FE-002.1 já trocou a paleta com competência. Verde e
dourado Vale Norte estão nos papéis certos: `theme-primary-*`,
`action-selection-*`, `action-text-link-05`, `theme-amber-*`. A escada de
superfícies escuras foi refinada e tem contraste medido. Isso funciona.

O que denuncia a origem não é cor. São seis coisas concretas:

1. **O octógono Onyx é a semântica de agente do produto.** `SvgOnyxOctagon`
   aparece em dez pontos de renderização, e o mais grave é `SvgOctagonWrapper`
   em `CustomAgentAvatar.tsx:76-85`: o octógono da marca upstream **é a moldura
   de todo avatar de especialista**. Um usuário Onyx vê a marca do Onyx em cada
   especialista TON.
2. **O loader de página anima o logo do Onyx se montando.** `OnyxLoader`
   (`web/lib/opal/src/components/loader/styles.css`) gira 360° em 2000ms
   fazendo crossfade entre o contorno do octógono e os quatro diamantes do
   `SvgOnyxLogo`. Duas vezes por ciclo, a marca upstream se desenha na tela.
   É o artefato mais reconhecível da aplicação.
3. **Não existe ativo de logo TON.** `web/lib/opal/src/logos/` tem 96 arquivos;
   três são marca Onyx e os outros 93 são logos de fornecedores. `web/public/`
   tem `logo.svg`, `logotype.png` e `onyx.ico`, todos Onyx. O fallback de
   `Logo` (`web/src/lib/app/components.tsx:102-107`) é `SvgOnyxLogoTyped`. Isso
   confirma a ADR-009 e é bloqueio de produto, não de engenharia.
4. **A geometria é mais arredondada do que TON pede.** O composer é
   `rounded-16` (16px) sem borda nenhuma, com a aresta feita só de
   `shadow-box-01`. A mensagem do usuário é uma bolha `rounded-t-16
   rounded-es-16`. `AgentCard` é `rounded-16` com gradiente radial decorativo
   (`radial-00`) e sombra no hover. Nada disso é "mínimo, operacional, preciso".
5. **A cadeia de ativação é sombra, não borda.** A auditoria encontrou o
   inverso do princípio TON: onde deveria haver borda + contraste de
   superfície, há sombra; e onde deveria haver estado explícito, há ausência.
   O caso extremo: **o composer não tem tratamento de foco nenhum**. O
   `contentEditable` tem `outline-hidden` e o contêiner não tem regra
   `focus-within`. O único sinal de foco no controle principal do produto é o
   cursor de texto.
6. **A superfície de streaming expõe raciocínio bruto.** `ReasoningRenderer`
   concatena `REASONING_DELTA` verbatim e oferece um modal "Full text" com
   download `.txt`. Isso é *chain-of-thought* exposto, em conflito direto com a
   direção de produto TON, que pede atividade operacional observável.

Além disso há dívida mensurável que qualquer trabalho visual vai encontrar:
~130 linhas de hex Atom One codificado em `custom-code-styles.css`, paleta
Tailwind bruta e o modificador `dark:` proibido em `Resubmit.tsx`, três
geometrias de anexo incompatíveis, oito skeletons com tokens e raios
divergentes, e um arquivo CSS morto de 371 linhas
(`thinkingBox/ThinkingBox.css`) com a linguagem visual antiga.

**A base técnica é madura e deve ser preservada.** O editor
`contentEditable`, a máquina de estados de upload, o pipeline de streaming, o
sistema de tokens Style Dictionary, a casca responsiva e a arquitetura Opal são
bons. O trabalho de `TON-VIS-*` é substituir apresentação, não arquitetura.

**Veredito de escopo:** de 61 linhas de matriz forense, 12 são KEEP, 34 são
ADAPT, 11 são REPLACE e 4 são IGNORE. Nenhuma exige nível 5. Duas exigem nível
4 e as duas são componentes TON novos, não reescritas.

---

## 2. Princípios visuais aplicados nesta auditoria

Os critérios abaixo foram usados para classificar cada superfície. Eles não são
opinião; são o filtro declarado da direção de produto.

| Princípio | Teste aplicado |
|---|---|
| Mínimo | O elemento carrega informação? Se some, o usuário perde algo? |
| Operacional | O estado mostrado corresponde a algo real e observável? |
| Silencioso | O elemento chama atenção em repouso sem motivo? |
| Preciso | A geometria e o espaçamento são intencionais ou herdados? |
| Corporativo | Um controller reconheceria isto como ferramenta de trabalho? |
| Técnico | A densidade serve leitura de dados ou serve estética? |

Hierarquia de meios preferida, em ordem: **tipografia → espaçamento → borda →
contraste de superfície → estado explícito → sombra**. Sombra é último recurso
e só para elevação real.

Reduzir dependência de: cartões flutuantes, pílulas, contêineres muito
arredondados, gradientes decorativos, sombras pesadas, visual de "faísca de
IA", iconografia grande e clichê de dashboard SaaS.

---

## 3. Estado atual — achados por sistema

### 3.1 Arquitetura de tokens

A cadeia é boa e tem uma única fonte de verdade. Isso é a maior alavanca do
projeto.

```text
web/lib/shared/tokens/*.json          (7 arquivos, Style Dictionary)
  → bun run build:tokens
  → web/lib/shared/dist/tokens.css    (gitignored; :root @4, .dark @510)
  → web/lib/opal/tailwind-preset.cjs  (mapeia var() → utilitário Tailwind)
  → web/tailwind-themes/tailwind.config.js (preset + extras do app)
  → web/src/app/globals.css           (@import + @config)
```

Os sete arquivos de origem:

| Arquivo | Linhas | Conteúdo |
|---|---:|---|
| `primitives.json` | 1078 | rampas cruas; `vale-norte-*` @846-1009; aliases `tint-*` @1010-1077 |
| `semantic-light.json` | 592 | bloco `light`, um par por variável CSS |
| `semantic-dark.json` | 592 | bloco `dark`, mesmo conjunto de chaves |
| `size.json` | 326 | tipografia métrica, padding, spacing, radius @286-313, blur @314-325 |
| `shadow.json` | 14 | `shadow-box-00/01/02` |
| `typography.json` | 14 | três famílias |
| `typography-presets.json` | 422 | 19 presets compostos |

**Quatro defeitos estruturais**, todos de propriedade de VIS-001:

1. **Espaçamento não é tokenizado de fato.** `size.json:102-257` define 25
   passos `spacing-block-*`, mas `tailwind-preset.cjs` **não tem chave
   `spacing`**. Todo `p-4`, `gap-2` e `mt-6` resolve para a escala embutida do
   Tailwind. Editar o token de espaçamento hoje tem **efeito zero na UI**. Os
   valores coincidem numericamente por acidente (mesma malha de 0.25rem).
2. **Movimento não tem camada de token.** Não existe token de duração nem de
   easing em lugar nenhum. Os valores estão espalhados como literais em
   `tailwind-preset.cjs`, `tailwind.config.js`, `globals.css` e em strings de
   classe de componente: 150ms, 200ms, 300ms, 500ms, 600ms, 800ms, 1s, 2s.
3. **Largura de borda não tem token ligado.** `size.json:258-261` define
   `weight-line-border: 1`, mas o preset não tem chave `borderWidth`. Toda
   largura vem do padrão Tailwind.
4. **A escala de blur é degenerada.** `backdrop-blur-01: 2px`,
   `-02: 1px`, `-03: 1px`. Dois passos idênticos e a escala invertida.

**Dois portões vão resistir a mudanças.** `web/lib/opal/src/ton-theme.test.ts`
@279-324 fixa o tema claro em referências exatas de primitivo, e @170-277 fixa
razões de contraste do escuro. `bun run verify:tokens` compara valores
resolvidos contra `origin/main`. Toda edição de token em VIS-001 precisa
atualizar esse teste no mesmo commit.

### 3.2 Cor — o que já é TON e o que ainda é upstream

**Já é TON.** `theme-primary-04/05/06`, `action-selection-00..06`,
`action-text-link-05`, `theme-amber-01/02/04/05`, `highlight-accent`, toda a
rampa `tint-*` e portanto todo `background-tint-*` nos dois temas, e — só no
escuro — `background-neutral-00..04`, `border-01..04` e `background-code-01`.

**Ainda é upstream.** A escada de texto (`text-01..05`, alpha-cinzas), os
neutros e bordas do tema claro (rampa `grey-*`), todos os `status-*`, todos os
`action-danger-*`, as doze rampas `theme-<hue>-*`, as cores de código, os
`highlight-match/selection/active`, as sombras, as máscaras e o `shimmer`.

**Dois resíduos de marca.** `onyx-ink-100/95/90` e `onyx-chrome-20/10/00`
(`primitives.json:822-845`) continuam definidos **e continuam expostos como
classes Tailwind** em `tailwind-preset.cjs:198-203`. E
`web/src/components/icons/icons.tsx` carrega `text-[#33C19E]!` — o verde menta
da marca Onyx — mais o `dark:text-black` sancionado.

**Uma inconsistência de nome perigosa.** `theme-green-05` é `#008933` (claro) e
`#00a43f` (escuro): **verde Onyx, não verde Vale Norte**. O verde da marca vive
só em `theme-primary-*`, `action-selection-*` e `action-text-link-05`. Um
implementador que buscar "verde" pelo nome do token vai pegar o errado.
`agentAvatarIconMap` já cai nessa armadilha: quatro dos dezoito ícones de
especialista usam `stroke-theme-green-05`.

**Uma armadilha de rampa no escuro.** `action-selection-*` **não é monotônica**
no escuro: `01`/`02` são lavagens escuras, `03` é um verde-menta claro e
`04`/`05`/`06` são preenchimentos médios. Quem assumir "número maior = mais
forte" vai errar.

**O canvas escuro não é neutro.** `background-tint-01` no escuro resolve para
`tint-93` = `vale-norte-neutral-93` = `#27332c`. É um carvão esverdeado. A
direção TON pede **escuro neutro, não escuro verde**. Isso é decisão explícita
para VIS-001 (ver §11.2), e é a única divergência real entre FE-002.1 e a
direção declarada agora.

### 3.3 Raio

`size.json:286-313`: `radius-02` 2px · `radius-04` 4px · `radius-08` 8px ·
`radius-12` 12px · `radius-16` 16px · `radius-20` 20px · `radius-round`
62.5rem. `rounded-full` mapeia para `radius-round`, não para `9999px`.

Consumo é **misto**. `theme.extend` não remove os raios embutidos do Tailwind,
então `rounded-sm/md/lg/xl/2xl/3xl` continuam resolvendo. Contagem em
`web/src/**/*.tsx`: **28 usos de raio tokenizado contra 14 de raio não
tokenizado**. Um terço dos raios do app ignora a escala.

Onde 16px aparece sem razão semântica:

| Superfície | Arquivo | Valor |
|---|---|---|
| Composer | `AppInputBar.tsx:831` | `rounded-16` |
| Composer Craft | `BaseInputBar.tsx:283-286` | `rounded-t-16` |
| Bolha do usuário | `HumanMessage.tsx:224-226` | `rounded-t-16 rounded-es-16` |
| Edição de mensagem | `HumanMessage.tsx:51-55` | `rounded-16` + `border` sem token |
| `AgentCard` | `web/src/app/css/card.css:1-3` | `rounded-16` |
| `ActionCardSkeleton` | `ActionCardSkeleton.tsx:11` | `rounded-16` |
| Waveform "speaking" | `Waveform.tsx:130` | `rounded-16` |

**Geometria de pílula sem razão semântica.** O composer está limpo:
`rounding="full"` não é usado em nenhum controle dele. As ocorrências reais:
`SidebarTabSkeleton.tsx:19` usa `rounded-full` no placeholder de ícone
recolhido; `ActionCardSkeleton` usa três barras `rounded-full`;
`CustomToolRenderer.tsx:165-176` usa três pontos `rounded-full` de 4px;
`web/src/lib/app/components.tsx:41` usa `rounded-full` no contêiner do logo
enterprise; `CustomAgentAvatar.tsx:103-118` usa `rounded-full` na imagem de
avatar. Os pontos de carga e o avatar de imagem são semanticamente
justificados. O resto não é.

### 3.4 Sombra e elevação

Só três tokens, em `shadow.json` inteiro:

```text
shadow-box-00  0px 0px 2px 1px  var(--shadow-01)
shadow-box-01  0px 2px 12px 0px var(--shadow-02), 0px 0px 4px 1px var(--shadow-02)
shadow-box-02  0px 2px 24px 0px var(--shadow-03), 0px 0px 12px 1px var(--shadow-03)
```

A geometria é invariante ao tema; só a cor troca. **No escuro as sombras são
brilhos brancos**: `shadow-01` escuro é `#ffffff0d`, `-02` é `#ffffff1a`, `-03`
é `#ffffff33`. Com 24px de blur, `shadow-box-02` lê como halo, não como sombra.

O caso mais custoso é `shadow-box-01` no composer. Ele não é decorativo: **é a
única aresta do composer**, porque o cartão não tem borda. E ele gerou um
contorno de três arquivos:

- `AppInputBar.tsx:832-841` — a nota explicando que a sombra estende ~14px;
- `AppPage.tsx:966-985` — a nota, mais os dois espaçadores animados
  `h-0` ↔ `h-[14px]` em @986-991 e @1041-1046;
- `AppChrome.tsx:632-647` — a compensação `pb-2` vs `py-2` no footer.

Trocar a aresta do composer de sombra para borda **remove os três hacks de
uma vez**. É o maior ganho de simplificação da trilha.

Onde a sombra é legítima e deve ficar: popover, dropdown, dialog, tooltip. Onde
pode sair: `AgentCard` (`hover:shadow-box-00`), `Waveform` "speaking"
(`shadow-box-01`), o badge de remover anexo (`shadow-xs` em
`FileCard.tsx:47`), e o composer.

### 3.5 Borda

Tokens: `border-01..05` e `border-inverted-01..05`, mais o alias `border` =
`var(--border-01)`.

**Não existe sistema semântico de papéis por nome.** Os papéis existem apenas
como convenção, e o único lugar onde estão escritos é um teste:
`ton-theme.test.ts:211-233` documenta `border-01` como fio de cabelo padrão
(≥1.5:1 sobre `background-tint-01`), `border-04` como contorno de foco genérico
(≥3:1 em toda superfície) e `border-05` como aresta de foco de input, pareada
com um anel interno `background-tint-04`. Não há `border-selected` nem
`border-error`; seleção usa `action-selection-*` e erro usa `status-error-*`.

**A cor de borda padrão é definida duas vezes em `globals.css`.** Em @26-34 um
shim de compatibilidade Tailwind v3 aplica
`border-color: var(--color-gray-200, currentcolor)` a `*, ::after, ::before,
::backdrop, ::file-selector-button`. Em @49-52, `@layer base { * { @apply
border-border } }`. Ambos em `@layer base`, mesma especificidade, então o
segundo ganha para elementos reais — mas **os pseudo-elementos ficam com
`#e5e7eb`**, um cinza que não conhece tema.

Bordas do tema claro ainda são cinzas upstream; as do escuro foram rebrandadas
para neutros esverdeados. Assimetria a resolver em VIS-001.

### 3.6 Tipografia

Três famílias em `typography.json`. Hanken Grotesk e DM Mono carregam por
`next/font` em `web/src/app/layout.tsx:38-56`, com as variáveis escritas inline
no `<html style>` em @96-108 para permitir a cauda CJK por locale. **KH Teka
carrega por `@font-face` local** (`web/lib/opal/src/styles/typography.css:18-33`,
dois `.otf` em `web/public/fonts/`) e **nenhum preset a referencia**. Está
carregada, tokenizada e não usada — exceto por um `style` inline em
`BuildWelcome.tsx:74-90`.

19 presets. Pesos em uso: 375, 400, 450, 500, 600, 700. `heading-h1` é o único
preset com px codificado (48px/64px) em vez de referência métrica.

**O achado que mais importa para a direção TON:** `.prose-onyx`
(`custom-code-styles.css:30-49`) define `--tw-prose-headings: var(--text-04)` e
`--tw-prose-body: var(--text-04)`. **Títulos e corpo têm exatamente a mesma
cor.** A diferenciação de heading vem só da escala de tamanho e peso do Tailwind
Typography. E `h1`–`h6` e `blockquote` **não são sobrescritos** em nenhum dos
dois pipelines de markdown.

Isso confirma a tese da direção: *há espaço grande para diferenciar por
tipografia antes de introduzir mais contêineres*. A hierarquia tipográfica está
subutilizada, não saturada.

Rótulos de seção da sidebar são `secondary-body` = 12px / peso 400 / 16px de
linha, cor `text-02` (~45% de opacidade no claro). Caixa de sentença, sem
letter-spacing. São rótulos de baixíssimo contraste.

### 3.7 Espaçamento e densidade

Ver §3.1 defeito 1: a escala existe e não está ligada.

Gaps recorrentes medidos:

| Contexto | Valor | Arquivo |
|---|---|---|
| Entre mensagens do transcript | `gap-12` (3rem) | `ChatUI.tsx:168-173` |
| Transcript, padding vertical | `pt-4 pb-8` | idem |
| Mensagem do assistente, blocos | `gap-3` | `AgentMessage.tsx:285-288` |
| Conteúdo do assistente, inline | `px-3` | `AgentMessage.tsx:306-315` |
| Header do app | `p-2 sm:px-4`, altura 52px | `AppChrome.tsx:414` |
| Sidebar, corpo | `px-2` | `sidebar/styles.css:141` |
| Sidebar, header de seção | `pt-3 ps-2 pe-1` | `sidebar/styles.css:145` |
| Sidebar, título de seção | `px-0.5 py-1.5` | `sidebar/styles.css:148` |
| Página, padding horizontal | `px-2 sm:px-4` | `AppPage.tsx:926` |

`gap-12` entre mensagens é generoso e correto para canvas conversacional.
`h-24` fixo no header do `AgentCard` e o `h-11` fixo da barra de ferramentas do
composer são densidade herdada que não se adapta.

**Largura de leitura tem três valores concorrentes**, o que é um defeito real:

| Constante | Valor | Onde |
|---|---:|---|
| `--app-page-main-content-width` | 45rem / 720px | `web/lib/opal/src/styles/sizes.css:13` |
| `MSG_MAX_W` | `md:max-w-[720px]` codificado | `ChatUI.tsx:28-31` |
| `width.message-default` | 740px | `tailwind.config.js:48` — **não usado pelo chat** |
| máscara de blur do canvas | `50% ± 25rem` (800px) | `AppChrome.tsx:684-690` |
| chat compartilhado | `max-w-200` | `SharedChatDisplay.tsx:233` |

### 3.8 Movimento — inventário e classificação

| Efeito | Valor | Origem | Classificação |
|---|---|---|---|
| Largura da sidebar | 200ms ease-in-out | `sidebar/styles.css:30` | KEEP |
| Slide da sidebar mobile | `duration-200` | `sidebar/styles.css:51` | KEEP |
| Opacidade do backdrop | `duration-200` | `sidebar/styles.css:75` | KEEP |
| Rótulo do tab recolhido | 200ms + visibility delay | `sidebar-tab/styles.css:26-73` | KEEP |
| `.interactive` fundo/cor | 150ms ease-in-out | `core/interactive/shared.css:23-38` | KEEP |
| Linhas do grid da home | `duration-150` | `AppPage.tsx:792` | KEEP |
| `Fade` (5 usos) | 150ms opacidade | `AppPage.tsx:88-108` | KEEP |
| Espaçadores de sombra | `duration-150` | `AppPage.tsx:986,1041` | REMOVE junto com a sombra |
| Barra de ferramentas do composer | `duration-150` | `AppInputBar.tsx:622` | KEEP |
| Faixa de anexos | `duration-150` + altura via JS | `AppInputBar.tsx:871-877` | KEEP |
| Alvo de soltura da sidebar | `duration-200` | `AppSidebar.tsx:174` | KEEP |
| Skeletons de scroll infinito | `duration-300` opacidade | `AppSidebar.tsx:190` | REDUCE |
| Header do timeline | `duration-300` cores | `AgentTimeline.tsx:371-382` | REDUCE para 200ms |
| Expansão do timeline | `animate-in fade-in slide-in-from-top-2 duration-300` | `AgentTimeline.tsx:401` | REDUCE |
| `shimmer-slide` | 1s ease-out infinito | `globals.css:280-301` | REPLACE |
| `BlinkingBar` | `animate-pulse` (2s) | `BlinkingBar.tsx` | REPLACE |
| Pontos de tool | `animate-pulse` + delays 0.1/0.2s | `CustomToolRenderer.tsx:162-183` | REPLACE |
| `OnyxLoader` | 2000ms rotação + crossfade | `loader/styles.css:15-76` | **REPLACE** |
| `animate-waveform` | 0.8s ease-in-out infinito | `globals.css:385-397` | REMOVE com o TTS |
| `animate-fade-in-up` | 500ms | `tailwind.config.js:22-32` | REDUCE |
| `.collapsible` | 500ms max-height + opacidade | `globals.css:349-353` | REDUCE |
| `animate-fadeIn` | 200ms | `globals.css:381` | KEEP |
| `onyx-math-appear` | 120ms ease-out | `custom-code-styles.css:7-21` | KEEP, renomear |
| Passos do onboarding | 500ms slide | `OnboardingFlow.tsx:48-74` | REDUCE |
| Renomear conversa, typewriter | 30ms por caractere | `ChatButton.tsx:156-178` | KEEP |
| `IntroBackground` / Craft | partículas, vídeo | `craft/components/*` | IGNORE (superfície suprimida) |

A faixa dominante já é 150–300ms, próxima da faixa TON de 120–280ms. **O
movimento não é o problema principal**; os desvios são o loader de marca, o
shimmer, e os três efeitos de 500ms.

**Não existe reset global de `prefers-reduced-motion`.** Só quatro blocos
escopados: `globals.css:334-346` (shimmer), `css/comet.css:28`,
`custom-code-styles.css:19` e `loader/styles.css:78-90`. Logo,
`animate-fade-in-scale`, `animate-waveform`, `animate-fade-in-up`,
`animate-pulse` e todo `duration-150` continuam rodando para quem pediu menos
movimento. `SvgSimpleLoader` usa `animate-spin` puro, enquanto `IconLoader` e
`OnyxLoader` usam `motion-safe:animate-spin` — e `SvgSimpleLoader` é o spinner
mais usado no código admin.

---

## 4. Inventário de impressões digitais Onyx

Cada item recebe classificação. Nada foi marcado para remoção só por ser
também usado pelo Onyx.

### 4.1 Marca visível — o núcleo do problema

| # | Impressão | Local exato | Classificação | Nível | Dono |
|---:|---|---|---|---:|---|
| F1 | `SvgOnyxOctagon` como moldura de **todo** avatar de especialista | `CustomAgentAvatar.tsx:22` import, `:82` render dentro de `SvgOctagonWrapper` (`:76-85`) | **REPLACE** | 4 | VIS-007 |
| F2 | `SvgOnyxOctagon` como ícone do destino Especialistas | `AppSidebar.tsx:75`, `:519` | **REPLACE** | 2 | VIS-007 |
| F3 | `SvgOnyxOctagon` no header de `/app/agents` | `AgentsNavigationPage.tsx:17`, `:123` | **REPLACE** | 2 | VIS-007 |
| F4 | `SvgOnyxOctagon` no header admin de agentes | `admin/AgentsPage.tsx:3`, `:23` | **REPLACE** | 2 | VIS-007 |
| F5 | `SvgOnyxOctagon` no header do editor de agente | `AgentEditorPage.tsx:68`, `:1367` | **REPLACE** | 2 | VIS-007 |
| F6 | `SvgOnyxOctagon` no seletor de agente da analítica (dois pontos) | `PersonaMessagesChart.tsx:11`, `:54`, `:78` | ADAPT | 2 | VIS-007 |
| F7 | `SvgOnyxOctagon` em estado vazio de acesso | `languageModels/shared.tsx:50`, `:415` | ADAPT | 2 | VIS-007 |
| F8 | `SvgOnyxOctagon` no header de `NoAgentModal` | `NoAgentModal.tsx:5`, `:16` | ADAPT | 2 | VIS-007 |
| F9 | `SvgOnyxOctagon` como metadado de rota admin | `admin-routes.ts:24`, `:205` | ADAPT | 1 | VIS-007 |
| F10 | **`OnyxLoader`**: 2000ms girando e montando o logo Onyx | `loader/styles.css:4-90`; geometria duplicada em `loader/components.tsx:96-115` (`OUTLINE_PATH`, `MARK_PATHS`, `STROKE_WIDTH`) | **REPLACE** | 4 | VIS-009 |
| F11 | Fallback de `Logo` é `SvgOnyxLogo` / `SvgOnyxLogoTyped` | `web/src/lib/app/components.tsx:15`, `:34-36`, `:54`, `:102-107` | ADAPT (bloqueado por ADR-009) | 1 | VIS-002 |
| F12 | `Logo onyxBranded` força a marca upstream ignorando white-label | `components.tsx:21-23`, `:34-40`; usado em `BuildWelcome.tsx:79` | IGNORE (superfície Craft suprimida) | 0 | — |
| F13 | `web/public/logo.svg` com `fill="black"` codificado, cego a tema | `web/public/logo.svg` | ADAPT | 0 | VIS-002 |
| F14 | `SvgOnyxLogo` no avatar do agente padrão, **sem moldura** | `AgentAvatar.tsx:40` | **REPLACE** | 3 | VIS-007 |
| F15 | `SvgOnyxLogo` size 44 na tela de login | `auth/AuthFlowContainer.tsx:38` | ADAPT | 1 | VIS-002 |
| F16 | `SvgOnyxLogo` no `WelcomeMessage` da home | `WelcomeMessage.tsx:64` via `Logo folded size={32}` | ADAPT | 2 | VIS-003 |
| F17 | Verde menta Onyx codificado | `web/src/components/icons/icons.tsx` `text-[#33C19E]!` | ADAPT | 1 | VIS-001 |
| F18 | Rampas `onyx-ink-*` / `onyx-chrome-*` expostas como classes Tailwind | `primitives.json:822-845`; `tailwind-preset.cjs:198-203` | **REPLACE** | 1 | VIS-001 |

### 4.2 Copy e idioma

| # | Impressão | Local | Classificação | Nível | Dono |
|---:|---|---|---|---:|---|
| C1 | `"Open Sidebar"` / `"Close Sidebar"` sem i18n | `sidebar/components.tsx:177`; consumido em `:183` aria-label, `:184` tooltip, `:216` Tooltip, `:223` Container aria-label | **REPLACE** via contrato `OpalStrings` | 2 | VIS-002 |
| C2 | `"Unmute"` / `"Mute"` e `"Unmute microphone"` / `"Mute microphone"` sem i18n | `Waveform.tsx:161`, `:203` | **REPLACE** | 2 | VIS-008 |
| C3 | `aria-label="share-chat-button"` — nome acessível é um seletor | `AppChrome.tsx:578` | ADAPT | 0 | VIS-002 |
| C4 | `NEW_AGENT_BUTTON_ARIA_LABEL = "AgentsPage/new-agent-button"` exposto como `aria-label` real | `AgentsNavigationPage.tsx:62` | ADAPT | 0 | VIS-007 |
| C5 | `aria-label="onboarding-flow"` sem i18n | `OnboardingFlow.tsx:44` | ADAPT | 0 | VIS-003 |
| C6 | Toasts em inglês codificado | `AppChrome.tsx:208` `"Failed to delete chat. Please try again."`, `:240` `"Could not end the incognito chat. Try again."` | ADAPT | 0 | VIS-002 |
| C7 | Erros de upload em inglês codificado | `web/src/lib/projects/svc.ts:11-13` `` `${action} failed (Status: ${response.status})` `` | ADAPT | 0 | VIS-005 |
| C8 | `title={agent.owner?.email \|\| "Onyx"}` — marca upstream como fallback de dono | `AgentCard.tsx:144` | **REPLACE** | 0 | VIS-007 |
| C9 | `title: "Agents"` / `sidebarLabel: "Agents"` sem i18n | `admin-routes.ts:207-208` | ADAPT | 0 | VIS-007 |
| C10 | `UNNAMED_CHAT = "New Chat"` sem i18n | `web/src/lib/constants.ts:115` | ADAPT | 0 | VIS-002 |
| C11 | `UPSTREAM_SUPPORT_APPENDIX` com convite `discord.gg` | `web/src/providers/AppProvider.tsx:41-42` | ADAPT (já não renderiza; código morto) | 0 | VIS-010 |
| C12 | Placeholder `"Onyx is speaking..."` e tooltip de setup de voz mencionando Onyx | `en.json:9534`, `:9543-9545` | **REPLACE** | 0 | VIS-008 |
| C13 | Saudação genérica de IA sorteada por `Math.random()` | `WelcomeMessage.tsx:28-38`; `en.json:10826-10827` `"How can I help?"` / `"Let's get started."`; `pt.json:10794-10795` | **REPLACE** | 2 | VIS-003 |
| C14 | `"Thinking..."`, `"Thought for {duration}"`, `"Full text"` — vocabulário de raciocínio | `en.json` `chat.messages.timeline.*`, `chat.messages.reasoning.*` | **REPLACE** | 2 | VIS-006 |
| C15 | Comentário `// Submit edit if "Command Enter" is pressed, like in ChatGPT` | `HumanMessage.tsx:77` | IGNORE (comentário, não copy) | 0 | — |
| C16 | Inconsistência de reticências e caixa: `"Thinking..."` vs `"Bash · running…"`; `"Coding agent"` vs `"Internal Search"`; `"Copied!"` é a única exclamação | `en.json` `chat.messages.timeline.*` | ADAPT | 0 | VIS-006 |
| C17 | `"PLAINTEXT"` como rótulo de extensão para `.txt` | `FilePickerPopover.tsx:31-37` | ADAPT | 0 | VIS-005 |
| C18 | `"User has stopped generation"` — terceira pessoa para quem agiu | `en.json` `chat.messages.agentMessage.stoppedGeneration.text` | ADAPT | 0 | VIS-006 |
| C19 | Literal `craft` visível com `font-kh-teka` inline | `BuildWelcome.tsx:74-90` | IGNORE (superfície suprimida) | 0 | — |
| C20 | `"Craft"` sem tradução no catálogo pt | `pt.json:13492-13494` | IGNORE (política FE-003: entrada oculta) | 0 | — |

### 4.3 Identificadores e acoplamentos com o nome upstream

Estes não são visuais. Estão listados porque um implementador vai encontrá-los,
e porque renomear alguns **quebra testes**.

| # | Identificador | Local | Decisão |
|---:|---|---|---|
| I1 | `id="onyx-chat-input"` | `AppInputBar.tsx:829` | KEEP |
| I2 | `id="onyx-chat-input-textbox"` | `AppInputBar.tsx:906`; acoplado por string em `AppChrome.tsx:702`, `:716`; usado em `web/tests/e2e/chat/InputBar.ts:90`, `:150` | KEEP — renomear exige tocar 4 arquivos e specs |
| I3 | `id="onyx-chat-input-send-button"` **duplicado no DOM** em modo busca | `AppInputBar.tsx:783` e `:1045` | ADAPT — defeito real de a11y, corrigir em VIS-004 |
| I4 | `id="onyx-human-message"` | `HumanMessage.tsx:210` | KEEP |
| I5 | `data-testid="onyx-ai-message"` | `AgentMessage.tsx:286` | KEEP |
| I6 | `data-testid="onyx-logo"`, `"chat-intro"` | `WelcomeMessage.tsx:60`, `:92` | KEEP — contrato e2e |
| I7 | `id="onyx-user-dropdown"` | `AccountPopover.tsx:256` | KEEP |
| I8 | `data-testid="AppSidebar/more-agents"` | `AppSidebar.tsx:519` | KEEP — decisão registrada em FE-004 |
| I9 | `@keyframes onyx-math-appear` | `custom-code-styles.css:7`, `:21` | ADAPT — renome cosmético, nível 1 |
| I10 | `.prose-onyx` como nome de classe | `custom-code-styles.css:30`; `MessageTextRenderer.tsx:494` | ADAPT — nível 1 |
| I11 | `onyx:draft:chat:<id>` em sessionStorage | `web/src/hooks/useDraft.ts:6` | KEEP |
| I12 | `onyx:onboardingCompleted:<userId>` em localStorage | `useShowOnboarding.ts:19-21` | KEEP — renomear reabre onboarding para todos |
| I13 | `temp_<uuid>` como prefixo de id otimista | `providers.tsx:56-63`; segundo consumidor em `AgentEditorPage.tsx:1160-1240` | KEEP — contrato interno |
| I14 | `NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED` (Danswer, nome pré-Onyx) | `web/src/lib/app/components.tsx:7`, `:73-75` | IGNORE — já não renderiza |
| I15 | `data-main-container` | `AppChrome.tsx:726` | KEEP |

### 4.4 Padrões visuais reconhecíveis como upstream

| # | Padrão | Local | Classificação | Nível | Dono |
|---:|---|---|---|---:|---|
| P1 | ~130 linhas de hex Atom One Light/Dark codificado, com `!important` em `.hljs` | `custom-code-styles.css:51-215` | **REPLACE** | 2 | VIS-006 |
| P2 | Cinzas de scrollbar codificados + `box-shadow: 0 0 10px #6b7280` no hover | `custom-code-styles.css:223-303` | **REPLACE** | 2 | VIS-006 |
| P3 | Paleta Tailwind bruta `text-red-700`, `text-neutral-700`, `bg-neutral-100`, `border-neutral-200` **mais** o modificador `dark:` proibido | `Resubmit.tsx:123`, `:136`, `:195`, `:218`, `:236` | **REPLACE** | 2 | VIS-006 |
| P4 | `prose dark:prose-invert` — segunda estratégia de tema, proibida | `markdownUtils.tsx:239` | **REPLACE** | 2 | VIS-006 |
| P5 | `thinkingBox/ThinkingBox.css` — 371 linhas mortas, zero importadores, com `box-shadow`, `text-shadow`, `perspective: 1000px`, `.dark` e hex cru | `web/src/app/app/message/thinkingBox/ThinkingBox.css` | **REPLACE** (excluir) | 0 | VIS-010 |
| P6 | `radial-00` — gradiente radial decorativo no `AgentCard` | `globals.css:40-47`; usado em `AgentCard.tsx:80` | **REPLACE** | 2 | VIS-007 |
| P7 | Vinheta `rgba(0,0,0,0.4)` e máscara com `black` literal no canvas | `AppChrome.tsx:665-670`, `:684-690` | ADAPT | 2 | VIS-002 |
| P8 | Faísca de IA genérica dentro de um passo de ferramenta | `CodingAgentRenderer.tsx:146` `stepIcon={SvgSparkle}` | **REPLACE** | 2 | VIS-006 |
| P9 | Três pontos pulsantes feitos à mão, com delays que não funcionam | `CustomToolRenderer.tsx:162-183` | **REPLACE** | 2 | VIS-006 |
| P10 | Botão de copiar feito à mão, ignorando `CopyButton` do Opal | `CodeBlock.tsx:45-68` | ADAPT | 2 | VIS-006 |
| P11 | `<a>` cru com `text-action-selection-01 hover:underline` | `CustomToolRenderer.tsx:220-232` | ADAPT | 2 | VIS-006 |
| P12 | `dangerouslySetInnerHTML` com saída do hljs | `CustomToolRenderer.tsx:51-54` | KEEP (funcional; nota de segurança) | 0 | — |
| P13 | JSON bruto de Request/Response como apresentação padrão de ferramenta | `CustomToolRenderer.tsx:185-200`, `:235-263` | ADAPT | 3 | VIS-006 |
| P14 | Raciocínio bruto exposto + modal "Full text" + download `.txt` | `ReasoningRenderer.tsx:85`, `:182-190` | **REPLACE** | 3 | VIS-006 |
| P15 | Estado vazio de `/app/agents` ignora `IllustrationContent` | `AgentsNavigationPage.tsx:167-175` | ADAPT | 2 | VIS-007 |
| P16 | Estado vazio de arquivos de projeto é barra tracejada feita à mão | `ProjectContextPanel.tsx:255-268` | ADAPT | 2 | VIS-005 |
| P17 | Classes inertes: `transition-transform duration-300 ease-in-out transform opacity-100` sem nada que as acione | `MessageToolbar.tsx:260` | ADAPT | 0 | VIS-006 |
| P18 | Token vazado como nome de classe: `className="... mainUiMuted underline"` | `sharedMarkdownComponents.tsx:35`, `:74` | ADAPT | 0 | VIS-006 |
| P19 | `shuffleWidths()` com `.sort(() => Math.random() - 0.5)` num caminho de render | `AppSidebar.tsx:110-114` | ADAPT | 1 | VIS-002 |
| P20 | Overlay de intro em `z-9999` disparado por notificação | `AppSidebar.tsx:571` | IGNORE (gated por `SHOW_BUILDER_PRODUCT_ENTRY = false`) | 0 | — |
| P21 | `scrollbar-color: #888 transparent` codificado | `globals.css:187` | ADAPT | 1 | VIS-001 |
| P22 | `--color-gray-200` em pseudo-elementos, cego a tema | `globals.css:32` | ADAPT | 1 | VIS-001 |
| P23 | `shimmer-base` / `shimmer-highlight` como hex cru dentro da camada de token | `semantic-light.json:3-10`, `semantic-dark.json:3-10` | ADAPT | 1 | VIS-001 |
| P24 | Larguras px codificadas fora do sistema | `tailwind.config.js:44-70` (`message-default` 740px, `searchbar` 850px, `document-sidebar` 800px, `content-max` 725px) | ADAPT | 1 | VIS-001 |

---

## 5. Matriz forense

Colunas: **Cls** = KEEP / ADAPT / REPLACE / IGNORE · **Nv** = nível de mudança
0–5 · **Dep.** = pré-requisito · **Val.** = requisito de validação.

Legenda de validação: `RTL` = Jest + React Testing Library · `PW` = Playwright ·
`TOK` = `ton-theme.test.ts` + `bun run verify:tokens` · `A11Y` = contraste e
foco medidos · `VIS` = revisão visual claro/escuro × 375/768/1280 · `BUILD` =
`bun run types:check` + `lint` + `build`.

### 5.1 Fundações e tokens

| Componente / arquivo | Comportamento e fingerprint atual | Problema | Cls | Nv | Alvo TON | Tokens / primitivos | Dep. | Fatia | Risco | Val. |
|---|---|---|---|---:|---|---|---|---|---|---|
| `web/lib/shared/tokens/primitives.json` | rampas `vale-norte-*` @846-1009 já TON; `onyx-ink-*`/`onyx-chrome-*` @822-845 residuais | resíduo de marca exposto como classe | REPLACE | 1 | remover as duas rampas e as classes do preset | `onyx-ink-*`, `onyx-chrome-*` | — | VIS-001 | classe usada em algum lugar não auditado | `BUILD`, `TOK`, grep |
| `primitives.json:1010-1077` (aliases `tint-*`) | `tint-*` → `vale-norte-neutral-*`; retinge toda superfície nos dois temas | canvas escuro é carvão verde, não neutro | ADAPT | 1 | separar: neutros verdadeiros no canvas, verde só em estado | `tint-02..98`, `background-tint-00..04` | — | VIS-001 | reabrir contraste aprovado em FE-002.1 | `TOK`, `A11Y`, `VIS` |
| `semantic-light.json` / `semantic-dark.json` | 592 linhas cada, mesmo conjunto de chaves | bordas claras ainda cinza upstream; escuras já verdes | ADAPT | 1 | simetria de papel de borda nos dois temas | `border-01..05` | — | VIS-001 | assimetria de contraste | `TOK`, `A11Y` |
| `semantic-*.json:3-10` | `shimmer-base`/`shimmer-highlight` como hex cru | valor fora do sistema dentro da camada de token | ADAPT | 1 | apontar para primitivo | `shimmer-*` | — | VIS-001 | baixo | `TOK` |
| `size.json:102-257` | 25 passos `spacing-block-*` definidos | **não ligados ao Tailwind**; editar não faz nada | ADAPT | 1 | adicionar chave `spacing` ao preset ou remover os tokens | `spacing-block-*`, `spacing-inline-*` | — | VIS-001 | ligar a escala muda todo `p-`/`gap-` de uma vez | `BUILD`, `VIS` amplo |
| `size.json:286-313` | `radius-02..20` + `radius-round` | escala boa; consumo misto (14 usos não tokenizados) | KEEP | 0 | manter escala, corrigir consumo | `radius-*` | — | VIS-001 | — | grep, `BUILD` |
| `size.json:258-261` | `weight-line-border: 1` definido | sem chave `borderWidth` no preset | ADAPT | 1 | ligar largura de borda ao token | `weight-line-border` | — | VIS-001 | baixo | `BUILD` |
| `size.json:314-325` | `backdrop-blur-01` 2px, `-02` 1px, `-03` 1px | escala degenerada e invertida | ADAPT | 1 | escala monotônica de três passos | `backdrop-blur-*` | — | VIS-001 | baixo | `VIS` |
| `shadow.json` (14 linhas) | 3 tokens; geometria invariante; **escuro = brilho branco** | halo no escuro; sombra usada como aresta | ADAPT | 1 | manter 3 níveis; reduzir raio; papel só de elevação real | `shadow-box-00/01/02`, `shadow-01/02/03` | — | VIS-001 | popover pode perder legibilidade | `VIS`, `A11Y` |
| `typography.json` + `typography-presets.json` | 3 famílias, 19 presets; **KH Teka carregada e não usada** | fonte morta; `heading-h1` com px cru | ADAPT | 1 | decidir KH Teka; converter `heading-h1` para métrica | `font-kh-teka`, `heading-h1` | — | VIS-001 | remover fonte quebra `BuildWelcome` | `BUILD`, `VIS` |
| **movimento (inexistente)** | zero token de duração/easing; literais em 4 arquivos | não há como ajustar movimento de forma central | ADAPT | 1 | criar `duration-*` e `easing-*` e um reset global de reduced-motion | novos | — | VIS-001 | reset global pode parar animação necessária | `A11Y`, `VIS` |
| `tailwind-preset.cjs` | mapeia cor, radius, shadow, blur, z-index, keyframes | sem `spacing`, `borderWidth`, `transitionDuration` | ADAPT | 1 | adicionar as três chaves | — | tokens acima | VIS-001 | ligar tudo de uma vez amplia o diff | `BUILD` |
| `tailwind.config.js:44-70` | larguras px codificadas + breakpoints | fora do sistema de token; `message-default` não usado | ADAPT | 1 | tokenizar larguras de leitura; manter breakpoints | novos tokens de largura | — | VIS-001 | breakpoints são contrato FE-004 | `BUILD`, `PW` |
| `globals.css:26-34` | `--color-gray-200` em pseudo-elementos | cor cega a tema | ADAPT | 1 | usar `border-01` | `border-01` | — | VIS-001 | baixo | `VIS` |
| `globals.css:49-52` | `* { @apply border-border }` | correto | KEEP | 0 | — | — | — | — | — | — |
| `globals.css:187` | `scrollbar-color: #888 transparent` | hex cru; a regra de `textarea` 47 linhas abaixo usa token | ADAPT | 1 | usar `scrollbar-thumb`/`-track` | `scrollbar-*` | — | VIS-001 | baixo | `VIS` |
| `globals.css:40-47` (`radial-00`) | gradiente radial utilitário | decoração sem função | REPLACE | 1 | excluir após migrar `AgentCard` | — | VIS-007 | VIS-001 | único consumidor é `AgentCard` | grep, `VIS` |
| `web/lib/opal/src/ton-theme.test.ts` | fixa tema claro e razões do escuro | é o portão; e é a **única** documentação dos papéis de borda | KEEP | 0 | estender com papéis nomeados | — | — | VIS-001 | esquecer de atualizar bloqueia o commit | `TOK` |
| `web/src/components/icons/icons.tsx` | `text-[#33C19E]!` + `dark:text-black` | verde de marca Onyx codificado | ADAPT | 1 | token TON; manter a exceção `createLogoIcon` | `theme-primary-05` | — | VIS-001 | `icons.test.tsx:66` afirma `dark:text-black` | `RTL`, `BUILD` |

### 5.2 Casca, navegação e header — IA de FE-004 congelada

| Componente / arquivo | Comportamento e fingerprint atual | Problema | Cls | Nv | Alvo TON | Tokens / primitivos | Dep. | Fatia | Risco | Val. |
|---|---|---|---|---:|---|---|---|---|---|---|
| `web/src/app/app/layout.tsx` (39L) | monta `ProjectsProvider > VoiceModeProvider > RootLayout.Root > [AppSidebar, AppChrome]` | nenhum | KEEP | 0 | — | — | — | — | — | — |
| `web/lib/opal/src/layouts/root/styles.css` (47L) | `h-dvh`, `overflow-hidden`, slots header/main/footer/panel | nenhum | KEEP | 0 | — | — | — | — | — | — |
| `web/lib/opal/src/layouts/sidebar/components.tsx` (342L) | 3 ramos responsivos; `effectiveFolded`; `data-folded`; scroll em sessionStorage | `"Open Sidebar"`/`"Close Sidebar"` codificado @177 | ADAPT | 2 | rótulos via `OpalStrings`; comportamento intacto | — | contrato `OpalStrings` | VIS-002 | 7 specs PW dependem dos rótulos em inglês | `RTL`, `PW` |
| `web/lib/opal/src/layouts/sidebar/styles.css` (149L) | slab `bg-background-tint-02`, `pb-2`; **sem borda, raio ou sombra**; largura 200ms | aresta é só degrau tonal; leve demais para casca operacional | ADAPT | 2 | borda de 1px na aresta interna; degrau tonal menor | `border-01`, `background-tint-02` | VIS-001 | VIS-002 | borda pode brigar com o canvas | `VIS`, `A11Y` |
| `sidebar/styles.css:145-148` | título de seção `pt-3 ps-2 pe-1` + `px-0.5 py-1.5` | rótulo 12px/400 em `text-02` (~45%) — contraste muito baixo | ADAPT | 2 | rótulo mais forte: peso 500+, `text-03`, tracking leve | `text-03`, preset `secondary-*` | VIS-001 | VIS-002 | — | `A11Y`, `VIS` |
| `web/lib/opal/src/components/buttons/sidebar-tab/components.tsx` (235L) | `Interactive.Stateful` → `Container rounding={2}` (8px inline), `size lg` (36px), `w-full`; overlay `Link`/`button` z-99 | ícone codificado `text-text-03` no ramo de children não-string @224 | ADAPT | 2 | manter mecânica; corrigir o ícone para seguir o estado | `--interactive-foreground-icon` | — | VIS-002 | ramo só ativo em renomear | `RTL`, `VIS` |
| `core/interactive/stateful/styles.css:453-583` | `empty` transparente · `hover` `tint-03` · **`selected` `tint-00`** · `disabled` opacidade 50 | **`selected:hover` volta a `tint-03`** → seleção inverte sob o cursor. **Sem célula `:active`** | ADAPT | 2 | selected = borda TON 1px + surface sutil; hover de selected mantém a seleção; adicionar `:active` | `action-selection-*`, `border-*`, `background-tint-*` | VIS-001 | VIS-002 | mudar `Interactive` afeta todo o app | `RTL`, `A11Y`, `VIS`, `PW` |
| `sidebar-tab/components.tsx:161-166` | foco = `outline-border-04 outline-offset-[-2px] focus-visible:outline-2` | funciona; inset por causa do clip | KEEP | 0 | manter | `border-04` | — | — | — | `A11Y` |
| `sidebar-tab/components.tsx:141-143` | `truncationSpacer` `w-0 group-hover:w-6` | ponto de truncamento muda ao passar o mouse | ADAPT | 2 | reservar largura fixa | — | — | VIS-002 | baixo | `VIS` |
| `web/src/sections/sidebar/AppSidebar.tsx` (690L) | composição de navegação + 5 hooks SWR + 2 `DndContext` + reorder + move + flags + overlay + footer | corpo inteiro renderiza `null` enquanto qualquer fonte carrega; `shuffleWidths` aleatório em render | ADAPT | 3 | skeleton por seção; largura determinística; **IA de FE-004 intacta** | `background-tint-04` | VIS-001 | VIS-002 | tocar o arquivo arrisca a IA congelada | `RTL` (`ton-navigation.test.tsx`), `PW` |
| `AppSidebar.tsx:118-201` (`RecentsSection`) | droppable + `IntersectionObserver`; alvo tinge `tint-03` `rounded-08` | definido inline; estado vazio usa API `Text` depreciada | ADAPT | 2 | extrair; `Text` novo; alvo de soltura com borda tracejada | `border-*`, `background-tint-03` | — | VIS-002 | extrair muda árvore de teste | `RTL`, `PW` |
| `AppSidebar.tsx:678` (`Divider`) | fronteira produto / histórico | mínimo possível com primitivo existente | ADAPT | 2 | decidir: espaçamento + rótulo em vez de linha | — | VIS-001 | VIS-002 | FE-004 pediu explicitamente esta decisão | `VIS`, `A11Y` |
| `web/src/sections/sidebar/ChatButton.tsx` (521L) | selected por URL; `nested` indenta 16px; ações em hover; typewriter 30ms/char | seleção herda o defeito de `selected:hover` | ADAPT | 2 | estado selecionado TON; resto intacto | via `Interactive` | VIS-002 | VIS-002 | 7 specs dependem de comportamento | `RTL`, `PW` |
| `web/src/lib/projects/components/ProjectFolderButton.tsx` (278L) | revela ações com `cn(!popoverOpen && "hidden", "group-hover/SidebarTab:flex")` | **sem `no-hover:opacity-100`** → menu inacessível no toque | ADAPT | 2 | usar `Hoverable` do Opal | — | — | VIS-002 | regressão de a11y de toque se errar | `RTL`, `PW` mobile |
| `web/src/sections/sidebar/AccountPopover.tsx` (286L) | trigger `SidebarTab` + avatar; `w-[16px]` arbitrário | valor arbitrário | ADAPT | 2 | usar escala de ícone | — | VIS-001 | VIS-002 | baixo | `VIS` |
| `web/src/lib/app/components.tsx:24-107` (`Logo`) | fallback `SvgOnyxLogo`/`SvgOnyxLogoTyped`; `rounded-full` no contêiner enterprise; comentário de "negative margin hack" | marca upstream é o fallback | ADAPT | 1 | ponto único de troca quando o ativo TON existir | — | **ADR-009** | VIS-002 | **bloqueado por ativo inexistente** | `VIS` |
| `web/src/layouts/chromes/AppChrome.tsx` (754L) | header 52px transparente, sem borda; **sem título de página**; 8 ações, até 5 visíveis; painel direito por slot | mistura render, rede, `localStorage`, tier e 11 `useState`; `useEffect` @260-360 monta `ReactNode` em estado | ADAPT | 3 | header com título de contexto + só ações relevantes; extrair `Header` | `border-01`, `background-tint-*` | VIS-001 | VIS-002 | arquivo grande e central | `RTL`, `PW`, `VIS` |
| `AppChrome.tsx:665-690` | vinheta `rgba(0,0,0,0.4)`; máscara com `black` literal; `blur(16px)`; `duration-600` | hex cru; efeito decorativo | ADAPT | 2 | tokenizar ou remover para o canvas TON | `mask-*` | VIS-001 | VIS-002 | fundos configuráveis são recurso enterprise | `VIS` |
| `AppChrome.tsx:690-720` | refoco imperativo por `getElementById("onyx-chat-input-textbox")` | acoplamento por string literal | KEEP | 0 | manter; documentar | — | — | — | — | — |
| `AppChrome.tsx:617-662` (`Footer`) | `pb-2` vs `py-2` compensando a sombra do composer | hack derivado de `shadow-box-01` | ADAPT | 2 | remover junto com a sombra do composer | — | VIS-004 | VIS-004 | acoplado a 3 arquivos | `VIS` |
| `web/lib/opal/src/constants.ts:7-9` | `sm` 724 · `md` 912 · `lg` 1232 | duplicata de `useScreenSize` em `web/src/hooks/` sem `isMounted` | ADAPT | 2 | unificar no hook do Opal | — | — | VIS-002 | divergência SSR | `RTL`, `PW` |

### 5.3 Home e nova conversa

| Componente / arquivo | Comportamento e fingerprint atual | Problema | Cls | Nv | Alvo TON | Tokens / primitivos | Dep. | Fatia | Risco | Val. |
|---|---|---|---|---:|---|---|---|---|---|---|
| `web/src/views/AppPage.tsx` (1095L) | grid de 3 linhas; 5 estados de `gridTemplateRows`; transição `duration-150` | um arquivo governa home + conversa | ADAPT | 3 | manter o grid; refinar linhas 1 e 3 | — | VIS-001 | VIS-003 | arquivo central do produto | `RTL`, `PW`, `VIS` |
| `AppPage.tsx:694-712` (`gridStyle`) | vazio `1fr auto 1fr` → chat `1fr auto 0fr` | mecanismo correto: composer nunca remonta | **KEEP** | 0 | preservar; é a base da transição TON | — | — | — | — | `PW` |
| `AppPage.tsx:88-108` (`Fade`) | 150ms só opacidade, `motion/react`, 5 usos | local, não exportado; sem transform | KEEP | 0 | manter; considerar deslocamento mínimo | novos `duration-*` | VIS-001 | VIS-003 | — | `VIS` |
| `web/src/app/app/components/WelcomeMessage.tsx` (99L) | `Math.random() < 0.5` entre `"How can I help?"` e `"Let's get started."`; `Logo folded size={32}`; `FrostedDiv`; `headingH2` via API `Text` depreciada | **copy genérica de IA, não determinística**; marca Onyx; vidro decorativo | **REPLACE** | 2 | entrada de domínio determinística: "O que você deseja analisar?"; sem `FrostedDiv` | presets de heading | VIS-001 | VIS-003 | compartilhado com `NRFPage` | `RTL`, `PW`, `VIS` |
| `web/src/sections/Suggestions.tsx` (54L) | lista vertical de `starter_messages`; `Interactive.Container rounding={2} size="lg"` | usa primitivo `@opal/core` direto, contra `web/AGENTS.md`; só existe se o agente tiver starters | ADAPT | 3 | ações rápidas de domínio contidas, com dado real | `border-01`, `background-tint-*` | VIS-001 | VIS-003 | — | `RTL`, `VIS` |
| `web/src/app/app/components/AgentDescription.tsx` (24L) | `Text secondaryBody text03` centralizado | API `Text` depreciada | ADAPT | 2 | `Text` novo | — | — | VIS-003 | baixo | `RTL` |
| `web/src/sections/onboarding/OnboardingFlow.tsx` (85L) | dentro da linha 2, acima do composer; `ShadowDiv mask`; passos 500ms | `aria-label="onboarding-flow"` sem i18n; 500ms fora da faixa | ADAPT | 2 | i18n; reduzir para 200ms | novos `duration-*` | VIS-001 | VIS-003 | grid já teve bug de overflow com cards largos | `RTL`, `VIS` |
| **dados para "consciência operacional"** | `chatSessions`, `userProjects`, `recentFiles`, `agents`, `notifications` (+`Summary`, `bySeverity`), `userUsage`, `promptShortcuts` | **não existe** `findings`/`occurrences`/`analysisRun`/`reports` em `web/src/lib` | — | 3 | usar só os cinco reais; `notifications` é o único feed por severidade | — | Backend 003c/003d | VIS-003 | **inventar métrica é falha de aceite** | `RTL`, revisão de produto |
| `web/src/app/nrf/NRFPage.tsx` (631L) | reusa `WelcomeMessage`; centraliza por flexbox, **sem `Fade`**; sem Suggestions/onboarding | gêmeo que dessincroniza | ADAPT | 2 | acompanhar VIS-003 | — | VIS-003 | VIS-003 | esquecer o gêmeo | `VIS` |
| `web/src/app/craft/components/BuildWelcome.tsx` (135L) | clona `"1fr auto 1fr"` codificado | gêmeo suprimido, mas vivo | IGNORE | 0 | — | — | — | — | dessincroniza silenciosamente | grep |

### 5.4 Composer

| Componente / arquivo | Comportamento e fingerprint atual | Problema | Cls | Nv | Alvo TON | Tokens / primitivos | Dep. | Fatia | Risco | Val. |
|---|---|---|---|---:|---|---|---|---|---|---|
| `web/src/hooks/useContentEditable.ts` (~870L) | `contentEditable` próprio: autosize 44↔200px, pilha undo/redo, IME, tiles, RTL, copy/cut achatado | maduro e muito especializado | **KEEP** | 0 | **não substituir o editor** | — | — | — | trocar por Lexical/TipTap é nível 5 injustificado | `RTL` |
| `web/src/sections/input/AppInputBar.tsx:827-843` | `shadow-box-01 bg-background-neutral-00 rounded-16`; **sem borda** | aresta é sombra; raio 16px alto; gerou hack de 3 arquivos | **REPLACE** (apresentação) | 2 | borda 1px + surface; raio 12px; **sem sombra** | `border-01/02`, `background-neutral-00`, `radius-12` | VIS-001 | VIS-004 | remover a sombra tira a aresta se a borda falhar | `VIS`, `A11Y`, `PW` |
| `AppInputBar.tsx:904-978` (`contentEditable`) | `outline-hidden`; sem `focus-within` no contêiner | **não há tratamento de foco no controle principal do produto** | **REPLACE** | 2 | borda de foco TON + anel interno, como `border-05` já prescreve | `border-05`, `background-tint-04` | VIS-001 | VIS-004 | — | `A11Y` obrigatório, `PW` teclado |
| `AppInputBar.tsx:612-816` (`chatControls`) | `h-11 p-1 flex justify-between`; colapsa com `inert` em busca | altura fixa; **sem wrap e sem scroll** → aperta no mobile | ADAPT | 3 | barra integrada com prioridade de overflow | — | VIS-001 | VIS-004 | esconder controle essencial no mobile | `PW` 375px |
| `AppInputBar.tsx:697-712` (Deep Research) | `SelectButton variant="select-light" icon={SvgHourglass} state=selected/empty foldable` | ampulheta é neutra; estado ativo é preenchimento de select | ADAPT | 2 | inativo neutro silencioso; ativo = contorno institucional + mudança sutil de surface. Sem neon, sem glow | `action-selection-*`, `border-*` | VIS-001 | VIS-004 | `TODO(@yuhong)` ENG-3818 pendente no gate | `VIS`, `A11Y` |
| `AppInputBar.tsx:770-811` (send/stop) | um botão, 4 ícones (`SvgSimpleLoader`/`SvgArrowUp`/`SvgStop`) | correto; `id` duplicado no DOM em busca | ADAPT | 2 | manter troca; corrigir id duplicado | — | — | VIS-004 | id duplicado é defeito de a11y | `A11Y`, `RTL` |
| `AppInputBar.tsx:1034-1058` (busca) | X + Search inline; segundo `id="onyx-chat-input-send-button"` | duplicata real | ADAPT | 2 | id único | — | — | VIS-004 | — | `RTL` |
| `AppInputBar.tsx:869-891` (faixa de anexos) | altura medida em JS (`PADDING = 8`) | funcional | KEEP | 0 | manter mecanismo | — | — | VIS-005 | — | `VIS` |
| `web/src/hooks/useDraft.ts` | `sessionStorage`, `onyx:draft:chat:<id>`, debounce 300ms | maduro | KEEP | 0 | — | — | — | — | — | `RTL` |
| `web/src/app/css/content-editable.css:2-14` | placeholder por `::before` com `attr(data-placeholder)` | elegante | KEEP | 0 | — | `text-03` | — | — | — | `VIS` |
| `content-editable.css:18-77` (tiles) | `radius-08`, anel `inset 0 0 0 1.5px action-selection-02`, preview 14rem | correto e já TON | KEEP | 0 | — | `action-selection-02` | — | — | — | `VIS` |
| `web/src/sections/model-selector/MultiModelSelector.tsx` | **fora** do composer: `AppPage.tsx:987-999` (chat) e `:908-920` (home) | dois lugares, duas aparências | ADAPT | 3 | posição única e contida | — | VIS-001 | VIS-004 | mover afeta os dois estados | `VIS`, `PW` |
| `web/src/sections/input/BaseInputBar.tsx:283-286` | gêmeo Craft, `rounded-t-16` | precisa acompanhar | ADAPT | 2 | acompanhar VIS-004 | idem | VIS-004 | VIS-004 | esquecer o gêmeo | `BUILD`, `VIS` |
| `web/src/sections/input/SharedAppInputBar.tsx:20-51` | composer falso; overlay `backdrop-blur-xs bg-background-neutral-00/50`; `"GPT-4o"` e `SvgOpenai` codificados | vidro decorativo; literal de modelo | ADAPT | 2 | estado desabilitado sóbrio | — | VIS-004 | VIS-004 | superfície pública de chat compartilhado | `VIS` |

### 5.5 Mensagens, streaming, ferramentas e citações

| Componente / arquivo | Comportamento e fingerprint atual | Problema | Cls | Nv | Alvo TON | Tokens / primitivos | Dep. | Fatia | Risco | Val. |
|---|---|---|---|---:|---|---|---|---|---|---|
| `web/src/sections/chat/ChatUI.tsx` | `gap-12`, `pt-4 pb-8`; `MSG_MAX_W` codificado `md:max-w-[720px]` | largura codificada; três constantes concorrentes | ADAPT | 2 | largura de leitura tokenizada única | novo token de largura | VIS-001 | VIS-006 | mudar largura muda todo o transcript | `VIS`, `PW` |
| `web/src/app/app/message/HumanMessage.tsx:224-226` | **única bolha**: `rounded-t-16 rounded-es-16 bg-background-tint-02 py-2 px-3`, cauda assimétrica | bolha sem função semântica; 16px | **REPLACE** | 2 | alinhamento + surface sutil + raio menor; sem cauda | `background-tint-02`, `radius-08/12` | VIS-001 | VIS-006 | usuários esperam distinguir seu texto | `VIS`, `A11Y` |
| `HumanMessage.tsx:51-55` (edição) | `border rounded-16` com `border` sem token | raio e borda sem token | ADAPT | 2 | borda tokenizada, raio 12px | `border-01` | VIS-001 | VIS-006 | baixo | `VIS` |
| `AgentMessage.tsx:285-315` | **sem bolha**: `flex flex-col gap-3`, conteúdo `px-3` | já minimal; correto | KEEP | 0 | manter | — | — | — | — | `VIS` |
| `MessageTextRenderer.tsx:494` | `prose prose-onyx font-main-content-body`; `rehype-highlight` diferido | nome de classe com marca | ADAPT | 1 | renomear para `prose-ton` | — | — | VIS-006 | classe usada em 1 lugar | `BUILD`, `VIS` |
| `custom-code-styles.css:30-49` (`.prose-onyx`) | `--tw-prose-headings` == `--tw-prose-body` == `text-04`; `h1..h6` e `blockquote` sem override | **títulos sem diferenciação de cor** — hierarquia tipográfica subutilizada | ADAPT | 2 | escada de heading real: cor, peso e espaçamento | `text-04/05`, presets | VIS-001 | VIS-006 | — | `VIS`, `A11Y` |
| `markdownUtils.tsx:239` | `prose dark:prose-invert` | **modificador `dark:` proibido**; segunda estratégia de tema | **REPLACE** | 2 | usar `prose-ton` nos dois pipelines | — | — | VIS-006 | dois pipelines divergem | `BUILD`, `VIS` |
| `custom-code-styles.css:51-215` | ~130 linhas de hex Atom One + `!important` em `.hljs` | paleta upstream fora do sistema | **REPLACE** | 2 | tema de sintaxe TON por token | novos `code-*` | VIS-001 | VIS-006 | legibilidade de código nos dois temas | `A11Y`, `VIS` |
| `custom-code-styles.css:223-303` | cinzas de scrollbar + `box-shadow: 0 0 10px #6b7280` | hex cru + glow | **REPLACE** | 2 | tokens de scrollbar; sem glow | `scrollbar-*` | VIS-001 | VIS-006 | baixo | `VIS` |
| `CodeBlock.tsx:138-160` | `bg-background-tint-00 rounded-12`, sem borda; raio interno concêntrico | raio concêntrico é bom | ADAPT | 2 | adicionar borda 1px; manter concêntrico | `border-01` | VIS-001 | VIS-006 | — | `VIS` |
| `CodeBlock.tsx:45-68` | botão de copiar à mão, `"Copied!"` 2000ms | ignora `CopyButton` do Opal | ADAPT | 2 | usar `CopyButton` | — | — | VIS-006 | — | `RTL`, `VIS` |
| `markdownUtils.tsx:35-103` (`ScrollableTable`) | células `whitespace-nowrap`; `ResizeObserver`; fade de borda | tabelas nunca quebram; ok para dados | KEEP | 0 | manter; densificar | `border-01/02` | VIS-001 | VIS-006 | — | `VIS` |
| `custom-code-styles.css:305-380` | `.markdown-table-card` `background-neutral-01`, raio 0.5rem, sem borda de célula | grade vem das variáveis prose | ADAPT | 2 | grade explícita e contida | `border-01/02` | VIS-001 | VIS-006 | — | `VIS` |
| `ShimmerText.tsx` + `globals.css:260-347` | clone mascarado; `shimmer-slide 1s infinito`; fallback Firefox; reduced-motion ok | brilho contínuo decorativo; único indicador de streaming | **REPLACE** | 3 | indicador de atividade operacional discreto, sem varredura contínua | `shimmer-*` → novos | VIS-001 | VIS-006 | é o sinal de "está trabalhando" | `A11Y`, `VIS` |
| `BlinkingBar.tsx` | `animate-pulse bg-theme-primary-05 w-2 h-4`, injetado por `" [*]() "` no markdown | hack de injeção; pulso 2s | ADAPT | 2 | cursor mais discreto; manter mecanismo | `theme-primary-05` | — | VIS-006 | mexer no markdown quebra render | `RTL`, `VIS` |
| `AgentTimeline.tsx:371-401` | header `rounded-t-12`, `transition-colors duration-300`, `animate-in slide-in-from-top-2` | 300ms acima da faixa | REDUCE | 2 | 200ms; entrada mais curta | novos `duration-*` | VIS-001 | VIS-006 | — | `VIS` |
| `timeline/primitives/tokens.ts:34-52` | `--timeline-*` (rail 2.25rem, iconSize 0.75rem…) | sistema local próprio, bem feito | KEEP | 0 | alinhar valores ao sistema global | — | VIS-001 | VIS-006 | — | `VIS` |
| `useTimelineHeader.ts` + `en.json` | `"Thinking..."`, `"Reading"`, `"Searching the web"`, `"Executing {toolName}"`… | vocabulário de raciocínio, não de operação | **REPLACE** | 2 | rótulos operacionais PT-BR: "Consultando fontes…", "Validando competência…", "Analisando contrato…" | — | Backend 003b/003c para lastrear | VIS-006 | rótulo sem processo real é decorativo | `RTL`, revisão de produto |
| **`ReasoningRenderer.tsx:85`, `:182-190`** | concatena `REASONING_DELTA` verbatim; `ExpandableTextDisplay` com modal "Full text" + download `.txt`; `THINKING_MIN_DURATION_MS = 500` artificial | **expõe chain-of-thought** — conflito direto com a direção TON | **REPLACE** | 3 | não expor raciocínio; substituir por atividade observável | — | VIS-006 | VIS-006 | remover pode esvaziar o timeline se não houver substituto | `RTL`, revisão de produto |
| `CompletedHeader.tsx:167-218` | `"Thought for {duration}"`, `"{count} steps"`; `role="button"` envolvendo `Button` real | vocabulário de raciocínio; interativo aninhado | ADAPT | 2 | "Concluído em {duração}" + "{n} etapas"; corrigir o aninhamento | — | — | VIS-006 | — | `A11Y`, `RTL` |
| `CustomToolRenderer.tsx:118-145` | status `"{toolName} running..."` etc.; ícone **sempre** `SvgActions` | sem ícone por estado | ADAPT | 2 | ícone e cor por estado: executando / concluído / falhou | `status-*` | VIS-001 | VIS-006 | — | `VIS` |
| `CustomToolRenderer.tsx:162-183` | três pontos `animate-pulse` com delays 0.1/0.2s | pulso de 2s torna os delays imperceptíveis; feito à mão | **REPLACE** | 2 | primitivo TON de execução | — | VIS-009 | VIS-006 | — | `VIS` |
| `CustomToolRenderer.tsx:185-263` | `IoBlockLabel` "Request"/"Response" + JSON bruto por padrão | JSON cru como apresentação padrão | ADAPT | 3 | nome da operação + estado + evidência; detalhe técnico recolhido | — | — | VIS-006 | admin pode precisar do JSON | `RTL`, `VIS` |
| `CodingAgentRenderer.tsx:146` | `stepIcon={SvgSparkle}` | faísca de IA genérica | **REPLACE** | 2 | ícone de operação | — | — | VIS-006 | — | `VIS` |
| `SourceTag.tsx:29-41` | `inlineCitation rounded-04` · `tag rounded-08` · `button rounded-08 h-9` | **não são pílulas**; geometria já contida | KEEP | 0 | manter; ajustar cor | `background-tint-02` | VIS-001 | VIS-006 | — | `VIS` |
| `SourceTag.tsx:158-182` (`IconStack`) | até 3 ícones de conector com `-space-x-1.5` e borda que inverte | ícones de conector upstream são identidade de terceiro, não Onyx | KEEP | 0 | manter | — | — | — | — | `VIS` |
| `MemoizedTextComponents.tsx:90-95` | citação não resolvida renderiza `<></>` | correto durante streaming | KEEP | 0 | — | — | — | — | — | `RTL` |
| `MessageToolbar.tsx:258-261` | **sempre visível** (`opacity-100`); classes `transition-transform` inertes | ruído em repouso; classes mortas | ADAPT | 2 | revelar no hover/foco com `Hoverable`; remover classes inertes | — | — | VIS-006 | esconder ação reduz descoberta | `A11Y`, `PW` |
| `HumanMessage.tsx:200-204` | `Hoverable.Item variant="appear-on-hover"`; no mobile fica permanente | padrão correto | KEEP | 0 | — | — | — | — | — | `PW` mobile |
| `Resubmit.tsx:123-249` | `text-red-700`, `text-neutral-700 dark:text-neutral-300`, `bg-neutral-100 dark:bg-neutral-800`; legado `@/components/ui/alert` | **paleta bruta + `dark:` proibido**; 6 cores cruas no `<pre>` | **REPLACE** | 2 | erro tokenizado com ícone + copy, sem depender de cor | `status-error-*`, `action-danger-*` | VIS-001 | VIS-006 | — | `BUILD`, `A11Y`, `VIS` |
| `Resubmit.tsx:62-131` (`RateLimitBanner`) | contagem 1s; `toLocaleDateString` direto | ignora `useFormatter` do next-intl | ADAPT | 0 | usar `useFormatter` | — | — | VIS-006 | baixo | `RTL` |
| `thinkingBox/ThinkingBox.css` | 371 linhas, **zero importadores**; `box-shadow`, `text-shadow`, `perspective`, `.dark`, hex cru | código morto com a linguagem visual antiga | **REPLACE** (excluir) | 0 | excluir | — | — | VIS-010 | nenhum | grep, `BUILD` |

### 5.6 Anexos, arquivos e arrastar/soltar

| Componente / arquivo | Comportamento e fingerprint atual | Problema | Cls | Nv | Alvo TON | Tokens / primitivos | Dep. | Fatia | Risco | Val. |
|---|---|---|---|---:|---|---|---|---|---|---|
| `web/src/lib/projects/svc.ts:34-65` | `POST /api/user/projects/file/upload` com `FormData` (`files`, `project_id`, `incognito_session_id`, `temp_id_map`) | erro em inglês codificado @11-13 | **KEEP** (infra) | 0 | preservar transporte; i18n do erro | — | — | VIS-005 | — | `RTL` |
| `web/src/lib/projects/providers.tsx` | `temp_<uuid>`; insert otimista em 3 listas; reconciliação por `temp_id`; precheck de tamanho; rollback; **polling de 3s** | maduro; sem % de bytes, sem retry, sem cancelamento | **KEEP** | 0 | **preservar a máquina de estados**; só apresentação muda | — | — | VIS-005 | mexer aqui quebra upload | `RTL` |
| `providers.tsx` (polling) | arquivo `failed` é **removido** de `currentMessageFiles` | **o composer nunca mostra anexo com erro** | ADAPT | 3 | manter o arquivo visível em estado de erro, com remoção explícita | `status-error-*` | — | VIS-005 | manter arquivo falho pode confundir envio | `RTL`, `VIS` |
| `providers.tsx:65-86` | `createOptimisticFile` fixa `chat_file_type: DOCUMENT` | tipo semântico não confiável no cliente | ADAPT | 2 | derivar categoria de `name` + `file_type` | — | — | VIS-005 | — | `RTL` |
| `web/src/lib/utils.ts:127-186` | só `IMAGE_EXTENSIONS` + `isImageFile` | **não existe enum de categoria**; mapeamento de ícone duplicado em 4 lugares | ADAPT | 3 | um `fileCategory(name, mime)` compartilhado: planilha, documento, imagem, apresentação, áudio, vídeo, arquivo compactado, outro | `status-*`, `theme-*` | — | VIS-005 | **nenhum backend necessário** | `RTL`, `VIS` |
| `PreviewModal/variants/xlsxVariant.tsx:11-23` | `SPREADSHEET_MIME_TYPES` já existe | conhecimento de MIME já presente e não reaproveitado | KEEP | 0 | semear a categorização com esta lista | — | — | VIS-005 | — | `RTL` |
| `web/src/sections/cards/FileCard.tsx:158-230` | cartão-linha `max-w-48` + `Interactive.Container border` + `AttachmentItemButton` | uma de **três** geometrias de anexo | ADAPT | 2 | geometria única com identidade semântica | `border-01`, `radius-08` | VIS-001 | VIS-005 | — | `VIS` |
| `FileCard.tsx:97-150` (`ImageFileCard`) | `h-20 w-20` / `h-11 w-11`, `rounded-08 border-border-01` | segunda geometria; sem preview local durante upload | ADAPT | 2 | preview compacto coerente | `border-01` | VIS-001 | VIS-005 | — | `VIS` |
| `FileCard.tsx:18-61` (`Removable`) | badge `-start-2 -top-2 h-4 w-4 rounded-04 shadow-xs`; só após upload | sombra; não permite cancelar | ADAPT | 2 | remoção sem sombra; permitir cancelar quando houver suporte | `border-01` | VIS-001 | VIS-005 | cancelar exige `AbortController` novo | `A11Y`, `VIS` |
| `web/src/sections/input/InputChipStrip.tsx:27-100` | **pílula real**: `px-1 py-px rounded-08 border`, `max-w-[120px]`; tem estado de erro | terceira geometria; só Craft | ADAPT | 2 | convergir com a geometria única | `status-error-02`, `border-01` | VIS-005 | VIS-005 | — | `VIS` |
| `AppPage.tsx:778-786` (`Dropzone`) | envolve **todo o viewport do chat**; só desestrutura `getRootProps` | **`isDragActive` nunca é lido** → zero affordance no maior alvo | **REPLACE** | 2 | overlay TON: borda tracejada + véu neutro + "Solte os arquivos aqui" | `border-*`, `mask-*` | VIS-001 | VIS-005 | **manter `noClick` e `noPaste`** | `RTL` (`dropzonePaste.test.tsx`), `PW` |
| `web/src/sections/input/__tests__/dropzonePaste.test.tsx` | afirma em nível de fonte que todo dropzone de composer passa `noPaste` | portão real | KEEP | 0 | respeitar | — | — | VIS-005 | remover `noPaste` duplica anexo | `RTL` |
| `ProjectContextPanel.tsx:246-268` | **único** drag-over do app: `border-2 border-dashed border-action-selection-05` | é o protótipo correto; estado vazio é barra à mão | ADAPT | 2 | promover o padrão; usar `IllustrationContent` no vazio | `action-selection-05`, `border-*` | VIS-001 | VIS-005 | — | `VIS` |
| `FilePickerPopover.tsx` | `LineItemButton rounding={2}` + `Hoverable replace-on-hover`; `"PLAINTEXT"` para `.txt`; API `Text` depreciada | look de picker upstream | ADAPT | 2 | linhas com identidade semântica de arquivo | `border-01` | VIS-005 | VIS-005 | — | `VIS` |
| `UserFilesModal.tsx` | lista filtrável com `AttachmentItemButton` + `timeAgo` | funcional | ADAPT | 2 | densidade operacional | — | VIS-001 | VIS-005 | — | `VIS` |
| `AgentEditorPage.tsx:1160-1240` | segundo consumidor de `temp_` | contrato interno | KEEP | 0 | **não mudar o prefixo** | — | — | — | — | `RTL` |
| `web/src/app/craft/contexts/UploadFilesContext.tsx` | segunda pilha de upload; limites 50MB/200MB/20; `classifyError` | duplicação, mas superfície suprimida | IGNORE | 0 | — | — | — | — | — | — |

### 5.7 Especialistas e identidade de runtime

| Componente / arquivo | Comportamento e fingerprint atual | Problema | Cls | Nv | Alvo TON | Tokens / primitivos | Dep. | Fatia | Risco | Val. |
|---|---|---|---|---:|---|---|---|---|---|---|
| `web/src/refresh-components/avatars/CustomAgentAvatar.tsx:76-85` | `SvgOctagonWrapper` = **octógono Onyx como moldura de todo avatar** | impressão digital mais grave do produto | **REPLACE** | 4 | sistema TON de identidade: caixa única, traço consistente, escala de ícone, acento semântico | novos tokens de acento | VIS-001 | **VIS-007** | 10 pontos de render + espelho mobile | `RTL`, `VIS`, `PW` |
| `CustomAgentAvatar.tsx:103-156` | cadeia: imagem → **círculo**; ícone → **octógono**; letra → **octógono**; fallback → **octógono** | **três formas diferentes** para a mesma entidade | **REPLACE** | 4 | uma forma para todos os estados | — | VIS-001 | VIS-007 | — | `RTL`, `VIS` |
| `CustomAgentAvatar.tsx:37-69` (`agentAvatarIconMap`) | 18 entradas fixas; cor por `stroke-*`; moldura sempre `stroke-text-04` | anel cinza em volta de glifo colorido; 4 entradas usam `theme-green-05` = **verde Onyx** | **REPLACE** | 3 | paleta de acento TON; moldura coerente com o acento | `theme-primary-*`, `theme-amber-*` | VIS-001 | VIS-007 | 18 ícones existentes viram outra coisa | `RTL`, `VIS` |
| `CustomAgentAvatar.tsx:134-147` | letra só se `/^[a-zA-Z]$/` | dígito, emoji e CJK caem no fallback genérico | ADAPT | 3 | fallback que aceita qualquer inicial | — | — | VIS-007 | — | `RTL` |
| `web/src/refresh-components/avatars/AgentAvatar.tsx:25-42` | agente padrão: logo enterprise em círculo, **ou `SvgOnyxLogo` sem moldura** | marca upstream como avatar do agente central | **REPLACE** | 3 | identidade "TON Central" na mesma caixa dos demais | — | ADR-009 | VIS-007 | ativo TON ainda não existe | `RTL`, `VIS` |
| `web/src/sections/agents/AgentCard.tsx:77-82` | `Card` **depreciado** + `radial-00` (gradiente) + `hover:shadow-box-00`; header `h-24` fixo; footer `bg-background-tint-01` | gradiente e sombra decorativos; cartão pesado; **sem estado selecionado** | **REPLACE** | 3 | linha ou cartão sóbrio: borda 1px, sem gradiente, sem sombra, com estado selecionado | `border-01/02`, `background-tint-*` | VIS-001 | VIS-007 | `Card` depreciado bloqueado por este uso | `VIS`, `A11Y` |
| `AgentCard.tsx:144` | `title={agent.owner?.email \|\| "Onyx"}` | marca upstream visível | **REPLACE** | 0 | fallback neutro i18n | — | — | VIS-007 | — | `RTL` |
| `web/src/views/AgentsNavigationPage.tsx:45` | grid `grid-cols-1 md:grid-cols-2 gap-2` | grade de cartões sem propósito claro | ADAPT | 3 | lista densa com agrupamento | `border-01` | VIS-001 | VIS-007 | — | `VIS`, `PW` |
| `AgentsNavigationPage.tsx:167-175` | estado vazio é `<Text>` centralizado | ignora `IllustrationContent` | ADAPT | 2 | usar o padrão do sistema | — | — | VIS-007 | — | `RTL`, `VIS` |
| `AgentEditorPage.tsx:233-282` | `InputAvatar h-30 w-30`; 19 `SquareButton` size 30; seleção via `transient` | seleção sem sinal explícito | ADAPT | 2 | seleção com borda + marca | `action-selection-*`, `border-*` | VIS-001 | VIS-007 | — | `A11Y`, `VIS` |
| `Suggestions.tsx` vs `AgentViewerModal.tsx:425-453` vs `AgentEditorPage.tsx:462` | **três geometrias** de starter message: linhas full-width · grid 2 colunas com ícone · campos de form | inconsistência entre superfícies da mesma entidade | ADAPT | 3 | uma geometria | — | VIS-001 | VIS-007 | — | `VIS` |
| `PersonaMessagesChart.tsx:54`, `:78` | octógono no seletor e nas linhas | superfície admin | ADAPT | 2 | acompanhar VIS-007 | — | VIS-007 | VIS-007 | — | `VIS` |
| `mobile/src/**` (octógono + strings) | espelho React Native | fora de `web/` | IGNORE | 0 | registrar para trilha mobile | — | — | — | dessincroniza | — |

### 5.8 Carregamento, vazios e superfícies de suporte

| Componente / arquivo | Comportamento e fingerprint atual | Problema | Cls | Nv | Alvo TON | Tokens / primitivos | Dep. | Fatia | Risco | Val. |
|---|---|---|---|---:|---|---|---|---|---|---|
| `web/lib/opal/src/components/loader/styles.css` (91L) | **`OnyxLoader`**: 2000ms, rotação 360° com crossfade octógono ↔ quatro diamantes, hold de 200ms; reduced-motion @78-90 | **a marca Onyx se desenha na tela duas vezes por ciclo** | **REPLACE** | 4 | primitivo de carregamento TON, sóbrio e curto | — | ADR-009 | **VIS-009** | usar logo TON exige o ativo | `A11Y`, `VIS` |
| `loader/components.tsx:96-115` | `OUTLINE_PATH` e `MARK_PATHS` **duplicam** a geometria dos ícones, por decisão comentada | trocar os ícones **dessincroniza o loader em silêncio** | **REPLACE** | 4 | fonte única de geometria | — | VIS-007 | VIS-009 | armadilha real de implementação | `VIS`, grep |
| `loader/components.tsx:64-77` (`IconLoader`) | `motion-safe:animate-spin`, 24px | correto | KEEP | 0 | — | `border-02` | — | — | — | `A11Y` |
| `web/lib/opal/src/icons/simple-loader.tsx` (`SvgSimpleLoader`) | `animate-spin` **puro**, sem `motion-safe:` | gira sob `prefers-reduced-motion`; é o spinner mais usado | ADAPT | 1 | `motion-safe:` | — | — | VIS-009 | — | `A11Y` |
| `PageLoader` | `OnyxLoader` 64px + `strings.loadingPage` | herda F10 | ADAPT | 2 | acompanhar VIS-009 | — | VIS-009 | VIS-009 | — | `VIS` |
| 8 skeletons (`SidebarTabSkeleton`, `ChatSessionSkeleton`, `ActionCardSkeleton`, `ToolItemSkeleton`, `LLMProviderSkeleton`, `ConnectorStaggeredSkeleton`, `UsageReports:71`, `ModelPickerButton`) | todos `animate-pulse`; tokens divergentes (`tint-04` / `tint-02` / `neutral-01`); raios divergentes (08/12/16); **só `ActionCardSkeleton` tem `role="status"`**; **só `UsageReports` usa `motion-safe:`** | inconsistência sistemática | ADAPT | 3 | um primitivo de skeleton: um token, um raio, `role="status"`, `motion-safe:` | `background-tint-*`, `radius-*` | VIS-001 | VIS-009 | 8 arquivos | `A11Y`, `RTL`, `VIS` |
| `IllustrationContent` + 18 ilustrações | genéricas: `no-result`, `not-found`, `no-access`, `un-plugged`… | **nenhuma ilustração de IA/robô/faísca** | KEEP | 0 | manter; usar onde falta | — | — | — | — | `VIS` |
| ~20 estados vazios | copy via `t(...)`, i18n limpo | dois desvios: `/app/agents` e arquivos de projeto | ADAPT | 2 | padronizar em `IllustrationContent`; copy de domínio | — | — | VIS-010 | — | `RTL`, `VIS` |
| `Waveform.tsx:130-171` (`"speaking"`) | 28 barras `animate-waveform` 0.8s, `bg-theme-blue-05`, `rounded-16 shadow-box-01` | resposta falada é fora do produto TON; azul fora da paleta | **REPLACE** (remover) | 2 | remover com o TTS | — | VIS-008 | VIS-008 | ver §8 sobre acoplamentos | `RTL`, `VIS` |
| `Waveform.tsx:174-206` (`"recording"`) | 120 barras por RMS real, timer mm:ss, `rounded-12` | é ditado legítimo e informativo | ADAPT | 2 | manter, sóbrio; strings em i18n | `text-03`, `border-01` | VIS-008 | VIS-008 | RMS vem do recorder atual | `VIS`, `A11Y` |
| `MicrophoneButton.tsx:315` | `prominence = isRecording ? "primary" : "tertiary"` | único sinal de gravação no botão | KEEP | 0 | manter | — | — | VIS-008 | — | `VIS` |
| `TTSButton.tsx` + `MessageToolbar.tsx:323-329` | botão de ler em voz alta, gated por `ttsEnabled` | conversa falada fora do produto | **REPLACE** (remover) | 2 | remover do toolbar | — | VIS-008 | VIS-008 | folha; seguro | `RTL` |
| `SettingsPage.tsx:1656-1681` | `<input type="range">` **cru** para velocidade de playback | viola a regra de inputs; e é config de TTS | **REPLACE** (remover) | 2 | remover com o TTS | — | VIS-008 | VIS-008 | — | `RTL` |
| `admin/VoicePage` (336L) + `shared.tsx` (468L) | separa modelos STT de grupos TTS | já separado, corte limpo | ADAPT | 3 | ocultar metade TTS | — | VIS-008 | VIS-008 | `stt-only.spec.ts` já cobre | `PW` |
| `admin/*` (tabelas, formulários, `SettingsLayouts`) | Opal consistente | densidade upstream; fora do caminho do cliente | ADAPT | 2 | densidade operacional onde o admin do cliente entra | `border-*` | VIS-001 | VIS-010 | escopo pode explodir | `VIS` |
| `AuthFlowContainer.tsx:38` | `SvgOnyxLogo size={44} className="text-theme-primary-05"` | marca upstream na primeira tela do produto | ADAPT | 1 | ponto de troca do logo TON | `theme-primary-05` | ADR-009 | VIS-002 | **bloqueado por ativo** | `VIS` |
| `web/src/app/craft/**` | `IntroBackground` com `#000000`/`#FFFFFF`; partículas; vídeo | superfície suprimida por FE-003 | IGNORE | 0 | — | — | — | — | — | — |

---

## 6. Mapa de componentes — quem é dono de quê

Ordem de autoridade de `web/AGENTS.md`: `web/lib/opal/src/` → `web/src/refresh-components/` →
`web/src/sections/` e `web/src/layouts/`. `web/src/components/` é legado.

| Domínio visual | Dono | Nível de camada |
|---|---|---|
| Tokens (cor, raio, sombra, tipo, spacing, blur) | `web/lib/shared/tokens/*.json` | fonte de verdade |
| Mapeamento token → utilitário | `web/lib/opal/tailwind-preset.cjs` | biblioteca |
| Máquina de estados de interação | `web/lib/opal/src/core/interactive/**` | biblioteca |
| Moldura de viewport e slots | `web/lib/opal/src/layouts/root/**` | biblioteca |
| Casca da sidebar (visual completo) | `web/lib/opal/src/layouts/sidebar/**` | biblioteca |
| Linha de navegação | `web/lib/opal/src/components/buttons/sidebar-tab/**` | biblioteca |
| Carregamento e vazio | `web/lib/opal/src/components/loader/**`, `layouts/illustration-content/**`, `illustrations/**` | biblioteca |
| Navegação autenticada (composição) | `web/src/sections/sidebar/AppSidebar.tsx` | produto |
| Header, canvas, painel direito, footer | `web/src/layouts/chromes/AppChrome.tsx` | produto |
| Home + conversa (grid) | `web/src/views/AppPage.tsx` | produto |
| Composer | `web/src/sections/input/AppInputBar.tsx` + `useContentEditable.ts` | produto |
| Transcript | `web/src/sections/chat/ChatUI.tsx` | produto |
| Mensagens, markdown, timeline, ferramentas | `web/src/app/app/message/**` | produto |
| Anexos e upload | `web/src/lib/projects/**` + `web/src/sections/cards/FileCard.tsx` | produto |
| Identidade de especialista | `web/src/refresh-components/avatars/**` + `web/src/sections/agents/**` | produto |
| Voz | `web/src/providers/VoiceModeProvider.tsx`, `web/src/hooks/useVoiceRecorder.ts`, `web/src/components/voice/Waveform.tsx` | produto |
| Estilo global e resíduos | `web/src/app/globals.css`, `web/src/app/css/**`, `web/src/app/app/message/custom-code-styles.css` | produto |

**Gêmeos que dessincronizam.** Alterar o composer exige tocar `AppInputBar`,
`BaseInputBar` e `SharedAppInputBar`. Alterar a home exige tocar `AppPage`,
`NRFPage` e (se reativado) `BuildWelcome`. Alterar os ícones de marca exige
tocar `onyx-octagon.tsx`, `onyx-logo.tsx` **e** as constantes duplicadas em
`loader/components.tsx`.

---

## 7. Achados responsivos

Breakpoints (`web/lib/opal/src/constants.ts:7-9`): `sm` 724 · `md` 912 · `lg`
1232. `tailwind.config.js` acrescenta `2xl` 1420 · `3xl` 1700 · `4xl` 2000.
FE-004 congelou o comportamento da sidebar nesses limites.

A casca responsiva é **madura e deve ser preservada**: três ramos de layout
(overlay mobile, overlay small com spacer de 52px, coluna desktop), backdrop que
recolhe ao toque, atalho Cmd/Ctrl+E, e o header que não rola.

Problemas concretos:

| # | Problema | Local | Fatia |
|---:|---|---|---|
| R1 | **Barra do composer não quebra nem rola.** `h-11 flex justify-between` fixo. Com anexar + ferramentas + Deep Research + chip de ferramenta forçada + microfone + enviar, os grupos se apertam em telas estreitas. Só Deep Research tem `foldable`, e só quando inativo | `AppInputBar.tsx:612-623` | VIS-004 |
| R2 | A largura de leitura de 45rem é `md:` apenas; abaixo de 768px o composer é de borda a borda | `AppPage.tsx:937` | VIS-004 |
| R3 | Menu de projeto **inacessível no toque** (sem `no-hover:`) | `ProjectFolderButton.tsx:232-237` | VIS-002 |
| R4 | `MSG_MAX_W` tem `md:min-w-[400px]`: em janelas estreitas de desktop o transcript pode empurrar | `ChatUI.tsx:28-31` | VIS-006 |
| R5 | Tabelas de markdown nunca quebram (todas as células `whitespace-nowrap`) e rolam; no mobile é a única opção viável, mas o fade de borda é o único indício | `markdownUtils.tsx:82-102` | VIS-006 |
| R6 | Anexos usam `flex-wrap` sem limite de linhas: muitos arquivos crescem a faixa indefinidamente | `AppInputBar.tsx:869-891` | VIS-005 |
| R7 | `AgentCard` tem header `h-24` fixo: descrições longas truncam igual em toda largura | `AgentCard.tsx:83` | VIS-007 |
| R8 | Grade de especialistas salta de 1 para 2 colunas em `md` e para aí | `AgentsNavigationPage.tsx:45` | VIS-007 |
| R9 | `NRFPage` centraliza por flexbox, sem o grid nem o `Fade`: comportamento diferente do `/app` | `NRFPage.tsx:437-465`, `:510` | VIS-003 |
| R10 | Duas cópias de `useScreenSize`; a do app não tem `isMounted`, a do Opal tem | `web/src/hooks/useScreenSize.ts` vs `web/lib/opal/src/hooks/useScreenSize.ts` | VIS-002 |
| R11 | `MessageToolbar` sempre visível soma altura por mensagem no mobile | `MessageToolbar.tsx:258-261` | VIS-006 |
| R12 | Painel direito de documentos é `w-100` fixo com transição de 300ms; no mobile vira modal (correto) | `AppPage.tsx:748-760` | VIS-006 |

---

## 8. Achados de tema claro e escuro

### 8.1 Claro

Canvas `background-tint-01` = `tint-02` = `#f8f9f8` — off-white com leve viés
verde. Alinhado à direção TON.

Superfícies: `tint-00` `#ffffff` · `tint-01` `#f8f9f8` · `tint-02` `#eff2f0` ·
`tint-03` `#e3e7e4` · `tint-04` `#cbd0cd`. Escada utilizável.

Divergências da direção:

1. **Bordas claras ainda são cinzas upstream** (`border-01` = `grey-10`
   `#e6e6e6`), enquanto as escuras já foram rebrandadas. Assimetria.
2. `theme-primary-05` = `#145c42` é escuro; funciona como preenchimento com
   texto claro, e como texto sobre superfície clara. Papel duplo aceitável, mas
   precisa ficar documentado.
3. `ton-theme.test.ts:279-324` **fixa o tema claro em referências exatas de
   primitivo**. Qualquer ajuste claro em VIS-001 falha o teste até ser
   atualizado no mesmo commit. Isso é intencional e bom.
4. Elevação: no claro as sombras são preto com 5/10/20% — discretas. O problema
   não é a cor, é o uso (aresta em vez de elevação).

### 8.2 Escuro

FE-002.1 fez um trabalho medido e correto **dentro da premissa que adotou**. A
escada tem ≥1.15 de contraste por passo, nenhuma superfície usa preto puro, e as
razões estão fixadas em teste (`ton-theme.test.ts:170-277`).

A escada escura atual:

| Token | Papel | Valor |
|---|---|---|
| `background-neutral-00` | campo de input / composer | `#0b1410` |
| `background-tint-00` | cartão, item selecionado | `#18231d` |
| `background-tint-01` | **canvas da aplicação** | `#27332c` |
| `background-tint-02` | sidebar, hover geral | `#344139` |
| `background-tint-03` | superfície elevada, hover de nav | `#414f47` |
| `background-tint-04` | anel interno de foco | `#56655d` |

**A divergência.** Todos esses valores são `vale-norte-neutral-*`, que são
neutros **esverdeados**. `#27332c` no canvas é um carvão verde. A direção TON
declarada agora pede:

```text
canvas:   quase-preto / carvão neutro
surface:  cinza neutro escuro
border:   cinza neutro
text:     off-white
verde:    foco / ativo / identidade
dourado:  atenção semântica específica
```

Ou seja: **escuro neutro, não escuro verde**. Isso não é erro de FE-002.1 — é
mudança de direção posterior. VIS-001 é dona da decisão, e ela tem custo real:
reabre as razões de contraste já aprovadas e obriga a reexecutar `A11Y` na
escada inteira.

Outros achados escuros:

1. **Sombras escuras são brilhos brancos.** `shadow-01` = `#ffffff0d`, `-02` =
   `#ffffff1a`, `-03` = `#ffffff33`. Com 24px de blur, `shadow-box-02` lê como
   halo. Migrar para borda + surface resolve isso de graça.
2. **`action-selection-*` não é monotônica no escuro** (ver §3.2). Documentar ou
   corrigir.
3. `theme-primary-*` **inverte** no escuro (verdes claros), então o mesmo token
   é preenchimento no claro e primeiro plano no escuro. Está afirmado em
   `ton-theme.test.ts:150-160` — é intencional, e precisa continuar documentado.
4. `mask-02` e `mask-03` têm **valores idênticos** nos dois temas
   (`alpha-grey-100-20` / `-40`), então o backdrop de modal não se adapta.
5. `.dark .hljs` carrega Atom One Dark em hex cru (P1).
6. `Resubmit.tsx` usa `dark:` proibido em três linhas (P3).
7. `markdownUtils.tsx:239` usa `dark:prose-invert` (P4).

---

## 9. Achados de acessibilidade

Estes são os que uma mudança visual pode **piorar** se ignorados, e os que ela
deve corrigir.

| # | Achado | Local | Severidade | Fatia |
|---:|---|---|---|---|
| A1 | **Composer sem indicação de foco.** `outline-hidden` no editável, nenhuma regra no contêiner | `AppInputBar.tsx:831`, `:929` | **alta** | VIS-004 |
| A2 | `id="onyx-chat-input-send-button"` **duplicado no DOM** em modo busca | `AppInputBar.tsx:783`, `:1045` | **alta** | VIS-004 |
| A3 | Menu de projeto inalcançável por toque (sem `no-hover:`) | `ProjectFolderButton.tsx:232-237` | **alta** | VIS-002 |
| A4 | `"Open Sidebar"`/`"Close Sidebar"` em inglês no `aria-label` do controle mais usado da casca, em produto PT-BR | `sidebar/components.tsx:177-223` | **alta** | VIS-002 |
| A5 | `aria-label="share-chat-button"` — leitor de tela anuncia um seletor | `AppChrome.tsx:578` | média | VIS-002 |
| A6 | `NEW_AGENT_BUTTON_ARIA_LABEL = "AgentsPage/new-agent-button"` como `aria-label` real | `AgentsNavigationPage.tsx:62` | média | VIS-007 |
| A7 | `aria-label="onboarding-flow"` sem tradução | `OnboardingFlow.tsx:44` | média | VIS-003 |
| A8 | `role="button" tabIndex={0}` envolvendo um `<Button>` real | `CompletedHeader.tsx:202-218` | média | VIS-006 |
| A9 | **Sem reset global de `prefers-reduced-motion`**; só 4 blocos escopados | `globals.css`, `comet.css`, `custom-code-styles.css`, `loader/styles.css` | **alta** | VIS-001 |
| A10 | `SvgSimpleLoader` com `animate-spin` puro; é o spinner mais usado | `icons/simple-loader.tsx` | média | VIS-009 |
| A11 | 7 dos 8 skeletons animam sob reduced-motion; 7 dos 8 sem `role="status"` | ver §5.8 | média | VIS-009 |
| A12 | Rótulos de seção da sidebar a ~45% de opacidade (`text-02`, 12px/400) | `sidebar/components.tsx:311-341` | média | VIS-002 |
| A13 | **Seleção inverte sob o cursor**: `selected:hover` usa o mesmo fundo do hover não-selecionado | `stateful/styles.css:453-583` | média | VIS-002 |
| A14 | **Sem célula `:active`** nas variantes de sidebar: pressionado é idêntico a hover | idem | baixa | VIS-002 |
| A15 | Anexo com falha desaparece sem aviso visual | `providers.tsx` (polling) | média | VIS-005 |
| A16 | Erro depende de cor bruta (`text-red-700`) sem ícone garantido | `Resubmit.tsx:123` | média | VIS-006 |
| A17 | Pseudo-elementos com borda `#e5e7eb` cega a tema | `globals.css:32` | baixa | VIS-001 |
| A18 | `text-01` como cor de estado vazio da sidebar (contraste muito baixo) | `AppSidebar.tsx:179-181` | média | VIS-002 |
| A19 | Ponto de truncamento do rótulo muda ao passar o mouse | `sidebar-tab/components.tsx:141-143` | baixa | VIS-002 |
| A20 | Zero affordance de arrastar no maior alvo de soltura da aplicação | `AppPage.tsx:778-786` | média | VIS-005 |

**Preservado e correto, não regredir:** dois landmarks `nav` com nome acessível
na sidebar (FE-004), `data-interactive-state="selected"` publicando estado sem
depender de cor, `aria-expanded` nas pastas de projeto, foco de 2px
`border-04` com offset negativo, `FoldedTooltip` mantido montado e suprimido,
`inert` na barra colapsada do composer, `aria-multiline`/`aria-disabled`/
`aria-placeholder` no editável, e o fallback de shimmer para reduced-motion.

---

## 10. Estado de voz e viabilidade de ditado

O requisito de produto é explícito: **TON não será um produto de conversa por
voz.** A interação futura é ditado apenas — microfone → texto → revisão → envio
normal por texto.

### 10.1 O que existe hoje

| Peça | Arquivo | Linhas | Transporte |
|---|---|---:|---|
| `VoiceModeProvider` | `web/src/providers/VoiceModeProvider.tsx` | 1118 | WebSocket TTS + `MediaSource` |
| `MicrophoneButton` | `web/src/sections/input/MicrophoneButton.tsx` | 319 | — |
| `useVoiceRecorder` | `web/src/hooks/useVoiceRecorder.ts` | ~530 | WebSocket STT, PCM16 |
| `Waveform` | `web/src/components/voice/Waveform.tsx` | 209 | — |
| `TTSButton` | `web/src/app/app/message/messageComponents/TTSButton.tsx` | 91 | HTTP streaming |
| `StreamingTTSPlayer` | `web/src/lib/streamingTTS.ts` | 551 | HTTP streaming |
| `useVoiceStatus` | `web/src/hooks/useVoiceStatus.ts` | 27 | `GET /api/voice/status` |
| Admin de voz | `web/src/views/admin/VoicePage/**` | 336 + 468 | — |

**Não existe componente de chamada de voz.** O laço conversacional é
*emergente*: `autoSend` (envia ao detectar silêncio) + `autoListen` (reabre o
microfone quando o TTS termina) + auto-playback do TTS. Desligar conversa é
desligar três props, não apagar um componente.

### 10.2 Ditado hoje depende do backend

`VoiceRecorderSession.start()` (`useVoiceRecorder.ts:106-172`) usa
`getUserMedia` + `AudioContext` + `createScriptProcessor(4096, 1, 1)`,
reamostra para 24 kHz, converte para PCM16 e envia quadros binários a cada
250ms por WebSocket para `/api/voice/transcribe/stream`. O VAD é **do
servidor**; o cliente só reage a `is_final`.

**Não há `MediaRecorder` e não há `SpeechRecognition`/`webkitSpeechRecognition`
em nenhum lugar de `web/`.** Portanto:

- manter o ditado como está **preserva** a dependência de `stt_enabled` e de um
  provedor STT configurado por um administrador;
- o `audioLevel` que alimenta a waveform de gravação é o RMS calculado no
  `onaudioprocess`. Uma migração para `SpeechRecognition` **perderia esse
  sinal**, e a waveform de 120 barras deixaria de funcionar;
- `ScriptProcessorNode` é uma API depreciada — dívida técnica registrada, fora
  do escopo visual.

### 10.3 Contrato futuro de ditado — requisitos para VIS-008

A auditoria de viabilidade de `SpeechRecognition` no navegador conclui que é
possível como **caminho alternativo**, não como substituição imediata. Os
requisitos abaixo são o contrato de VIS-008:

- detecção de capacidade sem falha silenciosa;
- **esconder o microfone quando não houver suporte** (hoje o comportamento é
  mostrar um botão desabilitado para administradores, o que é razoável);
- consciência de contexto seguro (`https` ou `localhost`);
- transcrição intermediária visível;
- transcrição final inserida no composer;
- inserção consciente do cursor onde for praticável;
- **sem perda de foco** do composer;
- parar ao enviar;
- watchdog de inatividade (já existe: `SILENCE_FALLBACK_TIMEOUT_MS` de 10s);
- pt-BR primeiro;
- considerações de Safari e iOS.

### 10.4 O que pode ser escondido com segurança

Seguro, são folhas: `TTSButton` no toolbar
(`MessageToolbar.tsx:323-329`); a waveform `"speaking"`
(`AppInputBar.tsx:844-851`); `autoSend={false}` e `autoListen={false}`
(`AppInputBar.tsx:744-745`) — **isto sozinho mata o laço conversacional e
mantém o ditado**; os três controles de voz em
`SettingsPage.tsx:1630-1681`; a metade TTS do admin de voz.

**Não pode ser removido, só neutralizado:**

1. **`stopTTS` é chamado por quatro interações não relacionadas a voz**:
   o wrapper de submit (`AppInputBar.tsx:293`), o dreno da fila de mensagens
   (`:408`), e os dois ramos do botão enviar/parar (`:804`, `:807`). O ícone e
   o estado desabilitado do botão dependem de `isVoicePlaybackControllable`
   (`:209`). **Manter `stopTTS` como no-op, não excluir.**
2. **`MessageTextRenderer` depende de `revealedCharCount`, `isAudioSyncActive`
   e `isAwaitingAutoPlaybackStart`** em seis pontos (`:145-149`, `:181-233`,
   `:428-447`). Remover essas chaves do tipo de contexto **quebra a compilação
   do renderizador de streaming**. A saída correta é o portão:
   `shouldUseAutoPlaybackSync` tem `autoPlayback` como primeiro conjunto, e
   `autoPlayback = voice_auto_playback && ttsEnabled`
   (`VoiceModeProvider.tsx:149-150`). Com `autoPlayback` falso, todos os ramos
   retornam `fullContent`. **Portar pelo gate, não amputar.**
3. `streamTTS` é chamado pelo `useLayoutEffect` de `AgentMessage.tsx:221-263`
   em cada pacote, **independentemente do que é renderizado**. Só é inerte
   porque `streamTTS` retorna cedo em `!autoPlayback` (`:698-700`).
4. `isDisabled` do microfone inclui `isTTSPlaying || isTTSLoading ||
   isAwaitingAutoPlaybackStart` (`MicrophoneButton.tsx:307-312`). Se algum
   travar em `true` e a UI de parar tiver sido removida, **o microfone fica
   permanentemente desabilitado sem saída**.
5. `VoiceModeProvider` é montado **duas vezes** (`app/app/layout.tsx:30`,
   `app/nrf/layout.tsx:17`) e `useVoiceMode()` lança fora do provider. O
   provider precisa continuar montado.
6. `MultiModelPanel.tsx:309` já passa `disableTTS`, e `AgentMessage.tsx:233`
   já curto-circuita nele. **Precedente pronto de caminho sem voz.**

### 10.5 Chaves i18n que ficam órfãs

Remover em **todos** os nove catálogos, ou `types:check` falha por paridade:
`chat.messages.tts.*` (`en.json:10239-10252`), `settings.chats.voice.*`
(`:13332-13347`), `chat.input.appInputBar.input.speakingPlaceholder` (`:9534`),
e a metade TTS de `admin.voice.*` (`:8105-8210`).

**Manter:** `chat.input.microphoneButton.*` (`:9610-9622`) e
`listeningPlaceholder` (`:9530`) — o ditado precisa deles.
`chat.input.appInputBar.voiceSetupButton.tooltip` (`:9543-9545`) ainda diz
"Onyx" e precisa ser reescrito, não removido.

---

## 11. Direção TON alvo

A especificação completa está em [`visual-language.md`](./visual-language.md).
Esta seção registra só as decisões que a auditoria concluiu serem necessárias, e
por quê.

### 11.1 Superfície e cor

**Neutro primeiro. Verde como estado e identidade. Dourado só onde for
semanticamente útil.** Não criar canvas verde.

A rampa `tint-*` hoje está aliasada em `vale-norte-neutral-*`, o que faz **toda**
superfície ter viés verde nos dois temas. A decisão de VIS-001 é separar:

- superfícies e bordas usam neutros verdadeiros;
- verde entra em `action-selection-*`, `theme-primary-*`, foco e identidade;
- dourado (`theme-amber-*`, `highlight-accent`) fica em atenção semântica
  específica, e **não** substitui `status-warning-*`.

### 11.2 Escuro

Escuro **neutro**, não escuro verde. Ver §8.2 para a escada atual e o custo. A
mudança obriga a reexecutar contraste em toda a escada e a atualizar
`ton-theme.test.ts:170-277`.

### 11.3 Geometria

Menos arredondado que a experiência upstream atual. Hierarquia candidata a
avaliar em VIS-001:

| Classe | Raio |
|---|---|
| controles compactos | pequeno (`radius-04`) |
| inputs e botões | pequeno-médio (`radius-04`/`radius-08`) |
| cartões, composer, popover | médio (`radius-08`/`radius-12`) |
| dialogs | médio-grande, só onde útil (`radius-12`) |
| circular | só avatar, ponto de status e pílula semântica |

Alvos concretos de redução de 16px → 12px: composer, bolha do usuário, cartão de
especialista, cartão de edição de mensagem.

### 11.4 Elevação

**Borda + contraste de superfície antes de sombra.** Sombra fica para elevação
real: popover, dropdown, dialog, camada flutuante. Os quatro alvos de remoção
estão em §3.4. O ganho estrutural é eliminar o contorno de 14px de três
arquivos.

### 11.5 Linguagem de estado

Definir os doze estados: `DEFAULT`, `HOVER`, `SELECTED`, `ACTIVE`,
`FOCUS_VISIBLE`, `PRESSED`, `DISABLED`, `LOADING`, `ERROR`, `SUCCESS`,
`ATTENTION`, `RUNNING`.

O que a auditoria encontrou hoje:

| Estado | Existe? | Observação |
|---|---|---|
| `DEFAULT` | sim | consistente via `Interactive` |
| `HOVER` | sim | `background-tint-03` |
| `SELECTED` | sim, com defeito | `background-tint-00`; **inverte sob o cursor** |
| `ACTIVE` | parcial | derivado da URL por `useAppPosition`; não é visual distinto |
| `FOCUS_VISIBLE` | parcial | bom no `SidebarTab`; **ausente no composer** |
| `PRESSED` | **não** | sem célula `:active` nas variantes de sidebar |
| `DISABLED` | sim | `opacity-50` — depende só de opacidade |
| `LOADING` | inconsistente | `invisible`, `null`, skeleton, spinner, shimmer — cinco tratamentos |
| `ERROR` | inconsistente | `status-error-*` em uns, paleta bruta em outros, ausente em anexos |
| `SUCCESS` | raro | quase não usado fora de status de indexação |
| `ATTENTION` | **não** | `highlight-accent` existe e é pouco usado |
| `RUNNING` | ad-hoc | pontos à mão, shimmer, spinner |

A linguagem alvo deve combinar **borda + superfície + tipografia + estado de
ícone + anel de foco acessível**, e não cor isolada.

### 11.6 Seleção e ativo

Direção: mudança sutil de superfície **+ borda TON de 1px** + tratamento de foco
acessível. Sem pílula preenchida grande.

Superfícies a auditar sob essa regra: conversa selecionada, navegação ativa,
especialista ativo, projeto selecionado, Deep Research ativo, anexo ativo, fonte
ou ferramenta ativa. Todas hoje passam pela mesma matriz de `Interactive`, o que
é vantagem: **um ajuste central corrige sete superfícies**, e é também o risco.

### 11.7 Atividade operacional em vez de raciocínio

Substituir o vocabulário de raciocínio por atividade observável. Exemplos de
direção, a validar com produto: "Consultando fontes…", "Validando
competência…", "Analisando contrato…", "Comparando dados…", "Executando
regra…", "Preparando resposta…".

Regra dura: **não expor chain-of-thought.** Distinguir atividade real observável
de "pensando" decorativo. `AnalysisRun`/`AnalysisStep` do backend podem lastrear
esses rótulos depois; até lá, o rótulo precisa corresponder a um pacote real.

### 11.8 Home

Chat primeiro, não dashboard. Direção conceitual: "O que você deseja analisar?"
com o composer como protagonista, e ações rápidas pequenas e relevantes ao
domínio.

**Restrição de honestidade, verificada:** não existe `findings`, `occurrences`,
`analysisRun` nem `reports` em `web/src/lib`. Uma faixa de consciência
operacional só pode usar: sessões de conversa, projetos, arquivos recentes,
especialistas disponíveis e **notificações** (o único feed com severidade e
resumo). Qualquer número de achados, ocorrências, cobertura, risco ou SLA
**seria inventado** e é falha de aceite.

### 11.9 Identidade de especialista

Um sistema unificado. Princípios: caixa delimitadora única, consistência de
traço, escala de ícone definida, acento semântico, e estados `idle`, `running`,
`attention`, `selected`.

VIS-000 **não cria** as personas. TON Central, CFO, Frota, Contratos, Auditor e
RH pertencem ao Plano backend 005 e a `TON-FE-005`.

### 11.10 Referência ClearEyed/Twenty — limite declarado

ClearEyed/Twenty é referência de **qualidade e interação**, aplicável a: nova
conversa, composer, apresentação de anexos, streaming, estados de ferramenta,
ditado, densidade mínima e microinterações.

**Não é** a referência estrutural da sidebar TON. Twenty é um CRM; TON não é.
FE-004 já estabeleceu a arquitetura de informação do TON, e ela está congelada.
Esta auditoria **não propõe** substituir a navegação de FE-004 pela sidebar do
CRM. Nenhuma medida aproximada da referência foi tratada como constante TON;
nenhum CSS foi copiado; nenhuma cor foi reproduzida mecanicamente.

### 11.11 Arquitetura preservada

Nada nesta auditoria recomenda: adotar Jotai, trocar SSE pelo Vercel AI SDK,
trocar o router, trocar a biblioteca de componentes, reescrever em outro
framework, ou reconstruir infraestrutura madura.

O editor `contentEditable`, a máquina de upload, o pipeline de streaming, o
sistema de tokens, a casca responsiva, o dnd-kit, o `next-intl` e o Opal ficam.

---

## 12. Fatiamento de implementação

Detalhe por fatia em
[`visual-implementation-roadmap.md`](./visual-implementation-roadmap.md).

| Fatia | Responsabilidade | Nível máx. | Depende de |
|---|---|---:|---|
| VIS-001 | Fundações e linguagem de superfície | 2 | VIS-000 |
| VIS-002 | Casca e navegação (visual de FE-004) | 3 | VIS-001 |
| VIS-003 | Home / nova conversa | 3 | VIS-001, VIS-004 |
| VIS-004 | Composer | 3 | VIS-001 |
| VIS-005 | Anexos e contexto | 3 | VIS-001, VIS-004 |
| VIS-006 | Mensagens, streaming, atividade de ferramenta | 3 | VIS-001 |
| VIS-007 | Especialistas e identidade de runtime | 4 | VIS-001; ADR-009 |
| VIS-008 | Voz apenas por ditado | 3 | VIS-004 |
| VIS-009 | Movimento e microinterações | 4 | VIS-001, VIS-007 |
| VIS-010 | QA final De-Onyx | 2 | todas |

**Fronteira exata de VIS-001**, decidida por esta auditoria:

*Dentro:* papéis de superfície e borda nomeados; hierarquia de raio; redução de
elevação; primitivos globais de estado (incluindo `:active` e a correção de
`selected:hover`); tratamento de selecionado e foco; refinamento de token de cor
(neutros do canvas, simetria de borda, resíduos `onyx-*`); fundação claro/escuro;
ligar `spacing` e `borderWidth` ao Tailwind; criar tokens de movimento e o reset
global de `prefers-reduced-motion`; corrigir a escala de blur; tokenizar
larguras de leitura; atualizar `ton-theme.test.ts`.

*Fora:* qualquer mudança de composição de página, o composer, mensagens, anexos,
identidade de especialista, o loader de marca, a home e a voz.

Ordem recomendada: **VIS-001 → VIS-004 → VIS-002 → VIS-005 → VIS-006 → VIS-003
→ VIS-007 → VIS-008 → VIS-009 → VIS-010.**

VIS-004 vem cedo porque remover a sombra do composer elimina o contorno de três
arquivos e desbloqueia VIS-003 (a transição da home depende da geometria final
do composer). VIS-003 vem depois de VIS-005 e VIS-006 porque a home precisa da
geometria final de anexo e de mensagem para a transição não saltar.

---

## 13. Inspeção de runtime

**RUNTIME VISUAL INSPECTION DEFERRED.**

Motivo: não existe runtime disponível para inspeção.

Evidência coletada nesta execução:

```text
docker ps            → apenas ces-redis e ces-postgres (outro projeto)
docker ps -a         → onyx-nginx-1            Exited (137) 2 hours ago
                       onyx-web_server-1       Exited (143) 2 hours ago
                       onyx-api_server-1       Exited (137) 2 hours ago
                       onyx-code-interpreter-1 Exited (0)   2 hours ago
                       onyx-relational_db-1    Exited (0)   2 hours ago
http://localhost:3000 → sem resposta
backend/log          → não existe
```

Nenhum serviço Onyx está no ar. As alternativas foram recusadas conforme a
política de execução concorrente:

1. iniciar `onyx-*` altera estado Docker compartilhado e pode conflitar com o
   Plano backend 003d, que pode estar em execução em outro worktree;
2. mesmo se iniciado, `onyx-web_server-1` roda imagem pronta sem bind mount do
   repositório — foi o que FE-002.1 e FE-004 registraram. Ele serviria código
   anterior e produziria falso positivo;
3. subir um segundo frontend contra o mesmo PostgreSQL faria o global-setup do
   Playwright registrar usuários no banco compartilhado.

A auditoria foi feita a partir de: código-fonte, CSS e tokens lidos
diretamente; testes existentes (`ton-theme.test.ts`, `ton-navigation.test.tsx`,
`ton-product-surface.test.tsx`, `dropzonePaste.test.tsx`, `icons.test.tsx`);
e os registros de execução de FE-002, FE-002.1, FE-003 e FE-004.

**Nenhuma captura de tela foi fabricada. Nenhuma observação de runtime foi
inventada.** Todo valor citado neste documento vem de um arquivo em disco no
commit `3de088cbd7`.

VIS-001 deve executar `VIS` (revisão visual claro/escuro × 375/768/1280) quando
existir ambiente que sirva o branch.

---

## 14. Fora de escopo, confirmado

- Nenhum arquivo de produção do frontend mudou. `git diff` limitado a
  `plans/ton/frontend/`.
- Nenhum arquivo em `backend/` mudou. Nenhum toque em `backend/onyx/db/ton/`,
  `backend/alembic/`, `Finding`, `Occurrence`, `Rule` ou `AnalysisRun`.
- Nenhuma dependência do Plano backend 003c ou 003d.
- Nenhum trabalho de `TON-FE-005` a `TON-FE-011`. Nenhuma persona criada.
- Nenhuma implementação `TON-VIS-001` a `TON-VIS-010`.
- A arquitetura de informação de FE-004 não foi redesenhada. Central,
  Especialistas, Projetos e o histórico separado por divider continuam como
  entregues.
- A sanitização de FE-003 não foi revertida. As quatro constantes de
  `web/src/lib/ton/product-surface.ts` continuam `false`.
- A sidebar CRM ClearEyed/Twenty não foi usada como referência estrutural.
- O worktree original não foi tocado. Nenhum merge, push ou rebase.

## 15. Limitações registradas

1. **Sem verificação de runtime** (§13). Toda medida de contraste citada vem de
   `ton-theme.test.ts` ou de cálculo sobre valores de token, não de pixels
   renderizados.
2. `web/lib/shared/dist/tokens.css` é gerado e gitignored. Foi amostrado, não
   lido inteiro; os valores foram resolvidos a partir dos sete JSON de origem.
3. `web/lib/shared/style-dictionary.config.mjs` e
   `web/lib/opal/scripts/bundle-css.mjs` não foram abertos, então a ordem exata
   de emissão dentro de `dist/tokens.css` além dos dois seletores não foi
   verificada.
4. Valores arbitrários do Tailwind (`text-[13px]`, `w-[42px]`) e literais
   `rgba()`/`hsl()` não foram enumerados exaustivamente. A varredura cobriu
   literais hex em `web/src/**/*.tsx` e contagens de classe de raio.
5. A geometria interna de `AttachmentItemButton` (Opal) não foi lida, então o
   raio e o padding exatos do cartão de anexo vêm do call site, não do
   componente.
6. `Hoverable` não tem CSS localizado; o mecanismo exato de opacidade foi
   inferido do uso.
7. O espelho `mobile/` foi registrado, não auditado. Ele tem cópias
   independentes do octógono, do avatar e da copy.
8. `web/src/components/` (legado) foi auditado apenas onde superfícies TON o
   importam.
