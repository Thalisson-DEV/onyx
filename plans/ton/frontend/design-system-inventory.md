# TON frontend: inventário do design system

## Método e fonte de verdade

Este inventário é uma leitura do código existente. A ordem de adoção indicada
abaixo vem de `web/AGENTS.md` e das exportações atuais:

1. `web/lib/opal/src/` (`@opal/*`) é a camada primária.
2. `web/src/refresh-components/` é a segunda camada para peças compostas.
3. `web/src/sections/` e `web/src/layouts/` compõem superfícies de produto.
4. `web/src/components/` é legado e não deve receber novas dependências, salvo
   `createLogoIcon` na exceção registrada no guia do frontend.

O inventário não propõe migração automática. Cada mudança TON deve reutilizar a
camada existente e registrar qualquer exceção.

## Camadas e componentes disponíveis

`web/lib/opal/src/components/index.ts` exporta componentes de interação, texto,
formulário e feedback. Os mais relevantes para TON são:

| Área | Componentes Opal observados | Uso TON preservador |
|---|---|---|
| Ação | `Button`, `LinkButton`, `TextButton`, `LineItemButton`, `FilterButton`, `SelectButton` | Ações primárias, secundárias, nav e menus. |
| Formulário | `InputTypeIn`, `InputTextArea`, `InputFile`, `InputPasswordTypeIn`, `InputSingleSelect`, `InputMultiSelect`, `InputSwitch`, `InputComboBox` | Auth, settings, agentes, upload e filtros. `InputSelect` e campos Formik relacionados vivem em `web/src/refresh-components/inputs` e `web/src/refresh-components/form`. |
| Texto | `Text`, `CompactMarkdown`, `Tag` | Hierarquia visual e markdown visível. |
| Navegação | `Tabs`, `SidebarTab`, `Popover`, `PopoverMenu`, `Modal`, `Pagination`, `EndOfList` | Sidebar, settings, dialogs, menus e listas. |
| Feedback | `IconLoader`, `OnyxLoader`, `ProgressBar`, `EndOfList`, `ConfirmationModalLayout`; store/provider de `Toast`; skeletons em `refresh-components` | Upload, indexação, erro, exclusão, espera e fim de lista. `Skeleton` não é export do barrel Opal atual. |
| Estrutura | `Divider`, `IconContainer`, `Spacer`, `ShadowDiv`, cards e table | Seções, painéis e tabelas administrativas. |
| Arquivos | `AttachmentItemButton`, picker e `UserFilesModal` | Seleção, visualização e remoção de arquivos. |

`web/lib/opal/src/layouts/index.ts` exporta `Content`, `ContentAction`,
`CardLayout`, layouts de input, `IllustrationContent`, `Section`,
`SettingsLayouts`, `RootLayout`, `SidebarLayouts`, `AuthLayouts`, `TagList`,
`ToastProvider`/store e layouts de confirmação. `RootLayout` deve continuar sendo a moldura
do chat. `SettingsLayouts` deve continuar sendo a moldura de settings e admin.

### Inventário por nível de composição

| Nível | Local | Papel atual | Regra para TON |
|---|---|---|---|
| Primitivos/componentes | `web/lib/opal/src/components/` e `@opal/components` | Botões, texto, inputs, tabela, modal, popover, feedback, ícones e tokens de componente. | Preferir sem alteração; usar somente props e variantes documentadas no README do componente. |
| Compostos de produção | `web/src/refresh-components/` | File picker, campos de formulário, avatares, cards, skeletons, command menu e wrappers. | Reutilizar com props ou pequena variante. Não duplicar uma peça em `web/src`. |
| Padrões de página | `web/src/sections/`, `web/src/layouts/`, `web/src/views/` | Shell, chat, sidebar, settings, knowledge, agentes, auth e admin. | Compor páginas TON a partir destes padrões; não criar casca paralela. |
| Legado | `web/src/components/` e classes CSS específicas em `web/src/app/` | Componentes antigos ainda usados por auth, admin, chat e EE. | Não adicionar novas dependências. Corrigir somente quando a rota fizer parte do fluxo TON. |
| Utilitários de estilo | `@opal/utils` (`cn`), `web/lib/opal/tailwind-preset.cjs`, CSS Opal e tokens compartilhados | Combinação de classes, exportação de tokens e estilos base. | Usar classes semânticas e propriedades lógicas; não usar cores Tailwind incorporadas nem `dark:`. |

