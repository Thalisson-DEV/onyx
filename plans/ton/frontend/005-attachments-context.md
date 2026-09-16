# TON-VIS-005 — anexos e contexto

**Status: DONE.** Somente frontend. Nenhum arquivo em `backend/` mudou. Nenhuma
dependência nova. Nenhum endpoint novo.

Executado no worktree isolado `../ton-vis-005`, branch `ton/vis-005`, a partir de
`540ca196a3ba89904072e6666268c73b524398a9` (branch `main`, árvore limpa). Esse
baseline contém TON-FE-000 a FE-004, VIS-000, VIS-001, VIS-004, VIS-002, e os
Planos backend 001, 002, 003a–003d, 007 e 008a.

Insumos: [`000-de-onyx-visual-audit.md`](./000-de-onyx-visual-audit.md) §3.4,
§6.3, e as linhas de anexo/upload do inventário ·
[`001-visual-foundations.md`](./001-visual-foundations.md) (papéis de borda,
escala de raio) · [`002-shell-navigation.md`](./002-shell-navigation.md) ·
[`004-composer.md`](./004-composer.md) §24 ·
[`visual-language.md`](./visual-language.md) §5, §6, §7, §10.3 ·
[`visual-implementation-roadmap.md`](./visual-implementation-roadmap.md) VIS-005 ·
`web/AGENTS.md`.

---

## 1. Conclusão executiva

Um arquivo anexado passou a dizer **o que é** e **em que estado está**, nas
quatro superfícies onde aparece, com a mesma geometria.

Três mudanças carregam o resto:

1. **Uma função de categoria.** `fileCategory(name, mime)` responde "que arquivo
   é este?" para o composer, o picker, o modal e o painel de projeto. Antes o
   mapeamento de ícone estava duplicado em quatro lugares, e nenhum deles
   distinguia planilha de PDF.
2. **Um anexo com falha não desaparece mais.** O poller removia arquivos
   `failed` de `currentMessageFiles`; o usuário via um toast e uma faixa de
   anexos vazia, sem saber qual arquivo falhou nem como removê-lo.
3. **Arrastar arquivo sobre o chat tem retorno visual.** O `Dropzone` já
   envolvia o viewport inteiro; ninguém lia `isDragActive`.

A infraestrutura de upload não foi reescrita. `temp_<uuid>`, insert otimista,
reconciliação por `temp_id`, precheck de tamanho, rollback e o polling de 3s
estão intactos, e há teste de fonte afirmando cada um.
**Nível de mudança aplicado: 3 (composição local).**

---

## 2. Mapa de componentes de anexo

Descoberto antes de editar. A coluna "dono" diz quem decide, não quem renderiza.

| Superfície | Arquivo | Dono da identidade |
|---|---|---|
| cartão no composer e no projeto | `web/src/sections/cards/FileCard.tsx` | próprio |
| tile de imagem | idem (`ImageFileCard`) | próprio |
| chip do composer Craft | `web/src/sections/input/InputChipStrip.tsx` | próprio |
| linha do picker | `web/src/refresh-components/popovers/FilePickerPopover.tsx` | próprio |
| linha do modal | `web/src/sections/modals/UserFilesModal.tsx` | próprio |
| painel de contexto do projeto | `web/src/lib/projects/components/ProjectContextPanel.tsx` | **delega** ao `FileCard` |
| overlay de arrastar do chat | `web/src/views/AppPage.tsx` | próprio |

`ProjectContextPanel` não deriva categoria: ele renderiza `FileCard`. Isso está
afirmado em teste, para que uma edição futura não reintroduza uma sexta cópia do
mapeamento.

Consumidores que **não** são superfície de anexo e continuam como estavam:
`AgentEditorPage` (segundo consumidor de `temp_`), `SkillFileTree` e as abas de
preview (via `getFileIcon`).

---

## 3. Arquitetura de upload existente (preservada)

Lida em `web/src/lib/projects/providers.tsx` e `svc.ts`:

- `generateTempId()` emite `temp_${crypto.randomUUID()}`.
- `createOptimisticFile()` insere em até três listas (`allRecentFiles`,
  `allCurrentProjectFiles`, e o mapa por projeto) com `status: UPLOADING`.
- `svcUploadFiles` envia `FormData` com `files`, `project_id`,
  `incognito_session_id` e `temp_id_map`.
- A resposta reconcilia por `temp_id` nas três listas mais
  `currentMessageFiles`.
- `rejected_files` e erro de rede fazem rollback por `temp_id`.
- Precheck de tamanho por `user_file_max_upload_size_mb`, com toast.
- Polling de `trackedUploadIds` a cada 3s via `getUserFileStatuses`.

