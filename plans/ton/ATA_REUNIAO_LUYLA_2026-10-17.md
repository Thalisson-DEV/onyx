# Ata — Reunião Vale Norte / TON — 17/10/2026 (sábado, ~2h36)

Participantes: Luyla Karina (controladoria), Luciana Miranda (controladoria), Thalisson Damião.
Fontes desta ata: transcrição do Meet + notas do Gemini (corrigidas aqui), Drive
`1q3oAEKhD-jvOJ900FMIc-B_k7rxgfx8H` e o código em `main` (ece2add460).

## 1. O que aconteceu

Luyla importou no homolog (Railway) o "Completo Jan-Set 2026 – Lançamentos Financeiros" (o
arquivo cru do NG, não o BD tratado) e o "Resumo Notas Fiscais", classificou as contas novas do
NG (pós-junho), resolveu as pendências e calculou a DRE do ano até setembro. Exportou o Excel
(`DRE Set/26/dre-2026-01-a-09.xlsx`, gerado 17/10 11:31).

Durante a reunião Thalisson entregou e publicou: busca no seletor de natureza (9b87e05333),
justificativa opcional ao classificar/criar natureza (af635aa712), motivo opcional nas decisões
de pendência (ece2add460). Grupos "Mútuo" (fora do resultado) e "Investimento" (próprio, após o
financiamento) foram criados **direto no banco do homolog** — não estão em migração/seed.

## 2. Correções às notas do Gemini

| Gemini disse | O que foi dito |
|---|---|
| "Criar planilha de **multas**" | Planilha à parte de **mútuos** (saídas da Vale para SPE/franquias/outras empresas), para não ficar no resultado. "Multos/mutos" na transcrição = mútuo. |
| Parcelamentos geram "R$ 128.000" acumulados | Acumulado de **~R$ 128 milhões** em parcelamentos — "praticamente o resultado do ano todo negativo" (o ensaio deu −R$ 131 mi no ano). É a maior distorção da DRE. |
| "Ajustar confirmação em lote" (já resolvido) | Pedido: **checkbox por linha** e confirmar só os marcados. Ainda não entregue. |
| Investimento "grupo próprio após financiamento" (decisão final) | Ficou ambíguo: (a) consórcio Bradesco é aplicação → DFC/balanço, fora da DRE; (b) rendimento de aplicação → receita financeira; (c) Thalisson criou grupo próprio "5 INVESTIMENTO (receita financeira)" antes do "Resultado após financiamento". Validar com Eric na segunda. |
| — (omitido) | Pendência de duplicidade deve **mostrar os dois registros lado a lado** e deixar escolher manter o 1º, o 2º ou os dois (parcelas diferentes). Hoje o TON sempre mantém o da primeira linha. |
| — (omitido) | "Lançamento sem unidade administrativa": falta poder **atribuir a unidade** na decisão (hoje só aceitar/ignorar). |
| — (omitido) | Textos das 3 opções de conciliação confundem ("lançamento complementar" × "evento distinto" × "diferença esperada") — reescrever. |
| — (omitido) | Bug: "Não foi possível registrar a decisão. Confira a evidência" na 1ª tentativa de "repetição legítima" (motivo é opcional). |
| — (omitido) | Comparar **meses lado a lado** escolhendo vários meses (ex.: ago e set). Não querem comparar unidades entre si (contratos diferentes); comparam a mesma unidade com anos anteriores. |
| — (omitido) | Outra fonte de pagamentos: o caixa entregue a Tásio semanalmente (terça). |

"Mira", "Mir", "Mirina" e "Miriam" = Miriam. "Tom" = TON. "Omier/Hom" = Omie.

## 3. Decisões

- **Prioridade da semana:** DRE caixa + DRE econômica e custos fixos. Contratos, aditivos,
  apostilamentos e dotação ficam para a 2ª etapa.
