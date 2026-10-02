# TON — Primeira apresentação para Luyla (Controladoria Vale Norte)

Data de preparação: 02/10/2026
Base: o produto rodando em `http://localhost:3000`, explorado tela por tela em 02/10/2026, com os dados reais de jan–jun/2026 importados hoje às 08:35.

> **Como ler as etiquetas deste guia**
>
> - **[DADO REAL]** é um número ou fato que aparece no TON com os dados da Vale Norte, ou que veio direto dos arquivos dela.
> - **[LEVANTAMENTO]** é um dado real apurado na preparação, comparando com o *Banco de Dados (Vale Norte).xlsm*, mas que **não aparece em nenhuma tela do TON**. Fale dele em voz alta e tenha a planilha aberta para mostrar.
> - **[HISTÓRICO]** vem do relatório de inconsistências de jan–abr/2026 (reunião de 15/06/2026). Não é o estado atual.
> - **[INTERPRETAÇÃO]** é uma leitura nossa sobre um dado real. Pode estar errada.
> - **[HIPÓTESE]** é uma explicação possível que ainda precisa da confirmação dela.
> - **[CAPACIDADE ATUAL]** é algo que o produto faz hoje.
> - **[PRÓXIMO PASSO]** ainda não existe. Não prometa prazo.

---

## ★ ROTEIRO PARA LER EM VOZ ALTA (use este durante a reunião)

> Esta parte foi escrita para ser **lida em voz alta**, mesmo por quem não é da área financeira. O resto do documento é material de consulta.
>
> **Três objetivos da reunião:** (1) mostrar o que já existe; (2) descobrir se é o que ela esperava; (3) sair com as próximas prioridades definidas por ela.
>
> **Regra de ouro:** você não precisa saber finanças. **Ela é a especialista.** Seu papel é mostrar, perguntar e anotar. Quando não souber, diga: *"Boa pergunta. Não sei te responder com certeza; vou anotar e te trago com a evidência."*
>
> Texto em **»** = ler. Texto em *[colchetes]* = o que fazer na tela.

### Mini-glossário (para você, não para ler)

| Palavra | O que significa, em linguagem simples |
|---|---|
| **DRE** | Demonstração do Resultado: a "conta de padaria" da empresa. Quanto entrou (receita), quanto saiu (custos e despesas) e quanto sobrou (resultado). |
| **Realizado** | O que de fato aconteceu: os lançamentos que estão no NG. |
| **Orçado** | O que estava planejado: vem das "dotações" (o orçamento de cada unidade). |
| **Dotação** | A planilha de orçamento de cada unidade (temos Mossoró, Juazeiro-BA e Itabirito). |
| **NG / Keevo** | O sistema onde a empresa lança as contas a pagar e receber. O TON lê um arquivo exportado dele. |
| **Natureza** | A "categoria" de cada lançamento (combustível, folha, locação…). É o que decide em que linha da DRE ele cai. |
| **Consolidado** | A empresa toda somada. "Por unidade" = cada operação separada (Mossoró, Toledo…). |
| **Acumulado** | Soma de janeiro até o mês escolhido. |
| **Conciliação** | Conferir se a mesma nota aparece igual em dois lugares (NG × faturamento). |
| **Parcelamentos** | Acordos para pagar impostos atrasados em parcelas. O ponto em discussão: o valor do acordo inteiro foi lançado como despesa de um mês só. |
| **PIS/COFINS** | Impostos sobre o faturamento, calculados pela Contabilidade. |
| **Competência** | O mês a que um valor "pertence", que pode ser diferente do mês em que foi pago. |

---

### PARTE 1 — Abertura (2 min) · *[tela: Visão Geral]*

» "Luyla, obrigado pelo tempo. Antes de começar, quero deixar claro o objetivo de hoje: te mostrar o que já foi construído, entender se isso está no caminho do que você esperava, e principalmente ouvir de você o que deve vir primeiro daqui pra frente."

» "Uma coisa importante: eu não sou da área financeira. Quem entende do processo é você. Então várias vezes eu vou te perguntar 'isso faz sentido?', e é sincero. Sua opinião é o que define os próximos passos."

» "O TON é uma ferramenta que lê os mesmos arquivos que você já usa: o export do NG, o faturamento e as dotações. Ela confere esses arquivos, monta a DRE no formato da sua controladoria e aponta o que parece estranho. Ela **não altera nada** no NG nem nas suas planilhas, e **não toma decisão sozinha**: quando encontra algo, registra e pede que alguém decida."

» "Tudo que eu vou mostrar usa os dados reais de janeiro a junho de 2026, que estavam na pasta que você compartilhou."

*[Aponte os quatro cartões do topo: DRE "Pronta", Pendências "0", Fontes, Próxima automação.]*

» "Essa é a primeira tela. Num olhar ela diz: a DRE está montada, não há pendência travando, quais arquivos foram usados e quando roda a próxima rotina automática."

---

### PARTE 2 — De onde vêm os dados (3 min) · *[menu → Fontes]*

» "Aqui ficam os arquivos que alimentam o TON. Hoje são três: os lançamentos do NG de janeiro a junho, a planilha de resumo das notas fiscais e as três dotações."

*[Clique na setinha à direita do NG → clique no nome do arquivo.]*

» "Do NG entraram 6.307 lançamentos. Quatro linhas não puderam ser lidas, porque o valor estava num formato inválido, e 19 lançamentos vieram sem unidade. O TON não esconde isso nem tenta adivinhar: mostra a lista."

» "Uma coisa que eu quero deixar bem clara: **ainda não existe conexão direta com o NG.** Está escrito aqui, 'aguardando acesso'. Hoje alguém exporta o arquivo e ele entra aqui."

*[Clique em "Atualizar dados" → mostre a janela → clique em "Cancelar".]*

» "Todo mês, o processo seria esse: o arquivo que vocês já exportam entra aqui."

---

### PARTE 3 — A DRE (6 min) · *[menu → Fechamento → DRE]*

» "Essa é a DRE que o TON montou, seguindo as categorias que estão no seu Banco de Dados. Está em junho, empresa toda."

*[Aponte o número grande.]*

» "Em junho, o resultado ficou em menos 361 mil reais. No acumulado do ano, menos 128 milhões. Esse acumulado assusta, e eu já explico, porque quase todo ele vem de uma linha só."

*[Clique na linha "Combustível".]*

» "O que eu acho mais útil: clico em qualquer linha e vejo exatamente quais lançamentos formam esse número, de que arquivo vieram e em qual linha da planilha. Qualquer número pode ser conferido na fonte."

» **Pergunta de expectativa:** "Esse formato de DRE é parecido com o que você usa? Falta alguma linha, ou alguma está diferente do que você faria?"

*[Anote a resposta.]*

**Se ela perguntar por que o Orçado está zerado, leia:**

» "Foi de propósito. As três dotações foram importadas, mas eu ainda não sei com segurança como encaixá-las na DRE: se os valores são anuais ou mensais, qual o sinal, e qual linha da dotação corresponde a qual linha da DRE. E só temos dotação de 3 unidades. Em vez de mostrar um orçado possivelmente errado, preferi mostrar zero e te perguntar. Como você faz essa comparação hoje?"

*[Opcional: no seletor "Escopo", escolha "000028 · TOLEDO-PR" e depois "000009 · MOSSORÓ-RN".]*

» "A mesma DRE abre por unidade. Também existe um grupo 'Sem unidade no NG', onde ficam aqueles 19 lançamentos que vieram sem unidade."


**4.3 PARCELAMENTOS** *[tela: DRE → linha "Parcelamentos", coluna "Acumulado"]*

» "Essa linha tem 128,9 milhões no acumulado, quase todo o resultado negativo do semestre. A maior parte está em abril, uns 91 milhões, e em maio, uns 38 milhões. No relatório de junho já tinha aparecido que, em abril, os acordos de parcelamento de impostos foram lançados pelo valor total do acordo, e não pela parcela do mês. **Eu não mudei nada:** o TON mostra como está no NG. **Esse valor deve ficar na DRE do mês, ou só a parcela paga?**"

**4.4 PIS/COFINS e receita** *[sem tela; se quiser, abra o PDF de PIS/COFINS]*

» "Na DRE do TON, a linha de impostos sobre faturamento está zerada, porque o PIS/COFINS vem da Contabilidade e ainda não entra no TON. Pela apuração de agosto, são uns 3,86 milhões no semestre. E a receita do TON vem do NG já sem as retenções: dá 59 milhões no semestre, contra 65,9 milhões da base do PIS/COFINS. **Como você quer ver a receita: líquida, como está, ou bruta com os impostos abaixo?**"

**4.5 Por que não vai bater 100% com o seu BI**

» "Se você comparar com o seu Power BI, vai haver diferença, e hoje eu consigo apontar pelo menos seis motivos: as linhas repetidas do Banco de Dados, o tratamento da 392, as 4 linhas de janeiro que ficaram de fora (uns 14 mil reais), o orçado zerado, a receita líquida e o PIS/COFINS. Nenhum deles quer dizer que o seu arquivo está errado. São escolhas que dependem de você."

---

### PARTE 5 — Estava de acordo com o que você esperava? (5 min)

» "Agora queria parar de mostrar e te ouvir. Três perguntas:"

» **1.** "Do que você viu, o que foi **mais útil**, aquilo que você usaria de verdade?"

» **2.** "O que você **esperava ver e não viu**?"

» **3.** "Tem algo que eu mostrei que **não faz sentido** para o seu dia a dia?"

