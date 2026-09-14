# TON frontend: auditoria mobile

## Escopo

Esta auditoria cobre o web app responsivo. Não propõe app nativo, offline ou
novo backend. O produto deve continuar online e usar as APIs existentes através
do frontend. Não foram feitas alterações de código.

## Contrato responsivo observado

Os breakpoints em `web/tailwind-themes/tailwind.config.js` são `sm=724px`,
`md=912px`, `lg=1232px`, `2xl=1420px`, `3xl=1700px` e `4xl=2000px`.
`web/src/hooks/useScreenSize.ts` expõe `isMobile`, `isSmall`, `isMedium` e
`isLarge`. No SSR, `isMobile` começa falso até a montagem; uma tela não deve
usar esse valor para autorização ou carga de dados.

O layout Opal define o comportamento em
`web/lib/opal/src/layouts/sidebar/README.md` e `styles.css`:

- desktop: sidebar flexível, dobrável;
- medium: sidebar fixa com overlay e spacer;
- mobile: overlay de altura total, backdrop borrado e conteúdo principal;
- body da sidebar preserva rolagem em `sessionStorage`;
- `root/styles.css` usa `h-dvh`, desativa scroll duplicado e mantém um slot.

Usar `start/end`, padding inline e `dir` lógico. O `DirectionProvider` e o
locale árabe tornam RTL parte da matriz, não um caso opcional.

## Evidência por fluxo

| Fluxo | Suporte existente | Risco/gap a validar |
|---|---|---|
| App shell | `AppChrome` abre sidebar por botão em mobile; shell usa `RootLayout` | Header, backdrop, foco e retorno ao conteúdo. |
| App sidebar | `SidebarLayouts.Root foldable` e overlay Opal | DnD de agentes/projetos em touch, recents longos e fechamento após navegação. |
| Chat | `AppPage` usa grid e modal de sources no mobile | Altura do teclado virtual, scroll único, streaming e mensagens longas. |
| Composer | `AppInputBar` suporta contenteditable, upload, voz, fila e drop | Drop não existe em touch; toolbar pode exceder a largura; foco/cursor. |
| Histórico | Recents na sidebar e `ChatSearchCommandMenu` | Abertura/fechamento da sidebar e filtros em viewport estreito. |
| Projetos | `ProjectContextPanel` tem botão mobile “view files” | Token count, card, drag/drop e modal de arquivos. |
| Arquivos | `UserFilesModal` e picker usam modal com busca | Input file, tamanho de modal, delete e status processing. |
| Sources | `DocumentsSidebar` vira modal em mobile | Backdrop, foco, seleção e retorno ao message node. |
| Knowledge | `KnowledgeTwoColumnView` + `KnowledgeSidebar` | Colunas devem virar fluxo empilhado; confirmar em viewport real. |
| Agents | `AgentsNavigationPage` com SettingsLayouts | Filtros, editor, upload avatar e campos longos. |
| Settings | Select de nav abaixo de `sm`; sidebar acima | Dropdown e foco; tabs longas; scroll do conteúdo. |
| Admin | `AdminChrome` abre sidebar mobile | Tables, connectors, forms e banners precisam de overflow testado. |
| Auth | `AuthLayouts` e páginas dedicadas | Teclado virtual, CAPTCHA, mensagens e links sem clipping. |
| Onboarding | Fluxo embutido em `AppPage` | Etapas, modal/input e progresso sem esconder composer. |

## Composer e arquivos: distinção necessária

`FilePickerPopover.tsx` oferece upload, arquivos recentes e modal de todos os
arquivos. `UserFilesModal.tsx` oferece busca, seleção, visualização e delete.
`ProjectsProvider` mantém `currentMessageFiles`, arquivos de projeto e recentes.

No mobile, o texto futuro deve distinguir, sem atribuir retenção que o backend
ainda não declarou:

- **Arquivo da mensagem:** anexado ao contexto da sessão/mensagem. Só deve ser
  chamado de temporário se o backend confirmar esse escopo e sua limpeza.
- **Arquivo persistente:** arquivo de projeto ou arquivo reutilizável indicado
  pelo servidor. Tem status, associações, visualização e exclusão controlada;
  arquivos recentes não provam retenção por si só.

O input file oculto permite `multiple`, mas o fluxo precisa de feedback claro
para `uploading`, `processing`, `completed`, `failed` e `deleting`. O picker
usa `accept="*/*"`; a revisão de produto deve decidir se há limites por tipo,
sem mudar o contrato por acidente.

## Gaps de interação mobile

### Navegação

Verificar que o botão abre a sidebar com nome acessível, coloca foco no painel,
fecha com Escape e restaura foco ao trigger. Verificar backdrop e navegação para
chat, projeto, agente, settings e admin. DnD no sidebar não deve ser a única
forma de ordenar ou mover.

### Chat e rolagem

Usar o slot de scroll do root. Não adicionar segundo scroll para mensagens.
Testar mensagem em streaming, code block, imagem, citation, source panel,
queue, stop/send, error e session not found. Validar `100dvh` quando o teclado
virtual aparece e quando o composer cresce.

### Composer

Confirmar toolbar horizontal ou quebra aceitável. Os botões de attach, tools,
deep research, multi-model, microphone e send precisam de label e target de
toque. O foco do contenteditable deve sobreviver à abertura de picker e modal.
Drag-and-drop é desktop; o equivalente mobile é o picker de arquivos.