Nada disso mudou. A única linha alterada em `providers.tsx` é o `continue` que
descartava arquivos `failed` — ver §7.

---

## 4. Contrato de `fileCategory`

Em `web/src/lib/utils.ts`, junto de `IMAGE_EXTENSIONS`, que a semeia.

```
fileCategory(name: string | null, mime?: string | null): FileCategory
```

Oito categorias: `SPREADSHEET` · `DOCUMENT` · `IMAGE` · `PRESENTATION` ·
`AUDIO` · `VIDEO` · `ARCHIVE` · `OTHER`.

### 4.1 Precedência

1. **MIME exato**, quando nomeia um formato. `application/pdf` é sinal mais forte
   que qualquer extensão, porque a extensão pode mentir.
2. **Extensão**, em minúsculas. É o que resolve o caso comum de o servidor
   devolver `application/octet-stream` ou `text/plain` para um `.xlsx` ou `.csv`.
3. **Família MIME** (`image/`, `audio/`, `video/`, `text/`), para formatos raros
   demais para enumerar (`image/heic`, `audio/flac`).
4. `OTHER`.

MIME não informativo — `""`, `application/octet-stream`, `binary/octet-stream`,
`application/binary`, `application/x-empty` e **`text/plain`** — é pulado nos
passos 1 e 3. `text/plain` entra nessa lista de propósito: servidores devolvem
`text/plain` para csv, md e tsv indistintamente, então deixá-lo decidir
transformaria toda planilha CSV em documento.

**Um arquivo nunca é `DOCUMENT` só por ter nome.** Extensão desconhecida com MIME
não informativo é `OTHER`.

### 4.2 Classificação por categoria

| Categoria | MIME exato | Extensão |
|---|---|---|
| `SPREADSHEET` | `…spreadsheetml.sheet`, `…ms-excel.sheet.macroenabled.12`, `…ms-excel`, `…opendocument.spreadsheet`, `text/csv`, `text/tab-separated-values` | `xlsx` `xlsm` `xls` `csv` `tsv` `ods` |
| `DOCUMENT` | `application/pdf`, `application/msword`, `…wordprocessingml.document`, `…opendocument.text`, `application/rtf`, `text/rtf`, `text/markdown` | `pdf` `doc` `docx` `odt` `rtf` `txt` `md` `markdown` |
| `IMAGE` | família `image/` | de `IMAGE_EXTENSIONS`: `png` `jpg` `jpeg` `gif` `webp` `svg` `bmp` |
| `PRESENTATION` | `…ms-powerpoint`, `…presentationml.presentation`, `…opendocument.presentation` | `ppt` `pptx` `odp` |
| `AUDIO` | família `audio/` | `mp3` `wav` `m4a` `ogg` `oga` `flac` `aac` |
| `VIDEO` | família `video/` | `mp4` `mov` `webm` `avi` `mkv` `m4v` |
| `ARCHIVE` | `application/zip`, `…x-zip-compressed`, `…vnd.rar`, `…x-rar-compressed`, `…x-7z-compressed`, `…x-tar`, `application/gzip`, `…x-gzip` | `zip` `rar` `7z` `tar` `gz` `tgz` `bz2` |
| `OTHER` | — | qualquer outra, ou nenhuma |

As duas primeiras entradas de planilha vêm de `SPREADSHEET_MIME_TYPES` em
`PreviewModal/variants/xlsxVariant.tsx`, como a auditoria pediu.

### 4.3 Uma duplicação que **não** foi removida, de propósito

`xlsxVariant.tsx` mantém a própria lista curta de MIME. A pergunta dele é "meu
parser consegue ler isto?", não "o que isto significa para o usuário":
`parseSpreadsheetPreview` só lê `xlsx`/`xlsm`. Ligá-lo ao `fileCategory` mandaria
`.xls` e `.ods` para um parser que não os abre. Ficou registrado um comentário no
arquivo dizendo isso.

### 4.4 `getFileIcon`

Passou a delegar ao `fileCategory` e mantém uma única distinção própria: arquivo
de código recebe o glifo de chaves, porque seus call sites listam código. Para
`OTHER` continua devolvendo `SvgFileText`, preservando o comportamento anterior
nas árvores de arquivo.

---

## 5. Contrato visual de categoria

Cada categoria tem um **glifo distinto** do sistema Opal, verificado por teste
(oito categorias, oito glifos):