*[Anote palavra por palavra. Não defenda o produto, só agradeça e anote.]*

» *(Se ela citar algo que já existe)* "Isso existe em parte. Posso te mostrar rapidinho?"
» *(Se ela citar algo que não existe)* "Ainda não existe. Anotei como prioridade candidata."

---

### PARTE 6 — O que ainda falta (2 min) · *[sem tela]*

» "Sendo bem transparente sobre o que **ainda não existe**:"
» "— a conexão direta com o NG; hoje é por arquivo;"
» "— o orçado comparado com o realizado;"
» "— o PIS/COFINS e o fluxo de caixa dentro do TON;"
» "— o histórico de 2025, para comparar com o ano anterior;"
» "— outras áreas, como frota, contratos, folha e compras;"
» "— a rotina diária: hoje existe uma rotina mensal;"
» "— e o TON confirmar sozinho, no mês seguinte, se uma correção foi feita no NG;"
» "— e um ambiente definitivo para a sua equipe usar. Hoje roda num ambiente de validação."

---

### PARTE 7 — Definir as prioridades (5 min)

» "Para eu não escolher sozinho, queria que você me ajudasse a ordenar. Dessas opções, quais são as **três mais importantes** para você?"

*[Leia a lista devagar e anote a ordem que ela der.]*

| # | Opção | Em uma frase |
|---|---|---|
| A | Validar as regras de hoje | Parcelamentos, a 392, as repetições e a receita, para a DRE do TON ficar "oficial" |
| B | Orçado × realizado | Ligar as dotações para comparar o planejado com o real |
| C | PIS/COFINS na DRE | Trazer a apuração da Contabilidade |
| D | Conexão direta com o NG | Parar de depender do arquivo exportado |
| E | Histórico 2025 | Comparar com o ano anterior |
| F | Fluxo de caixa / conciliação bancária | Conferir o NG contra o banco |
| G | Frota e combustível | Controle de abastecimento e veículos |
| H | Rotina diária e acompanhamento | "O que mudou desde ontem" e lembrar quem precisa corrigir o quê |
| I | Outra coisa | O que ela disser |

» "E para a prioridade número um: **o que você precisa me passar**, e **quem da sua equipe** eu posso procurar?"

---

### PARTE 8 — Fechamento (1 min)

» "Resumindo o que combinamos: as prioridades são *[ler as 3 que ela escolheu]*. De você eu preciso *[ler o que ela disse]*. Eu volto com a primeira prioridade avançada e te mostro o antes e depois. Podemos marcar a próxima conversa?"

» "Obrigado. A sua visão é o que mais ajuda o TON a ficar útil de verdade."

---

### Se ela perguntar e você não souber

| Ela pergunta… | Você responde |
|---|---|
| Algo técnico de contabilidade | "Não sei responder com segurança. Vou anotar e te trago com a evidência." |
| "Esse número está certo?" | "Ele está calculado com as regras que eu mostrei e dá para conferir na fonte. Se está certo, quem diz é você. Por isso quero sua validação." |
| "Substitui meu Excel/BI?" | "Não. Por enquanto ele roda junto. Só faz sentido trocar alguma coisa quando você confiar nele." |
| "A IA decide sozinha?" | "Não. As regras de conferência são fixas. Toda decisão fica registrada com o nome de quem decidiu." |
| "Quando fica pronto?" | "Depende das prioridades que você definir e das informações que eu preciso de você. Prefiro te dar um prazo depois de hoje." |
| Um número que você não tem | "Deixa eu abrir aqui." *[tela da DRE]*, ou: "Não tenho esse número agora; anoto e te mando." |

> **Para mais respostas, veja o FAQ (seção 5). Para o roteiro detalhado com todos os números, veja a seção 2.**

---

## 0. ANTES DA REUNIÃO — checklist obrigatório (bastidores, não mostrar)

### 0.0 Situação dos ajustes (atualizado em 02/10/2026, à tarde)

Backup do banco feito antes de qualquer ajuste: `Documentos\onyx_backups\pre_presentation_fixes_2026-10-02.dump`.

| # | Ponto | Situação |
|---|---|---|
| 1 | Aviso "dados sintéticos" | ✅ Resolvido. Variável desligada (API e rotinas reiniciadas), instrução do Assistente regravada, selo do topo sumiu e relatório novo gerado às 14:51, que diz "Dados das fontes autorizadas. Confira o período e a data de importação." |
| 2 | DREs sem cálculo | ✅ 144 cálculos feitos (jan–jun × consolidado + 23 unidades). **Prontos**: consolidado, Administração Central, Juazeiro-BA, Sento Sé-BA, Mossoró-RN, Juazeiro do Norte, Toledo-PR, Itabirito-MG e "Sem unidade no NG", em todos os meses. As 49 combinações "não prontas" são unidades **sem nenhum lançamento** naquele mês (motivo: "sem realizado"); evite abrir Macau, Natal, Aparecida, Guarulhos, Quixadá, Diretoria e os aterros. |
| 3 | Justificativas de teste na 392 | ⏸️ **Não alterado** (decisão sua, veja abaixo). |
| 4 | Conversas de teste no histórico | ✅ As 37 conversas antigas foram apagadas (exclusão reversível). ⚠️ **Sobraram 2 conversas de teste minhas** ("Fechamento junho/2026…" e "Análise sem título"), com a resposta errada do item 5. **Apague as duas** pelo menu de cada uma em **Conversas** (a exclusão por mim foi bloqueada). |
| 5 | Assistente | ✅ **Defeito da DRE corrigido** no código e aplicado no TON em execução. Teste: a conversa "Fechamento Junho/2026: DRE e Pendências" (2min04s) traz a DRE de junho com os números iguais aos da tela. ⚠️ **Falta reconstruir a tela web**: enquanto isso não for feito, frases com dois "R$" aparecem embaralhadas, como fórmula. Depois da reconstrução, abra essa conversa pronta na reunião. **Não faça perguntas ao vivo** (2 minutos por resposta). Sem a reconstrução, não mostre o Assistente. |
| 6 | Efeito colateral corrigido | Junho (consolidado + 7 unidades + Sem unidade) foi recalculado por último, para ser o cálculo mais recente. |

**Sobre o item 3 (392):** as três decisões registradas classificam a 392 na **conciliação com o faturamento** ("Lançamento complementar" e depois "Eventos distintos"). Elas **não mudam nenhum número da DRE**, porque a DRE usa só o realizado do NG. O tratamento da duplicidade em si está na ocorrência da revisão do NG, que tem justificativa completa. Porém "Eventos distintos" contradiz a explicação da reunião ("é a mesma nota"). Opções:
- (a) **Deixar como está** e falar na reunião: "essas classificações de conciliação foram testes meus; a decisão de verdade sobre a 392 é sua". Risco zero.
- (b) Registrar uma nova classificação com justificativa clara. Isso exige reprocessar a base e recalcular de novo as 144 DREs (há backup). Fica limpo, mas as versões de teste continuam visíveis no histórico, porque o histórico não se apaga.

Na exploração apareceram pontos que **atrapalham a apresentação se não forem resolvidos antes**. Por ordem de gravidade:

| # | Problema encontrado | Onde aparece | O que fazer |
|---|---|---|---|
| 1 | O selo **"Ambiente de demonstração — dados sintéticos"** fica no topo de todas as telas, mesmo com os dados reais | Cabeçalho, relatório "Fechamento preliminar mensal" e respostas do Assistente ("os dados deste ambiente são sintéticos…") | A variável de ambiente `TON_DEMO_SYNTHETIC_DATA` está ligada no servidor local. Desligar (`false`), reiniciar o servidor e depois **Automações → Fechamento preliminar mensal → "Executar agora"** para gerar o relatório de novo sem o aviso. Sem isso, a primeira pergunta dela vai ser "mas isso é dado de mentira?". |
| 2 | Só **junho/consolidado** tem DRE calculada na base atual. Jan–mai e **todas as unidades** mostram *"A base está pronta, mas ainda não há cálculo oficial para este período"* | Fechamento → DRE, ao trocar Período ou Escopo | Na própria tela da DRE, clicar em **"Recalcular DRE"** em cada combinação que você pretende mostrar. Mínimo: junho para Toledo-PR, Mossoró-RN, Juazeiro do Norte, Itabirito-MG, Sento Sé-BA, Juazeiro-BA, Administração Central e "Sem unidade no NG". Se quiser mostrar o mês de abril (parcelamentos), recalcular **abril consolidado**. Se quiser mostrar a 392, recalcular **fevereiro consolidado**. (Existem cálculos por unidade, mas de uma base anterior. A tela usa a base mais recente.) |
| 3 | A trilha de decisões mostra justificativas de teste: **"teste"**, **"ng erradxo"**, **"foi erro no ng"**. A nota 392 aparece como "Lançamento complementar" (versão 1) e depois como "Eventos distintos" (versões 2 e 3) | Fechamento → Visão geral → "Decisões recentes"; Administração do TON → "Trilha de decisões financeiras"; Visão Geral → "Atividade do TON" | As versões antigas ficam guardadas (é auditoria, não dá para apagar). Opções: (a) registrar agora uma nova decisão com justificativa clara, que vira a versão mais recente e aparece primeiro; ou (b) assumir na reunião: "essas primeiras foram testes meus na preparação, e o histórico guarda tudo, inclusive os testes". **Não esconda.** Se ela vir, é melhor que você tenha falado antes. |
| 4 | O histórico de conversas na barra lateral tem conversas da fase de testes: "Pendência Unidade de demonstração", "Fechamento financeiro 07/2026", "Bloqueios DRE julho 2026" etc. | Barra lateral → Histórico; tela Conversas | Arquivar ou apagar as conversas antigas antes da reunião, ou não abrir a barra de histórico. As conversas feitas antes de 08:35 de hoje são da fase de testes. |
| 5 | O Assistente demorou **2min17s (23 etapas)** para responder "Quais pendências impedem a publicação da DRE…" | Assistente | **Não faça pergunta ao vivo** sem ter ensaiado. Se quiser mostrar o Assistente, faça a pergunta antes da reunião (depois do item 1) e abra a conversa pronta. |
| 6 | A DRE e a tela de Pendências levam alguns segundos para carregar (mostram barras cinzas) | DRE, Pendências | Abrir as telas em abas antes de começar. |
| 7 | O card "Especialistas" do CFO diz "Nenhuma margem, previsão ou DRE foi calculada nesta análise" | Especialistas | Não leia essa frase em voz alta. Ela se refere à análise automática, não à DRE (que está calculada). Se ela perguntar, veja o FAQ 18. |