- **Agenda:** dom 18/10 9h30 (follow-up) · seg 19/10: Miriam valida as duas DREs (talvez terça
  cedo), reunião com Eric (contabilidade) sobre naturezas; Thalisson só a partir das 11h
  (treinamento em Remanso até 10h30) · qua 21/10: apresentação oficial à diretoria.
- **DRE caixa** = data do pagamento/recebimento (o que o TON usa hoje, segundo Luyla, porque os
  lançamentos financeiros são o caixa). **DRE econômica** = competência; deriva-se da de caixa
  redistribuindo parcelamentos/atrasos ao mês a que pertencem.
- **Estrutura da DRE (anotação da Miriam):** faturamento → retenções → subtotal líquido →
  pagamentos → subtotal → taxas → provisões → tributos não pagos → ajustes de IR → resultado.
  Manter só os 4 tributos pedidos; rever a posição de "impostos s/ faturamento" (PIS/COFINS).
  Luyla manda o detalhamento item a item.
- **Naturezas:** venda de imobilizado e acordos (judiciais, ressarcimento) → "Outras receitas"
  dentro da receita líquida; mútuo → grupo próprio fora do resultado; fundo fixo → natureza
  própria (aberto até a prestação de contas); dois tipos de rescisão (real × provisão); folha
  inclui adiantamento, 13º, consignado, pensão, contribuição sindical, plano de saúde, INSS sem
  folha; recebimento do consórcio de Guarulhos (hoje positivo em despesas operacionais) → receita.
  Evitar "despesas extras" (Miriam não quer nada sem especificar); por ora "despesas diversas".
- **Unidades:** DRE com **várias unidades selecionadas** e total delas; Administração Central
  separada; desativar (não excluir) inativas — Natal, Macau. Unidades continuam vindo do NG.
- **Exportação:** com uma unidade, só aquela unidade (para mandar ao gestor dela); com
  consolidado, o consolidado e abaixo cada unidade.
- **Meses** por extenso (o seletor mostra "Mês"/abreviação).
- **Abas 2020** do resumo de faturamento: ignorar; só 2025–2026 (NF 528 = eventos distintos).
- **Extrato bancário** mensal (Luyla pede a Cláudia) entra como nova fonte. Traz data,
  favorecido e valor; sem número de documento.
- **IA:** DeepSeek via Fireworks (sem retenção; dados LGPD P4), não a API chinesa.
- Luciana usa o login da Luyla até ganhar perfil próprio (simultâneo permitido).

## 4. Pendências — Thalisson

DRE / homolog (antes de segunda):
1. DRE editável "como planilha" (prometido para a tarde de 17/10): editar estrutura, grupos,
   subtotais, ordem e naturezas na própria DRE.
2. Cadastro de **grupos da DRE** pela controladoria (hoje só natureza).
3. Levar Mútuo/Investimento do banco do homolog para migração/seed.
4. Cache/recalculo no homolog lite (DRE pede recálculo a cada unidade; "pendência" falsa em Mossoró).
5. Exportação respeitando o filtro de unidade; consolidado + unidades abaixo.
6. Meses por extenso no seletor. No Excel o cabeçalho saiu "Feb/Apr/May/Aug/Sep" (formato de data
   no locale inglês) e, aberto pelo Drive, as fórmulas `SUMIFS(Base[...])` aparecem `#REF!` —
   Luyla não tem Excel instalado; testar no Google Sheets.
7. DRE com seleção múltipla de unidades; desativar unidades.
8. DRE econômica × caixa (duas estruturas/regimes) + tratamento de parcelamentos lançados pelo total.
9. Seleção por checkbox na confirmação em lote (classificação de contas).

Pendências/conciliação:
10. Duplicidade: mostrar os dois registros e escolher qual manter (ou os dois).
11. Atribuir unidade em "lançamento sem unidade administrativa".
12. Reescrever os textos das decisões de conciliação.
13. Bug do registro de "repetição legítima" na 1ª tentativa.
14. Comparar vários meses lado a lado.
15. Limpar as resoluções para a reimportação de jul/ago (dito na reunião).

