## Why

A DRE real jan–jun/2026 do TON depende de escolhas que só a Controladoria pode validar e que hoje
estão implícitas no código ou em decisões de teste: PARCELAMENTOS de R$ 128,9 mi no acumulado (saldo
de acordos tributários lançado inteiro em abril e maio — Prompt Mestre §6.2 "evento não recorrente",
relatório de 15/06/2026 §3.1), tratamento da NF 392 (o TON mantém uma linha e exclui a cópia; a Luyla
zera as duas e usa a nota do faturamento), receita da DRE (NG líquida de retenções × faturamento
bruto com impostos deduzidos), "Movimentos não gerenciais" fora do resultado, mútuos/Chácara como
unidades do resultado, e os 19 sem unidade como "risco aceito". A reunião de 2026-10-03 com a Luyla
é o momento de obter essas decisões; elas precisam virar regras versionadas, aplicadas
deterministicamente e visíveis na DRE — não ajustes manuais.

## What Changes

- Novo registro de **tratamentos de fechamento**: cada tratamento é uma regra versionada com escopo
  (natureza/conta, unidade, período), efeito determinístico (excluir do resultado do período,
  reclassificar para linha X, substituir valor por fonte Y), autor, data, justificativa e evidência
  da decisão (ata/mensagem da Controladoria).
- A normalização aplica os tratamentos vigentes e registra quais versões usou; a DRE mostra, por
  linha, os tratamentos aplicados e o valor antes/depois.
- Tratamentos que exigem dado externo (ex.: "só a parcela paga entra" exige cronograma de parcelas)
  ficam bloqueados até a fonte existir, com a pendência declarada.
- Decisões de teste da preparação são substituídas por decisões reais da Controladoria (novas
  versões; o histórico permanece).

## Capabilities