### 0.1 Fontes: como deixar prontas e o que mostrar (pedido de hoje)

**Onde estão os arquivos (Drive da Luyla, pasta compartilhada):**

| Fonte no TON | Arquivo | Local no Drive |
|---|---|---|
| NG / Lançamentos financeiros | `Completo - Jan-Jun 2026 - Lançamentos Financeiros.xlsx` (versão "ok", 1,6 MB) | `DRE Jun-26 › Lançamentos em Lote - jan a Jun-26` |
| Faturamento / Notas fiscais | `RESUMO NOTAS FISCAIS - FATURAMENTO VALE NORTE -.xls` | raiz da pasta |
| Dotação / Orçamento | `DOTACAO (MOSSORO - RN) 14082026 14h.xlsx`, `DOTACAO (JUAZEIRO BA) 30032026 (1).xlsx`, `DOTACAO (ITABIRITO MG) 17102025.xlsx` | `Dotações - João Hebert (jul-26)` |
| (referência, não é importado) | `Banco de Dados (Vale Norte).xlsm` | raiz da pasta |
| (referência, não é importado) | `DRE de Controladoria (1).pbix`, `Vale Norte.pbix` | `DRE Jun-26` |

Baixe esses arquivos para uma pasta local (ex.: `Documentos\TON_Fontes_ValeNorte`) para tê-los à mão. Abra o Banco de Dados no Excel antes da reunião: ele será usado na etapa das diferenças.

**Recomendação: NÃO reimporte nada ao vivo no ambiente da reunião.** Conferi como a importação funciona:

- Uma nova importação do NG cria uma **revisão nova, do zero**. As decisões já registradas (a duplicidade da 392, os 19 sem unidade) **não são reaproveitadas** pela revisão nova, e voltam como pendência.
- **Qualquer** importação (NG, faturamento ou dotação) recalcula a base **incluindo as três dotações**. A DRE de hoje foi montada só com o realizado (Orçado = 0), porque a forma de ler as dotações (mapeamento e sinal) ainda não foi validada. Uma importação ao vivo muda isso e deve tirar a DRE de "Pronta".
- O arquivo de Juazeiro no Drive se chama `... 30032026 (1).xlsx`, mas o importado se chama `... 30032026.xlsx`. O TON agrupa as dotações pelo nome do arquivo, então importar com o "(1)" criaria uma **quarta** dotação, duplicando Juazeiro.

**Como mostrar as fontes com segurança (o roteiro abaixo já usa isso):**
1. Fontes → expandir **NG / Lançamentos financeiros** (seta à direita da linha) → mostrar o **Histórico de importações** e clicar no arquivo para abrir o resultado: 6.307 registros importados, 4 rejeitados, 51 avisos, e a lista "Pendências encontradas".
2. Clicar em **"Atualizar dados"** de qualquer fonte para mostrar a janela de envio ("Selecione um arquivo XLSX desta fonte", "Escolher arquivo / Ou arraste um arquivo para cá") e depois clicar em **"Cancelar"**. Fale: "todo mês é assim: o arquivo que você já exporta entra aqui".
3. Se mesmo assim quiser importar ao vivo: faça um backup do banco antes, importe **no fim da reunião**, avise que isso reabre as pendências e restaure o backup depois.

### 0.2 Mostrar o estado corrigido ou o tratamento?

Mostre o **estado já tratado**, e o **caminho do tratamento pelo histórico**: o que foi encontrado, a evidência, a decisão, quem decidiu e quando. Não refaça o tratamento ao vivo (pelo motivo acima). E apresente cada decisão como **proposta para ela validar**, não como fato consumado. Quem tem autoridade sobre essas regras é a Controladoria.

---

## 1. Objetivo e mensagem principal

**Objetivo da reunião:** Luyla entender, em 30–40 minutos, o que é o TON, ver a DRE dela montada com os dados reais de jan–jun/2026, ver que o TON **encontra e explica** inconsistências com evidência, e sair com **as decisões que só ela pode tomar** (regras de classificação, duplicidades, parcelamentos, dotações).

**Mensagem principal (diga com estas palavras ou parecidas):**

> "O TON não substitui o NG, o Excel nem o Power BI. Ele lê os mesmos arquivos que você já usa, mostra de onde vem cada número, aponta o que parece inconsistente e deixa a decisão com você. Hoje ele já monta a DRE de jan a jun com os dados reais. O que eu preciso agora é da sua validação das regras."

**Três coisas que ela deve levar da reunião:**
1. Cada número da DRE pode ser rastreado até a linha do arquivo do NG.
2. O TON encontrou coisas concretas (a 392 duplicada, os 19 sem unidade, as repetições no Banco de Dados) e não "corrigiu sozinho": registrou e pediu decisão.
3. Ainda falta muita coisa (integração direta com o NG, orçado × realizado, histórico de 2025), e a próxima etapa depende dela.

---

## 2. Roteiro (≈ 35 minutos)

Abas abertas antes de começar, nesta ordem:
1. `localhost:3000/ton` (Visão Geral)
2. `localhost:3000/ton/fontes` (Fontes)
3. `localhost:3000/ton/dre` (Fechamento → DRE)
4. `localhost:3000/ton/fechamento` (Fechamento → Visão geral)
5. `localhost:3000/ton/automacoes` (Automações)
6. `localhost:3000/ton/especialistas` (Especialistas)
7. Excel: `Banco de Dados (Vale Norte).xlsm`

---

### Etapa 1 — O que é o TON (3 min)

- **TELA:** Visão Geral
- **COMO CHEGAR:** menu lateral → **Visão Geral** (ou clique no logo Vale Norte)
- **MOSTRAR:**
  - Saudação "Aqui está o que precisa da sua atenção hoje."
  - Os quatro cartões: **FECHAMENTO · DRE "Pronta"**, **PENDÊNCIAS "0"**, **FONTES "1/3"**, **PRÓXIMA AUTOMAÇÃO "03 de nov., 08:00"**.
  - O menu lateral: Visão Geral, Assistente, Fechamento (DRE, Pendências), Automações, Relatórios, Fontes, Especialistas.
- **FALAR:**
  > "O TON é uma controladoria digital para a Vale Norte. Ele pega os arquivos que você já trabalha (o NG, o faturamento, as dotações), confere, monta a DRE e aponta o que precisa de decisão. Esta é a página de entrada: em um olhar, ela diz se o fechamento está pronto, se há pendência, se as fontes estão em dia e quando roda a próxima rotina."
  >
  > "Vou te mostrar com os dados reais de janeiro a junho de 2026. Os dados de teste que existiam foram apagados hoje de manhã."
- **OBJETIVO:** Ela entender que é uma ferramenta de controle, não um chat.
- **TRANSIÇÃO:** "Antes de qualquer número, deixa eu te mostrar de onde vêm os dados."

> Se ela perguntar do "1/3" em Fontes: veja o FAQ 15.

---

### Etapa 2 — As fontes (4 min)

- **TELA:** Fontes
- **COMO CHEGAR:** menu lateral → **Fontes**
- **MOSTRAR:**
  1. O topo: **MODO DE AQUISIÇÃO "Arquivo exportado — Importação manual (XLSX/XLS)"** e **INTEGRAÇÃO DIRETA NG "Aguardando acesso e configuração"**.
  2. Os dois quadros: "Hoje: arquivo exportado do NG — Em uso" e "Próximo: conexão direta (VPN/API ou base de leitura) — Aguardando acesso".
  3. As três fontes: **NG / Lançamentos financeiros** (6.307 registros), **Faturamento / Notas fiscais** (1.258 registros), **Dotação / Orçamento** (3 arquivos de 15 linhas cada).
  4. Clicar na **seta à direita** da linha do NG → **Histórico de importações (1)** → clicar em `Completo - Jan-Jun 2026 - Lançamentos Financeiros.xlsx` → mostrar **6.307 importados · 4 rejeitados · 51 avisos** e a lista **Pendências encontradas** (Unidade ausente 19, Valor inválido 4, etc.).
  5. Clicar em **Atualizar dados** → mostrar a janela de envio → **Cancelar**.
- **FALAR:**
  > "Hoje os dados entram como entram para você: pelo arquivo exportado. Usei a versão 'ok' do NG de jan a jun que estava na pasta *DRE Jun-26*, o resumo de notas fiscais e as três dotações (Mossoró, Juazeiro-BA e Itabirito). O Banco de Dados (Vale Norte) eu usei como referência para entender como você classifica as contas, mas ele não é importado."
  >
  > "Repare que o TON não esconde o que não conseguiu ler: 4 linhas do NG foram rejeitadas, 19 lançamentos vieram sem unidade, e cada coisa dessas vira um item para olhar."
  >
  > "A conexão direta com o NG ainda **não existe**. Está escrito aqui: aguardando acesso. Hoje é arquivo."
