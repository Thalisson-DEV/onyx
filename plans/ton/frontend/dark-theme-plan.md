# TON frontend: plano de tema escuro

## Estado atual

O tema já tem uma infraestrutura funcional:

- `web/src/app/layout.tsx` monta `ThemeProvider` de `next-themes` com
  `attribute="class"`, `defaultTheme="system"` e `enableSystem`.
- `web/lib/shared/tokens/semantic-light.json` e `semantic-dark.json` fornecem
  semântica por modo.
- `web/lib/opal/tailwind-preset.cjs` mapeia cores, radius, sombras e masks.
- `web/src/app/globals.css` importa `@onyx-ai/opal/root.css`.
- `web/src/app/app/settings/general` expõe aparência e escolha de background.
- `web/tests/e2e/utils/theme.ts` define o localStorage `theme` para e2e.

O plano completa o mapeamento TON usando os tokens atuais. Não criar uma folha
escura paralela, nem espalhar regras `dark:` pelas telas.

## Princípios

1. O modo escuro é uma variação semântica do mesmo sistema.
2. Verde institucional continua ação ou identidade, não superfície dominante.
3. Dourado é acento contido. Não substituir success, warning ou danger.
4. Neutros controlam fundo, texto e borda. Evitar preto e branco absolutos.
5. Componentes Opal são a autoridade. Legacy recebe revisão somente ao tocar a
   tela.
6. Usar tokens e classes semânticas. `web/AGENTS.md` proíbe novos `dark:` e
   cores Tailwind incorporadas na aplicação.

## Mapeamento de tokens a decidir

Os valores abaixo são papéis, não hex finais. Os valores devem ser aprovados
por design e registrados em `primitives.json` e nos dois arquivos semânticos.

| Papel | Light | Dark | Nota TON |
|---|---|---|---|
| Canvas | Neutro claro | Neutro profundo, não preto absoluto | Manter leitura longa do chat. |
| Surface | Neutro de painel | Neutro elevado | Sidebar, cards, composer e modal. |
| Text primary | Neutro escuro | Neutro claro | Contraste forte sem branco puro. |
| Text secondary | Neutro médio | Neutro claro reduzido | Timestamps, extensões e ajuda. |
| Border | Neutro baixo contraste | Neutro visível | Separar sem grades fortes. |
| Action | Verde institucional | Verde ajustado para contraste | Botão, link, seleção e foco. |
| Action support | Verde suave | Verde profundo/contorno | Hover e estados secundários. |
| Accent | Dourado contido | Dourado ajustado | Destaque institucional, sem estado de erro. |
| Success | Semântico verde status | Verde status distinto da marca | Não confundir marca com sucesso. |
| Warning | Âmbar existente | Âmbar mais claro | Upload, licença e atenção. |
| Danger | Vermelho existente | Vermelho mais claro | Delete, auth e erro. |
| Focus | Ring semântico | Ring claro e forte | Teclado e a11y. |
| Overlay | Mask existente | Mask escurecida/translúcida | Modal, sidebar e sources. |
| Shadow | `shadow.*` Opal | Sombra mais discreta + border | Dark não deve virar halo. |

Não adicionar alias TON em cada componente. Criar aliases somente quando um
papel semântico não existir. Preservar nomes e contratos de Opal evita um fork.

## Áreas com maior risco visual

### Shell e navegação

`AppChrome` aplica background, vignette, backdrop, footer e padding de sombra.
`AppSidebar` e `AdminSidebar` usam overlay e estado folded. Confirmar texto,
ícones, dividers e foco em ambos os modos. O backdrop mobile deve separar o
conteúdo sem esconder o foco ativo.

### Chat e composer

`AppPage`, `ChatUI`, `ChatScrollContainer`, `AppInputBar` e renderizadores de
mensagem têm estados de streaming, code, image, file, reasoning e citations.
Testar superfícies para mensagens, markdown, links, code blocks, attachments,
fila e stop/send. Inputs contenteditable não podem perder cursor ou contraste.

### Fontes, arquivos e projetos

`DocumentsSidebar`, `FilePickerPopover`, `UserFilesModal` e
`ProjectContextPanel` usam estados selected, loading, processing, delete,
empty e error. Verificar que a extensão de arquivo, status e ações de hover são
legíveis. Sombra e mask de modal devem funcionar em dark.

### Settings, auth e admin

