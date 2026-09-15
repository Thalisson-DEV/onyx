# TON — linguagem visual

Especificação alvo, independente de página. Companheira de
[`000-de-onyx-visual-audit.md`](./000-de-onyx-visual-audit.md).

**Este documento é especificação. Nenhum token de produção foi alterado.** Os
valores marcados como *candidato* precisam de aprovação de design e de medição
de contraste antes de entrar em `web/lib/shared/tokens/`.

---

## 1. Caráter

TON é uma ferramenta de controladoria e inteligência operacional. A interface
deve ler como instrumento de trabalho, não como produto de consumo.

| Atributo | Significa | Não significa |
|---|---|---|
| Mínimo | só o que carrega informação | vazio ou incompleto |
| Operacional | estado corresponde a processo real | rótulo decorativo |
| Silencioso | nada chama atenção em repouso | sem hierarquia |
| Preciso | geometria e ritmo intencionais | rígido ou apertado |
| Corporativo | sóbrio e confiável | cinza e sem vida |
| Técnico | densidade serve leitura de dados | denso em todo lugar |

### 1.1 Hierarquia de meios

Ao diferenciar dois elementos, usar nesta ordem. Descer um nível só quando o
anterior não resolver.

```text
1. tipografia          (tamanho, peso, cor de texto)
2. espaçamento         (proximidade e agrupamento)
3. borda               (1px como fronteira de informação)
4. contraste de superfície
5. estado explícito    (atributo de dados + tratamento visual)
6. sombra              (só elevação real)
```

Consequência direta: **não adicionar um contêiner antes de tentar tipografia e
espaçamento.** A auditoria mostrou que a hierarquia tipográfica está
subutilizada (títulos e corpo compartilham `text-04`), então há espaço grande
nos níveis 1 e 2.

### 1.2 Reduzir dependência de

Cartões flutuantes · pílulas sem semântica · contêineres muito arredondados ·
gradientes decorativos · sombras pesadas · visual de "faísca de IA" ·
iconografia grande · clichê de dashboard SaaS.

---

## 2. Superfícies e canvas

### 2.1 Princípio

**Neutro primeiro.** O canvas e as superfícies são neutros. Verde é estado e
identidade. Dourado é atenção semântica específica.

**Não existe canvas verde.** A rampa `tint-*` hoje está aliasada em
`vale-norte-neutral-*`, o que dá viés verde a toda superfície nos dois temas
(`primitives.json:1010-1077`). VIS-001 separa isso.

### 2.2 Escada de superfície

Cinco papéis. Cada passo precisa de contraste mínimo de 1.15 contra o vizinho,
verificável em `ton-theme.test.ts`.

| Papel | Uso | Token atual |
|---|---|---|
| `canvas` | fundo da aplicação, canvas conversacional | `background-tint-01` |
| `surface` | sidebar, painel, faixa de rodapé de cartão | `background-tint-02` |
| `surface-raised` | cartão, popover, item selecionado | `background-tint-00` |
| `surface-hover` | realce de interação | `background-tint-03` |
| `field` | input, composer | `background-neutral-00` |

Nota de nomenclatura: a escada atual é numérica (`-00` a `-04`) e **não é
monotônica em ordem de luminância** — `tint-00` é a mais clara no claro e serve
de superfície elevada no escuro. Os nomes de papel acima são a leitura correta.
VIS-001 decide se introduz aliases nomeados ou apenas documenta.

### 2.3 Claro

Candidato: manter a estrutura atual, reduzir o viés verde do canvas.

| Papel | Atual | Direção |
|---|---|---|
| `canvas` | `#f8f9f8` | off-white neutro; viés verde mínimo ou nenhum |
| `surface` | `#eff2f0` | cinza neutro claro |
| `surface-raised` | `#ffffff` | branco |
| `surface-hover` | `#e3e7e4` | cinza neutro |
| `field` | `#ffffff` | branco |

Evitar: verde em tudo, grades de cartão sem propósito, blocos de cor decorativos.

### 2.4 Escuro