- **DADOS:** [DADO REAL] 6.307 registros NG; 4 rejeitados; 51 avisos; 1.258 notas de faturamento (15 linhas rejeitadas, 1 aviso); 3 dotações sem rejeição.
- **OBJETIVO:** Confiança de que nada foi inventado, e clareza de que **não há integração** com o NG.
- **TRANSIÇÃO:** "Com essas fontes, o TON montou a DRE. Vamos ver."

---

### Etapa 3 — A DRE real (6 min)

- **TELA:** Fechamento → DRE
- **COMO CHEGAR:** menu lateral → **Fechamento → DRE** (ou a aba **DRE** dentro de Fechamento)
- **MOSTRAR:**
  1. Topo: **PERÍODO "Junho de 2026"**, **ESCOPO "Consolidado"**, **MESES DO EXERCÍCIO** jan–jun todos marcados como prontos.
  2. Selo **"Resultado oficial — Calculado em 02/10/2026"**.
  3. Cartões: **REALIZADO -R$ 361.153,06** (acumulado -R$ 128.226.287,81) e **ORÇADO R$ 0,00**.
  4. A tabela: 1 RECEITA LÍQUIDA → 2 CUSTOS MÃO DE OBRA → 3 CUSTOS OPERACIONAIS → RESULTADO OPERACIONAL → 4 FINANCIAMENTO → RESULTADO APÓS FINANCIAMENTO → **MOVIMENTOS NÃO GERENCIAIS (fora do resultado)**.
  5. Clicar em **Combustível** ("Ver composição") → abre o painel **COMPOSIÇÃO DA LINHA** com os **36 lançamentos** de junho: natureza "3.01 · COMBUSTÍVEL", unidade, data, documento, arquivo, **"Planilha Jun ok · linha 1.933"**, "Revisão: Revisado".
  6. (Opcional) **Base e estrutura** → mostrar o nome **"DRE Gerencial Vale Norte (formato da controladoria)"**.
- **FALAR:**
  > "Essa é a DRE gerencial no formato da Controladoria, com as mesmas naturezas que você usa. Junho: receita líquida de R$ 10,4 milhões, resultado após financiamento de -R$ 361 mil. No acumulado, -R$ 128,2 milhões. Já já eu explico esse acumulado, porque ele tem uma linha que pesa muito."
  >
  > "O mais importante: clico em qualquer linha e vejo de onde veio. Aqui são os 36 lançamentos de combustível de junho, cada um com a planilha e a linha do arquivo do NG. Você consegue conferir qualquer número na fonte."
  >
  > "O Orçado está zerado **de propósito**. Eu importei as dotações, mas ainda não sei com certeza como elas devem ser lidas (sinal, competência, qual conta casa com qual natureza). Preferi mostrar zero a mostrar um orçado errado. Isso é uma das coisas que eu preciso validar com você."
- **DADOS (junho/2026, consolidado)** [DADO REAL]:

  | Linha | Junho | Acumulado jan–jun |
  |---|---:|---:|
  | 1 Receita líquida | R$ 10.409.196,48 | R$ 59.025.246,21 |
  | 2 Custos mão de obra | -R$ 4.567.371,70 | -R$ 26.710.782,58 |
  | 3 Custos operacionais | -R$ 6.159.813,33 | -R$ 162.276.929,93 |
  | — dos quais Parcelamentos | R$ 0,00 | -R$ 128.878.935,13 |
  | Resultado operacional | -R$ 317.988,55 | -R$ 129.962.466,30 |
  | 4 Financiamento | -R$ 43.164,51 | R$ 1.736.178,49 |
  | **Resultado após financiamento** | **-R$ 361.153,06** | **-R$ 128.226.287,81** |
  | Movimentos não gerenciais (fora do resultado) | R$ 242.380,66 | R$ 4.307.726,59 |

- **ATENÇÃO:**
  - A linha **Impostos s/faturamento está zerada**, e a receita se chama **"Faturamento (líquido de retenções, NG)"**. [INTERPRETAÇÃO] A receita já vem líquida das retenções do NG. Pergunte a ela se é assim que ela quer ver (veja a pergunta R1).
  - **Nenhum valor desta DRE foi validado por ela.** Fale "a DRE que o TON montou", não "a DRE correta".
- **OBJETIVO:** Mostrar que a DRE existe, segue o formato dela e é rastreável.
- **TRANSIÇÃO:** "Isso é o consolidado. Também dá para ver por unidade."

---

### Etapa 4 — Unidades (3 min)

> As unidades já foram recalculadas (checklist 0.0, item 2). Use só as 7 principais e "Sem unidade no NG". As unidades sem lançamento no mês mostram "não pronta".

- **TELA:** Fechamento → DRE
- **COMO CHEGAR:** na DRE, clicar no seletor **ESCOPO** (onde está "Consolidado")
- **MOSTRAR:**
  1. A lista de unidades do NG: 000001 Administração Central, 000002 Juazeiro-BA, 000005 Sento Sé-BA, 000009 Mossoró-RN, 000026 Juazeiro do Norte, 000028 Toledo-PR, 000030 Itabirito-MG… e também 000027 Mossoró Aterro, 000033 Itabirito Aterro, 000034 Juazeiro do Norte - Aterro, os mútuos, Chácara, Diretoria… e no fim **SEM-UNIDADE · Sem unidade no NG**.
  2. Escolher **000028 · TOLEDO-PR** → mostrar a DRE da unidade.
  3. Trocar para **Mossoró-RN** ou **Itabirito-MG**.
- **FALAR:**
  > "As unidades são as unidades administrativas do NG, com o mesmo código. A lista tem 22, porque inclui centros como Mútuos, Chácara e Diretoria, além das operações. Para a conversa de hoje, as principais são Mossoró, Juazeiro do Norte, Toledo, Itabirito, Sento Sé, Juazeiro-BA e Administração Central."
  >
  > "Note que existe uma 'unidade' chamada **Sem unidade no NG**. Eu não joguei esses lançamentos em lugar nenhum. Eles ficam visíveis à parte até alguém dizer a unidade certa."
- **DADOS:** [DADO REAL] 22 unidades administrativas + "Sem unidade no NG". Leia os valores de cada unidade **na tela**. Não foram anotados aqui porque o cálculo atual por unidade é de uma base anterior.
- **OBJETIVO:** Mostrar que o consolidado se abre por unidade, e abrir o tema "sem unidade".
- **TRANSIÇÃO:** "E como o TON sabe em que linha da DRE cada lançamento cai? Pelas classificações."

---

### Etapa 5 — Classificações (3 min)

- **TELA:** Fechamento → DRE → painel **COMPOSIÇÃO DA LINHA** (qualquer linha) + Excel do Banco de Dados
- **COMO CHEGAR:** na DRE, clicar no nome de uma linha (ex.: **Locação** ou **Folha**)
- **MOSTRAR:**
  1. No painel, o código e a natureza de cada lançamento (ex.: "3.01 · COMBUSTÍVEL").
  2. No Excel: abas **BANCO DE DADOS** (código do NG → natureza) e **AUXILIARES** (natureza → grupo da DRE).
- **FALAR:**
  > "Não inventei classificação. Usei a sua estrutura: no Banco de Dados, a aba *BANCO DE DADOS* diz qual natureza cada código do NG tem, e a aba *AUXILIARES* diz em que grupo da DRE cada natureza cai. O TON seguiu isso. São 26 linhas, uma por natureza, mais 'Movimentos não gerenciais', que fica fora do resultado, como no seu BI."
  >
  > "Se alguma classificação estiver diferente do que você faz hoje, é exatamente isso que eu quero ouvir. Uma mudança de regra fica registrada com data, quem decidiu e por quê."
- **DADOS:** [DADO REAL] 26 contas na estrutura "DRE Gerencial Vale Norte (formato da controladoria)", baseadas nas abas BANCO DE DADOS e AUXILIARES do *Banco de Dados (Vale Norte).xlsm*.
- **OBJETIVO:** Ela reconhecer a própria estrutura e entender que mudar uma regra é decisão dela.
- **TRANSIÇÃO:** "Agora o primeiro achado concreto."

---

### Etapa 6 — Nota 392 de Toledo (4 min)

- **TELA:** Fechamento → Visão geral (**Decisões recentes**) e, se recalculou fevereiro, DRE de **Fevereiro de 2026** → composição de **Faturamento (líquido de retenções, NG)**
- **COMO CHEGAR:** menu lateral → **Fechamento** → aba **Visão geral** → rolar até **Decisões recentes**
- **MOSTRAR:**
  1. As entradas "Conciliação classificada — 392 / 2600000000392".
  2. (Se ensaiado) Composição da linha em fevereiro, mostrando a 392 apenas uma vez.
