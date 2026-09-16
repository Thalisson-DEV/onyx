# TON — mensagens, streaming e atividade de ferramenta (VIS-006)

## Estado

**DONE.** Implementação e validação concluídas.

Baseline: `c2add0aea5`. Worktree: `C:\Users\Thalisson\Documents\ton-vis-006`.
Branch: `ton/vis-006`.

## Componentes

| Área | Componentes |
|---|---|
| Largura e mensagem humana | `ChatUI`, `HumanMessage` |
| Resposta | `MessageTextRenderer`, `markdownUtils`, `MinimalMarkdown` |
| Markdown e código | `custom-code-styles.css`, `CodeBlock` |
| Ações | `MessageToolbar` |
| Timeline | `AgentTimeline`, headers, `ActivityIndicator`, `ActivityStatus` |
| Raciocínio privado | `ReasoningRenderer`, `CodingAgentRenderer` |
| Ferramentas | `CustomToolRenderer`, `toolDisplayHelpers` |
| Erro | `Resubmit`, `ErrorBanner`, `RateLimitBanner` |

## Mapa de pacotes

| Pacote observável | Texto permitido |
|---|---|
| `SEARCH_TOOL_START` com busca interna | Consultando fontes… |
| `SEARCH_TOOL_START` com internet | Pesquisando na web… |
| `FETCH_TOOL_START` | Abrindo endereços… |
| `PYTHON_TOOL_START` | Executando código… |
| `FILE_READER_START` | Lendo arquivo… |
| `CUSTOM_TOOL_START` | Executando `{toolName}`… |
| `IMAGE_GENERATION_TOOL_START` | Gerando imagens… |
| `MEMORY_TOOL_START` | Atualizando memória… |
| `DEEP_RESEARCH_PLAN_START` | Montando plano… |
| `RESEARCH_AGENT_START` | Pesquisando… |
| `REASONING_START` | Processando… |
| Pacote sem mapeamento seguro | Processando… |

O fallback informa somente que o runtime está ativo. Ele não inventa uma ação.

## Rótulos rejeitados

“Analisando contrato”, “Executando regra”, “Comparando dados” e “Validando
competência” foram rejeitados. Os pacotes não provam essas ações.

“Pensando” também foi removido. Esse texto descrevia introspecção, não operação.

## Raciocínio privado

Antes, `ReasoningRenderer` concatenava `REASONING_DELTA`. Ele mostrava o texto
em Markdown e oferecia uma tela de texto completo com cópia e download.

Agora, o renderizador lê somente tipos de pacote. Ele mostra os estados
`running`, `completed` ou `failed`. Ele nunca lê o campo `reasoning`.

`CodingAgentRenderer` também não lê o conteúdo de
`CODING_AGENT_THINKING_DELTA`. Ele mantém somente um passo operacional sem corpo.

Não existe caminho de download, cópia, modal, tooltip ou texto oculto para o
raciocínio privado.

## Mensagem humana e resposta

`HumanMessage` usa `bg-surface`, `radius-08`, espaçamento compacto e alinhamento
ao fim. A cauda assimétrica foi removida. Anexos continuam em `FileDisplay`, sem
alterar o contrato de VIS-005.

`ChatUI` usa `md:max-w-reading`. O valor continua em 45rem. A resposta do
assistente continua sem bolha. A hierarquia vem da tipografia.

## Markdown

Todos os caminhos da conversa usam `prose-ton`. O caminho `prose-onyx` e
`dark:prose-invert` foram removidos da mensagem e da timeline.

Os headings têm escala, peso, cor e ritmo distintos. Listas, links, citações e
blocos de citação usam propriedades lógicas e tokens semânticos.

A tabela usa uma grade de 1px, cabeçalho distinto, números tabulares e células
compactas. O contêiner rola no eixo horizontal em telas estreitas. A página não
recebe a largura da tabela.

## Código

O tema Atom One com cores hex foi removido. O highlight usa os tokens
`code-code`, `code-comment`, `code-keyword`, `code-string`, `code-number` e
`code-definition` nos dois temas.

O scrollbar usa tokens neutros. Ele não tem glow. `CodeBlock` usa o
`CopyButton` do Opal e mantém o texto traduzido do aplicativo.

## Erro e limite

`Resubmit` e `ErrorBanner` usam texto, borda, superfície e tipografia semânticos.
O detalhe técnico fica recolhido. `RateLimitBanner` formata data e hora com
`useFormatter`.

## Atividade e ferramentas