**Escuro neutro, não escuro verde.** Esta é a única divergência declarada em
relação a FE-002.1, e é decisão de VIS-001.

```text
canvas:   quase-preto / carvão neutro
surface:  cinza neutro escuro
border:   cinza neutro
text:     off-white
verde:    foco / ativo / identidade
dourado:  atenção semântica específica
```

Estado atual, para comparação (todos `vale-norte-neutral-*`, portanto
esverdeados):

| Papel | Valor atual |
|---|---|
| `field` | `#0b1410` |
| `surface-raised` | `#18231d` |
| `canvas` | `#27332c` |
| `surface` | `#344139` |
| `surface-hover` | `#414f47` |
| anel de foco interno | `#56655d` |

Restrições obrigatórias, herdadas de FE-002.1 e a preservar:

1. nenhuma superfície usa preto puro;
2. cada passo mantém ≥1.15 de contraste;
3. `text-05` e `text-01` não mudam, para que `disabled` continue o mais fraco;
4. `border-04` e `border-05` mantêm foco acima de 3:1.

Custo declarado: mudar para neutro reabre as razões aprovadas em FE-002.1 e
obriga a reexecutar contraste na escada inteira, mais atualizar
`ton-theme.test.ts:170-277` no mesmo commit.

---

## 3. Cor

### 3.1 Papéis

| Papel | Token | Uso |
|---|---|---|
| identidade | `theme-primary-04/05/06` | marca, logo, acento institucional |
| estado interativo | `action-selection-00..06` | selecionado, ativo, foco |
| link | `action-text-link-05` | texto navegável |
| atenção | `theme-amber-*`, `highlight-accent` | atenção semântica específica |
| sucesso | `status-success-*` | resultado positivo |
| aviso | `status-warning-*` | condição a observar |
| erro | `status-error-*`, `action-danger-*` | falha, destruição |
| informação | `status-info-*` | neutro informativo |

### 3.2 Regras duras

1. **Verde de marca ≠ verde de sucesso.** `theme-primary-*` e
   `action-selection-*` são identidade e estado. `status-success-*` é resultado.
   Nunca trocar um pelo outro.
2. **Dourado não substitui aviso.** `theme-amber-*` é atenção institucional.
   `status-warning-*` continua sendo aviso.
3. **`theme-green-05` não é verde Vale Norte.** É `#008933`/`#00a43f`, verde
   Onyx. Não usar como cor de marca. Quatro entradas de
   `agentAvatarIconMap` erram nisso hoje.
4. **Nada de cor embutida do Tailwind** e **nada de modificador `dark:`**, por
   `web/AGENTS.md`. Única exceção: `createLogoIcon`.
5. **Estado nunca depende só de cor.** Combinar com borda, tipografia, ícone ou
   texto.
6. `action-selection-*` **não é monotônica no escuro**: `01`/`02` são lavagens
   escuras, `03` é menta claro, `04`/`05`/`06` são preenchimentos médios. Não
   assumir "maior = mais forte".
7. `theme-primary-*` **inverte** entre temas: preenchimento no claro, primeiro
   plano no escuro. Comportamento intencional, afirmado em
   `ton-theme.test.ts:150-160`.

### 3.3 Resíduos a eliminar

`onyx-ink-100/95/90` e `onyx-chrome-20/10/00` (`primitives.json:822-845`,
expostos em `tailwind-preset.cjs:198-203`); `text-[#33C19E]!` em
`web/src/components/icons/icons.tsx`; hex cru de `shimmer-*` em
`semantic-*.json:3-10`; `--color-gray-200` em `globals.css:32`; `#888` em
`globals.css:187`; ~130 linhas de Atom One em `custom-code-styles.css:51-215`;
paleta bruta e `dark:` em `Resubmit.tsx`.

---

## 4. Hierarquia de borda

Bordas são o meio principal de fronteira e de estado no TON. Hoje **não existe
sistema nomeado** — os papéis existem só como convenção documentada em um teste
(`ton-theme.test.ts:211-233`).