Fontes e análises:
16. Extrato bancário como fonte (data, favorecido, valor) e conciliação com o NG.
17. Custos fixos × extrato × NG: pago e lançado / pago e não lançado / lançado e não pago;
    feedback preliminar. Depois: 2% da ADM central cobre os custos fixos? e redução de custos.
18. Mostrar a Eloísa (segunda) como trocar o tipo da coluna Número do documento para texto no Power Query.
19. Perfil próprio da Luciana.
20. Custos mensais (servidor + provedor de IA) para a Luyla levar à diretoria na quarta.

## 5. Pendências — Luyla / Luciana

- Mandar a estrutura detalhada da DRE (subitens e subtotais) e os grupos novos.
- Refazer manualmente jul e ago no Completo Jan-Set e reimportar (o arquivo no Drive foi
  alterado às 14:19 de 17/10, depois da exportação — talvez já esteja corrigido).
- Corrigir a natureza do consórcio de Guarulhos; decidir o consórcio Bradesco com Eric.
- Revisar as naturezas com a contabilidade (Eric, segunda).
- Planilha de mútuos à parte; pedir à Miriam a planilha de custos fixos da ADM central e o
  controle de mútuos (quanto cada sócio resgata).
- Pedir extrato bancário mensal (Cláudia) e a planilha de fluxo de caixa do Mateus (Cláudia ou
  computador do Douglas). A de Ferrari é a do modelo econômico.
- Cobrar o orçamento/dotações faltantes do João; atualizar a planilha de dotação.
- Finalizar a planilha de custos fixos (incluir variáveis recorrentes, rever o "4 milhões" do
  financiamento da Caixa e o item ORBS).
- Tirar Palotina (licitação perdida) da planilha de contratos; incluir Curitiba quando entrar no NG.
- Testar assistente, automações e relatórios.
- Pesquisar se o Omie atende prestação de serviço público.

## 6. Pontos em aberto

- O que exatamente vai na DRE econômica além da redistribuição de parcelamentos (aguarda o
  detalhamento da Luyla).
- A coluna "Emissão" do export de lançamentos financeiros (a única data que o parser lê) é de
  fato a data do pagamento? Luyla disse que sim ("o que o TON está pegando é a data do pagamento").
- Mossoró: Miriam teria falado em ~R$ 200 mil de resultado; ninguém confirmou.
- Lançamentos de financiamento da Pajero (parcela 7 faltando?) e empréstimo Castelo R$ 50 mil
  31/07 duplicado — conferir no extrato.

## 7. Implementado em 17/10 (local, sem commit, homolog intocado)

- DRE: visão lado a lado / mês a mês, soma só dos meses exibidos, clique na linha e no valor, editor de estrutura, cálculo automático, várias unidades somadas (com "Operacionais ativas" lido do cadastro e "×" para limpar), Excel por unidade / consolidado / conjunto, sem `#REF!`.
- Grupos da DRE: criados junto com a primeira natureza (Classificação → Naturezas → "Novo grupo da DRE" ou "+ Novo grupo" no cadastro de natureza), dentro ou fora do resultado.
- Unidades: aba com ativa/inativa e tipo editável.
- Pendências: ordem de trabalho, guia para a Classificação, chips por tipo de caso, seleção em lote, duplicidade lado a lado, decisão em um clique, textos novos.
- Correções de backend: batimento em centavos (NF 528), unidade que começou no meio do ano não fica mais bloqueada por "realizado ausente", resultado bloqueado é refeito quando as pendências mudam, prontidão 14 s → 2,3 s, cálculo do ano numa chamada (25 s → 0,8 s), regra do assistente para descontos de folha.
- Pendente: atribuir unidade a lançamento sem unidade (precisa de change OpenSpec: chave estável por registro), DRE econômica × caixa e parcelamentos (aguarda Luyla), extrato bancário (aguarda arquivo), custos fixos × NG (Drive desconectado), perfil da Luciana.
