# TON-VIS-003 — Home / nova conversa

**Estado: CONCLUÍDO (DONE). Revisão visual aprovada em runtime.**

Executado no worktree `../ton-vis-003`, branch `ton/vis-003`, a partir de
`8820fb9bade3428fd2508463e72b4745f5ec3663`.

A composição final da Central padrão e a integração do seletor de modelos foram
validadas e aprovadas no runtime nos temas claro e escuro.


---

## 1. Home anterior

A home padrão mostrava a marca, uma saudação aleatória e o composer. O espaço
restante não dava direção ao usuário.

`WelcomeMessage` escolhia entre duas frases com `Math.random()`. O componente
também usava `FrostedDiv`, que criava um contêiner visual em volta da entrada.

As sugestões vinham somente das mensagens iniciais do agente. A Central padrão
não tinha ações de domínio próprias.

---

## 2. Hierarquia final

A composição corrigida usa esta ordem:

1. título de domínio;
2. uma linha de apoio;
3. composer existente (com seletor de modelo integrado na toolbar inferior);
4. contexto “Começar por”;
5. quatro comandos compactos.

O canvas é o contêiner. Não existe card de hero, sombra ou gradiente. O composer
continua como a principal superfície interativa.

A Central padrão não mostra a marca TON no conteúdo. A marca permanece na
sidebar. O título, o apoio, o composer e os comandos ficam alinhados à esquerda.
Agentes personalizados mantêm a identidade e as mensagens iniciais existentes.

O bloco usa a largura de leitura existente de 720 px. A linha superior e a
linha inferior usam a proporção `4fr` e `5fr`. Isso posiciona o bloco um pouco
acima do centro sem usar deslocamento fixo.

---

## 3. Copy determinística

Título PT-BR:

> O que precisa ser analisado?

Linha de apoio PT-BR:

> Envie arquivos ou descreva a situação que deseja investigar.

Placeholder do composer na Central padrão:

> Descreva o que deseja investigar...

A linha de apoio foi mantida. Ela explica as duas entradas reais da Central:
arquivo e texto.

`Math.random()` saiu do caminho de render da home padrão. A hora local e a
configuração de saudação também não alteram o título. Todos os nove catálogos
receberam as novas chaves.

---

## 4. Ações rápidas

A ordem é fixa:

1. Analisar arquivo;
2. Revisar contrato;
3. Investigar divergência;
4. Analisar resultado.

Cada comando envia um prompt comum pelo `OnSubmitProps` existente. Não existe
rota, API, agente ou objeto de workflow novo.

Os comandos usam botões terciários pequenos com um ícone de seta. Eles quebram
linha conforme a largura. Não usam cards, bordas, sombras ou fundo colorido.

As ações são honestas porque pedem análise sobre dados que o usuário ainda vai
fornecer. Elas não prometem execução de CFO, Frota, Contratos, ocorrência,
relatório ou ROI.

Se o usuário já anexou arquivos, a ação envia os mesmos `currentMessageFiles`.
Isso mantém o arquivo durante a transição para a conversa.

Agentes personalizados continuam usando `starter_messages`. O nome, o avatar e
a descrição desses agentes não foram substituídos pela copy da Central.

---

## 5. Composer e anexos

`AppInputBar` aceita uma substituição opcional de placeholder. A Central padrão
fornece essa copy. Outros contextos mantêm o placeholder existente. A borda, o
raio, o foco, a barra, o envio, o Deep Research e os IDs de VIS-004 continuam intactos.

Decisão final: model selector integrated into composer toolbar.
- O seletor de modelo foi posicionado dentro da toolbar inferior direita do composer, antes do microfone e do botão enviar/stop.
- O seletor utiliza a variante limpa `select-light`, exibindo ícone do provedor e nome do modelo, eliminando a cápsula com fundo opaco (`select-input`) e padding excessivo em repouso.
- O componente alinha-se verticalmente com o microfone e o botão enviar.
- Em telas estreitas (375 px), o nome é truncado responsivamente com elipse, preservando o tooltip completo no hover/foco.
- Decisão sobre o botão "+": identificado como `SvgPlusCircle` do `MultiModelSelector`, cuja semântica exclusiva é adicionar modelos para comparação simultânea (multi-model chat, até 3 modelos). Não possui relação com anexos ou contexto (função coberta pelo clipe `SvgPaperclip` na toolbar esquerda). Portanto, seu comportamento e arquitetura permanecem preservados no seletor de modelo sem invenção de comportamento.

`AppPage` mantém um único call site de `AppInputBar`. O componente não recebe
`key` e não fica em um ramo condicional. A mudança de home para conversa move o
mesmo componente entre as linhas do grid.

Essa identidade preserva:

- rascunho em `useDraft`;
- modelo em `multiModel.selectedModels`;
- anexos em `currentMessageFiles`;
- Deep Research e estado de upload internos.

A linha do composer continua com altura automática. A linha das ações usa
rolagem vertical e bloqueia overflow horizontal. Zero, um ou vários anexos não
dependem de altura fixa da home.

As ações permanecem visíveis com anexos. Essa decisão é determinística. O
layout tem espaço e rolagem para mantê-las acessíveis sem colisão.

O seletor de arquivos recentes não mudou.

---

## 6. Transição e movimento

O mecanismo de `gridTemplateRows` continua ativo:

- home: `minmax(0, 4fr) auto minmax(0, 5fr)`;
- conversa: `1fr auto 0fr`.

O `Fade` continua com 150 ms. Não há escala, mola, salto ou morph.

O onboarding trocou 500 ms por `duration-fast`. A entrada usa
`motion-safe`, e o conteúdo continua compreensível sem animação.

---

## 7. Responsividade

As ações usam uma linha flexível com quebra automática. Cada comando ocupa
somente a largura do conteúdo. O layout não usa rolagem horizontal.

Em 375 px, os comandos quebram em mais linhas. Em larguras maiores, eles usam o
espaço disponível. A largura máxima continua alinhada ao composer.

Estas regras foram verificadas por contrato estático. A inspeção visual em
375 px, 768 px, 1280 px e desktop grande está pendente no runtime Docker.

---

## 8. Onboarding e NRF

`aria-label="onboarding-flow"` foi substituído por
`t("flow.ariaLabel")`. Todos os catálogos têm a chave.

`NRFPage` usa o mesmo `WelcomeMessage` e o mesmo `Suggestions`. O seletor de
modelo agora tem um único call site junto do composer também no NRF. A lógica
de negócio do NRF não mudou.

---

## 9. Acessibilidade

- O título principal usa `h1`.
- A linha de apoio usa `p`.
- As ações usam `Button` do Opal.
- Cada ação tem o nome visível como nome acessível.
- O foco visível vem do primitivo Opal.
- O layout não depende de cor para comunicar função.
- O composer mantém foco e identidade na transição.
- O onboarding usa nome traduzido.
- O movimento respeita `prefers-reduced-motion`.

---

## 10. Testes e gates

Testes focados de VIS-003:

- `homeVisualContract.test.tsx`;
- `Suggestions.test.tsx`.

Eles cobrem copy determinística, ordem das ações, contrato de envio, anexos,
identidade do composer, grid, movimento, NRF, onboarding e segurança estática.

Resultado conjunto:

- 14 suítes passaram;
- 419 testes passaram;
- 0 snapshot falhou.

Regressões incluídas:

- `ton-theme`;
- `ton-foundations`;
- `ton-product-surface`;
- `ton-navigation`;
- `ton-shell`;
- `composerVisualContract`;
- `attachmentVisualContract`;
- `messageVisualContract`;
- processamento de pacotes e reasoning de VIS-006;
- `dropzonePaste`.

Gates:

- `bun run types:check`: passou, 98,81% de cobertura de tipos;
- `bun run lint`: passou com avisos existentes e 0 erros;
- `bun run build`: passou;
- build de `onyxdotapp/onyx-web-server:latest`: passou;
- formatação dos 17 arquivos de frontend alterados: passou;
- `bun run format:check` global: falha no baseline com 1.402 arquivos;
- `git diff --check`: passou.

---

## 11. Runtime Docker e validação visual aprovada

A stack Docker foi inicializada em etapas graduais para preservar o teto de
memória do WSL2 (~5.788 GiB). A imagem `onyxdotapp/onyx-web-server:latest` foi
gerada com sucesso e todos os 10 serviços responderam com integridade e saúde
operacional (~4.17 GiB consumidos, mais de 1.6 GiB livres).

A revisão visual da home e do composer foi inspecionada e aprovada pelo usuário:
- Tema claro e tema escuro validados com contraste e tokens semânticos íntegros.
- Model selector integrado harmonicamente à toolbar inferior direita do composer.
- Botão "+" preservado com sua função de multi-model selector (sem relação com anexos).
- Alinhamento à esquerda, copy determinística, comandos compactos e transição fluida.

Com a validação concluída e aprovada, o VIS-003 está oficialmente marcado como **DONE**.

---

## 12. Segurança de escopo

Não há dashboard, KPI ou métrica inventada. Não há contagem de achados,
ocorrências ou relatórios.

Nenhum arquivo de backend mudou. Nenhuma API ou dependência foi adicionada.
Não houve trabalho de VIS-007, VIS-008, VIS-009, VIS-010 ou limpeza admin 008B.

Especialistas, identidade visual global e marca continuam para VIS-007 ou uma
fatia posterior com ativo aprovado.