### 4.1 Papéis alvo

| Papel | Função | Token candidato | Contraste mínimo |
|---|---|---|---|
| `subtle` | divisor interno, grade de tabela | `border-01` | 1.5:1 sobre canvas |
| `default` | fronteira de componente: cartão, input, composer | `border-01`/`border-02` | 1.5:1 |
| `interactive` | fronteira que responde a hover | `border-02` | 1.5:1 |
| `selected` | **item selecionado ou ativo** | `action-selection-04/05` | 3:1 |
| `focus` | anel de `focus-visible` | `border-04` | 3:1 em toda superfície |
| `error` | validação falhou | `status-error-05` | 3:1 |
| `attention` | precisa de olhar | `theme-amber-05` | 3:1 |

### 4.2 Regras

1. Largura padrão é **1px**. Ligar `weight-line-border` ao Tailwind
   (`size.json:258-261` existe e não está mapeado).
2. Foco usa **2px** com offset, e é o único caso de 2px permitido por padrão.
3 Bordas claras e escuras devem ter **papéis simétricos**. Hoje as claras são
   cinzas upstream e as escuras foram rebrandadas.
4. A cor de borda padrão precisa de **uma única** declaração. Hoje `globals.css`
   declara duas vezes (@26-34 e @49-52) e os pseudo-elementos ficam com um cinza
   cego a tema.
5. Não usar borda como decoração. Se não separa nem comunica estado, remover.

---

## 5. Hierarquia de raio

TON é **menos arredondado** que a experiência upstream atual.

### 5.1 Escala

A escala existente é boa e fica (`size.json:286-313`): `radius-02` 2px ·
`radius-04` 4px · `radius-08` 8px · `radius-12` 12px · `radius-16` 16px ·
`radius-20` 20px · `radius-round` 62.5rem.

### 5.2 Atribuição alvo

| Classe | Raio candidato | Exemplos |
|---|---|---|
| controle compacto | `radius-04` | chip, tag, ícone-botão pequeno |
| input e botão | `radius-04`/`radius-08` | botão, campo, linha de nav |
| cartão, composer, popover | `radius-08`/`radius-12` | composer, cartão, dropdown |
| dialog | `radius-12` | modal — só onde for útil |
| circular | `radius-round` | **só** avatar, ponto de status, pílula semântica |

### 5.3 Reduções concretas

| Superfície | Hoje | Alvo | Arquivo |
|---|---|---|---|
| composer | 16px | 12px | `AppInputBar.tsx:831` |
| composer Craft | 16px topo | 12px | `BaseInputBar.tsx:283-286` |
| bolha do usuário | 16px assimétrico | 8–12px simétrico | `HumanMessage.tsx:224-226` |
| cartão de edição | 16px | 12px | `HumanMessage.tsx:51-55` |
| cartão de especialista | 16px | 8–12px | `web/src/app/css/card.css:1-3` |
| waveform "speaking" | 16px | removido com o TTS | `Waveform.tsx:130` |
| `ActionCardSkeleton` | 16px | acompanhar o cartão | `ActionCardSkeleton.tsx:11` |

### 5.4 Circular sem razão semântica

Auditado; estes são os casos e a decisão:

| Local | Uso | Decisão |
|---|---|---|
| `CustomAgentAvatar.tsx:103-118` | imagem de avatar | **manter** — semântico |
| `SidebarTabSkeleton.tsx:19` | placeholder de ícone recolhido | converter para `radius-04` |
| `ActionCardSkeleton.tsx` | três barras `rounded-full` | converter |
| `CustomToolRenderer.tsx:165-176` | três pontos de carga de 4px | **manter** se o primitivo continuar pontual |
| `web/src/lib/app/components.tsx:41` | contêiner do logo enterprise | avaliar; hoje força círculo em logo quadrado |
| `Waveform.tsx` | barras de waveform | manter; é forma de barra |

### 5.5 Corrigir o consumo

Um terço dos raios do app ignora a escala: 28 usos tokenizados contra 14 usos de
`rounded-sm/md/lg/xl/2xl/3xl`. VIS-001 converte os 14.

