# Reunião TON × Vale Norte — 19/10/2026 (segunda, 9h30)

Participantes: Luyla e Luciana Miranda (Controladoria Vale Norte), Thalisson Damião (Eloí ao lado).
Fontes: notas do Gemini e transcrição. As notas do Gemini têm erros; as correções estão no §2.

## 1. O que foi decidido

| # | Decisão | Situação |
|---|---|---|
| 1 | Luyla refaz julho e agosto à mão (o NF veio com número interno do documento, não o da nota) e reenvia | Com a Luyla |
| 2 | Parcelamentos fora do resultado enquanto o NG não é corrigido | Feito por ela na reunião com um tratamento de fechamento (EXCLUDE da natureza PARCELAMENTOS, todas as unidades e períodos) no homolog; a linha ficou zerada no consolidado |
| 3 | Ocultar natureza/grupo na estrutura da DRE, com histórico, motivo e volta de versão | Pronto local (§3) |
| 4 | Notificação de erros de parcelamento no e-mail semanal, pedida pelo chat do Tom | A automação aceita pedidos pelo chat ("Pedir ao TON"); testar com ela quando o envio de e-mail funcionar |
| 5 | Faturamento continua vindo da planilha Excel (não do NG) | Já é assim |
| 6 | Parcelamentos de jan a set vêm de uma planilha à parte, no lugar do NG | Pronto local (§3); modelo para ela preencher em `TON_Entregas/TON - Modelo parcelamentos pagos - 2026-10-19.xlsx` |
| 7 | Ver qual registro tem problema nas Fontes | Pronto local (§3) |
| 8 | DRE econômica (competência) | Aguarda Luyla alinhar com o Eric como extrair o relatório por competência no NG |
| 9 | DRE de custos fixos (Administração Central) + cruzamento banco × NG × planilha | Aguarda a planilha ajustada com a Luciana e o extrato (Cláudia) |
| 10 | Envio de e-mail com remetente `central@nucleocontrole…` | Falta o endereço completo, a chave do Resend (ou SMTP) e a verificação do domínio |

Prazos: Luyla entrega as estruturas e planilhas até o fim do dia 19/10; reunião com a Miriam em 20/10 (dependia da agenda dela); apresentação oficial à diretoria na quarta, 21/10. Thalisson disse que talvez não consiga fechar as duas DREs novas no dia 19; Luyla aceitou fazer pelo Excel no máximo.

## 2. Correções às notas do Gemini

- "Opção para ocultar parcelamentos foi implementada": na reunião o efeito veio do **tratamento de fechamento** (EXCLUDE). A opção de ocultar na estrutura foi feita depois, local.
- "Thalisson subiu atualização para visualizar registros": ele disse que ia subir, mas **não foi publicado** no homolog; ficou local.
- As 15 linhas rejeitadas do faturamento: 12 vinham de abas de anos anteriores ("MATRIZ 2013" … "VALE NORTE 2024"), MACAU e CONSÓRCIO GUARULHOS; só 3 estão na aba "VALE NORTE 2025-2026" (2 datas inválidas, 1 competência fora do ano).
- "Uso de tabela Excel para parcelamentos … em vez do NG": é uma planilha **de parcelamentos pagos** de janeiro a setembro; o faturamento é outra fonte.
- Remetente do e-mail: "central@nucleocontrole" está incompleto (domínio não dito por inteiro).

## 3. Implementado em 19/10 (local, sem commit, homolog intocado)

- **Fontes → linhas com problema → "Ver linhas"**: aba, linha, coluna e o conteúdo da linha lido do próprio arquivo importado, com a célula problemática destacada; NG com os nomes das colunas e a conta do bloco.
- **Faturamento lê só as abas vigentes**: abas cujo ano no nome é anterior ao penúltimo ano do arquivo ficam fora ("Aba fora do período esperado"). Com o arquivo de setembro: 15 → 5 problemas, todos reais.
- **Estrutura da DRE**:
  - grupo e natureza podem ser ocultados (continuam somando);
  - natureza pode sair do resultado ("Fora do resultado"): mantém o valor, marcado na DRE e no Excel, mas o grupo não soma — substitui o tratamento de fechamento quando a mudança é da estrutura;
  - aba **Histórico**: cada versão com autor, data, motivo e as mudanças em palavras; "Voltar para esta versão" mostra a prévia antes de confirmar e cria uma versão nova.
- **Fonte "Parcelamentos pagos"** (Excel, opcional): lida pelo cabeçalho (Mês ou Data de pagamento, Unidade, Valor pago; Conta NG, Credor, Nº do parcelamento, Parcela opcionais). Em cada natureza e mês da planilha, os lançamentos do NG ficam zerados como "Substituído pela planilha de parcelamentos" e entram os valores da planilha. Testado no banco local com uma planilha de teste: 16 lançamentos do NG (R$ 128,9 mi) substituídos, DRE do ano calculada nos 9 meses.
- Revertido: o filtro por conta do NG nos tratamentos (Thalisson pediu para desconsiderar; a regra por natureza já atendeu).

## 4. Pendências

- Publicar no homolog quando a Luyla não estiver testando (migração `d2f6a8c4e1b9`).
- Receber da Luyla: julho e agosto refeitos, planilha de parcelamentos (ou confirmar o modelo), planilha de custos fixos, modelo da DRE econômica, orientação do Eric sobre competência, lista de e-mails das unidades.
- E-mail: endereço completo do remetente, conta Resend com o domínio verificado (ou SMTP do provedor), variáveis no Railway.

## 5. Tarde de 19/10 — pacote "DRE Set-26" e extratos (local, sem commit)

- **DRE Caixa e DRE Econômica (simplificadas)**, no modelo `DRE_Mossoro_Caixa_Competencia_2026.xlsm`: estruturas derivadas da gerencial (migração `e4b8d2f6a0c3`), mesmas naturezas reagrupadas; acompanham sozinhas cada versão nova da gerencial. Seletor "Modelo da DRE" na tela; botão "Criar DRE Caixa e Econômica" para o admin quando ainda não existem. Mossoró bate centavo por centavo com o modelo (Caixa jan: 4.425.443,66 / −2.365.097,13 / −13,60 / 2.060.332,93). Linhas de ajuste manual existem, zeradas.
- Financiamento, Investimento, Mútuo e Não gerenciais: bloco fora do resultado. Fundo fixo em Pagamentos (como no modelo).
- NG de 18/10: só janeiro mudou; julho/agosto ainda não refeitos. Números de documento vinham como `2596.0` — corrigido no parser.
- **Extratos jul–set** (Extrato Bancário Analítico do NG, PDF): lidos com totais conferidos ao centavo. Conferência com o NG em `TON_Entregas/TON - Conferencia extrato x NG - jul a set 2026.xlsx`. Achado: a data do NG não é a data do pagamento (salário de julho no NG 31/07, pago 06/08; locação Vamos de maio paga 14/09); só ~2/3 das saídas casam no mesmo dia.
- Custos fixos (Adm Central): diagnóstico por conta do NG e fornecedor; não cabe como estrutura de DRE (natureza é mais grossa que a conta NG).
