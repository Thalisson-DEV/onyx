## Why

Na reunião de 2026-10-23 a Luyla disse que o contas a pagar das unidades é "uma das prioridades, eu
atuaria mais nisso", porque alimenta a DRE "da forma mais real possível" e permite confrontar TON × NG
("aqui faltou lançar"). Hoje seis unidades mandam toda semana um Excel, cada uma num modelo, com NF e
boleto soltos no e-mail e nomes de arquivo aleatórios. Três pessoas do financeiro conferem linha a
linha, imprimem nota e boleto, passam para quem paga, lançam no NG (descrição, unidade, natureza) e dão
baixa com o comprovante. Falta informação (natureza, placa, destino da peça), falta anexo, e o
financeiro liga para a unidade ou para o fornecedor pedindo segunda via. Parte das solicitações já vai
pelo Zeev (solicitação de pagamento, reembolso), parte ainda por planilha, sem motivo claro.

A análise dos arquivos de 2026-10-21/22 (pasta compartilhada "Contas a PAGAR - Unidades") mostrou:
pelo menos 4 modelos (9 a 19 colunas); fornecedor sem CNPJ e com nomes diferentes; estimativas
misturadas com contas reais; fórmulas quebradas (`#VALUE!`, `#REF!`, desconto copiado de outra
linha); NF e parcela repetidas em mais de uma unidade; folha, INSS e FGTS dentro do contas a pagar da
unidade; medições lançadas como "crédito"; status "em atraso" calculado pela data de hoje; dados
bancários em texto livre, às vezes em nome de terceiro.

Prompt Mestre: §3 (contrato de dados), §11 (ponto cego "processo sem rastreabilidade"), §13 (ledger),
T7 (pagamento sem apropriação), T8 (fornecedor × unidade), `NGF-XS-APPROVAL-MISSING`.

## What Changes

- **Entrada de contas a pagar no TON pela unidade**, uma linha por título (cada parcela é um título),
  enviada quando a nota chega: unidade (do usuário), fornecedor do cadastro, tipo e número do
  documento, emissão, competência, vencimento, parcela "x de y" e valor total da compra, valor do
  título, natureza, destino (veículo do cadastro, obra, estoque, administração), descrição e número
  do pedido no Zeev quando houver.
- **Anexos obrigatórios** (NF e boleto, ou recibo) guardados com nome padronizado; o TON confere valor
  e CNPJ do anexo com a linha (leitura determinística do XML/PDF quando possível; senão, conferência
  humana marcada).
- **Estimativas** como tipo próprio, separadas das contas reais, substituídas pela nota quando ela
  chega; estimativa vencida sem nota vira alerta.
- **Fluxo de trabalho do financeiro** no TON: recebido → conferido → liberado para pagamento → lançado
  no NG → pago (baixa). O status de pagamento vem da baixa no NG (e do extrato, quando conciliado),
  nunca digitado pela unidade. O TON não lança no NG nesta change (ver `ng-write-back`).
- **Fora da planilha da unidade:** saldo, totais, tabelas dinâmicas, status manual, folha, encargos e
  impostos (vêm do DP/NG), medições e faturamento (vêm do faturamento), dados bancários (ficam no
  cadastro do fornecedor).
- **Conferências determinísticas:** NF/parcela repetida; anexo diferente da linha; conta sem anexo;
  favorecido do pagamento diferente do fornecedor; mesma conta bancária para favorecidos diferentes;
  estimativa sem nota; fornecedor novo ou com nome parecido e CNPJ diferente; título enviado em cima do
  vencimento (regra de prazo a definir — o Zeev hoje monitora "menos de 5 dias úteis"); lançado no
  NG × enviado pela unidade (o que falta de cada lado).
- **Uso na DRE:** a econômica recebe o título pela competência; a de caixa só o que foi pago.
- Carga inicial dos fornecedores a partir do NG e das planilhas atuais; as planilhas não viram modelo.
- Avisos do fluxo com cópia para a Controladoria (`central@nucleocontroller.com.br`), como a ata da
  Controladoria de 20/10 já pede para os envios de contas a pagar das unidades.
- Para lançar no NG o financeiro precisa saber para qual unidade e local foi a compra (ex.: ferramenta
  da ITA para qual unidade) e, em peça, a placa: esses campos são obrigatórios na entrada.

## Capabilities

### New Capabilities
- `unit-payables`: entrada de contas a pagar pelas unidades, anexos, estimativas, fluxo do financeiro,
  conferências e confronto com o NG.

### Modified Capabilities
<!-- nenhuma; o cadastro de fornecedores é compartilhado com `procurement-domain` -->

## Impact

- Backend: novo domínio `onyx/ton/payables` (títulos, anexos, estados), cadastro de fornecedores
  compartilhado, regras, armazenamento de arquivo (file store do Onyx ou o que vier do
  `platform-ces-foundation`), ligação com fatos do NG.
- Frontend: tela da unidade (enviar título, ver pendências do financeiro), fila do financeiro
  (conferir, liberar), detalhe com anexos e histórico. Provável uso no celular pelos gestores.
- DRE: origem econômica por competência e de caixa por pagamento.

## Dependências

- Validação do documento de padrão pela Controladoria (enviado em 2026-10-23) e respostas às
  perguntas dele (folha fora, quem mantém cadastros, prazo de envio).
- Lista de usuários das unidades (gestores e quem envia) e regras de acesso por unidade.
- Relação com o Zeev decidida em 2026-10-24: o TON lê a solicitação de pagamento do Zeev e concilia
  com o título enviado pela unidade (pedido sem título, título sem pedido, valor/fornecedor/vencimento
  diferentes, aprovação ausente). Depende de `zeev-integration` sincronizando esses fluxos com
  confiabilidade.
- Piloto em Toledo e Mossoró (decidido em 2026-10-24).
- Para o status "pago": baixa do NG (export ou `ng-direct-integration`) e/ou extrato
  (`bank-reconciliation-cash`).
- Treinamento dos gestores; piloto com uma unidade (sugestão no documento: Toledo).

## Estado de dado

Real, com piloto numa unidade em paralelo à planilha antiga por um mês.