Nota: `rounded-full` mapeia para `radius-round` = 62.5rem, **não** `9999px`.

---

## 6. Elevação

### 6.1 Princípio

**Borda + contraste de superfície antes de sombra.**

Sombra fica reservada para elevação genuína: popover, dropdown, dialog, tooltip,
camada flutuante necessária. Sombra **não** é aresta e **não** é decoração.

### 6.2 Escala

Três níveis, como hoje (`shadow.json`), com raio reduzido:

| Nível | Uso | Hoje |
|---|---|---|
| `elevation-0` | em fluxo: cartão, composer, linha | sem sombra; borda + surface |
| `elevation-1` | popover, dropdown, tooltip | `shadow-box-00`/`-01` |
| `elevation-2` | dialog, overlay modal | `shadow-box-02` |

### 6.3 Remoções

| Superfície | Hoje | Ação |
|---|---|---|
| composer | `shadow-box-01` **é a única aresta** | trocar por borda 1px; **remove o hack de 14px em 3 arquivos** |
| cartão de especialista | `hover:shadow-box-00` | remover; usar borda |
| waveform "speaking" | `shadow-box-01` | removido com o TTS |
| badge de remover anexo | `shadow-xs` | remover |

### 6.4 Escuro

Hoje as sombras escuras são **brilhos brancos** (`#ffffff0d`/`1a`/`33`), e com
24px de blur `shadow-box-02` lê como halo. Migrar para borda + surface resolve
isso sem token novo. Onde a sombra permanecer no escuro, reduzir o raio e
apoiar-se em borda.

### 6.5 Blur

A escala é degenerada hoje: `-01` 2px, `-02` 1px, `-03` 1px. Corrigir para três
passos monotônicos. Blur é para backdrop de overlay, não para vidro decorativo.

---

## 7. Linguagem de estado

Doze estados. Todo componente interativo declara os que suporta.

| Estado | Meio primário | Meio de apoio | Nunca |
|---|---|---|---|
| `DEFAULT` | surface + texto | — | — |
| `HOVER` | contraste de surface | — | mudar tamanho ou posição |
| `SELECTED` | **borda TON 1px + surface sutil** | peso de texto, estado de ícone | pílula preenchida grande |
| `ACTIVE` | igual a `SELECTED` + atributo de dados | — | só cor |
| `FOCUS_VISIBLE` | **anel 2px `border-04` com offset** | — | remover contorno sem substituto |
| `PRESSED` | surface um passo mais forte | — | idêntico a `HOVER` |
| `DISABLED` | texto e ícone reduzidos + `aria-disabled` | cursor | **só opacidade** |
| `LOADING` | skeleton ou indicador contido | rótulo | trocar layout |
| `ERROR` | borda `error` + ícone + texto | surface `status-error-00` | só cor |
| `SUCCESS` | ícone + texto | surface | só cor |
| `ATTENTION` | borda/ícone dourado + texto | — | confundir com `ERROR` |
| `RUNNING` | indicador de atividade + rótulo operacional | tempo decorrido | animação contínua chamativa |

### 7.1 Defeitos a corrigir

Estes três são defeitos reais encontrados na auditoria, não preferências:

1. **`SELECTED` inverte sob o cursor.** `stateful/styles.css:453-583`: selecionado
   é `background-tint-00`, e `selected:hover` vira `background-tint-03` — o mesmo
   fundo do hover não selecionado. A seleção desaparece ao passar o mouse.
   Correção: hover de item selecionado mantém o sinal de seleção e só intensifica.
2. **`PRESSED` não existe** nas variantes de sidebar (sem célula `:active`).
   Pressionado é indistinguível de hover.
3. **`FOCUS_VISIBLE` ausente no composer.** O controle principal do produto não
   tem tratamento de foco: `outline-hidden` no editável, nada no contêiner.
   Correção: borda de foco + anel interno, exatamente o padrão que
   `ton-theme.test.ts:211-233` já prescreve para `border-05` +
   `background-tint-04`.

