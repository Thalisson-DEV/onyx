# Ata — Reunião TON × Controladoria Vale Norte (2026-10-03)

Participantes: Thalisson Damião, Luyla Karina (Controladoria). Duração ~55 min; encerrada antes do fim
por um imprevisto da Luyla (continuação marcada para segunda-feira, 2026-10-05, à tarde).
Fonte: transcrição do Google Meet. As notas automáticas do Gemini foram conferidas contra a
transcrição; correções na seção 6.

## 1. Decisões

| # | Decisão | Trecho |
|---|---|---|
| D1 | **Prioridade agora é a DRE** (resultado da empresa e de cada unidade/filial, que é o que a diretoria quer ver). Contratos e dotações vêm depois. | 00:28–00:30 |
| D2 | **Parcelamentos: a DRE mostra só a parcela efetivamente paga no mês em que foi paga** (DRE "mista": parcela de janeiro paga em março aparece em março). Os valores de abril (~R$ 90,9 mi) e maio (~R$ 38 mi) são erro de lançamento no NG: parcelamentos cancelados e refeitos sem excluir as parcelas futuras. A Luyla vai limpar no NG com o contador. | 00:23, 00:58 |
| D3 | **Relatório semanal de inconsistências por e-mail para o Financeiro**, gerado pelo TON, com regras, frequência e destinatários configuráveis na administração. | 01:05–01:08 |
| D4 | **Correções sugeridas pelo TON passam por aprovação humana** ("aprovado ou rejeitado, corrija dessa forma"). | 00:39 |
| D5 | NF 392 de Toledo: **é duplicidade** (líquidos 616 mil × 706 mil possivelmente por juros/atraso; só o gestor da unidade explica). O certo é o Financeiro corrigir no NG; até lá exclui-se uma linha. O tratamento do TON (manter uma, excluir a cópia) está alinhado. | 01:02–01:06 |
| D6 | Formato da DRE do TON **está "quase igual" ao do Power BI**; a Luyla vai comparar em detalhe na segunda ou terça. Drill-down por lançamento foi muito bem recebido. | 00:45–00:47 |
| D7 | Orçado zerado **era esperado**: nem a Controladoria fez ainda a compatibilização dotação → natureza (também não está no BI). | 00:48–00:49 |

## 2. Pedidos novos da Luyla

1. **Ver/montar a DRE no Excel**, podendo acrescentar linhas, outro centro de custo e cálculos próprios (`dre-excel-export`).
2. **Comparar com o mesmo período do ano anterior** por unidade (ex.: folha no fim de ano) — depende de 2025; ela prefere trazer 2025 pela VPN, não por tratamento manual.
3. **Exportar lançamentos do NG em Excel pelo TON**, já com as correções que eles fazem hoje à mão.
4. **Cadastro de classificação editável no TON** (tabela tipo Excel na administração): quando surgir conta/descrição nova no NG, o TON acusa, pré-classifica por regras definidas pela Controladoria e pede revisão. Hoje isso é feito à mão numa planilha.
5. **Checar natureza × CNPJ do fornecedor**: ex.: combustível lançado como "despesas extras" perde crédito de PIS/COFINS. Hoje o contador revisa item a item e demora (PIS/COFINS de julho chegou no fim de setembro).
6. **Cálculo automático de PIS/COFINS** no futuro; ela tem a planilha Excel com as fórmulas.
7. **Frota lançada direto no TON**, em tempo real, substituindo a planilha estática mantida por um gerente (Igor).
8. Indicadores de folha (ex.: hora extra) a partir do NG — ela passa a lista na próxima semana.
9. Renomear **"Escopo" → "Unidades/filiais"** e o especialista **PROCUREMENT → "Compras/Suprimentos"**.

## 3. Fatos de processo aprendidos