### Projetos, sources e knowledge

Modal de fontes deve manter seleção e permitir retorno ao chat. O painel de
projeto deve ter CTA “view files” claro e não depender de hover. Knowledge deve
oferecer caminho linear para selecionar pasta/documento. Empty, loading e error
devem ocupar a largura disponível.

### Admin e settings

`SettingsLayouts` troca sidebar por dropdown em viewport abaixo de `sm`.
Testar labels longos, locale alemão/árabe, campos de conectores, tables e
mensagens de licença. No admin, o trigger mobile deve respeitar permissão; não
mostrar rota proibida só porque a sidebar abriu.

## O que não fazer nesta fase

- Não adicionar service worker, cache offline ou sincronização local.
- Não criar rota mobile separada.
- Não substituir Opal sidebar/root por navegação nova.
- Não trocar DnD desktop por uma implementação sem decisão de UX.
- Não esconder erro como estado vazio em connectors/knowledge.
- Não alterar endpoints para resolver layout.
- Não remover i18n, RTL ou comportamento CE/EE para simplificar mobile.

## Matriz de teste manual

Executar com o app online e dados de teste:

| Caso | Viewport sugerido | Resultado esperado |
|---|---|---|
| iPhone estreito | 375×812 | Sidebar overlay, composer utilizável, no clipping. |
| Android largo | 412×915 | Arquivo, modal e sources cabem com teclado. |
| Tablet portrait | 768×1024 | Regra medium consistente e painel acessível. |
| Tablet landscape | 1024×768 | Chat e sidebar sem segundo scroll. |
| Desktop base | 1280×720 | Comparar com e2e e shell atual. |
| RTL | 375×812 + árabe | Start/end, icons e focus corretos. |

Para cada viewport: abrir/fechar sidebar; iniciar chat; enviar/stop; selecionar
arquivo no escopo da mensagem; abrir arquivo reutilizável somente quando o
servidor declarar esse escopo; abrir sources; abrir projeto;
buscar histórico; abrir agents; visitar settings; visitar admin; alternar tema;
passar por onboarding; entrar/sair.

## Testes automatizados existentes e lacunas

Já existem `web/tests/e2e/admin/admin_mobile_sidebar.spec.ts`, testes de input,
foco, upload, project files, sidebar e welcome no diretório `chat`, além de
`settings_pages.spec.ts`, `onboarding_flow.spec.ts` e testes de theme. A regra
e2e em `web/tests/e2e/README.md` exige Page Objects em
`web/tests/e2e/pages`, locators acessíveis e matchers que aguardam.

Lacunas TON para adicionar quando a tela mudar:

- POM para sidebar do app, chat e composer em mobile.
- POM para picker/modal de arquivos e painel de sources.
- POM para projeto com arquivo no escopo da mensagem e arquivo persistente
  somente quando esse escopo for declarado pelo servidor.
- POM para settings dropdown e admin mobile.
- casos light/dark, flags off/on, CE/EE e RTL.
- asserts de foco, aria-label, overflow, loading/error/empty e teclado.

Jest/RTL pode cobrir mapeamento de breakpoint e visibilidade por flag. Playwright
deve validar comportamento real. Visual regression deve focar shell, composer,
sidebar e modal; evitar snapshots gerais.

## Backlog mobile

- `TON-MOBILE-01`: executar matriz de viewport e registrar falhas por fluxo.
- `TON-MOBILE-02`: validar foco de sidebar, modal e source panel.
- `TON-MOBILE-03`: revisar altura dinâmica e teclado no composer.
- `TON-MOBILE-04`: separar copy de arquivo de mensagem e arquivo persistente
  somente após o contrato do servidor definir retenção e limpeza.
- `TON-MOBILE-05`: cobrir knowledge e connectors sem estado vazio enganoso.
- `TON-MOBILE-06`: cobrir settings/admin com labels longos e RTL.
- `TON-MOBILE-07`: adicionar e2e/POM somente para falhas confirmadas.
- `TON-MOBILE-08`: validar dark theme em backdrop, modal, source e composer.

## Critérios de aceite

Mobile está pronto quando os fluxos de login, onboarding, chat, composer,
histórico, projetos, arquivos, knowledge, agents, settings e admin funcionarem
online em 375px e 412px sem clipping, scroll duplo, perda de foco ou ação
dependente de hover. O mesmo conteúdo deve funcionar em 768px e RTL. O resultado
deve conservar os contratos atuais e não criar uma plataforma offline.

## Classificação do audit

| Estado | Evidência |
|---|---|
| Já funciona | Sidebar overlay, root com `dvh` e slot único de scroll, modal de sources, picker de arquivos, project files mobile e settings dropdown. |
| Pequena adaptação provável | Labels e targets de toque, foco de overlay/modal, copy de escopo de mensagem/persistência declarada, overflow de toolbar e status de upload. |
| Precisa de verificação | Teclado virtual com composer, DnD em touch, knowledge de duas colunas, tables/admin, RTL, dark backdrop e restauração de foco. |
| Estrutural somente se comprovado | Novo domínio mobile, persistência offline, rota separada ou mudança de breakpoints. Nenhum é justificado pela inspeção atual. |

Esta classificação evita transformar gaps de QA em rewrite. A evidência de falha
deve incluir viewport, estado, rota e passos reproduzíveis antes de considerar
Level 4 ou 5.