### 7.2 Publicação de estado

Manter o mecanismo existente. `Interactive.Stateful` publica
`data-interactive-variant`, `-prominence`, `-state`, `data-interaction` e
`data-disabled` no mesmo nó do `Interactive.Container`. Isso dá estado
inspecionável e independente de cor, e é a razão pela qual **um ajuste central
corrige sete superfícies de seleção de uma vez**.

Os estados internos hoje são só `empty | filled | selected`. Se `PRESSED` e
`RUNNING` exigirem célula própria, VIS-001 estende a união.

### 7.3 Seleção e ativo — superfícies cobertas

Conversa selecionada · navegação ativa · especialista ativo · projeto
selecionado · Deep Research ativo · anexo ativo · fonte ou ferramenta ativa.

Todas passam pela mesma matriz de `Interactive`. Vantagem e risco na mesma
frase: uma mudança central resolve as sete, e uma mudança errada quebra as sete.

---

## 8. Tipografia

### 8.1 Famílias

Manter as atuais. **Não introduzir fonte nova.**

- `font-hanken-grotesk` — UI e conteúdo
- `font-dm-mono` — código, IDs, números de relatório
- `font-kh-teka` — **carregada e não usada por nenhum preset**. VIS-001 decide:
  adotar como voz de display, ou remover o `@font-face` e os dois `.otf`. Hoje o
  único consumidor é um `style` inline em `BuildWelcome.tsx:74-90`.

### 8.2 Escada alvo

19 presets existem. A direção não é criar presets, é **usar a escada que já
existe com intenção**.

| Papel | Preset | Nota |
|---|---|---|
| display | `heading-h1` | 48px/64px — hoje é o único preset com px cru |
| título de página | `heading-h2` | 24px/36px, peso 600 |
| título de seção | `heading-h3` | 18px/28px, peso 600 |
| corpo de conteúdo | `main-content-body` | 16px/24px, peso 450 |
| ênfase de conteúdo | `main-content-emphasis` | peso 700 |
| corpo de UI | `main-ui-body` | 14px/20px, peso 500 |
| UI silenciosa | `main-ui-muted` | peso 400 |
| ação de UI | `main-ui-action` | peso 600 |
| rótulo secundário | `secondary-body` | 12px/16px |
| ação secundária | `secondary-action` | 12px, peso 600 |
| mono de conteúdo | `main-content-mono` | 16px/23px |
| mono de UI | `main-ui-mono` | 14px/20px |
| mono secundário | `secondary-mono` / `-label` | 12px |
| figura | `figure-small-label` / `-value` | 10px |

### 8.3 O ganho principal

`.prose-onyx` define `--tw-prose-headings` **igual a** `--tw-prose-body`
(`custom-code-styles.css:30-49`). Títulos de markdown não têm diferenciação de
cor, e `h1`–`h6` e `blockquote` não são sobrescritos em nenhum dos dois
pipelines.

**Diferenciar por tipografia antes de introduzir contêineres** é a
recomendação central desta especificação, e este é o exemplo concreto: uma
escada de heading real (cor, peso, espaçamento acima e abaixo) melhora a leitura
de resposta longa sem nenhum cartão novo.

### 8.4 Números e relatórios

Dados operacionais usam mono com `tabular-nums`. O padrão já existe:
`Waveform.tsx:196` usa `font-mono text-xs tabular-nums` no timer.

### 8.5 Regras

1. `Text` de `@opal/components` com `font` e `color` explícitos. A API de flags
   booleanos de `refresh-components/texts/Text` é **depreciada** e ainda aparece
   em `WelcomeMessage`, `AgentDescription`, `AppSidebar` (estado vazio),
   `FilePickerPopover` e `ProjectContextPanel`.
2. Sem nó de texto solto. Sem string literal em `src/`.
3. Rótulo de seção precisa ser legível: hoje é 12px/400 em `text-02` (~45%).
   Elevar para `text-03` e peso 500 no mínimo.
4. Caixa de sentença. Sem caixa alta decorativa.