- **FALAR:**
  > "Na planilha *Fev ok* do NG, a linha 30 (documento **2600000000392**) repete a nota da linha 29 (documento **392**): mesma conta, mesma data e mesmo valor bruto, **R$ 758.696,86**, Toledo, mas com retenção e líquido diferentes (616.061,85 × 706.726,12). Parece a mesma nota escrita de dois jeitos: uma vez só o número, outra com o ano e zeros na frente. No faturamento, a nota existe uma vez só, com líquido de 616.061,85, igual à linha 29." (Mapa completo das linhas no roteiro de leitura, Parte 4.1.)
  >
  > "Pelo que vi no seu Banco de Dados, você já tinha tratado isso zerando as duas linhas e usando a nota do faturamento. O TON fez diferente: manteve a primeira e tirou a cópia do realizado, deixando registrado o motivo e pedindo a correção no NG."
  >
  > "Essas decisões que aparecem aqui fui eu que registrei, na preparação, e as primeiras foram testes. Mas a ideia é exatamente essa: **quem decide é a Controladoria**. Você concorda com esse tratamento ou prefere o seu?"
- **DADOS:**
  - [DADO REAL] Ocorrência registrada na revisão do NG: *Fev ok*, linha 30 × linha 29, documentos 2600000000392 × 392, classificada como **duplicidade com o documento em outro formato**, com bloqueio do fechamento até ser decidida.
  - [DADO REAL] Valor: R$ 758.696,86, Toledo (fornecido na preparação; confirme na composição ou no arquivo antes de citar).
  - [INTERPRETAÇÃO] O NG grava a mesma nota com duas numerações.
  - [HIPÓTESE] Erro de digitação ou de integração na origem. Só ela ou a equipe dela pode confirmar.
- **OBJETIVO:** Mostrar um achado de ~R$ 0,76 mi com evidência de linha e planilha, e pedir a decisão dela.
- **TRANSIÇÃO:** "Esse foi um caso no NG. No seu Banco de Dados encontrei outro tipo de repetição."

---

### Etapa 7 — 2.325 linhas repetidas e a conta 9.6.0009 (4 min)

- **TELA:** Excel `Banco de Dados (Vale Norte).xlsm` (**não há tela do TON para isso**)
- **COMO CHEGAR:** trocar para a janela do Excel
- **MOSTRAR:** a aba BANCO DE DADOS filtrada na conta **9.6.0009** (prepare o filtro antes).
- **FALAR:**
  > "Comparando o seu Banco de Dados com o NG, encontrei **2.325 linhas repetidas**. Na conta 9.6.0009, isso pesa: no Banco de Dados ela soma **cerca de R$ 2,52 milhões**; sem as repetições, **cerca de R$ 1,52 milhão**. É quase R$ 1 milhão de diferença numa conta só."
  >
  > "Não estou dizendo que o seu arquivo está errado. Pode ser que a repetição seja intencional, por exemplo uma etapa da consulta que traz o mesmo lançamento duas vezes por causa de rateio ou de outra junção. Preciso que você me diga se essas linhas deveriam estar lá."
- **DADOS:**
  - [LEVANTAMENTO] 2.325 linhas repetidas no Banco de Dados; 9.6.0009 ≈ R$ 2,52 mi no BD × ≈ R$ 1,52 mi sem repetições.
  - [HIPÓTESE] Duplicação gerada no tratamento do arquivo (junção de consultas ou cópias). **Não confirmada.**
- **CUIDADO:** esse número **não aparece em nenhuma tela do TON**. Não diga "o TON mostra". Diga "na preparação, comparando com o NG, eu encontrei".
- **OBJETIVO:** Mostrar que o trabalho de cruzar as fontes já produz valor, sem acusar o arquivo dela.
- **TRANSIÇÃO:** "Outro ponto que aparece direto no TON são os lançamentos sem unidade."

---

### Etapa 8 — 19 lançamentos sem unidade (2 min)

- **TELA:** Fontes (resultado da importação do NG) e/ou Fechamento → Visão geral → **Achados da revisão financeira**
- **COMO CHEGAR:** Fontes → seta do NG → arquivo → "Pendências encontradas: **Unidade ausente 19**"; ou Fechamento → rolar até **Achados da revisão financeira**
- **MOSTRAR:** o texto do achado: *"Este lançamento não possui unidade administrativa, necessária para atribuição ao contrato/unidade no fechamento gerencial."* e, no relatório, a recomendação *"Informe a unidade administrativa no NG. Nenhum valor é sugerido porque não há evidência estruturada que determine uma única unidade."*
- **FALAR:**
  > "São 19 lançamentos que vieram do NG sem unidade. O TON não chuta a unidade. Ele separa num grupo próprio, 'Sem unidade no NG', que entra no consolidado mas não aparece em nenhuma unidade. O certo é corrigir na origem. Você sabe quem lança esses itens?"
- **DADOS:** [DADO REAL] 19 lançamentos com unidade em branco no NG (jan–jun/2026); hoje marcados como **"Risco aceito"** no relatório, para não travar a DRE.
- **OBJETIVO:** Mostrar o comportamento de não inventar dados.
- **TRANSIÇÃO:** "E agora o maior número da DRE."

---

### Etapa 9 — PARCELAMENTOS (4 min)

- **TELA:** Fechamento → DRE (Junho, Consolidado), coluna **Acumulado**
- **COMO CHEGAR:** DRE → linha **Parcelamentos** dentro de 3 CUSTOS OPERACIONAIS
- **MOSTRAR:** acumulado **-R$ 128.878.935,13**, comparado com o resultado acumulado de **-R$ 128.226.287,81**. (Se recalculou abril: período **Abril de 2026** → clicar em **Parcelamentos** → ver os lançamentos.)
- **FALAR:**
  > "Essa linha sozinha tem R$ 128,9 milhões no acumulado, praticamente todo o resultado negativo do semestre. Pela distribuição por mês, ela se concentra em abril (cerca de R$ 90,9 mi) e maio (cerca de R$ 38,0 mi)."
  >
  > "No relatório de inconsistências de junho já havia o ponto de que, em abril, os termos de transação tributária foram lançados pelo saldo total dos acordos, e não pela parcela do mês. **Eu não mudei nada disso.** A DRE mostra como está no NG. Por isso é um ponto para você validar: esse valor deve ficar na DRE do período, ou só a parcela paga?"
- **DADOS:**
  - [DADO REAL] Parcelamentos acumulado jan–jun = -R$ 128.878.935,13.
  - [DADO REAL] Por mês (cálculo anterior por mês, cuja soma é igual ao acumulado atual): fev ≈ -R$ 13 mil; abr ≈ -R$ 90,89 mi; mai ≈ -R$ 37,97 mi.
  - [HISTÓRICO] Relatório de 15/06/2026: abril tinha 7 lançamentos de transação tributária somando ≈ R$ 90,9 mi, e o relatório recomendava lançar só a parcela mensal.
  - [INTERPRETAÇÃO] Sem a linha de Parcelamentos, o acumulado seria de **cerca de +R$ 0,65 mi** (conta simples: -128.226.287,81 + 128.878.935,13). **Não é um número do TON, é só aritmética.** Use só se ela perguntar "e sem isso?".
  - [HIPÓTESE] Maio repete o mesmo padrão de abril (saldo de acordo lançado inteiro). **Não verificado.**
- **NÃO DIGA:** "esses R$ 128,9 mi estão errados". Diga: "é o maior ponto para validação".
- **OBJETIVO:** Ela decidir o tratamento de parcelamentos, a decisão de maior impacto.
- **TRANSIÇÃO:** "Isso me leva às diferenças entre o que o TON mostra e o seu Banco de Dados."

---

### Etapa 10 — Diferenças com o Banco de Dados (3 min)

- **TELA:** Fechamento → DRE + Excel
- **COMO CHEGAR:** já estão abertos
- **FALAR (leia a lista com calma):**
  > "Se você comparar esta DRE com a do seu BI, ela **não vai bater exatamente**, e eu sei por quê, em pelo menos cinco pontos:"
  > 1. "**Repetições:** as 2.325 linhas repetidas que estão no Banco de Dados não estão no TON, porque ele lê o NG direto."
  > 2. "**Nota 392:** você zerou as duas linhas e usou a nota; o TON manteve uma e tirou a cópia."
  > 3. "**4 linhas de janeiro, cerca de R$ 13,9 mil**, ficaram fora porque o valor na planilha *Jan ok* não é um número válido (linhas 1086, 1087, 1100…). O TON não adivinha valor."
  > 4. "**Orçado zerado:** as dotações foram importadas, mas não entram até a gente validar a leitura."
  > 5. "**Receita:** aqui a receita vem do NG, líquida das retenções. Se no seu BI a receita vem do faturamento, vai haver diferença."
  > 6. "**PIS/COFINS:** a apuração da Contabilidade dá cerca de R$ 3,86 milhões a recolher no semestre, e a linha 'Impostos s/faturamento' do TON está zerada. O TON ainda não recebe essa apuração."
  >
  > "Cada diferença tem uma causa que dá para apontar. Nenhuma delas é 'o TON está certo e o BD está errado'. São escolhas que você precisa confirmar."
- **DADOS:** [DADO REAL] 4 linhas rejeitadas (valor inválido na coluna F da planilha *Jan ok*); [LEVANTAMENTO] ≈ R$ 13,9 mil; [DADO REAL] conciliação NG × faturamento na base atual: **79 notas conciliadas + 1 classificada como complementar (= 80)**, 2 classificadas como eventos distintos, 35 só no NG, 214 só no faturamento, 929 notas do faturamento sem unidade correspondente. *(A conciliação só aparece na área técnica. Não abra; só cite se perguntarem.)*
- **OBJETIVO:** Antecipar a pergunta "por que não bate?" com causas concretas.
- **TRANSIÇÃO:** "Resumindo o que já existe e o que ainda falta."

---

### Etapa 11 — O que já existe (2 min)