| Categoria | Ícone |
|---|---|
| `SPREADSHEET` | `SvgSpreadsheetFile` |
| `DOCUMENT` | `SvgFileText` |
| `IMAGE` | `SvgImage` (ou o próprio preview) |
| `PRESENTATION` | `SvgFileChartPie` |
| `AUDIO` | `SvgAudioFile` |
| `VIDEO` | `SvgVideoFile` |
| `ARCHIVE` | `SvgFiles` |
| `OTHER` | `SvgFile` |

**Decisão: categoria não usa cor.** A linguagem visual autoriza acento semântico
TON para categoria (§10.3), e a decisão foi não usar. Duas razões:

1. Oito matizes inventados para oito categorias seriam decoração, não semântica —
   não existe significado TON que diga que planilha é verde e vídeo é azul.
2. Com a cor livre, ela fica inteira para **estado**, que é a única coisa urgente
   num anexo. Um cartão vermelho no meio de seis cartões neutros lê como falha
   sem precisar de leitura.

Categoria é comunicada por **glifo + rótulo textual** (`Planilha`, `Documento`,
`Apresentação`, `Áudio`, `Vídeo`, `Arquivo compactado`, `Imagem`, `Arquivo`), dois
canais, nenhum deles cor. Isso satisfaz §34 com folga.

Nenhum ícone novo foi criado, nenhuma dependência de ícone foi adicionada, e não
há emoji nem cor crua do Tailwind — afirmado por teste nas cinco superfícies.

---

## 6. Geometria unificada

A auditoria encontrou três linguagens concorrentes. Elas convergiram para uma
família, sem virar uma dimensão só.

O ponto de convergência é `AttachmentItemButton`, do Opal, que já entrega
exatamente os eixos que §3 exige: zona de ícone (tile), hierarquia de nome
(`title`), hierarquia de metadado (`description`), local do status
(`description`), afordância de remoção (`rightChildren`), borda e raio
(`Interactive.Container`), e a matriz de hover/selected/focus
(`Interactive.Stateful`, variante `select-heavy`).

| Eixo | Valor |
|---|---|
| raio | `radius-12`, uma constante `ATTACHMENT_RADIUS` usada pela linha, pelo tile e pelo `<img>` |
| borda | 1px; `border-01` em repouso, `border-error` na falha |
| superfície | herdada da paleta interativa; `status-error-00` na falha |
| elevação | `elevation-0`; zero sombra nas cinco superfícies, afirmado por teste |
| remoção | `Button` do Opal em `Hoverable.Item`, `size="sm"` |
| largura | por superfície: `max-w-48` no composer e no projeto, `full` no picker e no modal |

Medido em Chromium: linha e tile de imagem em **12px** nos dois temas e nas três
larguras.

### 6.1 Duas decisões de raio

**`radius-12`, não `radius-08`.** A auditoria sugeriu `radius-08` para o
cartão-linha. `AttachmentItemButton` fixa `rounding={3}` (12px) no próprio
contêiner interno, e VIS-005 é nível 3: mudar o Opal seria nível 4. Um invólucro
de 8px em volta de um contêiner interativo de 12px vazaria o fundo de hover nos
cantos. Como o roadmap diz que o código de produção é a fonte de verdade, o valor
nativo do componente venceu, e o tile de imagem subiu de `rounded-08` para
`rounded-12` para acompanhar.

**`radius-04` no chip Craft**, não `radius-08`. Chip é controle compacto (§5.2), e
um chip aninhado num composer de `radius-12` precisa ficar **dentro** da curva do
pai, não ecoá-la.

---

## 7. Modelo de estado

`UserFileStatus` tem sete membros e chega em duas caixas: o endpoint de status
responde em minúsculas, o arquivo otimista do cliente usa o enum em maiúsculas.
Cada superfície refazia essa comparação na mão.

`web/src/lib/projects/utils.ts` passou a concentrar a derivação:

```
attachmentState(status): AttachmentState
```

| `UserFileStatus` | `AttachmentState` | Copy PT-BR |
|---|---|---|
| `UPLOADING` | `UPLOADING` | Enviando… |
| `PROCESSING` | `PROCESSING` | Processando… |
| `COMPLETED`, `SKIPPED` | `READY` | o rótulo de categoria |
| `FAILED`, `CANCELED` | `FAILED` | Falha no envio |
| `DELETING` | `DELETING` | Removendo… |
| desconhecido / ausente | `READY` | o rótulo de categoria |

Nenhum estado foi inventado: os cinco existem no contrato do frontend hoje. A
comparação é insensível à caixa.

`READY` mostra a **categoria**, não a palavra "Pronto": num cartão que já não tem
indicador de atividade, "Planilha" informa mais que "Pronto".