`SettingsLayouts` tem navegação por sidebar ou select mobile. `AuthLayouts` e
`LoginPage` precisam de background, inputs e CAPTCHA legíveis. `AdminChrome`,
tables, disabled tier entries e `AppearanceThemeSettings` exigem a mesma
semântica; EE não pode introduzir sua própria paleta semântica.

## Implementação planejada

1. Inventariar usos diretos de cor e sombra com `rg` antes de mudar tokens.
2. Aprovar paleta Vale Norte e pares de contraste.
3. Atualizar primitives e semântica light/dark em conjunto.
4. Verificar exportação no `tailwind-preset.cjs` e `root.css`.
5. Testar Opal e refresh components em isolamento.
6. Corrigir somente bypasses nas telas tocadas: hex, built-in color e sombra
   manual; não iniciar migração de todo `web/src/components`.
7. Validar shell, chat, composer, files, sources, projects, agents, settings,
   auth e admin theme.
8. Remover ou adaptar backgrounds Onyx em `AppChrome` após decisão de marca.

## Acessibilidade e critérios

O mínimo para aceitar dark é:

- texto principal e controles com contraste WCAG aplicável;
- foco visível em teclado contra surface clara e escura;
- estados disabled ainda distinguíveis por texto/estrutura;
- links e ações não dependentes apenas de cor;
- erros, warnings e success com ícone ou copy além da cor;
- overlays sem cortar diálogo, tooltip ou menu;
- conteúdo markdown, code e imagens legíveis;
- `prefers-color-scheme` funciona via `system`;
- usuário pode escolher light, dark ou system sem flicker visível.

Contraste deve ser medido nos pares de tokens finais. A paleta não é aceita por
aparência subjetiva somente.

## Flags e CE/EE

Tema não deve depender de uma flag de produto. A escolha light/dark já é um
estado de preferência. Uma flag TON pode controlar apenas rollout de uma paleta
aprovada no entry point global e deve ter teste on/off e plano de remoção.

Admin theme é uma superfície EE (`web/src/app/ee/admin/theme`). Seu acesso
continua em `proxy.ts`, `ee/layout.tsx` e `paidTierGated`; não usar esse route
para liberar tokens para CE. A aparência padrão TON deve funcionar sem licença
EE. Billing e upgrade permanecem ocultos ao cliente TON quando não fizerem
parte do produto.

## Bypasses a auditar

- `web/src/app/globals.css`: cores de scrollbar e utilitários.
- usos legados `@/components` em auth, ChatUI, admin e EE.
- classes built-in e hex encontradas em `web/src`.
- backgrounds, vignette e shadow em `AppChrome`.
- input file oculto e estados de arquivos em `FilePickerPopover` e
  `UserFilesModal`.
- imagens e ilustrações com fundo próprio.
- banners de billing e licença.

Registrar cada bypass com arquivo, papel semântico, risco e decisão. Não mudar
um bypass apenas para deixar o diff maior.

## Testes e tooling

Use Jest/RTL para resolver o modo e estados de fallback. Use Playwright com o
helper de tema e Page Objects. A cobertura mínima é:

| Área | Light | Dark | Mobile |
|---|---:|---:|---:|
| Login/signup | ✓ | ✓ | ✓ |
| App shell/sidebar | ✓ | ✓ | ✓ |
| Chat/composer/streaming | ✓ | ✓ | ✓ |
| Files/projects/sources | ✓ | ✓ | ✓ |
| Agents/settings | ✓ | ✓ | ✓ |
| Admin/theme/disabled tiers | ✓ | ✓ | ✓ |
| Shared chat | ✓ | ✓ | ✓ |

Adicionar checks de contraste e foco aos testes a11y. Fazer screenshots de
referência somente de shell, sidebar, chat, composer, settings e auth. Rodar
`bun run types:check`, lint/format e o conjunto e2e relacionado em cada mudança.

## Entregáveis e backlog

- `TON-DARK-01`: aprovar pares e papéis da paleta.
- `TON-DARK-02`: atualizar tokens light/dark e exportações Opal.
- `TON-DARK-03`: auditar bypasses em shell/chat/files/settings/admin.
- `TON-DARK-04`: visual e a11y desktop/mobile.
- `TON-DARK-05`: validar `system`, persistência e ausência de flicker.
- `TON-DARK-06`: registrar exceções legacy e evitar escopo de migração ampla.