- **TELA:** Automações, depois Especialistas
- **COMO CHEGAR:** menu lateral → **Automações**; depois **Especialistas**
- **MOSTRAR:**
  - Automações: **"Fechamento preliminar mensal" — Agendada**, primeiro dia útil do mês às 08:00, próxima execução **03/11/2026**; "Nenhuma rotina aprova decisões financeiras". Abaixo, **"Aguardando capacidade (8)"**: R1 Varredura diária de exceções, R2 Auditoria semanal de combustível, R4 Reconciliação contratual… todas **Bloqueadas**.
  - Especialistas: **Atuando (3)**: CFO, AUDITOR e CEO. **Aguardando fonte (6)**: COO, FROTA, CONTRATOS, COMPLIANCE, PROCUREMENT, RH, cada um com "PRECISA DE …".
  - (Opcional) Relatórios → "Fechamento preliminar mensal" → **Abrir**. *Só se o relatório foi gerado de novo após o item 1 do checklist.*
- **FALAR:**
  > "Hoje existe uma rotina mensal que roda sozinha no primeiro dia útil e gera um relatório do fechamento. As outras oito estão aqui, mas **bloqueadas**, porque dependem de fontes que ainda não temos: frota, contratos, recebíveis…"
  >
  > "Os 'especialistas' são as frentes de análise. Três trabalham hoje, todas no financeiro. As outras seis estão esperando dados. A tela mostra o que cada uma precisa."
- **OBJETIVO:** Mostrar com honestidade o que funciona e o que é só estrutura pronta.
- **TRANSIÇÃO:** "E o que falta, de forma bem direta."

---

### Etapa 12 — O que falta (2 min)

- **TELA:** nenhuma (fale olhando para ela) ou Fontes (quadro "Próximo: conexão direta")
- **FALAR:** use a seção 4 em versão curta:
  > "Falta: conectar direto no NG, para não depender de arquivo; validar o orçado × realizado com as dotações; fechar o ciclo de 'encontrou → você decide → recalcula → confere se resolveu'; trazer 2025 para comparar; trazer frota, contratos, folha; e colocar isso para uso diário, num ambiente de produção. Hoje é um ambiente de validação, na minha máquina."
- **OBJETIVO:** Sem surpresa depois. Ela sabe exatamente o tamanho do que falta.
- **TRANSIÇÃO:** "Para andar, eu preciso de algumas coisas suas."

---

### Etapa 13 — Próximos passos (3 min)

- **TELA:** Visão Geral (volta ao início)
- **FALAR:**
  > "Proposta de próximos passos, na ordem que eu acho mais útil:
  > 1. Você valida as regras de hoje: parcelamentos, a 392, as repetições do BD e a receita líquida;
  > 2. me diz como ler as dotações, para ligar o orçado;
  > 3. me passa o fechamento de 2025, se fizer sentido;
  > 4. a gente vê com a TI o acesso de leitura ao NG.
  >
  > Prazo eu não consigo te dar agora, porque depende dessas respostas."
- Faça as 5 perguntas da Cola Rápida (seção 10).
- **OBJETIVO:** Sair com decisões, responsáveis e o próximo encontro marcado.

---

## 3. O que já temos

### Pronto (funciona hoje com os dados reais)
- [CAPACIDADE ATUAL] Importação manual dos arquivos do NG, do faturamento e das dotações, com histórico e contagem de importados, rejeitados e avisos por arquivo.
- [CAPACIDADE ATUAL] Revisão automática do NG: linhas rejeitadas, lançamentos sem unidade e duplicidade da mesma nota em dois formatos (caso da 392).
- [CAPACIDADE ATUAL] DRE gerencial no formato da Controladoria, jan–jun/2026, consolidada e por unidade, com acumulado do ano e exportação CSV.
- [CAPACIDADE ATUAL] Rastreabilidade: cada linha da DRE abre os lançamentos com arquivo, aba e linha de origem.
- [CAPACIDADE ATUAL] Registro de decisões com quem, quando, justificativa e versão (as versões antigas ficam guardadas).
- [CAPACIDADE ATUAL] Rotina mensal agendada "Fechamento preliminar mensal" que gera relatório.
- [CAPACIDADE ATUAL, com defeito] Assistente que consulta fontes e pendências. Ainda não reconhece a DRE calculada e leva de 1,5 a 3 minutos por resposta. **Não demonstrar.**

### Em validação (existe, mas depende dela)
- Classificação código NG → natureza → linha da DRE, tirada do Banco de Dados (26 linhas).
- Tratamento da 392 (manter a primeira, tirar a cópia) × o tratamento dela (zerar as duas e usar a nota).
- PARCELAMENTOS ≈ R$ 128,9 mi no resultado do período.
- Receita = faturamento líquido de retenções vindo do NG; impostos s/faturamento = 0.
- Os 19 sem unidade aceitos como "risco aceito" no grupo "Sem unidade no NG".
- Conciliação NG × faturamento (80 notas casadas; 214 só no faturamento; 929 sem unidade correspondente).
- Leitura das 3 dotações (importadas, **fora** da DRE).
- Os achados do levantamento no Banco de Dados (2.325 repetições, 9.6.0009).

### Em desenvolvimento / não existe ainda
- Integração direta com NG/Keevo.
- Orçado × realizado na DRE.
- Ciclo completo pendência → decisão → recalcular → verificar com os dados reais.
- Histórico de 2025.
- Especialistas e rotinas fora do financeiro (8 rotinas e 6 especialistas bloqueados por falta de fonte).
- Ambiente de produção e acesso para a equipe dela.

---

## 4. O que falta (explicação simples)

**Integração direta NG/Keevo** — Hoje alguém exporta o arquivo e eu importo. O próximo passo é o TON ler direto do NG, só leitura, sem alterar nada lá. Depende de acesso (VPN, API ou uma base de leitura) que precisa ser liberado pela TI ou pelo fornecedor. **Não existe hoje e não tem data.**

**Orçado × realizado totalmente validado** — As dotações de Mossoró, Juazeiro-BA e Itabirito foram lidas, mas não entram na DRE porque ainda não está claro: o sinal dos valores, o mês de cada valor (a dotação é anual; o TON não divide por 12 sem regra), qual linha da dotação casa com qual natureza, e o que fazer com as unidades sem dotação. O relatório de junho já dizia que 6 de 7 unidades estavam com dotação desatualizada.

**Pendência → decisão → recalcular → verificar** — Hoje o TON encontra, registra a decisão e recalcula. O que falta é o ciclo fechado: depois da decisão, mostrar "antes 13 pendências, agora 11", e no mês seguinte **conferir sozinho** se a correção foi feita no NG (por exemplo, se a 392 parou de aparecer duplicada). Também falta: uma reimportação reaproveitar as decisões já tomadas.

**Histórico (especialmente 2025)** — Sem 2025 não dá para comparar com o ano anterior, ver sazonalidade ou dizer que algo está fora do normal. O TON não faz previsão nem detecção de anomalia sem histórico, de propósito.

**Outros domínios** — Frota/abastecimento, produção, contratos, folha, compras e documentos. A estrutura está pronta, mas sem fonte não há análise. Os pontos de combustível, locações e contratos do relatório de junho dependem disso.

**Especialistas com fontes reais** — Hoje só CFO, AUDITOR e CEO atuam, e só no financeiro. Os outros seis aparecem como "Aguardando fonte".

**Acompanhamento diário** — Hoje há uma rotina mensal. Falta a rotina diária ("o que mudou desde ontem", "o que está esperando quem"), e ela depende da integração com o NG, porque com arquivo manual não existe dado novo todo dia.

**Produção** — O que ela está vendo roda num ambiente de validação. Falta ambiente definitivo, acesso para a equipe dela, cópias de segurança e as regras de quem pode ver e decidir o quê.

---

## 5. FAQ — perguntas prováveis

**1. "Isso substitui o Excel, o Power BI ou o NG?"**
Não. O NG continua sendo onde se lança. O Excel e o BI continuam até você confiar no TON. O TON entra no meio: lê o que sai do NG, confere e mostra o que precisa de atenção. A ideia é reduzir retrabalho, não trocar a sua ferramenta amanhã.

**2. "A DRE está correta?"**
Ela está calculada com regras explícitas e cada número volta para a linha do NG. Mas "correta" quem diz é você. Há pontos que ainda dependem da sua validação: parcelamentos, a receita líquida, a 392 e o orçado. Por isso eu chamo de "a DRE que o TON montou", não de DRE oficial.

**3. "Por que não bate com o meu BD?"**
Por pelo menos cinco motivos conhecidos: as 2.325 linhas repetidas no BD, o tratamento diferente da 392, as 4 linhas de janeiro fora (~R$ 13,9 mil), o orçado zerado e a receita vinda do NG líquida de retenções. Se sobrar diferença depois disso, é algo que eu ainda não sei explicar, e quero investigar com você.

**4. "De onde vieram as classificações?"**
Do seu Banco de Dados: aba BANCO DE DADOS (código NG → natureza) e aba AUXILIARES (natureza → grupo da DRE). Eu não criei classificação nova.

**5. "Esses R$ 128,9 milhões estão errados?"**
Eu não sei dizer se estão errados. Eles estão no NG assim. O relatório de junho já levantava que, em abril, os acordos tributários foram lançados pelo saldo total. O TON mostra o número como está e marca como ponto de validação. Se a regra for "só a parcela paga entra no resultado", isso vira uma regra registrada com a sua decisão.