- Fluxo atual de inconsistências: Controladoria filtra → manda relatório ao Financeiro → Financeiro corrige no NG → Controladoria reextrai tudo e confere. Correção retroativa obriga a refazer os meses seguintes (ex.: correção de março refez março–junho).
- As 4 linhas rejeitadas e parte dos "sem unidade" vêm de **quebra de linha do export do NG** quando a descrição é longa (valor fora da coluna, detalhe sem resumo, valor inválido). A VPN resolve; a Eloía tem uma macro que corrige o export.
- Atribuição manual de unidade é feita pela **cidade do CNPJ do fornecedor**.
- Classificação: quando aparece descrição de conta nova no NG, classificam à mão (estrutura do balanço + natureza).
- Unidades começaram a lançar direto no NG (descentralização em andamento; rotatividade atrasa).
- Os 29 códigos fora do Banco de Dados: a folha a Luyla conhece (códigos antigos ainda em uso); **mútuos e fundo fixo ela precisa revisar**.
- Dotações: só Mossoró, Juazeiro-BA e Itabirito estão em 2026; as demais existem só de anos anteriores e a licitação está atualizando.
- Fontes existentes: **contratos** (planilha Excel de controle com links para contrato e aditivos), **frota** (planilha do Igor). RH: alguma base. Compras: não. Compliance: com o gerente.
- PIS/COFINS: o percentual de julho e agosto chegou "antes de ontem"; a DRE de jul/ago depende dele.

## 4. Próximos passos

| Responsável | Ação |
|---|---|
| Thalisson | Testar com o Celso (2026-10-03, ~9h) se o TON acessa o servidor com VPN e qual VPN é |
| Thalisson | Enviar pelo WhatsApp a lista dos 29 códigos classificados por semelhança |
| Thalisson | Especificar e construir: integração NG, relatório semanal de inconsistências, verificação de correção, cadastro de classificação |
| Luyla | Enviar a planilha Excel de cálculo de PIS/COFINS (link) |
| Luyla | Limpar os parcelamentos no NG com o contador |
| Luyla | Mostrar a planilha de controle de contratos (segunda) |
| Luyla | Mostrar o fluxo NG → planilha → Power BI (segunda) |
| Luyla | Cobrar da licitação as dotações 2026 de todas as unidades |
| Luyla | Comparar a DRE do TON com o Power BI (segunda/terça) |
| Ambos | Reunião segunda-feira (2026-10-05) à tarde |

## 5. Perguntas que ficaram para segunda

- R1: receita da DRE vem do NG líquida ou do faturamento bruto com impostos como dedução? (ela adiou)
- Como o TON aplica "só a parcela paga" enquanto o NG não é limpo: o export/banco do NG distingue parcela paga de prevista (data de pagamento, status)?
- Os 19 sem unidade: usar a atribuição por cidade do CNPJ como regra?
- F3: folha da DRE pelo NG ou pela folha FG? (não chegou a ser perguntada)
- Mútuos e fundo fixo: ficam fora do resultado?
- Quem recebe o e-mail semanal no Financeiro; quais regras entram no primeiro relatório.

## 6. Correções às notas automáticas do Gemini

- "Prejuízo acumulado de 128.287.818,81": o valor na DRE é **−R$ 128.226.287,81** (a transcrição truncou).
- "Erro de 95 milhões": a Luyla citou "95 milhões, se eu não me engano"; no NG são ~R$ 90,9 mi em abril e ~R$ 38,0 mi em maio.
- "Integrar com o NG para permitir a correção de registros": o TON **não escreve no NG**. Ele detecta, avisa e verifica; quem corrige é o Financeiro.
- "Luyla: enviar a base de 2025": ela disse que é melhor trazer 2025 pela VPN do que tratar manualmente.
- "19 lançamentos totalizaram 306 no mês e 30.000 negativos no ano": números ditos de cabeça, **não conferidos**.
- O Gemini não registrou os pedidos 4, 5, 7 e 9 da seção 2.