---

## 9. Espaçamento e densidade

### 9.1 Duas densidades, não uma

| Contexto | Caráter | Exemplos |
|---|---|---|
| conversacional | espaço negativo generoso | transcript, home, composer |
| operacional | densidade controlada | tabelas, listas admin, arquivos, anexos |

**Não aplicar uma densidade em tudo.** O `gap-12` (3rem) entre mensagens está
correto para canvas conversacional e seria errado numa tabela de ocorrências.

### 9.2 A escala precisa existir de fato

`size.json:102-257` define 25 passos `spacing-block-*`. **O preset não tem chave
`spacing`**, então todo `p-`/`gap-`/`m-` resolve para a escala embutida do
Tailwind e editar o token não faz nada.

VIS-001 decide: ligar a escala (e aceitar que a mudança é global), ou remover os
tokens órfãos e declarar a escala do Tailwind como a oficial. **Manter os dois
sem ligação é a pior opção**, porque parece configurável e não é.

### 9.3 Largura de leitura

Hoje existem **cinco** valores concorrentes:

| Constante | Valor | Onde |
|---|---:|---|
| `--app-page-main-content-width` | 720px | `sizes.css:13` |
| `MSG_MAX_W` | 720px codificado | `ChatUI.tsx:28-31` |
| `width.message-default` | 740px | `tailwind.config.js:48` — **não usado** |
| máscara de blur | 800px | `AppChrome.tsx:684-690` |
| chat compartilhado | `max-w-200` | `SharedChatDisplay.tsx:233` |

Alvo: **um token de largura de leitura**, consumido por composer, transcript,
home e chat compartilhado.

### 9.4 Alvos de densidade

| Problema | Local | Direção |
|---|---|---|
| barra do composer com altura fixa e sem overflow | `AppInputBar.tsx:612-623` | prioridade de overflow |
| header de cartão de especialista `h-24` fixo | `AgentCard.tsx:83` | altura por conteúdo |
| rótulo de seção com muito padding e pouco contraste | `sidebar/styles.css:145-148` | menos padding, mais peso |
| grade de tabela vinda só das variáveis prose | `custom-code-styles.css:305-380` | grade explícita e densa |

---

## 10. Iconografia

### 10.1 Regras

1. Somente `@opal/icons`. Nunca `lucide-react` nem `react-icons`. Ícone faltante
   entra em `web/lib/opal/src/icons/` via Figma MCP.
2. **Nenhum ícone de marca serve de semântica.** `SvgOnyxOctagon` como moldura de
   avatar de especialista é exatamente o erro a eliminar.
3. Traço consistente. Os ícones atuais usam `strokeWidth 1.5` em 16×16.
4. Escala definida por contexto, não arbitrária. Hoje há `w-[16px]` cru em
   `AccountPopover.tsx:260`.
5. Ícone segue o estado do componente. Hoje `sidebar-tab/components.tsx:224`
   codifica `text-text-03` e ignora `--interactive-foreground-icon`.
6. Sem faísca de IA. `SvgSparkle` em `CodingAgentRenderer.tsx:146` sai.
7. Ícone decorativo recebe `aria-hidden`. Ícone informativo recebe nome
   acessível.

### 10.2 Identidade de especialista

Princípios para VIS-007. **VIS-000 não cria as personas.**

| Aspecto | Requisito |
|---|---|
| caixa delimitadora | **uma** forma para todos os estados e fallbacks |
| traço | espessura consistente, escalando com o tamanho |
| escala de ícone | proporção fixa dentro da caixa |
| acento semântico | derivado de papel, não sorteado |
| `idle` | neutro, sem animação |
| `running` | indicador contido, sem girar a identidade |
| `attention` | dourado, distinto de erro |
| `selected` | borda TON + surface, igual ao resto do sistema |

O problema atual é forma: imagem enviada → **círculo**; ícone → **octógono**;
letra → **octógono**; fallback → **octógono**; agente padrão → **diamante sem
moldura**. Quatro tratamentos para uma entidade.