**6. "O TON altera meus dados?"**
Não. Ele não escreve no NG, não mexe no seu Excel e não muda o arquivo importado. O arquivo original fica guardado do jeito que entrou. Quando algo é decidido, fica registrado no TON, e a correção na origem continua sendo feita por quem lança.

**7. "A IA decide sozinha?"**
Não. As regras de conferência são fixas e explícitas, não é a IA que "acha" o erro. A IA ajuda a explicar e a resumir. Aprovar classificação, aceitar risco e definir regra exige uma pessoa, e fica registrado quem foi.

**8. "O que falta?"**
Integração direta com o NG, orçado × realizado, ciclo completo de decisão e verificação, histórico de 2025, outros domínios (frota, contratos, folha), rotina diária e ambiente de produção.

**9. "O que você precisa de mim?"**
Validar quatro regras (parcelamentos, a 392, as repetições do BD e a receita líquida), me explicar como ler as dotações, me dizer se faz sentido trazer 2025, e indicar quem na TI pode liberar o acesso de leitura ao NG.

**10. "Quem fez essas decisões que aparecem na tela?"**
Eu, na preparação. Algumas foram testes, e o histórico guarda tudo, inclusive os testes, porque é para auditoria. As decisões de verdade devem ser suas ou de quem você indicar.

**11. "Dá para conectar direto no NG?"**
É o objetivo, mas hoje não existe. Depende de liberação de acesso de leitura. Até lá, é o mesmo arquivo exportado que você já usa.

**12. "Por que o orçado está zerado?"**
Porque eu preferi zero a um orçado errado. As dotações foram lidas, mas a forma de encaixar na DRE (sinal, mês, conta) precisa da sua regra.

**13. "Por que 4 linhas ficaram de fora?"**
Na planilha *Jan ok*, a coluna de valor dessas linhas não tem um número válido (linhas 1086, 1087, 1100…). O TON não adivinha valor. Ele separa e mostra. Somam cerca de R$ 13,9 mil.

**14. "Os 19 sem unidade entram onde?"**
No consolidado, sim; em nenhuma unidade. Ficam num grupo "Sem unidade no NG" até a unidade ser informada na origem.

**15. "Por que aparece 'Fontes 1/3' se as três foram importadas?"**
As três foram importadas. O "1/3" conta quantas estão sem nenhum aviso: a dotação está limpa; o NG (51 avisos, 4 rejeitadas) e o faturamento (15 linhas rejeitadas) ficam como "Requer atenção" até os avisos serem vistos.

**16. "Funciona por unidade?"**
Sim, a DRE abre pelas 22 unidades administrativas do NG, mais o grupo "Sem unidade". Por contrato, ainda não: falta o cadastro de contratos.

**17. "Quanto tempo leva para atualizar quando o NG muda?"**
Importar o arquivo leva segundos. Mas hoje uma reimportação reabre as pendências já decididas e é preciso decidir de novo. Reaproveitar as decisões é uma das melhorias necessárias.

**18. "O especialista CFO diz que nenhuma DRE foi calculada. Como assim?"**
Aquela frase descreve a análise automática daquele momento, não a DRE. A DRE de junho está calculada, com o selo "Resultado oficial". É um texto a ajustar.

**19. "Posso perguntar qualquer coisa para o Assistente?"**
A ideia é essa: perguntar sobre fechamento, fontes e DRE. Mas o Assistente ainda está em ajuste. Hoje ele é lento e ainda não lê a DRE calculada direito. Por isso hoje eu mostro tudo pelas telas.

**20. "Isso detecta fraude?"**
Não. Ele aponta inconsistências, como duplicidade, falta de unidade ou valor inválido. Interpretar se é erro, retrabalho ou outra coisa é papel das pessoas. Ele não acusa ninguém.

**21. "Meus dados estão seguros? Quem vê isso?"**
Hoje roda num ambiente de validação, com acesso só meu. Antes de qualquer uso pela equipe, a gente define quem vê e quem decide o quê. Existe controle de acesso por usuário e grupo.

**22. "Vocês vão usar o relatório de inconsistências de junho?"**
Ele foi a base para entender os problemas. Alguns pontos já aparecem nos dados (parcelamentos de abril). Outros dependem de fontes que ainda não temos (banco, frota, locações).

**23. "O TON faz DFC?"**
Não, hoje só DRE gerencial.

**25. "E o PIS/COFINS? Por que impostos está zerado?"**
Porque a apuração de PIS/COFINS vem da Contabilidade e ainda não entra no TON. Só o export do NG entra. Pelo PDF de agosto, são cerca de R$ 3,86 mi a recolher de janeiro a junho. Se você me confirmar como ele entra na sua DRE, essa vira a próxima fonte.

**24. "E se eu discordar de uma regra?"**
Melhor ainda: a regra muda, fica registrado quem mudou e por quê, a DRE é recalculada e a versão anterior continua guardada para comparação.

---

## 6. Perguntas para a Luyla

**Regras e classificações**
- C1. A classificação código NG → natureza → grupo da DRE do Banco de Dados é a vigente? Há exceções que você faz "na mão" e não estão nas abas?
- C2. "Movimentos não gerenciais" fica fora do resultado no seu BI também?
- C3. Mútuos (Castellu, Cidade Universitária, Controller) e Chácara devem continuar como unidades do resultado, ou ficam fora?

**Duplicidades**
- D1. Na 392 você prefere o seu tratamento (zerar as duas e usar a nota) ou o do TON (manter uma e tirar a cópia)?
- D2. As 2.325 linhas repetidas no Banco de Dados são intencionais? De onde elas vêm no seu tratamento?
- D3. Quem corrige duplicidade no NG, e como você fica sabendo que foi corrigido?

**Parcelamentos**
- P1. Os R$ 128,9 mi de PARCELAMENTOS devem ficar na DRE do período, ou só a parcela paga?
- P2. Se for só a parcela: de onde vem o valor mensal pago (jurídico, tributário, extrato)?
- P3. Maio (~R$ 38 mi) tem a mesma natureza que abril?

**Receita**
- R1. A receita da DRE deve vir do NG líquida de retenções, ou do faturamento bruto com impostos deduzidos?
- R2. Por que o faturamento tem notas sem unidade correspondente no NG (929)? Existe uma tabela de/para de contrato → unidade?
- R3. PIS/COFINS da Contabilidade entra em que linha?

**Orçamento**
- O1. As dotações de Mossoró, Juazeiro-BA e Itabirito são as vigentes? E as outras unidades?
- O2. Os valores da dotação são mensais ou anuais? Positivo é despesa ou receita?
- O3. Como uma linha da dotação casa com uma natureza da DRE?

**Fechamento**
- F1. Em que dia do mês o NG "ok" fica pronto? (O POP fala em dia 09 para o NG e dia 10 para a DRE.)
- F2. O que mais atrasa o seu fechamento hoje?
- F3. A folha entra pelo NG ou por um relatório separado de folha/FGTS?

**Retrabalho**
- T1. Quanto tempo você gasta por mês tratando o export do NG antes de colocar no Banco de Dados?
- T2. Que conferência você faz todo mês igual, que gostaria de não fazer mais?
- T3. Que pergunta a diretoria sempre te faz e que é difícil de responder?

---

## 7. Como responder a divergências sem ficar na defensiva

Use sempre a sequência **ACHADO → HIPÓTESE → DECISÃO → REGRA → CONSEQUÊNCIA**.

| Passo | O que dizer | Exemplo (PARCELAMENTOS) |
|---|---|---|
| **ACHADO** | O fato, com a fonte | "No NG, a natureza PARCELAMENTOS soma R$ 128,9 mi de jan a jun, a maior parte em abril e maio." |
| **HIPÓTESE** | Uma ou mais explicações, como possibilidade | "Pode ser o saldo dos acordos lançado inteiro, como o relatório de junho apontou para abril. Ou pode ser outra coisa que eu não conheço." |
| **DECISÃO** | Perguntar quem decide e o quê | "Você decide: fica no resultado do período ou só a parcela paga?" |
| **REGRA** | Transformar a decisão em regra escrita | "Então a regra fica: 'PARCELAMENTOS de saldo de acordo saem do resultado; entra só a parcela paga, informada pelo tributário'." |
| **CONSEQUÊNCIA** | O que muda depois | "A DRE é recalculada, o acumulado muda, a decisão fica registrada com seu nome e a versão anterior fica guardada." |

**Quando ela disser "isso está errado":**
> "Pode ser. Me mostra como você faz que eu comparo linha a linha. Se a regra do TON estiver diferente da sua, a gente registra a sua."

**Quando ela disser "no meu BD está diferente":**
> "Ótimo, essa comparação é o que mais me ajuda. Já sei de cinco causas de diferença. Vamos ver se essa é uma delas ou uma nova."

**Quando você não souber:**
> "Não sei. Vou verificar e te respondo com a evidência."

---

## 8. Frases a evitar

| Não diga | Diga |
|---|---|
| "O seu Excel / o NG está errado." | "Encontrei uma diferença entre o NG e o BD, e quero entender qual regra vale." |
| "O TON é a fonte da verdade." / "Esse é o número certo." | "Esse é o número que o TON calculou com estas regras. Quem valida é você." |
| "É tudo automático." | "A conferência roda sozinha. A decisão é sempre de uma pessoa." |
| "A IA decidiu / a IA corrigiu." | "A regra encontrou; eu registrei a decisão; você valida." |
| "Já estamos integrados ao NG." | "Hoje entra pelo arquivo exportado. A conexão direta depende de acesso." |
| "Isso aqui está pronto para produção." | "É um ambiente de validação." |
| "Detectamos fraude." | "Encontramos uma inconsistência para revisão." |
| "Em duas semanas sai o orçado." | "Depende da regra das dotações. Depois que você me passar, eu te digo o prazo." |
| "Esses R$ 128,9 mi estão errados." | "É o maior ponto para validação." |
| Termos técnicos (sistema por trás, banco, servidor, código, nomes de ferramentas) | "o TON", "o arquivo", "a regra", "o registro" |