### Inventário dos recursos visuais

| Recurso | Fonte observada | Uso seguro |
|---|---|---|
| Ícones | `@opal/icons` e `web/lib/opal/src/icons/` | Usar o ícone existente com nome/tooltip acessível; importar do Figma somente quando faltar. |
| Tipografia | `Text`/presets Opal, `Hanken_Grotesk`, `DM_Mono` e KH Teka | Declarar `font` e `color` em `Text`; manter fontes atuais antes de adicionar outra. |
| Cor | `web/lib/shared/tokens/primitives.json`, `semantic-light.json`, `semantic-dark.json` e `web/lib/opal/tailwind-preset.cjs` | Alterar tokens semânticos em conjunto; não codificar cor em tela. |
| Radius | `web/lib/shared/tokens/size.json` e classes semânticas exportadas pelo preset | Reutilizar a escala; não introduzir valores isolados. |
| Espaçamento | `size.json`, props de layout Opal e classes utilitárias | Preferir `padding` e props do componente antes de wrappers e margens. |
| Bordas | Tokens semânticos `border-*` e estilos das variantes Opal | Preferir borda/surface contrast para elevação contida; não usar hex local. |
| Elevação/sombra | `web/lib/shared/tokens/shadow.json`, `ShadowDiv` e variantes de layout | Manter elevação em modal/popover; revisar sombras expressivas de surfaces comuns. |
| Layout | `RootLayout`, `SidebarLayouts`, `SettingsLayouts`, `AuthLayouts`, `Content`, `Section` e `Card` | Compor com layouts existentes e preservar o contrato mobile/RTL. |

`@opal/core` fornece primitivas internas como `Disabled` e `Interactive`. O
guia do frontend proíbe uso direto dessas primitivas pela aplicação, exceto
`Hoverable`, que já é usado para revelar ações de arquivos e sidebar.

## Padrões observados nas superfícies TON

- `web/src/views/AppPage.tsx` combina `ChatUI`, `SearchUI`, project UI,
  `AppInputBar` e painel de fontes sem um componente de tela alternativo.
- `web/src/layouts/chromes/AppChrome.tsx` fornece header, largura, background,
  painéis e footer.
- `web/src/sections/sidebar/AppSidebar.tsx` e `AdminSidebar.tsx` usam layouts
  de sidebar, tabs e botões Opal.
- `web/src/sections/input/AppInputBar.tsx` usa contenteditable e controles Opal
  para upload, tools, voz, pesquisa e envio.
- `web/src/refresh-components/popovers/FilePickerPopover.tsx` usa
  `LineItemButton`, `PopoverMenu`, `Text`, `Button`, `Hoverable` e icons Opal.
- `web/src/sections/modals/UserFilesModal.tsx` usa `Modal`, `InputTypeIn`,
  `AttachmentItemButton`, `Button`, `Section` e `ScrollIndicatorDiv`.
- `web/src/sections/knowledge/agent-knowledge/*` e
  `SourceHierarchyBrowser.tsx` compõem a seleção de conhecimento.
- `web/src/sections/onboarding/OnboardingFlow.tsx` fornece onboarding embutido.

Esses pontos são os locais de adaptação. Não se deve substituir o composer,
chat ou sidebar por uma cópia TON sem uma mudança de nível 4 ou 5.

## Tokens e semântica

Os tokens vivem em `web/lib/shared/tokens/`:

- `primitives.json`: escalas neutras e cromáticas.
- `semantic-light.json` e `semantic-dark.json`: texto, background, border,
  action, status, theme, mask e shadow por modo.
- `size.json`: métricas de linha, fonte, padding, espaçamento e radius.
- `shadow.json`: `box-00`, `box-01` e `box-02`.
- `typography.json` e `typography-presets.json`: família, peso, tamanho e
  presets.

`web/lib/opal/tailwind-preset.cjs` expõe tokens semânticos no Tailwind. Os
prefixos existentes incluem texto (`text-05` e similares), backgrounds,
borders, actions, themes, status, shadow, masks, radius, box shadow e blur.
`web/lib/opal/src/_reference.css` importa os tokens compartilhados e
`web/lib/opal/src/root.css` importa tamanhos, tipografia e z-index.

O mesmo preset fornece as utilities de border e elevação usadas pelas telas.
`cn` e `@opal/utils` são o caminho esperado para compor classes. O guia do
frontend também exige `Button`/inputs Opal ou refresh, sem elementos raw novos,
e exige propriedades lógicas para layouts que suportam RTL.

Regra TON: alterar primitives e mapeamento semântico em conjunto, validar light
e dark e usar classes semânticas na tela. Não usar cores Tailwind incorporadas
nem adicionar `dark:`; o guia do frontend exige tokens semânticos.

## Tipografia

`web/src/app/layout.tsx` carrega `Hanken_Grotesk` e `DM_Mono`. A camada Opal
possui fontes KH Teka em `web/lib/opal/src/styles/typography.css` e fontes OTF
em `web/public/fonts/KHTeka*.otf`. O produto deve escolher uma hierarquia TON
com as famílias já disponíveis antes de incluir fonte nova.

O componente `Text` deve declarar font e color. Texto que aparece em markdown
deve usar `string | RichStr`, conforme `web/AGENTS.md`. Copy de TON deve usar
`next-intl`; não colocar texto literal em `web/src`.

Plano seguro de tipo:

- título de shell e página: preset Opal de heading;
- body e labels de controle: preset body Opal;
- metadata e extensões: secondary body/mono já usados pelo picker;
- código, IDs e métricas: `DM_Mono` ou preset mono;
- markdown: `CompactMarkdown` e estilos existentes.

## Espaçamento, radius e sombras

`size.json` registra escala de spacing em blocos de 4, 6, 8, 10, 12, 16, 20,
24, 28, 32 e valores maiores, além de espaçamento inline. Também registra
`radius-02` (0.125rem), `radius-04` (0.25rem), `radius-08` (0.5rem),
`radius-12` (0.75rem), `radius-16` (1rem), `radius-20` (1.25rem) e
`radius-round`.

`shadow.json` define `box-00` (linha sutil), `box-01` (2px/12px) e `box-02`
(2px/24px). `AppChrome` usa padding e sombra dinâmica para acomodar o input;
essa interação deve ser validada no chat e no mobile.

Para TON:

- usar `size.json` para gap e padding;
- usar radius semântico, não valores isolados por tela;
- usar `box-01`/`box-02` somente quando a hierarquia exigir elevação;
- manter cards e inputs com a densidade Opal atual;
- documentar qualquer novo valor antes de adicioná-lo.

## Ícones, logos e ilustrações

`web/lib/opal/src/icons` é a fonte de ícones. Botões devem receber ícone Opal e
tooltip/label acessível. Não usar SVG inline novo em telas TON.

Logos ficam em `web/lib/opal/src/logos`; a marca atual também aparece em
`web/src/lib/app/components.tsx` (`Logo`, `SvgOnyxLogo`) e no account popover.
Não há ativo oficial TON/Logo Vale Norte no inventário. Até a aprovação do
arquivo, usar um ponto de integração de logo existente e não inventar uma marca
final em código.