`ActivityIndicator` substitui o shimmer contínuo por um loader contido e texto
estável. O loader respeita movimento reduzido. `BlinkingBar` também para a
animação com movimento reduzido, mas mantém o caret funcional.

`ActivityStatus` expõe estado por texto oculto, ícone e atributo de teste. Um
custom tool deriva falha de `CUSTOM_TOOL_DELTA.error` ou de `ERROR`. Detalhes
JSON só entram no DOM quando o passo está expandido.

O `SvgSparkle` foi removido do agente de código. O estado usa ícones de execução.

## Toolbar e cabeçalhos

As ações do `MessageToolbar` ficam visíveis. Esta decisão é intencional. O
estado oculto de `Hoverable` usa `pointer-events: none` e quebraria clique,
teclado, toque e os contratos Playwright existentes.

O toolbar tem `role="group"` e nome traduzido. `CompletedHeader` e
`StoppedHeader` deixam a linha como apresentação. Somente o `Button` expande a
timeline. Não existe controle interativo aninhado.

## Citações e anexos

`SourceTag`, mapas de citação e apresentação de fontes não mudaram. A superfície
já usa tokens e foco global. `FileDisplay` continua sendo o caminho de anexos da
mensagem humana. Os testes de VIS-005 continuam verdes.

## Contratos preservados

Não houve mudança em `usePacketProcessor`, `useTypewriter`,
`useSmoothStreaming`, esquema de pacote, IDs, persistência, cancelamento ou no
contrato `children([...])`.

`revealedCharCount`, `isAudioSyncActive` e `isAwaitingAutoPlaybackStart`
continuam no caminho de voz. O placeholder novo usa os mesmos gates existentes.

## Testes

Testes focados cobrem vazamento de um e vários deltas, raciocínio com resposta,
ferramenta e erro, ausência de exportação, estados de ferramenta, mapeamento de
pacote, fallback genérico, geometria, Markdown, tabela, cópia, erro, toolbar,
cabeçalhos e anexos.

Resultado: 4 suítes focadas, 24 testes, todos verdes. A regressão executou 12
suítes e 401 testes, todos verdes.

`bun run types:check`: verde, sem erro, cobertura 98,81%. `bun run lint`: verde,
somente avisos preexistentes do repositório. `bun run build`: verde.

## Validação responsiva e acessível

O runtime local recebeu uma imagem construída deste worktree. O container
`onyx-web_server-1` ficou saudável e a porta 3000 respondeu HTTP 200.

Uma conversa real validou mensagem longa do usuário, H1, H2, lista, citação,
tabela, link, bloco TypeScript, CopyButton, toolbar e timeline concluída.

Medições em 375, 768 e 1280, nos temas claro e escuro, deram overflow horizontal
de página igual a zero. Em 375, a tabela rolou dentro de 335px, com conteúdo de
446px. Em 768 e 1280, ela coube sem rolagem ativa. O toolbar manteve quatro
botões visíveis nos seis pares.

No claro, o canvas mediu `rgb(250, 250, 250)` e a mensagem humana
`rgb(240, 240, 240)`. No escuro, mediu `rgb(51, 51, 51)` e
`rgb(64, 64, 64)`. O bloco de código escuro mediu `rgb(31, 31, 31)`.

O snapshot acessível reconheceu H1/H2, link, botão Copy, botão de expansão e o
estado “Completed”. O teste RTL temporário manteve overflow zero e a tabela com
`overflow-x: auto`. Nenhum texto de raciocínio privado apareceu no DOM.

O upload de anexo pela automação do navegador foi bloqueado pela restrição de
caminho do processo Chrome. Não houve contorno que alterasse a configuração.
`attachmentVisualContract`, `FileCard`, `dropzonePaste` e a asserção de
`FileDisplay` cobrem a preservação de VIS-005.

Estados running, completed e failed de ferramenta e erro foram validados em RTL
isolado. O runtime real produziu e validou o estado completed. Não foi inventado
um gatilho de falha ou ferramenta para obter uma captura decorativa.

## Trabalho diferido

- VIS-009 pode ligar o caret a tokens de movimento próprios.
- VIS-008 continua dona da arquitetura de voz.
- VIS-003 e VIS-007 continuam fora desta fatia.

## Conflitos prováveis

- `MessageToolbar` também pertence ao corte de TTS em VIS-008.
- `custom-code-styles.css` conflita com qualquer mudança global de Markdown.
- Os nove catálogos conflitam textualmente com outras fatias de copy.
- Renderizadores de timeline podem conflitar com VIS-009 em movimento.