### 10.3 Identidade semântica de arquivo

Categorias candidatas: planilha · documento · imagem · apresentação · áudio ·
vídeo · arquivo compactado · outro.

Cores são **semânticas TON**, não valores copiados de referência.

Viabilidade confirmada: `ProjectFile` já carrega `name` e `file_type` (MIME), e
`SPREADSHEET_MIME_TYPES` já existe em
`PreviewModal/variants/xlsxVariant.tsx:11-23`. **Nenhum trabalho de backend é
necessário.** O que falta é uma função única, porque hoje o mapeamento de ícone
está duplicado em quatro lugares.

### 10.4 Marca

**Não existe ativo TON/Vale Norte no repositório.** `web/lib/opal/src/logos/` tem
96 arquivos, três Onyx e 93 de fornecedores. `web/public/logo.svg` é a marca
Onyx com `fill="black"` codificado.

Por ADR-009: não inventar logo. Usar o `Logo` configurável e o fallback textual.
Os pontos de troca, quando o ativo existir: `web/src/lib/app/components.tsx`
(sidebar, home, páginas de erro), `AuthFlowContainer.tsx:38` (login),
`AgentAvatar.tsx:40` (agente padrão) e `loader/components.tsx:96-115` (loader).

---

## 11. Movimento

### 11.1 Princípios

Breve · funcional · baixa amplitude · não decorativo.

Faixa candidata **120–280ms**, por interação. A auditoria mediu a faixa atual e
ela já é 150–300ms, portanto o movimento **não é o problema principal**.

### 11.2 Papéis de duração

| Papel | Candidato | Uso |
|---|---:|---|
| `instant` | 120ms | mudança de cor, hover, foco |
| `fast` | 150ms | transição de estado, fade de conteúdo |
| `base` | 200ms | dobra da sidebar, expansão, overlay |
| `slow` | 280ms | transição de layout maior |

Easing: `ease-out` para entrada, `ease-in-out` para mudança contínua de layout.
Sem bounce, sem escala dramática, sem movimento contínuo decorativo.

### 11.3 Não existe camada de token

Não há token de duração nem de easing em nenhum lugar. Os valores estão como
literais em `tailwind-preset.cjs`, `tailwind.config.js`, `globals.css` e em
strings de classe de componente. VIS-001 cria a camada.

### 11.4 Alvos

| Alvo | Hoje | Ação |
|---|---|---|
| `OnyxLoader` | 2000ms montando a marca Onyx | **substituir** |
| `shimmer-slide` | 1s varredura contínua | substituir por indicador contido |
| `animate-waveform` | 0.8s infinito | remover com o TTS |
| `.collapsible` | 500ms | reduzir |
| `animate-fade-in-up` | 500ms | reduzir |
| passos do onboarding | 500ms | reduzir |
| header do timeline | 300ms | 200ms |
| espaçadores de sombra | 150ms | **remover** com a sombra |
| pontos de ferramenta | `animate-pulse` 2s com delays inúteis | substituir |

### 11.5 Reduced motion — requisito

**Não existe reset global de `prefers-reduced-motion`.** Só quatro blocos
escopados. Logo, `animate-fade-in-scale`, `animate-waveform`,
`animate-fade-in-up`, `animate-pulse` e todo `duration-150` continuam rodando
para quem pediu menos movimento.

VIS-001 entrega um reset global. Casos específicos:

- `SvgSimpleLoader` usa `animate-spin` puro e é o spinner mais usado no admin →
  precisa de `motion-safe:`;
- 7 dos 8 skeletons animam sob reduced-motion;
- o único que acerta hoje é `UsageReports.tsx:71`.

### 11.6 Microinterações

Necessidades registradas para VIS-009. Nenhuma implementada agora.

