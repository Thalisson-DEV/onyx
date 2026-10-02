# TON — PROCESSO DA LUYLA E PROBLEMAS FINANCEIROS CONHECIDOS

## Fonte principal

`Relatorio_Inconsistencias_Jan_Abr_2026_ValeNorte.txt`

Período original do relatório:
Jan–Abr/2026.

**Importante:** os valores abaixo são históricos de um relatório de 15/06/2026. Eles são contexto de problema, não “estado atual” sem nova validação.

---

# 1. Processo atual da Controladoria

Luyla explicou que:

- o NG/Keevo gera exportações financeiras que precisam de tratamento;
- os lançamentos são revisados/corrigidos e versões “ok” existem;
- o processo é mensal;
- correções retroativas podem exigir refazer competências posteriores;
- faturamento é manualmente preenchido e tratado como fonte oficial;
- PIS/COFINS vem da Contabilidade;
- Dotação é mantida por unidade/gestor;
- Zeev é usado para processos/SLA/produtividade;
- a DRE/DFC é produzida no Power BI.

## Excel mãe

`Banco de Dados (Vale Norte).xlsm`

Esse arquivo é o “Excel mãe” que alimenta o BI.

Processo legado:

```text
NG export
→ revisão humana “ok”
→ VBA FINANCEIRO
→ FATURAMENTO
→ FOLHA
→ Power Query
→ BANCO DE DADOS
→ Power BI
```

Ele é importante como **linhagem de negócio**, não como arquitetura futura do TON.

---

# 2. POP Controladoria

POP citado:
`POP-CTR-01 — Emitir relatório de lançamentos financeiros e folha para gerar DRE/DFC no Power BI`

Pontos importantes:

- Faturamento deve chegar ao Financeiro até dia 05;
- PIS/COFINS até dia 05;
- Dotação é atualizada anualmente;
- NG Financial report é tratado e entra no banco até dia 09;
- folha/FGTS e relatório entram até dia 05;
- Controladoria analisa semanalmente/mensalmente;
- DRE/DFC é produzida até dia 10;
- Diretoria valida mensalmente.

O POP reconhece Centro de Custo, Centro de Resultado e Unidade Administrativa como identificadores importantes.

Para DRE gerencial, a Natureza Gerencial é mais consistente que Conta Gerencial.

---

# 3. Problemas financeiros históricos conhecidos

## 3.1 Parcelamentos tributários no resultado

Abril/2026:
~R$ 90,9MM foram lançados como despesa/resultados referentes ao saldo total dos acordos tributários.

O relatório interpreta que não deveriam representar a saída de caixa do mês.

Ação proposta:
- retirar saldo total da DRE periódica;
- registrar apenas parcela mensal efetivamente paga;
- tratar saldo como passivo tributário renegociado;
- confirmar cronograma/valores com jurídico/tributário.

### O que TON deve aprender
Não basta detectar “valor enorme”.
Precisa entender semântica do lançamento e competência.

---

## 3.2 Impostos s/Faturamento com Valor Final zero

139 lançamentos.
~R$ 9,6MM em movimento negativo, mas Valor Final zero.

Hipótese do relatório:
retenções podem estar sendo deduzidas no faturamento e não transitando como grupo de impostos.

TON deve:
- cruzar NG × faturamento;
- identificar divergência;
- mostrar evidência;
- pedir confirmação quando a semântica não estiver fechada.

---

## 3.3 Mútuos internos / Chácara

~R$ 4,2MM no período foram classificados como DESPESAS DIVERSAS.

O relatório afirma que parte deveria ser tratada em Ativo/Passivo e/ou Ativo em Formação.

TON deve perceber o impacto na leitura da rentabilidade e não tratar necessariamente como custo operacional de contrato.

---

## 3.4 Despesas jurídicas/engenharia

Jan+Fev/2026:
crescimento de ~R$ 72,5K em 2025 para ~R$ 473,8K em 2026.

Um item de ~R$ 323,7K de consultoria em Itabirito estava mascarado.

Problema:
sem fornecedor identificável não existe auditoria adequada.

TON deve tratar identidade/documentação como requisito de confiança.

---

## 3.5 Encargos sociais

Jan+Fev/2026:
encargos ~R$ 2,94MM / folha ~R$ 4,73MM ≈ 62%.

Relatório usa 35%–45% como referência de investigação.

Isso é **hipótese de análise do relatório**, não constante universal do TON.

TON deve:
- detectar;
- mostrar composição;
- pedir validação;
- não hard-code uma regra sem fonte/configuração aprovada.

---