**Sem porcentagem.** A infraestrutura não expõe bytes enviados nem progresso de
indexação, então o cartão mostra estado, não número. Um teste afirma que nenhuma
das cinco superfícies contém `progress`, `percent` ou `%`.

A copy é operacional e não insinua análise: "Processando" descreve indexação, que
é o que de fato acontece.

---

## 8. Arquivo com falha permanece visível

### 8.1 O defeito

`providers.tsx`, no merge de status do poller:

```
if (latestStatus === "failed") { changed = true; continue; }
```

O arquivo saía de `currentMessageFiles`. Restava um toast, sem nome de arquivo.

### 8.2 A correção

O `continue` saiu; o status é mesclado como qualquer outro. São **cinco linhas
removidas**, dentro do updater existente. Nada mais em `providers.tsx` mudou.

### 8.3 Por que é seguro — decisão do gate de envio

`AppInputBar` bloqueia o envio em dois predicados, e só neles:

```
currentMessageFiles.some(f => f.status === UserFileStatus.UPLOADING)
currentMessageFiles.filter(f => f.status === UserFileStatus.PROCESSING)
```

`FAILED` não é nenhum dos dois, portanto **um anexo com falha não prende o envio**.
Nenhuma linha do gate mudou; o comportamento correto já estava lá. Há teste
afirmando que `AppInputBar` não menciona `UserFileStatus.FAILED`, para que uma
edição futura não transforme falha em bloqueio por acidente.

Como a falha é terminal no modelo do frontend — o poller já remove o id de
`trackedUploadIds` ao ver `failed`, e não existe contrato de retry —, o cartão
oferece **remoção explícita e nada mais**. Nenhum retry foi inventado.

### 8.4 A fronteira de transporte

Manter o arquivo na lista criava um risco novo: `projectFilesToFileDescriptors`
mapeava tudo, então um id de arquivo que falhou iria junto com a mensagem.

A separação ficou onde pertence: visibilidade é apresentação, anexação é
transporte. `projectFilesToFileDescriptors` filtra `FAILED`/`CANCELED`. O usuário
vê a falha; o servidor nunca a recebe.

### 8.5 O que **não** entrou nessa mudança, e por quê

Rejeição do servidor (`rejected_files`) e erro de rede continuam fazendo
rollback. Nos dois casos **não existe registro no servidor**: manter a linha
deixaria um `temp_` órfão, sem id real para remover nem para consultar. O toast
já nomeia o motivo devolvido pelo backend. Só o caminho `FAILED` do poller —
que é o que a auditoria apontou — passou a preservar o arquivo.

---

## 9. Overlay de arrastar no chat

`AppPage.tsx` desestruturava apenas `getRootProps`. Passou a ler `isDragActive` e
a renderizar `ChatDropOverlay` dentro do root `relative` que já existia.

Medido em Chromium, seis configurações:

| Propriedade | Valor |
|---|---|
| posição | `absolute inset-0`, cobre o root exatamente |
| altura do root | 160px com e sem overlay — **zero deslocamento de layout** |
| `pointer-events` | `none` |
| véu | `bg-mask-02` = `rgba(0,0,0,0.2)`, igual nos dois temas |
| aresta | 1px **tracejada**, `border-selected` (`#227653` claro, `#a9cdbd` escuro), `radius-12`, com `inset-2` |
| `backdrop-filter` | `none` — sem glassmorphism |
| `box-shadow` | `none` |
| movimento | `motion-safe:animate-in motion-safe:fade-in-0`; nenhum `animate-in` sem o prefixo |
| a11y | `aria-hidden` |

`if (!active) return null` — sair do arraste desmonta o overlay no mesmo commit
de render, sem transição de saída pendente.

Copy por next-intl: `chat.app.dropzone.instruction` ("Solte os arquivos aqui") e
`chat.app.dropzone.description`.

`noClick` e `noPaste` continuam no `<Dropzone>`. `dropzonePaste.test.tsx` passa
**sem alteração**.

### 9.1 Arraste inválido: não implementado, e por quê

O `Dropzone` do chat não passa `accept` — aceita `*/*`, como o input do picker.
Sem restrição declarada, `isDragReject` do react-dropzone é sempre `false`: o
componente **não tem como saber** que um arquivo é inválido antes do drop. A
rejeição real acontece depois, no precheck de tamanho e no `rejected_files` do
servidor, e já tem toast. Fabricar um estado de rejeição visual aqui seria
mentira, então §11 foi cumprido não implementando.

### 9.2 O painel de projeto acompanhou