| Interação | Comportamento alvo |
|---|---|
| foco no composer | borda de foco aparece em `instant` |
| enviar → parar | troca de ícone sem salto de layout |
| primeira mensagem | conteúdo da home cede, chat assume, composer assenta |
| navegação selecionada | borda e surface em `instant` |
| conversa selecionada | igual à navegação |
| pesquisa ativa | contorno institucional, sem glow |
| upload concluído | confirmação discreta, sem celebração |
| especialista executando | indicador contido junto à identidade |
| fonte/ferramenta concluída | estado final estável, sem pulso |
| erro | aparece sem sacudir o layout |
| dropdown | `fade-in-scale` existente, em `base` |

---

## 12. Filosofia claro/escuro

1. **Um sistema, duas variações semânticas.** Não existe folha escura paralela.
   `.dark` reatribui token; a tela não conhece o tema.
2. **Sem `dark:` e sem cor embutida do Tailwind.** Regra de `web/AGENTS.md`,
   violada hoje em `Resubmit.tsx` e `markdownUtils.tsx:239`.
3. **Paridade de papel, não de valor.** Cada papel existe nos dois temas; os
   valores diferem.
4. **Contraste é medido, não julgado.** `ton-theme.test.ts` é o portão.
5. **Escuro não vira halo.** Sombra escura ganha borda em vez de brilho.
6. **`system` funciona sem flicker.** `next-themes` com `attribute="class"` e
   `disableTransitionOnChange`, mais o sync de preferência por usuário.
7. **Tema não é feature flag.** É preferência.

---

## 13. Contrato de acessibilidade

Toda recomendação visual precisa preservar ou melhorar:

| Requisito | Verificação |
|---|---|
| contraste de texto | WCAG aplicável, medido nos pares finais |
| contraste de borda | `subtle` ≥1.5:1; `focus`/`selected` ≥3:1 |
| navegação por teclado | toda ação alcançável e operável |
| `focus-visible` | visível em toda superfície, claro e escuro |
| landmarks semânticos | os dois `nav` da sidebar preservados |
| nome acessível | sem seletor de teste como `aria-label` |
| reduced motion | respeitado globalmente |
| alvo de toque | ações alcançáveis sem hover |
| estado sem cor | borda, ícone, texto ou atributo |
| truncamento | ponto de corte estável, com tooltip quando cortado |
| RTL | propriedades lógicas (`ms-`, `pe-`, `start-`) |

### 13.1 A corrigir

Foco do composer · `id` duplicado do botão enviar · menu de projeto no toque ·
`"Open Sidebar"`/`"Close Sidebar"` sem i18n · `aria-label="share-chat-button"` ·
`"AgentsPage/new-agent-button"` como `aria-label` · `role="button"` envolvendo
`Button` · reset global de reduced-motion · `role="status"` nos skeletons ·
contraste dos rótulos de seção · seleção que inverte sob o cursor ·
`PRESSED` ausente · anexo com falha que desaparece · erro dependente de cor
bruta.

### 13.2 A não regredir

Dois landmarks `nav` com nome acessível · `data-interactive-state` publicando
estado sem cor · `aria-expanded` nas pastas · foco 2px `border-04` com offset
negativo · `FoldedTooltip` montado e suprimido · `inert` na barra colapsada ·
`aria-multiline`/`aria-disabled`/`aria-placeholder` no editável · fallback de
shimmer para reduced-motion · ações de mensagem permanentes no mobile.

---

## 14. Limites desta especificação

1. **Somente especificação.** Nenhum token de produção mudou.
2. Valores marcados *candidato* precisam de aprovação de design e medição.
3. A mudança do escuro para neutro tem custo declarado: reabre contraste
   aprovado em FE-002.1.
4. Ligar a escala de espaçamento é mudança global. Decisão de VIS-001.
5. **ClearEyed/Twenty é referência de qualidade e interação, não de estrutura.**
   Nenhuma medida da referência foi tratada como constante TON, nenhum CSS foi
   copiado, nenhuma cor foi reproduzida, e a arquitetura de informação de FE-004
   permanece.
6. Nenhuma recomendação troca biblioteca, framework, gerenciador de estado,
   editor, transporte ou router.
7. Personas concretas de especialista não são criadas aqui.
8. O logo continua bloqueado pela ADR-009.