Ilustrações e estados vazios devem reutilizar `IllustrationContent` e
`web/lib/opal/src/illustrations`. O estado “nenhuma fonte” não deve parecer
erro: `useAvailableSources` pode retornar vazio após falha e a UI precisa
separar `loading`, `error` e `empty`.

## Responsividade do sistema

Breakpoints do `web/tailwind-themes/tailwind.config.js`:

| Chave | Largura |
|---|---:|
| `sm` | 724px |
| `md` | 912px |
| `lg` | 1232px |
| `2xl` | 1420px |
| `3xl` | 1700px |
| `4xl` | 2000px |

`useScreenSize` usa os breakpoints Opal para mobile/small/medium/large.
`web/lib/opal/src/layouts/sidebar/styles.css` torna a sidebar overlay em
medium e mobile, com backdrop; `root/styles.css` mantém altura dinâmica e um
slot de scroll. Use propriedades lógicas para start/end e padding inline.

## Dívida visual e de adoção

O estado atual ainda contém imports antigos de `@/components` em auth, ChatUI,
admin, providers e páginas EE. Também há cores hex de scrollbar e classes
legadas em áreas fora de Opal. Isso é dívida de migração, não justificativa
para uma migração ampla durante o rebrand.

Itens para revisão visual:

- `web/src/app/globals.css`: scrollbar, markdown e utilitários globais.
- `web/src/components/ui/*`: componentes fora da ordem de autoridade.
- `web/src/app/ee/admin/theme/*`: inputs e controles de white-label.
- `web/src/layouts/chromes/AppChrome.tsx`: backgrounds customizados, vignette,
  shadow e footer.
- `web/src/sections/input/*`: contenteditable, drop zone, fila e estados de
  upload.
- `web/src/sections/chat/*`: streaming, citations, code/image/file renderers.

Classificação de mudança:

| Nível | Alteração | Exemplo |
|---|---|---|
| 0 | Copy, texto ou configuração | Labels TON, descrição de agente e metadata. |
| 1 | Ajuste de tema ou token | Tokens Vale Norte, logo e light/dark. |
| 2 | Composição ou variante pequena | Item de nav, modal ou variante Opal. |
| 3 | Nova página TON usando o sistema existente | Futura tela de ocorrência ou relatório. |
| 4 | Mudança estrutural de frontend | Fluxo que cruza cascas e contratos atuais. |
| 5 | Reescrita do design system ou da arquitetura | Substituição da arquitetura visual ou de frontend. |

Fase inicial: níveis 0–3. Toda exceção precisa registrar componente, motivo,
status de substituição e cobertura de teste.

## Checklist para cada tela TON

1. Escolher componente Opal existente.
2. Usar token semântico para cor, tamanho, radius e sombra.
3. Usar `Text` com preset e cor declarados.
4. Usar ícone Opal e label/tooltip acessível.
5. Adicionar copy ao `web/src/i18n/messages/en.json` e manter catálogos.
6. Usar classes lógicas para RTL e layout.
7. Testar desktop, mobile, light, dark, loading, empty e error.
8. Testar flag ligada e desligada quando houver flag.
9. Verificar CE/EE e permissão antes de mostrar a entrada.
10. Rodar type coverage e testes do comportamento alterado.

## Ferramentas e testes

`web/package.json` fornece Bun, Oxlint, Oxfmt, type check, Jest/RTL,
Playwright e Storybook. Use os testes co-localizados descritos em
`web/tests/README.md`. Para e2e, crie Page Object em `web/tests/e2e/pages` e
use locators acessíveis conforme `web/tests/e2e/README.md`.

Para a identidade TON, a matriz mínima é: shell, sidebar, settings, login,
welcome, composer, modal de arquivos, painel de fontes e admin theme em
viewport desktop e mobile, cada um em light e dark. Validar foco, contraste,
leitura por teclado, truncamento, overflow e RTL. Preferir testes de comportamento
e poucas imagens de referência. Não criar snapshots de toda a árvore.