---

## 9. Próxima evolução

```text
ENCONTRA  →  EVIDENCIA  →  EXPLICA  →  DECISÃO HUMANA  →  RECALCULA  →  MOSTRA IMPACTO  →  ACOMPANHA  →  VERIFICA
```

| Passo | Hoje | Exemplo com a 392 |
|---|---|---|
| Encontra | ✅ existe | A regra acha a mesma nota em dois formatos na planilha *Fev ok* |
| Evidencia | ✅ existe | Planilha, linhas 29 e 30, documentos, valor |
| Explica | ✅ existe (texto do achado, relatório, Assistente) | "Mesma conta, data e valor; nota existe uma vez no faturamento" |
| Decisão humana | ✅ existe, registrada com versão | Luyla escolhe o tratamento |
| Recalcula | ✅ existe ("Recalcular DRE") | DRE de fevereiro e acumulado recalculados |
| Mostra impacto | ⚠️ parcial | Falta "antes × depois" automático na tela |
| Acompanha | ❌ falta | Lembrar quem precisa corrigir no NG |
| Verifica | ❌ falta | Na próxima importação, confirmar que a duplicidade sumiu |

> "O TON já encontra, mostra a evidência, explica, registra a sua decisão e recalcula. O que vem agora é ele acompanhar e verificar sozinho se o problema foi resolvido na origem."

---

## 9.1 Material de apoio dos arquivos da Luyla (pasta `plans/ton/DRE Jun-26/`)

> Esses arquivos são dados do cliente. A pasta foi adicionada ao `.git/info/exclude` (vale só na sua máquina) para nunca entrar num commit.

| Arquivo | O que é | Está no TON? | Quando usar na reunião |
|---|---|---|---|
| `Completo - Jan-Jun 2026 - Lançamentos Financeiros.xlsx` (em `DRE Jun-26/Lançamentos em Lote…`) | NG revisado "ok", abas *Jan ok* … *Jun ok* | ✅ importado | Para mostrar a 392 (*Fev ok*, linhas 29 e 30) e as linhas rejeitadas de janeiro (*Jan ok*, linhas 1086, 1087, 1100…) direto no arquivo |
| `RESUMO NOTAS FISCAIS - FATURAMENTO VALE NORTE -.xls` | Resumo das notas fiscais | ✅ importado (1.258 notas) | Para mostrar que a nota 392 existe uma vez no faturamento |
| 3 × `DOTACAO (...)` | Dotações de Mossoró, Juazeiro-BA e Itabirito | ✅ importadas, **fora da DRE** | Pergunta O1–O3 |
| `Banco de Dados (Vale Norte).xlsm` | O "Excel mãe" que alimenta o BI | ❌ só referência | Etapas 5, 7 e 10 (classificações, 2.325 repetições, 9.6.0009) |
| `APURAÇÃO VALE NORTE PIS COFINS 2026.pdf` | Apuração de PIS/COFINS da Contabilidade, posição 07/08/2026 | ❌ **não está no TON** | Etapa 10, item 6, e pergunta R3 |
| `Fluxo de caixa - jan-junho-26 Contas a pagar-receber.pdf` | Relatório analítico de fluxo de caixa (pagamentos e recebimentos), emissão 01/01 a 30/06/2026, posição 07/08/2026, várias empresas/filiais (matriz, MO, JN, PR, IT) | ❌ **não está no TON** | Só se ela falar de caixa/DFC: "o TON ainda não lê o fluxo de caixa; seria uma próxima fonte". **Não foi analisado** (mais de mil páginas). Não cite números dele. |
| `Vale Norte.pbix`, `DRE de Controladoria (1).pbix` | Painéis do Power BI | ❌ | Se ela quiser comparar a DRE do BI com a do TON, abra o painel dela, não tente reproduzir |

### PIS/COFINS: o que dá para dizer [DADO REAL do PDF + INTERPRETAÇÃO]

Apuração "com totalidade de despesas fiscalmente creditáveis", posição 07/08/2026:

| Mês 2026 | Receita base (3.1.1.01.0002 Serviços Prestados a Prazo) | PIS a recolher | COFINS a recolher |
|---|---:|---:|---:|
| Janeiro | R$ 10.101.719,41 | R$ 122.513,46 | R$ 564.304,41 |
| Fevereiro | R$ 6.591.699,68 | R$ 57.489,38 | R$ 264.799,55 |
| Março | R$ 14.575.196,97 | R$ 182.116,84 | R$ 833.005,76 |
| Abril | R$ 10.592.388,95 | R$ 99.838,72 | R$ 459.863,19 |
| Maio | R$ 11.856.995,88 | R$ 123.515,72 | R$ 568.920,87 |
| Junho | R$ 12.196.719,84 | R$ 104.640,29 | R$ 481.979,51 |
| **Jan–jun** | **R$ 65.914.720,73** | **R$ 690.114,39** | **R$ 3.172.873,30** |

PIS + COFINS a recolher no semestre: **R$ 3.862.987,69** (o PDF indica 5,96% s/ faturamento).

**Comparação com a DRE do TON:**
- Receita: PIS/COFINS usa **R$ 65,91 mi** de receita no semestre. A DRE do TON mostra **R$ 59,03 mi** de receita líquida (NG, líquida de retenções). Diferença: **R$ 6,89 mi** no semestre; em junho, R$ 12,20 mi × R$ 10,41 mi (diferença de R$ 1,79 mi).
  - [HIPÓTESE] A maior parte da diferença são as retenções (o TON usa a receita líquida). Também pode haver diferença de mês (emissão × recebimento). **Não verificado.**
- Impostos: a DRE do TON tem **Impostos s/faturamento = R$ 0,00**, mas a apuração mostra **R$ 3,86 mi** de PIS/COFINS a recolher no semestre.
  - [INTERPRETAÇÃO] O PIS/COFINS da Contabilidade não chega ao TON pelo export do NG. Pelo POP, ele vem da Contabilidade até o dia 05. Se a DRE dela inclui esse imposto, a DRE do TON está **sem essa dedução**.

**Como falar:**
> "Uma coisa que eu ainda não tenho no TON é a apuração de PIS/COFINS. Pelo PDF de agosto, são cerca de R$ 3,86 milhões a recolher no semestre, e na DRE do TON essa linha está zerada. Na sua DRE, o PIS/COFINS entra como dedução da receita? Se entrar, essa é uma fonte que eu preciso trazer."

(Acrescentada ao FAQ como pergunta 25.)

---

## 10. COLA RÁPIDA (uma página)

**ABERTURA (30 s)**
> "Luyla, o TON é uma controladoria digital para a Vale Norte. Ele lê os mesmos arquivos que você usa (o NG, o faturamento e as dotações), monta a DRE no seu formato, mostra de onde vem cada número e aponta o que precisa de decisão. Não substitui o NG nem o seu BI, e não decide nada sozinho. Vou te mostrar com os dados reais de jan a jun de 2026, e no fim te digo com franqueza o que ainda falta."

**5 TELAS PRINCIPAIS**
1. **Visão Geral** (`/ton`): status em um olhar.
2. **Fontes** (`/ton/fontes`): arquivos reais, 6.307 lançamentos, 4 rejeitados, 19 sem unidade, NG "Aguardando acesso".
3. **Fechamento → DRE** (`/ton/dre`): DRE no formato dela; clicar numa linha → lançamentos com planilha e linha.
4. **Fechamento → Visão geral** (`/ton/fechamento`): achados e decisões (392).
5. **Automações / Especialistas**: o que roda hoje e o que está bloqueado por falta de fonte.

**5 MENSAGENS**
1. Cada número volta até a linha do NG.
2. O TON encontrou: a 392 (R$ 758.696,86, Toledo) duplicada, 19 sem unidade, 2.325 repetições no BD (9.6.0009: ~R$ 2,52 mi → ~R$ 1,52 mi).
3. PARCELAMENTOS (~R$ 128,9 mi) é o maior ponto de validação, e não foi alterado.
4. Nada é decidido sozinho: a regra encontra, a pessoa decide, fica registrado.
5. Falta integração com o NG, orçado, 2025, outros domínios e produção, e o próximo passo depende dela.

**5 PERGUNTAS**
1. PARCELAMENTOS: fica no resultado do período ou só a parcela paga?
2. Nota 392: o seu tratamento ou o do TON?
3. As 2.325 linhas repetidas no BD são intencionais?
4. Receita: do NG líquida de retenções ou do faturamento bruto?
5. Dotações: mensais ou anuais, qual sinal, e quem mantém?

**FECHAMENTO (30 s)**
> "Hoje você viu a DRE real de jan a jun montada pelo TON, com cada número rastreável, e quatro achados concretos. Nada disso é definitivo sem você. Se você topar, o próximo passo é validar essas quatro regras e me explicar as dotações. Com isso eu ligo o orçado e a gente marca a próxima conversa já com o antes e depois."

**SE TUDO DER ERRADO NA TELA:** volte para o Excel do Banco de Dados e fale dos achados (392, 2.325, 9.6.0009, parcelamentos). Os achados valem mesmo sem a tela.