### New Capabilities
- `closing-treatments`: tratamentos de fechamento validados pela Controladoria, versionados e aplicados na normalização/DRE.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/financial_domain.py` (aplicação), `backend/onyx/ton/dre/engine.py`
  (proveniência), nova tabela de tratamentos, UI DRE (indicador de tratamento) e Administração do TON.

## Dependências

- Respostas da Luyla às perguntas C1–C3, D1–D3, P1–P3, R1–R3 do guia de apresentação
  (`plans/ton/APRESENTACAO_LUYLA_2026-10-02.md` §6). Sem resposta, o tratamento fica como está e
  aparece como "ponto para validação".

## Estado de dado

Real. Cada tratamento validado deve ser comparado com o "Banco de Dados (Vale Norte).xlsm" e o BI.

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

- **Parcelamentos decidido (D2):** a DRE mostra só a parcela efetivamente paga, no mês do pagamento
  (DRE "mista", não competência). Os ~R$ 90,9 mi de abril e ~R$ 38 mi de maio são parcelas futuras de
  parcelamentos cancelados e refeitos que não foram excluídas no NG; a Luyla vai limpar no NG com o
  contador. Primeiro tratamento a implementar: "PARCELAMENTOS entram pela data de pagamento; parcela
  prevista e não paga fica fora do resultado". Pergunta aberta: o NG (export ou banco) identifica
  parcela paga × prevista? Se não, o tratamento fica bloqueado e a correção acontece na limpeza do NG.
- **NF 392 (D5):** confirmada como duplicidade; o tratamento atual (manter uma linha, excluir a cópia,
  pedir correção no NG) está alinhado. Substituir as decisões de teste por uma decisão com
  justificativa da Controladoria.
- **19 sem unidade:** a Controladoria atribui pela cidade do CNPJ do fornecedor; regra candidata em
  `supplier-nature-consistency`. Até lá, ficam em "Sem unidade no NG".
- **Receita (R1), folha (F3), mútuos e fundo fixo:** adiados para a reunião de segunda (2026-10-05).

## Atualização de 2026-10-23 (atas da Controladoria de 16/10 e 20/10 lidas no Drive + reunião de 23/10)

As atas de 16/10 e 20/10 são documentos da própria Controladoria (reunião com a Miriam), lidos na
pasta compartilhada em 23/10. Cada item abaixo vira **tratamento candidato** ou ajuste de estrutura,
confirmado por escrito antes de aplicar.

**Estrutura e ordem da DRE (ata 16/10):** Faturamento → Retenções → Subtotal líquido → Pagamentos →
Subtotal líquido → Taxas → Provisões → Tributos não pagos → Ajustes do IR → Resultado líquido;
provisões no fim da estrutura.

**Itens da ata de 20/10 (Vale Norte):**
- excluir a **taxa de contingência de 1%** (fica só a taxa de administração; avaliar se os 2% de cada
  contrato bastam para a administração central). Hoje o assistente propõe a contingência de 1% como
  padrão: corrigir em `agentic-assistant`;
- ratear o **termo de apostilamento** no faturamento da DRE e mostrar o apostilamento separado;
- "revisar a estrutura igual à de Ferrari" (a esclarecer com a Luyla);
- separar os custos do **terreno do aterro de Mossoró**: sair de despesa com terreno e entrar em
  despesa de aterro, com rubrica própria (ata de 16/10);
- suprimir a conta **"Estorno de Despesa"** no faturamento (devoluções de colaboradores); definir o
  tratamento do estorno de **férias pagas em duplicidade** em setembro (DP: será descontado a partir da
  próxima folha);
- **FGTS rescisório** classificado como rescisório mesmo que de competências anteriores, para não
  duplicar com o provisionado/folha;
- falta a provisão de **FGTS 40% da folha**;
- todo valor descontado do funcionário e repassado a terceiros/fisco identificado e classificado
  (INSS base, INSS férias, IRRF, consignado, vale-transporte, adicional noturno; reflexos como DSR);
- **rescisões deduzidas das provisões** correspondentes (hoje a fórmula duplica) — e, não urgente, um
  especialista de folha para a dedução provisão × efetivo (ver `hr-payroll-domain`);
- formalizar a planilha de **custos fixos** (Adm Central);
- item **"Despesas extraordinárias"** para o acordo extrajudicial de R$ 288 mil parcelado em 8x;
- reclassificar **Fan Card** para combustível; criar centro de custo de **Consultoria**; confirmar
  custos de cartório (protestos e baixas) (ata 16/10);
- no econômico, considerar as férias do mês e retirar o provisionamento de férias para não duplicar
  com a folha; provisionar multas rescisórias de FGTS pelo relatório analítico do DP (ata 16/10).

**Franquias/NC3 (ata 20/10, Eric):** indicadores e notas explicativas; rateio "Administração Local
(NC3)" e "Administração Central (1%)"; tirar da DRE NFs de implantação (Julimar, ~R$ 53 mil da Bauducco
em janeiro) e manter custos de implantação fora da DRE operacional; royalties por competência; juros e
antecipação pelos extratos de cartão; capital de giro no fluxo de caixa; estimativa de CMV; detalhar
provisões trabalhistas e de aluguel. **Fora do escopo atual do TON (outra empresa do grupo) até a
Luyla confirmar.**

**Parcelamentos (reunião de 23/10):**
- A Luciana preenche o modelo "Parcelamentos pagos" do TON. Junho ficou sem pagamento de nenhum
  parcelamento. Combinado: as parcelas não pagas são marcadas na coluna em branco (I) com o status
  "não paga", e o TON considera pagas as demais. O modelo e o perfil ganham a coluna de status
  (oferecida pelo Thalisson).
- Outros parcelamentos podem surgir (procuradoria; pedidos de outras pessoas que a Controladoria ainda
  não acompanha). O modelo deve aceitar novos credores sem mudar o layout.
- Consórcios Bradesco (5 veículos): parcelas pagas e restantes, falta o valor da parcela (ata 20/10;
  planilha na pasta Custos Fixos).

**Custos fixos (23/10):** a planilha de custos fixos é a **referência mensal** (meta: o que se deve
gastar por mês, ex.: energia, folha). Em 2027 a Controladoria compara na DRE da matriz. Liga com
`budget-vs-actual`.

**Apagar linha da DRE (23/10):** a Luyla pediu para excluir uma linha (ex.: "imposto sem faturamento",
que já está dentro de um grupo). Hoje só dá para ocultar ou tirar do resultado; o chat não exclui. O
Thalisson disse que consegue incluir. Ver `agentic-assistant`.