`ProjectContextPanel` era o único drag-over do app, com
`border-2 border-dashed border-action-selection-05` e `rounded-lg`. Passou para
1px, `border-selected`, `radius-12` — o mesmo sinal do viewport, para que soltar
arquivo leia igual nos dois lugares.

---

## 10. Picker, modal e painel de projeto

**`FilePickerPopover`.** A linha passou a mostrar o glifo de categoria e, onde
antes havia a extensão crua (`XLSX`, e `PLAINTEXT` para `.txt`), o rótulo de
categoria ou o estado. Falha usa `SvgAlertCircle` mais o texto — sem override de
cor, porque a linha herda a cor da paleta interativa e disputar isso por ordem de
classe seria frágil. Seleção, busca, fonte de arquivo, permissões e os contratos
de backend não mudaram.

**`UserFilesModal`.** `getIcon` e `getDescription` passaram a ler
`attachmentState` e `fileCategory`; ganharam o caso `FAILED`, que não existia. O
estado vazio saiu de um `<Text text03>` solto para `IllustrationContent`, **sem
ilustração** — só título e descrição, conforme §17 ("nenhuma ilustração
decorativa"). Nada mais do modal mudou.

**`ProjectContextPanel`.** Herda a identidade via `FileCard`. O estado vazio, que
era uma barra tracejada de `h-12` feita à mão com o texto colado na borda, passou
a `IllustrationContent` dentro do mesmo frame tracejado — que agora acumula as
duas funções, estado vazio e alvo de arraste. Adicionar/remover contexto, APIs,
seleção, permissões e drag/drop não mudaram.

**`InputChipStrip`** (composer Craft). Chip passou a `radius-04`, o glifo veio da
categoria compartilhada, e as duas cores de erro cruas
(`border-status-error-02`, `text-status-error-02`) viraram os papéis nomeados
`border-error` e `stroke-status-error-05`.

---

## 11. Contrato VIS-004 preservado

Nada do composer mudou. `.ton-composer`, `focus-within`, estrutura da barra,
send/stop, Deep Research, seletor de modelo e comportamento responsivo estão
intactos: `composerVisualContract.test.ts` passa sem alteração.

A faixa de anexos continua medindo a altura do conteúdo em JS. O cartão ficou
mais alto por causa do controle de remoção de 24px no slot de ação, e a medição
acompanha sozinha, porque lê `scrollHeight` em vez de assumir uma altura.

---

## 12. i18n

Nove catálogos, paridade mantida, `catalog.test.ts` verde. Chaves novas:

| Chave | pt-BR |
|---|---|
| `cards.file.category.{spreadsheet,document,image,presentation,audio,video,archive,other}` | Planilha · Documento · Imagem · Apresentação · Áudio · Vídeo · Arquivo compactado · Arquivo |
| `cards.file.failed.description` | Falha no envio |
| `cards.file.deleting.description` | Removendo… |
| `cards.file.remove.ariaLabel` | Remover {name} |
| `cards.file.status.announcement` | {name}: {status} |
| `chat.app.dropzone.instruction` | Solte os arquivos aqui |
| `chat.app.dropzone.description` | Eles são anexados a esta conversa. |
| `chat.modals.userFiles.emptyState.title` | Nenhum arquivo |
| `chat.projects.contextPanel.emptyFiles.title` | Nenhum arquivo ainda |

Removida: `cards.file.remove.label`, substituída pela variante com `{name}`.

Nenhuma string PT-BR está embutida em componente.

### 12.1 Copy de erro de `svc.ts`: escopo revisto

A auditoria apontou `svc.ts:11-13` como erro em inglês codificado. O código atual
é `handleRequestError`, que faz `throw new Error(\`${action} failed (Status:
${response.status})\`)`. Auditado o destino dessas mensagens: **nenhuma chega à
tela**. Os call sites em `providers.tsx` capturam o erro e emitem toasts que já
passam por next-intl (`projects.uploads.failed.toast`,
`projects.uploads.rejected.toast`, `projects.uploads.oversized.toast`); os
`const message = err instanceof Error ? err.message : "…"` que restam em
`createProject`, `renameProject`, `getRecentFiles` e `getFilesInProject` são
variáveis mortas — atribuídas e nunca lidas.

Traduzir uma string de diagnóstico que nunca é renderizada acrescentaria nove
entradas de catálogo sem efeito para o usuário, e `svc.ts` é um módulo sem React,
onde `useTranslations` não existe. **`svc.ts` ficou intocado.** As variáveis
mortas pertencem a uma limpeza própria, não a VIS-005.

---

## 13. Acessibilidade

| Item | Resultado |
|---|---|
| nome do arquivo anunciado | `title` no `Content`; nome completo, não truncado |
| categoria sem depender de cor | glifo distinto + rótulo textual; categoria não usa cor |
| nome acessível do controle de remoção | `Remover {name}`, medido em Chromium |
| status anunciado | `role="status" aria-live="polite"`, **vazio em repouso**: só narra `UPLOADING`, `PROCESSING`, `DELETING` e `FAILED` |
| falha anunciada | `"falhou.xlsx: Falha no envio"`, medido |
| alvo de toque | 24×24px, medido (era 16×16px) |
| toque sem hover | `Hoverable` esconde só dentro de `@media (hover: hover)`; em toque o controle fica visível |
| teclado | `[data-hover-group]:has(:focus-visible)` revela o controle; foco global de VIS-001 |
| overlay de arraste | `aria-hidden`: narra um gesto de ponteiro que a tecnologia assistiva não executa, e o caminho acessível para anexar é o picker do composer |
| contraste | ver §14 |

O `<button>` cru do badge de remoção anterior saiu; virou `Button` do Opal.

---

## 14. Contraste medido

Calculado sobre os tokens resolvidos, nos dois temas.

| Par | Claro | Escuro |
|---|---:|---:|
| aresta de erro sobre superfície de erro | 4.56:1 | 4.00:1 |
| glifo de erro sobre superfície de erro | 4.56:1 | 4.00:1 |
| aresta tracejada sobre o véu do overlay | 3.46:1 | 11.32:1 |
| título do overlay sobre o véu | 13.08:1 | 19.56:1 |
| descrição do overlay sobre o véu | 13.08:1 | 19.56:1 |

`status-error-05` é `#dc2626` nos dois temas e mede 2.13:1 sobre o canvas escuro
`#333333`. Por isso o cartão com falha recebeu `bg-status-early-error` —
`status-error-00`, `#210504` no escuro —, que leva a aresta a 4.00:1. A
superfície de erro entrou por medição, não por gosto: sem ela a borda de falha
não passaria 3:1 no escuro.

---

## 15. Responsivo

375 · 768 · 1280, claro e escuro. Todas as verificações passaram nas seis
configurações.

| Item | Resultado |
|---|---|
| nome longo | truncado com `scrollWidth > clientWidth`; `title` mantém a string inteira |
| overflow horizontal | nenhum; o cartão fica em `max-w-48` = 192px, e a faixa é `flex-wrap` |
| ícone esmagado | não; o tile do `AttachmentItemButton` tem largura própria |
| status legível | rótulo de estado presente nos três breakpoints |
| remoção alcançável | 24×24px nos três breakpoints |
| composer | não transborda; a medição de altura é dinâmica |
| feedback de arraste | `absolute inset-0`, sem overflow, sem mudança de altura do root |

---

## 16. Testes

Novos:

| Arquivo | Escopo | Testes |
|---|---|---:|
| `src/lib/__tests__/fileCategory.test.ts` | categoria por MIME, por extensão, precedência, caixa, fallback, identidade | 51 |
| `src/lib/projects/utils.test.ts` | `attachmentState`, gate de envio, filtro de descritor | 18 |
| `src/sections/cards/FileCard.test.tsx` | identidade, estados, falha visível/removível, remoção acessível, nome longo, imagem | 21 |
| `src/sections/cards/attachmentVisualContract.test.ts` | contrato de fonte: geometria, tokens, remoção, overlay, upload preservado | 60 |

Estendido: `src/lib/projects/providers.test.tsx`, com nove testes de
visibilidade de falha via polling. Os quatro testes de upload que já existiam
não foram tocados.

**A correção foi verificada por inversão.** Com o `continue` reintroduzido em
`providers.tsx`, "keeps a failed file in currentMessageFiles" e "does not leave a
failed file looking like it is still uploading or indexing" falham. Os testes que
passavam por vazio nesse cenário — envio não bloqueado, descritor vazio, remoção
— ganharam `expect(files).toHaveLength(1)` antes da asserção, para não passarem
justamente pelo defeito que removem.

`dropzonePaste.test.tsx` passa **sem nenhuma alteração**, incluindo a asserção de
fonte de que os três dropzones de composer passam `noPaste`.

---

## 17. Validação de runtime

**Runtime da aplicação: deferido.** Mesma razão registrada em
`002-shell-navigation.md` §13 e `004-composer.md` §24: os serviços Onyx em
execução servem o worktree original, e apontá-los para este worktree mexeria no
runtime compartilhado de outro trabalho.

**Validação visual: FEITA, em runtime isolado.** Chromium via `@playwright/test`
(já instalado; nenhuma dependência adicionada), carregando o **CSS que o build de
produção emitiu**, sobre uma página gerada pelo **componente `FileCard` real**
renderizado com `renderToStaticMarkup` — não markup copiado à mão. Sem servidor,
sem container, sem banco.

Validado nos dois temas em 375/768/1280: as oito categorias, os estados
`UPLOADING`/`PROCESSING`/`READY`/`FAILED`, nome longo, arquivo desconhecido,
preview de imagem, imagem com falha, cartão sem remoção, e o overlay de arraste.
Todas as verificações passaram nas seis configurações. O harness era temporário e
foi removido; os valores medidos estão em §6, §9, §14 e §15.

Limitação registrada: na página estática o `<img>` do preview aponta para
`/api/chat/file/...` e não resolve, então o tile mostra imagem quebrada em vez de
foto. O fallback `onError` que troca para o glifo é um handler React e não roda em
markup estático. O caminho está coberto por RTL em `FileCard.test.tsx`.

---

## 18. Portões de qualidade

| Portão | Resultado |
|---|---|
| `bun run types:check` | **0 erros**; cobertura de tipo 98.81% (233832/236644 identificadores, 1246 arquivos) |
| `bun run lint` | **0 erros**; nenhum aviso novo nos arquivos alterados |
| `bun run build` | **sucesso** |
| `oxfmt --check` nos arquivos alterados | limpo |
| `dropzonePaste.test.tsx` | verde, sem alteração |
| `composerVisualContract.test.ts` | verde |
| `ton-shell` · `ton-navigation` · `ton-product-surface` · `ton-privacy` | verdes |
| `ton-theme` · `ton-foundations` | verdes |
| `catalog.test.ts` (paridade de nove catálogos, forma ICU) | verde |
| suítes de anexo | 18 suítes, 386 testes verdes |

Confirmado por consulta ao CSS do build que todas as classes novas geram regra
real: `border-border-error`, `border-border-selected`, `bg-mask-02`,
`bg-status-error-00`, `stroke-status-error-05`, `rounded-12`, `rounded-04`,
`bg-background-tint-01`, `sr-only`.

### 18.1 Falhas pré-existentes, não relacionadas

Na suíte completa, 11 suítes falham por **timeout de 5000ms** sob carga paralela
nesta máquina: `admin/billing/page`, `SkillEditorPage`, `SkillsPage`,
`lib/auth/components`, `ImportSkillsFromGitHubModal`, `ExternalAppsPage`,
`ConfigureProviderModal`, `ScheduleTaskForm`, `CreateSkillModal`,
`languageModels/CustomModal`, `output-panel/FilesTab`.

Rodadas isoladamente neste worktree, as onze passam: **84/84**. As mesmas onze
falham no worktree baseline limpo. São timeouts de ambiente, não asserções, e não
têm relação com VIS-005.

---

## 19. Trabalho de backend deferido

Nada de ingestão entrou. Continuam fora, no Plano backend 004, pausado à espera
dos arquivos reais da Vale Norte: parsing de PDF, parsing de Excel, MarkItDown,
`SourceSnapshot`, NG, Keevo, OCR, extração, normalização, estado de arquivo no
backend e regras determinísticas.

Nenhum metadado foi inventado. O cartão mostra nome, categoria e estado — os três
campos que `ProjectFile` já carrega. Não há confiança de fonte, qualidade de
ingestão, estado de OCR, domínio de negócio nem páginas extraídas.

### 19.1 Capacidades que a UX gostaria e o backend não tem

Registradas, não implementadas:

1. **Tamanho do arquivo.** `ProjectFile` não traz bytes, então o cartão não mostra
   tamanho. `formatBytes` já existe em `web/src/lib/utils.ts` e serviria no dia em
   que o campo existir.
2. **Motivo da falha por arquivo.** O poller devolve `status: failed` sem
   mensagem. O cartão diz "Falha no envio" e nada mais. `rejected_files` traz
   `reason` no caminho de rejeição, mas esse caminho faz rollback (§8.5).
3. **Retry.** Não existe contrato. Nenhum foi inventado.
4. **Progresso real.** Não há bytes enviados nem progresso de indexação. Sem
   porcentagem falsa.

---

## 20. Arquivos alterados

Produção:

- `web/src/lib/utils.ts` — `FileCategory`, `fileCategory`, `fileCategoryIcon`,
  `FILE_CATEGORY_LABEL_KEYS`, listas de MIME; `getFileIcon` delegando.
- `web/src/lib/projects/utils.ts` — `AttachmentState`, `attachmentState`,
  `isFailedAttachment`; filtro de falha em `projectFilesToFileDescriptors`.
- `web/src/lib/projects/providers.tsx` — o `continue` de `failed` removido.
- `web/src/sections/cards/FileCard.tsx` — reescrito sobre a identidade
  compartilhada.
- `web/src/sections/input/InputChipStrip.tsx` — raio, glifo, papéis de erro.
- `web/src/refresh-components/popovers/FilePickerPopover.tsx` — identidade na
  linha.
- `web/src/sections/modals/UserFilesModal.tsx` — identidade, estado `FAILED`,
  `IllustrationContent`.
- `web/src/lib/projects/components/ProjectContextPanel.tsx` —
  `IllustrationContent`, drag-over alinhado.
- `web/src/views/AppPage.tsx` — `ChatDropOverlay`.
- `web/src/sections/modals/PreviewModal/variants/xlsxVariant.tsx` — só comentário.
- `web/src/i18n/messages/*.json` — nove catálogos.

Testes: `src/lib/__tests__/fileCategory.test.ts`,
`src/lib/projects/utils.test.ts`, `src/sections/cards/FileCard.test.tsx`,
`src/sections/cards/attachmentVisualContract.test.ts`,
`src/lib/projects/providers.test.tsx` (estendido).

Documentação: este arquivo, mais `visual-implementation-roadmap.md`.

**`web/src/lib/projects/svc.ts` não foi alterado** — ver §12.1.
**`web/src/lib/projects/providers.tsx` foi alterado em cinco linhas** — ver §8.2.
Ambos estavam nas listas do briefing; nenhum foi editado por estar listado.

---

## 21. Nenhuma condição de parada foi atingida

| Condição | Situação |
|---|---|
| falha visível exigiria backend/API | não; `status: failed` já chega ao cliente |
| falha indistinguível de uploading/indexing | não; `UserFileStatus` separa os três |
| corrigir visibilidade exigiria reescrever o provider | não; cinco linhas |
| `temp_<uuid>` teria de mudar | não |
| `noPaste`/`noClick` teriam de sair | não; ambos continuam |
| biblioteca de upload nova | não |
| categoria exigiria metadado de backend | não; `name` + `file_type` bastam |
| overlay exigiria trocar o `Dropzone` | não; só ler `isDragActive` |
| VIS-004 exigiria redesenho estrutural | não |
| VIS-002 exigiria redesenho | não |
| ingestão de backend | não |

---

## 22. Fora de escopo, confirmado

Não implementados: VIS-003 (home, ações rápidas, métricas), VIS-006 (mensagens,
`HumanMessage`, `AgentMessage`, raciocínio, timeline, markdown, ferramentas,
source tags), VIS-007 (identidade de especialista, personas), VIS-008 (voz),
VIS-009, VIS-010.

A casca de VIS-002 e o composer de VIS-004 não foram redesenhados. Nenhuma
regressão exigiu tocá-los.

---

## 23. O que VIS-006 e VIS-003 herdam

**VIS-006 (mensagens).** `FileCard` é o componente compartilhado que renderiza
anexo dentro de mensagem; a identidade semântica, a geometria e o estado já valem
lá sem trabalho novo. `AttachmentState` e `attachmentState` estão disponíveis para
o estado de ferramenta, que precisa da mesma distinção
executando/concluído/falhou, com o papel `border-error` já medido nos dois temas.

**VIS-003 (home).** A transição da home dependia da geometria final de anexo, que
agora está fixa: `radius-12`, borda de 1px, `max-w-48` no composer. A faixa de
anexos mede altura dinamicamente, então uma home que monte o composer com anexos
já presentes não salta.

---

## 24. Conflitos de integração prováveis

1. **`web/src/lib/utils.ts`** — o arquivo cresceu ~250 linhas. Qualquer fatia que
   adicione utilitário no mesmo trecho conflita textualmente.
2. **`web/src/views/AppPage.tsx`** — VIS-003 edita as linhas 1 e 3 do grid;
   VIS-005 adicionou `ChatDropOverlay` antes do componente e uma linha dentro do
   `Dropzone`. Regiões diferentes, conflito provável apenas nos imports.
3. **Os nove catálogos** — toda fatia mexe neles. Os blocos são
   `cards.file`, `chat.app.dropzone`, `chat.modals.userFiles.emptyState` e
   `chat.projects.contextPanel.emptyFiles`.
4. **`web/src/lib/projects/providers.tsx`** — cinco linhas dentro do merge do
   poller. Conflita com qualquer fatia que toque o mesmo updater.
5. **`web/src/sections/cards/FileCard.tsx`** — reescrito. Uma fatia que o tenha
   editado em paralelo conflita por inteiro.