## 3.6 Queda de receita de Mossoró

Abril/2026:
receita muito abaixo dos meses anteriores.

Hipóteses:
- NF pendente;
- suspensão;
- glosa;
- competência retroativa;
- outro evento contratual.

TON precisa cruzar faturamento/contrato/produção/medição e evitar conclusão prematura.

---

## 3.7 Despesas financeiras atípicas

Picos em fevereiro/março de 2026.

Hipóteses:
- encargos;
- IOF;
- parcelamentos;
- data errada;
- financiamento.

Novamente:
TON deve encontrar e explicar a divergência, não inventar causa.

---

## 3.8 Salto de receita em Itabirito

Abril/2026 teve pico de receita versus média anterior.

Hipóteses:
- medição retroativa;
- parcelas acumuladas;
- apostilamento;
- aditivo.

Precisa de contexto documental.

---

# 4. Falhas de processo importantes

## 4.1 Lançamentos concentrados no fechamento

Problema:
unidades enviam lançamentos acumulados.

Efeitos:
- fechamento atrasado;
- Financeiro sem visão antecipada;
- mais erros;
- retrabalho.

Proposta histórica:
rotina semanal de lançamentos e prazo de encerramento.

---

## 4.2 Contas a pagar incompletas

Problemas:
- NF sem conferência;
- fornecedor não cadastrado;
- competência ausente;
- unidade/centro de custo ausente;
- rateio de veículo ausente;
- risco de atraso/duplicidade.

Proposta:
checklist de Contas a Pagar e antecedência mínima.

---

## 4.3 Locações

~R$ 5,4MM acumulados no período histórico.

Problemas:
- competência;
- veículos compartilhados;
- identificação de unidade;
- duplicidade;
- falta de relatório consolidado.

TON futuro pode transformar isso em:
- source health;
- work queue;
- contrato/frota/reconciliação.

---

## 4.4 Fundo Fixo e viagens

Problemas:
- gastos invisíveis;
- prestação irregular;
- ausência de separação entre adiantamento e prestação;
- risco fiscal/trabalhista.

Propostas históricas:
- periodicidade;
- limite de prestação;
- bloqueio de novo adiantamento quando prestação permanece aberta.

---

## 4.5 Duplicidades

O relatório cita pagamentos com documentos iguais associados a fornecedores distintos.

Fluxo desejado:
1. extrato bancário identifica candidato;
2. gestor confirma;
3. se confirmado, devolução/estorno;
4. evidência fica registrada.

TON deve apoiar esse fluxo, não “decidir” sozinho.

---

## 4.6 Conciliação bancária

Foi identificada divergência entre banco e NG.

Possíveis causas:
- NG sem débito bancário;
- débito bancário sem NG;
- transferência intercompany em apenas uma ponta;
- diferença entre data de lançamento e compensação.

Automação proposta:
- importação de extratos;
- cruzamento com NG;
- remessa CNAB.

Este é um grande candidato a evolução futura do TON.

---

## 4.7 Dotações

Relatório histórico cita unidades com dotação desatualizada ou incompleta.

Sem orçamento comparável:
não existe controle sólido de desvio orçado × realizado.

No TON:
período de orçamento nunca deve ser inferido apenas por nome/arquivo ou pela divisão anual por 12.

---

## 4.8 Combustível

O relatório histórico aponta combustível como grande despesa e falta de controle consolidado sobre:

- postos conveniados;
- desconto;
- prazo;
- limite;
- consumo por veículo;
- posto correto.

Esse é um forte caso de futuro domínio FROTA.

---

# 5. Ações históricas da reunião Financeiro 15/06/2026

Entre os pontos registrados:

- corrigir tratamento de parcelamentos tributários;
- obter extratos bancários detalhados;
- revisar acessos bancários;
- identificar duplicidades;
- investigar queda de receita de Mossoró;
- identificar despesas financeiras atípicas;
- implantar rotina semanal de lançamentos;
- aprovar checklist de Contas a Pagar;
- padronizar histórico de locações;
- atualizar dotações;
- reclassificar mútuos/Chácara;
- levantar postos negociados;
- estudar automação de conciliação/CNAB;
- criar relatório de frota locada;
- identificar fornecedores mascarados;
- definir regras de prestação de contas.

Essas ações são uma mina de requisitos futuros para TON.

---

# 6. O que mais importa para o produto

O TON deve conseguir transformar problemas como esses em:

```text
detecção
→ evidência
→ impacto
→ responsável
→ decisão
→ ação
→ verificação
```

Não apenas em uma página com “13 pendências”.
